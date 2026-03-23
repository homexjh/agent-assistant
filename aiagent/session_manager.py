"""
session_manager.py - 会话管理器

负责：
- 按 session_id 累积消息
- 检测超时（5分钟无新消息）
- 生成摘要并写入 Daily Log
- 不清空消息，支持继续累积

Usage:
    session_mgr = SessionManager(data_dir)
    summary = session_mgr.add_message(session_id, "user", "hello")
    if summary:
        print(f"Generated summary: {summary}")
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class SessionManager:
    """
    会话管理器：负责消息累积和定时摘要生成
    
    核心功能：
    1. 按 session_id 累积消息
    2. 检测超时（5分钟无新消息）
    3. 生成摘要并写入 Daily Log
    4. 不清空消息，支持继续累积
    """
    
    TIMEOUT_SECONDS = 300  # 5分钟超时
    MIN_VALID_MESSAGES = 5  # 最少有效消息数
    MAX_MESSAGES_KEEP = 100  # 最多保留100条消息（防止文件过大）
    
    def __init__(self, data_dir: Path):
        """
        Args:
            data_dir: data/sessions/ 目录路径
        """
        self.sessions_dir = data_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str
    ) -> Optional[str]:
        """
        添加消息到会话，触发超时检测
        
        Args:
            session_id: 会话 ID
            role: 'user' 或 'assistant'
            content: 消息内容
            
        Returns:
            如果生成了新摘要，返回摘要内容；否则返回 None
        """
        # 1. 加载会话
        session = self._load_session(session_id)
        
        # 2. 添加消息
        now = datetime.now()
        message = {
            "role": role,
            "content": content,
            "timestamp": now.isoformat()
        }
        session["messages"].append(message)
        session["last_active"] = now.isoformat()
        
        # 3. 检查是否需要生成摘要
        summary = self._check_and_generate_summary(session, now)
        
        # 4. 清理旧消息（保留最近 MAX_MESSAGES_KEEP 条）
        if len(session["messages"]) > self.MAX_MESSAGES_KEEP:
            session["messages"] = session["messages"][-self.MAX_MESSAGES_KEEP:]
        
        # 5. 保存会话
        self._save_session(session_id, session)
        
        return summary
    
    def _check_and_generate_summary(
        self, 
        session: dict, 
        now: datetime
    ) -> Optional[str]:
        """
        检查超时条件并生成摘要
        
        Returns:
            生成的摘要内容，或 None
        """
        # 获取上次摘要时间
        last_summary_str = session.get("last_summary_at")
        if last_summary_str:
            last_summary = datetime.fromisoformat(last_summary_str)
        else:
            last_summary = datetime.min
        
        # 检查超时
        time_since_summary = (now - last_summary).total_seconds()
        if time_since_summary < self.TIMEOUT_SECONDS:
            return None  # 未超时，不生成
        
        # 统计有效消息
        valid_count = self._count_valid_messages(session["messages"])
        if valid_count < self.MIN_VALID_MESSAGES:
            return None  # 消息不足，不生成
        
        # 生成摘要
        summary = self._generate_summary(session["messages"])
        
        # 更新会话摘要记录
        if "summaries" not in session:
            session["summaries"] = []
        
        session["summaries"].append({
            "time": now.strftime("%H:%M"),
            "content": summary,
            "message_count": valid_count,
            "timestamp": now.isoformat()
        })
        session["last_summary_at"] = now.isoformat()
        
        # 写入 Daily Log
        self._write_to_daily_log(summary, now)
        
        return summary
    
    def _generate_summary(self, messages: list[dict]) -> str:
        """
        生成摘要内容
        
        策略：取最近一条用户消息作为摘要
        """
        # 取最近10条消息
        recent = messages[-10:]
        
        # 找最后一条用户消息
        for msg in reversed(recent):
            if msg.get("role") == "user":
                content = msg.get("content", "")[:50]
                if len(content) >= 3:
                    return f"用户询问: {content}..."
        
        # 如果没有用户消息，找助手消息
        for msg in reversed(recent):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")[:50]
                if len(content) >= 3:
                    return f"对话: {content}..."
        
        return "对话进行中"
    
    def _write_to_daily_log(self, summary: str, now: datetime):
        """写入 Daily Log"""
        try:
            from .daily_log import append_to_daily_log
            
            time_str = now.strftime("%H:%M")
            entry = f"[{time_str}] {summary}"
            
            result = append_to_daily_log(entry=entry, section="自动摘要")
            print(f"[daily-log] Summary written: {result}", flush=True)
        except Exception as e:
            print(f"[daily-log] Error writing to daily log: {e}", flush=True)
    
    def _count_valid_messages(self, messages: list[dict]) -> int:
        """统计有效消息数（user/assistant 且内容长度 >= 3）"""
        count = 0
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role in ["user", "assistant"] and len(content) >= 3:
                count += 1
        
        return count
    
    def _load_session(self, session_id: str) -> dict:
        """加载会话文件，不存在则创建"""
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text(encoding="utf-8"))
                # 确保新字段存在（兼容旧会话文件）
                if "last_summary_at" not in data:
                    data["last_summary_at"] = None
                if "summaries" not in data:
                    data["summaries"] = []
                if "last_active" not in data:
                    data["last_active"] = data.get("created_at", datetime.now().isoformat())
                return data
            except Exception as e:
                print(f"[session] Error loading session {session_id}: {e}", flush=True)
        
        # 创建新会话
        now = datetime.now()
        return {
            "id": session_id,
            "title": "",
            "created_at": now.isoformat(),
            "last_active": now.isoformat(),
            "last_summary_at": None,
            "messages": [],
            "summaries": []
        }
    
    def _save_session(self, session_id: str, session: dict):
        """保存会话到文件"""
        try:
            session_file = self.sessions_dir / f"{session_id}.json"
            session_file.write_text(
                json.dumps(session, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[session] Error saving session {session_id}: {e}", flush=True)
    
    def get_session_summary(self, session_id: str) -> list[dict]:
        """
        获取会话的所有摘要
        
        Returns:
            摘要列表
        """
        session = self._load_session(session_id)
        return session.get("summaries", [])
    
    def cleanup_old_sessions(self, max_age_days: int = 30):
        """
        清理过期会话文件
        
        Args:
            max_age_days: 保留天数，默认30天
        """
        cutoff = datetime.now() - timedelta(days=max_age_days)
        cleaned = 0
        
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                data = json.loads(session_file.read_text(encoding="utf-8"))
                last_active = datetime.fromisoformat(data.get("last_active", data.get("created_at", "1970-01-01")))
                if last_active < cutoff:
                    session_file.unlink()
                    cleaned += 1
            except:
                pass
        
        if cleaned > 0:
            print(f"[session] Cleaned up {cleaned} old sessions", flush=True)
