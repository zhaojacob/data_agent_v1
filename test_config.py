"""
测试配置模块
============
验证环境检测和数据库配置是否正确
"""

import os
from config import is_production, get_db_config, DB_CONNECTION_STRING

print("=" * 70)
print("Data Agent 配置测试")
print("=" * 70)

# 检测环境
print(f"\n📍 环境检测:")
print(f"   RENDER 环境变量: {os.getenv('RENDER', '未设置')}")
print(f"   ENVIRONMENT 环境变量: {os.getenv('ENVIRONMENT', '未设置')}")
print(f"   检测结果: {'🌐 生产环境 (Render)' if is_production() else '💻 本地开发'}")

# 数据库配置
print(f"\n🗄️  数据库配置:")
config = get_db_config()
for key, value in config.items():
    if key == 'password':
        print(f"   {key}: {'*' * len(str(value))}")  # 隐藏密码
    else:
        print(f"   {key}: {value}")

# 连接字符串（隐藏密码）
print(f"\n🔗 连接字符串:")
conn_str = DB_CONNECTION_STRING
# 隐藏密码部分
if 'password=' in conn_str:
    parts = conn_str.split('password=')
    if len(parts) > 1:
        password_part = parts[1].split()[0]
        conn_str = conn_str.replace(password_part, '*' * 8)
print(f"   {conn_str}")

# 测试连接
print(f"\n🔌 测试数据库连接:")
try:
    import psycopg
    conn = psycopg.connect(DB_CONNECTION_STRING)
    print(f"   ✅ 连接成功！")
    
    # 测试查询
    with conn.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user;")
        db_name, user = cursor.fetchone()
        print(f"   数据库: {db_name}")
        print(f"   用户: {user}")
        
        # 检查 business_data schema
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name = 'business_data';
        """)
        result = cursor.fetchone()
        if result:
            print(f"   ✅ business_data schema 存在")
            
            # 检查 news 表
            cursor.execute("""
                SELECT COUNT(*) 
                FROM business_data.news;
            """)
            count = cursor.fetchone()[0]
            print(f"   ✅ business_data.news 表存在，共 {count} 条记录")
        else:
            print(f"   ⚠️  business_data schema 不存在")
    
    conn.close()
    
except Exception as e:
    print(f"   ❌ 连接失败: {e}")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)
