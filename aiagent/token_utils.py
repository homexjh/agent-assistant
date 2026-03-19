"""
token_utils.py - Token 计数工具

提供简单的 token 估算功能（无需 tiktoken 依赖）
适用于上下文使用量展示，精度足够
"""


def estimate_tokens(text: str | None) -> int:
    """
    估算文本的 token 数量。
    
    简化算法：
    - 中文字符：1.5 tokens/字（CJK 字符在 tiktoken 中通常占 1-2 tokens）
    - 英文单词：1.3 tokens/词
    - 数字/标点：0.5 tokens/个
    
    该估算对展示用途足够准确（误差 < 20%）
    """
    if not text:
        return 0
    
    if isinstance(text, list):
        # 多模态内容（如图片）
        total = 0
        for item in text:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    total += estimate_tokens(item.get("text", ""))
                elif item.get("type") == "image_url":
                    # 图片在 vision 模型中通常占约 1000 tokens
                    total += 1000
            else:
                total += estimate_tokens(str(item))
        return total
    
    text = str(text)
    
    import re
    
    # 统计不同类型的字符
    cjk_chars = len(re.findall(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', text))
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    numbers = len(re.findall(r'\d', text))
    other_chars = len(text) - cjk_chars - sum(len(w) for w in re.findall(r'[a-zA-Z]+', text)) - numbers
    
    # 估算 tokens
    tokens = (
        cjk_chars * 1.5 +      # CJK 字符
        english_words * 1.3 +   # 英文单词
        numbers * 0.5 +         # 数字
        other_chars * 0.5       # 其他字符（标点、空格等）
    )
    
    return int(tokens)


def count_message_tokens(message: dict) -> int:
    """
    计算单条消息的 token 数
    包含角色开销（约 4 tokens）
    """
    role_overhead = 4  # role 字段的开销
    
    content = message.get("content", "")
    content_tokens = estimate_tokens(content)
    
    # 如果有 tool_calls，也计算进去
    tool_calls_tokens = 0
    if "tool_calls" in message:
        for tc in message["tool_calls"]:
            if isinstance(tc, dict):
                tool_calls_tokens += estimate_tokens(tc.get("function", {}).get("name", ""))
                tool_calls_tokens += estimate_tokens(tc.get("function", {}).get("arguments", ""))
            else:
                tool_calls_tokens += estimate_tokens(str(tc))
    
    # 如果有 tool_call_id（工具返回），也计算
    tool_response_tokens = 0
    if message.get("role") == "tool":
        tool_response_tokens = estimate_tokens(message.get("content", ""))
    
    return role_overhead + content_tokens + tool_calls_tokens + tool_response_tokens


def count_messages_tokens(messages: list[dict]) -> int:
    """
    计算消息列表的总 token 数
    包含系统开销（约 3 tokens 每消息）
    """
    if not messages:
        return 0
    
    # 每消息额外开销（格式标记等）
    per_message_overhead = 3
    # 整体前缀开销
    prefix_overhead = 3
    
    total = prefix_overhead
    for msg in messages:
        total += count_message_tokens(msg) + per_message_overhead
    
    return int(total)


# 常用模型的上下文窗口（用于显示百分比）
MODEL_CONTEXT_LIMITS = {
    # OpenAI
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4": 8192,
    "gpt-4-turbo": 128000,
    "gpt-3.5-turbo": 16385,
    
    # Moonshot (Kimi)
    "kimi-k2": 200000,
    "kimi-k2-0711-preview": 200000,
    "kimi-k2.5": 200000,
    "moonshot-v1-8k": 8192,
    "moonshot-v1-32k": 32768,
    "moonshot-v1-128k": 128000,
    
    # Anthropic
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    
    # DeepSeek
    "deepseek-chat": 64000,
    "deepseek-coder": 64000,
    "deepseek-reasoner": 64000,
    
    # 默认值
    "default": 200000,
}


def get_context_limit(model: str | None) -> int:
    """获取模型的上下文窗口大小"""
    if not model:
        return MODEL_CONTEXT_LIMITS["default"]
    
    model_lower = model.lower()
    
    # 精确匹配
    if model_lower in MODEL_CONTEXT_LIMITS:
        return MODEL_CONTEXT_LIMITS[model_lower]
    
    # 部分匹配
    for key, limit in MODEL_CONTEXT_LIMITS.items():
        if key in model_lower:
            return limit
    
    return MODEL_CONTEXT_LIMITS["default"]


def format_token_count(count: int) -> str:
    """格式化 token 数为易读格式"""
    if count >= 10000:
        return f"{count / 1000:.1f}K"
    elif count >= 1000:
        return f"{count / 1000:.1f}K"
    else:
        return str(count)


def get_token_usage_info(messages: list[dict], model: str | None = None) -> dict:
    """
    获取完整的 token 使用信息
    
    Returns:
        {
            "current": 1234,        # 当前上下文 token 数
            "limit": 200000,        # 模型上下文限制
            "percentage": 0.6,      # 使用百分比
            "formatted": "1.2K",    # 格式化显示
            "status": "normal",     # normal / warning / danger
        }
    """
    current = count_messages_tokens(messages)
    limit = get_context_limit(model)
    percentage = (current / limit) * 100 if limit > 0 else 0
    
    # 状态判断
    if percentage >= 80:
        status = "danger"
    elif percentage >= 50:
        status = "warning"
    else:
        status = "normal"
    
    return {
        "current": current,
        "limit": limit,
        "percentage": round(percentage, 1),
        "formatted": format_token_count(current),
        "formatted_limit": format_token_count(limit),
        "status": status,
    }
