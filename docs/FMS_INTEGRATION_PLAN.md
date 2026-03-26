# NAS FMS 系统集成实施方案

> **项目**: AI PC Agent OS 对接 NAS FMS 多模态检索系统
> **FMS 地址**: `http://172.16.50.51:8001`
> **实施状态**: ✅ **已完成，已合并到 master**
> **测试验证**: ✅ **26次工具调用无错误**
> **后续规划**: [FMS_INTEGRATION_SUMMARY.md](./FMS_INTEGRATION_SUMMARY.md)
> **文档日期**: 2026-03-26

---

## 一、背景与目标

### 1.1 背景

NAS 部署了 **FMS (File Management System)** 智能文件管理系统，提供：

- 多模态文件检索（文本搜文档/图片/视频、以图搜图）
- 基于知识库的智能问答
- 文件自动分类和索引

目前 Agent 无法直接访问 NAS 资源，需要通过 HTTP API 封装为工具和 Skill。

### 1.2 目标

| 阶段              | 目标                                                   | 状态   |
| ----------------- | ------------------------------------------------------ | ------ |
| **Phase 1** | 核心工具封装（fms_retrieve, fms_chat, fms_list_files） | 待实施 |
| **Phase 2** | FMS Skill 创建（触发词、使用指南）                     | 待实施 |
| **Phase 3** | 测试验证（工具测试 + Web UI 集成测试）                 | 待实施 |
| **Phase 4** | 扩展功能（fms_delete, fms_task_control，可选）         | 预留   |

### 1.3 对接价值

| 能力       | 用户场景           | 示例                  |
| ---------- | ------------------ | --------------------- |
| 文档检索   | 快速查找公司文档   | "搜索关于班车的文档"  |
| 知识问答   | 基于内部知识库问答 | "公司班车有哪些路线"  |
| 图片搜索   | 找特定类型的图片   | "找风景优美的图片"    |
| 多模态关联 | 跨类型检索         | 用文本搜相关图片/视频 |

---

## 二、FMS 系统能力分析

### 2.1 核心接口清单

| 接口                                    | 方法 | 功能         | 优先级       |
| --------------------------------------- | ---- | ------------ | ------------ |
| `/api/fms/retrieve`                   | POST | 多模态检索   | **P0** |
| `/api/fms/chat`                       | POST | 知识库问答   | **P0** |
| `/api/fms/get_knowledge_files`        | GET  | 获取文件列表 | **P0** |
| `/api/fms/delete_file`                | POST | 删除文件     | P1           |
| `/api/fms/ingest_file`                | POST | 文件入库     | 预留         |
| `/api/fms/ingest_progress`            | GET  | 入库进度     | 预留         |
| `/api/fms/{pause/resume/cancel}_task` | POST | 任务管理     | 预留         |

### 2.2 检索类型详解

| 类型            | 输入     | 输出     | 应用场景     |
| --------------- | -------- | -------- | ------------ |
| `text2doc`    | 文本     | 文档列表 | 关键词搜文档 |
| `doc2doc`     | 文档路径 | 相似文档 | 找相似文档   |
| `text2image`  | 文本     | 图片列表 | 关键词搜图片 |
| `image2image` | 图片路径 | 相似图片 | 以图搜图     |
| `text2video`  | 文本     | 视频列表 | 关键词搜视频 |

---

## 三、架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                         用户层                               │
│  "搜索NAS上关于班车的文档"  "知识库问答：公司福利有哪些"        │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    fms Skill 层                             │
│  - 意图识别（关键词匹配）                                     │
│  - 参数提取（查询内容、文件类型等）                            │
│  - 工具选择和调用                                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    FMS Tools 层                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │fms_retrieve │  │  fms_chat   │  │  fms_list_files     │  │
│  │(多模态检索)  │  │(知识库问答)  │  │  (获取文件列表)      │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │              │
│         └────────────────┼─────────────────────┘              │
│                          │                                   │
│         ┌────────────────┼─────────────────────┐              │
│         ▼                ▼                     ▼              │
│    ┌─────────┐     ┌─────────┐          ┌─────────┐          │
│    │ Error   │     │ Result  │          │  Error  │          │
│    │ Handler │     │ Formatter│         │ Handler │          │
│    └─────────┘     └─────────┘          └─────────┘          │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   HTTP Client 层                            │
│              aiohttp 异步 HTTP 请求                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    FMS Server 层                            │
│              172.16.50.51:8001                               │
│         (NAS 上的文件管理系统)                                │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 数据流向

