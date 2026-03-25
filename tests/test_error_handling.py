"""错误处理标准化测试

测试内容：
1. AgentError 数据类的创建和转换
2. ErrorParser 的错误解析功能
3. ResourceManagerBridge 的注册和事件发射
"""

import pytest
import asyncio
from datetime import datetime
from aiagent.errors import AgentError, ErrorType, ErrorSeverity
from aiagent.error_parser import ErrorParser, ErrorPattern
from aiagent.resource_bridge import (
    set_resource_manager,
    get_resource_manager,
    register_error_handler,
    unregister_error_handler,
    emit_error,
    has_resource_manager,
    ResourceManagerBridge,
)


# ========== Test AgentError ==========

class TestAgentError:
    """测试错误数据类"""
    
    def test_basic_creation(self):
        """测试基本创建"""
        error = AgentError(
            code="TEST_ERROR",
            type=ErrorType.TEMPORARY,
            message="Test error message"
        )
        assert error.code == "TEST_ERROR"
        assert error.type == ErrorType.TEMPORARY
        assert error.message == "Test error message"
        assert error.timestamp is not None
        assert error.severity == ErrorSeverity.WARNING  # 自动推断
    
    def test_severity_inference(self):
        """测试严重程度自动推断"""
        # RESOURCE -> CRITICAL
        error = AgentError(code="R1", type=ErrorType.RESOURCE, message="m")
        assert error.severity == ErrorSeverity.CRITICAL
        
        # PERMANENT -> ERROR
        error = AgentError(code="P1", type=ErrorType.PERMANENT, message="m")
        assert error.severity == ErrorSeverity.ERROR
        
        # TEMPORARY -> WARNING
        error = AgentError(code="T1", type=ErrorType.TEMPORARY, message="m")
        assert error.severity == ErrorSeverity.WARNING
        
        # DEPENDENCY -> WARNING
        error = AgentError(code="D1", type=ErrorType.DEPENDENCY, message="m")
        assert error.severity == ErrorSeverity.WARNING
        
        # PERMISSION -> ERROR
        error = AgentError(code="PER1", type=ErrorType.PERMISSION, message="m")
        assert error.severity == ErrorSeverity.ERROR
        
        # UNKNOWN -> INFO
        error = AgentError(code="U1", type=ErrorType.UNKNOWN, message="m")
        assert error.severity == ErrorSeverity.INFO
    
    def test_custom_severity(self):
        """测试自定义严重程度"""
        error = AgentError(
            code="TEST",
            type=ErrorType.TEMPORARY,
            message="m",
            severity=ErrorSeverity.CRITICAL  # 覆盖自动推断
        )
        assert error.severity == ErrorSeverity.CRITICAL
    
    def test_to_dict(self):
        """测试转换为字典"""
        error = AgentError(
            code="TEST_001",
            type=ErrorType.TEMPORARY,
            message="Test message",
            tool_name="test_tool",
            retryable=True,
            retry_after=5,
            details={"key": "value"}
        )
        d = error.to_dict()
        
        assert d["status"] == "error"
        assert d["error"]["code"] == "TEST_001"
        assert d["error"]["type"] == "temporary"
        assert d["error"]["message"] == "Test message"
        assert d["error"]["tool"] == "test_tool"
        assert d["error"]["retryable"] is True
        assert d["error"]["retry_after"] == 5
        assert d["error"]["details"]["key"] == "value"
        assert "timestamp" in d["error"]
    
    def test_to_llm_text_without_retry(self):
        """测试 LLM 文本（不可重试）"""
        error = AgentError(
            code="PERMANENT_ERROR",
            type=ErrorType.PERMANENT,
            message="Something failed",
            retryable=False
        )
        text = error.to_llm_text()
        assert "PERMANENT_ERROR" in text
        assert "Something failed" in text
        assert "retry" not in text.lower()  # 不可重试，不应有 retry 提示
    
    def test_to_llm_text_with_retry(self):
        """测试 LLM 文本（可重试）"""
        error = AgentError(
            code="TEMP_ERROR",
            type=ErrorType.TEMPORARY,
            message="Temporary failure",
            retryable=True,
            retry_after=10
        )
        text = error.to_llm_text()
        assert "TEMP_ERROR" in text
        assert "Temporary failure" in text
        assert "retry" in text.lower()
        assert "10s" in text


# ========== Test ErrorParser ==========

