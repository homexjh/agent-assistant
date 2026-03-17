# aiagent 超详细任务拆解

---

## Phase 1: MVP 核心 (Day 1-10)

---

### Day 1: 项目初始化 (8小时)

#### 任务 1.1: 创建项目目录结构 (1小时)
```bash
# 执行的命令
mkdir -p aiagent/{tools,skills,workspace}
mkdir -p tests/{unit,integration,e2e}
touch aiagent/__init__.py
touch aiagent/tools/__init__.py
touch tests/__init__.py
```
**产出文件**:
- `aiagent/__init__.py`
- `aiagent/tools/__init__.py`
- `aiagent/tools/types.py` (空)
- `aiagent/agent.py` (空)
- `aiagent/main.py` (空)
- `tests/__init__.py`

#### 任务 1.2: 编写 pyproject.toml (1.5小时)
**具体内容**:
```toml
[project]
name = "aiagent"
version = "0.1.0"
description = "Lightweight AI Agent with tool-use capabilities"
requires-python = ">=3.11"
dependencies = [
    "openai>=1.0.0",
    "python-dotenv>=1.0.0",
    "aiohttp>=3.9.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "black>=24.0.0",
    "ruff>=0.3.0",
    "mypy>=1.8.0",
]
```
**产出文件**: `pyproject.toml`

#### 任务 1.3: 创建环境配置文件 (0.5小时)
**产出文件**:
- `.env.example` (OPENAI_API_KEY, OPENAI_BASE_URL, MODEL)
- `.gitignore` (Python标准)
- `.env` (本地，不提交)

#### 任务 1.4: README 框架 (1小时)
**必须包含**:
- 项目简介
- 安装步骤
- 快速开始
- 目录结构说明
**产出文件**: `README.md`

#### 任务 1.5: 初始化 Git 并提交 (0.5小时)
```bash
git init
git add .
git commit -m "Initial commit: project structure"
```

#### 任务 1.6: 安装依赖并验证 (1小时)
```bash
uv sync
python -c "import aiagent; print('OK')"
```

#### 任务 1.7: 创建 Makefile (1小时)
**目标**:
- `make install` - 安装依赖
- `make test` - 运行测试
- `make format` - 代码格式化
- `make lint` - 代码检查
- `make run` - 启动 CLI

#### 任务 1.8: GitHub Actions CI (1.5小时)
**产出文件**: `.github/workflows/ci.yml`
**必须包含**:
- Python 3.11/3.12 测试矩阵
- 代码格式检查 (black)
- 类型检查 (mypy)
- 测试覆盖率

**Day 1 验收标准**:
- [ ] `uv sync` 成功
- [ ] `python -m aiagent` 可以运行（虽然还是空的）
- [ ] CI 能通过基础检查
- [ ] Git 提交成功

---

### Day 2: LLM 客户端封装 (8小时)

#### 任务 2.1: 创建 llm.py 框架 (1小时)
**产出文件**: `aiagent/llm.py`
**类结构**:
```python
class LLMClient:
    def __init__(self, api_key, base_url, model)
    async def chat(self, messages, tools, stream)
    async def chat_stream(self, messages, tools)
    def _build_request(self, messages, tools)
```

#### 任务 2.2: 实现 __init__ 和配置加载 (1.5小时)
**代码要求**:
- 从环境变量读取配置
- 默认值处理
- 配置验证（检查空值）
- 详细错误提示

#### 任务 2.3: 实现 chat 方法 (非流式) (2小时)
**必须处理**:
- 异常: APIError
- 异常: RateLimitError
- 异常: Timeout
- 重试机制 (指数退避, 最多3次)
- 返回统一格式

#### 任务 2.4: 实现 chat_stream 方法 (2小时)
**必须处理**:
- 解析 SSE 流
- 处理工具调用流
- 处理 content 流
- 错误处理

#### 任务 2.5: 编写单元测试 (1.5小时)
**测试文件**: `tests/unit/test_llm.py`
**测试用例** (至少5个):
1. `test_chat_success` - 正常调用
2. `test_chat_with_tools` - 带工具调用
3. `test_chat_api_error` - API错误重试
4. `test_chat_stream_success` - 流式调用
5. `test_chat_invalid_config` - 配置错误

**使用 mock**: `unittest.mock.patch`

**Day 2 验收标准**:
- [ ] `pytest tests/unit/test_llm.py -v` 全部通过
- [ ] 可以独立运行测试脚本测试 LLM 调用
- [ ] 流式和非流式都工作正常

