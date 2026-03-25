# 错误标准化与资源管理系统对接方案

## 背景与动机

### 当前问题

当前框架的错误处理存在以下问题，阻碍与资源管理系统的对接：

1. **错误信息非结构化**：工具返回字符串错误 `"Error: command timed out after 30s"`，无法被程序解析
2. **错误类型不明确**：LLM 和外部系统无法区分临时错误（可重试）和永久错误（需终止）
3. **无错误事件机制**：错误发生时无法实时通知外部系统（如资源管理）
4. **重复错误无熔断**：同一工具连续失败时无限制策略，浪费资源

### 为什么现在就要做

虽然资源管理系统尚未对接，但：
- **架构预留成本更低**：现在定义接口，将来只需实现，避免大规模重构
- **错误模式积累**：现在就开始标准化收集，积累错误处理经验
- **LLM 兼容性**：可以渐进式改造，保持现有接口不变

---

## 目标

1. **短期（现在）**：
   - 定义标准化错误结构
   - 实现错误解析器（从字符串提取结构化信息）
   - 建立错误事件广播机制
   - 预留资源管理对接接口

2. **长期（对接时）**：
   - 资源管理系统实现 `ResourceManagerBridge` 接口
   - 实现自动重试、熔断、扩容等策略
   - 建立统一的错误监控和告警

---

## 架构设计

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   工具层     │────→│  ErrorNormalizer │────→│   LLM (兼容)    │
│ (保持现状)   │     │   (错误标准化)    │     │  看到字符串错误  │
└─────────────┘     └────────┬─────────┘     └─────────────────┘
                             │
                    ┌────────▼─────────┐
                    │   EventEmitter   │
                    │  (错误事件广播)   │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ↓              ↓              ↓
        ┌─────────┐   ┌──────────┐   ┌──────────────┐
        │  日志    │   │ 资源管理  │   │ 监控/告警    │
        │  记录    │   │  (预留)   │   │  (预留)      │
        └─────────┘   └──────────┘   └──────────────┘