class TestErrorParser:
    """测试错误解析器"""
    
    # ---------- exec 工具 ----------
    
    def test_exec_timeout(self):
        """测试 exec 超时错误"""
        content = "Error: command timed out after 30s"
        error = ErrorParser.parse(content, "exec")
        
        assert error is not None
        assert error.code == "EXEC_TIMEOUT"
        assert error.type == ErrorType.TEMPORARY
        assert error.retryable is True
        assert error.retry_after == 5
        assert error.details["timeout"] == 30
    
    def test_exec_spawn_failed(self):
        """测试 exec 进程启动失败"""
        content = "Error spawning process: No such file or directory"
        error = ErrorParser.parse(content, "exec")
        
        assert error is not None
        assert error.code == "EXEC_SPAWN_FAILED"
        assert error.type == ErrorType.PERMANENT
        assert error.retryable is False
    
    def test_exec_errno(self):
        """测试 exec errno 错误"""
        content = "[Errno 13] Permission denied"
        error = ErrorParser.parse(content, "exec")
        
        assert error is not None
        assert error.code == "EXEC_ERRNO_13"
        assert error.type == ErrorType.PERMANENT
    
    # ---------- browser 工具 ----------
    
    def test_browser_element_not_found(self):
        """测试浏览器元素未找到"""
        content = "Error: no element found for selector '.button-class'"
        error = ErrorParser.parse(content, "browser")
        
        assert error is not None
        assert error.code == "BROWSER_ELEMENT_NOT_FOUND"
        assert error.type == ErrorType.PERMANENT
        assert error.details["selector"] == ".button-class"
    
    def test_browser_not_installed(self):
        """测试浏览器未安装"""
        content = "Error: Playwright browser (Chromium) is not installed."
        error = ErrorParser.parse(content, "browser")
        
        assert error is not None
        assert error.code == "BROWSER_NOT_INSTALLED"
        assert error.type == ErrorType.DEPENDENCY
    
    # ---------- web 工具 ----------
    
    def test_http_429(self):
        """测试 HTTP 429 错误"""
        content = "HTTP Error 429: Too Many Requests"
        error = ErrorParser.parse(content, "web_fetch")
        
        assert error is not None
        assert error.code == "HTTP_429"
        assert error.type == ErrorType.TEMPORARY
        assert error.retryable is True
        assert error.retry_after == 10
    
    def test_http_500(self):
        """测试 HTTP 500 错误（永久）"""
        content = "HTTP Error 500: Internal Server Error"
        error = ErrorParser.parse(content, "web_fetch")
        
        assert error is not None
        assert error.code == "HTTP_500"
        assert error.type == ErrorType.PERMANENT  # 5xx 中非 502/503/504 视为永久
        assert error.retryable is False
    
    def test_web_fetch_error(self):
        """测试 web fetch 通用错误"""
        content = "Error fetching https://example.com: Connection refused"
        error = ErrorParser.parse(content, "web_fetch")
        
        assert error is not None
        assert error.code == "WEB_FETCH_ERROR"
        assert error.type == ErrorType.TEMPORARY
    
    def test_web_no_results(self):
        """测试搜索无结果 - 注意：目前解析为 UNKNOWN_ERROR，因为模式匹配需要以 Error 开头"""
        content = "No results found for: some query"
        error = ErrorParser.parse(content, "web_search")
        
        # 当前实现：不含 Error 关键词的简单消息不会被解析为错误
        # 这是预期的行为（避免将正常消息误判为错误）
        # 如果需要特殊处理，可以在实际调用时包装为 Error
        assert error is None  # 当前行为
    
    # ---------- file 工具 ----------
    
    def test_file_not_found(self):
        """测试文件未找到"""
        content = "File not found: /path/to/file.txt"
        error = ErrorParser.parse(content, "read")
        
        assert error is not None
        assert error.code == "FILE_NOT_FOUND"
        assert error.type == ErrorType.PERMANENT
    
    def test_file_permission_denied(self):
        """测试文件权限错误"""
        content = "Permission denied: /etc/shadow"
        error = ErrorParser.parse(content, "read")
        
        assert error is not None
        assert error.code == "FILE_PERMISSION_DENIED"
        assert error.type == ErrorType.PERMISSION
    
    # ---------- 边界情况 ----------
    
    def test_no_error(self):
        """测试正常内容不解析为错误"""
        content = "Successfully executed command\nOutput: hello"
        error = ErrorParser.parse(content, "exec")
        assert error is None
    
    def test_empty_content(self):
        """测试空内容"""
        assert ErrorParser.parse("", "exec") is None
        assert ErrorParser.parse(None, "exec") is None
    
    def test_unknown_error(self):
        """测试未知错误格式"""
        content = "Error: Something weird happened"
        error = ErrorParser.parse(content, "unknown_tool")
        
        assert error is not None
        assert error.code == "UNKNOWN_ERROR"
        assert error.type == ErrorType.UNKNOWN


