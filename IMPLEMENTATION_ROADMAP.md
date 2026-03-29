# AIPC-Agent-One 整合实施路线图

## 当前状态

**分支**: `dev/run-project` (已验证可运行)  
**基线**: 端侧 AgenticChatService 已完整运行  
**目标**: 渐进式增强，不破坏现有功能

---

## 实施原则

1. **增量开发**: 每个 Phase 独立可交付
2. **向后兼容**: 不破坏现有 API 和行为
3. **测试先行**: 每个功能先有测试，后实现
4. **快速验证**: 每步完成后可立即运行验证

---

## Step 0: 环境准备 (Day 1)

### 0.1 确认基线状态

```bash
cd /Users/emdoor/Documents/projects/AIPC-Agent-One

# 确认当前分支
git branch  # 应在 dev/run-project

# 保存当前工作区（防万一）
git stash

# 确认服务可启动
python -m src.aipc_agent.main  # 或你的启动命令
```

### 0.2 创建功能分支

```bash
# 从 dev/run-project 切出第一阶段分支
git checkout -b feature/subagent-workspace-isolation

# 推送远程（便于协作/备份）
git push -u origin feature/subagent-workspace-isolation
```

### 0.3 测试框架准备

```bash
# 确认测试依赖
pip install pytest pytest-asyncio pytest-aiohttp aioresponses

# 验证现有测试可运行
cd /Users/emdoor/Documents/projects/AIPC-Agent-One
pytest tests/ -v --tb=short -x 2>&1 | head -50
```

**预期结果**: 现有测试通过或明确知道哪些失败

---

## Step 1: Subagent Workspace 隔离 (Week 1)

### Day 1-2: 核心 Workspace 模块

**任务**: 创建 `subagent_workspace.py` 模块

```
新增文件:
src/aipc_agent/modules/agentic_chat/subagent_workspace.py     [新建]
tests/modules/agentic_chat/test_subagent_workspace.py          [新建]
```

**实现顺序**:

1. **先写测试** (TDD)
   ```python
   # tests/modules/agentic_chat/test_subagent_workspace.py
   # 先写 3 个核心测试:
   # - test_create_workspace_success
   # - test_build_context_from_memory  
   # - test_cleanup_archive
   ```

2. **实现功能**
   ```python
   # src/aipc_agent/modules/agentic_chat/subagent_workspace.py
   # 移植云端代码，适配 asyncio:
   # - create_subagent_workspace()
   # - build_context_injection()
   # - cleanup_subagent_workspace()
   ```

3. **本地验证**
   ```bash
   pytest tests/modules/agentic_chat/test_subagent_workspace.py -v
   ```

**交付标准**: 
- ✅ 3 个核心单元测试通过
- ✅ 代码覆盖率 > 80%

---

### Day 3-4: 集成到 SubagentManager

**任务**: 修改 SubagentManager 使用 Workspace

```
修改文件:
src/aipc_agent/modules/agentic_chat/subagent_manager.py        [修改]
tests/modules/agentic_chat/test_subagent_manager_enhanced.py   [新建]
```

**实现顺序**:

1. **修改 SubagentSession 添加 workspace 字段**
   ```python
   @dataclass
   class SubagentSession:
       # ... 现有字段 ...
       workspace_dir: Optional[Path] = None
       cleanup_policy: str = "archive"  # archive/keep/delete
   ```

2. **修改 spawn() 创建 workspace**
   ```python
   async def spawn(self, ...) -> str:
       # ... 现有验证 ...
       
       # 新增: 创建 workspace
       workspace_dir = await create_subagent_workspace(
           subagent_id=sid,
           parent_workspace=self._parent_workspace,
       )
       session.workspace_dir = workspace_dir
   ```

3. **修改 _run_subagent() 注入 context**
   ```python
   async def _run_subagent(self, session: SubagentSession):
       # 新增: 从 workspace 读取 MEMORY.md 注入
       context = await build_context_injection(session.workspace_dir)
       system_prompt = self._build_system_prompt(context)
       # ... 现有逻辑 ...
   ```

4. **修改 kill/完成时清理 workspace**
   ```python
   async def kill(self, target: str) -> str:
       # ... 现有 kill 逻辑 ...
       
       # 新增: 清理 workspace
       if session.workspace_dir:
           await cleanup_subagent_workspace(
               session.workspace_dir, 
               session.cleanup_policy
           )
   ```

