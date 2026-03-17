# aiagent 从零开发计划

## 项目目标
构建一个轻量级、可扩展的 AI Agent 系统，支持工具调用、子 Agent 并行、Skill 扩展。

---

## 阶段规划

### 🚀 Phase 1: MVP 核心 (Week 1-2)
**目标**：最小可用版本，支持基本的对话和工具调用

---

#### Day 1: 项目骨架搭建
**任务清单**:
- [ ] 初始化 Python 项目结构
  ```
  aiagent/
  ├── pyproject.toml
  ├── README.md
  ├── .env.example
  ├── aiagent/
  │   ├── __init__.py
  │   ├── agent.py (空壳)
  │   └── main.py (CLI入口)
  └── tests/
      └── __init__.py
  ```
- [ ] 配置依赖管理 (uv/poetry)
- [ ] 基础环境变量配置 (.env)
  - OPENAI_API_KEY
  - OPENAI_BASE_URL
  - MODEL
- [ ] 创建 Git 仓库，提交初始代码

**交付物**: 可运行的空项目框架

---

#### Day 2: LLM 客户端封装
**任务清单**:
- [ ] 创建 `aiagent/llm.py`
  - 封装 AsyncOpenAI 客户端
  - 支持流式/非流式调用
  - 错误处理 (重试、超时)
- [ ] 编写单元测试
  - Mock LLM 响应
  - 测试流式输出
- [ ] 简单的命令行测试脚本

**代码示例**:
```python
class LLMClient:
    async def chat(self, messages, tools=None, stream=False)
    async def chat_stream(self, messages, tools=None)
```

**交付物**: 可独立测试的 LLM 模块

---

#### Day 3: 工具系统基础
**任务清单**:
- [ ] 创建 `aiagent/tools/types.py`
  - ToolDefinition TypedDict
  - RegisteredTool 类
- [ ] 创建 `aiagent/tools/__init__.py`
  - 工具注册表
  - execute_tool 函数
- [ ] 实现第一个工具: `exec`
  - 执行 shell 命令
  - 返回 stdout/stderr/exit_code
- [ ] 编写工具测试

**交付物**: 可注册和执行工具的基础系统

---

#### Day 4: Tool-Use 主循环
**任务清单**:
- [ ] 实现 `aiagent/agent.py` 核心类
  - Agent.__init__() 初始化
  - Agent.run() 主循环
  - 支持多轮工具调用
- [ ] 实现工具调用解析
  - 解析 LLM 返回的 tool_calls
  - 并行执行多个工具
- [ ] 集成测试
  - 端到端对话测试

**主循环逻辑**:
```python
for round in range(MAX_ROUNDS):
    response = await llm.chat(messages, tools)
    if response.tool_calls:
        results = await execute_tools(response.tool_calls)
        messages.extend(results)
    else:
        return response.content
```

**交付物**: 支持工具调用的基础 Agent

---

#### Day 5: 文件操作工具
**任务清单**:
- [ ] 实现 `read` 工具
  - 支持 offset/limit
  - 错误处理
- [ ] 实现 `write` 工具
  - 自动创建目录
- [ ] 实现 `edit` 工具
  - 字符串替换
  - 唯一性检查
- [ ] 集成测试

**交付物**: 完整的文件操作工具集

---

#### Day 6: CLI 交互界面
**任务清单**:
- [ ] 完善 `main.py`
  - 交互式对话循环
  - 历史记录维护
  - 优雅退出 (Ctrl+C)
- [ ] 添加日志输出
  - 工具调用日志
  - 错误日志
- [ ] 美化输出 (rich/click 可选)

**交付物**: 可用的命令行交互界面

---

#### Day 7: 第一阶段验收
**任务清单**:
- [ ] 端到端测试
  - 完整对话流程
  - 工具调用链
- [ ] Bug 修复
- [ ] 代码审查和重构
- [ ] 更新文档

**验收标准**:
- ✅ 用户可以通过 CLI 与 Agent 对话
- ✅ Agent 可以执行 shell 命令
- ✅ Agent 可以读写文件
- ✅ 支持多轮工具调用

---

### 🔧 Phase 2: 工具扩展 (Week 3-4)
**目标**：丰富的工具集，覆盖常见开发场景

