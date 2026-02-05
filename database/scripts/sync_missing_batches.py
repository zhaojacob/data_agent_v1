"""
智能增量同步脚本 - 只导入数据库中缺失的批次
对比数据库已有批次和文件系统中的批次，只导入缺失的部分
"""

import os
import json
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set
from dotenv import load_dotenv

# 加载环境变量（从项目根目录）
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

# 数据源路径
DATA_SOURCE_PATH = r"F:\anaconda_projects\financial-news-brief\data_fetcher\pipeline_results\pipeline_raw"


def get_db_config(use_local: bool = True) -> dict:
    """获取数据库配置"""
    if use_local:
        return {
            'host': os.getenv('LOCAL_PG_HOST', 'localhost'),
            'port': int(os.getenv('LOCAL_PG_PORT', '5432')),
            'user': os.getenv('LOCAL_PG_USER', 'postgres'),
            'password': os.getenv('LOCAL_PG_PASSWORD'),
            'dbname': os.getenv('LOCAL_PG_DBNAME', 'data_agent')
        }
    else:
        return {
            'host': os.getenv('SUPABASE_ADMIN_HOST'),
            'port': int(os.getenv('SUPABASE_ADMIN_PORT', '5432')),
            'user': os.getenv('SUPABASE_ADMIN_USER'),
            'password': os.getenv('SUPABASE_ADMIN_PASSWORD'),
            'dbname': os.getenv('SUPABASE_ADMIN_DBNAME', 'postgres')
        }


def get_existing_batch_ids(conn) -> Set[str]:
    """从数据库获取已存在的批次ID列表"""
    query = "SELECT DISTINCT batch_id FROM business_data.news WHERE batch_id IS NOT NULL"
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
            return {row[0] for row in results}
    except Exception as e:
        print(f"⚠️  查询已有批次失败: {e}")
        return set()


def get_file_system_batch_ids() -> List[str]:
    """从文件系统获取所有批次文件夹名称"""
    base_path = Path(DATA_SOURCE_PATH)
    if not base_path.exists():
        print(f"❌ 数据源路径不存在: {DATA_SOURCE_PATH}")
        return []
    
    folders = [f.name for f in base_path.iterdir() if f.is_dir() and f.name.startswith('batch_')]
    return sorted(folders)


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


def truncate_field(value: str, max_length: int) -> str:
    """截断字段到指定长度"""
    if value and len(value) > max_length:
        return value[:max_length-3] + '...'
    return value or ''


def prepare_article_data(article: Dict, keyword: str, batch_id: str) -> tuple:
    """准备单条新闻数据"""
    publish_time = parse_datetime(article.get('datetime') or article.get('search_pub_time'))
    
    # 截断可能超长的字段（与数据库 VARCHAR 限制匹配）
    author = truncate_field(article.get('author', ''), 100)
    source = truncate_field(article.get('source', ''), 100)
    source_chinese = truncate_field(article.get('source_chinese', ''), 100)
    keyword_truncated = truncate_field(keyword, 100)
    
    return (
        article.get('title', ''),
        article.get('url', ''),
        source,
        source_chinese,
        article.get('search_title', ''),
        article.get('search_summary', ''),
        article.get('search_pub_time', ''),
        article.get('content', ''),
        article.get('content_length', 0),
        author,
        publish_time,
        parse_date_only(article.get('date')),
        article.get('datetime', ''),
        article.get('timestamp'),
        parse_datetime(article.get('fetch_time')),
        keyword_truncated,
        batch_id
    )


