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
