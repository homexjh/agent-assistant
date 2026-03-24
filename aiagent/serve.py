"""
serve.py - Agent 可视化服务（纯标准库，无第三方依赖）

启动：uv run python -m aiagent.serve
访问：http://localhost:8765
"""
from __future__ import annotations
import asyncio
import inspect
import json
import os
import queue as _qmod
import threading
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env 文件（从项目根目录）
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_path = os.path.join(_project_root, ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)
else:
    load_dotenv()  #  fallback 到当前目录

_HTML_PATH = os.path.join(os.path.dirname(__file__), "web_ui.html")

# run_id -> stop_event，供前端 /stop 调用
_active_runs: dict[str, threading.Event] = {}
_active_lock = threading.Lock()

# 全局 SessionManager 实例（每个 worker 一个）
_session_manager = None

def _get_session_manager():
    """获取或创建 SessionManager 单例"""
    global _session_manager
    if _session_manager is None:
        from .session_manager import SessionManager
        data_dir = Path(__file__).parent.parent / "data" / "sessions"
        _session_manager = SessionManager(data_dir)
    return _session_manager


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静音默认日志

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            self._serve_html()
        elif path == "/run":
            query    = qs.get("q",       [""])[0]
            run_id   = qs.get("rid",     [str(uuid.uuid4())])[0]
            history_raw = qs.get("h",    ["[]"])[0]
            model    = qs.get("model",   [""])[0] or None
            base_url = qs.get("base_url",[""])[0] or None
            api_key  = qs.get("api_key", [""])[0] or None
            provider_type = qs.get("provider_type", ["openai"])[0]
            deployment = qs.get("deployment", [""])[0] or None
            api_version = qs.get("api_version", [""])[0] or None
            try:
                history = json.loads(history_raw)
            except Exception:
                history = []
            self._serve_sse(run_id, query, history,
                            model=model, base_url=base_url, api_key=api_key,
                            provider_type=provider_type, deployment=deployment, api_version=api_version)
        elif path == "/stop":
            rid = qs.get("rid", [""])[0]
            with _active_lock:
                ev = _active_runs.get(rid)
            if ev:
                ev.set()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        elif path == "/cron":
            self._handle_cron_get(qs)
        elif path == "/cron/logs":
            self._handle_cron_logs()
        elif path == "/config":
            self._serve_config()
        elif path == "/api/sessions":
            self._handle_sessions_list()
        elif path.startswith("/api/sessions/"):
            self._handle_session_get(path)
        elif path == "/api/skills":
            self._handle_skills_list()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        # 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        if path == "/cron":
            self._handle_cron_post(data)
        elif path == "/run":
            self._handle_run_post(data)
        elif path.startswith("/api/sessions"):
            self._handle_session_post(path, data)
        else:
            self.send_response(404)
            self.end_headers()
    
    def _handle_run_post(self, data):
        """处理 POST /run 请求（支持文件上传）"""
        import base64
        import tempfile
        
        query = data.get("q", "")
        run_id = data.get("rid", str(uuid.uuid4()))
        history_raw = data.get("h", "[]")
        model = data.get("model") or None
        base_url = data.get("base_url") or None
        api_key = data.get("api_key") or None
        provider_type = data.get("provider_type", "openai")
        deployment = data.get("deployment") or None
        api_version = data.get("api_version") or None
        files = data.get("files", [])
        
        try:
            history = json.loads(history_raw)
        except:
            history = []
        
        # 创建临时目录保存上传的文件
        upload_dir = os.path.join(tempfile.gettempdir(), f"aiagent_uploads_{run_id}")
        os.makedirs(upload_dir, exist_ok=True)
        
        # 处理文件：保存到磁盘并生成描述
        file_descriptions = []
        images_for_vision = []
        saved_files = []  # 记录保存的文件路径，用于清理
        
        for f in files:
            file_name = f.get("name", "unknown")
            file_type = f.get("type", "other")
            file_mime = f.get("mime", "")
            file_size = f.get("size", 0)
            file_data = f.get("data")  # base64 for images
            file_text = f.get("text")  # text content for code files
            
            # 安全化文件名
            safe_name = "".join(c for c in file_name if c.isalnum() or c in "._-").rstrip()
            if not safe_name:
                safe_name = "unnamed_file"
            file_path = os.path.join(upload_dir, safe_name)
            
            if file_type == "image" and file_data:
                # 图片：保存到磁盘 + Vision API 处理
                try:
                    with open(file_path, "wb") as fp:
                        fp.write(base64.b64decode(file_data))
                    saved_files.append(file_path)
                    
                    images_for_vision.append({
                        "name": file_name,
                        "mime": file_mime,
                        "data": file_data
                    })
                    file_descriptions.append(f"[图片: {file_name} (已保存到: {file_path})]")
                except Exception as e:
                    file_descriptions.append(f"[图片: {file_name} (保存失败: {e})]")
                
            elif file_type == "pdf":
                # PDF：保存到磁盘，方便 pdf 工具读取
                try:
                    # PDF 数据需要从 base64 解码（如果前端传了数据）
                    if file_data:
                        with open(file_path, "wb") as fp:
                            fp.write(base64.b64decode(file_data))
                    else:
                        # 如果没有数据，创建一个标记文件
                        file_path = os.path.join(upload_dir, safe_name)
                    saved_files.append(file_path)
                    file_descriptions.append(f"[PDF文件: {file_name} (路径: {file_path})]")
                except Exception as e:
                    file_descriptions.append(f"[PDF文件: {file_name} (保存失败: {e})]")
                
            elif file_type == "code" and file_text:
                # 代码文件：保存到磁盘 + 内容预览
                try:
                    with open(file_path, "w", encoding="utf-8") as fp:
                        fp.write(file_text)
                    saved_files.append(file_path)
                    
                    preview = file_text[:2000]
                    if len(file_text) > 2000:
                        preview += "\n... (内容已截断)"
                    file_descriptions.append(f"[文件: {file_name} (路径: {file_path})]\n```\n{preview}\n```")
                except Exception as e:
                    file_descriptions.append(f"[文件: {file_name} (保存失败: {e})]")
                    
            else:
                # 其他文件：尝试保存
                if file_data:
                    try:
                        with open(file_path, "wb") as fp:
                            fp.write(base64.b64decode(file_data))
                        saved_files.append(file_path)
                        file_descriptions.append(f"[文件: {file_name}, 类型: {file_mime}, 大小: {file_size}字节 (路径: {file_path})]")
                    except Exception as e:
                        file_descriptions.append(f"[文件: {file_name} (保存失败: {e})]")
                else:
                    file_descriptions.append(f"[文件: {file_name}, 类型: {file_mime}, 大小: {file_size}字节]")
        
        # 合并文件描述到查询
        if file_descriptions:
            enriched_query = query + "\n\n" + "\n\n".join(file_descriptions) if query else "\n\n".join(file_descriptions)
        else:
            enriched_query = query
        
        # 发送 SSE 响应
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self._cors()
        self.end_headers()
        
        def emit(event: str, **kwargs):
            data = json.dumps({"event": event, **kwargs}, ensure_ascii=False)
            try:
                self.wfile.write(f"data: {data}\n\n".encode())
                self.wfile.flush()
            except Exception:
                pass
        
        stop_event = threading.Event()
        with _active_lock:
            _active_runs[run_id] = stop_event
        
        q: _qmod.Queue[dict | None] = _qmod.Queue()
        
        def run_agent():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    _run_agent(enriched_query, history, q, stop_event,
                               model=model, base_url=base_url, api_key=api_key,
                               provider_type=provider_type, deployment=deployment, api_version=api_version,
                               images=images_for_vision, session_id=run_id)
                )
            except Exception as e:
                q.put({"event": "error", "message": str(e)})
            finally:
                try:
                    pending = asyncio.all_tasks(loop)
                    if pending:
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                except Exception:
                    pass
                loop.close()
                q.put(None)
        
        t = threading.Thread(target=run_agent, daemon=True)
        t.start()
        
        while True:
            try:
                item = q.get(timeout=300)
            except _qmod.Empty:
                emit("error", message="Agent timeout (300s no response).")
                break
            if item is None:
                break
            emit(**item)
        
        with _active_lock:
            _active_runs.pop(run_id, None)
        
        try:
            self.wfile.write(b'data: {"event":"end"}\n\n')
            self.wfile.flush()
        except Exception:
            pass
    
    def _handle_cron_get(self, qs):
        """处理 GET /cron 请求"""
        from .tools.cron import _jobs
        import time
        
        action = qs.get("action", ["list"])[0]
        
        if action == "list":
            jobs = []
            for job_id, job in _jobs.items():
                jobs.append({
                    "id": job_id,
                    "name": job.get("name", ""),
                    "schedule": job.get("schedule", {}),
                    "enabled": job.get("enabled", True),
                    "run_count": job.get("run_count", 0),
                    "last_run": job.get("last_run"),
                    "next_run": job.get("next_run")
                })
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({"jobs": jobs}).encode())
        else:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Unknown action"}).encode())
    
    def _handle_cron_logs(self):
        """处理 GET /cron/logs 请求"""
        from .tools.cron import get_logs, get_running_agents
        
        logs = get_logs()
        running = get_running_agents()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps({"logs": logs, "running": list(running.keys())}).encode())
    
    def _handle_cron_post(self, data):
        """处理 POST /cron 请求"""
        from .tools.cron import _jobs, _lock, _persist, _parse_schedule, _run_job, _ensure_scheduler
        import time
        
        action = data.get("action", "")
        result = {"status": "error", "error": "Unknown action"}
        
        if action == "list":
            jobs = []
            for job_id, job in _jobs.items():
                jobs.append({
                    "id": job_id,
                    "name": job.get("name", ""),
                    "schedule": job.get("schedule", {}),
                    "enabled": job.get("enabled", True),
                    "run_count": job.get("run_count", 0)
                })
            result = {"status": "ok", "jobs": jobs}
        
        elif action == "add":
            name = data.get("name", "")
            schedule = data.get("schedule", {})
            payload = data.get("payload", {})
            
            if not name or not schedule or not payload:
                result = {"status": "error", "error": "Missing required fields"}
            else:
                _ensure_scheduler()
                job_id = str(uuid.uuid4())[:8]
                now = time.time()
                next_run = _parse_schedule(schedule, now)
                
                job = {
                    "id": job_id,
                    "name": name,
                    "schedule": schedule,
                    "payload": payload,
                    "enabled": True,
                    "next_run": next_run,
                    "run_count": 0,
                    "created_at": now
                }
                
                with _lock:
                    _jobs[job_id] = job
                _persist()
                result = {"status": "ok", "job_id": job_id}
        
        elif action == "remove":
            job_id = data.get("job_id", "")
            if job_id:
                with _lock:
                    if job_id in _jobs:
                        del _jobs[job_id]
                _persist()
                result = {"status": "ok"}
            else:
                result = {"status": "error", "error": "job_id required"}
        
        elif action == "run":
            job_id = data.get("job_id", "")
            if job_id:
                with _lock:
                    job = _jobs.get(job_id)
                if job:
                    _run_job(job)
                    result = {"status": "ok"}
                else:
                    result = {"status": "error", "error": "Job not found"}
            else:
                result = {"status": "error", "error": "job_id required"}
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")

    def _serve_html(self):
        with open(_HTML_PATH, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _serve_config(self):
        """返回服务器配置（从 .env 读取），供前端使用"""
        
        # 构建各提供商配置
        providers = {}
        
        # Kimi 配置
        kimi_key = os.getenv("KIMI_API_KEY", "")
        if kimi_key:
            providers["kimi"] = {
                "base_url": os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
                "api_key": kimi_key,
                "models": os.getenv("KIMI_MODELS", "kimi-k2.5,kimi-k2-0711-preview").split(","),
                "has_key": True,
            }
        
        # Qwen 配置
        qwen_key = os.getenv("QWEN_API_KEY", "")
        if qwen_key:
            providers["qwen"] = {
                "base_url": os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
                "api_key": qwen_key,
                "models": os.getenv("QWEN_MODELS", "qwen3-max-2026-01-23,qwen3.5-plus").split(","),
                "has_key": True,
            }
        
        # Azure 配置
        azure_key = os.getenv("AZURE_API_KEY", "")
        if azure_key:
            providers["azure"] = {
                "endpoint": os.getenv("AZURE_ENDPOINT", ""),
                "deployment": os.getenv("AZURE_DEPLOYMENT", "gpt-4o"),
                "api_version": os.getenv("AZURE_API_VERSION", "2024-08-01-preview"),
                "api_key": azure_key,
                "models": os.getenv("AZURE_MODELS", "gpt-4o").split(","),
                "has_key": True,
                "type": "azure",  # 标记为 Azure 类型，需要特殊处理
            }
        
        config = {
            "default_provider": os.getenv("DEFAULT_PROVIDER", "kimi"),
            "default_model": os.getenv("DEFAULT_MODEL", "kimi-k2.5"),
            "providers": providers,
            "available_providers": list(providers.keys()),
        }
        
        body = json.dumps(config).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _serve_sse(self, run_id: str, query: str, history: list,
                   model=None, base_url=None, api_key=None,
                   provider_type='openai', deployment=None, api_version=None):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self._cors()
        self.end_headers()

        def emit(event: str, **kwargs):
            data = json.dumps({"event": event, **kwargs}, ensure_ascii=False)
            try:
                self.wfile.write(f"data: {data}\n\n".encode())
                self.wfile.flush()
            except Exception:
                pass

        stop_event = threading.Event()
        with _active_lock:
            _active_runs[run_id] = stop_event

        q: _qmod.Queue[dict | None] = _qmod.Queue()

        def run_agent():
            # 每次请求独立的 event loop，不共享，不复用
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    _run_agent(query, history, q, stop_event,
                               model=model, base_url=base_url, api_key=api_key,
                               provider_type=provider_type, deployment=deployment, api_version=api_version,
                               session_id=run_id)
                )
            except Exception as e:
                q.put({"event": "error", "message": str(e)})
            finally:
                # 等待所有 pending tasks 完成再关闭，避免 "Event loop is closed" 警告
                try:
                    pending = asyncio.all_tasks(loop)
                    if pending:
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                except Exception:
                    pass
                loop.close()
                q.put(None)  # 通知主线程结束

        t = threading.Thread(target=run_agent, daemon=True)
        t.start()

        while True:
            try:
                item = q.get(timeout=300)  # 超时保护：5分钟（浏览器操作可能需要较长时间）
            except _qmod.Empty:
                emit("error", message="Agent timeout (300s no response). Task may be too complex. Try breaking it into smaller subtasks.")
                break
            if item is None:
                break
            emit(**item)

        with _active_lock:
            _active_runs.pop(run_id, None)

        try:
            self.wfile.write(b'data: {"event":"end"}\n\n')
            self.wfile.flush()
        except Exception:
            pass


