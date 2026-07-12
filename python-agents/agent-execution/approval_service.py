"""审批业务逻辑。

封装指令审批/驳回的业务规则：仅 PENDING_APPROVAL / PENDING 状态可审批。
DB CRUD 委托 shared.db（get_instruction / update_instruction_status / create_approval）。

错误不在本模块捕获，统一交由 main.py 异常处理器兜底。
"""

from shared import db

from .models import ApprovalDecision, ApprovalRequest


async def approve(instruction_id: str, req: ApprovalRequest) -> dict:
    """审批指令。

    - approve：状态推进到 APPROVED；
    - reject：状态推进到 REJECTED。
    同时写入 approvals 审批记录。返回更新后的指令记录。

    Raises:
        ValueError: 指令不存在或不在待审批状态。
    """
    instr = await db.get_instruction(instruction_id)
    if instr is None:
        raise ValueError(f"指令不存在: {instruction_id}")
    if instr["status"] not in ("PENDING_APPROVAL", "PENDING"):
        raise ValueError("指令不在待审批状态")

    new_status = (
        "APPROVED" if req.decision == ApprovalDecision.APPROVE else "REJECTED"
    )
    result = await db.update_instruction_status_and_create_approval(
        instruction_id=instruction_id,
        new_status=new_status,
        decision=req.decision.value,
        approver=req.approver,
        comment=req.comment,
    )
    if result is None:
        raise ValueError(f"指令不存在: {instruction_id}")
    return result
