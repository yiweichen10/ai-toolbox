#!/usr/bin/env python3
"""
English SSG build script for aitoolbox.hk/en/
Completely independent from build.py — no imports, no shared state.
Outputs all pages under /en/ prefix.
"""
import json
import os
import re
import argparse
from datetime import datetime

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
EN_DIR   = os.path.join(BASE_DIR, 'en')   # all output goes under /en/

# ─── Site constants ────────────────────────────────────────────────────────────
SITE_NAME   = "AI Tool Lab"
SITE_DOMAIN = "https://www.aitoolbox.hk"
SITE_LOGO   = f"{SITE_DOMAIN}/images/logo.png"

# ─── Back-to-top button (no Chinese) ──────────────────────────────────────────
BACK_TO_TOP_BLOCK = '''<button id="backToTop" aria-label="Back to top">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="18 15 12 9 6 15"></polyline>
    </svg>
</button>
<script>
document.addEventListener("DOMContentLoaded",function(){var b=document.getElementById("backToTop");if(!b)return;var s=function(){if(window.scrollY>400){b.classList.add("visible")}else{b.classList.remove("visible")}};window.addEventListener("scroll",s,{passive:true});s();b.addEventListener("click",function(){window.scrollTo({top:0,behavior:"smooth"})});});
</script>'''

# ─── Global nav (English) ─────────────────────────────────────────────────────
GLOBAL_NAV_EN = '''    <nav class="global-nav" aria-label="Global navigation">
        <div class="global-nav-inner">
            <a href="/en/category/" class="gn-item">📂 All Categories</a>
            <a href="/en/articles/" class="gn-item">📖 Articles</a>
            <a href="/en/" class="gn-item">🏠 Home</a>
        </div>
    </nav>'''

# ─── Google Analytics (reuse existing tag if available; no Baidu) ─────────────
GA_BLOCK = ''  # Add GA4 tag here when ready

# ─── English category slug map ────────────────────────────────────────────────
CATEGORY_SLUG_MAP_EN = {
    "AI Chat":        "ai-chat",
    "AI Writing":     "ai-writing",
    "AI Image":       "ai-image",
    "AI Coding":      "ai-coding",
    "AI Video":       "ai-video",
    "AI Audio":       "ai-audio",
    "AI Office":      "ai-office",
    "AI Design":      "ai-design",
    "AI Search":      "ai-search",
    "AI Translation": "ai-translation",
    "AI Automation":  "ai-automation",
    "AI Productivity":"ai-productivity",
    "AI Income":      "ai-income",
    "AI Tools":       "ai-tools",
}

def get_category_slug_en(name: str) -> str:
    if name in CATEGORY_SLUG_MAP_EN:
        return CATEGORY_SLUG_MAP_EN[name]
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

# ─── Helpers ──────────────────────────────────────────────────────────────────

def escape_html(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))

def markdown_to_html(md: str) -> str:
    """Convert Markdown to HTML — same logic as build.py but standalone."""
    if not md:
        return ''
    html = md
    # Code blocks
    html = re.sub(
        r'```(\w*)\n([\s\S]*?)```',
        lambda m: '<pre><code>' + m.group(2).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</code></pre>',
        html
    )
    # Tables
    def table_replace(m):
        header = m.group(1)
        body   = m.group(3)
        headers = [c.strip() for c in header.split('|') if c.strip()]
        rows    = body.strip().split('\n')
        table   = '<table><thead><tr>'
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
    # Headings
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$',  r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$',   r'<h1>\1</h1>', html, flags=re.MULTILINE)
    # Blockquote
    html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
    # Bold / inline code
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    # Links
    html = re.sub(r'\[([^\]]+)\]\((/[^)]+)\)', r'<a href="\2">\1</a>', html)
    html = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', html)
    # Lists
    html = re.sub(r'^- (.+)$',        r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^\d+\. (.+)$',    r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul>\1</ul>', html)
    # Paragraphs
    lines   = html.split('\n')
    result  = []
    in_p    = False
    block_tags = ('<h1','<h2','<h3','<ul','</ul','<li','<table','</table',
                  '<pre','</pre','<blockquote','</blockquote')
    for line in lines:
        stripped = line.strip()
        is_tag   = stripped == '' or any(stripped.startswith(t) for t in block_tags)
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

# ─── Header / footer partials ─────────────────────────────────────────────────

def header_html(title_text: str = "AI Tool Lab") -> str:
    return f'''    <header class="header">
        <div class="header-inner">
            <a href="/en/" style="text-decoration:none;">
                <h1>🛠️ {SITE_NAME} <span>Daily updates · 500+ AI tools</span></h1>
            </a>
        </div>
    </header>'''