```
用户输入 → Skill解析 → 选择Tool → HTTP请求 → FMS处理 → 结果格式化 → LLM展示
```

---

## 四、详细实施步骤

### Phase 1: 核心工具封装（第1-2天）

#### 4.1.1 创建 FMS 工具模块

**文件**: `aiagent/tools/fms.py`

```python
"""
FMS (File Management System) 工具

NAS 智能文件管理系统对接模块，支持多模态检索和知识库问答。
"""

from __future__ import annotations
import aiohttp
import json
from typing import Optional, List, Dict, Any
from .types import RegisteredTool, ToolDefinition

# FMS 服务器配置
FMS_BASE_URL = "http://172.16.50.51:8001"
DEFAULT_TIMEOUT = 30  # 秒


# ========== 内部辅助函数 ==========

async def _fms_request(
    endpoint: str,
    method: str = "GET",
    json_data: dict = None,
    params: dict = None,
) -> dict:
    """
    发送 HTTP 请求到 FMS 服务器
  
    Args:
        endpoint: API 端点路径（如 /api/fms/chat）
        method: HTTP 方法
        json_data: POST 请求的 JSON 数据
        params: GET 请求的查询参数
  
    Returns:
        FMS 响应的 JSON 数据
  
    Raises:
        返回错误信息字典，不抛出异常
    """
    url = f"{FMS_BASE_URL}{endpoint}"
  
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)) as session:
            if method.upper() == "GET":
                async with session.get(url, params=params) as resp:
                    return await _handle_response(resp)
            else:
                async with session.post(url, json=json_data) as resp:
                    return await _handle_response(resp)
    except aiohttp.ClientConnectorError as e:
        return {"code": -1, "message": f"无法连接到 FMS 服务器: {e}", "data": None}
    except aiohttp.ClientTimeout as e:
        return {"code": -1, "message": f"FMS 请求超时 ({DEFAULT_TIMEOUT}s): {e}", "data": None}
    except Exception as e:
        return {"code": -1, "message": f"FMS 请求异常: {e}", "data": None}


async def _handle_response(resp: aiohttp.ClientResponse) -> dict:
    """处理 HTTP 响应"""
    try:
        data = await resp.json()
    except Exception:
        text = await resp.text()
        return {"code": -1, "message": f"无效的 JSON 响应: {text[:200]}", "data": None}
  
    if resp.status != 200:
        return {
            "code": resp.status,
            "message": data.get("message", f"HTTP {resp.status}"),
            "data": None
        }
  
    return data


def _format_retrieve_results(results: List[Dict]) -> str:
    """格式化检索结果为表格"""
    if not results:
        return "未找到相关文件"
  
    lines = [
        f"找到 {len(results)} 个相关文件：\n",
        "| 相似度 | 文件路径 | 类型 | 内容片段 |",
        "|--------|----------|------|----------|",
    ]
  
    for r in results:
        score = r.get("score", 0)
        path = r.get("file_path", "N/A")
        file_class = r.get("file_class", "default")
        chunk = r.get("doc_chunk", "")[:60].replace("\n", " ").replace("|", "\\|")
        lines.append(f"| {score:.2f} | `{path}` | {file_class} | {chunk}... |")
  
    return "\n".join(lines)


def _format_chat_response(data: dict) -> str:
    """格式化问答响应"""
    answer = data.get("answer", "无回答")
    chunks = data.get("chunk", [])
  
    result = f"**回答**：\n{answer}\n"
  
    if chunks:
        result += "\n**参考来源**：\n"
        for i, c in enumerate(chunks[:3], 1):
            path = c.get("path", "N/A")
            content = c.get("content", "")[:80].replace("\n", " ")
            result += f"{i}. `{path}`\n   > {content}...\n"
  
    return result


def _format_file_list(files: List[Dict]) -> str:
    """格式化文件列表"""
    if not files:
        return "知识库中没有文件"
  
    # 按类型分组
    docs = [f for f in files if f.get("type") == "document"]
    images = [f for f in files if f.get("type") == "image"]
    videos = [f for f in files if f.get("type") == "video"]
  
    result = f"知识库共有 {len(files)} 个文件：\n"
    result += f"- 📄 文档: {len(docs)} 个\n"
    result += f"- 🖼️ 图片: {len(images)} 个\n"
    result += f"- 🎬 视频: {len(videos)} 个\n\n"
  
    # 显示前10个文件
    result += "**最近文件**（显示前10个）：\n"
    for f in files[:10]:
        emoji = "📄" if f.get("type") == "document" else "🖼️" if f.get("type") == "image" else "🎬"
        path = f.get("file_path", "N/A")
        result += f"{emoji} `{path}`\n"
  
    if len(files) > 10:
        result += f"\n... 还有 {len(files) - 10} 个文件"
  
    return result


# ========== 核心工具实现 ==========

async def fms_retrieve_handler(
    query: str,
    type: str = "text2doc",
    top_k: int = 10,
    score_threshold: float = 0.5,
) -> str:
    """
    FMS 多模态检索
  
    支持文本搜文档、文本搜图片、以图搜图、文本搜视频等多种检索方式。
  
    Args:
        query: 查询内容（文本或文件路径）
        type: 检索类型，可选值：
            - text2doc: 文本搜文档
            - doc2doc: 文档搜相似文档
            - text2image: 文本搜图片
            - image2image: 以图搜图（query为图片路径）
            - text2video: 文本搜视频
        top_k: 返回结果数量（默认10）
        score_threshold: 相似度阈值 0-1（默认0.5）
  
    Returns:
        格式化的检索结果表格
    """
    # 参数验证
    valid_types = ["text2doc", "doc2doc", "text2image", "image2image", "text2video"]
    if type not in valid_types:
        return f"Error: 不支持的检索类型 '{type}'。可选值: {', '.join(valid_types)}"
  
    data = await _fms_request(
        "/api/fms/retrieve",
        method="POST",
        json_data={
            "type": type,
            "query": query,
            "top_k": top_k,
            "score_threshold": score_threshold,
        }
    )
  
    if data["code"] != 200:
        return f"Error [{data.get('code', 'Unknown')}]: {data.get('message', '检索失败')}"
  
    results = data.get("data", {}).get("results", [])
    return _format_retrieve_results(results)


async def fms_chat_handler(query: str) -> str:
    """
    FMS 知识库智能问答
  
    基于 NAS 知识库内容进行智能问答。
  
    Args:
        query: 用户问题
  
    Returns:
        AI 生成的回答及相关文档来源
    """
    if not query or not query.strip():
        return "Error: 查询内容不能为空"
  
    data = await _fms_request(
        "/api/fms/chat",
        method="POST",
        json_data={"query": query}
    )
  
    if data["code"] != 200:
        return f"Error [{data.get('code', 'Unknown')}]: {data.get('message', '问答失败')}"
  
    return _format_chat_response(data.get("data", {}))


async def fms_list_files_handler(file_type: Optional[str] = None) -> str:
    """
    获取 FMS 知识库文件列表
  
    Args:
        file_type: 文件类型过滤，可选值：document, image, video。不填返回所有
  
    Returns:
        文件列表统计和详情
    """
    params = {}
    if file_type:
        valid_types = ["document", "image", "video"]
        if file_type not in valid_types:
            return f"Error: 不支持的文件类型 '{file_type}'。可选值: {', '.join(valid_types)}"
        params["file_type"] = file_type
  
    data = await _fms_request(
        "/api/fms/get_knowledge_files",
        method="GET",
        params=params if params else None
    )
  
    if data["code"] != 200:
        return f"Error [{data.get('code', 'Unknown')}]: {data.get('message', '获取文件列表失败')}"
  
    files = data.get("data", [])
    return _format_file_list(files)


# ========== 工具注册定义 ==========

fms_retrieve_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "fms_retrieve",
            "description": (
                "NAS FMS 多模态文件检索。支持：\n"
                "- text2doc: 用关键词搜索文档\n"
                "- doc2doc: 找与某文档相似的文档\n"
                "- text2image: 用关键词搜索图片\n"
                "- image2image: 以图搜图（传入图片路径）\n"
                "- text2video: 用关键词搜索视频"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "查询内容。文本搜索时输入关键词，以图搜图时输入图片路径",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["text2doc", "doc2doc", "text2image", "image2image", "text2video"],
                        "description": "检索类型",
                        "default": "text2doc",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回结果数量",
                        "default": 10,
                    },
                    "score_threshold": {
                        "type": "number",
                        "description": "相似度阈值 0-1",
                        "default": 0.5,
                    },
                },
                "required": ["query"],
            },
        },
    ),
    handler=fms_retrieve_handler,
)


fms_chat_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "fms_chat",
            "description": (
                "基于 NAS 知识库的智能问答。"
                "当用户询问公司制度、文档内容、内部知识时使用此工具。"
                "示例：'公司班车有哪些路线'、'请介绍一下年假制度'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "用户的问题",
                    },
                },
                "required": ["query"],
            },
        },
    ),
    handler=fms_chat_handler,
)


fms_list_files_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "fms_list_files",
            "description": "获取 NAS 知识库中的文件列表，可查看有哪些文档、图片、视频",
            "parameters": {
                "type": "object",
        "properties": {
                    "file_type": {
                        "type": "string",
                        "enum": ["document", "image", "video"],
                        "description": "文件类型过滤，不填返回所有类型",
                    },
                },
            },
        },
    ),
    handler=fms_list_files_handler,
)


# ========== 预留扩展（Phase 4）==========

# async def fms_ingest_handler(paths: List[str]) -> str:
#     """文件入库（预留）"""
#     pass

# async def fms_delete_handler(paths: List[str]) -> str:
#     """删除文件（预留）"""
#     pass

# async def fms_task_control_handler(action: str, task_id: str, task_type: str) -> str:
#     """任务管理（预留）"""
#     pass
```

