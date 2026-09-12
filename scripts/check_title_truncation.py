#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""标题截断巡检（只读，不改数据）。

背景（2026-09-12）：
`scripts/seo_title_helper.py::gen_positioning()` 对手填 `positioning` 走
`explicit[:30]` 硬切，无语义感知 → 首句超 30 字的工具，title 会断在词中间
（如「…能替代」「…DeepSeek原」「…基础设」）。

本脚本列出所有「会触发硬切」的已发布工具，作为是否做全站 title 引擎修复的
影响面清单。修复动作须另行走数据级（缩短 positioning 至 ≤30 且语义完整）
或引擎级（改为语义边界截断，需全站 title 回归）。

用法：
    python scripts/check_title_truncation.py            # 人读报告
    python scripts/check_title_truncation.py --json     # 机器可读
"""
import os
import sys
import io
import json
import argparse

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from data_store import load_all_tools  # noqa: E402

LIMIT = 30  # 与 gen_positioning 的 explicit[:30] 对齐


def scan():
    hits = []
    for t in load_all_tools():
        if not t.get('published'):
            continue
        pos = (t.get('positioning') or '').strip()
        if len(pos) > LIMIT:
            hits.append({
                'slug': t.get('slug'),
                'name': t.get('name'),
                'positioning_len': len(pos),
                'cut_preview': pos[:LIMIT],
            })
    hits.sort(key=lambda h: -h['positioning_len'])
    return hits


def main():
    ap = argparse.ArgumentParser(description='标题截断巡检（positioning > 30 会被硬切）')
    ap.add_argument('--json', action='store_true', help='输出 JSON')
    args = ap.parse_args()

    hits = scan()
    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
        return

    print(f'已发布工具中 positioning > {LIMIT} 字（title 必被硬切）: {len(hits)} 个')
    print('-' * 72)
    for h in hits:
        print(f"{h['slug']:<34} {h['positioning_len']:>3}  {h['cut_preview']}")
    print('-' * 72)
    print('处理方式：优先数据级——把 positioning 缩到 ≤30 字且首句语义完整；')
    print('          若做引擎级（语义边界截断），须先跑全站 title 回归。')


if __name__ == '__main__':
    main()
