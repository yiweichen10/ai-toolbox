#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
给文章新增 `topic` 字段（细分主题，对应 19 个工具分类）。
2026-08-30 用户拍板：首页标签=大类(content_type 5种)，列表页卡片=细分主题(topic)。
幂等：topic 已存在且非空则跳过（除非 --force）；可重跑。

优先级：
  1. orig_category 能匹配工具分类（19种）→ 直接用作 topic（人工归并过的值最可信）
  2. 否则从 description+content 提取正文工具名 → 众数工具分类
  3. 否则留空（列表页回退显示 content_type 大类）
"""
import sys, os, re
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_store import load_all_articles, load_all_tools, save_article


def _norm(s):
    return re.sub(r'[^a-z0-9一-\u9fff]', '', str(s).lower())


def derive_topic(a, tool_norms, tool_cats):
    """返回细分主题（19 工具分类之一）或 ''"""
    c = a.get('orig_category', '') or a.get('category', '')
    if c in tool_cats:
        return c
    body = _norm((a.get('description') or '') + ' ' +
                 (a.get('content') or a.get('markdown') or ''))
    cats = [tcat for t, tcat in tool_norms if t and t in body and tcat]
    if cats:
        return Counter(cats).most_common(1)[0][0]
    return ''


def main():
    force = '--force' in sys.argv
    tools = load_all_tools()
    tool_cats = {t.get('category') for t in tools if t.get('category')}
    tool_norms = [(_norm(t.get('name', '')), t.get('category', ''))
                  for t in tools if t.get('published', True)]

    arts = load_all_articles()
    changed = skipped = empty = 0
    dist = Counter()
    for a in arts:
        if a.get('topic') and not force:
            skipped += 1
            dist[a['topic']] += 1
            continue
        topic = derive_topic(a, tool_norms, tool_cats)
        if topic:
            if a.get('topic') != topic:
                a['topic'] = topic
                changed += 1
            dist[topic] += 1
            save_article(a)
        else:
            empty += 1
            if 'topic' in a and not force:
                pass
            elif 'topic' in a:
                del a['topic']
                save_article(a)
            else:
                pass

    print('=== topic 推导完成 ===')
    print(f'  新增/更新: {changed}  已存在跳过: {skipped}  无主题留空: {empty}')
    print('=== topic 分布 ===')
    for k, v in dist.most_common():
        print(f'  {v:3d}  {k}')


if __name__ == '__main__':
    main()
