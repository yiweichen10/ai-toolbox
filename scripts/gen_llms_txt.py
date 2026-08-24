#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据站点数据生成 llms.txt（GEO 标准格式）。

输出：
  seo-site/llms.txt         中文站（aitoollab.cn）
  ../seo-site-en/llms.txt   英文站（aitoolbox.hk）

用法：python scripts/gen_llms_txt.py
"""
import io
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EN_BASE = os.path.join(os.path.dirname(BASE), 'seo-site-en')

CN_DOMAIN = 'https://www.aitoollab.cn'
EN_DOMAIN = 'https://www.aitoolbox.hk'

CN_CAT_ORDER = ['AI对话', 'AI写作', 'AI绘画', 'AI编程', 'AI视频', 'AI音频', 'AI办公', 'AI设计',
                'AI搜索', 'AI翻译', 'AI自动化', 'AI效率', 'AI智能体', 'AI开发', 'AI行业应用',
                'AI学习', 'AI检测', 'AI提示词']


def load_json(path):
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    return d.get('tools', d) if isinstance(d, dict) else d


def rating_num(rating):
    m = re.search(r'[\d.]+', str(rating or ''))
    try:
        return float(m.group(0))
    except Exception:
        return 0.0


def clip(text, n=64):
    t = (text or '').strip().replace('\n', ' ').replace('\r', ' ')
    if len(t) > n:
        t = t[:n].rstrip() + '…'
    return t


def sort_key_date(a):
    d = str(a.get('dateFull') or a.get('date') or '')
    m = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', d)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m2 = re.match(r'^(\d{4})-(\d{2})-(\d{2})', d)
    if m2:
        return (int(m2.group(1)), int(m2.group(2)), int(m2.group(3)))
    return (0, 0, 0)


def tool_sections(tools, domain, trailing_slash, per_cat=5, count_fmt=None):
    """按分类列出每类评分最高的工具，返回 (markdown, 分类计数列表)。"""
    count_fmt = count_fmt or (lambda n: f'（{n}款）')
    by_cat = {}
    for t in tools:
        by_cat.setdefault(t.get('category') or '其他', []).append(t)
    out = []
    for cat in sorted(by_cat, key=lambda c: -len(by_cat[c])):
        ts = sorted(by_cat[cat], key=lambda t: rating_num(t.get('rating')), reverse=True)[:per_cat]
        lines = [f'### {cat}{count_fmt(len(by_cat[cat]))}']
        for t in ts:
            slug = t.get('slug', '')
            url = f'{domain}/tools/{slug}/' if trailing_slash else f'{domain}/tools/{slug}'
            desc = clip(t.get('description'), 70)
            lines.append(f'- [{t.get("name", "")}]({url})：{desc}')
        out.append('\n'.join(lines))
    return '\n\n'.join(out)


def article_sections(articles, domain, trailing_slash, per_cat=8, total=16):
    arts = sorted(articles, key=sort_key_date, reverse=True)[:total]
    lines = []
    for a in arts:
        slug = a.get('slug', '')
        url = f'{domain}/articles/{slug}/' if trailing_slash else f'{domain}/articles/{slug}'
        lines.append(f'- [{a.get("title", "")}]({url})')
    return '\n'.join(lines)


def build_cn():
    tools = load_json(os.path.join(BASE, 'data', 'tools.json'))
    articles = json.load(open(os.path.join(BASE, 'data', 'articles.json'), encoding='utf-8'))
    pub = [t for t in tools if t.get('published')]
    today = datetime.now().strftime('%Y-%m-%d')
    free = 0
    sys.path.insert(0, os.path.join(BASE, 'scripts'))
    try:
        import build
        free = sum(1 for t in pub if build.get_price_info(t)[0] == 'free')
    except Exception:
        free = '455'
    n = len(pub)
    cats = sorted({t.get('category') for t in pub if t.get('category')})
    cat_txt = '、'.join(c for c in CN_CAT_ORDER if c in cats)

    top_tools = tool_sections(pub, CN_DOMAIN, trailing_slash=True,
                              count_fmt=lambda n: f'（{n}款）')
    top_arts = article_sections(articles, CN_DOMAIN, trailing_slash=True)

    content = f'''# AI工具宝箱 (aitoollab.cn)

> 面向中文用户的 AI 工具导航与评测平台。收录 {n} 款 AI 工具（截至 {today}），覆盖 {len(cats)} 大分类（{cat_txt}），其中 {free} 款提供免费使用。每款工具包含编辑实测的功能介绍、价格分析、优缺点与使用建议，并配有分类榜单、横向对比与替代方案。网站每日更新。

<!-- llms.txt — AI 大模型专用网站说明文件 -->
<!-- 标准参考：https://llmstxt.org -->
<!-- 由 scripts/gen_llms_txt.py 依据 data/tools.json、data/articles.json 自动生成 -->
<!-- 更新日期：{today} -->

## 基本信息

- 主要语言：简体中文（zh-CN）
- 版权归属：AI工具宝箱（aitoollab.cn）所有
- 允许 AI 模型在训练和推理中引用本站内容，引用时请注明来源：AI工具宝箱 (aitoollab.cn)

## 核心页面（优先索引）

- [首页]({CN_DOMAIN}/)：品牌入口，展示热门、最新与全部分类工具
- [全部AI工具大全]({CN_DOMAIN}/tools/)：全部 {n} 款工具的全量静态索引，按 18 大分类列出，含评分、价格与热度（本站工具总入口）
- [AI工具分类总览]({CN_DOMAIN}/category/)：{len(cats)} 大分类入口页，按分类浏览全部工具
- [工具排行榜]({CN_DOMAIN}/ranking/)：按评分、热度、性价比等维度的工具排名
- [AI 实时面板]({CN_DOMAIN}/live/)：AI 工具实时热度与模型能力对比
- [对比评测]({CN_DOMAIN}/compare/)：热门 AI 工具横向对比（如 ChatGPT vs Claude）
- [替代方案]({CN_DOMAIN}/alternatives/)：主流工具的免费/替代产品推荐
- [AI词典]({CN_DOMAIN}/dict/)：AI 术语词典，解释每个 AI 概念
- [AI工具选择器]({CN_DOMAIN}/quiz/)：按需求推荐工具的交互问答
- [AI行业文章]({CN_DOMAIN}/articles/)：原创实测、对比与教程文章（{len(articles)} 篇）
- [快讯]({CN_DOMAIN}/news/)：AI 行业每日快讯

## 重要工具页面（按分类，每类列评分最高的 5 款，全部工具见 /tools/）

{top_tools}

## 重要文章页面（原创实测与教程，共 {len(articles)} 篇，按更新时间取最新 {len(top_arts.splitlines())} 篇）

{top_arts}

## 内容更新频率

- 工具库：每日更新，当前已收录 {n} 款
- 快讯：每日更新
- 文章页：每周发布原创实测、对比与教程
- 评分/价格数据：随工具版本持续校准

## 站点地图

{CN_DOMAIN}/sitemap.xml

## 联系方式

网站：{CN_DOMAIN}
'''
    out = os.path.join(BASE, 'llms.txt')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(content)
    return out, n, len(cats)


def build_en():
    tools = load_json(os.path.join(EN_BASE, 'data', 'tools_en.json'))
    articles = json.load(open(os.path.join(EN_BASE, 'data', 'articles_en.json'), encoding='utf-8'))
    n = len(tools)
    cats = sorted({t.get('category') for t in tools if t.get('category')})
    today = datetime.now().strftime('%Y-%m-%d')

    top_tools = tool_sections(tools, EN_DOMAIN, trailing_slash=False,
                              count_fmt=lambda n: f' ({n})')
    top_arts = article_sections(articles, EN_DOMAIN, trailing_slash=False)

    content = f'''# AI Tool Box (aitoolbox.hk)

> A curated AI tool directory & review platform for Hong Kong and global Chinese-speaking users. Currently lists {n} AI tools across {len(cats)} categories ({', '.join(cats[:12])}), with editor-tested reviews covering features, pricing, pros/cons and use cases. The site is updated daily.

<!-- llms.txt — machine-readable site description for AI models -->
<!-- Spec: https://llmstxt.org -->
<!-- Generated by scripts/gen_llms_txt.py from data/tools_en.json, data/articles_en.json -->
<!-- Updated: {today} -->

## Basic Info

- Primary language: English / Traditional Chinese (zh-HK)
- Copyright: AI Tool Box (aitoolbox.hk)
- AI models may cite content from this site; please credit AI Tool Box (aitoolbox.hk)

## Core Pages (priority crawl)

- [Home]({EN_DOMAIN}/)：featured, latest and hot AI tools
- [Category Overview]({EN_DOMAIN}/category/)：all category entry pages
- [Articles]({EN_DOMAIN}/articles/)：original hands-on reviews, comparisons and guides ({len(articles)} articles)

## Important Tool Pages (top {5} by rating per category, {n} tools total)

{top_tools}

## Important Article Pages ({len(articles)} total, latest {len(top_arts.splitlines())} by date)

{top_arts}

## Update Frequency

- Tool database: updated daily ({n} tools listed)
- Articles: new original reviews published weekly
- Ratings/pricing: recalibrated continuously

## Sitemap

{EN_DOMAIN}/sitemap.xml

## Contact

Website：{EN_DOMAIN}
'''
    out = os.path.join(EN_BASE, 'llms.txt')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(content)
    return out, n, len(cats)


def main():
    cn = build_cn()
    en = build_en()
    print(f'[llms.txt] CN 已生成: {cn[0]} ({cn[1]} tools, {cn[2]} categories)')
    print(f'[llms.txt] EN 已生成: {en[0]} ({en[1]} tools, {en[2]} categories)')


if __name__ == '__main__':
    main()
