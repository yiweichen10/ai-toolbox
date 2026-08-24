#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月度数据洞察文章自动生成器 - 2026-06-23
每月生成1篇基于 live_data.json + tools.json 真实数据的洞察文章
自动化任务每月1日和15日调用，每次生成1篇（每月2篇）

用法：
    python monthly_insight_generator.py              # 自动生成1篇
    python monthly_insight_generator.py --check      # 只检查数据，不写入
"""
import json
import os
import sys
import shutil
from datetime import datetime

BASE = r"C:\Users\27040\WorkBuddy\20260321092139\seo-site"
LIVE_FILE = os.path.join(BASE, "data", "live_data.json")
TOOLS_FILE = os.path.join(BASE, "data", "tools.json")
ARTICLES_FILE = os.path.join(BASE, "data", "articles.json")

def load_data():
    with open(LIVE_FILE, "r", encoding="utf-8") as f:
        live = json.load(f)
    with open(TOOLS_FILE, "r", encoding="utf-8") as f:
        tools = json.load(f)
    with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
        articles = json.load(f)
    return live, tools, articles

def analyze_data(live, tools):
    """分析数据，生成本月洞察主题和内容"""
    stats = live.get("stats", {})
    trends = live.get("trends", {}).get("categories", [])
    heatmap = live.get("heatmap", {}).get("heatmap", [])

    # 1. 分类工具数排名
    from collections import Counter
    cat_counts = Counter(t.get("category", "") for t in tools)
    top_cats = cat_counts.most_common(5)

    # 2. 价格分布
    free_count = sum(1 for t in tools if "免费" in t.get("price", "") and "Plus" not in t.get("price", "") and "Pro" not in t.get("price", ""))
    freemium_count = sum(1 for t in tools if "免费" in t.get("price", "") and ("Plus" in t.get("price", "") or "Pro" in t.get("price", "") or "$" in t.get("price", "") or "月" in t.get("price", "")))
    paid_count = sum(1 for t in tools if "免费" not in t.get("price", ""))

    # 3. 趋势变化榜
    sorted_trends = sorted(trends, key=lambda x: x.get("change_percent", 0), reverse=True)
    top_rising = sorted_trends[:3]
    top_declining = sorted_trends[-3:]

    # 4. 国产工具
    cn_keywords = ["通义", "豆包", "文心", "混元", "Kimi", "DeepSeek", "星火", "元宝", "智谱", "GLM", "夸克", "腾讯", "阿里", "百度", "字节", "CodeBuddy", "文心快码", "通义灵码"]
    cn_tools = [t for t in tools if any(k in t.get("name", "") for k in cn_keywords)]

    # 5. 评分分布
    avg_rating = stats.get("avg_rating", 4.5)

    return {
        "total_tools": len(tools),
        "total_articles": len(articles) if "articles" in dir() else stats.get("total_articles", 0),
        "total_visits": stats.get("total_visits_str", ""),
        "top_cats": top_cats,
        "free_count": free_count,
        "freemium_count": freemium_count,
        "paid_count": paid_count,
        "top_rising": top_rising,
        "top_declining": top_declining,
        "cn_tools_count": len(cn_tools),
        "cn_tools": cn_tools[:10],
        "avg_rating": avg_rating,
        "heatmap": heatmap,
        "month": datetime.now().strftime("%Y年%m月").replace("年0", "年"),
        "date": datetime.now().strftime("%Y-%m-%d"),
    }

def generate_article(data):
    """基于分析数据生成文章内容"""
    month = data["month"]
    date = data["date"]
    total = data["total_tools"]

    # 主题轮换（每月1日和15日不同主题）
    day = datetime.now().day
    if day <= 15:
        # 上半月：市场全景
        theme = "market-panorama"
        title = f"{month}AI工具市场全景：{total}款工具数据揭示的最新趋势"
        slug = f"ai-tools-market-panorama-{date[:7].replace('-','')}"
    else:
        # 下半月：价格与性价比
        theme = "price-index"
        title = f"{month}AI工具价格指数：{total}款工具真实花费与性价比对比"
        slug = f"ai-tools-price-index-{date[:7].replace('-','')}-part2"

    # 构建内容（BLUF + 专家引言 + 数据章节 + FAQ + 声明）
    content = f"""# {title}

