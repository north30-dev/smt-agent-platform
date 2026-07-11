# Python Knowledge Agent API

**版本**: v1.1 | **日期**: 2026-07-11 | **状态**: Phase 3-4

---

## 八、Python Knowledge Agent API

### 8.1 基础信息

| 项目 | 值 |
|------|-----|
| 服务名称 | agent-knowledge |
| 技术栈 | FastAPI + LangChain + Milvus |
| 端口 | 8004 |
| 依赖服务 | Milvus (19530)、LLM Service (1234) |

### 8.2 知识检索API

#### 8.2.1 知识问答

**端点**: `POST /v1/knowledge/query`

**请求体**:

```json
{
  "question": "贴片机元件偏移如何处理？",
  "context": {
    "device_type": "贴片机",
    "defect_type": "元件偏移"
  }
}
```

**响应示例**:

```json
{
  "answer": "贴片机元件偏移通常由以下原因引起：1. 吸嘴磨损...",
  "sources": [
    {
      "case_no": "QC-001",
      "title": "贴片机元件偏移处理案例",
      "relevance_score": 0.92
    }
  ],
  "llm_response": "根据知识库检索和历史案例分析，建议..."
}
```

#### 8.2.2 历史案例检索

**端点**: `POST /v1/knowledge/cases/search`

**请求体**:

```json
{
  "query": "温度异常导致焊接不良",
  "filters": {
    "device_type": "回流焊炉",
    "defect_type": "焊接不良"
  },
  "top_k": 5
}
```

**响应示例**:

```json
{
  "cases": [
    {
      "case_no": "QC-002",
      "device_type": "回流焊炉",
      "defect_type": "焊接不良",
      "symptom_description": "焊点虚焊或冷焊",
      "root_cause_analysis": "温度曲线参数不合适...",
      "corrective_actions": "优化温度曲线...",
      "effectiveness_score": 90.0,
      "relevance_score": 0.88
    }
  ],
  "total": 1
}
```

#### 8.2.3 上传知识文档

**端点**: `POST /v1/knowledge/upload`

**请求体**: `multipart/form-data`

**响应示例**:

```json
{
  "doc_id": "doc-2026-0001",
  "doc_name": "SMT印刷机维护手册.pdf",
  "chunk_count": 42
}
```

#### 8.2.4 文档列表

**端点**: `GET /v1/knowledge/docs`

**响应示例**:

```json
{
  "data": [
    {
      "doc_id": "doc-2026-0001",
      "doc_name": "SMT印刷机维护手册.pdf",
      "chunk_count": 42,
      "upload_time": "2026-07-11 10:00:00"
    }
  ]
}
```

#### 8.2.5 删除文档

**端点**: `DELETE /v1/knowledge/docs/{doc_id}`
