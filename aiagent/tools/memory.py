"""
memory.py - 记忆管理工具

综合功能：
  - memory_search: 原有功能（搜索/保存/清空/读取）
  - memory_get: 结构化读取（点号路径）
  - memory_set: 结构化写入（点号路径）
  - memory_list: 列出记忆内容
"""
from __future__ import annotations
import json
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING

from ..memory_manager import MemoryManager, get_memory_manager, get_user_manager
from .types import RegisteredTool, ToolDefinition

if TYPE_CHECKING:
    from ..agent import Agent

# 原有功能的文件路径
_MEMORY_FILE = Path(__file__).parent.parent.parent / "workspace" / "MEMORY.md"


def _ensure_memory_file() -> Path:
    """确保记忆文件存在"""
    _MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not _MEMORY_FILE.exists():
        _MEMORY_FILE.write_text("# Memory\n\n", encoding="utf-8")
    return _MEMORY_FILE


# ═══════════════════════════════════════════════════════════════
# 原有功能（保留兼容）
# ═══════════════════════════════════════════════════════════════

async def _memory_search_handler(
    action: str,
    query: str = "",
    content: str = "",
    tag: str = "",
    **_: object,
) -> str:
    """
    原有记忆搜索工具
    
    action:
      search  - 在 MEMORY.md 中全文搜索 query，返回匹配段落
      save    - 追加一条记忆到 MEMORY.md（带时间戳和可选 tag）
      clear   - 清空 MEMORY.md（保留标题）
      read    - 返回 MEMORY.md 全文
    """
    memory_file = _ensure_memory_file()

    if action == "read":
        return memory_file.read_text(encoding="utf-8")

    if action == "clear":
        memory_file.write_text("# Memory\n\n", encoding="utf-8")
        return "Memory cleared."

    if action == "save":
        if not content:
            return json.dumps({"status": "error", "error": "content is required for save"})
        ts = time.strftime("%Y-%m-%d %H:%M")
        tag_str = f" #{tag}" if tag else ""
        entry = f"\n## [{ts}]{tag_str}\n{content.strip()}\n"
        with open(memory_file, "a", encoding="utf-8") as f:
            f.write(entry)
        return f"Memory saved (tag={tag or 'none'})."

    if action == "search":
        if not query:
            return json.dumps({"status": "error", "error": "query is required for search"})
        text = memory_file.read_text(encoding="utf-8")
        # 简单全文搜索
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        matches = list(pattern.finditer(text))
        if not matches:
            return f"No matches found for '{query}'."
        # 提取匹配上下文
        results = []
        for m in matches:
            start = max(m.start() - 100, 0)
            end = min(m.end() + 100, len(text))
            snippet = text[start:end]
            results.append(f"...{snippet}...")
        return "\n\n---\n\n".join(results[:5])  # 最多返回5个结果

    return json.dumps({"status": "error", "error": f"Unknown action: {action}"})


# ═══════════════════════════════════════════════════════════════
# 新增结构化功能
# ═══════════════════════════════════════════════════════════════

async def _memory_get_handler(
    key: str,
    source: str = "memory",
    default: str | None = None,
    **_: object,
) -> str:
    """
    从结构化记忆文件读取值
    
    Args:
        key: 键路径，支持点号分隔，如 "facts.project.repo_path"
        source: 来源文件，"memory" 或 "user"
        default: 默认值（可选）
    
    Returns:
        值字符串
    """
    try:
        if source == "user":
            manager = get_user_manager()
        else:
            manager = get_memory_manager()
        
        value = manager.get(key, default)
        
        if value is None:
            return f"Key '{key}' not found in {source}.md"
        
        return str(value)
    
    except Exception as e:
        return f"Error reading memory: {e}"


