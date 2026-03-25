"""标准化错误定义，为后续资源管理对接预留"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any
from datetime import datetime


class ErrorType(Enum):
    """错误类型分类"""
    TEMPORARY = "temporary"      # 可重试：超时、网络抖动
    PERMANENT = "permanent"      # 不可重试：语法错误、文件不存在
    RESOURCE = "resource"        # 资源不足：内存、磁盘、配额
    PERMISSION = "permission"    # 权限问题
    DEPENDENCY = "dependency"    # 依赖缺失：playwright 未安装
    UNKNOWN = "unknown"          # 未知错误


class ErrorSeverity(Enum):
    """错误严重程度"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AgentError:
    """标准化错误数据结构
    
    用于资源管理系统和结构化日志记录。
    同时提供 to_llm_text() 方法保持 LLM 兼容性。
    """
    code: str                          # 错误码，如 "EXEC_TIMEOUT"
    type: ErrorType                    # 错误类型
    message: str                       # 人类可读信息
    tool_name: Optional[str] = None    # 哪个工具报的错
    severity: Optional[ErrorSeverity] = None  # 严重程度（自动推断）
    retryable: bool = False            # 是否可重试
    retry_after: Optional[int] = None  # 建议等待秒数
    details: Optional[dict] = None     # 详细上下文
    timestamp: Optional[str] = None    # ISO 格式时间戳
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.severity is None:
            self.severity = self._infer_severity()
    
    def _infer_severity(self) -> ErrorSeverity:
        """根据错误类型推断严重程度"""
        if self.type == ErrorType.RESOURCE:
            return ErrorSeverity.CRITICAL
        if self.type == ErrorType.PERMANENT:
            return ErrorSeverity.ERROR
        if self.type == ErrorType.TEMPORARY:
            return ErrorSeverity.WARNING
        if self.type == ErrorType.DEPENDENCY:
            return ErrorSeverity.WARNING
        if self.type == ErrorType.PERMISSION:
            return ErrorSeverity.ERROR
        return ErrorSeverity.INFO
    
    def to_dict(self) -> dict:
        """转换为字典格式（给资源管理系统用）"""
        return {
            "status": "error",
            "error": {
                "code": self.code,
                "type": self.type.value,
                "severity": self.severity.value if self.severity else None,
                "message": self.message,
                "tool": self.tool_name,
                "retryable": self.retryable,
                "retry_after": self.retry_after,
                "details": self.details,
                "timestamp": self.timestamp,
            }
        }
    
    def to_llm_text(self) -> str:
        """转换为 LLM 友好的文本（保持兼容）"""
        text = f"Error [{self.code}]: {self.message}"
        if self.retryable:
            text += "\n💡 This is a temporary error. You can retry"
            if self.retry_after:
                text += f" after {self.retry_after}s"
            text += "."
        return text
    
    def __str__(self) -> str:
        return self.to_llm_text()
