"""
subagent_tools.py - sessions_spawn 和 subagents 工具

这两个工具需要在 Agent 初始化时动态绑定 manager 和 agent_factory，
所以通过工厂函数创建 RegisteredTool，而不是模块级常量。
"""
from __future__ import annotations
import json
import time
from typing import TYPE_CHECKING
from .tools.types import RegisteredTool, ToolDefinition
from . import subagent_registry as registry
from .subagent import spawn_subagent, SubagentManager

if TYPE_CHECKING:
    from .agent import Agent


def create_spawn_tool(
    parent_id: str,
    manager: SubagentManager,
    agent_factory,
    depth: int = 0,
    parent_workspace: str | None = None,
) -> RegisteredTool:
    """创建 sessions_spawn 工具，绑定当前 Agent 上下文。"""

    async def _handler(
        task: str,
        label: str = "",
        model: str | None = None,
        context_fields: list[str] | None = None,
        cleanup: str = "archive",
        **_: object,
    ) -> str:
        from .tools import emit_todo
        
        # 生成子任务标识
        sub_label = label or f"子任务-{manager.count_active() + 1}"
        emit_todo([
            {"id": f"sub_{sub_label}", "title": f"🔄 {sub_label}", "status": "in_progress"},
        ])
        
        result = spawn_subagent(
            task=task,
            label=sub_label,
            model=model or manager.session_id,  # 子 Agent 继承父 model
            parent_id=parent_id,
            depth=depth,
            manager=manager,
            agent_factory=agent_factory,
            parent_workspace=parent_workspace,
            context_fields=context_fields or ["user_preferences", "current_project", "system"],
            cleanup_policy=cleanup,
        )
        
        # 如果立即出错，标记为错误
        if result.get("status") == "error":
            emit_todo([
                {"id": f"sub_{sub_label}", "title": f"❌ {sub_label}", "status": "error"},
            ])
        
        return json.dumps(result, ensure_ascii=False)

    return RegisteredTool(
        definition=ToolDefinition(
            type="function",
            function={
                "name": "sessions_spawn",
                "description": (
                    "Spawn an isolated subagent to handle a task in the background. "
                    "The subagent runs independently and will announce its result when done. "
                    "Use when: (1) task can run in parallel, (2) task is large and self-contained. "
                    "Returns immediately with a run_id."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "The complete task description for the subagent.",
                        },
                        "label": {
                            "type": "string",
                            "description": "Short human-readable label for this subagent (optional).",
                        },
                        "model": {
                            "type": "string",
                            "description": "Model override for the subagent (optional, inherits parent by default).",
                        },
                        "context_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Fields from parent memory to inject (default: [\"user_preferences\", \"current_project\", \"system\"]).",
                        },
                        "cleanup": {
                            "type": "string",
                            "enum": ["immediate", "keep", "archive"],
                            "description": "Cleanup policy after subagent completes: immediate (delete), keep (retain), archive (move to archive).",
                        },
                    },
                    "required": ["task"],
                },
            },
        ),
        handler=_handler,  # type: ignore[arg-type]
    )


