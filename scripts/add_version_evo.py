#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
给「同品牌版本型」工具页追加/更新「版本演进对比」小节。

用法:
  python scripts/add_version_evo.py --slug glm-5-2 --facts scripts/_glm_evo.json

facts JSON 结构（由 agent 用 WebSearch 核实后填写，禁止编造）:
{
  "brand": "GLM",
  "improvement_notes": [
    "上下文窗口 200K → 1M 无损（5 倍，且真实可用不劣化）",
    "Terminal-Bench 2.1 63.5 → 81.0（+17.5）"
  ],
  "versions": [
    {"name":"GLM-5.1","date":"2025.4","specs":{"上下文窗口":"200K","Terminal-Bench 2.1":"63.5","SWE-bench Pro":"58.4","Code Arena":"未参评","国产算力 Day 0":"否","推理力度控制":"否"}},
    {"name":"GLM-5.2","date":"2026.6","specs":{"上下文窗口":"1M 无损","Terminal-Bench 2.1":"81.0","SWE-bench Pro":"62.1","Code Arena":"全球可用模型第一","国产算力 Day 0":"华为昇腾/寒武纪等 8 家","推理力度控制":"多档可调"}}
  ]
}

脚本会:
  1. 收集所有版本出现过的 spec 维度，生成对比表
  2. 追加/替换 content 末尾的「## {brand} 版本演进对比」小节
  3. 不改动其它字段，写回 tools.json
"""
import json
import argparse
import sys
import os

TOOLS_JSON = os.path.join(os.path.dirname(__file__), '..', 'data', 'tools.json')
SECTION_TITLE_TMPL = "{} 版本演进对比"


def build_section(brand, versions, notes):
    # 收集所有维度
    dims = []
    for v in versions:
        for k in v.get('specs', {}):
            if k not in dims:
                dims.append(k)
    # 表头
    header = '| 对比维度 | ' + ' | '.join(v['name'] + ('（' + v['date'] + '）' if v.get('date') else '') for v in versions) + ' |'
    sep = '|------|' + '|'.join(['------'] * len(versions)) + '|'
    rows = []
    for d in dims:
        cells = []
        for v in versions:
            cells.append(v.get('specs', {}).get(d, '—'))
        rows.append('| ' + d + ' | ' + ' | '.join(cells) + ' |')
    table = '\n'.join([header, sep] + rows)
    notes_block = ''
    if notes:
        notes_block = '\n\n**主要升级点：**\n' + '\n'.join('- ' + n for n in notes)
    tail = ''
    if len(versions) >= 1:
        latest = versions[-1]['name']
        tail = f'\n\n后续若发布更新代（如 5.3 / 6.0），本小节会持续补充各代差异。'
    return f"\n\n## {SECTION_TITLE_TMPL.format(brand)}\n\n{table}{notes_block}{tail}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug', required=True)
    ap.add_argument('--facts', required=True, help='facts JSON 路径')
    ap.add_argument('--tools', default=TOOLS_JSON)
    args = ap.parse_args()

    facts = json.load(open(args.facts, encoding='utf-8'))
    brand = facts.get('brand', '')
    versions = facts.get('versions', [])
    notes = facts.get('improvement_notes', [])
    if not brand or not versions:
        print('facts 缺少 brand 或 versions，终止')
        sys.exit(1)

    t = json.load(open(args.tools, encoding='utf-8'))
    target = None
    for x in t:
        if x.get('slug') == args.slug:
            target = x
            break
    if not target:
        print('slug', args.slug, '不存在，终止')
        sys.exit(1)

    section = build_section(brand, versions, notes)
    title = '## ' + SECTION_TITLE_TMPL.format(brand)
    content = target.get('content', '')
    # 若已有同品牌小节则替换，否则追加
    if title in content:
        pre = content.split(title)[0].rstrip()
        target['content'] = pre + section
        print('已替换已有版本演进对比小节')
    else:
        target['content'] = content.rstrip() + section
        print('已追加版本演进对比小节')
    target['content'] = target['content'].rstrip() + '\n'

    json.dump(t, open(args.tools, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('saved', args.tools, '| 新 content 长度', len(target['content']))


if __name__ == '__main__':
    main()
