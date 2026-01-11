"""
init_students.py
使用 Python 初始化学生成绩表

运行方式：
    cd F:\anaconda_projects\data_agent
    python init_students.py
"""
import psycopg
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 数据库连接配置（从 .env 读取）
DB_CONFIG = {
    'host': os.getenv('PG_HOST', 'localhost'),
    'port': int(os.getenv('PG_PORT', '5432')),
    'user': os.getenv('PG_USER', 'postgres'),
    'password': os.getenv('PG_PASSWORD'),
    'dbname': os.getenv('PG_DBNAME', 'data_agent'),
}


def init_database():
    """初始化数据库表和数据"""
    
    print(f"🔗 连接数据库: {DB_CONFIG['dbname']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}")
    
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
            print("✅ 表 students_scores 创建成功")
            
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
            cur.execute("SELECT * FROM students_scores ORDER BY id")
            rows = cur.fetchall()
            
            print("\n📊 数据预览：")
            print("-" * 60)
            print(f"{'ID':<4} {'姓名':<10} {'课程1':<8} {'课程2':<8} {'课程3':<8}")
            print("-" * 60)
            for row in rows:
                print(f"{row[0]:<4} {row[1]:<10} {row[2]:<8} {row[3]:<8} {row[4]:<8}")
            print("-" * 60)
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        raise
    finally:
        conn.close()
    
    print("\n✅ 数据库初始化完成！")


def test_query():
    """测试查询功能"""
    conn = psycopg.connect(**DB_CONFIG)
    
    try:
        with conn.cursor() as cur:
            # 计算平均分
            cur.execute("""
                SELECT name, 
                       course1, course2, course3,
                       ROUND((course1 + course2 + course3) / 3.0, 1) AS average
                FROM students_scores
                ORDER BY average DESC
            """)
            rows = cur.fetchall()
            
            print("\n📈 成绩排名（按平均分）：")
            print("-" * 70)
            print(f"{'姓名':<10} {'课程1':<8} {'课程2':<8} {'课程3':<8} {'平均分':<8}")
            print("-" * 70)
            for row in rows:
                print(f"{row[0]:<10} {row[1]:<8} {row[2]:<8} {row[3]:<8} {row[4]:<8}")
            
    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
    test_query()
