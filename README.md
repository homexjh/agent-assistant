# aiagent

基于多 LLM 提供商（Kimi/Qwen/Azure）的自主 AI Agent 运行时。用户 query 进来，Agent 通过 tool-use 主循环执行 shell 命令、读写文件、抓取网页、管理后台进程、调用子 Agent 等，完成复杂多步任务。

---

## 特性

- **多 LLM 提供商支持**：Kimi (Moonshot)、通义千问 (Qwen)、Azure OpenAI
- **Web UI + CLI 双模式**：浏览器可视化交互 或 命令行对话
- **13+ 内置工具**：代码执行、文件操作、网页抓取、浏览器控制、定时任务、语音合成等
- **三级 Skill 安全架构**：System（完全信任）/ User（基本信任）/ Market（需检查）
- **可视化 Skill 管理**：Web UI 技能面板 + 4步创建向导
- **子 Agent 并行**：支持派生子 Agent 异步执行任务，自动隔离工作空间
- **代码安全扫描**：自动检测危险代码模式（rm -rf、curl\|sh 等）
- **系统化研究能力**：4阶段研究方法论（广度→深度→验证→综合）
- **分离式记忆架构**：USER.md（用户画像）+ MEMORY.md（结构化记忆）

---

## 架构总览

```
用户输入
    ↓
┌─────────────────┐    ┌─────────────────┐
│  Web UI Mode    │    │   CLI Mode      │
│  (Browser)      │    │  (Terminal)     │
│  localhost:8765 │    │  python -m main │
└────────┬────────┘    └────────┬────────┘
         │                      │
         └──────────┬───────────┘
                    ↓
              Agent Core
         ┌─────────┴─────────┐
         ↓                   ↓
   Skill 系统            工具执行
   (三级安全架构)        (13+ 工具)
   - system/             - exec/read/write
   - user/               - web_search/fetch
   - market/             - browser/pdf/image
         ↓                   ↓
    安全扫描器          子 Agent 系统
    (危险代码检测)       (并行+隔离)
```

---

## 快速开始

### 1. 安装依赖

```bash
uv sync

# 可选依赖（按需）
uv add pdfminer.six          # pdf 工具
uv add playwright && uv run playwright install chromium  # browser 工具
uv add croniter              # cron 工具支持 cron 表达式
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env` 并填入你的 API Key：

```bash
cp .env.example .env
```

编辑 `.env`：

```ini
# ========== Kimi (Moonshot) 配置 ==========
KIMI_API_KEY=sk-your-kimi-api-key
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODELS=kimi-k2.5,kimi-k2-0711-preview,moonshot-v1-8k

# ========== 通义千问 (Qwen) 配置 ==========
QWEN_API_KEY=sk-your-qwen-api-key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODELS=qwen3.5-plus,qwen3-max-2026-01-23,qwen3-coder-next,qwen3-coder-plus

# ========== Azure OpenAI 配置 ==========
AZURE_API_KEY=your-azure-api-key
AZURE_ENDPOINT=https://your-resource.openai.azure.com
AZURE_DEPLOYMENT=gpt-4o
AZURE_API_VERSION=2024-08-01-preview
AZURE_MODELS=gpt-4o

# ========== 默认配置 ==========
DEFAULT_PROVIDER=kimi
DEFAULT_MODEL=kimi-k2.5
```

---

## 使用方式

### Web UI 模式（推荐）

启动 Web 服务，在浏览器中交互：

```bash
uv run python -m aiagent.serve
# 打开 http://localhost:8765
```

界面功能：
- 实时 SSE 流式响应
- 可视化工具调用过程
- 支持多提供商/模型快速切换
- 对话历史管理
- **🛠️ Skill 管理面板**：分类展示技能，支持可视化创建
- **📋 任务进度面板**：实时显示 todo 列表
- **🔒 安全提示**：危险操作前显示警告

### CLI 模式

#### 查看可用模型

```bash
uv run python -m aiagent.main --list-models
# 或简写
uv run python -m aiagent.main -l
```

#### 启动对话

```bash
# 使用默认提供商
uv run python -m aiagent.main

# 指定提供商
uv run python -m aiagent.main --provider qwen
uv run python -m aiagent.main -p azure

# 指定具体模型
uv run python -m aiagent.main --provider qwen --model qwen3-coder-plus
```

---

## 工具列表（13+ 个）