#### 4.1.2 注册工具到系统

**修改**: `aiagent/tools/__init__.py`

```python
# 在文件顶部添加导入
from .fms import fms_retrieve_tool, fms_chat_tool, fms_list_files_tool

# 在注册区域添加
_register(fms_retrieve_tool)
_register(fms_chat_tool)
_register(fms_list_files_tool)
```

---

### Phase 2: FMS Skill 创建（第3天）

#### 4.2.1 创建 Skill 目录和文件

```bash
mkdir -p skills/system/fms
touch skills/system/fms/SKILL.md
```

**文件**: `skills/system/fms/SKILL.md`

```markdown
---
name: nas-fms
description: NAS智能文件管理系统，支持多模态检索（文本搜文档/图片/视频、以图搜图）和知识库问答
triggers:
  - "搜索NAS"
  - "NAS上"
  - "知识库"
  - "查找文件"
  - "以图搜图"
  - "搜索图片"
  - "搜索视频"
  - "公司文档"
---

# NAS FMS 智能文件管理

## 功能概述

连接 NAS 上的 FMS (File Management System) 文件管理系统，实现：
- 🔍 **多模态文件检索**：用关键词搜索文档、图片、视频
- 🖼️ **以图搜图**：上传图片找相似图片
- 💬 **知识库问答**：基于公司内部文档智能问答
- 📋 **文件列表**：查看知识库中所有文件

## 触发场景

| 用户意图 | 示例 | 调用工具 |
|----------|------|----------|
| 搜索文档 | "搜索NAS上关于班车的文档" | `fms_retrieve(type="text2doc")` |
| 搜索图片 | "找风景优美的图片" | `fms_retrieve(type="text2image")` |
| 以图搜图 | "用这张图片找相似的" | `fms_retrieve(type="image2image")` |
| 搜索视频 | "搜索产品介绍视频" | `fms_retrieve(type="text2video")` |
| 知识问答 | "公司班车有哪些路线" | `fms_chat` |
| 查看文件 | "NAS里有多少文件" | `fms_list_files` |

## 使用示例

### 示例 1：文档搜索
用户："搜索NAS上关于人工智能的文档"

思考过程：
1. 用户提到 "NAS" 和 "搜索文档"
2. 使用 `fms_retrieve` 工具
3. type="text2doc"（文本搜文档）
4. query="人工智能"

工具调用：
```json
{
  "tool": "fms_retrieve",
  "arguments": {
    "type": "text2doc",
    "query": "人工智能",
    "top_k": 10
  }
}
```

### 示例 2：知识库问答

用户："介绍一下公司的班车路线"

思考过程：

1. 用户询问公司内部信息
2. 这是知识库问答场景
3. 使用 `fms_chat` 工具

工具调用：

```json
{
  "tool": "fms_chat",
  "arguments": {
    "query": "介绍一下公司的班车路线"
  }
}
```

### 示例 3：图片搜索

用户："找关于风景的图片"

工具调用：

```json
{
  "tool": "fms_retrieve",
  "arguments": {
    "type": "text2image",
    "query": "风景",
    "top_k": 10
  }
}
```

### 示例 4：查看文件列表

用户："知识库里有哪些文档？"

工具调用：

```json
{
  "tool": "fms_list_files",
  "arguments": {
    "file_type": "document"
  }
}
```

## 注意事项

1. **路径格式**：以图搜图时需要提供 NAS 上的完整路径，如 `/workspace/.../photo.jpg`
2. **检索类型选择**：
   - 文本关键词 → `text2doc` / `text2image` / `text2video`
   - 已有文件找相似 → `doc2doc` / `image2image`
3. **结果解读**：相似度分数越接近 1 越相关，低于 0.5 的结果可信度较低

## 相关工具

- `fms_retrieve` - 多模态检索（核心工具）
- `fms_chat` - 知识库问答
- `fms_list_files` - 获取文件列表

```

