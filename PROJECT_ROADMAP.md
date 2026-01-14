# Data Agent 项目总路线图

> 最后更新：2026-01-14  
> 目标：金融领域的 Google Deep Research

---

## 📊 项目目标 vs 当前状态

### 🎯 最终目标
**金融领域的 Deep Research 级别研究报告生成系统**
- 类似 Google Deep Research：多步骤推理、深度信息检索、结构化报告输出
- 结合金融终端数据（Wind/Bloomberg 等）
- 访问金融数据库（财务数据、市场数据、新闻等）
- 生成专业级金融研究报告

### 📍 当前状态（2026-01-14 更新）
**基础数据分析 Agent + Web 前端（Demo 可用）**
- ✅ 单轮对话式交互
- ✅ 基础工具：SQL 查询、Python 执行（E2B 沙盒）、绘图、网络搜索
- ✅ 简单的工具调用链（查询 → 分析 → 可视化）
- ✅ **FastAPI + Chainlit 前端**（已部署到 Render）
- ✅ **真正的流式输出**（asyncio.Queue 实现边执行边输出）
- ✅ **Supabase 云数据库**（PostgreSQL）
- ✅ **E2B 代码沙盒**（安全隔离执行）
- ✅ **SQL 安全验证**（仅允许 SELECT）
- ⏳ LangSmith 监控（待配置环境变量）
- ⏳ 会话记忆持久化（待实现）
- ⏳ 图片云存储（待迁移到 Supabase Storage）
- ❌ 缺乏多步骤规划能力
- ❌ 缺乏深度研究流程
- ❌ 缺乏结构化报告生成
- ❌ 缺乏金融专业数据源

### 🌐 访问地址
- **Demo**: https://data-agent-v1.onrender.com
- **API 文档**: https://data-agent-v1.onrender.com/api/docs

---

## 🔍 核心差距分析

### 1️⃣ **架构层面**（最关键）

| 维度 | Deep Research | 当前项目 | 差距 |
|------|--------------|---------|------|
| **Agent 架构** | Multi-Agent 系统（规划器、研究员、分析师、写作者） | 单一 ReAct Agent | ⭐⭐⭐⭐⭐ |
| **推理模式** | 分层规划 + 反思循环 | 简单 ReAct（观察-思考-行动） | ⭐⭐⭐⭐⭐ |
| **记忆系统** | 长期记忆 + 工作记忆 + 知识图谱 | 简单对话历史 | ⭐⭐⭐⭐ |
| **输出格式** | 结构化报告（章节、引用、图表） | 单轮对话回复 | ⭐⭐⭐⭐⭐ |

### 2️⃣ **数据层面**

| 维度 | 理想状态 | 当前项目 | 差距 |
|------|---------|---------|------|
| **金融数据** | Wind/Bloomberg/财汇/东方财富 | 仅有 Supabase 测试数据 | ⭐⭐⭐⭐⭐ |
| **新闻数据** | 实时金融新闻爬虫 + 历史库 | Tavily 通用搜索 | ⭐⭐⭐⭐ |
| **研报数据** | 券商研报库 | 无 | ⭐⭐⭐⭐⭐ |
| **另类数据** | 舆情、ESG、供应链等 | 无 | ⭐⭐⭐⭐ |

### 3️⃣ **功能层面**

| 功能 | Deep Research | 当前项目 | 差距 |
|------|--------------|---------|------|
| **任务分解** | 自动将研究问题拆解为子任务 | 无 | ⭐⭐⭐⭐⭐ |
| **信息检索** | 多源并行检索 + 相关性排序 | 单一搜索工具 | ⭐⭐⭐⭐ |
| **数据分析** | 复杂统计建模 + 机器学习 | 简单 Python 计算 | ⭐⭐⭐ |
| **可视化** | 专业金融图表（K线、因子分析等） | 基础 matplotlib | ⭐⭐⭐ |
| **报告生成** | 多章节、引用、目录、摘要 | 无 | ⭐⭐⭐⭐⭐ |
| **人机协作** | 中间结果确认、方向调整 | 无 | ⭐⭐⭐⭐ |

