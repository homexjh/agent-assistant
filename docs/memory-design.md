# 记忆系统与上下文管理设计文档

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-03-18 | 初始版本，包含 Phase 1-4 规划 |
| 1.1 | 2026-03-19 | 添加详细架构设计和原理说明 |

---

## 1. 整体架构

### 1.1 分层记忆架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         用户交互层                                   │
│                    （对话输入、文件上传、Web UI）                      │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      工作记忆 (Working Memory)                        │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  当前对话上下文 (history[])                                     │ │
│  │  - 用户消息                                                    │ │
│  │  - Assistant 回复                                              │ │
│  │  │  ├── 普通文本                                               │ │
│  │  │  ├── 推理过程 (reasoning_content)                          │ │
│  │  │  ├── 工具调用 (tool_calls)                                 │ │
│  │  │  └── 工具结果 (tool_result)                                │ │
│  │  - Token 使用量：约 0-200K                                     │ │
│  │  - 生命周期：单次对话                                          │ │
│  │  - 存储：内存                                                  │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
        ┌──────────────────┐    ┌──────────────────┐
        │   子 Agent 隔离   │    │  服务端会话存储   │
        │  (Subagent WS)   │    │  (sessions/)     │
        │                  │    │                  │
        │ 临时 workspace/  │    │ 持久化历史对话   │
        │ subagents/{id}/  │    │ - index.json     │
        │ - 隔离运行       │    │ - sess_xxx.json  │
        │ - 结果回传       │    │ - 跨会话检索     │
        └──────────────────┘    └──────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      长期记忆 (Long-term Memory)                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  MEMORY.md - 结构化长期记忆                                    │ │
│  │  ┌─────────────┬────────────────────────────────────────────┐ │ │
│  │  │ System      │ current_date, version                      │ │ │
│  │  ├─────────────┼────────────────────────────────────────────┤ │ │
│  │  │ User Prefs  │ language, timezone, response_style         │ │ │
│  │  ├─────────────┼────────────────────────────────────────────┤ │ │
│  │  │ Facts       │ Project info, Personal info                │ │ │
│  │  ├─────────────┼────────────────────────────────────────────┤ │ │
│  │  │ Daily Summ. │ 每日对话摘要                               │ │ │
│  │  └─────────────┴────────────────────────────────────────────┘ │ │
│  │  - 保留：永久                                                   │ │
│  │  - 更新：每次对话后选择性写入                                   │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 各层职责

| 层级 | 时效性 | 容量 | 存储位置 | 核心职责 |
|------|--------|------|----------|----------|
| **Working Memory** | 秒级 | 200K tokens | 内存 | 当前对话实时处理 |
| **Sessions** | 天级 | GB 级 | 文件 (data/sessions/) | 近期对话持久化、检索 |
| **Subagent WS** | 任务级 | MB 级 | 文件 (workspace/subagents/) | 子 Agent 隔离运行 |
| **MEMORY.md** | 永久 | MB 级 | 文件 (workspace/MEMORY.md) | 核心知识、用户画像 |

---

## 2. 详细设计

### 2.1 工作记忆 (Working Memory)

#### 数据结构

```python
# 内存中的 history 数组
history = [
    {
        "role": "user",
        "content": "用户输入内容",
        "metadata": {"timestamp": "..."}
    },
    {
        "role": "assistant",
        "content": "回复文本",
        "metadata": {
            "type": "reasoning",  # reasoning / final / tool_calls
            "round": 1
        }
    },
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [...],  # 工具调用
        "metadata": {"type": "tool_calls"}
    },
    {
        "role": "tool",
        "content": "工具返回结果",
        "tool_call_id": "...",
        "name": "exec"
    }
]
```

#### 为什么放在内存

- **快**：纳秒级访问，不阻塞对话
- **灵活**：可以随时修改、截断、重建
- **临时**：对话结束后可以丢弃

#### 数据流转

```
对话开始时：Sessions 文件 ──加载──► Working Memory (history)
对话进行中：Working Memory ──实时保存──► Sessions 文件
对话结束时：Working Memory ──最终保存──► Sessions 文件
```

---

### 2.2 服务端会话存储

#### 存储结构

```
data/sessions/
├── index.json              # 会话索引
│   └── [{"id": "...", "title": "...", "updated_at": ...}]
├── sess_xxx1.json          # 会话1完整历史
│   └── {"id": "...", "messages": [...], "created_at": ...}
└── sess_xxx2.json          # 会话2完整历史
```

#### 为什么需要这层

1. **持久化**：服务重启后对话还在
2. **跨会话检索**：可以查找、继续之前的对话
3. **调试方便**：可以直接查看 JSON 文件

---

### 2.3 子 Agent Workspace 隔离

#### 设计原则：严格隔离 + 上下文注入

