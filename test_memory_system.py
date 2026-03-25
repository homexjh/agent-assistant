#!/usr/bin/env python3
"""
测试 Memory 系统 - 展示 Week 1-3 的所有新功能

运行: python test_memory_system.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from aiagent.memory_manager import MemoryManager
from aiagent.daily_log import (
    create_daily_log,
    get_daily_log_path,
    append_to_daily_log,
    list_recent_logs,
)
from aiagent.workspace import _DEFAULT_WORKSPACE


# =============================================================================
# 测试 1: MemoryManager - 结构化内存管理
# =============================================================================
def test_memory_manager():
    print("=" * 60)
    print("🔹 测试 1: MemoryManager - 结构化 MEMORY.md 管理")
    print("=" * 60)
    
    memory_path = _DEFAULT_WORKSPACE / "MEMORY.md"
    mm = MemoryManager(memory_path)
    
    # 1.1 读取现有数据
    print("\n1.1 读取现有数据：")
    print(f"   system.current_date = {mm.get('system.current_date')}")
    print(f"   system.version = {mm.get('system.version')}")
    print(f"   facts.project.repo_path = {mm.get('facts.project.repo_path')}")
    print(f"   facts.project.tech_stack = {mm.get('facts.project.tech_stack')}")
    
    # 1.2 读取不存在的键
    print("\n1.2 读取不存在的键：")
    print(f"   facts.nonexistent = {mm.get('facts.nonexistent')}")
    print(f"   facts.nonexistent (with default) = {mm.get('facts.nonexistent', 'default_value')}")
    
    # 1.3 写入数据
    print("\n1.3 写入新数据：")
    mm.set("facts.test.key1", "value1")
    mm.set("facts.test.nested.key2", "nested_value")
    print(f"   已写入 facts.test.key1 = {mm.get('facts.test.key1')}")
    print(f"   已写入 facts.test.nested.key2 = {mm.get('facts.test.nested.key2')}")
    
    # 1.4 列出所有键
    print("\n1.4 列出所有可用的键（部分）：")
    keys = mm.list_keys()
    for key in keys[:10]:
        print(f"   - {key}")
    if len(keys) > 10:
        print(f"   ... 还有 {len(keys) - 10} 个")
    
    # 1.5 更新系统日期
    print("\n1.5 更新系统日期：")
    old_date = mm.get("system.current_date")
    mm.update_system_date()
    new_date = mm.get("system.current_date")
    print(f"   原日期: {old_date}")
    print(f"   新日期: {new_date}")
    
    print("\n✅ MemoryManager 测试通过\n")


# =============================================================================
# 测试 2: 每日日志系统
# =============================================================================
def test_daily_log():
    print("=" * 60)
    print("🔹 测试 2: 每日日志系统")
    print("=" * 60)
    
    # 2.1 获取今天日志路径
    print("\n2.1 今天的日志路径：")
    log_path = get_daily_log_path()
    print(f"   {log_path}")
    
    # 2.2 创建日志（如果不存在）
    print("\n2.2 创建/获取今天的日志：")
    if not log_path.exists():
        create_daily_log(summary="测试日志")
        print("   ✓ 创建了新的日志文件")
    else:
        print("   → 日志文件已存在")
    
    # 2.3 追加内容
    print("\n2.3 追加内容到日志：")
    append_to_daily_log("测试记录 1: MemoryManager 工作正常", "对话列表")
    append_to_daily_log("测试记录 2: 需要修复 bug #123", "待办")
    append_to_daily_log("测试记录 3: 完成了功能 A", "重要事项")
    print("   ✓ 已追加 3 条记录")
    
    # 2.4 查看日志内容
    print("\n2.4 日志内容：")
    content = log_path.read_text(encoding="utf-8")
    print(content[:800] + "..." if len(content) > 800 else content)
    
    # 2.5 列出最近日志
    print("\n2.5 最近的日志文件：")
    recent_logs = list_recent_logs(days=7)
    for log in recent_logs[:5]:
        print(f"   - {log.name}")
    
    print("\n✅ 每日日志测试通过\n")


# =============================================================================
# 测试 3: Memory 工具（通过模拟调用）
# =============================================================================
async def test_memory_tools():
    print("=" * 60)
    print("🔹 测试 3: Memory 工具")
    print("=" * 60)
    
    from aiagent.tools.memory import (
        memory_get_tool,
        memory_set_tool,
        memory_list_tool,
        memory_search_tool,
    )
    
    # 3.1 memory_get
    print("\n3.1 memory_get 工具：")
    result = await memory_get_tool.handler(key="system.version")
    print(f"   调用: memory_get(key='system.version')")
    print(f"   结果: {result}")
    
    # 3.2 memory_set
    print("\n3.2 memory_set 工具：")
    result = await memory_set_tool.handler(key="facts.test.tool_test", value="test_value")
    print(f"   调用: memory_set(key='facts.test.tool_test', value='test_value')")
    print(f"   结果: {result}")
    
    # 3.3 memory_list
    print("\n3.3 memory_list 工具：")
    result = await memory_list_tool.handler()
    print(f"   调用: memory_list()")
    lines = result.split("\n")
    print(f"   结果 (前 10 行):")
    for line in lines[:10]:
        print(f"     {line}")
    
    # 3.4 memory_search
    print("\n3.4 memory_search 工具（全文搜索）：")
    result = await memory_search_tool.handler(action="search", query="project")
    print(f"   调用: memory_search(action='search', query='project')")
    print(f"   结果: {result[:300]}...")
    
    print("\n✅ Memory 工具测试通过\n")


# =============================================================================
# 测试 4: 每日日志工具
# =============================================================================
async def test_daily_log_tools():
    print("=" * 60)
    print("🔹 测试 4: 每日日志工具")
    print("=" * 60)
    
    from aiagent.tools.daily_log import (
        daily_log_get_tool,
        daily_log_append_tool,
        daily_log_list_tool,
    )
    
    # 4.1 daily_log_get
    print("\n4.1 daily_log_get 工具：")
    result = await daily_log_get_tool.handler()
    print(f"   调用: daily_log_get()")
    lines = result.split("\n")
    print(f"   结果 (前 10 行):")
    for line in lines[:10]:
        print(f"     {line}")
    
    # 4.2 daily_log_append
    print("\n4.2 daily_log_append 工具：")
    result = await daily_log_append_tool.handler(
        entry="通过工具测试添加的日志",
        section="对话列表"
    )
    print(f"   调用: daily_log_append(entry='...', section='对话列表')")
    print(f"   结果: {result}")
    
    # 4.3 daily_log_list
    print("\n4.3 daily_log_list 工具：")
    result = await daily_log_list_tool.handler(days=7)
    print(f"   调用: daily_log_list(days=7)")
    print(f"   结果:")
    for line in result.split("\n"):
        print(f"     {line}")
    
    print("\n✅ 每日日志工具测试通过\n")


# =============================================================================
# 主函数
# =============================================================================
async def main():
    print("\n" + "=" * 60)
    print("🧪 Memory 系统测试 - Week 1-3 功能验证")
    print("=" * 60 + "\n")
    
    try:
        # 测试 1: MemoryManager
        test_memory_manager()
        
        # 测试 2: 每日日志
        test_daily_log()
        
        # 测试 3: Memory 工具
        await test_memory_tools()
        
        # 测试 4: 每日日志工具
        await test_daily_log_tools()
        
        print("=" * 60)
        print("🎉 所有测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
