# 从零构建 aiagent (达到现有架构水平)

**目标**: 从空目录开始，一步步实现出当前项目的完整功能
**最终状态**: 与现有代码同等级别的系统

---

## Week 1: 核心骨架 (Day 1-7)

### Day 1: 项目初始化 + LLM基础调用
**上午 (4h)**
- 创建项目目录结构 (`mkdir aiagent aiagent/tools tests workspace skills`)
- 编写 `pyproject.toml` (依赖: openai, python-dotenv)
- 配置 `.env` 文件 (API Key, Base URL, Model)
- 实现最简LLM调用测试脚本
  ```python
  import asyncio
  from openai import AsyncOpenAI
  
  async def test():
      client = AsyncOpenAI(api_key="...", base_url="...")
      resp = await client.chat.completions.create(
          model="kimi-k2-0711-preview",
          messages=[{"role": "user", "content": "hello"}]
      )
      print(resp.choices[0].message.content)
  
  asyncio.run(test())
  ```

**下午 (4h)**
- 封装 `LLMClient` 类
  - `__init__` 接收 api_key, base_url, model
  - `chat()` 方法封装调用
  - 添加重试机制 (最多3次，指数退避)
  - 异常处理 (APIError, Timeout)
- 编写测试验证LLM调用正常

**交付**: 能稳定调用LLM的基础模块
**代码量**: ~100行

---

### Day 2: 工具类型定义 + exec工具
**上午 (4h)**
- 设计工具类型系统
  ```python
  # aiagent/tools/types.py
  from typing import TypedDict, Callable, Awaitable
  
  class ToolDefinition(TypedDict):
      type: str  # "function"
      function: dict
  
  class RegisteredTool:
      def __init__(self, definition, handler):
          self.definition = definition
          self.handler = handler
      
      @property
      def name(self): 
          return self.definition["function"]["name"]
  ```
- 实现工具注册表
  ```python
  _registry: dict[str, RegisteredTool] = {}
  
  def register_tool(tool): 
      _registry[tool.name] = tool
  
  def get_tool_definitions():
      return [t.definition for t in _registry.values()]
  
  async def execute_tool(tool_call_id, name, arguments):
      # 解析JSON参数，调用handler，格式化结果
  ```

**下午 (4h)**
- 实现第一个工具 `exec`
  - 功能: 执行shell命令
  - 参数: command, cwd, timeout
  - 使用 subprocess.run
  - 返回 stdout/stderr/exit_code
  - 错误处理: 超时、命令不存在
- 注册 exec 工具
- 测试: 执行 `echo hello`, `ls -la`, 超时测试

**交付**: 可注册、可执行的exec工具
**代码量**: ~150行 (types + 注册表 + exec)

---

### Day 3: 文件操作工具 (read/write/edit)
**上午 (4h)**
- 实现 `read` 工具
  - 参数: path, offset, limit
  - 文件存在检查
  - 编码处理 (utf-8)
  - 分页读取实现
- 实现 `write` 工具
  - 参数: path, content
  - 自动创建父目录 (os.makedirs)
  - 原子写入 (临时文件+rename)

**下午 (4h)**
- 实现 `edit` 工具 (最复杂)
  - 参数: path, old_str, new_str
  - old_str 出现次数检查 (必须唯一)
  - 字符串替换
  - 多行字符串处理
  - 错误信息: "出现X次，请提供更多上下文"
- 实现 `apply_patch` 工具
  - 解析 unified diff 格式
  - hunk处理 (@@ -line,count +line,count @@)
  - 删除行(-)和添加行(+)处理
- 测试所有文件工具

**交付**: 完整的文件操作能力
**代码量**: ~300行

---

### Day 4: Tool-Use主循环 (核心)
**上午 (4h)**
- 实现 `Agent` 类框架
  ```python
  class Agent:
      def __init__(self, model, api_key, base_url):
          self.client = LLMClient(...)
          self.tools = get_tool_definitions()
      
      async def run(self, user_message, history=None):
          # 主循环实现
  ```