def create_subagents_tool(parent_id: str, manager: SubagentManager) -> RegisteredTool:
    """创建 subagents 工具（list / kill / steer）。"""

    async def _handler(
        action: str = "list",
        target: str | None = None,
        message: str = "",
        **_: object,
    ) -> str:
        runs = registry.list_runs(parent_id)

        if action == "list":
            now = time.time()
            lines: list[str] = []
            active = [r for r in runs if r.ended_at is None]
            recent = [r for r in runs if r.ended_at is not None]

            lines.append(f"active subagents ({len(active)}):")
            if not active:
                lines.append("  (none)")
            for r in active:
                elapsed = int(now - (r.started_at or r.created_at))
                lines.append(f"  [{r.run_id[:8]}] {r.label!r}  running {elapsed}s")

            lines.append(f"\nrecent subagents ({len(recent)}):")
            if not recent:
                lines.append("  (none)")
            for r in recent:
                status = (r.outcome or {}).get("status", "?")
                lines.append(f"  [{r.run_id[:8]}] {r.label!r}  {status}")

            return "\n".join(lines)

        if action == "kill":
            if not target:
                return json.dumps({"status": "error", "error": "target is required for kill"})
            matched = [r for r in runs if r.run_id.startswith(target) or r.label == target]
            if not matched:
                return json.dumps({"status": "error", "error": f"No subagent matching '{target}'"})
            killed = 0
            for r in matched:
                if registry.mark_terminated(r.run_id):
                    killed += 1
            return json.dumps({"status": "ok", "killed": killed})

        if action == "steer":
            if not target:
                return json.dumps({"status": "error", "error": "target is required for steer"})
            if not message:
                return json.dumps({"status": "error", "error": "message is required for steer"})
            matched = [r for r in runs if r.run_id.startswith(target) or r.label == target]
            if not matched:
                return json.dumps({"status": "error", "error": f"No subagent matching '{target}'"})
            # 通过 announce 机制把修正指令注入目标子 Agent（注入父的 announce 队列，
            # 由父在下一轮 LLM 迭代中作为 user message 发给子）
            run = matched[0]
            registry.add_steer(run.run_id, message)
            return json.dumps({
                "status": "ok",
                "message": f"Steer message queued for subagent '{run.label}' ({run.run_id[:8]}). "
                           "It will receive the instruction on its next iteration."
            })

        return json.dumps({"status": "error", "error": f"Unknown action: {action}. Use list/kill/steer."})

    return RegisteredTool(
        definition=ToolDefinition(
            type="function",
            function={
                "name": "subagents",
                "description": (
                    "Manage spawned subagents for this session. "
                    "action='list': show active and recent subagents. "
                    "action='kill': terminate a subagent by run_id prefix or label. "
                    "action='steer': send a mid-course correction message to a running subagent."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["list", "kill", "steer"],
                            "description": "Action to perform.",
                        },
                        "target": {
                            "type": "string",
                            "description": "run_id prefix or label (required for kill/steer).",
                        },
                        "message": {
                            "type": "string",
                            "description": "Correction instruction to send (required for steer).",
                        },
                    },
                    "required": ["action"],
                },
            },
        ),
        handler=_handler,  # type: ignore[arg-type]
    )


def create_sessions_send_tool(
    parent_id: str,
    manager: SubagentManager,
) -> RegisteredTool:
    """创建 sessions_send 工具：向指定 subagent 发送消息（跨 session 通信）。"""

    async def _handler(target: str, message: str, **_: object) -> str:
        all_runs = registry.all_runs()
        matched = [r for r in all_runs if r.run_id.startswith(target) or r.label == target]
        if not matched:
            return json.dumps({"status": "error", "error": f"No subagent matching '{target}'"})
        run = matched[0]
        registry.add_steer(run.run_id, message)
        return json.dumps({
            "status": "ok",
            "sent_to": run.label,
            "run_id": run.run_id[:8],
        })

    return RegisteredTool(
        definition=ToolDefinition(
            type="function",
            function={
                "name": "sessions_send",
                "description": (
                    "Send a message to any running subagent by run_id prefix or label. "
                    "The subagent will receive the message as a steering instruction on its next iteration. "
                    "Use for cross-session communication between agents."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "run_id prefix or label of the target subagent.",
                        },
                        "message": {
                            "type": "string",
                            "description": "Message/instruction to send to the subagent.",
                        },
                    },
                    "required": ["target", "message"],
                },
            },
        ),
        handler=_handler,  # type: ignore[arg-type]
    )


def create_agents_list_tool(manager: SubagentManager) -> RegisteredTool:
    """创建 agents_list 工具：列出所有已知 Agent（跨所有 session）。"""

    async def _handler(**_: object) -> str:
        all_runs = registry.all_runs()
        if not all_runs:
            return "No agents registered."
        import time as _time
        now = _time.time()
        lines = [f"All known agents ({len(all_runs)}):"]
        for r in all_runs:
            rc = "running" if r.ended_at is None else (r.outcome or {}).get("status", "done")
            elapsed = int(now - r.created_at)
            lines.append(
                f"  [{r.run_id[:8]}] label={r.label!r}  parent={r.parent_id[:8]}  "
                f"status={rc}  age={elapsed}s"
            )
        return "\n".join(lines)

    return RegisteredTool(
        definition=ToolDefinition(
            type="function",
            function={
                "name": "agents_list",
                "description": (
                    "List all known agents across all sessions (global registry). "
                    "Shows run_id, label, parent session, status, and age."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        ),
        handler=_handler,  # type: ignore[arg-type]
    )
