#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_p0_fixes.py —— P0 落地脚本（安全边界：只改标错的字段）

读取 MASTER_TODO.json 中 P0 工具被标记的 fields（description/price/platform/content），
从 4 个 p0_correct_batchX.json 取对应正确值，写入 tools.json（保持顶层 list）。
同时修正已确认的 windsurf URL 错误（devin.ai -> windsurf.com）。
不改未标记的字段，不触碰其他工具。
"""
import json, glob, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'tools.json')
TODO = os.path.join(ROOT, 'scripts', '_verify_batches', 'MASTER_TODO.json')
BATCH_DIR = os.path.join(ROOT, 'scripts', '_verify_batches')

FIELD_MAP = {
    'description': ('description_correct', 'description'),
    'price':       ('price_correct', 'price'),
    'platform':    ('platform_correct', 'platform'),
    'content':     ('content_correct', 'content'),
}

# 额外已确认的 URL 错误纠正（来自 P0 agent 复核，非原 P0 fields 但为错）
URL_OVERRIDE = {
    'windsurf': 'https://windsurf.com',
}

def load_batches():
    correct = {}
    for f in sorted(glob.glob(os.path.join(BATCH_DIR, 'p0_correct_batch*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        for e in d.get('results', []):
            correct[e['slug']] = e
    return correct

def main():
    todo = json.load(open(TODO, encoding='utf-8'))
    p0 = {e['slug']: e for e in todo['items'] if e.get('stage') == 'P0_url_fixed_content_pending'}
    correct = load_batches()

    tools = json.load(open(DATA, encoding='utf-8'))
    assert isinstance(tools, list), 'tools.json 必须是顶层 list'
    by = {t['slug']: t for t in tools if t.get('slug')}

    report = []
    for slug, item in p0.items():
        t = by.get(slug)
        if not t or not t.get('published'):
            report.append((slug, 'SKIP', '未找到或未发布', []))
            continue
        e = correct.get(slug)
        if not e:
            report.append((slug, 'SKIP', '无 corrected 数据', []))
            continue
        flagged = set(item.get('fields', []))
        changes = []
        for fld in flagged:
            if fld not in FIELD_MAP:
                continue
            src_key, dst_key = FIELD_MAP[fld]
            new_val = (e.get(src_key) or '').strip()
            if not new_val:
                continue
            old_val = (t.get(dst_key) or '').strip()
            if old_val == new_val:
                continue
            # 长度护栏：content 不能过短（防 agent 漏产出）
            if dst_key == 'content' and len(new_val) < 600:
                changes.append(f'{dst_key}: 跳过(内容过短{len(new_val)})')
                continue
            t[dst_key] = new_val
            changes.append(f'{dst_key}: 已更新')
        # URL 额外纠正
        if slug in URL_OVERRIDE:
            new_u = URL_OVERRIDE[slug]
            if (t.get('url') or '').rstrip('/') != new_u.rstrip('/'):
                t['url'] = new_u
                changes.append('url: 已修正为 ' + new_u)
        report.append((slug, 'OK' if changes else 'NOCHANGE', e.get('confidence', ''), changes))

    json.dump(tools, open(DATA, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    # 二次校验：仍是 list
    recheck = json.load(open(DATA, encoding='utf-8'))
    assert isinstance(recheck, list), '写回后结构异常'

    print('=== P0 落地报告 ===')
    ok = sum(1 for r in report if r[1] == 'OK')
    for slug, status, conf, ch in report:
        print(f'{slug:20s} {status:9s} conf={conf:7s} {ch}')
    print(f'\n总计 {len(report)} 项，实际改动 {ok} 项。tools.json 已写回（顶层 list 校验通过）。')

if __name__ == '__main__':
    main()