---

### Day 3: 工具系统基础 (8小时)

#### 任务 3.1: 定义工具类型 (1.5小时)
**产出文件**: `aiagent/tools/types.py`
**必须包含**:
```python
class ToolParameter(TypedDict):
    type: str
    description: str
    enum: list[str]  # optional

class ToolFunction(TypedDict):
    name: str
    description: str
    parameters: dict

class ToolDefinition(TypedDict):
    type: str
    function: ToolFunction

class RegisteredTool:
    def __init__(self, definition, handler)
    @property
    def name(self) -> str
```

#### 任务 3.2: 创建工具注册中心 (2小时)
**产出文件**: `aiagent/tools/__init__.py`
**必须实现**:
```python
_registry: dict[str, RegisteredTool] = {}

def register_tool(tool: RegisteredTool) -> None
def get_tool_definitions() -> list[ToolDefinition]
def get_tool(name: str) -> RegisteredTool | None
async def execute_tool(tool_call_id, name, arguments) -> dict
```

#### 任务 3.3: 实现 exec 工具 (2小时)
**产出文件**: `aiagent/tools/exec.py`
**功能要求**:
- 执行 shell 命令
- 参数: command, cwd, timeout
- 返回: stdout, stderr, exit_code
- 超时处理 (默认30秒)
- 错误处理: 命令不存在、权限错误

**代码行数**: ~60行

#### 任务 3.4: 注册 exec 工具并测试 (1.5小时)
```python
# 在 tools/__init__.py 中
from .exec import exec_tool
register_tool(exec_tool)
```

**测试文件**: `tests/unit/tools/test_exec.py`
**测试用例**:
1. `test_exec_echo` - 简单命令
2. `test_exec_with_cwd` - 指定工作目录
3. `test_exec_timeout` - 超时处理
4. `test_exec_not_found` - 命令不存在
5. `test_exec_error_exit` - 非零退出码

#### 任务 3.5: 集成验证 (1小时)
**脚本**: `scripts/test_tools.py`
```python
async def main():
    definitions = get_tool_definitions()
    print(f"Registered tools: {[t['function']['name'] for t in definitions]}")
    # 执行测试命令
```

**Day 3 验收标准**:
- [ ] `get_tool_definitions()` 返回 exec 工具
- [ ] `execute_tool` 可以执行 shell 命令
- [ ] 所有 exec 工具测试通过
- [ ] 超时功能正常工作

---

### Day 4: Tool-Use 主循环 (8小时)

#### 任务 4.1: 创建 Agent 类框架 (1小时)
**产出文件**: `aiagent/agent.py`
```python
class Agent:
    def __init__(self, model, api_key, base_url)
    async def run(self, user_message, history) -> str
    async def _execute_tool_calls(self, tool_calls) -> list[dict]
    async def _execute_single_tool(self, tool_call) -> dict
```

#### 任务 4.2: 实现 Agent.__init__ (1.5小时)
**必须完成**:
- 初始化 LLMClient
- 加载工具定义列表
- 设置系统 prompt
- 创建消息历史管理

#### 任务 4.3: 实现主循环 run 方法 (3小时)
**伪代码**:
```python
async def run(self, user_message, history):
    messages = self._build_messages(user_message, history)
    
    for round_i in range(MAX_TOOL_ROUNDS):  # 30轮
        response = await self.llm.chat(messages, self.tools)
        
        if response.tool_calls:
            tool_results = await self._execute_tool_calls(response.tool_calls)
            messages.extend(tool_results)
            continue
        
        return response.content
```

**必须处理**:
- 消息格式转换
- 工具调用结果添加到历史
- 最大轮数限制
- 异常情况

#### 任务 4.4: 实现工具调用执行 (1.5小时)
**_execute_tool_calls**:
- 并行执行 (asyncio.gather)
- 错误收集
- 结果格式化

**_execute_single_tool**:
- 解析 JSON 参数
- 调用 execute_tool
- 错误包装

#### 任务 4.5: 编写集成测试 (1小时)
**测试文件**: `tests/integration/test_agent.py`
**测试用例**:
1. `test_agent_simple_response` - 无需工具的对话
2. `test_agent_single_tool` - 单次工具调用
3. `test_agent_multiple_tools` - 并行工具调用
4. `test_agent_tool_chain` - 工具调用链
5. `test_agent_max_rounds` - 最大轮数限制

**使用 mock LLM**: 预设响应