---

## 🚀 下一步建设重点（优先级排序）

### 🔥 **P0 - 基础设施完善（本周）**

#### 1. ~~修复图片显示问题~~（✅ 已完成）
- Chainlit 流式响应已修复
- 支持 LangGraph 返回的 `model` key
- 使用 `asyncio.Queue` 实现真正的流式输出

#### 2. ~~Render 部署验证~~（✅ 已完成）
- Demo 已上线：https://data-agent-v1.onrender.com
- 聊天功能、图片生成、API 接口均可用

#### 3. **LangSmith 监控配置**（⏳ 待配置）
- 时间：10 分钟
- 方案：在 Render 环境变量中添加：
  ```
  LANGCHAIN_TRACING_V2=true
  LANGCHAIN_API_KEY=lsv2_pt_xxxxxxxx
  LANGCHAIN_PROJECT=data-agent
  ```
- 原因：追踪 Agent 执行链路、调试问题、分析性能
- 说明：LangGraph 内置追踪逻辑，只需配置环境变量即可启用

#### 4. **图片云存储迁移**
- 时间：2-3 小时
- 方案：迁移到 Supabase Storage
- 原因：Render 容器重启会丢失本地图片
- 实现：
  ```python
  # 修改 fig_inter，上传到 Supabase Storage
  from supabase import create_client
  supabase.storage.from_("images").upload(filename, file_content)
  # 返回公开 URL
  url = supabase.storage.from_("images").get_public_url(filename)
  ```

#### 5. **会话记忆持久化**
- 时间：2-3 小时
- 方案：LangGraph PostgresSaver + Supabase
- 原因：刷新页面后对话历史丢失
- 实现：
  ```python
  from langgraph.checkpoint.postgres import PostgresSaver
  checkpointer = PostgresSaver.from_conn_string(SUPABASE_URL)
  agent = create_agent(..., checkpointer=checkpointer)
  ```
- 注意：需要在 Supabase 创建 checkpointer 所需的表

#### 6. **冷启动优化**
- 时间：30 分钟
- 方案：UptimeRobot 每 5 分钟 ping `/api/health`
- 原因：Render 免费套餐 15 分钟无请求会休眠
- 替代方案：升级 Render 付费套餐（$7/月）

#### 7. **确定金融数据源方案**
- 时间：1-3 天调研
- 选项：
  - **免费方案**：AKShare（Python 库，免费但不稳定）、Tushare（需注册积分）
  - **付费方案**：Wind API（需本地终端）、东方财富 Choice（云端 API）
  - **自建方案**：整合你的 `financial-news-brief` 新闻爬虫项目
- **建议**：
  - 短期：用 AKShare 快速验证基础功能
  - 中期：整合 `financial-news-brief` 的新闻数据
  - 长期：考虑付费数据源（如需商业化）

#### 8. **设计数据库 Schema**
- 时间：1 天
- 内容：
  - 股票基本信息表（代码、名称、行业）
  - 财务数据表（资产负债表、利润表、现金流量表）
  - 市场数据表（日行情、分钟行情）
  - 新闻表（标题、内容、来源、时间）
  - 研报表（标题、作者、机构、摘要）

---

### 🔥 **P1 - 核心架构升级（1-2 周）**

#### 9. **升级为 Multi-Agent 架构**
这是最关键的一步，决定了项目能否达到 Deep Research 级别。

**推荐架构**：
```
┌─────────────────────────────────────────────────┐
│           Supervisor Agent (协调者)              │
│  - 任务分解                                      │
│  - 子任务分配                                    │
│  - 进度监控                                      │
└─────────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼
   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
   │ Planner│  │Researcher│ │Analyst │  │ Writer │
   │ 规划器 │  │ 研究员   │  │ 分析师 │  │ 写作者 │
   └────────┘  └────────┘  └────────┘  └────────┘
        │           │           │           │
        └───────────┴───────────┴───────────┘
                    │
            ┌───────┴───────┐
            ▼               ▼
        [工具层]        [数据层]
     - SQL查询        - PostgreSQL
     - Python执行     - 金融数据API
     - 网络搜索       - 向量数据库
     - 绘图工具       - 文件存储
```

