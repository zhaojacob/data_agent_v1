"""
Data Agent - FastAPI + Chainlit 整合入口
=========================================
FastAPI 作为底座，Chainlit 挂载提供聊天界面。

架构优势：
- 保留 API 接口供外部系统调用（Webhooks、定时任务等）
- Chainlit 提供人类友好的聊天界面
- 单服务部署，成本 $7/月

运行方式：
    uvicorn app:app --host 0.0.0.0 --port 8000

访问：
    - 聊天界面: http://localhost:8000/
    - API 文档: http://localhost:8000/api/docs
    - 健康检查: http://localhost:8000/api/health
"""

import os
import re
import json
import uuid
from typing import Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from chainlit.utils import mount_chainlit

# 加载环境变量
load_dotenv(override=True)

# 导入 Agent
from graph import agent

# ============================================================
# 配置
# ============================================================
IMAGES_DIR = os.getenv('IMAGES_DIR', os.path.join(os.path.dirname(__file__), 'images'))
os.makedirs(IMAGES_DIR, exist_ok=True)

# ============================================================
# 创建 FastAPI 应用
# ============================================================
app = FastAPI(
    title="Data Agent API",
    version="1.0.0",
    description="智能数据分析助手 - FastAPI + Chainlit",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ============================================================
# CORS 配置
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境改为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 静态文件服务（图片）
# ============================================================
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")

# ============================================================
# 请求/响应模型
# ============================================================
class InvokeRequest(BaseModel):
    """Agent 调用请求"""
    message: str = Field(..., description="用户消息")
    thread_id: Optional[str] = Field(None, description="会话 ID（用于记忆）")

class InvokeResponse(BaseModel):
    """Agent 调用响应"""
    output: str
    thread_id: Optional[str] = None

class TriggerReportRequest(BaseModel):
    """触发报告请求"""
    stock: str = Field(..., description="股票代码或名称")
    thread_id: Optional[str] = None

# ============================================================
# API 路由
# ============================================================

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "data-agent",
        "version": "1.0.0",
        "mode": "fastapi+chainlit"
    }


@app.get("/api/")
async def api_root():
    """API 根路径"""
    return {
        "message": "Data Agent API",
        "docs": "/api/docs",
        "health": "/api/health",
        "invoke": "/api/agent/invoke",
        "stream": "/api/agent/stream",
        "chat_ui": "/"
    }


