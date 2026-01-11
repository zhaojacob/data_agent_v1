"""
test_supabase_connection.py
测试 Supabase 数据库连接

使用方法：
    conda activate lg
    cd F:\anaconda_projects\data_agent
    python test_supabase_connection.py
"""

import os
from dotenv import load_dotenv
import psycopg

# 加载环境变量
load_dotenv(override=True)

def test_connection():
    """测试 Supabase 连接"""
    
    # 读取配置
    host = os.getenv('PG_HOST')
    port = os.getenv('PG_PORT')
    user = os.getenv('PG_USER')
    password = os.getenv('PG_PASSWORD')
    dbname = os.getenv('PG_DBNAME')
    
    print("=" * 50)
    print("Supabase Connection Test")
    print("=" * 50)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"User: {user}")
    print(f"Database: {dbname}")
    print(f"Password: {'*' * len(password) if password else 'NOT SET'}")
    print("=" * 50)
    
    # 测试连接
    print("\n[1/3] Testing connection...")
    try:
        conn = psycopg.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            dbname=dbname
        )
        print("✅ Connection successful!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    # 测试查询
    print("\n[2/3] Testing query (business_data.students_scores)...")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM business_data.students_scores LIMIT 3")
            rows = cur.fetchall()
            print(f"✅ Query successful! Found {len(rows)} rows")
            for row in rows:
                print(f"   {row}")
    except Exception as e:
        print(f"❌ Query failed: {e}")
    
    # 测试权限（应该失败）
    print("\n[3/3] Testing write permission (should fail)...")
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO business_data.students_scores (name) VALUES ('test')")
        print("⚠️ WARNING: Write succeeded (unexpected!)")
    except Exception as e:
        print(f"✅ Write blocked as expected: {type(e).__name__}")
    
    conn.close()
    print("\n" + "=" * 50)
    print("Test completed!")
    print("=" * 50)

if __name__ == "__main__":
    test_connection()
