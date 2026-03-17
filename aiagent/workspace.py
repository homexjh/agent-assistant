"""
workspace.py - 读取 workspace/ 目录，拼装 system prompt

加载顺序（固定）：
  IDENTITY.md → SOUL.md → TOOLS.md → MEMORY.md
  + 其余 .md 文件（按文件名排序）
  + skills 摘要列表（末尾追加）
"""
from __future__ import annotations
from pathlib import Path
from .skills import scan_skills, build_skills_summary

# workspace 目录默认与包同级
_DEFAULT_WORKSPACE = Path(__file__).parent.parent / "workspace"

# 固定优先加载的文件（顺序敏感）
_PRIORITY_FILES = ["IDENTITY.md", "SOUL.md", "TOOLS.md", "MEMORY.md"]


def build_system_prompt(
    workspace_dir: str | Path | None = None,
    skills_dir: str | Path | None = None,
) -> str:
    """
    读取 workspace/ 下所有 .md 文件，拼接成 system prompt 字符串。
    优先文件按 _PRIORITY_FILES 顺序，其余按文件名排序追加。
    末尾追加 skills 摘要。
    """
    workspace = Path(workspace_dir) if workspace_dir else _DEFAULT_WORKSPACE

    if not workspace.exists():
        return "You are a helpful AI agent."

    sections: list[str] = []
    loaded: set[str] = set()

    # 1. 按优先顺序加载 workspace/*.md
    for filename in _PRIORITY_FILES:
        fp = workspace / filename
        if fp.exists():
            content = fp.read_text(encoding="utf-8").strip()
            if content:
                sections.append(content)
            loaded.add(filename)

    # 2. 剩余 .md 文件按字母顺序加载
    for fp in sorted(workspace.glob("*.md")):
        if fp.name not in loaded:
            content = fp.read_text(encoding="utf-8").strip()
            if content:
                sections.append(content)

    # 3. 追加 skills 摘要（末尾）
    skills = scan_skills(skills_dir)
    summary = build_skills_summary(skills)
    if summary:
        sections.append(summary)

    return "\n\n---\n\n".join(sections)
