# 大模型服务 API

**版本**: v1.1 | **日期**: 2026-07-11 | **状态**: Phase 3-4

---

## 十一、大模型服务 API

### 11.1 基础信息

| 项目 | 值 |
|------|-----|
| 服务名称 | LLM Service |
| 技术栈 | OpenAI兼容API |
| 端口 | 由部署配置决定 |
| 当前模型 | 由部署配置决定 |

### 11.2 大模型调用API

#### 11.2.1 获取模型列表

**端点**: `GET /v1/models`

**认证**: Bearer Token

```http
GET http://your-llm-service-url/v1/models
Authorization: Bearer <token>
```

**响应示例**:

```json
{
  "data": [
    {
      "id": "google/gemma-4-e4b",
      "object": "model",
      "owned_by": "google"
    }
  ]
}
```

#### 11.2.2 对话补全

**端点**: `POST /v1/chat/completions`

**认证**: Bearer Token

**请求体**:

```json
{
  "model": "google/gemma-4-e4b",
  "messages": [
    {
      "role": "user",
      "content": "分析贴片机元件偏移的可能原因"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 1000
}
```

**响应示例**:

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "贴片机元件偏移可能由以下原因引起：1. 吸嘴磨损..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 120,
    "total_tokens": 135
  }
}
```