- 实现消息组装
  - system prompt (简单字符串)
  - history 拼接
  - user_message 添加

**下午 (4h)**
- 实现Tool-Use循环逻辑
  ```python
  MAX_ROUNDS = 30
  messages = [system] + history + [user]
  
  for round in range(MAX_ROUNDS):
      response = await self.client.chat(messages, self.tools)
      
      if response.tool_calls:
          # 并行执行所有工具
          results = await asyncio.gather(*[
              execute_tool(tc.id, tc.function.name, tc.function.arguments)
              for tc in response.tool_calls
          ])
          messages.extend(results)
      else:
          return response.content
  ```
- 处理 tool_calls 解析
- 处理执行结果添加到消息
- 测试: 能完成"读取文件并总结"这样的多轮任务

**交付**: 能自动调用工具的Agent
**代码量**: ~150行

---

### Day 5: CLI交互界面
**上午 (4h)**
- 实现 `main.py`
  ```python
  async def chat_loop():
      agent = Agent()
      history = []
      while True:
          user_input = input("you> ")
          if user_input in ("exit", "quit"):
              break
          reply = await agent.run(user_input, history)
          print(f"agent> {reply}")
          history.extend([...])
  ```
- 添加特殊命令支持
  - `/exit` - 退出
  - `/clear` - 清空历史
  - `/history` - 显示历史

**下午 (4h)**
- 添加日志输出
  - 打印工具调用信息
  - 打印每轮循环信息
  - 添加颜色区分 (可选)
- 添加错误处理
  - 捕获KeyboardInterrupt
  - 友好退出提示
  - 错误信息展示
- 测试完整交互流程

**交付**: 可用的命令行界面
**代码量**: ~100行

---

### Day 6: 更多工具 (web + process)
**上午 (4h)**
- 实现 `web_fetch` 工具
  - urllib 请求网页
  - User-Agent设置
  - HTML转文本 (正则去标签)
  - 编码检测
  - 返回内容截断
- 实现 `web_search` 工具
  - DuckDuckGo Lite请求
  - HTML解析提取结果 (正则)
  - 格式化输出 (标题/URL/摘要)

**下午 (4h)**
- 实现 `process` 工具
  - start: 后台启动进程 (subprocess.Popen)
  - list: 列出管理的进程
  - log: 读取进程输出文件
  - kill: 终止进程
  - 进程状态管理字典
- 测试所有新工具

**交付**: 网络操作和进程管理能力
**代码量**: ~250行

---

### Day 7: 第一阶段验收
**全天 (8h)**
- 编写测试用例
  - exec工具测试
  - 文件工具测试
  - Agent集成测试
  - CLI测试
- 端到端场景测试
  - "创建一个Python文件并运行"
  - "搜索Python教程"
  - "启动后台进程并监控"
- Bug修复
- 代码清理和注释

**交付**: 稳定可用的基础Agent (CLI版)
**总代码量**: ~1000行

---

## Week 2: 高级工具 + 子Agent基础 (Day 8-14)

### Day 8: browser工具 (复杂)
**上午 (4h)**
- 添加 playwright 依赖
- 实现 browser 状态管理 (全局变量)
- 实现基础操作
  - status: 检查浏览器状态
  - open: 打开URL (playwright启动)
  - close: 关闭浏览器

**下午 (4h)**
- 实现页面操作
  - snapshot: 获取页面文本 (JS执行)
  - navigate: 导航到URL
  - screenshot: 截图
  - 自动截图 (每个操作后)
- 实现 _ensure_browser 辅助函数
- 测试: 打开百度、截图、获取文本

**交付**: 浏览器自动化能力
**代码量**: ~300行

---

### Day 9: browser工具 (高级操作)
**全天 (8h)**
- 实现 `act` 操作 (最复杂)
  - 参数: action, selector, value
  - click: 点击元素
  - fill: 填写输入框
  - press: 按键
  - evaluate: 执行JS
