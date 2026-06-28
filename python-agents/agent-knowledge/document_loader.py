"""文档加载与切分模块。

根据文件扩展名解析原始内容为纯文本，再按字符切分为带重叠的 chunk。
支持 .md/.txt/.pdf/.docx 四种格式。
"""

import io
from pathlib import Path

import docx
import pypdf


def load_and_split(
    content: bytes,
    filename: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """根据文件扩展名加载内容并切分为 chunk。

    Args:
        content: 文件原始字节。
        filename: 文件名（用于推断扩展名）。
        chunk_size: 单个 chunk 字符数，默认 500。
        overlap: 相邻 chunk 重叠字符数，默认 50。

    Returns:
        切分后的文本块列表（已过滤空字符串）。

    Raises:
        ValueError: 不支持的文件类型。
    """
    text = _load_text(content, filename)
    return _split_text(text, chunk_size, overlap)


def _load_text(content: bytes, filename: str) -> str:
    """按扩展名解析文件字节为纯文本。"""
    ext = Path(filename).suffix.lower()
    if ext in (".md", ".txt"):
        return content.decode("utf-8", errors="ignore")
    if ext == ".pdf":
        return _load_pdf(content)
    if ext == ".docx":
        return _load_docx(content)
    raise ValueError(f"不支持的文件类型：{ext}")


def _load_pdf(content: bytes) -> str:
    """提取 PDF 全部页文本并拼接。"""
    reader = pypdf.PdfReader(io.BytesIO(content))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n".join(pages)


def _load_docx(content: bytes) -> str:
    """提取 docx 全部段落文本并拼接。"""
    document = docx.Document(io.BytesIO(content))
    return "\n".join(p.text for p in document.paragraphs)


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """按字符切分，相邻段重叠 overlap 字符。"""
    if not text:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap 必须满足 0 <= overlap < chunk_size")

    step = chunk_size - overlap
    chunks: list[str] = []
    i = 0
    while i < len(text):
        chunk = text[i : i + chunk_size]
        if chunk:
            chunks.append(chunk)
        if i + chunk_size >= len(text):
            break
        i += step
    return chunks
