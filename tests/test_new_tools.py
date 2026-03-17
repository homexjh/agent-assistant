"""
新增工具测试：image / pdf / tts / browser / cron
不需要 LLM API Key（image/pdf 会调 LLM，但有 API Key 检测）
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
import time
import tempfile

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


def _has_api_key() -> bool:
    key = os.getenv("OPENAI_API_KEY", "")
    return bool(key) and not key.startswith("sk-xxx")


# ─────────────────────────────────────────────
# tts（macOS say，零依赖）
# ─────────────────────────────────────────────
async def test_tts():
    print("\n【tts】")
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as f:
        tmp = f.name

    try:
        args = json.dumps({"text": "hello", "provider": "say", "output": tmp, "play": False})
        r = await execute_tool("tts1", "tts", args)
        check("tts say 保存文件",
              "saved" in r["content"].lower() or "played" in r["content"].lower(),
              r["content"].strip())
        if "saved" in r["content"].lower():
            check("tts 输出文件存在", os.path.exists(tmp), tmp)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


# ─────────────────────────────────────────────
# browser（检查 playwright 是否安装）
# ─────────────────────────────────────────────
async def test_browser():
    print("\n【browser】")
    r = await execute_tool("br1", "browser", '{"action": "status"}')
    # 要么 playwright 未安装报错，要么返回 stopped/running
    check("browser status 不抛异常",
          "browser" in r["content"].lower() or "playwright" in r["content"].lower(),
          r["content"].strip())

    # 如果 playwright 可用，测试 open + snapshot + close
    if "playwright is not installed" in r["content"].lower():
        print("    ⚠️  playwright 未安装，跳过 open/snapshot 测试")
        print("    安装：uv add playwright && uv run playwright install chromium")
        return

    open_args = json.dumps({"action": "open", "url": "about:blank", "headless": True})
    r2 = await execute_tool("br2", "browser", open_args)
    check("browser open about:blank", "about:blank" in r2["content"] or "Opened" in r2["content"],
          r2["content"].strip())

    r3 = await execute_tool("br3", "browser", '{"action": "close"}')
    check("browser close", "closed" in r3["content"].lower(), r3["content"].strip())


# ─────────────────────────────────────────────
# cron
# ─────────────────────────────────────────────
async def test_cron():
    print("\n【cron】")

    r = await execute_tool("cr1", "cron", '{"action": "status"}')
    check("cron status", "running" in r["content"].lower(), r["content"].strip())

    # 添加一个 5 秒后触发的 exec 任务
    from datetime import datetime, timezone, timedelta
    at_time = (datetime.now(timezone.utc) + timedelta(seconds=5)).isoformat()
    add_args = json.dumps({
        "action": "add",
        "name": "test_cron_job",
        "schedule": {"kind": "at", "at": at_time},
        "payload": {"kind": "message", "text": "cron_test_ok"},
    })
    r2 = await execute_tool("cr2", "cron", add_args)
    check("cron add 成功", "added" in r2["content"].lower(), r2["content"].strip())

    r3 = await execute_tool("cr3", "cron", '{"action": "list"}')
    check("cron list 包含任务", "test_cron_job" in r3["content"], r3["content"].strip())

    # 提取 job_id
    job_id = None
    for word in r2["content"].split():
        if word.startswith("id="):
            job_id = word[3:]
            break

    if job_id:
        run_args = json.dumps({"action": "run", "job_id": job_id})
        r4 = await execute_tool("cr4", "cron", run_args)
        check("cron run 立即触发", "triggered" in r4["content"].lower(), r4["content"].strip())

        rm_args = json.dumps({"action": "remove", "job_id": job_id})
        r5 = await execute_tool("cr5", "cron", rm_args)
        check("cron remove 成功", "removed" in r5["content"].lower(), r5["content"].strip())
    else:
        check("cron job_id 解析", False, r2["content"])


# ─────────────────────────────────────────────
# image（需要 API Key，否则跳过）
# ─────────────────────────────────────────────
async def test_image():
    print("\n【image】")
    if not _has_api_key():
        print("    ⚠️  无 API Key，跳过 image LLM 测试")
        return

    # 生成一个简单的 1x1 红色像素 PNG（base64 内联）
    import base64
    # 最小 PNG：1x1 红色像素
    PNG_1X1_RED = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00'
        b'\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(PNG_1X1_RED)
        tmp_img = f.name

    try:
        args = json.dumps({
            "prompt": "What color is the dominant color in this image? Reply in one word.",
            "image": tmp_img,
        })
        r = await execute_tool("img1", "image", args)
        check("image 分析本地文件不报错",
              "Error calling LLM" not in r["content"] and "Error loading" not in r["content"],
              r["content"][:120])
    finally:
        os.unlink(tmp_img)

    # 无图片参数报错
    r2 = await execute_tool("img2", "image", '{"prompt": "test"}')
    check("image 无图片参数返回 Error", "Error" in r2["content"], r2["content"][:60])


# ─────────────────────────────────────────────
# pdf（检查 pdfminer）
# ─────────────────────────────────────────────
async def test_pdf():
    print("\n【pdf】")

    r = await execute_tool("pdf1", "pdf", '{"prompt": "test"}')
    check("pdf 无文件参数返回 Error", "Error" in r["content"], r["content"][:60])

    try:
        import pdfminer  # noqa
        print("    pdfminer.six 已安装")
        # 如果有 API Key，测试真实 PDF（公开文档）
        if _has_api_key():
            args = json.dumps({
                "pdf": "https://www.w3.org/WAI/WCAG21/wcag-2-1.pdf",
                "prompt": "What is the title of this document? Reply in one sentence.",
                "pages": "1",
            })
            r2 = await execute_tool("pdf2", "pdf", args)
            check("pdf 分析不报错", "Error" not in r2["content"][:30], r2["content"][:120])
        else:
            print("    ⚠️  无 API Key，跳过 LLM 分析测试")
    except ImportError:
        # pdfminer 未安装，用不存在的文件触发安装提示
        r3 = await execute_tool("pdf3", "pdf", '{"pdf": "/nonexistent.pdf", "prompt": "test"}')
        check("pdf 未安装 pdfminer 返回提示",
              "pdfminer" in r3["content"].lower() or "not installed" in r3["content"].lower(),
              r3["content"][:100])


# ─────────────────────────────────────────────
# 工具注册数量验证
# ─────────────────────────────────────────────
async def test_registration():
    print("\n【工具注册】")
    from aiagent.tools import get_tool_definitions
    tools = get_tool_definitions()
    names = {t["function"]["name"] for t in tools}
    check(f"内置工具总数 >= 14", len(tools) >= 14, f"共 {len(tools)} 个: {sorted(names)}")
    for expected in ["exec", "read", "write", "edit", "apply_patch",
                     "process", "web_fetch", "web_search", "memory_search",
                     "image", "pdf", "tts", "browser", "cron"]:
        check(f"工具 '{expected}' 已注册", expected in names)


# ─────────────────────────────────────────────
# main
# ─────────────────────────────────────────────
async def main():
    print("=" * 55)
    print("  aiagent 新增工具测试（image/pdf/tts/browser/cron）")
    print("=" * 55)

    await test_registration()
    await test_tts()
    await test_browser()
    await test_cron()
    await test_image()
    await test_pdf()

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
