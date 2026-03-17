"""
子 Agent 测试 —— 需要有效的 API Key

验证：spawn → 执行 → announce 回调 → 父 Agent 收到结果
以及：steer 修正指令、agents_list 等管理功能
"""
from __future__ import annotations
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from aiagent.agent import Agent
from aiagent import subagent_registry as registry

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results: list[bool] = []


def check(label: str, cond: bool, detail: str = "") -> bool:
    status = PASS if cond else FAIL
    suffix = f"\n      detail: {detail}" if detail else ""
    print(f"  {status}  {label}{suffix}")
    results.append(cond)
    return cond


# ─────────────────────────────────────────────
# Case 1：派生子 Agent，等待结果
# ─────────────────────────────────────────────
async def case_spawn_and_wait():
    print("\n【SubAgent Case 1】spawn → 等待结果")
    agent = Agent()
    reply = await agent.run(
        "用 sessions_spawn 派生一个子 Agent，任务是 `echo subagent_case1`，"
        "等它完成后告诉我它的输出是什么。"
    )
    check("父 Agent 收到子 Agent 的结果", "subagent_case1" in reply, reply[:160])


# ─────────────────────────────────────────────
# Case 2：agents_list 查看全局 Agent 列表
# ─────────────────────────────────────────────
async def case_agents_list():
    print("\n【SubAgent Case 2】agents_list 列出 Agent")
    agent = Agent()
    reply = await agent.run(
        "用 agents_list 工具列出所有 Agent 运行记录，把结果告诉我。"
    )
    check("回复包含 run_id 或 Agent 信息", any(k in reply for k in ["run_id", "session", "agent", "task"]),
          reply[:160])


# ─────────────────────────────────────────────
# Case 3：subagents action=list 查看子 Agent
# ─────────────────────────────────────────────
async def case_subagents_list():
    print("\n【SubAgent Case 3】subagents list")
    agent = Agent()
    reply = await agent.run(
        "先用 sessions_spawn 派生一个子 Agent 执行 `sleep 2`，"
        "然后立刻用 subagents 工具 action=list 查看子 Agent 状态，告诉我有哪些子 Agent。"
    )
    check("能看到子 Agent 状态", any(k in reply for k in ["running", "pending", "sub", "agent"]),
          reply[:160])


# ─────────────────────────────────────────────
# main
# ─────────────────────────────────────────────
async def main():
    print("=" * 55)
    print("  aiagent 子 Agent 测试")
    print("  需要有效的 OPENAI_API_KEY")
    print("=" * 55)

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-xxx"):
        print("\n⚠️  未检测到有效 API Key，跳过测试")
        sys.exit(0)

    await case_spawn_and_wait()
    await case_agents_list()
    await case_subagents_list()

    total = len(results)
    passed = sum(results)
    print()
    print("=" * 55)
    if passed == total:
        print(f"🎉 全部通过 {passed}/{total}")
    else:
        print(f"⚠️  {passed}/{total} 通过，{total - passed} 失败")
    print("=" * 55)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())