**Day 4 验收标准**:
- [ ] Agent 可以完成无需工具的对话
- [ ] Agent 可以执行单次工具调用
- [ ] Agent 可以并行执行多个工具
- [ ] 主循环测试全部通过

---

### Day 5: 文件操作工具 (8小时)

#### 任务 5.1: 实现 read 工具 (1.5小时)
**产出文件**: `aiagent/tools/file.py` (read部分)
**功能**:
- 参数: path, offset, limit
- 支持大文件分页读取
- 错误处理: 文件不存在、权限错误
- 返回文件内容和元数据

#### 任务 5.2: 实现 write 工具 (1.5小时)
**功能**:
- 参数: path, content
- 自动创建父目录
- 错误处理: 目录创建失败、写入失败
- 返回写入结果

#### 任务 5.3: 实现 edit 工具 (2小时)
**功能**:
- 参数: path, old_str, new_str
- 检查 old_str 唯一性
- 支持多行字符串
- 详细错误信息

**难点**: 多行字符串匹配

#### 任务 5.4: 注册工具并测试 (1.5小时)
**测试文件**: `tests/unit/tools/test_file.py`
**测试用例** (至少6个):
1. `test_read_simple` - 读取文件
2. `test_read_with_offset_limit` - 分页读取
3. `test_read_not_found` - 文件不存在
4. `test_write_new_file` - 创建新文件
5. `test_write_create_dirs` - 自动创建目录
6. `test_edit_simple` - 简单替换
7. `test_edit_multiline` - 多行替换
8. `test_edit_not_unique` - 非唯一匹配

#### 任务 5.5: 端到端测试 (1.5小时)
**测试文件**: `tests/e2e/test_file_operations.py`
**场景**:
- "读取 README.md"
- "创建一个 Python 文件"
- "修改文件中的某行"

**Day 5 验收标准**:
- [ ] read/write/edit 三个工具可用
- [ ] 可以完成文件读写编辑的完整流程
- [ ] 所有文件工具测试通过

---

### Day 6: CLI 交互界面 (8小时)

#### 任务 6.1: 实现基础 CLI 框架 (1.5小时)
**产出文件**: `aiagent/main.py`
**功能**:
```python
def chat_loop():
    agent = Agent()
    history = []
    while True:
        user_input = input("you> ")
        if user_input in ("exit", "quit"):
            break
        reply = await agent.run(user_input, history)
        print(f"agent> {reply}")
        history.append(...)
```

#### 任务 6.2: 添加历史记录管理 (1.5小时)
**功能**:
- 维护多轮对话历史
- 历史长度限制 (防止超长)
- 历史持久化 (可选)

#### 任务 6.3: 添加命令支持 (1.5小时)
**支持命令**:
- `/exit` - 退出
- `/clear` - 清空历史
- `/history` - 显示历史
- `/tools` - 显示可用工具

**实现**: 命令拦截器

#### 任务 6.4: 添加日志输出 (1.5小时)
**功能**:
- 工具调用日志
- LLM 调用日志
- 错误日志
- 日志级别控制 (INFO/DEBUG)

#### 任务 6.5: 美化输出 (1小时)
**可选方案**:
- 使用 `rich` 库
- 代码高亮
- 工具调用可视化
- 思考过程显示

#### 任务 6.6: CLI 测试 (1小时)
**测试文件**: `tests/e2e/test_cli.py`
**使用**: `pexpect` 或 `subprocess` 模拟交互

**Day 6 验收标准**:
- [ ] 可以运行 `python -m aiagent.main` 进入交互
- [ ] 支持多轮对话
- [ ] 命令可以正常使用
- [ ] 工具调用有日志输出

---

### Day 7: 第一阶段验收 (8小时)

#### 任务 7.1: 端到端测试 (3小时)
**测试场景** (至少5个):
1. "你好" - 简单对话
2. "列出当前目录" - 执行shell
3. "读取 README.md 内容" - 读文件
4. "创建一个 hello.py 文件" - 写文件
5. "查看文件并总结" - 多工具链

#### 任务 7.2: Bug 修复 (2小时)
- 根据测试结果修复
- 边界情况处理
- 错误信息优化

#### 任务 7.3: 代码审查和重构 (2小时)
**检查项**:
- 代码风格一致性
- 函数长度 (<50行)
- 类型注解完整
- 文档字符串

#### 任务 7.4: 文档更新 (1小时)
- 更新 README
- 添加使用示例
- API 文档

**Day 7 验收标准**:
- [ ] 5个端到端场景全部通过
- [ ] 代码审查无重大问题
- [ ] README 文档完整
- [ ] 可以对外展示的基础版本

