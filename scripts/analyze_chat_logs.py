#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 助手问答日志分析（P2-9：别名/标签持续进化的数据源）

用法：
  python3 scripts/analyze_chat_logs.py [log_file] [feedback_file]

默认读取服务器日志路径，本地不存在则回退到 logs/ai_assistant.log。
输出 reports/ai-assistant-analysis-YYYYMMDD.md，包含：
  - 总体统计（提问量/缓存命中率/错误率/平均延迟）
  - 模型使用与 429 降级统计（观测免费档限流）
  - Top 高频问题
  - 检索薄弱问题（候选数少 / 命中为空，疑似别名/标签缺失）
  - 负面反馈问题（用户点"没用"，优先补强方向）
"""

from __future__ import print_function

import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = sys.argv[1] if len(sys.argv) > 1 else (
    '/var/www/aitoollab/logs/ai_assistant.log'
)
if not os.path.isfile(LOG):
    _local = os.path.join(BASE, 'logs', 'ai_assistant.log')
    if os.path.isfile(_local):
        LOG = _local
FB = sys.argv[2] if len(sys.argv) > 2 else (
    '/var/www/aitoollab/data/ai_feedback.json'
)
if not os.path.isfile(FB):
    _local_fb = os.path.join(BASE, 'data', 'ai_feedback.json')
    if os.path.isfile(_local_fb):
        FB = _local_fb


def norm(q):
    return re.sub(r'[\s\u3000,，。、!！?？;；:：()（）[\]【】]+', '', str(q or '')).lower()


def load_entries():
    entries = []
    if not os.path.isfile(LOG):
        return entries
    for line in io.open(LOG, encoding='utf-8', errors='replace'):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if 'query' in obj and obj.get('query'):
            entries.append(obj)
    return entries


def load_feedback():
    items = []
    if not os.path.isfile(FB):
        return items
    try:
        data = json.load(io.open(FB, encoding='utf-8'))
    except (ValueError, OSError):
        return items
    items = data.get('log', []) if isinstance(data, dict) else []
    return items


def main():
    entries = load_entries()
    fb = load_feedback()
    today = datetime.now().strftime('%Y-%m-%d')
    out = []
    w = out.append

    w('# AI 助手问答日志分析 %s' % today)
    w('')
    w('> 数据源：`%s` ｜ 反馈：`%s`' % (LOG, FB))
    w('')

    if not entries:
        w('暂无问答日志。')
        return _write(out, today)

    total = len(entries)
    cache_hit = sum(1 for e in entries if e.get('cache') == 'hit')
    errors = sum(1 for e in entries if e.get('error'))
    lat = [e.get('latency_ms') or 0 for e in entries]
    avg_lat = sum(lat) / len(lat) if lat else 0

    w('## 总体统计')
    w('')
    w('| 指标 | 数值 |')
    w('|---|---|')
    w('| 提问量 | %d |' % total)
    w('| 缓存命中 | %d（%.1f%%） |' % (cache_hit, 100.0 * cache_hit / total))
    w('| 出错 | %d（%.1f%%） |' % (errors, 100.0 * errors / total))
    w('| 平均延迟 | %d ms |' % int(avg_lat))
    w('')

    # 模型使用与 429 降级（免费档限流观测）
    fresh = [e for e in entries if e.get('cache') != 'hit']
    model_cnt = Counter(e.get('model') or 'unknown' for e in fresh)
    degraded = [e for e in fresh if e.get('fallbacks')]
    fb_total = sum(e.get('fallbacks') or 0 for e in fresh)
    w('## 模型使用与降级（免费档限流观测）')
    w('')
    w('| 模型 | 请求数 |')
    w('|---|---|')
    for m, n in model_cnt.most_common():
        w('| %s | %d |' % (m, n))
    w('')
    w('- 发生过降级的请求：%d（%.1f%%）' % (
        len(degraded),
        100.0 * len(degraded) / len(fresh) if fresh else 0.0,
    ))
    w('- 累计降级次数：%d' % fb_total)
    w('')

    # 高频问题（仅统计非缓存命中，避免重复计数）
    by_q = Counter(norm(e.get('query', '')) for e in fresh if e.get('query'))
    w('## Top 高频问题（用户真实提问，前 20）')
    w('')
    w('| 次数 | 问题 | 平均候选数 |')
    w('|---|---|---|')
    for q, n in by_q.most_common(20):
        cands = [e.get('candidate_count') or 0 for e in fresh if norm(e.get('query', '')) == q]
        avg_c = int(sum(cands) / len(cands)) if cands else 0
        w('| %d | %s | %d |' % (n, q, avg_c))
    w('')

    # 检索薄弱：候选 < 4 或命中为空（未走缓存的真实请求）
    weak = [e for e in fresh
            if (e.get('candidate_count') is not None and e.get('candidate_count') < 4)
            or (not e.get('matched'))]
    if weak:
        w('## 检索薄弱问题（疑似别名/标签/描述缺失，重点补强）')
        w('')
        w('| 问题 | 候选数 | 命中 | 出错 |')
        w('|---|---|---|---|')
        seen = set()
        for e in weak:
            q = norm(e.get('query', ''))
            if q in seen:
                continue
            seen.add(q)
            w('| %s | %s | %d | %s |' % (
                q,
                e.get('candidate_count') if e.get('candidate_count') is not None else '?',
                len(e.get('matched') or []),
                '是' if e.get('error') else '',
            ))
        w('')

    # 负面反馈
    neg = [x for x in fb if x.get('value') == -1]
    if neg:
        w('## 负面反馈问题（用户点"没用"，优先调优方向）')
        w('')
        w('| 时间 | 问题 |')
        w('|---|---|')
        for x in neg[-20:]:
            w('| %s | %s |' % (x.get('ts', ''), x.get('query', '')))
        w('')

    # 别名建议（基于薄弱问题的公共词）
    if weak:
        w('## 别名/标签补强建议')
        w('')
        w('从"检索薄弱"问题中提取的候选关键词（人工复核后补入 `CATEGORY_ALIASES` 或工具标签）：')
        w('')
        for e in weak[:15]:
            q = (e.get('query') or '').strip()
            w('- `%s`' % q)
        w('')

    _write(out, today)


def _write(lines, today):
    path = os.path.join(BASE, 'reports', 'ai-assistant-analysis-%s.md' % today)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except OSError:
        pass
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('report -> %s' % path)


if __name__ == '__main__':
    main()
