"""
agent.py - LLM tool-use 主循环

流程：
  1. 构建 system prompt（来自 workspace/）
  2. 把用户消息 + 历史对话发给 LLM
  3. 如果 LLM 返回 tool_calls → 并行执行所有工具 → 结果追加到对话 → 继续循环
  4. 如果 LLM 返回纯文本 → 检查 announce 队列（子 Agent 是否有结果回来）
     → 有：把结果注入对话，继续循环
     → 无：返回给调用方，循环结束
  5. 每轮 LLM 调用前检查 steer 队列（父 Agent 的修正指令）
"""
from __future__ import annotations
import asyncio
import inspect
import json
import os
import uuid
from openai import AsyncOpenAI
from .tools import get_tool_definitions, execute_tool
from .tools.types import ToolDefinition
from .workspace import build_system_prompt
from .subagent import SubagentManager
from .subagent_tools import (
    create_spawn_tool,
    create_subagents_tool,
    create_sessions_send_tool,
    create_agents_list_tool,
)
from . import subagent_registry as registry

# 最大工具调用轮次，防止死循环
MAX_TOOL_ROUNDS = 50


class Agent:
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        workspace_dir: str | None = None,
        skills_dir: str | None = None,
        depth: int = 0,
        session_id: str | None = None,
        run_id: str | None = None,   # 子 Agent 用，用于轮询 steer 队列
    ):
        self.model = model or os.getenv("MODEL", "kimi-k2-0711-preview")
        self.depth = depth
        self.session_id = session_id or str(uuid.uuid4())
        self.run_id = run_id  # None 表示顶层 Agent

        self.client = AsyncOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY", ""),
            base_url=base_url or os.getenv("OPENAI_BASE_URL", "https://api.moonshot.cn/v1"),
        )
        self.system_prompt = build_system_prompt(workspace_dir, skills_dir)

        # SubagentManager：管理子 Agent 的 announce 队列
        self.manager = SubagentManager(session_id=self.session_id)

        # 工具列表 = 内置工具 + subagent 工具
        _api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        _base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.moonshot.cn/v1")

        def _agent_factory():
            return Agent(
                model=self.model,
                api_key=_api_key,
                base_url=_base_url,
                workspace_dir=workspace_dir,
                skills_dir=skills_dir,
                depth=self.depth + 1,
            )

        self._spawn_tool = create_spawn_tool(
            parent_id=self.session_id,
            manager=self.manager,
            agent_factory=_agent_factory,
            depth=self.depth,
        )
        self._subagents_tool = create_subagents_tool(
            parent_id=self.session_id,
            manager=self.manager,
        )
        self._sessions_send_tool = create_sessions_send_tool(
            parent_id=self.session_id,
            manager=self.manager,
        )
        self._agents_list_tool = create_agents_list_tool(manager=self.manager)

        self._extra_tools: dict[str, object] = {
            self._spawn_tool.name: self._spawn_tool,
            self._subagents_tool.name: self._subagents_tool,
            self._sessions_send_tool.name: self._sessions_send_tool,
            self._agents_list_tool.name: self._agents_list_tool,
        }

        # 最终传给 LLM 的 tool schema
        self.tools: list[ToolDefinition] = (
            get_tool_definitions()
            + [
                self._spawn_tool.definition,
                self._subagents_tool.definition,
                self._sessions_send_tool.definition,
                self._agents_list_tool.definition,
            ]
        )

    async def _execute_tool(self, tool_call_id: str, name: str, arguments: str) -> dict:
        """先查 extra_tools，再走内置工具注册表。"""
        extra = self._extra_tools.get(name)
        if extra is not None:
            try:
                kwargs = json.loads(arguments)
            except json.JSONDecodeError as e:
                return {"role": "tool", "tool_call_id": tool_call_id,
                        "content": f"Error parsing args: {e}"}
            try:
                if inspect.iscoroutinefunction(extra.handler):
                    content = await extra.handler(**kwargs)
                else:
                    content = extra.handler(**kwargs)
            except Exception as e:
                content = f"Error: {e}"
            return {"role": "tool", "tool_call_id": tool_call_id, "content": content}

        return await execute_tool(tool_call_id, name, arguments)

    async def run(self, user_message: str, history: list[dict] | None = None) -> str:
        """
        执行一次完整的 Agent 任务。
        history: 可传入上一轮对话以支持多轮。
        返回最终 assistant 文本回复。
        """
        # 绑定当前事件循环，子线程 announce 时需要
        self.manager.bind_loop(asyncio.get_event_loop())

        messages: list[dict] = [{"role": "system", "content": self.system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        for round_i in range(MAX_TOOL_ROUNDS):

            # ── 每轮前：检查 steer 队列（父 Agent 的修正指令）──
            if self.run_id:
                steer_msg = registry.pop_steer(self.run_id)
                if steer_msg:
                    print(f"\n[steer] received correction: {steer_msg[:80]}")
                    messages.append({"role": "user", "content": f"[STEER] {steer_msg}"})

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,  # type: ignore[arg-type]
                tool_choice="auto",
            )

            msg = response.choices[0].message
            messages.append(msg.model_dump(exclude_unset=False))

            # ── 有工具调用 → 执行 ──────────────────────────
            if msg.tool_calls:
                print(f"\n[round {round_i + 1}] executing {len(msg.tool_calls)} tool call(s)...")
                tool_results = await asyncio.gather(*[
                    self._execute_tool(tc.id, tc.function.name, tc.function.arguments)
                    for tc in msg.tool_calls
                ])
                for tc, result in zip(msg.tool_calls, tool_results):
                    preview = result["content"][:120].replace("\n", " ")
                    print(f"  tool={tc.function.name}  →  {preview}")
                messages.extend(tool_results)
                continue

            # ── 无工具调用 → 检查 announce 队列 ────────────
            # 首先尝试非阻塞获取
            announce_msg = None
            try:
                announce_msg = self.manager.announce_queue.get_nowait()
            except Exception:
                pass
            
            # 如果没有announce消息但有活跃子Agent，等待它们完成
            if announce_msg is None and self.manager.count_active() > 0:
                print(f"\n[waiting] {self.manager.count_active()} subagent(s) running, waiting...")
                # 最多等待60秒，每0.5秒检查一次
                for _ in range(120):
                    await asyncio.sleep(0.5)
                    try:
                        announce_msg = self.manager.announce_queue.get_nowait()
                        break
                    except Exception:
                        pass
                    if self.manager.count_active() == 0:
                        break
            
            if announce_msg:
                print(f"\n[announce] subagent result received, continuing...")
                messages.append(announce_msg)
                continue

            # 队列也空 → 任务完成
            return msg.content or ""

        return "[max tool rounds reached]"