- 实现 `scroll` 操作
- 实现 `tabs` 操作 (列出标签页)
- 实现自动截图保存
- 错误处理: 元素不存在、超时

**交付**: 完整的浏览器工具
**代码量**: ~200行 (累计browser 500行)

---

### Day 10: 其他工具 (pdf/image/tts/cron)
**上午 (4h)**
- 实现 `pdf` 工具
  - 使用 pdfminer.six 提取文本
  - 可选依赖处理
- 实现 `image` 工具
  - 调用Vision模型分析图片
  - Base64编码图片
- 实现 `tts` 工具
  - macOS say命令
  - OpenAI TTS备选

**下午 (4h)**
- 实现 `cron` 工具 (复杂)
  - 任务注册表 (全局字典)
  - 调度器线程 (每秒检查)
  - 支持 at/every/cron 三种调度
  - 任务持久化 (JSON文件)
  - 支持 exec/agent 任务类型
- 实现 `memory_search` 工具 (简单版本)
  - 关键词搜索
  - 或基于文件的简单存储

**交付**: 完整的工具集 (14个工具)
**代码量**: ~400行

---

### Day 11: 子Agent注册表设计
**上午 (4h)**
- 设计子Agent数据模型
  ```python
  @dataclass
  class SubagentRun:
      run_id: str  # uuid
      parent_id: str
      task: str
      label: str
      model: str
      created_at: float
      started_at: Optional[float]
      ended_at: Optional[float]
      outcome: Optional[dict]
      steer_messages: list[str]
  ```
- 实现内存注册表
  ```python
  _runs: dict[str, SubagentRun] = {}
  _lock = threading.Lock()
  ```
- 实现基本CRUD
  - register_run()
  - mark_started()
  - mark_ended()
  - list_runs()

**下午 (4h)**
- 实现JSON持久化
  - 存储路径: `.subagent_registry.json`
  - _persist() 函数
  - load_from_disk() 启动加载
  - 文件锁防并发写入
- 实现查询接口
  - get_run(run_id)
  - list_runs(parent_id)
  - all_runs()

**交付**: 子Agent注册中心
**代码量**: ~150行

---

### Day 12: 子Agent派生机制
**上午 (4h)**
- 设计 `SubagentManager` 类
  ```python
  class SubagentManager:
      def __init__(self, session_id):
          self.announce_queue = Queue()
      
      def announce(self, run_id, result):
          # 子Agent完成后调用
          self.announce_queue.put({...})
      
      def count_active(self):
          # 统计活跃子Agent
  ```
- 实现 `spawn_subagent` 函数
  - 安全检查: 深度限制(MAX_SPAWN_DEPTH=3)
  - 安全检查: 并发限制(MAX_CHILDREN=5)
  - 创建 run_id (uuid)
  - 注册到注册表

**下午 (4h)**
- 实现后台线程执行
  ```python
  def _run_in_thread():
      agent = agent_factory()
      result = asyncio.run(agent.run(task))
      registry.mark_ended(run_id, {...})
      manager.announce(run_id, result)
  
  threading.Thread(target=_run_in_thread, daemon=True).start()
  ```
- 实现 announce 消息格式
- 实现 agent_factory 注入

**交付**: 能派生子Agent并后台执行
**代码量**: ~120行

---

### Day 13: 子Agent工具集成
**上午 (4h)**
- 实现 `sessions_spawn` 工具
  - 参数: task, label, model
  - handler调用spawn_subagent
  - 返回: {status, run_id, label}
- 实现 `subagents` 工具
  - action=list: 列出子Agent
  - action=kill: 终止子Agent
  - action=steer: 发送修正指令

**下午 (4h)**
- 实现 `sessions_send` 工具 (跨session通信)
- 实现 `agents_list` 工具 (全局列表)
- 将子Agent工具集成到Agent
  - Agent.__init__ 创建工具
  - 添加到 tools 列表
