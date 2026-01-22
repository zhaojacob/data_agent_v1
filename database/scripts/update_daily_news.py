"""
每日增量更新脚本 - 导入最新批次的新闻数据
用于 financial-news-brief 爬取完成后的日常更新
"""

import os
import json
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

# 加载环境变量（从项目根目录）
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

# 数据源路径
DATA_SOURCE_PATH = r"F:\anaconda_projects\financial-news-brief\data_fetcher\pipeline_results\pipeline_raw"


def get_db_config(use_local: bool = True) -> dict:
    """获取数据库配置"""
    if use_local:
        # 使用 postgres 超级用户（有所有权限）
        return {
            'host': os.getenv('LOCAL_PG_HOST', 'localhost'),
            'port': int(os.getenv('LOCAL_PG_PORT', '5432')),
            'user': os.getenv('LOCAL_PG_USER', 'postgres'),
            'password': os.getenv('LOCAL_PG_PASSWORD'),  # 从 .env 读取
            'dbname': os.getenv('LOCAL_PG_DBNAME', 'data_agent')
        }
    else:
        # 云端模式：使用 Supabase 管理员账户（有写入权限）
        return {
            'host': os.getenv('SUPABASE_ADMIN_HOST'),
            'port': int(os.getenv('SUPABASE_ADMIN_PORT', '5432')),
            'user': os.getenv('SUPABASE_ADMIN_USER'),
            'password': os.getenv('SUPABASE_ADMIN_PASSWORD'),
            'dbname': os.getenv('SUPABASE_ADMIN_DBNAME', 'postgres')
        }


def parse_datetime(time_str: str) -> datetime:
    """解析时间字符串"""
    if not time_str:
        return None
    
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    
    print(f"⚠️  无法解析时间: {time_str}")
    return None


def parse_date_only(date_str: str):
    """解析日期（仅年月日）"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return None


def load_json_file(file_path: str) -> Dict:
    """加载 JSON 文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载文件失败 {file_path}: {e}")
        return None


def extract_batch_id(file_path: str) -> str:
    """从文件路径提取批次ID"""
    parts = Path(file_path).parts
    for part in parts:
        if part.startswith('batch_'):
            return part
    return None


def prepare_article_data(article: Dict, keyword: str, batch_id: str) -> tuple:
    """准备单条新闻数据"""
    # 时间处理：优先使用 datetime，其次 search_pub_time
    publish_time = parse_datetime(article.get('datetime') or article.get('search_pub_time'))
    
    return (
        article.get('title', ''),
        article.get('url', ''),
        article.get('source', ''),
        article.get('source_chinese', ''),
        article.get('search_title', ''),
        article.get('search_summary', ''),
        article.get('search_pub_time', ''),
        article.get('content', ''),
        article.get('content_length', 0),
        article.get('author', ''),
        publish_time,                                    # publish_time (TIMESTAMPTZ)
        parse_date_only(article.get('date')),          # date_only (DATE)
        article.get('datetime', ''),                    # datetime_str (VARCHAR)
        article.get('timestamp'),                       # timestamp_unix (BIGINT)
        parse_datetime(article.get('fetch_time')),     # fetch_time (TIMESTAMPTZ)
        keyword,
        batch_id
    )


