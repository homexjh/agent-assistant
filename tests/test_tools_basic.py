"""
基础工具单元测试 —— 不需要 LLM API Key，完全本地执行

覆盖工具：exec / read / write / edit / apply_patch / process / memory_search
"""
from __future__ import annotations
import asyncio
import os
import sys
import tempfile
import time

# 让测试可以在项目根目录直接运行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from aiagent.tools import execute_tool

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results: list[bool] = []


def check(label: str, cond: bool, detail: str = "") -> bool:
    status = PASS if cond else FAIL
    suffix = f"  →  {detail}" if detail else ""
    print(f"  {status}  {label}{suffix}")
    results.append(cond)
    return cond


# ─────────────────────────────────────────────
# 1. exec
# ─────────────────────────────────────────────
async def test_exec():
    print("\n【exec】")

    r = await execute_tool("t1", "exec", '{"command": "echo hello_exec"}')
    check("echo 输出正确", "hello_exec" in r["content"], r["content"].strip())

    r = await execute_tool("t2", "exec", '{"command": "ls /tmp", "timeout": 5}')
    check("ls /tmp 成功", r["content"].startswith("stdout:"), r["content"][:60])

    r = await execute_tool("t3", "exec", '{"command": "exit 1"}')
    check("非零 exit_code 被捕获", "exit_code: 1" in r["content"], r["content"].strip())

    r = await execute_tool("t4", "exec", '{"command": "sleep 10", "timeout": 1}')
    check("超时被捕获", "timed out" in r["content"].lower(), r["content"].strip())


# ─────────────────────────────────────────────
# 2. read / write
# ─────────────────────────────────────────────
async def test_read_write():
    print("\n【read / write】")

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        tmp = f.name

    try:
        r = await execute_tool("t5", "write", f'{{"path": "{tmp}", "content": "line1\\nline2\\nline3"}}')
        check("write 成功", "Successfully wrote" in r["content"], r["content"].strip())

        r = await execute_tool("t6", "read", f'{{"path": "{tmp}"}}')
        check("read 全文", r["content"].strip() == "line1\nline2\nline3", r["content"].strip())

        r = await execute_tool("t7", "read", f'{{"path": "{tmp}", "offset": 2, "limit": 1}}')
        check("read offset/limit", r["content"].strip() == "line2", r["content"].strip())

        r = await execute_tool("t8", "read", '{"path": "/nonexistent_xyz_abc.txt"}')
        check("read 不存在的文件返回 Error", r["content"].startswith("Error"), r["content"][:60])
    finally:
        os.unlink(tmp)


# ─────────────────────────────────────────────
# 3. edit
# ─────────────────────────────────────────────
async def test_edit():
    print("\n【edit】")

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
        f.write("foo bar baz\n")
        tmp = f.name

    try:
        import json
        args = json.dumps({"path": tmp, "old_str": "bar", "new_str": "REPLACED"})
        r = await execute_tool("t9", "edit", args)
        check("edit 成功", "Successfully edited" in r["content"], r["content"].strip())

        with open(tmp) as f:
            content = f.read()
        check("edit 内容正确", "REPLACED" in content and "bar" not in content, content.strip())

        # 不存在的 old_str
        args2 = json.dumps({"path": tmp, "old_str": "not_there", "new_str": "x"})
        r2 = await execute_tool("t10", "edit", args2)
        check("edit 找不到 old_str 返回 Error", "Error" in r2["content"], r2["content"][:60])
    finally:
        os.unlink(tmp)


# ─────────────────────────────────────────────
# 4. apply_patch
# ─────────────────────────────────────────────
async def test_apply_patch():
    print("\n【apply_patch】")

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
        f.write("line1\nline2\nline3\n")
        tmp = f.name

    try:
        patch = (
            "--- a/file\n"
            "+++ b/file\n"
            "@@ -2,1 +2,1 @@\n"
            "-line2\n"
            "+LINE_TWO\n"
        )
        import json
        args = json.dumps({"path": tmp, "patch": patch})
        r = await execute_tool("t11", "apply_patch", args)
        check("apply_patch 成功", "Successfully applied" in r["content"], r["content"].strip())

        with open(tmp) as f:
            content = f.read()
        check("patch 内容正确", "LINE_TWO" in content, content.strip())
    finally:
        os.unlink(tmp)


# ─────────────────────────────────────────────
# 5. process
# ─────────────────────────────────────────────
async def test_process():
    print("\n【process】")
    import json

    # 启动后台进程
    args = json.dumps({"action": "start", "name": "test_proc", "command": "sleep 5"})
    r = await execute_tool("t12", "process", args)
    check("process start 成功", "started" in r["content"].lower(), r["content"].strip())

    # list
    r = await execute_tool("t13", "process", '{"action": "list"}')
    check("process list 包含进程", "test_proc" in r["content"], r["content"].strip())

    # log
    r = await execute_tool("t14", "process", '{"action": "log", "name": "test_proc"}')
    check("process log 不报错", "Error" not in r["content"] or "no output" in r["content"].lower(),
          r["content"][:60])

    # kill
    r = await execute_tool("t15", "process", '{"action": "kill", "name": "test_proc"}')
    check("process kill 成功", "killed" in r["content"].lower() or "terminated" in r["content"].lower(),
          r["content"].strip())


# ─────────────────────────────────────────────
# 6. memory_search
# ─────────────────────────────────────────────
async def test_memory():
    print("\n【memory_search】")
    import json

    tag = f"test_{int(time.time())}"
    args = json.dumps({"action": "save", "content": f"单元测试写入的记忆 tag={tag}", "tag": tag})
    r = await execute_tool("t16", "memory_search", args)
    check("memory save 成功", "saved" in r["content"].lower(), r["content"].strip())

    args2 = json.dumps({"action": "search", "query": tag})
    r2 = await execute_tool("t17", "memory_search", args2)
    check("memory search 能找到", tag in r2["content"], r2["content"][:120])


# ─────────────────────────────────────────────
# main
# ─────────────────────────────────────────────
async def main():
    print("=" * 55)
    print("  aiagent 基础工具测试")
    print("=" * 55)

    await test_exec()
    await test_read_write()
    await test_edit()
    await test_apply_patch()
    await test_process()
    await test_memory()

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