**问题（隔离前）**：
```
父 Agent
├── MEMORY.md (长期记忆)
└── 子 Agent A 运行中
    └── [可能写入 MEMORY.md，污染父 Agent 记忆]
```

**方案（隔离后）**：
```
父 Agent Workspace              子 Agent A Workspace
├── MEMORY.md (完整)             ├── MEMORY.md (仅系统信息)
├── AGENTS.md ──复制─────────>   ├── AGENTS.md (副本)
├── TOOLS.md  ──复制─────────>   ├── TOOLS.md (副本)
└── SOUL.md   ──复制─────────>   ├── SOUL.md (副本)
                                  └── 子 Agent 只能在这里写文件

上下文注入（只读，一次性）：
"【来自父 Agent 的上下文】
 【重要！工作目录】你的工作空间是 xxx
 所有文件必须保存到此目录下！"
```

#### 架构图

```
父 Agent                      子 Agent (隔离)
┌────────────────┐            ┌────────────────────┐
│ MEMORY.md      │            │ 隔离 Workspace     │
│  - 用户偏好     │ ──注入──>  │ - AGENTS.md (副本) │
│  - 项目信息     │  (只读)    │ - TOOLS.md (副本)  │
└────────────────┘            │ - MEMORY.md (新)   │
       │                       │ - result.txt       │
       │                       └────────────────────┘
       │                                │
       │                                │ announce 回传
       │                                ▼
       └────────────────────────── 接收结果
       (选择性合并到长期记忆)
```

#### 为什么严格隔离

1. **安全性**：子 Agent 可能被攻击/误导，隔离防止污染
2. **并行性**：多个子 Agent 同时运行互不干扰
3. **可追溯**：每个子 Agent 的工作目录可单独检查
4. **可清理**：任务完成后可删除/归档

#### 上下文注入机制

```python
# 注入内容示例
"""
【来自父 Agent 的上下文（仅本次任务有效）】

【重要！工作目录】
你的工作空间是：/workspace/subagents/task-20260320-xxx/
所有文件必须保存到此目录下！
使用 exec 工具时请加上 cwd="/workspace/subagents/task-20260320-xxx/"。

【用户偏好】
- language: zh-CN
- timezone: Asia/Shanghai

【当前项目】
aiagent

---

【你的任务】
查询广州今天的天气...
"""
```

---

### 2.4 长期记忆 (MEMORY.md)

#### 当前格式（非结构化）

```markdown
# Memory
- 用户的幸运数字是 42
- 测试记忆条目
- 当前系统日期：...
```

**问题**：
- Agent 读不懂类型（这是用户偏好？还是项目信息？）
- 无法精确读取特定字段
- 更新困难

#### 目标格式（结构化）

```markdown
# Memory

## System
- current_date: 2026-03-20
- last_updated: 2026-03-20T14:30:00+08:00
- version: 1.0

## User Preferences
- language: zh-CN
- timezone: Asia/Shanghai
- response_style: concise

## Facts
### Project: aiagent
- repo_path: /Users/emdoor/Documents/projects/ai_pc_aiagent_os
- current_branch: feature/todo-list-20260318
- tech_stack: Python, FastAPI

### Personal
- name: emdoor
- lucky_number: 42

## Daily Summaries
### 2026-03-20
- 完成子 Agent Workspace 隔离
- 实现上下文注入机制
```

#### 结构化的好处

| 能力 | 非结构化 | 结构化 |
|------|----------|--------|
| 精确读取 | ❌ 无法 | ✅ `memory_get("user_preferences.language")` |
| 分类管理 | ❌ 混在一起 | ✅ System/User/Facts 分离 |
| 自动更新 | ❌ 手动 | ✅ `memory_set("system.date", "...")` |
| 上下文注入 | ❌ 有限 | ✅ 选择性注入特定 section |

---

## 3. 数据流转

### 3.1 完整数据流

```
用户输入
    │
    ▼
┌─────────────────────────┐
│  工作记忆 (history)      │◄──── 当前对话上下文
│  - 加载 Sessions 历史    │
│  - 实时接收用户输入      │
└─────────────────────────┘
    │
    ├─► LLM 处理 ──► 生成回复
    │
    ├─► 实时保存到 Sessions/
    │
    ├─► 派生子 Agent ──► 隔离 Workspace
    │                       │
    │                       ▼
    │                   子 Agent 运行
    │                       │
    │                       ▼
    │                   announce 回传结果
    │                       │
    └───────────────────────┘
        │
        ▼
    对话结束
        │
        ├─► 保存到 Sessions/
        │
        └─► 选择性更新 MEMORY.md
            (用户明确说"记住 xxx" 或检测到重要事实)
```

### 3.2 子 Agent 数据流