async def _run_agent(query: str, history: list, q: "_qmod.Queue",
                     stop_event: threading.Event,
                     model=None, base_url=None, api_key=None,
                     provider_type='openai', deployment=None, api_version=None,
                     images=None, session_id: str = None):
    """运行 Agent，把事件放入队列。stop_event 置位时立即中断。
    
    Args:
        provider_type: 'openai' 或 'azure'
        deployment: Azure deployment name
        api_version: Azure API version
        images: 图片列表 [{"name": str, "mime": str, "data": base64_str}]
        session_id: 会话ID，用于消息累积和摘要生成
    """

    def put(**kwargs):
        q.put(kwargs)
    
    # 任务列表状态
    todo_state = {"todos": []}
    
    def emit_todo(todos: list[dict]):
        """
        发送任务列表更新。
        todos: [{"id": str, "title": str, "status": "pending|in_progress|done|error"}]
        """
        todo_state["todos"] = todos
        put(event="todo", todos=todos)
    
    # 设置任务列表发送器到上下文
    from .tools import set_todo_emitter
    set_todo_emitter(emit_todo)

    def stopped() -> bool:
        return stop_event.is_set()

    from .tools import get_tool_definitions, execute_tool
    from .workspace import build_system_prompt
    from .subagent import SubagentManager
    from .subagent_tools import (
        create_spawn_tool, create_subagents_tool,
        create_sessions_send_tool, create_agents_list_tool,
    )

    MAX_ROUNDS = 50
    
    # 创建客户端
    if provider_type == 'azure':
        # Azure OpenAI 使用特殊客户端
        from openai import AsyncAzureOpenAI
        client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=base_url,  # Azure 使用 endpoint 不是 base_url
            api_version=api_version or "2024-08-01-preview",
        )
        # Azure 使用 deployment name 而不是 model name
        model = deployment or model
    else:
        # 标准 OpenAI 兼容客户端
        from openai import AsyncOpenAI
        # 多提供商模式：使用传入的参数，仅当为 None 时才使用环境变量
        model    = model if model is not None else os.getenv("MODEL", "kimi-k2.5")
        api_key  = api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "")
        base_url = base_url if base_url is not None else os.getenv("OPENAI_BASE_URL", "https://api.moonshot.cn/v1")
        if not api_key:
            raise ValueError("api_key is required for non-Azure providers")
        if not base_url:
            raise ValueError("base_url is required for non-Azure providers")
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    # 使用传入的 session_id，如果没有则生成新的
    if session_id is None:
        session_id = str(uuid.uuid4())
    manager = SubagentManager(session_id=session_id)

    # 父 Agent workspace（默认）
    from .workspace import _DEFAULT_WORKSPACE
    parent_workspace = _DEFAULT_WORKSPACE

    system_prompt = build_system_prompt()

    def _agent_factory(workspace_dir=None):
        from .agent import Agent
        return Agent(
            model=model,
            api_key=api_key,
            base_url=base_url,
            workspace_dir=workspace_dir or parent_workspace,
            depth=1,
        )

    spawn_tool = create_spawn_tool(
        session_id, manager, _agent_factory,
        depth=0, parent_workspace=str(parent_workspace),
    )
    sub_tool   = create_subagents_tool(session_id, manager)
    send_tool  = create_sessions_send_tool(session_id, manager)
    list_tool  = create_agents_list_tool(manager)

    extra_tools = {
        spawn_tool.name: spawn_tool,
        sub_tool.name:   sub_tool,
        send_tool.name:  send_tool,
        list_tool.name:  list_tool,
    }
    tools = (
        get_tool_definitions()
        + [spawn_tool.definition, sub_tool.definition,
           send_tool.definition,  list_tool.definition]
    )

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    
    # 构造用户消息（支持多模态图片）
    if images:
        content = [{"type": "text", "text": query}]
        for img in images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{img['mime']};base64,{img['data']}"
                }
            })
        messages.append({"role": "user", "content": content})
        user_message_content = query  # 用于 SessionManager
    else:
        messages.append({"role": "user", "content": query})
        user_message_content = query

    put(event="start", model=model)
    
    # 使用 SessionManager 记录用户消息（如果提供了 session_id）
    if session_id:
        try:
            session_mgr = _get_session_manager()
            summary = session_mgr.add_message(session_id, "user", user_message_content)
            if summary:
                print(f"[session] Generated summary for {session_id}: {summary[:50]}...", flush=True)
        except Exception as e:
            print(f"[session] Error adding user message: {e}", flush=True)

    async def exec_tool(tc_id, name, arguments):
        extra = extra_tools.get(name)
        if extra:
            try:
                kwargs = json.loads(arguments)
            except Exception as e:
                return {"role": "tool", "tool_call_id": tc_id,
                        "content": f"Error parsing args: {e}"}
            try:
                if inspect.iscoroutinefunction(extra.handler):
                    content = await extra.handler(**kwargs)
                else:
                    content = extra.handler(**kwargs)
            except Exception as e:
                content = f"Error: {e}"
            return {"role": "tool", "tool_call_id": tc_id, "content": str(content)}
        return await execute_tool(tc_id, name, arguments)

    for round_i in range(MAX_ROUNDS):
        if stopped():
            put(event="stopped")
            return

        put(event="thinking", round=round_i + 1)

        # 计算并发送当前上下文的 token 使用量
        from .token_utils import get_token_usage_info
        token_info = get_token_usage_info(messages, model)
        put(event="token_usage", **token_info)

        try:
            resp = await client.chat.completions.create(
                model=model, messages=messages,
                tools=tools, tool_choice="auto",  # type: ignore
            )
        except Exception as e:
            put(event="error", message=str(e))
            return

        if stopped():
            put(event="stopped")
            return

        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_unset=False))

        # reasoning
        raw = msg.model_dump(exclude_unset=False)
        reasoning = raw.get("reasoning_content") or raw.get("thinking")
        if reasoning:
            put(event="reasoning", round=round_i + 1, content=reasoning)

        # 工具调用
        if msg.tool_calls:
            calls = []
            for tc in msg.tool_calls:
                try:
                    args_obj = json.loads(tc.function.arguments)
                except Exception:
                    args_obj = tc.function.arguments
                calls.append({"id": tc.id, "name": tc.function.name, "args": args_obj})
            put(event="tool_calls", round=round_i + 1, calls=calls)

            results = await asyncio.gather(*[
                exec_tool(tc.id, tc.function.name, tc.function.arguments)
                for tc in msg.tool_calls
            ])

            for tc, result in zip(msg.tool_calls, results):
                content = result["content"]
                img = None
                # 处理浏览器截图 - 支持多种格式
                if tc.function.name == "browser" and isinstance(content, str):
                    # 优先匹配 📸 Screenshot: 格式（自动截图）
                    if "📸 Screenshot:" in content:
                        path = content.split("📸 Screenshot:")[-1].strip().split("\n")[0]
                        img = _img_b64(path)
                    # 也支持旧的 Screenshot saved to: 格式
                    elif "Screenshot saved to:" in content:
                        path = content.split("Screenshot saved to:")[-1].strip()
                        img = _img_b64(path)
                put(event="tool_result", round=round_i + 1,
                    tool_id=tc.id, name=tc.function.name,
                    content=content[:2000], image=img)

            messages.extend(results)
            continue

        # announce 队列（子 Agent 结果）
        # 首先尝试非阻塞获取，如果没有但有活跃子Agent，则等待
        ann_msg = None
        try:
            ann_msg = manager.announce_queue.get_nowait()
        except Exception:
            pass
        
        # 如果没有announce消息但有活跃子Agent，等待它们完成
        if ann_msg is None and manager.count_active() > 0:
            put(event="waiting_subagents", 
                active=manager.count_active(),
                message=f"等待 {manager.count_active()} 个子Agent完成...")
            # 最多等待30秒，每0.5秒检查一次
            for _ in range(60):
                if stopped():
                    put(event="stopped")
                    return
                await asyncio.sleep(0.5)
                try:
                    ann_msg = manager.announce_queue.get_nowait()
                    break  # 获取到消息，跳出等待
                except Exception:
                    pass
                # 如果所有子Agent都结束了但还是没消息，也退出等待
                if manager.count_active() == 0:
                    break
        
        if ann_msg:
            put(event="subagent_announce",
                round=round_i + 1,
                content=str(ann_msg.get("content", ""))[:500])
            messages.append(ann_msg)
            continue

        # 完成
        final_content = msg.content or ""
        put(event="done", content=final_content)
        
        # 使用 SessionManager 记录助手回复（如果提供了 session_id）
        # 这会触发超时检测，如果满足条件会生成摘要
        if session_id:
            try:
                session_mgr = _get_session_manager()
                summary = session_mgr.add_message(session_id, "assistant", final_content)
                if summary:
                    print(f"[session] Generated summary after assistant response: {summary[:50]}...", flush=True)
            except Exception as e:
                print(f"[session] Error adding assistant message: {e}", flush=True)
        
        return

    put(event="done", content="[max tool rounds reached]")


