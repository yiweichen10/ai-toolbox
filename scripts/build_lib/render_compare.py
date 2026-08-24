# render_compare.py — 对比页/替代页/Quiz/对比索引/替代索引/排行索引
# 模块7：从 build.py 拆分（2026-08-24）
import os
import re
import random

from build_lib.html_utils import (
    escape_html, markdown_to_html,
)
from build_lib.data_loaders import (
    get_category_slug, load_compare_data, load_quiz_data, load_ranking_data,
)
from build_lib.render_tool import (
    build_tool_page, make_tool_card_html, tool_icon_html,
)


def build_compare_page(compare_data, all_tools, all_articles=None, existing_compare_slugs=None):
    import build  # 延迟：build 完全加载后解析
    """
    生成对比页面 (Phase 2: 程序化SEO)
    URL格式: /compare/{toolA-vs-toolB}/index.html
    覆盖关键词: "XX vs XX" / "XX和XX对比" / "XX XX哪个好"
    """
    slug = compare_data.get('slug', 'unknown')
    title = compare_data.get('title', 'AI工具对比')
    subtitle = compare_data.get('subtitle', '')
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

    # Meta description（2026-08-06：兜底从「短句」升级为完整描述，消除 Bing 过短警告）
    _cmp_names = [t.get('name', '') for t in compared_tools if t.get('name')]
    if len(_cmp_names) >= 2:
        _cmp_fallback = (f"{_cmp_names[0]}和{_cmp_names[1]}哪个好？{build.BUILD_YEAR}年深度对比评测："
                         f"从功能、价格、优缺点、适用场景到真实实测数据逐项拆解，涵盖免费额度、"
                         f"中文可用性与上手难度，逐项打分对比后给出按预算和场景的最优选择，"
                         f"附完整选型建议，帮你一次看清差距、快速选出最适合自己的AI工具。")
    else:
        _cmp_fallback = (f"{title}：{build.BUILD_YEAR}年AI工具深度对比评测，从功能、价格、优缺点、"
                         f"适用场景到真实实测数据逐项拆解，涵盖免费额度与中文可用性，"
                         f"逐项打分后附完整选型建议与避坑提示，帮你快速做出最适合自己的选择。")
    _cmp_meta = compare_data.get('meta_description') or ''
    # 2026-08-13（阶段2.3）：门槛 100 → 115，避免 100~114 字的数据描述被 Bing 判过短
    meta_desc = _cmp_meta if len(_cmp_meta) >= 115 else _cmp_fallback

    # 对比工具头部（并排展示）
    compare_headers = ''
    for t in compared_tools:
        compare_headers += f'''
            <div class="compare-tool-card">
                {tool_icon_html(t, large=True)}
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
            verdict_html = f'''<div class="quick-verdict" id="verdict">
                <h3>⚡ 快速结论</h3>
                <ul>{verdict_items}</ul>
            </div>'''

    # FAQ
    faq_html = ''
    faq_schema = []
    for faq_item in faq_list:
        q = faq_item.get('question') or faq_item.get('q', '')
        a = faq_item.get('answer') or faq_item.get('a', '')
        if q and a:
            faq_html += f'''<div class="faq-item"><div class="faq-q">{escape_html(q)}</div><div class="faq-a">{markdown_to_html(a)}</div></div>\n'''
            faq_schema.append({'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}})
    if faq_html:
        faq_html = f'<div class="faq-section" id="faq"><h3>❓ 常见问题</h3>{faq_html}</div>'

    # FAQ Schema
    faq_page_schema = ''
    if faq_schema:
        faq_sd = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_schema}
        faq_page_schema = f'<script type="application/ld+json">{json.dumps(faq_sd, ensure_ascii=False)}</script>'

    # Article Schema（对比文章也是Article类型）- AEO+GEO 增强 EEAT 信号 2026-06-23
    from datetime import datetime as _dt
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": meta_desc,
        "datePublished": compare_data.get("last_updated", _dt.now().strftime('%Y-%m-%d')),
        "dateModified": compare_data.get("last_updated", _dt.now().strftime('%Y-%m-%d')),
        "inLanguage": "zh-CN",
        "author": {
            "@type": "Organization",
            "name": "AI工具宝箱编辑组",
            "url": "https://www.aitoollab.cn/",
            "description": "专注 AI 工具实测与对比研究的独立编辑团队",
            "knowsAbout": ["AI工具评测", "AI模型对比", "AEO内容优化", "GEO生成式引擎优化"]
        },
        "publisher": {
            "@type": "Organization",
            "name": "AI工具宝箱",
            "url": "https://www.aitoollab.cn/",
            "logo": {
                "@type": "ImageObject",
                "url": "https://www.aitoollab.cn/images/logo.png"
            },
            "foundingDate": "2026-03-21",
            "slogan": "实测数据驱动 AI 工具决策",
            "sameAs": ["https://github.com/yiweichen10/ai-toolbox"]
        },
        "isPartOf": {
            "@type": "WebSite",
            "name": "AI工具宝箱",
            "url": "https://www.aitoollab.cn/"
        }
    }
    article_schema_json = json.dumps(article_schema, ensure_ascii=False, indent=2)

    # Breadcrumb
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoollab.cn/"},
            {"@type": "ListItem", "position": 2, "name": "工具对比", "item": "https://www.aitoollab.cn/compare/"},
            {"@type": "ListItem", "position": 3, "name": title[:30], "item": f"https://www.aitoollab.cn/compare/{slug}/"}
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
        tool_link_parts.append(f'<a href="/tools/{s}/" style="display:inline-block;background:{c}22;color:{c};padding:6px 16px;border-radius:20px;text-decoration:none;font-size:14px;margin:4px;">{e} {n}详情</a>')
    tool_links = ''.join(tool_link_parts)

    # 内部链接：相关对比 + 相关替代方案
    related_compares_html = ''
    # 从所有已发布工具中找其他可能相关的对比组合（2026-08-13：只链接真实存在的对比页，消除 Bing 4xx 死链）
    _existing_cmp = set(existing_compare_slugs) if existing_compare_slugs is not None else None
    other_tools = [t for t in all_tools if t['slug'] not in compared_slugs][:5]
    if other_tools and compared_tools:
        extra_links = ''
        main_tool = compared_tools[0] if compared_tools else None
        for ot in other_tools[:4]:
            combo_slug = build_compare_slug_from_slugs([main_tool['slug'], ot['slug']])
            if _existing_cmp is not None and combo_slug not in _existing_cmp:
                continue
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
    <link rel="canonical" href="https://www.aitoollab.cn/compare/{slug}/">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(meta_desc)}">
    <meta property="og:url" content="https://www.aitoollab.cn/compare/{slug}/">
    <meta property="og:image" content="{og_image}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(title)} - AI工具宝箱">
    <meta name="twitter:description" content="{escape_html(meta_desc)}">
    <meta name="twitter:image" content="{og_image}">
    <style>{build.CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript>
    <script type="application/ld+json">{breadcrumb_json}</script>
    <script type="application/ld+json">{article_schema_json}</script>
    {faq_page_schema}
    {build.BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/compare/">工具对比</a> &gt; <span>{' vs '.join([t['name'] for t in compared_tools])}</span>
    </nav>

    <main class="article-container">
        <h1 style="text-align:center;font-size:30px;margin:8px 0 16px;color:#222;">{escape_html(title)}</h1>
        <div class="compare-header" style="display:flex;gap:16px;justify-content:center;flex-wrap:wrap;padding:24px;background:linear-gradient(135deg,#f8faff,#f0f4ff);border-radius:12px;margin-bottom:24px;">
            {compare_headers}
        </div>

        {verdict_html}

        <h2 id="overview" style="font-size:22px;color:#333;">{escape_html(subtitle) if subtitle else ''}</h2>

        <div style="margin:16px 0;display:flex;flex-wrap:wrap;gap:8px;">
            {tool_links}
        </div>

        <article class="article-body" data-tts>
            {content_html}
        </article>

        {faq_html}

        {related_compares_html}
    </main>

    <footer class="footer">
        <p>&copy; {build.BUILD_YEAR} AI工具宝箱 &middot; 每日精选优质AI工具 &middot; 最后更新 {today_iso} &middot; ''' + build.ICP_BEIAN + '''</p>
    </footer>
    ''' + build.BACK_TO_TOP_BLOCK + '''
</body>
</html>'''
    return html

