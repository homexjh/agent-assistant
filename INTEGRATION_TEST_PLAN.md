# AIPC-Agent-One 双模式整合测试计划

## 测试策略概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        测试金字塔                                │
├─────────────────────────────────────────────────────────────────┤
│  🎯 E2E 测试 (5%)  - 完整用户场景验证                            │
│     └── 子Agent完整生命周期 / Skill触发 / 工具链                  │
├─────────────────────────────────────────────────────────────────┤
│  🔗 集成测试 (25%) - 模块间交互验证                               │
│     └── Subagent+Workspace / Tool+Registry / Skill+Security     │
├─────────────────────────────────────────────────────────────────┤
│  🧪 单元测试 (70%) - 核心逻辑验证                                 │
│     └── 每个新增/修改函数的独立测试                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Subagent Workspace 隔离测试

### 1.1 单元测试

#### `test_subagent_workspace.py`

```python
# 测试目标: subagent_workspace.py 的核心函数

class TestWorkspaceCreation:
    """测试工作空间创建"""
    
    async def test_create_workspace_success(self):
        """TC-W01: 正常创建工作空间"""
        # Given: 有效的 subagent_id 和 parent_workspace
        # When: 调用 create_subagent_workspace()
        # Then: 返回 workspace 路径，目录存在，包含标准结构
        
    async def test_create_workspace_nested(self):
        """TC-W02: 嵌套子Agent工作空间"""
        # Given: parent_workspace 本身是一个子Agent的 workspace
        # When: 创建孙Agent的 workspace
        # Then: 路径正确嵌套，不冲突
        
    async def test_create_workspace_permissions(self):
        """TC-W03: 工作空间权限设置"""
        # Given: 新创建的 workspace
        # When: 检查目录权限
        # Then: 权限为 0o700 (仅所有者可读写执行)

class TestContextInjection:
    """测试上下文注入"""
    
    async def test_build_context_from_memory(self):
        """TC-C01: 从 MEMORY.md 构建上下文"""
        # Given: 包含关键信息的 MEMORY.md
        # When: 调用 build_context_injection()
        # Then: 返回格式化的 context 字符串
        
    async def test_build_context_missing_memory(self):
        """TC-C02: MEMORY.md 不存在时的降级"""
        # Given: 没有 MEMORY.md 的 workspace
        # When: 调用 build_context_injection()
        # Then: 返回空字符串或默认上下文，不报错
        
    async def test_context_fields_filter(self):
        """TC-C03: 指定字段过滤"""
        # Given: context_fields = ["goal", "constraints"]
        # When: 构建上下文
        # Then: 仅包含指定字段的内容

class TestWorkspaceCleanup:
    """测试工作空间清理"""
    
    async def test_cleanup_archive(self):
        """TC-L01: 归档策略"""
        # Given: 策略为 "archive"
        # When: 调用 cleanup_subagent_workspace()
        # Then: workspace 移动到 archive/ 目录，保留文件
        
    async def test_cleanup_delete(self):
        """TC-L02: 删除策略"""
        # Given: 策略为 "delete"
        # When: 调用 cleanup_subagent_workspace()
        # Then: workspace 完全删除
        
    async def test_cleanup_keep(self):
        """TC-L03: 保留策略"""
        # Given: 策略为 "keep"
        # When: 调用 cleanup_subagent_workspace()
        # Then: workspace 保持不变
```

#### `test_subagent_manager_enhanced.py`

```python
# 测试目标: 增强后的 SubagentManager

class TestSubagentManagerWorkspace:
    """测试 SubagentManager 的 Workspace 集成"""
    
    async def test_spawn_creates_workspace(self):
        """TC-SM01: spawn 自动创建工作空间"""
        # Given: 初始化的 SubagentManager
        # When: 调用 spawn()
        # Then: SubagentSession.workspace_dir 不为空，目录存在
        
    async def test_session_tracks_workspace(self):
        """TC-SM02: Session 跟踪工作空间状态"""
        # Given: 已创建的 subagent
        # When: 查询 session
        # Then: session 包含 workspace_dir 和 cleanup_policy
        
    async def test_yield_includes_workspace_info(self):
        """TC-SM03: yield_result 返回工作空间路径"""
        # Given: 完成的 subagent
        # When: 调用 yield_result()
        # Then: 结果包含 workspace 路径供父Agent访问

class TestContextPropagation:
    """测试上下文传播"""
    
    async def test_parent_context_injected(self):
        """TC-CP01: 父Agent上下文注入子Agent"""
        # Given: 父Agent有 MEMORY.md
        # When: spawn 子Agent
        # Then: 子Agent的 system prompt 包含父上下文
        
    async def test_context_hint_merged(self):
        """TC-CP02: context_hint 与 MEMORY 合并"""
        # Given: spawn 时提供 context_hint
        # When: 子Agent启动
        # Then: system prompt 同时包含 MEMORY 和 context_hint
```