async def _generate_conversation_summary(messages: list[dict], client=None, model=None) -> None:
    """
    生成对话摘要并记录到 Daily Log
    
    触发条件：
    - 有效的 user/assistant 消息 >= 5
    
    模式选择（通过环境变量 DAILY_LOG_SUMMARY_MODE 控制）：
    - rule: 使用规则提取（默认，免费，速度快）
    - llm:  使用 LLM 生成（消耗 token，质量更好）
    """
    from .daily_log import append_to_daily_log
    from datetime import datetime
    import os
    
    # 获取摘要模式
    mode = os.getenv("DAILY_LOG_SUMMARY_MODE", "rule").lower()
    
    print(f"[daily-log-debug] _generate_conversation_summary called with {len(messages)} messages, mode={mode}", flush=True)
    
    # 过滤有效对话消息
    valid_msgs = []
    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")
        
        if role in ["user", "assistant"] and content and len(content) > 5:
            # 排除 reasoning 类型的内容
            metadata = m.get("metadata", {})
            if metadata.get("type") not in ["reasoning", "tool_calls"]:
                valid_msgs.append({"role": role, "content": content[:500]})
    
    print(f"[daily-log-debug] Valid messages: {len(valid_msgs)} (need >= 5)", flush=True)
    
    # 触发条件：至少5轮有效对话
    if len(valid_msgs) < 5:
        print(f"[daily-log-debug] Not enough valid messages, returning", flush=True)
        return
    
    # 只取最近10条，控制 token
    recent_msgs = valid_msgs[-10:]
    
    try:
        # 根据模式选择摘要生成方式
        if mode == "llm" and client and model:
            # LLM 模式：使用 AI 生成摘要
            summary = await _generate_summary_with_llm(recent_msgs, client, model)
        else:
            # Rule 模式：使用规则提取（默认）
            summary = _generate_summary_with_rule(valid_msgs)
        
        # 获取当前时间
        time_str = datetime.now().strftime("%H:%M")
        entry = f"[{time_str}] {summary}"
        
        # 记录到日志
        from .daily_log import get_daily_log_path
        log_path = get_daily_log_path()
        print(f"[daily-log-debug] Writing to: {log_path}", flush=True)
        
        result = append_to_daily_log(entry=entry, section="自动摘要")
        print(f"[daily-log] Summary recorded ({mode}): {result}, entry: {entry}", flush=True)
        
    except Exception as e:
        print(f"[daily-log] Error generating summary: {e}", flush=True)


