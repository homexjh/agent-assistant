# AIPC-Agent-One 双模式架构整合计划

## 执行摘要

基于对两个代码库的完整分析，发现 **AIPC-Agent-One 端侧的 Agentic 模式实际上比云端更完善**。端侧已有完整的 Tool-Use Loop、反射机制、Hooks、上下文引擎和 Step Evaluator，而云端只是一个简化版本。

**整合策略调整**：不是用云端替换端侧，而是将云端的**特定功能**（FMS/Git 工具、Skill Security）增强到端侧的现有架构中。

## 1. 架构对比分析

### 1.1 执行模型对比

| 维度 | AIPC-Agent-One (端侧) | aiagent (云端) | 结论 |
|------|----------------------|----------------|------|
| **核心循环** | Tool-Use Loop + Reflection + Hooks | 简单 Tool-Use Loop | 端侧更完善 |
| **并发模型** | asyncio | threading | 端侧更现代 |
| **Subagent** | spawn/yield/steer/kill + 状态管理 | spawn + announce_queue | 端侧功能更全 |
| **Context** | Context Engine (eligibility/compression) | 简单 MEMORY.md 注入 | 端侧更智能 |
| **Memory** | Vector DB + Context Builder | 文件持久化 | 端侧更高级 |
| **Risk Control** | RiskLevel (L0-L3) + Approval | 基础 registry | 端侧更完善 |

### 1.2 Subagent 详细对比

**端侧 SubagentManager** (`src/aipc_agent/modules/agentic_chat/subagent_manager.py`):
- ✅ asyncio 异步架构（FastAPI 友好）
- ✅ SubagentSession 完整状态管理（pending/running/completed/failed/killed）
- ✅ yield_result（阻塞获取结果）
- ✅ steer（向子Agent发送消息）
- ✅ kill（终止子Agent）
- ✅ completion_queue（完成事件收集）
- ✅ timeout 控制（180s）
- ❌ **缺少**: Workspace 隔离
- ❌ **缺少**: Context 注入（从父Agent MEMORY.md）
- ❌ **缺少**: Registry 持久化

**云端 SubagentManager** (`aiagent/subagent.py`):
- ✅ Workspace 隔离（独立目录）
- ✅ Context 注入（从父Agent MEMORY.md 读取）
- ✅ Registry 持久化（JSON 文件）
- ❌ threading 架构（较老）
- ❌ 无状态管理
- ❌ 无 steer/kill

### 1.3 Skill 系统对比

**端侧 Skill 系统** (`src/aipc_agent/modules/skill/`):
- ✅ OpenClaw 格式（SKILL.md + frontmatter）
- ✅ 多源加载（bundled/user/workspace/extra）
- ✅ 运行时过滤（eligibility）
- ✅ 斜杠命令解析（/skillname）
- ❌ **缺少**: 3-tier Security（T1/T2/T3）
- ❌ **缺少**: 描述匹配触发

**云端 Skill 系统** (`aiagent/skills/` + `SKILL_TIER_SYSTEM.md`):
- ✅ 3-tier Security（T1 Protected / T2 User / T3 Session）
- ✅ 描述匹配触发（agent 自动选择 skill）
- ✅ 权限系统（explicit_grant）
- ❌ 无 OpenClaw 格式支持
- ❌ 无 frontmatter

### 1.4 工具系统对比

**端侧已有工具** (40+ 个):
- 文件操作：read, write, edit, dir_scan, file_search, file_organize, file_meta
- 执行：exec, process
- 浏览器：browser_open, browser_act, browser_evaluate, browser_screenshot, browser_snapshot, browser_tabs
- Web：web_search, web_fetch
- 知识库：kb_index, kb_qa, kb_search
- 内存：memory_get, memory_query, memory_search
- 子智能体：subagent_spawn, subagent_control, subagent_yield
- 文档：doc_parse, doc_desensitize, pii_detect
- 定时任务：cron_manage, cron_query
- 其他：text_merge, text_split, export_csv, deliver_report, apply_patch

**云端特有工具**:
- ✅ **FMS 工具**: fms_list_models, fms_model_info, fms_estimate_cost, fms_check_permission, fms_smart_select
- ✅ **Git 工具**: git_read_file, git_list_dir, git_search_files, git_execute
- ✅ **MCP 工具**: mcp_server_run

## 2. 整合方案

### 2.1 Phase 1: Subagent 增强（Week 1）

**目标**: 为端侧 Subagent 添加 Workspace 隔离和 Context 注入

**移植内容**:

```python
# 新增文件: src/aipc_agent/modules/agentic_chat/subagent_workspace.py
# 从云端 aiagent/subagent_workspace.py 移植，适配 asyncio

# 修改: src/aipc_agent/modules/agentic_chat/subagent_manager.py
# 1. 在 _run_wrapper 中创建 workspace
# 2. 在 _run_subagent 中注入 context
# 3. 在 subagent 完成后清理 workspace（按策略）
```

**关键修改点**:
1. `SubagentSession` 添加 `workspace_dir` 字段
2. `_run_wrapper` 调用 workspace 创建/清理
3. `_run_subagent` 从 MEMORY.md 读取并注入 context
4. 可选：`SubagentRegistry` JSON 持久化

### 2.2 Phase 2: 工具移植（Week 1-2）

