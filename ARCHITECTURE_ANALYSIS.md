# aiagent_2 项目架构分析

## 一、项目对比概览

| 维度 | OpenClaw (原始项目) | aiagent_2 (简化版本) |
|------|---------------------|----------------------|
| **语言** | TypeScript (Node.js) | Python 3.13 |
| **代码规模** | ~500+ 核心文件，数万个测试文件 | ~23 个 Python 文件 |
| **架构复杂度** | 企业级分布式系统 | 轻量级单体应用 |
| **通信方式** | 多通道 (WhatsApp/Telegram/Slack/等 20+) | CLI + Web UI |
| **部署方式** | Gateway + Daemon + 多平台 App | 本地运行 |
| **子 Agent 系统** | ACP (Agent Control Plane) | threading + Queue |
| **Skill 系统** | local-skillhub (嵌入向量路由) | 简单 frontmatter 扫描 |
| **浏览器控制** | CDP + Playwright Bridge | Playwright |
| **持久化** | 多层级存储系统 | JSON 文件 |

---

## 二、架构图

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户接口层                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌─────────────────────────────────────────────────┐   │
│  │ CLI (main.py)│    │ Web UI (serve.py + web_ui.html)                │   │
│  │ - 交互式对话  │    │ - SSE 实时流                                   │   │
│  │ - 多轮历史    │    │ - 工具调用可视化                                │   │
│  └──────┬───────┘    └────────────────────┬────────────────────────────┘   │
│         │                                   │                                │
│         └─────────────────┬─────────────────┘                                │
│                           │                                                  │
│                           ▼                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                              Agent 核心层                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         Agent 类 (agent.py)                         │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │                     LLM Tool-Use 主循环                      │   │   │
│  │  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │   │   │
│  │  │  │ 第1轮   │───→│ 第2轮   │───→│ 第3轮   │───→│ 第N轮   │  │   │   │
│  │  │  │ LLM调用 │    │ LLM调用 │    │ LLM调用 │    │ 返回结果 │  │   │   │
│  │  │  └───┬─────┘    └────┬────┘    └────┬────┘    └────┬────┘  │   │   │
│  │  │      │               │              │              │       │   │   │
│  │  │      ▼               ▼              ▼              ▼       │   │   │
│  │  │  ┌─────────────────────────────────────────────────────────┐ │   │   │
│  │  │  │              并行工具执行 (asyncio.gather)               │ │   │   │
│  │  │  └─────────────────────────────────────────────────────────┘ │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │   │
│  │  │ build_system_   │  │ get_tool_       │  │ 子Agent工具 (动态)   │ │   │
│  │  │ prompt()        │  │ definitions()   │  │ - sessions_spawn    │ │   │
│  │  │                 │  │                 │  │ - subagents         │ │   │
│  │  │ 加载:           │  │ 注册:           │  │ - sessions_send     │ │   │
│  │  │ - IDENTITY.md   │  │ - 14个内置工具   │  │ - agents_list       │ │   │
│  │  │ - SOUL.md       │  │                 │  │                     │ │   │
│  │  │ - TOOLS.md      │  │                 │  │                     │ │   │
│  │  │ - skills/ 摘要  │  │                 │  │                     │ │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      SubagentManager (subagent.py)                  │   │
│  │                                                                     │   │
│  │   announce_queue (queue.Queue) ◄────── 子Agent完成通知              │   │
│  │          │                                                          │   │
│  │          ▼                                                          │   │
│  │   父Agent 注入结果到对话历史                                          │   │
│  │                                                                     │   │
│  │   安全限制:                                                          │   │
│  │   - 最大深度: 3层                                                    │   │
│  │   - 最大子Agent: 5个                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              工具层 (18个工具)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        内置工具 (14个)                               │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │ exec    │ │ read    │ │ write   │ │ edit    │ │apply_   │       │   │
│  │  │ 执行shell│ │ 读取文件│ │ 写入文件│ │ 编辑文件│ │ patch   │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │process  │ │web_fetch│ │web_search│ │memory_  │ │image    │       │   │
│  │  │进程管理  │ │抓取网页  │ │DuckDuckGo│ │search   │ │图像分析  │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                   │   │
│  │  │pdf      │ │tts      │ │browser  │ │cron     │                   │   │
│  │  │PDF分析  │ │文字转语音│ │浏览器控制│ │定时任务  │                   │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        子Agent工具 (4个)                             │   │
│  │                                                                     │   │
│  │   sessions_spawn ──► 派生子Agent (后台线程运行)                      │   │
│  │   subagents      ──► 管理子Agent (list/kill/steer)                   │   │
│  │   sessions_send  ──► 跨session通信                                   │   │
│  │   agents_list    ──► 全局Agent列表                                   │   │
│  │                                                                     │   │
│  │   子Agent执行流程:                                                   │   │
│  │   threading.Thread ──► asyncio.run(Agent.run(task))                 │   │
│  │                              │                                      │   │
│  │                              ▼                                      │   │
│  │                    完成后 ──► announce_queue.put(result)            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              基础设施层                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │  subagent_      │  │    skills.py    │  │       workspace.py          │ │
│  │  registry.py    │  │                 │  │                             │ │
│  │                 │  │ - scan_skills() │  │ - build_system_prompt()     │ │
│  │ - 内存注册表     │  │ - build_skills_ │  │ - 加载 .md 配置文件         │ │
│  │ - 磁盘持久化     │  │   summary()     │  │   (IDENTITY/SOUL/TOOLS)     │ │
│  │ - steer消息队列  │  │                 │  │                             │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘ │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │   git_utils.py  │  │   tools/types.py│  │      pyproject.toml         │ │
│  │                 │  │                 │  │                             │ │
│  │ - Git增强工具    │  │ - ToolDefinition│  │ - 项目配置                   │ │
│  │   (分支/status)  │  │ - RegisteredTool│  │ - 依赖管理                   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              外部服务层                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        LLM API (Moonshot/Kimi)                       │   │
│  │                                                                     │   │
│  │  - 模型: kimi-k2-0711-preview (默认)                                │   │
│  │  - API: OpenAI 兼容格式                                             │   │
│  │  - 工具调用: function calling                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │  Playwright     │  │  pdfminer.six   │  │        croniter             │ │
│  │  (可选)         │  │   (可选)        │  │       (可选)                │ │
│  │                 │  │                 │  │                             │ │
│  │ 浏览器自动化    │  │  PDF文本提取    │  │    cron表达式解析           │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流图

