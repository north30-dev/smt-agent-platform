"""知识助手 Agent 的 Pydantic 请求/响应模型。

字段命名统一 snake_case，与 OpenAPI 契约对齐。
"""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """知识库问答请求体。"""

    question: str = Field(..., min_length=1, max_length=500, description="用户问题")


class SourceItem(BaseModel):
    """问答命中的来源片段。"""

    doc_id: str = Field(..., description="来源文档 ID")
    chunk_id: int = Field(..., description="来源分块 ID")
    score: float = Field(..., description="相似度得分")
    snippet: str = Field(..., description="命中文本片段")


class AskResponse(BaseModel):
    """知识库问答响应。"""

    answer: str = Field(..., description="大模型生成的答案")
    sources: list[SourceItem] = Field(..., description="命中的来源片段列表")


class DocumentInfo(BaseModel):
    """知识库文档元信息。"""

    doc_id: str = Field(..., description="文档 ID")
    doc_name: str = Field(..., description="文档名称")
    chunk_count: int = Field(..., description="分块数量")
    create_time: str = Field(..., description="入库时间（ISO-8601）")


class UploadResponse(BaseModel):
    """知识文档上传响应。"""

    doc_id: str = Field(..., description="文档 ID")
    doc_name: str = Field(..., description="文档名称")
    chunk_count: int = Field(..., description="分块数量")


class DeleteResponse(BaseModel):
    """知识库文档删除响应。"""

    success: bool = Field(..., description="是否删除成功")
    deleted_chunks: int = Field(..., description="实际删除的分块数量")