def footer_html() -> str:
    today = datetime.now().strftime('%Y-%m-%d')
    return f'''    <footer class="footer">
        <p>© {datetime.now().year} {SITE_NAME} · Best AI Tools, Updated Daily · <a href="/" style="color:#999;">中文版</a></p>
    </footer>'''

def hreflang_tags(zh_path: str, en_path: str) -> str:
    """Generate hreflang link tags for zh/en pair."""
    return (
        f'    <link rel="alternate" hreflang="zh-CN" href="{SITE_DOMAIN}{zh_path}">\n'
        f'    <link rel="alternate" hreflang="en"    href="{SITE_DOMAIN}{en_path}">\n'
        f'    <link rel="alternate" hreflang="x-default" href="{SITE_DOMAIN}{en_path}">\n'
    )

# ─── Tool page ────────────────────────────────────────────────────────────────

def get_og_image_url(slug: str) -> str:
    """Return og:image URL — use existing image if available, else fallback to logo."""
    local_path = os.path.join(BASE_DIR, 'images', 'og', f'{slug}-og.png')
    if os.path.exists(local_path):
        return f'{SITE_DOMAIN}/images/og/{slug}-og.png'
    return f'{SITE_DOMAIN}/images/logo.png'


def build_tool_page_en(tool: dict, all_tools: list, all_articles: list = None) -> str:
    slug = tool['slug']
    name = tool['name']
    cat  = tool.get('category', 'AI Tools')
    cat_slug = get_category_slug_en(cat)

    # Related tools
    same_cat   = [t for t in all_tools if t['slug'] != slug and t.get('category') == cat]
    other_cat  = [t for t in all_tools if t['slug'] != slug and t.get('category') != cat]
    import random; random.seed(42)
    selected   = (same_cat + other_cat)[:5]
    related_html = ''
    if selected:
        cards = ''
        for r in selected:
            cards += f'''<a href="/en/tools/{r['slug']}/" class="related-card">
                <div style="font-size:24px;margin-bottom:8px;">{r['emoji']}</div>
                <div style="font-weight:600;">{r['name']}</div>
                <div style="font-size:13px;color:#666;">{r.get('category','')}</div>
            </a>\n'''
        related_html = f'''<div class="related-tools" id="relatedSection">
            <h3>🔗 Related Tools</h3>
            <div class="related-grid">{cards}</div>
        </div>'''

    # Related articles
    related_articles_html = ''
    if all_articles:
        name_lower = name.lower()
        matched = [a for a in all_articles if name_lower in a.get('title','').lower() or name_lower in a.get('description','').lower()]
        if len(matched) < 2:
            matched += [a for a in all_articles if a not in matched][:3 - len(matched)]
        if matched:
            cards = ''
            for a in matched[:3]:
                cards += f'''<a href="/en/articles/{a['slug']}/" class="related-card">
                    <div style="font-weight:600;margin-bottom:4px;">📖 {escape_html(a['title'][:40])}</div>
                    <div style="font-size:13px;color:#666;">{a.get('dateFull', a.get('date',''))}</div>
                </a>\n'''
            related_articles_html = f'''<div class="related-tools">
                <h3>📚 Related Articles</h3>
                <div class="related-grid">{cards}</div>
            </div>'''

    # Pros / cons
    pros_cons_html = ''
    if tool.get('pros') and tool.get('cons'):
        pros_html = ''.join(f'<li>{p}</li>' for p in tool['pros'])
        cons_html = ''.join(f'<li>{c}</li>' for c in tool['cons'])
        pros_cons_html = f'''<div class="pros-cons">
            <div class="pros">
                <h4>👍 Pros</h4>
                <ul>{pros_html}</ul>
            </div>
            <div class="cons">
                <h4>👎 Cons</h4>
                <ul>{cons_html}</ul>
            </div>
        </div>'''

    # Features
    features_html = ''
    if tool.get('features'):
        items = ''.join(f'<div class="feature-item">{f}</div>\n' for f in tool['features'])
        features_html = f'<div class="features-grid">{items}</div>'

    # FAQ
    faq_html   = ''
    faq_schema = []
    if tool.get('faq'):
        for fi in tool['faq']:
            q, a = fi.get('question',''), fi.get('answer','')
            if q and a:
                faq_html += f'''<div class="faq-item">
                    <details>
                        <summary>{escape_html(q)}</summary>
                        <div class="faq-answer">{markdown_to_html(a)}</div>
                    </details>
                </div>\n'''
                faq_schema.append({'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':a}})
        if faq_html:
            faq_html = f'<div class="faq-section"><h3>❓ FAQ</h3>{faq_html}</div>'

    faq_page_schema = ''
    if faq_schema:
        faq_sd = {"@context":"https://schema.org","@type":"FAQPage","mainEntity":faq_schema}
        faq_page_schema = f'<script type="application/ld+json">{json.dumps(faq_sd, ensure_ascii=False)}</script>'

    # Badge
    badge_html = ''
    if tool.get('badge'):
        bc = {'hot':'#ff4444','new':'#00aa00','pick':'#667eea'}.get(tool['badge'].get('type'),'#667eea')
        badge_html = f' <span class="badge" style="background:{bc};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;">{tool["badge"]["text"]}</span>'

    # Platform
    platform_html = ''
    if tool.get('platform'):
        platform_html = f'<div class="tool-meta-item">📦 <strong>Platform</strong>: {tool["platform"]}</div>'

    # Dates
    today_iso   = datetime.now().strftime('%Y-%m-%d')
    date_pub    = tool.get('datePublished', today_iso)
    date_mod    = tool.get('dateModified',  today_iso)

    # Structured data
    breadcrumb_data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type":"ListItem","position":1,"name":"Home","item":f"{SITE_DOMAIN}/en/"},
            {"@type":"ListItem","position":2,"name":cat,"item":f"{SITE_DOMAIN}/en/category/{cat_slug}/"},
            {"@type":"ListItem","position":3,"name":name,"item":f"{SITE_DOMAIN}/en/tools/{slug}/"},
        ]
    }
    software_data = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": name,
        "applicationCategory": "UtilitiesApplication",
        "operatingSystem": tool.get('platform','Web'),
        "description": tool['description'],
        "datePublished": date_pub,
        "dateModified":  date_mod,
        "offers": {"@type":"Offer","price":tool.get('price',''),"priceCurrency":"USD"},
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": tool['rating'].replace('⭐ ',''),
            "ratingCount": "1000"
        }
    }
    breadcrumb_json  = json.dumps(breadcrumb_data,  ensure_ascii=False, indent=2)
    structured_json  = json.dumps(software_data,    ensure_ascii=False, indent=2)

    # Content (strip duplicate pros/cons headers)
    content_md   = tool.get('content','')
    content_html = markdown_to_html(content_md)

    # hreflang
    hreflang  = hreflang_tags(f'/tools/{slug}/', f'/en/tools/{slug}/')
    og_image  = get_og_image_url(slug)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(name)} Review 2026: Features, Pricing & Alternatives - {SITE_NAME}</title>
    <meta name="description" content="{escape_html(name)} full review 2026: {escape_html(tool['description'][:120])} Pricing, pros, cons, and alternatives.">
    <meta name="keywords" content="{escape_html(name)},{escape_html(name)} review,{escape_html(name)} pricing,{escape_html(cat)},AI tools 2026">
    <link rel="canonical" href="{SITE_DOMAIN}/en/tools/{slug}/">
{hreflang}    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(name)} Review 2026 - {SITE_NAME}">
    <meta property="og:description" content="{escape_html(tool['description'][:150])}">
    <meta property="og:url" content="{SITE_DOMAIN}/en/tools/{slug}/">
    <meta property="og:image" content="{og_image}">
    <meta property="og:site_name" content="{SITE_NAME}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(name)} Review 2026 - {SITE_NAME}">
    <meta name="twitter:description" content="{escape_html(tool['description'][:120])}">
    <meta name="twitter:image" content="{og_image}">
    <link rel="stylesheet" href="/css/style.css">
    <script type="application/ld+json">{breadcrumb_json}</script>
    <script type="application/ld+json">{structured_json}</script>
    {faq_page_schema}
{GA_BLOCK}
</head>
<body>
{header_html()}

    <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="/en/">Home</a> &gt; <a href="/en/category/{cat_slug}/">{escape_html(cat)}</a> &gt; <span>{escape_html(name)}</span>
    </nav>

    <main class="article-container">
        <div class="tool-header">
            <div class="tool-header-top">
                <div class="tool-icon-lg" style="background:{tool['color']};">{tool['emoji']}</div>
                <div class="tool-header-info">
                    <h2>{escape_html(name)}{badge_html}</h2>
                    <p class="subtitle">{escape_html(tool['description'])}</p>
                    <div class="rating-bar">{tool['rating']} <span style="font-size:14px;color:#999;">({tool.get('visits','0')} visits)</span></div>
                </div>
            </div>
            <div class="tool-meta">
                <div class="tool-meta-item">🌐 <strong>Website</strong>: {tool['url'].replace('https://','')}</div>
                <div class="tool-meta-item">💰 <strong>Price</strong>: {tool.get('price','')}</div>
                {platform_html}
                <div class="tool-meta-item">🏷️ <strong>Category</strong>: {escape_html(cat)}</div>
            </div>
            <div class="action-bar">
                <a href="{tool['url']}" target="_blank" rel="noopener" class="action-btn action-btn-primary">Visit {escape_html(name)} →</a>
            </div>
        </div>

        {features_html}

        <article class="article-body">
            {content_html}
        </article>

        {pros_cons_html}

        {faq_html}

        {related_html}

        {related_articles_html}
    </main>

