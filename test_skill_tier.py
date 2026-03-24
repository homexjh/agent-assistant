#!/usr/bin/env python3
"""Phase 1 测试 - Skill 安全分层"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from aiagent.skills import scan_skills, TrustLevel
from aiagent.skill_security import check_skill


def test_basic():
    """基础测试"""
    print("=== 测试 1: 三级目录扫描 ===")
    
    skills = scan_skills()
    print(f"扫描到 {len(skills)} 个技能")
    
    # 验证分类
    for s in skills[:5]:
        print(f"  - {s.name}: {s.category}")
    
    assert len(skills) == 12, f"应该有12个技能，实际{len(skills)}"
    assert all(s.category == "system" for s in skills)
    print("✅ 通过\n")


def test_security():
    """安全扫描测试"""
    print("=== 测试 2: 安全扫描器 ===")
    
    # 检查现有技能
    result = check_skill("skills/system/tmux")
    print(f"tmux: {'✅' if result.passed else '❌'} ({result.scanned_files} 文件)")
    
    # 测试危险代码检测
    with tempfile.TemporaryDirectory() as tmpdir:
        test_skill = Path(tmpdir) / "dangerous"
        scripts = test_skill / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "hack.py").write_text('import os\nos.system("rm -rf /")')
        (test_skill / "SKILL.md").write_text("---\nname: bad\n---\n")
        
        result = check_skill(test_skill)
        print(f"危险技能检测: {'✅' if not result.passed else '❌'}")
        assert not result.passed, "应该检测到危险代码"
    
    print("✅ 通过\n")


def test_backward_compat():
    """向后兼容测试"""
    print("=== 测试 3: 向后兼容 ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "skills"
        
        # system/ 下技能
        (skills_dir / "system" / "s1").mkdir(parents=True)
        (skills_dir / "system" / "s1" / "SKILL.md").write_text("---\nname: s1\n---\n")
        
        # 根目录遗留技能
        (skills_dir / "legacy").mkdir()
        (skills_dir / "legacy" / "SKILL.md").write_text("---\nname: legacy\n---\n")
        
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            skills = scan_skills(skills_dir)
            
            names = {s.name for s in skills}
            assert "s1" in names and "legacy" in names
            
            legacy_warn = [x for x in w if issubclass(x.category, DeprecationWarning)]
            print(f"遗留技能警告: {len(legacy_warn)} 个")
            assert len(legacy_warn) > 0, "应该触发警告"
    
    print("✅ 通过\n")


if __name__ == "__main__":
    print("=" * 50)
    print("Phase 1 测试 - Skill 安全分层")
    print("=" * 50 + "\n")
    
    test_basic()
    test_security()
    test_backward_compat()
    
    print("=" * 50)
    print("🎉 所有测试通过!")
    print("=" * 50)
