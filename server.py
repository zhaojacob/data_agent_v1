"""
server.py
=========
Data Agent 后端服务入口

功能：
- 使用 FastAPI 暴露 Agent API
- 提供 /invoke（同步）和 /stream（流式）接口
- 支持 CORS 跨域访问（前端调用）

运行方式：
    本地开发：
        cd F:\\anaconda_projects\\data_agent
        uvicorn server:app --reload --port 8000
    
    或者直接运行：
        python server.py

API 文档：
    启动后访问 http://localhost:8000/docs 查看 Swagger UI
"""

import os
import json
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 加载环境变量（必须在导入 graph 之前）
load_dotenv(override=True)

# 导入 Agent（从 graph.py）
from graph import agent

# ============================================================
# 创建 FastAPI 应用
# ============================================================
app = FastAPI(
    title="Data Agent API",
    version="1.0.0",
    description="智能数据分析助手 API",
)

# ============================================================
# 静态文件服务（用于访问生成的图片）
# ============================================================
images_dir = os.getenv('IMAGES_DIR', '/app/images')
os.makedirs(images_dir, exist_ok=True)
app.mount("/images", StaticFiles(directory=images_dir), name="images")

# ============================================================
# CORS 配置（允许前端跨域访问）
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境改为具体前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 请求/响应模型
# ============================================================
class InvokeRequest(BaseModel):
    """调用请求"""
    message: str
    thread_id: Optional[str] = None

class InvokeResponse(BaseModel):
    """调用响应"""
    output: str
    thread_id: Optional[str] = None

# ============================================================
# 健康检查接口
# ============================================================
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "data-agent",
        "version": "1.0.0"
    }

# ============================================================
# 调试接口：列出 images 目录中的文件
# ============================================================
@app.get("/debug/images")
async def list_images():
    """列出 images 目录中的所有文件（调试用）"""
    try:
        files = []
        if os.path.exists(images_dir):
            for f in os.listdir(images_dir):
                file_path = os.path.join(images_dir, f)
                if os.path.isfile(file_path):
                    files.append({
                        "name": f,
                        "size": os.path.getsize(file_path),
                        "url": f"/images/{f}"
                    })
        return {
            "images_dir": images_dir,
            "exists": os.path.exists(images_dir),
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# 根路径
# ============================================================
@app.get("/")
async def root():
    """根路径，返回 API 信息"""
    return {
        "message": "Data Agent API is running",
        "docs": "/docs",
        "invoke": "/agent/invoke"
    }

# # ============================================================
# # Agent 调用接口（同步）
# # ============================================================
# @app.post("/agent/invoke", response_model=InvokeResponse)
# async def invoke_agent(request: InvokeRequest):
#     """
#     同步调用 Agent
    
#     请求示例：
#         POST /agent/invoke
#         {"message": "查询 students_scores 表的所有数据"}
    
#     响应示例：
#         {"output": "查询结果...", "thread_id": null}
#     """
#     try:
#         # 构造输入（LangGraph Agent 的标准输入格式）
#         input_data = {"messages": [("user", request.message)]}
        
#         # 调用 Agent
#         result = agent.invoke(input_data)
        
#         # 提取最后一条消息作为输出
#         if "messages" in result and len(result["messages"]) > 0:
#             last_message = result["messages"][-1]
#             # 处理不同类型的消息格式
#             if hasattr(last_message, "content"):
#                 output = last_message.content
#             elif isinstance(last_message, tuple):
#                 output = last_message[1]
#             else:
#                 output = str(last_message)
#         else:
#             output = str(result)
        
#         return InvokeResponse(
#             output=output,
#             thread_id=request.thread_id
#         )
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Agent 调用失败: {str(e)}")

# # ============================================================
# # Agent 流式调用接口
# # ============================================================
# @app.post("/agent/stream")
# async def stream_agent(request: InvokeRequest):
#     """
#     流式调用 Agent（Server-Sent Events）
    
#     返回格式：SSE (text/event-stream)
#     """
#     async def generate():
#         try:
#             input_data = {"messages": [("user", request.message)]}
            
#             # 使用 stream 方法
#             for chunk in agent.stream(input_data):
#                 # 将每个 chunk 转为 JSON 并发送
#                 yield f"data: {json.dumps(chunk, ensure_ascii=False, default=str)}\n\n"
            
#             yield "data: [DONE]\n\n"
            
#         except Exception as e:
#             yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
#     return StreamingResponse(
#         generate(),
#         media_type="text/event-stream"
#     )

# ============================================================
# Agent 调用接口（同步）- 修复版
# ============================================================
@app.post("/agent/invoke", response_model=InvokeResponse)
async def invoke_agent(request: InvokeRequest):
    try:
        input_data = {"messages": [("user", request.message)]}
        
        # 构造 Config 以启用记忆
        # 如果前端没传 thread_id，Agent 就不会读取历史，也不会保存历史
        config = {"configurable": {"thread_id": request.thread_id}} if request.thread_id else None
        
        # 调用 Agent (传入 config)
        result = agent.invoke(input_data, config=config)
        
        # 结果解析逻辑
        output = "No response"
        if "messages" in result and len(result["messages"]) > 0:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                output = last_message.content
            else:
                output = str(last_message)
        
        return InvokeResponse(
            output=output,
            thread_id=request.thread_id # 原样返回 ID，方便前端确认
        )
        
    except Exception as e:
        print(f"Error: {e}") # 建议在后台打印日志
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

# ============================================================
# Agent 流式调用接口 - 修复版
# ============================================================
@app.post("/agent/stream")
async def stream_agent(request: InvokeRequest):
    async def generate():
        try:
            input_data = {"messages": [("user", request.message)]}
            config = {"configurable": {"thread_id": request.thread_id}} if request.thread_id else None
            
            # 使用 stream
            for chunk in agent.stream(input_data, config=config):
                # 这里简单处理：直接把 chunk 转字符串发给前端
                # 前端需要根据 LangGraph 的返回结构进行解析
                yield f"data: {json.dumps(chunk, ensure_ascii=False, default=str)}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )



# ============================================================
# 启动入口
# ============================================================
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    print(f"""
    ============================================================
              Data Agent API Server Starting...
    ============================================================
      Local URL:    http://localhost:{port}
      API Docs:     http://localhost:{port}/docs
      Health:       http://localhost:{port}/health
      Agent:        http://localhost:{port}/agent/invoke
    ============================================================
    """)
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
