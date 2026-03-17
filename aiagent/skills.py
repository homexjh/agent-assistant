"""
skills.py - skill 扫描与加载

## Skill 目录结构
skills/
└── my-skill/
    └── SKILL.md      ← frontmatter(name, description) + body(使用说明)

## 两阶段使用
1. 启动时：扫描所有 SKILL.md，只读 frontmatter → 生成摘要列表 → 写入 system prompt
2. 按需加载：LLM 判断需要某 skill → 调 read 工具读 SKILL.md 全文 → body 注入上下文
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_SKILLS_DIR = Path(__file__).parent.parent / "skills"


@dataclass
class SkillMeta:
    name: str
    description: str
    path: Path  # SKILL.md 的完整路径


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """
    解析 YAML frontmatter。
    返回 (meta_dict, body)。
    只处理简单 key: value（不依赖 PyYAML）。
    """
    if not text.startswith("---"):
        return {}, text

    end = text.find("---", 3)
    if end == -1:
        return {}, text

    fm_block = text[3:end].strip()
    body = text[end + 3:].strip()

    meta: dict[str, str] = {}
    for line in fm_block.splitlines():
        m = re.match(r"^(\w[\w-]*):\s*(.+)$", line)
        if m:
            key = m.group(1).strip()
            val = m.group(2).strip().strip('"').strip("'")
            meta[key] = val

    return meta, body


def scan_skills(skills_dir: str | Path | None = None) -> list[SkillMeta]:
    """
    扫描 skills/ 目录，返回所有有效 skill 的元数据列表。
    只读 frontmatter，不读 body（轻量）。
    """
    skills_path = Path(skills_dir) if skills_dir else _DEFAULT_SKILLS_DIR

    if not skills_path.exists():
        return []

    results: list[SkillMeta] = []

    for skill_md in sorted(skills_path.rglob("SKILL.md")):
        try:
            text = skill_md.read_text(encoding="utf-8")
            meta, _ = _parse_frontmatter(text)

            name = meta.get("name", "").strip()
            description = meta.get("description", "").strip()

            if not name:
                continue  # 没有 name，跳过

            results.append(SkillMeta(
                name=name,
                description=description or "(no description)",
                path=skill_md,
            ))
        except Exception:
            continue  # 读取失败跳过

    return results


def build_skills_summary(skills: list[SkillMeta]) -> str:
    """
    生成写入 system prompt 的 skill 摘要段落。
    """
    if not skills:
        return ""

    lines = ["# Available Skills\n"]
    lines.append("The following skills are available. To use a skill, read its SKILL.md for full instructions.\n")
    for s in skills:
        lines.append(f"- **{s.name}**: {s.description}")
        lines.append(f"  - path: `{s.path}`")
    return "\n".join(lines)
