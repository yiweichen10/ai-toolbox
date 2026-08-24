# -*- coding: utf-8 -*-
"""把 7 个 Web3×AI 工具从 web3-ai-tools.json 合并进 tools.json（published=True + 已核实）"""
import json, io, sys
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = __file__.rsplit('\\', 2)[0]
P = BASE + '/data/tools.json'
SRC = BASE + '/web3-ai-tools.json'

today = datetime.now().strftime('%Y-%m-%d')

# slug → 补充字段（url/category/rating/badge）
META = {
    'gensyn':          {'url': 'https://gensyn.foundation',      'category': '去中心化AI', 'rating': '⭐ 4.2'},
    'io-net':          {'url': 'https://io.net',                 'category': '去中心化AI', 'rating': '⭐ 4.3'},
    'grass':           {'url': 'https://www.getgrass.io',        'category': '去中心化AI', 'rating': '⭐ 4.1'},
    'sapien':          {'url': 'https://sapien.io',              'category': '去中心化AI', 'rating': '⭐ 4.0'},
    'near-ai':         {'url': 'https://near.ai',                'category': '去中心化AI', 'rating': '⭐ 4.4'},
    'prime-intellect': {'url': 'https://www.primeintellect.ai',  'category': 'AI开发',   'rating': '⭐ 4.5'},
    'subquery':        {'url': 'https://subquery.network',       'category': 'AI开发',   'rating': '⭐ 4.0'},
}

data = json.load(open(P, encoding='utf-8'))
existing = {x['slug'] for x in data}
new_tools = json.load(open(SRC, encoding='utf-8'))

added = []
for t in new_tools:
    slug = t['slug']
    if slug in existing:
        print(f'⚠️ slug 已存在，跳过: {slug}')
        continue
    m = META[slug]
    t.update({
        'url': m['url'],
        'category': m['category'],
        'rating': m['rating'],
        'visits': '暂无数据',
        'published': True,
        'content_verified': True,
        'confidence': 'high',
        'last_verified': today,
        'published_date': today,
        'created_date': today,
        'badge': None,
    })
    data.append(t)
    added.append(slug)

json.dump(data, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

# 校验
d2 = json.load(open(P, encoding='utf-8'))
by = {x['slug']: x for x in d2}
print(f'已追加 {len(added)} 个工具: {added}')
print(f'tools.json 总数: {len(d2)}')
for s in added:
    x = by[s]
    print(f'  {s}: category={x["category"]}, published={x["published"]}, cv={x["content_verified"]}, content={len(x["content"])}字')
