# Phase 5 实施计划：技能系统完善

> **路线**: 轻量级、向后兼容、不追 Docker 沙箱
> **时间**: 2 周 (Week 4-5)  
> **状态**: ✅ 已完成 (2026-03-24)  
> **分支**: `feature/skill-security-tier-20260324` (已推送到远程)

---

## 一、背景与目标

### 现状
- ✅ 已有 ~~12~~ 14 个技能（新增 research + find-skills）
- ✅ 基础设施完整 (init + package + validate + security)
- ✅ Web UI + API 已存在 (`serve.py`)
- ✅ `web_search`/`web_fetch` 工具 + research skill 系统化研究
- ✅ 外部 skill 安全机制（代码扫描）

### 目标（全部完成）
1. ✅ **安全**: 目录分级 + 代码扫描（轻量，不追 Docker）
2. ✅ **能力**: 新增 research skill（利用现有工具）
3. ✅ **生态**: 支持本地 .skill 文件安装（无需中心化市场）

### 测试验证
- ✅ 20个单元测试全部通过
- ✅ Web UI 实测验证（research + find-skills + 安全扫描）
- ✅ 代码扫描有效检测危险代码（`rm -rf /` 测试通过）

---

## 二、与 DeerFlow 对比总结

### 核心差异

| 维度 | DeerFlow (字节跳动) | 我们的项目 | 我们的策略 |
|------|-------------------|-----------|-----------|
| **架构重量** | 重型 (LangGraph + Docker) | 轻量 (原生 + 进程隔离) | 保持轻量 |
| **沙箱方案** | Docker 容器隔离 | 进程隔离 + 代码扫描 | 不追 Docker，够用即可 |
| **技能市场** | 中心化 (skills.sh + npx CLI) | 去中心化 (GitHub + .skill 文件) | 避免生态建设负担 |
| **Skill 数量** | 17 个 | 12 个 | 补齐核心能力 |
| **Eval 体系** | 完整 (测试 + benchmark + 优化器) | 基础验证 | 够用即可，不做重 |
| **Memory 设计** | 简单长期记忆 | **分离架构** (USER + MEMORY) | **领先** |
| **Session 追踪** | 粗粒度 | **细粒度** (60s timeout + summary) | **领先** |
| **前端** | React 重型应用 | 轻量 Web UI (serve.py) | 够用即可 |

### 技能对比详情

| DeerFlow 技能 | 我们有？ | 策略 |
|--------------|---------|------|
| deep-research | 无 | **复用工具，创建 skill** |
| find-skills | 无 | **创建轻量版** |
| data-analysis | 无 | 可选，暂不优先 |
| chart-visualization | 无 | 可选，暂不优先 |
| ppt-generation | 无 | 可选，暂不优先 |
| image-generation | 无 | 可选，暂不优先 |
| skill-creator | 有 | 已有，功能对齐 |
| github-deep-research | 无 | 可整合到 github skill |

### 关键借鉴点

**DeerFlow 值得学的**:
- `deep-research` 的 4 阶段研究方法论 -> 我们复用到 `research` skill
- `find-skills` 的技能发现思路 -> 我们创建轻量本地版
- 代码验证逻辑 -> 参考强化我们的 `quick_validate.py`

**我们领先的**:
- Memory 分离架构 (USER.md + MEMORY.md)
- Session 级消息追踪与自动摘要
- 更轻量的部署 (无 Docker 依赖)

---

## 三、不做的事项（明确边界）

| 不做 | 理由 |
|-----|------|
| Docker 沙箱 | 太重，进程隔离+代码扫描足够 |
| 中心化技能市场 (skills.sh) | 需要生态建设，维护成本高 |
| `npx skills` CLI | 可以用 GitHub 直接下载 .skill 文件替代 |
| 完整 eval 测试体系 | 太重，manual test + simple validation 足够 |
| 修改 SKILL.md 格式 | 向后兼容优先，目录分级即可 |

---

## 四、实施阶段

### Phase 1: 安全基础（高优先级）

**任务 1: 目录结构调整**
```bash
mkdir -p skills/system skills/user skills/market
# 现有技能迁移到 skills/system/
```

**任务 2: 安全扫描器 (`aiagent/skill_security.py`)**
```python
# 危险模式检查（仅 market 级）
DANGEROUS_PATTERNS = {
    "rm_rf": r"rm\s+-rf\s+/",
    "curl_pipe": r"curl.*\|\s*(sh|bash)",
    "eval": r"eval\s*\(",
    "exec_system": r"os\.system\s*\(",
}
```

**任务 3: 扫描逻辑更新 (`aiagent/skills.py`)**
- 支持三级目录扫描
- SkillMeta 添加 `trust_level` 字段
- 向后兼容：根目录技能视为 system 级

---

### Phase 2: 核心技能补充（中优先级）

