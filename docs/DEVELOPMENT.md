# Data Agent 开发指南

> 本地开发、工具添加、架构说明

---

## 目录

1. [本地开发](#1-本地开发)
2. [核心模块](#2-核心模块)
3. [工具开发](#3-工具开发)
4. [数据库配置](#4-数据库配置)
5. [API 接口](#5-api-接口)
6. [学习资源](#6-学习资源)

---

## 1. 本地开发

### 1.1 环境要求

- Python 3.10+
- PostgreSQL 15+ (本地) 或 Supabase 账户
- Conda 环境 (推荐 `lg`)

### 1.2 依赖安装

```bash
conda activate lg
pip install -r requirements.txt
```

### 1.3 环境变量

本地开发使用 `.env` 文件：

```env
# === LLM ===
DEEPSEEK_API_KEY=sk-xxx

# === 搜索 ===
TAVILY_API_KEY=tvly-xxx

# === 代码沙盒 ===
E2B_API_KEY=e2b_xxx

# === 本地数据库 ===
LOCAL_PG_HOST=localhost
LOCAL_PG_PORT=5432
LOCAL_PG_USER=postgres
LOCAL_PG_PASSWORD=your_password
LOCAL_PG_DBNAME=data_agent

# === 云数据库 (生产环境自动使用) ===
SUPABASE_HOST=aws-xxx.supabase.com
SUPABASE_PORT=6543
SUPABASE_USER=xxx
SUPABASE_PASSWORD=xxx
SUPABASE_DBNAME=postgres

# === LangSmith (可选) ===
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_xxx
LANGCHAIN_PROJECT=data-agent
```

### 1.4 启动命令

```bash
# 开发模式 (热重载)
uvicorn app:app --reload --port 8000

# 仅 Chainlit
chainlit run chainlit_app.py -w
```

---

## 2. 核心模块

### 2.1 文件说明

| 文件 | 功能 |
|------|------|
| `graph.py` | **核心** - LangGraph Agent、工具定义、系统提示 |
| `app.py` | **入口** - FastAPI + Chainlit 挂载 |
| `config.py` | **配置** - 自动检测环境，切换数据库 |
| `chainlit_app.py` | Chainlit 前端，流式输出实现 |
| `server.py` | 备用 FastAPI 服务 (无 Chainlit) |

### 2.2 工具列表

| 工具 | 功能 | 推荐场景 |
|------|------|---------|
| `sql_inter` | SQL 查询 | 查看数据 |
| `analyze_data` ⭐ | SQL + Python 分析 | 数据统计 |
| `plot_data` ⭐ | SQL + 绑图 | 数据可视化 |
| `python_inter` | 纯 Python 执行 | 无数据库计算 |
| `fig_inter` | 纯绑图 | 用户提供数据 |
| `search_tool` | Tavily 搜索 | 网络信息 |

### 2.3 环境自动检测

`config.py` 自动检测运行环境：

```python
from config import get_db_config, is_production

if is_production():
    # 使用 Supabase (检测到 RENDER 环境变量)
else:
    # 使用 localhost
```

检测逻辑：
1. 检查 `RENDER` 环境变量 (Render 自动设置)
2. 检查 `ENVIRONMENT=production`
3. 检查 `SUPABASE_URL` 或 `USE_SUPABASE=true`

---

## 3. 工具开发

### 3.1 添加新工具

在 `graph.py` 中：

```python
from pydantic import BaseModel, Field
from langchain.tools import tool

# 1. 定义输入 Schema
class MyToolInput(BaseModel):
    param1: str = Field(description="参数1说明")
    param2: int = Field(default=10, description="参数2说明")

# 2. 定义工具函数
@tool(args_schema=MyToolInput)
def my_tool(param1: str, param2: int = 10) -> str:
    """工具描述（LLM 会看到）"""
    # 实现逻辑
    return f"结果: {param1}, {param2}"

# 3. 注册到工具列表
tools = [
    search_tool,
    sql_inter,
    analyze_data,
    plot_data,
    python_inter,
    fig_inter,
    my_tool,  # 新增
]
```

### 3.2 数据共享模式

主进程和 E2B 沙盒之间数据共享：

```python
# ✅ 推荐: analyze_data / plot_data
# 主进程查询 SQL → JSON 序列化 → 嵌入沙盒代码 → df 变量可用

# ❌ 不推荐: extract_data + python_inter
# 变量无法在沙盒间传递
```

### 3.3 SQL 安全验证

```python
from graph import validate_sql

is_valid, message = validate_sql("SELECT * FROM users")
# True, "验证通过"

is_valid, message = validate_sql("DROP TABLE users")
# False, "禁止使用 DROP 操作"
```

---

## 4. 数据库配置

### 4.1 本地 PostgreSQL

```bash
# 创建数据库
psql -U postgres -c "CREATE DATABASE data_agent"

# 创建 schema 和表
psql -U postgres -d data_agent -f database/schema/create_news_table.sql
```

### 4.2 Supabase 云数据库

1. 创建 Supabase 项目
2. 在 SQL Editor 执行 `database/schema/create_news_table.sql`
3. 配置环境变量

### 4.3 数据库表

业务数据在 `business_data` schema 中：

```sql
-- 查询新闻
SELECT * FROM business_data.news LIMIT 10;

-- 查询学生成绩
SELECT * FROM business_data.students_scores;
```

---

## 5. API 接口

### 5.1 端点列表

| 端点 | 方法 | 功能 |
|-----|------|------|
| `/` | GET | Chainlit 聊天界面 |
| `/api/health` | GET | 健康检查 |
| `/api/agent/invoke` | POST | 同步调用 Agent |
| `/api/agent/stream` | POST | 流式调用 (SSE) |
| `/images/{filename}` | GET | 图片静态服务 |

### 5.2 调用示例

```python
import requests

# 同步调用
response = requests.post(
    "http://localhost:8000/api/agent/invoke",
    json={"message": "查询 business_data.news 表"}
)
print(response.json()["output"])

# 流式调用
response = requests.post(
    "http://localhost:8000/api/agent/stream",
    json={"message": "分析新闻数据"},
    stream=True
)
for line in response.iter_lines():
    print(line.decode())
```

---

## 6. 学习资源

### 6.1 LangGraph

- **官方文档**: https://langchain-ai.github.io/langgraph/
- **概念指南**: https://langchain-ai.github.io/langgraph/concepts/
- **教程**: https://langchain-ai.github.io/langgraph/tutorials/

### 6.2 核心概念

| 概念 | 说明 |
|------|------|
| State | Agent 的"记忆"，在节点间传递 |
| Node | 执行具体逻辑的函数 |
| Edge | 节点之间的连接，决定流转方向 |
| Graph | 节点和边组成的工作流 |

### 6.3 当前使用的简化模式

```python
from langchain.agents import create_agent

agent = create_agent(
    model=model,           # DeepSeek
    tools=tools,           # 工具列表
    system_prompt=prompt,  # 系统提示
    checkpointer=memory    # 记忆存储
)
```

---

## 附录: 待办事项

- [ ] LangSmith 监控配置
- [ ] 图片云存储 (Supabase Storage)
- [ ] 会话记忆持久化 (PostgresSaver)
- [ ] Multi-Agent 架构升级
- [ ] 金融数据源集成 (AKShare)
