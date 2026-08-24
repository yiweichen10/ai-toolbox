#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""今日推荐候选池（v6.5）
每天构建时自动预选 5 款候选（新发布/热门/有评测），排除近 7 天已推荐，
写入 data/picks_candidates.json 供编辑确认；同时维护 data/picks_history.json。
不修改 homepage_picks.json —— 确认动作由人工完成。
"""
import json
import math
import os
import re
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, 'data')


def load(name, default):
    try:
        with open(os.path.join(DATA, name), encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def save(name, obj):
    with open(os.path.join(DATA, name), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def parse_visits(v):
    if not v:
        return 0
    s = str(v).replace(',', '').replace('+', '').replace('约', '').strip()
    for unit, mult in (('亿', 1e8), ('万', 1e4)):
        if unit in s:
            try:
                return float(''.join(ch for ch in s.replace(unit, '') if ch.isdigit() or ch == '.')) * mult
            except ValueError:
                pass
    try:
        return float(''.join(ch for ch in s if ch.isdigit() or ch == '.'))
    except ValueError:
        return 0


def show_date(t):
    return str(t.get('published_date') or t.get('created_date') or '')[:10]


def main():
    tools = [t for t in load('tools.json', []) if t.get('published') and t.get('slug')]
    articles = load('articles.json', [])
    cur = load('homepage_picks.json', {}).get('picks', [])
    history = load('picks_history.json', [])
    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    cutoff60 = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')

    # 维护历史：当前推荐计入当天历史，保留 60 天
    for p in cur:
        slug = p.get('slug')
        if slug and not any(h.get('slug') == slug and h.get('date') == today for h in history):
            history.append({'slug': slug, 'date': today})
    history = [h for h in history if h.get('date', '') >= cutoff60]
    exclude = {p.get('slug') for p in cur if p.get('slug')} | {
        h['slug'] for h in history if h.get('date', '') >= week_ago and h.get('slug')
    }

    # 有实测评测关联的工具
    reviewed = set()
    for a in articles:
        rel = a.get('related_tools') or []
        if isinstance(rel, list):
            for r in rel:
                if isinstance(r, str):
                    reviewed.add(r)

    cands = {}

    def add(t, tag, reason):
        if not t or t.get('slug') in exclude:
            return
        slug = t['slug']
        if slug in cands:
            if tag not in cands[slug]['tags']:
                cands[slug]['tags'].append(tag)
            return
        score = 0.0
        v = parse_visits(t.get('visits'))
        if v:
            score += min(40, math.log10(max(v, 1)) * 5.7)
        try:
            rating = float(''.join(ch for ch in str(t.get('rating') or '') if ch.isdigit() or ch == '.') or 0)
            score += rating * 6
        except ValueError:
            pass
        if slug in reviewed:
            score += 8
        d = show_date(t)
        if len(d) == 10:
            try:
                days = (datetime.now() - datetime.strptime(d, '%Y-%m-%d')).days
                score += max(0, 10 - days)
            except ValueError:
                pass
        cands[slug] = {
            'slug': slug,
            'name': t.get('name', ''),
            'category': t.get('category', ''),
            'price': t.get('price', ''),
            'visits': t.get('visits', ''),
            'rating': t.get('rating', ''),
            'score': round(score, 1),
            'tags': [tag],
            'reason': reason,
            'date': d,
        }

    # 来源 A：最近发布
    for t in sorted([x for x in tools if show_date(x)], key=show_date, reverse=True)[:8]:
        add(t, '新发布', '今日新收录 · ' + str(t.get('description', ''))[:48])
    # 来源 B：热门访问
    for t in sorted(tools, key=lambda x: parse_visits(x.get('visits')), reverse=True)[:8]:
        add(t, '热门', '访问量领先 · ' + str(t.get('description', ''))[:48])
    # 来源 C：有实测评测
    for t in tools:
        if t['slug'] in reviewed:
            add(t, '编辑实测', '有深度评测支撑 · ' + str(t.get('description', ''))[:48])

    top = sorted(cands.values(), key=lambda c: c['score'], reverse=True)
    # 类别多样性：Top5 中同一分类最多 2 款
    final = []
    cat_count = {}
    for c in top:
        cat = c.get('category', '')
        if cat_count.get(cat, 0) >= 2:
            continue
        cat_count[cat] = cat_count.get(cat, 0) + 1
        final.append(c)
        if len(final) >= 5:
            break
    if len(final) < 5:
        seen = {x['slug'] for x in final}
        for c in top:
            if c['slug'] in seen:
                continue
            cat = c.get('category', '')
            if cat_count.get(cat, 0) >= 2:
                continue
            cat_count[cat] = cat_count.get(cat, 0) + 1
            final.append(c)
            seen.add(c['slug'])
            if len(final) >= 5:
                break
    top = final[:5]
    save('picks_candidates.json', {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'picks': top,
    })
    save('picks_history.json', history)

    # ── 自动确认（2026-08-07：默认全自动；人工改过 homepage_picks.json 则不覆盖）──
    _cur = load('homepage_picks.json', {})
    _is_auto = _cur.get('auto', False)
    _cur_date = str(_cur.get('date', ''))
    _today = datetime.now().strftime('%Y-%m-%d')

    def _corrupt_text(s):
        # CJK 被 ASCII 化（连续问号/替换符）视为编码损坏，损坏时即使当天也强制重建（2026-08-13）
        return isinstance(s, str) and ('\ufffd' in s or re.search(r'\?{3,}', s) is not None)

    _cur_corrupt = any(_corrupt_text(p.get('reason')) or _corrupt_text(p.get('tag')) for p in _cur.get('picks', []))
    if _is_auto and _cur_date == _today and not _cur_corrupt:
        print('[picks_auto] 今天已自动确认过，保持当日推荐不变')
    elif _is_auto or not _cur.get('picks'):
        if _cur_corrupt:
            print('[picks_auto] 检测到推荐文案编码损坏，重建当日推荐')
        _auto_top = []
        _cat_cnt = {}
        for _c in top:
            _cat = _c.get('category', '')
            if _cat_cnt.get(_cat, 0) >= 1:
                continue
            _cat_cnt[_cat] = _cat_cnt.get(_cat, 0) + 1
            _auto_top.append(_c)
            if len(_auto_top) >= 3:
                break
        if len(_auto_top) < 3:
            _seen = {x['slug'] for x in _auto_top}
            for _c in top:
                if _c['slug'] in _seen:
                    continue
                _auto_top.append(_c)
                _seen.add(_c['slug'])
                if len(_auto_top) >= 3:
                    break
        _auto_picks = []
        for _c in _auto_top:
            _r = str(_c.get('reason', ''))
            _short = re.sub(r'^(访问量领先|今日新收录|有深度评测支撑)\s*·\s*', '', _r)
            _short = re.split(r'[。！？]', _short)[0].strip()
            if len(_short) > 45:
                _cut = _short[:45]
                # 英文边界保护：第 46 字符是英文/数字则回退最近空格
                if len(_short) > 45 and (_short[45].isascii() and (_short[45].isalpha() or _short[45].isdigit())):
                    _sp = _cut.rfind(" ")
                    if _sp > 8:
                        _cut = _cut[:_sp]
                _short = _cut.rstrip(" ，,。：:")
            _auto_picks.append({
                'slug': _c['slug'],
                'reason': _short,
                'tag': (_c.get('tags') or ['编辑实测'])[0],
            })
        save('homepage_picks.json', {
            'auto': True,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'picks': _auto_picks,
        })
        print('[picks_auto] 已自动确认今日推荐: ' + ' / '.join(p['slug'] for p in _auto_picks))
    else:
        print('[picks_auto] 检测到人工配置，保留不覆盖（想恢复自动：把 homepage_picks.json 的 auto 设为 true）')

    print('[picks_candidates] 候选池 %d 个，今日推荐 Top%d：' % (len(cands), len(top)))
    for c in top:
        print(' - %s | %s | 分 %.1f | %s' % (c['name'], c['category'], c['score'], '/'.join(c['tags'])))


if __name__ == '__main__':
    main()