def _generate_summary_with_rule(valid_msgs: list[dict]) -> str:
    """使用规则提取摘要（免费、快速）"""
    # 取最后一条用户消息作为摘要
    last_user_msg = None
    for m in reversed(valid_msgs):
        if m["role"] == "user":
            last_user_msg = m["content"][:50]
            break
    
    # 统计用户消息数量
    user_count = sum(1 for m in valid_msgs if m["role"] == "user")
    
    if last_user_msg:
        if user_count >= 10:
            return f"深入讨论: {last_user_msg}..."
        elif user_count >= 5:
            return f"对话: {last_user_msg}..."
        else:
            return f"询问: {last_user_msg}..."
    else:
        return "对话完成"


async def _generate_summary_with_llm(recent_msgs: list[dict], client, model: str) -> str:
    """使用 LLM 生成摘要（消耗 token，质量更好）"""
    # 构造对话文本
    conversation_lines = []
    for m in recent_msgs:
        role_display = "用户" if m["role"] == "user" else "助手"
        content = m["content"][:300]
        conversation_lines.append(f"{role_display}: {content}")
    
    conversation_text = "\n".join(conversation_lines)
    
    prompt = f"""请用一句话总结以下对话的核心内容（30字以内）：

{conversation_text}

总结："""
    
    try:
        # 某些模型（如 kimi-k2.5）可能不支持 temperature，尝试不带 temperature 调用
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.3,
            )
        except Exception as e:
            if "temperature" in str(e).lower():
                # 如果不支持 temperature，重试不带该参数
                response = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=50,
                )
            else:
                raise
        
        summary = response.choices[0].message.content.strip()
        
        # 清理前缀
        for prefix in ["总结：", "摘要：", "Summary:", "总结："]:
            if summary.startswith(prefix):
                summary = summary[len(prefix):].strip()
        
        if summary and len(summary) >= 5:
            return summary[:50]  # 限制长度
        else:
            # 如果 LLM 返回空或太短，fallback 到 rule 模式
            return _generate_summary_with_rule(recent_msgs)
            
    except Exception as e:
        print(f"[daily-log] LLM summary failed: {e}, fallback to rule mode", flush=True)
        return _generate_summary_with_rule(recent_msgs)