{footer_html()}
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''


# ─── Article page ─────────────────────────────────────────────────────────────

def build_article_page_en(article: dict, all_articles: list, all_tools: list = None) -> str:
    slug     = article['slug']
    title    = article['title']
    cat      = article.get('category', 'AI Tools')
    cat_slug = get_category_slug_en(cat)
    date_str = article.get('dateFull', article.get('date',''))

    # Parse date to ISO for schema
    article_date = article.get('date', datetime.now().strftime('%Y-%m-%d'))

    # Related tools
    related_tools_html = ''
    if all_tools:
        title_lower = title.lower()
        matched = [t for t in all_tools if t.get('name','').lower() in title_lower]
        if len(matched) < 3:
            matched += [t for t in all_tools if t not in matched][:5 - len(matched)]
        if matched:
            cards = ''
            for t in matched[:5]:
                cards += f'''<a href="/en/tools/{t['slug']}/" class="related-card">
                    <div style="font-size:24px;margin-bottom:8px;">{t['emoji']}</div>
                    <div style="font-weight:600;">{escape_html(t['name'])}</div>
                    <div style="font-size:13px;color:#666;">{escape_html(t.get('category',''))}</div>
                </a>\n'''
            related_tools_html = f'''<div class="related-tools">
            <h3>🔧 Related Tools</h3>
            <div class="related-grid">{cards}</div>
        </div>'''

    # Related articles
    same_cat = [a for a in all_articles if a['slug'] != slug and a.get('category') == cat]
    if len(same_cat) < 2:
        same_cat = [a for a in all_articles if a['slug'] != slug][:3]
    related_html = ''
    if same_cat:
        cards = ''
        for a in same_cat[:3]:
            cards += f'''<a href="/en/articles/{a['slug']}/" class="related-card">
                <div style="font-weight:600;margin-bottom:4px;">{escape_html(a['title'])}</div>
                <div style="font-size:13px;color:#666;">{a.get('dateFull', a.get('date',''))}</div>
            </a>\n'''
        related_html = f'''<div class="related-tools">
            <h3>📖 Related Articles</h3>
            <div class="related-grid">{cards}</div>
        </div>'''

    # Structured data
    breadcrumb_data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type":"ListItem","position":1,"name":"Home","item":f"{SITE_DOMAIN}/en/"},
            {"@type":"ListItem","position":2,"name":cat,"item":f"{SITE_DOMAIN}/en/category/{cat_slug}/"},
            {"@type":"ListItem","position":3,"name":title,"item":f"{SITE_DOMAIN}/en/articles/{slug}/"},
        ]
    }
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": article.get('description',''),
        "datePublished": article_date,
        "dateModified":  article.get('dateModified', article_date),
        "author": {"@type":"Organization","name":SITE_NAME},
        "publisher": {
            "@type": "Organization",
            "name": SITE_NAME,
            "logo": {"@type":"ImageObject","url":SITE_LOGO}
        },
        "mainEntityOfPage": {"@type":"WebPage","@id":f"{SITE_DOMAIN}/en/articles/{slug}/"}
    }
    breadcrumb_json = json.dumps(breadcrumb_data,  ensure_ascii=False, indent=2)
    structured_json = json.dumps(article_schema,   ensure_ascii=False, indent=2)

    content_html = markdown_to_html(article.get('content',''))
    hreflang     = hreflang_tags(f'/articles/{slug}/', f'/en/articles/{slug}/')
    og_image     = get_og_image_url(slug)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)} - {SITE_NAME}</title>
    <meta name="description" content="{escape_html(article.get('description',''))}">
    <meta name="keywords" content="{escape_html(article.get('keywords',''))}">
    <link rel="canonical" href="{SITE_DOMAIN}/en/articles/{slug}/">
{hreflang}    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(title)} - {SITE_NAME}">
    <meta property="og:description" content="{escape_html(article.get('description',''))}">
    <meta property="og:url" content="{SITE_DOMAIN}/en/articles/{slug}/">
    <meta property="og:image" content="{og_image}">
    <meta property="og:site_name" content="{SITE_NAME}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(title)} - {SITE_NAME}">
    <meta name="twitter:description" content="{escape_html(article.get('description',''))}">
    <meta name="twitter:image" content="{og_image}">
    <link rel="stylesheet" href="/css/style.css">
    <script type="application/ld+json">{breadcrumb_json}</script>
    <script type="application/ld+json">{structured_json}</script>
{GA_BLOCK}
</head>
<body>
{header_html()}

    <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="/en/">Home</a> &gt; <a href="/en/category/{cat_slug}/">{escape_html(cat)}</a> &gt; <span>{escape_html(title)[:30]}...</span>
    </nav>

    <main class="article-container">
        <article class="article-body">
            <h1 style="margin-bottom:16px;">{escape_html(title)}</h1>
            <div style="color:#999;font-size:14px;margin-bottom:24px;">
                {date_str} · {escape_html(cat)}
            </div>
            {content_html}
        </article>

        {related_html}

        {related_tools_html}
    </main>

