# Data Agent 前端开发路线图

> 最后更新：2026-01-13  
> 状态：规划中

---

## 目录

1. [项目背景与目标](#1-项目背景与目标)
2. [当前进展](#2-当前进展)
3. [技术方案分析](#3-技术方案分析)
4. [推荐方案](#4-推荐方案)
5. [实施计划](#5-实施计划)
6. [待办事项](#6-待办事项)
7. [更新日志](#7-更新日志)

---

## 1. 项目背景与目标

### 1.1 项目定位

Data Agent 是一个类似 Google Deep Research 的智能数据分析平台，核心能力包括：

- 连接私有化金融数据库（Supabase PostgreSQL）
- 调用数据 API 进行实时数据获取
- 使用 E2B 沙盒安全执行 Python 代码
- 生成数据可视化图表
- 网络搜索获取最新信息

### 1.2 目标用户

资本市场从业者（分析师、研究员、投资经理），需要：
- 专业的金融研报生成界面
- 交互式数据可视化（K线图、统计图表）
- 长时间任务的进度追踪
- 数据溯源和结论验证

### 1.3 核心挑战

| 挑战 | 说明 |
|------|------|
| 长任务处理 | Deep Research 类任务可能需要 5-10 分钟 |
| 流式输出 | 用户需要实时看到 Agent 的思考过程 |
| 图表渲染 | 需要展示 Agent 生成的可视化图片 |
| 会话管理 | 支持多轮对话和历史记录 |

---

## 2. 当前进展

### 2.1 已完成 ✅

| 模块 | 状态 | 说明 |
|------|------|------|
| LangGraph Agent | ✅ 完成 | `graph.py` - SQL查询、Python执行、绘图、搜索 |
| FastAPI 后端 | ✅ 完成 | `server.py` - /agent/invoke, /agent/stream |
| E2B 沙盒集成 | ✅ 完成 | 代码在云端隔离环境执行 |
| SQL 安全验证 | ✅ 完成 | 仅允许 SELECT，禁止危险操作 |
| Supabase 数据库 | ✅ 完成 | 云端 PostgreSQL，business_data schema |
| Render 部署 | ✅ 完成 | https://data-agent-v1.onrender.com |
| Streamlit 前端 | ✅ 完成 | `streamlit_app.py` - 本地可用，未部署 |

### 2.2 待完成 ⏳

| 模块 | 状态 | 优先级 |
|------|------|--------|
| 前端框架选型 | ⏳ 规划中 | P0 |
| 前端部署 | ⏳ 待开始 | P0 |
| 图片持久化存储 | ⏳ 待开始 | P1 |
| 会话记忆持久化 | ⏳ 待开始 | P1 |
| 用户认证 | ⏳ 待开始 | P2 |

---

## 3. 技术方案分析

### 3.1 Vercel 超时问题

**问题本质**：Vercel Serverless Function 有执行时间限制

| 套餐 | 超时限制 |
|------|----------|
| Hobby (免费) | 10 秒 |
| Pro | 60 秒 |
| Enterprise | 900 秒 |

**影响**：如果前端通过 Vercel API Route 转发请求到 Render 后端，长任务会被 Vercel 掐断。

**解决方案**：

```
❌ 会超时的路径：
浏览器 → Vercel API Route → Render 后端
         (Vercel 10秒后断开)

✅ 不会超时的路径：
浏览器 → 直接连接 Render 后端
         (浏览器与 Render 直连，无中间层限制)
```

### 3.2 框架对比

| 框架 | 开发成本 | UI 定制性 | 部署复杂度 | 适用场景 |
|------|----------|-----------|------------|----------|
| **Chainlit** | 低 (1-2天) | 中等 | 低 | 快速验证、内部工具 |
| **Streamlit** | 最低 | 低 | 低 | 数据科学演示 |
| **Next.js** | 高 (1-2周) | 很高 | 中等 | 商业级产品 |
| **Gradio** | 低 | 低 | 低 | ML 模型演示 |

### 3.3 Chainlit 方案详解

**优势**：
- 原生支持 LangGraph/LangChain 流式输出
- 内置聊天 UI，开箱即用
- 支持图片、文件展示
- 可部署到 Render（与后端同平台）

**劣势**：
- UI 定制能力有限
- 难以实现复杂布局（如左右分栏）
- 不适合需要交互式图表的场景

**架构选择**：

#### 方案 A：两个独立服务（微服务模式）

```
┌─────────────────┐     ┌─────────────────┐
│  Render 服务 1  │     │  Render 服务 2  │
│  Chainlit UI    │────→│  FastAPI Agent  │
│  ($7/月)        │HTTP │  ($7/月)        │
└─────────────────┘     └─────────────────┘
```

适用：大型团队、需要独立扩展、前后端分离维护

#### 方案 B：挂载模式（推荐 ✅）

```
┌─────────────────────────────────────┐
│         单个 Render 服务 ($7/月)     │
│  ┌─────────────────────────────┐   │
│  │  Chainlit (入口)             │   │
│  │    ↓ 内部调用（零延迟）       │   │
│  │  LangGraph Agent (graph.py) │   │
│  └─────────────────────────────┘   │
│                                     │
│  可选：FastAPI 挂载到 /api 路径     │
│  （供外部系统调用）                  │
└─────────────────────────────────────┘
```

适用：个人开发者、小团队、验证阶段

**挂载模式优势**：

| 方面 | 两个服务 | 挂载模式 |
|------|----------|----------|
| 成本 | $14/月 | $7/月 |
| 延迟 | HTTP 网络请求 | 内部调用，零延迟 |
| 冷启动 | 两个服务都要唤醒 | 只唤醒一个 |
| 维护 | 两套部署配置 | 一套搞定 |

**挂载模式代码结构**：

```python
# chainlit_app.py - 直接调用 Agent，无需 HTTP
from graph import agent
import chainlit as cl

@cl.on_message
async def main(message: cl.Message):
    # 直接调用 LangGraph Agent（内部调用，零延迟）
    result = agent.invoke({"messages": [("user", message.content)]})
    await cl.Message(content=result["messages"][-1].content).send()
```

```python
# 可选：如果需要同时暴露 API 给外部系统
from fastapi import FastAPI
from chainlit.utils import mount_chainlit

app = FastAPI()

@app.get("/api/health")
def health():
    return {"status": "ok"}

# Chainlit 挂载到根路径
mount_chainlit(app=app, target="chainlit_app.py", path="/")
```

### 3.4 Next.js 方案详解

**优势**：
- 完全自定义 UI（shadcn/ui 组件库）
- 支持复杂布局（左右分栏、多面板）
- 可集成 TradingView、Recharts 等专业图表库
- 支持 SSR/SSG，SEO 友好
- Vercel 部署体验极佳

**劣势**：
- 开发成本高
- 需要自己实现流式输出解析
- 需要处理 Vercel 超时问题

**架构**：
```
用户浏览器
    │
    ├── 静态资源 ──→ Vercel (Next.js)
    │
    └── API 请求 ──→ Render (FastAPI)  ← 直连，绕过 Vercel
                          │
                          ▼
                     Supabase
```

### 3.5 长任务处理模式

对于 5-10 分钟的 Deep Research 任务，推荐**异步任务队列模式**：

```
1. 提交任务
   POST /api/research {"query": "分析茅台"}
   → 返回 {"task_id": "job_123", "status": "started"}

2. 后台执行
   Render 后端在后台运行 LangGraph
   每一步状态写入 Supabase

3. 前端轮询/订阅
   方案A: 每 3 秒 GET /api/jobs/job_123
   方案B: Supabase Realtime 订阅状态变化

4. 用户体验
   - 可以关闭页面，回来继续看进度
   - 网络抖动不会导致任务丢失
```

---

## 4. 推荐方案

### 4.1 分阶段策略

```
阶段一 (现在)          阶段二 (验证后)
┌─────────────┐       ┌─────────────┐
│  Chainlit   │  ──→  │  Next.js    │
│  快速验证   │       │  产品化     │
└─────────────┘       └─────────────┘
   1-2 天                1-2 周
```

### 4.2 阶段一：Chainlit 快速上线（挂载模式）

**目标**：验证核心流程，快速获得用户反馈

**采用方案**：挂载模式（单服务部署）

**任务清单**：
- [ ] 创建 `chainlit_app.py`（直接调用 `graph.agent`）
- [ ] 配置流式输出（使用 `agent.stream()`）
- [ ] 处理图片显示（从 E2B 沙盒下载）
- [ ] 修改 Dockerfile 启动 Chainlit
- [ ] 部署到 Render（复用现有服务或新建）
- [ ] 可选：挂载 FastAPI 到 `/api` 路径（供外部调用）

**文件结构**：
```
data_agent/
├── chainlit_app.py    ← 新增：Chainlit 入口
├── graph.py           ← 现有：LangGraph Agent
├── server.py          ← 现有：FastAPI（可选保留）
├── Dockerfile         ← 修改：启动 Chainlit
└── requirements.txt   ← 添加：chainlit 依赖
```

**预期成果**：
- 可公开访问的聊天界面
- 支持 SQL 查询、代码执行、绘图
- 流式输出 Agent 思考过程
- 单服务部署，成本 $7/月

### 4.3 阶段二：Next.js 产品化（可选）

**触发条件**：当需要以下功能时启动

- [ ] 左右分栏布局（思考过程 + 研报预览）
- [ ] 交互式 K 线图（TradingView Widget）
- [ ] PDF 导出功能
- [ ] 数据溯源高亮
- [ ] 用户认证和使用额度

**技术栈**：
- Next.js 14 (App Router)
- shadcn/ui 组件库
- Recharts / TradingView
- Supabase Auth
- Vercel 部署

---

## 5. 实施计划

### 5.1 阶段一时间线

| 日期 | 任务 | 产出 |
|------|------|------|
| Day 1 | 创建 Chainlit 应用 | `chainlit_app.py` |
| Day 1 | 本地测试流式输出 | 验证通过 |
| Day 2 | 修改 Dockerfile | 支持 Chainlit 启动 |
| Day 2 | 部署到 Render | 公开访问地址 |

### 5.2 基础设施优化

| 任务 | 优先级 | 说明 |
|------|--------|------|
| 解决 Render 冷启动 | P1 | 升级付费套餐 或 UptimeRobot 定时 ping |
| 图片存储迁移 | P1 | 从本地文件改为 Supabase Storage |
| 会话记忆持久化 | P1 | 配置 LangGraph PostgresSaver |

---

## 6. 待办事项

### 6.1 P0 - 必须完成

- [ ] **前端框架确认**：Chainlit vs Next.js
- [ ] **Chainlit 应用开发**：创建 `chainlit_app.py`
- [ ] **部署配置**：修改 Dockerfile 支持 Chainlit
- [ ] **Render 部署**：前端上线

### 6.2 P1 - 重要

- [ ] **图片存储**：迁移到 Supabase Storage，避免 Render 重启丢失
- [ ] **会话持久化**：配置 LangGraph checkpointer
- [ ] **冷启动优化**：UptimeRobot 或升级 Render 套餐

### 6.3 P2 - 后续

- [ ] **用户认证**：Supabase Auth 集成
- [ ] **使用额度**：限制 API 调用次数
- [ ] **Next.js 重构**：如需复杂 UI

### 6.4 P3 - 远期

- [ ] **异步任务队列**：支持超长任务
- [ ] **PDF 导出**：研报生成
- [ ] **交互式图表**：TradingView 集成

---

## 7. 更新日志

### 2026-01-13

**[新增] 创建前端开发路线图**
- 分析 Chainlit vs Next.js 方案
- 制定分阶段实施策略
- 整理待办事项清单
- 记录 Vercel 超时问题及解决方案

**[优化] 采纳 Gemini 挂载模式建议**
- 对比两个服务 vs 挂载模式的优劣
- 推荐单服务部署方案（$7/月 vs $14/月）
- 更新 Chainlit 架构图和代码示例
- Chainlit 直接调用 `graph.agent`，无需 HTTP 中转

---

## 附录

### A. 相关文档

- `DEPLOYMENT_LOG.md` - 后端部署日志
- `SECURITY_GUIDE.md` - 安全加固指南
- `server.py` - FastAPI 后端代码
- `graph.py` - LangGraph Agent 代码

### B. 参考资源

- [Chainlit 官方文档](https://docs.chainlit.io/)
- [Next.js 官方文档](https://nextjs.org/docs)
- [Render 部署指南](https://render.com/docs)
- [Supabase Storage](https://supabase.com/docs/guides/storage)
- [E2B 沙盒文档](https://e2b.dev/docs)
