"""
全量验证：Phase 1~4 所有步骤
"""
from __future__ import annotations
import asyncio
from dotenv import load_dotenv
load_dotenv()

from aiagent.tools import get_tool_definitions, execute_tool
from aiagent.skills import scan_skills
from aiagent.workspace import build_system_prompt
from aiagent.agent import Agent

PASS = "✅ PASS"
FAIL = "❌ FAIL"


def check(label: str, cond: bool, detail: str = "") -> bool:
    status = PASS if cond else FAIL
    print(f"  {status}  {label}" + (f"  →  {detail}" if detail else ""))
    return cond


async def main() -> None:
    all_ok = True

    # ────────────────────────────────────────────────
    print("\n【Phase 1】工具注册与执行")
    tools = get_tool_definitions()
    names = {t["function"]["name"] for t in tools}
    all_ok &= check("exec 工具已注册", "exec" in names)
    all_ok &= check("read 工具已注册", "read" in names)
    all_ok &= check("write 工具已注册", "write" in names)

    r = await execute_tool("t1", "exec", '{"command":"echo hello"}')
    all_ok &= check("exec 执行正常", "hello" in r["content"], r["content"].strip())

    r = await execute_tool("t2", "write", '{"path":"/tmp/_aiagent_verify.txt","content":"ok"}')
    all_ok &= check("write 执行正常", "Successfully wrote" in r["content"], r["content"].strip())

    r = await execute_tool("t3", "read", '{"path":"/tmp/_aiagent_verify.txt"}')
    all_ok &= check("read 执行正常", r["content"].strip() == "ok", r["content"].strip())

    # ────────────────────────────────────────────────
    print("\n【Phase 2】workspace / system prompt 拼装")
    prompt = build_system_prompt()
    all_ok &= check("system prompt 非空", len(prompt) > 100, f"{len(prompt)} chars")
    for fname in ["Identity", "Soul", "Tools", "Memory"]:
        all_ok &= check(f"包含 {fname} 段", fname in prompt)

    # ────────────────────────────────────────────────
    print("\n【Phase 3】LLM tool-use 主循环")
    agent = Agent()
    all_ok &= check("Agent 初始化成功", agent.model == "kimi-k2-0711-preview", agent.model)
    reply = await agent.run("用 exec 工具执行 `echo phase3_ok`，只告诉我输出结果。")
    all_ok &= check("LLM 发起 tool_call 并返回回复", "phase3_ok" in reply, reply[:80])

    # ────────────────────────────────────────────────
    print("\n【Phase 4】skill 扫描加载")
    skills = scan_skills()
    skill_names = {s.name for s in skills}
    all_ok &= check(f"扫描到 {len(skills)} 个 skill", len(skills) >= 12, str(skill_names))
    all_ok &= check("system prompt 含 skill 摘要", "Available Skills" in prompt)
    for expected in ["weather", "github", "tmux"]:
        all_ok &= check(f"skill '{expected}' 存在", expected in skill_names)

    # Agent 能读取 SKILL.md
    r = await execute_tool("t4", "read", f'{{"path":"{list(s.path for s in skills if s.name=="weather")[0]}"}}')
    all_ok &= check("weather SKILL.md 可读", "wttr.in" in r["content"] or "weather" in r["content"].lower())

    # ────────────────────────────────────────────────
    print()
    if all_ok:
        print("🎉 所有 Phase 1~4 验证通过，可进行 Phase 5")
    else:
        print("⚠️  存在失败项，请检查后再继续")


asyncio.run(main())
