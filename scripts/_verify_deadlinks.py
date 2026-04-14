#!/usr/bin/env python3
import json

BASE_DIR = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site'

with open(f'{BASE_DIR}/data/tools.json', encoding='utf-8') as f:
    tools = json.load(f)

# Check phind
phind = [t for t in tools if t['slug'] == 'phind']
if phind:
    print(f"phind: published={phind[0].get('published')}, name={phind[0]['name']}")
else:
    print('phind: 不在tools.json中')

# Check kling-ai
kling = [t for t in tools if 'kling' in t['slug'].lower()]
for t in kling:
    print(f"kling相关: slug={t['slug']}, published={t.get('published')}, name={t['name']}")

with open(f'{BASE_DIR}/data/articles.json', encoding='utf-8') as f:
    articles = json.load(f)

# Check ai-beginner-tools-0409
art = [a for a in articles if a['slug'] == 'ai-beginner-tools-0409']
if art:
    print(f"ai-beginner-tools-0409: 存在, title={art[0].get('title','')[:50]}")
else:
    print('ai-beginner-tools-0409: 不在articles.json中')
    similar = [a for a in articles if 'beginner' in a['slug'] or '0409' in a['slug']]
    for a in similar:
        print(f"  相似文章slug: {a['slug']}")

# Check if phind HTML exists
import os
phind_html = os.path.join(BASE_DIR, 'tools', 'phind', 'index.html')
print(f"\nphind HTML存在: {os.path.exists(phind_html)}")

# Check if ai-beginner-tools-0409 HTML exists
art_html = os.path.join(BASE_DIR, 'articles', 'ai-beginner-tools-0409', 'index.html')
print(f"ai-beginner-tools-0409 HTML存在: {os.path.exists(art_html)}")

# Count total articles and tools in HTML
tool_count = sum(1 for d in os.listdir(os.path.join(BASE_DIR, 'tools')) if os.path.isdir(os.path.join(BASE_DIR, 'tools', d)))
article_count = 0
articles_dir = os.path.join(BASE_DIR, 'articles')
if os.path.exists(articles_dir):
    for d in os.listdir(articles_dir):
        if os.path.isdir(os.path.join(articles_dir, d)) and d != 'page':
            article_count += 1
print(f"\nHTML中工具目录数: {tool_count}")
print(f"HTML中文章目录数: {article_count}")
print(f"JSON中已发布工具数: {sum(1 for t in tools if t.get('published'))}")
print(f"JSON中文章数: {len(articles)}")
