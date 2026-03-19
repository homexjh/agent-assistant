# 记忆系统与父子 Agent 设计文档

## 1. 当前阶段评估

| 模块                              | 状态                     | 说明                          |
| --------------------------------- | ------------------------ | ----------------------------- |
| **Phase 1: 服务端会话存储** | ✅**已完成**       | 会话列表 + 消息持久化到文件   |
| **Phase 2: Token 感知**     | ✅**已完成**       | 实时显示上下文 token 使用量     |
| **Phase 3: Compaction**     | ⏳**延后**         | 等实际需求出现再做            |
| **MEMORY.md**               | ⚠️**基础版**     | 需要结构化升级                |
| **父子 Agent 记忆**         | ✅**已完成**       | Workspace 隔离 + 上下文注入   |

---

## 2. 务实开发计划（调整后）

### 背景

当前模型（kimi-k2）上下文窗口为 **200K tokens**，普通对话很难触及限制：

- 典型对话：~1000-3000 tokens/轮
- 20 轮才：20K-60K tokens
- 距离 200K 还有很大余量

**结论**：Phase 2/3 的复杂截断和 compaction 机制现阶段收益有限，优先做**更紧迫、更有实际收益**的事项。

---

### Week 1: 轻量 Token 计数 + 子 Agent 隔离

#### Day 1-2: Token 统计（仅展示，不截断） ✅ 已完成

实现目标：

- [x] 实现简化 token 估算算法（中文 1.5 tokens/字，英文 1.3 tokens/词）
- [x] 在 Web UI Header 显示当前对话的 token 使用量
- [x] 支持状态颜色（normal/warning/danger）

预期界面：

```
ᵀᵒᵋᵉₙꞰ 1.2K / 200K (0.6%)
```

**实现细节**：
- 新增 `aiagent/token_utils.py` 提供 token 估算功能
- 每轮对话前发送 `token_usage` 事件更新显示
- 支持多种模型的上下文窗口查询（kimi/gpt/claude/deepseek）

#### Day 3-5: Phase 4 - 子 Agent 隔离强化

**背景**：子 Agent 目前可以访问父 Agent 的 MEMORY.md，存在污染风险。

实现目标：

- [x] 子 Agent 使用独立 workspace：`workspace/subagents/{label}-{timestamp}/`
- [x] 禁止子 Agent 写入父 Agent 的 MEMORY.md（只读复制基础配置文件）
- [x] 上下文注入：启动时从父 Agent MEMORY.md 读取关键信息作为 task 前缀

**实现细节**：

```python
# 新增文件: aiagent/subagent_workspace.py
# 核心功能:
- create_subagent_workspace()  # 创建隔离 workspace
- build_context_injection()    # 构建上下文注入
- cleanup_subagent_workspace() # 清理策略

# 修改: aiagent/subagent.py
spawn_subagent(
    task="...",
    label="...",
    parent_workspace="workspace/",           # 父 Agent workspace
    context_fields=["user_preferences", "current_project"],  # 注入字段
    cleanup_policy="archive"                 # 清理策略
)
```

**复制的文件**：AGENTS.md, TOOLS.md, IDENTITY.md, SOUL.md

**子 Agent MEMORY.md**：仅包含系统信息，不含父 Agent 长期记忆

**清理策略**：
- `immediate` - 任务完成立即删除
- `keep` - 保留不动  
- `archive` (默认) - 移动到 `workspace/subagents/archive/`

架构图：

```
父 Agent Workspace                    子 Agent Workspace
┌──────────────────┐                 ┌──────────────────┐
│ MEMORY.md        │ ──注入文本──>   │ 隔离运行区       │
│  - 用户偏好       │   (只读)        │  - result.json   │
│  - 当前项目       │                 │  - transcript    │
└──────────────────┘                 └──────────────────┘
         │                                    │
         │                                    │ announce
         ▼                                    ▼
    更新/合并结果 <────────────────────── 任务完成
```

**API 设计**：

```python
def spawn_subagent(
    task: str, 
    label: str,
    context_injection: dict = None,  # 注入的上下文字段
    cleanup: str = "archive"  # immediate / keep / archive
):
    """
    1. 读取父 Agent MEMORY.md 中 context_injection 指定的字段
    2. 组装增强 task（前缀注入）
    3. 在独立 workspace 启动子 Agent
    4. 完成后通过 announce 回传结果
    """
```

#### Day 6-7: Phase 5 - MEMORY.md 结构化（基础版）

**目标**：让 Agent 能正确读取和写入结构化记忆

当前格式（非结构化）：

```markdown
# Memory
- User likes chinese
- Project: aiagent
```

新格式（结构化）：

```markdown
# Memory

## System
- current_date: 2026-03-19
- version: 1

## User Preferences
- language: zh-CN
- timezone: Asia/Shanghai

## Facts
### Project: aiagent
- repo_path: /Users/emdoor/Documents/projects/ai_pc_aiagent_os
- current_branch: feature/todo-list-20260318

## Daily Summaries
### 2026-03-19
- 完成服务端会话存储修复
```

实现：

- [ ] 定义 MEMORY.md schema
- [ ] 实现 `memory_get(key)` 和 `memory_set(key, value)` 工具
- [ ] 自动更新 `System.current_date`

---

### Week 2+: 后续优化（按需进行）

| 优先级 | 事项       | 触发条件                  |
| ------ | ---------- | ------------------------- |
| 中     | 上下文截断 | 用户反馈"对话太长记不住"  |
| 中     | Compaction | 上下文经常超过 50K tokens |
| 低     | 向量记忆   | 需要语义搜索记忆          |

