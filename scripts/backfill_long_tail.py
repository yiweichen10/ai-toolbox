# -*- coding: utf-8 -*-
"""
批量补全 tools.json 的 long_tail 字段（2026-07-25）。

- 仅给「缺失 long_tail」的工具生成，不覆盖已有值（未来人工核实词安全）。
- 生成规则见 seo_title_helper.gen_long_tail：分类意图桶 + 价格/竞品属性。
- 用途：让全站 412 个工具页（含未发布）都带差异化长尾种子，标题引擎不再走兜底。
"""
import json
import os
import sys

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'scripts'))
from data_store import save_tools_batch, save_articles_batch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
TOOLS_JSON = os.path.join(DATA_DIR, 'tools.json')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_title_helper import gen_long_tail


def main():
    tools = load_all_tools()
    slug_map = {t['slug']: t for t in tools if t.get('slug')}
    force = '--force' in sys.argv

    added = 0
    existing = 0
    for t in tools:
        if force or not t.get('long_tail'):
            t['long_tail'] = gen_long_tail(t, slug_map)
            added += 1
        else:
            existing += 1

    save_tools_batch(tools)

    print(f"long_tail 补全完成：新增 {added} 个，已有 {existing} 个，总计 {len(tools)} 个")
    # 抽样展示几个，确认话术自然
    sample = [t for t in tools if t.get('long_tail')][:5]
    for t in sample:
        print(f"  - {t['name']} ({t['category']}) -> {t['long_tail']}")


if __name__ == '__main__':
    main()
