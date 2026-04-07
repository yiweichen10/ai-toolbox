
import os
import re

file_path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py'
content = open(file_path, 'r', encoding='utf-8').read()

# 1. Define the code to be inserted
UI_I18N = """
# UI国际化字典 (SEO Face-lift)
UI_I18N = {
    'zh-CN': {
        'nav_ranking': '📊 工具排行',
        'nav_quiz': '🎯 AI工具选择器',
        'nav_live': '📈 实时面板',
        'nav_compare': '⚖️ 对比评测',
        'nav_alternatives': '🔄 替代方案',
        'nav_categories': '📂 全部分类',
        'header_title': 'AI工具宝箱',
        'header_subtitle': '每日更新 · 收录工具 持续更新',
        'footer_text': 'AI工具宝箱 · 每日精选优质AI工具',
        'breadcrumb_home': '首页',
        'breadcrumb_articles': '文章列表',
        'breadcrumb_compare': '工具对比',
        'breadcrumb_alternative': '替代方案',
        'breadcrumb_quiz': '工具选择器',
        'breadcrumb_ranking': '工具排行榜',
        'breadcrumb_live': '实时看板',
        'related_tools': '🔧 相关工具',
        'related_articles': '📖 相关文章',
        'back_to_top': '返回顶部',
        'last_updated': '最后更新',
        'tool_website': '官网',
        'tool_price': '价格',
        'tool_category': '分类',
        'tool_platform': '平台',
        'tool_use_now': '立即使用',
        'tool_features': '核心功能',
        'tool_pros_cons': '优缺点分析',
        'tool_pros': '✅ 优点',
        'tool_cons': '❌ 缺点',
        'view_details': '详情',
        'more_compare': '🔗 更多相关对比',
        'more_alternatives': '🔗 更多替代方案',
    },
    'en': {
        'nav_ranking': '📊 Ranking',
        'nav_quiz': '🎯 AI Selector',
        'nav_live': '📈 Live Board',
        'nav_compare': '⚖️ Comparison',
        'nav_alternatives': '🔄 Alternatives',
        'nav_categories': '📂 Categories',
        'header_title': 'AI Tool Box',
        'header_subtitle': 'Daily Updates · Hand-picked AI Tools',
        'footer_text': 'AI Tool Box · Quality AI Tools Daily',
        'breadcrumb_home': 'Home',
        'breadcrumb_articles': 'Articles',
        'breadcrumb_compare': 'Comparison',
        'breadcrumb_alternative': 'Alternatives',
        'breadcrumb_quiz': 'AI Selector',
        'breadcrumb_ranking': 'Ranking',
        'breadcrumb_live': 'Live Board',
        'related_tools': '🔧 Related Tools',
        'related_articles': '📖 Related Articles',
        'back_to_top': 'Back to Top',
        'last_updated': 'Last Updated',
        'tool_website': 'Website',
        'tool_price': 'Pricing',
        'tool_category': 'Category',
        'tool_platform': 'Platform',
        'tool_use_now': 'Use Now',
        'tool_features': 'Key Features',
        'tool_pros_cons': 'Pros & Cons',
        'tool_pros': '✅ Pros',
        'tool_cons': '❌ Cons',
        'view_details': 'Details',
        'more_compare': '🔗 More Comparisons',
        'more_alternatives': '🔗 More Alternatives',
    }
}

def get_ui_text(key, lang='zh-CN'):
    \"\"\"获取指定语言的UI文本\"\"\"
    if lang not in UI_I18N:
        lang = 'zh-CN'
    return UI_I18N[lang].get(key, UI_I18N['zh-CN'].get(key, ''))

def get_global_nav(lang='zh-CN'):
    \"\"\"获取指定语言的全局导航栏HTML\"\"\"
    t = lambda k: get_ui_text(k, lang)
    return f'''    <nav class="global-nav" aria-label="Global Navigation">
        <div class="global-nav-inner">
            <a href="/ranking/" class="gn-item">{t('nav_ranking')}</a>
            <a href="/quiz/" class="gn-item">{t('nav_quiz')}</a>
            <a href="/live/" class="gn-item">{t('nav_live')}</a>
            <a href="/compare/" class="gn-item">{t('nav_compare')}</a>
            <a href="/alternatives/" class="gn-item">{t('nav_alternatives')}</a>
            <a href="/category/" class="gn-item">{t('nav_categories')}</a>
        </div>
    </nav>'''

GLOBAL_NAV = get_global_nav('zh-CN')

def escape_html(text):
    \"\"\"简单HTML转义\"\"\"
    if not text: return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")

def get_category_slug(category_name):
    \"\"\"获取分类的slug，优先使用映射表，否则拼音化\"\"\"
    if category_name in CATEGORY_SLUG_MAP:
        return CATEGORY_SLUG_MAP[category_name]
    
    # 简单的拼音化处理 (如果 pypinyin 可用)
    if pinyin:
        py_list = pinyin(category_name, style=Style.NORMAL)
        slug = '-'.join([item[0] for item in py_list]).lower()
        return re.sub(r'[^a-z0-9\-]', '', slug)
    return category_name.lower()

def markdown_to_html(md):
    \"\"\"将Markdown转换为简单HTML (增强版)\"\"\"
    if not md:
        return ''
    # 统一换行符
    html = md.replace('\\r\\n', '\\n')
    
    # 确保表格和标题前后有换行符，方便正则匹配
    html = re.sub(r'([^\\n])\\n\\|', r'\\1\\n\\n|', html)
    
    # 代码块
    html = re.sub(r'```(\\w*)\\n([\\s\\S]*?)```', lambda m: '<pre><code>' + m.group(2).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</code></pre>', html)
    
    # 表格 (改进正则，支持无前导换行的情况)
    def table_replace(m):
        header = m.group(1)
        sep = m.group(2)
        body = m.group(3)
        headers = [c.strip() for c in header.split('|') if c.strip()]
        rows = body.strip().split('\\n')
        table = '<div class="table-container"><table><thead><tr>'
        for h in headers:
            table += f'<th>{h}</th>'
        table += '</tr></thead><tbody>'
        for row in rows:
            cells = [c.strip() for c in row.split('|') if c.strip()]
            if not cells: continue
            table += '<tr>'
            for c in cells:
                table += f'<td>{c}</td>'
            table += '</tr>'
        table += '</tbody></table></div>'
        return table
    html = re.sub(r'(?:^|\\n)(\\|.+\\|)\\n(\\|[-:| ]+\\|)\\n((?:\\|.+\\|(?:$|\\n))+)', table_replace, html)
    
    # 标题 (增加 # H1 支持)
    html = re.sub(r'^### (.+)$', r'<h3>\\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\\1</h1>', html, flags=re.MULTILINE)
    
    # 引用
    html = re.sub(r'^> (.+)$', r'<blockquote>\\1</blockquote>', html, flags=re.MULTILINE)
    
    # 加粗/斜体/行内代码
    html = re.sub(r'\\*\\*(.+?)\\*\\*', r'<strong>\\1</strong>', html)
    html = re.sub(r'\\*(.+?)\\*', r'<em>\\1</em>', html)
    html = re.sub(r'`([^`]+)`', r'<code>\\1</code>', html)
    
    # 链接
    html = re.sub(r'\\[([^]]+)\\]\\((/[^)]+)\\)', r'<a href="\\2">\\1</a>', html)
    html = re.sub(r'\\[([^]]+)\\]\\((https?://[^)]+)\\)', r'<a href="\\2" target="_blank" rel="noopener">\\1</a>', html)
    
    # 列表
    html = re.sub(r'^- (.+)$', r'<li>\\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^(\\d+)\\. (.+)$', r'<li>\\2</li>', html, flags=re.MULTILINE)
    html = re.sub(r'((?:<li>.*?</li>\\n?)+)', r'<ul>\\1</ul>', html)
    
    # 分隔线
    html = html.replace('\\n---\\n', '\\n<hr>\\n')
    
    # 段落
    lines = html.split('\\n')
    result = []
    in_p = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_p:
                result.append('</p>')
                in_p = False
            continue
            
        is_tag = (stripped.startswith('<h') or stripped.startswith('<ul') or 
                  stripped.startswith('</ul') or stripped.startswith('<li') or 
                  stripped.startswith('<table') or stripped.startswith('</table') or 
                  stripped.startswith('<div') or stripped.startswith('</div') or 
                  stripped.startswith('<pre') or stripped.startswith('</pre') or 
                  stripped.startswith('<blockquote') or stripped.startswith('</blockquote') or 
                  stripped.startswith('<hr'))
        
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
                result.append('<br>' + line)
    if in_p:
        result.append('</p>')
    return '\\n'.join(result)

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

def build_tool_page(tool, all_tools, all_articles=None):
    \"\"\"生成单个工具详情页的完整HTML\"\"\"
    lang = tool.get('lang', 'zh-CN')
    t = lambda k: get_ui_text(k, lang)

    slug = tool['slug']
    name = tool['name']
    emoji = tool.get('emoji', '🛠️')
    category = tool.get('category', 'AI工具')
    price = tool.get('price', '免费')
    platform = tool.get('platform', 'Web')
    rating = tool.get('rating', '5.0')
    website = tool.get('website', '#')
    description = tool.get('description', '')
    features = tool.get('features', [])
    pros = tool.get('pros', [])
    cons = tool.get('cons', [])
    faq = tool.get('faq', [])
    content_md = tool.get('content', '')

    title = f"{emoji} {name} - {category} - {t('header_title')}"
    meta_desc = f"{name} 是一个{category}类AI工具。价格：{price}。支持平台：{platform}。{description[:100]}"
    keywords = [name, category, "AI工具", "人工智能"]

    # OG Image
    og_image = ensure_og_image(slug, data_obj=tool, is_article=False)

    # FAQ Schema
    faq_schema_items = []
    faq_html = ""
    for item in faq:
        q = item.get('question', '')
        a = item.get('answer', '')
        if q and a:
            faq_schema_items.append({
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a}
            })
            faq_html += f'<div class="faq-item"><details><summary>{escape_html(q)}</summary><div class="faq-answer">{markdown_to_html(a)}</div></details></div>'
    
    faq_section = ""
    if faq_html:
        faq_section = f'''<div class="faq-section"><h3>❓ {t("tool_features")}</h3>{faq_html}</div>'''

    faq_schema = ""
    if faq_schema_items:
        faq_sd = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_schema_items}
        faq_schema = f'''<script type="application/ld+json">{json.dumps(faq_sd, ensure_ascii=False)}</script>'''

    # Breadcrumb
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": t('breadcrumb_home'), "item": "https://www.aitoolbox.hk/"},
            {"@type": "ListItem", "position": 2, "name": category, "item": f"https://www.aitoolbox.hk/category/{get_category_slug(category)}/"},
            {"@type": "ListItem", "position": 3, "name": name, "item": f"https://www.aitoolbox.hk/tools/{slug}/"}
        ]
    }
    breadcrumb_json = json.dumps(breadcrumb, ensure_ascii=False, indent=2)

    # Related Tools
    related_tools_html = ""
    if all_tools:
        related = [rt for rt in all_tools if rt.get('category') == category and rt.get('slug') != slug][:4]
        for rt in related:
            rslug = rt['slug']
            remoji = rt.get('emoji','🛠️')
            rname = rt['name']
            rprice = rt.get('price','')
            related_tools_html += f'''
            <a href="/tools/{rslug}/" class="tool-card" style="text-decoration:none;color:inherit;border:1px solid #eee;padding:12px;border-radius:10px;display:block;">
                <div style="font-size:32px;margin-bottom:8px;">{remoji}</div>
                <div style="font-weight:700;">{rname}</div>
                <div style="font-size:12px;color:#666;">{rprice}</div>
            </a>'''
    
    if related_tools_html:
        related_tools_html = f'''<div class="related-section"><h3>{t("related_tools")}</h3><div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(160px, 1fr));gap:12px;">{related_tools_html}</div></div>'''

    # Content HTML
    article_content_html = markdown_to_html(content_md)

    html = f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)}</title>
    <meta name="description" content="{escape_html(meta_desc)}">
    <meta name="keywords" content="{escape_html(', '.join(keywords))}">
    <link rel="canonical" href="https://www.aitoolbox.hk/tools/{slug}/">
    <meta property="og:title" content="{escape_html(name)}">
    <meta property="og:image" content="{og_image}">
    <link rel="stylesheet" href="/css/style.css">
    <script type="application/ld+json">{breadcrumb_json}</script>
    {faq_schema}
    {BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><h1>🛠️ {t('header_title')} <span>{t('header_subtitle')}</span></h1></a>
        </div>
    </header>
    <nav class="breadcrumb">
        <a href="/">{t('breadcrumb_home')}</a> &gt; <a href="/category/{get_category_slug(category)}/">{category}</a> &gt; <span>{name}</span>
    </nav>
    <main class="tool-container" style="max-width:900px;margin:0 auto;padding:20px;">
        <div class="tool-header" style="display:flex;gap:24px;margin-bottom:32px;align-items:flex-start;flex-wrap:wrap;">
            <div class="tool-icon" style="font-size:80px;background:#f8f9fa;padding:20px;border-radius:20px;">{emoji}</div>
            <div class="tool-info" style="flex:1;min-width:300px;">
                <h1 style="margin:0 0 12px;font-size:32px;">{name}</h1>
                <p style="font-size:18px;color:#555;line-height:1.6;margin-bottom:20px;">{description}</p>
                <div class="tool-meta" style="display:flex;gap:20px;margin-bottom:24px;font-size:14px;color:#666;flex-wrap:wrap;">
                    <span><strong>{t('tool_category')}</strong>: {category}</span>
                    <span><strong>{t('tool_price')}</strong>: {price}</span>
                    <span><strong>{t('tool_platform')}</strong>: {platform}</span>
                </div>
                <a href="{website}" class="btn-primary" target="_blank" rel="nofollow" style="display:inline-block;background:#4285F4;color:#fff;padding:12px 32px;border-radius:30px;text-decoration:none;font-weight:700;">{t('tool_use_now')} →</a>
            </div>
        </div>
        <div class="tool-body">
            <div class="features-box" style="margin-bottom:32px;">
                <h3>{t('tool_features')}</h3>
                <ul style="column-count:2;column-gap:40px;">{"".join([f"<li>{f}</li>" for f in features])}</ul>
            </div>
            <div class="pros-cons" style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:32px;">
                <div class="pros" style="background:#f6ffed;border:1px solid #b7eb8f;padding:20px;border-radius:12px;">
                    <h4 style="margin-top:0;color:#389e0d;">{t('tool_pros')}</h4>
                    <ul style="padding-left:20px;">{"".join([f"<li>{p}</li>" for p in pros])}</ul>
                </div>
                <div class="cons" style="background:#fff1f0;border:1px solid #ffa39e;padding:20px;border-radius:12px;">
                    <h4 style="margin-top:0;color:#cf1322;">{t('tool_cons')}</h4>
                    <ul style="padding-left:20px;">{"".join([f"<li>{c}</li>" for c in cons])}</ul>
                </div>
            </div>
            <article class="article-body">
                {article_content_html}
            </article>
            {faq_section}
        </div>
        {related_tools_html}
    </main>
    <footer class="footer">
        <p>© 2026 {t('header_title')} · {t('footer_text')}</p>
    </footer>
    {BACK_TO_TOP_BLOCK}
</body>
</html>'''
    return html

def build_compare_page(compare_data, all_tools, all_articles=None):
    \"\"\"
    生成工具对比页面 (Phase 2: 对比页)
    URL格式: /compare/{slug}/index.html
    \"\"\"
    lang = compare_data.get('lang', 'zh-CN')
    t = lambda k: get_ui_text(k, lang)

    slug = compare_data.get('slug', 'unknown')
    title = compare_data.get('title', 'AI工具对比评测')
    subtitle = compare_data.get('subtitle', '')
    meta_desc = compare_data.get('meta_description', '')
    keywords = compare_data.get('keywords', [])
    content_md = compare_data.get('content', '')
    compared_slugs = compare_data.get('tools', [])
    verdict = compare_data.get('verdict', {})
    faq_list = compare_data.get('faq', [])

    # 获取对比的工具详情
    compared_tools = []
    for s in compared_slugs:
        tool = next((t for t in all_tools if t['slug'] == s), None)
        if tool:
            compared_tools.append(tool)

    # 对比表头
    compare_headers = ''
    for tool in compared_tools:
        compare_headers += f'''<div class="tool-compare-card" style="flex:1;min-width:200px;text-align:center;padding:16px;border:1px solid #eee;border-radius:12px;background:#fff;">
            <div style="font-size:40px;margin-bottom:8px;">{tool['emoji']}</div>
            <div style="font-weight:700;font-size:18px;">{tool['name']}</div>
            <div style="color:#666;font-size:13px;margin:4px 0;">{tool.get('price','')}</div>
            <div style="color:#fbbc05;">{'★' * int(float(tool.get('rating',0)))}</div>
        </div>'''

    # 结论
    verdict_html = ''
    if verdict:
        v_title = verdict.get('title', '最终结论')
        v_text = verdict.get('text', '')
        verdict_html = f'''<div class="verdict-box" style="background:#e8f0fe;border-left:5px solid #4285F4;padding:20px;border-radius:8px;margin:24px 0;">
            <h3 style="margin-top:0;color:#1967d2;">💡 {v_title}</h3>
            <div style="line-height:1.6;">{markdown_to_html(v_text)}</div>
        </div>'''

    # FAQ
    faq_html = ''
    faq_schema = []
    for fi in faq_list:
        q, a = fi.get('question', ''), fi.get('answer', '')
        if q and a:
            faq_html += f'''<div class="faq-item"><details><summary>{escape_html(q)}</summary><div class="faq-answer">{markdown_to_html(a)}</div></details></div>\\n'''
            faq_schema.append({'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}})
    if faq_html:
        faq_html = f'<div class="faq-section"><h3>❓ {t("tool_features")}</h3>{faq_html}</div>'

    faq_page_schema = ''
    if faq_schema:
        faq_sd = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_schema}
        faq_page_schema = f'''<script type="application/ld+json">{json.dumps(faq_sd, ensure_ascii=False)}</script>'''

    from datetime import datetime as _dtq
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": meta_desc,
        "datePublished": compare_data.get("last_updated", _dtq.now().strftime('%Y-%m-%d')),
        "author": {"@type": "Organization", "name": f"{t('header_title')}"},
        "publisher": {"@type": "Organization", "name": f"{t('header_title')}"}
    }
"""

# 2. find UI_I18N start
start_marker = "# UI国际化字典"
start_idx = content.find(start_marker)
if start_idx == -1:
    start_idx = content.find("UI_I18N = {")

# find matching }
# It's followed by article_schema_json
end_marker = "article_schema_json = json.dumps(article_schema, ensure_ascii=False, indent=2)"
end_idx = content.find(end_marker)

# Find where build_compare_page ends
next_func_marker = "def build_alternatives_page"
end_of_func_idx = content.find(next_func_marker, end_idx)

if start_idx != -1 and end_idx != -1 and end_of_func_idx != -1:
    # Indent the dangling part of build_compare_page
    dangling_part = content[end_idx:end_of_func_idx]
    indented_part = "\n".join(["    " + line if line.strip() else line for line in dangling_part.split("\n")])
    
    # Combine
    new_content = content[:start_idx] + UI_I18N + indented_part + content[end_of_func_idx:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Success')
else:
    print(f'Failed: start_idx={start_idx}, end_idx={end_idx}, end_of_func={end_of_func_idx}')
