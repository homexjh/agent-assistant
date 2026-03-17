"""
aiagent - 交互式命令行入口

用法：
  uv run python -m aiagent.main
  uv run python -m aiagent.main --provider qwen
  uv run python -m aiagent.main --provider qwen --model qwen3-coder-plus
  uv run python -m aiagent.main --list-models
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


def get_provider_config(provider: str, model: str | None = None) -> dict:
    """根据提供商名称获取配置
    
    Args:
        provider: 提供商名称 (kimi/qwen/azure)
        model: 指定的模型名称，如果为None则使用默认值
    """
    # 从环境变量获取模型列表
    kimi_models = os.getenv("KIMI_MODELS", "kimi-k2.5,kimi-k2-0711-preview,moonshot-v1-8k").split(",")
    qwen_models = os.getenv("QWEN_MODELS", "qwen3.5-plus,qwen3-max-2026-01-23,qwen3-coder-next,qwen3-coder-plus").split(",")
    azure_models = os.getenv("AZURE_MODELS", "gpt-4o").split(",")
    
    configs = {
        "kimi": {
            "models": kimi_models,
            "default_model": os.getenv("DEFAULT_MODEL", kimi_models[0]),
            "api_key": os.getenv("KIMI_API_KEY", ""),
            "base_url": os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
        },
        "qwen": {
            "models": qwen_models,
            "default_model": qwen_models[0],
            "api_key": os.getenv("QWEN_API_KEY", ""),
            "base_url": os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        },
        "azure": {
            "models": azure_models,
            "default_model": azure_models[0],
            "api_key": os.getenv("AZURE_API_KEY", ""),
            "base_url": os.getenv("AZURE_ENDPOINT", ""),
        },
    }
    
    config = configs.get(provider, configs["kimi"])
    # 如果指定了模型，使用指定的；否则使用默认
    config["model"] = model if model else config["default_model"]
    return config


def list_all_models():
    """列出所有提供商的可用模型"""
    print("=== AIAgent 可用模型列表 ===\n")
    
    providers = ["kimi", "qwen", "azure"]
    default_provider = os.getenv("DEFAULT_PROVIDER", "kimi")
    
    for provider in providers:
        config = get_provider_config(provider)
        has_key = "✓" if config["api_key"] else "✗"
        is_default = " (默认)" if provider == default_provider else ""
        
        print(f"{provider.upper()}{is_default} [{has_key}]")
        print(f"  Base URL: {config['base_url'] or '未配置'}")
        print("  可用模型:")
        for i, model in enumerate(config["models"], 1):
            marker = " →" if model == config["default_model"] else "   "
            print(f"    {i}.{marker} {model}")
        print()
    
    print("使用方式:")
    print("  uv run python -m aiagent.main --provider qwen")
    print("  uv run python -m aiagent.main --provider qwen --model qwen3-coder-plus")


async def chat_loop(provider: str = "kimi", model: str | None = None) -> None:
    # 获取提供商配置
    config = get_provider_config(provider, model)
    
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
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="指定使用的模型名称 (如: qwen3.5-plus, gpt-4o)"
    )
    parser.add_argument(
        "--list-models", "-l",
        action="store_true",
        help="列出所有可用的模型"
    )
    args = parser.parse_args()
    
    # 如果指定了 --list-models，显示模型列表并退出
    if args.list_models:
        list_all_models()
        return
    
    asyncio.run(chat_loop(provider=args.provider, model=args.model))


if __name__ == "__main__":
    main()
