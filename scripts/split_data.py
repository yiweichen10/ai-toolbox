#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据化整为零：将单体 data/tools.json / data/articles.json 拆分为每实体一个文件。

输出：
  data/tools/<slug>.json      每个文件 = 单个工具 dict
  data/articles/<slug>.json   每个文件 = 单篇文章 dict

约定：
  - 文件命名用记录自身的 slug 字段（slug 唯一且永久，URL 不变）。
  - 已存在的小文件会被覆盖（幂等，可重跑）。
  - build.py 加载器目录优先：存在 data/tools/ 且非空则聚合目录，否则回退单体。

用法：
  python scripts/split_data.py            # 拆分 tools + articles
  python scripts/split_data.py --dry-run  # 只统计，不写文件
"""
import os
import sys
import json
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# 非法文件名字符
_SAFE = re.compile(r'[^A-Za-z0-9._-]')


def _safe_filename(slug):
    s = _SAFE.sub('-', str(slug)).strip('-')
    return s or 'unknown'


def split_monolith(monolith_name, out_dir_name, id_key='slug', dry_run=False):
    src = os.path.join(DATA_DIR, monolith_name)
    if not os.path.isfile(src):
        print(f'[SKIP] {monolith_name} 不存在')
        return 0, 0

    try:
        data = json.load(open(src, 'r', encoding='utf-8'))
    except Exception as e:
        print(f'[ERR] 读取 {monolith_name} 失败: {e}')
        return 0, 0

    if not isinstance(data, list):
        print(f'[ERR] {monolith_name} 不是数组 (类型={type(data).__name__})')
        return 0, 0

    out_dir = os.path.join(DATA_DIR, out_dir_name)
    n_ok = 0
    n_skip = 0
    seen = set()
    for item in data:
        if not isinstance(item, dict):
            n_skip += 1
            continue
        slug = item.get(id_key)
        if not slug:
            n_skip += 1
            continue
        fname = _safe_filename(slug) + '.json'
        if fname in seen:
            # slug 冲突（理论不应有，validate_data 已查），跳过避免互相覆盖
            print(f'  [WARN] 重复 slug 跳过: {slug}')
            n_skip += 1
            continue
        seen.add(fname)
        if not dry_run:
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, fname), 'w', encoding='utf-8') as f:
                json.dump(item, f, ensure_ascii=False, indent=2)
        n_ok += 1

    if not dry_run:
        os.makedirs(out_dir, exist_ok=True)
    print(f'[{"DRY" if dry_run else "OK"}] {monolith_name} -> {out_dir_name}/ : {n_ok} 文件, {n_skip} 跳过(无slug/非dict/冲突)')
    return n_ok, n_skip


if __name__ == '__main__':
    dry = '--dry-run' in sys.argv
    print('=== 数据化整为零 (split_data.py) ===')
    if dry:
        print('[DRY-RUN] 仅统计，不写文件')
    t_ok, t_skip = split_monolith('tools.json', 'tools', dry_run=dry)
    a_ok, a_skip = split_monolith('articles.json', 'articles', dry_run=dry)
    print(f'\n汇总: tools={t_ok} articles={a_ok} (跳过 tools={t_skip} articles={a_skip})')
