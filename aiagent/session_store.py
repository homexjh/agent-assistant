"""
session_store.py - 服务端会话存储管理

提供基于文件的会话持久化，替代 localStorage 存储方案。
存储结构：
  data/sessions/{session_id}.json  - 单个会话完整数据
  data/sessions/index.json         - 会话索引（列表视图用）
"""
from __future__ import annotations
import json
import os
import time
from pathlib import Path
from typing import Any

# 存储目录
DATA_DIR = Path(__file__).parent.parent / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
INDEX_FILE = SESSIONS_DIR / "index.json"

# 限制配置
MAX_SESSIONS = 100  # 最多保留 100 个会话
MAX_MESSAGES_PER_SESSION = 200  # 单个会话最多消息数


def _ensure_dir():
    """确保存储目录存在"""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _load_index() -> dict[str, Any]:
    """加载会话索引"""
    _ensure_dir()
    if not INDEX_FILE.exists():
        return {"sessions": {}, "version": 1}
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"sessions": {}, "version": 1}


def _save_index(index: dict[str, Any]):
    """保存会话索引"""
    _ensure_dir()
    tmp_file = INDEX_FILE.with_suffix(".tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    tmp_file.replace(INDEX_FILE)


def _get_session_file(session_id: str) -> Path:
    """获取会话文件路径"""
    return SESSIONS_DIR / f"{session_id}.json"


def _sanitize_messages(messages: list[dict]) -> list[dict]:
    """
    清理消息，移除不必要的字段，控制大小。
    只保留核心字段：role, content, tool_calls, tool_call_id
    """
    sanitized = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        clean_msg: dict[str, Any] = {"role": msg.get("role", "user")}
        
        # 处理 content
        content = msg.get("content")
        if content is not None:
            # 如果是多模态 content（数组），简化处理
            if isinstance(content, list):
                # 只保留文本部分，图片等大数据不存储
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                clean_msg["content"] = "\n".join(text_parts) if text_parts else "[图片/文件内容]"
            else:
                clean_msg["content"] = content
        
        # 保留 tool_calls（如果有）
        if "tool_calls" in msg:
            clean_msg["tool_calls"] = msg["tool_calls"]
        if "tool_call_id" in msg:
            clean_msg["tool_call_id"] = msg["tool_call_id"]
        
        # 保留 name（工具结果）
        if "name" in msg:
            clean_msg["name"] = msg["name"]
            
        sanitized.append(clean_msg)
    
    return sanitized


def list_sessions() -> list[dict[str, Any]]:
    """
    获取会话列表（按更新时间倒序）
    返回: [{id, title, updated_at, message_count, model}]
    """
    index = _load_index()
    sessions = []
    
    for session_id, meta in index.get("sessions", {}).items():
        sessions.append({
            "id": session_id,
            "title": meta.get("title", "新对话"),
            "updated_at": meta.get("updated_at", 0),
            "created_at": meta.get("created_at", 0),
            "message_count": meta.get("message_count", 0),
            "model": meta.get("model", ""),
        })
    
    # 按更新时间倒序
    sessions.sort(key=lambda x: x["updated_at"], reverse=True)
    return sessions


def get_session(session_id: str) -> dict[str, Any] | None:
    """
    获取完整会话数据
    返回: {id, title, messages, created_at, updated_at, model} 或 None
    """
    session_file = _get_session_file(session_id)
    if not session_file.exists():
        return None
    
    try:
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 验证基本结构
        if not isinstance(data, dict) or "messages" not in data:
            return None
            
        return {
            "id": session_id,
            "title": data.get("title", "新对话"),
            "messages": data.get("messages", []),
            "created_at": data.get("created_at", 0),
            "updated_at": data.get("updated_at", 0),
            "model": data.get("model", ""),
        }
    except Exception:
        return None


def create_session(title: str = "新对话", model: str = "") -> str:
    """
    创建新会话
    返回: session_id
    """
    _ensure_dir()
    
    session_id = f"sess_{int(time.time() * 1000)}"
    now = int(time.time() * 1000)
    
    session_data = {
        "id": session_id,
        "title": title,
        "messages": [],
        "created_at": now,
        "updated_at": now,
        "model": model,
        "version": 1,
    }
    
    # 保存会话文件
    session_file = _get_session_file(session_id)
    tmp_file = session_file.with_suffix(".tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)
    tmp_file.replace(session_file)
    
    # 更新索引
    index = _load_index()
    index["sessions"][session_id] = {
        "title": title,
        "created_at": now,
        "updated_at": now,
        "message_count": 0,
        "model": model,
    }
    _save_index(index)
    
    # 清理旧会话
    _cleanup_old_sessions()
    
    return session_id


def update_session(session_id: str, messages: list[dict], title: str | None = None) -> bool:
    """
    更新会话消息
    messages: 完整的消息列表（会覆盖）
    title: 可选，更新标题
    """
    session_file = _get_session_file(session_id)
    
    # 加载现有数据（如果存在）
    if session_file.exists():
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    else:
        data = {}
    
    now = int(time.time() * 1000)
    
    # 更新字段
    data["id"] = session_id
    data["updated_at"] = now
    if "created_at" not in data:
        data["created_at"] = now
    if "version" not in data:
        data["version"] = 1
    
    # 清理并保存消息
    sanitized = _sanitize_messages(messages)
    # 限制消息数量（保留最新的）
    if len(sanitized) > MAX_MESSAGES_PER_SESSION:
        sanitized = sanitized[-MAX_MESSAGES_PER_SESSION:]
    data["messages"] = sanitized
    
    # 更新标题
    if title:
        data["title"] = title
    elif "title" not in data:
        # 从第一条用户消息生成标题
        for msg in sanitized:
            if msg.get("role") == "user" and msg.get("content"):
                content = msg["content"]
                if isinstance(content, str):
                    data["title"] = content[:30] + "..." if len(content) > 30 else content
                    break
        else:
            data["title"] = "新对话"
    
    # 保存
    _ensure_dir()
    tmp_file = session_file.with_suffix(".tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_file.replace(session_file)
    
    # 更新索引
    index = _load_index()
    if session_id not in index["sessions"]:
        index["sessions"][session_id] = {}
    
    index["sessions"][session_id].update({
        "title": data["title"],
        "updated_at": now,
        "message_count": len(sanitized),
        "model": data.get("model", ""),
    })
    _save_index(index)
    
    return True


def append_messages(session_id: str, messages: list[dict]) -> bool:
    """
    追加消息到会话（用于增量保存）
    """
    session = get_session(session_id)
    if session is None:
        # 会话不存在，创建新的
        if not messages:
            return False
        create_session()
        return update_session(session_id, messages)
    
    existing = session.get("messages", [])
    combined = existing + messages
    return update_session(session_id, combined)


def delete_session(session_id: str) -> bool:
    """删除会话"""
    session_file = _get_session_file(session_id)
    
    # 删除文件
    try:
        if session_file.exists():
            session_file.unlink()
    except Exception:
        pass
    
    # 更新索引
    index = _load_index()
    if session_id in index.get("sessions", {}):
        del index["sessions"][session_id]
        _save_index(index)
        return True
    return False


def _cleanup_old_sessions():
    """清理最旧的会话，保持数量在限制内"""
    index = _load_index()
    sessions = index.get("sessions", {})
    
    if len(sessions) <= MAX_SESSIONS:
        return
    
    # 按更新时间排序，删除最旧的
    sorted_sessions = sorted(
        sessions.items(),
        key=lambda x: x[1].get("updated_at", 0)
    )
    
    to_delete = sorted_sessions[:len(sorted_sessions) - MAX_SESSIONS]
    
    for session_id, _ in to_delete:
        delete_session(session_id)


def clear_all_sessions() -> int:
    """清空所有会话，返回删除数量"""
    index = _load_index()
    session_ids = list(index.get("sessions", {}).keys())
    
    count = 0
    for session_id in session_ids:
        if delete_session(session_id):
            count += 1
    
    return count