- 测试: 派生子Agent，查看列表，等待完成

**交付**: 子Agent管理工具可用
**代码量**: ~250行

---

### Day 14: 父子通信 (Steer机制)
**上午 (4h)**
- 实现Steer消息存储
  ```python
  # 在SubagentRun中添加
  steer_messages: list[str]
  
  def add_steer(run_id, message):
      # 添加消息到队列
  
  def pop_steer(run_id):
      # 取出一条消息
  ```
- 实现父Agent发送steer
  - subagents工具的steer action
  - sessions_send工具

**下午 (4h)**
- 实现子Agent接收steer
  - Agent.run() 每轮检查
  - 如果有steer消息，注入到messages
  - 格式: {"role": "user", "content": "[STEER] ..."}
- 实现Agent等待子Agent完成
  - 检查announce_queue
  - 有活跃子Agent时等待
  - 超时处理
- 测试完整流程

**交付**: 父子双向通信
**代码量**: ~100行

---

## Week 3: Skill系统 + Web服务基础 (Day 15-21)

### Day 15: Skill元数据与扫描
**上午 (4h)**
- 设计Skill数据结构
  ```python
  @dataclass
  class SkillMeta:
      name: str
      description: str
      path: Path
  ```
- 实现 frontmatter 解析
  - 检测 `---` 边界
  - 简单YAML解析 (key: value)
  - 提取 name, description
  - 返回 body (剩余内容)

**下午 (4h)**
- 实现 `scan_skills()` 函数
  - 遍历 skills/ 目录
  - 查找所有 SKILL.md
  - 解析 frontmatter
  - 返回 SkillMeta 列表
- 实现 `build_skills_summary()`
  - 生成Markdown格式的Skill列表
  - 用于注入system prompt
- 测试: 创建几个测试Skill

**交付**: Skill扫描系统
**代码量**: ~100行

---