**实现方式**：
- 使用 LangGraph 的 `StateGraph` + `Supervisor` 模式
- 参考你的 `deer-flow` 项目（如果它有类似架构）
- 时间：3-5 天

**建议的 Agent 分工**：
| Agent | 职责 | 工具 |
|-------|------|------|
| Planner | 分解研究任务、制定执行计划 | 无（纯推理） |
| Researcher | 信息检索、数据收集 | search_tool, sql_inter |
| Analyst | 数据分析、计算指标 | python_inter, extract_data |
| Writer | 整合信息、生成报告 | fig_inter（图表） |

#### 10. **实现结构化报告生成**
- 定义报告模板（Markdown/PDF）
- 章节管理：摘要、正文、图表、引用
- 时间：2-3 天

**报告模板示例**：
```markdown
# {公司名称} 投资价值分析报告

## 摘要
{一段话总结核心观点}

## 1. 公司概况
- 基本信息
- 主营业务
- 行业地位

## 2. 财务分析
- 盈利能力（ROE、净利率）
- 成长性（营收增速、利润增速）
- 估值水平（PE、PB）
{插入图表}

## 3. 行业分析
- 行业趋势
- 竞争格局

## 4. 风险提示
- 主要风险因素

## 5. 投资建议
{结论}

---
数据来源：{来源列表}
生成时间：{时间戳}
```

---

### 🔥 **P2 - 功能增强（2-4 周）**

#### 11. **添加金融专业工具**
- K线图绘制（mplfinance）
- 技术指标计算（TA-Lib）
- 财务指标计算（ROE、PE、PB 等）
- 时间：3-5 天

**推荐工具库**：
| 库 | 用途 | 安装 |
|----|------|------|
| mplfinance | K线图、成交量图 | `pip install mplfinance` |
| ta-lib | 技术指标（MACD、RSI、布林带） | 需要先安装 C 库 |
| akshare | 免费金融数据 | `pip install akshare` |
| tushare | 金融数据（需积分） | `pip install tushare` |

#### 12. ~~实现流式输出~~（✅ 已完成）
- ✅ Chainlit 流式输出已实现
- ✅ 使用 `asyncio.Queue` 实现真正的边执行边输出
- ✅ 显示 Agent 思考过程和工具执行结果

#### 13. **添加向量数据库（RAG）**
- 存储历史研报、新闻
- 语义检索相关内容
- 工具：Supabase Vector（推荐，与现有架构一致）或 Chroma
- 时间：3-5 天

**实现方案**：
```python
# Supabase Vector 示例
from supabase import create_client

# 存储文档
supabase.table("documents").insert({
    "content": "研报内容...",
    "embedding": embedding_vector,  # OpenAI/DeepSeek embedding
    "metadata": {"source": "券商研报", "date": "2026-01-14"}
}).execute()

# 语义检索
results = supabase.rpc("match_documents", {
    "query_embedding": query_vector,
    "match_count": 5
}).execute()
```

#### 14. **整合 financial-news-brief 项目**
- 你已有的新闻爬虫项目
- 将爬取的新闻存入 Supabase
- 为 Agent 添加新闻检索工具
- 时间：2-3 天

**整合方案**：
1. 新闻爬虫定时运行，存入 `business_data.news` 表
2. 添加 `search_news` 工具，支持关键词/时间范围检索
3. 结合向量数据库，支持语义检索

#### 15. **Context Engineering 优化**
这是决定产品质量的关键，参考 Karpathy 的建议。

**策略 1：工具返回结构化摘要**
```python
# 不要返回原始数据（可能很长）
def search_news(keyword):
    # 原始数据可能有 100 条
    raw_results = fetch_news(keyword)
    
    # 返回结构化摘要
    return {
        "total": len(raw_results),
        "top_5": [summarize(r) for r in raw_results[:5]],
        "sentiment": analyze_sentiment(raw_results),
        "hint": "如需详情，调用 get_news_detail(id)"
    }
```