### 1.2 集成测试

#### `test_subagent_workspace_integration.py`

```python
class TestSubagentWorkspaceLifecycle:
    """测试完整生命周期"""
    
    async def test_full_lifecycle_archive(self):
        """TC-I01: 完整生命周期 - 归档策略"""
        # Steps:
        # 1. 父Agent创建 workspace
        # 2. 父Agent spawn 子Agent（自动创建子 workspace）
        # 3. 子Agent写入文件到 workspace
        # 4. 子Agent完成
        # 5. 父Agent yield_result
        # 6. 验证子 workspace 归档到 archive/ 目录
        
    async def test_nested_subagents_workspace(self):
        """TC-I02: 嵌套子Agent工作空间隔离"""
        # Steps:
        # 1. 祖父Agent spawn 父Agent
        # 2. 父Agent spawn 子Agent
        # 3. 验证三个 workspace 层级正确
        # 4. 验证每个 workspace 互相隔离
        
    async def test_workspace_persistence_across_steers(self):
        """TC-I03: steer 操作间工作空间持久化"""
        # Steps:
        # 1. spawn 子Agent
        # 2. 子Agent写入文件
        # 3. steer 发送新指令
        # 4. 验证子Agent能读取之前写入的文件
```

### 1.3 回归测试

```python
class TestSubagentBackwardCompatibility:
    """确保现有功能不受影响"""
    
    async def test_existing_spawn_without_workspace(self):
        """TC-R01: 无 workspace 参数时行为不变"""
        # 验证: 不提供 workspace_dir 时，subagent 仍能正常运行
        
    async def test_concurrent_subagents(self):
        """TC-R02: 并发子Agent不受影响"""
        # 验证: 同时运行3个子Agent，都能正确管理 workspace
        
    async def test_kill_cleans_workspace(self):
        """TC-R03: kill 时清理工作空间"""
        # 验证: kill subagent 时，根据策略清理 workspace
```

### 1.4 E2E 测试场景

```yaml
# test_e2e_subagent_workspace.yml

Scenario: 子Agent独立完成文件分析任务
  Given: 用户在父Agent中要求分析代码库
  When: 
    - 父Agent spawn "分析 src/ 目录结构" 子Agent
    - 子Agent在独立 workspace 中执行 dir_scan
    - 子Agent生成分析报告到 workspace/report.md
    - 子Agent完成，父Agent yield_result
  Then:
    - 子Agent workspace 按策略归档
    - 父Agent能访问 report.md 内容
    - 子Agent的临时文件不影响父Agent workspace

Scenario: 嵌套子Agent处理复杂任务
  Given: 用户要求调研并生成报告
  When:
    - 父Agent spawn "调研主题" 子Agent
    - 子Agent spawn "搜索网络资源" 孙Agent
    - 孙Agent spawn "提取关键信息" 曾孙Agent
  Then:
    - 每个Agent有独立的 workspace
    - 信息通过 context 逐层传递
    - 所有 workspace 按策略清理
```

---

## Phase 2: FMS/Git 工具测试

### 2.1 单元测试

#### `test_fms_tools.py`