### Day 16: Skill集成到Agent
**上午 (4h)**
- 修改 `workspace.py`
  - 加载 workspace/*.md
  - 加载 skills摘要
  - 合并成 system prompt
- 修改 `Agent.__init__`
  - 调用 build_system_prompt()
  - 注入到 messages

**下午 (4h)**
- 实现Skill按需加载逻辑
  - Agent自动识别需要Skill
  - 调用 read 工具读取完整内容
  - 或使用特定格式触发
- 创建内置Skill
  - coding-agent/SKILL.md
  - github/SKILL.md
  - weather/SKILL.md
- 测试Skill触发

**交付**: Agent能感知和使用Skill
**代码量**: ~80行

---

### Day 17: Web服务基础 (HTTP)
**上午 (4h)**
- 实现基础HTTP服务器
  ```python
  from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
  
  class Handler(BaseHTTPRequestHandler):
      def do_GET(self):
          if self.path == "/":
              self._serve_html()
          elif self.path.startswith("/run"):
              self._serve_sse()
  ```
- 实现静态文件服务 (web_ui.html)
- 实现CORS处理

**下午 (4h)**
- 创建基础 `web_ui.html`
  - HTML骨架
  - 输入框
  - 消息展示区域
  - 基础CSS样式
- 实现 `/` 路由返回HTML
- 测试: 浏览器能打开界面

**交付**: 基础Web服务器
**代码量**: ~200行 (serve.py 100 + html 100)

---

### Day 18: SSE实时流
**上午 (4h)**
- 理解SSE协议
  - Content-Type: text/event-stream
  - 格式: `data: {...}\n\n`
- 实现 `/run` SSE端点
  - 解析查询参数 (q, history, model)
  - 创建Queue用于事件传递
  - 启动Agent在后台线程
  - 循环从Queue取事件发送

**下午 (4h)**
- 实现事件类型
  - start: 开始
  - thinking: 思考中
  - tool_calls: 工具调用
  - tool_result: 工具结果
  - done: 完成
- 前端接收并展示
  - EventSource API
  - 解析事件
  - 更新DOM
- 测试流式输出

**交付**: 实时流式对话
**代码量**: ~200行

---

### Day 19: Web UI增强
**上午 (4h)**
- 美化界面
  - 消息气泡样式
  - 代码高亮 (highlight.js或prism)
  - 工具调用特殊展示
- 添加功能
  - 停止按钮 (发送停止信号)
  - 清空对话
  - 历史记录展示

**下午 (4h)**
- 实现工具调用可视化
  - 展开/收起工具详情
  - 显示工具参数
  - 显示工具结果
- 实现思考过程展示
  - 如果模型返回reasoning_content
  - 可折叠展示
- 响应式布局

**交付**: 美观的Web界面
**代码量**: ~200行 (HTML/CSS/JS)

---

### Day 20: 子Agent在Web中的展示
**上午 (4h)**
- 扩展事件类型
  - subagent_start: 子Agent启动
  - subagent_complete: 子Agent完成
  - waiting_subagents: 等待中
- 前端展示子Agent状态
  - 子Agent列表
  - 实时状态更新
  - 结果展示

**下午 (4h)**
- 添加子Agent管理功能
  - 查看所有子Agent
  - 终止子Agent按钮
  - 发送steer消息
- 集成到主界面

**交付**: Web界面支持子Agent管理
**代码量**: ~150行

---

### Day 21: 第三阶段验收
**全天 (8h)**
- 端到端测试
  - CLI测试
  - Web测试
  - 子Agent测试
  - Skill测试
- Bug修复
- 性能优化
- 文档编写

**交付**: 完整系统 (CLI + Web + 子Agent + Skill)
**累计代码量**: ~3500行

---

## Week 4: 高级功能 + 测试完善 (Day 22-28)

### Day 22: cron任务Web管理
- 实现 `/cron` API端点
  - GET: 获取任务列表
  - POST: 添加/删除/执行任务
- Web界面管理定时任务
  - 任务列表
  - 添加任务表单
  - 执行日志查看

**代码量**: ~200行

### Day 23: 增强Git工具
- 实现 git_status 工具
- 实现 git_branch 工具
- 实现 git_diff 工具
- 集成到 git_enhanced 模块

**代码量**: ~150行

### Day 24: 错误处理增强
- 全局异常捕获
- 友好的错误页面
- 错误日志记录
- 自动错误报告(可选)

**代码量**: ~100行

### Day 25-26: 编写测试
- 单元测试 (工具测试)
- 集成测试 (Agent测试)
- E2E测试 (完整流程)
- 测试覆盖率统计

**代码量**: ~500行 (测试代码)

### Day 27: 性能优化
- 异步优化
- 连接池 (HTTP)
- 缓存机制
- 启动速度优化

### Day 28: 最终验收
- 完整功能测试
- 文档完善
- 发布检查

---

## 开发总结

| Week | 核心产出 | 代码量 | 关键技术 |
|------|----------|--------|----------|
| Week 1 | Agent核心 + 基础工具 + CLI | ~1000行 | Tool-Use循环、subprocess、文件IO |
| Week 2 | 高级工具 + 子Agent基础 | ~1200行 | Playwright、threading、Queue |
| Week 3 | Skill系统 + Web服务 | ~800行 | Frontmatter、HTTP、SSE |
| Week 4 | 高级功能 + 测试 | ~700行 | 测试框架、性能优化 |
| **总计** | **完整系统** | **~3700行** | **全栈Agent系统** |

---

## 与现有代码对比

当前项目实际代码量: ~3500-4000行
- agent.py: 206行
- subagent.py: 117行
- subagent_registry.py: 139行
- subagent_tools.py: 260行
- skills.py: 101行
- workspace.py: 59行
- serve.py: 509行
- main.py: 54行
- tools/: ~2000行 (14个工具)
- 测试: ~500行

**开发计划完全匹配现有规模！**
