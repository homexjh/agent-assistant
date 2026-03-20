# 记忆系统与上下文管理设计文档

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-03-18 | 初始版本，包含 Phase 1-5 规划 |
| 1.1 | 2026-03-20 | 添加详细架构设计、OpenClaw 参考、实施计划 |

---

## 1. 设计目标

### 1.1 核心原则

| 原则 | 说明 | 决策依据 |
|------|------|----------|
| **简单优先** | 文件-based，无外部依赖 | 本地开发场景，避免过度工程 |
| **严格隔离** | 子 Agent 无法访问父 Agent 敏感信息 | 安全性，防止记忆污染 |
| **按需注入** | 只传递任务必要的上下文 | 减少 Token 浪费，保护隐私 |
| **渐进优化** | 先做基础结构化，向量记忆按需再做 | MVP 阶段，验证需求后再投入 |

### 1.2 不做的事项

| 功能 | 原因 | 未来可能触发条件 |
|------|------|-----------------|
| 向量记忆数据库 | 增加复杂度，当前场景不需要 | 记忆条目 > 1000，需要语义搜索 |
| BM25 全文检索 | Markdown 文件简单读取足够 | 需要复杂记忆检索 |
| 智能遗忘算法 | 手动维护 MEMORY.md 更可控 | 记忆量爆炸，手动维护困难 |
| 云端存储 | 本地开发，无需同步 | 多设备协作需求 |

---

## 2. 整体架构

### 2.1 分层记忆架构

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
│  │  │  ├── 工具调用 (tool_calls)                                  │ │
│  │  │  └── 工具结果 (tool_result)                                 │ │
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
│  │  workspace/ 目录                                              │ │
│  │  ┌─────────────┬────────────────────────────────────────────┐ │ │
│  │  │ AGENTS.md   │ 启动序列、操作清单、行为规则（所有Agent可见）│ │ │
│  │  ├─────────────┼────────────────────────────────────────────┤ │ │
│  │  │ TOOLS.md    │ 环境专属信息（所有Agent可见）                │ │ │
│  │  ├─────────────┼────────────────────────────────────────────┤ │ │
│  │  │ SOUL.md     │ 人格、语气、价值观（所有Agent可见）          │ │ │
│  │  ├─────────────┼────────────────────────────────────────────┤ │ │
│  │  │ USER.md     │ 用户画像、个人偏好（仅主Agent可见）⭐新增     │ │ │
│  │  ├─────────────┼────────────────────────────────────────────┤ │ │
│  │  │ MEMORY.md   │ 项目信息、技术栈（仅主Agent可见）            │ │ │
│  │  ├─────────────┼────────────────────────────────────────────┤ │ │
│  │  │ memory/     │ 每日会话日志 ⭐新增                           │ │ │
│  │  │ └── YYYY-MM-DD.md                                          │ │ │
│  │  └─────────────┴────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 各层职责

| 层级 | 时效性 | 容量 | 存储位置 | 核心职责 | 可见性 |
|------|--------|------|----------|----------|--------|
| **Working Memory** | 秒级 | 200K tokens | 内存 | 当前对话实时处理 | 当前 Agent |
| **Sessions** | 天级 | GB 级 | 文件 (data/sessions/) | 近期对话持久化、检索 | 当前 Agent |
| **Subagent WS** | 任务级 | MB 级 | 文件 (workspace/subagents/) | 子 Agent 隔离运行 | 子 Agent 独享 |
| **USER.md** | 永久 | KB 级 | 文件 (workspace/) | 用户画像、私密偏好 | **仅主 Agent** |
| **MEMORY.md** | 永久 | KB 级 | 文件 (workspace/) | 项目信息、技术栈 | **仅主 Agent** |

### 2.3 文件可见性矩阵

