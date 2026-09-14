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
import shutil
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
# 上游 category 缺失时的关键词兜底表（顺序即优先级；命中不了回落 industry）
# 顺序刻意把"政策/治理类"放最前：否则含"模型""发布"字样的政策新闻会被误判成模型发布。
# 只放高辨识度词，模糊词（合作/投资/研究/安全）一律不列，让它们落到 industry 默认值。
CAT_FALLBACK_HINTS = (
    ('industry', ('呼吁', '放缓', '审慎', '准则', '监管', '治理', '政策', '合规', '出口管制',
                  '国会', '白宫', '诉讼', '收购', '融资', '估值', '营收', '上市', '裁员')),
    ('models', ('模型', '参数量', '架构', '开源', '权重', 'benchmark', '登顶', '跑分', '上下文窗口')),
    ('paper', ('论文', '预印本', 'arxiv', '定理', '实验', '证明')),
    ('products', ('发布', '上线', '推出', '公测', '开放', 'api', '应用', '订阅', '新功能', '更新')),
)
VALID_CATEGORIES = tuple(CAT_LABEL.keys())


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


def _infer_category(it):
    """上游 category 缺失（null/空）时的确定性兜底（2026-09-14 立规）。

    背景：aihot API 偶发返回 "category": null（实证：2026-09-12 两条、2026-09-14 一条），
    旧 to_news() 直接透传 → category=null → 页面空徽章 + 栏目筛选下该条消失。
    这里按关键词做可解释的确定性推断，命中不了回落 industry，并在 stdout 告警供人工复核。
    """
    text = ' '.join(str(it.get(k) or '') for k in ('title', 'title_en', 'summary')).lower()
    for cat, kws in CAT_FALLBACK_HINTS:
        if any(k in text for k in kws):
            return cat
    return 'industry'


def to_news(it, date_str):
    cat_raw = it.get('category') or ''
    cat = CAT_MAP.get(cat_raw, cat_raw)
    if not cat:
        cat = _infer_category(it)
        print(f'  ⚠️ 上游缺分类，按关键词推断为 [{cat}]: {(it.get("title") or "")[:36]}')
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


def _backfill_categories():
    """一次性/可重复执行的存量修复（2026-09-14）：给历史 news_*.json 里 category 为 null/空
    的条目补上推断分类（确定性规则，只补缺、不覆盖已有值），修前逐文件存 .bak。
    只修"缺失"，不改任何已有分类 —— 遵守"category 一律不动"的边界。
    """
    import glob
    fixed_total = 0
    for fp in sorted(glob.glob(os.path.join(BASE_DIR, 'data', 'news_*.json'))):
        try:
            items = json.load(open(fp, encoding='utf-8'))
        except Exception:
            continue
        if not isinstance(items, list):
            continue
        changed = []
        for it in items:
            if not it.get('category'):
                cat = _infer_category(it)
                changed.append((it.get('id'), it.get('category'), cat, (it.get('title') or '')[:36]))
                it['category'] = cat
                it['category_label'] = CAT_LABEL.get(cat, cat)
                it['tags'] = [cat]
        if not changed:
            continue
        shutil.copy2(fp, fp + '.bak')
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        json.load(open(fp, encoding='utf-8'))  # 读回校验
        for _id, _old, _new, _t in changed:
            print(f'  [补分类] {os.path.basename(fp)} {_id}: {_old!r} → {_new} | {_t}')
        fixed_total += len(changed)
    print(f'✅ 存量分类补全完成：修复 {fixed_total} 条')
    return fixed_total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date')
    ap.add_argument('--take', type=int, default=50)
    ap.add_argument('--limit', type=int, default=8)
    ap.add_argument('--backfill-categories', action='store_true',
                    help='只给历史文件里缺失的 category 补推断值，不采集')
    args = ap.parse_args()

    if args.backfill_categories:
        _backfill_categories()
        return

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