```
用户输入
    │
    ▼
┌─────────────────┐
│   Agent.run()   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  1. 构建 messages (system + history + user) │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐     ┌─────────────────┐
│  2. 调用 LLM API                       │────→│  Moonshot API   │
│     (with tools schema)                │←────│  (kimi-k2)      │
└─────────────────────────────────────────┘     └─────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  3. 检查 LLM 响应                       │
│                                         │
│  如果有 tool_calls ─────────────────────┼────→ 并行执行工具
│  如果纯文本 + announce_queue 有数据 ────┼────→ 注入子Agent结果，继续循环
│  如果纯文本 + 队列为空 ─────────────────┼────→ 返回最终结果
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  4. 工具执行结果添加到 messages         │
│     跳转到步骤 2 (下一轮)               │
└─────────────────────────────────────────┘
```

### 2.3 子 Agent 通信机制

```
┌─────────────────────────────────────────────────────────────────┐
│                        父 Agent (主线程)                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              SubagentManager                            │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │        announce_queue (queue.Queue)              │   │   │
│  │  │  ┌─────────────────────────────────────────┐     │   │   │
│  │  │  │  {"role":"user","content":"[subagent:xxx]│     │   │   │
│  │  │  │   Task completed.\n\nResult:\n..."}     │     │   │   │
│  │  │  └─────────────────────────────────────────┘     │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                                                         │   │
│  │  count_active() ──→ 返回当前活跃子Agent数量            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ▲                                  │
│                              │                                  │
│          子Agent完成后调用 announce() 放入队列                   │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│                              │         子 Agent (后台线程)       │
│  ┌───────────────────────────┘                                   │
│  │                                                               │
│  │  threading.Thread(target=_run_in_thread)                      │
│  │       │                                                       │
│  │       ▼                                                       │
│  │  asyncio.run(agent.run(task))                                 │
│  │       │                                                       │
│  │       ▼                                                       │
│  │  完成后 ──→ manager.announce(run_id, result)                  │
│  │              │                                                │
│  │              ▼                                                │
│  │  announce_queue.put({"role":"user", ...})                     │
│  │                                                               │
│  └───────────────────────────────────────────────────────────────┘
```

