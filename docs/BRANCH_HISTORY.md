# 分支历史与提交记录

> 记录项目所有分支的创建、合并、提交历史
> 最后更新: 2026-03-25 (master 已合并最新功能)

---

## 📊 分支关系总览

```
master (4c417fb) ← **当前最新** (已添加错误标准化方案)
  │
  ├── fix/browser-snapshot-tab-20260325 (f54da48) ← **已合并**到 master
  │     ├── fix: snapshot 崩溃 + 标签页切换
  │     ├── fix: 移除重复 global 声明
  │     ├── fix: 点击后自动切换新标签页
  │     └── fix: 局部变量同步问题
  │
  ├── feature/todo-list-20260318 (84778f0) ← 已合并到 master
  │     │  (包含: Skill 安全分层 + Web UI 技能向导 + README 重写)
  │     │
  │     ├── merge: 用户画像分离与安全上下文注入 (22b2a7b)
  │     │
  │     ├── feature/memory-week1-20260319 (51b8826)
  │     │     └── fix: 修复 'NoneType' object is not iterable 错误
  │     │
  │     ├── feature/subagent-isolation-20260319 (2287b9c)
  │     │     └── fix: 子 Agent 文件创建到错误目录的问题
  │     │
  │     ├── feature/server-session-20260318 (d5b7124)
  │     │     └── fix: 修复刷新后无法加载会话的问题
  │     │
  │     └── feature/session-level-summary-20260323 (0d6279e) ← 会话级别摘要（开发中）
  │           ├── fix: 删除旧的请求级别摘要逻辑
  │           ├── fix: 前端使用 sid 作为 rid
  │           └── feat: 实现 SessionManager 会话级别摘要
  │
  ├── feature/skill-security-tier-20260324 (92d9433) ← **已合并**到 feature/todo-list-20260318
  │     ├── feat: Phase 1 - Skill 安全分层基础实施
  │     ├── feat: Phase 2 - 添加 research skill 和测试
  │     ├── feat: Phase 2 - 添加 find-skills skill 和测试
  │     ├── feat: add skill management panel to Web UI
  │     ├── feat: enhance skill panel with empty state UX
  │     ├── feat: add visual skill creation wizard
  │     └── merge: 合并到 feature/todo-list-20260318 (ded74e2)
  │
  └── feature/memory-struct-20260320 (aac4adc) ← **已合并**到 feature/todo-list-20260318
        ├── aac4adc feat: Daily Log 自动摘要功能 + Skill 安全计划文档
        ├── daf1b05 docs: Add Phase 5 implementation report
        ├── 6481e2b docs: Update memory system design doc for Phase 5 completion
        ├── 21c7d0c feat: Auto-generate conversation summary for long dialogues (>5 rounds)
        ├── 05defa6 fix: Add missing Path import in agent.py
        ├── de2790e fix: Memory tools definition format and add list_keys method
        └── 92d3bac feat: Week 2-3 - Memory tools and daily log system
```

---

## 📝 详细提交记录

### master 分支

| 提交 | 日期 | 说明 |
|------|------|------|
| c4c14c4 | 2026-03-25 | **merge**: 合并 feature/todo-list-20260318 (Skill 安全分层 + README 更新) |
| 9fbd374 | 2026-03-16 | feat: 添加任务列表（Todo List）功能 |

**状态**: ✅ **最新稳定版本**，包含所有 Phase 5 功能

**包含功能**:
- ✅ Todo List 任务管理
- ✅ 用户画像分离 (USER.md / MEMORY.md)
- ✅ 子 Agent Workspace 隔离
- ✅ Daily Log 自动摘要
- ✅ **Skill 三级安全架构** (system/user/market)
- ✅ **Web UI 技能管理面板 + 创建向导**
- ✅ **4阶段研究能力** (research skill)
- ✅ **代码安全扫描器**
- ✅ **重写 README 文档**

---

### feature/todo-list-20260318 (主开发分支)