```python
class TestFmsListModelsTool:
    """测试 FMS 模型列表工具"""
    
    async def test_list_models_success(self, mock_fms_client):
        """TC-F01: 正常获取模型列表"""
        # Given: FMS 服务可用，有多个模型
        # When: 调用 fms_list_models
        # Then: 返回模型列表，包含名称、提供商、能力
        
    async def test_list_models_service_unavailable(self):
        """TC-F02: FMS 服务不可用"""
        # Given: FMS 服务连接失败
        # When: 调用工具
        # Then: 返回友好的错误信息，建议检查配置
        
    async def test_list_models_empty(self):
        """TC-F03: 无可用模型"""
        # Given: FMS 服务正常但无模型
        # When: 调用工具
        # Then: 返回空列表提示

class TestFmsEstimateCostTool:
    """测试成本估算工具"""
    
    async def test_estimate_cost_success(self):
        """TC-F04: 正常估算成本"""
        # Given: 输入 token 数、模型 ID
        # When: 调用 estimate_cost
        # Then: 返回预估成本和货币单位
        
    async def test_estimate_cost_invalid_model(self):
        """TC-F05: 无效模型ID"""
        # Given: 不存在的模型 ID
        # When: 调用工具
        # Then: 返回错误，建议可用模型

class TestFmsSmartSelectTool:
    """测试智能模型选择"""
    
    async def test_smart_select_by_task_type(self):
        """TC-F06: 按任务类型选择"""
        # Given: task_type="code_generation"
        # When: 调用 smart_select
        # Then: 返回适合代码生成的模型
        
    async def test_smart_select_with_constraints(self):
        """TC-F07: 带约束条件选择"""
        # Given: max_latency="low", max_cost="medium"
        # When: 调用 smart_select
        # Then: 返回满足约束的模型
```

#### `test_git_tools.py`

```python
class TestGitReadFileTool:
    """测试 Git 文件读取"""
    
    async def test_read_file_success(self, mock_git_repo):
        """TC-G01: 正常读取文件"""
        # Given: 有效的 repo_path 和 file_path
        # When: 调用 git_read_file
        # Then: 返回文件内容和元数据
        
    async def test_read_file_with_ref(self):
        """TC-G02: 读取特定分支/提交的文件"""
        # Given: ref="feature-branch"
        # When: 调用工具
        # Then: 返回该分支上的文件内容
        
    async def test_read_file_not_found(self):
        """TC-G03: 文件不存在"""
        # Given: 不存在的 file_path
        # When: 调用工具
        # Then: 返回 404 错误，建议相似文件
        
    async def test_read_file_binary(self):
        """TC-G04: 二进制文件处理"""
        # Given: 二进制文件路径
        # When: 调用工具
        # Then: 返回 base64 编码或提示无法显示

class TestGitSearchFilesTool:
    """测试 Git 文件搜索"""
    
    async def test_search_by_name(self):
        """TC-G05: 按文件名搜索"""
        # Given: pattern="*.py"
        # When: 调用 git_search_files
        # Then: 返回匹配的 Python 文件列表
        
    async def test_search_by_content(self):
        """TC-G06: 按内容搜索"""
        # Given: content="TODO", path="src/"
        # When: 调用工具
        # Then: 返回包含 "TODO" 的文件
        
    async def test_search_case_sensitive(self):
        """TC-G07: 大小写敏感搜索"""
        # Given: pattern="ClassName", case_sensitive=true
        # When: 调用工具
        # Then: 仅返回精确匹配

class TestGitExecuteTool:
    """测试 Git 命令执行"""
    
    async def test_execute_git_log(self):
        """TC-G08: 执行 git log"""
        # Given: command="log --oneline -10"
        # When: 调用 git_execute
        # Then: 返回最近10条提交
        
    async def test_execute_forbidden_command(self):
        """TC-G09: 禁止危险命令"""
        # Given: command="push --force"
        # When: 调用工具
        # Then: 拒绝执行，返回安全警告
        
    async def test_execute_invalid_git_command(self):
        """TC-G10: 无效 git 命令"""
        # Given: command="invalid-cmd"
        # When: 调用工具
        # Then: 返回 git 错误输出
```

### 2.2 集成测试

