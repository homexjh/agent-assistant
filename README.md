# aiagent

基于多 LLM 提供商（Kimi/Qwen/Azure）的自主 AI Agent 运行时。用户 query 进来，Agent 通过 tool-use 主循环执行 shell 命令、读写文件、抓取网页、管理后台进程、调用子 Agent 等，完成复杂多步任务。

---

## 特性

- **多 LLM 提供商支持**：Kimi (Moonshot)、通义千问 (Qwen)、Azure OpenAI
- **Web UI + CLI 双模式**：浏览器可视化交互 或 命令行对话
- **18+ 内置工具**：代码执行、文件操作、网页抓取、浏览器控制、定时任务等
- **子 Agent 并行**：支持派生子 Agent 异步执行任务
- **Skill 扩展**：通过 Markdown 文件扩展 Agent 能力

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
                    ↓
        LLM tool-use 主循环
                    ↓
    ┌───────────────┼───────────────┐
    ↓               ↓               ↓
  工具执行       子 Agent        LLM 调用
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
- 支持多提供商切换
- 支持多模型选择
- 对话历史管理

### CLI 模式

#### 查看可用模型

```bash
uv run python -m aiagent.main --list-models
# 或简写
uv run python -m aiagent.main -l
```

输出示例：
```
=== AIAgent 可用模型列表 ===

KIMI (默认) [✓]
  Base URL: https://api.moonshot.cn/v1
  可用模型:
    1. → kimi-k2.5
    2.    kimi-k2-0711-preview
    3.    moonshot-v1-8k

QWEN [✓]
  Base URL: https://dashscope.aliyuncs.com/compatible-mode/v1
  可用模型:
    1. → qwen3.5-plus
    2.    qwen3-max-2026-01-23
    3.    qwen3-coder-next
    4.    qwen3-coder-plus

AZURE [✗]
  Base URL: 未配置
  可用模型:
    1. → gpt-4o
```

标记说明：
- `[✓]` - API Key 已配置
- `[✗]` - API Key 未配置
- `→` - 默认模型

#### 启动对话

```bash
# 使用默认提供商
uv run python -m aiagent.main

# 指定提供商
uv run python -m aiagent.main --provider qwen
uv run python -m aiagent.main -p azure

# 指定具体模型
uv run python -m aiagent.main --provider qwen --model qwen3-coder-plus
uv run python -m aiagent.main -p kimi -m kimi-k2-0711-preview
```

---

## 工具列表（18+ 个）

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
| `sessions_send` | 动态 | 向任意子 Agent 发送 steer 指令 |
| `agents_list` | 动态 | 列出全局所有 Agent 运行记录 |

---

## 目录结构

```
aiagent/
├── aiagent/                   # Python 包（核心代码）
│   ├── main.py                # CLI 入口
│   ├── serve.py               # Web UI HTTP 服务
│   ├── web_ui.html            # Web UI 前端
│   ├── agent.py               # LLM tool-use 主循环
│   ├── subagent.py            # 子 Agent 派生与管理
│   ├── subagent_registry.py   # 注册中心（内存 + 磁盘持久化）
│   ├── subagent_tools.py      # 子 Agent 相关工具
│   ├── skills.py              # Skill 扫描与加载
│   ├── workspace.py           # system prompt 拼装
│   └── tools/                 # 工具实现
│       ├── exec.py            # shell 执行
│       ├── file.py            # read/write/edit/apply_patch
│       ├── process.py         # 后台进程管理
│       ├── web.py             # web_fetch/web_search
│       ├── memory.py          # 持久化记忆
│       ├── image.py           # 图片视觉分析
│       ├── pdf.py             # PDF 提取
│       ├── tts.py             # 文字转语音
│       ├── browser.py         # Playwright 浏览器控制
│       ├── cron.py            # 定时任务
│       └── git_enhanced.py    # Git 操作
│
├── workspace/                 # Agent 身份与配置
│   ├── IDENTITY.md            # Agent 身份定义
│   ├── SOUL.md                # 行为原则
│   ├── TOOLS.md               # 工具说明
│   ├── MEMORY.md              # 持久化记忆文件
│   ├── AGENTS.md              # 子 Agent 使用指南
│   ├── BOOTSTRAP.md           # 启动检查清单
│   └── USER.md                # 用户偏好档案
│
├── skills/                    # 可扩展技能
│   ├── weather/SKILL.md
│   ├── github/SKILL.md
│   └── ...
│
├── tests/                     # 测试套件
│   ├── README.md
│   ├── run_all.py
│   ├── test_tools_basic.py
│   ├── test_skills.py
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
```

详见 [tests/README.md](tests/README.md)。

---

## Skill 系统

在 `skills/` 目录下新建 `<name>/SKILL.md`，格式：

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

## 子 Agent

父 Agent 通过 `sessions_spawn` 工具派生子 Agent 异步执行任务，子 Agent 完成后通过 announce 队列通知父 Agent。

安全限制：
- 最大嵌套深度：3 层
- 每个父 Agent 最多同时持有 5 个子 Agent

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
