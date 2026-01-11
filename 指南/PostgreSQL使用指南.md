# PostgreSQL 使用指南

本指南介绍如何在 PostgreSQL 中创建表、插入数据，以及数据库工作的基本原理。

---

## 一、数据库基础原理

### 1.1 什么是数据库？

数据库是**结构化存储数据的系统**，可以理解为一个"超级 Excel"：
- **数据库 (Database)**：相当于一个 Excel 文件
- **表 (Table)**：相当于 Excel 中的一个工作表 (Sheet)
- **行 (Row)**：相当于 Excel 中的一行数据
- **列 (Column)**：相当于 Excel 中的一列（字段）

### 1.2 SQL 语言

SQL (Structured Query Language) 是操作数据库的标准语言：

| 操作类型 | SQL 命令 | 说明 |
|---------|---------|------|
| 创建 | `CREATE` | 创建数据库、表 |
| 查询 | `SELECT` | 查询数据 |
| 插入 | `INSERT` | 插入新数据 |
| 更新 | `UPDATE` | 修改现有数据 |
| 删除 | `DELETE` | 删除数据 |

### 1.3 PostgreSQL vs MySQL

| 特性 | PostgreSQL | MySQL |
|-----|-----------|-------|
| 数据类型 | 更丰富（JSON、数组、UUID） | 基础类型 |
| 标准兼容 | 更严格遵循 SQL 标准 | 有自己的扩展语法 |
| 扩展性 | 支持自定义类型、函数 | 较少 |
| 适用场景 | 复杂查询、数据分析 | Web 应用、简单场景 |

---

## 二、环境信息

根据 `.env` 文件中的配置：

```
PG_HOST=localhost
PG_PORT=5432
PG_USER=financial-news-brief
PG_PASSWORD=272102
PG_DBNAME=data_agent
```

---

## 三、创建示例表和数据

### 3.1 方式一：使用 pgAdmin（图形界面）

1. **打开 pgAdmin**，连接到服务器

2. **展开数据库**：Servers → PostgreSQL → Databases → `data_agent`

3. **打开查询工具**：右键 `data_agent` → Query Tool

4. **执行以下 SQL**：

```sql
-- 创建学生成绩表
CREATE TABLE students_scores (
    id SERIAL PRIMARY KEY,          -- SERIAL 是 PostgreSQL 的自增类型
    name VARCHAR(50),
    course1 INT,
    course2 INT,
    course3 INT
);

-- 插入 10 位学生的成绩数据
INSERT INTO students_scores (name, course1, course2, course3)
VALUES
    ('学生1', 85, 92, 78),
    ('学生2', 76, 88, 91),
    ('学生3', 90, 85, 80),
    ('学生4', 65, 70, 72),
    ('学生5', 82, 89, 95),
    ('学生6', 91, 93, 87),
    ('学生7', 77, 78, 85),
    ('学生8', 88, 92, 91),
    ('学生9', 84, 76, 80),
    ('学生10', 89, 90, 92);

-- 查看数据
SELECT * FROM students_scores;
```

5. **点击执行按钮**（▶️ 或按 F5）

---

### 3.2 方式二：使用 psql 命令行

打开 PowerShell 或命令提示符：

```powershell
# 连接到数据库
psql -U financial-news-brief -d data_agent -h localhost

# 输入密码后，执行 SQL
```

在 psql 中执行：

```sql
-- 创建表
CREATE TABLE students_scores (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50),
    course1 INT,
    course2 INT,
    course3 INT
);

-- 插入数据
INSERT INTO students_scores (name, course1, course2, course3)
VALUES
    ('学生1', 85, 92, 78),
    ('学生2', 76, 88, 91),
    ('学生3', 90, 85, 80),
    ('学生4', 65, 70, 72),
    ('学生5', 82, 89, 95),
    ('学生6', 91, 93, 87),
    ('学生7', 77, 78, 85),
    ('学生8', 88, 92, 91),
    ('学生9', 84, 76, 80),
    ('学生10', 89, 90, 92);

-- 查看数据
SELECT * FROM students_scores;

-- 退出
\q
```

---

### 3.3 方式三：使用 SQL 脚本文件

1. **创建脚本文件** `init_students.sql`：

```sql
-- init_students.sql
-- 学生成绩表初始化脚本

-- 如果表已存在则删除（可选，谨慎使用）
DROP TABLE IF EXISTS students_scores;

-- 创建表
CREATE TABLE students_scores (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    course1 INT CHECK (course1 >= 0 AND course1 <= 100),
    course2 INT CHECK (course2 >= 0 AND course2 <= 100),
    course3 INT CHECK (course3 >= 0 AND course3 <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入数据
INSERT INTO students_scores (name, course1, course2, course3)
VALUES
    ('学生1', 85, 92, 78),
    ('学生2', 76, 88, 91),
    ('学生3', 90, 85, 80),
    ('学生4', 65, 70, 72),
    ('学生5', 82, 89, 95),
    ('学生6', 91, 93, 87),
    ('学生7', 77, 78, 85),
    ('学生8', 88, 92, 91),
    ('学生9', 84, 76, 80),
    ('学生10', 89, 90, 92);

-- 验证
SELECT * FROM students_scores;
```