**任务 4: 创建 `research` skill**
- 参考 DeerFlow `deep-research` 方法论
- 复用现有 `web_search` + `web_fetch` 工具
- 4 阶段研究流程：探索 -> 深入 -> 验证 -> 综合

**任务 5: 创建 `find-skills` skill**
- 本地技能发现助手
- 指导用户安装 .skill 文件

---

### Phase 3: 体验优化（低优先级 / 可选）

**任务 6: 本地技能索引**
```bash
# 生成 skills/.index.json 加速扫描
python -m aiagent.skills_index --update
```

**任务 7: 安装脚本增强**
```bash
# 支持从 GitHub 直接下载
aiagent install-skill https://github.com/user/skill-repo
```

---

## 五、详细设计

### 5.1 目录分级策略

| 级别 | 目录 | 来源 | 执行方式 | 安全检查 |
|-----|------|-----|---------|---------|
| System | `skills/system/` | 官方/系统 | 直接执行 | 跳过 |
| User | `skills/user/` | 用户本地 | 直接执行 | 可选 |
| Market | `skills/market/` | 外部下载 | 直接执行 | **强制扫描** |

**向后兼容**: 根目录下的技能视为 system 级，输出警告建议迁移。

### 5.2 代码扫描实现

```python
# aiagent/skill_security.py
class SkillSecurityChecker:
    def check_skill(self, skill_path: Path) -> SecurityResult:
        # 仅扫描 scripts/ 下的 .py, .sh 文件
        # 返回: passed, issues[]
```

**注意**: 扫描≠沙箱，只是拒绝明显危险的代码（如 `rm -rf /`）。

### 5.3 Research Skill 设计

参考 DeerFlow，但适配我们的工具：

```markdown
---
name: research
description: 系统性网络研究。当用户需要深入了解主题、生成报告前收集信息、
  或需要多角度验证时使用。触发词："研究一下"、"帮我查一下"、"这个主题的资料"
---

# Research

## 4 阶段研究法

### Phase 1: 广度探索
- 用 3-5 个不同关键词搜索
- 识别关键维度（技术、市场、案例等）

### Phase 2: 深度挖掘
- 每个维度深入搜索
- 使用 web_fetch 获取全文

### Phase 3: 多角度验证
- 事实数据、案例、专家观点、趋势、对比

### Phase 4: 综合检查
- [ ] 是否覆盖 3-5 个角度？
- [ ] 是否有权威来源？
- [ ] 信息是否最新？
```

---

## 六、文件变更清单

| 文件 | 操作 | 说明 |
|-----|------|-----|
| `skills/system/` | 新建+迁移 | 系统级技能目录 |
| `skills/user/` | 新建 | 用户技能目录 |
| `skills/market/` | 新建 | 外部技能目录 |
| `aiagent/skills.py` | 修改 | 三级目录扫描 |
| `aiagent/skill_security.py` | 新建 | 代码扫描器 |
| `skills/research/` | 新建 | 研究方法论 skill |
| `skills/find-skills/` | 新建 | 技能发现 skill |

---

## 七、验收标准（全部完成）

### Phase 1 完成 ✅
- [x] 目录结构调整完成（`skills/{system,user,market}/`）
- [x] `skill_security.py` 实现并测试（危险代码扫描）
- [x] `skills.py` 支持三级扫描 + 分组显示

### Phase 2 完成 ✅
- [x] `research` skill 可用（4阶段研究法，Web UI 实测验证）
- [x] `find-skills` skill 可用（技能发现指南，Web UI 实测验证）

### Phase 3 （可选，暂不实施）
- [ ] 本地技能索引生成
- [ ] GitHub 直接下载安装脚本

**注：Phase 3 为可选优化，当前功能已满足需求**

---

## 八、参考文档

| 文档 | 说明 |
|------|------|
| `SKILL_SECURITY_TIER_IMPLEMENTATION.md` | **详细实施报告**（问题解决、测试覆盖、Git历史）|
| `DEERFLOW_SKILL_ANALYSIS.md` | 竞品分析（背景参考）|
| `BRANCH_HISTORY.md` | 分支历史和提交记录 |

### 相关文件位置

```
aiagent/
├── skill_security.py          # 安全扫描器
├── skills.py                  # 三级扫描 + 分组显示
skills/
├── system/                    # 系统内置技能（14个）
│   ├── research/              # 研究方法论 ✅
│   ├── find-skills/           # 技能发现 ✅
│   └── ...
├── user/                      # 用户技能（空）
└── market/                    # 外部技能（空）
tests/
├── test_research_skill.py     # research 测试（9个）
└── test_find_skills_skill.py  # find-skills 测试（8个）
```

---

**本计划为唯一实施文档，其他相关文档仅作背景参考。**

**状态：✅ 已完成，已推送到远程，可合并到主分支**