---

### Day 8: Web 工具 (8小时)

#### 任务 8.1: 实现 web_fetch 工具 (2.5小时)
**产出文件**: `aiagent/tools/web.py`
**功能**:
- HTTP GET 请求
- User-Agent 设置
- 超时处理
- HTML 转纯文本
- 错误处理 (404, 500, 超时)

**代码要求**:
```python
async def _web_fetch_handler(url, max_chars=8000, raw=False)
```

#### 任务 8.2: 实现 web_search 工具 (2.5小时)
**功能**:
- DuckDuckGo Lite 搜索
- 结果解析
- 返回标题/URL/摘要
- 支持指定结果数量

**难点**: 解析 HTML 结构

#### 任务 8.3: 编写 web 工具测试 (2小时)
**测试文件**: `tests/unit/tools/test_web.py`
**测试用例** (至少4个):
1. `test_fetch_google` - 抓取 Google
2. `test_fetch_with_redirect` - 重定向处理
3. `test_fetch_timeout` - 超时
4. `test_search_python` - 搜索 Python

**使用**: `responses` 库 mock HTTP

#### 任务 8.4: 集成验证 (1小时)
**手动测试**:
- 抓取几个网站
- 搜索几个关键词
- 检查输出格式

**Day 8 验收标准**:
- [ ] web_fetch 可以抓取网页
- [ ] web_search 可以搜索
- [ ] HTML 转文本效果良好
- [ ] 所有 web 工具测试通过

---

### Day 9: 进程管理工具 (8小时)

#### 任务 9.1: 实现 process_start (2小时)
**产出文件**: `aiagent/tools/process.py`
**功能**:
- 后台启动进程
- 生成进程 ID
- 记录启动时间
- 保存 stdout/stderr 到文件

#### 任务 9.2: 实现 process_list/kill/log (2小时)
**功能**:
- list: 列出所有管理中的进程
- kill: 终止指定进程
- log: 读取进程输出日志

#### 任务 9.3: 进程状态管理 (1.5小时)
**数据结构**:
```python
_processes: dict[str, dict] = {
    "proc_001": {
        "pid": 12345,
        "command": "python server.py",
        "started_at": 1234567890,
        "log_file": "/tmp/proc_001.log",
        "status": "running"
    }
}
```

#### 任务 9.4: 测试 (2小时)
**测试文件**: `tests/unit/tools/test_process.py`
**测试用例**:
1. `test_start_process` - 启动进程
2. `test_list_processes` - 列出进程
3. `test_kill_process` - 终止进程
4. `test_read_log` - 读取日志

**Day 9 验收标准**:
- [ ] 可以后台启动长期运行的进程
- [ ] 可以查看进程列表
- [ ] 可以读取进程输出
- [ ] 可以终止进程

---

### Day 10: 浏览器工具基础 (8小时)

#### 任务 10.1: Playwright 环境准备 (1小时)
```bash
uv add playwright
uv run playwright install chromium
```

#### 任务 10.2: 浏览器状态管理 (1.5小时)
**产出文件**: `aiagent/tools/browser.py`
**全局状态**:
```python
_browser = None
_page = None
_playwright = None
_screenshot_dir = None
_step_counter = 0
```

#### 任务 10.3: 实现基础操作 (2.5小时)
**功能**:
- status: 检查状态
- open: 打开 URL
- close: 关闭浏览器
- 截图功能

#### 任务 10.4: 实现高级操作 (2小时)
**功能**:
- snapshot: 获取页面文本
- navigate: 导航到URL
- screenshot: 手动截图

#### 任务 10.5: 测试和验证 (1小时)
**手动测试**:
- 打开百度
- 获取页面文本
- 截图验证

**Day 10 验收标准**:
- [ ] 浏览器可以启动
- [ ] 可以打开网页
- [ ] 可以获取页面文本
- [ ] 截图功能正常

---

## Phase 2: 工具完善 (Day 11-20)

---

### Day 11: 浏览器工具高级功能 (8小时)

#### 任务 11.1: 实现 act 操作 (3小时)
**功能**:
- click: 点击元素
- fill: 输入文本
- press: 按键
- evaluate: 执行 JS

**参数设计**:
```python
action: str  # "click", "fill", "press", "evaluate"
selector: str  # CSS selector
value: str  # 输入值或按键
script: str  # JS 代码
```

#### 任务 11.2: 实现 scroll/tabs (1.5小时)
**功能**:
- scroll: 滚动页面
- tabs: 列出所有标签页

