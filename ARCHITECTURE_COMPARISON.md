# AIAgent vs OpenClaw 架构对比分析

## 项目概述

### AIAgent (ai_pc_aiagent_os)
一个简化版的个人AI助手，基于Python构建，专注于本地工具执行和子Agent协作。

### OpenClaw
一个企业级的个人AI助手平台，基于TypeScript构建，支持多通道、多Agent、插件化架构。

---

## 一、整体架构对比

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          架构层次对比                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  AIAgent (Python)                    OpenClaw (TypeScript)                 │
│  ════════════════                    ═════════════════════                 │
│                                                                             │
│  ┌─────────────┐                     ┌─────────────────────────┐           │
│  │  Web UI     │                     │  Multi-Channel Gateway  │           │
│  │  (SSE)      │                     │  (WS/Telegram/Slack/...)│           │
│  └──────┬──────┘                     └───────────┬─────────────┘           │
│         │                                         │                         │
│  ┌──────▼──────┐                     ┌───────────▼─────────┐               │
│  │ HTTP Server │                     │    Gateway Server   │               │
│  │(Threading  │                     │   (Control Plane)   │               │
│  │ HTTPServer) │                     └───────┬───────────┘               │
│  └──────┬──────┘                             │                             │
│         │                              ┌──────▼──────┐                     │
│  ┌──────▼──────┐                     ┌──────────────┐                      │
│  │    Agent    │                     │   Pi Agent   │                      │
│  │   (Core)    │                     │   Runtime    │                      │
│  └──────┬──────┘                     └──────┬───────┘                      │
│         │                                    │                              │
│  ┌──────▼──────┐                     ┌──────▼──────┐                      │
│  │ Tool System │                     │  Tool/Skill │                      │
│  │ (Registry)  │                     │   Registry  │                      │
│  └──────┬──────┘                     └──────┬──────┘                      │
│         │                                    │                              │
│  ┌──────▼──────┐                     ┌──────▼──────┐                      │
│  │ Subagent    │                     │   Plugins   │                      │
│  │  Manager    │                     │   (MCP)     │                      │
│  └─────────────┘                     └─────────────┘                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、AIAgent 详细架构

### 2.1 核心组件

