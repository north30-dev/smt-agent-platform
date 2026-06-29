"""agent_knowledge.document_loader 单元测试。

覆盖 4 种文件格式（md/txt/pdf/docx）的 load_and_split 切分逻辑，
补齐 phase2 报告 B-2 盲区：真实 PDF/docx 解析此前零覆盖。

PDF 与 docx fixture 在测试内动态生成（避免提交二进制文件），
md/txt 从 tests/fixtures/ 读取。
"""

import io
from pathlib import Path

import docx
import pypdf
import pytest

from agent_knowledge.document_loader import load_and_split

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_load_and_split_markdown():
    """Markdown 文件应被解析为非空 chunks，且每块不超过 chunk_size。"""
    content = (FIXTURES_DIR / "sample.md").read_bytes()
    chunks = load_and_split(content, "sample.md", chunk_size=500, overlap=50)

    assert len(chunks) > 0
    assert all(len(c) <= 500 for c in chunks)
    # 验证内容确实被解析（非空字符串）
    assert any("钢网清洁" in c for c in chunks)


def test_load_and_split_txt():
    """纯文本文件应被解析为非空 chunks。"""
    content = (FIXTURES_DIR / "sample.txt").read_bytes()
    chunks = load_and_split(content, "sample.txt", chunk_size=500, overlap=50)

    assert len(chunks) > 0
    assert all(len(c) <= 500 for c in chunks)
    assert any("真空吸嘴" in c for c in chunks)


def test_load_and_split_pdf():
    """PDF 文件应通过 pypdf 解析路径不抛异常。

    限制：pypdf.PdfWriter 仅能生成空白页（无文本），reportlab 不在依赖中。
    本用例验证 PDF 解析路径正常返回（空白 PDF 返回空 chunks），
    含文本 PDF 的切分验证留待引入 reportlab 后补充。
    """
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    chunks = load_and_split(pdf_bytes, "sample.pdf", chunk_size=500, overlap=50)

    assert isinstance(chunks, list)
    assert all(len(c) <= 500 for c in chunks)


def test_load_and_split_docx():
    """docx 文件应通过 python-docx 解析为非空 chunks。"""
    doc = docx.Document()
    for i in range(20):
        doc.add_paragraph(f"SMT 设备维护第 {i + 1} 条：定期检查关键部件磨损情况。")
    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    chunks = load_and_split(docx_bytes, "sample.docx", chunk_size=500, overlap=50)

    assert len(chunks) > 0
    assert all(len(c) <= 500 for c in chunks)
    assert any("SMT" in c for c in chunks)


def test_load_and_split_unsupported_type():
    """不支持的文件类型应抛出 ValueError。"""
    with pytest.raises(ValueError, match="不支持的文件类型"):
        load_and_split(b"content", "sample.xlsx")