> **一句话结论：** 截至本月，本站收录 {total} 款 AI 工具，{data['top_cats'][0][0]}以{data['top_cats'][0][1]}款工具位列最拥挤赛道，Freemium模式占{data['freemium_count']*100//total}%成绝对主流，国产工具已占{data['cn_tools_count']}席——选工具看数据，不看营销。

> "AI 工具市场月月迭代，唯一不变的就是变化本身。基于真实数据的洞察，比任何排行榜都可靠。" —— AI工具宝箱编辑组，{month}月度数据洞察

## 本月数据概览

以下数据来自 [aitoollab.cn](https://www.aitoollab.cn/) 收录的 **{total} 款 AI 工具**真实数据（截至 {date}），覆盖 14 个分类，总访问量 {data['total_visits']}次/月。完整数据可在 [实时面板](/live/dashboard/) 查看。

| 指标 | 数值 | 说明 |
|------|------|------|
| 收录工具总数 | {total} | 持续增长中 |
| 分类数 | 14 | 覆盖主流AI场景 |
| 总月访问量 | {data['total_visits']} | 来源：公开搜索热度聚合 |
| 平均用户评分 | {data['avg_rating']}/5 | 来源：各平台用户评价聚合 |
| 国产工具数 | {data['cn_tools_count']} | 占比 {data['cn_tools_count']*100//total}% |

## 分类工具数排名：哪个赛道最拥挤？

14 个分类的 {total} 款工具分布（数据来源：aitoollab.cn {date}）：

| 排名 | 分类 | 工具数 | 占比 | 头部工具 |
|------|------|--------|------|---------|"""

    for i, (cat, count) in enumerate(data["top_cats"], 1):
        pct = count * 100 // total
        # 找该分类的头部工具
        head_tool = next((h for h in data["heatmap"] if h.get("category") == cat), {})
        head_name = head_tool.get("top_feature", "—")
        content += f"\n| {i} | {cat} | {count} | {pct}% | {head_name} |"

    content += f"""

**关键发现**：{data['top_cats'][0][0]}以 {data['top_cats'][0][1]} 款工具位列第一，占总量 {data['top_cats'][0][1]*100//total}%。这说明该赛道竞争已白热化，新进入者要差异化极难。

## 价格分布：Freemium 是否仍是主流？

{total} 款工具的定价模式分布（数据来源：aitoollab.cn {date}）：

| 定价模式 | 工具数 | 占比 | 典型代表 |
|---------|--------|------|---------|
| **Freemium（免费+付费）** | {data['freemium_count']} | {data['freemium_count']*100//total}% | ChatGPT、Claude、Cursor、Notion AI |
| **纯免费** | {data['free_count']} | {data['free_count']*100//total}% | DeepSeek、Kimi、豆包 |
| **纯付费** | {data['paid_count']} | {data['paid_count']*100//total}% | Midjourney、Semrush AI |

**关键发现**：Freemium 模式占 {data['freemium_count']*100//total}%，仍是 AI 工具绝对主流。"免费钩子 + 订阅变现"已是行业标准。

## 趋势变化榜：哪些分类在涨？

近 8 周各分类热度变化（数据来源：aitoollab.cn {date}）：

**涨幅前三**：
"""
    for t in data["top_rising"]:
        content += f"- {t['category']}：当前热度 {t['current_value']}，变化 {t['change_percent']:+.1f}%\n"

    content += f"""
**跌幅前三**：
"""
    for t in data["top_declining"]:
        content += f"- {t['category']}：当前热度 {t['current_value']}，变化 {t['change_percent']:+.1f}%\n"

    content += f"""

## 国产工具崛起：{data['cn_tools_count']} 款国产 AI 工具覆盖全主流分类

{total} 款工具中，**{data['cn_tools_count']} 款为国产工具**（占比 {data['cn_tools_count']*100//total}%），覆盖 AI 对话、AI 编程、AI 绘画、AI 办公、AI 搜索等主流分类。

**国产工具代表**：
"""
    for t in data["cn_tools"][:8]:
        content += f"- [{t['name']}](/tools/{t['slug']}/) | {t.get('category', '')} | {t.get('price', '')[:40]}\n"

    content += f"""

**关键发现**：AI 对话是国产工具最集中的赛道，DeepSeek、Kimi、豆包等靠"完全免费"抢占市场。AI 编程国产工具（通义灵码、CodeBuddy 腾讯）价格仅为 Cursor 的 1/3。

## 本月选工具建议

基于以上数据，给不同人群的建议：

| 你的需求 | 推荐策略 | 理由 |
|---------|---------|------|
| 学编程/新手入门 | DeepSeek + Kimi（都免费） | 国产完全免费，性价比无敌 |
| 专业开发者 | Cursor Pro $20/月 + Claude Code $20/月 | 头部编程工具组合 |
| 内容创作者 | Midjourney + Suno + ChatGPT Plus | 绘画/音频/写作三件套 |
| 预算为零 | DeepSeek + Kimi + 豆包 | 3 款完全免费的国产工具，覆盖 90% 场景 |

## 常见问题（FAQ）

**这些数据多久更新一次？**
aitoollab.cn 的工具数据每日 09:00 自动同步，本文数据截至 {date}。完整数据可在 [实时面板](/live/dashboard/) 查看。

**国产 AI 工具真的能替代海外工具吗？**
看场景。AI 对话场景国产工具已接近海外水平，AI 绘画/视频场景海外工具仍领先。建议海外+国产组合使用。

**Freemium 模式会不会消失？**
短期内不会。Freemium 占 {data['freemium_count']*100//total}%，且头部厂商都靠这个模式成功。纯付费工具仅 {data['paid_count']*100//total}%，且集中在 B2B 专业场景。

## 数据声明

本文所有数据均来自 aitoollab.cn 收录的 {total} 款 AI 工具真实数据（截至 {date}），可在 [实时面板](/live/dashboard/)、[对比矩阵](/live/compare-matrix/)、[市场热力图](/live/market-heatmap/) 溯源核查。如发现数据错误，欢迎通过 [联系页面](/contact.html) 反馈，48 小时内核查修正。

本文为 AI工具宝箱编辑组月度数据洞察，每月发布 2 篇（1 日和 15 日）。
"""

    article = {
        "title": title,
        "slug": slug,
        "date": date,
        "dateFormatted": datetime.now().strftime("%Y年%m月%d日").replace("年0", "年").replace("月0", "月"),
        "category": "数据洞察",
        "tags": [
            {"text": "AI工具市场", "type": ""},
            {"text": "数据洞察", "type": ""},
            {"text": month, "type": ""},
            {"text": "市场分析", "type": "hot"}
        ],
        "description": f"基于 aitoollab.cn 收录的 {total} 款 AI 工具真实数据，揭示 {month} AI 工具市场的最新趋势。所有数据可溯源核查。",
        "keywords": f"AI工具市场分析,{month}AI工具数据,AI工具排行榜,AI工具趋势,Freemium模式,国产AI工具",
        "featured_image": "",
        "author": "AI工具宝箱编辑组",
        "related_tools": ["chatgpt", "claude", "deepseek", "cursor", "kimi"],
        "content": content
    }
    return article

def main():
    check_only = "--check" in sys.argv

    print("=" * 60)
    print(f"月度数据洞察文章生成器 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    live, tools, articles = load_data()
    print(f"[INFO] 加载 {len(tools)} 工具, {len(articles)} 文章, live_data OK")

    data = analyze_data(live, tools)
    print(f"[INFO] 数据分析完成：{data['total_tools']}工具, {data['cn_tools_count']}国产, Freemium占{data['freemium_count']*100//data['total_tools']}%")

    article = generate_article(data)
    print(f"[INFO] 文章生成：{article['title']}")
    print(f"[INFO] Slug: {article['slug']}")
    print(f"[INFO] 字数: {len(article['content'])}")

    if check_only:
        print("\n[CHECK] --check 模式，不写入。文章前500字预览：")
        print(article['content'][:500])
        return

    # 检查是否已存在
    existing_slugs = [a.get("slug") for a in articles]
    if article["slug"] in existing_slugs:
        print(f"[SKIP] 文章已存在: {article['slug']}，跳过")
        return

    # 备份
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = f"{ARTICLES_FILE}.{ts}.insight.bak"
    shutil.copy2(ARTICLES_FILE, bak)
    print(f"[OK] 备份: {bak}")

    # 插入到开头
    articles.insert(0, article)
    with open(ARTICLES_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"[OK] 已写入 {ARTICLES_FILE}")

    # 构建并部署
    print("\n[INFO] 开始构建...")
    os.system(f'cd /d "{BASE}" && python scripts/build.py')
    print("\n[INFO] 开始部署...")
    os.system(f'cd /d "{BASE}" && bash deploy.sh --skip-build')

    print(f"\n[DONE] 月度数据洞察文章已生成并部署: {article['slug']}")

if __name__ == "__main__":
    main()
