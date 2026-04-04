#!/usr/bin/env python3
"""SSG构建脚本：将JSON数据生成为静态HTML文件，SEO友好"""
import json
import os
import re

# 返回顶部按钮 HTML + 内联脚本（避免在 f-string 中转义花括号）
BACK_TO_TOP_BLOCK = '''<button id="backToTop" aria-label="返回顶部">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="18 15 12 9 6 15"></polyline>
    </svg>
</button>
<script>
document.addEventListener("DOMContentLoaded",function(){var b=document.getElementById("backToTop");if(!b)return;var s=function(){if(window.scrollY>400){b.classList.add("visible")}else{b.classList.remove("visible")}};window.addEventListener("scroll",s,{passive:true});s();b.addEventListener("click",function(){window.scrollTo({top:0,behavior:"smooth"})});});
</script>'''

from pypinyin import pinyin, Style

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# OG图片自动生成：缺失时自动调用gen_seo_images生成
def ensure_og_image(slug, data_obj=None, is_article=False):
    """检查OG图片是否存在，不存在则自动生成。返回og_image URL或空字符串。"""
    og_image_local = os.path.join(BASE_DIR, 'images', 'og', f'{slug}-og.png')
    og_image_url = f'https://www.aitoolbox.hk/images/og/{slug}-og.png'
    if os.path.exists(og_image_local):
        return og_image_url
    # 自动生成
    try:
        from gen_seo_images import make_article_og_image, make_og_image, generate_image
        if is_article and data_obj:
            html = make_article_og_image(data_obj)
        elif data_obj and not is_article:
            all_tools = []
            tools_path = os.path.join(DATA_DIR, 'tools.json')
            if os.path.exists(tools_path):
                with open(tools_path, encoding='utf-8') as f:
                    all_tools = json.load(f)
            html = make_og_image(data_obj, all_tools)
        else:
            return ''
        if generate_image(html, og_image_local):
            print(f'  [OG] 自动生成: {slug}-og.png')
            return og_image_url
        else:
            print(f'  [OG] 生成失败: {slug}-og.png')
            return ''
    except Exception as e:
        print(f'  [OG] 生成异常: {slug} - {e}')
        return ''

BAIDU_TONGJI = '''<script>
var _hmt = _hmt || [];
(function() {
  var hm = document.createElement("script");
  hm.src = "https://hm.baidu.com/hm.js?6ac10754cf0bb444085d1d7764eb2c6b";
  var s = document.getElementsByTagName("script")[0]; 
  s.parentNode.insertBefore(hm, s);
})();
</script>'''

# 为常用分类提供固定且语义化的英文slug，优先使用这些
CATEGORY_SLUG_MAP = {
    "AI对话": "ai-chat",
    "AI写作": "ai-writing",
    "AI绘画": "ai-painting",
    "AI编程": "ai-coding",
    "AI视频": "ai-video",
    "AI音频": "ai-audio",
    "AI办公": "ai-office",
    "AI设计": "ai-design",
    "AI搜索": "ai-search",
    "AI翻译": "ai-translation",
    "AI自动化": "ai-automation",
    "AI效率": "ai-efficiency",
}

def get_category_slug(category_name):
    """
    根据中文分类名生成SEO友好的英文slug。
    优先使用预设映射，否则使用拼音。
    """
    if category_name in CATEGORY_SLUG_MAP:
        return CATEGORY_SLUG_MAP[category_name]
    
    # 使用pypinyin生成拼音，并转换为连字符连接的小写形式
    pinyin_list = pinyin(category_name, style=Style.NORMAL)
    slug = '-'.join([item[0] for item in pinyin_list if item and item[0].strip()]).lower()
    return slug

def markdown_to_html(md):
    """将Markdown转换为简单HTML"""
    if not md:
        return ''
    html = md
    # 代码块
    html = re.sub(r'```(\w*)\n([\s\S]*?)```', lambda m: '<pre><code>' + m.group(2).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</code></pre>', html)
    # 表格
    def table_replace(m):
        header = m.group(1)
        sep = m.group(2)
        body = m.group(3)
        headers = [c.strip() for c in header.split('|') if c.strip()]
        rows = body.strip().split('\n')
        table = '<table><thead><tr>'
        for h in headers:
            table += f'<th>{h}</th>'
        table += '</tr></thead><tbody>'
        for row in rows:
            cells = [c.strip() for c in row.split('|') if c.strip()]
            table += '<tr>'
            for c in cells:
                table += f'<td>{c}</td>'
            table += '</tr>'
        table += '</tbody></table>'
        return table
    html = re.sub(r'\n(\|.+\|)\n(\|[-:| ]+\|)\n((?:\|.+\|\n?)+)', table_replace, html)
    # 标题
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    # 引用
    html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
    # 加粗/行内代码
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    # 链接 [text](url) — 先处理站内相对链接，再处理外链
    html = re.sub(r'\[([^\]]+)\]\((/[^)]+)\)', r'<a href="\2">\1</a>', html)
    html = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', html)
    # 列表：将连续的 <li> 包裹在 <ul> 中
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', html, flags=re.MULTILINE)
    # 把连续的裸 <li> 行用 <ul> 包裹起来
    html = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul>\1</ul>', html)
    # 段落：将连续非标签行包裹成p
    lines = html.split('\n')
    result = []
    in_p = False
    for line in lines:
        stripped = line.strip()
        is_tag = stripped.startswith('<h') or stripped.startswith('<ul') or stripped.startswith('</ul') or stripped.startswith('<li') or stripped.startswith('<table') or stripped.startswith('</table') or stripped.startswith('<pre') or stripped.startswith('</pre') or stripped.startswith('<blockquote') or stripped.startswith('</blockquote') or stripped == ''
        if is_tag:
            if in_p:
                result.append('</p>')
                in_p = False
            result.append(line)
        else:
            if not in_p:
                result.append('<p>' + line)
                in_p = True
            else:
                result.append(line)
    if in_p:
        result.append('</p>')
    return '\n'.join(result)

def escape_html(text):
    """转义HTML特殊字符（用于属性值）"""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def get_category_stats(tools):
    """
    统计每个分类下的工具数量，并返回一个字典。
    例如：{'AI对话': 8, 'AI绘画': 12}
    """
    category_counts = {}
    for tool in tools:
        if tool.get('published', False) and 'category' in tool:
            category = tool['category']
            category_counts[category] = category_counts.get(category, 0) + 1
    return category_counts

def build_tool_page(tool, all_tools, all_articles=None):
    """生成单个工具详情页的完整HTML"""
    slug = tool['slug']

    # ── 相关工具（自动补足到5个：同分类2-3个 + 跨分类2-3个）──────────────
    related_html = ''
    manually_related = tool.get('related', [])
    manually_related_tools = [t for t in all_tools if t['slug'] in manually_related and t['slug'] != slug]

    same_category = [t for t in all_tools if t['slug'] != slug and t.get('category') == tool.get('category')]
    other_category = [t for t in all_tools if t['slug'] != slug and t.get('category') != tool.get('category')]

    import random
    same_shuffled = same_category.copy()
    other_shuffled = other_category.copy()
    random.seed(42)  # 保证每次生成结果稳定

    # 优先用手动指定的，超出的自动补
    selected = manually_related_tools.copy()
    for t in same_shuffled:
        if len(selected) >= 5:
            break
        if t not in selected:
            selected.append(t)
    for t in other_shuffled:
        if len(selected) >= 5:
            break
        if t not in selected:
            selected.append(t)

    if selected:
        related_cards = ''
        for r in selected[:5]:
            related_cards += f'''<a href="/tools/{r['slug']}/index.html" class="related-card">
                <div style="font-size:24px;margin-bottom:8px;">{r['emoji']}</div>
                <div style="font-weight:600;">{r['name']}</div>
                <div style="font-size:13px;color:#666;">{r['category']}</div>
            </a>
'''
        related_html = f'''<div class="related-tools" id="relatedSection">
            <h3>🔗 相关工具推荐</h3>
            <div class="related-grid">{related_cards}</div>
        </div>'''

    # ── 相关文章（工具页底部推荐2-3篇相关文章）────────────────────────
    related_articles_html = ''
    if all_articles:
        tool_name = tool['name'].lower()
        # 优先匹配工具名的文章
        matched = []
        for a in all_articles:
            title_lower = a.get('title', '').lower()
            desc_lower = a.get('description', '').lower()
            if tool_name in title_lower or tool_name in desc_lower:
                matched.append(a)
        # 没有精确匹配的，取同类文章
        if len(matched) < 2:
            category_articles = [a for a in all_articles if a.get('category') == tool.get('category') and a not in matched]
            matched.extend(category_articles[:3 - len(matched)])
        # 还不够，取最新文章
        if len(matched) < 2:
            for a in all_articles:
                if a not in matched:
                    matched.append(a)
                    if len(matched) >= 3:
                        break

        if matched:
            cards = ''
            for a in matched[:3]:
                cards += f'''<a href="/articles/{a['slug']}/index.html" class="related-card">
                    <div style="font-weight:600;margin-bottom:4px;">📖 {escape_html(a['title'][:30])}</div>
                    <div style="font-size:13px;color:#666;">{a.get('dateFull', a.get('date', ''))}</div>
                </a>
'''
            related_articles_html = f'''<div class="related-tools">
                <h3>📚 相关文章</h3>
                <div class="related-grid">{cards}</div>
            </div>'''

    # FAQ 区块
    faq_html = ''
    faq_schema = []
    if tool.get('faq'):
        for faq_item in tool['faq']:
            question = faq_item.get('question', '')
            answer = faq_item.get('answer', '')
            if question and answer:
                faq_html += f'''<div class="faq-item">
                    <details>
                        <summary>{escape_html(question)}</summary>
                        <div class="faq-answer">{markdown_to_html(answer)}</div>
                    </details>
                </div>\n'''
                # FAQ Schema
                faq_schema.append({
                    '@type': 'Question',
                    'name': question,
                    'acceptedAnswer': {
                        '@type': 'Answer',
                        'text': answer
                    }
                })
        if faq_html:
            faq_html = f'''<div class="faq-section">
                <h3>❓ 常见问题</h3>
                {faq_html}
            </div>'''

    # 功能列表
    features_html = ''
    if tool.get('features'):
        for f in tool['features']:
            features_html += f'<div class="feature-item">{f}</div>\n'
        features_html = f'<div class="features-grid">{features_html}</div>'

    # 优缺点
    pros_cons_html = ''
    if tool.get('pros') and tool.get('cons'):
        pros_html = ''.join(f'<li>{p}</li>' for p in tool['pros'])
        cons_html = ''.join(f'<li>{c}</li>' for c in tool['cons'])
        pros_cons_html = f'''<div class="pros-cons">
            <div class="pros">
                <h4>👍 优点</h4>
                <ul>{pros_html}</ul>
            </div>
            <div class="cons">
                <h4>👎 缺点</h4>
                <ul>{cons_html}</ul>
            </div>
        </div>'''

    # 徽章
    badge_html = ''
    if tool.get('badge'):
        badge_color = {'hot': '#ff4444', 'new': '#00aa00', 'pick': '#667eea'}.get(tool['badge'].get('type'), '#667eea')
        badge_html = f' <span class="badge" style="background:{badge_color};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;">{tool["badge"]["text"]}</span>'

    # 平台
    platform_html = ''
    if tool.get('platform'):
        platform_html = f'<div class="tool-meta-item">📦 <strong>平台</strong>：{tool["platform"]}</div>'

    # 结构化数据
    from datetime import datetime
    today_iso = datetime.now().strftime('%Y-%m-%d')
    # 优先用工具数据里的日期字段，否则用今天
    date_published = tool.get('datePublished', tool.get('date_published', today_iso))
    date_modified = tool.get('dateModified', tool.get('date_modified', today_iso))

    category_slug_for_schema = get_category_slug(tool.get('category', ''))
    breadcrumb_data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "首页",
                "item": "https://www.aitoolbox.hk/"
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": tool.get('category', ''),
                "item": f"https://www.aitoolbox.hk/category/{category_slug_for_schema}/"
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": tool['name'],
                "item": f"https://www.aitoolbox.hk/tools/{slug}/"
            }
        ]
    }

    software_data = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": tool['name'],
        "applicationCategory": "UtilitiesApplication",
        "operatingSystem": tool.get('platform', 'Web'),
        "description": tool['description'],
        "datePublished": date_published,
        "dateModified": date_modified,
        "offers": {
            "@type": "Offer",
            "price": tool.get('price', ''),
            "priceCurrency": "USD"
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": tool['rating'].replace('⭐ ', ''),
            "ratingCount": tool.get('visits', '0').replace('万', '0000')
        }
    }
    structured_data = json.dumps(software_data, ensure_ascii=False, indent=2)
    breadcrumb_json = json.dumps(breadcrumb_data, ensure_ascii=False, indent=2)

    # FAQ Schema（输出到<head>，用于Google丰富摘要）
    faq_page_schema = ''
    if faq_schema:
        faq_page_schema_data = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": faq_schema
        }
        faq_page_schema = f'<script type="application/ld+json">{json.dumps(faq_page_schema_data, ensure_ascii=False)}</script>'

    # OG Image（自动生成缺失的OG图片）
    og_image = ensure_og_image(slug, data_obj=tool, is_article=False)

    # 信息图
    infographic_path = os.path.join(BASE_DIR, 'images', 'infographics', f'{slug}-infographic.png')
    has_infographic = os.path.exists(infographic_path)
    infographic_html = ''
    if has_infographic:
        infographic_html = f'''<figure class="tool-infographic">
            <img src="/images/infographics/{slug}-infographic.png" alt="{escape_html(tool['name'])}功能亮点信息图" width="1200" height="630" loading="lazy">
            <figcaption>{escape_html(tool['name'])} 核心功能一览</figcaption>
        </figure>'''

    # 文章内容（从content中移除重复的优缺点部分）
    content_md = tool.get('content', '')
    # 移除 content 中 "## 优缺点分析" 及之后到下一个 ## 的内容（因为我们有独立的优缺点区块）
    content_md = re.sub(r'## 优缺点分析[\s\S]*?(?=## \w)', '', content_md)
    # 也移除末尾的优缺点
    content_md = re.sub(r'## 优缺点分析[\s\S]*$', '', content_md)
    content_html = markdown_to_html(content_md)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(tool['name'])}评测2026：功能介绍+使用技巧+免费版体验 - AI工具宝箱</title>
    <meta name="description" content="{escape_html(tool['name'])}全面评测2026：{escape_html(tool['description'])} 功能介绍、免费版体验、与同类工具对比。">
    <meta name="keywords" content="{escape_html(tool['name'])},{escape_html(tool['name'])}评测,{escape_html(tool['name'])}使用教程,{escape_html(tool['category'])},AI工具">
    <link rel="canonical" href="https://www.aitoolbox.hk/tools/{slug}/">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(tool['name'])}评测2026：功能介绍+使用技巧+免费版体验 - AI工具宝箱">
    <meta property="og:description" content="{escape_html(tool['name'])}全面评测2026：{escape_html(tool['description'])}">
    <meta property="og:url" content="https://www.aitoolbox.hk/tools/{slug}/">
