# MCP 接入方案分析

## OpenClaw 是怎么做 MCP 的

### 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        OpenClaw MCP 架构                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────────┐         ┌─────────────────────────────┐  │
│   │   Pi Agent Core  │────────►│  MCP Proxy (mcp-proxy.mjs)  │  │
│   │   (Agent 核心)    │         │                             │  │
│   └──────────────────┘         │  • 拦截 session/new 请求     │  │
│           ▲                      │  • 注入 mcpServers 配置      │  │
│           │                      │  • 转发给实际 Agent          │  │
│           │                      └──────────────┬──────────────┘  │
│           │                                     │                 │
│   ┌───────┴────────┐    ┌───────────────────────┴────────────┐   │
│   │  chrome-mcp.ts │    │         ACP Agent                 │   │
│   │                │    │  (Codex/Claude/Gemini/OpenCode)   │   │
│   │  MCP Client    │    └───────────────┬────────────────────┘   │
│   │  直接连接      │                    │                        │
│   └───────┬────────┘                    │ Stdio                  │
│           │                             ▼                        │
│           │              ┌─────────────────────────────────────┐ │
│           │              │  MCP Server (chrome-devtools-mcp)   │ │
│           │              │  • list_pages                       │ │
│           │              │  • navigate_page                    │ │
│           │              │  • take_screenshot                  │ │
│           └─────────────►└─────────────────────────────────────┘ │
│                              ▲                                   │
│                              │ Stdio                             │
│                   ┌──────────┴──────────┐                        │
│                   │   Chrome DevTools   │                        │
│                   │   Protocol          │                        │
│                   └─────────────────────┘                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 两种集成方式

#### 方式 1: 内置 MCP Client（如 chrome-mcp.ts）

```typescript
// OpenClaw 直接作为 MCP Client
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

// 1. 创建传输层
const transport = new StdioClientTransport({
  command: "npx",
  args: ["-y", "chrome-devtools-mcp@latest", "--autoConnect"],
});

// 2. 创建客户端
const client = new Client({ name: "openclaw-browser", version: "0.0.0" }, {});

// 3. 连接
await client.connect(transport);

// 4. 调用工具
const result = await client.callTool({
  name: "list_pages",
  arguments: {},
});
```

**适用场景**：浏览器控制等特定功能

#### 方式 2: MCP Proxy（让子 Agent 使用 MCP）

```javascript
// mcp-proxy.mjs 核心逻辑
function rewriteLine(line, mcpServers) {
  const parsed = JSON.parse(line);
  
  // 只在 session/new 等请求中注入 mcpServers
  if (shouldInject(parsed.method)) {
    parsed.params.mcpServers = mcpServers;
  }
  
  return JSON.stringify(parsed);
}

// 代理流程
stdin ──► rewriteLine (注入配置) ──► 子 Agent ──► MCP Server
```

**适用场景**：让外部 Agent（如 Codex、Claude Code）使用 MCP 工具

### OpenClaw 的配置方式

```typescript
// 在 acpx 配置中定义 MCP servers
{
  "agents": {
    "codex": "npx @zed-industries/codex-acp"
  },
  "mcpServers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"],
      "env": []
    }
  ]
}

// 启动时通过 proxy 注入
buildMcpProxyAgentCommand({
  targetCommand: "npx @zed-industries/codex-acp",
  mcpServers: [...]
});
// 生成: node mcp-proxy.mjs --payload <base64编码的配置>
```

---

## aiagent 的 MCP 接入方案

### 方案对比

| 方案 | 复杂度 | 优点 | 缺点 |
|------|--------|------|------|
| **A: 内置 MCP Client** | 低 | 简单直接，控制力强 | 每个 server 需单独编码 |
| **B: 工具级 MCP 代理** | 中 | 复用现有工具系统 | 需要转换层 |
| **C: Agent 级 MCP 注入** | 高 | 完整兼容 OpenClaw | 需要改动核心架构 |

### 推荐方案：A + B 混合