```

### 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| `AgentError` | `aiagent/errors.py` | 标准化错误数据结构 |
| `ErrorParser` | `aiagent/error_parser.py` | 解析工具错误字符串 |
| `EventEmitter` | `aiagent/tools/__init__.py` | 广播错误事件 |
| `ResourceManagerBridge` | `aiagent/resource_bridge.py` | 资源管理对接接口 |

---

## 错误分类体系

### 错误类型（ErrorType）

| 类型 | 说明 | 示例 | 建议处理 |
|------|------|------|----------|
| `TEMPORARY` | 临时错误，可重试 | 网络超时、Rate Limit | 指数退避重试 |
| `PERMANENT` | 永久错误，无需重试 | 命令不存在、语法错误 | 立即终止 |
| `RESOURCE` | 资源不足 | 内存不足、磁盘满 | 扩容或清理 |
| `PERMISSION` | 权限问题 | 文件不可读 | 通知管理员 |
| `DEPENDENCY` | 依赖缺失 | Playwright 未安装 | 自动安装/提示 |
| `UNKNOWN` | 未知错误 | 未识别的错误格式 | 记录并告警 |

### 严重程度（Severity）

| 级别 | 场景 | 通知方式 |
|------|------|----------|
| `DEBUG` | 调试信息 | 仅日志 |
| `INFO` | 正常流程信息 | 日志 |
| `WARNING` | 可恢复的警告 | 日志 + 可选通知 |
| `ERROR` | 功能失败 | 日志 + 通知 |
| `CRITICAL` | 系统级故障 | 日志 + 立即告警 |

---

## 标准化错误结构

```json
{
  "status": "error",
  "error": {
    "code": "EXEC_TIMEOUT",
    "type": "temporary",
    "severity": "warning",
    "message": "Command timed out after 30s",
    "tool": "exec",
    "retryable": true,
    "retry_after": 5,
    "details": {
      "command": "npm install",
      "timeout": 30,
      "exit_code": null
    },
    "timestamp": "2026-03-25T15:30:00+08:00"
  }
}
```

### 错误码规范

格式：`{TOOL}_{ERROR_DETAIL}`

| 错误码 | 说明 | 所属工具 |
|--------|------|----------|
| `EXEC_TIMEOUT` | 命令执行超时 | exec |
| `EXEC_NOT_FOUND` | 命令不存在 | exec |
| `EXEC_PERMISSION_DENIED` | 权限拒绝 | exec |
| `BROWSER_NOT_INSTALLED` | 浏览器未安装 | browser |
| `BROWSER_ELEMENT_NOT_FOUND` | 元素未找到 | browser |
| `BROWSER_NAVIGATION_FAILED` | 导航失败 | browser |
| `WEB_HTTP_ERROR` | HTTP 请求错误 | web_fetch/web_search |
| `WEB_TIMEOUT` | 网络超时 | web_fetch/web_search |
| `FILE_NOT_FOUND` | 文件不存在 | read/write |
| `FILE_PERMISSION_DENIED` | 文件权限错误 | read/write |
| `PDF_PARSE_ERROR` | PDF 解析失败 | pdf |
| `IMAGE_ANALYSIS_ERROR` | 图片分析失败 | image |

---

## 实施步骤

### Phase 1: 基础设施（第1周）

#### 1.1 创建错误定义模块

**文件**: `aiagent/errors.py`

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any
from datetime import datetime

class ErrorType(Enum):
    TEMPORARY = "temporary"
    PERMANENT = "permanent"
    RESOURCE = "resource"
    PERMISSION = "permission"
    DEPENDENCY = "dependency"
    UNKNOWN = "unknown"

class ErrorSeverity(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class AgentError:
    code: str
    type: ErrorType
    message: str
    tool_name: Optional[str] = None
    severity: Optional[ErrorSeverity] = None
    retryable: bool = False
    retry_after: Optional[int] = None
    details: Optional[dict] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.severity is None:
            self.severity = self._infer_severity()
    
    def _infer_severity(self) -> ErrorSeverity:
        if self.type == ErrorType.RESOURCE:
            return ErrorSeverity.CRITICAL
        if self.type == ErrorType.PERMANENT:
            return ErrorSeverity.ERROR
        if self.type == ErrorType.TEMPORARY:
            return ErrorSeverity.WARNING
        return ErrorSeverity.INFO
    
    def to_dict(self) -> dict:
        return {
            "status": "error",
            "error": {
                "code": self.code,
                "type": self.type.value,
                "severity": self.severity.value,
                "message": self.message,
                "tool": self.tool_name,
                "retryable": self.retryable,
                "retry_after": self.retry_after,
                "details": self.details,
                "timestamp": self.timestamp,
            }
        }
    
    def to_llm_text(self) -> str:
        """转换为 LLM 友好的文本"""
        text = f"Error [{self.code}]: {self.message}"
        if self.retryable:
            text += f"\n💡 This is a temporary error. You can retry"
            if self.retry_after:
                text += f" after {self.retry_after}s"
            text += "."
        return text
```

#### 1.2 创建错误解析器

**文件**: `aiagent/error_parser.py`

