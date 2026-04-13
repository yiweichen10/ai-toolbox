#!/usr/bin/env python3
"""
内链校验脚本 - 检查文章内容中引用的工具链接是否与 tools.json 的真实 slug 匹配

用法：
    python scripts/check_internal_links.py          # 检查并报告
    python scripts/check_internal_links.py --fix    # 检查并自动修复（模糊匹配）

问题场景：AI生成文章时手动写工具内链，猜测的slug可能与tools.json不一致，
例如写了 /tools/kling 但实际slug是 /tools/kling-ai，导致死链。
"""

import json
import re
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_FILE = os.path.join(BASE_DIR, 'data', 'tools.json')
ARTICLES_FILE = os.path.join(BASE_DIR, 'data', 'articles.json')
DOMAIN = 'www.aitoolbox.hk'


def load_tools():
    with open(TOOLS_FILE, encoding='utf-8') as f:
        return json.load(f)


def load_articles():
    with open(ARTICLES_FILE, encoding='utf-8') as f:
        return json.load(f)


def extract_tool_links(content):
    """从文章内容中提取所有 /tools/xxx 链接"""
    # 匹配多种格式：/tools/xxx, /tools/xxx/, /tools/xxx/index.html
    # 也匹配带域名的：https://www.aitoolbox.hk/tools/xxx
    pattern = r'(?:https?://[^/]+)?/tools/([a-z0-9\-]+)/?(?:index\.html)?'
    matches = re.findall(pattern, content)
    return list(set(matches))


def find_best_match(bad_slug, valid_slugs, tool_names):
    """尝试找到最佳匹配的slug"""
    # 1. 精确包含匹配：bad_slug 是某个真实slug的子串或被包含
    for s in valid_slugs:
        if bad_slug in s or s in bad_slug:
            return s

    # 2. 去掉/加上 -ai 后缀匹配
    variants = [bad_slug, bad_slug + '-ai', bad_slug.replace('-ai', '')]
    for v in variants:
        if v in valid_slugs:
            return v

    # 3. 工具名匹配：bad_slug 可能是工具名的英文翻译
    for slug, name in tool_names.items():
        # 简单的前缀匹配
        if bad_slug.startswith(slug[:4]) or slug.startswith(bad_slug[:4]):
            return slug

    return None


def main():
    auto_fix = '--fix' in sys.argv

    tools = load_tools()
    articles = load_articles()

    # 构建有效slug集合和slug→名称映射（只包含已发布的）
    valid_slugs = set()
    slug_to_name = {}
    for t in tools:
        valid_slugs.add(t['slug'])
        slug_to_name[t['slug']] = t['name']

    print(f"已发布工具slug: {len(valid_slugs)} 个")
    print(f"文章数量: {len(articles)} 篇\n")

    total_issues = 0
    total_fixed = 0
    fix_log = []

    for article in articles:
        slug = article['slug']
        content = article.get('content', '')

        if not content:
            continue

        links = extract_tool_links(content)
        bad_links = [l for l in links if l not in valid_slugs]

        if not bad_links:
            continue

        for bad_slug in bad_links:
            total_issues += 1
            best_match = find_best_match(bad_slug, valid_slugs, slug_to_name)
            match_info = f" → 建议修复为: /tools/{best_match}" if best_match else " → 未找到匹配，需手动处理"

            print(f"[DEAD] Article [{slug}] references invalid slug: /tools/{bad_slug}{match_info}")

            if auto_fix and best_match:
                # 执行修复
                old_patterns = [
                    f'/tools/{bad_slug}',
                    f'/tools/{bad_slug}/',
                    f'/tools/{bad_slug}/index.html',
                ]
                new_path = f'/tools/{best_match}'
                for old_p in old_patterns:
                    article['content'] = article['content'].replace(old_p, new_path)
                total_fixed += 1
                fix_log.append(f"  [FIX] /tools/{bad_slug} -> /tools/{best_match}")
                print(fix_log[-1])

    print(f"\n{'='*50}")
    print(f"共发现 {total_issues} 个内链问题")

    if auto_fix:
        if total_fixed > 0:
            with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=4)
            print(f"已自动修复 {total_fixed} 个，已保存到 articles.json")
        else:
            print("没有可自动修复的链接")
    else:
        if total_issues > 0:
            print("运行 python scripts/check_internal_links.py --fix 可自动修复")
        else:
            print("[OK] All internal links valid, no dead links found.")


if __name__ == '__main__':
    main()
