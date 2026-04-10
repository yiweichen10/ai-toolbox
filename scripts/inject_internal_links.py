#!/usr/bin/env python3
"""
inject_internal_links.py
========================
批量给工具详情页和文章页的正文添加站内链接 + 给工具详情页添加站内CTA。

核心逻辑：
1. 从 tools.json 读取所有工具名 → slug 映射
2. 扫描 tools/*/index.html 和 articles/*/index.html
3. 在 article-body 区域内，将工具名替换为 <a href="/tools/slug/">工具名</a>
4. 在工具详情页 action-bar 区域，添加站内CTA按钮

安全措施：
- 只在 article-body 内替换（不影响导航/header/footer）
- 不替换已在 <a> 标签内的文字
- 不替换 HTML 标签属性中的文字
- 每个工具名每页最多链接1次（避免过度优化）
- 不链接当前页面自身的工具名
"""

import json
import re
import os
from pathlib import Path
from html.parser import HTMLParser

SITE_ROOT = Path(__file__).resolve().parent.parent
TOOLS_JSON = SITE_ROOT / "data" / "tools.json"
TOOLS_DIR = SITE_ROOT / "tools"
ARTICLES_DIR = SITE_ROOT / "articles"


def load_tool_map():
    """加载工具名→slug映射，按名称长度降序排列（优先匹配长名）"""
    with open(TOOLS_JSON, "r", encoding="utf-8") as f:
        tools = json.load(f)
    # 按名称长度降序排列，避免 "Gemini" 先于 "Gemini 2.5" 被替换
    tool_map = sorted(
        [(t["name"], t["slug"]) for t in tools if t.get("published", True)],
        key=lambda x: len(x[0]),
        reverse=True,
    )
    return tool_map


def inject_links_in_article_body(html: str, tool_map: list, current_slug: str = None) -> str:
    """在 article-body 区域内注入站内链接"""
    # 找到 article-body 区域
    pattern = r'(<article class="article-body">)(.*?)(</article>)'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return html

    body_content = match.group(2)
    linked_tools = set()  # 追踪已链接的工具，每页每个工具最多1次

    for tool_name, slug in tool_map:
        if slug == current_slug:
            continue  # 不链接自己
        if tool_name in linked_tools:
            continue

        escaped_name = re.escape(tool_name)
        replacements_made = 0
        max_per_tool = 1  # 每页每个工具最多链接1次

        def make_replacer(tn, sl):
            """工厂函数：为每次循环创建独立的replacer"""
            count = [0]
            def replace_tool_name(m):
                if count[0] >= 1:
                    return m.group(0)
                # m.group(0) 是完整匹配，直接替换整个匹配为带链接版本
                count[0] += 1
                linked_tools.add(tn)
                return f'<a href="/tools/{sl}/" style="color:var(--primary-color);text-decoration:underline;text-underline-offset:3px;font-weight:500;">{tn}</a>'
            return replace_tool_name

        # 用更智能的方式：只在非标签文本中替换
        # 策略：分段处理，将HTML拆分为标签和文本，只在文本中替换
        parts = re.split(r'(<[^>]+>)', body_content)
        new_parts = []
        replacer = make_replacer(tool_name, slug)
        for part in parts:
            if part.startswith('<') and part.endswith('>'):
                # 这是HTML标签，不处理
                new_parts.append(part)
            else:
                # 这是文本内容，替换（但跳过已在<a>标签上下文中的）
                # 检查前面的parts是否包含未闭合的<a>
                context_before = ''.join(new_parts[-5:]) if len(new_parts) >= 5 else ''.join(new_parts)
                if '<a ' in context_before and '</a>' not in context_before[context_before.rfind('<a '):]:
                    # 我们在<a>标签内，跳过
                    new_parts.append(part)
                else:
                    new_part = re.sub(escaped_name, replacer, part, count=1)
                    new_parts.append(new_part)
        body_content = ''.join(new_parts)

    # 重新组装
    new_html = html[:match.start()] + match.group(1) + body_content + match.group(3) + html[match.end():]
    return new_html


def inject_faq_links(html: str, tool_map: list, current_slug: str = None) -> str:
    """在FAQ答案中添加内链"""
    # 找到 faq-section 区域
    pattern = r'(<div class="faq-section">)(.*?)(</div>\s*</div>\s*<div class="related)'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return html

    faq_content = match.group(2)
    linked_tools = set()

    for tool_name, slug in tool_map:
        if slug == current_slug:
            continue
        if tool_name in linked_tools:
            continue

        escaped_name = re.escape(tool_name)

        def make_replacer(tn, sl):
            count = [0]
            def replace_tool_name(m):
                if count[0] >= 1:
                    return m.group(0)
                count[0] += 1
                linked_tools.add(tn)
                return f'<a href="/tools/{sl}/" style="color:var(--primary-color);text-decoration:underline;text-underline-offset:3px;font-weight:500;">{tn}</a>'
            return replace_tool_name

        # 同样用分段方式处理
        parts = re.split(r'(<[^>]+>)', faq_content)
        new_parts = []
        replacer = make_replacer(tool_name, slug)
        for part in parts:
            if part.startswith('<') and part.endswith('>'):
                new_parts.append(part)
            else:
                context_before = ''.join(new_parts[-5:]) if len(new_parts) >= 5 else ''.join(new_parts)
                if '<a ' in context_before and '</a>' not in context_before[context_before.rfind('<a '):]:
                    new_parts.append(part)
                else:
                    new_part = re.sub(escaped_name, replacer, part, count=1)
                    new_parts.append(new_part)
        faq_content = ''.join(new_parts)

    new_html = html[:match.start()] + match.group(1) + faq_content + html[match.end():]
    return new_html