@app.post("/api/agent/invoke", response_model=InvokeResponse)
async def invoke_agent(request: InvokeRequest):
    """
    同步调用 Agent
    
    适用场景：简单查询、快速响应
    """
    try:
        input_data = {"messages": [("user", request.message)]}
        config = {
            "configurable": {"thread_id": request.thread_id},
            "recursion_limit": 50  # 增加递归限制
        } if request.thread_id else {"recursion_limit": 50}
        
        result = agent.invoke(input_data, config=config)
        
        output = "No response"
        if "messages" in result and len(result["messages"]) > 0:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                output = last_message.content
            else:
                output = str(last_message)
        
        return InvokeResponse(output=output, thread_id=request.thread_id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.post("/api/agent/stream")
async def stream_agent(request: InvokeRequest):
    """
    流式调用 Agent (SSE)
    
    适用场景：长任务、需要实时反馈
    
    返回格式（每行）：
        data: {"node": "model", "content": "AI 回复内容"}\n\n
        data: {"node": "tools", "content": "工具执行结果"}\n\n
        data: {"type": "ping"}\n\n  (keep-alive 心跳)
        data: [DONE]\n\n
    
    注意：此函数将 LangGraph stream_mode="updates" 的输出转换为简化的 SSE 格式，
    供前端 Vercel AI SDK useChat hook 消费。
    
    [重要] 使用异步 astream() 并添加 keep-alive 心跳，防止前端超时。
    心跳每 15 秒发送一次，确保连接不会因为工具执行时间过长而断开。
    """
    import asyncio
    
    async def generate():
        # 创建一个队列来存储 SSE 数据
        queue = asyncio.Queue()
        done = asyncio.Event()
        agent_task = None
        keepalive_task = None
        
        async def stream_agent_data():
            """异步流式获取 Agent 数据"""
            try:
                input_data = {"messages": [("user", request.message)]}
                config = {
                    "configurable": {"thread_id": request.thread_id},
                    "recursion_limit": 50
                } if request.thread_id else {"recursion_limit": 50}
                
                async for chunk in agent.astream(input_data, config=config):
                    if done.is_set():  # 检查是否已取消
                        break
                        
                    print(f"[DEBUG] chunk type: {type(chunk)}, keys: {chunk.keys() if isinstance(chunk, dict) else 'N/A'}")
                    
                    for node_name, node_output in chunk.items():
                        print(f"[DEBUG] node_name: {node_name}, node_output type: {type(node_output)}")
                        
                        if "messages" in node_output:
                            messages = node_output["messages"]
                            print(f"[DEBUG] messages type: {type(messages)}, len: {len(messages) if hasattr(messages, '__len__') else 'N/A'}")
                            
                            for msg in messages:
                                print(f"[DEBUG] msg type: {type(msg)}, has content: {hasattr(msg, 'content')}")
                                
                                if hasattr(msg, "content"):
                                    content = msg.content
                                    print(f"[DEBUG] content type: {type(content)}, value: {str(content)[:100]}")
                                    
                                    if isinstance(content, str) and content.strip():
                                        sse_data = json.dumps({'node': node_name, 'content': content}, ensure_ascii=False)
                                        print(f"[DEBUG] Sending SSE: {sse_data[:200]}")
                                        await queue.put(f"data: {sse_data}\n\n")
                
                await queue.put("data: [DONE]\n\n")
            except asyncio.CancelledError:
                print("[DEBUG] Agent task cancelled")
                raise
            except Exception as e:
                print(f"[DEBUG] Agent error: {e}")
                await queue.put(f"data: {json.dumps({'error': str(e)})}\n\n")
            finally:
                done.set()
        
        async def send_keepalive():
            """每 15 秒发送一次心跳"""
            try:
                while not done.is_set():
                    await asyncio.sleep(15)
                    if not done.is_set():
                        print("[DEBUG] Sending keep-alive ping")
                        await queue.put(f"data: {json.dumps({'type': 'ping'})}\n\n")
            except asyncio.CancelledError:
                print("[DEBUG] Keepalive task cancelled")
                raise
        
        try:
            # 启动 Agent 流和心跳任务
            agent_task = asyncio.create_task(stream_agent_data())
            keepalive_task = asyncio.create_task(send_keepalive())
            
            # 从队列中读取数据并 yield
            while not done.is_set() or not queue.empty():
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield data
                except asyncio.TimeoutError:
                    continue
                    
        except GeneratorExit:
            # 客户端断开连接
            print("[DEBUG] Client disconnected")
            done.set()
        except Exception as e:
            print(f"[DEBUG] Stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # 确保清理所有任务
            done.set()
            if keepalive_task and not keepalive_task.done():
                keepalive_task.cancel()
                try:
                    await keepalive_task
                except asyncio.CancelledError:
                    pass
            if agent_task and not agent_task.done():
                agent_task.cancel()
                try:
                    await agent_task
                except asyncio.CancelledError:
                    pass
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/trigger-report")
async def trigger_report(request: TriggerReportRequest):
    """
    触发股票分析报告（示例 Webhook 接口）
    
    适用场景：
    - TradingView 信号触发
    - 定时任务调用
    - 外部系统集成
    """
    try:
        message = f"请分析 {request.stock} 的最新数据，生成简要报告"
        input_data = {"messages": [("user", message)]}
        config = {
            "configurable": {"thread_id": request.thread_id},
            "recursion_limit": 50  # 增加递归限制
        } if request.thread_id else {"recursion_limit": 50}
        
        result = agent.invoke(input_data, config=config)
        
        output = "No response"
        if "messages" in result and len(result["messages"]) > 0:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                output = last_message.content
        
        return {
            "status": "ok",
            "stock": request.stock,
            "report": output
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@app.get("/api/debug/images")
async def list_images():
    """列出已生成的图片（调试用）"""
    try:
        files = []
        if os.path.exists(IMAGES_DIR):
            for f in os.listdir(IMAGES_DIR):
                file_path = os.path.join(IMAGES_DIR, f)
                if os.path.isfile(file_path):
                    files.append({
                        "name": f,
                        "size": os.path.getsize(file_path),
                        "url": f"/images/{f}"
                    })
        return {"images_dir": IMAGES_DIR, "files": files, "count": len(files)}
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# 挂载 Chainlit 到根路径
# ============================================================
# Chainlit 的回调函数在 chainlit_app.py 中定义
mount_chainlit(app=app, target="chainlit_app.py", path="/")


# ============================================================
# 启动入口
# ============================================================
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    print(f"""
    ============================================================
              Data Agent Starting (FastAPI + Chainlit)
    ============================================================
      Chat UI:      http://localhost:{port}/
      API Docs:     http://localhost:{port}/api/docs
      Health:       http://localhost:{port}/api/health
    ============================================================
    """)
    
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
