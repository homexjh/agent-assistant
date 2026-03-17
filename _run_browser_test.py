import asyncio, sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from aiagent.agent import Agent

async def main():
    agent = Agent()
    print(f"Model: {agent.model}")
    print("=" * 60)
    reply = await agent.run(
        "请用浏览器打开 https://www.baidu.com，"
        "截图保存到 /tmp/baidu_screenshot.png，"
        "然后在搜索框输入「北京天气」并点击搜索按钮，"
        "再截图保存到 /tmp/baidu_search_result.png，"
        "最后告诉我两张截图的路径和搜索结果页面的标题。"
    )
    print("\n【最终回复】")
    print(reply)

asyncio.run(main())
