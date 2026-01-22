# Data Agent 部署指南

> Render 云部署、Docker 配置、环境变量

---

## 目录

1. [Render 部署](#1-render-部署)
2. [Docker 部署](#2-docker-部署)
3. [环境变量配置](#3-环境变量配置)
4. [安全配置](#4-安全配置)
5. [故障排查](#5-故障排查)

---

## 1. Render 部署

### 1.1 当前部署

- **Demo**: https://data-agent-v1.onrender.com
- **API 文档**: https://data-agent-v1.onrender.com/api/docs
- **套餐**: Starter ($7/月)

### 1.2 部署步骤

1. **创建 Web Service**
   - 连接 GitHub 仓库
   - 选择 Docker 部署

2. **配置环境变量**
   - 见 [环境变量配置](#3-环境变量配置)

3. **部署设置**
   ```
   Build Command: (使用 Dockerfile)
   Start Command: (使用 Dockerfile CMD)
   Health Check Path: /api/health
   ```

### 1.3 注意事项

- Render 自动设置 `RENDER=true` 环境变量
- `config.py` 检测到后自动使用 Supabase 数据库
- 图片临时存储在 `/tmp/images`，重启后丢失

---

## 2. Docker 部署

### 2.1 Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 创建图片目录
RUN mkdir -p /tmp/images

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.2 本地 Docker 测试

```bash
# 构建镜像
docker build -t data-agent .

# 运行容器
docker run -p 8000:8000 --env-file .env data-agent

# 访问
# http://localhost:8000
```

---

## 3. 环境变量配置

### 3.1 必需变量

```env
# LLM (必需)
DEEPSEEK_API_KEY=sk-xxx

# 搜索 (必需)
TAVILY_API_KEY=tvly-xxx

# 代码沙盒 (必需)
E2B_API_KEY=e2b_xxx

# 云数据库 (Render 必需)
SUPABASE_HOST=aws-xxx.pooler.supabase.com
SUPABASE_PORT=6543
SUPABASE_USER=xxx
SUPABASE_PASSWORD=xxx
SUPABASE_DBNAME=postgres
```

### 3.2 可选变量

```env
# 环境标识 (Render 自动设置 RENDER=true)
ENVIRONMENT=production

# 图片目录
IMAGES_DIR=/tmp/images

# LangSmith 监控
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_xxx
LANGCHAIN_PROJECT=data-agent
```

### 3.3 Render 配置

在 Render Dashboard → Environment → Environment Variables 中添加：

| 变量 | 值 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | sk-xxx | DeepSeek API |
| `TAVILY_API_KEY` | tvly-xxx | Tavily 搜索 |
| `E2B_API_KEY` | e2b_xxx | E2B 沙盒 |
| `SUPABASE_HOST` | aws-xxx | Supabase 主机 |
| `SUPABASE_PORT` | 6543 | Supabase 端口 |
| `SUPABASE_USER` | xxx | Supabase 用户 |
| `SUPABASE_PASSWORD` | xxx | Supabase 密码 |
| `SUPABASE_DBNAME` | postgres | Supabase 数据库 |

---

## 4. 安全配置

### 4.1 SQL 安全

代码层验证 (graph.py):
- ✅ 仅允许 SELECT
- ❌ 禁止 DROP, DELETE, INSERT, UPDATE, TRUNCATE
- ❌ 禁止访问系统表 (pg_shadow, pg_roles 等)

数据库层防护:
- 创建只读用户
- 限制 schema 访问权限

### 4.2 代码执行安全

E2B 云端沙盒:
- 代码在隔离容器中执行
- 无法访问主机文件系统
- 无法访问网络 (除特定 API)
- 60 秒超时限制

系统提示限制:
- 禁止 `os.system()`, `subprocess`
- 禁止 `pip install`
- 禁止文件写入
- 禁止网络请求

### 4.3 API 安全

当前状态:
- CORS 允许所有来源 (`allow_origins=["*"]`)
- 无身份认证

生产建议:
- 限制 CORS 来源
- 添加 API Key 认证
- 添加速率限制

---

## 5. 故障排查

### 5.1 常见问题

**问题: 数据库连接失败**
```
检查:
1. 环境变量是否正确设置
2. Supabase 项目是否暂停 (免费版 7 天不活跃会暂停)
3. IP 白名单是否配置
```

**问题: E2B 沙盒超时**
```
原因: 代码执行超过 60 秒
解决: 优化代码，减少数据量
```

**问题: 图片无法显示**
```
检查:
1. /images 路由是否正确挂载
2. 图片目录是否有写入权限
3. 文件名是否包含特殊字符
```

### 5.2 日志查看

```bash
# Render 日志
# 在 Dashboard → Logs 查看

# 本地日志
uvicorn app:app --reload --log-level debug
```

### 5.3 健康检查

```bash
curl https://data-agent-v1.onrender.com/api/health
# {"status":"healthy","service":"data-agent","version":"1.0.0"}
```

---

## 附录: 架构图

```
                    用户
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              Render 服务 ($7/月)                     │
│  ┌───────────────────────────────────────────────┐ │
│  │  FastAPI + Chainlit (app.py)                   │ │
│  │    ├── /              聊天界面                  │ │
│  │    ├── /api/agent/*   API 接口                 │ │
│  │    └── /images/*      图片服务                 │ │
│  └───────────────────────────────────────────────┘ │
│                        │                            │
│                        ▼                            │
│  ┌───────────────────────────────────────────────┐ │
│  │  LangGraph Agent (graph.py)                    │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│    Supabase    │  │     E2B        │  │    Tavily      │
│   PostgreSQL   │  │    Sandbox     │  │    Search      │
└────────────────┘  └────────────────┘  └────────────────┘
```