```
┌─────────────────────────────────────────────────────────────────┐
│                      aiagent MCP 架构                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    aiagent (Python)                      │   │
│   │                                                          │   │
│   │   ┌──────────────┐    ┌──────────────┐    ┌──────────┐  │   │
│   │   │   MCP Tool   │    │   MCP Tool   │    │  Native  │  │   │
│   │   │ (filesystem) │    │   (fetch)    │    │  Tools   │  │   │
│   │   └──────┬───────┘    └──────┬───────┘    └────┬─────┘  │   │
│   │          │                    │                 │        │   │
│   │          └────────────────────┴─────────────────┘        │   │
│   │                              │                           │   │
│   │                         Tool Registry                    │   │
│   │                         (统一注册)                        │   │
│   └──────────────────────────────┼───────────────────────────┘   │
│                                  │                               │
│   ┌──────────────────────────────┼───────────────────────────┐   │
│   │                         MCP Client (Python SDK)           │   │
│   │                              │                            │   │
│   │   ┌──────────────────────────┴────────────────────────┐  │   │
│   │   │              StdioClientTransport                │  │   │
│   │   │                                                   │  │   │
│   │   │  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │  │   │
│   │   │  │ MCP Server  │  │ MCP Server  │  │  Native   │ │  │   │
│   │   │  │(filesystem) │  │   (fetch)   │  │   Tools   │ │  │   │
│   │   │  └─────────────┘  └─────────────┘  └───────────┘ │  │   │
│   │   └──────────────────────────────────────────────────┘  │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 具体实现方案

### 1. 添加 MCP 依赖

```toml
# pyproject.toml
[project.optional-dependencies]
mcp = [
    "mcp>=1.12.0",  # Python MCP SDK
]
```

### 2. 创建 MCP 工具包装器

```python
# aiagent/tools/mcp_wrapper.py
"""MCP 工具集成 - 将 MCP Server 的工具暴露为 aiagent 工具"""

import asyncio
from typing import Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from aiagent.tools import register_tool


class MCPToolWrapper:
    """包装 MCP Server 为 aiagent 工具"""
    
    def __init__(self, name: str, command: str, args: list[str] = None, env: dict = None):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.session: ClientSession | None = None
        self._tools: list[dict] = []
        
    async def connect(self):
        """连接到 MCP Server"""
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env={**self.env, "PATH": "/usr/local/bin:/usr/bin:/bin"}
        )
        
        self._client = stdio_client(server_params)
        self._read, self._write = await self._client.__aenter__()
        self.session = await ClientSession(self._read, self._write).__aenter__()
        await self.session.initialize()
        
        # 获取工具列表
        tools_response = await self.session.list_tools()
        self._tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
            for tool in tools_response.tools
        ]
        
    async def disconnect(self):
        """断开连接"""
        if self.session:
            await self.session.__aexit__(None, None, None)
        if hasattr(self, '_client'):
            await self._client.__aexit__(None, None, None)
            
    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """调用 MCP 工具"""
        if not self.session:
            raise RuntimeError("MCP client not connected")
            
        result = await self.session.call_tool(tool_name, arguments)
        
        # 转换结果为字符串
        output = []
        for content in result.content:
            if content.type == "text":
                output.append(content.text)
            elif content.type == "image":
                output.append(f"[Image: {content.mimeType}]")
            elif content.type == "resource":
                output.append(f"[Resource: {content.resource.uri}]")
                
        return "\n".join(output) if output else "Tool executed successfully"
        
    def get_tool_definitions(self) -> list[dict]:
        """获取工具定义（用于注册到 aiagent）"""
        definitions = []
        for tool in self._tools:
            definitions.append({
                "type": "function",
                "function": {
                    "name": f"{self.name}_{tool['name']}",  # 前缀避免冲突
                    "description": f"[{self.name}] {tool['description']}",
                    "parameters": tool["parameters"]
                }
            })
        return definitions
```

### 3. MCP 工具管理器

```python
# aiagent/tools/mcp_manager.py
"""管理多个 MCP Server"""

import json
from pathlib import Path
from typing import dict, list

from aiagent.tools.mcp_wrapper import MCPToolWrapper