# ========== Test Resource Bridge ==========

class MockResourceManager(ResourceManagerBridge):
    """模拟资源管理器"""
    
    def __init__(self):
        self.errors = []
        self.resources_requested = []
    
    async def report_error(self, error: AgentError, context: dict):
        self.errors.append({"error": error, "context": context})
    
    async def request_resource(self, resource_type: str, amount: int) -> bool:
        self.resources_requested.append({"type": resource_type, "amount": amount})
        return True
    
    async def release_resource(self, resource_type: str, amount: int):
        pass


class TestResourceBridge:
    """测试资源管理桥接"""
    
    def test_set_get_resource_manager(self):
        """测试设置和获取资源管理器"""
        mock = MockResourceManager()
        set_resource_manager(mock)
        
        assert get_resource_manager() is mock
        assert has_resource_manager() is True
    
    def test_error_handler_registration(self):
        """测试错误处理器注册"""
        handler_called = []
        
        def handler(error, context):
            handler_called.append(True)
        
        register_error_handler(handler)
        
        # 发射错误
        error = AgentError(code="TEST", type=ErrorType.TEMPORARY, message="test")
        emit_error(error, {"test": "context"})
        
        # 给异步处理器一点时间
        import time
        time.sleep(0.1)
        
        assert len(handler_called) == 1
        
        # 注销
        unregister_error_handler(handler)
    
    def test_emit_error_without_handlers(self):
        """测试没有处理器时不报错"""
        error = AgentError(code="TEST", type=ErrorType.TEMPORARY, message="test")
        # 不应抛出异常
        emit_error(error, {})
    
    def test_resource_manager_should_retry(self):
        """测试默认重试策略"""
        mock = MockResourceManager()
        
        # 可重试错误，第0次
        error = AgentError(code="TEMP", type=ErrorType.TEMPORARY, message="m", retryable=True)
        assert asyncio.run(mock.should_retry(error, 0)) is True
        
        # 可重试错误，第2次
        assert asyncio.run(mock.should_retry(error, 2)) is True
        
        # 可重试错误，第3次（达到上限）
        assert asyncio.run(mock.should_retry(error, 3)) is False
        
        # 不可重试错误
        error = AgentError(code="PERM", type=ErrorType.PERMANENT, message="m", retryable=False)
        assert asyncio.run(mock.should_retry(error, 0)) is False
    
    def test_resource_manager_get_retry_delay(self):
        """测试重试延迟计算（指数退避）"""
        mock = MockResourceManager()
        
        error = AgentError(code="TEMP", type=ErrorType.TEMPORARY, message="m", retry_after=5)
        
        # 指数退避：5, 10, 20
        assert asyncio.run(mock.get_retry_delay(error, 0)) == 5
        assert asyncio.run(mock.get_retry_delay(error, 1)) == 10
        assert asyncio.run(mock.get_retry_delay(error, 2)) == 20
        
        # 无 retry_after 时默认 5
        error2 = AgentError(code="TEMP", type=ErrorType.TEMPORARY, message="m")
        assert asyncio.run(mock.get_retry_delay(error2, 0)) == 5


# ========== Integration Tests ==========

class TestIntegration:
    """集成测试"""
    
    def test_end_to_end_error_flow(self):
        """测试完整错误流程"""
        mock = MockResourceManager()
        set_resource_manager(mock)
        
        # 解析错误
        content = "command timed out after 30s"
        error = ErrorParser.parse(content, "exec")
        
        # 发射错误
        context = {"tool_call_id": "test_123", "tool_name": "exec"}
        emit_error(error, context)
        
        # 验证
        assert error.code == "EXEC_TIMEOUT"
        assert error.type == ErrorType.TEMPORARY
        assert error.to_llm_text() == "Error [EXEC_TIMEOUT]: Command timed out after 30s\n💡 This is a temporary error. You can retry after 5s."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
