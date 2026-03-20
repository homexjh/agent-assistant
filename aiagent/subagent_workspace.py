"""
subagent_workspace.py - 子 Agent Workspace 隔离管理

核心功能：
  - 创建隔离的 workspace 目录
  - 从父 Agent MEMORY.md 提取上下文注入
  - 管理子 Agent 文件的创建和清理
"""
from __future__ import annotations
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

# 子 Agent 基础目录
_SUBAGENT_BASE = Path(__file__).parent.parent / "workspace" / "subagents"

# 父 Agent 需要复制给子 Agent 的文件（基础配置）
_BASE_CONFIG_FILES = [
    "AGENTS.md",
    "TOOLS.md",
    "IDENTITY.md",
]

# 可选复制文件（如果不存在也不报错）
_OPTIONAL_CONFIG_FILES = [
    "SOUL.md",
]


def _parse_memory_for_injection(memory_path: Path) -> dict[str, Any]:
    """
    从父 Agent 的 MEMORY.md 提取关键信息用于上下文注入。
    
    返回结构化的上下文信息，包括：
    - user_preferences: 用户偏好
    - current_project: 当前项目
    - facts: 重要事实
    """
    context = {
        "user_preferences": {},
        "current_project": None,
        "facts": [],
        "system": {},
    }
    
    if not memory_path.exists():
        return context
    
    try:
        content = memory_path.read_text(encoding="utf-8")
    except Exception:
        return context
    
    # 简单的 markdown 解析，提取关键 section
    current_section = None
    
    for line in content.split("\n"):
        line = line.strip()
        
        # 检测 section 标题
        if line.startswith("## "):
            section_name = line[3:].strip().lower().replace(" ", "_")
            current_section = section_name
            continue
        
        # 检测 subsection (###)
        if line.startswith("### ") and current_section == "facts":
            subsection = line[4:].strip()
            if subsection.startswith("Project: "):
                context["current_project"] = subsection[9:].strip()
            continue
        
        # 解析列表项
        if line.startswith("- ") and current_section:
            item = line[2:].strip()
            if ": " in item:
                key, value = item.split(": ", 1)
                key = key.strip()
                value = value.strip()
                
                if current_section == "user_preferences":
                    context["user_preferences"][key] = value
                elif current_section == "system":
                    context["system"][key] = value
                elif current_section == "facts":
                    context["facts"].append({key: value})
    
    return context


def build_context_injection(
    memory_path: Path,
    fields: list[str] | None = None,
    max_chars: int = 500,
    workspace_dir: Path | str | None = None,
) -> str:
    """
    构建上下文注入文本，作为子 Agent task 的前缀。
    
    Args:
        memory_path: 父 Agent MEMORY.md 路径
        fields: 要注入的字段列表，默认 ["user_preferences", "current_project"]
        max_chars: 注入文本的最大长度
        workspace_dir: 子 Agent 的 workspace 路径，用于告知工作目录
    
    Returns:
        格式化的上下文文本，或空字符串（如果无内容）
    """
    if fields is None:
        fields = ["user_preferences", "current_project"]
    
    context = _parse_memory_for_injection(memory_path)
    
    parts = []
    
    # 工作目录提示（最重要）
    if workspace_dir:
        ws_path = str(workspace_dir)
        parts.append(f"""【重要！工作目录】
你的工作空间是：{ws_path}
所有文件必须保存到此目录下！
使用 exec 工具时请加上 cwd="{ws_path}"。""")
    
    # 用户偏好
    if "user_preferences" in fields and context["user_preferences"]:
        prefs = context["user_preferences"]
        pref_lines = [f"- {k}: {v}" for k, v in prefs.items()]
        parts.append("【用户偏好】\n" + "\n".join(pref_lines))
    
    # 当前项目
    if "current_project" in fields and context["current_project"]:
        parts.append(f"【当前项目】{context['current_project']}")
    
    # 系统信息（当前日期等）
    if "system" in fields and context["system"].get("current_date"):
        parts.append(f"【当前日期】{context['system']['current_date']}")
    
    if not parts:
        return ""
    
    injection = "【来自父 Agent 的上下文（仅本次任务有效）】\n" + "\n\n".join(parts)
    
    # 截断到最大长度
    if len(injection) > max_chars:
        injection = injection[:max_chars - 3] + "..."
    
    return injection + "\n\n---\n\n"


