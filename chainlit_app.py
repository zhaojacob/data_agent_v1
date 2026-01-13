"""
Data Agent Chainlit 前端
========================
基于 Chainlit 的聊天界面，直接调用 LangGraph Agent。

功能：
- 与 Data Agent 对话
- 流式输出 Agent 思考过程
- 显示 Agent 生成的图表
- 支持会话历史

运行方式：
    chainlit run chainlit_app.py -w

依赖：
    pip install chainlit
"""

import os
import re
import chainlit as cl
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)

# 导入 Agent
from graph import agent

# 图片目录配置
IMAGES_DIR = os.getenv('IMAGES_DIR', os.path.join(os.path.dirname(__file__), 'images'))
os.makedirs(IMAGES_DIR, exist_ok=True)


@cl.on_chat_start
async def on_chat_start():
    """
    会话开始时的初始化
    """
    # 初始化会话 ID（用于 Agent 记忆）
    import uuid
    thread_id = str(uuid.uuid4())
    cl.user_session.set("thread_id", thread_id)
    
    # 发送欢迎消息
    await cl.Message(
        content="""👋 你好！我是 **Data Agent**，你的智能数据分析助手。

我可以帮你：
- 🔍 **查询数据库** - 执行 SQL 查询，获取数据
- 🐍 **执行 Python 代码** - 数据处理、统计分析
- 📊 **生成图表** - matplotlib/seaborn 可视化
- 🌐 **搜索网络** - 获取最新信息

试试问我：
- "查询 business_data.students_scores 表的所有数据"
- "计算每门课程的平均分"
- "绘制成绩分布柱状图"
"""
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """
    处理用户消息
    """
    # 获取会话 ID
    thread_id = cl.user_session.get("thread_id")
    
    # 构造输入
    input_data = {"messages": [("user", message.content)]}
    config = {"configurable": {"thread_id": thread_id}} if thread_id else None
    
    # 创建一个消息用于流式更新
    msg = cl.Message(content="")
    await msg.send()
    
    try:
        # 使用流式输出
        full_response = ""
        
        async for chunk in stream_agent_response(input_data, config):
            full_response += chunk
            await msg.stream_token(chunk)
        
        # 流式结束
        await msg.update()
        
        # 注意：如果 Agent 返回的消息中已包含 Markdown 图片语法 ![](path)，
        # Chainlit 会自动渲染，无需额外处理。
        # 只有当图片路径是本地文件且 Chainlit 无法直接访问时，才需要手动发送。
        # await handle_images(full_response, msg)
        
    except Exception as e:
        error_msg = f"❌ 发生错误: {str(e)}"
        await msg.stream_token(error_msg)
        await msg.update()


async def stream_agent_response(input_data: dict, config: dict):
    """
    流式获取 Agent 响应
    
    LangGraph Agent 的 stream() 返回的是每个节点的输出，
    我们需要提取最终的 AI 消息内容。
    """
    try:
        for chunk in agent.stream(input_data, config=config):
            # chunk 的结构取决于 Agent 类型
            # 通常是 {"agent": {"messages": [...]}} 或 {"tools": {"messages": [...]}}
            
            if "agent" in chunk:
                messages = chunk["agent"].get("messages", [])
                for msg in messages:
                    if hasattr(msg, "content") and msg.content:
                        yield msg.content
            
            elif "tools" in chunk:
                # 工具调用的中间结果，可以选择显示或跳过
                messages = chunk["tools"].get("messages", [])
                for msg in messages:
                    if hasattr(msg, "content") and msg.content:
                        # 显示工具执行结果（可选）
                        tool_output = msg.content
                        if len(tool_output) > 500:
                            tool_output = tool_output[:500] + "..."
                        yield f"\n\n🔧 *工具执行结果*:\n```\n{tool_output}\n```\n\n"
                        
    except Exception as e:
        yield f"\n\n❌ Agent 执行错误: {str(e)}"


async def handle_images(response_text: str, msg: cl.Message):
    """
    检查响应中是否包含图片路径，如果有则发送图片
    """
    # 匹配图片路径: /images/xxx.png 或 images/xxx.png
    image_pattern = r'/?images/([^\s\)\]]+\.png)'
    matches = re.findall(image_pattern, response_text)
    
    if matches:
        elements = []
        for filename in matches:
            image_path = os.path.join(IMAGES_DIR, filename)
            
            if os.path.exists(image_path):
                # 创建图片元素
                elements.append(
                    cl.Image(
                        name=filename,
                        path=image_path,
                        display="inline"
                    )
                )
        
        if elements:
            # 发送包含图片的消息
            await cl.Message(
                content="📊 生成的图表：",
                elements=elements
            ).send()


# ============================================================
# 可选：挂载 FastAPI（如果需要同时暴露 API）
# ============================================================
# 如果你需要同时提供 API 接口给外部系统调用，
# 可以取消下面的注释，使用 FastAPI 挂载模式。
#
# from fastapi import FastAPI
# from chainlit.utils import mount_chainlit
#
# app = FastAPI(title="Data Agent API")
#
# @app.get("/api/health")
# def health():
#     return {"status": "healthy", "service": "data-agent"}
#
# # 挂载 Chainlit 到根路径
# mount_chainlit(app=app, target="chainlit_app.py", path="/chat")
#
# 启动方式：uvicorn chainlit_app:app --host 0.0.0.0 --port 8000