```python
"""从工具错误字符串解析为标准错误"""

import re
from typing import Optional, Callable
from .errors import AgentError, ErrorType, ErrorSeverity

class ErrorPattern:
    def __init__(self, regex: str, factory: Callable, priority: int = 0):
        self.regex = re.compile(regex, re.IGNORECASE)
        self.factory = factory
        self.priority = priority

class ErrorParser:
    """解析工具返回的错误字符串"""
    
    PATTERNS = [
        # exec 工具
        ErrorPattern(
            r"command timed out after (\d+)s",
            lambda m: AgentError(
                code="EXEC_TIMEOUT",
                type=ErrorType.TEMPORARY,
                message=f"Command timed out after {m.group(1)}s",
                retryable=True,
                retry_after=5,
                details={"timeout": int(m.group(1))}
            ),
            priority=100
        ),
        ErrorPattern(
            r"Error spawning process: (.+)",
            lambda m: AgentError(
                code="EXEC_SPAWN_FAILED",
                type=ErrorType.PERMANENT,
                message=f"Failed to spawn process: {m.group(1)}",
                retryable=False
            ),
            priority=90
        ),
        # browser 工具
        ErrorPattern(
            r"no element found for selector '(.+)'",
            lambda m: AgentError(
                code="BROWSER_ELEMENT_NOT_FOUND",
                type=ErrorType.PERMANENT,
                message=f"Element not found: {m.group(1)}",
                retryable=False,
                details={"selector": m.group(1)}
            ),
            priority=80
        ),
        ErrorPattern(
            r"Playwright browser .* is not installed",
            lambda m: AgentError(
                code="BROWSER_NOT_INSTALLED",
                type=ErrorType.DEPENDENCY,
                message="Browser not installed. Run: uv run playwright install chromium",
                retryable=False
            ),
            priority=80
        ),
        # web 工具
        ErrorPattern(
            r"HTTP Error (\d+): (.+)",
            lambda m: AgentError(
                code=f"HTTP_{m.group(1)}",
                type=ErrorType.TEMPORARY if m.group(1) in ["429", "502", "503", "504"] else ErrorType.PERMANENT,
                message=f"HTTP {m.group(1)}: {m.group(2)}",
                retryable=m.group(1) in ["429", "502", "503", "504"],
                retry_after=10 if m.group(1) == "429" else 5,
                details={"status_code": int(m.group(1)), "reason": m.group(2)}
            ),
            priority=70
        ),
        # 通用模式
        ErrorPattern(
            r"Error: ([^.]+)",
            lambda m: AgentError(
                code="UNKNOWN_ERROR",
                type=ErrorType.UNKNOWN,
                message=m.group(1).strip(),
                retryable=False
            ),
            priority=0
        ),
    ]
    
    @classmethod
    def parse(cls, content: str, tool_name: str) -> Optional[AgentError]:
        """解析错误字符串，返回标准化错误"""
        if not content or not isinstance(content, str):
            return None
        
        # 按优先级排序
        sorted_patterns = sorted(cls.PATTERNS, key=lambda p: -p.priority)
        
        for pattern in sorted_patterns:
            match = pattern.regex.search(content)
            if match:
                error = pattern.factory(match)
                error.tool_name = tool_name
                if tool_name and not error.details:
                    error.details = {}
                if error.details is not None:
                    error.details["original_content"] = content[:200]
                return error
        
        return None
    
    @classmethod
    def register_pattern(cls, regex: str, factory: Callable, priority: int = 0):
        """动态注册新的错误模式（用于插件扩展）"""
        cls.PATTERNS.append(ErrorPattern(regex, factory, priority))
```

#### 1.3 预留资源管理接口

**文件**: `aiagent/resource_bridge.py`

