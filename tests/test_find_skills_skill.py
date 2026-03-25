#!/usr/bin/env python3
"""
Test for find-skills skill

测试内容：
1. skill 文件存在且格式正确
2. frontmatter 包含必需的字段
3. 内容包含安装指导
4. 包含安全提示
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from aiagent.skills import scan_skills, _parse_frontmatter


class TestFindSkillsSkill(unittest.TestCase):
    """测试 find-skills skill"""
    
    @classmethod
    def setUpClass(cls):
        """查找 find-skills skill"""
        cls.skills_dir = Path(__file__).parent.parent / "skills"
        cls.skill_md = cls.skills_dir / "system" / "find-skills" / "SKILL.md"
        
    def test_skill_file_exists(self):
        """测试 skill 文件存在"""
        self.assertTrue(self.skill_md.exists(), 
                       f"SKILL.md 不存在: {self.skill_md}")
        
    def test_frontmatter_has_required_fields(self):
        """测试 frontmatter 包含必需字段"""
        content = self.skill_md.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(content)
        
        # 检查必需字段
        self.assertIn("name", meta, "缺少 name 字段")
        self.assertIn("description", meta, "缺少 description 字段")
        
        # 检查字段值
        self.assertEqual(meta["name"], "find-skills", "name 应该为 'find-skills'")
        self.assertIn("技能", meta["description"], "description 应该提到'技能'")
        
    def test_content_has_install_guide(self):
        """测试内容包含安装指导"""
        content = self.skill_md.read_text(encoding="utf-8")
        
        # 检查关键章节
        self.assertIn("安装", content, "应该有安装指导")
        self.assertIn("skills/market", content, "应该提到 market 目录")
        self.assertIn("skills/user", content, "应该提到 user 目录")
        
    def test_content_has_security_info(self):
        """测试内容包含安全信息"""
        content = self.skill_md.read_text(encoding="utf-8")
        
        # 检查安全相关内容
        self.assertIn("安全", content, "应该有安全提示")
        self.assertIn("skill_security", content, "应该提到安全检查工具")
        
    def test_content_has_directory_structure(self):
        """测试内容包含目录结构说明"""
        content = self.skill_md.read_text(encoding="utf-8")
        
        # 检查三级目录
        self.assertIn("system", content.lower(), "应该提到 system 级")
        self.assertIn("user", content.lower(), "应该提到 user 级")
        self.assertIn("market", content.lower(), "应该提到 market 级")
        
    def test_content_has_examples(self):
        """测试内容包含示例对话"""
        content = self.skill_md.read_text(encoding="utf-8")
        
        # 检查示例
        self.assertIn("示例", content, "应该有示例对话")
        
    def test_skill_scanned_correctly(self):
        """测试 skill 被正确扫描"""
        skills = scan_skills()
        
        # 查找 find-skills skill
        find_skills = [s for s in skills if s.name == "find-skills"]
        self.assertEqual(len(find_skills), 1, "应该只有一个 find-skills skill")
        
        skill = find_skills[0]
        self.assertEqual(skill.category, "system", "应该在 system 类别")
        

class TestFindSkillsIntegration(unittest.TestCase):
    """测试集成"""
    
    def test_skill_in_system_prompt(self):
        """测试 skill 会出现在 system prompt 中"""
        from aiagent.skills import scan_skills, build_skills_summary
        
        skills = scan_skills()
        summary = build_skills_summary(skills)
        
        # 检查 find-skills 在摘要中
        self.assertIn("find-skills", summary.lower(), 
                     "system prompt 应该包含 find-skills skill")
        
        # 检查路径正确
        self.assertIn("skills/system/find-skills/SKILL.md", summary,
                     "应该显示正确的路径")


if __name__ == "__main__":
    # 运行单元测试
    print("="*60)
    print("Find-Skills Skill 单元测试")
    print("="*60)
    
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "="*60)
    print("测试完成!")
    print("="*60)
