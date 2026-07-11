# Python Execution Agent API

**版本**: v1.1 | **日期**: 2026-07-11 | **状态**: Phase 3-4

---

## 十、Python Execution Agent API

### 10.1 基础信息

| 项目 | 值 |
|------|-----|
| 服务名称 | agent-execution |
| 技术栈 | FastAPI + SQLAlchemy |
| 端口 | 8006 |
| 依赖服务 | PostgreSQL (5432) |

### 10.2 执行管理API

#### 10.2.1 创建执行指令

**端点**: `POST /v1/execution/command`

**请求体**:

```json
{
  "command_type": "MAINTENANCE",
  "target_device_id": 1,
  "description": "更换轴承",
  "priority": "HIGH",
  "assigned_to": "维修组A"
}
```

**响应示例**:

```json
{
  "command_id": "CMD-20260711-001",
  "status": "PENDING",
  "message": "指令创建成功"
}
```

#### 10.2.2 审批执行指令

**端点**: `POST /v1/execution/approve`

**请求体**:

```json
{
  "command_id": "CMD-20260711-001",
  "approved": true,
  "approver": "张工",
  "comment": "同意执行"
}
```

#### 10.2.3 上报执行进度

**端点**: `POST /v1/execution/progress`

**请求体**:

```json
{
  "command_id": "CMD-20260711-001",
  "progress_percent": 50,
  "status": "IN_PROGRESS",
  "remark": "轴承已拆卸，准备安装新件"
}
```

#### 10.2.4 查询指令列表

**端点**: `GET /v1/execution/commands`

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 指令状态筛选 |
| device_id | int | 否 | 设备ID筛选 |