def import_batch_folder(conn, batch_id: str) -> int:
    """导入单个批次文件夹的所有数据"""
    batch_path = Path(DATA_SOURCE_PATH) / batch_id
    if not batch_path.exists():
        print(f"❌ 批次文件夹不存在: {batch_path}")
        return 0
    
    json_files = list(batch_path.glob('*.json'))
    if not json_files:
        return 0
    
    total_articles = 0
    
    for json_file in json_files:
        data = load_json_file(str(json_file))
        if not data or 'articles' not in data:
            continue
        
        keyword = data.get('keyword', '')
        articles = data.get('articles', [])
        
        if not articles:
            continue
        
        # 准备数据并去重
        seen_urls = set()
        values = []
        
        for article in articles:
            url = article.get('url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                values.append(prepare_article_data(article, keyword, batch_id))
        
        if not values:
            continue
        
        # 批量插入
        insert_query = """
            INSERT INTO business_data.news
            (title, url, source, source_chinese, search_title, search_summary, search_pub_time,
             content, content_length, author, 
             publish_time, date_only, datetime_str, timestamp_unix, fetch_time,
             keyword, batch_id)
            VALUES %s
            ON CONFLICT (url) DO UPDATE SET
                title = EXCLUDED.title,
                source_chinese = EXCLUDED.source_chinese,
                content = EXCLUDED.content,
                content_length = EXCLUDED.content_length,
                publish_time = EXCLUDED.publish_time,
                updated_at = NOW()
        """
        
        try:
            with conn.cursor() as cur:
                execute_values(cur, insert_query, values)
                conn.commit()
                total_articles += len(values)
        except Exception as e:
            conn.rollback()
            print(f"❌ 插入数据失败 ({json_file.name}): {e}")
    
    return total_articles


def sync_missing_batches(use_local: bool = True, dry_run: bool = False):
    """
    智能同步缺失的批次数据
    
    Args:
        use_local: True 使用本地数据库，False 使用 Supabase
        dry_run: True 只显示缺失批次，不实际导入
    """
    db_config = get_db_config(use_local)
    db_type = "本地 PostgreSQL" if use_local else "Supabase 云"
    
    print("="*60)
    print("智能增量同步工具")
    print(f"📍 目标数据库: {db_type}")
    print("="*60)
    
    # 连接数据库
    try:
        conn = psycopg2.connect(**db_config)
        print("✅ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return
    
    # 获取已有批次
    existing_batches = get_existing_batch_ids(conn)
    print(f"\n📊 数据库中已有 {len(existing_batches)} 个批次")
    
    # 获取文件系统中的批次
    fs_batches = get_file_system_batch_ids()
    print(f"📂 文件系统中共有 {len(fs_batches)} 个批次")
    
    # 计算缺失的批次
    missing_batches = [b for b in fs_batches if b not in existing_batches]
    
    if not missing_batches:
        print("\n✅ 数据库已是最新，无需同步！")
        conn.close()
        return
    
    print(f"\n🔍 发现 {len(missing_batches)} 个缺失批次:")
    for batch in missing_batches:
        print(f"   - {batch}")
    
    if dry_run:
        print("\n📋 [预览模式] 未执行实际导入")
        conn.close()
        return
    
    # 开始导入缺失批次
    print(f"\n{'='*60}")
    print("开始导入缺失批次...")
    print(f"{'='*60}")
    
    total_batches = 0
    total_articles = 0
    
    for batch_id in missing_batches:
        print(f"\n📦 处理批次: {batch_id}")
        count = import_batch_folder(conn, batch_id)
        if count > 0:
            total_batches += 1
            total_articles += count
            print(f"   ✅ 导入 {count} 条新闻")
        else:
            print(f"   ⚠️  无数据或导入失败")
    
    conn.close()
    
    print(f"\n{'='*60}")
    print("✅ 智能同步完成！")
    print(f"   - 同步批次: {total_batches} 个")
    print(f"   - 导入新闻: {total_articles} 条")
    print(f"{'='*60}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='智能增量同步 - 只导入数据库中缺失的批次')
    parser.add_argument('--cloud', action='store_true', help='使用 Supabase 云数据库（默认使用本地）')
    parser.add_argument('--dry-run', action='store_true', help='预览模式：只显示缺失批次，不实际导入')
    
    args = parser.parse_args()
    
    sync_missing_batches(use_local=not args.cloud, dry_run=args.dry_run)