{footer_html()}
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''


# ─── Category page ────────────────────────────────────────────────────────────

def build_category_page_en(cat_name: str, tools: list) -> str:
    cat_slug = get_category_slug_en(cat_name)
    tool_cards = ''
    for t in tools:
        badge_html = ''
        if t.get('badge'):
            bc = {'hot':'#ff4444','new':'#00aa00','pick':'#667eea'}.get(t['badge'].get('type'),'#667eea')
            badge_html = f'<span class="badge" style="background:{bc};color:#fff;padding:2px 6px;border-radius:3px;font-size:11px;">{t["badge"]["text"]}</span>'
        tool_cards += f'''<a href="/en/tools/{t['slug']}/" class="tool-card">
            <div class="tool-icon" style="background:{t['color']};">{t['emoji']}</div>
            <div class="tool-info">
                <h3>{escape_html(t['name'])} {badge_html}</h3>
                <p>{escape_html(t['description'][:80])}</p>
                <div class="tool-meta-row">
                    <span>{t['rating']}</span>
                    <span>{t.get('price','')}</span>
                </div>
            </div>
        </a>\n'''

    breadcrumb_data = {
        "@context":"https://schema.org","@type":"BreadcrumbList",
        "itemListElement":[
            {"@type":"ListItem","position":1,"name":"Home","item":f"{SITE_DOMAIN}/en/"},
            {"@type":"ListItem","position":2,"name":cat_name,"item":f"{SITE_DOMAIN}/en/category/{cat_slug}/"},
        ]
    }
    breadcrumb_json = json.dumps(breadcrumb_data, ensure_ascii=False, indent=2)
    hreflang = hreflang_tags(f'/category/{cat_slug}/', f'/en/category/{cat_slug}/')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Best {escape_html(cat_name)} Tools 2026 ({len(tools)} Reviewed) - {SITE_NAME}</title>
    <meta name="description" content="Best {escape_html(cat_name)} AI tools in 2026. We reviewed {len(tools)} tools and ranked them by features, pricing, and real-world performance.">
    <meta name="keywords" content="{escape_html(cat_name)},best {escape_html(cat_name)} tools,AI tools 2026">
    <link rel="canonical" href="{SITE_DOMAIN}/en/category/{cat_slug}/">
{hreflang}    <link rel="stylesheet" href="/css/style.css">
    <script type="application/ld+json">{breadcrumb_json}</script>
{GA_BLOCK}
</head>
<body>
{header_html()}

    <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="/en/">Home</a> &gt; <a href="/en/category/">Categories</a> &gt; <span>{escape_html(cat_name)}</span>
    </nav>

    <main class="tool-list-container">
        <h1 style="margin-bottom:8px;">Best {escape_html(cat_name)} Tools 2026</h1>
        <p style="color:#666;margin-bottom:24px;">{len(tools)} tools reviewed and ranked</p>
        <div class="tool-grid">
            {tool_cards}
        </div>
    </main>