```python
"""资源管理系统对接接口（预留）

使用方法：
1. 资源管理系统实现 ResourceManagerBridge 接口
2. 初始化时调用 set_resource_manager()

示例：
    class MyResourceManager(ResourceManagerBridge):
        async def report_error(self, error: AgentError, context: dict):
            await self.send_to_control_center(error.to_dict())
    
    set_resource_manager(MyResourceManager())
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, List
import asyncio
from .errors import AgentError

class ResourceManagerBridge(ABC):
    """资源管理系统需要实现的接口"""
    
    @abstractmethod
    async def report_error(self, error: AgentError, context: dict):
        """
        报告错误给资源管理系统
        
        Args:
            error: 标准化错误对象
            context: 上下文信息，包含:
                - session_id: 会话ID
                - tool_call_id: 工具调用ID
                - tool_name: 工具名称
                - arguments: 工具参数
                - timestamp: 时间戳
                - agent_depth: Agent 嵌套深度
        """
        pass
    
    @abstractmethod
    async def request_resource(self, resource_type: str, amount: int) -> bool:
        """
        请求资源扩容
        
        Args:
            resource_type: 资源类型 (cpu, memory, disk, network)
            amount: 请求数量
        
        Returns:
            bool: 是否成功获取资源
        """
        pass
    
    @abstractmethod
    async def release_resource(self, resource_type: str, amount: int):
        """释放资源"""
        pass
    
    async def should_retry(self, error: AgentError, attempt: int) -> bool:
        """
        决定是否重试（可由资源管理策略覆盖）
        
        Args:
            error: 错误对象
            attempt: 当前重试次数（从0开始）
        
        Returns:
            bool: 是否继续重试
        """
        if not error.retryable:
            return False
        max_attempts = 3  # 默认最大重试3次
        return attempt < max_attempts

# 全局实例
_resource_manager: Optional[ResourceManagerBridge] = None
_error_handlers: List[Callable[[AgentError, dict], None]] = []

def set_resource_manager(manager: ResourceManagerBridge):
    """设置资源管理器（系统初始化时调用）"""
    global _resource_manager
    _resource_manager = manager
    
    # 注册为错误处理器
    register_error_handler(lambda err, ctx: _notify_resource_manager(err, ctx))
    
    print(f"[ResourceBridge] Resource manager registered: {type(manager).__name__}")

def get_resource_manager() -> Optional[ResourceManagerBridge]:
    """获取当前资源管理器"""
    return _resource_manager

def register_error_handler(handler: Callable[[AgentError, dict], None]):
    """注册错误处理器（可用于日志、监控等）"""
    _error_handlers.append(handler)

def unregister_error_handler(handler: Callable[[AgentError, dict], None]):
    """注销错误处理器"""
    if handler in _error_handlers:
        _error_handlers.remove(handler)

def emit_error(error: AgentError, context: dict):
    """
    广播错误事件给所有处理器
    工具层调用此函数通知错误
    """
    for handler in _error_handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                asyncio.create_task(handler(error, context))
            else:
                handler(error, context)
        except Exception as e:
            # 处理器错误不应影响主流程
            print(f"[ResourceBridge] Handler error: {e}")

def _notify_resource_manager(error: AgentError, context: dict):
    """内部：通知资源管理系统"""
    if _resource_manager:
        try:
            if asyncio.iscoroutinefunction(_resource_manager.report_error):
                asyncio.create_task(_resource_manager.report_error(error, context))
            else:
                _resource_manager.report_error(error, context)
        except Exception as e:
            print(f"[ResourceBridge] Failed to notify resource manager: {e}")
```

### Phase 2: 集成改造（第2周）

#### 2.1 修改工具注册表

**文件**: `aiagent/tools/__init__.py`

添加错误解析和广播：

```python
# 在文件顶部添加导入
from ..error_parser import ErrorParser
from ..resource_bridge import emit_error

# 修改 execute_tool 函数
async def execute_tool(tool_call_id: str, name: str, arguments: str) -> dict:
    """执行一次 tool call（增加错误标准化）"""
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
        
        # 可选：将结构化错误附加到返回中（供前端/资源管理使用）
        # LLM 仍然只看到文本，但其他系统可以读取 _structured_error
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": error.to_llm_text(),  # LLM 看到友好文本
            "_structured_error": error.to_dict(),  # 机器可读
        }

    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}
```

#### 2.2 Agent 层错误处理增强

**文件**: `aiagent/agent.py`

在 `_execute_tool` 中也添加错误标准化：

```python
async def _execute_tool(self, tool_call_id: str, name: str, arguments: str) -> dict:
    """执行工具调用（增加子 Agent 工具的错误处理）"""
    from .error_parser import ErrorParser
    from .resource_bridge import emit_error
    
    extra = self._extra_tools.get(name)
    if extra is not None:
        try:
            kwargs = json.loads(arguments)
        except json.JSONDecodeError as e:
            return {"role": "tool", "tool_call_id": tool_call_id,
                    "content": f"Error parsing args: {e}"}
        try:
            if inspect.iscoroutinefunction(extra.handler):
                content = await extra.handler(**kwargs)
            else:
                content = extra.handler(**kwargs)
        except Exception as e:
            content = f"Error: {e}"
        
        # 解析并广播错误
        error = ErrorParser.parse(content, name)
        if error:
            context = {
                "session_id": self.session_id,
                "tool_call_id": tool_call_id,
                "tool_name": name,
                "agent_depth": self.depth,
            }
            emit_error(error, context)
            return {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": error.to_llm_text(),
                "_structured_error": error.to_dict(),
            }
        
        return {"role": "tool", "tool_call_id": tool_call_id, "content": content}

    return await execute_tool(tool_call_id, name, arguments)
```

