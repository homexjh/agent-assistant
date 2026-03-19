# 记忆系统设计文档

## 1. 当前阶段评估

| 模块 | 状态 | 说明 |
|------|------|------|
| **Phase 1: 服务端会话存储** | ✅ **已完成** | 会话列表 + 消息持久化到文件 |
| **Phase 2: Token 感知** | 🔄 **进行中** | 需要实现上下文截断 |
| **Phase 3: Compaction** | ⏳ **待启动** | 需要设计摘要机制 |
| **MEMORY.md** | ⚠️ **基础版** | 简单文本存储，无向量检索 |
| **父子 Agent 记忆** | ❌ **未实现** | 目前独立运行，无共享 |

---

## 2. 记忆分层架构（三阶段完整版）

### 2.1 三层记忆模型

```
┌─────────────────────────────────────────────────────────────┐
│                    工作记忆 (Working Memory)                   │
│              当前对话上下文 (10-20轮，约 8K-16K tokens)         │
├─────────────────────────────────────────────────────────────┤
│                    短期记忆 (Short-term Memory)                │
│         memory/YYYY-MM-DD.md - 当天完整对话日志                │
├─────────────────────────────────────────────────────────────┤
│                    长期记忆 (Long-term Memory)                 │
│  MEMORY.md - 用户偏好、重要事实、项目信息                      │
│  memory/projects/*.md - 项目专用记忆                          │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 各层职责

| 层级 | 存储位置 | 内容 | 保留时间 | 检索方式 |
|------|----------|------|----------|----------|
| 工作记忆 | 内存 (history[]) | 当前对话 | 会话期间 | 直接访问 |
| 短期记忆 | memory/YYYY-MM-DD.md | 完整对话记录 | 7-30天 | 文件名日期 |
| 长期记忆 | MEMORY.md, projects/*.md | 摘要、偏好、事实 | 永久 | 关键词/向量搜索 |

---

## 3. MEMORY.md 优化方案

### 3.1 当前问题
- 只是简单的 Markdown 文本追加
- 无结构化检索能力
- AI 容易误读时间戳

### 3.2 新目录结构

```
workspace/
├── MEMORY.md              # 长期记忆（用户偏好、重要事实）
├── memory/
│   ├── 2026-03-19.md      # 每日日志（当天对话摘要）
│   ├── 2026-03-18.md      # 昨日日志
│   ├── subagents/         # 子 Agent 写入区
│   │   ├── weather-beijing-001.md
│   │   └── weather-shanghai-002.md
│   └── projects/          # 项目专用记忆
│       └── aiagent.md
└── .memory-index/         # 向量索引（Phase 3+）
    └── memory.sqlite
```

### 3.3 结构化格式（新 MEMORY.md）

```markdown
# Memory

## System
- current_date: 2026-03-19
- last_updated: 2026-03-19T14:30:00+08:00

## User Preferences
- lucky_number: 42
- preferred_language: zh-CN
- timezone: Asia/Shanghai

## Facts
### Project: aiagent
- repo_path: /Users/emdoor/Documents/projects/ai_pc_aiagent_os
- current_branch: feature/todo-list-20260318

### Personal
- name: emdoor
- interests: [AI, coding, automation]

## Daily Summaries
### 2026-03-19
- 完成了服务端会话存储的 bug 修复
- 讨论了记忆系统的三阶段优化计划

## Tags
#project/aiagent #personal #preferences
```

### 3.4 更新规则

1. **自动写入**: AI 在完成任务后自动追加关键信息
2. **结构化**: 使用 YAML frontmatter 格式便于解析
3. **时间戳**: 所有条目必须带 ISO 8601 时间戳
4. **标签系统**: 支持 #tag 便于分类检索

---

## 4. 父子 Agent 记忆共享机制

### 4.1 当前问题

- 子 Agent 独立运行，无法访问父 Agent 的上下文
- 子 Agent 完成后只返回最终结果，丢失思考过程
- 多次 spawn 子 Agent 时重复提供背景信息

### 4.2 分层写入方案（推荐）

```
父 Agent (main session)
    │
    ├── 读取 MEMORY.md + memory/今日.md 获取上下文
    │
    ├── spawn 子 Agent A
    │   ├── 注入父 Agent 的上下文（只读）
    │   ├── 子 Agent 写入 workspace/memory/subagents/xxx.md
    │   └── 完成后通知父 Agent
    │
    ├── spawn 子 Agent B
    │   └── 同样可以访问共享上下文
    │
    └── 汇总所有子 Agent 结果，选择性合并到主记忆

workspace/memory/
├── parent/              # 父 Agent 主记忆（只读继承）
│   ├── MEMORY.md
│   └── 2026-03-19.md
└── subagents/           # 子 Agent 写入区
    ├── weather-beijing-001.md
    └── weather-shanghai-002.md
