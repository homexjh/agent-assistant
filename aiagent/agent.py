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
from pathlib import Path
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
from .memory_manager import MemoryManager
from .daily_log import create_daily_log, get_daily_log_path

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
        # 支持多种环境变量名（兼容不同配置习惯）
        self.model = model or os.getenv("MODEL") or os.getenv("DEFAULT_MODEL") or "kimi-k2-0711-preview"
        self.depth = depth
        self.session_id = session_id or str(uuid.uuid4())
        self.run_id = run_id  # None 表示顶层 Agent

        # API 配置：优先使用传入参数，其次尝试多种环境变量名
        _api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("KIMI_API_KEY") or ""
        _base_url = base_url or os.getenv("OPENAI_BASE_URL") or os.getenv("KIMI_BASE_URL") or "https://api.moonshot.cn/v1"
        
        self.client = AsyncOpenAI(
            api_key=_api_key,
            base_url=_base_url,
        )
        self.system_prompt = build_system_prompt(workspace_dir, skills_dir)
        
        # 自动更新 MEMORY.md 中的日期
        self._update_memory_date(workspace_dir)
        
        # 自动创建今天的日志文件（如果不存在）
        self._ensure_daily_log()

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

    def _update_memory_date(self, workspace_dir: str | None) -> None:
        """更新 MEMORY.md 中的 system.current_date为今天"""
        from .workspace import _DEFAULT_WORKSPACE
        ws = Path(workspace_dir) if workspace_dir else _DEFAULT_WORKSPACE
        memory_path = ws / "MEMORY.md"
        
        if memory_path.exists():
            try:
                mm = MemoryManager(memory_path)
                mm.update_system_date()
            except Exception:
                # 如果更新失败，无需报错（非关键功能）
                pass

    def _ensure_daily_log(self) -> None:
        """确保今天的日志文件存在（如果不存在则创建）"""
        try:
            log_path = get_daily_log_path()
            if not log_path.exists():
                create_daily_log()
        except Exception:
            # 如果创建失败，无需报错（非关键功能）
            pass

    async def _auto_log_summary(self, messages: list[dict]) -> None:
        """
        后台任务：自动生成对话摘要并记录到日志
        
        触发条件：
        - 对话轮数 > 5
        - 有效的 user/assistant 消息 >= 2
        """
        start_msg = f"[auto-log-debug] _auto_log_summary started with {len(messages)} messages"
        print(start_msg, flush=True)
        
        # 写入文件确保能看到
        try:
            from pathlib import Path
            Path("/tmp/summary-debug.log").write_text(start_msg + "\n", encoding="utf-8")
        except:
            pass
        
        # 使用 print 代替 logging，因为 Server 中 logging 可能未配置
        def log(msg):
            line = f"[auto-log] {msg}"
            print(line, flush=True)
            # 追加到文件
            try:
                from pathlib import Path
                Path("/tmp/summary-debug.log").write_text(line + "\n", encoding="utf-8")
            except:
                pass
        
        try:
            # 过滤有效对话消息
            valid_msgs = []
            for m in messages:
                role = m.get("role", "")
                content = m.get("content", "")
                
                # 只取 user 和 assistant 的消息，排除系统消息和工具调用
                if role in ["user", "assistant"] and content and len(content) >= 3:
                    # 排除 reasoning 类型的内容
                    metadata = m.get("metadata", {})
                    if metadata.get("type") not in ["reasoning", "tool_calls"]:
                        valid_msgs.append({"role": role, "content": content[:500]})
            
            log(f"Total messages: {len(messages)}, Valid: {len(valid_msgs)}")
            
            # 触发条件：至少5轮有效对话
            if len(valid_msgs) < 5:
                log(f"Not enough valid messages ({len(valid_msgs)} < 5), skipping")
                return
            
            # 只取最近10条，控制 token
            recent_msgs = valid_msgs[-10:]
            
            # 构造对话文本
            conversation_lines = []
            for m in recent_msgs:
                role_display = "用户" if m["role"] == "user" else "助手"
                # 截断过长内容
                content = m["content"][:300]
                conversation_lines.append(f"{role_display}: {content}")
            
            conversation_text = "\n".join(conversation_lines)
            
            # 构造 prompt
            prompt = f"""请用一句话总结以下开发对话的核心内容（30字以内）：

{conversation_text}

总结："""
            
            # 调用 LLM 生成摘要
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.3,
            )
            
            summary = response.choices[0].message.content.strip()
            log(f"Generated summary: {summary[:50]}...")
            
            # 清理输出（去掉可能的前缀）
            for prefix in ["总结：", "摘要：", "Summary:"]:
                if summary.startswith(prefix):
                    summary = summary[len(prefix):].strip()
            
            if not summary or len(summary) < 5:
                log(f"Summary too short, skipping")
                return
            
            # 获取当前时间
            from datetime import datetime
            time_str = datetime.now().strftime("%H:%M")
            
            # 记录到日志
            from .daily_log import append_to_daily_log
            entry = f"[{time_str}] {summary}"
            result = append_to_daily_log(entry=entry, section="自动摘要")
            
            log(f"Append result: {result}, entry: {entry[:50]}...")
            print(f"[auto-log] 已记录对话摘要: {summary[:50]}...")
            
        except Exception as e:
            # 非关键功能，失败时记录日志但不阻断主流程
            import traceback
            log(f"Error: {e}")
            log(traceback.format_exc())

    async def _execute_tool(self, tool_call_id: str, name: str, arguments: str) -> dict:
        """先查 extra_tools，再走内置工具注册表。
        
        新增：错误标准化和广播
        """
        from .error_parser import ErrorParser
        from .resource_bridge import emit_error
        
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
            
            # 解析并广播错误（子 Agent 工具）
            error = ErrorParser.parse(content, name)
            if error:
                context = {
                    "session_id": self.session_id,
                    "tool_call_id": tool_call_id,
                    "tool_name": name,
                    "agent_depth": self.depth,
                    "timestamp": error.timestamp,
                }
                emit_error(error, context)
                return {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": error.to_llm_text(),
                    "_structured_error": error.to_dict(),
                }
            
            return {"role": "tool", "tool_call_id": tool_call_id, "content": content}

        return await execute_tool(tool_call_id, name, arguments)

    async def run(self, user_message: str, history: list[dict] | None = None, images: list[dict] | None = None) -> str:
        """
        执行一次完整的 Agent 任务。
        history: 可传入上一轮对话以支持多轮。
        images: 图片列表 [{"name": str, "mime": str, "data": base64_str}]
        返回最终 assistant 文本回复。
        """
        # 绑定当前事件循环，子线程 announce 时需要
        self.manager.bind_loop(asyncio.get_event_loop())

        messages: list[dict] = [{"role": "system", "content": self.system_prompt}]
        if history:
            messages.extend(history)
        
        # 构造用户消息（支持多模态图片）
        if images:
            # OpenAI vision 格式
            content = [{"type": "text", "text": user_message}]
            for img in images:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{img['mime']};base64,{img['data']}"
                    }
                })
            messages.append({"role": "user", "content": content})
        else:
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
            final_content = msg.content or ""
            
            # 生成对话摘要并记录（在返回前完成）
            # 这是在对话完成后执行的，不会阻塞用户响应时间
            debug_msg = f"[auto-log-debug] About to call _auto_log_summary with {len(messages)} messages\n"
            print(debug_msg, flush=True)
            
            # 同时写入文件（确保能看到）
            try:
                from pathlib import Path
                Path("/tmp/agent-debug.log").write_text(debug_msg, encoding="utf-8")
            except:
                pass
            
            try:
                await self._auto_log_summary(messages.copy())
            except Exception as e:
                import traceback
                err_msg = f"[auto-log] Failed to generate summary: {e}\n{traceback.format_exc()}"
                print(err_msg, flush=True)
                # 写入错误日志
                try:
                    from pathlib import Path
                    Path("/tmp/agent-error.log").write_text(err_msg, encoding="utf-8")
                except:
                    pass
            
            return final_content

        return "[max tool rounds reached]"