| 工具 | 类型 | 描述 |
|------|------|------|
| `exec` | 内置 | 执行 shell 命令，返回 stdout/stderr/exit_code |
| `read` | 内置 | 读取文件，支持 offset/limit 分页 |
| `write` | 内置 | 写文件，自动创建父目录 |
| `edit` | 内置 | 精准替换文件中的唯一字符串（old_str → new_str） |
| `apply_patch` | 内置 | 应用 unified diff patch |
| `process` | 内置 | 后台进程管理（start/list/log/kill） |
| `web_fetch` | 内置 | 抓取 URL 内容，HTML 自动转纯文本 |
| `web_search` | 内置 | DuckDuckGo 搜索（无需 API Key） |
| `memory_search` | 内置 | 持久化记忆（save/search/read/clear） |
| `image` | 内置 | 用视觉模型分析本地图片或 URL |
| `pdf` | 内置 | 提取 PDF 文本并用 LLM 分析（需 `pdfminer.six`） |
| `tts` | 内置 | 文字转语音（macOS say 零依赖，或 OpenAI TTS） |
| `browser` | 内置 | Playwright 控制浏览器（需 `playwright`） |
| `cron` | 内置 | 本地定时任务（at/every/cron 三种调度类型） |
| `sessions_spawn` | 动态 | 派生子 Agent，立即返回 run_id |
| `subagents` | 动态 | 管理本 session 的子 Agent（list/kill/steer） |
| `daily_log` | 内置 | 每日日志自动摘要 |

---

## Skill 系统

### 三级安全架构

| 级别 | 目录 | 信任度 | 徽章 | 说明 |
|------|------|--------|------|------|
| **System** | `skills/system/` | 🟢 完全信任 | 绿色 | 14个内置技能，经过安全审核 |
| **User** | `skills/user/` | 🔵 基本信任 | 蓝色 | 用户通过向导创建的技能 |
| **Market** | `skills/market/` | 🟡 需检查 | 黄色 | 第三方技能，自动安全扫描 |

### 内置 Skills（14个）

| Skill | 功能 |
|-------|------|
| `research` | **4阶段系统化研究**：广度探索 → 深度挖掘 → 多角度验证 → 综合检查 |
| `find-skills` | 技能发现与安装指南 |
| `skill-creator` | 通过向导创建新技能 |
| `coding-agent` | 专业编程助手 |
| `github` / `gh-issues` | GitHub 操作与 Issue 管理 |
| `summarize` | 内容摘要生成 |
| `weather` | 天气查询 |
| `obsidian` | Obsidian 笔记集成 |
| `nano-pdf` | PDF 处理 |
| `peekaboo` | 系统监控 |
| `session-logs` | 会话日志分析 |
| `tmux` | Tmux 会话管理 |
| `xurl` | URL 处理工具 |

### 创建新 Skill

**方式一：Web UI 向导（推荐）**

1. 打开 Web UI，点击「🛠️ Skills」面板
2. 点击「创建新 Skill」
3. 选择模板（空白/工作流程/工具集合/参考指南/能力模块）
4. 填写名称、描述、内容
5. 选择存储位置（User 或 Market）

**方式二：手动创建**

在 `skills/user/` 或 `skills/market/` 目录下新建 `<name>/SKILL.md`：

```markdown
---
name: my-skill
description: 一句话描述这个 skill 的用途
---

# My Skill

这里是详细使用说明，Agent 需要时会完整读取这段内容。
```

Agent 启动时会自动扫描所有 skill 的 frontmatter 摘要注入 system prompt，用户提到相关需求时 Agent 会主动 `read` 对应 SKILL.md 获取完整指引。

---

## 安全机制

### 代码安全扫描

Skill 加载时自动扫描危险代码模式：

| 检测项 | 模式 | 风险等级 |
|--------|------|----------|
| 强制删除 | `rm -rf /` | 🔴 高危 |
| 管道执行 | `curl \| sh` | 🔴 高危 |
| 动态执行 | `eval()` | 🟠 中危 |
| 系统调用 | `os.system()` | 🟠 中危 |
| 子进程 Shell | `subprocess.*shell=True` | 🟠 中危 |

扫描结果：
- 🟢 安全：无危险模式
- 🟡 警告：发现可疑代码
- 🔴 危险：发现高危模式

### 子 Agent 隔离

- **Workspace 隔离**：每个子 Agent 独立工作目录
- **最大嵌套深度**：3 层
- **并行限制**：每个父 Agent 最多 5 个子 Agent
- **自动清理**：子 Agent 完成后资源回收

---

## 记忆系统

分离式记忆架构：