| 提交 | 日期 | 作者 | 说明 | 变更文件 |
|------|------|------|------|----------|
| 22b2a7b | 2026-03-18 | emdoor | **merge**: 用户画像分离与安全上下文注入 | - |
| 9c83b06 | 2026-03-18 | emdoor | feat: Week 1 - 用户画像分离与安全上下文注入 | `aiagent/subagent_workspace.py`, `aiagent/agent.py`, `workspace/MEMORY.md`, `workspace/USER.md` |
| 74d248a | 2026-03-18 | emdoor | docs: 更新设计文档 v1.1 - Phase 5 详细实施计划 | `docs/memory-design.md` |
| f1fdf3c | 2026-03-18 | emdoor | docs: 更新记忆系统设计文档 v1.1 | `docs/memory-design.md` |
| 3aca797 | 2026-03-17 | emdoor | **merge**: 子 Agent Workspace 隔离功能 | - |

**状态**: 当前主开发分支，已合并多个子功能

**包含功能**:
- ✅ Todo List 任务管理
- ✅ 用户画像分离 (USER.md / MEMORY.md)
- ✅ 子 Agent Workspace 隔离
- ✅ SubAgent 安全上下文注入
- ✅ **Daily Log 自动摘要** (合并自 feature/memory-struct-20260320)
- ✅ **Skill 安全分层 + Web UI 技能管理** (合并自 feature/skill-security-tier-20260324)

**合并记录**:
| 日期 | 合并来源 | 合并提交 | 说明 |
|------|----------|----------|------|
| 2026-03-25 | feature/todo-list-20260318 → master | c4c14c4 | **大合并**: 所有 Phase 5 功能 + README 重写 |
| 2026-03-25 | feature/skill-security-tier-20260324 | ded74e2 | Skill 安全分层 + Web UI 技能向导 |

---

### feature/memory-struct-20260320 (Phase 5 完整实现 + Daily Log 优化)

基于: `feature/todo-list-20260318` (22b2a7b)

| 提交 | 日期 | 作者 | 类型 | 说明 | 主要变更 |
|------|------|------|------|------|----------|
| aac4adc | 2026-03-23 | emdoor | feat | **Daily Log 自动摘要功能完整实现** | `aiagent/serve.py` (+250 行), `docs/` (+800 行) |
| daf1b05 | 2026-03-20 | emdoor | docs | Add Phase 5 implementation report | `PHASE5_IMPLEMENTATION_REPORT.md` (+146 行) |
| 6481e2b | 2026-03-20 | emdoor | docs | Update memory system design doc | `docs/memory-design.md` (+97/-17) |
| 21c7d0c | 2026-03-20 | emdoor | feat | Auto-generate conversation summary | `aiagent/agent.py` (摘要生成逻辑) |
| 05defa6 | 2026-03-20 | emdoor | fix | Add missing Path import | `aiagent/agent.py` (+1 行) |
| de2790e | 2026-03-20 | emdoor | fix | Memory tools definition format | `aiagent/tools/memory.py` (工具定义格式) |
| 92d3bac | 2026-03-20 | emdoor | feat | Week 2-3 - Memory tools and daily log | 6 个文件, +1001/-26 行 |

**新增文件**:
- `aiagent/memory_manager.py` (307 行) - Memory 管理器
- `aiagent/daily_log.py` (220 行) - 每日日志管理
- `aiagent/tools/daily_log.py` (175 行) - Daily Log 工具
- `MEMORY_SYSTEM_USAGE.md` (172 行) - 使用文档
- `PHASE5_IMPLEMENTATION_REPORT.md` (146 行) - 实施报告
- `PHASE5_WEEK4_SKILL_SECURITY_PLAN.md` (200+ 行) - Skill 安全计划
- `BRANCH_HISTORY.md` (300+ 行) - 分支历史记录
- `test_memory_system.py` (239 行) - 测试文件

