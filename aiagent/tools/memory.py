"""memory_search 工具：搜索 workspace/MEMORY.md + 持久化写入"""
from __future__ import annotations
import json
import re
import time
from pathlib import Path
from .types import RegisteredTool, ToolDefinition

_MEMORY_FILE = Path(__file__).parent.parent.parent / "workspace" / "MEMORY.md"


def _ensure_memory_file() -> None:
    _MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not _MEMORY_FILE.exists():
        _MEMORY_FILE.write_text("# Memory\n\n", encoding="utf-8")


async def _memory_handler(
    action: str,
    query: str = "",
    content: str = "",
    tag: str = "",
) -> str:
    """
    action:
      search  - 在 MEMORY.md 中全文搜索 query，返回匹配段落
      save    - 追加一条记忆到 MEMORY.md（带时间戳和可选 tag）
      clear   - 清空 MEMORY.md（保留标题）
      read    - 返回 MEMORY.md 全文
    """
    _ensure_memory_file()

    if action == "read":
        return _MEMORY_FILE.read_text(encoding="utf-8")

    if action == "clear":
        _MEMORY_FILE.write_text("# Memory\n\n", encoding="utf-8")
        return "Memory cleared."

    if action == "save":
        if not content:
            return json.dumps({"status": "error", "error": "content is required for save"})
        ts = time.strftime("%Y-%m-%d %H:%M")
        tag_str = f" #{tag}" if tag else ""
        entry = f"\n## [{ts}]{tag_str}\n{content.strip()}\n"
        with open(_MEMORY_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
        return f"Memory saved (tag={tag or 'none'})."

    if action == "search":
        if not query:
            return json.dumps({"status": "error", "error": "query is required for search"})
        text = _MEMORY_FILE.read_text(encoding="utf-8")
        # 按 ## 段落分割
        sections = re.split(r"\n(?=## )", text)
        matches = [s for s in sections if query.lower() in s.lower()]
        if not matches:
            return f"No memory entries matching: {query!r}"
        return f"Found {len(matches)} matching entries:\n\n" + "\n---\n".join(matches)

    return json.dumps({"status": "error", "error": f"Unknown action: {action}. Use search/save/read/clear."})


memory_search_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "memory_search",
            "description": (
                "Manage persistent memory stored in workspace/MEMORY.md. "
                "action='save': save a note or fact to memory with optional tag. "
                "action='search': full-text search across all memory entries. "
                "action='read': read all memory. "
                "action='clear': wipe all memory."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search", "save", "read", "clear"],
                        "description": "Action to perform.",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (required for search).",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to save (required for save).",
                    },
                    "tag": {
                        "type": "string",
                        "description": "Optional tag/category for the saved entry.",
                    },
                },
                "required": ["action"],
            },
        },
    ),
    handler=_memory_handler,  # type: ignore[arg-type]
)
