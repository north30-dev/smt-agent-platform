"""执行指令业务逻辑。

封装指令创建、查询、进度更新的业务规则：
- 两种创建模式（自动生成 / 手动）；
- 自动执行判定（基于优先级与类型）；
- 指令状态机校验。

DB CRUD 委托 shared.db（init_execution_tables / create_instruction / get_instruction /
list_instructions / update_instruction_status），不在本模块直接操作连接池。
错误不在本模块捕获，统一交由 main.py 异常处理器兜底。
"""

from uuid import uuid4

from shared import db
from shared.config import settings
from shared.observability import get_counter

from .models import (
    InstructionCreateRequest,
    InstructionPriority,
    InstructionStatus,
    InstructionType,
    ProgressRequest,
)

# 合法状态跳转（current, target）
_VALID_TRANSITIONS: set[tuple[str, str]] = {
    ("APPROVED", "EXECUTING"),
    ("EXECUTING", "COMPLETED"),
    ("EXECUTING", "FAILED"),
    ("PENDING", "APPROVED"),
}


def _should_auto_execute(instr_type, priority) -> bool:
    """判定指令是否可自动执行（无需人工审批）。

    规则：priority 在自动审批列表 AND type 不在需审批类型 AND priority 不在需审批优先级。
    兼容 enum / str 入参（str, Enum 在 Python 3.11+ str() 返回带类名前缀，故取 .value）。
    """
    type_str = (
        instr_type.value
        if isinstance(instr_type, InstructionType)
        else str(instr_type)
    )
    priority_str = (
        priority.value
        if isinstance(priority, InstructionPriority)
        else str(priority)
    )
    return (
        priority_str in settings.execution_auto_approve_priorities
        and type_str not in settings.execution_require_approval_types
        and priority_str not in settings.execution_require_approval_priorities
    )


async def create_instructions(req: InstructionCreateRequest) -> list[dict]:
    """创建执行指令。

    两种模式：
    1. 自动生成（source_workflow_id 存在）：从 diagnosis 派生 REPAIR，
       从 schedule_adjustment 派生 PRODUCTION_ADJUST。
    2. 手动（type + payload 存在）：单条指令。

    每条指令：
    - instruction_id = f"instr-{uuid4().hex[:12]}"；
    - auto_execute 由 _should_auto_execute 判定；
    - status = APPROVED（自动执行）或 PENDING_APPROVAL（需审批）。

    Returns:
        创建后的指令 dict 列表（DB 返回的完整记录）。
    """
    plans: list[tuple[InstructionType, dict]] = []
    if req.source_workflow_id is not None:
        if req.diagnosis is not None:
            plans.append(
                (InstructionType.REPAIR, {"diagnosis": req.diagnosis})
            )
        if req.schedule_adjustment is not None:
            plans.append(
                (
                    InstructionType.PRODUCTION_ADJUST,
                    {"schedule_adjustment": req.schedule_adjustment},
                )
            )
    else:
        # 手动模式：model_validator 已保证 type + payload 存在
        plans.append((req.type, req.payload))

    created: list[dict] = []
    for instr_type, payload in plans:
        instruction_id = f"instr-{uuid4().hex[:12]}"
        auto_execute = _should_auto_execute(instr_type, req.priority)
        status = (
            InstructionStatus.APPROVED
            if auto_execute
            else InstructionStatus.PENDING_APPROVAL
        )
        record = await db.create_instruction(
            instruction_id=instruction_id,
            source_workflow_id=req.source_workflow_id,
            type=instr_type.value,
            payload=payload,
            status=status.value,
            priority=req.priority.value,
            auto_execute=auto_execute,
        )
        created.append(record)
        _instruction_created_counter = get_counter(
            "instruction_created_total", "创建的执行指令总数"
        )
        _instruction_created_counter.inc()
    return created


async def get_instruction(instruction_id: str) -> dict | None:
    """按 instruction_id 查询指令，不存在返回 None。"""
    return await db.get_instruction(instruction_id)


async def list_instructions(
    page: int = 1,
    size: int = 20,
    status: str | None = None,
    instruction_type: str | None = None,
) -> dict:
    """分页查询指令，委托 db.list_instructions。

    Returns:
        {records, total, page, size}
    """
    return await db.list_instructions(page, size, status, instruction_type)


async def update_progress(instruction_id: str, req: ProgressRequest) -> dict:
    """更新指令进度（状态机校验）。

    合法跳转：APPROVED→EXECUTING、EXECUTING→COMPLETED、EXECUTING→FAILED、
    PENDING→APPROVED。PENDING_APPROVAL→APPROVED 仅由审批接口触发，不在此处允许。

    Raises:
        ValueError: 指令不存在或非法状态跳转。
    """
    current = await db.get_instruction(instruction_id)
    if current is None:
        raise ValueError(f"指令不存在: {instruction_id}")
    current_status = current["status"]
    target = req.status.value
    if (current_status, target) not in _VALID_TRANSITIONS:
        raise ValueError(f"非法状态跳转: {current_status} → {target}")
    result = await db.update_instruction_status(
        instruction_id, target, note=req.note
    )
    if result is None:
        # 极端竞态：get 与 update 之间被删除
        raise ValueError(f"指令不存在: {instruction_id}")
    return result
