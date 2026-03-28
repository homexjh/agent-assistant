"""工具注册中心：统一管理所有工具的注册与执行"""
from __future__ import annotations
import inspect
import json
from contextvars import ContextVar
from .types import RegisteredTool, ToolDefinition

# 错误标准化支持
from ..error_parser import ErrorParser
from ..resource_bridge import emit_error

# 上下文变量：用于在工具中发送任务列表更新
todo_emitter: ContextVar[callable | None] = ContextVar('todo_emitter', default=None)

def set_todo_emitter(emitter: callable | None):
    """设置任务列表发送函数"""
    todo_emitter.set(emitter)

def emit_todo(todos: list[dict]):
    """
    在工具中调用以更新任务列表。
    todos: [{"id": str, "title": str, "status": "pending|in_progress|done|error"}]
    """
    emitter = todo_emitter.get()
    if emitter:
        emitter(todos)
from .exec import exec_tool
from .file import read_tool, write_tool, edit_tool, apply_patch_tool, restore_tool
from .process import process_tool
from .web import web_fetch_tool, web_search_tool
from .memory import (
    memory_search_tool,
    memory_get_tool,
    memory_set_tool,
    memory_list_tool,
)
from .image import image_tool
from .pdf import pdf_tool
from .tts import tts_tool
from .browser import browser_tool
from .cron import cron_tool
from .git_enhanced import git_enhanced_tools
from .daily_log import (
    daily_log_create_tool,
    daily_log_append_tool,
    daily_log_get_tool,
    daily_log_list_tool,
)
from .fms import (
    fms_retrieve_tool,
    fms_chat_tool,
    fms_list_files_tool,
    fms_download_tool,
)

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
_register(memory_get_tool)
_register(memory_set_tool)
_register(memory_list_tool)
_register(daily_log_create_tool)
_register(daily_log_append_tool)
_register(daily_log_get_tool)
_register(daily_log_list_tool)
_register(image_tool)
_register(pdf_tool)
_register(tts_tool)
_register(browser_tool)
_register(cron_tool)

# 注册 FMS 工具
_register(fms_retrieve_tool)
_register(fms_chat_tool)
_register(fms_list_files_tool)
_register(fms_download_tool)

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

    # 新增：解析错误并广播事件
    error = ErrorParser.parse(content, name)
    if error:
        context = {
            "tool_call_id": tool_call_id,
            "tool_name": name,
            "arguments": kwargs,
            "timestamp": error.timestamp,
        }
        emit_error(error, context)
        
        # 返回结构化错误（LLM 看到文本，机器可读 _structured_error）
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": error.to_llm_text(),  # LLM 看到友好文本
            "_structured_error": error.to_dict(),  # 机器可读（资源管理用）
        }

    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}
