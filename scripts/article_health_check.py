#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章健康度检查脚本 - 2026-06-24
每月自动检查文章质量，生成健康度报告：
1. 哪些文章缺BLUF/引言/FAQ（AEO+GEO合规性）
2. 哪些工具页缺实测数据区块
3. 哪些文章数据可能过期（>3个月未更新）
4. 文章分类标签分布

用法：
    python article_health_check.py              # 执行检查
    python article_health_check.py --report     # 查看历史报告
"""
import json
import csv
import os
from datetime import datetime
from pathlib import Path
from collections import Counter

BASE_DIR = Path(r"C:\Users\27040\WorkBuddy\20260321092139\seo-site")
ARTICLES_FILE = BASE_DIR / "data" / "articles.json"
TOOLS_FILE = BASE_DIR / "data" / "tools.json"
REPORT_DIR = BASE_DIR / "data" / "health_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# AEO+GEO必备元素
REQUIRED_ELEMENTS = {
    "BLUF": ["一句话结论", "Bottom line", "结论先说", "结论："],
    "专家引言": ["> \"", "> —"],
    "FAQ": ["## 常见问题", "## FAQ", "## Frequently Asked"],
    "数据来源": ["来源", "数据来源", "Source:", "实测"],
    "最终结论": ["## 最终", "## 总结", "## Final", "## 最终结论"],
}

def load_data():
    with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
        articles = json.load(f)
    with open(TOOLS_FILE, "r", encoding="utf-8") as f:
        tools = json.load(f)
    return articles, tools

def check_article_health(article):
    """检查单篇文章的AEO+GEO合规性"""
    content = article.get("content", "")
    slug = article.get("slug", "")
    title = article.get("title", "")
    date = article.get("date", "")
    category = article.get("category", "")

    issues = []

    # 检查必备元素
    for element, patterns in REQUIRED_ELEMENTS.items():
        found = any(p in content for p in patterns)
        if not found:
            issues.append(f"缺{element}")

    # 检查字数
    if len(content) < 1500:
        issues.append(f"字数偏少({len(content)})")

    # 检查H2数量
    h2s = [l.strip() for l in content.split("\n") if l.strip().startswith("## ") and not l.strip().startswith("### ")]
    if len(h2s) < 3:
        issues.append(f"H2偏少({len(h2s)})")

    # 检查数据时效性（>3个月）
    if date:
        try:
            article_date = datetime.strptime(date[:10], "%Y-%m-%d")
            days_old = (datetime.now() - article_date).days
            if days_old > 90:
                issues.append(f"数据可能过期({days_old}天)")
        except:
            pass

    return {
        "slug": slug[:40],
        "title": title[:50],
        "category": category,
        "date": date[:10] if date else "",
        "content_length": len(content),
        "h2_count": len(h2s),
        "issues": "; ".join(issues) if issues else "✅ 合格",
        "issue_count": len(issues),
    }

def check_tool_health(tool):
    """检查单个工具页是否有实测数据"""
    content = tool.get("content", "")
    slug = tool.get("slug", "")
    name = tool.get("name", "")

    has_test_data = "实测数据" in content or "Test Data" in content
    has_faq = "FAQ" in content or "常见问题" in content

    return {
        "slug": slug[:40],
        "name": name[:30],
        "has_test_data": has_test_data,
        "has_faq": has_faq,
        "needs_update": not has_test_data,
    }

def run_check():
    print("=" * 60)
    print(f"文章健康度检查 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    articles, tools = load_data()
    print(f"[INFO] 加载 {len(articles)} 篇文章, {len(tools)} 个工具")

    # 1. 检查文章健康度
    print("\n--- 文章健康度检查 ---")
    article_results = []
    issue_count = 0
    for a in articles:
        result = check_article_health(a)
        article_results.append(result)
        if result["issue_count"] > 0:
            issue_count += 1

    print(f"  总文章: {len(articles)}")
    print(f"  有问题: {issue_count}")
    print(f"  合格率: {(len(articles)-issue_count)*100//len(articles)}%")

    # 按问题数排序，显示Top10问题文章
    sorted_results = sorted(article_results, key=lambda x: x["issue_count"], reverse=True)
    print(f"\n  问题最多Top10:")
    for r in sorted_results[:10]:
        if r["issue_count"] > 0:
            print(f"    {r['slug'][:35]:<35} | {r['issues'][:50]}")

    # 2. 检查工具页实测数据
    print("\n--- 工具页实测数据检查 ---")
    tool_results = []
    tools_without_data = []
    for t in tools:
        result = check_tool_health(t)
        tool_results.append(result)
        if result["needs_update"]:
            tools_without_data.append(t["name"])

    print(f"  总工具: {len(tools)}")
    print(f"  有实测数据: {len(tools)-len(tools_without_data)}")
    print(f"  缺实测数据: {len(tools_without_data)}")

    # 3. 文章分类分布
    print("\n--- 文章分类分布 ---")
    cat_counts = Counter(a.get("category", "") for a in articles)
    for cat, count in cat_counts.most_common(10):
        print(f"  {cat:<20} | {count} 篇")

    # 4. 生成CSV报告
    report_date = datetime.now().strftime("%Y-%m-%d")

    # 文章健康度报告
    article_csv = REPORT_DIR / f"article_health_{report_date}.csv"
    with open(article_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["slug", "title", "category", "date", "content_length", "h2_count", "issues", "issue_count"])
        writer.writeheader()
        writer.writerows(article_results)

    # 工具页报告
    tool_csv = REPORT_DIR / f"tool_health_{report_date}.csv"
    with open(tool_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["slug", "name", "has_test_data", "has_faq", "needs_update"])
        writer.writeheader()
        writer.writerows(tool_results)

    # 汇总报告
    summary_file = REPORT_DIR / "health_summary.csv"
    file_exists = summary_file.exists()
    with open(summary_file, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "total_articles", "articles_with_issues", "article_pass_rate", "total_tools", "tools_with_data", "tools_needing_update"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "date": report_date,
            "total_articles": len(articles),
            "articles_with_issues": issue_count,
            "article_pass_rate": f"{(len(articles)-issue_count)*100//len(articles)}%",
            "total_tools": len(tools),
            "tools_with_data": len(tools)-len(tools_without_data),
            "tools_needing_update": len(tools_without_data),
        })

    print(f"\n--- 报告文件 ---")
    print(f"  文章健康度: {article_csv}")
    print(f"  工具页健康度: {tool_csv}")
    print(f"  汇总报告: {summary_file}")
    print(f"\n[DONE] 健康度检查完成")

def show_report():
    """显示历史报告"""
    summary_file = REPORT_DIR / "health_summary.csv"
    if not summary_file.exists():
        print("暂无历史报告")
        return

    print("=" * 60)
    print("文章健康度历史报告")
    print("=" * 60)

    with open(summary_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("暂无数据")
        return

    print(f"\n{'日期':<12} {'文章总数':<8} {'有问题':<8} {'合格率':<8} {'工具总数':<8} {'有数据':<8} {'待更新':<8}")
    print("-" * 70)
    for r in rows:
        print(f"{r['date']:<12} {r['total_articles']:<8} {r['articles_with_issues']:<8} {r['article_pass_rate']:<8} {r['total_tools']:<8} {r['tools_with_data']:<8} {r['tools_needing_update']:<8}")

    print(f"\n报告目录: {REPORT_DIR}")

if __name__ == "__main__":
    import sys
    if "--report" in sys.argv:
        show_report()
    else:
        run_check()