5. **写集成测试**
   ```python
   # tests/modules/agentic_chat/test_subagent_manager_enhanced.py
   # - test_spawn_creates_workspace
   # - test_parent_context_injected
   # - test_kill_cleans_workspace
   ```

**本地验证**:
```bash
# 运行新增测试
pytest tests/modules/agentic_chat/test_subagent_manager_enhanced.py -v

# 运行回归测试（确保不破坏现有功能）
pytest tests/modules/agentic_chat/test_subagent*.py -v
```

**交付标准**:
- ✅ 新增集成测试通过
- ✅ 现有 Subagent 相关测试仍通过
- ✅ 手动验证: spawn 一个子Agent，检查 workspace 目录是否创建

---

### Day 5: 回归测试 & 合并

**任务**: 全面验证 & 合并到 dev/run-project

```bash
# 1. 运行所有相关测试
pytest tests/modules/agentic_chat/ -v --tb=short

# 2. 启动服务，手动测试
python -m src.aipc_agent.main
# 在 chat 中测试: "spawn 一个子Agent分析当前目录"

# 3. 合并回 dev/run-project
git checkout dev/run-project
git merge feature/subagent-workspace-isolation
git push origin dev/run-project

# 4. 删除功能分支
git branch -d feature/subagent-workspace-isolation
```

**Checkpoint 1 完成** ✅

---

## Step 2: FMS 工具移植 (Week 2)

### Day 1-2: FMS 客户端 & 基础工具

**任务**: 创建 FMS 工具集

```
新增文件:
src/aipc_agent/modules/tools/fms_client.py              [新建]
src/aipc_agent/modules/tools/fms_list_models_tool.py    [新建]
src/aipc_agent/modules/tools/fms_model_info_tool.py     [新建]
tests/modules/tools/test_fms_tools.py                   [新建]
```

**实现顺序**:

1. **FMS 客户端封装**
   ```python
   # src/aipc_agent/modules/tools/fms_client.py
   class FMSClient:
       async def list_models(self) -> list[ModelInfo]
       async def get_model_info(self, model_id: str) -> ModelInfo
       async def estimate_cost(self, model_id: str, tokens: int) -> CostEstimate
   ```

2. **基础工具实现** (2 个先)
   ```python
   # fms_list_models_tool.py - 简单列表
   # fms_model_info_tool.py - 单个模型详情
   ```

3. **单元测试** (Mock FMS 服务)
   ```python
   # test_fms_list_models_success
   # test_fms_list_models_service_unavailable
   # test_fms_model_info_success
   # test_fms_model_info_not_found
   ```

**本地验证**:
```bash
pytest tests/modules/tools/test_fms_tools.py -v
```

---

### Day 3: 高级 FMS 工具 & 注册

**任务**: 完成剩余 FMS 工具并注册

```
新增文件:
src/aipc_agent/modules/tools/fms_estimate_cost_tool.py   [新建]
src/aipc_agent/modules/tools/fms_smart_select_tool.py    [新建]

修改文件:
src/aipc_agent/modules/tools/__init__.py                 [修改 - 注册工具]
```

**关键步骤**:

1. **实现高级工具**
   ```python
   # fms_estimate_cost_tool.py - 成本估算
   # fms_smart_select_tool.py - 智能模型选择
   ```

2. **注册到工具系统**
   ```python
   # src/aipc_agent/modules/tools/__init__.py
   from .fms_list_models_tool import FmsListModelsTool
   # ... 其他导入
   
   def register_default_tools(registry: ComponentRegistry):
       # ... 现有注册 ...
       registry.register(FmsListModelsTool())
       # ... 注册其他 FMS 工具
   ```

3. **集成测试**
   ```python
   # test_fms_tools_in_agent_loop
   # test_fms_cost_check_before_action
   ```

**本地验证**:
```bash
# 启动服务，测试工具是否可用
python -m src.aipc_agent.main
# 询问 "FMS 有哪些可用模型？"
```

---

### Day 4-5: Git 工具移植

**任务**: 移植 Git 工具集

```
新增文件:
src/aipc_agent/modules/tools/git_read_file_tool.py       [新建]
src/aipc_agent/modules/tools/git_list_dir_tool.py        [新建]
src/aipc_agent/modules/tools/git_search_files_tool.py    [新建]
src/aipc_agent/modules/tools/git_execute_tool.py         [新建]
tests/modules/tools/test_git_tools.py                    [新建]

修改文件:
src/aipc_agent/modules/tools/__init__.py                 [修改 - 注册工具]
```

**安全重点**:
- `git_execute_tool.py` 需要命令白名单
- 路径遍历防护