**策略 2：分层上下文**
```
System Prompt（固定，约 1000 tokens）
    ↓
任务上下文（动态注入：研究主题、已完成步骤，约 500 tokens）
    ↓
工作记忆（最近 3 轮对话 + 当前工具结果，约 2000 tokens）
```

**策略 3：研究模板库**
为不同任务类型预设 Prompt 模板：
- 个股分析模板
- 行业对比模板
- 事件影响分析模板
- 财务健康度检查模板

**策略 4：两阶段检索**
```
第一阶段：快速检索（关键词匹配）
    → 返回候选列表（标题、摘要）
    
第二阶段：精准检索（用户确认后）
    → 获取完整内容
```

---

### 🔥 **P3 - 生产化（1-2 周）**

#### 16. **用户认证与权限**
- 多用户支持
- API Key 管理
- 使用限制
- 方案：Supabase Auth（与现有架构一致）
- 时间：3-5 天

**实现方案**：
```python
# Supabase Auth 集成
from supabase import create_client

# 用户注册/登录
auth_response = supabase.auth.sign_in_with_password({
    "email": "user@example.com",
    "password": "password"
})

# JWT 验证中间件
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

async def verify_token(token: str = Depends(HTTPBearer())):
    user = supabase.auth.get_user(token.credentials)
    if not user:
        raise HTTPException(status_code=401)
    return user
```

#### 17. **监控与日志**
- Agent 执行日志
- 成本追踪（API 调用：DeepSeek、E2B、Tavily）
- 错误告警
- 方案：LangSmith + Render 日志 + Supabase 存储
- 时间：2-3 天

**成本追踪表设计**：
```sql
CREATE TABLE usage_logs (
    id SERIAL PRIMARY KEY,
    user_id UUID,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    service VARCHAR(50),  -- 'deepseek', 'e2b', 'tavily'
    tokens_used INT,
    cost_usd DECIMAL(10, 6),
    request_id VARCHAR(100)
);
```

#### 18. **E2B 沙盒优化**
- 添加重试逻辑（解决偶发连接失败）
- 考虑复用沙盒实例减少创建开销
- 预装金融分析库（mplfinance、TA-Lib）
- 时间：1-2 天

**重试逻辑示例**：
```python
import tenacity

@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
    retry=tenacity.retry_if_exception_type(ConnectionError)
)
def download_from_sandbox(sbx, path):
    return sbx.files.read(path, format='bytes')
```

#### 19. **错误处理与用户体验**
- 友好的错误提示
- 任务超时处理
- 断点续传（长任务）
- 时间：2-3 天

**错误分类**：
| 错误类型 | 用户提示 | 处理方式 |
|----------|----------|----------|
| 数据库连接失败 | "数据库暂时不可用，请稍后重试" | 自动重试 3 次 |
| E2B 沙盒超时 | "代码执行超时，请简化计算" | 提示用户优化代码 |
| LLM API 限流 | "请求过于频繁，请稍后重试" | 指数退避重试 |
| 工具执行失败 | 显示具体错误 | 记录日志，通知开发者 |

---

## 💡 最小可行路径（MVP）更新

根据当前进展，调整 MVP 路径：

### 第一阶段（本周）：基础设施完善
1. ✅ 修复图片显示 / Chainlit 流式输出
2. ✅ 验证 Render 部署
3. 🔄 LangSmith 监控配置（10 分钟）
4. 🔄 图片云存储迁移（Supabase Storage）
5. 🔄 会话记忆持久化（PostgresSaver）
6. 🔄 冷启动优化（UptimeRobot）

**产出**：稳定可用的 Web 应用，支持多轮对话，可追踪调试

---

### 第二阶段（下周）：金融数据接入
7. 🔄 接入 AKShare（免费金融数据）
8. 🔄 设计金融数据库 Schema
9. 🔄 添加 3-5 个金融专业工具（K线图、财务指标）
10. 🔄 整合 financial-news-brief 新闻数据

