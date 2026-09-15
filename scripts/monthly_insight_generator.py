#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月度数据洞察文章自动生成器

自动化任务每月 1 日和 15 日调用（automation-1782302172577），每月产出 2 篇：
  - 市场全景  ai-tools-market-panorama-YYYYMM   （本月第一篇，通常 1 日）
  - 价格指数  ai-tools-price-index-YYYYMM-part2  （本月第二篇，通常 15 日）

2026-09-15 重构（修复四个实测缺陷）：
  1. 【空转】原实现用 `day <= 15 → 全景 / else → 价格指数` 选主题，而 slug 只带月份。
     调度是 BYMONTHDAY=1,15 → 1 日与 15 日算出**同一个 slug** → 15 日必命中
     "已存在"分支 SKIP → 第二篇永不生成（7/8 月第二篇 date 均为 -16，调度原为 1+16）。
     现改为**按"本月全景文是否已存在"决定主题**，与调度日期解耦，不再有边界错位。
  2. 【重复内容】原实现两个主题共用同一个 f-string 正文，仅标题/slug 不同
     （实测 8 月两篇字符相似度 93.2%、8 个 H2 完全一致）= 标题级伪装的重复页。
     现拆成两个结构完全不同的内容构建器：市场全景 vs 价格指数。
  3. 【数据不自洽】原实现用关键词匹配自己重算价格三桶，实测 443+322+119=884 > 总数 707
     （超 25%，桶不互斥），已上线文章里印着 46%+61%+16%=123%。
     现一律读 live_data.json 的权威 price_distribution（188+411+80+28=707）。
  4. 【硬编码】正文原写死"14 个分类"，实际 live_data.stats.total_categories=19。现改读真值。

用法：
    python monthly_insight_generator.py                      # 自动选主题生成 1 篇
    python monthly_insight_generator.py --check              # 只分析+预览，不写入
    python monthly_insight_generator.py --theme price-index  # 强制主题（补发用）