```
┌─────────────────────────────────────────────────────────────────┐
│                      AIAgent Architecture                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         Entry Points                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  CLI Mode   │  │ Web UI Mode │  │   Subagent (Spawned)    │ │
│  │  main.py    │  │  serve.py   │  │    (via spawn_tool)     │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
└─────────┼────────────────┼─────────────────────┼───────────────┘
          │                │                     │
          └────────────────┼─────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────┐
│                         Agent Core                               │
│                         agent.py                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                      Agent Class                          │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  Attributes:                                        │  │  │
│  │  │  - model: str              # LLM model name        │  │  │
│  │  │  - depth: int              # Spawn recursion depth │  │  │
│  │  │  - session_id: str         # Unique session ID     │  │  │
│  │  │  - client: AsyncOpenAI     # OpenAI-compatible API │  │  │
│  │  │  - manager: SubagentManager# Child agent manager   │  │  │
│  │  │  - tools: list[Tool]       # Available tools       │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                                                                │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  Main Loop: run(query, history)                     │  │  │
│  │  │                                                     │  │  │
│  │  │  while round < MAX_TOOL_ROUNDS:                    │  │  │
│  │  │    1. Check steer queue (parent instructions)      │  │  │
│  │  │    2. Build messages: system + history + query     │  │  │
│  │  │    3. Call LLM with tools                          │  │  │
│  │  │    4. If tool_calls:                               │  │  │
│  │  │       - Execute tools in parallel                  │  │  │
│  │  │       - Append results to history                  │  │  │
│  │  │       - Continue loop                              │  │  │
│  │  │    5. If text response:                            │  │  │
│  │  │       - Check announce queue (child results)       │  │  │
│  │  │       - If children done: return result            │  │  │
│  │  │       - Else: continue loop                        │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Tool System                                │
│                    tools/__init__.py                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────┐    ┌──────────────────────────────────┐  │
│   │  Registry       │    │         Tool Categories          │  │
│   │  (dict-based)   │    ├──────────────────────────────────┤  │
│   │                 │    │                                  │  │
│   │  _registry: {   │    │  File Operations:                │  │
│   │    "exec": ..., │    │  - read_tool                     │  │
│   │    "write": ...,│    │  - write_tool                    │  │
│   │    "spawn": ... │    │  - edit_tool                     │  │
│   │  }              │    │  - apply_patch_tool              │  │
│   └─────────────────┘    │  - restore_tool                  │  │
│                          │                                  │  │
│                          │  Process & Execution:            │  │
│                          │  - exec_tool (bash)              │  │
│                          │  - process_tool                  │  │
│                          │                                  │  │
│                          │  Web & Search:                   │  │
│                          │  - web_fetch_tool                │  │
│                          │  - web_search_tool               │  │
│                          │  - browser_tool (playwright)     │  │
│                          │                                  │  │
│                          │  Media & Documents:              │  │
│                          │  - image_tool                    │  │
│                          │  - pdf_tool                      │  │
│                          │  - tts_tool                      │  │
│                          │                                  │  │
│                          │  System & Memory:                │  │
│                          │  - memory_search_tool            │  │
│                          │  - cron_tool                     │  │
│                          │                                  │  │
│                          │  Git Operations:                 │  │
│                          │  - git_enhanced_tools            │  │
│                          │                                  │  │
│                          │  Subagent Tools:                 │  │
│                          │  - spawn_tool                    │  │
│                          │  - subagents_tool                │  │
│                          │  - sessions_send_tool            │  │
│                          │  - agents_list_tool              │  │
│                          └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Subagent System                              │
│              subagent.py + subagent_registry.py                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────┐    ┌────────────────────────────┐│
│   │   SubagentManager       │    │    SubagentRegistry         ││
│   │   (Per parent agent)    │    │    (Global singleton)       ││
│   ├─────────────────────────┤    ├────────────────────────────┤│
│   │                         │    │                             ││
│   │ - session_id: str       │    │ - _runs: dict[run_id, Run] ││
│   │ - announce_queue: Queue │    │                             ││
│   │                         │    │ Methods:                    ││
│   │ Methods:                │    │ - register_run()            ││
│   │ - announce()            │    │ - get_run()                 ││
│   │ - count_active()        │    │ - list_runs()               ││
│   └─────────────────────────┘    │ - update_run()              ││
│                                  │ - cleanup_old_runs()        ││
│   ┌─────────────────────────┐    └────────────────────────────┘│
│   │   spawn_subagent()      │                                   │
│   ├─────────────────────────┤    Spawn Constraints:             │
│   │                         │    - MAX_SPAWN_DEPTH = 3          │
│   │ Creates new Agent in    │    - MAX_CHILDREN = 5             │
│   │ background thread       │                                   │
│   │                         │    Lifecycle:                     │
│   │ Safety checks:          │    - spawn → run → announce     │
│   │ - depth < MAX_DEPTH     │    - parent polls announce_queue │
│   │ - active < MAX_CHILDREN │                                   │
│   └─────────────────────────┘                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Web UI Layer                                │
│                       serve.py                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────┐    ┌─────────────────────────────────────┐│
│   │  HTTP Server    │    │           Endpoints                 ││
│   │  (Threading)    │    ├─────────────────────────────────────┤│
│   │                 │    │                                     ││
│   │ - Static file   │    │ GET  /        → web_ui.html         ││
│   │   serving       │    │ GET  /config  → Provider config     ││
│   │ - SSE streaming │    │ GET  /run     → SSE stream          ││
│   │ - Multi-provider│    │ POST /cron    → Cron job mgmt       ││
│   │   support       │    │ GET  /cron/logs → Cron logs         ││
│   └─────────────────┘    │ GET  /stop    → Stop run            ││
│                          └─────────────────────────────────────┘│
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │                 SSE Event Flow                           │  │
│   │                                                          │  │
│   │  Client ──GET /run?q=...──→ Server                       │  │
│   │                              │                           │  │
│   │                              ▼                           │  │
│   │                      ┌──────────────┐                   │  │
│   │                      │ _serve_sse() │                   │  │
│   │                      │ (Thread)     │                   │  │
│   │                      └──────┬───────┘                   │  │
│   │                             │                           │  │
│   │         ┌───────────────────┼───────────────────┐       │  │
│   │         ▼                   ▼                   ▼       │  │
│   │    ┌─────────┐        ┌─────────┐        ┌─────────┐   │  │
│   │    │  start  │        │thinking │        │  tool   │   │  │
│   │    │  event  │        │  event  │        │ result  │   │  │
│   │    └────┬────┘        └────┬────┘        └────┬────┘   │  │
│   │         │                   │                   │       │  │
│   │         └───────────────────┼───────────────────┘       │  │
│   │                             ▼                           │  │
│   │                      ┌────────────┐                    │  │
│   │                      │ done/error │                    │  │
│   │                      └─────┬──────┘                    │  │
│   │                            │                           │  │
│   │  Client ◄──SSE stream──────┘                           │  │
│   │                                                          │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 AIAgent 数据流

```
┌─────────────────────────────────────────────────────────────────┐
│                     AIAgent Data Flow                            │
└─────────────────────────────────────────────────────────────────┘

