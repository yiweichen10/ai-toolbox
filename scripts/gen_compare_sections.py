#!/usr/bin/env python3
"""
gen_compare_sections.py — 为已核查工具生成 A-vs-B 竞品对比小节

设计原则:
  - 仅基于【已核查】数据生成, 避免拿未核实信息做对比(不产生新幻觉)。
  - 竞品取同分类 Top3: 优先用 related(已是有效slug)中同分类者, 不足则从同分类按 visits 补。
  - 结论(verdict)由真实字段数据驱动推导(性价比/口碑/功能数), 不编造主观断言。
  - 产出存 tools.json 的 `compare_section` 字段; build.py 据此渲染实时对比表。

用法:
  python scripts/gen_compare_sections.py            # 全量重算(仅填已核查工具)
  python scripts/gen_compare_sections.py --dry-run  # 预览不写盘
  python scripts/gen_compare_sections.py --slug chatgpt  # 单工具
"""
import json
import os
import re
import argparse
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_JSON = os.path.join(BASE_DIR, 'data', 'tools.json')
TODAY = datetime.now().strftime('%Y-%m-%d')

KNOWN_CATS = {'AI编程','AI开发','AI对话','AI视频','AI效率','AI设计','AI办公',
              'AI行业应用','AI绘画','AI音频','AI写作','AI智能体','AI搜索','AI自动化','AI翻译'}


def load_tools():
    with open(TOOLS_JSON, encoding='utf-8') as f:
        return json.load(f)


def price_num(s):
    """从 price 字符串提首个金额数字(带币种权重: ¥/￥/元=CNY, €=EUR, $/USD), 免费=0。"""
    if not s:
        return None, None
    s = str(s)
    if '免费' in s or s.strip().lower() in ('free', 'free版'):
        return 0.0, 'CNY'
    m = re.search(r'([¥￥]|\$|€|£)\s*([\d,]+(?:\.\d+)?)', s)
    if not m:
        m2 = re.search(r'([\d,]+(?:\.\d+)?)\s*(?:元|人民币|美元|欧元|RMB)', s)
        if not m2:
            return None, None
        num = float(m2.group(1).replace(',', ''))
        cur = 'CNY' if ('元' in s or '人民币' in s or 'RMB' in s) else 'USD'
        return num, cur
    sym = m.group(1)
    num = float(m.group(2).replace(',', ''))
    cur = {'¥': 'CNY', '￥': 'CNY', '$': 'USD', '€': 'EUR', '£': 'GBP'}.get(sym, 'USD')
    return num, cur


def rating_num(s):
    if not s:
        return None
    m = re.search(r'[\d.]+', str(s))
    return float(m.group()) if m else None


def visits_num(s):
    """解析 visits: 支持 '5.9万' / '12k' / '12345'。"""
    if not s:
        return 0
    s = str(s).strip()
    try:
        if '万' in s:
            return int(float(s.replace('万', '')) * 10000)
        if 'k' in s.lower():
            return int(float(re.sub(r'[kK]', '', s)) * 1000)
        return int(float(re.sub(r'[^\d.]', '', s) or 0))
    except ValueError:
        return 0


def is_verified(t):
    return bool(t.get('content_verified')) or bool(t.get('price_verified'))


def pick_competitors(tool, tool_map, slug_list):
    """仅从【已核查】竞品中选取, 保证对比基于核实数据。优先同分类, 不足补 related 中已核查异分类。"""
    slug = tool['slug']
    cat = tool.get('category', '')
    # 同分类且已核查的竞品, 按 visits 降序
    cand = [s for s in slug_list if s != slug
            and tool_map[s].get('category') == cat and is_verified(tool_map[s])]
    cand.sort(key=lambda s: -visits_num(tool_map[s].get('visits', '0')))
    comps = cand[:3]
    # 不足3: 用 related 中已核查的异分类补
    if len(comps) < 3:
        rel = [r for r in (tool.get('related') or [])
               if r in tool_map and r != slug and is_verified(tool_map[r]) and r not in comps]
        rel.sort(key=lambda s: -visits_num(tool_map[s].get('visits', '0')))
        comps += rel[:3 - len(comps)]
    return comps[:3]


def build_verdict(tool, comps, tool_map):
    group = [tool] + comps
    # 性价比: 最便宜(含免费)
    priced = [(t, price_num(t.get('price', ''))) for t in group]
    priced_valid = [(t, p) for t, (p, c) in priced if p is not None]
    cheapest = min(priced_valid, key=lambda x: x[1])[0] if priced_valid else None
    # 口碑: 评分最高
    rated = [(t, rating_num(t.get('rating', ''))) for t in group]
    rated_valid = [(t, r) for t, r in rated if r is not None]
    top_rated = max(rated_valid, key=lambda x: x[1])[0] if rated_valid else None
    # 功能数
    feat_counts = [(t, len(t.get('features') or [])) for t in group]
    most_feat = max(feat_counts, key=lambda x: x[1])[0] if feat_counts else None

    comp_names = '、'.join(tool_map[c]['name'] for c in [x['slug'] for x in comps])
    cat = tool.get('category', '')
    parts = [f"{tool['name']} 与 {comp_names} 同属{cat}赛道。"]

    if cheapest and cheapest['slug'] != tool['slug']:
        parts.append(f"若优先性价比，{cheapest['name']}（{cheapest.get('price','')}）门槛更低；")
    elif cheapest:
        parts.append(f"在性价比上，{cheapest['name']}（{cheapest.get('price','')}）门槛更低；")

    if top_rated and top_rated['slug'] != tool['slug']:
        parts.append(f"若看重口碑，{top_rated['name']}（{top_rated.get('rating','')}）评分更高；")
    elif top_rated:
        parts.append(f"口碑方面，{top_rated['name']}（{top_rated.get('rating','')}）领先；")

    pos = tool.get('positioning') or tool.get('verified_what') or tool.get('description', '')
    pos = pos[:60] if pos else '其差异化定位'
    parts.append(f"{tool['name']} 的优势在于{pos}，适合看重该特性的用户。")
    return ''.join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--slug', help='仅处理单个工具')
    args = ap.parse_args()

    tools = load_tools()
    tool_map = {t['slug']: t for t in tools}
    slug_list = [t['slug'] for t in tools]

    made = 0
    skipped = 0
    for tool in tools:
        if args.slug and tool['slug'] != args.slug:
            continue
        slug = tool['slug']
        # 门槛: 本工具已核查 + 至少2个竞品已核查
        if not is_verified(tool):
            skipped += 1
            continue
        comps = pick_competitors(tool, tool_map, slug_list)
        verified_comps = [c for c in comps if is_verified(tool_map[c])]
        if len(verified_comps) < 2:
            tool['compare_section'] = None
            skipped += 1
            continue
        verdict = build_verdict(tool, [tool_map[c] for c in verified_comps], tool_map)
        tool['compare_section'] = {
            'competitors': verified_comps,
            'verdict': verdict,
            'generated': TODAY,
        }
        made += 1

    print(f"[compare] 生成对比小节: {made} 个工具; 跳过(未核查/竞品不足): {skipped}")

    if args.dry_run:
        print("[compare] dry-run, 不写盘")
        return
    shutil.copy2(TOOLS_JSON, TOOLS_JSON.replace('.json', f'.{TODAY}.bak'))
    json.dump(tools, open(TOOLS_JSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"[compare] 已写回 {TOOLS_JSON} (备份 tools.{TODAY}.bak)")


if __name__ == '__main__':
    main()
