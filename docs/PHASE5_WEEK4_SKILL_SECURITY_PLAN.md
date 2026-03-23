# Phase 5 Week 4: Skill 权限分级与自检系统

## 目标
为 Skill 系统设计完整的安全体系，实现三级权限分级和自动化安全检查。

---

## 当前分支状态

| 项目 | 状态 |
|------|------|
| **当前分支** | `feature/memory-struct-20260320` |
| **工作目录** | `/Users/emdoor/Documents/projects/ai_pc_aiagent_os` |
| **已完成功能** | USER.md/MEMORY.md 分离、MemoryManager、Daily Log 自动摘要 |
| **待开发功能** | Skill 权限分级与自检系统 |

### 本地分支列表
```
* feature/memory-struct-20260320      daf1b05 docs: Add Phase 5 implementation report
  feature/memory-week1-20260319       51b8826 fix: 修复 'NoneType' object is not iterable 错误
  feature/server-session-20260318     d5b7124 fix: 修复刷新后无法加载会话的问题
  feature/subagent-isolation-20260319 2287b9c fix: 子 Agent 文件创建到错误目录的问题
  feature/todo-list-20260318          22b2a7b merge: 用户画像分离与安全上下文注入
  master                              9fbd374 feat: 添加任务列表（Todo List）功能
```

### 建议操作
```bash
# 选项1: 在当前分支继续开发（推荐）
# 已经在 feature/memory-struct-20260320 分支，可直接开始

# 选项2: 创建新分支
git checkout -b feature/skill-security-20260322
```

---

## 已发现的 Bug（需先修复）

### Bug 1: MEMORY.md 日期不更新 ✅ 已修复
**问题**: `MemoryManager.update_system_date()` 修改了数据但没有调用 `save()`
**修复**: 在 `aiagent/memory_manager.py:184` 添加 `self.save()`
**状态**: 已修复

### Bug 2: Daily Log 消息过滤太严格
**问题**: 只统计 `type != reasoning/tool_calls` 的消息，但 assistant 消息大部分是这些类型
**影响**: 需要 5 条有效消息才触发摘要，实际很难达到
**建议**: 降低阈值或调整过滤条件

### Bug 3: 异常静默处理
**问题**: `_auto_log_summary` 中所有异常都被 `try-except` 捕获并忽略
**影响**: 出错时看不到任何日志
**建议**: 至少打印错误日志

---

## 实施计划

### Week 4-1: 权限分级系统基础 (Day 1-2)

#### Task 1.1: 扩展 Skill 元数据结构
- [ ] 修改 `aiagent/skills.py` 中的 `SkillMeta` dataclass
- [ ] 添加 `level`, `security_score`, `permissions` 字段
- [ ] 更新 `_parse_frontmatter()` 支持新的权限字段

#### Task 1.2: 三级目录结构
```
skills/
├── system/          # Level 1: 系统内置
│   ├── weather/
│   └── session-logs/
├── user/            # Level 2: 用户自定义
│   └── (用户创建的技能)
└── market/          # Level 3: 外部市场
    └── (第三方技能)
```

- [ ] 创建三级目录结构
- [ ] 修改 `scan_skills()` 自动识别 level（基于路径）
- [ ] 迁移现有 skills 到 system/ 目录

#### Task 1.3: SKILL.md 权限声明规范
```yaml
---
name: example-skill
description: "示例技能"
version: "1.0.0"

# 权限声明
permissions:
  filesystem:
    read: ["/workspace/**", "/tmp/**"]
    write: ["/workspace/output/**"]
  network:
    allowed_hosts: ["api.example.com"]
    allow_localhost: false
  execution:
    allow_shell: true
    allowed_commands: ["python", "node"]
    blocked_commands: ["sudo", "rm -rf /"]
  system:
    allow_env_read: true
    allowed_env_vars: ["HOME", "USER"]

# 安全级别
security:
  level: "user"           # system | user | market
  auto_approve: false
  sandbox_required: false
---
```

---

### Week 4-2: 安全自检系统 (Day 3-4)

#### Task 2.1: SkillSecurityChecker 核心类
- [ ] 创建 `aiagent/skill_security.py`
- [ ] 实现 `_check_structure()` - 目录结构检查
- [ ] 实现 `_check_permissions()` - 权限声明验证
- [ ] 实现 `_check_scripts()` - 脚本安全扫描
- [ ] 实现 `_check_dependencies()` - 依赖可用性检查
- [ ] 实现 `_calculate_score()` - 安全评分算法

#### Task 2.2: 危险模式检测
```python
DANGEROUS_PATTERNS = [
    # 文件操作
    r"rm\s+-rf\s+/",
    r"chmod\s+777\s+/",
    # 系统命令
    r"sudo\s+",
    r"mkfs\.",
    # 网络风险
    r"curl\s+.*\|\s*sh",
    r"wget\s+.*\|\s*sh",
    # 敏感路径访问
    r"/etc/shadow",
    r"/etc/passwd",
    r"~/.ssh",
]
```