def import_batch_file(conn, file_path: str, use_local: bool) -> int:
    """导入单个批次文件"""
    data = load_json_file(file_path)
    if not data or 'articles' not in data:
        return 0
    
    keyword = data.get('keyword', '')
    batch_id = extract_batch_id(file_path)
    articles = data.get('articles', [])
    
    if not articles:
        return 0
    
    # 准备数据并去重（按 URL）
    seen_urls = set()
    values = []
    duplicate_count = 0
    
    for article in articles:
        url = article.get('url')
        if url and url not in seen_urls:
            seen_urls.add(url)
            values.append(prepare_article_data(article, keyword, batch_id))
        elif url in seen_urls:
            duplicate_count += 1
    
    if not values:
        return 0
    
    if duplicate_count > 0:
        print(f"   ⚠️  跳过 {duplicate_count} 条重复 URL")
    
    # 根据数据库类型选择表名
    # 注意：本地和云端都使用 business_data.news
    table_name = "business_data.news"
    
    # 批量插入（使用 ON CONFLICT 避免重复）
    insert_query = f"""
        INSERT INTO {table_name}
        (title, url, source, source_chinese, search_title, search_summary, search_pub_time,
         content, content_length, author, 
         publish_time, date_only, datetime_str, timestamp_unix, fetch_time,
         keyword, batch_id)
        VALUES %s
        ON CONFLICT (url) DO UPDATE SET
            title = EXCLUDED.title,
            source_chinese = EXCLUDED.source_chinese,
            search_title = EXCLUDED.search_title,
            search_summary = EXCLUDED.search_summary,
            search_pub_time = EXCLUDED.search_pub_time,
            content = EXCLUDED.content,
            content_length = EXCLUDED.content_length,
            author = EXCLUDED.author,
            publish_time = EXCLUDED.publish_time,
            date_only = EXCLUDED.date_only,
            datetime_str = EXCLUDED.datetime_str,
            timestamp_unix = EXCLUDED.timestamp_unix,
            updated_at = NOW()
    """
    
    try:
        with conn.cursor() as cur:
            execute_values(cur, insert_query, values)
            conn.commit()
            return len(values)
    except Exception as e:
        conn.rollback()
        print(f"❌ 插入数据失败: {e}")
        return 0


def get_latest_batch_folder() -> Optional[Path]:
    """获取最新的批次文件夹"""
    base_path = Path(DATA_SOURCE_PATH)
    if not base_path.exists():
        print(f"❌ 数据源路径不存在: {DATA_SOURCE_PATH}")
        return None
    
    folders = [f for f in base_path.iterdir() if f.is_dir() and f.name.startswith('batch_')]
    if not folders:
        print("❌ 未找到任何批次文件夹")
        return None
    
    # 按文件夹名称排序，最新的在最后
    folders = sorted(folders)
    return folders[-1]


def update_latest_batch(use_local: bool = True, batch_folder: Optional[str] = None):
    """
    导入最新批次数据（增量更新）
    
    Args:
        use_local: True 使用本地数据库，False 使用 Supabase
        batch_folder: 指定批次文件夹名称，None 则自动选择最新批次
    """
    # 获取数据库配置
    db_config = get_db_config(use_local)
    db_type = "本地 PostgreSQL" if use_local else "Supabase 云"
    print(f"📍 使用{db_type}数据库")
    
    # 连接数据库
    try:
        conn = psycopg2.connect(**db_config)
        print("✅ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return
    
    # 确定要导入的批次
    if batch_folder:
        batch_path = Path(DATA_SOURCE_PATH) / batch_folder
        if not batch_path.exists():
            print(f"❌ 指定的批次文件夹不存在: {batch_path}")
            conn.close()
            return
    else:
        batch_path = get_latest_batch_folder()
        if not batch_path:
            conn.close()
            return
    
    print(f"\n📦 处理批次: {batch_path.name}")
    print(f"{'='*60}")
    
    # 获取该批次的所有 JSON 文件
    json_files = list(batch_path.glob('*.json'))
    print(f"   找到 {len(json_files)} 个 JSON 文件")
    
    total_files = 0
    total_articles = 0
    
    for json_file in json_files:
        count = import_batch_file(conn, str(json_file), use_local)
        if count > 0:
            total_files += 1
            total_articles += count
            print(f"   ✅ {json_file.name}: {count} 条新闻")
    
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"✅ 增量更新完成！")
    print(f"   - 批次: {batch_path.name}")
    print(f"   - 处理文件: {total_files} 个")
    print(f"   - 导入新闻: {total_articles} 条")
    print(f"{'='*60}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='每日增量更新新闻数据')
    parser.add_argument('--cloud', action='store_true', help='使用 Supabase 云数据库（默认使用本地）')
    parser.add_argument('--batch', type=str, help='指定批次文件夹名称（如 batch_20260120_090818），不指定则自动选择最新批次')
    
    args = parser.parse_args()
    
    print("="*60)
    print("新闻数据增量更新工具")
    print("用途：每日爬取后更新最新数据")
    print("="*60)
    
    update_latest_batch(use_local=not args.cloud, batch_folder=args.batch)
