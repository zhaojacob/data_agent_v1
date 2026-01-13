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
    print(f"[DEBUG] 收到消息: {message.content}")
    
    # 获取会话 ID
    thread_id = cl.user_session.get("thread_id")
    print(f"[DEBUG] thread_id: {thread_id}")
    
    # 构造输入
    input_data = {"messages": [("user", message.content)]}
    config = {"configurable": {"thread_id": thread_id}} if thread_id else None
    
    # 创建一个消息用于流式更新
    msg = cl.Message(content="")
    await msg.send()
    
    try:
        print("[DEBUG] 开始调用 Agent...")
        # 使用流式输出
        full_response = ""
        
        async for chunk in stream_agent_response(input_data, config):
            print(f"[DEBUG] 收到 chunk: {chunk[:50] if chunk else 'empty'}...")
            full_response += chunk
            await msg.stream_token(chunk)
        
        print(f"[DEBUG] Agent 响应完成，总长度: {len(full_response)}")
        # 流式结束
        await msg.update()
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[ERROR] 发生错误:\n{error_detail}")
        error_msg = f"❌ 发生错误: {str(e)}"
        await msg.stream_token(error_msg)
        await msg.update()


async def stream_agent_response(input_data: dict, config: dict):
    """
    流式获取 Agent 响应
    
    LangGraph Agent 的 stream() 返回的是每个节点的输出，
    我们需要提取最终的 AI 消息内容。
    
    注意：agent.stream() 是同步的，需要在线程池中运行以避免阻塞事件循环
    """
    import asyncio
    
    print("[DEBUG] stream_agent_response 开始")
    
    def sync_stream():
        """同步生成器，在线程池中运行"""
        print("[DEBUG] sync_stream 开始执行")
        results = []
        try:
            for chunk in agent.stream(input_data, config=config):
                print(f"[DEBUG] agent.stream 返回 chunk: {list(chunk.keys())}")
                
                # 处理不同的 chunk 结构
                # LangGraph 可能返回 'agent', 'tools', 'model' 等不同的 key
                for key in chunk:
                    node_output = chunk[key]
                    print(f"[DEBUG] 处理 key={key}, type={type(node_output)}")
                    
                    # 尝试从 messages 中提取内容
                    messages = None
                    if isinstance(node_output, dict):
                        messages = node_output.get("messages", [])
                    elif hasattr(node_output, "messages"):
                        messages = node_output.messages
                    
                    if messages:
                        for msg in messages:
                            content = None
                            if hasattr(msg, "content"):
                                content = msg.content
                            elif isinstance(msg, dict):
                                content = msg.get("content")
                            
                            if content:
                                print(f"[DEBUG] 提取到内容: {content[:100]}...")
                                # 工具消息特殊处理
                                if key == "tools":
                                    if len(content) > 500:
                                        content = content[:500] + "..."
                                    results.append(f"\n\n🔧 *工具执行结果*:\n```\n{content}\n```\n\n")
                                else:
                                    results.append(content)
                    else:
                        # 如果没有 messages，尝试直接获取内容
                        if isinstance(node_output, str):
                            print(f"[DEBUG] 直接字符串: {node_output[:100]}...")
                            results.append(node_output)
                        elif hasattr(node_output, "content") and node_output.content:
                            print(f"[DEBUG] 直接 content: {node_output.content[:100]}...")
                            results.append(node_output.content)
                            
            print(f"[DEBUG] sync_stream 完成，共 {len(results)} 个结果")
        except Exception as e:
            import traceback
            print(f"[ERROR] sync_stream 错误:\n{traceback.format_exc()}")
            results.append(f"\n\n❌ Agent 执行错误: {str(e)}")
        return results
    
    # 在线程池中运行同步代码
    loop = asyncio.get_event_loop()
    print("[DEBUG] 准备在线程池中执行 sync_stream")
    results = await loop.run_in_executor(None, sync_stream)
    print(f"[DEBUG] 线程池执行完成，返回 {len(results)} 个结果")
    
    # 逐个 yield 结果
    for result in results:
        yield result


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