```
父 Agent spawn_subagent()
    │
    ├──► 创建隔离 Workspace
    │       - 复制 AGENTS.md, TOOLS.md, SOUL.md
    │       - 创建新的 MEMORY.md (仅系统信息)
    │
    ├──► 构建上下文注入
    │       - 工作目录提示
    │       - 用户偏好
    │       - 项目信息
    │
    ├──► 组装增强 Task
    │       (上下文注入 + 原始 Task)
    │
    └──► 在子线程中运行子 Agent
            │
            ▼
        子 Agent 执行 Task
            │
            ├─► 使用隔离 Workspace 的工具
            │
            └─► 完成 ──► manager.announce(result)
                            │
                            ▼
                        父 Agent 接收结果
                            │
                            ├─► 展示给用户
                            │
                            └─► 选择性更新 MEMORY.md
```

---

## 4. 设计原则

### 4.1 分层原则

**快变慢存**：
- 需要实时访问的 → Working Memory（内存）
- 需要持久化的 → Sessions（文件）
- 需要长期保留的 → MEMORY.md（文件）

**分层的好处**：
- 效率：不是所有信息都需要实时加载
- 成本：长上下文成本高，分层可以截断
- 组织：不同类型的信息有不同的生命周期

### 4.2 隔离原则

**严格隔离**：
- 子 Agent 是"临时工"，完成特定任务
- 父 Agent 是"管家"，管理长期记忆
- 防止"临时工"把"管家"的记录本弄脏

**单向数据流**：
```
父 Agent ──注入──► 子 Agent (只读)
          (工作目录、用户偏好)
          
子 Agent ──回传──► 父 Agent (通过 announce)
          (任务结果，父 Agent 选择性采纳)
```

### 4.3 注入原则

**只读注入**：
- 子 Agent 通过 Task 前缀获取上下文
- 子 Agent 无法写父 Agent 的文件
- 父 Agent 有最终决定权

---

## 5. 实施路线图

### Phase 1: 服务端会话存储 ✅ 已完成
- [x] 会话列表 + 消息持久化到文件
- [x] REST API 管理会话
- [x] 实时保存和重建

### Phase 2: Token 统计 ✅ 已完成
- [x] 简化 token 估算算法
- [x] Web UI 显示使用量
- [x] 多模型上下文窗口支持

### Phase 3: Compaction ⏳ 延后
- 智能上下文截断
- LLM 摘要生成
- 按需启动

### Phase 4: 子 Agent 隔离 ✅ 已完成
- [x] 独立 Workspace 目录
- [x] 上下文注入机制
- [x] 清理策略 (immediate/keep/archive)

### Phase 5: MEMORY.md 结构化 🔄 规划中
- [ ] 定义结构化 Schema
- [ ] 实现 memory_get/memory_set 工具
- [ ] 自动更新 System.current_date
- [ ] 迁移现有 MEMORY.md

### Phase 6: 向量记忆（可选）⏳ 规划中
- 语义搜索记忆
- 相关性检索

---

## 6. 配置文件

### 记忆系统配置

```python
# config/memory.py

MEMORY_CONFIG = {
    # Working Memory
    "max_context_tokens": 200000,
    "reserve_tokens": 2000,
    
    # Sessions
    "sessions_dir": "data/sessions",
    "max_sessions": 100,
    
    # Subagent
    "subagent": {
        "base_path": "workspace/subagents",
        "max_concurrent": 5,
        "max_depth": 3,
        "cleanup_policy": "archive",  # immediate/keep/archive
        "context_injection": {
            "enabled": True,
            "fields": ["user_preferences", "current_project", "system"],
            "max_chars": 800,
        },
    },
    
    # Long-term Memory
    "memory": {
        "format_version": "1.0",
        "auto_update_date": True,
        "sections": ["System", "User Preferences", "Facts", "Daily Summaries"],
    },
}
```

---

## 7. 附录

### 7.1 术语表

| 术语 | 说明 |
|------|------|
| Working Memory | 当前对话的上下文，存储在内存中 |
| Sessions | 持久化的对话历史，存储在文件中 |
| Subagent WS | 子 Agent 的隔离工作目录 |
| MEMORY.md | 长期记忆文件，结构化存储 |
| 上下文注入 | 父 Agent 向子 Agent 传递信息的方式 |
| announce | 子 Agent 向父 Agent 回传结果的机制 |

### 7.2 相关文件

| 文件 | 职责 |
|------|------|
| `aiagent/memory_manager.py` | MEMORY.md 解析和管理（规划中） |
| `aiagent/subagent_workspace.py` | 子 Agent Workspace 管理 |
| `aiagent/subagent.py` | 子 Agent 派生和隔离逻辑 |
| `aiagent/session_store.py` | 服务端会话存储 |
| `aiagent/token_utils.py` | Token 估算工具 |
| `workspace/MEMORY.md` | 长期记忆文件 |
| `data/sessions/` | 会话存储目录 |
| `workspace/subagents/` | 子 Agent 隔离目录 |
