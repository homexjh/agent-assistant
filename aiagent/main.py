"""
aiagent - 交互式命令行入口

用法：
  uv run python -m aiagent.main
  uv run python -m aiagent.main --provider qwen
  uv run python -m aiagent.main --provider azure
  或直接：aiagent（安装后）
"""
from __future__ import annotations
import asyncio
import argparse
import os
import sys
from dotenv import load_dotenv
from aiagent.agent import Agent

# 加载 .env 文件（从项目根目录）
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_path = os.path.join(_project_root, ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)
else:
    load_dotenv()


def get_provider_config(provider: str) -> dict:
    """根据提供商名称获取配置"""
    configs = {
        "kimi": {
            "model": os.getenv("DEFAULT_MODEL", "kimi-k2.5"),
            "api_key": os.getenv("KIMI_API_KEY", ""),
            "base_url": os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
        },
        "qwen": {
            "model": os.getenv("QWEN_MODELS", "qwen3.5-plus").split(",")[0],
            "api_key": os.getenv("QWEN_API_KEY", ""),
            "base_url": os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        },
        "azure": {
            "model": os.getenv("AZURE_MODELS", "gpt-4o").split(",")[0],
            "api_key": os.getenv("AZURE_API_KEY", ""),
            "base_url": os.getenv("AZURE_ENDPOINT", ""),
        },
    }
    return configs.get(provider, configs["kimi"])


async def chat_loop(provider: str = "kimi") -> None:
    # 获取提供商配置
    config = get_provider_config(provider)
    
    if not config["api_key"]:
        print(f"错误: 未配置 {provider} 的 API Key")
        print(f"请在 .env 文件中设置 {provider.upper()}_API_KEY")
        sys.exit(1)
    
    if provider == "azure" and not config["base_url"]:
        print("错误: 使用 Azure 需要配置 AZURE_ENDPOINT")
        sys.exit(1)
    
    # 创建 Agent 实例，传入提供商配置
    agent = Agent(
        model=config["model"],
        api_key=config["api_key"],
        base_url=config["base_url"],
    )

    print("=== aiagent ===")
    print(f"provider: {provider}")
    print(f"model   : {agent.model}")
    print(f"base_url: {config['base_url']}")
    print(f"tools   : {[t['function']['name'] for t in agent.tools]}")
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
    # 获取默认提供商
    default_provider = os.getenv("DEFAULT_PROVIDER", "kimi")
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="AIAgent CLI - 个人AI助手")
    parser.add_argument(
        "--provider", "-p",
        type=str,
        default=default_provider,
        choices=["kimi", "qwen", "azure"],
        help=f"选择LLM提供商 (默认: {default_provider})"
    )
    args = parser.parse_args()
    
    asyncio.run(chat_loop(provider=args.provider))


if __name__ == "__main__":
    main()
