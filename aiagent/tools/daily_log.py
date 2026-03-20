"""
daily_log.py - 每日日志工具

工具列表：
  - daily_log_create: 创建今天的日志
  - daily_log_append: 追加内容到今天的日志
  - daily_log_get: 读取今天的日志内容
  - daily_log_list: 列出最近的日志
"""
from __future__ import annotations
from pathlib import Path

from ..daily_log import (
    create_daily_log,
    append_to_daily_log,
    get_daily_log_path,
    list_recent_logs,
)
from .models import ToolDefinition
from .base import RegisteredTool


# =============================================================================
# 日志工具
# =============================================================================

async def _daily_log_create_handler(summary: str = "") -> str:
    """创建今天的日志文件"""
    try:
        log_path = create_daily_log(summary=summary)
        return f"✓ 日志文件创建成功: {log_path}"
    except Exception as e:
        return f"✗ 创建失败: {e}"


daily_log_create_tool = RegisteredTool(
    definition=ToolDefinition(
        name="daily_log_create",
        description="创建今天的日志文件（如果不存在）",
        parameters={
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "今天的摘要，可留空"
                }
            },
            "required": []
        }
    ),
    handler=_daily_log_create_handler
)


async def _daily_log_append_handler(entry: str, section: str = "对话列表") -> str:
    """追加内容到今天的日志"""
    try:
        success = append_to_daily_log(entry, section)
        if success:
            return f"✓ 已追加到 [{section}]: {entry[:50]}{'...' if len(entry) > 50 else ''}"
        return f"✗ 追加失败"
    except Exception as e:
        return f"✗ 错误: {e}"


daily_log_append_tool = RegisteredTool(
    definition=ToolDefinition(
        name="daily_log_append",
        description="追加一条记录到今天的日志",
        parameters={
            "type": "object",
            "properties": {
                "entry": {
                    "type": "string",
                    "description": "要记录的内容"
                },
                "section": {
                    "type": "string",
                    "description": "目标 section，默认是'对话列表'",
                    "enum": ["对话列表", "重要事项", "待办", "摘要"],
                    "default": "对话列表"
                }
            },
            "required": ["entry"]
        }
    ),
    handler=_daily_log_append_handler
)


async def _daily_log_get_handler() -> str:
    """读取今天的日志内容"""
    try:
        log_path = get_daily_log_path()
        
        if not log_path.exists():
            # 自动创建
            create_daily_log()
            return f"日志文件不存在，已创建: {log_path}"
        
        content = log_path.read_text(encoding="utf-8")
        return content
    except Exception as e:
        return f"错误: {e}"


daily_log_get_tool = RegisteredTool(
    definition=ToolDefinition(
        name="daily_log_get",
        description="读取今天的日志内容",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    handler=_daily_log_get_handler
)


async def _daily_log_list_handler(days: int = 7) -> str:
    """列出最近的日志"""
    try:
        logs = list_recent_logs(days=days)
        
        if not logs:
            return f"最近 {days} 天没有日志文件"
        
        lines = [f"最近 {len(logs)} 个日志:"]
        for log in logs:
            lines.append(f"- {log.name}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"错误: {e}"


daily_log_list_tool = RegisteredTool(
    definition=ToolDefinition(
        name="daily_log_list",
        description="列出最近 N 天的日志文件",
        parameters={
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "查看最近几天的日志",
                    "default": 7
                }
            },
            "required": []
        }
    ),
    handler=_daily_log_list_handler
)


# 导出所有日志工具
__all__ = [
    "daily_log_create_tool",
    "daily_log_append_tool",
    "daily_log_get_tool",
    "daily_log_list_tool",
]
