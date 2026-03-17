"""web_fetch / web_search 工具"""
from __future__ import annotations
import json
import re
import urllib.request
import urllib.parse
import urllib.error
from .types import RegisteredTool, ToolDefinition


# ── web_fetch ─────────────────────────────────────────────

def _html_to_text(html: str) -> str:
    """极简 HTML → 纯文本（去标签，保留换行结构）。"""
    # 去掉 script / style 块
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    # 块级标签换行
    html = re.sub(r"<(br|p|div|h[1-6]|li|tr)[^>]*>", "\n", html, flags=re.IGNORECASE)
    # 去掉剩余标签
    html = re.sub(r"<[^>]+>", "", html)
    # 解码常见 HTML 实体
    for ent, ch in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                    ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " ")]:
        html = html.replace(ent, ch)
    # 压缩空白
    lines = [ln.strip() for ln in html.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


async def _web_fetch_handler(
    url: str,
    max_chars: int = 8000,
    raw: bool = False,
) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; aiagent/1.0)",
        "Accept": "text/html,application/xhtml+xml,*/*",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read()
            # 尝试探测编码
            charset = "utf-8"
            m = re.search(r"charset=([^\s;]+)", content_type)
            if m:
                charset = m.group(1)
            text = body.decode(charset, errors="replace")
    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason}  url={url}"
    except Exception as e:
        return f"Error fetching {url}: {e}"

    if not raw and "html" in content_type.lower():
        text = _html_to_text(text)

    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[truncated, total {len(text)} chars]"

    return text


web_fetch_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "web_fetch",
            "description": (
                "Fetch content from a URL. "
                "HTML pages are converted to plain text automatically. "
                "Use for reading web pages, APIs, raw files, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch.",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Max characters to return (default 8000).",
                    },
                    "raw": {
                        "type": "boolean",
                        "description": "If true, return raw content without HTML stripping (default false).",
                    },
                },
                "required": ["url"],
            },
        },
    ),
    handler=_web_fetch_handler,  # type: ignore[arg-type]
)


# ── web_search ────────────────────────────────────────────

async def _web_search_handler(query: str, num: int = 5) -> str:
    """
    使用 DuckDuckGo Lite 搜索（无需 API key）。
    返回标题 + URL + 摘要列表。
    """
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; aiagent/1.0)",
        "Accept": "text/html",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"Error searching: {e}"

    # 提取搜索结果：title + url + snippet
    results: list[dict] = []
    # DuckDuckGo HTML lite 结构解析
    result_blocks = re.findall(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
        r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
        html, re.DOTALL
    )

    for href, title_html, snippet_html in result_blocks[:num]:
        title = re.sub(r"<[^>]+>", "", title_html).strip()
        snippet = re.sub(r"<[^>]+>", "", snippet_html).strip()
        # DuckDuckGo 的 href 是 //duckduckgo.com/l/?uddg=<encoded_url>
        real_url = href
        m = re.search(r"uddg=([^&]+)", href)
        if m:
            real_url = urllib.parse.unquote(m.group(1))
        if title:
            results.append({"title": title, "url": real_url, "snippet": snippet})

    if not results:
        # fallback: 提取所有带标题的链接
        links = re.findall(r'href="(https?://[^"]+)"[^>]*>([^<]{5,80})<', html)
        for href, text in links[:num]:
            results.append({"title": text.strip(), "url": href, "snippet": ""})

    if not results:
        return f"No results found for: {query}"

    lines = [f"Search results for: {query}\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   {r['url']}")
        if r["snippet"]:
            lines.append(f"   {r['snippet']}")
        lines.append("")

    return "\n".join(lines)


web_search_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "web_search",
            "description": (
                "Search the web using DuckDuckGo (no API key required). "
                "Returns a list of titles, URLs, and snippets. "
                "Use to find information, documentation, news, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query.",
                    },
                    "num": {
                        "type": "integer",
                        "description": "Number of results to return (default 5, max 10).",
                    },
                },
                "required": ["query"],
            },
        },
    ),
    handler=_web_search_handler,  # type: ignore[arg-type]
)
