#!/usr/bin/env python3
"""
仅为指定文章或最新文章生成OG图片
用法：
    python gen_single_og.py              # 生成最新文章的OG图片
    python gen_single_og.py <slug>       # 生成指定文章的OG图片
示例：
    python gen_single_og.py claude-code-source-leak-2026
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')

sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from gen_seo_images import make_article_og_image, generate_image
import json

# 读取文章数据
with open(os.path.join(DATA_DIR, 'articles.json'), encoding='utf-8') as f:
    articles = json.load(f)

if not articles:
    print("错误: articles.json 为空")
    sys.exit(1)

# 根据参数决定生成哪篇
if len(sys.argv) > 1:
    slug = sys.argv[1]
    article = next((a for a in articles if a['slug'] == slug), None)
    if not article:
        print(f"错误: 未找到文章 slug={slug}")
        print(f"可用slug: {[a['slug'] for a in articles[:5]]}...")
        sys.exit(1)
else:
    # 默认生成最新一篇
    article = articles[0]
    slug = article['slug']

print(f"为文章生成OG图片: {article['title']}")
print(f"slug: {slug}")

og_path = os.path.join(IMAGES_DIR, 'og', f'{slug}-og.png')

# 检查是否已存在
if os.path.exists(og_path):
    print(f"OG图片已存在: {og_path}")
    print("使用 --force 强制重新生成（暂不支持）")
else:
    print(f"输出: {og_path}")
    og_html = make_article_og_image(article)
    if generate_image(og_html, og_path):
        print("OG图片生成成功!")
    else:
        print("OG图片生成失败!")
        sys.exit(1)