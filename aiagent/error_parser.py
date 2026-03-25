"""从工具错误字符串解析为标准错误"""

from __future__ import annotations
import re
from typing import Optional, Callable, List
from dataclasses import dataclass
from .errors import AgentError, ErrorType, ErrorSeverity


@dataclass
class ErrorPattern:
    """错误模式定义"""
    regex: str
    factory: Callable
    priority: int = 0


class ErrorParser:
    """解析工具返回的错误字符串
    
    将工具返回的字符串错误解析为结构化的 AgentError。
    支持动态注册新的错误模式。
    """
    
    # 内置错误模式列表
    PATTERNS: List[ErrorPattern] = [
        # ========== exec 工具 ==========
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
        ErrorPattern(
            r"\[Errno (\d+)\] (.+)",
            lambda m: AgentError(
                code=f"EXEC_ERRNO_{m.group(1)}",
                type=ErrorType.PERMANENT,
                message=m.group(2),
                retryable=False,
                details={"errno": int(m.group(1))}
            ),
            priority=85
        ),
        
        # ========== browser 工具 ==========
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
        ErrorPattern(
            r"Error executing tool \"browser\"",
            lambda m: AgentError(
                code="BROWSER_EXECUTION_ERROR",
                type=ErrorType.TEMPORARY,
                message="Browser operation failed",
                retryable=True,
                retry_after=3
            ),
            priority=75
        ),
        
        # ========== web 工具 ==========
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
        ErrorPattern(
            r"Error fetching (.+): (.+)",
            lambda m: AgentError(
                code="WEB_FETCH_ERROR",
                type=ErrorType.TEMPORARY,
                message=f"Failed to fetch {m.group(1)}: {m.group(2)}",
                retryable=True,
                retry_after=5,
                details={"url": m.group(1), "reason": m.group(2)}
            ),
            priority=65
        ),
        ErrorPattern(
            r"Error searching: (.+)",
            lambda m: AgentError(
                code="WEB_SEARCH_ERROR",
                type=ErrorType.TEMPORARY,
                message=f"Search failed: {m.group(1)}",
                retryable=True,
                retry_after=3
            ),
            priority=65
        ),
        ErrorPattern(
            r"No results found for: (.+)",
            lambda m: AgentError(
                code="WEB_NO_RESULTS",
                type=ErrorType.PERMANENT,
                message=f"No search results for: {m.group(1)}",
                retryable=False
            ),
            priority=60
        ),
        
        # ========== file 工具 ==========
        ErrorPattern(
            r"File not found: (.+)",
            lambda m: AgentError(
                code="FILE_NOT_FOUND",
                type=ErrorType.PERMANENT,
                message=f"File not found: {m.group(1)}",
                retryable=False,
                details={"path": m.group(1)}
            ),
            priority=70
        ),
        ErrorPattern(
            r"Permission denied: (.+)",
            lambda m: AgentError(
                code="FILE_PERMISSION_DENIED",
                type=ErrorType.PERMISSION,
                message=f"Permission denied: {m.group(1)}",
                retryable=False,
                details={"path": m.group(1)}
            ),
            priority=70
        ),
        ErrorPattern(
            r"Path traversal detected",
            lambda m: AgentError(
                code="FILE_PATH_TRAVERSAL",
                type=ErrorType.PERMANENT,
                message="Path traversal detected",
                retryable=False
            ),
            priority=75
        ),
        
        # ========== pdf 工具 ==========
        ErrorPattern(
            r"Error extracting PDF",
            lambda m: AgentError(
                code="PDF_PARSE_ERROR",
                type=ErrorType.PERMANENT,
                message="Failed to extract PDF content",
                retryable=False
            ),
            priority=60
        ),
        
        # ========== image 工具 ==========
        ErrorPattern(
            r"Error loading image",
            lambda m: AgentError(
                code="IMAGE_LOAD_ERROR",
                type=ErrorType.PERMANENT,
                message="Failed to load image",
                retryable=False
            ),
            priority=60
        ),
        ErrorPattern(
            r"Error analyzing image",
            lambda m: AgentError(
                code="IMAGE_ANALYSIS_ERROR",
                type=ErrorType.TEMPORARY,
                message="Failed to analyze image",
                retryable=True,
                retry_after=3
            ),
            priority=55
        ),
        
        # ========== 通用模式 ==========
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
        """解析错误字符串，返回标准化错误
        
        Args:
            content: 工具返回的内容
            tool_name: 工具名称
            
        Returns:
            AgentError: 如果解析成功，否则 None
        """
        if not content or not isinstance(content, str):
            return None
        
        # 检查是否包含错误关键词（扩展匹配范围）
        content_stripped = content.strip()
        error_indicators = [
            "error", "Error", "ERROR",
            "HTTP Error",
            "timed out", "timeout",
            "not found", "Not Found",
            "permission denied", "Permission denied",
            "no such file", "No such file",
            "no results",
            "[Errno",
            "failed", "Failed", "FAIL",
            "unable to", "Unable to",
            "cannot", "Cannot", "Can't",
        ]
        
        has_error = any(indicator in content for indicator in error_indicators)
        if not has_error:
            return None
        
        # 按优先级排序（高优先级先匹配）
        sorted_patterns = sorted(cls.PATTERNS, key=lambda p: -p.priority)
        
        for pattern in sorted_patterns:
            match = re.search(pattern.regex, content, re.IGNORECASE)
            if match:
                error = pattern.factory(match)
                error.tool_name = tool_name
                # 保存原始内容供调试
                if error.details is None:
                    error.details = {}
                error.details["original_content"] = content[:500]  # 限制长度
                return error
        
        return None
    
    @classmethod
    def register_pattern(cls, regex: str, factory: Callable, priority: int = 0):
        """动态注册新的错误模式（用于插件扩展）
        
        Args:
            regex: 正则表达式
            factory: 匹配后的工厂函数，接收 match 对象返回 AgentError
            priority: 优先级（越高越先匹配）
        """
        cls.PATTERNS.append(ErrorPattern(regex, factory, priority))
    
    @classmethod
    def list_patterns(cls) -> List[str]:
        """列出所有已注册的错误模式（用于调试）"""
        return [p.regex for p in cls.PATTERNS]
