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

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Callable, List
import asyncio
from .errors import AgentError


class ResourceManagerBridge(ABC):
    """资源管理系统需要实现的接口
    
    资源管理系统通过实现此接口，可以：
    1. 接收 Agent 的错误报告
    2. 控制资源分配和释放
    3. 决定是否重试失败的操作
    """
    
    @abstractmethod
    async def report_error(self, error: AgentError, context: dict):
        """报告错误给资源管理系统
        
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
        """请求资源扩容
        
        Args:
            resource_type: 资源类型 (cpu, memory, disk, network)
            amount: 请求数量
        
        Returns:
            bool: 是否成功获取资源
        """
        pass
    
    @abstractmethod
    async def release_resource(self, resource_type: str, amount: int):
        """释放资源
        
        Args:
            resource_type: 资源类型
            amount: 释放数量
        """
        pass
    
    async def should_retry(self, error: AgentError, attempt: int) -> bool:
        """决定是否重试（可由资源管理策略覆盖）
        
        默认策略：
        - 可重试错误最多重试3次
        - 不可重试错误立即失败
        
        Args:
            error: 错误对象
            attempt: 当前重试次数（从0开始）
        
        Returns:
            bool: 是否继续重试
        """
        if not error.retryable:
            return False
        max_attempts = 3
        return attempt < max_attempts
    
    async def get_retry_delay(self, error: AgentError, attempt: int) -> int:
        """获取重试延迟（指数退避）
        
        Args:
            error: 错误对象
            attempt: 当前重试次数
            
        Returns:
            int: 延迟秒数
        """
        base_delay = error.retry_after or 5
        # 指数退避：5, 10, 20...
        return base_delay * (2 ** attempt)


# ========== 全局实例管理 ==========

_resource_manager: Optional[ResourceManagerBridge] = None
_error_handlers: List[Callable[[AgentError, dict], None]] = []


def set_resource_manager(manager: ResourceManagerBridge):
    """设置资源管理器（系统初始化时调用）
    
    Args:
        manager: 资源管理器实例
    """
    global _resource_manager
    _resource_manager = manager
    
    # 自动注册为错误处理器
    register_error_handler(lambda err, ctx: _notify_resource_manager(err, ctx))
    
    print(f"[ResourceBridge] Resource manager registered: {type(manager).__name__}")


def get_resource_manager() -> Optional[ResourceManagerBridge]:
    """获取当前资源管理器"""
    return _resource_manager


def has_resource_manager() -> bool:
    """检查是否已注册资源管理器"""
    return _resource_manager is not None


# ========== 错误处理器管理 ==========

def register_error_handler(handler: Callable[[AgentError, dict], None]):
    """注册错误处理器（可用于日志、监控等）
    
    Args:
        handler: 处理器函数，接收 (AgentError, context) 参数
    """
    _error_handlers.append(handler)


def unregister_error_handler(handler: Callable[[AgentError, dict], None]):
    """注销错误处理器"""
    if handler in _error_handlers:
        _error_handlers.remove(handler)


def list_error_handlers() -> List[str]:
    """列出所有已注册的错误处理器（用于调试）"""
    return [f"{h.__module__}.{h.__name__}" for h in _error_handlers]


# ========== 错误广播 ==========

def emit_error(error: AgentError, context: dict):
    """广播错误事件给所有处理器
    
    工具层调用此函数通知错误。所有处理器异步执行，
    单个处理器失败不影响其他处理器。
    
    Args:
        error: 标准化错误对象
        context: 上下文信息
    """
    for handler in _error_handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                # 异步处理器，创建后台任务
                asyncio.create_task(_run_async_handler(handler, error, context))
            else:
                # 同步处理器，直接调用
                handler(error, context)
        except Exception as e:
            # 处理器错误不应影响主流程
            print(f"[ResourceBridge] Handler error: {e}")


async def _run_async_handler(handler, error, context):
    """运行异步处理器并捕获异常"""
    try:
        await handler(error, context)
    except Exception as e:
        print(f"[ResourceBridge] Async handler error: {e}")


def _notify_resource_manager(error: AgentError, context: dict):
    """内部：通知资源管理系统
    
    如果已注册资源管理器，将错误异步发送给它。
    """
    if _resource_manager:
        try:
            coro = _resource_manager.report_error(error, context)
            if asyncio.iscoroutine(coro):
                asyncio.create_task(_run_async_handler(
                    lambda e, c: _resource_manager.report_error(e, c),
                    error, context
                ))
            # 如果是同步方法，直接调用
        except Exception as e:
            print(f"[ResourceBridge] Failed to notify resource manager: {e}")


# ========== 便捷函数 ==========

def get_error_summary() -> dict:
    """获取错误统计摘要（用于调试）
    
    Returns:
        dict: 包含处理器数量、资源管理器状态等
    """
    return {
        "error_handlers_count": len(_error_handlers),
        "has_resource_manager": _resource_manager is not None,
        "resource_manager_type": type(_resource_manager).__name__ if _resource_manager else None,
    }