| 组件 | 文件 | 用途 |
|------|------|------|
| 用户画像 | `workspace/USER.md` | 用户偏好、背景、习惯 |
| 结构化记忆 | `workspace/MEMORY.md` | 关键信息、待办事项 |
| 每日日志 | `workspace/memory/YYYY-MM-DD.md` | 自动摘要的历史对话 |
| 会话存储 | `data/sessions/*.json` | 持久化对话历史 |

---

## 目录结构

```
aiagent/
├── aiagent/                   # Python 包（核心代码）
│   ├── main.py                # CLI 入口
│   ├── serve.py               # Web UI HTTP 服务
│   ├── web_ui.html            # Web UI 前端
│   ├── agent.py               # LLM tool-use 主循环
│   ├── skills.py              # Skill 扫描器（三级架构）
│   ├── skill_security.py      # 安全扫描器
│   ├── subagent.py            # 子 Agent 派生与管理
│   ├── subagent_registry.py   # 注册中心（内存 + 磁盘）
│   ├── subagent_tools.py      # 子 Agent 相关工具
│   ├── session_manager.py     # 会话管理
│   ├── workspace.py           # system prompt 拼装
│   └── tools/                 # 工具实现
│       ├── exec.py            # shell 执行
│       ├── file.py            # read/write/edit/apply_patch
│       ├── process.py         # 后台进程管理
│       ├── web.py             # web_fetch/web_search
│       ├── memory.py          # 持久化记忆
│       ├── daily_log.py       # 每日日志
│       ├── image.py           # 图片视觉分析
│       ├── pdf.py             # PDF 提取
│       ├── tts.py             # 文字转语音
│       ├── browser.py         # Playwright 浏览器控制
│       ├── cron.py            # 定时任务
│       └── git_enhanced.py    # Git 操作
│
├── skills/                    # Skill 目录（三级结构）
│   ├── system/                # 14个系统技能
│   │   ├── research/          # 4阶段研究能力
│   │   ├── find-skills/       # 技能发现
│   │   ├── skill-creator/     # 技能创建向导
│   │   └── ...                # 其他11个技能
│   ├── user/                  # 用户技能（通过向导创建）
│   └── market/                # 第三方技能（自动安全扫描）
│
├── workspace/                 # Agent 身份与配置
│   ├── IDENTITY.md            # Agent 身份定义
│   ├── SOUL.md                # 行为原则
│   ├── TOOLS.md               # 工具说明
│   ├── MEMORY.md              # 结构化记忆文件
│   ├── AGENTS.md              # 子 Agent 使用指南
│   ├── BOOTSTRAP.md           # 启动检查清单
│   └── USER.md                # 用户偏好档案
│
├── data/                      # 数据目录
│   └── sessions/              # 会话存储
│
├── tests/                     # 测试套件
│   ├── README.md
│   ├── run_all.py
│   ├── test_tools_basic.py
│   ├── test_skills.py
│   ├── test_skill_security.py
│   └── ...
│
├── .env                       # API Key 配置（不提交）
├── .env.example               # 配置示例
└── pyproject.toml
```

---

## 测试

```bash
# 全部测试（需要 API Key）
uv run python tests/run_all.py

# 只跑本地测试（无需 API Key）
uv run python tests/run_all.py --no-llm

# 单独运行某项
uv run python tests/test_tools_basic.py
uv run python tests/test_skills.py
uv run python tests/test_skill_security.py
```

详见 [tests/README.md](tests/README.md)。

---

## 多提供商实现原理

```
.env 配置
    ↓
serve.py / main.py 读取配置
    ↓
┌─────────────────────────────────────────┐
│  Kimi          Qwen           Azure     │
│  (OpenAI SDK)  (OpenAI SDK)   (Azure)   │
│                                         │
│  base_url      base_url       endpoint  │
│  api_key       api_key        api_key   │
│  model         model          deployment│
└─────────────────────────────────────────┘
    ↓
Agent.run() → LLM API 调用
```

- Kimi 和 Qwen 使用标准 OpenAI SDK（兼容模式）
- Azure 使用 AzureOpenAI SDK（特殊处理 endpoint + deployment）
- Web UI 通过 `/config` API 动态获取可用提供商和模型
- CLI 通过 `--provider` 和 `--model` 参数切换

---

## 贡献

欢迎提交 Issue 和 PR！

### 添加新 Skill

1. 在 `skills/user/` 目录下创建 `<skill-name>/SKILL.md`
2. 使用 Web UI 向导创建（推荐）
3. 运行测试确保无安全问题

### 代码规范

- 遵循 PEP 8
- 添加类型注解
- 编写单元测试
