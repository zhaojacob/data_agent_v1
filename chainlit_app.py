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
    真正的 Token 级别流式输出（打字机效果）
    
    使用 astream_events API 获取 LLM 生成过程中的每个 token，
    实现类似 ChatGPT 的打字机效果。
    """
    print("[DEBUG] stream_agent_response 开始（Token 级别流式）")
    
    try:
        # 使用 astream_events 获取 token 级别的流
        async for event in agent.astream_events(input_data, config=config, version="v2"):
            event_type = event.get("event")
            
            # 调试：打印事件类型（可以注释掉减少日志）
            # print(f"[DEBUG] 事件类型: {event_type}")
            
            # 1. LLM 流式输出 - 打字机效果的核心
            if event_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk:
                    # 获取 token 内容
                    content = None
                    if hasattr(chunk, "content"):
                        content = chunk.content
                    elif isinstance(chunk, dict):
                        content = chunk.get("content")
                    
                    if content:
                        # 逐 token 输出，实现打字机效果
                        yield content
            
            # 2. 工具开始执行 - 显示正在执行的工具
            elif event_type == "on_tool_start":
                tool_name = event.get("name", "unknown")
                print(f"[DEBUG] 工具开始执行: {tool_name}")
                yield f"\n\n🔧 *正在执行工具: {tool_name}*\n"
            
            # 3. 工具执行完成 - 显示结果摘要
            elif event_type == "on_tool_end":
                tool_name = event.get("name", "unknown")
                output = event.get("data", {}).get("output", "")
                print(f"[DEBUG] 工具执行完成: {tool_name}, 输出长度: {len(str(output))}")
                
                # 格式化工具输出
                output_str = str(output)
                if len(output_str) > 500:
                    output_str = output_str[:500] + "...(已截断)"
                
                yield f"\n```\n{output_str}\n```\n\n"
            
            # 4. 链/Agent 结束 - 可选的结束标记
            # elif event_type == "on_chain_end":
            #     print("[DEBUG] Agent 执行完成")
                
    except Exception as e:
        import traceback
        print(f"[ERROR] stream_agent_response 错误:\n{traceback.format_exc()}")
        yield f"\n\n❌ Agent 执行错误: {str(e)}"
    
    print("[DEBUG] stream_agent_response 结束")


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
