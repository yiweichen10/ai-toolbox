#!/usr/bin/env python3
"""SSG构建脚本：将JSON数据生成为静态HTML文件，SEO友好"""
import json
import os
import re

from pypinyin import pinyin, Style

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

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

def build_tool_page(tool, all_tools):
    """生成单个工具详情页的完整HTML"""
    slug = tool['slug']
    
    # 相关工具
    related_html = ''
    if tool.get('related'):
        related_cards = ''
        for r_slug in tool['related']:
            r = next((t for t in all_tools if t['slug'] == r_slug), None)
            if r:
                related_cards += f'''<a href="/tools/{r['slug']}/index.html" class="related-card">
                    <div style="font-size:24px;margin-bottom:8px;">{r['emoji']}</div>
                    <div style="font-weight:600;">{r['name']}</div>
                    <div style="font-size:13px;color:#666;">{r['category']}</div>
                </a>\n'''
        related_html = f'''<div class="related-tools" id="relatedSection">
            <h3>🔗 相关工具推荐</h3>
            <div class="related-grid">{related_cards}</div>
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
    structured_data = json.dumps({
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": tool['name'],
        "applicationCategory": "UtilitiesApplication",
        "operatingSystem": tool.get('platform', 'Web'),
        "description": tool['description'],
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
    }, ensure_ascii=False, indent=2)

    # OG Image
    og_image = f'https://www.aitoolbox.hk/images/og/{slug}-og.png'

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
    <title>{escape_html(tool['name'])}评测 - AI工具宝箱</title>
    <meta name="description" content="{escape_html(tool['name'])}全面评测：{escape_html(tool['description'])}">
    <meta name="keywords" content="{escape_html(tool['name'])}评测,{escape_html(tool['name'])}使用教程,{escape_html(tool['category'])}工具">
    <link rel="canonical" href="https://www.aitoolbox.hk/tools/{slug}/index.html">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(tool['name'])}评测 - AI工具宝箱">
    <meta property="og:description" content="{escape_html(tool['description'])}">
    <meta property="og:url" content="https://www.aitoolbox.hk/tools/{slug}/index.html">
    <meta property="og:image" content="{og_image}">
    <link rel="stylesheet" href="/css/style.css">
    <script type="application/ld+json">{structured_data}</script>
{BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><h1>🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></h1></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/">{escape_html(tool['category'])}</a> &gt; <span>{escape_html(tool['name'])}</span>
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

        {related_html}
    </main>

    <footer class="footer">
        <p>© 2026 AI工具宝箱 · 每日精选优质AI工具</p>
    </footer>
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
    <link rel="canonical" href="https://www.aitoolbox.hk/category/{category_slug}/index.html">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{escape_html(category_name)} - AI工具宝箱">
    <meta property="og:description" content="AI工具宝箱收录{escape_html(category_name)}分类下最新最全的AI工具。">
    <meta property="og:url" content="https://www.aitoolbox.hk/category/{category_slug}/index.html">
    <meta property="og:image" content="https://www.aitoolbox.hk/images/og/category-{category_slug}-og.png">
    <link rel="stylesheet" href="/css/style.css">
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
</body>
</html>'''
    return html

def build_article_page(article, all_articles):
    """生成单个文章页的完整HTML"""
    slug = article['slug']
    
    # 相关文章
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

    # OG Image
    og_image = f'https://www.aitoolbox.hk/images/og/{slug}-og.png'

    # 信息图（文章内嵌）
    infographic_path = os.path.join(BASE_DIR, 'images', 'infographics', f'{slug}-infographic.png')
    has_infographic = os.path.exists(infographic_path)
    infographic_html = ''
    if has_infographic:
        infographic_html = f'''<figure class="tool-infographic">
            <img src="/images/infographics/{slug}-infographic.png" alt="{escape_html(article['title'])} - 数据对比信息图" width="1200" height="630" loading="lazy">
            <figcaption>{escape_html(article['title'])} · 核心数据一览</figcaption>
        </figure>'''

    structured_data = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article['title'],
        "description": article.get('description', ''),
        "datePublished": article.get('dateFull', ''),
        "author": {"@type": "Organization", "name": "AI工具宝箱"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱"},
        "image": og_image
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
    <link rel="canonical" href="https://www.aitoolbox.hk/articles/{slug}/index.html">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(article['title'])} - AI工具宝箱">
    <meta property="og:description" content="{escape_html(article.get('description', ''))}">
    <meta property="og:image" content="{og_image}">
    <meta property="og:url" content="https://www.aitoolbox.hk/articles/{slug}/index.html">
    <meta property="og:site_name" content="AI工具宝箱">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(article['title'])} - AI工具宝箱">
    <meta name="twitter:description" content="{escape_html(article.get('description', ''))}">
    <meta name="twitter:image" content="{og_image}">
    <link rel="stylesheet" href="/css/style.css">
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
    </main>

    <footer class="footer">
        <p>© 2026 AI工具宝箱 · 每日精选优质AI工具</p>
    </footer>