```python
class TestFmsToolIntegration:
    """FMS 工具与 AgenticChatService 集成"""
    
    async def test_fms_tools_in_agent_loop(self):
        """TC-FI01: Agent 循环中使用 FMS 工具"""
        # Steps:
        # 1. 用户询问 "哪个模型最适合代码生成？"
        # 2. Agent 调用 fms_smart_select
        # 3. Agent 基于结果回答
        
    async def test_fms_cost_check_before_action(self):
        """TC-FI02: 行动前检查成本"""
        # Steps:
        # 1. 用户要求 "分析这个大型代码库"
        # 2. Agent 调用 fms_estimate_cost
        # 3. Agent 询问用户确认后再执行

class TestGitToolIntegration:
    """Git 工具与 AgenticChatService 集成"""
    
    async def test_git_tools_for_code_review(self):
        """TC-GI01: 使用 Git 工具进行代码审查"""
        # Steps:
        # 1. 用户要求 "审查这个 PR 的修改"
        # 2. Agent 调用 git_execute 获取 diff
        # 3. Agent 调用 git_read_file 读取相关文件
        # 4. Agent 生成审查报告
        
    async def test_git_search_for_context(self):
        """TC-GI02: 搜索代码获取上下文"""
        # Steps:
        # 1. 用户询问 "这个函数在哪里定义的？"
        # 2. Agent 调用 git_search_files
        # 3. Agent 读取找到的文件并回答
```

### 2.3 安全测试

```python
class TestGitToolSecurity:
    """Git 工具安全测试"""
    
    async def test_path_traversal_protection(self):
        """TC-GS01: 路径遍历防护"""
        # Given: file_path="../../../etc/passwd"
        # When: 调用 git_read_file
        # Then: 拒绝访问，记录安全事件
        
    async def test_command_injection_protection(self):
        """TC-GS02: 命令注入防护"""
        # Given: command="log; rm -rf /"
        # When: 调用 git_execute
        # Then: 拒绝执行，警告恶意命令
        
    async def test_repo_path_validation(self):
        """TC-GS03: 仓库路径验证"""
        # Given: repo_path="/not/a/git/repo"
        # When: 调用工具
        # Then: 返回错误，验证路径有效性
```

---

## Phase 3: Skill Security 测试

### 3.1 单元测试

#### `test_skill_security.py`

```python
class TestSkillTier:
    """测试技能层级"""
    
    def test_t1_protected_requires_explicit_grant(self):
        """TC-ST01: T1 需要显式授权"""
        # Given: T1 skill (数据库操作)
        # When: 首次尝试执行
        # Then: 暂停并请求用户授权
        
    def test_t2_user_requires_user_confirmation(self):
        """TC-ST02: T2 需要用户确认"""
        # Given: T2 skill (文件写入)
        # When: 执行时
        # Then: 提示用户确认
        
    def test_t3_session_auto_approved(self):
        """TC-ST03: T3 自动批准"""
        # Given: T3 skill (网络搜索)
        # When: 执行时
        # Then: 直接执行，无需确认

class TestSkillGuard:
    """测试技能守卫"""
    
    async def test_check_permission_t1_not_granted(self):
        """TC-SG01: T1 未授权时拒绝"""
        # Given: 用户未授权 T1 skill
        # When: SkillGuard.check_permission()
        # Then: 返回 denied，提供授权指引
        
    async def test_grant_permission_t1(self):
        """TC-SG02: 授权 T1 skill"""
        # Given: 用户确认授权
        # When: SkillGuard.grant_permission()
        # Then: 权限持久化，下次自动通过
        
    async def test_revoke_permission(self):
        """TC-SG03: 撤销授权"""
        # Given: 已授权的 T1 skill
        # When: 用户撤销授权
        # Then: 下次执行需重新授权
        
    async def test_session_temp_grant(self):
        """TC-SG04: 会话级临时授权"""
        # Given: T3 skill
        # When: 首次执行
        # Then: 自动授权，仅当前会话有效

class TestPermissionStore:
    """测试权限存储"""
    
    async def test_persist_granted_permissions(self):
        """TC-SP01: 持久化已授权权限"""
        # Given: 用户授权 skill_A
        # When: 重启服务
        # Then: 授权状态保持不变
        
    async def test_list_user_permissions(self):
        """TC-SP02: 列出用户权限"""
        # Given: 用户有多个授权
        # When: 调用 list_permissions()
        # Then: 返回所有授权的技能和时间戳
```

### 3.2 集成测试