---

## 3. 详细设计

### 3.1 父子 Agent 记忆共享方案（改良版严格隔离）

#### 设计原则

**核心目标**：子 Agent 不污染父 Agent 记忆，同时能获取必要上下文

**参考对比**：

- OpenClaw：严格隔离，子 Agent 只继承 AGENTS.md + TOOLS.md
- 我们的方案：改良版严格隔离，允许**一次性上下文注入**

#### 上下文注入机制

```python
def prepare_context_injection(fields: list[str]) -> str:
    """从父 Agent MEMORY.md 读取指定字段，组装注入文本"""
    memory = parse_memory_md()  # 解析结构化 MEMORY.md
  
    injection_parts = []
    for field in fields:
        if field in memory:
            injection_parts.append(f"- {field}: {memory[field]}")
  
    if not injection_parts:
        return ""
  
    return f"""【来自父 Agent 的上下文（只读，仅本次任务有效）】
{chr(10).join(injection_parts)}

---

"""

def spawn_subagent(
    task: str, 
    label: str,
    context_injection: list[str] = ["user_preferences", "current_project"]
):
    # 1. 准备注入上下文
    injection = prepare_context_injection(context_injection)
  
    # 2. 组装增强任务
    enhanced_task = injection + task
  
    # 3. 在独立 workspace 启动
    run_id = sessions_spawn(
        task=enhanced_task,
        label=label,
        workspace=f"workspace/subagents/{label}-{timestamp}/"
    )
  
    return run_id
```

#### 结果回传机制（已存在）

```python
# subagent.py - 已存在
def spawn_subagent(task, label):
    def run_and_announce():
        result = run_session(task)
        manager.announce(run_id, result)
  
    threading.Thread(target=run_and_announce).start()
```

父 Agent 处理：

```python
# agent.py
# 在对话循环中检查 announce 队列
while True:
    try:
        msg = manager.announce_queue.get_nowait()
        messages.append(msg)  # 注入子 Agent 结果
    except Empty:
        break
```

#### 隔离保证

| 层级                 | 父 Agent   | 子 Agent                 | 控制方式   |
| -------------------- | ---------- | ------------------------ | ---------- |
| **文件系统**   | workspace/ | workspace/subagents/xxx/ | 物理隔离   |
| **MEMORY.md**  | 可读写     | ❌ 不可访问              | 路径隔离   |
| **上下文注入** | 提供       | 只读（文本）             | 一次性注入 |
| **结果回传**   | 接收       | 写入 announce 队列       | 队列机制   |

### 3.2 记忆分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    工作记忆 (Working Memory)                   │
│              当前对话上下文 (~200K tokens)                      │
│              存储：内存 (history[])                           │
├─────────────────────────────────────────────────────────────┤
│                    短期记忆 (Short-term Memory)                │
│         memory/YYYY-MM-DD.md - 当天完整对话日志                │
│         保留：7-30天（按需配置）                                │
├─────────────────────────────────────────────────────────────┤
│                    长期记忆 (Long-term Memory)                 │
│  MEMORY.md - 用户偏好、重要事实、项目信息（结构化）              │
│  memory/projects/*.md - 项目专用记忆                          │
│  保留：永久                                                   │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 MEMORY.md Schema（v1.0）

```markdown
# Memory

## System
- current_date: 2026-03-19
- last_updated: 2026-03-19T14:30:00+08:00
- version: 1

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

## Daily Summaries
### 2026-03-19
- 完成子 Agent 隔离设计
```

---

## 4. 配置汇总

```python
# config/memory.py

MEMORY_CONFIG = {
    # Phase 2: Token 统计（轻量版）
    "ui": {
        "show_token_count": True,
        "token_count_position": "header",  # header / footer / hidden
    },
  
    # Phase 4: 子 Agent
    "subagent": {
        "workspace": {
            "base_path": "workspace/subagents",
            "cleanup_policy": "archive",  # immediate / keep / archive
            "keep_duration_hours": 24,
        },
        "context_injection": {
            "enabled": True,
            "default_fields": ["user_preferences", "current_project"],
            "max_chars": 500,
        },
        "sandbox": {
            "isolated": True,  # True: 禁止访问父 Agent 文件
        },
    },
  
    # Phase 5: MEMORY.md
    "memory": {
        "format_version": "1.0",
        "auto_update_date": True,
    },
  
    # Phase 3: Compaction（预留，暂不启用）
    "compaction": {
        "enabled": False,  # 默认关闭，等实际需要再开启
        "threshold_tokens": 60000,  # 提升到 60K
        "summary_model": "gpt-4o-mini",
    },
}
```

---

## 5. 实施路线图

### Week 1（当前）

| 天数    | 任务                    | 产出                         |
| ------- | ----------------------- | ---------------------------- |
| Day 1-2 | Token 统计              | UI 显示 token 使用量         |
| Day 3-4 | 子 Agent workspace 隔离 | 独立目录运行                 |
| Day 5   | 上下文注入              | 子 Agent 能读取父 Agent 偏好 |
| Day 6-7 | MEMORY.md 结构化        | 新格式 + memory_get/set 工具 |

### 后续（按需）

- **Token 截断**：等用户反馈需要时
- **Compaction**：等上下文经常超过 50K 时
- **向量记忆**：等需要语义搜索时

---

## 6. 下一步行动

1. **确认技术选型**：

   - Token 计数库：tiktoken（精确）vs 字符估算（简单）
   - 子 Agent 隔离：路径限制 vs 文件权限
2. **开始 Week 1 Day 1**：实现 Token 统计
