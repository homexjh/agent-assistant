"""
pdf 工具：提取 PDF 文本并用 LLM 分析

依赖：pdfminer.six（可选，未安装时降级为提示用户安装）
支持本地文件路径和 http/https URL。
"""
from __future__ import annotations
import io
import os
import urllib.request
from .types import RegisteredTool, ToolDefinition


def _parse_page_range(pages: str, total: int) -> list[int]:
    """解析页码范围字符串，返回 0-based 页码列表。例：'1-3,5' → [0,1,2,4]"""
    result: set[int] = set()
    for part in pages.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a.strip()), int(b.strip())
            result.update(range(start - 1, min(end, total)))
        elif part:
            n = int(part)
            if 1 <= n <= total:
                result.add(n - 1)
    return sorted(result)


def _extract_text_pdfminer(data: bytes, page_indices: list[int] | None = None) -> str:
    """用 pdfminer.six 提取 PDF 文本。"""
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTTextContainer

    pdf_file = io.BytesIO(data)
    pages_text: list[str] = []

    for page_num, page_layout in enumerate(extract_pages(pdf_file)):
        if page_indices is not None and page_num not in page_indices:
            continue
        page_text = ""
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                page_text += element.get_text()
        pages_text.append(f"[Page {page_num + 1}]\n{page_text.strip()}")
        if len(pages_text) >= 20:  # 最多 20 页
            break

    return "\n\n".join(pages_text)


def _load_pdf_bytes(path_or_url: str) -> bytes:
    p = path_or_url.strip()
    if p.startswith("http://") or p.startswith("https://"):
        req = urllib.request.Request(p, headers={"User-Agent": "aiagent/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    expanded = os.path.expanduser(p)
    if not os.path.exists(expanded):
        raise FileNotFoundError(f"PDF file not found: {expanded!r}")
    with open(expanded, "rb") as f:
        return f.read()


async def _pdf_handler(
    prompt: str = "Analyze this PDF document.",
    pdf: str | None = None,
    pdfs: list[str] | None = None,
    pages: str | None = None,
    max_chars: int = 12000,
) -> str:
    """提取 PDF 文本并用 LLM 分析。"""
    paths: list[str] = []
    if pdf:
        paths.append(pdf)
    if pdfs:
        paths.extend(pdfs)
    if not paths:
        return "Error: must provide 'pdf' or 'pdfs' parameter."
    if len(paths) > 10:
        return "Error: too many PDFs (max 10)."

    # 先检查 pdfminer 是否安装
    try:
        import pdfminer  # noqa
    except ImportError:
        return (
            "Error: pdfminer.six is not installed. "
            "Run: uv add pdfminer.six"
        )

    # 提取文本
    all_texts: list[str] = []
    for p in paths:
        try:
            data = _load_pdf_bytes(p)
        except Exception as e:
            return f"Error loading PDF {p!r}: {e}"

        try:
            page_indices = None
            if pages:
                page_indices = _parse_page_range(pages, 9999)
            text = _extract_text_pdfminer(data, page_indices)
        except Exception as e:
            return f"Error extracting PDF text from {p!r}: {e}"

        fname = os.path.basename(p)
        all_texts.append(f"=== {fname} ===\n{text}")

    combined = "\n\n".join(all_texts)
    if len(combined) > max_chars:
        combined = combined[:max_chars] + f"\n\n[truncated at {max_chars} chars]"

    # 调用 LLM
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.moonshot.cn/v1"),
        )
        model = os.getenv("MODEL", "kimi-k2-0711-preview")
        messages = [
            {
                "role": "user",
                "content": (
                    f"{prompt}\n\n"
                    f"PDF content:\n\n{combined}"
                ),
            }
        ]
        response = await client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            max_tokens=2048,
        )
        return response.choices[0].message.content or "(empty response)"
    except Exception as e:
        return f"Error calling LLM for PDF analysis: {e}"


pdf_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "pdf",
            "description": (
                "Extract text from a PDF file and analyze it with the LLM. "
                "Supports local file paths and http/https URLs. "
                "Requires pdfminer.six: uv add pdfminer.six"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Analysis prompt. Default: 'Analyze this PDF document.'",
                    },
                    "pdf": {
                        "type": "string",
                        "description": "Single PDF: local file path or URL.",
                    },
                    "pdfs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Multiple PDFs: list of paths or URLs (max 10).",
                    },
                    "pages": {
                        "type": "string",
                        "description": "Page range, e.g. '1-5' or '1,3,5-7'. Default: all pages.",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Max characters of extracted text to send to LLM. Default: 12000.",
                    },
                },
                "required": [],
            },
        },
    ),
    handler=_pdf_handler,  # type: ignore[arg-type]
)