**产出**：能查询真实金融数据、生成专业图表的 Agent

---

### 第三阶段（第 3-4 周）：架构升级
11. 🔄 升级为 Multi-Agent（Supervisor + 子 Agent）
12. 🔄 实现简单的报告生成（Markdown 格式）
13. 🔄 添加任务分解能力
14. 🔄 添加向量数据库（RAG）
15. 🔄 Context Engineering 优化

**产出**：能自动分解任务、多步骤研究、生成结构化报告的系统

---

## 🎯 当前最紧迫的任务（更新）

| 优先级 | 任务 | 状态 | 预计时间 |
|--------|------|------|----------|
| P0 | ~~Render 部署验证~~ | ✅ 已完成 | - |
| P0 | LangSmith 监控配置 | ⏳ 待配置 | 10 分钟 |
| P0 | 图片云存储迁移 | ⏳ 待开始 | 2-3 小时 |
| P0 | 会话记忆持久化 | ⏳ 待开始 | 2-3 小时 |
| P1 | 冷启动优化 | ⏳ 待开始 | 30 分钟 |
| P1 | 接入 AKShare | ⏳ 待开始 | 1 天 |
| P1 | 金融数据库 Schema | ⏳ 待开始 | 1 天 |

---

## 🧠 Context Engineering 深度建议

### 为什么 Context Engineering 如此重要？

Karpathy 指出：**"Context is the new hyperparameter"**。对于金融研究 Agent：
- 上下文质量直接决定报告质量
- 金融数据量大，必须精准筛选
- 多步骤任务需要保持上下文连贯

### 具体实施建议

#### 1. 工具返回优化
```python
# ❌ 不好的做法：返回原始数据
def get_stock_data(symbol):
    return df.to_json()  # 可能有 10000 行

# ✅ 好的做法：返回结构化摘要
def get_stock_data(symbol):
    return {
        "symbol": symbol,
        "latest_price": df['close'].iloc[-1],
        "change_pct": calculate_change(df),
        "summary": f"最近 30 天涨跌幅 {change}%",
        "data_range": f"{df.index[0]} ~ {df.index[-1]}",
        "hint": "如需详细数据，请调用 get_stock_detail(symbol, start, end)"
    }
```

#### 2. 动态 System Prompt
```python
def build_system_prompt(task_type: str, context: dict) -> str:
    base_prompt = "你是金融分析助手..."
    
    if task_type == "stock_analysis":
        return base_prompt + f"""
当前任务：分析 {context['symbol']}
已完成步骤：{context['completed_steps']}
待完成步骤：{context['pending_steps']}
关键发现：{context['key_findings']}
"""
    elif task_type == "industry_comparison":
        return base_prompt + "..."
```

#### 3. 记忆管理策略
```
短期记忆（当前会话）
├── 最近 3 轮对话
├── 当前任务状态
└── 工具执行结果摘要

长期记忆（跨会话）
├── 用户偏好（关注的股票、行业）
├── 历史研究报告索引
└── 常用查询模板
```

#### 4. 检索增强策略
```python
# 两阶段检索
async def research_topic(query: str):
    # 阶段 1：快速检索，返回候选
    candidates = await vector_search(query, top_k=20)
    summaries = [summarize(c) for c in candidates]
    
    # 让 LLM 选择最相关的
    selected = await llm.select_relevant(query, summaries)
    
    # 阶段 2：获取完整内容
    full_content = await fetch_full_content(selected)
    return full_content
```

---

## 🔬 技术深度建议

### 1. LangGraph 状态管理优化

当前使用简单的 `messages` 状态，建议扩展：

```python
from typing import TypedDict, List, Optional

class AgentState(TypedDict):
    messages: List[BaseMessage]
    
    # 任务状态
    task_type: Optional[str]  # "stock_analysis", "industry_comparison"
    task_plan: Optional[List[str]]  # 任务步骤列表
    current_step: int
    
    # 研究上下文
    research_topic: Optional[str]
    collected_data: dict  # 已收集的数据
    key_findings: List[str]  # 关键发现
    
    # 报告状态
    report_sections: dict  # 已完成的报告章节
```