### Phase 3: 测试验证（第3周）

#### 3.1 单元测试

**文件**: `tests/test_error_handling.py`

```python
"""错误处理标准化测试"""

import pytest
from aiagent.errors import AgentError, ErrorType, ErrorSeverity
from aiagent.error_parser import ErrorParser

class TestErrorParser:
    """测试错误解析器"""
    
    def test_exec_timeout(self):
        content = "Error: command timed out after 30s"
        error = ErrorParser.parse(content, "exec")
        assert error is not None
        assert error.code == "EXEC_TIMEOUT"
        assert error.type == ErrorType.TEMPORARY
        assert error.retryable is True
        assert error.retry_after == 5
    
    def test_browser_not_installed(self):
        content = "Error: Playwright browser (Chromium) is not installed"
        error = ErrorParser.parse(content, "browser")
        assert error is not None
        assert error.code == "BROWSER_NOT_INSTALLED"
        assert error.type == ErrorType.DEPENDENCY
    
    def test_http_429(self):
        content = "HTTP Error 429: Too Many Requests"
        error = ErrorParser.parse(content, "web_fetch")
        assert error is not None
        assert error.code == "HTTP_429"
        assert error.type == ErrorType.TEMPORARY
        assert error.retry_after == 10
    
    def test_no_error(self):
        content = "Successfully executed command"
        error = ErrorParser.parse(content, "exec")
        assert error is None

class TestAgentError:
    """测试错误数据结构"""
    
    def test_to_dict(self):
        error = AgentError(
            code="TEST_ERROR",
            type=ErrorType.TEMPORARY,
            message="Test message",
            tool_name="test_tool"
        )
        d = error.to_dict()
        assert d["status"] == "error"
        assert d["error"]["code"] == "TEST_ERROR"
        assert "timestamp" in d["error"]
    
    def test_to_llm_text_with_retry(self):
        error = AgentError(
            code="TEMP_ERROR",
            type=ErrorType.TEMPORARY,
            message="Temporary failure",
            retryable=True,
            retry_after=10
        )
        text = error.to_llm_text()
        assert "TEMP_ERROR" in text
        assert "retry" in text.lower()
        assert "10s" in text
```

#### 3.2 集成测试

```python
# tests/test_resource_bridge.py

import pytest
from aiagent.resource_bridge import (
    set_resource_manager, 
    get_resource_manager,
    ResourceManagerBridge
)
from aiagent.errors import AgentError, ErrorType

class MockResourceManager(ResourceManagerBridge):
    def __init__(self):
        self.errors = []
    
    async def report_error(self, error: AgentError, context: dict):
        self.errors.append((error, context))
    
    async def request_resource(self, resource_type: str, amount: int) -> bool:
        return True
    
    async def release_resource(self, resource_type: str, amount: int):
        pass

def test_resource_manager_registration():
    mock = MockResourceManager()
    set_resource_manager(mock)
    assert get_resource_manager() is mock
```

---

## 对接指南

### 资源管理系统接入步骤

当资源管理系统开发完成后，按以下步骤对接：

#### 步骤 1: 实现接口

```python
# 在资源管理系统中
from aiagent.resource_bridge import ResourceManagerBridge
from aiagent.errors import AgentError

class MyResourceManager(ResourceManagerBridge):
    def __init__(self, control_center_url: str):
        self.url = control_center_url
        self.session = aiohttp.ClientSession()
    
    async def report_error(self, error: AgentError, context: dict):
        """报告错误到控制中心"""
        payload = {
            "error": error.to_dict(),
            "context": context,
            "resource_state": await self._get_current_resources(),
        }
        async with self.session.post(
            f"{self.url}/errors", 
            json=payload
        ) as resp:
            if resp.status != 200:
                logger.error(f"Failed to report error: {resp.status}")
    
    async def request_resource(self, resource_type: str, amount: int) -> bool:
        """请求资源扩容"""
        # 实现资源申请逻辑
        pass
    
    async def should_retry(self, error: AgentError, attempt: int) -> bool:
        """根据资源状况决定是否重试"""
        # 如果系统负载高，减少重试次数
        if await self._get_cpu_usage() > 80%:
            return attempt < 1  # 只重试1次
        return attempt < 3  # 默认3次
```