''' + (f'    <meta property="og:image" content="{og_image}">\n' if og_image else '') + f'''    <link rel="stylesheet" href="/css/style.css">
    <script type="application/ld+json">{breadcrumb_json}</script>
    <script type="application/ld+json">{structured_data}</script>
    {faq_page_schema}
{BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><h1>🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></h1></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/category/{category_slug_for_schema}/">{escape_html(tool['category'])}</a> &gt; <span>{escape_html(tool['name'])}</span>
    </nav>

    <main class="article-container">
        <div class="tool-header">
            <div class="tool-header-top">
                <div class="tool-icon-lg" style="background:{tool['color']};">{tool['emoji']}</div>
                <div class="tool-header-info">
                    <h2>{escape_html(tool['name'])}{badge_html}</h2>
                    <p class="subtitle">{escape_html(tool['description'])}</p>
                    <div class="rating-bar">{tool['rating']} <span style="font-size:14px;color:#999;">({tool.get('visits', '0')}浏览)</span></div>
                </div>
            </div>
            <div class="tool-meta">
                <div class="tool-meta-item">🌐 <strong>官网</strong>：{tool['url'].replace('https://', '')}</div>
                <div class="tool-meta-item">💰 <strong>价格</strong>：{tool.get('price', '')}</div>
                {platform_html}
                <div class="tool-meta-item">🏷️ <strong>分类</strong>：{escape_html(tool['category'])}</div>
            </div>
            <div class="action-bar">
                <a href="{tool['url']}" target="_blank" rel="noopener" class="action-btn action-btn-primary">立即使用 →</a>
            </div>
        </div>

        {features_html}

        <article class="article-body">
            {content_html}
        </article>

        {infographic_html}

        {pros_cons_html}

        {faq_html}

        {related_html}

        {related_articles_html}
    </main>

    <footer class="footer">
        <p>© 2026 AI工具宝箱 · 每日精选优质AI工具</p>
    </footer>
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''
    return html


def build_compare_page(compare_data, all_tools, all_articles=None):
    """
    生成对比页面 (Phase 2: 程序化SEO)
    URL格式: /compare/{toolA-vs-toolB}/index.html
    覆盖关键词: "XX vs XX" / "XX和XX对比" / "XX XX哪个好"
    """
    slug = compare_data.get('slug', 'unknown')
    title = compare_data.get('title', 'AI工具对比')
    subtitle = compare_data.get('subtitle', '')
    meta_desc = compare_data.get('meta_description', f'{title} - AI工具宝箱深度评测')
    keywords = compare_data.get('keywords', [])
    content_md = compare_data.get('content', '')
    faq_list = compare_data.get('faq', [])
    compared_slugs = compare_data.get('compared_tools', compare_data.get('compared_tools', []))
    quick_verdict = compare_data.get('quick_verdict', {})
    
    # 获取被对比的工具对象
    compared_tools = []
    for s in compared_slugs:
        t = next((tool for tool in all_tools if tool['slug'] == s), None)
        if t:
            compared_tools.append(t)
    
    # 对比工具头部（并排展示）
    compare_headers = ''
    for t in compared_tools:
        compare_headers += f'''
            <div class="compare-tool-card">
                <div class="tool-icon-lg" style="background:{t['color']};font-size:36px;width:64px;height:64px;display:flex;align-items:center;justify-content:center;border-radius:12px;">{t['emoji']}</div>
                <div style="font-weight:700;font-size:18px;margin-top:8px;">{escape_html(t['name'])}</div>
                <div style="font-size:13px;color:#666;">{t.get('price', '')}</div>
            </div>'''
    
    # Quick Verdict 区块
    verdict_html = ''
    if quick_verdict:
        verdict_items = ''
        for key, label in [('overall_winner', '🏆 综合推荐'), ('best_for_beginners', '🌱 新手推荐'),
                           ('best_value', '💰 性价比之选'), ('best_for_pro', '🚀 专业用户推荐')]:
            if key in quick_verdict:
                winner = quick_verdict[key]
                # 找到对应的工具
                winner_tool = next((t for t in compared_tools if t['name'] in winner or winner in t['name']), None)
                winner_name = winner_tool['name'] if winner_tool else winner
                verdict_items += f'<li><strong>{label}</strong>：{winner_name}</li>\n'
        if verdict_items:
            verdict_html = f'''<div class="quick-verdict" style="background:linear-gradient(135deg,#f0f7ff,#e8f4f8);border-left:4px solid #4285F4;padding:20px 24px;border-radius:8px;margin:24px 0;">
                <h3 style="margin:0 0 12px;font-size:18px;">⚡ 快速结论</h3>
                <ul style="margin:0;padding-left:20px;line-height:2;">{verdict_items}</ul>
            </div>'''

    # FAQ
    faq_html = ''
    faq_schema = []
    for faq_item in faq_list:
        q = faq_item.get('question', '')
        a = faq_item.get('answer', '')
        if q and a:
            faq_html += f'''<div class="faq-item"><details><summary>{escape_html(q)}</summary><div class="faq-answer">{markdown_to_html(a)}</div></details></div>\n'''
            faq_schema.append({'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}})
    if faq_html:
        faq_html = f'<div class="faq-section"><h3>❓ 常见问题</h3>{faq_html}</div>'

    # FAQ Schema
    faq_page_schema = ''
    if faq_schema:
        faq_sd = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_schema}
        faq_page_schema = f'<script type="application/ld+json">{json.dumps(faq_sd, ensure_ascii=False)}</script>'

    # Article Schema（对比文章也是Article类型）
    from datetime import datetime as _dt
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": meta_desc,
        "datePublished": compare_data.get("last_updated", _dt.now().strftime('%Y-%m-%d')),
        "dateModified": compare_data.get("last_updated", _dt.now().strftime('%Y-%m-%d')),
        "author": {
            "@type": "Organization",
            "name": "AI工具宝箱",
            "url": "https://www.aitoolbox.hk/"
        },
        "publisher": {
            "@type": "Organization",
            "name": "AI工具宝箱",
            "logo": {
                "@type": "ImageObject",
                "url": "https://www.aitoolbox.hk/images/og/default-og.png"
            }
        }
    }
    article_schema_json = json.dumps(article_schema, ensure_ascii=False, indent=2)

    # Breadcrumb
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoolbox.hk/"},
            {"@type": "ListItem", "position": 2, "name": "工具对比", "item": "https://www.aitoolbox.hk/compare/"},
            {"@type": "ListItem", "position": 3, "name": title[:30], "item": f"https://www.aitoolbox.hk/compare/{slug}/"}
        ]
    }
    breadcrumb_json = json.dumps(breadcrumb, ensure_ascii=False, indent=2)

    # 相关链接（每个被对比的工具链接到自己的工具页）
    tool_link_parts = []
    for t in compared_tools:
        s = t['slug']
        c = t['color']
        e = t['emoji']
        n = t['name']
        tool_link_parts.append(f'<a href="/tools/{s}/index.html" style="display:inline-block;background:{c}22;color:{c};padding:6px 16px;border-radius:20px;text-decoration:none;font-size:14px;margin:4px;">{e} {n}详情</a>')
    tool_links = ''.join(tool_link_parts)

    # 内部链接：相关对比 + 相关替代方案
    related_compares_html = ''
    # 从所有已发布工具中找其他可能相关的对比组合
    other_tools = [t for t in all_tools if t['slug'] not in compared_slugs][:5]
    if other_tools and compared_tools:
        extra_links = ''
        main_tool = compared_tools[0] if compared_tools else None
        for ot in other_tools[:4]:
            combo_slug = build_compare_slug_from_slugs([main_tool['slug'], ot['slug']])
            extra_links += f'<a href="/compare/{combo_slug}/" style="font-size:13px;color:#4285F4;text-decoration:none;display:block;padding:4px 0;">→ {main_tool["name"]} vs {ot["name"]}</a>'
        if extra_links:
            related_compares_html = f'''<div class="related-tools" style="margin-top:30px;">
                <h3>🔗 更多相关对比</h3>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">{extra_links}</div>
            </div>'''

    content_html = markdown_to_html(content_md)

    # OG Image
    og_image = ensure_og_image(slug, data_obj=compare_data, is_article=True)

    from datetime import datetime as _dt
    today_iso = _dt.now().strftime('%Y-%m-%d')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)} - AI工具宝箱</title>
    <meta name="description" content="{escape_html(meta_desc)}">
    <meta name="keywords" content="{escape_html(', '.join(keywords))},AI工具对比,AI工具评测">
    <link rel="canonical" href="https://www.aitoolbox.hk/compare/{slug}/">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(meta_desc)}">
    <meta property="og:url" content="https://www.aitoolbox.hk/compare/{slug}/">
    <meta property="og:image" content="{og_image}">
    <link rel="stylesheet" href="/css/style.css">
    <script type="application/ld+json">{breadcrumb_json}</script>
    <script type="application/ld+json">{article_schema_json}</script>
    {faq_page_schema}
    {BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><h1>🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></h1></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/compare/">工具对比</a> &gt; <span>{' vs '.join([t['name'] for t in compared_tools])}</span>
    </nav>

    <main class="article-container">
        <div class="compare-header" style="display:flex;gap:16px;justify-content:center;flex-wrap:wrap;padding:24px;background:linear-gradient(135deg,#f8faff,#f0f4ff);border-radius:12px;margin-bottom:24px;">
            {compare_headers}
        </div>

        {verdict_html}

        <h2 style="font-size:22px;color:#333;">{escape_html(subtitle) if subtitle else ''}</h2>

        <div style="margin:16px 0;display:flex;flex-wrap:wrap;gap:8px;">
            {tool_links}
        </div>

        <article class="article-body">
            {content_html}
        </article>

        {faq_html}

        {related_compares_html}
    </main>

    <footer class="footer">
        <p>&copy; 2026 AI工具宝箱 &middot; 每日精选优质AI工具 &middot; 最后更新 {today_iso}</p>
    </footer>
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''
    return html


def build_alternatives_page(alt_data, all_tools, all_articles=None):
    """
    生成替代方案页面 (Phase 3: 替代方案页)
    URL格式: /alternatives/{tool-slug}-alternatives/index.html
    覆盖关键词: "XX替代" / "XX类似工具" / "XX平替" / "代替XX"
    """
    slug = alt_data.get('slug', 'unknown')
    title = alt_data.get('title', 'AI工具替代方案')
    meta_desc = alt_data.get('meta_description', f'{title} - AI工具宝箱')
    keywords = alt_data.get('keywords', [])
    content_md = alt_data.get('content', '')
    faq_list = alt_data.get('faq', [])
    target_slug = alt_data.get('target_tool', '')

    # 目标工具
    target_tool = next((t for t in all_tools if t['slug'] == target_slug), None)

    # FAQ
    faq_html = ''
    faq_schema = []
    for fi in faq_list:
        q, a = fi.get('question', ''), fi.get('answer', '')
        if q and a:
            faq_html += f'''<div class="faq-item"><details><summary>{escape_html(q)}</summary><div class="faq-answer">{markdown_to_html(a)}</div></details></div>\n'''
            faq_schema.append({'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}})
    if faq_html:
        faq_html = f'<div class="faq-section"><h3>❓ 常见问题</h3>{faq_html}</div>'

    faq_page_schema = ''
    if faq_schema:
        faq_sd = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_schema}
        faq_page_schema = f'<script type="application/ld+json">{json.dumps(faq_sd, ensure_ascii=False)}</script>'

    from datetime import datetime as _dt2
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": meta_desc,
        "datePublished": alt_data.get("last_updated", _dt2.now().strftime('%Y-%m-%d')),
        "author": {"@type": "Organization", "name": "AI工具宝箱"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱"}
    }
    article_schema_json = json.dumps(article_schema, ensure_ascii=False, indent=2)

    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoolbox.hk/"},
            {"@type": "ListItem", "position": 2, "name": "替代方案", "item": "https://www.aitoolbox.hk/alternatives/"},
            {"@type": "ListItem", "position": 3, "name": target_tool['name'] if target_tool else slug, "item": f"https://www.aitoolbox.hk/alternatives/{slug}/"}
        ]
    }
    breadcrumb_json = json.dumps(breadcrumb, ensure_ascii=False, indent=2)

    # 目标工具卡片
    target_card_html = ''
    if target_tool:
        target_card_html = f'''<div style="background:#fff5e6;border:1px solid #ffd666;border-radius:10px;padding:20px;margin:20px 0;display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
            <div style="font-size:40px;">{target_tool['emoji']}</div>
            <div><strong>寻找替代方案：</strong>{target_tool['name']}</div>
            <div style="color:#666;font-size:14px;">{target_tool.get('price','')}</div>
            <a href="/tools/{target_slug}/" style="margin-left:auto;color:#4285F4;text-decoration:none;font-size:14px;">查看原工具详情 →</a>
        </div>'''

    content_html = markdown_to_html(content_md)
    og_image = ensure_og_image(slug, data_obj=alt_data, is_article=True)
    from datetime import datetime as _dt
    today_iso = _dt.now().strftime('%Y-%m-%d')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)} - AI工具宝箱</title>
    <meta name="description" content="{escape_html(meta_desc)}">
    <meta name="keywords" content="{escape_html(', '.join(keywords))},AI工具替代,AI工具推荐">
    <link rel="canonical" href="https://www.aitoolbox.hk/alternatives/{slug}/">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(meta_desc)}">
    <meta property="og:url" content="https://www.aitoolbox.hk/alternatives/{slug}/">
    <meta property="og:image" content="{og_image}">
    <link rel="stylesheet" href="/css/style.css">
    <script type="application/ld+json">{breadcrumb_json}</script>
    <script type="application/ld+json">{article_schema_json}</script>
    {faq_page_schema}
    {BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><h1>🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></h1></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/alternatives/">替代方案</a> &gt; <span>{target_tool['name'] if target_tool else slug}</span>
    </nav>

    <main class="article-container">
        {target_card_html}

        <article class="article-body">
            {content_html}
        </article>

        {faq_html}
    </main>

    <footer class="footer">
        <p>&copy; 2026 AI工具宝箱 &middot; 每日精选优质AI工具 &middot; 最后更新 {today_iso}</p>
    </footer>
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''
    return html


def build_compare_slug_from_slugs(slugs):
    """从slug列表构建对比页slug（供内部链接使用）"""
    return '-'.join(sorted(slugs))


def load_compare_data():
    """加载对比数据文件"""
    compare_file = os.path.join(DATA_DIR, 'compare_data.json')
    if os.path.exists(compare_file):
        with open(compare_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"compares": [], "alternatives": [], "metadata": {}}


def load_quiz_data():
    """加载Quiz数据文件 (Phase 4)"""
    quiz_file = os.path.join(DATA_DIR, 'quiz_data.json')
    if os.path.exists(quiz_file):
        with open(quiz_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"quizzes": [], "metadata": {}}


def load_ranking_data():
    """加载排名数据文件 (Phase 5)"""
    ranking_file = os.path.join(DATA_DIR, 'ranking_data.json')
    if os.path.exists(ranking_file):
        with open(ranking_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"rankings": [], "metadata": {}}


# ════════════════════════════════════════════════════════
# Phase 4: Quiz 页面构建
# ════════════════════════════════════════════════════════

def build_quiz_page(quiz_data, all_tools, all_articles=None):
    """
    生成 Quiz/工具选择器页面 (Phase 4)
    URL: /quiz/{slug}/index.html 或 /quiz/index.html (总入口)
    覆盖关键词: "AI工具选择器"、"哪个AI工具好"、"AI工具推荐测试"
    """
    slug = quiz_data.get('slug', 'unknown')
    title = quiz_data.get('title', 'AI工具选择器')
    meta_desc = quiz_data.get('meta_description', '')
    keywords = quiz_data.get('keywords', [])
    questions = quiz_data.get('questions', [])
    content = quiz_data.get('content')  # AI生成的内容
    rec_tool_slugs = quiz_data.get('recommended_tools', [])
    category = quiz_data.get('category', 'all')
    is_main_entry = (quiz_data.get('target_url') == '/quiz/') or (slug == 'ai-tool-finder-2026')

    # 构建问答交互 HTML
    questions_html = ''
    for i, q in enumerate(questions):
        qid = q.get('id', f'q{i+1}')
        options_html = ''
        for j, opt in enumerate(q.get('options', [])):
            val = opt.get('value', f'opt{j}')
            label_text = opt.get('label', '')
            options_html += f'''                <label class="quiz-option" data-question="{qid}" data-value="{val}">
                    <input type="radio" name="{qid}" value="{val}"> {escape_html(label_text)}
                </label>\n'''
        questions_html += f'''            <div class="quiz-question" data-question-id="{qid}">
                <h3>{i+1}. {escape_html(q['text'])}</h3>
                <div class="quiz-options">{options_html}                </div>
            </div>
'''

    # 推荐工具卡片（基于答案匹配）
    rec_tools_html = ''
    if rec_tool_slugs:
        for rs in rec_tool_slugs[:8]:
            tool = next((t for t in all_tools if t['slug'] == rs), None)
            if not tool:
                continue
            rec_tools_html += f'''            <div class="quiz-recommendation" data-tool-slug="{tool['slug']}" style="display:none;">
                <a href="/tools/{tool['slug']}/index.html" class="rec-card">
                    <div class="rec-icon" style="background:{tool['color']};">{tool['emoji']}</div>
                    <div class="rec-info">
                        <strong>{escape_html(tool['name'])}</strong>
                        <span>{escape_html(tool.get('price',''))} | {tool['rating']}</span>
                        <p>{escape_html(tool['description'][:80])}</p>
                    </div>
                    <span class="rec-arrow">查看详情 →</span>
                </a>
            </div>\n'''

    # AI内容区域
    content_html = ''
    faq_section = ''
    faq_schema_list = []

    if content:
        # Intro
        intro = content.get('intro', '')
        if intro:
            content_html += f'<div class="quiz-intro">{markdown_to_html(intro)}</div>'

        # Tool recommendations from AI
        for tr in content.get('tool_recommendations', []):
            tname = tr.get('tool_name', 'Unknown')
            tprofile = tr.get('match_profile', '')
            strengths = tr.get('strengths', [])
            weaknesses = tr.get('weaknesses', [])
            strengths_html = ''.join(f'<li>{s}</li>' for s in strengths)
            weaknesses_html = ''.join(f'<li>{w}</li>' for w in weaknesses)
            content_html += f'''<div class="tool-rec-detail">
                <h3>{tname}</h3>
                <p>{tprofile}</p>
                <div class="tw-col">
                    <div><strong>优势</strong><ul>{strengths_html}</ul></div>
                    <div><strong>不足</strong><ul>{weaknesses_html}</ul></div>
                </div>
            </div>'''

        # Content sections
        for sec in content.get('content_sections', []):
            heading = sec.get('heading', '')
            body = sec.get('body', '')
            if heading and body:
                content_html += f'<section><h2>{escape_html(heading)}</h2>{markdown_to_html(body)}</section>'

        # FAQ
        faq_items = content.get('faq', [])
        for fi in faq_items:
            q, a = fi.get('question', ''), fi.get('answer', '')
            if q and a:
                faq_section += f'''<div class="faq-item"><details><summary>{escape_html(q)}</summary><div class="faq-answer">{markdown_to_html(a)}</div></details></div>\n'''
                faq_schema_list.append({'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}})

        # Conclusion
        conclusion = content.get('conclusion', '')
        if conclusion:
            content_html += f'<div class="quiz-conclusion">{markdown_to_html(conclusion)}</div>'

    if faq_section:
        faq_section = f'<div class="faq-section"><h3>常见问题</h3>{faq_section}</div>'

    # FAQ Schema
    faq_page_schema = ''
    if faq_schema_list:
        faq_sd = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_schema_list}
        faq_page_schema = f'<script type="application/ld+json">{json.dumps(faq_sd, ensure_ascii=False)}</script>'

    # Article Schema
    from datetime import datetime as _dtq
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": meta_desc,
        "datePublished": quiz_data.get("last_updated", _dtq.now().strftime('%Y-%m-%d')),
        "author": {"@type": "Organization", "name": "AI工具宝箱"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱"}
    }
    article_schema_json = json.dumps(article_schema, ensure_ascii=False, indent=2)

    # Breadcrumb
    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoolbox.hk/"},
            {"@type": "ListItem", "position": 2, "name": "AI工具选择器", "item": "https://www.aitoolbox.hk/quiz/"},
            {"@type": "ListItem", "position": 3, "name": title[:30], "item": f"https://www.aitoolbox.hk/quiz/{slug}/"}
        ]
    }
    breadcrumb_json = json.dumps(breadcrumb, ensure_ascii=False, indent=2)

    og_image = ensure_og_image(slug, data_obj=quiz_data, is_article=True)
    from datetime import datetime as _dt
    today_iso = _dt.now().strftime('%Y-%m-%d')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)} - AI工具宝箱</title>
    <meta name="description" content="{escape_html(meta_desc)}">
    <meta name="keywords" content="{escape_html(', '.join(keywords))},AI工具选择器,AI工具推荐">
    <link rel="canonical" href="https://www.aitoolbox.hk/quiz/{'/' if is_main_entry else slug + '/'}">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(meta_desc)}">
    <meta property="og:url" content="https://www.aitoolbox.hk/quiz/{'/' if is_main_entry else slug + '/'}">
    <meta property="og:image" content="{og_image}">
    <link rel="stylesheet" href="/css/style.css">
    <script type="application/ld+json">{breadcrumb_json}</script>
    <script type="application/ld+json">{article_schema_json}</script>
    {faq_page_schema}
{BAIDU_TONGJI}
    <style>
    .quiz-container {{ max-width:800px;margin:0 auto; }}
    .quiz-progress {{ display:flex;justify-content:space-between;margin-bottom:24px;padding:12px;background:#f8f9fa;border-radius:10px; }}
    .quiz-progress .step {{ font-size:12px;color:#999; }}
    .quiz-progress .step.active {{ color:#4285F4;font-weight:700; }}
    .quiz-question {{ background:#fff;padding:24px;border-radius:12px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,0.08); }}
    .quiz-question h3 {{ margin:0 0 16px;color:#333; }}
    .quiz-options {{ display:flex;flex-direction:column;gap:10px; }}
    .quiz-option {{ display:block;padding:14px 18px;border:2px solid #e8e8e8;border-radius:10px;cursor:pointer;transition:all 0.2s;font-size:15px; }}
    .quiz-option:hover {{ border-color:#4285F4;background:#f0f7ff; }}
    .quiz-option input:checked + span, .quiz-option.selected {{ border-color:#4285F4;background:#e8f0fe; }}
    .quiz-option input {{ display:none; }}
    .quiz-result {{ text-align:center;padding:32px;display:none; }}
    .quiz-result h2 {{ color:#4285F4;margin-bottom:20px; }}
    .quiz-recommendation {{ margin:12px 0; }}
    .rec-card {{ display:flex;align-items:center;gap:16px;padding:16px;border:1px solid #e8e8e8;border-radius:12px;text-decoration:none;color:inherit;transition:all 0.2s; }}
    .rec-card:hover {{ border-color:#4285F4;box-shadow:0 4px 12px rgba(66,133,244,0.15);transform:translateY(-1px); }}
    .rec-icon {{ width:48px;height:48px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px;flex-shrink:0; }}
    .rec-info {{ flex:1; }}
    .rec-info strong {{ display:block;font-size:16px; }}
    .rec-info span {{ color:#666;font-size:13px; }}
    .rec-info p {{ margin:4px 0 0;color:#888;font-size:13px; }}
    .rec-arrow {{ color:#4285F4;font-size:14px;flex-shrink:0; }}
    .btn-quiz-submit {{ display:block;width:100%;padding:16px;background:linear-gradient(135deg,#4285F4,#5b9aff);color:#fff;border:none;border-radius:12px;font-size:18px;font-weight:700;cursor:pointer;margin-top:16px;transition:opacity 0.2s; }}
    .btn-quiz-submit:hover {{ opacity:0.9; }}
    .quiz-intro {{ background:#f0f7ff;padding:20px;border-radius:10px;margin-bottom:24px;border-left:4px solid #4285F4; }}
    .quiz-conclusion {{ background:#f8f9fa;padding:20px;border-radius:10px;margin-top:24px; }}
    .tool-rec-detail {{ margin:20px 0;padding:20px;background:#fff;border-radius:10px;border:1px solid #eee; }}
    .tool-rec-detail h3 {{ color:#333;margin-top:0; }}
    .tw-col {{ display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:12px; }}
    @media(max-width:600px){{ .tw-col{{grid-template-columns:1fr;}} .rec-card{{flex-wrap:wrap;}} }}
    </style>
'''

    # Build progress steps HTML (outside f-string to avoid scope issues)
    _ps_parts = []
    for i, q in enumerate(questions):
        _qid = q.get('id', 'q' + str(i+1))
        _qtext = escape_html(q['text'][:15])
        _active = ' active' if i == 0 else ''
        _ps_parts.append('<span class="step' + _active + '" data-step="' + _qid + '">' + str(i+1) + '. ' + _qtext + '</span>')
    _ps_parts.append('<span class="step" data-step="result">结果</span>')
    progress_steps = '\n                    '.join(_ps_parts)

    html += f'''
</head>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><h1>AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></h1></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/quiz/">AI工具选择器</a> &gt; <span>{title[:25]}...</span>
    </nav>

    <main class="article-container">
        <div class="quiz-container">
            <h1 style="text-align:center;">{escape_html(title)}</h1>

            <div id="quizForm">
                <div class="quiz-progress">
                    {progress_steps}
                </div>

{questions_html}
                <button class="btn-quiz-submit" onclick="showQuizResult()">查看我的推荐工具</button>
            </div>

            <div id="quizResult" class="quiz-result">
                <h2>根据你的需求，我们推荐以下AI工具</h2>
{rec_tools_html}
                <button class="btn-quiz-submit" style="margin-top:20px;" onclick="resetQuiz()" style="background:#667eea;">重新测试</button>
            </div>

            {content_html}

            {faq_section}
        </div>
    </main>

    <footer class="footer">
        <p>&copy; 2026 AI工具宝箱 &middot; 每日精选优质AI工具 &middot; 最后更新 {today_iso}</p>
    </footer>
''' + BACK_TO_TOP_BLOCK + '''
<script>
// Quiz 交互逻辑
function showQuizResult() {
    var answers = {};
    document.querySelectorAll('.quiz-option input:checked').forEach(function(el) {
        answers[el.name] = el.value;
    });
    if(Object.keys(answers).length < ''' + str(len(questions)) + ''') {
        alert('请回答完所有问题后再查看推荐！');
        return;
    }
    document.getElementById('quizForm').style.display = 'none';
    var resultDiv = document.getElementById('quizResult');
    resultDiv.style.display = 'block';
    
    // 显示所有推荐工具（简单版：全部显示，后续可做精确匹配逻辑）
    resultDiv.querySelectorAll('.quiz-recommendation').forEach(function(el) { el.style.display='block'; });
    window.scrollTo({top:resultDiv.offsetTop - 20, behavior:'smooth'});
}
function resetQuiz() {
    document.getElementById('quizResult').style.display = 'none';
    document.getElementById('quizForm').style.display = 'block';
    document.querySelectorAll('.quiz-option input').forEach(function(el){el.checked=false;});
    document.querySelectorAll('.quiz-option').forEach(function(el){el.classList.remove('selected');});
    window.scrollTo({top:0,behavior:'smooth'});
}
document.querySelectorAll('.quiz-option').forEach(function(opt){
    opt.addEventListener('click',function(){
        var name=this.querySelector('input').name;
        document.querySelectorAll('.quiz-option[name="'+name+'"]').forEach(function(o){o.classList.remove('selected');});
        this.classList.add('selected');
        this.querySelector('input').checked=true;
    });
});
</script>
</body>
</html>'''
    return html


# ════════════════════════════════════════════════════════
# Phase 5: Ranking 页面构建
# ════════════════════════════════════════════════════════

def build_ranking_page(ranking_data, all_tools, all_articles=None):
    """
    生成排名页面 (Phase 5)
    URL: /ranking/{slug}/index.html 或 /ranking/index.html (总榜入口)
    覆盖关键词: "AI工具排行榜"、"AI工具排名2026"、"热门AI工具"
    """
    slug = ranking_data.get('slug', 'unknown')
    title = ranking_data.get('title', 'AI工具排行榜')
    meta_desc = ranking_data.get('meta_description', '')
    keywords = ranking_data.get('keywords', [])
    ranked_tools = ranking_data.get('ranked_tools', [])[:20]  # 展示前20
    total_tools = ranking_data.get('total_tools', len(ranked_tools))
    content = ranking_data.get('content')  # AI分析内容
    rtype = ranking_data.get('type', 'special')
    category = ranking_data.get('category', '')
    icon = ranking_data.get('icon', '📊')
    methodology = ranking_data.get('methodology', {})
    last_updated = ranking_data.get('last_updated', '')

    is_overall = (slug == '2026-ai-tools-overall-ranking')

    # 排名表格
    table_rows = ''
    medals = ['\U0001F947', '\U0001F948', '\U0001F949']  # 金银铜
    for i, item in enumerate(ranked_tools):
        rank = item.get('rank', i+1)
        medal = medals[i] if i < 3 else str(rank)
        score = item.get('score', 0)
        sd = item.get('scores', {})
        tool_name = item.get('name', 'Unknown')
        tool_emoji = item.get('emoji', '🔧')
        tool_color = item.get('color', '#666')
        price = item.get('price', '')
        rating = item.get('rating', '')
        badge_html = ''
        badge = item.get('badge', {})
        if isinstance(badge, dict) and badge.get('text'):
            btype = badge.get('type', '')
            bcolor_map = {'hot': '#ff4444', 'new': '#00aa00', 'pick': '#667eea'}
            bcolor = bcolor_map.get(btype, '#667eea')
            badge_html = '<span class="badge" style="background:' + bcolor + ';color:#fff;font-size:11px;padding:2px 6px;border-radius:3px;">' + badge['text'] + '</span>'
        
        # 分数条
        if rank <= 3:
            bar_color = '#4285F4'
        elif rank <= 10:
            bar_color = '#667eea'
        else:
            bar_color = '#999'
        bar_width = min(score, 100)
        
        # 趋势箭头
        if rank <= 3:
            trend_color = '#00aa00'
            trend_sym = '&#8593;'
        elif rank > 15:
            trend_color = '#ff4444'
            trend_sym = ''
        else:
            trend_color = '#666'
            trend_sym = '&#8594;' if rank <= 10 else ''
        
        table_rows += f'''                <tr class="rank-row" data-rank="{rank}">
                    <td class="rank-num">{medal}</td>
                    <td class="rank-tool">
                        <a href="/tools/{item['slug']}/index.html" style="display:flex;align-items:center;gap:10px;text-decoration:none;color:inherit;">
                            <span style="font-size:24px;background:{tool_color};width:40px;height:40px;border-radius:10px;display:inline-flex;align-items:center;justify-content:center;">{tool_emoji}</span>
                            <span style="font-weight:600;">{escape_html(tool_name)}</span> {badge_html}
                        </a>
                    </td>
                    <td class="rank-score">
                        <div class="score-bar"><div class="score-fill" style="width:{bar_width}%;background:{bar_color};"></div></div>
                        <span class="score-val">{score}</span>
                    </td>
                    <td class="rank-rating">{rating or '-'}</td>
                    <td class="rank-price">{escape_html(price) or '免费'}</td>
                    <td class="rank-trend">
                        <span style="color:{trend_color};">{trend_sym}</span>
                    </td>
                </tr>
'''

    # AI内容区域
    content_html = ''
    faq_section = ''
    faq_schema_list = []
    trend_badge = ''
    from datetime import datetime as _rdt

    if content:
        # Summary / 综述
        summary = content.get('summary', '')
        if summary:
            content_html += f'<div class="ranking-summary">{markdown_to_html(summary)}</div>'
            trend_badge = '<div class="live-badge">实时更新 · 数据截至 ' + (last_updated or _rdt.now().strftime('%Y-%m-%d')) + '</div>'

        # Top3 分析
        top3 = content.get('top3_analysis', [])
        if top3:
            top3_html = ''
            for ta in top3:
                top3_html += f'''<div class="podium-analysis">
                    <h3>第{ta['rank']}名 - {ta.get('tool_name','')}</h3>
                    {markdown_to_html(ta.get('analysis',''))}
                </div>'''
            content_html += f'<div class="top3-section">{top3_html}</div>'

        # 趋势分析
        trend = content.get('trend_analysis', '')
        if trend:
            content_html += f'<div class="trend-section"><h2>行业趋势分析</h2>{markdown_to_html(trend)}</div>'

        # 分类洞察
        insights = content.get('category_insights', [])
        if insights:
            ins_html = ''.join(f'<div class="insight-card"><h3>{escape_html(i["insight_title"])}</h3>{markdown_to_html(i["content"])}</div>' for i in insights)
            content_html += f'<div class="insights-section"><h2>深度洞察</h2>{ins_html}</div>'

        # FAQ
        for fi in content.get('faq', []):
            q, a = fi.get('question', ''), fi.get('answer', '')
            if q and a:
                faq_section += f'<div class="faq-item"><details><summary>{escape_html(q)}</summary><div class="faq-answer">{markdown_to_html(a)}</div></details></div>\n'
                faq_schema_list.append({'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}})

        # Conclusion
        conclusion = content.get('conclusion', '')
        if conclusion:
            content_html += f'<div class="ranking-conclusion">{markdown_to_html(conclusion)}</div>'

    if faq_section:
        faq_section = f'<div class="faq-section"><h3>关于本排名</h3>{faq_section}</div>'

    # FAQ Schema
    faq_ps = ''
    if faq_schema_list:
        faq_sd = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_schema_list}
        faq_ps = f'<script type="application/ld+json">{json.dumps(faq_sd, ensure_ascii=False)}</script>'

    # Schema (use _rdt already imported above)
    # _dtr alias for backward compat
    _dtr = _rdt
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": meta_desc,
        "datePublished": ranking_data.get("last_updated", _dtr.now().strftime('%Y-%m-%d'))[:10],
        "dateModified": last_updated[:10] if last_updated else _dtr.now().strftime('%Y-%m-%d'),
        "author": {"@type": "Organization", "name": "AI工具宝箱"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱"}
    }
    article_schema_json = json.dumps(article_schema, ensure_ascii=False, indent=2)

    # Breadcrumb
    bc_name_2 = "AI工具排行榜" if is_overall else (category + "排行榜" if category else "排行榜")
    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoolbox.hk/"},
            {"@type": "ListItem", "position": 2, "name": "AI工具排行", "item": "https://www.aitoolbox.hk/ranking/"},
            {"@type": "ListItem", "position": 3, "name": title[:30], "item": f"https://www.aitoolbox.hk/ranking/{slug}/"}
        ]
    }
    breadcrumb_json = json.dumps(breadcrumb, ensure_ascii=False, indent=2)

    og_image = ensure_og_image(slug, data_obj=ranking_data, is_article=True)

    # 相关链接：其他排名
    related_links = ''
    other_ranks = [
        ('2026-ai-tools-overall-ranking', '综合热度榜'),
        ('best-free-ai-tools-ranking-2026', '免费工具榜'),
        ('best-value-ai-tools-ranking-2026', '性价比榜'),
        ('rising-ai-tools-2026-trending', '新兴趋势榜')
    ]
    for rslug, rname in other_ranks:
        if rslug != slug:
            related_links += f'<a href="/ranking/{rslug}/" class="rank-sub-link">{rname} →</a>\n'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)} - AI工具宝箱</title>
    <meta name="description" content="{escape_html(meta_desc)}">
    <meta name="keywords" content="{escape_html(', '.join(keywords))},AI工具排行榜,AI工具排名,AI热度排行">
    <link rel="canonical" href="https://www.aitoolbox.hk/ranking/{slug}/">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(meta_desc)}">
    <meta property="og:url" content="https://www.aitoolbox.hk/ranking/{slug}/">
    <meta property="og:image" content="{og_image}">
    <link rel="stylesheet" href="/css/style.css">
    <script type="application/ld+json">{breadcrumb_json}</script>
    <script type="application/ld+json">{article_schema_json}</script>
    {faq_ps}
{BAIDU_TONGJI}
    <style>
    .ranking-hero {{ text-align:center;padding:32px 20px;background:linear-gradient(135deg,#f0f4ff,#e8f0fe);border-radius:16px;margin-bottom:28px; }}
    .ranking-hero .hero-icon {{ font-size:56px;margin-bottom:12px; }}
    .ranking-hero h1 {{ margin:0 0 8px;font-size:26px; }}
    .ranking-hero p {{ color:#666;margin:0;font-size:15px; }}
    .live-badge {{ display:inline-block;background:#00c853;color:#fff;font-size:12px;padding:3px 12px;border-radius:12px;margin-top:10px;font-weight:600;animation:pulse 2s infinite; }}
    @keyframes pulse {{ 0%{{opacity:1}} 50%{{opacity:.7}} 100%{{opacity:1}} }}
    .ranking-table-wrap {{ overflow-x:auto;background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:28px; }}
    .ranking-table {{ width:100%;border-collapse:collapse;min-width:600px; }}
    .ranking-table th {{ background:#f8f9fa;padding:14px 12px;text-align:left;font-size:13px;color:#666;border-bottom:2px solid #eee;white-space:nowrap; }}
    .ranking-table td {{ padding:12px;border-bottom:1px solid #f0f0f0;vertical-align:middle; }}
    .rank-row:hover {{ background:#f8f9ff; }}
    .rank-num {{ font-size:20px;text-align:center;width:50px;font-weight:700; }}
    .rank-tool a {{ font-weight:600; }}
    .rank-score {{ min-width:120px; }}
    .score-bar {{ width:80px;height:6px;background:#eee;border-radius:3px;display:inline-block;vertical-align:middle;overflow:hidden; }}
    .score-fill {{ height:100%;border-radius:3px;transition:width .5s; }}
    .score-val {{ font-weight:700;font-size:14px;margin-left:6px; }}
    .rank-rating {{ white-space:nowrap; }}
    .rank-price {{ color:#666;font-size:13px;white-space:nowrap; }}
    .rank-trend {{ text-align:center;font-size:16px; }}
    .rank-sub-nav {{ display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;justify-content:center; }}
    .rank-sub-link {{ display:inline-block;padding:8px 16px;background:#f0f4ff;color:#4285F4;border-radius:20px;text-decoration:none;font-size:13px;font-weight:600;transition:all .2s; }}
    .rank-sub-link:hover {{ background:#4285F4;color:#fff; }}
    .ranking-summary {{ background:#f0f7ff;padding:20px 24px;border-left:4px solid #4285F4;border-radius:8px;margin-bottom:24px;font-size:15px;line-height:1.8; }}
    .podium-analysis {{ background:#fff;padding:20px;border-radius:10px;margin:12px 0;border:1px solid #eee; }}
    .podium-analysis h3 {{ color:#333;margin-top:0; }}
    .trend-section,.insights-section {{ margin:28px 0; }}
    .insight-card {{ background:#fafbfc;padding:20px;border-radius:10px;margin:12px 0;border-left:4px solid #667eea; }}
    .insight-card h3 {{ margin-top:0;color:#333; }}
    .ranking-conclusion {{ background:#f8f9fa;padding:24px;border-radius:10px;margin-top:24px; }}
    .methodology-note {{ background:#fffbf0;border:1px solid #ffd666;border-radius:8px;padding:16px 20px;margin:20px 0;font-size:13px;color:#856404; }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><h1>AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></h1></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href/">首页</a> &gt; <a href="/ranking/">AI工具排行</a> &gt; <span>{title[:25]}...</span>
    </nav>

    <main class="article-container">
        <div class="ranking-hero">
            <div class="hero-icon">{icon}</div>
            <h1>{escape_html(title)}</h1>
            <p>{escape_html(meta_desc[:120])}</p>
            {trend_badge}
        </div>

        <div class="rank-sub-nav">
            {related_links}
        </div>

        <div class="ranking-table-wrap">
            <table class="ranking-table">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>工具名称</th>
                        <th>综合分</th>
                        <th>评分</th>
                        <th>价格</th>
                        <th>趋势</th>
                    </tr>
                </thead>
                <tbody>
{table_rows}
                </tbody>
            </table>
        </div>

        {content_html}

        {faq_section}

        <div class="methodology-note">
            <strong>排名说明：</strong>本排名基于多维度数据综合计算（热度30% + 质量25% + 功能20% + 价格15% + 新鲜度10%），每日自动更新。数据来源于工具官方信息、用户评价聚合和市场活跃度指标。排名仅供参考，具体选择请根据个人需求和实际体验决定。
        </div>
    </main>

    <footer class="footer">
        <p>&copy; 2026 AI工具宝箱 &middot; 每日精选优质AI工具 &middot; 更新于 {(last_updated or _rdt.now().strftime('%Y-%m-%d %H:%M'))}</p>
    </footer>
''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''
    return html


def build_category_page(category_name, tools_in_category):
    """生成单个分类页的完整HTML"""
    category_slug = get_category_slug(category_name)
    
    tools_html = ''
    for i, t in enumerate(tools_in_category):
        badge_html = f'<span class="badge badge-{t.get("badge", {}).get("type", "")}">{t.get("badge", {}).get("text", "")}</span>' if t.get('badge') else ''
        tags_html = ''.join([f'<span class="tag {tag.get("type", "")}">{tag.get("text", "")}</span>' for tag in t.get('tags', [])])
        tools_html += f'''                        <article class="tool-card fade-in" style="animation-delay: {i * 0.05}s;" onclick="location.href=\'/tools/{t['slug']}/index.html\'">
                            <div class="tool-icon" style="background:{t['color']};">{t['emoji']}</div>
                            <h4>{escape_html(t['name'])} {badge_html}</h4>
                            <p class="desc">{escape_html(t['description'])}</p>
                            <div class="tags">{tags_html}</div>
                            <div class="meta">
                                <span class="rating">{t['rating']}</span>
                                <span class="visits">👁 {t['visits']}</span>
                            </div>
                        </article>\n'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(category_name)} - AI工具宝箱</title>
    <meta name="description" content="AI工具宝箱收录{escape_html(category_name)}分类下最新最全的AI工具。">
    <meta name="keywords" content="AI工具,{escape_html(category_name)},人工智能,效率工具,AI导航">
    <link rel="canonical" href="https://www.aitoolbox.hk/category/{category_slug}/">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{escape_html(category_name)} - AI工具宝箱">
    <meta property="og:description" content="AI工具宝箱收录{escape_html(category_name)}分类下最新最全的AI工具。">
    <meta property="og:url" content="https://www.aitoolbox.hk/category/{category_slug}/">
    <meta property="og:image" content="https://www.aitoolbox.hk/images/og/category-{category_slug}-og.png">
    <link rel="stylesheet" href="/css/style.css">
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {{
                "@type": "ListItem",
                "position": 1,
                "name": "首页",
                "item": "https://www.aitoolbox.hk/"
            }},
            {{
                "@type": "ListItem",
                "position": 2,
                "name": "{escape_html(category_name)}",
                "item": "https://www.aitoolbox.hk/category/{category_slug}/"
            }}
        ]
    }}
    </script>
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "{escape_html(category_name)} - AI工具宝箱",
        "description": "AI工具宝箱收录{escape_html(category_name)}分类下最新最全的AI工具。",
        "url": "https://www.aitoolbox.hk/category/{category_slug}/index.html"
    }}
    </script>
{BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><h1>🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></h1></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <span>{escape_html(category_name)}</span>
    </nav>

    <main class="container">
        <section class="section">
            <div class="section-header">
                <h3>{escape_html(category_name)}</h3>
            </div>
            <div class="tools-grid">
{tools_html}
            </div>
        </section>
    </main>

    <footer class="footer">
        <p>© 2026 AI工具宝箱 · 每日精选优质AI工具</p>
    </footer>
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''
    return html


def build_article_page(article, all_articles, all_tools=None):
    """生成单个文章页的完整HTML"""
    slug = article['slug']

    # ── 相关工具（通过关键词匹配：标题/描述中提到哪些工具就推哪些）────
    related_tools_html = ''
    if all_tools:
        article_title = article.get('title', '').lower()
        article_desc = article.get('description', '').lower()
        article_content = article.get('content', '').lower()
        # 找工具名在文章中出现的工具
        matched_tools = []
        for t in all_tools:
            tool_name_lower = t.get('name', '').lower()
            if (tool_name_lower in article_title or
                tool_name_lower in article_desc or
                tool_name_lower in article_content):
                matched_tools.append(t)
        # 不够5个则按分类补充
        if len(matched_tools) < 5:
            article_category = article.get('category', '')
            same_cat_tools = [t for t in all_tools
                             if t.get('category') == article_category
                             and t not in matched_tools]
            for t in same_cat_tools:
                if len(matched_tools) >= 5:
                    break
                matched_tools.append(t)
        # 再不够，取热门工具
        if len(matched_tools) < 5:
            for t in sorted(all_tools, key=lambda x: x.get('visits', '0'), reverse=True):
                if len(matched_tools) >= 5:
                    break
                if t not in matched_tools:
                    matched_tools.append(t)

        if matched_tools:
            cards = ''
            for t in matched_tools[:5]:
                cards += f'''<a href="/tools/{t['slug']}/index.html" class="related-card">
                    <div style="font-size:24px;margin-bottom:8px;">{t['emoji']}</div>
                    <div style="font-weight:600;">{escape_html(t['name'])}</div>
                    <div style="font-size:13px;color:#666;">{escape_html(t.get('category', ''))}</div>
                </a>
'''
            related_tools_html = f'''<div class="related-tools">
            <h3>🔧 相关工具</h3>
            <div class="related-grid">{cards}</div>
        </div>'''

    # ── 相关文章 ──────────────────────────────────────────────────────
    related_html = ''
    same_category = [a for a in all_articles if a['slug'] != slug and a.get('category') == article.get('category')]
    if len(same_category) < 2:
        same_category = [a for a in all_articles if a['slug'] != slug][:3]
    if same_category:
        cards = ''
        for a in same_category[:3]:
            cards += f'''<a href="/articles/{a['slug']}/index.html" class="related-card">
                <div style="font-weight:600;margin-bottom:4px;">{escape_html(a['title'])}</div>
                <div style="font-size:13px;color:#666;">{a.get('dateFull', a.get('date', ''))}</div>
            </a>\n'''
        related_html = f'''<div class="related-tools">
            <h3>📖 相关文章</h3>
            <div class="related-grid">{cards}</div>
        </div>'''

    # OG Image（自动生成缺失的OG图片）
    og_image = ensure_og_image(slug, data_obj=article, is_article=True)

    # 信息图（文章内嵌）
    infographic_path = os.path.join(BASE_DIR, 'images', 'infographics', f'{slug}-infographic.png')
    has_infographic = os.path.exists(infographic_path)
    infographic_html = ''
    if has_infographic:
        infographic_html = f'''<figure class="tool-infographic">
            <img src="/images/infographics/{slug}-infographic.png" alt="{escape_html(article['title'])} - 数据对比信息图" width="1200" height="630" loading="lazy">
            <figcaption>{escape_html(article['title'])} · 核心数据一览</figcaption>
        </figure>'''

    from datetime import datetime
    today_iso = datetime.now().strftime('%Y-%m-%d')
    article_date = article.get('dateFull', today_iso)
    article_date_modified = article.get('dateModified', article_date)
    article_category = article.get('category', '文章')
    article_category_slug = get_category_slug(article_category)

    breadcrumb_article_data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "首页",
                "item": "https://www.aitoolbox.hk/"
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": article_category,
                "item": f"https://www.aitoolbox.hk/category/{article_category_slug}/"
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": article['title'],
                "item": f"https://www.aitoolbox.hk/articles/{slug}/"
            }
        ]
    }
    breadcrumb_article_json = json.dumps(breadcrumb_article_data, ensure_ascii=False, indent=2)

    structured_data = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article['title'],
        "description": article.get('description', ''),
        "datePublished": article_date,
        "dateModified": article_date_modified,
        "author": {"@type": "Organization", "name": "AI工具宝箱"},
        "publisher": {
            "@type": "Organization",
            "name": "AI工具宝箱",
            "logo": {
                "@type": "ImageObject",
                "url": "https://www.aitoolbox.hk/images/logo.png"
            }
        },
        "image": og_image if og_image else "https://www.aitoolbox.hk/images/logo.png",
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"https://www.aitoolbox.hk/articles/{slug}/"
        }
    }, ensure_ascii=False, indent=2)

    content_html = markdown_to_html(article.get('content', ''))

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(article['title'])} - AI工具宝箱</title>
    <meta name="description" content="{escape_html(article.get('description', ''))}">
    <meta name="keywords" content="{escape_html(article.get('keywords', ''))}">
    <link rel="canonical" href="https://www.aitoolbox.hk/articles/{slug}/">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(article['title'])} - AI工具宝箱">
    <meta property="og:description" content="{escape_html(article.get('description', ''))}">
''' + (f'    <meta property="og:image" content="{og_image}">\n' if og_image else '') + f'''    <meta property="og:url" content="https://www.aitoolbox.hk/articles/{slug}/">
    <meta property="og:site_name" content="AI工具宝箱">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(article['title'])} - AI工具宝箱">
    <meta name="twitter:description" content="{escape_html(article.get('description', ''))}">
''' + (f'    <meta name="twitter:image" content="{og_image}">\n' if og_image else '') + f'''    <link rel="stylesheet" href="/css/style.css">
    <script type="application/ld+json">{breadcrumb_article_json}</script>
    <script type="application/ld+json">{structured_data}</script>
{BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><h1>🛠️ AI工具宝箱 <span>每日更新 · 已收录 500+ 工具</span></h1></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <span>{escape_html(article.get('category', '文章'))}</span> &gt; <span>{escape_html(article['title'])[:20]}...</span>
    </nav>

    <main class="article-container">
        <article class="article-body">
            <h1 style="margin-bottom:16px;">{escape_html(article['title'])}</h1>
            <div style="color:#999;font-size:14px;margin-bottom:24px;">
                {article.get('dateFull', article.get('date', ''))} · {escape_html(article.get('category', ''))}
            </div>
            {infographic_html}
            {content_html}
        </article>

        {related_html}

        {related_tools_html}
    </main>

    <footer class="footer">
        <p>© 2026 AI工具宝箱 · 每日精选优质AI工具</p>
    </footer>
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''
    return html


def build_article_list_pages(articles):
    """生成文章分页列表页（/articles/page/1, page/2...）
    每页 10 篇，并加入 rel=next/prev + canonical"""
    
    ITEMS_PER_PAGE = 10
    total_pages = max(1, (len(articles) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    
    for page_num in range(1, total_pages + 1):
        start_idx = (page_num - 1) * ITEMS_PER_PAGE
        end_idx = min(start_idx + ITEMS_PER_PAGE, len(articles))
        page_articles = articles[start_idx:end_idx]
        
        # 生成当前页文章 HTML
        articles_html = ''
        for i, a in enumerate(page_articles):
            articles_html += f'''                        <article class="article-card" style="animation-delay: {i * 0.05}s;">
                            <h3><a href="/articles/{a['slug']}/index.html">{escape_html(a['title'])}</a></h3>
                            <div class="article-meta">
                                <span class="date">{a.get('dateFull', a.get('date', ''))}</span>
                                <span class="category">{escape_html(a.get('category', ''))}</span>
                            </div>
                            <p class="summary">{escape_html(a.get('description', '')[:150])}</p>
                        </article>\n'''
        
        # 生成分页导航 HTML
        pagination_html = '<div class="pagination">'
        if page_num > 1:
            pagination_html += f'<a href="/articles/page/{page_num - 1}/" class="prev">&larr; 上一页</a>\n'
        pagination_html += f'<span class="page-info">{page_num} / {total_pages}</span>\n'
        if page_num < total_pages:
            pagination_html += f'<a href="/articles/page/{page_num + 1}/" class="next">下一页 &rarr;</a>\n'
        pagination_html += '</div>'
        
        # 生成链接标签（rel next/prev/canonical）
        link_tags = f'    <link rel="canonical" href="https://www.aitoolbox.hk/articles/page/{page_num}/">\n'
        if page_num > 1:
            link_tags += f'    <link rel="prev" href="https://www.aitoolbox.hk/articles/page/{page_num - 1}/">\n'
        if page_num < total_pages:
            link_tags += f'    <link rel="next" href="https://www.aitoolbox.hk/articles/page/{page_num + 1}/">\n'
        
        # 生成页面 HTML
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI工具宝箱 - 最新文章 第{page_num}页</title>
    <meta name="description" content="AI工具宝箱最新文章列表，分享AI工具评测、使用教程、行业资讯等内容。第{page_num}页。">
    <meta name="keywords" content="AI工具,AI文章,AI评测,AI教程">
    {link_tags}    <meta property="og:type" content="website">
    <meta property="og:title" content="AI工具宝箱 - 最新文章">
    <meta property="og:description" content="AI工具宝箱最新文章列表，分享AI工具评测、使用教程、行业资讯等内容。">
    <meta property="og:url" content="https://www.aitoolbox.hk/articles/page/{page_num}/">
    <link rel="stylesheet" href="/css/style.css">
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {{
                "@type": "ListItem",
                "position": 1,
                "name": "首页",
                "item": "https://www.aitoolbox.hk/"
            }},
            {{
                "@type": "ListItem",
                "position": 2,
                "name": "文章列表",
                "item": "https://www.aitoolbox.hk/articles/page/1/"
            }},
            {{
                "@type": "ListItem",
                "position": 3,
                "name": "第 {page_num} 页",
                "item": "https://www.aitoolbox.hk/articles/page/{page_num}/"
            }}
        ]
    }}
    </script>
{BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><h1>&#x1F6E0; AI工具宝箱 <span>每日更新 · 最新资讯</span></h1></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/articles/page/1/">文章列表</a> &gt; <span>第 {page_num} 页</span>
    </nav>

    <main class="article-container">
        <h2 style="margin-bottom:24px;">&#x1F4DD; 最新文章</h2>
        <div class="articles-list">
{articles_html}
        </div>
        
        {pagination_html}
    </main>

    <footer class="footer">
        <p>&#xA9; 2026 AI工具宝箱 · 每日精选优质AI工具</p>
    </footer>
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''

        # 创建目录并保存文件
        dir_path = os.path.join(BASE_DIR, 'articles', 'page', str(page_num))
        os.makedirs(dir_path, exist_ok=True)
        with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'[OK] articles/page/{page_num}/index.html')
    
    return total_pages


def replace_between_tags(html, start_tag, new_content):
    """通过 div 嵌套深度精确替换标签间内容，避免正则贪婪匹配破坏HTML结构"""
    start_idx = html.find(start_tag)
    if start_idx == -1:
        print(f'[WARN] 未找到标记: {start_tag}')
        return html

    content_start = start_idx + len(start_tag)
    depth = 1
    pos = content_start

    while pos < len(html) and depth > 0:
        next_open = html.find('<div', pos)
        next_close = html.find('</div>', pos)

        if next_close == -1:
            print(f'[WARN] 未找到闭合标签: {start_tag}')
            return html

        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + 4
        else:
            depth -= 1
            if depth == 0:
                return html[:content_start] + '\n' + new_content + '\n                    </div>' + html[next_close + 6:]
            pos = next_close + 6

    return html


def build_index_page(tools, articles):
    # 生成静态首页
    index_html_template = os.path.join(BASE_DIR, 'index.html')
    with open(index_html_template, 'r', encoding='utf-8') as f:
        html = f.read()

    # 首屏 12 个工具静态渲染（改善 LCP）
    tools_html = ''
    for i, t in enumerate(tools[:12]):  # 只渲染前 12 个
        badge_html = f'<span class="badge badge-{t.get("badge", {}).get("type", "")}">{t.get("badge", {}).get("text", "")}</span>' if t.get('badge') else ''
        tags_html = ''.join([f'<span class="tag {tag.get("type", "")}">{tag.get("text", "")}</span>' for tag in t.get('tags', [])])
        tools_html += f'''                        <article class="tool-card fade-in" style="animation-delay: {i * 0.05}s;" onclick="location.href=\'/tools/{t['slug']}/index.html\'">
                            <div class="tool-icon" style="background:{t['color']};">{t['emoji']}</div>
                            <h4>{escape_html(t['name'])} {badge_html}</h4>
                            <p class="desc">{escape_html(t['description'])}</p>
                            <div class="tags">{tags_html}</div>
                            <div class="meta">
                                <span class="rating">{t['rating']}</span>
                                <span class="visits">👁 {t['visits']}</span>
                            </div>
                        </article>\n'''
    
    # 轻量化工具数据（首页JS只需展示字段，content/pros/cons/features等大字段去掉）
    # 这些字段的完整内容在各自独立的工具详情页（静态HTML）中，不影响SEO
    LIGHTWEIGHT_KEYS = {'name', 'slug', 'emoji', 'color', 'description', 'category',
                        'tags', 'rating', 'visits', 'badge', 'url', 'price', 'platform'}
    def make_lightweight(tool_list):
        return [{k: v for k, v in t.items() if k in LIGHTWEIGHT_KEYS} for t in tool_list]

    # 其余工具存储到 data 属性（JS 动态加载）
    remaining_tools_json = json.dumps(make_lightweight(tools[12:]), ensure_ascii=False, indent=2)

    # 对全部工具的懒加载占位符（分类筛选时需要）
    all_tools_json = json.dumps(make_lightweight(tools), ensure_ascii=False, indent=2)
        
    articles_html = ''
    for a in articles[:6]:
        articles_html += f'''                        <li>
                            <span class="date">{a.get('date', '')}</span>
                            <a class="title" href="/articles/{a['slug']}/index.html">{escape_html(a['title'])}</a>
                        </li>\n'''
    
    # 动态生成热门分类列表
    category_counts = get_category_stats(tools)
    categories_html = ''
    # 按照 index.html 中的顺序
    ordered_categories = ["AI对话", "AI写作", "AI绘画", "AI编程", "AI视频", "AI音频", "AI办公", "AI设计", "AI搜索", "AI翻译", "AI自动化", "AI效率"]
    for category in ordered_categories:
        count = category_counts.get(category, 0)
        # 假设分类页面路径为 /category/slug/index.html
        category_slug = get_category_slug(category)
        categories_html += f'''                        <li><a href="/category/{category_slug}/index.html">{category} ({count})</a></li>\n'''

    # 更新页脚链接
    footer_links_html = '''            <a href="/about.html">关于我们</a>
            <a href="/contact.html">联系方式</a>
            <a href="/privacy.html">隐私政策</a>
            <a href="/links.html">友情链接</a>''' # 暂时使用占位符链接

    # 替换工具数量（动态计算）
    all_tools_count = 0
    tools_json_path = os.path.join(DATA_DIR, 'tools.json')
    if os.path.exists(tools_json_path):
        with open(tools_json_path, 'r', encoding='utf-8') as f:
            all_tools_data = json.load(f)
            all_tools_count = len(all_tools_data)
    if all_tools_count > 100:
        count_text = f'已收录 {all_tools_count // 100 * 100}+ 工具'
    else:
        count_text = f'已收录 {all_tools_count} 款工具'
    html = re.sub(r'每日更新 · 已收录 \d+\+ 工具', f'每日更新 · {count_text}', html)
    html = re.sub(r'每日更新 · 收录工具 持续更新', f'每日更新 · {count_text}', html)

    # 动态替换 stats 区域数据（精选工具数量 + 分类数量）
    cat_stats = get_category_stats(tools)
    cat_count = len(cat_stats)
    if all_tools_count > 100:
        tool_stat_text = f'{all_tools_count // 100 * 100}+'
    else:
        tool_stat_text = str(all_tools_count)
    html = re.sub(r'<div class="num">20\+</div>', f'<div class="num">{tool_stat_text}</div>', html)
    html = re.sub(r'<div class="label">精选工具</div>', '<div class="label">精选工具</div>', html)
    html = re.sub(r'<div class="num">12</div>(?=\s*<div class="label">工具分类</div>)', f'<div class="num">{cat_count}</div>', html)

    # 替换内容（replace_between_tags 通过 div 嵌套深度精确匹配，不会破坏 HTML 结构）
    html = replace_between_tags(html, '<div class="tools-grid" id="toolsGrid">', tools_html)
    html = re.sub(r'(<ul id="articleList">)[\s\S]*?(</ul>)', lambda m: m.group(1) + '\n' + articles_html + '                    </ul>', html)
    html = re.sub(r'(<div class="sidebar-card">\s*<h4>&#x1F525; 热门分类</h4>\s*<ul>)[\s\S]*?(</ul>\s*</div>)', lambda m: m.group(1) + '\n' + categories_html + '                    </ul>\n                </div>', html)
    html = re.sub(r'(<div class="footer-links">)[\s\S]*?(</div>)', lambda m: m.group(1) + '\n' + footer_links_html + '\n        </div>', html)
    
    # 生成外部工具数据文件（避免首页内联 4.7MB JSON）
    tools_data_js_path = os.path.join(BASE_DIR, 'js', 'tools-data.js')
    os.makedirs(os.path.dirname(tools_data_js_path), exist_ok=True)
    with open(tools_data_js_path, 'w', encoding='utf-8') as f:
        f.write(f'window.__ALL_TOOLS__ = {all_tools_json};\nwindow.__REMAINING_TOOLS__ = {remaining_tools_json};\n')
    print(f'[OK] js/tools-data.js ({os.path.getsize(tools_data_js_path)//1024}KB)')

    # 移除旧的内联 __ALL_TOOLS__ / __REMAINING_TOOLS__ 脚本（避免重复）
    html = re.sub(r'<script>\s*window\.__ALL_TOOLS__\s*=\s*\[[\s\S]*?\];\s*\n?\s*window\.__REMAINING_TOOLS__\s*=\s*\[[\s\S]*?\];?\s*</script>', '', html)

    # 移除旧的 tools-data.js 引用（避免重复注入）
    html = re.sub(r'<script\s+src="/js/tools-data\.js"></script>\s*', '', html)

    # 在 </head> 前注入外部数据文件引用
    html = html.replace('</head>', '<script src="/js/tools-data.js"></script>\n</head>')
    
    # 移除所有已有的百度统计代码片段（无论占位符还是真实代码），避免重复叠加
    html = re.sub(r'<script>\s*var _hmt\s*=\s*_hmt\s*\|\|\s*\[\];\s*\(function\(\)\s*\{[\s\S]*?hm\.src\s*=\s*"[^"]*";[\s\S]*?\}\)\(\);?\s*</script>', '', html)
    html = re.sub(r'<!--\s*BAIDU_TONGJI_PLACEHOLDER\s*-->', '', html)
    
    # 注入 OG 标签（如果缺失 og:url）
    if 'og:url' not in html:
        html = html.replace('</head>', '<meta property="og:url" content="https://www.aitoolbox.hk/">\n</head>')

    # 注入真实百度统计代码
    html = html.replace('</head>', f'{BAIDU_TONGJI}\n</head>')

    # 注入 Bing Webmaster 验证标签
    BING_VERIFY = '    <meta name="msvalidate.01" content="D2B58E242903570E029A957ECDFF1E05" />'
    if 'msvalidate.01' not in html:
        html = html.replace('</head>', f'{BING_VERIFY}\n</head>')

    # 确保返回顶部按钮存在（兜底注入）
    if 'id="backToTop"' not in html:
        BACK_TO_TOP_HTML = '''
    <button id="backToTop" aria-label="返回顶部">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="18 15 12 9 6 15"></polyline>
        </svg>
    </button>'''
        html = html.replace('</body>', BACK_TO_TOP_HTML + '\n</body>')

    # 注入返回顶部内联兜底脚本（在 main.js 之前，按钮之后执行）
    # 注意：按钮可能在 main.js 引用之后，所以用 DOMContentLoaded 确保 DOM 就绪
    BACK_TO_TOP_FAILSAFE = '''<script>
// 返回顶部按钮 - 内联兜底版本（DOMContentLoaded 确保按钮已存在）
document.addEventListener("DOMContentLoaded",function(){
    var b=document.getElementById("backToTop");
    if(!b)return;
    var s=function(){
        if(window.scrollY>400){b.classList.add("visible")}
        else{b.classList.remove("visible")}
    };
    window.addEventListener("scroll",s,{passive:true});
    s();
    b.addEventListener("click",function(){window.scrollTo({top:0,behavior:"smooth"})});
});
</script>
'''
    # 先清理已存在的所有返回顶部相关内联脚本（防止重复注入）
    html = re.sub(r'<script>\s*// 返回顶部按钮[\s\S]*?</script>\s*', '', html)
    html = re.sub(r'<script>\s*\(function\(\)\{\s*var b=document\.getElementById\("backToTop"\)[\s\S]*?\}\)\(\);\s*</script>\s*', '', html)
    # 注入一次兜底脚本（在 main.js 之前）
    html = html.replace('<script src="/js/main.js"></script>', BACK_TO_TOP_FAILSAFE + '<script src="/js/main.js"></script>')

    return html

def generate_sitemap(tools, articles, categories, compares=None, alternatives=None, quizzes=None, rankings=None):
    """生成 sitemap.xml"""
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')

    urls = []
    # 首页
    urls.append(f'''    <url>
        <loc>https://www.aitoolbox.hk/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>''')

    # 注意：不在sitemap中加入文章分页URL（/articles/page/N/），避免浪费爬虫预算
    # 分页通过页面上的 rel=next/prev 让爬虫自然发现即可

    # 工具页
    for tool in tools:
        priority = '0.9' if tool.get('badge') else '0.8'
        urls.append(f'''    <url>
        <loc>https://www.aitoolbox.hk/tools/{tool['slug']}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>{priority}</priority>
    </url>''')

    # 文章页
    for article in articles:
        priority = '0.9' if '2026' in article.get('title', '') else '0.8'
        urls.append(f'''    <url>
        <loc>https://www.aitoolbox.hk/articles/{article['slug']}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>{priority}</priority>
    </url>''')
    
    # 分类页（categories 参数已经是经过 get_category_slug 处理的 slug 列表）
    for category_name in categories:
        urls.append(f'''    <url>
        <loc>https://www.aitoolbox.hk/category/{category_name}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>''')

    # 对比页 (Phase 2)
    if compares:
        for cp in compares:
            cslug = cp.get('slug', '')
            if cslug:
                prio = '0.9' if cp.get('priority') == 'high' else '0.8'
                urls.append(f'''    <url>
        <loc>https://www.aitoolbox.hk/compare/{cslug}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>{prio}</priority>
    </url>''')

    # 替代方案页 (Phase 3)
    if alternatives:
        for alt in alternatives:
            aslug = alt.get('slug', '')
            if aslug:
                urls.append(f'''    <url>
        <loc>https://www.aitoolbox.hk/alternatives/{aslug}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.8</priority>
    </url>''')

    # Quiz 选择器页 (Phase 4)
    if quizzes:
        for qd in quizzes:
            qslug = qd.get('slug', '')
            if qslug:
                is_main = (qd.get('target_url') == '/quiz/') or qslug == 'ai-tool-finder-2026'
                loc = f'/' if is_main else f'/{qslug}/'
                urls.append(f'''    <url>
        <loc>https://www.aitoolbox.hk/quiz{loc}</loc>
        <lastmod>{today}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.9</priority>
    </url>''')

    # Ranking 排名页 (Phase 5)
    if rankings:
        for rd in rankings:
            rslug = rd.get('slug', '')
            if rslug:
                is_overall = rslug == '2026-ai-tools-overall-ranking'
                loc = f'/' if is_overall else f'/{rslug}/'
                urls.append(f'''    <url>
        <loc>https://www.aitoolbox.hk/ranking{loc}</loc>
        <lastmod>{today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>''')

    sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>'''

    return sitemap

def push_to_indexnow(urls):
    """通过 IndexNow 协议向 Bing/Yandex 等搜索引擎推送新链接"""
    import urllib.request
    import urllib.error
    import json as _json

    KEY = "d2b58e242903570e029a957ecdff1e05"  # 与 Bing 验证码同一个值（小写）
    api_url = "https://api.indexnow.org/indexnow"

    payload = _json.dumps({
        "host": "www.aitoolbox.hk",
        "key": KEY,
        "keyLocation": f"https://www.aitoolbox.hk/{KEY}.txt",
        "urlList": urls[:10000]  # IndexNow 单次上限 10000 条
    }).encode("utf-8")

    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[IndexNow] Success: HTTP {resp.status}, pushed {len(urls)} URLs")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[IndexNow] HTTP {e.code}: {body}")
        return False
    except Exception as e:
        print(f"[IndexNow] Failed: {e}")
        return False


def push_to_baidu(urls):
    """主动向百度搜索引擎推送链接"""
    api_url = "http://data.zz.baidu.com/urls?site=https://www.aitoolbox.hk&token=WkOz42Q1xowpLZcB"
    
    try:
        import urllib.request
        import urllib.error
        data = '\n'.join(urls).encode('utf-8')
        req = urllib.request.Request(api_url, data=data, headers={'Content-Type': 'text/plain'})
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                result = response.read().decode('utf-8')
                print(f"[Baidu Push] Success: {result}")
                return True
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            print(f"[Baidu Push] HTTP {e.code}: {body}")
            return False
    except Exception as e:
        print(f"[Baidu Push] Failed: {e}")
        return False

def main():
    # 加载数据
    with open(os.path.join(DATA_DIR, 'tools.json'), 'r', encoding='utf-8') as f:
        all_tools = json.load(f)
    with open(os.path.join(DATA_DIR, 'articles.json'), 'r', encoding='utf-8') as f:
        articles = json.load(f)

    # 过滤出已发布的工具
    published_tools = [tool for tool in all_tools if tool.get('published', False)]
    print(f"检测到 {len(all_tools)} 个工具，其中 {len(published_tools)} 个已发布。")

    # 按分类分组工具
    tools_by_category = {}
    for tool in published_tools:
        category = tool.get('category')
        if category:
            if category not in tools_by_category:
                tools_by_category[category] = []
            tools_by_category[category].append(tool)
    
    # 生成分类页
    for category_name, tools_in_category in tools_by_category.items():
        category_slug = get_category_slug(category_name)
        dir_path = os.path.join(BASE_DIR, 'category', category_slug)
        os.makedirs(dir_path, exist_ok=True)
        html = build_category_page(category_name, tools_in_category)
        with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'[OK] category/{category_slug}/index.html')

    # 生成工具页
    for tool in published_tools:
        slug = tool['slug']
        dir_path = os.path.join(BASE_DIR, 'tools', slug)
        os.makedirs(dir_path, exist_ok=True)
        html = build_tool_page(tool, published_tools, articles) # 传递已发布工具列表 + 全部文章
        with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'[OK] tools/{slug}/index.html')

    # 生成文章页 (文章不受published字段控制，全部生成)
    for article in articles:
        slug = article['slug']
        dir_path = os.path.join(BASE_DIR, 'articles', slug)
        os.makedirs(dir_path, exist_ok=True)
        html = build_article_page(article, articles, published_tools)
        with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'[OK] articles/{slug}/index.html')

    # 生成文章分页列表页
    total_pages = build_article_list_pages(articles)

    # ═══════════════════════════════════════════════════════
    # Phase 2+3: 生成对比页和替代方案页（程序化SEO）
    # ═══════════════════════════════════════════════════════
    compare_data = load_compare_data()
    all_compares = compare_data.get('compares', [])
    all_alternatives = compare_data.get('alternatives', [])

    compare_count = 0
    alt_count = 0

    if all_compares:
        print(f'\n[Phase2] Generating compare pages ({len(all_compares)})...')
        for cp in all_compares:
            cslug = cp.get('slug', 'unknown')
            dir_path = os.path.join(BASE_DIR, 'compare', cslug)
            os.makedirs(dir_path, exist_ok=True)
            try:
                html = build_compare_page(cp, published_tools, articles)
                with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f'  [OK] compare/{cslug}/index.html')
                compare_count += 1
            except Exception as e:
                print(f'  [FAIL] compare/{cslug}/: {e}')

    if all_alternatives:
        print(f'\n[Phase3] Generating alternatives pages ({len(all_alternatives)})...')
        for alt in all_alternatives:
            aslug = alt.get('slug', 'unknown')
            dir_path = os.path.join(BASE_DIR, 'alternatives', aslug)
            os.makedirs(dir_path, exist_ok=True)
            try:
                html = build_alternatives_page(alt, published_tools, articles)
                with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f'  [OK] alternatives/{aslug}/index.html')
                alt_count += 1
            except Exception as e:
                print(f'  [FAIL] alternatives/{aslug}/: {e}')

    # ═══════════════════════════════════════════════════════
    # Phase 4: Quiz / 工具选择器页面（程序化SEO）
    # ═══════════════════════════════════════════════════════
    quiz_data = load_quiz_data()
    all_quizzes = quiz_data.get('quizzes', [])
    quiz_count = 0

    if all_quizzes:
        print(f'\n[Phase4] Generating quiz pages ({len(all_quizzes)})...')
        for qd in all_quizzes:
            qslug = qd.get('slug', 'unknown')
            # 总入口放在 /quiz/index.html，其他在 /quiz/{slug}/index.html
            is_main = qd.get('target_url') == '/quiz/' or qslug == 'ai-tool-finder-2026'
            if is_main:
                dir_path = os.path.join(BASE_DIR, 'quiz')
            else:
                dir_path = os.path.join(BASE_DIR, 'quiz', qslug)

            os.makedirs(dir_path, exist_ok=True)
            try:
                html = build_quiz_page(qd, published_tools, articles)
                with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
                    f.write(html)
                loc = f'quiz/' if is_main else f'quiz/{qslug}/'
                print(f'  [OK] {loc}index.html')
                quiz_count += 1
            except Exception as e:
                loc = f'quiz/' if is_main else f'quiz/{qslug}/'
                print(f'  [FAIL] {loc}: {e}')

    # ═══════════════════════════════════════════════════════
    # Phase 5: Ranking / 排名页面（动态排名系统）
    # ═══════════════════════════════════════════════════════
    ranking_data = load_ranking_data()
    all_rankings = ranking_data.get('rankings', [])
    ranking_count = 0

    if all_rankings:
        print(f'\n[Phase5] Generating ranking pages ({len(all_rankings)})...')
        for rd in all_rankings:
            rslug = rd.get('slug', 'unknown')
            is_overall = rslug == '2026-ai-tools-overall-ranking'
            if is_overall:
                dir_path = os.path.join(BASE_DIR, 'ranking')
            else:
                dir_path = os.path.join(BASE_DIR, 'ranking', rslug)

            os.makedirs(dir_path, exist_ok=True)
            try:
                html = build_ranking_page(rd, published_tools, articles)
                with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
                    f.write(html)
                loc = f'ranking/' if is_overall else f'ranking/{rslug}/'
                print(f'  [OK] {loc}index.html')
                ranking_count += 1
            except Exception as e:
                loc = f'ranking/' if is_overall else f'ranking/{rslug}/'
                print(f'  [FAIL] {loc}: {e}')

    # 生成 sitemap.xml
    # 传递所有已发布的分类名称列表 + 对比/替代/Quiz/Ranking数据
    sitemap = generate_sitemap(published_tools, articles, [get_category_slug(cat) for cat in tools_by_category.keys()],
                                all_compares, all_alternatives,
                                all_quizzes if 'all_quizzes' in dir() else [],
                                all_rankings if 'all_rankings' in dir() else [])
    with open(os.path.join(BASE_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(sitemap)
    print(f'[OK] sitemap.xml ({len(published_tools)} tools + {len(articles)} articles + {len(tools_by_category)} categories + {total_pages} article pages + {compare_count} compares + {alt_count} alternatives + {quiz_count} quizzes + {ranking_count} rankings)')

    # 生成静态首页
    index_html = build_index_page(published_tools, articles) # 使用已发布的工具
    with open(os.path.join(BASE_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
    print(f'[OK] index.html (Static Pre-rendered)')

    # 收集需要推送的链接（仅推送新增页面，避免浪费配额）
    push_cache_file = os.path.join(BASE_DIR, '.baidu_pushed.json')
    pushed_urls = set()
    if os.path.exists(push_cache_file):
        with open(push_cache_file, 'r', encoding='utf-8') as f:
            pushed_urls = set(json.load(f))
    
    all_urls = ["https://www.aitoolbox.hk/"]
    for tool in published_tools: # 只推送已发布的工具
        all_urls.append(f"https://www.aitoolbox.hk/tools/{tool['slug']}/")
    for article in articles:
        all_urls.append(f"https://www.aitoolbox.hk/articles/{article['slug']}/")
    for category_name in tools_by_category.keys(): # 添加分类页面的URL
        category_slug = get_category_slug(category_name)
        all_urls.append(f"https://www.aitoolbox.hk/category/{category_slug}/")
    for cp in (all_compares or []):  # 对比页
        cslug = cp.get('slug', '')
        if cslug:
            all_urls.append(f"https://www.aitoolbox.hk/compare/{cslug}/")
    for alt in (all_alternatives or []):  # 替代方案页
        aslug = alt.get('slug', '')
        if aslug:
            all_urls.append(f"https://www.aitoolbox.hk/alternatives/{aslug}/")
    for qd in (all_quizzes or []):  # Quiz选择器页
        qslug = qd.get('slug', '')
        if qslug:
            is_main = (qd.get('target_url') == '/quiz/') or qslug == 'ai-tool-finder-2026'
            all_urls.append(f"https://www.aitoolbox.hk/quiz{'' if is_main else '/' + qslug + '/'}")
    for rd in (all_rankings or []):  # 排名页
        rslug = rd.get('slug', '')
        if rslug:
            is_overall = rslug == '2026-ai-tools-overall-ranking'
            all_urls.append(f"https://www.aitoolbox.hk/ranking{'' if is_overall else '/' + rslug + '/'}")
    
    new_urls = [u for u in all_urls if u not in pushed_urls]
    
    if new_urls:
        print(f"\nPushing {len(new_urls)} new URLs to Baidu...")
        push_result = push_to_baidu(new_urls)
        # 只在推送成功时才更新缓存
        if push_result:
            pushed_urls.update(new_urls)
            with open(push_cache_file, 'w', encoding='utf-8') as f:
                json.dump(list(pushed_urls), f)
    else:
        print(f"\nNo new URLs to push. ({len(all_urls)} total, all already pushed)")

    # IndexNow 推送（Bing / Yandex / Seznam 同步）
    indexnow_cache_file = os.path.join(BASE_DIR, '.indexnow_pushed.json')
    indexnow_pushed = set()
    if os.path.exists(indexnow_cache_file):
        with open(indexnow_cache_file, 'r', encoding='utf-8') as f:
            indexnow_pushed = set(json.load(f))

    new_indexnow_urls = [u for u in all_urls if u not in indexnow_pushed]
    if new_indexnow_urls:
        print(f"\nPushing {len(new_indexnow_urls)} new URLs via IndexNow (Bing/Yandex)...")
        if push_to_indexnow(new_indexnow_urls):
            indexnow_pushed.update(new_indexnow_urls)
            with open(indexnow_cache_file, 'w', encoding='utf-8') as f:
                json.dump(list(indexnow_pushed), f)
    else:
        print(f"\nIndexNow: No new URLs to push. ({len(all_urls)} total, all already pushed)")
    
    print(f'\nDone! {len(published_tools)} tools + {len(articles)} articles + {quiz_count} quizzes + {ranking_count} rankings')

if __name__ == '__main__':
    main()