**本地验证**:
```bash
# 运行 Git 工具测试
pytest tests/modules/tools/test_git_tools.py -v

# 安全测试
pytest tests/modules/tools/test_git_tools.py::TestGitToolSecurity -v
```

**Checkpoint 2 完成** ✅

---

## Step 3: Skill Security 增强 (Week 3)

### Day 1-2: Security 核心模块

**任务**: 实现 3-tier Security 核心

```
新增文件:
src/aipc_agent/modules/skill/security.py                 [新建]
src/aipc_agent/modules/skill/permission_store.py         [新建]
tests/modules/skill/test_security.py                     [新建]

修改文件:
src/aipc_agent/schemas/skill.py                          [修改 - 添加字段]
```

**实现顺序**:

1. **更新 Schema**
   ```python
   # src/aipc_agent/schemas/skill.py
   class SkillTier(Enum):
       T1_PROTECTED = "T1"    # 需要显式授权
       T2_USER = "T2"         # 需要用户确认
       T3_SESSION = "T3"      # 自动批准
   
   class SkillInfo:
       # ... 现有字段 ...
       tier: SkillTier = SkillTier.T3_SESSION
       permissions: list[dict] = field(default_factory=list)
   ```

2. **实现 Security 模块**
   ```python
   # src/aipc_agent/modules/skill/security.py
   class SkillGuard:
       async def check_permission(self, skill: SkillInfo) -> PermissionResult
       async def grant_permission(self, skill_name: str, user_id: str)
       async def revoke_permission(self, skill_name: str, user_id: str)
   ```

3. **权限持久化**
   ```python
   # src/aipc_agent/modules/skill/permission_store.py
   class PermissionStore:
       async def load(self) -> dict
       async def save(self, permissions: dict)
   ```

**本地验证**:
```bash
pytest tests/modules/skill/test_security.py -v
```

---

### Day 3: 集成到 SkillLoader

**任务**: 在加载时解析 security 字段

```
修改文件:
src/aipc_agent/modules/skill/frontmatter.py              [修改 - 解析 tier]
src/aipc_agent/modules/skill/service.py                  [修改 - 权限检查]
tests/modules/skill/test_security_integration.py         [新建]
```

**关键修改**:

1. **Frontmatter 解析 tier**
   ```python
   # src/aipc_agent/modules/skill/frontmatter.py
   def resolve_openclaw_metadata(frontmatter: dict) -> dict:
       # ... 现有解析 ...
       metadata["tier"] = SkillTier(frontmatter.get("tier", "T3"))
       return metadata
   ```

2. **SKILL.md 示例**
   ```markdown
   ---
   name: database_query
   tier: T1
   permissions:
     - scope: database
       actions: [read]
   ---
   
   # Database Query Skill
   ```

3. **Service 层权限检查**
   ```python
   # src/aipc_agent/modules/skill/service.py
   class SkillLoaderService:
       async def execute_skill(self, skill_name: str, ...):
           skill = self.get_by_name(skill_name)
           # 新增: 权限检查
           permission = await self._skill_guard.check_permission(skill)
           if not permission.granted:
               return PermissionRequiredResponse(permission)
           # ... 执行 skill
   ```

---

### Day 4-5: Agent Loop 集成 & 测试

**任务**: 在 AgenticChatService 中集成权限检查

```
修改文件:
src/aipc_agent/modules/agentic_chat/service.py           [修改 - 执行前检查]
tests/modules/agentic_chat/test_skill_security_integration.py  [新建]
```

**回归测试**:
```bash
# 确保无 tier 的旧 skill 仍能运行
pytest tests/modules/skill/test_skill_backward_compatibility.py -v

# 完整 skill 系统测试
pytest tests/modules/skill/ -v
```

**Checkpoint 3 完成** ✅

---

## Step 4: 描述匹配触发 (Week 4)

### Day 1-2: Skill Matcher 核心

**任务**: 实现描述匹配算法

```
新增文件:
src/aipc_agent/modules/skill/matcher.py                  [新建]
src/aipc_agent/modules/skill/embedding_service.py        [新建 - 可选]
tests/modules/skill/test_matcher.py                      [新建]
```

**算法选择** (从简到繁):

方案 A: 关键词匹配 (简单，先实现)
```python
class SkillMatcher:
    def match(self, user_input: str, skills: list[SkillEntry]) -> list[MatchResult]:
        # 使用简单的 TF-IDF 或 BM25
        # 返回置信度 > threshold 的技能列表
```