#### 步骤 2: 注册到 Agent 系统

```python
# 在系统启动时
from aiagent.resource_bridge import set_resource_manager

manager = MyResourceManager("http://control-center:8080")
set_resource_manager(manager)
```

#### 步骤 3: 消费错误事件

资源管理系统会实时收到所有错误，可以：

| 错误类型 | 资源管理动作 |
|----------|--------------|
| `RESOURCE` (内存不足) | 触发扩容或清理策略 |
| `TEMPORARY` (超时) | 自动重试或调整超时参数 |
| `DEPENDENCY` (未安装) | 触发自动安装流程 |
| `PERMISSION` | 发送告警通知管理员 |

---

## 这样做的好处

### 1. 对当前系统（短期收益）

| 收益 | 说明 |
|------|------|
| **统一错误格式** | 所有错误都有标准结构，便于日志分析 |
| **更好的 LLM 提示** | 告诉 LLM 哪些错误可重试，提高成功率 |
| **便于调试** | 结构化错误包含更多上下文信息 |

### 2. 对未来对接（长期收益）

| 收益 | 说明 |
|------|------|
| **零侵入集成** | 资源管理系统只需实现接口，不改 Agent 代码 |
| **向后兼容** | 现有字符串错误保留，LLM 不受影响 |
| **可扩展** | 新增工具只需添加错误模式，无需改架构 |
| **独立演化** | Agent 和资源管理可以独立升级 |

### 3. 架构优势

```
┌─────────────────────────────────────────────┐
│           适配器模式（Adapter）               │
├─────────────────────────────────────────────┤
│  旧系统 ──→ ErrorParser ──→ 标准化错误 ──→ 新系统 │
│   (工具)      (适配器)       (统一接口)    (资源管理)│
└─────────────────────────────────────────────┘
```

- **开闭原则**：对扩展开放（加错误模式），对修改封闭（不改工具）
- **单一职责**：错误标准化、事件广播、资源管理各司其职
- **依赖倒置**：Agent 依赖抽象接口，不依赖具体资源管理实现

---

## 分支管理

### 新建分支

```bash
# 创建功能分支
git checkout -b feature/error-standardization-20260326
```

### 分支命名规范

- **主分支**: `feature/error-standardization-YYYYMMDD`
- **热修复**: `fix/error-parser-bug-YYYYMMDD`
- **文档**: `docs/error-handling-guide`

### 提交计划

| 提交 | 内容 | 文件 |
|------|------|------|
| commit 1 | feat: add AgentError dataclass and ErrorType enum | `aiagent/errors.py` |
| commit 2 | feat: implement ErrorParser for tool error parsing | `aiagent/error_parser.py` |
| commit 3 | feat: add ResourceManagerBridge interface | `aiagent/resource_bridge.py` |
| commit 4 | feat: integrate error parsing into tool registry | `aiagent/tools/__init__.py` |
| commit 5 | feat: add error handling to Agent._execute_tool | `aiagent/agent.py` |
| commit 6 | test: add error handling unit tests | `tests/test_error_handling.py` |
| commit 7 | docs: add error handling documentation | `docs/ERROR_HANDLING.md` |

---

## 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 错误模式匹配不准确 | 中 | 中 | 保留原始内容在 details 中，便于调试 |
| 性能开销（正则匹配） | 低 | 低 | 只在出现 Error 时解析，正常路径无开销 |
| LLM 困惑于新的提示 | 低 | 中 | 保持 LLM 文本格式不变，仅增加重试提示 |
| 事件处理器阻塞主流程 | 低 | 高 | 所有处理器异步执行，错误被捕获 |

---

## 相关文档

- [错误码规范](./ERROR_CODES.md)（待创建）
- [资源管理对接指南](./RESOURCE_INTEGRATION.md)（待创建）
- [API 文档](./API.md)（待创建）

---

**创建日期**: 2026-03-26  
**作者**: AI Agent Team  
**状态**: 设计完成，待实施
