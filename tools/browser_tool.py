"""
浏览器自动化工具（browser-use 版本）
====================================
使用 browser-use 库实现 AI 驱动的浏览器自动化

核心理念：
- 只需一个通用工具，用自然语言描述任务
- AI 自动识别页面元素，无需手写选择器
- 凭证通过配置自动注入，安全且灵活

使用前准备：
1. pip install browser-use
2. playwright install chromium
3. 在 .env 文件中配置：
   DEEPSEEK_API_KEY=你的API密钥
   
   # 网站凭证（可选，按需配置）
   CAIXIN_USERNAME=你的用户名
   CAIXIN_PASSWORD=你的密码
"""

import os
import asyncio
from typing import Optional, Dict
from pydantic import BaseModel, Field
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 凭证配置
# ============================================================

def get_all_credentials() -> Dict:
    """
    获取所有已配置的网站凭证
    
    从环境变量读取，格式：{SITE}_USERNAME, {SITE}_PASSWORD
    返回 browser-use 需要的 sensitive_data 格式
    """
    sensitive_data = {}
    
    # 支持的网站列表（可扩展）
    sites = {
        "caixin": ["caixin.com", "caixinglobal.com"],
        "weibo": ["weibo.com", "weibo.cn"],
        "zhihu": ["zhihu.com"],
        # 添加更多网站...
    }
    
    for site_key, domains in sites.items():
        username = os.getenv(f"{site_key.upper()}_USERNAME")
        password = os.getenv(f"{site_key.upper()}_PASSWORD")
        
        if username and password:
            # 为该网站的所有域名配置凭证
            for domain in domains:
                sensitive_data[domain] = {
                    "username": username,
                    "password": password,
                }
    
    return sensitive_data


# ============================================================
# 核心：通用浏览器任务工具
# ============================================================

async def _run_browser_agent(task: str, sensitive_data: Optional[Dict] = None) -> str:
    """
    运行 browser-use Agent 执行任务
    
    Args:
        task: 自然语言描述的任务
        sensitive_data: 敏感数据（用户名密码等）
    
    Returns:
        Agent 执行结果
    """
    try:
        from browser_use import Agent, Browser
        from browser_use.llm import ChatDeepSeek
    except ImportError:
        return "❌ 请先安装 browser-use：pip install browser-use && playwright install chromium"
    
    try:
        # 创建浏览器实例
        browser = Browser(
            headless=True,  # 无头模式，服务器部署用 True
        )
        
        # 创建 LLM（使用 DeepSeek）
        llm = ChatDeepSeek(
            model="deepseek-chat",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
        )
        
        # 合并凭证：自动获取 + 手动传入
        all_creds = get_all_credentials()
        if sensitive_data:
            all_creds.update(sensitive_data)
        
        # 创建 Agent
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            sensitive_data=all_creds if all_creds else None,
        )
        
        # 执行任务
        history = await agent.run()
        
        # 提取结果
        if history:
            # AgentHistoryList 可能不支持直接索引，转为 list
            history_list = list(history) if hasattr(history, '__iter__') else [history]
            if history_list:
                last_step = history_list[-1]
                if hasattr(last_step, 'result'):
                    return str(last_step.result)
                return str(last_step)
        
        return "✅ 任务执行完成"
        
    except Exception as e:
        import traceback
        return f"❌ 浏览器操作失败：{type(e).__name__}: {e}\n{traceback.format_exc()}"


def _run_async(coro):
    """同步运行异步函数"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ============================================================
# 唯一对外工具：browser_task
# ============================================================

class BrowserTaskInput(BaseModel):
    """浏览器任务输入参数"""
    task: str = Field(
        description="""用自然语言描述的浏览器任务。
        
示例：
- "访问财新网，登录后搜索'证监会'，返回前5条新闻的标题和链接"
- "打开百度，搜索'人工智能'，总结前3条结果"
- "访问 https://example.com，提取页面上所有的联系方式"
- "登录微博，查看热搜榜前10条"

提示：
- 如果需要登录，直接说"登录"，系统会自动使用已配置的凭证
- 尽量描述清楚期望的输出格式（如 JSON、列表等）
"""
    )


@tool(args_schema=BrowserTaskInput)
def browser_task(task: str) -> str:
    """
    执行浏览器自动化任务（AI 驱动）
    
    这是一个通用的浏览器操作工具，可以用自然语言描述任何浏览器任务，
    AI 会自动完成页面导航、登录、点击、输入、提取等操作。
    
    特点：
    - 无需指定 CSS 选择器，AI 自动识别页面元素
    - 支持自动登录（需在 .env 中配置网站凭证）
    - 适应网站 UI 变化，无需修改代码
    
    Args:
        task: 用自然语言描述的任务
    
    Returns:
        任务执行结果
    
    示例：
        browser_task("访问财新网，搜索'央行降息'，返回前5条新闻")
        browser_task("登录知乎，查看我的关注列表")
        browser_task("打开淘宝，搜索'机械键盘'，返回最便宜的3个商品")
    """
    result = _run_async(_run_browser_agent(task))
    return result


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    """测试 browser-use 工具"""
    print("=== 通用浏览器任务测试 ===")
    print("已配置的凭证域名:", list(get_all_credentials().keys()))
    print()
    
    # 测试任务
    result = browser_task.invoke({
        "task": "访问 https://search.caixin.com/search/search.jsp?keyword=证监会，提取前3条搜索结果的标题和链接，返回 JSON 格式"
    })
    print(result)
