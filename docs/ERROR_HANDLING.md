# 错误处理标准化指南

本文档介绍 AI PC Agent OS 的错误处理标准化系统。

## 概述

系统通过以下组件实现错误标准化：

- **AgentError**: 标准化错误数据结构
- **ErrorParser**: 将工具错误字符串解析为结构化错误
- **ResourceManagerBridge**: 资源管理系统对接接口

## 快速开始

### 查看错误是否被正确解析

```python
from aiagent.error_parser import ErrorParser

content = "Error: command timed out after 30s"
error = ErrorParser.parse(content, "exec")

if error:
    print(f"错误码: {error.code}")        # EXEC_TIMEOUT
    print(f"类型: {error.type.value}")    # temporary
    print(f"可重试: {error.retryable}")   # True
    print(error.to_llm_text())            # LLM 友好的文本
```

### 注册自定义错误处理器

```python
from aiagent.resource_bridge import register_error_handler
from aiagent.errors import AgentError

def my_error_handler(error: AgentError, context: dict):
    print(f"[{error.code}] {error.message}")
    print(f"Context: {context}")

register_error_handler(my_error_handler)
```

### 对接资源管理系统

```python
from aiagent.resource_bridge import ResourceManagerBridge, set_resource_manager

class MyResourceManager(ResourceManagerBridge):
    async def report_error(self, error: AgentError, context: dict):
        # 发送到你的资源管理系统
        await send_to_control_center(error.to_dict())
    
    async def request_resource(self, resource_type: str, amount: int) -> bool:
        return True
    
    async def release_resource(self, resource_type: str, amount: int):
        pass

# 注册
set_resource_manager(MyResourceManager())
```

## 错误类型

| 类型 | 说明 | 自动重试 |
|------|------|----------|
| `temporary` | 临时错误（超时、网络抖动） | 是 |
| `permanent` | 永久错误（命令不存在） | 否 |
| `resource` | 资源不足（内存、磁盘） | 否 |
| `permission` | 权限问题 | 否 |
| `dependency` | 依赖缺失 | 否 |
| `unknown` | 未知错误 | 否 |

## 错误码规范

格式：`{CATEGORY}_{DETAIL}`

### exec 工具
- `EXEC_TIMEOUT` - 命令执行超时
- `EXEC_SPAWN_FAILED` - 进程启动失败
- `EXEC_ERRNO_{N}` - 系统错误码

### browser 工具
- `BROWSER_ELEMENT_NOT_FOUND` - 元素未找到
- `BROWSER_NOT_INSTALLED` - 浏览器未安装
- `BROWSER_EXECUTION_ERROR` - 执行失败

### web 工具
- `HTTP_{CODE}` - HTTP 错误码
- `WEB_FETCH_ERROR` - 获取失败
- `WEB_SEARCH_ERROR` - 搜索失败

### file 工具
- `FILE_NOT_FOUND` - 文件不存在
- `FILE_PERMISSION_DENIED` - 权限拒绝
- `FILE_PATH_TRAVERSAL` - 路径遍历攻击

## 返回结构

工具执行错误时返回：

```json
{
  "role": "tool",
  "tool_call_id": "call_xxx",
  "content": "Error [EXEC_TIMEOUT]: Command timed out after 30s\n💡 This is a temporary error. You can retry after 5s.",
  "_structured_error": {
    "status": "error",
    "error": {
      "code": "EXEC_TIMEOUT",
      "type": "temporary",
      "severity": "warning",
      "message": "Command timed out after 30s",
      "tool": "exec",
      "retryable": true,
      "retry_after": 5,
      "details": {...},
      "timestamp": "2026-03-26T10:00:00"
    }
  }
}
```

- `content`: LLM 看到的友好文本
- `_structured_error`: 机器可读的结构化数据

## 测试

```bash
# 运行错误处理测试
uv run python -m pytest tests/test_error_handling.py -v
```

## 架构图

```
工具执行
    │
    ▼
ErrorParser.parse() ──→ AgentError
    │                       │
    │                       ▼
    │               emit_error()
    │                       │
    ▼                       ▼
LLM 友好文本          资源管理系统
    │                       │
    │                       ▼
    │               监控/告警/扩容
    ▼
返回给 LLM
```