---

## 三、核心模块详解

### 3.1 Agent 核心 (agent.py)

```python
class Agent:
    def __init__(...):
        # 初始化 LLM 客户端
        self.client = AsyncOpenAI(...)
        
        # 构建 system prompt (workspace/*.md + skills)
        self.system_prompt = build_system_prompt(...)
        
        # 子 Agent 管理器
        self.manager = SubagentManager(session_id=...)
        
        # 工具列表 = 内置工具 + 子Agent工具
        self.tools = get_tool_definitions() + [spawn_tool, subagents_tool, ...]
    
    async def run(self, user_message, history=None):
        # 主循环: 最多 MAX_TOOL_ROUNDS (50) 轮
        for round_i in range(MAX_TOOL_ROUNDS):
            # 1. 检查 steer 队列 (父Agent的修正指令)
            
            # 2. 调用 LLM
            response = await self.client.chat.completions.create(...)
            
            # 3. 处理 tool_calls (并行执行)
            if msg.tool_calls:
                results = await asyncio.gather(...)
                continue  # 进入下一轮
            
            # 4. 检查 announce 队列 (子Agent结果)
            if announce_msg:
                messages.append(announce_msg)
                continue  # 进入下一轮
            
            # 5. 无工具调用、无子Agent结果 → 返回最终答案
            return msg.content
```

### 3.2 工具注册系统 (tools/__init__.py)

```python
# 全局注册表
_registry: dict[str, RegisteredTool] = {}

# 注册所有工具
_register(exec_tool)
_register(read_tool)
_register(write_tool)
_register(edit_tool)
_register(apply_patch_tool)
_register(process_tool)
_register(web_fetch_tool)
_register(web_search_tool)
_register(memory_search_tool)
_register(image_tool)
_register(pdf_tool)
_register(tts_tool)
_register(browser_tool)
_register(cron_tool)

# 公开 API
def get_tool_definitions() -> list[ToolDefinition]:
    return [t.definition for t in _registry.values()]

async def execute_tool(tool_call_id, name, arguments):
    tool = _registry.get(name)
    return await tool.handler(**kwargs)
```

### 3.3 子 Agent 派生 (subagent.py)

```python
def spawn_subagent(task, label, model, parent_id, depth, manager, agent_factory):
    # 安全检查
    if depth >= MAX_SPAWN_DEPTH:  # 3层
        return {"status": "error", ...}
    if active >= MAX_CHILDREN:    # 5个
        return {"status": "error", ...}
    
    # 创建 run_id
    run_id = new_run_id()
    
    # 注册到全局注册表
    registry.register_run(SubagentRun(...))
    
    # 在后台线程运行
    def _run_in_thread():
        agent = agent_factory()
        result = asyncio.run(agent.run(task))
        registry.mark_ended(run_id, {...})
        manager.announce(run_id, result)  # 通知父Agent
    
    threading.Thread(target=_run_in_thread, daemon=True).start()
    
    return {"status": "spawned", "run_id": run_id, ...}
```

### 3.4 Skill 系统 (skills.py)

```python
# Skill 目录结构
skills/
└── my-skill/
    └── SKILL.md      # frontmatter(name, description) + body

# 扫描 Skill
def scan_skills(skills_dir) -> list[SkillMeta]:
    for skill_md in sorted(skills_path.rglob("SKILL.md")):
        text = skill_md.read_text()
        meta, body = _parse_frontmatter(text)  # 解析 YAML frontmatter
        results.append(SkillMeta(name=meta["name"], description=meta["description"], path=skill_md))
    return results

# 生成摘要 (注入 system prompt)
def build_skills_summary(skills) -> str:
    return "# Available Skills\n\n" + "\n".join([f"- **{s.name}**: {s.description}" for s in skills])
```

