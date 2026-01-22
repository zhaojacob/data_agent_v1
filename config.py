"""
Data Agent 配置模块
==================
自动检测运行环境，选择合适的数据库配置。

环境检测逻辑：
- 本地开发：使用 localhost PostgreSQL
- Render 部署：使用 Supabase 云数据库

检测方法：
1. 检查 RENDER 环境变量（Render 自动设置）
2. 检查 ENVIRONMENT 环境变量（手动设置）
3. 默认为本地环境
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(override=True)


def is_production() -> bool:
    """
    检测是否为生产环境（Render）
    
    Returns:
        bool: True 表示生产环境，False 表示本地开发
    """
    # 方法1：检查 RENDER 环境变量（Render 自动设置）
    if os.getenv('RENDER'):
        return True
    
    # 方法2：检查 ENVIRONMENT 环境变量（手动设置）
    env = os.getenv('ENVIRONMENT', 'development').lower()
    if env in ['production', 'prod']:
        return True
    
    # 方法3：检查是否有 Supabase 特定的环境变量
    if os.getenv('SUPABASE_URL') or os.getenv('USE_SUPABASE') == 'true':
        return True
    
    return False


def get_db_config() -> dict:
    """
    获取数据库配置
    
    Returns:
        dict: 包含数据库连接参数的字典
    """
    if is_production():
        # 生产环境：使用 Supabase
        config = {
            'host': os.getenv('SUPABASE_HOST', 'aws-1-ap-northeast-2.pooler.supabase.com'),
            'port': int(os.getenv('SUPABASE_PORT', '6543')),
            'user': os.getenv('SUPABASE_USER', 'agent_reader.khoqxgnmngysizvwtqlh'),
            'password': os.getenv('SUPABASE_PASSWORD', '272102abc'),
            'dbname': os.getenv('SUPABASE_DBNAME', 'postgres'),
        }
        print(f"🌐 [生产环境] 使用 Supabase: {config['host']}")
    else:
        # 本地开发：使用 localhost PostgreSQL
        config = {
            'host': os.getenv('LOCAL_PG_HOST', 'localhost'),
            'port': int(os.getenv('LOCAL_PG_PORT', '5432')),
            'user': os.getenv('LOCAL_PG_USER', 'postgres'),
            'password': os.getenv('LOCAL_PG_PASSWORD'),  # 从 .env 读取
            'dbname': os.getenv('LOCAL_PG_DBNAME', 'data_agent'),
        }
        print(f"💻 [本地开发] 使用 localhost: {config['host']}:{config['port']}/{config['dbname']}")
    
    return config


def get_db_connection_string() -> str:
    """
    获取数据库连接字符串（用于 psycopg）
    
    Returns:
        str: PostgreSQL 连接字符串
    """
    config = get_db_config()
    return f"host={config['host']} port={config['port']} dbname={config['dbname']} user={config['user']} password={config['password']}"


# 导出配置
DB_CONFIG = get_db_config()
DB_CONNECTION_STRING = get_db_connection_string()

# 其他配置
IMAGES_DIR = os.getenv('IMAGES_DIR', os.path.join(os.path.dirname(__file__), 'images'))
os.makedirs(IMAGES_DIR, exist_ok=True)

# API Keys
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
E2B_API_KEY = os.getenv('E2B_API_KEY')

# LangSmith
LANGSMITH_TRACING = os.getenv('LANGSMITH_TRACING', 'false').lower() == 'true'
LANGSMITH_API_KEY = os.getenv('LANGSMITH_API_KEY')
LANGSMITH_PROJECT = os.getenv('LANGSMITH_PROJECT', 'data-agent')


if __name__ == "__main__":
    """测试配置"""
    print("=" * 60)
    print("Data Agent 配置测试")
    print("=" * 60)
    print(f"运行环境: {'生产环境 (Render)' if is_production() else '本地开发'}")
    print(f"数据库配置: {DB_CONFIG}")
    print(f"连接字符串: {DB_CONNECTION_STRING}")
    print(f"图片目录: {IMAGES_DIR}")
    print("=" * 60)
