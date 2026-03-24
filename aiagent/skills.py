"""
skills.py - skill 扫描与加载（支持三级目录结构）

## Skill 目录结构（新）
skills/
├── system/          # 系统级技能（完全信任）
│   └── my-skill/
│       └── SKILL.md
├── user/            # 用户级技能（基本信任）
│   └── my-skill/
│       └── SKILL.md
└── market/          # 市场级技能（需安全检查）
    └── my-skill/
        └── SKILL.md

## 向后兼容
skills/ 根目录下的技能视为 system 级（输出警告）

## 两阶段使用
1. 启动时：扫描所有 SKILL.md，只读 frontmatter → 生成摘要列表 → 写入 system prompt
2. 按需加载：LLM 判断需要某 skill → 调 read 工具读 SKILL.md 全文 → body 注入上下文
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal

_DEFAULT_SKILLS_DIR = Path(__file__).parent.parent / "skills"


class TrustLevel(Enum):
    """技能信任级别"""
    SYSTEM = "system"      # 系统级：完全信任
    USER = "user"          # 用户级：基本信任
    MARKET = "market"      # 市场级：需安全检查


@dataclass
class SkillMeta:
    name: str
    description: str
    path: Path             # SKILL.md 的完整路径
    trust_level: TrustLevel = TrustLevel.SYSTEM  # 信任级别
    category: str = ""     # 所属分类（system/user/market/legacy）


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


def scan_skills(
    skills_dir: str | Path | None = None,
    check_legacy: bool = True
) -> list[SkillMeta]:
    """
    扫描 skills/ 目录，返回所有有效 skill 的元数据列表。
    
    支持三级目录结构：
    - skills/system/  -> TrustLevel.SYSTEM
    - skills/user/    -> TrustLevel.USER
    - skills/market/  -> TrustLevel.MARKET
    
    向后兼容：根目录下的技能视为 system 级（输出警告）
    
    Args:
        skills_dir: 技能根目录，默认使用项目根目录下的 skills/
        check_legacy: 是否检查根目录下的遗留技能
        
    Returns:
        SkillMeta 列表
    """
    skills_path = Path(skills_dir) if skills_dir else _DEFAULT_SKILLS_DIR

    if not skills_path.exists():
        return []

    results: list[SkillMeta] = []
    processed_paths: set[Path] = set()  # 避免重复处理

    # 1. 扫描三级目录结构
    level_mapping = {
        "system": (TrustLevel.SYSTEM, "system"),
        "user": (TrustLevel.USER, "user"),
        "market": (TrustLevel.MARKET, "market"),
    }

    for level_dir_name, (trust_level, category) in level_mapping.items():
        level_path = skills_path / level_dir_name
        
        if not level_path.exists() or not level_path.is_dir():
            continue
            
        for skill_md in sorted(level_path.rglob("SKILL.md")):
            if skill_md in processed_paths:
                continue
                
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
                    trust_level=trust_level,
                    category=category,
                ))
                processed_paths.add(skill_md)
            except Exception:
                continue  # 读取失败跳过

    # 2. 向后兼容：扫描根目录下的遗留技能
    if check_legacy and skills_path.exists():
        for item in sorted(skills_path.iterdir()):
            # 跳过三级目录和隐藏目录
            if item.name in level_mapping or item.name.startswith("."):
                continue
                
            if not item.is_dir():
                continue
                
            skill_md = item / "SKILL.md"
            if not skill_md.exists() or skill_md in processed_paths:
                continue
                
            try:
                text = skill_md.read_text(encoding="utf-8")
                meta, _ = _parse_frontmatter(text)

                name = meta.get("name", "").strip()
                description = meta.get("description", "").strip()

                if not name:
                    continue

                # 遗留技能视为 system 级，但标记为 legacy
                import warnings
                warnings.warn(
                    f"Skill '{name}' found in root directory. "
                    f"Consider moving it to skills/system/ for better organization.",
                    DeprecationWarning,
                    stacklevel=2
                )

                results.append(SkillMeta(
                    name=name,
                    description=description or "(no description)",
                    path=skill_md,
                    trust_level=TrustLevel.SYSTEM,
                    category="legacy",
                ))
                processed_paths.add(skill_md)
            except Exception:
                continue

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
        if s.category and s.category != "system":
            lines.append(f"  - [{s.category}]")
    
    return "\n".join(lines)