**目标**: 将云端的 FMS 和 Git 工具移植到端侧

**移植内容**:

```python
# 新增文件: src/aipc_agent/modules/tools/fms_tools.py
# - FmsListModelsTool
# - FmsModelInfoTool  
# - FmsEstimateCostTool
# - FmsCheckPermissionTool
# - FmsSmartSelectTool

# 新增文件: src/aipc_agent/modules/tools/git_tools.py
# - GitReadFileTool
# - GitListDirTool
# - GitSearchFilesTool
# - GitExecuteTool
```

**注意事项**:
- 端侧使用 `NativeTool` 基类
- 需要适配 RiskLevel 和 ToolPolicy
- FMS 工具需要 FMS 服务集成

### 2.3 Phase 3: Skill 安全增强（Week 2）

**目标**: 为端侧 Skill 系统添加 3-tier Security

**移植内容**:

```python
# 新增文件: src/aipc_agent/modules/skill/security.py
# - SkillTier (T1/T2/T3)
# - SkillGuard
# - PermissionStore

# 修改: src/aipc_agent/schemas/skill.py
# 添加 SkillTier 枚举和权限字段

# 修改: src/aipc_agent/modules/skill/frontmatter.py
# 支持解析 security 字段

# 修改: src/aipc_agent/modules/skill/service.py
# - SkillLoaderService 添加权限检查
# - 添加显式授权接口
```

**整合策略**:
- 保留 OpenClaw 格式（SKILL.md + frontmatter）
- 在 frontmatter 中添加 `tier` 和 `permissions` 字段
- T1/T2/T3 权限控制与端侧现有的 approval 机制结合

### 2.4 Phase 4: 描述匹配触发（Week 2-3）

**目标**: 添加云端特有的描述匹配触发机制

**移植内容**:

```python
# 新增文件: src/aipc_agent/modules/skill/matcher.py
# - SkillMatcher（描述相似度匹配）
# - Confidence scoring

# 修改: src/aipc_agent/modules/agentic_chat/service.py
# - 在 tool_use_loop 中添加 skill 匹配步骤
# - 与现有的斜杠命令共存
```

**触发机制**:
- 优先级: 斜杠命令 > 描述匹配 > 普通对话
- 描述匹配阈值可配置（默认 0.8）
- 匹配结果通过 prompt 注入

## 3. 文件映射

### 云端 → 端侧 文件映射

| 云端文件 | 端侧目标文件 | 状态 |
|---------|-------------|------|
| `aiagent/subagent_workspace.py` | `src/aipc_agent/modules/agentic_chat/subagent_workspace.py` | 需移植 |
| `aiagent/subagent_registry.py` | `src/aipc_agent/modules/agentic_chat/subagent_registry.py` | 可选 |
| `aiagent/skills/` | `src/aipc_agent/modules/skill/security.py` | 需适配 |
| `aiagent/tools.py` (FMS/Git) | `src/aipc_agent/modules/tools/fms_tools.py` | 需移植 |
| `aiagent/tools.py` (FMS/Git) | `src/aipc_agent/modules/tools/git_tools.py` | 需移植 |

### 端侧需要修改的文件

| 文件 | 修改内容 |
|------|---------|
| `src/aipc_agent/modules/agentic_chat/subagent_manager.py` | 添加 workspace/context/registry 支持 |
| `src/aipc_agent/modules/agentic_chat/service.py` | 集成 skill matcher |
| `src/aipc_agent/modules/skill/service.py` | 添加 security 检查 |
| `src/aipc_agent/schemas/skill.py` | 添加 tier/permissions 字段 |
| `src/aipc_agent/modules/tools/__init__.py` | 注册新工具 |

## 4. 实施建议

### 4.1 优先级

1. **高优先级**: Subagent Workspace 隔离（影响稳定性）
2. **中优先级**: FMS/Git 工具（功能扩展）
3. **中优先级**: Skill 3-tier Security（安全增强）
4. **低优先级**: 描述匹配触发（用户体验）

### 4.2 测试策略

```python
# 测试文件规划
tests/modules/agentic_chat/test_subagent_workspace.py
tests/modules/tools/test_fms_tools.py
tests/modules/tools/test_git_tools.py
tests/modules/skill/test_security.py
```

### 4.3 风险缓解

| 风险 | 缓解措施 |
|------|---------|
| 破坏现有功能 | 渐进式移植，每阶段完整测试 |
| Skill 格式不兼容 | 保留 OpenClaw 为主，tier 作为可选扩展 |
| FMS 依赖 | 工具加载时检查 FMS 服务可用性 |
| 性能下降 | asyncio 保持，避免 threading |

## 5. 总结

### 关键洞察

1. **端侧架构更先进**: 端侧的 AgenticChatService 比云端更完整，不需要替换
2. **云端价值在功能**: 云端的 Workspace 隔离、FMS/Git 工具、Skill Security 值得移植
3. **整合是增强**: 将云端功能作为端侧的增强，而非架构替换

### 下一步行动

1. 创建子任务分支 `feature/subagent-workspace`
2. 移植 `subagent_workspace.py` 并适配 asyncio
3. 在 `SubagentManager` 中集成 workspace 创建/清理
4. 编写单元测试验证隔离性

---

*计划制定: 2026-03-26*  
*基于代码库: AIPC-Agent-One (端侧) + aiagent (云端)*
