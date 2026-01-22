# Data Agent

> 基于 LangGraph 的智能数据分析助手  
> 目标：金融领域的 Deep Research

**Demo**: https://data-agent-v1.onrender.com

---

## 🚀 功能

| 功能 | 说明 | 工具 |
|------|------|------|
| 📊 数据库查询 | SQL 查询 PostgreSQL/Supabase | `sql_inter` |
| 🔬 数据分析 | SQL + Python 统计分析 | `analyze_data` ⭐ |
| 📈 数据可视化 | SQL + matplotlib/seaborn 绑图 | `plot_data` ⭐ |
| 🐍 Python 执行 | E2B 云端沙盒安全执行 | `python_inter` |
| 🎨 纯绑图 | matplotlib/seaborn 图表 | `fig_inter` |
| 🌐 网络搜索 | Tavily 搜索引擎 | `search_tool` |

---

## 📁 项目结构

```
data_agent/
├── app.py              # 入口: FastAPI + Chainlit (Render 部署)
├── graph.py            # 核心: LangGraph Agent + 工具定义
├── config.py           # 配置: 自动检测环境，切换数据库
├── chainlit_app.py     # Chainlit 前端 (流式输出)
├── server.py           # 备用: 纯 FastAPI 服务
├── requirements.txt    # Python 依赖
├── Dockerfile          # Docker 部署配置
├── langgraph.json      # LangGraph 配置
├── .env                # 环境变量 (本地)
│
├── database/           # 数据库相关
│   ├── schema/         # SQL 建表脚本
│   └── scripts/        # 数据导入脚本
│
├── tools/              # 扩展工具 (待集成)
│   ├── akshare_tool.py # AKShare 金融数据
│   └── browser_tool.py # Playwright 浏览器自动化
│
└── docs/               # 文档 (已精简)
    ├── DEVELOPMENT.md  # 开发指南
    └── DEPLOYMENT.md   # 部署指南
```

---

## ⚡ 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd F:\anaconda_projects\data_agent

# 激活 conda 环境
conda activate lg

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入以下配置：

```env
# LLM
DEEPSEEK_API_KEY=sk-xxx

# 搜索
TAVILY_API_KEY=tvly-xxx

# 代码沙盒
E2B_API_KEY=e2b_xxx

# 本地数据库
LOCAL_PG_HOST=localhost
LOCAL_PG_PORT=5432
LOCAL_PG_USER=postgres
LOCAL_PG_PASSWORD=your_password
LOCAL_PG_DBNAME=data_agent
```

### 3. 启动服务

```bash
# 方式1: FastAPI + Chainlit (推荐)
uvicorn app:app --reload --port 8000

# 方式2: 仅 Chainlit
chainlit run chainlit_app.py -w

# 访问
# 聊天界面: http://localhost:8000/
# API 文档: http://localhost:8000/api/docs
```

---

## 🔧 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│  FastAPI + Chainlit (app.py)                                │
│    ├── /              聊天界面                              │
│    ├── /api/agent/invoke    同步 API                        │
│    └── /api/agent/stream    流式 API (SSE)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  LangGraph Agent (graph.py)                                 │
│    ├── 模型: DeepSeek (deepseek-chat)                       │
│    ├── 记忆: MemorySaver (会话内)                           │
│    └── 工具: sql_inter, analyze_data, plot_data, ...        │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│   PostgreSQL   │  │   E2B 沙盒     │  │    Tavily      │
│  (Supabase)    │  │  (代码执行)    │  │   (搜索)       │
└────────────────┘  └────────────────┘  └────────────────┘
```

---

## 🔒 安全机制

| 层面 | 措施 |
|------|------|
| **SQL** | 仅允许 SELECT，禁止 DROP/DELETE/INSERT |
| **代码执行** | E2B 云端沙盒，完全隔离 |
| **系统提示** | 禁止 os.system、subprocess、网络请求等 |

---

## 📊 当前状态 vs 目标

| 维度 | 当前 | 目标 |
|------|------|------|
| Agent 架构 | 单一 ReAct | Multi-Agent 系统 |
| 数据源 | Supabase 测试数据 | Wind/Bloomberg/AKShare |
| 输出格式 | 对话回复 | 结构化研究报告 |
| 记忆 | 会话内 | 持久化 + 知识图谱 |

---

## 📚 文档

- [开发指南](docs/DEVELOPMENT.md) - 本地开发、工具添加、架构说明
- [部署指南](docs/DEPLOYMENT.md) - Render/Docker 部署、环境变量配置

---

## 📄 License

MIT
