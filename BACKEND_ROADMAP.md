# Data Agent 后端开发路线图

> 最后更新：2026-01-13  
> 状态：✅ 核心功能完成，持续优化中

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术架构](#2-技术架构)
3. [当前进展](#3-当前进展)
4. [核心模块](#4-核心模块)
5. [API 接口](#5-api-接口)
6. [安全机制](#6-安全机制)
7. [待办事项](#7-待办事项)
8. [更新日志](#8-更新日志)

---

## 1. 项目概述

### 1.1 项目定位

Data Agent 后端是一个基于 LangGraph 的智能数据分析引擎，为前端提供：
- 自然语言到 SQL 的转换与执行
- Python 代码的安全执行（E2B 沙盒）
- 数据可视化图表生成
- 网络搜索能力

### 1.2 技术栈

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| Agent 框架 | LangGraph | 状态机式 Agent 编排 |
| LLM | DeepSeek | 中文优化，性价比高 |
| Web 框架 | FastAPI | 异步、高性能 |
| 数据库 | Supabase PostgreSQL | 云端托管，免运维 |
| 代码沙盒 | E2B | 云端隔离执行环境 |
| 搜索引擎 | Tavily | AI 优化的搜索 API |
| 部署平台 | Render | Docker 部署，自动扩缩 |

---

## 2. 技术架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户请求                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI + Chainlit (app.py)                                │
│  ├── /              Chainlit 聊天界面                        │
│  ├── /api/agent/invoke    同步调用                          │
│  ├── /api/agent/stream    流式调用 (SSE)                    │
│  └── /api/trigger-report  Webhook 接口                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  LangGraph Agent (graph.py)                                 │
│  ├── 状态管理 (messages, thread_id)                         │
│  ├── 工具路由 (根据用户意图选择工具)                          │
│  └── 响应生成 (流式/同步)                                    │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   sql_inter     │ │  python_inter   │ │   fig_inter     │
│   extract_data  │ │  (E2B 沙盒)     │ │  (E2B 沙盒)     │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│    Supabase     │ │    E2B Cloud    │ │   /images/      │
│   PostgreSQL    │ │    Sandbox      │ │   本地存储       │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 2.2 数据流

```
用户消息 → LangGraph Agent → 工具选择 → 工具执行 → 结果整合 → 响应生成
                ↑                                        │
                └────────── 多轮对话记忆 ←───────────────┘
```

---

## 3. 当前进展

### 3.1 已完成 ✅

| 模块 | 状态 | 文件 | 说明 |
|------|------|------|------|
| LangGraph Agent | ✅ | `graph.py` | 核心 Agent 逻辑 |
| SQL 查询工具 | ✅ | `graph.py` | `sql_inter`, `extract_data` |
| Python 执行工具 | ✅ | `graph.py` | `python_inter` (E2B) |
| 绘图工具 | ✅ | `graph.py` | `fig_inter` (E2B) |
| 网络搜索工具 | ✅ | `graph.py` | Tavily 集成 |
| SQL 安全验证 | ✅ | `graph.py` | `validate_sql()` |
| FastAPI 服务 | ✅ | `server.py` | 纯 API 模式 |
| FastAPI+Chainlit | ✅ | `app.py` | 挂载模式 |
| Supabase 集成 | ✅ | `.env` | 云端 PostgreSQL |
| E2B 沙盒集成 | ✅ | `graph.py` | 代码隔离执行 |
| Render 部署 | ✅ | `Dockerfile` | 容器化部署 |

### 3.2 待完成 ⏳

| 模块 | 状态 | 优先级 | 说明 |
|------|------|--------|------|
| 会话记忆持久化 | ⏳ | P1 | LangGraph PostgresSaver |
| 图片云存储 | ⏳ | P1 | Supabase Storage |
| 用户认证 | ⏳ | P2 | Supabase Auth |
| 使用额度限制 | ⏳ | P2 | API 调用计数 |
| 异步任务队列 | ⏳ | P3 | 长任务支持 |

---

## 4. 核心模块

### 4.1 LangGraph Agent (`graph.py`)

**功能**：编排 LLM 与工具的交互流程

**工具列表**：
| 工具 | 功能 | 安全措施 |
|------|------|----------|
| `sql_inter` | 执行 SQL 查询 | `validate_sql()` 验证 |
| `extract_data` | 提取数据到 DataFrame | `validate_sql()` 验证 |
| `python_inter` | 执行 Python 代码 | E2B 沙盒隔离 |
| `fig_inter` | 生成可视化图表 | E2B 沙盒隔离 |
| `search_tool` | 网络搜索 | Tavily API |

**系统提示词要点**：
- 所有业务数据在 `business_data` schema
- 仅允许 SELECT 查询
- 绘图必须创建 `fig` 对象
- 禁止危险操作（系统命令、网络请求等）

### 4.2 FastAPI 服务 (`app.py`)

**架构**：FastAPI 作为底座，Chainlit 挂载

**路由**：
```python
/                    # Chainlit 聊天界面
/api/docs            # Swagger 文档
/api/health          # 健康检查
/api/agent/invoke    # 同步调用
/api/agent/stream    # 流式调用 (SSE)
/api/trigger-report  # Webhook 示例
/images/{filename}   # 静态图片
```

### 4.3 Chainlit 前端 (`chainlit_app.py`)

**功能**：
- 会话初始化 (`on_chat_start`)
- 消息处理 (`on_message`)
- 流式响应 (`stream_agent_response`)
- 图片渲染 (`handle_images`)

---

## 5. API 接口

### 5.1 同步调用

```bash
POST /api/agent/invoke
Content-Type: application/json

{
  "message": "查询 business_data.students_scores 表的所有数据",
  "thread_id": "optional-session-id"
}
```

**响应**：
```json
{
  "output": "查询结果...",
  "thread_id": "session-id"
}
```

### 5.2 流式调用

```bash
POST /api/agent/stream
Content-Type: application/json

{
  "message": "分析数据并绘制图表",
  "thread_id": "optional-session-id"
}
```

**响应**：Server-Sent Events (SSE)
```
data: {"agent": {"messages": [...]}}
data: {"tools": {"messages": [...]}}
data: [DONE]
```

### 5.3 Webhook 示例

```bash
POST /api/trigger-report
Content-Type: application/json

{
  "stock": "茅台",
  "thread_id": "optional-session-id"
}
```

---

## 6. 安全机制

### 6.1 SQL 安全

**双重防护**：
1. **代码层**：`validate_sql()` 函数
   - 仅允许 SELECT
   - 禁止危险关键字 (DROP, DELETE, INSERT...)
   - 禁止访问系统表 (pg_shadow, pg_roles...)

2. **数据库层**：只读用户 `agent_reader`
   - 仅有 `business_data` schema 的 SELECT 权限

### 6.2 代码执行安全

**E2B 沙盒**：
- 云端隔离环境，无法访问主机
- 内置超时限制
- 无法执行系统命令
- 无法访问网络（除非显式配置）

### 6.3 系统提示词限制

```
禁止：
- os.system(), subprocess, popen
- pip install, conda install
- open() 写入文件
- requests, urllib, socket
- eval(), exec(), compile()
- __import__, getattr, setattr
```

---

## 7. 待办事项

### 7.1 P1 - 重要

- [ ] **会话记忆持久化**
  - 配置 LangGraph PostgresSaver
  - 连接 Supabase `agent_memory` schema
  
- [ ] **图片云存储**
  - 迁移到 Supabase Storage
  - 避免 Render 重启丢失图片

### 7.2 P2 - 后续

- [ ] **用户认证**
  - Supabase Auth 集成
  - JWT 验证中间件

- [ ] **使用额度**
  - API 调用计数
  - 用户配额管理

### 7.3 P3 - 远期

- [ ] **异步任务队列**
  - 支持 5-10 分钟的长任务
  - 任务状态持久化

- [ ] **多模型支持**
  - OpenAI GPT-4
  - Claude
  - 本地模型

---

## 8. 已知问题

### 8.1 E2B 沙盒偶发连接失败

**现象**：从 E2B 沙盒下载图片时偶尔报错：
```
[WinError 10054] 远程主机强迫关闭了一个现有的连接
```

**原因**：
- E2B 沙盒有生命周期限制（默认几分钟）
- 网络抖动或沙盒超时导致连接断开

**影响**：Agent 会自动重试，通常第二次能成功

**后续优化**：
- [ ] 在 `fig_inter` 中添加重试逻辑
- [ ] 考虑复用沙盒实例减少创建开销

### 8.2 图片存储流程说明

绘图功能的安全架构：
```
用户代码 → E2B 云端沙盒执行（隔离环境）
    ↓
图片生成在沙盒内 → /tmp/fig_xxx.png
    ↓
服务器通过 E2B API 下载 → sbx.files.read()
    ↓
保存到服务器 images 目录 → /images/fig_xxx.png
    ↓
前端通过 HTTP 访问图片
```

**安全性**：用户代码无法直接写入服务器文件系统，只能通过受控的 `fig_inter` 工具生成图片。

---

## 9. 更新日志

### 2026-01-13

**[完成] FastAPI + Chainlit 整合**
- 创建 `app.py` - 挂载模式入口
- 修复 `chainlit_app.py` 流式响应问题
- 支持 LangGraph 返回的 `model` key（不只是 `agent`/`tools`）
- 保留 API 接口供外部调用

**[文档] 新增已知问题章节**
- 记录 E2B 沙盒偶发连接失败问题
- 说明图片存储的安全架构

### 2026-01-04

**[完成] E2B 沙盒集成**
- `python_inter` 改用 E2B 执行
- `fig_inter` 改用 E2B 执行 + 图片下载
- 详见 `DEPLOYMENT_LOG.md`

**[完成] SQL 安全验证**
- 新增 `validate_sql()` 函数
- 双重防护机制
- 详见 `SECURITY_GUIDE.md`

**[完成] Supabase 云数据库**
- 迁移到 Supabase PostgreSQL
- 配置只读用户 `agent_reader`
- 创建 `business_data` schema

---

## 附录

### A. 相关文档

- `DEPLOYMENT_LOG.md` - 部署日志
- `SECURITY_GUIDE.md` - 安全加固指南
- `FRONTEND_ROADMAP.md` - 前端开发路线图

### B. 环境变量

```env
# LLM
DEEPSEEK_API_KEY=your_key

# 数据库
PG_HOST=aws-1-ap-northeast-2.pooler.supabase.com
PG_PORT=6543
PG_USER=agent_reader.xxx
PG_PASSWORD=your_password
PG_DBNAME=postgres

# E2B 沙盒
E2B_API_KEY=your_key

# 搜索
TAVILY_API_KEY=your_key

# 图片目录
IMAGES_DIR=/app/images
```

### C. 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app:app --reload --port 8000

# 访问
# 聊天界面: http://localhost:8000/
# API 文档: http://localhost:8000/api/docs
```