async def _memory_set_handler(
    key: str,
    value: str,
    source: str = "memory",
    **_: object,
) -> str:
    """
    写入值到结构化记忆文件
    
    Args:
        key: 键路径，支持点号分隔，如 "facts.project.current_branch"
        value: 要设置的值
        source: 来源文件，"memory" 或 "user"
    
    Returns:
        成功/失败信息
    """
    try:
        if source == "user":
            manager = get_user_manager()
        else:
            manager = get_memory_manager()
        
        success = manager.set(key, value)
        
        if not success:
            return f"Failed to set '{key}': invalid path or type conflict"
        
        # 保存到文件
        save_success = manager.save()
        
        if save_success:
            return f"Successfully set {source}.{key} = {value}"
        else:
            return f"Value set but failed to save to file"
    
    except Exception as e:
        return f"Error writing memory: {e}"


async def _memory_list_handler(
    source: str = "memory",
    section: str | None = None,
    **_: object,
) -> str:
    """
    列出记忆内容
    
    Args:
        source: 来源文件，"memory" 或 "user"
        section: 指定 section（可选）
    
    Returns:
        格式化的记忆内容
    """
    try:
        if source == "user":
            manager = get_user_manager()
        else:
            manager = get_memory_manager()
        
        data = manager.get_all()
        
        if section:
            # 只显示指定 section
            section_data = data.get(section, {})
            if not section_data:
                return f"Section '{section}' not found"
            return _format_section(section, section_data)
        
        # 显示所有内容
        parts = []
        for sec_name, sec_data in data.items():
            parts.append(_format_section(sec_name, sec_data))
        
        return "\n\n".join(parts) if parts else "No memory entries"
    
    except Exception as e:
        return f"Error listing memory: {e}"


def _format_section(name: str, data: dict) -> str:
    """格式化 section 内容"""
    lines = [f"## {name}"]
    
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"\n### {key}")
            for sub_key, sub_value in value.items():
                lines.append(f"- {sub_key}: {sub_value}")
        else:
            lines.append(f"- {key}: {value}")
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 工具定义
# ═══════════════════════════════════════════════════════════════

# 原有工具（保留兼容）
memory_search_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "memory",
            "description": (
                "Search, save, read, or clear MEMORY.md entries. "
                "Use 'search' to find existing memories, 'save' to add new ones."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search", "save", "read", "clear"],
                        "description": "Action to perform",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (for action='search')",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to save (for action='save')",
                    },
                    "tag": {
                        "type": "string",
                        "description": "Optional tag for saved memory",
                    },
                },
                "required": ["action"],
            },
        },
    ),
    handler=_memory_search_handler,
)

# 新增结构化工具
memory_get_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "memory_get",
            "description": (
                "Read a value from structured memory files (MEMORY.md or USER.md). "
                "Supports dot notation for nested keys like 'facts.project.repo_path'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Key path using dot notation, e.g., 'facts.project.repo_path' or 'system.current_date'",
                    },
                    "source": {
                        "type": "string",
                        "enum": ["memory", "user"],
                        "description": "Source file: 'memory' for MEMORY.md (project facts) or 'user' for USER.md (user preferences)",
                        "default": "memory",
                    },
                    "default": {
                        "type": "string",
                        "description": "Default value if key not found",
                    },
                },
                "required": ["key"],
            },
        },
    ),
    handler=_memory_get_handler,
)

memory_set_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "memory_set",
            "description": (
                "Write a value to structured memory files (MEMORY.md or USER.md). "
                "Automatically creates sections if needed. Supports dot notation for nested keys."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Key path using dot notation, e.g., 'facts.project.current_branch'",
                    },
                    "value": {
                        "type": "string",
                        "description": "Value to set",
                    },
                    "source": {
                        "type": "string",
                        "enum": ["memory", "user"],
                        "description": "Source file: 'memory' for MEMORY.md or 'user' for USER.md",
                        "default": "memory",
                    },
                },
                "required": ["key", "value"],
            },
        },
    ),
    handler=_memory_set_handler,
)

memory_list_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "memory_list",
            "description": "List all memory entries or entries from a specific section",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "enum": ["memory", "user"],
                        "description": "Source file to list",
                        "default": "memory",
                    },
                    "section": {
                        "type": "string",
                        "description": "Specific section to list (optional)",
                    },
                },
            },
        },
    ),
    handler=_memory_list_handler,
)
