"""
LLM 端到端测试 —— 需要有效的 API Key

每个 case 都是真实用户 query 驱动，验证 Agent 能正确完成任务。
"""
from __future__ import annotations
import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from aiagent.agent import Agent

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
# Case 1：执行 shell 命令，返回结果
# ─────────────────────────────────────────────
async def case_exec_and_reply():
    print("\n【Case 1】exec + 回复")
    agent = Agent()
    reply = await agent.run("用 exec 工具执行 `echo e2e_case1`，然后告诉我输出是什么。")
    check("回复包含 e2e_case1", "e2e_case1" in reply, reply[:120])


# ─────────────────────────────────────────────
# Case 2：写文件 → 读文件 → 校验内容
# ─────────────────────────────────────────────
async def case_write_and_read():
    print("\n【Case 2】write → read → 校验")
    agent = Agent()
    tmp = "/tmp/_aiagent_e2e_case2.txt"
    reply = await agent.run(
        f"用 write 工具把字符串 'hello_e2e' 写到 {tmp}，"
        f"再用 read 工具读出来，告诉我文件内容是什么。"
    )
    check("回复提到 hello_e2e", "hello_e2e" in reply, reply[:120])


# ─────────────────────────────────────────────
# Case 3：多步任务 — 创建 Python 文件并运行
# ─────────────────────────────────────────────
async def case_create_and_run_python():
    print("\n【Case 3】创建 Python 文件并执行")
    agent = Agent()
    tmp = "/tmp/_aiagent_e2e_case3.py"
    reply = await agent.run(
        f"用 write 工具在 {tmp} 写一个 Python 脚本，内容是 `print('case3_ok')`，"
        f"再用 exec 工具用 python3 运行它，告诉我运行结果。"
    )
    check("回复包含 case3_ok", "case3_ok" in reply, reply[:120])


# ─────────────────────────────────────────────
# Case 4：edit 工具 — 修改文件中的某行
# ─────────────────────────────────────────────
async def case_edit_file():
    print("\n【Case 4】edit 工具修改文件")
    # 预先准备文件
    tmp = "/tmp/_aiagent_e2e_case4.txt"
    with open(tmp, "w") as f:
        f.write("version = 1\n")

    agent = Agent()
    reply = await agent.run(
        f"用 edit 工具把 {tmp} 里的 'version = 1' 改成 'version = 2'，"
        f"然后用 read 读出文件内容告诉我。"
    )
    check("回复提到 version = 2", "version = 2" in reply or "version=2" in reply, reply[:120])


# ─────────────────────────────────────────────
# Case 5：多轮对话 — 上下文保持
# ─────────────────────────────────────────────
async def case_multi_turn():
    print("\n【Case 5】多轮对话上下文保持")
    agent = Agent()
    history = []

    # 第一轮
    r1 = await agent.run("我的幸运数字是 42，记住它。", history=history)
    history += [
        {"role": "user", "content": "我的幸运数字是 42，记住它。"},
        {"role": "assistant", "content": r1},
    ]

    # 第二轮
    r2 = await agent.run("我的幸运数字是多少？", history=history)
    check("第二轮能回忆起幸运数字 42", "42" in r2, r2[:120])


# ─────────────────────────────────────────────
# main
# ─────────────────────────────────────────────
async def main():
    print("=" * 55)
    print("  aiagent 端到端（LLM）测试")
    print("  需要有效的 OPENAI_API_KEY")
    print("=" * 55)

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-xxx"):
        print("\n⚠️  未检测到有效 API Key，跳过 LLM 测试")
        print("   请在 .env 中设置 OPENAI_API_KEY 后重试")
        sys.exit(0)

    await case_exec_and_reply()
    await case_write_and_read()
    await case_create_and_run_python()
    await case_edit_file()
    await case_multi_turn()

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