---

#### Day 8: Web 工具
**任务清单**:
- [ ] 实现 `web_fetch` 工具
  - URL 内容抓取
  - HTML 转文本
- [ ] 实现 `web_search` 工具
  - DuckDuckGo 搜索
  - 结果格式化
- [ ] 添加超时和重试机制

**交付物**: Web 抓取和搜索能力

---

#### Day 9: 进程管理工具
**任务清单**:
- [ ] 实现 `process` 工具
  - start: 后台启动进程
  - list: 列出进程
  - log: 查看日志
  - kill: 终止进程
- [ ] 进程状态管理
- [ ] 日志轮转

**交付物**: 后台进程管理能力

---

#### Day 10: 浏览器工具 (基础)
**任务清单**:
- [ ] 安装 Playwright 依赖
- [ ] 实现 `browser` 工具基础功能
  - status: 检查状态
  - open: 打开 URL
  - close: 关闭浏览器
- [ ] 截图功能

**交付物**: 基础浏览器控制能力

---

#### Day 11: 浏览器工具 (高级)
**任务清单**:
- [ ] 实现 `browser` 高级功能
  - snapshot: 获取页面文本
  - act: 点击/输入/按键
  - scroll: 滚动页面
- [ ] 自动截图
- [ ] 错误处理

**交付物**: 完整的浏览器自动化

---

#### Day 12: 其他工具
**任务清单**:
- [ ] 实现 `memory_search` 工具
  - 本地向量搜索 (可选)
  - 或简单的关键词搜索
- [ ] 实现 `apply_patch` 工具
  - unified diff 格式
- [ ] 工具文档

**交付物**: 补充工具集

---

#### Day 13-14: 第二阶段验收
**任务清单**:
- [ ] 所有工具集成测试
- [ ] 性能优化
- [ ] Bug 修复
- [ ] 工具使用文档

**验收标准**:
- ✅ 14个内置工具全部可用
- ✅ 工具错误处理完善
- ✅ 工具文档完整

---

### 🌳 Phase 3: 子 Agent 系统 (Week 5-6)
**目标**：支持并行子任务执行

---

#### Day 15: 子 Agent 注册表
**任务清单**:
- [ ] 创建 `subagent_registry.py`
  - SubagentRun 数据类
  - 内存注册表
  - 持久化到 JSON
- [ ] 实现注册/更新/查询接口
- [ ] 线程安全 (Lock)

**交付物**: 子 Agent 注册中心

---

#### Day 16: 子 Agent 管理器
**任务清单**:
- [ ] 创建 `subagent.py`
  - SubagentManager 类
  - announce_queue (Queue)
- [ ] 实现 `spawn_subagent` 函数
  - 安全检查 (深度/数量)
  - 线程启动
- [ ] 实现 announce 机制

**交付物**: 子 Agent 派生能力

---

#### Day 17: 子 Agent 工具
**任务清单**:
- [ ] 创建 `subagent_tools.py`
  - `sessions_spawn` 工具
  - `subagents` 工具 (list/kill/steer)
- [ ] 工具集成到 Agent
- [ ] 基础测试

**交付物**: 子 Agent 管理工具

---

#### Day 18: 父子通信优化
**任务清单**:
- [ ] 实现 `sessions_send` 工具
  - 跨 session 通信
- [ ] 实现 `agents_list` 工具
  - 全局 Agent 列表
- [ ] Steer 机制完善
  - 父 Agent 发送修正指令
  - 子 Agent 接收并执行

**交付物**: 完整的父子通信机制

---

#### Day 19-20: 子 Agent 系统测试
**任务清单**:
- [ ] 并行任务测试
- [ ] 深度限制测试
- [ ] 数量限制测试
- [ ] 异常场景测试
  - 子 Agent 崩溃
  - 父 Agent 提前退出

**验收标准**:
- ✅ 子 Agent 可以并行执行
- ✅ 安全限制生效
- ✅ 父子通信正常

---

### 🎨 Phase 4: Skill 系统 (Week 7)
**目标**：可扩展的知识库系统

---

#### Day 21: Skill 扫描与加载
**任务清单**:
- [ ] 创建 `skills.py`
  - `scan_skills()` 函数
  - frontmatter 解析
  - SkillMeta 数据类