### 3.5 Web 服务 (serve.py)

```
HTTP Server (ThreadingHTTPServer)
├── GET  /           → 返回 web_ui.html
├── GET  /run        → SSE 流式响应 (Agent 执行)
│   ├── event: start
│   ├── event: thinking
│   ├── event: reasoning
│   ├── event: tool_calls
│   ├── event: tool_result
│   ├── event: subagent_announce
│   └── event: done
├── GET  /stop       → 停止指定 run_id
├── GET/POST /cron   → 定时任务管理 API
└── GET  /cron/logs  → 获取执行日志
```

---

## 四、与 OpenClaw 的详细对比

### 4.1 功能对比

| 功能 | OpenClaw | aiagent_2 | 简化说明 |
|------|----------|-----------|----------|
| **多通道** | 20+ 通道 (WhatsApp/Telegram/Slack/等) | CLI + Web UI | 移除了复杂的多通道适配层 |
| **子 Agent** | ACP (Agent Control Plane) | threading + Queue | 移除了 RPC 和网络通信，改为进程内队列 |
| **Skill 路由** | 嵌入向量 + 相似度计算 | 简单 frontmatter 摘要 | 移除了向量数据库和复杂路由算法 |
| **浏览器** | CDP Bridge + Playwright | 纯 Playwright | 简化为直接调用 |
| **持久化** | 多层存储 (Redis/SQLite/文件) | JSON 文件 | 移除了数据库存储 |
| **部署** | Gateway + Daemon + App | 本地运行 | 移除了网络架构 |
| **语音** | Wake Word + Talk Mode + TTS | 简单 TTS (say/OpenAI) | 移除了语音唤醒和连续对话 |
| **Canvas** | Live Canvas + A2UI | 无 | 移除了可视化画布 |
| **移动应用** | iOS/Android 应用 | 无 | 移除了移动端 |
| **安全配置** | DM Pairing / Allowlist | 无 | 移除了安全策略层 |

### 4.2 代码结构对比

**OpenClaw:**
```
src/
├── agents/           # 482 个文件 - Agent 运行时
├── browser/          # 浏览器控制 (CDP/Bridge)
├── channels/         # 多通道抽象层
├── cli/              # CLI 命令系统
├── commands/         # 命令实现
├── config/           # 配置系统
├── cron/             # 定时任务
├── gateway/          # Gateway 控制平面
├── infra/            # 基础设施
├── memory/           # 记忆系统
├── plugins/          # 插件系统
├── routing/          # 路由系统
├── skills/           # Skill 系统
└── ...
```

**aiagent_2:**
```
aiagent/
├── agent.py              # 主循环 (206行)
├── subagent.py           # 子Agent (117行)
├── subagent_registry.py  # 注册中心 (139行)
├── subagent_tools.py     # 子Agent工具 (260行)
├── skills.py             # Skill扫描 (101行)
├── workspace.py          # 配置加载 (59行)
├── serve.py              # Web服务 (509行)
├── main.py               # CLI入口 (54行)
└── tools/                # 工具实现
    ├── __init__.py       # 工具注册 (94行)
    ├── types.py          # 类型定义 (40行)
    ├── exec.py           # shell执行 (67行)
    ├── file.py           # 文件操作 (429行)
    ├── web.py            # 网页抓取 (186行)
    ├── browser.py        # 浏览器 (413行)
    ├── cron.py           # 定时任务 (401行)
    └── ...
```

### 4.3 架构理念对比

| 维度 | OpenClaw | aiagent_2 |
|------|----------|-----------|
| **设计目标** | 企业级个人AI助手平台 | 轻量级本地AI Agent |
| **扩展性** | 高度可扩展 (插件/通道/Provider) | 简单扩展 (Skill) |
| **复杂度** | 高 (支持多用户/多设备/分布式) | 低 (单用户/单机) |
| **依赖** | 大量外部依赖和基础设施 | 最小依赖 (openai, dotenv) |
| **部署** | 复杂 (Gateway + Daemon + 多客户端) | 简单 (pip install + 运行) |
| **适用场景** | 个人/团队日常使用，多平台覆盖 | 开发/调试/自动化任务 |

