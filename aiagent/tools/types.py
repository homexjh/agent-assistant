"""工具系统类型定义"""
from __future__ import annotations
from typing import Any, Callable, Awaitable, TypedDict


class ToolParameter(TypedDict, total=False):
    type: str
    description: str
    enum: list[str]


class ToolParameters(TypedDict, total=False):
    type: str
    properties: dict[str, Any]
    required: list[str]


class ToolFunction(TypedDict):
    name: str
    description: str
    parameters: ToolParameters


class ToolDefinition(TypedDict):
    type: str  # always "function"
    function: ToolFunction


# 工具处理函数：接收 kwargs，返回字符串结果
ToolHandler = Callable[..., Awaitable[str]]


class RegisteredTool:
    def __init__(self, definition: ToolDefinition, handler: ToolHandler):
        self.definition = definition
        self.handler = handler

    @property
    def name(self) -> str:
        return self.definition["function"]["name"]
