# aiagent

基于 kimi-k2 的自主 AI Agent 运行时。用户 query 进来，Agent 通过 tool-use 主循环执行 shell 命令、读写文件、抓取网页、管理后台进程、调用子 Agent 等，完成复杂多步任务。

---

## 架构总览

```
用户输入
    ↓
main.py (CLI 多轮对话)
    ↓
Agent.__init__()
  ├── build_system_prompt()    ← workspace/*.md + skills/ 摘要
  ├── get_tool_definitions()   ← 9 个内置工具 schema
  └── create_*_tool()          ← 4 个子 Agent 工具
    ↓
Agent.run(user_message, history)
  └── LLM tool-use 主循环（最多 30 轮）
        ├── 检查 steer 队列（父 Agent 修正指令）
        ├── LLM API 调用
        ├── 有 tool_calls → 并行 asyncio.gather 执行 → 继续
        ├── 无 tool_calls，announce_queue 非空 → 注入子 Agent 结果 → 继续
        └── 无 tool_calls，队列空 → 返回最终文本

SubAgent 派生：
  sessions_spawn → threading.Thread → asyncio.run(child_agent.run(task))
                                          └── 完成后 announce → 父的 Queue
```

---

## 工具列表（18 个）

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
| `image` | 内置 | 用视觉模型分析本地图片或 URL（kimi: 自动上传） |
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
│   ├── agent.py               # LLM tool-use 主循环
│   ├── subagent.py            # 子 Agent 派生与管理
│   ├── subagent_registry.py   # 注册中心（内存 + 磁盘持久化）
│   ├── subagent_tools.py      # 子 Agent 相关工具
│   ├── skills.py              # Skill 扫描与加载
│   ├── workspace.py           # system prompt 拼装
│   └── tools/
│       ├── exec.py            # shell 执行
│       ├── file.py            # read/write/edit/apply_patch
│       ├── process.py         # 后台进程管理
│       ├── web.py             # web_fetch/web_search
│       ├── memory.py          # 持久化记忆
│       ├── image.py           # 图片视觉分析
│       ├── pdf.py             # PDF 提取 + LLM 分析（需 pdfminer.six）
│       ├── tts.py             # 文字转语音（macOS say / OpenAI TTS）
│       ├── browser.py         # Playwright 浏览器控制（需 playwright）
│       └── cron.py            # 本地定时任务调度
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
├── skills/                    # 可扩展技能（12 个）
│   ├── weather/SKILL.md
│   ├── github/SKILL.md
│   ├── tmux/SKILL.md
│   └── ...
│
├── tests/                     # 测试套件
│   ├── README.md              # 测试说明
│   ├── run_all.py             # 一键运行入口
│   ├── test_tools_basic.py    # 基础工具测试（无需 API Key）
│   ├── test_skills.py         # Skill 系统测试（无需 API Key）
│   ├── test_new_tools.py      # 新增工具测试（无需 API Key）
│   ├── test_e2e_llm.py        # 端到端 LLM 测试
│   └── test_subagent.py       # 子 Agent 测试
│
├── .env                       # API Key 配置（不提交）
├── .env.example               # 配置示例
└── pyproject.toml
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

复制 `.env.example` 为 `.env` 并填入：

```
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.moonshot.cn/v1
MODEL=kimi-k2-0711-preview
```

### 3. 启动对话

```bash
# 方式一：uv run
uv run python -m aiagent.main

# 方式二：安装后直接使用命令
uv pip install -e .
aiagent
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