class MCPManager:
    """管理 MCP Server 连接和工具注册"""
    
    def __init__(self, config_path: str = "~/.aiagent/mcp.json"):
        self.config_path = Path(config_path).expanduser()
        self.servers: dict[str, MCPToolWrapper] = {}
        self._handlers: dict[str, callable] = {}
        
    def load_config(self) -> list[dict]:
        """加载 MCP 配置"""
        if not self.config_path.exists():
            return []
            
        with open(self.config_path) as f:
            config = json.load(f)
            return config.get("mcpServers", [])
            
    async def connect_all(self):
        """连接所有配置的 MCP Server"""
        servers_config = self.load_config()
        
        for server_config in servers_config:
            name = server_config["name"]
            wrapper = MCPToolWrapper(
                name=name,
                command=server_config["command"],
                args=server_config.get("args", []),
                env={e["name"]: e["value"] for e in server_config.get("env", [])}
            )
            
            try:
                await wrapper.connect()
                self.servers[name] = wrapper
                
                # 注册工具
                for tool_def in wrapper.get_tool_definitions():
                    tool_name = tool_def["function"]["name"]
                    self._handlers[tool_name] = self._create_handler(wrapper, tool_def)
                    
            except Exception as e:
                print(f"Failed to connect MCP server '{name}': {e}")
                
    def _create_handler(self, wrapper: MCPToolWrapper, tool_def: dict):
        """创建工具 handler"""
        original_name = tool_def["function"]["name"].replace(f"{wrapper.name}_", "", 1)
        
        async def handler(**kwargs):
            return await wrapper.call_tool(original_name, kwargs)
            
        return handler
        
    def get_all_tools(self) -> list[dict]:
        """获取所有 MCP 工具定义"""
        tools = []
        for wrapper in self.servers.values():
            tools.extend(wrapper.get_tool_definitions())
        return tools
        
    def get_handlers(self) -> dict[str, callable]:
        """获取所有工具 handler"""
        return self._handlers
        
    async def disconnect_all(self):
        """断开所有连接"""
        for wrapper in self.servers.values():
            await wrapper.disconnect()
```

### 4. 配置文件示例

```json
// ~/.aiagent/mcp.json
{
  "mcpServers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/xjh/projects"],
      "env": []
    },
    {
      "name": "fetch",
      "command": "uvx",
      "args": ["mcp-server-fetch"],
      "env": []
    },
    {
      "name": "sqlite",
      "command": "uvx",
      "args": ["mcp-server-sqlite", "--db-path", "/Users/xjh/data.db"],
      "env": []
    }
  ]
}
```

### 5. 集成到 aiagent

```python
# aiagent/tools/__init__.py

# ... 现有导入 ...
from aiagent.tools.mcp_manager import MCPManager

# MCP 管理器实例
_mcp_manager: MCPManager | None = None

async def init_mcp_tools():
    """初始化 MCP 工具"""
    global _mcp_manager
    _mcp_manager = MCPManager()
    await _mcp_manager.connect_all()
    
    # 注册 MCP 工具
    for name, handler in _mcp_manager.get_handlers().items():
        tool_def = next(
            t for t in _mcp_manager.get_all_tools() 
            if t["function"]["name"] == name
        )
        _register(RegisteredTool(
            definition=tool_def,
            handler=handler
        ))

async def shutdown_mcp_tools():
    """关闭 MCP 连接"""
    if _mcp_manager:
        await _mcp_manager.disconnect_all()
```

### 6. 启动时加载

```python
# aiagent/serve.py

async def main():
    # 初始化 MCP 工具
    await init_mcp_tools()
    
    try:
        server = HTTPServer(("localhost", 8765), Handler)
        print("Server started at http://localhost:8765")
        server.serve_forever()
    finally:
        # 清理 MCP 连接
        await shutdown_mcp_tools()
```

---

## 使用示例

### 配置后自动获得的新工具

```python
# 假设配置了 filesystem MCP server

# 新工具自动可用：
# - filesystem_read_file
# - filesystem_write_file  
# - filesystem_list_directory
# - filesystem_search_files

# 使用示例：
User: "读取我的项目 README"
Agent: [filesystem_read_file] path="/Users/xjh/projects/aiagent/README.md"

User: "搜索所有 Python 文件"
Agent: [filesystem_search_files] pattern="*.py"
```

---

## 与 OpenClaw 的差异

| 特性 | OpenClaw | aiagent 方案 |
|------|----------|--------------|
| 实现语言 | TypeScript | Python |
| MCP SDK | `@modelcontextprotocol/sdk` | `mcp` (Python) |
| 集成层级 | Agent 级别（注入配置） | Tool 级别（包装为工具） |
| 子 Agent 支持 | ✅ MCP Proxy | ❌ 暂不支持 |
| 动态加载 | ✅ 运行时配置 | ✅ 启动时加载 |
| 工具前缀 | 无 | 有（避免冲突） |

---

## 总结

**OpenClaw 的方案**：
- 作为 MCP Client 直接连接（如 chrome-mcp）
- 通过 MCP Proxy 让子 Agent 使用 MCP

**aiagent 的推荐方案**：
- 作为 MCP Client 包装为工具
- 保持简单：启动时加载，运行时可用
- 优势：复用现有工具系统，无需改动核心架构

**实现工作量**：
- 新增 2 个文件（mcp_wrapper.py, mcp_manager.py）
- 修改 2 个文件（__init__.py, serve.py）
- 约 200 行代码
- 1-2 天完成