User Request Flow:
═══════════════════════════════════════════════════════════════════

┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────────────┐
│  User   │────→│ Web UI  │────→│  Agent  │────→│   LLM API       │
│ Input   │     │(Browser)│     │(Python) │     │ (OpenAI-compat) │
└─────────┘     └────┬────┘     └────┬────┘     └────────┬────────┘
                     │               │                    │
                     │    ┌──────────┘                    │
                     │    │                               │
                     │    ▼                               │
                     │ ┌──────────────────┐               │
                     │ │ Tool Call Detected│               │
                     │ └────────┬─────────┘               │
                     │          │                          │
                     │          ▼                          │
                     │ ┌──────────────────┐                │
                     │ │ Parallel Tool    │                │
                     │ │ Execution        │                │
                     │ │ (asyncio.gather) │                │
                     │ └────────┬─────────┘                │
                     │          │                          │
                     └──────────┼──────────────────────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │  Tool Results → LLM │
                     │  (Next iteration)   │
                     └─────────────────────┘

Subagent Spawn Flow:
═══════════════════════════════════════════════════════════════════

Parent Agent              SubagentRegistry            Child Agent
     │                          │                          │
     │── spawn_subagent() ─────→│                          │
     │                          │── register_run() ───────→│
     │                          │                          │── run in thread
     │                          │                          │
     │◄── run_id ──────────────│                          │
     │                          │                          │
     │  (polls announce_queue)  │                          │
     │◄─────────────────────────│←──── announce() ─────────┘
     │                          │    (on completion)

