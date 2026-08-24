# render_ranking.py — 排行页
# 模块8：从 build.py 拆分（2026-08-24）
import os
import re
import random

from build_lib.html_utils import (
    escape_html, markdown_to_html,
)
from build_lib.data_loaders import (
    load_ranking_data, get_category_slug,
)
from build_lib.render_tool import (
    make_tool_card_html, build_tool_page, tool_icon_html,
)


def build_ranking_page(ranking_data, all_tools, all_articles=None):
    import build  # 延迟：build 完全加载后解析
    """
    生成排名页面 (Phase 5)
    URL: /ranking/{slug}/index.html 或 /ranking/index.html (总榜入口)
    覆盖关键词: "AI工具排行榜"、"AI工具排名2026"、"热门AI工具"
    """
    slug = ranking_data.get('slug', 'unknown')
    title = ranking_data.get('title', 'AI工具排行榜')
    keywords = ranking_data.get('keywords', [])
    ranked_tools = ranking_data.get('ranked_tools', [])[:20]  # 展示前20
    # 2026-08-13（Bing 4xx 修复）：只展示已发布工具，避免排行页指向未发布工具的死链
    _rk_published = get_published_tool_slugs()
    ranked_tools = [t for t in ranked_tools if t.get('slug') in _rk_published]
    total_tools = ranking_data.get('total_tools', len(ranked_tools))
    content = ranking_data.get('content') or {}  # AI分析内容（None时用空字典）
    rtype = ranking_data.get('type', 'special')
    category = ranking_data.get('category', '')
    icon = ranking_data.get('icon', '📊')
    methodology = ranking_data.get('methodology', {})
    last_updated = ranking_data.get('last_updated', '')

    is_overall = (slug == '2026-ai-tools-overall-ranking')

    # Meta description（2026-08-06：短兜底升级为完整描述，消除 Bing 过短警告）
    _rk_meta = ranking_data.get('meta_description') or ''
    if len(_rk_meta) >= 115:
        meta_desc = _rk_meta
    else:
        _rk_cat = category or 'AI'
        _rk_name = _rk_cat.replace('AI', '', 1) if _rk_cat.startswith('AI') else _rk_cat
        meta_desc = (f"{title}：{build.BUILD_YEAR}年最新{_rk_cat}工具排行，基于热度与实测数据综合评分，"
                     f"收录{total_tools}款工具，逐款给出价格、免费额度、功能亮点与上榜理由，"
                     f"覆盖主流及国产AI工具，每日更新、数据可溯源，帮你快速选出最值得用的"
                     f"{_rk_name}AI工具，避开踩坑。")

    # v6.5: 预计算有实测评测的工具 slug 集合（用于上榜理由）
    _reviewed_slugs = set()
    if all_articles:
        for _a in all_articles:
            _rel = _a.get('related_tools') or []
            if isinstance(_rel, list):
                for _r in _rel:
                    if isinstance(_r, str):
                        _reviewed_slugs.add(_r)

    def _rank_reason(item):
        """从真实数据生成一句话上榜理由"""
        parts = []
        _v = str(item.get('visits') or '').strip()
        if _v:
            parts.append('月访问 ' + _v)
        _r = str(item.get('rating') or '').strip().replace('⭐', '').strip()
        if _r:
            parts.append('评分 ' + _r)
        _p = str(item.get('price') or '').strip()
        if '免费' in _p:
            parts.append('免费可用')
        elif _p:
            parts.append(_p[:18])
        if item.get('slug') in _reviewed_slugs:
            parts.append('有实测评测')
        return ' · '.join(parts[:3]) or '编辑收录'

    # 排名表格
    table_rows = ''
    medals = ['\U0001F947', '\U0001F948', '\U0001F949']  # 金银铜
    top3_html = ''
    # P0/UX（2026-08-09）：排行页统一用真实工具 LOGO（assets/icons），无图标才回退 emoji 色块
    def _rank_icon(item, size=40):
        slug = item.get('slug', '')
        _, web_path = resolve_icon(slug)
        if web_path:
            return (f'<img src="{web_path}" alt="{escape_html(item.get("name", ""))}" loading="lazy" '
                    f'width="{size}" height="{size}" '
                    f'style="width:{size}px;height:{size}px;border-radius:10px;object-fit:contain;'
                    f'background:#fff;padding:3px;border:1px solid var(--border-light);flex:none;">')
        return (f'<span style="font-size:{int(size * 0.55)}px;background:{item.get("color", "#667eea")};'
                f'width:{size}px;height:{size}px;border-radius:10px;display:inline-flex;'
                f'align-items:center;justify-content:center;flex:none;">{item.get("emoji", "🔧")}</span>')

    for i, item in enumerate(ranked_tools[:3]):
        top3_html += f'<a class="rank-top3-card" href="/tools/{item["slug"]}/">'
        top3_html += '<span class="rt3-medal">' + medals[i] + '</span>'
        top3_html += '<span class="rt3-icon">' + _rank_icon(item, 52) + '</span>'
        top3_html += '<span class="rt3-body"><span class="rt3-name">' + escape_html(item.get('name', '')) + '</span>'
        top3_html += '<span class="rt3-reason">' + escape_html(_rank_reason(item)) + '</span></span></a>'
    if top3_html:
        top3_html = '<div class="rank-top3">' + top3_html + '</div>'
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
                        <a href="/tools/{item['slug']}/" style="display:flex;align-items:center;gap:10px;text-decoration:none;color:inherit;">
                            {_rank_icon(item, 40)}
                            <span style="font-weight:600;">{escape_html(tool_name)}</span> {badge_html}
                        </a>
                    </td>
                    <td class="rank-reason">{_rank_reason(item)}</td>
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
            q, a = fi.get('question') or fi.get('q', ''), fi.get('answer') or fi.get('a', '')
            if q and a:
                faq_section += f'<div class="faq-item"><div class="faq-q">{escape_html(q)}</div><div class="faq-a">{markdown_to_html(a)}</div></div>\n'
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

    # ItemList Schema：把排名工具列表结构化，GEO 价值最高
    # AI 搜索引擎可直接引用"第1名是XX，第2名是XX"
    _item_list_elements = []
    for _i, _it in enumerate(ranked_tools[:20], 1):
        _item_list_elements.append({
            "@type": "ListItem",
            "position": _i,
            "name": _it.get('name', ''),
            "url": f"https://www.aitoollab.cn/tools/{_it.get('slug', '')}/",
        })
    if _item_list_elements:
        _item_list_schema = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": title,
            "description": meta_desc,
            "numberOfItems": len(_item_list_elements),
            "itemListElement": _item_list_elements
        }
        item_list_schema_json = json.dumps(_item_list_schema, ensure_ascii=False, indent=2)
    else:
        item_list_schema_json = ''

    # Breadcrumb
    bc_name_2 = "AI工具排行榜" if is_overall else (category + "排行榜" if category else "排行榜")
    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoollab.cn/"},
            {"@type": "ListItem", "position": 2, "name": "AI工具排行", "item": "https://www.aitoollab.cn/ranking/"},
            {"@type": "ListItem", "position": 3, "name": title[:30], "item": f"https://www.aitoollab.cn/ranking/{slug}/"}
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
    <link rel="canonical" href="https://www.aitoollab.cn/ranking/{slug}/">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(meta_desc)}">
    <meta property="og:url" content="https://www.aitoollab.cn/ranking/{slug}/">
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
    <script type="application/ld+json">{item_list_schema_json}</script>
    {faq_ps}
{build.BAIDU_TONGJI}
    <style>
    .ranking-container {{ max-width:1200px; }}
    .ranking-hero {{ display:flex;align-items:center;gap:14px;text-align:left;padding:16px 20px;background:linear-gradient(135deg,#f0f4ff,#e8f0fe);border-radius:14px;margin-bottom:16px; }}
    .ranking-hero .hero-icon {{ font-size:32px;margin:0;flex:none;width:52px;height:52px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.72);border-radius:14px; }}
    .ranking-hero .hero-text {{ flex:1;min-width:0; }}
    .ranking-hero h1 {{ margin:0;font-size:22px; }}
    .ranking-hero p {{ color:#666;margin:3px 0 0;font-size:13.5px;line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden; }}
    .ranking-hero .live-badge {{ margin-top:0;margin-left:auto;flex:none; }}
    @media (max-width:640px) {{ .ranking-hero {{ flex-wrap:wrap;padding:14px;gap:10px; }} .ranking-hero h1 {{ font-size:19px; }} .ranking-hero .hero-icon {{ width:42px;height:42px;font-size:26px; }} .ranking-hero .live-badge {{ margin-left:0; }} }}
    .live-badge {{ display:inline-block;background:#00c853;color:#fff;font-size:12px;padding:3px 12px;border-radius:12px;margin-top:10px;font-weight:600;animation:pulse 2s infinite; }}
    @keyframes pulse {{ 0%{{opacity:1}} 50%{{opacity:.7}} 100%{{opacity:1}} }}
    .ranking-table-wrap {{ overflow-x:auto;background:var(--surface,#fff);border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:28px; }}
    .ranking-table {{ width:100%;border-collapse:collapse;min-width:600px; }}
    .ranking-table th {{ background:var(--surface-2,#f8f9fa);padding:14px 12px;text-align:left;font-size:13px;color:var(--text-muted,#666);border-bottom:2px solid var(--border,#eee);white-space:nowrap; }}
    .ranking-table td {{ padding:12px;border-bottom:1px solid var(--border-light,#f0f0f0);vertical-align:middle; }}
    .rank-row:hover {{ background:var(--surface-2,#f8f9ff); }}
    .rank-num {{ font-size:20px;text-align:center;width:50px;font-weight:700; }}
    .rank-tool a {{ font-weight:600; }}
    .rank-tool a > span {{ max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }}
    .rank-score {{ min-width:120px; }}
    .score-bar {{ width:80px;height:6px;background:#eee;border-radius:3px;display:inline-block;vertical-align:middle;overflow:hidden; }}
    .score-fill {{ height:100%;border-radius:3px;transition:width .5s; }}
    .score-val {{ font-weight:700;font-size:14px;margin-left:6px; }}
    .rank-rating {{ white-space:nowrap; }}
    .rank-price {{ color:#666;font-size:13px;white-space:nowrap;max-width:240px;overflow:hidden;text-overflow:ellipsis; }}
    .rank-trend {{ text-align:center;font-size:16px; }}
    .rank-sub-nav {{ display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;justify-content:center; }}
    .rank-sub-link {{ display:inline-block;padding:8px 16px;background:#f0f4ff;color:#4285F4;border-radius:20px;text-decoration:none;font-size:13px;font-weight:600;transition:all .2s; }}
    .rank-sub-link:hover {{ background:#4285F4;color:#fff; }}
    .rank-reason {{ font-size:12px;color:var(--text-muted,#888);max-width:230px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }}
    .rank-top3 {{ display:flex;gap:12px;margin-bottom:16px; }}
    .rank-top3-card {{ flex:1;display:flex;align-items:center;gap:10px;padding:12px 14px;background:var(--surface,#fff);border:1px solid var(--border,#eee);border-radius:12px;text-decoration:none;color:inherit;transition:box-shadow .15s,transform .15s;min-width:0; }}
    .rank-top3-card:hover {{ box-shadow:0 6px 18px rgba(0,0,0,.08);transform:translateY(-2px); }}
    .rt3-medal {{ font-size:22px;flex:none; }}
    .rt3-icon {{ width:40px;height:40px;border-radius:10px;display:inline-flex;align-items:center;justify-content:center;font-size:20px;flex:none; }}
    .rt3-body {{ min-width:0;display:flex;flex-direction:column; }}
    .rt3-name {{ font-size:14px;font-weight:700;color:var(--text-main,#333); }}
    .rt3-reason {{ font-size:12px;color:var(--text-muted,#888);overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }}
    @media (max-width:768px) {{ .rank-top3 {{ flex-direction:column;gap:8px; }} .ranking-table-wrap {{ overflow:hidden;background:transparent;box-shadow:none;border-radius:0;margin-bottom:20px; }} .ranking-table {{ width:100%;min-width:0; }} .ranking-table thead {{ display:none; }} .ranking-table tbody {{ display:flex;flex-direction:column;gap:8px; }} .ranking-table tbody, .ranking-table tr, .ranking-table td {{ display:block; }} .ranking-table tr.rank-row {{ display:grid;grid-template-columns:30px minmax(0,1fr) auto;gap:2px 10px;align-items:center;background:#fff;border:1px solid #eee;border-radius:12px;padding:10px 12px; }} .ranking-table tr.rank-row > td {{ min-width:0;padding:0; }} .rank-num {{ grid-row:1/3;grid-column:1;width:auto;font-size:16px;font-weight:700;text-align:center; }} .rank-tool {{ grid-row:1;grid-column:2; }} .rank-tool .badge {{ display:none; }} .rank-tool a {{ gap:8px;font-size:13.5px;min-width:0; }} .rank-tool a > span {{ max-width:100%;white-space:normal;overflow:hidden; }} .rank-score {{ grid-row:1;grid-column:3;display:flex;align-items:center;gap:6px;min-width:0; }} .score-bar {{ width:56px; }} .score-val {{ display:inline;font-size:13px;font-weight:700;margin-left:0; }} .rank-rating {{ grid-row:2;grid-column:3;font-size:12px;color:#888;white-space:nowrap; }} .rank-price {{ grid-row:2;grid-column:2;max-width:none;white-space:normal;font-size:12px;line-height:1.35;overflow-wrap:anywhere; }} .ranking-table td.rank-reason, .ranking-table td.rank-trend {{ display:none; }} }}
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
            <a href="/" style="text-decoration:none;"><div class="site-logo">AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href/">首页</a> &gt; <a href="/ranking/">AI工具排行</a> &gt; <span>{title[:25]}...</span>
    </nav>

    <main class="article-container ranking-container">
        <div class="ranking-hero">
            <div class="hero-icon">{icon}</div>
            <div class="hero-text">
                <h1>{escape_html(title)}</h1>
                <p>{escape_html(meta_desc[:120])}</p>
            </div>
            {trend_badge}
        </div>

        <div class="rank-sub-nav">
            {related_links}
        </div>

        {top3_html}

        <div class="ranking-table-wrap">
            <table class="ranking-table">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>工具名称</th>
                        <th>上榜理由</th>
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

        <section class="ranking-analysis" style="margin:32px 0 24px;padding:24px;background:var(--surface-2,#f8fafc);border-radius:12px;">
            <h2 style="font-size:20px;font-weight:700;margin-bottom:16px;">📊 {title}深度解读</h2>
            <p style="line-height:1.8;color:var(--text-muted,#475569);margin-bottom:14px;">本榜单收录了{total_tools}款主流AI工具，综合评分基于热度、质量、功能、价值和新鲜度五大维度。榜单每日自动更新，确保数据时效性。排名前列的工具在用户访问量、功能完整度和性价比方面表现突出，是当前AI工具市场的头部产品。</p>
            <p style="line-height:1.8;color:var(--text-muted,#475569);margin-bottom:14px;">从榜单趋势来看，AI对话和AI编程类工具持续领跑，免费和免费增值模式的工具占据多数席位。国产AI工具（如DeepSeek、Kimi、豆包）在中文场景下表现优秀，与国际工具形成有力竞争。建议用户根据具体使用场景和预算选择，多数工具提供免费版可供试用。</p>
            <p style="line-height:1.8;color:var(--text-muted,#475569);">如需更精准的推荐，可使用我们的<a href="/quiz/" style="color:#4285F4;">AI工具选择器</a>，3分钟找到最适合你的AI助手。也可查看<a href="/category/" style="color:#4285F4;">全部分类</a>浏览特定领域的工具。</p>
        </section>

        <div class="methodology-note">
            <strong>排名说明：</strong>本排名基于多维度数据综合计算（热度30% + 质量25% + 功能20% + 价格15% + 新鲜度10%），每日自动更新。数据来源于工具官方信息、用户评价聚合和市场活跃度指标。排名仅供参考，具体选择请根据个人需求和实际体验决定。
        </div>
    </main>

    <footer class="footer">
        <p>&copy; {build.BUILD_YEAR} AI工具宝箱 &middot; 每日精选优质AI工具 &middot; 更新于 {(last_updated or _rdt.now().strftime('%Y-%m-%d %H:%M'))} &middot; ''' + build.ICP_BEIAN + '''</p>
    </footer>
''' + build.BACK_TO_TOP_BLOCK + '''
 </body>
</html>'''
    return html