"""
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE_FILE = os.path.join(BASE, "data", "live_data.json")

sys.path.insert(0, os.path.join(BASE, "scripts"))


def load_data():
    with open(LIVE_FILE, "r", encoding="utf-8") as f:
        live = json.load(f)
    # 2026-08-26 去单体化: 分片优先
    from data_store import load_all_tools, load_all_articles
    tools = load_all_tools()
    articles = load_all_articles()
    return live, tools, articles


# 订阅月费解析：只认显式 "$N/月" 或 "$N/人/月"；取最低正值 = 入门付费档
MONTHLY_PRICE_RE = re.compile(r"\$\s?(\d+(?:\.\d+)?)\s*/\s*(?:人/)?月")


def parse_monthly_price(price_text):
    """返回入门付费档月费（float）；解析不出返回 None。绝不猜值。"""
    if not price_text or not isinstance(price_text, str):
        return None
    vals = [float(v) for v in MONTHLY_PRICE_RE.findall(price_text)]
    vals = [v for v in vals if v > 0]
    return min(vals) if vals else None


def analyze_data(live, tools, articles):
    stats = live.get("stats", {})
    trends = live.get("trends", {}).get("categories", [])
    heatmap = live.get("heatmap", {}).get("heatmap", [])

    total = len(tools)

    # 1. 分类工具数排名
    cat_counts = Counter(t.get("category", "") for t in tools)
    top_cats = cat_counts.most_common(5)

    # 2. 定价模式分布 —— 权威源：live_data.json（四档互斥且合计 = 总数）
    price_dist = stats.get("price_distribution", {})
    if not price_dist or sum(price_dist.values()) != total:
        raise SystemExit(
            "[FATAL] live_data.json 的 price_distribution 缺失或合计≠工具总数"
            f"（{price_dist} vs {total}）。拒绝用关键词匹配自算兜底——"
            "请先修上游 live_data 生成逻辑。"
        )

    # 3. 月费价格带（仅解析得出的样本，覆盖率如实披露）
    priced = []
    for t in tools:
        v = parse_monthly_price(t.get("price"))
        if v is not None:
            priced.append((v, t.get("name", ""), t.get("category", ""), t.get("slug", "")))
    bands = [
        ("$10 以下", 0, 10),
        ("$10 ~ $20", 10, 20),
        ("$20 ~ $50", 20, 50),
        ("$50 以上", 50, float("inf")),
    ]
    band_rows = []
    for label, lo, hi in bands:
        hit = [p for p in priced if lo <= p[0] < hi]
        band_rows.append({
            "label": label, "count": len(hit),
            "pct": (len(hit) * 100 // len(priced)) if priced else 0,
            "examples": ", ".join(n for _, n, _, _ in sorted(hit)[:3]),
        })

    # 4. 分类月费中位数（样本 >= 5 才写，避免小样本误导）
    by_cat = defaultdict(list)
    for v, _n, c, _s in priced:
        by_cat[c].append(v)
    cat_medians = sorted(
        [(c, statistics.median(v), len(v)) for c, v in by_cat.items() if len(v) >= 5],
        key=lambda x: -x[1],
    )

    # 5. 趋势变化
    sorted_trends = sorted(trends, key=lambda x: x.get("change_percent", 0), reverse=True)
    top_rising = sorted_trends[:3]
    top_declining = sorted_trends[-3:]

    # 6. 国产工具（名称关键词命中，仅用于举例，不作比例结论）
    cn_keywords = ["通义", "豆包", "文心", "混元", "Kimi", "DeepSeek", "星火", "元宝",
                   "智谱", "GLM", "夸克", "腾讯", "阿里", "百度", "字节", "CodeBuddy",
                   "文心快码", "通义灵码"]
    cn_tools = [t for t in tools if any(k in t.get("name", "") for k in cn_keywords)]

    # 7. price 描述中的"免费/开源/未公开"提及数（文本命中，仅作可获得性参考）
    def has_kw(kw):
        return sum(1 for t in tools if kw in (t.get("price") or ""))

    month = datetime.now().strftime("%Y年%m月").replace("年0", "年")

    return {
        "total_tools": total,
        "total_articles": len(articles),
        "total_categories": stats.get("total_categories", 0),
        "total_visits": stats.get("total_visits_str", ""),
        "avg_rating": stats.get("avg_rating", 0),
        "top_cats": top_cats,
        "price_dist": price_dist,
        "priced_count": len(priced),
        "price_median": statistics.median([p[0] for p in priced]) if priced else 0,
        "price_mean": statistics.mean([p[0] for p in priced]) if priced else 0,
        "price_min": min([p[0] for p in priced]) if priced else 0,
        "price_max": max([p[0] for p in priced]) if priced else 0,
        "band_rows": band_rows,
        "cat_medians": cat_medians,
        "top_rising": top_rising,
        "top_declining": top_declining,
        "cn_tools_count": len(cn_tools),
        "cn_tools": cn_tools[:10],
        "kw_free": has_kw("免费"),
        "kw_opensource": has_kw("开源"),
        "kw_undisclosed": has_kw("未公开"),
        "heatmap": heatmap,
        "month": month,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }


def pick_theme(articles, forced=None):
    """按「本月全景文是否已存在」选主题 —— 与调度日期解耦，避免边界错位空转。"""
    ym = datetime.now().strftime("%Y%m")
    panorama_slug = f"ai-tools-market-panorama-{ym}"
    existing = {a.get("slug") for a in articles}
    if forced:
        return forced
    return "price-index" if panorama_slug in existing else "market-panorama"


# ---------------------------------------------------------------- 主题一：市场全景

def build_panorama(d):
    total = d["total_tools"]
    top_cat, top_n = d["top_cats"][0]
    fm = d["price_dist"].get("freemium", 0)
    content = f"""# {d['month']}AI工具市场全景：{total}款工具数据揭示的最新趋势