```

---

## 三、OpenClaw 详细架构

### 3.1 核心组件

```
┌─────────────────────────────────────────────────────────────────┐
│                     OpenClaw Architecture                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Channel Layer                               │
│              (Multi-platform Integration)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Incoming Messages:                                             │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│   │WhatsApp │ │Telegram │ │ Discord │ │  Slack  │ │ Signal  │  │
│   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘  │
│        │           │           │           │           │       │
│   ┌────┴───────────┴───────────┴───────────┴───────────┴────┐  │
│   │              Channel Adapters (src/channels/)            │  │
│   │         - Message normalization                          │  │
│   │         - Media handling                                 │  │
│   │         - Thread binding                                 │  │
│   └──────────────────────────┬───────────────────────────────┘  │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│                      Gateway Server                              │
│              src/gateway/ - Control Plane                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌───────────────────────────────────────────────────────────┐│
│   │                    Gateway Core                            ││
│   │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐ ││
│   │  │  Client Mgmt  │  │  Session Mgmt │  │   Routing     │ ││
│   │  │  client.ts    │  │  sessions/    │  │  routing/     │ ││
│   │  └───────────────┘  └───────────────┘  └───────────────┘ ││
│   │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐ ││
│   │  │  Auth/Rate    │  │   Channel     │  │    Cron       │ ││
│   │  │  auth.ts      │  │   Health      │  │   cron/       │ ││
│   │  └───────────────┘  └───────────────┘  └───────────────┘ ││
│   └───────────────────────────────────────────────────────────┘│
│                              │                                   │
│   ┌──────────────────────────▼───────────────────────────────┐  │
│   │                     Call Handler                          │  │
│   │                   gateway/call.ts                         │  │
│   │                                                           │  │
│   │  ┌─────────────────────────────────────────────────────┐  │  │
│   │  │  Session Resolution:                                 │  │  │
│   │  │  - Session key from channel+account+peer             │  │  │
│   │  │  - Thread binding policy                             │  │  │
│   │  │  - Delivery context normalization                    │  │  │
│   │  └─────────────────────────────────────────────────────┘  │  │
│   │                            │                               │  │
│   │                            ▼                               │  │
│   │  ┌─────────────────────────────────────────────────────┐  │  │
│   │  │  Agent Selection:                                    │  │  │
│   │  │  - Multi-agent routing                               │  │  │
│   │  │  - Workspace isolation                               │  │  │
│   │  │  - Session activation modes                          │  │  │
│   │  └─────────────────────────────────────────────────────┘  │  │
│   └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│                       Pi Agent Runtime                           │
│                src/agents/ - Agent Core                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │                  Agent Runtime (acp-spawn.ts)             │  │
│   │                                                           │  │
│   │  Spawn Modes:                                             │  │
│   │  - "run": One-shot task execution                        │  │
│   │  - "session": Persistent session with thread binding      │  │
│   │                                                           │  │
│   │  Sandbox Modes:                                           │  │
│   │  - "inherit": Use parent sandbox settings                 │  │
│   │  - "require": Force sandbox isolation                     │  │
│   │                                                           │  │
│   │  Stream Targets:                                          │  │
│   │  - "parent": Relay output to parent session               │  │
│   │                                                           │  │
│   └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│   ┌──────────────────────────▼───────────────────────────────┐  │
│   │                   Agent Scope (agent-scope.ts)            │  │
│   │                                                           │  │
│   │  - Workspace directory resolution                         │  │
│   │  - Tool capability filtering                              │  │
│   │  - Sandbox runtime status                                 │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │                Tool System (tools/)                       │  │
│   │                                                           │  │
│   │  Built-in Tools:                                          │  │
│   │  - apply-patch.ts    - File editing                       │  │
│   │  - browser.ts        - Web browser automation             │  │
│   │  - canvas.ts         - Visual workspace                   │  │
│   │  - exec.ts           - Command execution                  │  │
│   │                                                           │  │
│   │  Skills:                                                  │  │
│   │  - Loaded from workspace/.claw/skills/                   │  │
│   │  - Bundled skills in skills/                             │  │
│   │  - ClawHub integration                                    │  │
│   │                                                           │  │
│   │  MCP Support:                                             │  │
│   │  - Via mcporter bridge                                    │  │
│   │  - External MCP servers                                   │  │
│   │                                                           │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │              Subagent System (acp-spawn.ts)               │  │
│   │                                                           │  │
│   │  ACP (Agent Control Protocol):                            │  │
│   │  - Parent-child session binding                           │  │
│   │  - Stream relay between sessions                          │  │
│   │  - Lifecycle management                                   │  │
│   │                                                           │  │
│   │  Session Identifiers:                                     │  │
│   │  - resolveAcpSessionCwd()                                 │  │
│   │  - resolveAcpThreadSessionDetailLines()                   │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│                      Memory & State                              │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│   │ Session Binding │  │     Memory      │  │   Auth Store    │ │
│   │    Service      │  │   (Plugin)      │  │  auth-profiles/ │ │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 OpenClaw 数据流

