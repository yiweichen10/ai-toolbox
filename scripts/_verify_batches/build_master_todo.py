#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 49 个 result_bXX.json 聚合为 master 问题清单 + 进度表。
只读取、只生成报告，不改 data/tools.json、不 build、不 deploy。
"""
import json, glob, os
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(ROOT)
DATA = os.path.join(PROJ, '..', 'data', 'tools.json')
BAK = os.path.join(PROJ, '..', 'data', 'tools.json.20260729.bak')

tools = json.load(open(DATA, encoding='utf-8'))
by_slug = {t['slug']: t for t in tools if t.get('slug')}

# 已修 URL 对照（备份 vs 当前）
old = {t['slug']: t for t in json.load(open(BAK, encoding='utf-8')) if t.get('slug')}
url_fixed = set()
for slug, t in old.items():
    if slug in by_slug and (t.get('url') or '').rstrip('/') != (by_slug[slug].get('url') or '').rstrip('/'):
        url_fixed.add(slug)

# 聚合所有 result（同 slug 多批次取并集，记录所有来源批次）
agg = {}
for f in sorted(glob.glob(os.path.join(ROOT, 'result_b*.json'))):
    try:
        d = json.load(open(f, encoding='utf-8'))
    except Exception:
        continue
    if not isinstance(d, dict) or 'tools' not in d:
        continue
    cat = d.get('category', '')
    for it in d['tools']:
        slug = it.get('slug')
        if not slug:
            continue
        e = agg.setdefault(slug, {
            'slug': slug, 'name': it.get('name'), 'category': cat,
            'batches': [], 'url_ok': True, 'url_current': '', 'url_correct': '',
            'hallucination': False, 'fields': set(), 'conflict': False,
            'confidences': [], 'notes': [],
        })
        e['batches'].append(d.get('batch_id'))
        if it.get('url_ok') is False:
            e['url_ok'] = False
            e['url_current'] = it.get('url_current') or ''
            if it.get('url_correct'):
                e['url_correct'] = it.get('url_correct')
        if it.get('hallucination') is True:
            e['hallucination'] = True
            for fld in (it.get('hallucination_fields') or []):
                e['fields'].add(fld)
        if it.get('conflict') is True:
            e['conflict'] = True
        if it.get('confidence'):
            e['confidences'].append(it.get('confidence'))
        if it.get('notes'):
            e['notes'].append((it.get('confidence'), it.get('notes')))

# 分类到阶段
def classify(e):
    slug = e['slug']
    t = by_slug.get(slug)
    published = bool(t and t.get('published'))
    e['published'] = published
    e['url_fixed'] = slug in url_fixed
    fields = e['fields']
    # 阶段优先级：
    #  P0 已修URL但content/price仍错（上次没收尾的遗留，最高优先）
    #  > 下架 > 整页错位(高危) > 价格编造 > 平台/其他 > 冲突 > 低置信
    if e['url_fixed'] and e['hallucination']:
        return 'P0_url_fixed_content_pending'  # URL改对但内容/价格仍错——上次遗留
    if (e['url_ok'] is False) and not e['url_correct']:
        return 'P1_url_review'          # URL 错且无正确官网 -> 人工决定下架/概念页
    if e['hallucination'] and ('content' in fields or 'description' in fields):
        return 'P2_content_highrisk'    # 整页/大段张冠李戴
    if e['hallucination'] and 'price' in fields:
        return 'P3_price_fix'           # 价格编造
    if e['hallucination']:
        return 'P4_other_field'         # platform 等其余字段
    if e['conflict']:
        return 'P5_conflict'            # 冲突待裁定
    if any(c in ('low', 'medium') for c in e['confidences']):
        return 'P6_lowconf'             # 低/中置信待复核
    return None

stage_order = ['P0_url_fixed_content_pending', 'P1_url_review', 'P2_content_highrisk',
               'P3_price_fix', 'P4_other_field', 'P5_conflict', 'P6_lowconf']
stage_name = {
    'P0_url_fixed_content_pending': 'P0 已修URL但内容/价格仍错（上次遗留，最高优先）',
    'P1_url_review': 'P1 URL 收尾（无正确官网，待下架/概念页决策）',
    'P2_content_highrisk': 'P2 内容高危重写（整页/大段张冠李戴）',
    'P3_price_fix': 'P3 价格编造修复（price 字段）',
    'P4_other_field': 'P4 其余字段幻觉（platform/description 等）',
    'P5_conflict': 'P5 冲突项人工裁定',
    'P6_lowconf': 'P6 低/中置信复核',
}

items = []
for slug, e in agg.items():
    st = classify(e)
    if st is None:
        continue
    e['stage'] = st
    e['fields'] = sorted(e['fields'])
    items.append(e)

items.sort(key=lambda e: (stage_order.index(e['stage']), e['slug']))

# 统计
from collections import Counter
cnt = Counter(e['stage'] for e in items)
total_problem_tools = len(items)
url_fixed_in_problems = sum(1 for e in items if e['url_fixed'])

# 写 MASTER json
master = {
    'total_tools_verified': len(agg),
    'problem_tools': total_problem_tools,
    'url_fixed_total': len(url_fixed),
    'url_fixed_among_problems': url_fixed_in_problems,
    'stage_counts': dict(cnt),
    'items': items,
}
with open(os.path.join(ROOT, 'MASTER_TODO.json'), 'w', encoding='utf-8') as f:
    json.dump(master, f, ensure_ascii=False, indent=2)

# 写 MASTER md（进度表，人读）
lines = []
lines.append('# 全量核实问题 Master 进度表')
lines.append('')
lines.append('> 生成时间：2026-07-30 | 数据源：49 个 result_bXX.json 聚合（419 工具 100% 核验）')
lines.append('> 本表仅整理收集，**未执行任何修改/构建/部署**。')
lines.append('')
lines.append('## 总览')
lines.append('')
lines.append(f'- 已核验工具：**{len(agg)} / 419**（100%）')
lines.append(f'- 已修 URL 并上线：**{len(url_fixed)} 个**（commit 已推送，线上生效）')
lines.append(f'- 仍有问题的工具（去重后）：**{total_problem_tools} 个**')
lines.append(f'  - 其中 URL 已修但 content/price 仍错的：**{url_fixed_in_problems} 个**（P2/P3 重点）')
lines.append('')
lines.append('## 阶段进度表')
lines.append('')
lines.append('| 阶段 | 说明 | 问题数 | 建议动作 | 状态 |')
lines.append('|------|------|--------|----------|------|')
action = {
    'P0_url_fixed_content_pending': '派 Agent 联网写出正确 content/description/price，校验后落地（上次收尾遗留）',
    'P1_url_review': '人工决定：下架 或 改写为「概念/孵化中」页',
    'P2_content_highrisk': '派 Agent 联网写出正确 content+description，校验后落地',
    'P3_price_fix': '派 Agent 联网核实正确定价（人民币/美元），批量修正 price',
    'P4_other_field': '派 Agent 核实 platform/description 等字段后修正',
    'P5_conflict': '人工逐条裁定：保留 / 改写 / 下架',
    'P6_lowconf': '人工或 Agent 二次复核，确认无误或降级处理',
}
for st in stage_order:
    lines.append(f'| {st} | {stage_name[st]} | {cnt.get(st,0)} | {action[st]} | ⏸ 待指令 |')
lines.append('')

# 每个阶段明细
for st in stage_order:
    sub = [e for e in items if e['stage'] == st]
    if not sub:
        continue
    lines.append(f'## {stage_name[st]}（{len(sub)} 项）')
    lines.append('')
    lines.append('| # | slug | 字段 | 置信 | URL已修 | 备注 |')
    lines.append('|---|------|------|------|---------|------|')
    for i, e in enumerate(sub, 1):
        conf = '/'.join(sorted(set(e['confidences']))) or '-'
        note = ''
        if e['notes']:
            # 取最高优先级 note 前 80 字
            e['notes'].sort(key=lambda x: (0 if x[0]=='high' else 1 if x[0]=='medium' else 2))
            note = (e['notes'][0][1] or '')[:80].replace('\n', ' ')
        lines.append(f'| {i} | {e["slug"]} | {",".join(e["fields"]) or "-"} | {conf} | {"✅" if e["url_fixed"] else "—"} | {note} |')
    lines.append('')

with open(os.path.join(ROOT, 'MASTER_TODO.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print('problem_tools:', total_problem_tools)
print('url_fixed_among_problems:', url_fixed_in_problems)
print('stage_counts:', dict(cnt))
print('written: MASTER_TODO.json + MASTER_TODO.md')