```python
class TestSkillSecurityIntegration:
    """Skill Security 与现有系统集成"""
    
    async def test_security_with_skill_loader(self):
        """TC-SSI01: SkillLoader 加载时解析 tier"""
        # Steps:
        # 1. SKILL.md 包含 `tier: T1` frontmatter
        # 2. SkillLoaderService.load_all()
        # 3. 验证 SkillEntry 包含 tier 信息
        
    async def test_security_with_agent_loop(self):
        """TC-SSI02: Agent 循环中执行权限检查"""
        # Steps:
        # 1. Agent 决定执行 T1 skill
        # 2. 调用前检查权限
        # 3. 未授权时暂停并请求用户
        # 4. 用户授权后继续执行
        
    async def test_security_with_frontmatter(self):
        """TC-SSI03: frontmatter 安全字段解析"""
        # Given SKILL.md:
        # ---
        # name: database_query
        # tier: T1
        # permissions:
        #   - scope: database
        #     actions: [read, write]
        # ---
        # When: 解析 frontmatter
        # Then: 正确提取 tier 和 permissions
```

### 3.3 回归测试

```python
class TestSkillBackwardCompatibility:
    """确保无 tier 的技能正常工作"""
    
    async def test_skill_without_tier_defaults_t3(self):
        """TC-SR01: 无 tier 默认 T3"""
        # Given: 旧 SKILL.md 无 tier 字段
        # When: 加载并执行
        # Then: 视为 T3，自动执行
        
    async def test_existing_skill_commands(self):
        """TC-SR02: 斜杠命令不受 security 影响"""
        # Given: 用户输入 /skillname
        # When: 解析命令
        # Then: 行为与之前一致
```

---

## Phase 4: 描述匹配触发测试

### 4.1 单元测试

#### `test_skill_matcher.py`

```python
class TestSkillMatcher:
    """测试技能匹配器"""
    
    async def test_match_by_description_exact(self):
        """TC-M01: 精确描述匹配"""
        # Given: 用户输入 "分析代码复杂度"
        # Given: skill 描述 "分析代码复杂度并提供改进建议"
        # When: 调用 match()
        # Then: 高置信度匹配 (>0.9)
        
    async def test_match_by_description_similar(self):
        """TC-M02: 相似描述匹配"""
        # Given: 用户输入 "帮我看看这段代码"
        # Given: skill 描述 "代码审查和分析"
        # When: 调用 match()
        # Then: 中等置信度匹配 (0.7-0.9)
        
    async def test_match_no_skill_matches(self):
        """TC-M03: 无匹配技能"""
        # Given: 用户输入 "今天天气如何"
        # Given: 所有 skill 都与代码相关
        # When: 调用 match()
        # Then: 返回空列表或低置信度
        
    async def test_match_multiple_skills(self):
        """TC-M04: 多个技能匹配"""
        # Given: 模糊输入 "处理文件"
        # Given: 多个文件相关 skill
        # When: 调用 match()
        # Then: 返回按置信度排序的列表
        
    async def test_match_below_threshold(self):
        """TC-M05: 低于阈值过滤"""
        # Given: threshold=0.8
        # Given: 最佳匹配置信度 0.6
        # When: 调用 match()
        # Then: 不返回该 skill

class TestConfidenceScoring:
    """测试置信度评分"""
    
    async def test_semantic_similarity_scoring(self):
        """TC-CS01: 语义相似度评分"""
        # Given: "写代码" vs "代码生成"
        # When: 计算相似度
        # Then: 高语义相似度分数
        
    async def test_keyword_boost(self):
        """TC-CS02: 关键词匹配加分"""
        # Given: 用户输入包含 skill 名称关键词
        # When: 计算置信度
        # Then: 关键词匹配给予额外权重
```

### 4.2 集成测试

```python
class TestSkillMatcherIntegration:
    """描述匹配与 Agent 集成"""
    
    async def test_matcher_in_agent_loop(self):
        """TC-MI01: Agent 循环中触发匹配"""
        # Steps:
        # 1. 用户输入 "帮我重构这个函数"
        # 2. Agent 调用 SkillMatcher
        # 3. 匹配到 "code_refactor" skill
        # 4. Agent 执行该 skill
        
    async def test_matcher_respects_eligibility(self):
        """TC-MI02: 匹配只考虑 eligible skills"""
        # Steps:
        # 1. skill_A 被用户禁用
        # 2. 用户输入匹配 skill_A 的描述
        # 3. 匹配结果不包含 skill_A
        
    async def test_matcher_with_security(self):
        """TC-MI03: 匹配结果受 security 约束"""
        # Steps:
        # 1. 匹配到 T1 skill
        # 2. 执行前需要授权
        # 3. 授权后继续
        
    async def test_command_overrides_matcher(self):
        """TC-MI04: 斜杠命令优先于匹配"""
        # Steps:
        # 1. 用户输入 "/skill_A 执行B"
        # 2. 虽然描述更匹配 skill_B
        # 3. 但执行 skill_A
```