```
┌─────────────────────────────────────────────────────────────────┐
│                     OpenClaw Data Flow                           │
└─────────────────────────────────────────────────────────────────┘

Incoming Message Flow:
═══════════════════════════════════════════════════════════════════

┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐
│  Channel  │───→│  Adapter  │───→│  Gateway  │───→│  Session  │
│  (Telegram│    │ (Normalize│    │  Routing  │    │  Resolver │
│  /Slack/..│    │  Message) │    │           │    │           │
└───────────┘    └───────────┘    └─────┬─────┘    └─────┬─────┘
                                         │                │
                                         │                ▼
                                         │         ┌──────────────┐
                                         │         │ Session Key: │
                                         │         │ channel+peer │
                                         │         │ +thread_id   │
                                         │         └──────┬───────┘
                                         │                │
                                         ▼                ▼
                                  ┌──────────────────────────┐
                                  │   Agent Selection        │
                                  │   - Workspace routing    │
                                  │   - Multi-agent config   │
                                  └────────────┬─────────────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │  Pi Runtime  │
                                        │  Tool Calls  │
                                        └──────┬───────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │   Response   │
                                        │   to Channel │
                                        └──────────────┘

Subagent Spawn Flow (ACP):
═══════════════════════════════════════════════════════════════════

Parent Session              ACP Control Plane            Child Session
     │                             │                             │
     │── spawnAcp() ──────────────→│                             │
     │                             │── create session ──────────→│
     │                             │                             │
     │◄── accepted ────────────────│                             │
     │                             │                             │
     │                             │◄── stream relay ────────────│
     │                             │                             │
     │◄── output relay ────────────│                             │
     │                             │                             │
     │                             │◄── complete ────────────────│
     │                             │                             │
     │◄── child result ────────────│                             │

```

---

## 四、关键差异对比

| 特性 | AIAgent | OpenClaw |
|------|---------|----------|
| **语言** | Python | TypeScript |
| **架构风格** | 单体应用 | 微服务/插件化 |
| **通道支持** | Web UI only | 20+ messaging channels |
| **Agent模型** | 单层父子关系 | 多层级AC协议 |
| **工具系统** | 内置+注册表 | 插件+Skill+MCP |
| **沙箱** | 无 | 完整Sandbox支持 |
| **状态管理** | 内存Queue | Session Binding Service |
| **配置** | .env文件 | 复杂配置系统 |
| **部署** | 本地运行 | Gateway+Node |
| **流式输出** | SSE | WebSocket |
| **记忆系统** | 简单向量搜索 | 可插拔Memory |
| **认证** | API Key | OAuth + Profile rotation |

---

## 五、AIAgent 设计取舍（相对OpenClaw的简化）

### 5.1 被简化的模块

```
OpenClaw Features → AIAgent Simplification:
═══════════════════════════════════════════════════════════════════

Multi-Channel Support:
  OpenClaw:  Telegram/WhatsApp/Discord/Slack/Signal/iMessage/...
  AIAgent:  → Web UI only (serve.py + web_ui.html)

Agent Communication Protocol (ACP):
  OpenClaw:  Full ACP with session binding, stream relay, sandbox modes
  AIAgent:  → Simple subagent spawn with announce queue

Tool System:
  OpenClaw:  Plugin SDK + MCP + Skills registry
  AIAgent:  → Direct tool registration in tools/__init__.py

Memory System:
  OpenClaw:  Pluggable memory providers
  AIAgent:  → Simple in-memory vector search

Authentication:
  OpenClaw:  OAuth + API key rotation + auth profiles
  AIAgent:  → Simple API key in .env

Sandbox:
  OpenClaw:  Full sandbox isolation (Docker/Podman)
  AIAgent:  → Direct subprocess execution

Configuration:
  OpenClaw:  Complex config system with validation
  AIAgent:  → Simple .env + localStorage override
```

