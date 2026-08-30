#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章内容类型归类（2026-08-08，对应 ROADMAP-TODO 第一阶段）。

把 22+ 个零散分类归并为 4 个内容类型：
    AI评测 / AI教程 / AI资讯 / 行业分析

说明：AI资讯 = 长文资讯（独立文章，如宇树牵手DeepSeek），区别于 /news/ 的
短快讯（news_*.json 每日摘要，不在此归类范围内）。

规则：
    1. 优先按分类映射（REVIEW_CATS / TUTORIAL_CATS / NEWS_CATS / ANALYSIS_CATS）；
    2. 标题含快讯特征（AI圈/本周/快讯等）→ AI资讯；
    3. 分析类分类下，标题前 28 字含强评测词（评测/实测/横评/测评）→ AI评测；
    4. 标题含教程特征（教程/指南/入门/怎么用/实战等）→ AI教程；
    5. 标题含 vs / 评测类词（实测/横评/对比/推荐/选型等）→ AI评测；
    6. 标题含分析类词（分析/趋势/盘点/报告/深度/行业等）→ 行业分析；
    7. 兜底 → 行业分析。

数据变更（幂等）：
    - 新增 content_type 字段；
    - 原 category 保留到 orig_category（仅在缺失时写入，不覆盖已有值）。

用法：
    python scripts/classify_articles.py [articles.json路径]
"""

import collections
import json
import re
import sys


REVIEW_CATS = {'AI评测', 'AI工具评测', 'AI模型评测', 'tool-review',
               '对比评测', '观点对比', 'tools-comparison'}
TUTORIAL_CATS = {'AI工具教程', '教程指南', 'AI教程'}
NEWS_CATS = {'AI资讯', 'AI行业动态', '行业动态', 'ai-news', 'industry-news'}
ANALYSIS_CATS = {'industry-analysis', '行业趋势', '行业分析', '数据洞察',
                 'AI趋势', 'AI行业分析'}

TUT_KW = ('教程', '指南', '入门', '怎么用', '如何使用', '上手', '保姆级',
          '工作流', '实战', '玩法', '使用教程', '完全使用', '流程')
REV_KW = ('评测', '实测', '横评', '测评', '对决', '测试', '对比', '推荐',
          '选型', '哪个好', '怎么选', '体验', '低估', '测了', '画了', '真实项目')
NEWS_KW = ('快讯', '本周', '上周', '发生了什么', 'AI圈', '新闻', '速览', '日报')
ANA_KW = ('分析', '趋势', '盘点', '报告', '全景', '格局', '复盘', '深度',
          '行业', '解析', '观察', '解读', '白皮书')
STRONG_REV = ('评测', '实测', '横评', '测评')

CONTENT_TYPES = ('AI评测', 'AI教程', 'AI资讯', '行业分析')


def classify(category, title):
    """根据原分类 + 标题返回内容类型。"""
    if category in REVIEW_CATS:
        return 'AI评测'
    if category in TUTORIAL_CATS:
        return 'AI教程'
    if category in NEWS_CATS:
        return 'AI资讯'
    if any(k in title for k in NEWS_KW):
        return 'AI资讯'
    if category in ANALYSIS_CATS:
        if any(k in title[:28] for k in STRONG_REV):
            return 'AI评测'
        return '行业分析'
    if any(k in title for k in TUT_KW):
        return 'AI教程'
    if any(k in title[:28] for k in STRONG_REV):
        return 'AI评测'
    if re.search(r'\b[vV][sS]\b', title):
        return 'AI评测'
    if any(k in title for k in REV_KW):
        return 'AI评测'
    if any(k in title for k in ANA_KW):
        return '行业分析'
    return '行业分析'


def main():
    # 2026-08-30 升级：单体 articles.json 已退役，改走 data_store 分片（幂等，可重跑）。
    # 新增 category 归一：非 4 类标准值 → 归一为 classify 结果值（用户拍板：SEO/GEO/用户角度细分合并）。
    # orig_category 仍仅缺失时写入，不覆盖已有值（原分类信息永不丢失）。
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from data_store import load_all_articles, save_article

    articles = load_all_articles()
    changed_cat = changed_ct = changed_orig = 0
    dist = collections.Counter()
    for a in articles:
        cat = a.get('category', '')
        title = a.get('title', '')
        if not a.get('orig_category'):
            a['orig_category'] = cat
            changed_orig += 1
        ct = classify(a.get('orig_category') or cat, title)
        if a.get('content_type') != ct:
            a['content_type'] = ct
            changed_ct += 1
        if cat != ct and cat != '数据洞察':  # category 归一到 4 类标准值（白名单：数据洞察=月度洞察专属身份，保留）
            a['category'] = ct
            changed_cat += 1
        dist[ct] += 1
        save_article(a)

    print('内容类型分布：')
    for k in ('AI评测', 'AI教程', 'AI资讯', '行业分析'):
        print('  %s: %d' % (k, dist.get(k, 0)))
    print('共 %d 篇文章：category 归一 %d 处 / content_type 修正 %d 处 / orig_category 补档 %d 处。'
          % (len(articles), changed_cat, changed_ct, changed_orig))


if __name__ == '__main__':
    main()