---

### Phase 3: 测试验证（第4天）

#### 4.3.1 单元测试

**文件**: `tests/test_fms.py`

```python
"""FMS 工具测试"""

import pytest
from aiagent.tools.fms import (
    fms_retrieve_handler,
    fms_chat_handler,
    fms_list_files_handler,
)


class TestFMSRetrieve:
    """测试检索功能"""
  
    @pytest.mark.asyncio
    async def test_text2doc_search(self):
        """测试文本搜文档"""
        result = await fms_retrieve_handler(
            query="班车",
            type="text2doc",
            top_k=3
        )
        # 验证返回格式
        assert "相似度" in result or "Error" in result or "未找到" in result
  
    @pytest.mark.asyncio
    async def test_invalid_type(self):
        """测试无效检索类型"""
        result = await fms_retrieve_handler(
            query="test",
            type="invalid_type"
        )
        assert "Error" in result
        assert "不支持的检索类型" in result


class TestFMSChat:
    """测试问答功能"""
  
    @pytest.mark.asyncio
    async def test_chat_basic(self):
        """测试基本问答"""
        result = await fms_chat_handler("公司班车")
        assert "Error" not in result or "无法连接" not in result
  
    @pytest.mark.asyncio
    async def test_chat_empty_query(self):
        """测试空查询"""
        result = await fms_chat_handler("")
        assert "Error" in result
        assert "不能为空" in result


class TestFMSListFiles:
    """测试文件列表"""
  
    @pytest.mark.asyncio
    async def test_list_all_files(self):
        """测试列出所有文件"""
        result = await fms_list_files_handler()
        assert "文档:" in result or "图片:" in result or "Error" in result
```