### 5.2 保留的核心能力

```
Core Capabilities Preserved:
═══════════════════════════════════════════════════════════════════

1. LLM Tool-Use Loop
   - Same core algorithm as OpenClaw
   - Parallel tool execution
   - Multi-round conversation

2. Subagent Spawning
   - Recursive agent creation
   - Parent-child communication
   - Depth limiting

3. Tool Categories
   - File operations
   - Web search/fetch
   - Browser automation
   - Media processing
   - Git operations

4. Web UI Experience
   - Real-time SSE streaming
   - Multi-provider support
   - Visual tool call display
```

---

## 六、推荐架构图

```
┌─────────────────────────────────────────────────────────────────┐
│              Simplified AIAgent Architecture                     │
│        (Recommended for Personal Use/Development)                │
└─────────────────────────────────────────────────────────────────┘

                          ┌─────────────┐
                          │   User      │
                          └──────┬──────┘
                                 │
                    ┌────────────┴────────────┐
                    │        Browser          │
                    │    (Web UI localhost)   │
                    └────────────┬────────────┘
                                 │ HTTP + SSE
                    ┌────────────▼────────────┐
                    │      HTTP Server        │
                    │    (Python stdlib)      │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │        Agent Core       │
                    │  ┌───────────────────┐  │
                    │  │ - LLM Client      │  │
                    │  │ - Tool Registry   │  │
                    │  │ - Subagent Mgr    │  │
                    │  │ - Workspace       │  │
                    │  └───────────────────┘  │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
    ┌─────────▼────────┐ ┌──────▼──────┐ ┌────────▼───────┐
    │   Tools          │ │ Subagents   │ │  LLM Provider  │
    │ - exec           │ │ (threads)   │ │ (OpenAI-compat)│
    │ - file           │ └─────────────┘ └────────────────┘
    │ - web            │
    │ - browser        │
    │ - git            │
    └──────────────────┘

Key Design Principles:
═══════════════════════════════════════════════════════════════════
1. Single-binary deployment (uv run python -m aiagent.serve)
2. Zero external dependencies for Web UI (pure stdlib HTTP)
3. Configuration via .env (simple & portable)
4. Tool extensibility via code (not plugin system)
5. Subagent for parallelism (not async/await)
```

---

## 七、数据流详细时序

### AIAgent 工具调用时序

```
┌──────┐    ┌────────┐    ┌─────────┐    ┌───────┐    ┌─────────┐
│ User │    │ Web UI │    │  Agent  │    │ Tools │    │   LLM   │
└──┬───┘    └───┬────┘    └────┬────┘    └───┬───┘    └────┬────┘
   │            │              │              │              │
   │── input ──→│              │              │              │
   │            │── query ────→│              │              │
   │            │              │── messages ──→              │
   │            │              │ (system+hist+query)         │
   │            │              │              │              │
   │            │              │←─ tool_calls ─│              │
   │            │              │   (decision)  │              │
   │            │              │              │              │
   │            │              │── parallel ──→│              │
   │            │              │   tool calls │              │
   │            │              │              │              │
   │            │              │←── results ──│              │
   │            │              │              │              │
   │            │              │── results ────→             │
   │            │              │   (continue loop...)        │
   │            │              │              │              │
   │            │              │←── response ─│              │
   │            │              │   (no more tools)           │
   │            │              │              │              │
   │            │←─ SSE events─│              │              │
   │            │ (thinking/   │              │              │
   │            │  tool/result)│              │              │
   │            │              │              │              │
   │←─ display ─│              │              │              │
   │            │              │              │              │
```

---

*文档生成时间: 2026-03-17*
*分析对象: ai_pc_aiagent_os (AIAgent) vs openclaw (OpenClaw)*