方案 B: 语义相似度 (后续优化)
```python
# 使用 sentence-transformers 或本地 embedding
# 预先计算 skill 描述的 embedding
# 用户输入实时计算 embedding，余弦相似度匹配
```

**实现顺序**:
1. 先实现方案 A (关键词 + 简单相似度)
2. 写单元测试验证
3. 调优阈值参数

---

### Day 3: 集成到 Agent Loop

**任务**: 在对话中自动匹配 skill

```
修改文件:
src/aipc_agent/modules/agentic_chat/service.py           [修改 - 添加匹配步骤]
tests/modules/agentic_chat/test_skill_matcher_integration.py  [新建]
```

**关键逻辑**:
```python
# src/aipc_agent/modules/agentic_chat/service.py

async def _tool_use_loop(self, ...):
    # ... 现有逻辑 ...
    
    # 新增: 检查是否匹配 skill
    if not self._current_skill:
        matches = await self._skill_matcher.match(
            user_message, 
            self._skill_loader.eligible_skills
        )
        if matches and matches[0].confidence > 0.8:
            # 自动触发 skill
            await self._execute_skill(matches[0].skill)
            return
    
    # ... 继续现有 tool use loop ...
```

**优先级处理**:
```python
# 1. 斜杠命令最高优先级
if message.startswith("/"):
    return self._handle_slash_command(message)

# 2. 描述匹配
matches = self._skill_matcher.match(message)
if matches[0].confidence > threshold:
    return self._execute_skill(matches[0].skill)

# 3. 普通对话处理
return self._handle_normal_chat(message)
```

---

### Day 4-5: 性能优化 & 最终测试

**任务**: 性能测试和最终回归

```bash
# 性能测试
pytest tests/modules/skill/test_matcher_performance.py -v

# 完整回归测试
pytest tests/ -v --tb=short -x

# 手动 E2E 测试
python -m src.aipc_agent.main
# 测试各种场景:
# - 斜杠命令
# - 描述触发 skill
# - 普通对话
# - 子Agent workspace
# - FMS/Git 工具
```

**Checkpoint 4 完成** ✅

---

## 分支管理策略

```
dev/run-project (主开发分支)
│
├── feature/subagent-workspace-isolation  (Week 1)
│   └── 合并后删除
│
├── feature/fms-git-tools                  (Week 2)
│   └── 合并后删除
│
├── feature/skill-security                 (Week 3)
│   └── 合并后删除
│
└── feature/skill-matcher                  (Week 4)
    └── 合并后删除
```

### 每个 Feature 分支的工作流

```bash
# 1. 创建分支
git checkout dev/run-project
git pull origin dev/run-project
git checkout -b feature/xxx

# 2. 开发 + 提交
git add .
git commit -m "feat: xxx - 具体描述"

# 3. 推送
git push origin feature/xxx

# 4. 完成时合并
git checkout dev/run-project
git merge feature/xxx
git push origin dev/run-project

# 5. 清理
git branch -d feature/xxx
git push origin --delete feature/xxx
```

---

## 快速验证清单

### 每个 Step 完成后检查

- [ ] 新增单元测试通过 (`pytest tests/xxx -v`)
- [ ] 相关回归测试通过
- [ ] 服务可正常启动 (`python -m src.aipc_agent.main`)
- [ ] 手动功能验证通过
- [ ] 代码覆盖率未下降 (`pytest --cov`)

### 最终交付检查

- [ ] 所有测试通过 (`pytest tests/ -v`)
- [ ] 子Agent workspace 隔离工作
- [ ] FMS/Git 工具可用
- [ ] Skill security 权限控制有效
- [ ] 描述匹配触发正常工作
- [ ] 文档已更新

---

## 风险应对

| 风险 | 应对措施 |
|------|---------|
| 开发进度延迟 | 每个 Step 可独立交付，延迟不影响已完成功能 |
| 测试发现重大 Bug | 回滚到上一个稳定 commit，重新切分支修复 |
| 与现有功能冲突 | 每步都有回归测试，冲突立即发现 |
| 性能下降 | Day 4-5 专门做性能测试，有问题回滚优化 |

---

## 开始实施

准备好后，执行:

```bash
cd /Users/emdoor/Documents/projects/AIPC-Agent-One

# Step 0: 确认基线
git status  # 确认在 dev/run-project
git log --oneline -3

# Step 0: 创建第一个功能分支
git checkout -b feature/subagent-workspace-isolation

# 开始 Day 1 任务...
```

需要我开始实施 **Step 1 Day 1** 的代码吗？
