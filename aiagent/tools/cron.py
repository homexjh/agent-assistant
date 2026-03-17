"""
cron 工具：本地定时任务调度

支持：
  add     - 添加任务（at/every/cron 三种调度类型）
  list    - 列出所有任务
  remove  - 删除任务
  run     - 立即触发一次
  status  - 查看调度器状态

任务 payload：
  - "exec"：执行 shell 命令（subprocess）
  - "message"：打印消息到 stdout

任务持久化到 workspace/CRON.json，进程重启后自动恢复。
依赖：schedule（可选，回退到简单 threading）
"""
from __future__ import annotations
import json
import os
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from .types import RegisteredTool, ToolDefinition

# ── 任务注册表 ───────────────────────────────────────────
_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()
_scheduler_thread: threading.Thread | None = None
_running = False

# ── 执行日志 ─────────────────────────────────────────────
_logs: list[dict] = []  # 最近执行日志
_max_logs = 100  # 最多保留100条

# ── 正在执行的任务 ───────────────────────────────────────
_running_agents: dict[str, dict] = {}  # job_id -> {start_time, thread}


def _add_log(job_id: str, job_name: str, kind: str, message: str):
    """添加执行日志"""
    global _logs
    _logs.append({
        "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "job_id": job_id,
        "job_name": job_name,
        "kind": kind,
        "message": message
    })
    # 只保留最近100条
    if len(_logs) > _max_logs:
        _logs = _logs[-_max_logs:]


def get_logs() -> list[dict]:
    """获取执行日志"""
    return _logs.copy()


def get_running_agents() -> dict[str, dict]:
    """获取正在执行的 Agent 任务"""
    # 清理已结束的线程
    current_time = datetime.now(timezone.utc).isoformat()
    for job_id in list(_running_agents.keys()):
        info = _running_agents[job_id]
        thread = info.get("thread")
        if thread and not thread.is_alive():
            del _running_agents[job_id]
    return _running_agents.copy()

_CRON_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "../../workspace/CRON.json"
)


def _persist():
    try:
        path = os.path.abspath(_CRON_FILE)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(_jobs, f, indent=2)
    except Exception:
        pass


def _load_from_disk():
    global _jobs
    try:
        path = os.path.abspath(_CRON_FILE)
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
                _jobs.clear()
                _jobs.update(data)
    except Exception:
        _jobs.clear()


def _run_job(job: dict):
    """执行一个 job。"""
    job["last_run"] = datetime.now(timezone.utc).isoformat()
    job["run_count"] = job.get("run_count", 0) + 1
    payload = job.get("payload", {})
    kind = payload.get("kind", "message")
    job_id = job.get("id", "unknown")
    job_name = job.get("name", "未命名")

    if kind == "exec":
        cmd = payload.get("command", "echo no-command")
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            out = result.stdout.strip() or result.stderr.strip()
            status = "成功" if result.returncode == 0 else f"失败(码{result.returncode})"
            log_msg = f"[{status}] {cmd[:50]} → {out[:100]}"
            print(f"[cron] job={job_id} cmd={cmd!r} → {out[:200]}")
            _add_log(job_id, job_name, "exec", log_msg)
        except Exception as e:
            print(f"[cron] job={job_id} error: {e}")
            _add_log(job_id, job_name, "error", str(e))
    elif kind == "message":
        msg = payload.get("text", "(no message)")
        print(f"[cron] job={job_id} message: {msg}")
        _add_log(job_id, job_name, "message", msg)
    elif kind == "agent":
        # Agent 智能任务 - 像聊天一样让 Agent 执行
        prompt = payload.get("prompt", "")
        if prompt:
            _run_agent_task(job_id, job_name, prompt)
    
    _persist()


def _run_agent_task(job_id: str, job_name: str, prompt: str):
    """在后台线程中运行 Agent 任务"""
    import threading
    
    def agent_worker():
        try:
            import asyncio
            from ..agent import Agent
            
            _add_log(job_id, job_name, "agent", "🤖 Agent 开始执行...")
            
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 创建 Agent 实例
            agent = Agent()
            
            # 运行 Agent
            result = loop.run_until_complete(agent.run(prompt))
            loop.close()
            
            # 记录结果
            summary = result[:200] + "..." if len(result) > 200 else result
            _add_log(job_id, job_name, "agent", f"✅ 完成: {summary}")
            print(f"[cron] Agent job={job_id} completed: {summary[:100]}")
            
        except Exception as e:
            error_msg = str(e)
            _add_log(job_id, job_name, "error", f"❌ Agent 执行失败: {error_msg}")
            print(f"[cron] Agent job={job_id} error: {error_msg}")
        finally:
            # 执行完成后从运行列表移除
            if job_id in _running_agents:
                del _running_agents[job_id]
    
    # 在后台线程中运行，不阻塞调度器
    t = threading.Thread(target=agent_worker, daemon=True, name=f"cron-agent-{job_id[:8]}")
    
    # 记录到运行中任务
    _running_agents[job_id] = {
        "start_time": datetime.now(timezone.utc).isoformat(),
        "thread": t
    }
    
    t.start()
    _add_log(job_id, job_name, "agent", "🚀 已启动 Agent 任务")