### 4.3 性能测试

```python
class TestMatcherPerformance:
    """匹配器性能测试"""
    
    async def test_match_latency_under_100ms(self):
        """TC-MP01: 匹配延迟 < 100ms"""
        # Given: 50 个 skill
        # When: 执行匹配
        # Then: 平均延迟 < 100ms
        
    async def test_match_with_many_skills(self):
        """TC-MP02: 大量技能时性能"""
        # Given: 200 个 skill
        # When: 执行匹配
        # Then: 延迟 < 500ms，不 OOM
```

---

## 测试执行计划

### 按 Phase 的测试节奏

```
Phase 1: Subagent Workspace
├── Week 1-2: 开发期间
│   ├── 每天: 运行相关单元测试
│   └── 每两天: 运行集成测试
├── Week 3: 功能冻结
│   ├── 完整回归测试
│   └── E2E 测试通过
└── Week 4: 发布前
    └── 性能基准测试

Phase 2: FMS/Git Tools
├── Week 1: 开发期间
│   ├── Mock 外部服务
│   └── 单元测试覆盖 > 90%
└── Week 2: 集成测试
    └── 真实服务联调 (staging)

Phase 3: Skill Security
├── Week 1: Security 核心
│   └── 安全测试优先
└── Week 2: 集成验证
    └── 权限持久化验证

Phase 4: Description Matcher
├── Week 1: 算法开发
│   └── 单元测试 + 性能测试
└── Week 2: 集成优化
    └── 阈值调优
```

### CI/CD 集成

```yaml
# .github/workflows/test.yml

name: Integration Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Phase-specific tests
        run: |
          # 根据修改的文件决定运行哪些测试
          if git diff --name-only | grep -q "subagent"; then
            pytest tests/modules/agentic_chat/test_subagent* -v
          fi
          if git diff --name-only | grep -q "fms\|git"; then
            pytest tests/modules/tools/test_fms_tools.py -v
            pytest tests/modules/tools/test_git_tools.py -v
          fi
      
  integration-tests:
    needs: unit-tests
    runs-on: ubuntu-latest
    services:
      # 启动测试依赖服务
      fms-mock:
        image: fms-mock:latest
    steps:
      - name: Run integration tests
        run: pytest tests/integration/ -v --timeout=300
      
  e2e-tests:
    needs: integration-tests
    runs-on: ubuntu-latest
    steps:
      - name: Run E2E scenarios
        run: pytest tests/e2e/ -v --timeout=600
```

### 测试覆盖率目标

| 模块 | 单元测试 | 集成测试 | 目标覆盖率 |
|------|---------|---------|-----------|
| subagent_workspace.py | 必测 | 必测 | 95% |
| subagent_manager.py (修改) | 必测 | 必测 | 90% |
| fms_tools.py | 必测 | Mock | 90% |
| git_tools.py | 必测 | Mock | 90% |
| skill_security.py | 必测 | 必测 | 95% |
| skill_matcher.py | 必测 | 必测 | 90% |

---

## 问题排查指南

### 常见测试失败场景

```python
# 1. Workspace 权限问题
# 错误: Permission denied when creating workspace
# 解决: 检查 umask 设置，确保测试环境目录权限正确

# 2. Async 测试事件循环冲突
# 错误: Event loop is closed
# 解决: 使用 pytest-asyncio，正确配置 event_loop fixture

# 3. 外部服务 Mock 失败
# 错误: Connection refused
# 解决: 使用 unittest.mock 或 pytest-mock，确保所有外部调用都被 mock

# 4. 测试数据残留
# 错误: Workspace already exists
# 解决: 使用 tempfile.TemporaryDirectory，确保清理
```

### Debug 技巧

```python
# 启用详细日志
import logging
logging.getLogger("aipc_agent").setLevel(logging.DEBUG)

# 打印 workspace 结构
import subprocess
subprocess.run(["tree", workspace_dir])

# 检查 subagent 状态
print(manager._sessions)

# 验证 context 注入
print(subagent_system_prompt)
```

---

*测试计划版本: 1.0*  
*更新日期: 2026-03-26*