def _img_b64(path: str) -> str | None:
    import base64
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        ext = path.rsplit(".", 1)[-1].lower()
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")
        return f"data:{mime};base64,{data}"
    except Exception:
        return None


# ============================================================================
# Session API 处理
# ============================================================================

def _json_response(self, data: dict, status: int = 200):
    """发送 JSON 响应"""
    self.send_response(status)
    self.send_header("Content-Type", "application/json")
    self._cors()
    self.end_headers()
    self.wfile.write(json.dumps(data, ensure_ascii=False).encode())


def _handle_sessions_list(self):
    """GET /api/sessions - 获取会话列表"""
    from . import session_store
    sessions = session_store.list_sessions()
    _json_response(self, {"sessions": sessions})


def _handle_session_get(self, path: str):
    """GET /api/sessions/{id} - 获取单个会话"""
    from . import session_store
    
    # 解析路径 /api/sessions/{id}
    parts = path.strip("/").split("/")
    if len(parts) < 3:
        _json_response(self, {"error": "Invalid session ID"}, 400)
        return
    
    session_id = parts[2]
    
    # 特殊处理：clear_all 操作
    if session_id == "clear_all":
        count = session_store.clear_all_sessions()
        _json_response(self, {"cleared": count})
        return
    
    session = session_store.get_session(session_id)
    if session is None:
        _json_response(self, {"error": "Session not found"}, 404)
        return
    
    _json_response(self, session)