```

### 4.3 具体实现

#### 4.3.1 子 Agent 启动时注入记忆

```javascript
// 父 Agent 在 spawn 子 Agent 时
function spawnSubagent(task, label) {
    // 1. 准备记忆上下文
    const memoryContext = {
        userPreferences: readMemory("user_preferences"),
        currentProject: readMemory("current_project"),
        recentFacts: readMemorySection("daily_summaries", 3)
    };
    
    // 2. 在 task 前添加上下文
    const enhancedTask = `
上下文信息（来自父 Agent 的记忆）：
- 用户偏好: ${memoryContext.userPreferences}
- 当前项目: ${memoryContext.currentProject}
- 相关背景: ${memoryContext.recentFacts}

你的任务：
${task}

注意：
1. 你可以访问 workspace/memory/parent/ 目录获取完整记忆
2. 完成后请将关键发现写入 workspace/memory/subagents/${label}.md
3. 不要修改 parent/ 目录下的文件
    `;
    
    return sessionsSpawn({task: enhancedTask, label});
}
```

#### 4.3.2 子 Agent 结果写回

```javascript
// 子 Agent 完成后自动执行
function onSubagentComplete(result, label, parentSessionId) {
    // 1. 提取关键信息
    const summary = extractKeyPoints(result);
    
    // 2. 写入子 Agent 专属区域
    writeToSubagentMemory(label, `
## [子 Agent: ${label}] ${new Date().toISOString()}
### 任务摘要
${summary}

### 详细结果
${result.substring(0, 2000)}...
`);
    
    // 3. 通知父 Agent
    notifyParent(parentSessionId, {
        type: 'subagent_complete',
        label: label,
        summary: summary
    });
}

// 父 Agent 选择性合并
function mergeSubagentMemory(label) {
    const content = readSubagentMemory(label);
    if (containsImportantFact(content)) {
        appendToDailyMemory(extractFact(content));
    }
}
```

---

## 5. 技术实施路线图

### Phase 2: Token 感知 + 智能截断 (2-3周)

#### Week 1: Token 计数基础
- [ ] 集成 tiktoken 或类似库进行 token 估算
- [ ] 在发送请求前计算当前上下文 token 数
- [ ] 添加配置项：`max_context_tokens` (默认 8000)

#### Week 2: 上下文截断策略
- [ ] 实现分层截断：
  - 保留 System Prompt (必须)
  - 保留最近 N 轮完整对话 (可配置，默认 10 轮)
  - 更早的历史：压缩为摘要或丢弃
- [ ] 添加 `reserve_tokens` 配置 (预留 token 给回复)

#### Week 3: 智能选择
- [ ] 当超过阈值时，使用相关性算法选择保留的消息
- [ ] 实现简单的关键词匹配保留重要消息

### Phase 3: Compaction + 摘要 (3-4周)

#### Week 1: Compaction 触发机制
- [ ] 监控 token 使用量
- [ ] 当接近阈值时触发 Compaction
- [ ] 标记 `compaction_pending` 状态

#### Week 2: LLM 摘要生成
- [ ] 调用 LLM 生成对话摘要
- [ ] 摘要格式标准化
- [ ] 保存摘要到 `memory/YYYY-MM-DD-summary.md`

#### Week 3: 摘要管理
- [ ] 加载时优先读取摘要 + 最近 N 条完整消息
- [ ] 支持摘要的层级合并（日摘要 → 周摘要 → 月摘要）
- [ ] 添加 compaction 计数器

#### Week 4: 向量记忆（可选）
- [ ] 集成本地 embedding 模型
- [ ] 实现语义搜索
- [ ] 添加 `memory_search` 工具

### Phase 4: 父子 Agent 记忆共享 (2周)

#### Week 1: 共享机制
- [ ] 子 Agent 继承父 Agent 的 memory 目录
- [ ] 实现记忆注入功能
- [ ] 子 Agent 结果自动写回

#### Week 2: 优化与测试
- [ ] 避免记忆污染（子 Agent 不修改父 Agent 的核心记忆）
- [ ] 并发子 Agent 的记忆合并策略
- [ ] 性能测试

---

## 6. 关键设计决策

### Q1: 摘要时机？
**方案 A**: 实时 Compaction（到达阈值立即摘要）
- 优点：始终控制上下文大小
- 缺点：可能中断对话流

**方案 B**: 延迟 Compaction（对话结束后批量处理）
- 优点：不影响当前对话
- 缺点：可能临时超出 token 限制

**推荐**: 方案 B + 紧急截断（超过硬限制时强制丢弃旧消息）

### Q2: 父子 Agent 记忆隔离级别？
**方案 A**: 完全共享（子 Agent 可直接修改父记忆）
- 风险：子 Agent 可能污染记忆

**方案 B**: 只读继承 + 写回审核
- 安全但复杂

**方案 C**: 分层写入（子 Agent 写入专用区域，父 Agent 选择性合并）
**推荐**: 方案 C

---

## 7. 配置文件设计

```python
# config/memory.py

MEMORY_CONFIG = {
    # Token 管理
    "max_context_tokens": 8000,
    "reserve_tokens": 2000,
    "recent_rounds_keep": 10,
    
    # Compaction
    "compaction": {
        "enabled": True,
        "threshold_tokens": 6000,  # 超过此值触发
        "summary_model": "gpt-4o-mini",  # 用于摘要的模型
        "min_messages_for_summary": 20,
    },
    
    # 记忆分层
    "memory": {
        "short_term_days": 30,  # 短期记忆保留天数
        "daily_log_enabled": True,
        "vector_search_enabled": False,  # Phase 4 启用
    },
    
    # 子 Agent
    "subagent": {
        "inherit_memory": True,
        "auto_writeback": True,
        "context_injection": True,
    }
}
```

---

## 8. 下一步行动建议

### 本周（立即开始）
1. ✅ MEMORY.md 已更新（当前日期说明）
2. 🔄 开始 Phase 2: Token 计数实现

### 下周
3. 上下文截断策略实现
4. 设计 MEMORY.md 新格式的解析器

### 后续
5. Compaction 机制设计
6. 父子 Agent 记忆共享原型

---

**需要我先提交这份设计文档，然后开始实现 Token 计数功能吗？**