def create_subagent_workspace(
    label: str,
    parent_workspace: Path | str | None = None,
    cleanup_policy: str = "archive",
) -> Path:
    """
    创建子 Agent 的隔离 workspace。
    
    Args:
        label: 子 Agent 标签，用于命名
        parent_workspace: 父 Agent workspace 路径（用于复制基础配置）
        cleanup_policy: 清理策略（immediate/keep/archive）
    
    Returns:
        创建的 workspace 路径
    """
    # 确保基础目录存在
    _SUBAGENT_BASE.mkdir(parents=True, exist_ok=True)
    
    # 生成唯一目录名：label-timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_label = "".join(c for c in label if c.isalnum() or c in "_-").rstrip()
    if not safe_label:
        safe_label = "subagent"
    
    workspace_dir = _SUBAGENT_BASE / f"{safe_label}-{timestamp}"
    
    # 如果已存在（极少概率），添加序号
    counter = 1
    original_dir = workspace_dir
    while workspace_dir.exists():
        workspace_dir = Path(f"{original_dir}-{counter}")
        counter += 1
    
    workspace_dir.mkdir(parents=True)
    
    # 复制基础配置文件
    parent_ws = Path(parent_workspace) if parent_workspace else _SUBAGENT_BASE.parent
    
    # 1. 复制必需的配置文件
    for filename in _BASE_CONFIG_FILES:
        src = parent_ws / filename
        if src.exists():
            shutil.copy2(src, workspace_dir / filename)
    
    # 2. 复制可选的配置文件
    for filename in _OPTIONAL_CONFIG_FILES:
        src = parent_ws / filename
        if src.exists():
            shutil.copy2(src, workspace_dir / filename)
    
    # 3. 创建子 Agent 专用的 MEMORY.md（只包含系统信息，不包含父 Agent 的长期记忆）
    # 注意：这里创建一个空/基础的 MEMORY.md，防止 agent 报错
    sub_memory = workspace_dir / "MEMORY.md"
    sub_memory.write_text("""# Memory

## System
- note: This is a sub-agent workspace. Long-term memory is not persisted here.
- workspace_dir: {workspace}
- parent_workspace: {parent}
- created_at: {timestamp}

## Important Instructions
**You MUST save all files to your workspace directory: {workspace}**

When using tools:
- Use absolute paths: {workspace}/filename
- Or use cwd parameter: cwd="{workspace}"
- Do NOT create files in the parent workspace or other directories

## Task Context
Task-specific context will be provided in the conversation.
""".format(
        workspace=str(workspace_dir),
        parent=str(parent_ws),
        timestamp=datetime.now().isoformat(),
    ), encoding="utf-8")
    
    # 4. 创建元数据文件（用于追踪）
    meta_file = workspace_dir / ".subagent_meta.json"
    import json
    meta_file.write_text(json.dumps({
        "label": label,
        "parent_workspace": str(parent_ws),
        "cleanup_policy": cleanup_policy,
        "created_at": datetime.now().isoformat(),
    }, indent=2), encoding="utf-8")
    
    return workspace_dir


def cleanup_subagent_workspace(workspace_dir: Path | str, policy: str | None = None) -> bool:
    """
    清理子 Agent workspace。
    
    Args:
        workspace_dir: workspace 路径
        policy: 清理策略（覆盖元数据中的策略）
    
    Returns:
        是否成功清理
    """
    ws_path = Path(workspace_dir)
    if not ws_path.exists():
        return True
    
    # 读取元数据获取策略
    meta_file = ws_path / ".subagent_meta.json"
    if policy is None and meta_file.exists():
        import json
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            policy = meta.get("cleanup_policy", "archive")
        except Exception:
            policy = "archive"
    
    policy = policy or "archive"
    
    if policy == "immediate":
        # 立即删除
        shutil.rmtree(ws_path)
        return True
    
    elif policy == "keep":
        # 保留，不做任何操作
        return True
    
    elif policy == "archive":
        # 移动到 archive 目录
        archive_dir = _SUBAGENT_BASE / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        # 添加归档时间戳
        archive_name = f"{ws_path.name}-archived-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        archive_path = archive_dir / archive_name
        
        shutil.move(str(ws_path), str(archive_path))
        return True
    
    return False


def list_subagent_workspaces(parent_only: bool = False) -> list[dict]:
    """
    列出所有子 Agent workspace。
    
    Args:
        parent_only: 是否只列出直属 workspace/subagents/ 下的（不包括 archive）
    
    Returns:
        workspace 信息列表
    """
    if not _SUBAGENT_BASE.exists():
        return []
    
    workspaces = []
    
    for item in _SUBAGENT_BASE.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            if parent_only and item.name == "archive":
                continue
            
            meta_file = item / ".subagent_meta.json"
            meta = {}
            if meta_file.exists():
                import json
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            
            workspaces.append({
                "path": str(item),
                "name": item.name,
                "label": meta.get("label", item.name),
                "created_at": meta.get("created_at"),
                "cleanup_policy": meta.get("cleanup_policy", "archive"),
            })
    
    return workspaces