| 文件 | 主 Agent | 子 Agent | 说明 |
|------|---------|---------|------|
| AGENTS.md | ✅ | ✅ (复制) | 启动序列、规则 |
| TOOLS.md | ✅ | ✅ (复制) | 工具说明 |
| SOUL.md | ✅ | ✅ (复制) | 人格、语气 |
| USER.md | ✅ | ❌ **不可见** | 用户画像、私密信息 |
| MEMORY.md | ✅ | ❌ **不可见** | 项目信息、技术栈 |
| memory/*.md | ✅ | ❌ **不可见** | 每日日志 |

---

## 3. 文件详细设计

### 3.1 USER.md（新增）⭐

**用途**：用户画像、个人偏好、私密信息

**加载时机**：仅主 Agent，每次对话

**子 Agent 可见性**：❌ **永不**

**Schema（v1.0）**:
```markdown
# User Profile

## Basic
- name: emdoor
- timezone: Asia/Shanghai
- language: zh-CN

## Preferences
- code_style: pep8
- doc_language: zh-CN
- response_style: concise

## Personal
- interests: AI, coding, automation
```

### 3.2 MEMORY.md（结构化改造）

**用途**：项目信息、技术栈、重要事实

**加载时机**：仅主 Agent，每次对话

**子 Agent 可见性**：❌ **永不直接可见，选择性注入**

**Schema（v1.0）**:
```markdown
# Memory

## System
- current_date: 2026-03-20
- last_updated: 2026-03-20T14:30:00+08:00
- version: 1.0

## Facts
### Project: aiagent
- repo_path: /Users/emdoor/Documents/projects/ai_pc_aiagent_os
- tech_stack: Python, FastAPI, SQLite
- current_branch: feature/todo-list-20260318

### Skills
- web_search: enabled
- browser: enabled
- exec: enabled
```

### 3.3 子 Agent MEMORY.md

**用途**：系统提示，告知工作目录

**内容**：
```markdown
# Memory

## System
- workspace_dir: /path/to/subagents/task-xxx
- parent_workspace: /path/to/workspace
- created_at: 2026-03-20T10:00:00

## Important Instructions
**You MUST save all files to your workspace directory!**

When using tools:
- Use absolute paths: /path/to/subagents/task-xxx/filename
- Or use cwd parameter: cwd="/path/to/subagents/task-xxx/"
- Do NOT create files in the parent workspace
```

---

## 4. 上下文注入设计

### 4.1 注入策略

**原则**：最小必要原则，只注入任务相关的基础信息

### 4.2 安全字段清单

| 字段 | 来源 | 是否注入 | 原因 |
|------|------|---------|------|
| language | USER.md | ✅ | 决定回复语言 |
| timezone | USER.md | ✅ | 决定时间显示 |
| response_style | USER.md | ✅ | 决定回复风格 |
| name | USER.md | ❌ | 与任务无关，保护隐私 |
| interests | USER.md | ❌ | 与任务无关，保护隐私 |
| repo_path | MEMORY.md | ⚠️ 视任务 | 代码任务需要，其他不需要 |
| tech_stack | MEMORY.md | ⚠️ 视任务 | 代码任务需要 |
| current_branch | MEMORY.md | ❌ | 敏感，任务无关 |

### 4.3 注入格式

```markdown
【来自父 Agent 的上下文（仅本次任务有效）】

【用户基础偏好】
- 语言：zh-CN（请用中文回复）
- 时区：Asia/Shanghai
- 回复风格：concise

【工作目录】
你的工作空间是：/workspace/subagents/task-20260320-xxx/
所有文件必须保存到此目录！
使用 exec 工具时请加上 cwd="/workspace/subagents/task-20260320-xxx/"。

【当前项目】aiagent（仅作背景参考）

---

【你的任务】
查询广州今天的天气...
```

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
- [ ] 智能上下文截断
- [ ] LLM 摘要生成
- **触发条件**：上下文经常超过 50K tokens

### Phase 4: 子 Agent 隔离 ✅ 已完成
- [x] 独立 Workspace 目录
- [x] 上下文注入机制
- [x] 清理策略 (immediate/keep/archive)

### Phase 5: 记忆系统完善 🔄 进行中

#### Week 1: 文件结构调整
- [ ] **新增 USER.md**：从现有 MEMORY.md 分离用户画像
- [ ] **修复上下文注入**：只注入安全字段（language/timezone/style）
- [ ] **更新加载逻辑**：主 Agent 加载 USER.md + MEMORY.md

#### Week 2: MEMORY.md 结构化
- [ ] **创建 memory_manager.py**：解析/写入结构化 Markdown
- [ ] **实现 memory_get(key)**：支持点号路径，如 `facts.project.repo_path`
- [ ] **实现 memory_set(key, value)**：自动创建 section
- [ ] **自动日期更新**：每次对话更新 `System.current_date`
- [ ] **迁移脚本**：将现有 MEMORY.md 转换为新格式

#### Week 3: 每日日志（可选）
- [ ] **创建 memory/ 目录**：按日期存储对话摘要
- [ ] **自动记录**：每天第一次对话时创建 `memory/YYYY-MM-DD.md`
- [ ] **手动触发**：支持 `/remember` 命令保存重要信息

### Phase 6: 向量记忆（按需）⏳ 未计划
- [ ] LanceDB 向量存储
- [ ] Embedding 模型集成
- [ ] 语义搜索
- **触发条件**：记忆条目 > 1000，需要语义检索

---

## 6. 技术设计

### 6.1 MemoryManager 类

```python
class MemoryManager:
    """结构化 MEMORY.md / USER.md 管理器"""
    
    def __init__(self, memory_path: Path):
        self.memory_path = memory_path
        self.data = self._parse()
    
    def _parse(self) -> dict:
        """解析 Markdown section 为嵌套字典"""
        # 解析 ## Section 和 ### Subsection
        # 支持 - key: value 格式
    
    def get(self, key: str, default=None):
        """
        获取值，支持点号路径
        get("facts.project.repo_path") → "/xxx/aiagent"
        get("system.current_date") → "2026-03-20"
        """
    
    def set(self, key: str, value):
        """
        设置值，支持点号路径
        set("facts.project.current_branch", "main")
        """
    
    def save(self):
        """保存回文件，保持 Markdown 格式"""
    
    def update_system_date(self):
        """自动更新 System.current_date"""
```

### 6.2 工具函数

```python
# tools/memory.py

async def memory_get(key: str, default: str = None) -> str:
    """
    从 MEMORY.md 读取结构化记忆
    
    Args:
        key: 键路径，如 "facts.project.repo_path"
        default: 默认值
    
    Returns:
        值字符串
    """

async def memory_set(key: str, value: str) -> str:
    """
    写入结构化记忆到 MEMORY.md
    
    Args:
        key: 键路径，如 "facts.project.current_branch"
        value: 要设置的值
    
    Returns:
        成功/失败信息
    """
```

### 6.3 配置文件

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
        "cleanup_policy": "archive",
        "context_injection": {
            "enabled": True,
            # ⚠️ 只注入安全字段
            "user_fields": ["language", "timezone", "response_style"],
            "max_chars": 500,
        },
    },
    
    # Long-term Memory
    "memory": {
        "format_version": "1.0",
        "auto_update_date": True,
        "sections": ["System", "Facts"],  # USER.md: ["Basic", "Preferences", "Personal"]
    },
}
```

---

## 7. 与 OpenClaw 的对比

### 7.1 我们学习的

| OpenClaw 实践 | 我们的实现 |
|--------------|-----------|
| AGENTS.md / TOOLS.md / SOUL.md 分离 | ✅ 已有 |
| USER.md 仅主 Agent 可见 | ✅ 新增 |
| MEMORY.md 永不暴露给子 Agent | ✅ 修复注入策略 |
| memory/ 每日日志目录 | ⚠️ Phase 5 Week 3 |
| checklists/ 高风险操作清单 | ❌ 暂不需要 |

### 7.2 我们不做的

| OpenClaw 功能 | 原因 |
|--------------|------|
| LanceDB 向量记忆 | 增加复杂度，本地开发不需要 |
| BM25 全文检索 | Markdown 文件简单读取足够 |
| 智能遗忘（Weibull） | 手动维护 MEMORY.md 更可控 |
| 多作用域隔离（global/agent/user） | 单一用户场景，workspace 隔离足够 |

---

## 8. 附录

### 8.1 文件模板

#### USER.md 模板
```markdown
# User Profile

## Basic
- name: 
- timezone: Asia/Shanghai
- language: zh-CN

## Preferences
- code_style: pep8
- doc_language: zh-CN
- response_style: concise

## Personal
- interests: 
```

#### MEMORY.md 模板
```markdown
# Memory

## System
- current_date: 2026-03-20
- version: 1.0

## Facts
### Project: 
- repo_path: 
- tech_stack: 
- current_branch: 
```

### 8.2 迁移指南

**从旧版 MEMORY.md 迁移**：

1. 备份原文件：`cp MEMORY.md MEMORY.md.backup`
2. 提取用户画像 → 移动到 USER.md
3. 格式化项目信息 → 按 Facts section 组织
4. 运行迁移脚本：`python scripts/migrate_memory.py`

### 8.3 相关文件

| 文件 | 职责 |
|------|------|
| `aiagent/memory_manager.py` | 核心解析/写入逻辑（新增） |
| `aiagent/tools/memory.py` | memory_get/memory_set 工具（新增） |
| `aiagent/subagent_workspace.py` | 子 Agent Workspace 管理 |
| `workspace/USER.md` | 用户画像（新增） |
| `workspace/MEMORY.md` | 项目信息（改造） |
| `workspace/memory/` | 每日日志目录（新增） |
