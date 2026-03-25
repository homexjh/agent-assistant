#!/usr/bin/env python3
"""
Test for research skill

测试内容：
1. skill 文件存在且格式正确
2. frontmatter 包含必需的字段
3. 内容包含 4 阶段研究法
4. Web UI 中 skill 列表正确显示
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from aiagent.skills import scan_skills, _parse_frontmatter


class TestResearchSkill(unittest.TestCase):
    """测试 research skill"""
    
    @classmethod
    def setUpClass(cls):
        """查找 research skill"""
        cls.skills_dir = Path(__file__).parent.parent / "skills"
        cls.research_skill_md = cls.skills_dir / "system" / "research" / "SKILL.md"
        
    def test_skill_file_exists(self):
        """测试 skill 文件存在"""
        self.assertTrue(self.research_skill_md.exists(), 
                       f"SKILL.md 不存在: {self.research_skill_md}")
        
    def test_frontmatter_has_required_fields(self):
        """测试 frontmatter 包含必需字段"""
        content = self.research_skill_md.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(content)
        
        # 检查必需字段
        self.assertIn("name", meta, "缺少 name 字段")
        self.assertIn("description", meta, "缺少 description 字段")
        
        # 检查字段值
        self.assertEqual(meta["name"], "research", "name 应该为 'research'")
        self.assertIn("研究", meta["description"], "description 应该包含'研究'")
        self.assertIn("web_search", meta["description"], 
                     "description 应该提到 web_search 工具")
        
    def test_content_has_four_phases(self):
        """测试内容包含 4 阶段研究法"""
        content = self.research_skill_md.read_text(encoding="utf-8")
        
        # 检查 4 个阶段标题
        phases = [
            "Phase 1",
            "Phase 2", 
            "Phase 3",
            "Phase 4",
            "广度探索",
            "深度挖掘",
            "多角度验证",
            "综合检查"
        ]
        
        for phase in phases:
            self.assertIn(phase, content, f"缺少阶段: {phase}")
            
    def test_content_has_search_tips(self):
        """测试包含搜索技巧"""
        content = self.research_skill_md.read_text(encoding="utf-8")
        
        # 检查关键元素
        self.assertIn("web_search", content, "应该提到 web_search")
        self.assertIn("web_fetch", content, "应该提到 web_fetch")
        self.assertIn("搜索", content, "应该提到搜索")
        
    def test_skill_scanned_correctly(self):
        """测试 skill 被正确扫描"""
        skills = scan_skills()
        
        # 查找 research skill
        research_skills = [s for s in skills if s.name == "research"]
        self.assertEqual(len(research_skills), 1, "应该只有一个 research skill")
        
        research = research_skills[0]
        self.assertEqual(research.category, "system", "应该在 system 类别")
        self.assertEqual(research.trust_level.value, "system", 
                        "信任级别应该是 system")
        
    def test_output_format_section(self):
        """测试包含输出格式章节"""
        content = self.research_skill_md.read_text(encoding="utf-8")
        
        # 检查输出格式
        self.assertIn("输出格式", content, "应该有输出格式章节")
        self.assertIn("来源汇总", content, "应该提到来源汇总")


class TestResearchSkillWebUI(unittest.TestCase):
    """测试 Web UI 集成"""
    
    def test_skill_in_system_prompt(self):
        """测试 skill 会出现在 system prompt 中"""
        from aiagent.skills import scan_skills, build_skills_summary
        
        skills = scan_skills()
        summary = build_skills_summary(skills)
        
        # 检查 research 在摘要中
        self.assertIn("research", summary.lower(), 
                     "system prompt 应该包含 research skill")
        
        # 检查路径正确
        self.assertIn("skills/system/research/SKILL.md", summary,
                     "应该显示正确的路径")
        
    def test_skill_categorized_correctly(self):
        """测试 skill 分类正确"""
        from aiagent.skills import scan_skills
        
        skills = scan_skills()
        research = [s for s in skills if s.name == "research"][0]
        
        # 验证分类
        self.assertEqual(research.category, "system")
        

class TestResearchWorkflow(unittest.TestCase):
    """测试研究流程（模拟使用）"""
    
    def test_research_workflow_structure(self):
        """测试研究流程结构完整性"""
        content = (Path(__file__).parent.parent / "skills" / "system" / 
                   "research" / "SKILL.md").read_text(encoding="utf-8")
        
        # 检查关键流程元素
        checkpoints = [
            "自检清单",
            "触发词",
            "Phase 1",
            "Phase 2",
            "Phase 3",
            "Phase 4",
        ]
        
        for checkpoint in checkpoints:
            self.assertIn(checkpoint, content, 
                         f"缺少关键流程元素: {checkpoint}")


def run_webui_test():
    """运行 Web UI 测试（需要服务器）"""
    import subprocess
    import time
    import urllib.request
    
    print("\n" + "="*60)
    print("Web UI 测试")
    print("="*60)
    
    # 启动服务器
    proc = subprocess.Popen(
        [sys.executable, "-m", "aiagent.serve"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).parent.parent
    )
    
    time.sleep(3)  # 等待启动
    
    try:
        # 测试首页
        req = urllib.request.Request("http://localhost:8765/")
        with urllib.request.urlopen(req, timeout=5) as resp:
            content = resp.read().decode("utf-8")
            assert "AIAgent" in content, "首页应该包含 AIAgent"
            print("✅ 首页加载正常")
        
        # 测试 sessions API
        req = urllib.request.Request("http://localhost:8765/api/sessions")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert "sessions" in data, "API 应该返回 sessions"
            print(f"✅ Sessions API 正常 ({len(data['sessions'])} 个会话)")
            
    except Exception as e:
        print(f"❌ Web UI 测试失败: {e}")
        return False
    finally:
        proc.terminate()
        proc.wait()
        
    return True


if __name__ == "__main__":
    # 运行单元测试
    print("="*60)
    print("Research Skill 单元测试")
    print("="*60)
    
    unittest.main(verbosity=2, exit=False)
    
    # 运行 Web UI 测试
    print("\n")
    run_webui_test()
