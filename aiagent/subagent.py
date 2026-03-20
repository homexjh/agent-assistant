"""
subagent.py - 子 Agent 派生与管理

核心机制：
  - spawn_subagent()：在独立线程中异步运行子 Agent，立即返回 run_id
  - 子 Agent 完成后通过 announce 回调通知父 Agent
  - SubagentManager：管理父 Agent 的 announce 消息队列（父←子通信）
  - Workspace 隔离：每个子 Agent 有独立的 workspace 目录
"""
from __future__ import annotations
import asyncio
import queue as _queue_mod
import threading
from pathlib import Path
from typing import Callable
from . import subagent_registry as registry
from .subagent_registry import SubagentRun, new_run_id
from .subagent_workspace import (
    create_subagent_workspace,
    cleanup_subagent_workspace,
    build_context_injection,
)

# 最大递归深度，防止无限派生
MAX_SPAWN_DEPTH = 3
# 最大同时存活的子 Agent 数量
MAX_CHILDREN = 5


class SubagentManager:
    """
    每个父 Agent 实例持有一个 SubagentManager。
    子 Agent 完成后把结果放入 announce_queue（线程安全），
    父 Agent 在空闲时从队列取出并注入对话历史。
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        # 使用线程安全的 queue.Queue，避免跨线程 asyncio event loop 问题
        self.announce_queue: _queue_mod.Queue[dict] = _queue_mod.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None  # 保留兼容接口，不再使用

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """兼容旧接口，现在不需要绑定 loop。"""
        self._loop = loop

    def announce(self, run_id: str, result: str, label: str = "") -> None:
        """子 Agent（在线程中）完成后调用，直接 put 到线程安全队列。"""
        msg = {
            "role": "user",
            "content": f"[subagent:{run_id}] Task completed.\n\nResult:\n{result}",
        }
        self.announce_queue.put(msg)
        
        # 尝试更新任务列表（如果 emit_todo 可用）
        try:
            from .tools import emit_todo
            status_icon = "✓" if "[ERROR]" not in result else "❌"
            status = "done" if "[ERROR]" not in result else "error"
            emit_todo([
                {"id": f"sub_{label or run_id}", "title": f"{status_icon} {label or run_id[:8]}", "status": status},
            ])
        except Exception:
            pass  # 忽略任务列表更新失败

    def count_active(self) -> int:
        runs = registry.list_runs(self.session_id)
        return sum(1 for r in runs if r.ended_at is None)


def spawn_subagent(
    *,
    task: str,
    label: str = "",
    model: str,
    parent_id: str,
    depth: int = 0,
    manager: SubagentManager,
    agent_factory: Callable[..., "Agent"],  # type: ignore[name-defined]  # noqa: F821
    parent_workspace: str | Path | None = None,
    context_fields: list[str] | None = None,
    cleanup_policy: str = "archive",
) -> dict:
    """
    派生一个子 Agent 在后台线程异步执行 task。
    
    新特性（隔离）：
      - 创建独立的 workspace 目录
      - 从父 Agent MEMORY.md 注入上下文
      - 任务完成后按策略清理 workspace
    
    立即返回 {"status": "spawned", "run_id": ..., "label": ..., "workspace": ...}

    安全检查：
      - depth < MAX_SPAWN_DEPTH
      - 当前活跃子数 < MAX_CHILDREN
    """
    if depth >= MAX_SPAWN_DEPTH:
        return {
            "status": "error",
            "error": f"Max spawn depth ({MAX_SPAWN_DEPTH}) reached. Cannot spawn deeper.",
        }

    active = manager.count_active()
    if active >= MAX_CHILDREN:
        return {
            "status": "error",
            "error": f"Too many active subagents ({active}/{MAX_CHILDREN}). Wait for some to finish.",
        }

    run_id = new_run_id()
    effective_label = label or task[:40]

    # 1. 创建隔离的 workspace
    try:
        sub_workspace = create_subagent_workspace(
            label=effective_label,
            parent_workspace=parent_workspace,
            cleanup_policy=cleanup_policy,
        )
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to create subagent workspace: {e}",
        }

    # 2. 从父 Agent MEMORY.md 读取上下文并注入
    parent_ws = Path(parent_workspace) if parent_workspace else None
    if parent_ws:
        memory_path = parent_ws / "MEMORY.md"
        context_injection = build_context_injection(
            memory_path=memory_path,
            fields=context_fields or ["user_preferences", "current_project", "system"],
            max_chars=800,  # 增加一点长度容量以包含工作目录信息
            workspace_dir=sub_workspace,  # 传入工作目录
        )
        # 组装增强 task
        enhanced_task = context_injection + task
    else:
        enhanced_task = task

    run = SubagentRun(
        run_id=run_id,
        parent_id=parent_id,
        task=task,  # 记录原始 task
        label=effective_label,
        model=model,
    )
    registry.register_run(run)

    def _run_in_thread() -> None:
        registry.mark_started(run_id)
        try:
            # 创建使用隔离 workspace 的 Agent
            agent = agent_factory(workspace_dir=sub_workspace)
            result = asyncio.run(agent.run(enhanced_task))
            registry.mark_ended(run_id, {"status": "ok", "result": result})
            manager.announce(run_id, result, label=effective_label)
        except Exception as e:
            err = str(e)
            registry.mark_ended(run_id, {"status": "error", "result": err})
            manager.announce(run_id, f"[ERROR] {err}", label=effective_label)
        finally:
            # 根据策略清理 workspace
            if cleanup_policy == "immediate":
                try:
                    cleanup_subagent_workspace(sub_workspace, policy="immediate")
                except Exception:
                    pass  # 忽略清理错误

    t = threading.Thread(target=_run_in_thread, daemon=True, name=f"subagent-{run_id[:8]}")
    t.start()

    return {
        "status": "spawned",
        "run_id": run_id,
        "label": effective_label,
        "workspace": str(sub_workspace),
        "message": "Subagent started in isolated workspace. You will be notified when it completes.",
    }
