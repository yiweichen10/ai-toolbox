#!/usr/bin/env python3
"""检查已构建HTML中的内链死链"""
import json, os, re, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

with open(os.path.join(DATA_DIR, 'tools.json'), encoding='utf-8') as f:
    tools = json.load(f)

published_slugs = {t['slug'] for t in tools if t.get('published', False)}
print(f'已发布工具数: {len(published_slugs)}')

dead_links = []
total_dead = 0

# 1. 检查工具页
tool_pages_dir = os.path.join(BASE_DIR, 'tools')
checked_tools = 0
for slug in published_slugs:
    html_path = os.path.join(tool_pages_dir, slug, 'index.html')
    if not os.path.exists(html_path):
        continue
    checked_tools += 1
    with open(html_path, encoding='utf-8') as f:
        content = f.read()
    # 找所有 /tools/xxx 链接 (绝对URL和相对URL)
    links = re.findall(r'href=["\']https?://www\.aitoolbox\.hk/tools/([^/"\'\s>#]+)', content)
    links += re.findall(r'href=["\']/tools/([^/"\'\s>#]+)', content)
    for link_slug in set(links):
        if link_slug not in published_slugs:
            dead_links.append(('tool', slug, link_slug))
            total_dead += 1

print(f'已检查工具页: {checked_tools}')
print(f'工具页死链数: {len([d for d in dead_links if d[0]=="tool"])}')

# 2. 检查文章页
articles_dir = os.path.join(BASE_DIR, 'articles')
checked_articles = 0
if os.path.exists(articles_dir):
    for root, dirs, files in os.walk(articles_dir):
        for fname in files:
            if fname != 'index.html':
                continue
            fpath = os.path.join(root, fname)
            checked_articles += 1
            rel = os.path.relpath(fpath, articles_dir).replace('\\', '/')
            with open(fpath, encoding='utf-8') as f:
                content = f.read()
            links = re.findall(r'href=["\']https?://www\.aitoolbox\.hk/tools/([^/"\'\s>#]+)', content)
            links += re.findall(r'href=["\']/tools/([^/"\'\s>#]+)', content)
            for link_slug in set(links):
                if link_slug not in published_slugs:
                    dead_links.append(('article', rel, link_slug))
                    total_dead += 1

print(f'已检查文章页: {checked_articles}')
print(f'文章页死链数: {len([d for d in dead_links if d[0]=="article"])}')
print(f'\n总计死链: {total_dead}')
print('=' * 80)

# 按死链目标分组，显示影响范围
from collections import Counter
dead_slug_counts = Counter(d[2] for d in dead_links)
print(f'\n死链目标（按出现次数排序）:')
for slug, count in dead_slug_counts.most_common():
    # 找到对应的工具名
    matching_tools = [t for t in tools if t['slug'] == slug]
    name = matching_tools[0]['name'] if matching_tools else '(未找到工具)'
    published = matching_tools[0].get('published', False) if matching_tools else False
    # 查找可能的正确slug
    similar = [t for t in tools if slug in t['slug'].lower() or t['slug'] in slug.lower()]
    similar_names = ', '.join(f"{t['slug']}" for t in similar[:3]) if similar else '无'
    print(f'  /tools/{slug} -> "{name}" (已发布:{published}, 相似slug: {similar_names})')

print(f'\n详细死链列表:')
for src_type, src, dead_slug in dead_links:
    print(f'  [{src_type}] {src} -> /tools/{dead_slug}')
