#!/usr/bin/env python3
"""全站HTML死链扫描 - 检查所有HTML文件中的内链"""
import json, re, os
from collections import Counter

BASE_DIR = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site'

with open(f'{BASE_DIR}/data/tools.json', encoding='utf-8') as f:
    tools = json.load(f)
published_slugs = {t['slug'] for t in tools if t.get('published', False)}
all_slugs = {t['slug'] for t in tools}

# 收集所有articles slug
with open(f'{BASE_DIR}/data/articles.json', encoding='utf-8') as f:
    articles = json.load(f)
article_slugs = {a['slug'] for a in articles}

dead_links = []
all_internal = []

# 扫描所有HTML文件
for root, dirs, files in os.walk(BASE_DIR):
    # 跳过特定目录
    dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', 'scripts', '.workbuddy', '.codebuddy', 'images', '_archive']]
    for fname in files:
        if not fname.endswith('.html'):
            continue
        fpath = os.path.join(root, fname)
        rel = os.path.relpath(fpath, BASE_DIR).replace('\\', '/')
        try:
            with open(fpath, encoding='utf-8') as f:
                content = f.read()
        except:
            continue
        
        # 查找 /tools/xxx 链接
        tool_links = re.findall(r'href=["\'](?:https?://www\.aitoolbox\.hk)?/tools/([a-z0-9][a-z0-9-]*)(?:/|#|["\'])', content)
        for slug in set(tool_links):
            target = f'/tools/{slug}'
            all_internal.append((rel, target))
            if slug not in all_slugs:
                dead_links.append((rel, target, '工具slug不存在'))
            elif slug not in published_slugs:
                dead_links.append((rel, target, '工具未发布'))
        
        # 查找 /articles/xxx 链接
        art_links = re.findall(r'href=["\'](?:https?://www\.aitoolbox\.hk)?/articles/([a-z0-9][a-z0-9-]*)(?:/|#|["\'])', content)
        for slug in set(art_links):
            target = f'/articles/{slug}'
            all_internal.append((rel, target))
            if slug not in article_slugs:
                dead_links.append((rel, target, '文章slug不存在'))

# 按类型统计
tool_dead = [d for d in dead_links if d[1].startswith('/tools/')]
art_dead = [d for d in dead_links if d[1].startswith('/articles/')]

print(f'全站HTML扫描结果:')
print(f'  总内链数: {len(all_internal)}')
print(f'  死链数: {len(dead_links)}')
print(f'    工具死链: {len(tool_dead)}')
print(f'    文章死链: {len(art_dead)}')

if dead_links:
    print(f'\n{"="*80}')
    print('死链详情（按目标URL分组）:')
    dead_by_target = Counter(d[1] for d in dead_links)
    for target, count in dead_by_target.most_common():
        sources = [d[0] for d in dead_links if d[1] == target]
        reason = [d[2] for d in dead_links if d[1] == target][0]
        print(f'\n  {target} ({reason}) - 被{count}个页面引用:')
        for src in sources[:5]:
            print(f'    <- {src}')
        if len(sources) > 5:
            print(f'    ... 还有{len(sources)-5}个')
    
    print(f'\n{"="*80}')
    print('全部死链列表:')
    for src, target, reason in dead_links:
        print(f'  {src} -> {target} ({reason})')