- [ ] 实现 `build_skills_summary()`
- [ ] 集成到 workspace

**Skill 目录结构**:
```
skills/
└── my-skill/
    └── SKILL.md
```

**交付物**: Skill 扫描系统

---

#### Day 22: Skill 使用流程
**任务清单**:
- [ ] Agent 自动读取 Skill
  - LLM 判断需要某个 skill
  - 调用 read 工具读取 SKILL.md
- [ ] Skill 缓存机制
- [ ] Skill 示例和文档

**交付物**: 完整的 Skill 使用流程

---

#### Day 23: 内置 Skill
**任务清单**:
- [ ] 创建示例 Skill
  - coding-agent
  - github
  - weather
  - 等
- [ ] Skill 模板
- [ ] Skill 开发文档

**交付物**: 示例 Skill 库

---

#### Day 24: Skill 系统测试
**任务清单**:
- [ ] Skill 扫描测试
- [ ] Skill 使用测试
- [ ] 边界情况测试

**验收标准**:
- ✅ Skill 自动发现
- ✅ Skill 按需加载
- ✅ Skill 文档清晰

---

### 🌐 Phase 5: Web UI (Week 8)
**目标**：可视化操作界面

---

#### Day 25: Web 服务基础
**任务清单**:
- [ ] 创建 `serve.py`
  - HTTP Server
  - 静态文件服务
  - CORS 配置
- [ ] 创建 `web_ui.html`
  - 基础布局
  - 输入框
  - 消息展示

**交付物**: 基础 Web 服务

---

#### Day 26: SSE 实时流
**任务清单**:
- [ ] 实现 SSE 端点 `/run`
- [ ] 事件类型定义
  - start
  - thinking
  - tool_calls
  - tool_result
  - done
- [ ] 前端事件处理

**交付物**: 实时流式响应

---

#### Day 27: Web UI 美化
**任务清单**:
- [ ] CSS 样式
  - 消息气泡
  - 代码高亮
  - 工具调用展示
- [ ] 图片显示
- [ ] 响应式布局

**交付物**: 美观的 Web 界面

---

#### Day 28: Web 功能增强
**任务清单**:
- [ ] 历史记录展示
- [ ] 停止生成按钮
- [ ] 模型选择 (可选)
- [ ] 文件上传 (可选)

**验收标准**:
- ✅ Web UI 可用
- ✅ 实时流式输出
- ✅ 工具调用可视化

---

### 📅 Phase 6: 定时任务 (Week 9)
**目标**：自动化定时执行

---

#### Day 29: Cron 核心
**任务清单**:
- [ ] 创建 `tools/cron.py`
  - 任务注册表
  - 调度器线程
  - 持久化到 JSON
- [ ] 支持 schedule 类型
  - at: 一次性
  - every: 周期性
  - cron: Cron 表达式

**交付物**: 定时任务调度器

---

#### Day 30: Cron 任务执行
**任务清单**:
- [ ] 支持 payload 类型
  - exec: shell 命令
  - message: 打印消息
  - agent: Agent 任务
- [ ] 执行日志
- [ ] Web UI 集成

**交付物**: 完整的定时任务系统

---

### 🧪 Phase 7: 测试与优化 (Week 10)
**目标**：稳定性保证

---

#### Day 31-32: 单元测试
**任务清单**:
- [ ] 工具测试
- [ ] Agent 核心测试
- [ ] 子 Agent 测试
- [ ] Mock LLM 响应

**交付物**: 单元测试覆盖率 > 70%

---

#### Day 33-34: 集成测试
**任务清单**:
- [ ] 端到端测试
- [ ] 性能测试
- [ ] 压力测试

**交付物**: 集成测试套件

---

#### Day 35: 性能优化
**任务清单**:
- [ ] 异步优化
- [ ] 内存优化
- [ ] 启动速度优化

**交付物**: 优化后的代码

---

## 输入扩展方案

### 当前输入方式
- CLI: 文本输入
- Web UI: 文本输入

### 可扩展输入

