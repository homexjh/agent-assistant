"""
Skill 系统测试 —— 不需要 LLM API Key

验证：skill 目录扫描 / frontmatter 解析 / system prompt 注入
"""
from __future__ import annotations
import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from aiagent.skills import scan_skills, SkillMeta
from aiagent.workspace import build_system_prompt

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results: list[bool] = []


def check(label: str, cond: bool, detail: str = "") -> bool:
    status = PASS if cond else FAIL
    suffix = f"  →  {detail}" if detail else ""
    print(f"  {status}  {label}{suffix}")
    results.append(cond)
    return cond


def test_skill_scan():
    print("\n【skill scan】")
    skills = scan_skills()
    check(f"扫描到 skill 数量 >= 10", len(skills) >= 10, f"共 {len(skills)} 个")

    names = {s.name for s in skills}
    for expected in ["weather", "github", "tmux", "summarize"]:
        check(f"skill '{expected}' 存在", expected in names)

    # 每个 skill 必须有 name / path / description
    for s in skills:
        ok = bool(s.name and s.path and s.description)
        check(f"skill '{s.name}' metadata 完整", ok,
              f"name={s.name!r} path={s.path!r} desc={bool(s.description)}")


def test_system_prompt_contains_skills():
    print("\n【system prompt 包含 skill 摘要】")
    prompt = build_system_prompt()
    check("prompt 非空", len(prompt) > 200, f"{len(prompt)} chars")
    check("包含 Available Skills 段落", "Available Skills" in prompt)
    check("包含 weather skill 摘要", "weather" in prompt.lower())
    check("包含 github skill 摘要", "github" in prompt.lower())


def test_custom_skill_dir():
    """在临时目录创建一个自定义 skill，验证能被扫描到。"""
    print("\n【自定义 skill 目录】")
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = os.path.join(tmpdir, "my_skill")
        os.makedirs(skill_dir)
        skill_md = os.path.join(skill_dir, "SKILL.md")
        with open(skill_md, "w") as f:
            f.write("---\nname: my_skill\ndescription: 我的测试 skill\n---\n\nSkill body.\n")

        skills = scan_skills(skills_dir=tmpdir)
        names = {s.name for s in skills}
        check("自定义 skill 被扫描到", "my_skill" in names, str(names))

        s = next((s for s in skills if s.name == "my_skill"), None)
        check("description 正确", s is not None and "测试" in s.description,
              s.description if s else "not found")


def main():
    print("=" * 55)
    print("  aiagent Skill 系统测试")
    print("=" * 55)

    test_skill_scan()
    test_system_prompt_contains_skills()
    test_custom_skill_dir()

    total = len(results)
    passed = sum(results)
    print()
    print("=" * 55)
    if passed == total:
        print(f"🎉 全部通过 {passed}/{total}")
    else:
        print(f"⚠️  {passed}/{total} 通过，{total - passed} 失败")
    print("=" * 55)
    import sys
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
