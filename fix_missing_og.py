#!/usr/bin/env python3
"""为缺失OG图片的文章批量生成OG图片"""
import sys
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')

sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from gen_seo_images import make_article_og_image, generate_image

# 读取文章数据
with open(os.path.join(DATA_DIR, 'articles.json'), encoding='utf-8') as f:
    articles = json.load(f)

# 需要补生成的slug列表
missing_slugs = [
    'ai-video-tools-2026-guide',
    'ai-writing-tools-2026-guide',
    'deepseek-complete-guide-2026',
    'ai-translation-tools-2026-guide',
    'ai-office-productivity-tools-2026',
]

success = 0
failed = 0

for slug in missing_slugs:
    article = next((a for a in articles if a['slug'] == slug), None)
    if not article:
        print(f'[SKIP] slug={slug} not found in articles.json')
        continue

    og_path = os.path.join(IMAGES_DIR, 'og', f'{slug}-og.png')
    if os.path.exists(og_path):
        print(f'[SKIP] {slug} - OG image already exists')
        continue

    print(f'[GEN] {article["title"][:40]}...', flush=True)
    og_html = make_article_og_image(article)
    if generate_image(og_html, og_path):
        print(f'  OK -> {og_path}')
        success += 1
    else:
        print(f'  FAIL')
        failed += 1

print(f'\nDone! Generated: {success}, Failed: {failed}')
