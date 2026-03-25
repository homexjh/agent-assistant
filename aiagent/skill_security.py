"""
Skill Security Checker - 轻量级技能安全检查

仅扫描危险代码模式，不做完整沙箱。
适用于 market 级技能的安全检查。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


# 危险代码模式定义
DANGEROUS_PATTERNS = {
    "rm_rf_root": r"rm\s+-rf\s+/+",
    "rm_rf_wildcard": r"rm\s+-rf\s+\*",
    "curl_pipe_sh": r"curl.*\|\s*(sh|bash|zsh)",
    "wget_pipe_sh": r"wget.*\|\s*(sh|bash|zsh)",
    "eval_exec": r"eval\s*\(",
    "exec_system": r"os\.system\s*\(",
    "subprocess_shell": r"subprocess\..*shell\s*=\s*True",
    "subprocess_call": r"subprocess\.call\s*\([^)]*shell\s*=",
    "chmod_suid": r"chmod\s+[0-7]*[0-7][0-7][0-7]",
    "sudo": r"sudo\s+",
    "dd_if": r"dd\s+if=",
    "mkfs": r"mkfs\.",
    "format_disk": r"format\s+/dev/",
}


@dataclass
class SecurityCheckResult:
    """安全检查结果"""
    passed: bool
    issues: list[str]
    scanned_files: int


def check_file_for_dangerous_patterns(
    file_path: Path, patterns: dict[str, str] | None = None
) -> list[str]:
    """
    检查单个文件中的危险代码模式。
    
    Args:
        file_path: 要检查的文件路径
        patterns: 自定义危险模式字典，默认使用 DANGEROUS_PATTERNS
        
    Returns:
        发现的危险问题列表
    """
    if patterns is None:
        patterns = DANGEROUS_PATTERNS
        
    issues = []
    
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [f"无法读取文件 {file_path}: {e}"]
    
    lines = content.split("\n")
    
    for pattern_name, pattern in patterns.items():
        for line_no, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                issues.append(
                    f"[{pattern_name}] {file_path}:{line_no}: {line.strip()[:80]}"
                )
    
    return issues


def check_skill(skill_path: Path) -> SecurityCheckResult:
    """
    检查技能目录的安全性。
    
    仅扫描 scripts/ 目录下的 .py 和 .sh 文件。
    
    Args:
        skill_path: 技能目录路径
        
    Returns:
        SecurityCheckResult 包含检查结果
    """
    skill_path = Path(skill_path)
    
    if not skill_path.exists():
        return SecurityCheckResult(
            passed=False, 
            issues=[f"技能路径不存在: {skill_path}"],
            scanned_files=0
        )
    
    all_issues = []
    scanned_files = 0
    
    # 只扫描 scripts/ 目录
    scripts_dir = skill_path / "scripts"
    
    if scripts_dir.exists() and scripts_dir.is_dir():
        for ext in ["*.py", "*.sh"]:
            for script_file in scripts_dir.glob(ext):
                if script_file.is_file():
                    scanned_files += 1
                    issues = check_file_for_dangerous_patterns(script_file)
                    all_issues.extend(issues)
    
    # 也检查 SKILL.md 本身（防止嵌入恶意命令）
    skill_md = skill_path / "SKILL.md"
    if skill_md.exists():
        scanned_files += 1
        # 对 SKILL.md 只检查最严重的模式
        critical_patterns = {
            k: v for k, v in DANGEROUS_PATTERNS.items() 
            if k in ["rm_rf_root", "curl_pipe_sh", "eval_exec"]
        }
        issues = check_file_for_dangerous_patterns(skill_md, critical_patterns)
        all_issues.extend(issues)
    
    return SecurityCheckResult(
        passed=len(all_issues) == 0,
        issues=all_issues,
        scanned_files=scanned_files
    )


def check_skills_directory(
    skills_dir: Path, 
    level: str = "market"
) -> dict[str, SecurityCheckResult]:
    """
    批量检查技能目录。
    
    Args:
        skills_dir: 技能根目录
        level: 要检查的级别 ("market" 会强制检查所有)
        
    Returns:
        技能名称到检查结果的映射
    """
    skills_dir = Path(skills_dir)
    results = {}
    
    if not skills_dir.exists():
        return results
    
    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir() and not skill_dir.name.startswith("."):
            result = check_skill(skill_dir)
            results[skill_dir.name] = result
    
    return results


if __name__ == "__main__":
    # 简单测试
    import sys
    
    if len(sys.argv) > 1:
        skill_path = Path(sys.argv[1])
        print(f"🔍 检查技能: {skill_path}")
        print("-" * 50)
        
        result = check_skill(skill_path)
        
        print(f"扫描文件数: {result.scanned_files}")
        print(f"检查结果: {'✅ 通过' if result.passed else '❌ 发现危险代码'}")
        
        if result.issues:
            print("\n发现的问题:")
            for issue in result.issues:
                print(f"  - {issue}")
    else:
        print("用法: python -m aiagent.skill_security <skill-path>")
