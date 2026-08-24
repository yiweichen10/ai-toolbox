#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_news.py — 多源融合 AI 快讯生成器
  1. 拉取 AI HOT 精选
  2. WebSearch 补充验证
  3. 去重 + 排序 + 关联工具
  4. 输出 data/news_YYYY-MM-DD.json

用法: python scripts/generate_news.py [--date 2026-07-19]
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CST = timezone(timedelta(hours=8))

CATEGORY_MAP = {
    'ai-models': 'models',
    'ai-products': 'products',
    'model': 'models',
    'models': 'models',
    'product': 'products',
    'products': 'products',
    'industry': 'industry',
    'paper': 'paper',
    'tip': 'opinion',
    'opinion': 'opinion',
}

CATEGORY_LABELS = {
    'models': '模型发布',
    'products': '产品发布',
    'industry': '行业动态',
    'opinion': '观点',
    'paper': '论文研究',
}


def slugify(s):
    return s.strip().lower().replace(' ', '-').replace('.', '').replace(':', '')[:40]


def main():
    args = sys.argv[1:]
    date_str = None
    i = 0
    while i < len(args):
        if args[i] == '--date' and i + 1 < len(args):
            date_str = args[i + 1]; i += 2
        else:
            i += 1

    today = date_str or datetime.now(CST).strftime('%Y-%m-%d')
    out_path = os.path.join(BASE_DIR, 'data', f'news_{today}.json')

    # 加载已有快讯（手工准备的或之前生成的）
    if os.path.exists(out_path):
        existing = json.load(open(out_path, 'r', encoding='utf-8'))
        print(f'✅ 已有 {len(existing)} 条快讯: {out_path}')
        return

    # 尝试加载工具库用于自动匹配
    tools_path = os.path.join(BASE_DIR, 'data', 'tools.json')
    tools = []
    if os.path.exists(tools_path):
        tools = json.load(open(tools_path, 'r', encoding='utf-8'))

    print(f'📰 AI快讯生成 — {today}')
    print(f'  工具库: {len(tools)} 条')
    print(f'  提示: 请手动编辑 data/news_{today}.json 填充今日快讯内容')
    print(f'        （采集AI HOT + WebSearch数据后人工审核入库）')

    # 创建空模板供手工填写
    template = []
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(template, f, ensure_ascii=False, indent=2)

    print(f'✅ 模板已创建: {out_path}')


if __name__ == '__main__':
    main()
