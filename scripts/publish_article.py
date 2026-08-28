#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动发布入库校验脚本（2026-08-18 立）：替代人工确认环节，把一篇新文章草稿
校验通过后写入分片 data/articles/<slug>.json（2026-08-26 去单体化：单体 data/articles.json 已退役，
分片才是真源，统一走 data_store.save_article）。任何校验不通过都不写文件并返回非 0，
由「SEO 选题写稿与自动发布」定时任务在发布链路中调用。

用法:
  python scripts/publish_article.py --draft tmp/<slug>.json [--dry-run]

  --dry-run  只校验，不写文件

退出码:
  0  校验通过（--dry-run 时仅通过、未写文件）
  2  校验失败（未写文件）
"""

import argparse
import datetime
import io
import json
import os
import re
import sys

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
# 单体已退役（2026-08-26）：不再定义 data/articles.json、data/tools.json 路径常量，读写一律走 data_store
ARTICLE_IMAGES_DIR = os.path.join(BASE, "images", "articles")

VALID_CONTENT_TYPES = ("AI评测", "AI教程", "AI资讯", "行业分析")
RESERVED_SLUGS = {"reviews", "tutorials", "news", "analysis", "page", "index", "404"}

# 写作铁律禁止的 AI 味表达（与 SEO-CONTENT-TODO.md / 定时任务 prompt 一致）
AI_FLAVOR_PATTERNS = [
    ("在当今", r"在当今"),
    ("值得注意的是", r"值得注意的是"),
    ("赋能", r"赋能"),
    ("一站式", r"一站式"),
    ("总而言之", r"总而言之"),
    ("综上所述", r"综上所述"),
    ("不可否认", r"不可否认"),
    ("让我们一起", r"让我们一起"),
    ("随着…的背景下", r"随着[^。，；!?！？]{0,15}(背景|时代|发展)"),
]

BANNED_FAQ_HEADINGS = ("## 常见问题", "## FAQ", "## 常见问题（FAQ）", "## 常见问题(FAQ)")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
LINK_RE = re.compile(r"\[([^\]]+)\]\(((?:https?://|/)[^)]+)\)")
PLACEHOLDER_RE = re.compile(r"【图\s*\d+\s*[：:]")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def today_str():
    return datetime.date.today().isoformat()


def check_required_fields(a, errors):
    required = [
        "title", "seo_title", "slug", "date", "dateFull", "category",
        "content_type", "tags", "summary", "description", "keywords",
        "author", "faq", "content",
    ]
    for key in required:
        val = a.get(key)
        if val is None or (isinstance(val, (list, dict)) and not val) or (isinstance(val, str) and not val.strip()):
            errors.append(f"缺少必填字段: {key}")


def check_slug(a, existing_slugs, errors):
    slug = a.get("slug", "")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,79}", slug):
        errors.append("slug 必须是小写字母/数字/连字符，3-80 位")
        return
    if slug in RESERVED_SLUGS:
        errors.append(f"slug 与内容分类目录冲突: {slug}")
    if slug in existing_slugs:
        errors.append(f"slug 已存在: {slug}")


def check_titles(a, existing_titles, errors):
    title = a.get("title", "")
    seo_title = a.get("seo_title", "")
    if len(title) > 60:
        errors.append(f"title 超 60 字（当前 {len(title)}）: {title}")
    if len(seo_title) > 60:
        errors.append(f"seo_title 超 60 字（当前 {len(seo_title)}）: {seo_title}")
    if title and title.casefold() in existing_titles:
        errors.append(f"与已有文章标题重复: {title}")


def check_dates(a, errors):
    date = a.get("date", "")
    date_full = a.get("dateFull", "")
    today = today_str()
    if date != today:
        errors.append(f"date 必须为今天（{today}），当前: {date}")
    if date_full != today:
        errors.append(f"dateFull 必须为今天（{today}），当前: {date_full}")


def check_content(a, errors):
    content = a.get("content", "")
    if not content:
        return
    length = len(content)
    if length < 600:
        errors.append(f"正文过短（{length} 字，要求 800-1500 字，下限 600）")
    elif length > 2200:
        errors.append(f"正文过长（{length} 字，要求 800-1500 字）")
    if "## " not in content:
        errors.append("正文缺少 h2 标题层级")
    for heading in BANNED_FAQ_HEADINGS:
        if heading in content:
            errors.append(f"正文不得包含「{heading}」小节（FAQ 请写入 faq 字段）")
    for m in PLACEHOLDER_RE.finditer(content):
        errors.append(f"正文残留未替换的配图占位: {m.group(0)}")


def check_images(a, errors):
    content = a.get("content", "")
    slug = a.get("slug", "")
    images = IMAGE_RE.findall(content)
    expected_prefix = f"https://www.aitoollab.cn/images/articles/{slug}/"
    for alt, url in images:
        if not url.startswith(expected_prefix):
            errors.append(f"配图 URL 必须形如 {expected_prefix}...，当前: {url}")
            continue
        rel = url[len(expected_prefix):]
        if "/" in rel or not rel.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            errors.append(f"配图文件名非法: {rel}")
            continue
        local = os.path.join(ARTICLE_IMAGES_DIR, slug, rel)
        if not os.path.isfile(local):
            errors.append(f"配图文件不存在: {local}")
    if not images:
        errors.append("正文没有配图（文章必须至少 1 张图）")
    elif a.get("content_type") == "AI教程" and len(images) < 2:
        errors.append("教程类文章必须 2-4 张配图")
    elif len(images) > 4:
        errors.append(f"配图过多（{len(images)} 张，上限 4 张）")


def check_faq(a, errors):
    faq = a.get("faq", [])
    if not isinstance(faq, list) or not (3 <= len(faq) <= 5):
        errors.append(f"FAQ 必须是 3-5 条，当前 {len(faq) if isinstance(faq, list) else '非列表'}")
        return
    seen_q = set()
    for i, item in enumerate(faq, 1):
        q = (item or {}).get("question", "")
        ans = (item or {}).get("answer", "")
        if not q or not ans:
            errors.append(f"FAQ 第 {i} 条缺少 question/answer")
            continue
        if len(q) > 80:
            errors.append(f"FAQ 第 {i} 条 question 过长（{len(q)} 字）")
        if len(ans) < 20:
            errors.append(f"FAQ 第 {i} 条 answer 过短（{len(ans)} 字）")
        if q.casefold() in seen_q:
            errors.append(f"FAQ 第 {i} 条 question 重复: {q}")
        seen_q.add(q.casefold())


def check_related_tools(a, tool_slugs, errors):
    related = a.get("related_tools") or []
    if not isinstance(related, list):
        errors.append("related_tools 必须是数组")
        return
    for slug in related:
        if slug not in tool_slugs:
            errors.append(f"related_tools 指向不存在的工具 slug: {slug}")


def check_meta(a, errors):
    ct = a.get("content_type", "")
    if ct not in VALID_CONTENT_TYPES:
        errors.append(f"content_type 必须是 {'/'.join(VALID_CONTENT_TYPES)} 之一，当前: {ct}")
    if not a.get("category"):
        errors.append("缺少 category")
    tags = a.get("tags", [])
    if not isinstance(tags, list) or len(tags) < 3:
        errors.append("tags 必须是至少 3 个的数组")
    for tag in tags if isinstance(tags, list) else []:
        if not isinstance(tag, str) or not (1 <= len(tag) <= 30):
            errors.append(f"tag 非法: {tag}")
    for key in ("summary", "description", "keywords"):
        val = a.get(key, "")
        if not isinstance(val, str) or not val.strip():
            errors.append(f"缺少 {key}")
    description = a.get("description", "")
    if description and (len(description) < 50 or len(description) > 200):
        errors.append(f"description 长度应在 50-200 字（当前 {len(description)}）")
    summary = a.get("summary", "")
    if summary and (len(summary) < 20 or len(summary) > 200):
        errors.append(f"summary 长度应在 20-200 字（当前 {len(summary)}）")


def check_headings(a, errors):
    content = a.get("content", "")
    if not content:
        return
    headings = re.findall(r"^#{2,3} ", content, re.M)
    if len(headings) < 2:
        errors.append(f"标题层级不足（至少 2 个 h2/h3，当前 {len(headings)}）")


def check_geo_style(a, warnings):
    """GEO/SEO 软性检查：不阻断发布，但提示写作时自查（2026-08-18 立）。"""
    content = a.get("content", "")
    faq = a.get("faq", [])
    for i, item in enumerate(faq, 1):
        q = (item or {}).get("question", "")
        if q and not q.endswith(("？", "?")):
            warnings.append(f"FAQ 第 {i} 条 question 建议用自然问句并以「？」结尾: {q}")
    links = [
        url for _, url in LINK_RE.findall(content)
        if "/images/" not in url and not url.startswith("#")
    ]
    if not links and not (a.get("related_tools") or []):
        warnings.append("正文没有站内链接（建议至少 1 条相关工具/文章链接，GEO 内链信号）")
    description = a.get("description", "")
    if description and not (80 <= len(description) <= 160):
        warnings.append(f"description 建议 80-160 字（当前 {len(description)}）")
    summary = a.get("summary", "")
    if summary and not (30 <= len(summary) <= 150):
        warnings.append(f"summary 建议 30-150 字（当前 {len(summary)}）")


def check_ai_flavor(a, errors):
    text = (a.get("title", "") + "\n" + a.get("content", "")).lower()
    for label, pattern in AI_FLAVOR_PATTERNS:
        if re.search(pattern, text):
            errors.append(f"命中 AI 味表达（写作铁律禁止）: {label}")


def main():
    parser = argparse.ArgumentParser(description="自动发布文章校验与入库")
    parser.add_argument("--draft", required=True, help="草稿 JSON 路径")
    parser.add_argument("--dry-run", action="store_true", help="只校验不写文件")
    args = parser.parse_args()

    if not os.path.isfile(args.draft):
        print(f"[FAIL] 草稿文件不存在: {args.draft}")
        return 2

    article = load_json(args.draft)
    from data_store import load_all_articles, load_all_tools, save_article
    articles = load_all_articles()
    tools_raw = load_all_tools()
    tools = tools_raw.get("tools", tools_raw) if isinstance(tools_raw, dict) else tools_raw

    existing_slugs = {a.get("slug") for a in articles if a.get("slug")}
    existing_titles = {a.get("title", "").casefold() for a in articles if a.get("title")}
    tool_slugs = {t.get("slug") for t in tools if t.get("slug")}

    errors = []
    warnings = []
    check_required_fields(article, errors)
    check_slug(article, existing_slugs, errors)
    check_titles(article, existing_titles, errors)
    check_dates(article, errors)
    check_content(article, errors)
    check_images(article, errors)
    check_faq(article, errors)
    check_related_tools(article, tool_slugs, errors)
    check_meta(article, errors)
    check_headings(article, errors)
    check_ai_flavor(article, errors)
    check_geo_style(article, warnings)

    slug = article.get("slug", "")
    if errors:
        print(f"[FAIL] 校验未通过（共 {len(errors)} 项），未写入任何文件:")
        for e in errors:
            print(f"  - {e}")
        return 2

    if args.dry_run:
        print(f"[OK] 校验通过（dry-run，未写文件）: {slug}")
    else:
        save_article(article)
        print(f"[OK] 已入库 data/articles/{slug}.json: {slug}")

    images = IMAGE_RE.findall(article.get("content", ""))
    print(f"  标题: {article.get('title')}")
    print(f"  正文: {len(article.get('content', ''))} 字 | 配图: {len(images)} 张 | FAQ: {len(article.get('faq', []))} 条")
    print(f"  日期: {article.get('date')} | content_type: {article.get('content_type')}")
    for w in warnings:
        print(f"  [提示] {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
