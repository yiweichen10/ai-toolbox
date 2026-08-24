#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regen_tools_data.py - 单独重新生成 js/tools-data.js
无需全量 build.py（不重建 661 个 HTML），只刷新首页 JS 用的工具数据。
适用场景：tools.json 字段变更（如新增 subcategory）、但 HTML 页面不需要重建时。

用法：
  python scripts/regen_tools_data.py
"""
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIGHTWEIGHT_KEYS = {'name', 'slug', 'emoji', 'color', 'description', 'category', 'subcategory',
                    'tags', 'rating', 'visits', 'badge', 'url', 'price', 'platform', 'created_date'}


def tool_icon_path(slug):
    if not slug:
        return ''
    for ext in ('.svg', '.png'):
        if os.path.exists(os.path.join(BASE_DIR, 'assets', 'icons', slug + ext)):
            return f'/assets/icons/{slug}{ext}'
    return ''


def make_lightweight(tool_list):
    out = []
    for t in tool_list:
        d = {k: v for k, v in t.items() if k in LIGHTWEIGHT_KEYS}
        d['icon'] = tool_icon_path(t.get('slug', ''))
        out.append(d)
    return out


def main():
    tools_path = os.path.join(BASE_DIR, 'data', 'tools.json')
    subs_path = os.path.join(BASE_DIR, 'data', 'subcategories.json')
    out_path = os.path.join(BASE_DIR, 'js', 'tools-data.js')

    tools = json.load(open(tools_path, encoding='utf-8'))
    subs = json.load(open(subs_path, encoding='utf-8'))

    # 与 build.py 保持一致：取所有工具的轻量版
    all_tools_json = json.dumps(make_lightweight(tools), ensure_ascii=False, indent=2)
    remaining_tools_json = json.dumps(make_lightweight(tools[8:]), ensure_ascii=False, indent=2)
    subcat_json = json.dumps(subs, ensure_ascii=False, indent=2)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f'window.__ALL_TOOLS__ = {all_tools_json};\n')
        f.write(f'window.__REMAINING_TOOLS__ = {remaining_tools_json};\n')
        f.write(f'window.__SUBCATEGORIES__ = {subcat_json};\n')

    size_kb = os.path.getsize(out_path) // 1024
    sub_cnt = sum(len(p.get('subcats', {})) for p in subs.values())
    has_sub = sum(1 for t in tools if t.get('subcategory'))
    print(f'[OK] js/tools-data.js ({size_kb}KB)  含 subcategory 工具 {has_sub}/{len(tools)}, '
          f'__SUBCATEGORIES__ 覆盖 {sub_cnt} 个子类目')


if __name__ == '__main__':
    main()
