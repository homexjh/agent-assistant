"""
memory_manager.py - 结构化 MEMORY.md / USER.md 管理器

核心功能：
  - 解析 Markdown section 为嵌套字典
  - 支持点号路径访问（如 "facts.project.repo_path"）
  - 保存时保持 Markdown 格式
  - 自动更新 System.current_date
"""
from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class MemoryManager:
    """结构化 Markdown 记忆管理器"""
    
    def __init__(self, memory_path: Path | str):
        """
        初始化管理器
        
        Args:
            memory_path: MEMORY.md 或 USER.md 的路径
        """
        self.memory_path = Path(memory_path)
        self.data: dict[str, Any] = {}
        self._dirty = False
        self._load()
    
    def _load(self) -> None:
        """从文件加载并解析"""
        if not self.memory_path.exists():
            self.data = self._create_default()
            return
        
        try:
            content = self.memory_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Warning: Failed to read {self.memory_path}: {e}")
            self.data = self._create_default()
            return
        
        self.data = self._parse_markdown(content)
    
    def _create_default(self) -> dict[str, Any]:
        """创建默认结构"""
        return {
            "System": {
                "current_date": datetime.now().strftime("%Y-%m-%d"),
                "version": "1.0",
            }
        }
    
    def _parse_markdown(self, content: str) -> dict[str, Any]:
        """
        解析 Markdown 内容为嵌套字典
        
        支持：
        - ## Section
        - ### Subsection
        - - key: value
        """
        result: dict[str, Any] = {}
        current_section: str | None = None
        current_subsection: str | None = None
        
        for line in content.split("\n"):
            line = line.rstrip()
            
            # 检测 ## Section
            if line.startswith("## "):
                section_name = line[3:].strip()
                current_section = section_name
                current_subsection = None
                result[current_section] = {}
                continue
            
            # 检测 ### Subsection
            if line.startswith("### ") and current_section:
                subsection_name = line[4:].strip()
                current_subsection = subsection_name
                result[current_section][current_subsection] = {}
                continue
            
            # 解析 - key: value
            if line.startswith("- ") and current_section:
                item = line[2:].strip()
                if ": " in item:
                    key, value = item.split(": ", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if current_subsection:
                        # 子 section 内
                        result[current_section][current_subsection][key] = value
                    else:
                        # 直接在 section 内
                        result[current_section][key] = value
        
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取值，支持点号路径
        
        Args:
            key: 键路径，如 "facts.project.repo_path" 或 "system.current_date"
            default: 默认值
        
        Returns:
            值或默认值
        
        Examples:
            >>> mm.get("system.current_date")
            "2026-03-20"
            >>> mm.get("facts.project.repo_path")
            "/Users/emdoor/.../aiagent"
        """
        parts = key.split(".")
        value = self.data
        
        for part in parts:
            # 尝试小写匹配
            if isinstance(value, dict) and part in value:
                value = value[part]
            # 尝试首字母大写匹配（标题风格）
            elif isinstance(value, dict) and part.capitalize() in value:
                value = value[part.capitalize()]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: str) -> bool:
        """
        设置值，支持点号路径
        
        Args:
            key: 键路径，如 "facts.project.current_branch"
            value: 要设置的值
        
        Returns:
            是否成功
        """
        parts = key.split(".")
        target = self.data
        
        # 遍历到倒数第二个部分
        for i, part in enumerate(parts[:-1]):
            # 尝试小写和大写
            lookup_key = part if part in target else part.capitalize()
            
            if lookup_key not in target:
                # 创建新的 section
                target[lookup_key] = {}
            
            target = target[lookup_key]
            
            if not isinstance(target, dict):
                # 中间路径不是字典，无法继续
                return False
        
        # 设置最后一个键
        final_key = parts[-1]
        target[final_key] = value
        self._dirty = True
        return True
    
    def update_system_date(self) -> bool:
        """
        自动更新 System.current_date
        
        Returns:
            是否更新了
        """
        today = datetime.now().strftime("%Y-%m-%d")
        current = self.get("system.current_date")
        
        if current != today:
            self.set("system.current_date", today)
            self.set("system.last_updated", datetime.now().isoformat())
            return True
        return False
    
    def save(self) -> bool:
        """
        保存到文件
        
        Returns:
            是否成功
        """
        if not self._dirty:
            return True
        
        try:
            content = self._serialize_to_markdown()
            self.memory_path.parent.mkdir(parents=True, exist_ok=True)
            self.memory_path.write_text(content, encoding="utf-8")
            self._dirty = False
            return True
        except Exception as e:
            print(f"Error saving memory: {e}")
            return False
    
    def _serialize_to_markdown(self) -> str:
        """将数据序列化为 Markdown 格式"""
        lines = ["# Memory\n"]
        
        # 固定的 section 顺序
        section_order = ["System", "User Preferences", "Facts", "Daily Summaries"]
        
        # 先写入固定顺序的 section
        for section in section_order:
            if section in self.data:
                lines.extend(self._serialize_section(section, self.data[section]))
        
        # 再写入其他 section
        for section, content in self.data.items():
            if section not in section_order:
                lines.extend(self._serialize_section(section, content))
        
        return "\n".join(lines)
    
    def _serialize_section(self, name: str, content: dict) -> list[str]:
        """序刖化一个 section"""
        lines = [f"\n## {name}\n"]
        
        for key, value in content.items():
            if isinstance(value, dict):
                # 子 section
                lines.append(f"\n### {key}\n")
                for sub_key, sub_value in value.items():
                    lines.append(f"- {sub_key}: {sub_value}")
            else:
                # 简单键值对
                lines.append(f"- {key}: {value}")
        
        return lines
    
    def get_all(self) -> dict[str, Any]:
        """获取所有数据的副本"""
        import copy
        return copy.deepcopy(self.data)


def get_memory_manager(workspace_dir: Path | str | None = None) -> MemoryManager:
    """
    获取 MEMORY.md 管理器
    
    Args:
        workspace_dir: workspace 目录，默认使用默认 workspace
    
    Returns:
        MemoryManager 实例
    """
    if workspace_dir is None:
        from .workspace import _DEFAULT_WORKSPACE
        workspace_dir = _DEFAULT_WORKSPACE
    
    return MemoryManager(Path(workspace_dir) / "MEMORY.md")


def get_user_manager(workspace_dir: Path | str | None = None) -> MemoryManager:
    """
    获取 USER.md 管理器
    
    Args:
        workspace_dir: workspace 目录，默认使用默认 workspace
    
    Returns:
        MemoryManager 实例
    """
    if workspace_dir is None:
        from .workspace import _DEFAULT_WORKSPACE
        workspace_dir = _DEFAULT_WORKSPACE
    
    return MemoryManager(Path(workspace_dir) / "USER.md")