{footer_html()}
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''


# ─── Article list page ────────────────────────────────────────────────────────

def build_article_list_en(articles: list) -> str:
    ITEMS_PER_PAGE = 10
    total   = len(articles)
    page1   = articles[:ITEMS_PER_PAGE]
    cards   = ''
    for a in page1:
        cards += f'''<article class="article-card">
            <h3><a href="/en/articles/{a['slug']}/">{escape_html(a['title'])}</a></h3>
            <div class="article-meta">
                <span class="date">{a.get('dateFull', a.get('date',''))}</span>
                <span class="category">{escape_html(a.get('category',''))}</span>
            </div>
            <p class="summary">{escape_html(a.get('description','')[:150])}</p>
        </article>\n'''

    hreflang = hreflang_tags('/articles/', '/en/articles/')
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Tool Articles & Guides 2026 - {SITE_NAME}</title>
    <meta name="description" content="In-depth AI tool reviews, comparisons, and guides. Updated daily with practical advice for using AI to save time and make money.">
    <link rel="canonical" href="{SITE_DOMAIN}/en/articles/">
{hreflang}    <link rel="stylesheet" href="/css/style.css">
{GA_BLOCK}
</head>
<body>
{header_html()}

    <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="/en/">Home</a> &gt; <span>Articles</span>
    </nav>

    <main class="article-list-container">
        <h1 style="margin-bottom:24px;">AI Tool Articles & Guides</h1>
        <div class="article-list">
            {cards}
        </div>
    </main>

