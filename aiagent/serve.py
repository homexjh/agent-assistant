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
                               images=images_for_vision)
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
                               provider_type=provider_type, deployment=deployment, api_version=api_version)
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
                     images=None):
    """运行 Agent，把事件放入队列。stop_event 置位时立即中断。
    
    Args:
        provider_type: 'openai' 或 'azure'
        deployment: Azure deployment name
        api_version: Azure API version
        images: 图片列表 [{"name": str, "mime": str, "data": base64_str}]
    """

    def put(**kwargs):
        q.put(kwargs)

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

    session_id = str(uuid.uuid4())
    manager = SubagentManager(session_id=session_id)

    system_prompt = build_system_prompt()

    def _agent_factory():
        from .agent import Agent
        return Agent(model=model, api_key=api_key, base_url=base_url, depth=1)

    spawn_tool = create_spawn_tool(session_id, manager, _agent_factory, depth=0)
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
    else:
        messages.append({"role": "user", "content": query})

    put(event="start", model=model)

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
        put(event="done", content=msg.content or "")
        return

    put(event="done", content="[max tool rounds reached]")


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


def main():
    port = 8765
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    server.socket.setsockopt(__import__("socket").SOL_SOCKET,
                             __import__("socket").SO_REUSEADDR, 1)
    print(f"AIAgent 可视化服务: http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
