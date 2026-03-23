# Memory 系统使用说明

## 一模块调用关系图

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Agent 启动时（每次对话开始）                                    │
│                                                                  │
│  agent.py:Agent.__init__()                                        │
│      │                                                           │
│      ├─── _update_memory_date()  ───┐                          │
│      │                          │                             │
│      │                          ▼                             │
│      │              memory_manager.py:MemoryManager                │
│      │                  └─── update_system_date()                │
│      │                          │                             │
│      │                          ▼                             │
│      │                  workspace/MEMORY.md                       │
│      │                  (更新 system.current_date)                │
│      │                                                          │
│      └─── _ensure_daily_log()  ───┐                          │
│                                 │                             │
│                                 ▼                             │
│                     daily_log.py:create_daily_log()               │
│                                 │                             │
│                                 ▼                             │
│                     workspace/memory/YYYY-MM-DD.md               │
│                     (创建今天日志文件)                            │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  LLM 调用工具时（通过 function calling）                            │
│                                                                  │
│  tools/__init__.py                                                │
│      ├─── 注册 memory_get_tool                                      │
│      ├─── 注册 memory_set_tool                                      │
│      ├─── 注册 memory_list_tool                                     │
│      ├─── 注册 memory_search_tool                                   │
│      ├─── 注册 daily_log_create_tool                               │
│      ├─── 注册 daily_log_append_tool                               │
│      ├─── 注册 daily_log_get_tool                                  │
│      └─── 注册 daily_log_list_tool                                 │
│                                                                  │
│  tools/memory.py ←───→ memory_manager.py:MemoryManager             │
│      │              (读写 MEMORY.md / USER.md)                     │
│      ├─── memory_get()  → mm.get(key)                             │
│      ├─── memory_set()  → mm.set(key, value)                      │
│      └─── memory_list() → mm.get_all()                            │
│                                                                  │
│  tools/daily_log.py ←───→ daily_log.py                            │
│      │              (读写 memory/YYYY-MM-DD.md)                     │
│      ├─── daily_log_create()  → create_daily_log()                │
│      ├─── daily_log_append()  → append_to_daily_log()             │
│      ├─── daily_log_get()     → get_daily_log_path() + 读取      │
│      └─── daily_log_list()    → list_recent_logs()                │
└──────────────────────────────────────────────────────────────────────────┘
```

## 二文件层级说明

### 1. memory_manager.py - 核心库
**位置:** `aiagent/memory_manager.py`

**被谁调用:**
- `aiagent/agent.py` - Agent启动时更新日期
- `aiagent/tools/memory.py` - 工具函数调用

**功能:** 解析 Markdown 为嵌套字典，支持点号路径访问

### 2. daily_log.py - 核心库  
**位置:** `aiagent/daily_log.py`

**被谁调用:**
- `aiagent/agent.py` - Agent启动时创建日志
- `aiagent/tools/daily_log.py` - 工具函数调用

**功能:** 管理每日日志文件的创建、追加、读取

### 3. tools/memory.py - 工具封装
**位置:** `aiagent/tools/memory.py`

**被谁调用:** 被 `tools/__init__.py` 注册到工具系统，供 LLM 调用

**功能:** 将 memory_manager.py 的功能封装为 LLM 可调用的工具

### 4. tools/daily_log.py - 工具封装
**位置:** `aiagent/tools/daily_log.py`

**被谁调用:** 被 `tools/__init__.py` 注册到工具系统，供 LLM 调用

**功能:** 将 daily_log.py 的功能封装为 LLM 可调用的工具

### 5. memory/2026-03-20.md - 数据文件
**位置:** `workspace/memory/YYYY-MM-DD.md`

**被谁读写:** `aiagent/daily_log.py`

**功能:** 存储每天的对话摘要、重要事项、待办列表

## 三具体使用场景

### 场景 1: 每天自动初始化
```python
# 每次对话开始时，Agent 自动执行:

# 1. 更新 MEMORY.md 中的日期
mm = MemoryManager("workspace/MEMORY.md")
mm.update_system_date()  # 更新为 2026-03-20

# 2. 创建今天的日志文件（如果不存在）
if not exists("workspace/memory/2026-03-20.md"):
    create_daily_log()  # 创建空日志模板
```

### 场景 2: LLM 使用 Memory 工具
```
用户: 当前项目路径是什么？

LLM 调用: memory_get(key="facts.project.repo_path")
返回: /Users/emdoor/Documents/projects/ai_pc_aiagent_os

LLM 回答: 当前项目路径是 /Users/.../ai_pc_aiagent_os
```

### 场景 3: LLM 记录日志
```
用户: 记录一下，我们讨论了修复 Path 导入问题

LLM 调用: daily_log_append(
    entry="修复了 agent.py 缺少 Path 导入导致子 Agent 报错的问题",
    section="重要事项"
)
```

## 四文件内容示例

### MEMORY.md (项目记忆)
```markdown
## System
- current_date: 2026-03-20
- version: 1.0

## Facts
### Project: aiagent
- repo_path: /Users/emdoor/.../aiagent
- current_branch: feature/memory-struct-20260320
```

### USER.md (用户画像，子Agent不可见)
```markdown
## Basic
- name: emdoor
- timezone: Asia/Shanghai
- language: zh-CN
```

### memory/2026-03-20.md (每日日志)
```markdown
# 2026-03-20 (Friday)

## 摘要
测试日志

## 对话列表
- 修复了 agent.py 缺少 Path 导入的问题

## 重要事项
- 完成了 Memory 系统开发

## 待办
- 合并到主分支
```