def _handle_session_post(self, path: str, data: dict):
    """POST /api/sessions 或 /api/sessions/{id} - 创建或更新会话"""
    from . import session_store
    
    # 解析路径
    parts = path.strip("/").split("/")
    
    # POST /api/sessions - 创建新会话
    if len(parts) < 3:
        title = data.get("title", "新对话")
        model = data.get("model", "")
        session_id = session_store.create_session(title, model)
        _json_response(self, {"id": session_id, "created": True})
        return
    
    session_id = parts[2]
    
    # POST /api/sessions/{id}/delete - 删除会话
    if len(parts) >= 4 and parts[3] == "delete":
        success = session_store.delete_session(session_id)
        _json_response(self, {"success": success})
        return
    
    # POST /api/sessions/{id} - 更新会话
    messages = data.get("messages", [])
    title = data.get("title")
    
    success = session_store.update_session(session_id, messages, title)
    if success:
        _json_response(self, {"success": True, "updated": True})
    else:
        _json_response(self, {"error": "Failed to update session"}, 500)


def _handle_skills_list(self):
    """GET /api/skills - 获取技能列表"""
    try:
        from .skills import scan_skills
        skills = scan_skills()
        
        # 按类别分组
        result = {
            "system": [],
            "user": [],
            "market": [],
            "legacy": []
        }
        
        for skill in skills:
            category = skill.category or "other"
            skill_info = {
                "name": skill.name,
                "description": skill.description,
                "path": str(skill.path),
                "trust_level": skill.trust_level.value,
                "category": category
            }
            if category in result:
                result[category].append(skill_info)
            else:
                result["legacy"].append(skill_info)
        
        _json_response(self, {"skills": result})
    except Exception as e:
        _json_response(self, {"error": str(e)}, 500)


# 绑定方法到 Handler
Handler._json_response = _json_response
Handler._handle_sessions_list = _handle_sessions_list
Handler._handle_session_get = _handle_session_get
Handler._handle_session_post = _handle_session_post
Handler._handle_skills_list = _handle_skills_list


def main():
    port = 8765
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    server.socket.setsockopt(__import__("socket").SOL_SOCKET,
                             __import__("socket").SO_REUSEADDR, 1)
    print(f"AIAgent 可视化服务: http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