#### 1. 图片输入 (Week 11, Day 36-37)
```
优先级: 高
难度: 中

实现方案:
├── Web UI 文件上传
│   ├── <input type="file" accept="image/*">
│   ├── 图片压缩
│   └── Base64 编码
│
├── Agent 处理
│   ├── 检测输入类型
│   ├── 调用 vision 模型 (kimi 支持)
│   └── 或调用 image 工具分析
│
└── 后端存储
    ├── 临时文件
    └── 清理机制
```

#### 2. 语音输入 (Week 11, Day 38-39)
```
优先级: 中
难度: 中

实现方案:
├── Web UI 录音
│   ├── MediaRecorder API
│   ├── 音频压缩 (opus)
│   └── 上传音频文件
│
├── 语音识别
│   ├── Whisper API (OpenAI)
│   ├── 或本地 Whisper (可选)
│   └── 返回文本
│
└── 语音输出 (TTS 已支持)
    └── 可以扩展为对话模式
```

#### 3. 文件拖拽上传 (Week 12, Day 40)
```
优先级: 中
难度: 低

实现方案:
├── Web UI 拖拽区域
│   └── ondrop 事件处理
│
├── 文件处理
│   ├── 文本文件: 直接读取内容
│   ├── PDF: 调用 pdf 工具
│   ├── 图片: 调用 image 工具
│   └── 其他: 提示用户
│
└── 大文件处理
    └── 分块读取
```

#### 4. 多模态输入 (Week 12, Day 41-42)
```
优先级: 低
难度: 高

实现方案:
├── 同时输入文本+图片
│   └── messages 格式支持
│
├── Vision 模型支持
│   └── kimi/gpt-4o 等
│
└── Web UI 支持
    ├── 图文混排输入
    └── 图片预览
```

---

## 总体时间表

```
Week 1-2:  Phase 1 - MVP 核心 (7天)
Week 3-4:  Phase 2 - 工具扩展 (7天)
Week 5-6:  Phase 3 - 子 Agent 系统 (6天)
Week 7:    Phase 4 - Skill 系统 (4天)
Week 8:    Phase 5 - Web UI (4天)
Week 9:    Phase 6 - 定时任务 (2天)
Week 10:   Phase 7 - 测试与优化 (5天)
Week 11-12: 输入扩展 (7天)
─────────────────────────────────
总计: 约 12 周 (3个月)
```

## 里程碑

| 里程碑 | 时间 | 交付物 |
|--------|------|--------|
| MVP | Week 2 | CLI 可用，基础工具 |
| 工具完善 | Week 4 | 14个工具全部可用 |
| 并行能力 | Week 6 | 子 Agent 系统可用 |
| 可扩展 | Week 7 | Skill 系统可用 |
| 可视化 | Week 8 | Web UI 可用 |
| 自动化 | Week 9 | 定时任务可用 |
| 稳定版 | Week 10 | 完整测试覆盖 |
| 增强版 | Week 12 | 多模态输入 |

## 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| LLM API 不稳定 | 高 | 添加重试、降级到本地模型 |
| Playwright 安装复杂 | 中 | 提供详细安装指南，可选依赖 |
| 并发 Bug | 高 | 充分测试，使用线程安全数据结构 |
| 功能蔓延 | 中 | 严格按阶段执行，控制范围 |

## 与 OpenClaw 的优化建议

### 当前差距

| 能力 | OpenClaw | aiagent_2 (计划中) | 建议 |
|------|----------|-------------------|------|
| 多通道 | 20+ | CLI + Web | 暂不需要，专注核心 |
| Skill 路由 | 向量相似度 | 简单摘要 | MVP 足够，后续可加向量 |
| 持久化 | 多层存储 | JSON 文件 | 足够，复杂场景用数据库 |
| 部署 | Gateway+Daemon | 本地运行 | 保持简单 |
| 语音 | Wake+Talk | 录音+Whisper | 可以添加 |
| Canvas | 完整实现 | 无 | 暂不实现 |
| 移动应用 | iOS/Android | 无 | 暂不实现 |

### 建议优化方向

1. **保持轻量**: 不要过度工程化，保持核心功能简洁
2. **可插拔设计**: 工具、Skill 都做成可插拔
3. **配置驱动**: 通过配置文件而非代码修改行为
4. **文档优先**: 每个功能都要有文档和示例
5. **测试驱动**: 先写测试再实现功能
