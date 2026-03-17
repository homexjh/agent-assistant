"""
一键运行所有测试的入口脚本

用法：
    uv run python tests/run_all.py           # 运行全部
    uv run python tests/run_all.py --no-llm  # 跳过需要 LLM 的测试
"""
from __future__ import annotations
import argparse
import asyncio
import importlib
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def _has_api_key() -> bool:
    key = os.getenv("OPENAI_API_KEY", "")
    return bool(key) and not key.startswith("sk-xxx")


async def run_async_test(module_name: str) -> bool:
    """导入并运行一个 async main() 测试模块，返回是否成功。"""
    mod = importlib.import_module(module_name)
    try:
        await mod.main()
        return True
    except SystemExit as e:
        return e.code == 0
    except Exception as e:
        print(f"  ❌ 运行 {module_name} 时发生异常: {e}")
        return False


def run_sync_test(module_name: str) -> bool:
    """导入并运行一个 sync main() 测试模块，返回是否成功。"""
    mod = importlib.import_module(module_name)
    try:
        mod.main()
        return True
    except SystemExit as e:
        return e.code == 0
    except Exception as e:
        print(f"  ❌ 运行 {module_name} 时发生异常: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="aiagent 测试套件")
    parser.add_argument("--no-llm", action="store_true", help="跳过需要 LLM API 的测试")
    args = parser.parse_args()

    has_key = _has_api_key()
    skip_llm = args.no_llm or not has_key

    print("=" * 60)
    print("  aiagent 全量测试套件")
    print("=" * 60)
    if skip_llm:
        reason = "--no-llm 指定" if args.no_llm else "未检测到有效 API Key"
        print(f"  ⚠️  跳过 LLM 相关测试（{reason}）")
    print()

    suite: list[tuple[str, str, bool]] = [
        # (显示名, 模块名, 是否需要 LLM)
        ("基础工具测试",          "tests.test_tools_basic",  False),
        ("Skill 系统测试",        "tests.test_skills",       False),
        ("新增工具测试",          "tests.test_new_tools",    False),
        ("端到端 LLM 测试",       "tests.test_e2e_llm",      True),
        ("子 Agent 测试",         "tests.test_subagent",     True),
    ]

    suite_results: list[tuple[str, bool, str]] = []  # (name, passed, note)
    t_start = time.time()

    for display_name, module_name, needs_llm in suite:
        if needs_llm and skip_llm:
            suite_results.append((display_name, True, "（已跳过）"))
            continue

        print(f"▶ {display_name} ...")
        t0 = time.time()
        try:
            mod = importlib.import_module(module_name)
            if asyncio.iscoroutinefunction(getattr(mod, "main", None)):
                passed = await run_async_test(module_name)
            else:
                passed = run_sync_test(module_name)
        except Exception as e:
            print(f"  ❌ 导入/运行失败: {e}")
            passed = False

        elapsed = time.time() - t0
        suite_results.append((display_name, passed, f"{elapsed:.1f}s"))

    total_time = time.time() - t_start
    passed_count = sum(1 for _, ok, _ in suite_results if ok)
    total_count = len(suite_results)

    print()
    print("=" * 60)
    print("  测试结果汇总")
    print("=" * 60)
    for name, ok, note in suite_results:
        icon = "✅" if ok else "❌"
        print(f"  {icon}  {name}  {note}")

    print()
    if passed_count == total_count:
        print(f"🎉 全部通过 {passed_count}/{total_count}  (耗时 {total_time:.1f}s)")
    else:
        print(f"⚠️  {passed_count}/{total_count} 通过  (耗时 {total_time:.1f}s)")
    print("=" * 60)

    sys.exit(0 if passed_count == total_count else 1)


if __name__ == "__main__":
    asyncio.run(main())
