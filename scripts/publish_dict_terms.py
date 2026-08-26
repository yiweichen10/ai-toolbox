#!/usr/bin/env python3
"""每日发布N条AI词典词条（从未发布池中选出）"""
import json
import os
import sys
import argparse
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description='每日发布AI词典词条')
    parser.add_argument('--count', '-n', type=int, default=2,
                        help='本次发布几条（默认2）')
    parser.add_argument('--dry-run', action='store_true',
                        help='仅预览不实际修改')
    args = parser.parse_args()

    sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
    # 2026-08-26 去单体化: 读分片 data/dict_terms/*.json, 写只落分片(单体已退役)
    from data_store import load_all_dict_terms, save_dict_term

    terms = load_all_dict_terms()

    published = [t for t in terms if t.get('published')]
    pending = [t for t in terms if not t.get('published')]

    print(f'已发布: {len(published)} | 待发布: {len(pending)}')

    if not pending:
        print('✅ 所有词条已发布完毕')
        return

    # 按顺序取前N条待发布
    to_publish = pending[:args.count]
    names = [t['term'] for t in to_publish]

    if args.dry_run:
        print(f'[DRY RUN] 将发布: {", ".join(names)}')
        return

    # 标记为已发布并写分片（每个词条一个文件 data/dict_terms/<slug>.json）
    for t in to_publish:
        t['published'] = True
        t['published_date'] = datetime.now().strftime('%Y-%m-%d')
        save_dict_term(t, indent=2)

    print(f'✅ 已发布 {len(to_publish)} 条: {", ".join(names)}')
    print(f'   已发布总量: {len(published) + len(to_publish)} / {len(terms)}')
    print(f'   已写分片 data/dict_terms/<slug>.json')


if __name__ == '__main__':
    main()
