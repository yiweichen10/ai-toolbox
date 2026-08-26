#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drip_publish.py - 每日滴灌发布
从 new_tools_*.json 队列中取 N 条（默认 5），合并到 tools.json，然后自动发布上线。
用法：
  python scripts/drip_publish.py [--count 5] [--dry-run] [--skip-deploy]
  python scripts/drip_publish.py --count 8          # 发布 8 条
  python scripts/drip_publish.py --dry-run          # 预览不执行
"""
import json
import os
import re
import sys
import random
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CST = timezone(timedelta(hours=8))

# 采集产物的 category 简码 → tools.json 中文分类
CATEGORY_MAP = {
    'agent':       'AI智能体',
    'automation':  'AI自动化',
    'browser':     'AI自动化',
    'coding':      'AI编程',
    'video-3d':    'AI视频',
    'embodied':    'AI行业应用',
    'robot':       'AI行业应用',
    'content':     'AI写作',
    'writing':     'AI写作',
    'design':      'AI设计',
    'image':       'AI绘画',
    'model':       'AI对话',
    'chat':        'AI对话',
    'audio':       'AI音频',
    'music':       'AI音频',
    'voice':       'AI音频',
    'office':      'AI办公',
    'search':      'AI搜索',
    'translation': 'AI翻译',
    'efficiency':  'AI效率',
    'dev':         'AI开发',
    'development': 'AI开发',
    'legal':       'AI行业应用',
    'medical':     'AI行业应用',
    'finance':     'AI行业应用',
    'education':   'AI行业应用',
    'recruitment': 'AI行业应用',
    'customer-service': 'AI行业应用',
    'security':    'AI行业应用',
    'learning':    'AI学习',
    'learn':       'AI学习',
    'course':      'AI学习',
    'detection':   'AI检测',
    'detector':    'AI检测',
    'ai-check':    'AI检测',
    'humanize':    'AI检测',
    'prompt':      'AI提示词',
    'prompting':   'AI提示词',
    'web3':        '去中心化AI',
    'decentralized': '去中心化AI',
    'depin':       '去中心化AI',
    'crypto-ai':   '去中心化AI',
    'other':       'AI效率',
}
FALLBACK_CAT = 'AI效率'

# 19 个顶层类目中文名（classification_rules.json 权威），中文类目直通入库
VALID_CATEGORIES = {
    'AI对话', 'AI写作', 'AI绘画', 'AI编程', 'AI视频', 'AI音频', 'AI办公',
    'AI设计', 'AI搜索', 'AI翻译', 'AI自动化', 'AI效率', 'AI智能体', 'AI开发',
    'AI行业应用', 'AI学习', 'AI检测', 'AI提示词', '去中心化AI',
}

# 新建工具的必填默认值
EMOJI_POOL = ['🤖','✨','🚀','💡','🔧','⚡','🎯','🔥','💎','🌟','🛠️','📡','🎭','🧩','🔮']
COLOR_POOL = ['#3b82f6','#8b5cf6','#10b981','#f59e0b','#ef4444','#ec4899','#6366f1',
              '#14b8a6','#f97316','#0ea5e9','#a855f7','#4f46e5','#06b6d4','#22c55e','#e11d48']


def slugify(name):
    s = name.strip().lower()
    s = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '-', s)
    s = s.strip('-')
    return s or name.strip().replace(' ', '-').lower()


def map_category(raw_cat):
    if not raw_cat:
        return FALLBACK_CAT
    stripped = raw_cat.strip()
    # 中文类目名直通（采集产物 category 已是 19 个顶层类目中文名）
    if stripped in VALID_CATEGORIES:
        return stripped
    # 英文简码兼容（转小写匹配）
    return CATEGORY_MAP.get(stripped.lower(), FALLBACK_CAT)


def new_tool_to_entry(t, idx):
    """把采集产物的 tool 对象转为 tools.json 格式。"""
    cat = map_category(t.get('category', ''))
    slug = slugify(t.get('name', ''))
    # 避免 slug 冲突：追加后缀
    # （会在 merge 阶段真正检测重名）

    return {
        'name': t.get('name', ''),
        'slug': slug,
        'emoji': random.choice(EMOJI_POOL),
        'color': random.choice(COLOR_POOL),
        'description': t.get('description', ''),
        'category': cat,
        'subcategory': None,
        'tags': [],
        'rating': round(random.uniform(3.5, 4.5), 1),
        'visits': f'{random.randint(200, 5000)}',
        'badge': {'type': 'new', 'text': 'NEW'},
        'url': t.get('url', ''),
        'price': None,
        'platform': None,
        'created_date': datetime.now(CST).strftime('%Y-%m-%d'),
        'published': True,
        '_source': t.get('source', ''),
        '_heat_signal': t.get('heat_signal', ''),
        '_confidence': t.get('confidence', 'medium'),
    }


def find_queue_files():
    files = []
    for f in os.listdir(os.path.join(BASE_DIR, 'data')):
        if f.startswith('new_tools_') and f.endswith('.json'):
            files.append(os.path.join(BASE_DIR, 'data', f))
    return sorted(files)


def load_queue():
    """加载所有待发布队列，返回 tools 列表 + 每个 tool 的源文件映射。"""
    entries = []
    source_map = {}
    for fp in find_queue_files():
        try:
            data = json.load(open(fp, 'r', encoding='utf-8'))
            if isinstance(data, list):
                for t in data:
                    entries.append(t)
                    source_map[id(t)] = fp
        except Exception as e:
            print(f'[WARN] 无法读取 {fp}: {e}')
    return entries, source_map


def unique_slug(slug_base, existing_slugs):
    """防止 slug 重名。"""
    if slug_base not in existing_slugs:
        return slug_base
    i = 2
    while f'{slug_base}-{i}' in existing_slugs:
        i += 1
    return f'{slug_base}-{i}'


def merge_tools(tools_json, new_entries, count):
    """把 new_entries 的前 count 条合并进工具库，返回 (updated_tools, published_ids, skipped_ids)。
    skipped_ids 包含因重复被跳过的条目，后续也应从队列中清理。
    2026-08-26 去单体化: 真源为分片 data/tools/*.json, 单体 tools.json 已退役。"""
    from data_store import load_all_tools, save_tools_batch
    tools = load_all_tools()
    existing_slugs = {t.get('slug', '') for t in tools}
    existing_names = {t.get('name', '').strip().lower() for t in tools}
    published = []
    skipped = []
    used_names = set()

    for idx, raw in enumerate(new_entries):
        if len(published) >= count:
            break

        name = raw.get('name', '').strip()
        if name.lower() in existing_names:
            print(f'  [SKIP] {name} — 已存在，跳过')
            skipped.append(raw)
            continue

        entry = new_tool_to_entry(raw, idx)
        entry['slug'] = unique_slug(entry['slug'], existing_slugs)
        existing_slugs.add(entry['slug'])
        existing_names.add(name.lower())

        tools.append(entry)
        published.append(entry)
        used_names.add(name.lower())
        print(f'  [ADD]  {name} → {entry["category"]}  ({entry["rating"]}★, {entry["visits"]}次)')

    if published:
        # 2026-08-26: 只写分片(新增的每个工具一个文件), 不写单体
        n = 0
        for e in published:
            from data_store import save_tool
            save_tool(e, indent=2)
            n += 1
        print(f'\n[OK] 分片已更新 (+{n} 条新工具分片, 库共 {len(tools)} 条)')
    else:
        print(f'\n[OK] 无变更 (队列中被跳过或全部重复)')

    # 已存在 + 已发布的都要从队列清理（用 name 做 key，因为 JSON 反序列化后 id() 会变）
    for s in skipped:
        used_names.add(s.get('name', '').strip().lower())

    return tools, used_names


def trim_queue(source_map, used_names):
    """从队列文件中移除已发布/已去重的工具（按 name 匹配）。"""
    for fp in set(source_map.values()):
        data = json.load(open(fp, 'r', encoding='utf-8'))
        new_data = [t for t in data if t.get('name', '').strip().lower() not in used_names]
        removed = len(data) - len(new_data)
        if removed > 0:
            json.dump(new_data, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            print(f'[PRUNE] {os.path.basename(fp)}: {len(data)} → {len(new_data)} (移 {removed})')


def main():
    count = 5
    dry_run = False
    skip_deploy = False
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--count' and i + 1 < len(args):
            count = int(args[i+1]); i += 2
        elif args[i] == '--dry-run':
            dry_run = True; i += 1
        elif args[i] == '--skip-deploy':
            skip_deploy = True; i += 1
        else:
            print(f'未知参数: {args[i]}'); sys.exit(1)

    entries, source_map = load_queue()
    total = len(entries)
    print(f'📋 待发布队列: {total} 条, 本次发布 {min(count, total)} 条')

    if total == 0:
        print('队列为空，无需操作。')
        return

    if dry_run:
        print('--- 预览（不执行）---')
        for idx, raw in enumerate(entries[:count]):
            cat = map_category(raw.get('category', ''))
            print(f'  [{idx+1}] {raw.get("name")} → {cat}')
        return

    # 2026-08-26 去单体化: 单体已退役, 无需备份单体; 直接合并写分片
    _, used_names = merge_tools(None, entries, count)
    trim_queue(source_map, used_names)

    # 刷新工具数据
    print('\n🔄 刷新 js/tools-data.js...')
    regen_script = os.path.join(BASE_DIR, 'scripts', 'regen_tools_data.py')
    if os.path.exists(regen_script):
        os.system(f'cd "{BASE_DIR}" && python "{regen_script}"')
    else:
        print('[WARN] regen_tools_data.py 未找到，跳过')

    if not skip_deploy:
        print('\n🚀 部署上线...')
        deploy_script = os.path.join(BASE_DIR, 'deploy.sh')
        os.system(f'cd "{BASE_DIR}" && bash "{deploy_script}" --skip-build')
    else:
        print('\n⏩ 跳过部署（--skip-deploy）')


if __name__ == '__main__':
    main()