**修改文件**:
- `aiagent/agent.py` (+119/-17) - 集成 Memory 和 Daily Log
- `aiagent/serve.py` (+250/-50) - 添加 _generate_conversation_summary
- `aiagent/memory_manager.py` (+1/-0) - 修复 update_system_date 保存问题
- `aiagent/tools/__init__.py` (+20/-3) - 注册新工具
- `aiagent/tools/memory.py` (+312/-26) - 扩展 Memory 工具
- `docs/memory-design.md` (+97/-17) - 更新设计文档
- `.env` (+5/-0) - 添加 DAILY_LOG_SUMMARY_MODE 配置

**状态**: Daily Log 功能完整实现，**已合并**到 `feature/todo-list-20260318` (2026-03-23)

**包含功能**:
- ✅ MemoryManager 结构化读写
- ✅ memory_get/set/list 工具
- ✅ Daily Log 自动创建和管理
- ✅ daily_log_create/append/get/list 工具
- ✅ 对话 >5 轮自动摘要
- ✅ 自动更新 System.current_date

---

### 已合并的子分支

#### feature/memory-week1-20260319
- **合并到**: `feature/todo-list-20260318`
- **提交**: 51b8826 fix: 修复 'NoneType' object is not iterable 错误
- **状态**: 已合并，可删除

#### feature/subagent-isolation-20260319
- **合并到**: `feature/todo-list-20260318`
- **提交**: 2287b9c fix: 子 Agent 文件创建到错误目录的问题
- **状态**: 已合并，可删除

#### feature/server-session-20260318
- **合并到**: `feature/todo-list-20260318`
- **提交**: d5b7124 fix: 修复刷新后无法加载会话的问题，添加缺失的 scrollToBottom 函数
- **状态**: 已合并，可删除

#### feature/session-level-summary-20260323
- **基于**: `feature/todo-list-20260318`
- **目的**: 实现会话级别 Daily Log 总结（方案B）
- **主要提交**:
  - `0d6279e` fix: 删除旧的请求级别摘要逻辑
  - `9e41d18` fix: 前端使用 sid 作为 rid
  - `9f2b740` fix: datetime 作用域问题
  - `2b385f2` fix: session_id 被覆盖
  - `a582fe2` fix: Path 未导入
  - `b08a06f` feat: 实现 SessionManager
- **Bug 修复**: 6个（详见 SESSION_SUMMARY_IMPLEMENTATION_REPORT.md）
- **状态**: 已实现并测试通过，待合并

---

## 🔄 合并历史

| 日期 | 目标分支 | 源分支 | 合并提交 | 说明 |
|------|----------|--------|----------|------|
| 2026-03-23 | feature/todo-list-20260318 | feature/memory-struct-20260320 | 9498bf1 | **大合并**: Daily Log 完整功能 + Skill 安全计划 |
| 2026-03-18 | feature/todo-list-20260318 | feature/memory-week1-20260319 | 22b2a7b | 合并 Week 1 修复 |
| 2026-03-18 | feature/todo-list-20260318 | feature/subagent-isolation-20260319 | 22b2a7b | 合并子 Agent 隔离修复 |
| 2026-03-18 | feature/todo-list-20260318 | (多个子分支) | 22b2a7b | 大合并：用户画像分离 |
| 2026-03-17 | feature/todo-list-20260318 | (子 Agent 功能) | 3aca797 | 合并子 Agent Workspace 隔离 |

---

## 📁 文件变更统计

### feature/memory-struct-20260320 相比 feature/todo-list-20260318

```
新增文件:
  aiagent/daily_log.py              | 220 +++++++
  aiagent/memory_manager.py         | 307 ++++++++++
  aiagent/tools/daily_log.py        | 175 ++++++
  MEMORY_SYSTEM_USAGE.md            | 172 ++++++
  PHASE5_IMPLEMENTATION_REPORT.md   | 146 +++++
  test_memory_system.py             | 239 +++++++++

修改文件:
  aiagent/agent.py                  | 119 +++++
  aiagent/tools/__init__.py        |  20 +
  aiagent/tools/memory.py          | 312 +++++++++-
  docs/memory-design.md            |  97 +++-

总计: 6 新增, 4 修改, ~1800 行变更
```