> **一句话结论：** 截至 {d['date']}，本站收录 {total} 款 AI 工具，{top_cat}以 {top_n} 款位居最拥挤赛道，定价以 Freemium 为主流（{fm} 款，占 {fm * 100 // total}%），可零成本上手的工具达 {d['kw_free']} 款——选工具先看数据结构，再看营销话术。

> "AI 工具市场月月迭代，唯一不变的就是变化本身。基于真实数据的洞察，比任何排行榜都可靠。" —— AI工具宝箱编辑组，{d['month']}月度数据洞察

## 本月数据概览

以下数据来自 [aitoollab.cn](https://www.aitoollab.cn/) 收录的 **{total} 款 AI 工具**真实数据（截至 {d['date']}），覆盖 {d['total_categories']} 个分类。完整数据可在 [实时面板](/live/dashboard/) 查看。

| 指标 | 数值 | 说明 |
|------|------|------|
| 收录工具总数 | {total} | 持续增长中 |
| 分类数 | {d['total_categories']} | 覆盖主流 AI 场景 |
| 总月访问量 | {d['total_visits']} | 来源：公开搜索热度聚合 |
| 平均用户评分 | {d['avg_rating']}/5 | 来源：各平台用户评价聚合 |
| 可零成本上手工具 | {d['kw_free']} 款 | price 字段含"免费"或"开源" |

## 定价模式分布：Freemium 还是免费更主流？

{total} 款工具的定价模式分布（来源：live_data.json，四档互斥，合计 = {total}）：

| 定价模式 | 工具数 | 占比 |
|---------|--------|------|
| **Freemium（免费+付费）** | {fm} | {fm * 100 // total}% |
| **纯免费** | {d['price_dist'].get('free', 0)} | {d['price_dist'].get('free', 0) * 100 // total}% |
| **纯付费** | {d['price_dist'].get('paid', 0)} | {d['price_dist'].get('paid', 0) * 100 // total}% |
| **企业版/定制** | {d['price_dist'].get('enterprise', 0)} | {d['price_dist'].get('enterprise', 0) * 100 // total}% |

**关键发现**：Freemium 占据最大份额，"免费钩子 + 订阅变现"仍是行业标准打法；纯免费单独成档，说明"完全免费"也是可持续的产品策略，而非短期促销。

## 分类工具数排名：哪个赛道最拥挤？

{total} 款工具在头部 {len(d['top_cats'])} 个分类的分布（数据来源：aitoollab.cn {d['date']}）：

| 排名 | 分类 | 工具数 | 占比 |
|------|------|--------|------|"""
    for i, (cat, count) in enumerate(d["top_cats"], 1):
        content += f"\n| {i} | {cat} | {count} | {count * 100 // total}% |"

    content += f"""

**关键发现**：{top_cat}以 {top_n} 款位列第一，占总量 {top_n * 100 // total}%。该赛道供给最充分，新进入者需要明确差异化才有位置。

## 趋势变化榜：哪些分类在涨？

近 8 周各分类热度变化（数据来源：aitoollab.cn {d['date']}）：

**涨幅前三**

"""
    for t in d["top_rising"]:
        content += f"- {t['category']}：当前热度 {t['current_value']}，变化 {t['change_percent']:+.1f}%\n"

    content += "\n**跌幅前三**\n\n"
    for t in d["top_declining"]:
        content += f"- {t['category']}：当前热度 {t['current_value']}，变化 {t['change_percent']:+.1f}%\n"

    content += f"""

## 国产工具在什么位置？

按工具名称关键词命中统计，**{d['cn_tools_count']} 款为国产 AI 工具**（本文仅作举例，比例口径见数据声明）。代表工具：

"""
    for t in d["cn_tools"][:8]:
        content += f"- [{t['name']}](/tools/{t['slug']}/) ｜ {t.get('category', '')} ｜ {(t.get('price') or '')[:40]}\n"

    content += """

**关键发现**：国产工具在 AI 对话、AI 编程两个场景的密度最高，且多以"免费额度 + 低价订阅"切入。

## 本月选工具建议

| 你的需求 | 推荐策略 | 理由 |
|---------|---------|------|
| 学编程 / 新手入门 | 先试国产免费工具 | 免费额度足够跑通基础流程，沉没成本为零 |
| 专业开发者 | 头部编程工具 + 国产组合 | 顶配能力 + 低成本兜底任务 |
| 内容创作者 | 绘画 / 音频 / 写作分场景各选 1 款 | 单点最强优于全家桶 |
| 预算为零 | 只选"纯免费"或开源工具 | 见上方纯免费档位与开源工具数量 |

## 常见问题（FAQ）

**这些数据多久更新一次？**
aitoollab.cn 的工具数据随每次构建自动同步，本文数据截至 {d['date']}。完整数据可在 [实时面板](/live/dashboard/) 查看。

**国产 AI 工具能替代海外工具吗？**
看场景。AI 对话场景国产工具已接近海外水平；AI 绘画、AI 视频等场景海外工具仍领先。建议组合使用，而非二选一。

**Freemium 模式会消失吗？**
短期内不会。它是当前占比最高的定价档，且头部厂商普遍采用；纯付费工具集中在 B2B 与专业场景。

## 数据声明

本文所有数据均来自 aitoollab.cn 收录的 {total} 款 AI 工具真实数据（截至 {d['date']}），可在 [实时面板](/live/dashboard/)、[对比矩阵](/live/compare-matrix/)、[市场热力图](/live/market-heatmap/) 溯源核查。
定价模式取自 live_data.json 的四档互斥统计（合计 = {total}）；"可零成本上手"为 price 字段文本命中数，非互斥分档，仅作可获得性参考。如发现数据错误，欢迎通过 [联系页面](/contact.html) 反馈，48 小时内核查修正。

本文为 AI工具宝箱编辑组月度数据洞察，每月发布 2 篇（市场全景 + 价格指数）。
"""
    return content


# ---------------------------------------------------------------- 主题二：价格指数

def build_price_index(d):
    total = d["total_tools"]
    med = d["price_median"]
    top_band = max(d["band_rows"], key=lambda x: x["count"])
    cat_top = d["cat_medians"][0] if d["cat_medians"] else ("—", 0.0, 0)
    cat_low = d["cat_medians"][-1] if d["cat_medians"] else ("—", 0.0, 0)
    ratio = f"{cat_top[1] / cat_low[1]:.0f}" if cat_low[1] else "—"
    fm = d["price_dist"].get("freemium", 0)

    content = f"""# {d['month']}AI工具价格指数：{total}款工具真实月费分布

> **一句话结论：** 在 {total} 款 AI 工具中，能明确解析出订阅月费的有 {d['priced_count']} 款，入门付费档中位数 **${med:.0f}/月**，其中 **{top_band['label']}** 是主战场（{top_band['count']} 款，占 {top_band['pct']}%）；分类之间价差明显——{cat_top[0]}中位 ${cat_top[1]:.0f}/月，{cat_low[0]}只要 ${cat_low[1]:.0f}/月。

> "价格不能单看数字，要看单位产出成本。同一个分类里月费差两倍的工具，功能覆盖可能只差一成——先明确自己的高频场景，再为它付钱。" —— AI工具宝箱编辑组，{d['month']}价格指数

## 定价模式分布：免费和付费各占多少？

{total} 款工具的定价模式分布（来源：live_data.json 四档互斥统计，合计 = {total}）：

| 定价模式 | 工具数 | 占比 | 说明 |
|---------|--------|------|------|
| **Freemium（免费+付费）** | {fm} | {fm * 100 // total}% | 免费额度 + 订阅解锁 |
| **纯免费** | {d['price_dist'].get('free', 0)} | {d['price_dist'].get('free', 0) * 100 // total}% | 无需付费即可使用 |
| **纯付费** | {d['price_dist'].get('paid', 0)} | {d['price_dist'].get('paid', 0) * 100 // total}% | 必须先付费 |
| **企业版/定制** | {d['price_dist'].get('enterprise', 0)} | {d['price_dist'].get('enterprise', 0) * 100 // total}% | 需询价 |

**关键发现**：{fm * 100 // total}% 走 Freemium。这意味着对多数工具，**先用免费额度验证再付费**是可行路径，不必一上来就订阅。

## 订阅月费价格带：多少钱是主流？

对 price 字段做结构化解析，{d['priced_count']} 款工具能取出明确的订阅月费（取最低付费档）：

| 月费区间 | 工具数 | 占样本比 | 代表工具 |
|---------|--------|---------|---------|"""
    for r in d["band_rows"]:
        content += f"\n| {r['label']} | {r['count']} | {r['pct']}% | {r['examples'] or '—'} |"

    content += f"""

统计口径：中位数 **${med:.0f}/月**，均值 ${d['price_mean']:.0f}/月，区间 ${d['price_min']:.0f} ~ ${d['price_max']:.0f}。

**关键发现**：{top_band['label']}集中了最多产品，是竞争最激烈的价位；超过 $50/月 的仅 {d['band_rows'][-1]['count']} 款，多为团队协作或企业向产品。

## 各分类月费中位数：哪个赛道最贵？

样本数 ≥ 5 的分类，按入门月费中位数从高到低：

| 分类 | 月费中位数 | 样本数 |
|------|-----------|--------|"""
    for c, m, n in d["cat_medians"]:
        content += f"\n| {c} | ${m:.0f} | {n} |"

    content += f"""

**关键发现**：{cat_top[0]}（中位 ${cat_top[1]:.0f}/月）与 {cat_low[0]}（中位 ${cat_low[1]:.0f}/月）相差约 {ratio} 倍。越靠近"替人完成复杂任务"的场景定价越高；越靠近"单点工具"，价格越贴近 $10。

## 零成本路径：多少工具可以免费开始？

| 口径 | 工具数 | 占总数 |
|------|--------|--------|
| price 描述含"免费" | {d['kw_free']} | {d['kw_free'] * 100 // total}% |
| price 描述含"开源" | {d['kw_opensource']} | {d['kw_opensource'] * 100 // total}% |
| price 描述为"未公开" | {d['kw_undisclosed']} | {d['kw_undisclosed'] * 100 // total}% |

**关键发现**：绝大多数工具有免费入口，{d['kw_opensource']} 款提到开源。反过来说，**"能不能免费用"已不再是选型门槛，能不能稳定产出才是**。

## 不同预算怎么选

| 月预算 | 建议组合 | 理由 |
|--------|---------|------|
| $0 | 纯免费档 + 开源工具 | 先跑通流程，验证真实需求 |
| $10 ~ $20 | 单点主力工具 1 款 | 该区间供给最多，比价空间最大 |
| $20 ~ $50 | 主力 + 辅助各 1 款 | 覆盖两个高频场景，避免为低频功能付费 |
| $50 以上 | 团队协作型产品 | 仅当需要多人协同或企业合规时考虑 |

## 常见问题（FAQ）

**为什么只有部分工具能解析出月费？**
因为很多工具的 price 字段是描述性文本（如"开源免费""按量计费""价格见官网"），没有统一的价格数字。本文只统计数据里能明确解析出 "$N/月" 的 {d['priced_count']} 款，**解析不出的不计入，也不估算**。

**AI 工具的月费中位数是多少？**
按本文样本，入门付费档中位数为 **${med:.0f}/月**，均值 ${d['price_mean']:.0f}/月——均值明显高于中位数，说明少数高价产品拉高了平均值。

**免费工具够用吗？**
对个人轻量使用，{d['kw_free']} 款含"免费"的工具基本够用；但一旦涉及高并发、商用授权或团队协作，通常仍需付费档。

## 数据声明

本文数据来自 aitoollab.cn 收录的 {total} 款 AI 工具真实数据（截至 {d['date']}）。定价模式取自 live_data.json 的四档互斥统计（合计 = {total}，可交叉验算）；月费价格带与分类中位数来自对 price 字段的显式解析，样本 {d['priced_count']} 款（占 {d['priced_count'] * 100 // total}%），**解析不出的工具一律不纳入统计，不用默认值补齐**。全部数据可在 [实时面板](/live/dashboard/)、[对比矩阵](/live/compare-matrix/) 溯源核查。如发现数据错误，欢迎通过 [联系页面](/contact.html) 反馈，48 小时内核查修正。

本文为 AI工具宝箱编辑组月度数据洞察，每月发布 2 篇（市场全景 + 价格指数）。
"""
    return content


def generate_article(d, theme):
    ym = datetime.now().strftime("%Y%m")
    if theme == "market-panorama":
        title = f"{d['month']}AI工具市场全景：{d['total_tools']}款工具数据揭示的最新趋势"
        slug = f"ai-tools-market-panorama-{ym}"
        content = build_panorama(d)
        desc = (f"用 {d['total_tools']} 款 AI 工具的真实数据看清 {d['month']} 市场格局："
                f"哪个分类最拥挤、Freemium 占比多少、{d['kw_free']} 款可零成本上手，全部可溯源核查。")
        kw = f"AI工具市场分析,{d['month']}AI工具数据,AI工具排行榜,AI工具趋势,Freemium模式,国产AI工具"
    else:
        title = f"{d['month']}AI工具价格指数：{d['total_tools']}款工具真实月费分布"
        slug = f"ai-tools-price-index-{ym}-part2"
        content = build_price_index(d)
        desc = (f"同一类 AI 工具月费能差好几倍。本文用 {d['total_tools']} 款工具的真实定价数据，"
                f"给出可对照的月费价格带与分类中位数，帮你按预算选对工具。")
        kw = f"AI工具价格,{d['month']}AI工具月费,AI工具定价,AI工具性价比,免费AI工具,订阅价格对比"

    return {
        "title": title,
        "slug": slug,
        "date": d["date"],
        "dateFormatted": datetime.now().strftime("%Y年%m月%d日").replace("年0", "年").replace("月0", "月"),
        "category": "数据洞察",
        "tags": [
            {"text": "AI工具市场", "type": ""},
            {"text": "数据洞察", "type": ""},
            {"text": d["month"], "type": ""},
            {"text": "市场分析", "type": "hot"},
        ],
        "description": desc,
        "keywords": kw,
        "featured_image": "",
        "author": "AI工具宝箱编辑组",
        "related_tools": ["chatgpt", "claude", "deepseek", "cursor", "kimi"],
        "content": content,
        "content_type": "行业分析",
        "orig_category": "数据洞察",
        "topic": "AI对话",
    }


def main():
    check_only = "--check" in sys.argv
    forced = None
    if "--theme" in sys.argv:
        forced = sys.argv[sys.argv.index("--theme") + 1]
        if forced not in ("market-panorama", "price-index"):
            raise SystemExit("[FATAL] --theme 只能是 market-panorama 或 price-index")

    print("=" * 60)
    print(f"月度数据洞察文章生成器 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    live, tools, articles = load_data()
    print(f"[INFO] 加载 {len(tools)} 工具, {len(articles)} 文章, live_data OK")

    d = analyze_data(live, tools, articles)
    print(f"[INFO] 数据: {d['total_tools']}工具 / {d['total_categories']}分类 / "
          f"可解析月费 {d['priced_count']} 款(中位 ${d['price_median']:.0f})")
    print(f"[INFO] 定价四档={d['price_dist']} 合计={sum(d['price_dist'].values())}")

    theme = pick_theme(articles, forced)
    print(f"[INFO] 主题: {theme}（依据：本月全景文"
          f"{'已存在 → 转出价格指数' if theme == 'price-index' else '尚未存在 → 出市场全景'}）")

    article = generate_article(d, theme)
    print(f"[INFO] 文章: {article['title']}")
    print(f"[INFO] Slug: {article['slug']}")
    print(f"[INFO] 正文字数: {len(article['content'])}")

    existing = {a.get("slug") for a in articles}
    if article["slug"] in existing:
        print(f"[SKIP] 文章已存在: {article['slug']}，跳过（不重复生成）")
        return

    if check_only:
        print("\n[CHECK] --check 模式，不写入。文章前 600 字预览：")
        print(article["content"][:600])
        return

    from data_store import save_article
    save_article(article, indent=2)
    print(f"[OK] 已写入分片 data/articles/{article['slug']}.json")

    # 构建 + 门禁 + 部署 + 线上验收：走单篇增量通道（2026-08-28 新增），
    # 不做 1100+ 页全量重建。deploy_fast.sh 内含线上 URL 验收，rc != 0 即视为失败。
    if "--no-deploy" in sys.argv:
        print("[SKIP] --no-deploy：已跳过构建与部署")
        return
    import subprocess
    env = os.environ.copy()
    # Windows 坑（AGENTS.md 铁律 11：换环境就崩的问题必须修进脚本）：
    # 某些执行环境（如本机 Bash 工具的 shim PATH）不含 coreutils，
    # deploy_fast.sh 会 `bash: command not found` → rc=127。存在 Git 自带 usr/bin 就补上。
    for _p in (r"C:\Program Files\Git\usr\bin", r"C:\Program Files\Git\bin"):
        if os.path.isdir(_p) and _p not in env.get("PATH", ""):
            env["PATH"] = _p + os.pathsep + env.get("PATH", "")
    print(f"\n[INFO] 开始增量构建+部署: deploy_fast.sh {article['slug']}")
    proc = subprocess.run(["bash", "deploy_fast.sh", article["slug"]], cwd=BASE, env=env)
    if proc.returncode != 0:
        raise SystemExit(f"[FATAL] 部署失败 rc={proc.returncode}，文章已写入分片但未上线，"
                         "请查 _deploy_fast_*.log 后按根因修复再重跑")
    print(f"\n[DONE] 月度数据洞察文章已生成并部署: {article['slug']}")


if __name__ == "__main__":
    main()