def inject_site_cta(html: str, tool_map: list, current_slug: str = None) -> str:
    """在工具详情页 action-bar 添加站内CTA"""
    # 找到 action-bar 区域
    pattern = r'(<div class="action-bar">)(.*?)(</div>)'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return html

    existing_ctas = match.group(2)

    # 查找当前工具的分类
    current_tool = None
    with open(TOOLS_JSON, "r", encoding="utf-8") as f:
        tools = json.load(f)
    for t in tools:
        if t["slug"] == current_slug:
            current_tool = t
            break

    # 获取同类工具的category slug
    category_slug_map = {
        "AI对话": "ai-chat", "AI写作": "ai-writing", "AI绘画": "ai-painting",
        "AI编程": "ai-coding", "AI视频": "ai-video", "AI音频": "ai-audio",
        "AI办公": "ai-office", "AI设计": "ai-design", "AI搜索": "ai-search",
        "AI翻译": "ai-translation", "AI自动化": "ai-automation", "AI效率": "ai-efficiency",
    }

    extra_ctas = ""
    if current_tool:
        cat = current_tool.get("category", "")
        cat_slug = category_slug_map.get(cat, "")
        if cat_slug:
            extra_ctas += f'\n                <a href="/category/{cat_slug}/" class="action-btn" style="background:var(--surface-bg);color:var(--primary-color);border:2px solid var(--primary-color);">更多{cat}工具 →</a>'

    # 添加对比和排行CTA
    extra_ctas += '\n                <a href="/ranking/" class="action-btn" style="background:var(--surface-bg);color:var(--text-muted);border:2px solid #e2e8f0;">📊 工具排行榜</a>'

    new_action_bar = match.group(1) + existing_ctas + extra_ctas + "\n            " + match.group(3)
    new_html = html[:match.start()] + new_action_bar + html[match.end():]
    return new_html


def add_article_toc_and_cta(html: str, tool_map: list) -> str:
    """给文章页底部添加站内CTA（工具推荐链接块）"""
    # 在 related-tools 之前，检查是否已存在站内CTA
    if "article-site-cta" in html:
        return html

    # 在 footer 前插入站内CTA
    cta_html = """
    <div class="article-site-cta" style="background:linear-gradient(135deg,var(--primary-color),var(--secondary-color));border-radius:var(--radius-lg);padding:32px;margin-bottom:32px;text-align:center;color:#fff;">
        <h3 style="font-size:20px;font-weight:800;margin-bottom:12px;">🎯 找到适合你的AI工具</h3>
        <p style="font-size:15px;opacity:0.9;margin-bottom:20px;">浏览100+精选AI工具，按分类、排行、场景筛选</p>
        <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
            <a href="/ranking/" style="display:inline-flex;align-items:center;padding:12px 24px;background:rgba(255,255,255,0.2);color:#fff;border-radius:var(--radius-md);font-weight:700;text-decoration:none;backdrop-filter:blur(4px);border:1px solid rgba(255,255,255,0.3);">📊 工具排行</a>
            <a href="/quiz/" style="display:inline-flex;align-items:center;padding:12px 24px;background:rgba(255,255,255,0.2);color:#fff;border-radius:var(--radius-md);font-weight:700;text-decoration:none;backdrop-filter:blur(4px);border:1px solid rgba(255,255,255,0.3);">🎯 AI工具选择器</a>
            <a href="/category/" style="display:inline-flex;align-items:center;padding:12px 24px;background:rgba(255,255,255,0.2);color:#fff;border-radius:var(--radius-md);font-weight:700;text-decoration:none;backdrop-filter:blur(4px);border:1px solid rgba(255,255,255,0.3);">📂 全部分类</a>
        </div>
    </div>
    """

    # 在 </main> 前插入
    html = html.replace("</main>", cta_html + "\n    </main>", 1)
    return html


def process_tool_page(filepath: Path, tool_map: list):
    """处理单个工具详情页"""
    slug = filepath.parent.name
    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()

    original = html

    # 1. 注入正文内链
    html = inject_links_in_article_body(html, tool_map, current_slug=slug)

    # 2. 注入FAQ内链
    html = inject_faq_links(html, tool_map, current_slug=slug)

    # 3. 添加站内CTA
    html = inject_site_cta(html, tool_map, current_slug=slug)

    if html != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        return True
    return False


def process_article_page(filepath: Path, tool_map: list):
    """处理单个文章页"""
    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()

    original = html

    # 1. 注入正文内链
    html = inject_links_in_article_body(html, tool_map)

    # 2. 添加站内CTA
    html = add_article_toc_and_cta(html, tool_map)

    if html != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        return True
    return False


def main():
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("[LINK] 开始注入站内链接和CTA...")
    tool_map = load_tool_map()
    print(f"   加载了 {len(tool_map)} 个工具映射")

    # 处理工具详情页
    tool_count = 0
    for tool_dir in TOOLS_DIR.iterdir():
        if not tool_dir.is_dir():
            continue
        index_file = tool_dir / "index.html"
        if not index_file.exists():
            continue
        if process_tool_page(index_file, tool_map):
            tool_count += 1
            print(f"   OK tools/{tool_dir.name}/")
    print(f"   修改了 {tool_count} 个工具详情页")

    # 处理文章页
    article_count = 0
    for art_dir in ARTICLES_DIR.iterdir():
        if not art_dir.is_dir():
            continue
        index_file = art_dir / "index.html"
        if not index_file.exists():
            continue
        if process_article_page(index_file, tool_map):
            article_count += 1
            print(f"   OK articles/{art_dir.name}/")
    print(f"   修改了 {article_count} 个文章页")

    print(f"\n[DONE] 共修改 {tool_count + article_count} 个页面")


if __name__ == "__main__":
    main()