{footer_html()}
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''


# ─── Category index page ──────────────────────────────────────────────────────

def build_category_index_en(tools_by_cat: dict) -> str:
    cat_cards = ''
    for cat_name, tools in tools_by_cat.items():
        cat_slug  = get_category_slug_en(cat_name)
        sample_emoji = tools[0]['emoji'] if tools else '🤖'
        cat_cards += f'''<a href="/en/category/{cat_slug}/" class="tool-card" style="text-decoration:none;">
            <div class="tool-icon" style="background:#667eea;">{sample_emoji}</div>
            <div class="tool-info">
                <h3>{escape_html(cat_name)}</h3>
                <p>{len(tools)} tools reviewed</p>
            </div>
        </a>\n'''

    hreflang = hreflang_tags('/category/', '/en/category/')
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>All AI Tool Categories 2026 - {SITE_NAME}</title>
    <meta name="description" content="Browse all AI tool categories. Find the best AI tools for writing, coding, image generation, video, and more.">
    <link rel="canonical" href="{SITE_DOMAIN}/en/category/">
{hreflang}    <link rel="stylesheet" href="/css/style.css">
{GA_BLOCK}
</head>
<body>
{header_html()}

    <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="/en/">Home</a> &gt; <span>All Categories</span>
    </nav>

    <main class="tool-list-container">
        <h1 style="margin-bottom:24px;">All AI Tool Categories</h1>
        <div class="tool-grid">
            {cat_cards}
        </div>
    </main>

{footer_html()}
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''


# ─── Homepage ─────────────────────────────────────────────────────────────────

def build_index_en(tools: list, articles: list) -> str:
    # Tool cards (top 12 by visits, fallback to first 12)
    def parse_visits(v):
        v = str(v).replace('K','000').replace('M','000000').replace(',','')
        try:
            return int(float(v))
        except:
            return 0

    top_tools = sorted(tools, key=lambda t: parse_visits(t.get('visits','0')), reverse=True)[:12]
    tool_cards = ''
    for t in top_tools:
        badge_html = ''
        if t.get('badge'):
            bc = {'hot':'#ff4444','new':'#00aa00','pick':'#667eea'}.get(t['badge'].get('type'),'#667eea')
            badge_html = f'<span class="badge" style="background:{bc};color:#fff;padding:2px 6px;border-radius:3px;font-size:11px;margin-left:6px;">{t["badge"]["text"]}</span>'
        tool_cards += f'''<a href="/en/tools/{t['slug']}/" class="tool-card">
            <div class="tool-icon" style="background:{t['color']};">{t['emoji']}</div>
            <div class="tool-info">
                <h3>{escape_html(t['name'])}{badge_html}</h3>
                <p>{escape_html(t['description'][:70])}</p>
                <div class="tool-meta-row">
                    <span>{t['rating']}</span>
                    <span>{t.get('price','')}</span>
                </div>
            </div>
        </a>\n'''

    # Recent articles (top 5)
    article_cards = ''
    for a in articles[:5]:
        article_cards += f'''<article class="article-card">
            <h3><a href="/en/articles/{a['slug']}/">{escape_html(a['title'])}</a></h3>
            <div class="article-meta">
                <span class="date">{a.get('dateFull', a.get('date',''))}</span>
                <span class="category">{escape_html(a.get('category',''))}</span>
            </div>
            <p class="summary">{escape_html(a.get('description','')[:120])}</p>
        </article>\n'''

    total_tools = len(tools)
    total_articles = len(articles)
    today = datetime.now().strftime('%B %d, %Y')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Best AI Tools 2026: {total_tools}+ Tools Reviewed & Ranked - {SITE_NAME}</title>
    <meta name="description" content="Discover the best AI tools in 2026. We review and rank {total_tools}+ AI tools across writing, coding, image generation, video, and more. Updated daily.">
    <meta name="keywords" content="best AI tools 2026,AI tools review,AI tools comparison,top AI tools">
    <link rel="canonical" href="{SITE_DOMAIN}/en/">
    <link rel="alternate" hreflang="zh-CN" href="{SITE_DOMAIN}/">
    <link rel="alternate" hreflang="en" href="{SITE_DOMAIN}/en/">
    <link rel="alternate" hreflang="x-default" href="{SITE_DOMAIN}/en/">
    <meta property="og:type" content="website">
    <meta property="og:title" content="Best AI Tools 2026: {total_tools}+ Reviewed - {SITE_NAME}">
    <meta property="og:description" content="Find the best AI tools for writing, coding, image generation, and productivity. Updated daily.">
    <meta property="og:url" content="{SITE_DOMAIN}/en/">
    <meta property="og:image" content="{SITE_DOMAIN}/images/logo.png">
    <meta property="og:site_name" content="{SITE_NAME}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Best AI Tools 2026: {total_tools}+ Reviewed - {SITE_NAME}">
    <meta name="twitter:description" content="Find the best AI tools for writing, coding, image generation, and productivity. Updated daily.">
    <meta name="twitter:image" content="{SITE_DOMAIN}/images/logo.png">
    <link rel="stylesheet" href="/css/style.css">
{GA_BLOCK}
</head>
<body>
{header_html()}

    <main>
        <section class="hero" style="text-align:center;padding:40px 20px 20px;">
            <h2 style="font-size:28px;margin-bottom:12px;">Find the Best AI Tools for Your Work</h2>
            <p style="color:#666;font-size:16px;max-width:600px;margin:0 auto 24px;">
                {total_tools}+ AI tools reviewed and ranked. Updated daily. Last updated: {today}.
            </p>
            <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
                <a href="/en/category/" class="action-btn action-btn-primary">Browse All Categories</a>
                <a href="/en/articles/" class="action-btn">Read Guides</a>
            </div>
        </section>

        <section style="max-width:1200px;margin:0 auto;padding:0 16px;">
            <h2 style="margin-bottom:20px;">🔥 Top AI Tools</h2>
            <div class="tool-grid">
                {tool_cards}
            </div>
            <div style="text-align:center;margin-top:24px;">
                <a href="/en/category/" class="action-btn">View All {total_tools}+ Tools →</a>
            </div>
        </section>

        <section style="max-width:1200px;margin:40px auto 0;padding:0 16px;">
            <h2 style="margin-bottom:20px;">📖 Latest Articles</h2>
            <div class="article-list">
                {article_cards}
            </div>
            <div style="text-align:center;margin-top:24px;">
                <a href="/en/articles/" class="action-btn">All Articles →</a>
            </div>
        </section>
    </main>

