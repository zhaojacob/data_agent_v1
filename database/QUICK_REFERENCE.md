# 快速参考卡

> 常用命令和查询速查表

---

## 🚀 快速命令

### 导入数据
```bash
# 首次导入所有历史数据
python scripts/import_all_news.py

# 每日增量更新
python scripts/update_daily_news.py

# 导入到云数据库
python scripts/import_all_news.py --cloud
```

### 验证数据库
```bash
# Windows 用户
cd scripts
verify_schema.bat

# 或在 pgAdmin Query Tool 中执行
# 打开 scripts/verify_schema.sql
```

---

## 📊 常用 SQL 查询

### 基本查询
```sql
-- 查看所有 schema
SELECT schema_name FROM information_schema.schemata;

-- 查看表结构
SELECT column_name, data_type 
FROM information_schema.columns
WHERE table_schema = 'business_data' AND table_name = 'news';

-- 统计总数
SELECT COUNT(*) FROM business_data.news;

-- 查看最新 10 条
SELECT * FROM business_data.news 
ORDER BY created_at DESC LIMIT 10;
```

### 统计分析
```sql
-- 按关键词统计
SELECT keyword, COUNT(*) as count
FROM business_data.news
GROUP BY keyword
ORDER BY count DESC;

-- 按来源统计
SELECT source_chinese, COUNT(*) as count
FROM business_data.news
WHERE source_chinese IS NOT NULL
GROUP BY source_chinese
ORDER BY count DESC;

-- 按日期统计
SELECT date_only, COUNT(*) as count
FROM business_data.news
WHERE date_only IS NOT NULL
GROUP BY date_only
ORDER BY date_only DESC
LIMIT 30;

-- 按批次统计
SELECT batch_id, COUNT(*) as count
FROM business_data.news
GROUP BY batch_id
ORDER BY batch_id DESC;
```

### 搜索查询
```sql
-- 按关键词搜索
SELECT title, source_chinese, publish_time
FROM business_data.news
WHERE keyword = '证监会'
ORDER BY publish_time DESC
LIMIT 20;

-- 按标题模糊搜索
SELECT title, source_chinese, publish_time
FROM business_data.news
WHERE title LIKE '%科创板%'
ORDER BY publish_time DESC
LIMIT 20;

-- 按时间范围搜索
SELECT title, publish_time, source_chinese
FROM business_data.news
WHERE publish_time >= '2026-01-20'
  AND publish_time < '2026-01-22'
ORDER BY publish_time DESC;

-- 查找长文（超过 1000 字）
SELECT title, content_length, source_chinese
FROM business_data.news
WHERE content_length > 1000
ORDER BY content_length DESC
LIMIT 20;
```

---

## 🔧 pgAdmin 操作

### 刷新 Schema
```
1. 找到：Servers → PostgreSQL → Databases → data_agent → Schemas
2. 右键点击 "Schemas"
3. 选择 "Refresh"
```

### 打开 Query Tool
```
1. 右键点击 "data_agent" 数据库
2. 选择 "Query Tool"
3. 输入 SQL 并按 F5 执行
```

### 查看表数据
```
1. 找到：Schemas → business_data → Tables → news
2. 右键点击 "news"
3. 选择 "View/Edit Data" → "All Rows"
```

### 导出数据
```
1. 执行查询
2. 点击结果窗口的 "Download as CSV" 按钮（💾）
3. 选择保存位置
```

---

## 🐍 Python 代码示例

### 连接数据库
```python
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('PG_HOST'),
    port=os.getenv('PG_PORT'),
    user=os.getenv('PG_USER'),
    password=os.getenv('PG_PASSWORD'),
    dbname=os.getenv('PG_DBNAME')
)
```

### 查询数据
```python
cursor = conn.cursor()

# 查询最新新闻
cursor.execute("""
    SELECT title, source_chinese, publish_time
    FROM business_data.news
    ORDER BY publish_time DESC
    LIMIT 10
""")

results = cursor.fetchall()
for row in results:
    print(f"{row[0]} - {row[1]} - {row[2]}")
```

### 按关键词查询
```python
keyword = "证监会"
cursor.execute("""
    SELECT title, publish_time
    FROM business_data.news
    WHERE keyword = %s
    ORDER BY publish_time DESC
    LIMIT 20
""", (keyword,))

results = cursor.fetchall()
```

---

## 📁 文件位置

### 数据源
```
F:\anaconda_projects\financial-news-brief\data_fetcher\pipeline_results\pipeline_raw\
└── batch_YYYYMMDD_HHMMSS\
    └── complete_pipeline_*.json
```

### 数据库文件
```
data_agent/database/
├── schema/
│   └── create_news_table.sql      # 表结构
├── scripts/
│   ├── import_all_news.py         # 批量导入
│   ├── update_daily_news.py       # 增量更新
│   ├── verify_schema.sql          # 验证脚本
│   └── verify_schema.bat          # Windows 验证
└── *.md                           # 文档
```

---

## ⚠️ 常见问题速查

| 问题 | 解决方法 |
|------|---------|
| pgAdmin 看不到 business_data | 右键 Schemas → Refresh |
| ON CONFLICT 错误 | 正常，自动去重，忽略即可 |
| 权限不够 | 使用 postgres 用户 |
| 导入失败 | 检查 .env 配置 |
| 查询报错 | 确保加上 schema：business_data.news |

---

## 🔗 详细文档

- [README.md](README.md) - 快速开始
- [PGADMIN_REFRESH_GUIDE.md](PGADMIN_REFRESH_GUIDE.md) - pgAdmin 刷新指南
- [PGADMIN_GUIDE.md](PGADMIN_GUIDE.md) - pgAdmin 完整指南
- [IMPORT_GUIDE.md](IMPORT_GUIDE.md) - 导入详细指南
- [FINAL_STRUCTURE.md](FINAL_STRUCTURE.md) - 表结构文档
- [CURRENT_STATUS.md](CURRENT_STATUS.md) - 当前状态

---

## 💡 快捷键

| 快捷键 | 功能 |
|--------|------|
| F5 | 执行 SQL 查询 |
| F7 | 格式化 SQL |
| Ctrl + Space | 自动补全 |
| Ctrl + / | 注释/取消注释 |

---

**保存这个文件，随时查阅！** 📌