---

## 五、项目整体流程

### 5.1 启动流程

```
1. 用户运行: uv run python -m aiagent.main
   │
   ▼
2. main.py: 加载 .env 配置
   │
   ▼
3. Agent.__init__()
   ├── 初始化 AsyncOpenAI 客户端
   ├── build_system_prompt() 加载 workspace/*.md
   │   ├── IDENTITY.md (身份定义)
   │   ├── SOUL.md (行为原则)
   │   ├── TOOLS.md (工具说明)
   │   └── skills/ 摘要列表
   ├── get_tool_definitions() 获取工具 schema
   └── 创建子 Agent 相关工具
   │
   ▼
4. 进入 chat_loop()，等待用户输入
```

### 5.2 单次请求处理流程

```
用户输入: "帮我创建一个 Python 项目"
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Agent.run(user_message, history)                         │
│    - 组装 messages: [system] + [history] + [user]           │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. 第1轮 LLM 调用                                           │
│    - 发送 messages + tools schema                           │
│    - LLM 决定调用工具: exec("mkdir myproject")              │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 并行执行工具                                             │
│    - execute_tool("exec", {...})                            │
│    - 返回: {"role": "tool", "content": "exit_code: 0"}      │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. 第2轮 LLM 调用                                           │
│    - messages 添加 tool 结果                                │
│    - LLM 决定调用工具: write("myproject/main.py", "...")    │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. 继续循环...                                              │
│    - 直到 LLM 不再调用工具                                   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. 返回最终结果                                             │
│    - "已创建 Python 项目，包含 main.py..."                   │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 子 Agent 派生流程

```
用户输入: "分析这个大型代码库，分成3个任务并行处理"
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. 父 Agent 调用 sessions_spawn                             │
│    - task="分析前端代码"                                     │
│    - label="frontend-analysis"                               │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. spawn_subagent()                                         │
│    - 创建 run_id="abc123"                                   │
│    - 注册到 subagent_registry                               │
│    - 启动 threading.Thread                                  │
│    - 立即返回: {"status": "spawned", "run_id": "abc123"}     │
└─────────────────────────────────────────────────────────────┘
    │
    ├── 父 Agent 继续处理其他任务 ────────────────────────────┐
    │                                                         │
    ▼                                                         │
┌─────────────────────────────────────────┐                   │
│ 3. 子 Agent 在后台线程运行               │                   │
│    - asyncio.run(agent.run(task))       │                   │
│    - 执行完成后调用 announce()          │                   │
└─────────────────────────────────────────┘                   │
    │                                                         │
    ▼                                                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. 父 Agent 检查 announce_queue                             │
│    - 发现子 Agent 完成消息                                  │
│    - 将结果注入 messages                                    │
│    - 继续 LLM 调用，整合结果                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 六、总结

aiagent_2 是 OpenClaw 的**精简版**，保留了核心功能但大幅简化了架构：

**保留的核心能力:**
1. ✅ LLM Tool-Use 主循环
2. ✅ 子 Agent 并行执行
3. ✅ 丰富的工具集 (18个)
4. ✅ Skill 扩展系统
5. ✅ Web 可视化界面

**简化的部分:**
1. ❌ 多通道支持 (改为 CLI + Web)
2. ❌ 复杂的 ACP 子 Agent 系统 (改为 threading + Queue)
3. ❌ 向量路由的 Skill 系统 (改为简单摘要)
4. ❌ 分布式部署架构 (改为本地运行)
5. ❌ 语音/Canvas/移动应用

**适用场景:**
- 本地开发调试
- 自动化脚本编写
- 快速原型开发
- 学习 Agent 架构

**架构优点:**
- 代码量少，易于理解和修改
- 依赖简单，易于部署
- Python 生态，工具丰富
- 单机运行，无需网络配置
