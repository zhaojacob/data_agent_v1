"""查找超长字段的数据"""
import json
from pathlib import Path

base = Path(r'F:\anaconda_projects\financial-news-brief\data_fetcher\pipeline_results\pipeline_raw')

print("搜索 author 字段超过 100 字符的记录...\n")

for batch_folder in sorted(base.iterdir()):
    if not batch_folder.is_dir() or not batch_folder.name.startswith('batch_'):
        continue
    for json_file in batch_folder.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for i, article in enumerate(data.get('articles', [])):
                author = article.get('author', '')
                if author and len(author) > 100:
                    print(f"📁 批次: {batch_folder.name}")
                    print(f"📄 文件: {json_file.name}")
                    print(f"📍 文章索引: {i}")
                    print(f"📰 标题: {article.get('title', '')[:60]}...")
                    print(f"📏 author 长度: {len(author)} 字符")
                    print(f"👤 author 内容:\n   {author}")
                    print("-" * 70)
        except Exception as e:
            print(f"错误: {json_file} - {e}")
