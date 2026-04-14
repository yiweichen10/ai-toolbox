#!/usr/bin/env python3
"""检查JSON数据源中的内链死链"""
import json, re

BASE_DIR = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site'

with open(f'{BASE_DIR}/data/tools.json', encoding='utf-8') as f:
    tools = json.load(f)
published_slugs = {t['slug'] for t in tools if t.get('published', False)}
all_slugs = {t['slug'] for t in tools}

# 1. 检查tools.json content字段中的内链
print('=== tools.json content字段中的内链死链 ===')
tool_dead_count = 0
for t in tools:
    content = t.get('content', '') or ''
    faq_raw = t.get('faq', '') or ''
    faq = json.dumps(faq_raw, ensure_ascii=False) if isinstance(faq_raw, (list, dict)) else str(faq_raw)
    text = content + faq
    links = re.findall(r'/tools/([a-z0-9][a-z0-9-]*)', text)
    for slug in set(links):
        if slug not in all_slugs:
            # 查找相似slug
            matching = [t2 for t2 in tools if slug in t2['slug'].lower() or t2['slug'] in slug.lower()]
            similar = ', '.join(t2['slug'] for t2 in matching[:3]) if matching else '无'
            status = '已发布' if t.get('published') else '未发布'
            print(f'  [{t["slug"]}]{status} -> /tools/{slug} (不存在, 相似: {similar})')
            tool_dead_count += 1
        elif slug != t['slug'] and slug not in published_slugs:
            print(f'  [{t["slug"]}] -> /tools/{slug} (引用了未发布工具)')
            tool_dead_count += 1
print(f'工具content死链数: {tool_dead_count}')

# 2. 检查articles.json中的内链
with open(f'{BASE_DIR}/data/articles.json', encoding='utf-8') as f:
    articles = json.load(f)
print(f'\n=== articles.json中的内链死链 ({len(articles)}篇) ===')
article_dead_count = 0
for a in articles:
    content = a.get('content', '') or ''
    links = re.findall(r'/tools/([a-z0-9][a-z0-9-]*)', content)
    for slug in set(links):
        if slug not in all_slugs:
            matching = [t2 for t2 in tools if slug in t2['slug'].lower() or t2['slug'] in slug.lower()]
            similar = ', '.join(t2['slug'] for t2 in matching[:3]) if matching else '无'
            print(f'  [{a["slug"]}] -> /tools/{slug} (不存在, 相似: {similar})')
            article_dead_count += 1
        elif slug not in published_slugs:
            print(f'  [{a["slug"]}] -> /tools/{slug} (未发布工具)')
            article_dead_count += 1
print(f'文章content死链数: {article_dead_count}')
print(f'\n总计数据源死链: {tool_dead_count + article_dead_count}')
