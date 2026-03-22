#!/usr/bin/env python3
"""SSG构建脚本：将JSON数据生成为静态HTML文件，SEO友好"""
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

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
    # 列表
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', html, flags=re.MULTILINE)
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
    <link rel="stylesheet" href="/css/style.css">
    <script type="application/ld+json">{structured_data}</script>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><h1>🛠️ AI工具宝箱 <span>每日更新 · 已收录 500+ 工具</span></h1></a>
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

        {pros_cons_html}

        {related_html}
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

    structured_data = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article['title'],
        "description": article.get('description', ''),
        "datePublished": article.get('dateFull', ''),
        "author": {"@type": "Organization", "name": "AI工具宝箱"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱"}
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
    <link rel="stylesheet" href="/css/style.css">
    <script type="application/ld+json">{structured_data}</script>
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

def main():
    # 加载数据
    with open(os.path.join(DATA_DIR, 'tools.json'), 'r', encoding='utf-8') as f:
        tools = json.load(f)
    with open(os.path.join(DATA_DIR, 'articles.json'), 'r', encoding='utf-8') as f:
        articles = json.load(f)

    # 生成工具页
    for tool in tools:
        slug = tool['slug']
        dir_path = os.path.join(BASE_DIR, 'tools', slug)
        os.makedirs(dir_path, exist_ok=True)
        html = build_tool_page(tool, tools)
        with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'[OK] tools/{slug}/index.html')

    # 生成文章页
    for article in articles:
        slug = article['slug']
        dir_path = os.path.join(BASE_DIR, 'articles', slug)
        os.makedirs(dir_path, exist_ok=True)
        html = build_article_page(article, articles)
        with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'[OK] articles/{slug}/index.html')

    print(f'\nDone! {len(tools)} tools + {len(articles)} articles')

if __name__ == '__main__':
    main()