#### 任务 11.3: 自动截图功能 (1.5小时)
- 每个操作后自动截图
- 步骤计数器
- 截图命名规范

#### 任务 11.4: 浏览器工具测试 (2小时)
**测试文件**: `tests/unit/tools/test_browser.py`
**使用**: 本地启动简单 HTTP 服务器测试

**Day 11 验收标准**:
- [ ] 可以模拟用户操作
- [ ] 每个操作自动截图
- [ ] 可以切换标签页

---

### Day 12-14: 剩余工具实现 (3天)

#### Day 12: memory_search + apply_patch (8小时)
- memory_search: 本地记忆搜索
- apply_patch: unified diff 格式补丁

#### Day 13: image + pdf 工具 (8小时)
- image: 图片分析 (调用 vision 模型)
- pdf: PDF 文本提取

#### Day 14: tts + git_enhanced (8小时)
- tts: 文字转语音
- git_enhanced: Git 增强工具

---

## Phase 3: 子 Agent 系统 (Day 15-24)

---

### Day 15: 子 Agent 注册表 (8小时)

#### 任务 15.1: 定义数据模型 (2小时)
**产出文件**: `aiagent/subagent_registry.py`
```python
@dataclass
class SubagentRun:
    run_id: str
    parent_id: str
    task: str
    label: str
    model: str
    created_at: float
    started_at: float | None
    ended_at: float | None
    outcome: dict | None
    steer_messages: list[str]
```

#### 任务 15.2: 实现内存注册表 (2小时)
```python
_runs: dict[str, SubagentRun] = {}
_lock = threading.Lock()

def register_run(run: SubagentRun)
def mark_started(run_id: str)
def mark_ended(run_id: str, outcome: dict)
def list_runs(parent_id: str)
def get_run(run_id: str)
```

#### 任务 15.3: 实现持久化 (2小时)
- JSON 序列化
- 磁盘读写
- 启动时加载

#### 任务 15.4: 测试 (2小时)
**测试文件**: `tests/unit/test_subagent_registry.py`
**测试用例**:
1. 注册/查询
2. 状态更新
3. 持久化/加载
4. 线程安全

---

### Day 16: SubagentManager (8小时)

#### 任务 16.1: 实现 Manager 类 (3小时)
**产出文件**: `aiagent/subagent.py`
```python
class SubagentManager:
    def __init__(self, session_id)
    def bind_loop(self, loop)
    def announce(self, run_id, result)
    def count_active(self) -> int
```

#### 任务 16.2: 实现 announce 队列 (2小时)
- queue.Queue 使用
- 线程安全
- 消息格式定义

#### 任务 16.3: 实现 spawn_subagent (2小时)
```python
def spawn_subagent(task, label, model, parent_id, depth, manager, agent_factory):
    # 安全检查
    # 创建 run_id
    # 注册
    # 启动线程
    # 返回结果
}
```

#### 任务 16.4: 测试 (1小时)
- Manager 基础测试

---

### Day 17: 子 Agent 工具实现 (8小时)

#### 任务 17.1: sessions_spawn 工具 (3小时)
**产出文件**: `aiagent/subagent_tools.py`
- 工具定义 (schema)
- handler 实现
- 参数验证

#### 任务 17.2: subagents 工具 (2.5小时)
- action=list
- action=kill
- action=steer

#### 任务 17.3: 工具集成到 Agent (1.5小时)
- 在 Agent.__init__ 中创建工具
- 添加到 tools 列表

#### 任务 17.4: 测试 (1小时)
- 工具调用测试

---

### Day 18-19: 父子通信完善 (2天)

#### Day 18: sessions_send + agents_list (8小时)
- 跨 session 通信
- 全局 Agent 列表

#### Day 19: Steer 机制 (8小时)
- 父发送修正指令
- 子接收并执行
- 双向通信测试

---

### Day 20: 子 Agent 系统测试 (8小时)

#### 任务 20.1: 并行任务测试 (2小时)
- 启动多个子 Agent
- 验证并行执行

#### 任务 20.2: 深度限制测试 (2小时)
- 测试最大深度限制
- 错误提示

#### 任务 20.3: 数量限制测试 (2小时)
- 测试最大子 Agent 数量

#### 任务 20.4: 异常测试 (2小时)
- 子 Agent 崩溃
- 父 Agent 提前退出
- 资源清理

---

## Phase 4: Skill 系统 (Day 21-28)

---

### Day 21-22: Skill 扫描与加载 (2天)

