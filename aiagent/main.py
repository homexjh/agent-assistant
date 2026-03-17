"""
aiagent - 交互式命令行入口

用法：
  uv run python -m aiagent.main
  或直接：aiagent（安装后）
"""
from __future__ import annotations
import asyncio
import sys
from dotenv import load_dotenv
from aiagent.agent import Agent

load_dotenv()


async def chat_loop() -> None:
    agent = Agent()

    print("=== aiagent ===")
    print(f"model : {agent.model}")
    print(f"tools : {[t['function']['name'] for t in agent.tools]}")
    print("输入 'exit' 退出\n")

    history: list[dict] = []

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("Bye.")
            break

        print("agent> ", end="", flush=True)
        reply = await agent.run(user_input, history=history)
        print(reply)

        # 维护多轮历史
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})


def main() -> None:
    asyncio.run(chat_loop())


if __name__ == "__main__":
    main()