---

## 🎯 当前状态

### ✅ 已完成：Phase 5 - Skill 安全分层

**分支**: `feature/skill-security-tier-20260324`

**状态**: **已完成，可合并**

**基于**: `feature/todo-list-20260318` (已包含 Daily Log + Memory + Session)

**实施内容** (参考 PHASE5_IMPLEMENTATION_PLAN.md + SKILL_SECURITY_TIER_IMPLEMENTATION.md):

#### Phase 1: 安全基础 ✅
- [x] 目录结构调整 (skills/{system,user,market}/)
- [x] skill_security.py (危险代码扫描)
- [x] skills.py 三级扫描 + 分组显示
- [x] 12个技能迁移到 system/

#### Phase 2: 核心技能补充 ✅
- [x] research skill (4阶段研究方法论)
- [x] find-skills skill (技能发现与管理)
- [x] 测试覆盖 (20个测试全部通过)

**新增技能 (14个总计):**
```
System Skills:
  - coding-agent, gh-issues, github, nano-pdf, obsidian
  - peekaboo, session-logs, skill-creator, summarize
  - tmux, weather, xurl
  - research ⭐ (新增)
  - find-skills ⭐ (新增)
```

**测试验证:**
- ✅ 20个单元测试全部通过
- ✅ Web UI 实测验证通过 (research skill)
- ✅ 安全扫描检测危险代码

**文档:**
- `docs/PHASE5_IMPLEMENTATION_PLAN.md` - 实施计划
- `docs/SKILL_SECURITY_TIER_IMPLEMENTATION.md` - 详细报告
- `docs/DEERFLOW_SKILL_ANALYSIS.md` - 竞品分析

---

## 🎯 历史合并记录

---

## 🔄 进行中分支

### fix/browser-snapshot-tab-20260325 ✅ 已合并
- **目的**: 修复浏览器工具的两个问题
- **基于**: `master` (efb4c08)
- **修复内容**:
  1. ✅ 修复 snapshot 递归函数崩溃（nodeType 检查）
  2. ✅ 添加 switch_tab action 支持标签页切换
  3. ✅ click 后自动切换到新标签页
  4. ✅ 修复局部变量未同步问题
- **状态**: **已合并到 master** (2cc7f08 + e0fc806, 2026-03-25)

---

## 🗑️ 可清理分支

以下分支已合并到 master，可删除:
- `fix/browser-snapshot-tab-20260325` ✅ **已合并到 master (e0fc806)**
- `feature/todo-list-20260318` ✅ **已合并到 master (c4c14c4)**
- `feature/memory-struct-20260320` ✅ 已合并
- `feature/skill-security-tier-20260324` ✅ 已合并
- `feature/memory-week1-20260319`
- `feature/subagent-isolation-20260319`
- `feature/server-session-20260318`

```bash
# 删除已合并分支
git branch -d fix/browser-snapshot-tab-20260325
git branch -d feature/todo-list-20260318
git branch -d feature/memory-struct-20260320
git branch -d feature/skill-security-tier-20260324
git branch -d feature/memory-week1-20260319
git branch -d feature/subagent-isolation-20260319
git branch -d feature/server-session-20260318
```

---

## 📝 更新记录

| 日期 | 更新内容 | 更新人 |
|------|----------|--------|
| 2026-03-26 | 完成: feature/error-standardization-20260326 实施（3阶段+26测试） | Kimi |
| 2026-03-26 | 文档: 添加错误标准化与资源管理对接方案 | Kimi |
| 2026-03-25 | 清理: 删除根目录过时规划文档 (6个文件) | Kimi |
| 2026-03-25 | 合并: fix/browser-snapshot-tab-20260325 → master | Kimi |
| 2026-03-25 | 添加: fix/browser-snapshot-tab-20260325 修复分支记录 | Kimi |
| 2026-03-25 | 更新: master 已合并 feature/todo-list-20260318，添加 README 更新记录 | Kimi |
| 2026-03-22 | 创建文档，记录所有分支历史 | Kimi |