{footer_html()}
    ''' + BACK_TO_TOP_BLOCK + '''
</body>
</html>'''


# ─── Sitemap (English only) ───────────────────────────────────────────────────

def generate_sitemap_en(tools: list, articles: list, cat_slugs: list) -> str:
    today = datetime.now().strftime('%Y-%m-%d')
    urls  = [
        f'    <url><loc>{SITE_DOMAIN}/en/</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>',
        f'    <url><loc>{SITE_DOMAIN}/en/category/</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>',
        f'    <url><loc>{SITE_DOMAIN}/en/articles/</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>0.8</priority></url>',
    ]
    for cs in cat_slugs:
        urls.append(f'    <url><loc>{SITE_DOMAIN}/en/category/{cs}/</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>')
    for t in tools:
        urls.append(f'    <url><loc>{SITE_DOMAIN}/en/tools/{t["slug"]}/</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>')
    for a in articles:
        pub = a.get('date', today)
        urls.append(f'    <url><loc>{SITE_DOMAIN}/en/articles/{a["slug"]}/</loc><lastmod>{pub}</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>')

    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(urls) + '\n</urlset>'


# ─── IndexNow push (Bing/Google) ──────────────────────────────────────────────

def push_to_indexnow_en(urls: list) -> bool:
    import urllib.request
    INDEXNOW_KEY = "6b95d3c7e8f24a1b9d0e5f2c8a7b4e3d"  # reuse same key as main site
    key_location = f"{SITE_DOMAIN}/{INDEXNOW_KEY}.txt"
    payload = json.dumps({
        "host": "www.aitoolbox.hk",
        "key": INDEXNOW_KEY,
        "keyLocation": key_location,
        "urlList": urls[:100]
    }).encode('utf-8')
    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"  IndexNow response: {resp.status}")
            return resp.status in (200, 202)
    except Exception as e:
        print(f"  IndexNow error: {e}")
        return False


# ─── Nav injection (English only — only scans /en/ dir) ──────────────────────

def inject_global_nav_en():
    """Inject English global nav into all HTML files under /en/ only."""
    injected = 0
    for root, dirs, files in os.walk(EN_DIR):
        for fname in files:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if '</header>' in content and 'class="global-nav"' not in content:
                    content = content.replace('</header>', GLOBAL_NAV_EN + '\n    </header>', 1)
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    injected += 1
            except Exception:
                pass
    if injected:
        print(f'[Post] Injected EN nav into {injected} HTML files under /en/')
    return injected


# ─── Main build ───────────────────────────────────────────────────────────────

def build_all_en(target: str = 'all'):
    # Load data
    tools_en_path    = os.path.join(DATA_DIR, 'tools_en.json')
    articles_en_path = os.path.join(DATA_DIR, 'articles_en.json')

    if not os.path.exists(tools_en_path):
        print(f'[ERROR] {tools_en_path} not found. Run generate_tools_en.py first.')
        return
    if not os.path.exists(articles_en_path):
        print(f'[ERROR] {articles_en_path} not found. Run generate_articles_en.py first.')
        return

    with open(tools_en_path,    encoding='utf-8') as f:
        all_tools = json.load(f)
    with open(articles_en_path, encoding='utf-8') as f:
        articles  = json.load(f)

    published_tools = [t for t in all_tools if t.get('published', False)]
    print(f'[EN] {len(published_tools)} published tools, {len(articles)} articles')

    # Group by category
    tools_by_cat: dict = {}
    for t in published_tools:
        cat = t.get('category','')
        if cat:
            tools_by_cat.setdefault(cat, []).append(t)

    # ── Category pages ────────────────────────────────────────────────────────
    if target in ('all', 'index', 'tools'):
        for cat_name, tools_in_cat in tools_by_cat.items():
            cat_slug = get_category_slug_en(cat_name)
            dir_path = os.path.join(EN_DIR, 'category', cat_slug)
            os.makedirs(dir_path, exist_ok=True)
            html = build_category_page_en(cat_name, tools_in_cat)
            with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(html)
            print(f'[OK] en/category/{cat_slug}/index.html')

        # Category index
        dir_path = os.path.join(EN_DIR, 'category')
        os.makedirs(dir_path, exist_ok=True)
        html = build_category_index_en(tools_by_cat)
        with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'[OK] en/category/index.html')

    # ── Tool pages ────────────────────────────────────────────────────────────
    if target in ('all', 'tools'):
        for tool in published_tools:
            slug     = tool['slug']
            dir_path = os.path.join(EN_DIR, 'tools', slug)
            os.makedirs(dir_path, exist_ok=True)
            html = build_tool_page_en(tool, published_tools, articles)
            with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(html)
            print(f'[OK] en/tools/{slug}/index.html')

    # ── Article pages ─────────────────────────────────────────────────────────
    if target in ('all', 'articles'):
        for article in articles:
            slug     = article['slug']
            dir_path = os.path.join(EN_DIR, 'articles', slug)
            os.makedirs(dir_path, exist_ok=True)
            html = build_article_page_en(article, articles, published_tools)
            with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(html)
            print(f'[OK] en/articles/{slug}/index.html')

        # Article list
        dir_path = os.path.join(EN_DIR, 'articles')
        os.makedirs(dir_path, exist_ok=True)
        html = build_article_list_en(articles)
        with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'[OK] en/articles/index.html')

    # ── English homepage ──────────────────────────────────────────────────────
    if target in ('all', 'index'):
        os.makedirs(EN_DIR, exist_ok=True)
        html = build_index_en(published_tools, articles)
        with open(os.path.join(EN_DIR, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'[OK] en/index.html')

    # ── Nav injection (EN only) ───────────────────────────────────────────────
    inject_global_nav_en()

    # ── Sitemap ───────────────────────────────────────────────────────────────
    cat_slugs = [get_category_slug_en(c) for c in tools_by_cat.keys()]
    sitemap   = generate_sitemap_en(published_tools, articles, cat_slugs)
    with open(os.path.join(EN_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(sitemap)
    print(f'[OK] en/sitemap.xml ({len(published_tools)} tools + {len(articles)} articles)')

    # ── IndexNow push ─────────────────────────────────────────────────────────
    cache_file = os.path.join(BASE_DIR, '.indexnow_en_pushed.json')
    pushed = set()
    if os.path.exists(cache_file):
        with open(cache_file, encoding='utf-8') as f:
            pushed = set(json.load(f))

    all_urls = [f"{SITE_DOMAIN}/en/"]
    all_urls += [f"{SITE_DOMAIN}/en/tools/{t['slug']}/" for t in published_tools]
    all_urls += [f"{SITE_DOMAIN}/en/articles/{a['slug']}/" for a in articles]
    all_urls += [f"{SITE_DOMAIN}/en/category/{get_category_slug_en(c)}/" for c in tools_by_cat]

    new_urls = [u for u in all_urls if u not in pushed]
    if new_urls:
        print(f'\n[EN] Pushing {len(new_urls)} new URLs via IndexNow...')
        if push_to_indexnow_en(new_urls):
            pushed.update(new_urls)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(list(pushed), f)
    else:
        print(f'[EN] IndexNow: no new URLs to push ({len(all_urls)} total, all pushed)')

    print(f'\n[EN] Done! {len(published_tools)} tools + {len(articles)} articles built under /en/')


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='AI Tool Lab English SSG')
    parser.add_argument(
        '--target', '-t',
        choices=['all', 'tools', 'articles', 'index'],
        default='all',
        help='Build target (default: all)'
    )
    args = parser.parse_args()
    build_all_en(args.target)


if __name__ == '__main__':
    main()