def _scheduler_loop():
    """后台线程：每秒检查所有任务是否到期。"""
    global _running
    while _running:
        now = time.time()
        with _lock:
            jobs_snapshot = list(_jobs.values())

        for job in jobs_snapshot:
            if not job.get("enabled", True):
                continue

            schedule = job.get("schedule", {})
            kind = schedule.get("kind")
            next_run = job.get("next_run")

            if next_run and now >= next_run:
                _run_job(job)

                # 计算下次执行时间
                if kind == "every":
                    every_ms = schedule.get("every_ms", 60000)
                    job["next_run"] = now + every_ms / 1000
                elif kind == "cron":
                    job["next_run"] = _next_cron(schedule.get("expr", ""), now)
                elif kind == "at":
                    job["enabled"] = False  # 一次性任务执行后禁用
                    job["next_run"] = None

                with _lock:
                    if job["id"] in _jobs:
                        _jobs[job["id"]] = job
                _persist()

        time.sleep(1)


def _next_cron(expr: str, after: float) -> float | None:
    """计算 cron 表达式的下一次触发时间（使用 croniter 或简单回退）。"""
    try:
        from croniter import croniter
        it = croniter(expr, after)
        return it.get_next(float)
    except ImportError:
        # croniter 未安装，回退为 60 秒后
        return after + 60
    except Exception:
        return None


def _ensure_scheduler():
    global _scheduler_thread, _running
    if _scheduler_thread is None or not _scheduler_thread.is_alive():
        _load_from_disk()
        _running = True
        _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
        _scheduler_thread.start()


def _parse_schedule(schedule: dict, now: float) -> float | None:
    """计算首次执行时间。"""
    kind = schedule.get("kind")
    if kind == "at":
        at_str = schedule.get("at", "")
        try:
            dt = datetime.fromisoformat(at_str.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            return None
    elif kind == "every":
        every_ms = schedule.get("every_ms", 60000)
        return now + every_ms / 1000
    elif kind == "cron":
        return _next_cron(schedule.get("expr", ""), now)
    return None


async def _cron_handler(
    action: str,
    job_id: str | None = None,
    name: str | None = None,
    schedule: dict | None = None,
    payload: dict | None = None,
    enabled: bool = True,
) -> str:
    _ensure_scheduler()

    if action == "status":
        with _lock:
            total = len(_jobs)
            active = sum(1 for j in _jobs.values() if j.get("enabled", True))
        return f"Cron scheduler running. Jobs: {total} total, {active} active."

    if action == "list":
        with _lock:
            jobs = list(_jobs.values())
        if not jobs:
            return "No cron jobs."
        lines = []
        for j in jobs:
            nr = j.get("next_run")
            nr_str = datetime.fromtimestamp(nr).strftime("%Y-%m-%d %H:%M:%S") if nr else "N/A"
            lines.append(
                f"  [{j['id'][:8]}] {j.get('name', '(unnamed)')}  "
                f"enabled={j.get('enabled', True)}  runs={j.get('run_count', 0)}  "
                f"next={nr_str}"
            )
        return "Cron jobs:\n" + "\n".join(lines)

    if action == "add":
        if not schedule or not payload:
            return "Error: 'schedule' and 'payload' are required for action=add."
        now = time.time()
        next_run = _parse_schedule(schedule, now)
        if next_run is None:
            return f"Error: could not parse schedule {schedule}."
        jid = str(uuid.uuid4())[:8]
        job = {
            "id": jid,
            "name": name or jid,
            "schedule": schedule,
            "payload": payload,
            "enabled": enabled,
            "next_run": next_run,
            "run_count": 0,
            "created_at": now,
        }
        with _lock:
            _jobs[jid] = job
        _persist()
        nr_str = datetime.fromtimestamp(next_run).strftime("%Y-%m-%d %H:%M:%S")
        return f"Job added: id={jid} name={job['name']!r} next_run={nr_str}"

    if action == "remove":
        if not job_id:
            return "Error: 'job_id' is required for action=remove."
        # 支持前缀匹配
        with _lock:
            matches = [k for k in _jobs if k.startswith(job_id)]
            if not matches:
                return f"Error: no job found with id starting with '{job_id}'."
            for k in matches:
                del _jobs[k]
        _persist()
        return f"Removed {len(matches)} job(s)."

    if action == "run":
        if not job_id:
            return "Error: 'job_id' is required for action=run."
        with _lock:
            matches = [k for k in _jobs if k.startswith(job_id)]
            if not matches:
                return f"Error: no job found with id starting with '{job_id}'."
            job = _jobs[matches[0]]
        _run_job(job)
        return f"Job {matches[0]!r} triggered immediately."

    return f"Error: unknown action '{action}'. Valid: status/list/add/remove/run"


cron_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "cron",
            "description": (
                "Manage local scheduled tasks. "
                "Supports one-time (at), repeating (every), and cron expression schedules. "
                "Tasks run in the background and persist across tool calls (not process restarts unless re-added)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["status", "list", "add", "remove", "run"],
                        "description": "Action to perform.",
                    },
                    "job_id": {
                        "type": "string",
                        "description": "Job ID (or prefix) for remove/run actions.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Human-readable name for the job (add action).",
                    },
                    "schedule": {
                        "type": "object",
                        "description": (
                            "Schedule definition (add action). "
                            "at: {kind:'at', at:'<ISO-8601 datetime>'}  "
                            "every: {kind:'every', every_ms:<milliseconds>}  "
                            "cron: {kind:'cron', expr:'<cron expression>'}"
                        ),
                    },
                    "payload": {
                        "type": "object",
                        "description": (
                            "What to do when triggered. "
                            "exec: {kind:'exec', command:'<shell command>'}  "
                            "message: {kind:'message', text:'<text to print>'}"
                        ),
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Whether the job is active. Default: true.",
                    },
                },
                "required": ["action"],
            },
        },
    ),
    handler=_cron_handler,  # type: ignore[arg-type]
)
