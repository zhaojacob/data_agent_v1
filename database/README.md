# Database 数据库模块

Data Agent 数据库相关文件。

---

## 📁 目录结构

```
database/
├── README.md                 # 本文件
├── QUICK_REFERENCE.md        # 常用命令速查
├── schema/
│   ├── create_news_table.sql # 建表脚本
│   ├── add_new_columns.sql   # 增量更新
│   └── cleanup_and_create.sql
└── scripts/
    ├── import_all_news.py    # 批量导入
    ├── update_daily_news.py  # 每日更新
    └── verify_schema.sql     # 验证脚本
```

---

## 🚀 快速开始

### 1. 创建表

```bash
# 命令行
psql -h localhost -U postgres -d data_agent -f schema/create_news_table.sql

# 或在 pgAdmin / Supabase SQL Editor 中执行
```

### 2. 导入数据

```bash
# 本地数据库
python scripts/import_all_news.py

# 云数据库
python scripts/import_all_news.py --cloud
```

### 3. 每日更新

```bash
python scripts/update_daily_news.py
python scripts/update_daily_news.py --cloud  # 云数据库
```

---

## 📊 表结构

所有业务数据在 `business_data` schema 中：

```sql
-- 新闻表
SELECT * FROM business_data.news LIMIT 10;

-- 学生成绩表 (测试数据)
SELECT * FROM business_data.students_scores;
```

### news 表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| title | TEXT | 标题 |
| url | TEXT | 链接 (唯一) |
| content | TEXT | 正文 |
| content_length | INT | 正文长度 |
| source | TEXT | 来源 (如 stcn, xinhua) |
| source_chinese | TEXT | 来源中文名 |
| keyword | TEXT | 搜索关键词 |
| datetime | TIMESTAMP | 发布时间 |
| created_at | TIMESTAMP | 入库时间 |

---

## ⚠️ 常见问题

### pgAdmin 看不到 business_data schema

**原因**: pgAdmin 界面缓存问题

**解决**:
1. 右键 `Schemas` → `Refresh`
2. 或断开重连数据库
3. 或重启 pgAdmin

**验证**: 执行 `scripts/verify_schema.sql`

### ON CONFLICT 错误

正常现象，脚本自动跳过重复数据。

### 权限不够

使用 `postgres` 用户导入数据。

---

## 📖 数据来源

数据来自 `financial-news-brief` 项目：

```
F:\anaconda_projects\financial-news-brief\data_fetcher\pipeline_results\pipeline_raw\
```
