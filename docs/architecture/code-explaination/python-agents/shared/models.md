# models

> 跨 Agent 共享的 Pydantic 模型。

**模块路径**: `shared/models.py`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/models.py`

---

## 类

### `ErrorResponse(BaseModel)`

> 统一错误响应模型

**签名**: `class ErrorResponse(BaseModel)`

**字段**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `error` | `str` | 是 | 错误码 |
| `message` | `str` | 是 | 错误描述 |