</body>
</html>'''
    return html

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

    tools_html = ''
    for i, t in enumerate(tools):
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

    # 替换内容（replace_between_tags 通过 div 嵌套深度精确匹配，不会破坏 HTML 结构）
    html = replace_between_tags(html, '<div class="tools-grid" id="toolsGrid">', tools_html)
    html = re.sub(r'(<ul id="articleList">)[\s\S]*?(</ul>)', lambda m: m.group(1) + '\n' + articles_html + '                    </ul>', html)
    html = re.sub(r'(<div class="sidebar-card">\s*<h4>&#x1F525; 热门分类</h4>\s*<ul>)[\s\S]*?(</ul>\s*</div>)', lambda m: m.group(1) + '\n' + categories_html + '                    </ul>\n                </div>', html)
    html = re.sub(r'(<div class="footer-links">)[\s\S]*?(</div>)', lambda m: m.group(1) + '\n' + footer_links_html + '\n        </div>', html)
    
    # 移除所有已有的百度统计代码片段（无论占位符还是真实代码），避免重复叠加
    html = re.sub(r'<script>\s*var _hmt\s*=\s*_hmt\s*\|\|\s*\[\];\s*\(function\(\)\s*\{[\s\S]*?hm\.src\s*=\s*"[^"]*";[\s\S]*?\}\)\(\);?\s*</script>', '', html)
    html = re.sub(r'<!--\s*BAIDU_TONGJI_PLACEHOLDER\s*-->', '', html)
    
    # 注入 OG 标签（如果缺失 og:url）
    if 'og:url' not in html:
        html = html.replace('</head>', '<meta property="og:url" content="https://www.aitoolbox.hk/">\n</head>')

    # 注入真实百度统计代码
    html = html.replace('</head>', f'{BAIDU_TONGJI}\n</head>')
        
    return html

def generate_sitemap(tools, articles, categories):
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

    # 工具页
    for tool in tools:
        priority = '0.9' if tool.get('badge') else '0.8'
        urls.append(f'''    <url>
        <loc>https://www.aitoolbox.hk/tools/{tool['slug']}/index.html</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>{priority}</priority>
    </url>''')

    # 文章页
    for article in articles:
        priority = '0.9' if '2026' in article.get('title', '') else '0.8'
        urls.append(f'''    <url>
        <loc>https://www.aitoolbox.hk/articles/{article['slug']}/index.html</loc>
        <lastmod>{today}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>{priority}</priority>
    </url>''')
    
    # 分类页
    for category_name in categories:
        category_slug = category_name.replace(' ', '-').lower()
        urls.append(f'''    <url>
        <loc>https://www.aitoolbox.hk/category/{category_slug}/index.html</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>''')

    sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>'''

    return sitemap

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
        html = build_tool_page(tool, published_tools) # 传递已发布的工具列表
        with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'[OK] tools/{slug}/index.html')

    # 生成文章页 (文章不受published字段控制，全部生成)
    for article in articles:
        slug = article['slug']
        dir_path = os.path.join(BASE_DIR, 'articles', slug)
        os.makedirs(dir_path, exist_ok=True)
        html = build_article_page(article, articles)
        with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'[OK] articles/{slug}/index.html')

    # 生成 sitemap.xml
    # 传递所有已发布的分类名称列表
    sitemap = generate_sitemap(published_tools, articles, [get_category_slug(cat) for cat in tools_by_category.keys()])
    with open(os.path.join(BASE_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(sitemap)
    print(f'[OK] sitemap.xml ({len(published_tools)} tools + {len(articles)} articles + {len(tools_by_category)} categories)')

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
        all_urls.append(f"https://www.aitoolbox.hk/tools/{tool['slug']}/index.html")
    for article in articles:
        all_urls.append(f"https://www.aitoolbox.hk/articles/{article['slug']}/index.html")
    for category_name in tools_by_category.keys(): # 添加分类页面的URL
        category_slug = get_category_slug(category_name)
        all_urls.append(f"https://www.aitoolbox.hk/category/{category_slug}/index.html")
    
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
    
    print(f'\nDone! {len(published_tools)} tools + {len(articles)} articles')

if __name__ == '__main__':
    main()
