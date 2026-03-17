"""process 工具：管理后台进程（start/list/kill/log）"""
from __future__ import annotations
import json
import os
import subprocess
import threading
import time
from .types import RegisteredTool, ToolDefinition

# 进程注册表：name → {"proc": Popen, "cmd": str, "started_at": float, "log": [str]}
_procs: dict[str, dict] = {}
_lock = threading.Lock()
_MAX_LOG_LINES = 200


def _collect_output(name: str, stream, tag: str) -> None:
    """后台线程：持续读取进程 stdout/stderr 存入 log。"""
    try:
        for line in stream:
            with _lock:
                if name in _procs:
                    entry = f"[{tag}] {line.rstrip()}"
                    _procs[name]["log"].append(entry)
                    if len(_procs[name]["log"]) > _MAX_LOG_LINES:
                        _procs[name]["log"] = _procs[name]["log"][-_MAX_LOG_LINES:]
    except Exception:
        pass


async def _process_handler(
    action: str,
    name: str = "",
    command: str = "",
    cwd: str | None = None,
    lines: int = 20,
) -> str:
    """
    action:
      start  - 启动后台进程，name 必须唯一
      list   - 列出所有后台进程及状态
      kill   - 终止指定 name 的进程
      log    - 查看指定 name 的最近输出
    """
    if action == "start":
        if not name:
            return json.dumps({"status": "error", "error": "name is required for start"})
        if not command:
            return json.dumps({"status": "error", "error": "command is required for start"})
        with _lock:
            if name in _procs and _procs[name]["proc"].poll() is None:
                return json.dumps({"status": "error", "error": f"Process '{name}' is already running"})

        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})

        entry: dict = {
            "proc": proc,
            "cmd": command,
            "started_at": time.time(),
            "log": [],
        }
        with _lock:
            _procs[name] = entry

        threading.Thread(target=_collect_output, args=(name, proc.stdout, "out"), daemon=True).start()
        threading.Thread(target=_collect_output, args=(name, proc.stderr, "err"), daemon=True).start()

        return json.dumps({"status": "started", "name": name, "pid": proc.pid, "command": command})

    if action == "list":
        with _lock:
            snapshot = {k: v for k, v in _procs.items()}
        if not snapshot:
            return "No background processes."
        rows = []
        for n, info in snapshot.items():
            rc = info["proc"].poll()
            status = "running" if rc is None else f"exited({rc})"
            elapsed = int(time.time() - info["started_at"])
            rows.append(f"  [{n}] {status}  {elapsed}s  cmd={info['cmd'][:60]}")
        return "Background processes:\n" + "\n".join(rows)

    if action == "kill":
        if not name:
            return json.dumps({"status": "error", "error": "name is required for kill"})
        with _lock:
            info = _procs.get(name)
        if info is None:
            return json.dumps({"status": "error", "error": f"No process named '{name}'"})
        proc = info["proc"]
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        with _lock:
            _procs.pop(name, None)
        return json.dumps({"status": "killed", "name": name})

    if action == "log":
        if not name:
            return json.dumps({"status": "error", "error": "name is required for log"})
        with _lock:
            info = _procs.get(name)
        if info is None:
            return f"No process named '{name}'."
        log = info["log"][-lines:]
        rc = info["proc"].poll()
        status = "running" if rc is None else f"exited({rc})"
        header = f"[{name}] status={status}\n"
        return header + ("\n".join(log) if log else "(no output yet)")

    return json.dumps({"status": "error", "error": f"Unknown action: {action}. Use start/list/kill/log."})


process_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "process",
            "description": (
                "Manage background processes. "
                "action='start': launch a command in background (non-blocking). "
                "action='list': show all background processes and their status. "
                "action='kill': terminate a process by name. "
                "action='log': view recent stdout/stderr of a process."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["start", "list", "kill", "log"],
                        "description": "Action to perform.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Unique name for the process (required for start/kill/log).",
                    },
                    "command": {
                        "type": "string",
                        "description": "Shell command to run (required for start).",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory (optional, for start).",
                    },
                    "lines": {
                        "type": "integer",
                        "description": "Number of recent log lines to return (optional, for log, default 20).",
                    },
                },
                "required": ["action"],
            },
        },
    ),
    handler=_process_handler,  # type: ignore[arg-type]
)