### 2. 工具执行优化

```python
# 并行执行独立工具
import asyncio

async def parallel_research(queries: List[str]):
    tasks = [search_tool.ainvoke(q) for q in queries]
    results = await asyncio.gather(*tasks)
    return results
```

### 3. 错误恢复机制

```python
from langgraph.checkpoint.postgres import PostgresSaver

# 配置 checkpointer，支持断点续传
checkpointer = PostgresSaver.from_conn_string(SUPABASE_URL)

# 如果任务中断，可以从上次状态恢复
agent = create_agent(
    model=model,
    tools=tools,
    checkpointer=checkpointer
)

# 恢复执行
result = agent.invoke(
    {"messages": []},  # 空消息，从 checkpoint 恢复
    config={"configurable": {"thread_id": "interrupted_task_123"}}
)
```

---

## 📊 成本估算

### 当前成本（Demo 阶段）
| 服务 | 费用 | 说明 |
|------|------|------|
| Render | $7/月 | Starter 套餐 |
| Supabase | $0/月 | 免费套餐 |
| DeepSeek | ~$1-5/月 | 按 token 计费，非常便宜 |
| E2B | $0/月 | 免费额度 |
| Tavily | $0/月 | 免费额度 |
| **总计** | **~$10/月** | |

### 生产环境预估
| 服务 | 费用 | 说明 |
|------|------|------|
| Render | $25/月 | Pro 套餐（无冷启动） |
| Supabase | $25/月 | Pro 套餐（更多存储） |
| DeepSeek | ~$20-50/月 | 取决于用量 |
| E2B | ~$20/月 | 取决于执行时间 |
| Tavily | ~$10/月 | 取决于搜索量 |
| **总计** | **~$100-130/月** | |

---

## 📚 相关文档

- `FRONTEND_ROADMAP.md` - 前端开发路线图
- `BACKEND_ROADMAP.md` - 后端开发路线图
- `DEPLOYMENT_LOG.md` - 部署日志
- `SECURITY_GUIDE.md` - 安全加固指南
- `DEMO_SUMMARY_20260113.md` - Demo 阶段总结报告

---

## � 参考资源

### 技术文档
- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangSmith 追踪指南](https://docs.smith.langchain.com/)
- [Chainlit 官方文档](https://docs.chainlit.io/)
- [Supabase Vector 文档](https://supabase.com/docs/guides/ai)
- [E2B 沙盒文档](https://e2b.dev/docs)

### 金融数据
- [AKShare 文档](https://akshare.akfamily.xyz/)
- [Tushare 文档](https://tushare.pro/document/2)
- [mplfinance 文档](https://github.com/matplotlib/mplfinance)

### 架构参考
- [Google Deep Research 论文](https://arxiv.org/abs/2312.xxxxx)
- [LangGraph Multi-Agent 示例](https://github.com/langchain-ai/langgraph/tree/main/examples)
- [deer-flow 项目](../deer-flow/)（如有类似架构可参考）

---

## 📝 更新日志

### 2026-01-14

**[更新] 项目路线图大幅完善**
- 新增：LangSmith 监控配置说明
- 新增：Context Engineering 深度建议（工具返回优化、动态 Prompt、记忆管理）
- 新增：技术深度建议（状态管理、并行执行、错误恢复）
- 新增：成本估算（Demo vs 生产环境）
- 新增：报告模板示例
- 新增：Agent 分工建议表
- 更新：标记 Render 部署已完成
- 更新：调整任务优先级

### 2026-01-13

**[更新] 项目路线图**
- 标记已完成：图片显示修复、Chainlit 流式输出
- 新增：图片云存储、会话记忆持久化、冷启动优化
- 新增：整合 financial-news-brief 项目建议
- 新增：E2B 沙盒优化建议
- 调整 MVP 路径，反映当前进展