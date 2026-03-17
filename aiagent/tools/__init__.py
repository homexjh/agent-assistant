"""工具注册中心：统一管理所有工具的注册与执行"""
from __future__ import annotations
import inspect
import json
from .types import RegisteredTool, ToolDefinition
from .exec import exec_tool
from .file import read_tool, write_tool, edit_tool, apply_patch_tool, restore_tool
from .process import process_tool
from .web import web_fetch_tool, web_search_tool
from .memory import memory_search_tool
from .image import image_tool
from .pdf import pdf_tool
from .tts import tts_tool
from .browser import browser_tool
from .cron import cron_tool
from .git_enhanced import git_enhanced_tools

# ── 注册表 ────────────────────────────────────────────────
_registry: dict[str, RegisteredTool] = {}


def _register(tool: RegisteredTool) -> None:
    _registry[tool.name] = tool


_register(exec_tool)
_register(read_tool)
_register(write_tool)
_register(edit_tool)
_register(restore_tool)
_register(apply_patch_tool)
_register(process_tool)
_register(web_fetch_tool)
_register(web_search_tool)
_register(memory_search_tool)
_register(image_tool)
_register(pdf_tool)
_register(tts_tool)
_register(browser_tool)
_register(cron_tool)

# 注册增强 Git 工具
for name, definition, handler in git_enhanced_tools:
    # Construct full tool definition with proper structure
    full_definition: ToolDefinition = {
        "type": "function",
        "function": {
            "name": name,
            "description": definition["description"],
            "parameters": definition["input_schema"]
        }
    }
    _register(RegisteredTool(definition=full_definition, handler=handler))


# ── 公开 API ──────────────────────────────────────────────

def get_tool_definitions() -> list[ToolDefinition]:
    """返回所有工具的 schema 列表，直接传给 LLM API。"""
    return [t.definition for t in _registry.values()]


async def execute_tool(tool_call_id: str, name: str, arguments: str) -> dict:
    """
    执行一次 tool call。

    返回格式：
    {
        "role": "tool",
        "tool_call_id": ...,
        "content": ...,
    }
    """
    tool = _registry.get(name)
    if tool is None:
        available = ", ".join(_registry.keys())
        content = f'Error: Unknown tool "{name}". Available: {available}'
        return {"role": "tool", "tool_call_id": tool_call_id, "content": content}

    try:
        kwargs = json.loads(arguments)
    except json.JSONDecodeError as e:
        content = f"Error: Failed to parse tool arguments as JSON: {e}\narguments: {arguments}"
        return {"role": "tool", "tool_call_id": tool_call_id, "content": content}

    try:
        if inspect.iscoroutinefunction(tool.handler):
            content = await tool.handler(**kwargs)
        else:
            content = tool.handler(**kwargs)
    except Exception as e:
        content = f'Error executing tool "{name}": {e}'

    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}