def build_alternatives_page(alt_data, all_tools, all_articles=None):
    import build  # 延迟：build 完全加载后解析
    """
    生成替代方案页面 (Phase 3: 替代方案页)
    URL格式: /alternatives/{tool-slug}-alternatives/index.html
    覆盖关键词: "XX替代" / "XX类似工具" / "XX平替" / "代替XX"
    """
    slug = alt_data.get('slug', 'unknown')
    title = alt_data.get('title', 'AI工具替代方案')
    keywords = alt_data.get('keywords', [])
    content_md = alt_data.get('content', '')
    faq_list = alt_data.get('faq', [])
    target_slug = alt_data.get('target_tool', '')

    # 目标工具
    target_tool = next((t for t in all_tools if t['slug'] == target_slug), None)

    # Meta description（2026-08-06：兜底从「短句」升级为完整描述，消除 Bing 过短警告）
    _alt_name = target_tool.get('name', '') if target_tool else ''
    if _alt_name:
        _alt_fallback = (f"{_alt_name}替代方案大全 {build.BUILD_YEAR}：最好用的替代工具盘点，含免费平替、"
                         f"国产替代与同类工具对比，逐款给出价格、功能差异与真实实测点评，"
                         f"解决访问限制、价格过高、功能不足等常见问题，并附选型建议、避坑提示"
                         f"与上手成本说明，帮你快速选对最适合自己的替代工具。")
    else:
        _alt_fallback = (f"{title} {build.BUILD_YEAR}：最好用的替代工具盘点，含免费平替、国产替代与同类工具对比，"
                         f"逐款给出价格、功能差异与真实实测点评，并附选型建议与避坑提示，"
                         f"帮你解决访问限制与价格问题，找到最合适、最省钱的AI工具。")
    _alt_meta = alt_data.get('meta_description') or ''
    # 2026-08-13（阶段2.3）：门槛 100 → 115，避免 100~114 字的数据描述被 Bing 判过短
    meta_desc = _alt_meta if len(_alt_meta) >= 115 else _alt_fallback

    # FAQ
    faq_html = ''
    faq_schema = []
    for fi in faq_list:
        q, a = fi.get('question') or fi.get('q', ''), fi.get('answer') or fi.get('a', '')
        if q and a:
            faq_html += f'''<div class="faq-item"><div class="faq-q">{escape_html(q)}</div><div class="faq-a">{markdown_to_html(a)}</div></div>\n'''
            faq_schema.append({'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}})
    if faq_html:
        faq_html = f'<div class="faq-section" id="faq"><h3>❓ 常见问题</h3>{faq_html}</div>'

    faq_page_schema = ''
    if faq_schema:
        faq_sd = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_schema}
        faq_page_schema = f'<script type="application/ld+json">{json.dumps(faq_sd, ensure_ascii=False)}</script>'

    # OG Image（必须在 article_schema 之前计算）
    og_image = ensure_og_image(slug, data_obj=alt_data, is_article=True)

    from datetime import datetime as _dt2
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": meta_desc,
        "datePublished": alt_data.get("last_updated", _dt2.now().strftime('%Y-%m-%d')),
        "dateModified": alt_data.get("last_updated", _dt2.now().strftime('%Y-%m-%d')),
        "image": og_image,
        "author": {"@type": "Organization", "name": "AI工具宝箱编辑组", "url": "https://www.aitoollab.cn/author/"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱",
                      "logo": {"@type": "ImageObject", "url": "https://www.aitoollab.cn/images/logo.png"}}
    }
    article_schema_json = json.dumps(article_schema, ensure_ascii=False, indent=2)

    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoollab.cn/"},
            {"@type": "ListItem", "position": 2, "name": "替代方案", "item": "https://www.aitoollab.cn/alternatives/"},
            {"@type": "ListItem", "position": 3, "name": target_tool['name'] if target_tool else slug, "item": f"https://www.aitoollab.cn/alternatives/{slug}/"}
        ]
    }
    breadcrumb_json = json.dumps(breadcrumb, ensure_ascii=False, indent=2)

    # 目标工具卡片
    target_card_html = ''
    if target_tool:
            target_card_html = f'''<div id="target" style="background:#fff5e6;border:1px solid #ffd666;border-radius:10px;padding:20px;margin:20px 0;display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
            {tool_icon_html(target_tool, size='md')}
            <div><strong>寻找替代方案：</strong>{target_tool['name']}</div>
            <div style="color:#666;font-size:14px;">{target_tool.get('price','')}</div>
            <a href="/tools/{target_slug}/" style="margin-left:auto;color:#4285F4;text-decoration:none;font-size:14px;">查看原工具详情 →</a>
        </div>'''

    content_html = markdown_to_html(content_md)
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
    <link rel="canonical" href="https://www.aitoollab.cn/alternatives/{slug}/">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(meta_desc)}">
    <meta property="og:url" content="https://www.aitoollab.cn/alternatives/{slug}/">
    <meta property="og:image" content="{og_image}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(title)} - AI工具宝箱">
    <meta name="twitter:description" content="{escape_html(meta_desc)}">
    <meta name="twitter:image" content="{og_image}">
    <style>{build.CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript>
    <script type="application/ld+json">{breadcrumb_json}</script>
    <script type="application/ld+json">{article_schema_json}</script>
    {faq_page_schema}
    {build.BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/alternatives/">替代方案</a> &gt; <span>{target_tool['name'] if target_tool else slug}</span>
    </nav>

    <main class="article-container">
        <h1 style="text-align:center;font-size:30px;margin:8px 0 16px;color:#222;">{escape_html(title)}</h1>
        {target_card_html}

        <article class="article-body">
            {content_html}
        </article>

        {faq_html}
    </main>

    <footer class="footer">
        <p>&copy; {build.BUILD_YEAR} AI工具宝箱 &middot; 每日精选优质AI工具 &middot; 最后更新 {today_iso} &middot; ''' + build.ICP_BEIAN + '''</p>
    </footer>
    ''' + build.BACK_TO_TOP_BLOCK + '''
</body>
</html>'''
    return html

def build_compare_slug_from_slugs(slugs):
    """从slug列表构建对比页slug（供内部链接使用）"""
    return '-'.join(sorted(slugs))

def build_quiz_page(quiz_data, all_tools, all_articles=None):
    import build  # 延迟：build 完全加载后解析
    """
    生成 Quiz/工具选择器页面 (Phase 4)
    URL: /quiz/{slug}/index.html 或 /quiz/index.html (总入口)
    覆盖关键词: "AI工具选择器"、"哪个AI工具好"、"AI工具推荐测试"
    """
    slug = quiz_data.get('slug', 'unknown')
    title = quiz_data.get('title', 'AI工具选择器')
    keywords = quiz_data.get('keywords', [])
    questions = quiz_data.get('questions', [])
    content = quiz_data.get('content')  # AI生成的内容
    rec_tool_slugs = quiz_data.get('recommended_tools', [])
    category = quiz_data.get('category', 'all')
    is_main_entry = (quiz_data.get('target_url') == '/quiz/') or (slug == 'ai-tool-finder-2026')

    # Meta description（2026-08-06：短兜底升级为完整描述，消除 Bing 过短警告）
    _qz_meta = quiz_data.get('meta_description') or ''
    if len(_qz_meta) >= 115:
        meta_desc = _qz_meta
    else:
        _qz_cat = 'AI' if category == 'all' else category
        meta_desc = (f"{title}：通过{len(questions)}道场景化问答，结合功能需求、预算与使用习惯，"
                     f"快速定位最适合你的{_qz_cat}工具，附推荐工具清单、价格与真实实测点评，"
                     f"从免费额度、上手难度到核心能力多维度匹配，逐步缩小选择范围，"
                     f"最终给出首选与备选方案，帮你告别选择困难，一键找到合适的AI工具。")

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

    # 推荐工具卡片（基于答案匹配）——附带工具属性用于前端过滤
    rec_tools_html = ''
    # 构建工具属性 JSON 供前端匹配使用
    _tool_attr_map = {}
    if rec_tool_slugs:
        for rs in rec_tool_slugs[:12]:
            tool = next((t for t in all_tools if t['slug'] == rs), None)
            if not tool:
                continue
            _tags = [tag.get('text', '') if isinstance(tag, dict) else str(tag) for tag in tool.get('tags', [])]
            _tool_attr_map[tool['slug']] = {
                'name': tool['name'],
                'category': tool.get('category', ''),
                'price': tool.get('price', ''),
                'tags': _tags,
                'is_free': '免费' in tool.get('price', '') or tool.get('price', '') == '',
                'has_api': any('API' in str(f) for f in tool.get('features', [])),
                'platform': tool.get('platform', ''),
            }
            rec_tools_html += f'''            <div class="quiz-recommendation" data-tool-slug="{tool['slug']}" data-category="{tool.get('category','')}" data-is-free='{str(_tool_attr_map[tool['slug']]['is_free']).lower()}' data-tags='{json.dumps(_tags, ensure_ascii=False)}' style="display:none;">
                <a href="/tools/{tool['slug']}/" class="rec-card">
                    {tool_icon_html(tool, size='sm')}
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
            q, a = fi.get('question') or fi.get('q', ''), fi.get('answer') or fi.get('a', '')
            if q and a:
                faq_section += f'''<div class="faq-item"><div class="faq-q">{escape_html(q)}</div><div class="faq-a">{markdown_to_html(a)}</div></div>\n'''
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
            {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoollab.cn/"},
            {"@type": "ListItem", "position": 2, "name": "AI工具选择器", "item": "https://www.aitoollab.cn/quiz/"},
            {"@type": "ListItem", "position": 3, "name": title[:30], "item": f"https://www.aitoollab.cn/quiz/{'/' if is_main_entry else slug + '/'}"}
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
    <link rel="canonical" href="https://www.aitoollab.cn/quiz/{'/' if is_main_entry else slug + '/'}">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(meta_desc)}">
    <meta property="og:url" content="https://www.aitoollab.cn/quiz/{'/' if is_main_entry else slug + '/'}">
    <meta property="og:image" content="{og_image}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(title)} - AI工具宝箱">
    <meta name="twitter:description" content="{escape_html(meta_desc)}">
    <meta name="twitter:image" content="{og_image}">
    <style>{build.CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript>
    <script type="application/ld+json">{breadcrumb_json}</script>
    <script type="application/ld+json">{article_schema_json}</script>
    {faq_page_schema}
{build.BAIDU_TONGJI}
    <style>
    .quiz-container {{ max-width:800px;margin:0 auto; }}
    .quiz-progress {{ display:flex;justify-content:space-between;margin-bottom:24px;padding:12px;background:var(--surface-2,#f8f9fa);border-radius:10px; }}
    .quiz-progress .step {{ font-size:12px;color:var(--text-muted,#999); }}
    .quiz-progress .step.active {{ color:#4285F4;font-weight:700; }}
    .quiz-question {{ background:var(--surface,#fff);padding:24px;border-radius:12px;margin-bottom:16px;box-shadow:var(--shadow-sm,0 1px 4px rgba(0,0,0,0.08)); }}
    .quiz-question h3 {{ margin:0 0 16px;color:var(--text-main,#333); }}
    .quiz-options {{ display:flex;flex-direction:column;gap:10px; }}
    .quiz-option {{ display:block;padding:14px 18px;border:2px solid var(--border,#e8e8e8);border-radius:10px;cursor:pointer;transition:all 0.2s;font-size:15px;color:var(--text-main); }}
    .quiz-option:hover {{ border-color:#4285F4;background:rgba(66,133,244,0.08); }}
    .quiz-option input:checked + span, .quiz-option.selected {{ border-color:#4285F4;background:rgba(66,133,244,0.14); }}
    .quiz-option input {{ display:none; }}
    .quiz-result {{ text-align:center;padding:32px;display:none; }}
    .quiz-result h2 {{ color:#4285F4;margin-bottom:20px; }}
    .quiz-recommendation {{ margin:12px 0; }}
    .rec-card {{ display:flex;align-items:center;gap:16px;padding:16px;border:1px solid var(--border,#e8e8e8);border-radius:12px;text-decoration:none;color:inherit;transition:all 0.2s; }}
    .rec-card:hover {{ border-color:#4285F4;box-shadow:0 4px 12px rgba(66,133,244,0.15);transform:translateY(-1px); }}
    .rec-icon {{ width:48px;height:48px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px;flex-shrink:0; }}
    .rec-info {{ flex:1; }}
    .rec-info strong {{ display:block;font-size:16px; }}
    .rec-info span {{ color:var(--text-muted,#666);font-size:13px; }}
    .rec-info p {{ margin:4px 0 0;color:var(--text-muted,#888);font-size:13px; }}
    .rec-arrow {{ color:#4285F4;font-size:14px;flex-shrink:0; }}
    .btn-quiz-submit {{ display:block;width:100%;padding:16px;background:linear-gradient(135deg,#4285F4,#5b9aff);color:#fff;border:none;border-radius:12px;font-size:18px;font-weight:700;cursor:pointer;margin-top:16px;transition:opacity 0.2s; }}
    .btn-quiz-submit:hover {{ opacity:0.9; }}
    .quiz-intro {{ background:var(--surface-2,#f0f7ff);padding:20px;border-radius:10px;margin-bottom:24px;border-left:4px solid #4285F4; }}
    .quiz-conclusion {{ background:var(--surface-2,#f8f9fa);padding:20px;border-radius:10px;margin-top:24px; }}
    .tool-rec-detail {{ margin:20px 0;padding:20px;background:var(--surface,#fff);border-radius:10px;border:1px solid var(--border,#eee); }}
    .tool-rec-detail h3 {{ color:var(--text-main,#333);margin-top:0; }}
    [data-theme="dark"] .quiz-intro {{ background:var(--surface-2) !important; }}
    [data-theme="dark"] .quiz-progress, [data-theme="dark"] .quiz-question,
    [data-theme="dark"] .quiz-conclusion, [data-theme="dark"] .tool-rec-detail {{ background:var(--surface) !important; }}
    [data-theme="dark"] .quiz-option {{ border-color:var(--border) !important; }}
    [data-theme="dark"] .quiz-option:hover, [data-theme="dark"] .quiz-option.selected,
    [data-theme="dark"] .quiz-option input:checked + span {{ background:rgba(66,133,244,0.14) !important;border-color:#4285F4 !important; }}
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
            <a href="/" style="text-decoration:none;"><div class="site-logo">AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
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
        <p>&copy; {build.BUILD_YEAR} AI工具宝箱 &middot; 每日精选优质AI工具 &middot; 最后更新 {today_iso} &middot; ''' + build.ICP_BEIAN + '''</p>
    </footer>
''' + build.BACK_TO_TOP_BLOCK + '''
<script>
// Quiz 交互逻辑 v2 — 支持取消选择 + 智能匹配推荐
(function(){
    // 点击选项：支持选中/取消
    document.querySelectorAll('.quiz-option').forEach(function(opt){
        opt.addEventListener('click', function(e){
            // 阻止 label 默认行为，手动控制 radio
            e.preventDefault();
            var radio = this.querySelector('input[type="radio"]');
            var name = radio.name;
            // 如果已选中，则取消；否则选中
            if (this.classList.contains('selected')) {
                this.classList.remove('selected');
                radio.checked = false;
            } else {
                document.querySelectorAll('.quiz-option input[name="'+name+'"]').forEach(function(o){
                    o.closest('.quiz-option').classList.remove('selected');
                    o.checked = false;
                });
                this.classList.add('selected');
                radio.checked = true;
            }
            updateProgress();
        });
    });

    // 更新进度条高亮
    function updateProgress(){
        var answered = document.querySelectorAll('.quiz-option.selected').length;
        var total = document.querySelectorAll('.quiz-question').length;
        document.querySelectorAll('.quiz-progress .step').forEach(function(s,i){
            s.classList.toggle('active', i < answered);
        });
    }

    // 答案 → 工具匹配规则
    var ANSWER_MATCH_RULES = {
        q1: function(v, tool){
            var cat = tool.getAttribute('data-category') || '';
            var tags = JSON.parse(tool.getAttribute('data-tags') || '[]');
            var map = {
                'chat':   ['AI对话','AI搜索','AI效率'],
                'writing':['AI写作','AI办公'],
                'image':  ['AI绘画','AI设计'],
                'code':   ['AI编程','AI自动化']
            };
            var match = map[v] || [];
            return match.indexOf(cat) !== -1 || match.some(function(t){ return tags.indexOf(t) !== -1; });
        },
        q2: function(v, tool){
            if(v === 'free') return tool.getAttribute('data-is-free') === 'true';
            if(v === 'any') return true;
            if(v === 'low'){
                var p = (tool.getAttribute('data-tags')||'[]');
                return p.indexOf('免费增值') !== -1 || p.indexOf('免费可用') !== -1;
            }
            return true;
        },
        q3: function(v, tool){
            if(v === 'cn'){
                var tags = JSON.parse(tool.getAttribute('data-tags') || '[]');
                return tags.indexOf('国内可用') !== -1 || tags.indexOf('国产') !== -1;
            }
            return true;
        },
        q4: function(v, tool){
            return true; // 用户类型不硬过滤，只影响排序
        },
        q5: function(v, tool){
            return true; // 看重什么不硬过滤，只影响排序
        }
    };

    // 答案 → 排序加分（软匹配）
    function computeScore(answers, tool){
        var score = 0;
        if(answers.q1){
            var cat = tool.getAttribute('data-category') || '';
            var tags = JSON.parse(tool.getAttribute('data-tags') || '[]');
            var map = {'chat':['AI对话'],'writing':['AI写作'],'image':['AI绘画','AI设计'],'code':['AI编程']};
            var m = map[answers.q1] || [];
            if(m.indexOf(cat) !== -1) score += 10;
            if(m.some(function(t){ return tags.indexOf(t) !== -1; })) score += 5;
        }
        if(answers.q2 === 'free' && tool.getAttribute('data-is-free') === 'true') score += 8;
        if(answers.q2 === 'any') score += 3;
        if(answers.q4 === 'pro' || answers.q4 === 'power') score += 3;
        return score;
    }

    window.showQuizResult = function(){
        var answers = {};
        document.querySelectorAll('.quiz-option input:checked').forEach(function(el){
            answers[el.name] = el.value;
        });
        var totalQ = ''' + str(len(questions)) + ''';
        if(Object.keys(answers).length < totalQ){
            alert('请回答完所有问题后再查看推荐！（或点击已选选项可取消选择）');
            return;
        }

        document.getElementById('quizForm').style.display = 'none';
        var resultDiv = document.getElementById('quizResult');
        resultDiv.style.display = 'block';

        // 智能匹配：根据答案过滤+排序推荐工具
        var cards = resultDiv.querySelectorAll('.quiz-recommendation');
        var scored = [];
        cards.forEach(function(el){
            var matchCount = 0;
            var slug = el.getAttribute('data-tool-slug');
            for(var qid in answers){
                var ruleFn = ANSWER_MATCH_RULES[qid];
                if(ruleFn && ruleFn(answers[qid], el)){
                    matchCount++;
                }
            }
            var sortScore = computeScore(answers, el);
            scored.push({el: el, match: matchCount, sortScore: sortScore});
        });

        // 按匹配数降序 → 排序分降序
        scored.sort(function(a,b){
            if(b.match !== a.match) return b.match - a.match;
            return b.sortScore - a.sortScore;
        });

        // 显示匹配度最高的前6个，其余隐藏
        scored.forEach(function(item, i){
            if(i < 6 && item.match > 0){
                item.el.style.display = 'block';
                item.el.style.order = i;
            } else {
                item.el.style.display = 'none';
            }
        });

        // 如果没有任何匹配（理论不该发生），显示全部
        var visible = resultDiv.querySelectorAll('.quiz-recommendation[style*="display: block"], .quiz-recommendation[style*="display:block"]');
        if(visible.length === 0){
            scored.forEach(function(item){ item.el.style.display = 'block'; });
        }

        // 更新进度条
        document.querySelectorAll('.quiz-progress .step').forEach(function(s){ s.classList.add('active'); });

        window.scrollTo({top: resultDiv.offsetTop - 20, behavior:'smooth'});
    };

    window.resetQuiz = function(){
        document.getElementById('quizResult').style.display = 'none';
        document.getElementById('quizForm').style.display = 'block';
        document.querySelectorAll('.quiz-option input').forEach(function(el){ el.checked = false; });
        document.querySelectorAll('.quiz-option').forEach(function(el){ el.classList.remove('selected'); });
        document.querySelectorAll('.quiz-recommendation').forEach(function(el){ el.style.display = 'none'; el.style.order = ''; });
        updateProgress();
        window.scrollTo({top:0, behavior:'smooth'});
    };
})();
</script>
</body>
</html>'''
    return html

def _build_ranking_index_page(all_rankings):
    import build  # 延迟：build 完全加载后解析
    """生成 ranking/index.html 总入口页：列出所有排行榜链接（2026-08-13：移除 Meta Refresh，改为真实栏目页）"""
    items_html = ''
    for rd in all_rankings:
        rslug = rd.get('slug', '')
        title = rd.get('title', rslug)
        icon = rd.get('icon', '📊')
        category = rd.get('category', '')
        if not rslug:
            continue
        # 短标题（去掉年份前缀等）
        short_title = title.replace('2026年', '').replace('2026', '').strip()
        cat_tag = f'<span style="font-size:11px;color:#888;">{category}</span>' if category else ''
        items_html += f'''    <li>
      <a href="/ranking/{rslug}/" style="display:flex;align-items:center;gap:10px;padding:12px 16px;border-radius:10px;text-decoration:none;color:inherit;transition:background .2s;">
        <span style="font-size:22px;">{icon}</span>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:600;font-size:15px;">{escape_html(short_title)}</div>
          {cat_tag}
        </div>
        <span style="color:#aaa;font-size:18px;">→</span>
      </a>
    </li>\n'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI工具排行榜 - 全部榜单 - AI工具宝箱</title>
    <meta name="description" content="AI工具宝箱全部排行榜：综合热度榜、免费工具榜、性价比榜、分类排行等19个分类与主题榜单，覆盖AI对话、写作、绘画、编程、视频、办公等全领域，均基于热度与实测数据综合评分并每日更新，附价格、免费额度与上榜理由，帮你快速选出最值得用的AI工具。">
    <link rel="canonical" href="https://www.aitoollab.cn/ranking/">
    <style>{build.CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript>
{build.BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">&#x1F6E0; AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <section style="max-width:720px;margin:40px auto;padding:0 24px;">
        <h1 style="font-size:28px;font-weight:800;margin-bottom:8px;">📊 AI工具排行榜</h1>
        <p style="color:var(--text-muted);margin-bottom:24px;font-size:15px;">
            共 <strong>{len(all_rankings)}</strong> 个榜单 · 覆盖AI全领域 · 每日更新
        </p>
        <ul style="list-style:none;padding:0;display:flex;flex-direction:column;gap:4px;background:var(--surface);border-radius:16px;overflow:hidden;box-shadow:var(--shadow-sm);border:1px solid var(--border-light);">
{items_html}        </ul>
        <p style="text-align:center;margin-top:20px;">
            <a href="/" style="color:var(--primary-color);font-size:14px;text-decoration:none;">← 返回首页</a>
        </p>
    </section>
</body>
</html>'''
    return html

def _build_compare_index_page(all_compares):
    import build  # 延迟：build 完全加载后解析
    """生成 compare/index.html 总入口页：列出所有对比评测链接"""
    items_html = ''
    for cp in (all_compares or []):
        cslug = cp.get('slug', '')
        title = cp.get('title', cslug)
        if not cslug:
            continue
        items_html += f'''    <li>
      <a href="/compare/{cslug}/" style="display:flex;align-items:center;gap:10px;padding:12px 16px;border-radius:10px;text-decoration:none;color:inherit;transition:background .2s;">
        <span style="font-size:22px;">⚖️</span>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:600;font-size:15px;">{escape_html(title)}</div>
        </div>
        <span style="color:#aaa;font-size:18px;">→</span>
      </a>
    </li>\n'''
    if not items_html:
        items_html = '<li style="padding:24px;text-align:center;color:#999;">暂无对比评测内容</li>'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI工具对比评测 - 全部对比 - AI工具宝箱</title>
    <meta name="description" content="AI工具宝箱全部对比评测：ChatGPT vs Claude、Midjourney vs Flux 等40+组深度对比，从功能、价格、优缺点到适用场景逐项拆解，并给出按预算和场景的选型结论，基于真实使用数据，帮你快速选出最适合自己的AI工具。">
    <link rel="canonical" href="https://www.aitoollab.cn/compare/">
    <style>{build.CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript>
{build.BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">&#x1F6E0; AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <section style="max-width:720px;margin:40px auto;padding:0 24px;">
        <h1 style="font-size:28px;font-weight:800;margin-bottom:8px;">⚖️ AI工具对比评测</h1>
        <p style="color:var(--text-muted);margin-bottom:24px;font-size:15px;">
            共 <strong>{len(all_compares or [])}</strong> 篇深度对比 · 帮你选对AI工具
        </p>
        <ul style="list-style:none;padding:0;display:flex;flex-direction:column;gap:4px;background:var(--surface);border-radius:16px;overflow:hidden;box-shadow:var(--shadow-sm);border:1px solid var(--border-light);">
{items_html}        </ul>
        <p style="text-align:center;margin-top:20px;">
            <a href="/" style="color:var(--primary-color);font-size:14px;text-decoration:none;">← 返回首页</a>
        </p>
    </section>
</body>
</html>'''
    return html

def _build_alternatives_index_page(all_alternatives):
    import build  # 延迟：build 完全加载后解析
    """生成 alternatives/index.html 总入口页：列出所有替代方案链接"""
    items_html = ''
    for alt in (all_alternatives or []):
        aslug = alt.get('slug', '')
        title = alt.get('title', aslug)
        if not aslug:
            continue
        items_html += f'''    <li>
      <a href="/alternatives/{aslug}/" style="display:flex;align-items:center;gap:10px;padding:12px 16px;border-radius:10px;text-decoration:none;color:inherit;transition:background .2s;">
        <span style="font-size:22px;">🔄</span>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:600;font-size:15px;">{escape_html(title)}</div>
        </div>
        <span style="color:#aaa;font-size:18px;">→</span>
      </a>
    </li>\n'''
    if not items_html:
        items_html = '<li style="padding:24px;text-align:center;color:#999;">暂无替代方案内容</li>'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI工具替代方案推荐 - 全部替代方案 - AI工具宝箱</title>
    <meta name="description" content="AI工具宝箱全部替代方案推荐：寻找ChatGPT、Midjourney、Cursor等热门AI工具的最佳平替，含免费方案、国产替代与同类工具对比，附真实实测点评与选型建议，帮你解决访问限制、价格过高与功能不足等问题，数据每日更新、内容可溯源。">
    <link rel="canonical" href="https://www.aitoollab.cn/alternatives/">
    <style>{build.CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript>
{build.BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">&#x1F6E0; AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <section style="max-width:720px;margin:40px auto;padding:0 24px;">
        <h1 style="font-size:28px;font-weight:800;margin-bottom:8px;">🔄 AI工具替代方案</h1>
        <p style="color:var(--text-muted);margin-bottom:24px;font-size:15px;">
            共 <strong>{len(all_alternatives or [])}</strong> 个替代方案 · 找到最适合你的AI工具
        </p>
        <ul style="list-style:none;padding:0;display:flex;flex-direction:column;gap:4px;background:var(--surface);border-radius:16px;overflow:hidden;box-shadow:var(--shadow-sm);border:1px solid var(--border-light);">
{items_html}        </ul>
        <p style="text-align:center;margin-top:20px;">
            <a href="/" style="color:var(--primary-color);font-size:14px;text-decoration:none;">← 返回首页</a>
        </p>
    </section>
</body>
</html>'''
    return html
