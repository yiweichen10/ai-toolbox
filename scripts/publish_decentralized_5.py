# -*- coding: utf-8 -*-
"""发布 5 个去中心化 AI 工具（置 published=True + 生成 OG 图）"""
import json, io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(BASE, 'data', 'tools.json')
SLUGS = ['bittensor', 'render-network', 'akash-network', 'elizaos', 'aixbt']

from datetime import datetime
today = datetime.now().strftime('%Y-%m-%d')

data = json.load(open(P, encoding='utf-8'))
to_pub = []
for x in data:
    if x['slug'] in SLUGS:
        x['published'] = True
        if not x.get('published_date'):
            x['published_date'] = today
        if not x.get('created_date'):
            x['created_date'] = today
        to_pub.append(x)
json.dump(data, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('已置 published=True:', [x['slug'] for x in to_pub])

# 生成 OG 图
try:
    from publish_new_tools import generate_tool_og_images
    og_ok, og_skip = generate_tool_og_images(to_pub)
    print(f'OG 图生成: {og_ok} 成功, {og_skip} 跳过')
except Exception as e:
    print('OG 图生成失败(非致命):', e)

# 校验
d2 = json.load(open(P, encoding='utf-8'))
pub = [x for x in d2 if x['slug'] in SLUGS and x.get('published')]
print('校验: 5工具已发布', len(pub), '个')
