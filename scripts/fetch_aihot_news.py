#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_aihot_news.py — 自动拉取 aihot 当日精选 → data/news_YYYY-MM-DD.json
供中文站 AI 快讯日更自动化调用。

数据源: aihot.virxact.com 公开 API（免 token，需带浏览器 UA）
用法: python scripts/fetch_aihot_news.py [--date 2026-07-20] [--take 50] [--limit 8]
幂等: 若 data/news_当天.json 已存在且非空，直接跳过。
"""
import json
import os
import re
import sys
import argparse
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CST = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
API = "https://aihot.virxact.com/api/public/items"

CAT_MAP = {
    'ai-models': 'models',
    'ai-products': 'products',
    'industry': 'industry',
    'paper': 'paper',
    'tip': 'opinion',
}
CAT_LABEL = {
    'models': '模型发布',
    'products': '产品发布',
    'industry': '行业动态',
    'opinion': '观点',
    'paper': '论文研究',
}


def fetch(since, take=50, mode='selected'):
    url = f"{API}?{urlencode({'mode': mode, 'since': since, 'take': take})}"
    req = Request(url, headers={'User-Agent': UA})
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


def pick(items, limit=30):
    """按类目均衡选 limit 条：每类最多 8 条，优先 score 高，再全局补。"""
    by_cat = {}
    for it in items:
        c = CAT_MAP.get(it.get('category', ''), it.get('category', ''))
        by_cat.setdefault(c, []).append(it)
    for c in by_cat:
        by_cat[c].sort(key=lambda x: (x.get('score') or 0), reverse=True)

    chosen = []
    quotas = {c: 3 for c in by_cat}
    cats = list(by_cat.keys())
    while len(chosen) < limit and any(quotas.get(c, 0) > 0 and by_cat.get(c) for c in cats):
        for c in cats:
            if len(chosen) >= limit:
                break
            if quotas.get(c, 0) > 0 and by_cat.get(c):
                chosen.append(by_cat[c].pop(0))
                quotas[c] -= 1

    if len(chosen) < limit:
        rest = [it for c in by_cat for it in by_cat[c]]
        rest.sort(key=lambda x: (x.get('score') or 0), reverse=True)
        seen = set(id(x) for x in chosen)
        for it in rest:
            if len(chosen) >= limit:
                break
            if id(it) not in seen:
                chosen.append(it)
                seen.add(id(it))
    return chosen


def _norm_title(t):
    """标题归一化：只留中英文/数字，用于同事件包含判断"""
    return re.sub(r'[^0-9a-zA-Z一-鿿]+', '', (t or '').lower())


def _title_tokens(t):
    """英文/数字词 + 中文 bigram，用于跨天同事件相似度判断"""
    t = (t or '').lower()
    words = set(re.findall(r'[a-z0-9][a-z0-9.\-]*', t))
    cjk = re.findall(r'[一-鿿]', t)
    grams = {''.join(cjk[i:i + 2]) for i in range(len(cjk) - 1)}
    return words | grams


def load_recent_signatures(today_str, days=3):
    """加载前 N 天已发快讯的 (归一化标题, 词元集, source_url)，用于跨天去重。
    背景（2026-08-16）：aihot 会把同一事件按不同来源连续多天推送
    （如 Qwen3.8 开源 08-13/14/15 连上 3 天），只按当天 item id 去重拦不住。"""
    sigs, urls = [], set()
    d0 = datetime.strptime(today_str, '%Y-%m-%d')
    for k in range(1, days + 1):
        fp = os.path.join(BASE_DIR, 'data',
                          f"news_{(d0 - timedelta(days=k)).strftime('%Y-%m-%d')}.json")
        if not os.path.exists(fp):
            continue
        try:
            for it in json.load(open(fp, encoding='utf-8')):
                sigs.append((_norm_title(it.get('title', '')),
                             _title_tokens(it.get('title', ''))))
                u = (it.get('source_url') or '').strip()
                if u:
                    urls.add(u)
        except Exception:
            pass
    return sigs, urls


def is_seen(title, url, sigs, urls, threshold=0.3):
    """与近 3 天已发条目的标题/来源比对，命中即视为同事件重复"""
    if url and url in urls:
        return True
    nt = _norm_title(title)
    tk = _title_tokens(title)
    if not nt:
        return False
    for ont, otk in sigs:
        if len(nt) > 6 and ont and (nt in ont or ont in nt):
            return True
        if tk and otk:
            j = len(tk & otk) / (len(tk | otk) or 1)
            if j >= threshold:
                return True
            # 语序颠倒型同事件（"Cursor 被 SpaceX 收购" vs "SpaceX 收购 Cursor"）：
            # Jaccard 偏低，但共享 >=2 个专名词（len>=3）且共享 >=1 个中文 bigram 即判重
            words_a = {w for w in tk if re.fullmatch(r'[a-z0-9][a-z0-9.\-]{2,}', w)}
            words_b = {w for w in otk if re.fullmatch(r'[a-z0-9][a-z0-9.\-]{2,}', w)}
            cjk_a = tk - words_a
            cjk_b = otk - words_b
            if len(words_a & words_b) >= 2 and (cjk_a & cjk_b):
                return True
    return False


def to_news(it, date_str):
    cat_raw = it.get('category', '')
    cat = CAT_MAP.get(cat_raw, cat_raw)
    pa = it.get('publishedAt', '')
    try:
        t = datetime.fromisoformat(pa)
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        t = t.astimezone(CST)
        pa_out = t.strftime('%Y-%m-%dT%H:%M:%S+08:00')
    except Exception:
        pa_out = pa
    src = it.get('source') or it.get('attribution') or ''
    url = it.get('url') or it.get('permalink') or ''
    return {
        'id': '',
        'title': it.get('title', ''),
        'summary': it.get('summary', '') or '',
        'category': cat,
        'category_label': CAT_LABEL.get(cat, cat),
        'source': src,
        'source_url': url,
        'published_at': pa_out,
        'tags': [cat] if cat else [],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date')
    ap.add_argument('--take', type=int, default=50)
    ap.add_argument('--limit', type=int, default=8)
    args = ap.parse_args()

    today = args.date or datetime.now(CST).strftime('%Y-%m-%d')
    out = os.path.join(BASE_DIR, 'data', f'news_{today}.json')

    if os.path.exists(out):
        try:
            ex = json.load(open(out, encoding='utf-8'))
            if ex:
                print(f'✅ 已存在 {len(ex)} 条: {out}（跳过）')
                return
        except Exception:
            pass

    since = (datetime.now(CST) - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S+08:00')
    try:
        resp = fetch(since, args.take, 'selected')
    except (URLError, HTTPError) as e:
        print('⚠️ aihot selected 失败:', e)
        resp = {'items': []}
    items = resp.get('items', []) if isinstance(resp, dict) else resp

    # 兜底：selected 不足时补 mode=all
    if len(items) < args.limit:
        try:
            resp2 = fetch(since, 100, 'all')
            extra = resp2.get('items', []) if isinstance(resp2, dict) else resp2
            seen = {it.get('id') for it in items}
            items += [x for x in extra if x.get('id') not in seen]
        except Exception as e:
            print('⚠️ aihot all 兜底失败:', e)

    if not items:
        print('❌ 未获取到任何快讯，写入空文件')
        json.dump([], open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        return

    # 跨天去重：过滤与前 3 天同事件的条目（在 pick 前过滤，名额由其他新闻补上）
    sigs, seen_urls = load_recent_signatures(today)
    if sigs:
        before = len(items)
        items = [it for it in items
                 if not is_seen(it.get('title', ''),
                                (it.get('url') or it.get('permalink') or '').strip(),
                                sigs, seen_urls)]
        dropped = before - len(items)
        if dropped:
            print(f'  ⟂ 跨天去重: 过滤 {dropped} 条与前 3 天同事件的条目')

    chosen = pick(items, args.limit)
    news = []
    for i, it in enumerate(chosen, 1):
        n = to_news(it, today)
        n['id'] = f"{today.replace('-', '')}-{i:03d}"
        news.append(n)

    json.dump(news, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'✅ 生成 {len(news)} 条 → {out}')
    for n in news:
        print(f"  [{n['category']}] {n['title']}")


if __name__ == '__main__':
    main()
