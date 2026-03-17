# aiagent 测试套件

## 目录结构

```
tests/
├── README.md              # 本文件
├── run_all.py             # 一键运行所有测试的入口
├── test_tools_basic.py    # 基础工具单元测试（无需 API Key）
├── test_skills.py         # Skill 系统测试（无需 API Key）
├── test_new_tools.py      # 新增工具测试：image/pdf/tts/browser/cron（无需 API Key）
├── test_e2e_llm.py        # 端到端 LLM 测试（需要 API Key）
└── test_subagent.py       # 子 Agent 测试（需要 API Key）
```

---

## 快速开始

### 运行全部测试

```bash
uv run python tests/run_all.py
```

### 只跑不需要 API Key 的测试

```bash
uv run python tests/run_all.py --no-llm
```

### 单独运行某个测试文件

```bash
uv run python tests/test_tools_basic.py
uv run python tests/test_skills.py
uv run python tests/test_new_tools.py
uv run python tests/test_e2e_llm.py
uv run python tests/test_subagent.py
```

---

## 测试说明

### `test_tools_basic.py` — 基础工具单元测试

**无需 LLM API Key**，直接调用工具 handler，验证每个工具的输入输出。

| 测试组 | 覆盖内容 |
|--------|----------|
| exec   | echo 输出、ls 命令、非零 exit_code、超时捕获 |
| read/write | 写文件、读全文、offset/limit 分页、读不存在文件的错误处理 |
| edit | 精准替换、找不到 old_str 的错误处理 |
| apply_patch | unified diff 应用、内容验证 |
| process | start 后台进程、list 状态、log 日志、kill 进程 |
| memory_search | save 记忆、search 检索 |

---

### `test_skills.py` — Skill 系统测试

**无需 LLM API Key**，验证 skill 扫描与 system prompt 注入。

| 测试组 | 覆盖内容 |
|--------|----------|
| skill scan | 扫描 `skills/` 目录，验证数量 ≥ 10，必须存在 weather/github/tmux/summarize |
| system prompt | 包含 Available Skills 段落，包含 weather/github 摘要 |
| 自定义 skill 目录 | 临时目录创建自定义 SKILL.md，验证能被正确扫描到 |

---

### `test_new_tools.py` — 新增工具测试

**基本无需 API Key**（image/pdf LLM 部分需要），验证新增的 5 个工具。

| 测试组 | 覆盖内容 |
|--------|----------|
| 工具注册 | 验证全部 14 个内置工具都已注册 |
| tts | macOS say 保存 .aiff 文件、文件存在验证 |
| browser | playwright 状态检查；已安装时测试 open/snapshot/close |
| cron | status/add/list/run/remove 完整流程 |
| image | 本地文件上传分析（需 API Key）；无参数错误处理 |
| pdf | 无参数错误处理；pdfminer 未安装提示 |

---

### `test_e2e_llm.py` — 端到端 LLM 测试

**需要有效的 `OPENAI_API_KEY`**，验证完整的用户 query → Agent 执行 → 回复流程。

| Case | 验证内容 |
|------|----------|
| Case 1 | exec + 回复：Agent 能调用 exec 工具并把结果反映在回复里 |
| Case 2 | write → read → 校验：Agent 能连续使用两个工具完成任务 |
| Case 3 | 创建 Python 文件并执行：多步任务，write 后用 exec 运行 |
| Case 4 | edit 工具：Agent 能理解并使用 edit 精准替换文件内容 |
| Case 5 | 多轮对话：第二轮能记住第一轮提到的信息 |

---

### `test_subagent.py` — 子 Agent 测试

**需要有效的 `OPENAI_API_KEY`**，验证父子 Agent 多层协作机制。

| Case | 验证内容 |
|------|----------|
| Case 1 | spawn → 等待结果：父 Agent 派生子 Agent，等子 Agent 完成并拿到结果 |
| Case 2 | agents_list：列出全局所有 Agent 运行记录 |
| Case 3 | subagents list：spawn 后立刻查看子 Agent 状态 |

---

## 前置条件

1. 已安装依赖：`uv sync`
2. 配置 `.env`（参考 `.env.example`）：
   ```
   OPENAI_API_KEY=sk-...
   OPENAI_BASE_URL=https://api.moonshot.cn/v1
   MODEL=kimi-k2-0711-preview
   ```
3. 可选依赖（按需安装）：
   ```bash
   uv add pdfminer.six          # pdf 工具
   uv add playwright            # browser 工具
   uv run playwright install chromium
   uv add croniter              # cron 工具支持 cron 表达式
   ```

