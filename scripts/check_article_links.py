# -*- coding: utf-8 -*-
"""
站内链接有效性校验：扫描 articles.json 中所有文章正文的站内链接，
检查 /articles/{slug}/ 与 /tools/{slug}/ 是否真实存在，输出死链清单。

用法：
    python scripts/check_article_links.py            # 全站扫描
    python scripts/check_article_links.py --slug xxx # 只查某篇
    python scripts/check_article_links.py --last     # 只查最新一篇（插入后必跑）
退出码：0 = 无死链，1 = 存在死链
"""
import json, os, re, sys, argparse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ART_RE = re.compile(r'(?:https://www\.aitoollab\.cn)?/articles/([a-z0-9\-]+)/')
TOOL_RE = re.compile(r'(?:https://www\.aitoollab\.cn)?/tools/([a-z0-9\-\.]+)/')


def load():
    # 2026-08-26 去单体化: 分片优先
    import sys as _sys
    _sys.path.insert(0, os.path.join(BASE, 'scripts'))
    from data_store import load_all_articles, load_all_tools
    articles = load_all_articles()
    tools = load_all_tools()
    return articles, tools


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug', help='只校验指定 slug 的文章')
    ap.add_argument('--last', action='store_true', help='只校验最新一篇文章')
    args = ap.parse_args()

    articles, tools = load()
    art_slugs = {a.get('slug') for a in articles}
    tool_slugs = {t.get('slug') for t in tools}

    targets = articles
    if args.last:
        targets = articles[-1:]
    elif args.slug:
        targets = [a for a in articles if a.get('slug') == args.slug]
        if not targets:
            print(f'[ERROR] 未找到文章: {args.slug}')
            return 1

    dead_art, dead_tool, dead_rel = [], [], []
    total_art = total_tool = 0

    for a in targets:
        slug = a.get('slug', '')
        content = a.get('content', '') or ''

        for m in set(ART_RE.findall(content)):
            total_art += 1
            if m not in art_slugs:
                dead_art.append((slug, m))

        for m in set(TOOL_RE.findall(content)):
            total_tool += 1
            if m not in tool_slugs:
                dead_tool.append((slug, m))

        for rt in (a.get('related_tools') or []):
            if rt not in tool_slugs:
                dead_rel.append((slug, rt))

    print(f'扫描文章 {len(targets)} 篇 | 文章链接 {total_art} 处 | 工具链接 {total_tool} 处')
    print('=' * 78)

    bad = False
    if dead_art:
        bad = True
        print(f'\n[死链] 指向不存在的文章 ({len(dead_art)} 处):')
        for host, target in dead_art:
            print(f'  {host}  ->  /articles/{target}/')
    if dead_tool:
        bad = True
        print(f'\n[死链] 指向不存在的工具 ({len(dead_tool)} 处):')
        for host, target in dead_tool:
            print(f'  {host}  ->  /tools/{target}/')
    if dead_rel:
        bad = True
        print(f'\n[无效] related_tools 中不存在的工具 ({len(dead_rel)} 处):')
        for host, target in dead_rel:
            print(f'  {host}  ->  {target}')

    if not bad:
        print('\n[OK] 全部站内链接有效，无死链。')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