2. **执行脚本**：

```powershell
psql -U financial-news-brief -d data_agent -h localhost -f init_students.sql
```

---

### 3.4 方式四：使用 Python 脚本

```python
"""
init_students.py
使用 Python 初始化学生成绩表
"""
import psycopg
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 数据库连接配置
DB_CONFIG = {
    'host': os.getenv('PG_HOST', 'localhost'),
    'port': int(os.getenv('PG_PORT', '5432')),
    'user': os.getenv('PG_USER', 'postgres'),
    'password': os.getenv('PG_PASSWORD'),
    'dbname': os.getenv('PG_DBNAME', 'data_agent'),
}

def init_database():
    """初始化数据库表和数据"""
    
    # 连接数据库
    conn = psycopg.connect(**DB_CONFIG)
    conn.autocommit = True
    
    try:
        with conn.cursor() as cur:
            # 1. 删除旧表（如果存在）
            cur.execute("DROP TABLE IF EXISTS students_scores")
            print("✅ 已清理旧表")
            
            # 2. 创建新表
            cur.execute("""
                CREATE TABLE students_scores (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) NOT NULL,
                    course1 INT,
                    course2 INT,
                    course3 INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ 表创建成功")
            
            # 3. 插入数据
            students_data = [
                ('学生1', 85, 92, 78),
                ('学生2', 76, 88, 91),
                ('学生3', 90, 85, 80),
                ('学生4', 65, 70, 72),
                ('学生5', 82, 89, 95),
                ('学生6', 91, 93, 87),
                ('学生7', 77, 78, 85),
                ('学生8', 88, 92, 91),
                ('学生9', 84, 76, 80),
                ('学生10', 89, 90, 92),
            ]
            
            cur.executemany(
                "INSERT INTO students_scores (name, course1, course2, course3) VALUES (%s, %s, %s, %s)",
                students_data
            )
            print(f"✅ 已插入 {len(students_data)} 条数据")
            
            # 4. 验证数据
            cur.execute("SELECT * FROM students_scores")
            rows = cur.fetchall()
            
            print("\n📊 数据预览：")
            print("-" * 50)
            print(f"{'ID':<4} {'姓名':<8} {'课程1':<6} {'课程2':<6} {'课程3':<6}")
            print("-" * 50)
            for row in rows:
                print(f"{row[0]:<4} {row[1]:<8} {row[2]:<6} {row[3]:<6} {row[4]:<6}")
            
    finally:
        conn.close()
    
    print("\n✅ 数据库初始化完成！")


if __name__ == "__main__":
    init_database()
```

运行：
```powershell
cd F:\anaconda_projects\data_agent
python init_students.py
```

---

## 四、常用 SQL 查询示例

```sql
-- 查看所有数据
SELECT * FROM students_scores;

-- 查看特定列
SELECT name, course1 FROM students_scores;

-- 条件查询：课程1成绩大于80的学生
SELECT * FROM students_scores WHERE course1 > 80;

-- 计算平均分
SELECT name, (course1 + course2 + course3) / 3.0 AS average 
FROM students_scores;

-- 按平均分排序
SELECT name, (course1 + course2 + course3) / 3.0 AS average 
FROM students_scores 
ORDER BY average DESC;

-- 统计信息
SELECT 
    COUNT(*) AS 学生人数,
    AVG(course1) AS 课程1平均分,
    MAX(course1) AS 课程1最高分,
    MIN(course1) AS 课程1最低分
FROM students_scores;
```

---

## 五、PostgreSQL vs MySQL 语法差异

| 功能 | MySQL | PostgreSQL |
|-----|-------|-----------|
| 自增主键 | `INT AUTO_INCREMENT` | `SERIAL` 或 `INT GENERATED ALWAYS AS IDENTITY` |
| 字符串连接 | `CONCAT(a, b)` | `a \|\| b` 或 `CONCAT(a, b)` |
| 限制行数 | `LIMIT 10` | `LIMIT 10`（相同） |
| 当前时间 | `NOW()` | `NOW()` 或 `CURRENT_TIMESTAMP` |
| 布尔类型 | `TINYINT(1)` | `BOOLEAN` |
| JSON | `JSON` | `JSON` 或 `JSONB`（推荐） |

---

## 六、验证 Agent 连接

在 `graph.py` 中的 `sql_inter` 工具已配置好连接 PostgreSQL。可以通过 Agent 测试：

```
用户：查询 students_scores 表的所有数据
Agent：调用 sql_inter("SELECT * FROM students_scores")
```

---

## 七、常见问题

### Q1: 连接被拒绝？
检查 PostgreSQL 服务是否运行：
```powershell
# Windows 服务
Get-Service postgresql*
```

### Q2: 权限不足？
确保用户有表的访问权限：
```sql
GRANT ALL PRIVILEGES ON TABLE students_scores TO "financial-news-brief";
```

### Q3: 表已存在？
使用 `DROP TABLE IF EXISTS` 先删除，或使用 `CREATE TABLE IF NOT EXISTS`。

---

**文档版本**: v1.0  
**最后更新**: 2026-01-02  
**适用数据库**: PostgreSQL 14+
