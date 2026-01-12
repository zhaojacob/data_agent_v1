"""
Data Agent Streamlit 前端
========================
一个简洁的聊天界面，连接到你的 Data Agent 后端。

功能：
- 与 Data Agent 对话
- 显示 Agent 生成的图表
- 支持会话历史
- 支持本地和云端后端

运行方式：
    streamlit run streamlit_app.py

依赖：
    pip install streamlit requests
"""

import streamlit as st
import requests
import uuid
import os
from datetime import datetime

# ============================================================
# 配置
# ============================================================

# 后端 API 地址（优先使用环境变量，否则使用默认值）
API_URL = os.getenv(
    "DATA_AGENT_API_URL", 
    "https://data-agent-v1.onrender.com"  # 你的 Render 部署地址
)

# 本地开发时可以切换到本地地址
# API_URL = "http://localhost:8000"

# ============================================================
# 页面配置
# ============================================================

st.set_page_config(
    page_title="Data Agent - 智能数据分析助手",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 自定义样式
# ============================================================

st.markdown("""
<style>
    /* 主标题样式 */
    .main-title {
        text-align: center;
        color: #1E88E5;
        margin-bottom: 0;
    }
    
    /* 副标题样式 */
    .sub-title {
        text-align: center;
        color: #666;
        font-size: 1.1rem;
        margin-top: 0;
    }
    
    /* 聊天消息样式 */
    .user-message {
        background-color: #E3F2FD;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 5px 0;
    }
    
    .assistant-message {
        background-color: #F5F5F5;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 5px 0;
    }
    
    /* 功能卡片样式 */
    .feature-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #1E88E5;
        margin: 10px 0;
    }
    
    /* 状态指示器 */
    .status-online {
        color: #4CAF50;
        font-weight: bold;
    }
    
    .status-offline {
        color: #f44336;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 侧边栏
# ============================================================

with st.sidebar:
    st.markdown("## ⚙️ 设置")
    
    # API 地址配置
    api_url_input = st.text_input(
        "后端 API 地址",
        value=API_URL,
        help="Data Agent 后端服务的地址"
    )
    
    # 更新 API 地址
    if api_url_input != API_URL:
        API_URL = api_url_input
    
    # 检查后端状态
    st.markdown("### 🔗 连接状态")
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        if response.status_code == 200:
            st.markdown('<span class="status-online">● 已连接</span>', unsafe_allow_html=True)
            health_data = response.json()
            st.caption(f"服务版本: {health_data.get('version', 'unknown')}")
        else:
            st.markdown('<span class="status-offline">● 连接异常</span>', unsafe_allow_html=True)
    except requests.exceptions.Timeout:
        st.markdown('<span class="status-offline">● 服务启动中...</span>', unsafe_allow_html=True)
        st.caption("免费服务可能需要 30-60 秒唤醒")
    except Exception as e:
        st.markdown('<span class="status-offline">● 无法连接</span>', unsafe_allow_html=True)
        st.caption(f"错误: {str(e)[:50]}")
    
    st.markdown("---")
    
    # 会话管理
    st.markdown("### 💬 会话管理")
    
    if st.button("🗑️ 清空对话历史", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()
    
    # 显示会话 ID
    if "thread_id" in st.session_state:
        st.caption(f"会话 ID: {st.session_state.thread_id[:8]}...")
    
    st.markdown("---")
    
    # 功能说明
    st.markdown("### 📚 功能说明")
    
    st.markdown("""
    <div class="feature-card">
        <strong>🔍 数据库查询</strong><br>
        查询 PostgreSQL 数据库中的数据
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <strong>🐍 Python 执行</strong><br>
        在安全沙盒中执行数据分析代码
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <strong>📊 数据可视化</strong><br>
        生成 matplotlib/seaborn 图表
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <strong>🌐 网络搜索</strong><br>
        搜索互联网获取最新信息
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.caption("Powered by LangGraph + DeepSeek")

# ============================================================
# 主界面
# ============================================================

# 标题
st.markdown('<h1 class="main-title">📊 Data Agent</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">智能数据分析助手 - 查询、分析、可视化</p>', unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# 初始化会话状态
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# ============================================================
# 显示聊天历史
# ============================================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # 如果消息中包含图片路径，显示图片
        if "image_path" in message:
            try:
                st.image(message["image_path"], caption="Agent 生成的图表")
            except Exception:
                st.caption(f"图片路径: {message['image_path']}")

# ============================================================
# 示例问题
# ============================================================

if len(st.session_state.messages) == 0:
    st.markdown("### 💡 试试这些问题：")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📋 查询学生成绩表", use_container_width=True):
            st.session_state.pending_question = "查询 business_data.students_scores 表的所有数据"
            st.rerun()
        
        if st.button("📊 绘制成绩分布图", use_container_width=True):
            st.session_state.pending_question = "从 students_scores 表提取数据，绘制各科成绩的柱状图"
            st.rerun()
    
    with col2:
        if st.button("🔢 计算平均分", use_container_width=True):
            st.session_state.pending_question = "计算 students_scores 表中每门课程的平均分"
            st.rerun()
        
        if st.button("🌐 搜索最新新闻", use_container_width=True):
            st.session_state.pending_question = "搜索今天的科技新闻"
            st.rerun()

# ============================================================
# 处理待处理的问题（来自示例按钮）
# ============================================================

if "pending_question" in st.session_state:
    pending = st.session_state.pending_question
    del st.session_state.pending_question
    
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": pending})
    
    # 调用 API
    with st.chat_message("user"):
        st.markdown(pending)
    
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            try:
                response = requests.post(
                    f"{API_URL}/agent/invoke",
                    json={
                        "message": pending,
                        "thread_id": st.session_state.thread_id
                    },
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    assistant_message = result.get("output", "抱歉，我没有得到有效的回复。")
                else:
                    assistant_message = f"❌ 请求失败: {response.status_code}"
                    
            except requests.exceptions.Timeout:
                assistant_message = "⏱️ 请求超时，服务可能正在启动中，请稍后重试。"
            except Exception as e:
                assistant_message = f"❌ 发生错误: {str(e)}"
        
        st.markdown(assistant_message)
        
        # 检查是否有图片（支持多种路径格式）
        if "images/" in assistant_message or "/images/" in assistant_message:
            import re
            # 匹配 /images/xxx.png 或 images/xxx.png
            image_matches = re.findall(r'/?images/[^\s\)\]]+\.png', assistant_message)
            for img_path in image_matches:
                # 确保路径格式正确
                img_path = img_path.lstrip('/')
                full_url = f"{API_URL}/{img_path}"
                try:
                    st.image(full_url, caption="Agent 生成的图表")
                except Exception as e:
                    st.caption(f"📷 图片加载失败: {full_url}")
    
    # 保存助手消息
    st.session_state.messages.append({"role": "assistant", "content": assistant_message})
    st.rerun()

# ============================================================
# 聊天输入
# ============================================================

if prompt := st.chat_input("输入你的问题..."):
    # 添加用户消息到历史
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 显示用户消息
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 调用 Agent API
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            try:
                response = requests.post(
                    f"{API_URL}/agent/invoke",
                    json={
                        "message": prompt,
                        "thread_id": st.session_state.thread_id
                    },
                    timeout=120  # 2分钟超时（考虑到 Render 冷启动）
                )
                
                if response.status_code == 200:
                    result = response.json()
                    assistant_message = result.get("output", "抱歉，我没有得到有效的回复。")
                else:
                    assistant_message = f"❌ 请求失败: HTTP {response.status_code}\n{response.text}"
                    
            except requests.exceptions.Timeout:
                assistant_message = "⏱️ 请求超时。如果服务刚启动，可能需要等待 30-60 秒，请重试。"
            except requests.exceptions.ConnectionError:
                assistant_message = "🔌 无法连接到后端服务，请检查 API 地址是否正确。"
            except Exception as e:
                assistant_message = f"❌ 发生错误: {str(e)}"
        
        # 显示回复
        st.markdown(assistant_message)
        
        # 检查回复中是否包含图片路径（支持多种格式）
        if "images/" in assistant_message or "/images/" in assistant_message:
            import re
            # 匹配 /images/xxx.png 或 images/xxx.png
            image_matches = re.findall(r'/?images/[^\s\)\]]+\.png', assistant_message)
            for img_path in image_matches:
                # 确保路径格式正确
                img_path = img_path.lstrip('/')
                full_url = f"{API_URL}/{img_path}"
                try:
                    st.image(full_url, caption="Agent 生成的图表")
                except Exception:
                    st.caption(f"📷 图片加载失败: {full_url}")
    
    # 保存助手消息到历史
    st.session_state.messages.append({"role": "assistant", "content": assistant_message})

# ============================================================
# 页脚
# ============================================================

st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888; font-size: 0.9rem;">
        Data Agent v1.0 | 
        <a href="https://data-agent-v1.onrender.com/docs" target="_blank">API 文档</a> | 
        <a href="https://github.com/zhaojacob/data_agent_v1" target="_blank">GitHub</a>
    </div>
    """,
    unsafe_allow_html=True
)