#### Day 21: 基础实现 (8小时)
- frontmatter 解析
- SkillMeta 定义
- scan_skills 函数
- 测试

#### Day 22: 集成到 Agent (8小时)
- build_skills_summary
- 注入 system prompt
- 按需加载机制

---

### Day 23: 内置 Skill (8小时)
- coding-agent Skill
- github Skill
- weather Skill
- 测试和文档

---

### Day 24: Skill 系统测试 (8小时)
- 扫描测试
- 使用测试
- 边界测试

---

## Phase 5: Web UI (Day 25-32)

---

### Day 25: Web 服务基础 (8小时)
- HTTP Server 搭建
- 静态文件服务
- 路由设计
- 基础 HTML

---

### Day 26-27: SSE 实时流 (2天)

#### Day 26: 后端 SSE (8小时)
- /run 端点
- 事件类型定义
- 流式发送

#### Day 27: 前端事件处理 (8小时)
- EventSource
- 事件解析
- UI 更新

---

### Day 28-29: UI 美化 (2天)
- CSS 样式
- 消息气泡
- 代码高亮
- 工具调用可视化

---

### Day 30-31: 功能增强 (2天)
- 历史记录
- 停止按钮
- 模型选择
- 文件上传 (可选)

---

### Day 32: Web UI 测试 (8小时)
- 功能测试
- 兼容性测试
- 性能测试

---

## Phase 6: 定时任务 (Day 33-36)

---

### Day 33: Cron 核心 (8小时)
- 任务注册表
- 调度器线程
- 持久化

---

### Day 34: 任务执行 (8小时)
- exec 任务
- message 任务
- agent 任务

---

### Day 35: Web UI 集成 (8小时)
- Cron 管理界面
- 日志查看

---

### Day 36: Cron 测试 (8小时)
- 单元测试
- 集成测试
- 边界测试

---

## Phase 7: 测试与优化 (Day 37-44)

---

### Day 37-38: 单元测试完善 (2天)
- 所有模块测试
- 覆盖率 > 80%

---

### Day 39-40: 集成测试 (2天)
- 端到端测试
- 性能测试

---

### Day 41-42: Bug 修复 (2天)
- 测试发现的问题
- 边界情况

---

### Day 43: 性能优化 (8小时)
- 异步优化
- 内存优化

---

### Day 44: 文档完善 (8小时)
- API 文档
- 使用指南
- 示例

---

## Phase 8: 输入扩展 (Day 45-56)

---

### Day 45-46: 图片输入 (2天)
- Web 上传组件
- Vision 模型支持
- 图文混排

---

### Day 47-48: 语音输入 (2天)
- 录音组件
- Whisper API
- 语音输出

---

### Day 49-50: 文件拖拽 (2天)
- 拖拽上传
- 文件类型处理

---

### Day 51-54: 多模态 (4天)
- 复杂输入处理
- 上下文管理

---

### Day 55-56: 最终验收 (2天)
- 全面测试
- Bug 修复
- 发布准备

---

## 工作量统计

| Phase | 天数 | 核心功能 | 测试覆盖 | 文档 |
|-------|------|----------|----------|------|
| Phase 1 | 10 | MVP核心 | 单元+集成 | 基础 |
| Phase 2 | 10 | 14个工具 | 单元+集成 | 工具文档 |
| Phase 3 | 10 | 子Agent | 单元+集成+E2E | 架构文档 |
| Phase 4 | 4 | Skill系统 | 单元+集成 | Skill开发指南 |
| Phase 5 | 8 | Web UI | 集成+E2E | UI文档 |
| Phase 6 | 4 | 定时任务 | 单元+集成 | 使用说明 |
| Phase 7 | 8 | 测试优化 | 全覆盖 | 完整文档 |
| Phase 8 | 12 | 输入扩展 | 集成测试 | 扩展指南 |
| **总计** | **56** | **完整系统** | **>80%** | **完整** |

---

## 关键决策点

### Day 7 (Phase 1结束)
**决策**: MVP 是否可用？
- ✅ 继续 Phase 2
- ❌ 修复后再继续

### Day 20 (Phase 3结束)
**决策**: 子 Agent 稳定性
- ✅ 继续 Phase 4
- ❌ 优化后再继续

### Day 32 (Phase 5结束)
**决策**: Web UI 体验
- ✅ 继续 Phase 6
- ❌ 优化后再继续

### Day 44 (Phase 7结束)
**决策**: 是否发布 v1.0
- ✅ 准备发布
- ❌ 继续 Phase 8
