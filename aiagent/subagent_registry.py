"""
subagent_registry.py - 子 Agent 注册中心（内存 + 磁盘持久化）

每条 SubagentRun 记录一个已派生的子 Agent 任务。
"""
from __future__ import annotations
import json
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path

_REGISTRY_PATH = Path(__file__).parent.parent / ".subagent_registry.json"
_lock = threading.Lock()

# 内存注册表：run_id → SubagentRun
_runs: dict[str, "SubagentRun"] = {}


@dataclass
class SubagentRun:
    run_id: str
    parent_id: str          # 父 Agent 的 session_id
    task: str
    label: str
    model: str
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    ended_at: float | None = None
    outcome: dict | None = None   # {"status": "ok"|"error", "result": str}
    steer_messages: list[str] = field(default_factory=list)  # 待处理的 steer 指令


# ── 写操作 ────────────────────────────────────────────────

def register_run(run: SubagentRun) -> None:
    with _lock:
        _runs[run.run_id] = run
        _persist()


def mark_started(run_id: str) -> None:
    with _lock:
        if run_id in _runs:
            _runs[run_id].started_at = time.time()
            _persist()


def mark_ended(run_id: str, outcome: dict) -> None:
    with _lock:
        if run_id in _runs:
            _runs[run_id].ended_at = time.time()
            _runs[run_id].outcome = outcome
            _persist()


def mark_terminated(run_id: str) -> bool:
    """强制终止（kill）一个运行中的子 Agent，返回是否成功标记。"""
    with _lock:
        run = _runs.get(run_id)
        if run and run.ended_at is None:
            run.ended_at = time.time()
            run.outcome = {"status": "killed"}
            _persist()
            return True
    return False


# ── 读操作 ────────────────────────────────────────────────

def list_runs(parent_id: str) -> list[SubagentRun]:
    with _lock:
        return [r for r in _runs.values() if r.parent_id == parent_id]


def get_run(run_id: str) -> SubagentRun | None:
    with _lock:
        return _runs.get(run_id)


def all_runs() -> list[SubagentRun]:
    """返回所有 Agent 的记录（跨 session）。"""
    with _lock:
        return list(_runs.values())


def add_steer(run_id: str, message: str) -> bool:
    """向指定子 Agent 的 steer 队列追加一条指令，返回是否成功。"""
    with _lock:
        run = _runs.get(run_id)
        if run is None:
            return False
        run.steer_messages.append(message)
        _persist()
        return True


def pop_steer(run_id: str) -> str | None:
    """子 Agent 在每轮循环前调用，取出第一条待处理 steer 指令。"""
    with _lock:
        run = _runs.get(run_id)
        if run and run.steer_messages:
            msg = run.steer_messages.pop(0)
            _persist()
            return msg
    return None


# ── 持久化 ────────────────────────────────────────────────

def _persist() -> None:
    """把当前内存注册表写到磁盘（已持有锁时调用）。"""
    try:
        data = {k: asdict(v) for k, v in _runs.items()}
        _REGISTRY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def load_from_disk() -> None:
    """启动时从磁盘加载历史记录。"""
    if not _REGISTRY_PATH.exists():
        return
    try:
        data = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
        with _lock:
            for k, v in data.items():
                _runs[k] = SubagentRun(**v)
    except Exception:
        pass


def new_run_id() -> str:
    return str(uuid.uuid4())


# 启动时加载
load_from_disk()