#### Task 2.3: 安全评分算法
| 检查项 | 权重 | 扣分规则 |
|--------|------|----------|
| 权限声明完整 | 20% | 缺少 permissions 扣 20 分 |
| 目录结构安全 | 15% | 发现二进制文件扣 15 分 |
| 脚本安全检查 | 25% | 每个危险模式扣 10 分 |
| 依赖满足度 | 20% | 每个缺失依赖扣 5 分 |
| 网络权限合理 | 20% | 过于宽泛扣 10-20 分 |

---

### Week 4-3: 集成与执行控制 (Day 5-6)

#### Task 3.1: 加载时安全检查
- [ ] 修改 `scan_skills()` 集成安全检查
- [ ] 添加 `--skip-security-check` 开发选项
- [ ] 实现检查结果缓存（避免每次重启重复检查）

#### Task 3.2: 使用时的权限控制
- [ ] 在 `agent.py` 中添加 `_check_skill_permission()`
- [ ] 实现用户确认对话框（通过 events 发送到前端）
- [ ] 添加 `auto_approved_skills` 列表（用户信任的技能）

#### Task 3.3: 执行时沙箱（可选/高级）
- [ ] **复用 SubAgent 机制**（详见下方说明）
- [ ] 为 Market 级别 skill 创建临时工作区
- [ ] 限制文件系统访问（通过环境变量/参数传递）

---

## 🔐 Skill 沙箱方案（复用 SubAgent）

### 核心思路
把 **Skill 执行** 包装成 **SubAgent 任务**，复用全套隔离机制：

```
父 Agent ──派生──→ 子 Agent（隔离 workspace，独立线程）
       ←──返回───  执行结果
```

**套用现有的父子 Agent 机制**：
- 原有用途：并行执行多个任务
- 新用途：隔离执行不信任的 Skill

### 实现方式
```python
# 直接执行（无沙箱）- 用于 system/user 级别
result = execute_skill(skill)

# 沙箱执行 - 用于 market 级别（复用 SubAgent）
result = spawn_subagent(task="execute_skill(skill)")
```

### 优势
- ✅ 复用现有代码（workspace 隔离、线程隔离、超时控制）
- ✅ 轻量（Python 进程级，无需 Docker）
- ✅ 执行完自动清理

### 限制
- 不是真正的系统级沙箱（仍可被突破）
- 仅作为第一层防护，配合代码扫描使用

---

## 文件变更清单

### 新建文件
```
aiagent/skill_security.py        # 安全检查核心类
aiagent/skill_permissions.py     # 权限控制装饰器/上下文
skills/system/                   # 系统内置技能目录
skills/user/                     # 用户自定义技能目录
skills/market/                   # 外部市场技能目录
tests/test_skill_security.py     # 安全系统测试
docs/skill-security.md           # 安全系统文档
docs/BRANCH_HISTORY.md           # 分支历史记录
```

### 修改文件
```
aiagent/skills.py               # 集成安全检查
aiagent/agent.py                # 使用时的权限控制
aiagent/events.py               # 添加 skill 确认事件
aiagent/memory_manager.py       # Bug 修复：添加 save() 调用
web/src/components/SkillManager.tsx  # Skill 管理页面
```

### 迁移文件
```
skills/weather/      -> skills/system/weather/
skills/skill-creator/ -> skills/system/skill-creator/
# ... 其他现有 skills
```

---

## 里程碑

| 里程碑 | 日期 | 交付物 |
|--------|------|--------|
| M1 | Day 2 | 三级目录结构 + 扩展元数据 |
| M2 | Day 4 | SkillSecurityChecker 完整实现 |
| M3 | Day 6 | 集成到加载和使用流程 |
| M4 | Day 7 | 前端界面 + 测试 + 文档 |

---

## 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 安全检查过严影响开发体验 | 中 | 添加 `--skip-security-check` 选项 |
| 权限声明格式不兼容旧 skills | 低 | 向后兼容：无声明默认为 user 级别 |
| 沙箱实现复杂 | 高 | MVP 阶段先实现警告+确认，暂不强制沙箱 |
| 误报（正常代码被标记危险） | 中 | 可配置的 pattern 白名单 |

---

## 相关文档

- [Phase 5 实施报告](./PHASE5_IMPLEMENTATION_REPORT.md)
- [Memory 系统设计](./memory-design.md)
- [Skill 创建指南](../skills/skill-creator/SKILL.md)
- [分支历史记录](./BRANCH_HISTORY.md) ⬅️ 新创建

---

## 当前工作区状态

```bash
# 未暂存的修改
modified:   .subagent_registry.json
modified:   aiagent/__pycache__/agent.cpython-313.pyc
modified:   aiagent/memory_manager.py  # Bug 修复
modified:   data/sessions/index.json
modified:   data/sessions/sess_*.json

# 未跟踪的文件
docs/PHASE5_WEEK4_SKILL_SECURITY_PLAN.md
docs/BRANCH_HISTORY.md
workspace/subagents/*/
```

**建议**: 
1. 提交 Bug 修复（memory_manager.py）
2. 提交文档更新（BRANCH_HISTORY.md）
3. 开始 Week 4 开发