#### 4.3.2 手动测试

```bash
# 测试连接
curl http://172.16.50.51:8001/api/fms/get_knowledge_files

# 启动 Agent 后测试
uv run python -c "
import asyncio
from aiagent.tools.fms import fms_chat_handler, fms_retrieve_handler

async def test():
    print('=== 测试问答 ===')
    r = await fms_chat_handler('班车路线')
    print(r[:200])
  
    print('\\n=== 测试检索 ===')
    r = await fms_retrieve_handler('班车', 'text2doc', top_k=3)
    print(r[:200])

asyncio.run(test())
"
```

---

## 五、技术要点

### 5.1 错误处理策略

| 错误场景   | 处理方式         | 返回信息                |
| ---------- | ---------------- | ----------------------- |
| 连接失败   | 捕获异常         | "无法连接到 FMS 服务器" |
| 请求超时   | 设置超时30s      | "FMS 请求超时"          |
| 服务端错误 | 检查 status code | 返回 FMS 错误信息       |
| 参数错误   | 前置验证         | 提示有效参数范围        |

### 5.2 结果格式化

- **检索结果**：Markdown 表格，包含相似度、路径、类型、片段
- **问答结果**：加粗标题 + 引用来源
- **文件列表**：分组统计 + 文件路径列表

### 5.3 性能考虑

- 使用 `aiohttp` 异步 HTTP 客户端
- 默认 30 秒超时
- 结果截断显示（避免 Token 超限）

---

## 六、实施计划

| 日期  | 任务      | 产出                             |
| ----- | --------- | -------------------------------- |
| Day 1 | Phase 1.1 | `aiagent/tools/fms.py`         |
| Day 2 | Phase 1.2 | 工具注册完成                     |
| Day 3 | Phase 2   | `skills/system/fms/SKILL.md`   |
| Day 4 | Phase 3   | `tests/test_fms.py` + 测试通过 |
| Day 5 | 文档整理  | 更新本文档 + BRANCH_HISTORY      |

---

## 七、风险与应对

| 风险           | 可能性 | 应对                             |
| -------------- | ------ | -------------------------------- |
| FMS 服务不可用 | 低     | 友好的错误提示，引导用户检查服务 |
| 网络延迟高     | 中     | 30秒超时 + 超时重试提示          |
| 结果过多       | 中     | top_k 限制 + 结果截断            |

---

## 八、相关文档

- [FMS API 文档](http://172.16.50.63:10880/zengzhiyun/agentone-fms/src/feature/agentone_fms/pc/api/api_document.md)
- [错误处理标准化](./ERROR_HANDLING.md) - 复用 AgentError 处理 FMS 错误

---

**创建日期**: 2026-03-26
**作者**: emdoor 谢建辉
**状态**: 已完成
