# render_index.py — 首页 + 工具总索引页
# 模块11：从 build.py 拆分（2026-08-24）
import os
import re
import json
import subprocess
import sys
import time
from datetime import datetime

from build_lib.html_utils import (escape_html, markdown_to_html, _collapse_blank_lines)
from build_lib.data_loaders import (load_tools, load_articles, get_category_slug, _load_dict_terms)
from build_lib.render_category import (get_subcat_def,)
from build_lib.render_tool import (make_tool_card_html, build_tool_page, ensure_og_image,
                                  get_category_stats, get_price_info, get_category_color_var,
                                  resolve_icon, tool_icon_html, extract_rating_num)
from build_lib.render_article import (replace_between_tags,)


def build_tools_index_page(tools):
    import build  # 延迟：build 完全加载后解析
    """生成 /tools/ 全部AI工具大全页（SEO+GEO：全量静态内链 + ItemList/FAQ/speakable 结构化数据）。"""
    from datetime import datetime
    today_iso = datetime.now().strftime('%Y-%m-%d')
    site = 'https://www.aitoollab.cn'
    n = len(tools)

    # 分类顺序与首页 CATEGORY_ORDER 保持一致，缺失分类排后面
    cat_order = ['AI对话', 'AI写作', 'AI绘画', 'AI编程', 'AI视频', 'AI音频', 'AI办公', 'AI设计',
                 'AI搜索', 'AI翻译', 'AI自动化', 'AI效率', 'AI智能体', 'AI开发', 'AI行业应用',
                 'AI学习', 'AI检测', 'AI提示词']
    by_cat = {}
    for t in tools:
        by_cat.setdefault(t.get('category') or '其他', []).append(t)
    ordered = [c for c in cat_order if c in by_cat] + [c for c in by_cat if c not in cat_order]
    free_n = sum(1 for t in tools if get_price_info(t)[0] == 'free')
    top_cats = '、'.join(ordered[:6])

    _title = f'全部AI工具大全（{n}款）- 免费AI工具导航 | AI工具宝箱'
    _meta_desc = (f'AI工具宝箱收录全部 {n} 款 AI 工具（{build.BUILD_YEAR}年每日更新），覆盖 AI对话、AI编程、'
                  f'AI视频、AI绘画、AI办公等 {len(ordered)} 大分类，{free_n} 款免费可用，'
                  f'含评分、价格、访问热度与实测评测，助你快速找到合适的 AI 工具。')
    _keywords = (f'AI工具大全,全部AI工具,免费AI工具,AI工具导航,AI工具合集,'
                 f'AI工具列表,AI软件大全,{build.BUILD_YEAR}')

    # ── 2026 热门工具（综合榜 × 人气飙升榜，slug 缺失自动跳过）──
    hot_slugs = ['deepseek', 'chatgpt', 'kimi', 'qwen-chat', 'doubao', 'jimeng-ai',
                 'kling-ai', 'trae', 'glm-5-2', 'tongyi-wanxiang', 'hailuo-ai',
                 'gemini-deep-research-agent']
    _slug_map = {t.get('slug'): t for t in tools}
    hot_tools = [t for s in hot_slugs if (t := _slug_map.get(s))]

    # ── 分类一句话描述（含长尾变体）──
    cat_intros = {
        'AI对话': 'AI对话 · 聊天机器人 · 对话助手',
        'AI写作': 'AI写作 · 文案生成 · 写作助手',
        'AI绘画': 'AI绘画 · AI画图 · 文生图',
        'AI编程': 'AI编程 · AI写代码 · 编程助手',
        'AI视频': 'AI视频生成 · 文生视频 · 数字人',
        'AI音频': 'AI配音 · 语音合成 · 音乐生成',
        'AI办公': 'AI办公 · AI做PPT · 会议纪要',
        'AI设计': 'AI设计 · AI Logo · 图像处理',
        'AI搜索': 'AI搜索 · 对话式搜索 · 知识问答',
        'AI翻译': 'AI翻译 · 实时翻译 · 文档翻译',
        'AI自动化': 'AI工作流 · RPA · 自动化',
        'AI效率': 'AI效率 · 生产力 · 提效工具',
        'AI智能体': 'AI智能体 · Agent · 智能体平台',
        'AI开发': 'AI开发 · 大模型API · 开发者工具',
        'AI行业应用': '行业AI · 垂直场景 · 企业AI',
        'AI学习': 'AI学习 · 在线课程 · 教育AI',
        'AI检测': 'AI检测 · 降AI率 · 原创检测',
        'AI提示词': 'AI提示词 · Prompt · 提示词库',
    }

    # ── 本周新增（live_data 自动更新，读不到则显示“每日”）──
    week_new = '每日'
    try:
        _live_stats = json.load(open(os.path.join(build.DATA_DIR, 'live_data.json'), encoding='utf-8'))
        _wn = (_live_stats.get('stats') or {}).get('this_week_new')
        if _wn:
            week_new = str(_wn)
    except Exception:
        pass

    def _row(t):
        """紧凑行式工具条目（分类区与热门区共用）。"""
        slug = t.get('slug', '')
        if not slug:
            return ''
        name = escape_html(t.get('name', ''))
        desc = escape_html((t.get('description') or '').strip())
        if len(desc) > 56:
            desc = desc[:56].rstrip() + '…'
        rn = extract_rating_num(t.get('rating', ''))
        price_cls, price_text = get_price_info(t)
        visits = escape_html(str(t.get('visits', '')))
        icon_html = tool_icon_html(t, size='sm')
        rating_html = f'<span class="rating-inline">★{rn}</span>' if rn else ''
        return f'''                        <a class="tools-index-row" href="/tools/{slug}/">
                            <span class="tools-index-icon">{icon_html}</span>
                            <span class="tools-index-main">
                                <span class="tools-index-name">{name} {rating_html}</span>
                                <span class="tools-index-desc">{desc}</span>
                            </span>
                            <span class="tools-index-meta">
                                <span class="price-pill {price_cls}">{price_text}</span>
                                <span class="tool-like" role="button" tabindex="0" data-slug="{slug}" aria-label="给 {name} 点赞" title="好用，点个赞">👍<b class="tool-like-count">0</b></span>
                                <span class="visits">{visits}</span>
                            </span>
                        </a>\n'''

    # ── 分类区块（紧凑行式，静态内链到每个工具页）──
    sections = ''
    for cat in ordered:
        cat_tools = by_cat[cat]
        cslug = get_category_slug(cat)
        cvar = get_category_color_var(cat)
        free_in_cat = sum(1 for t in cat_tools if get_price_info(t)[0] == 'free')
        rows = ''.join(_row(t) for t in cat_tools)
        _intro = cat_intros.get(cat, '')
        sections += f'''        <section class="home-section cat-section" id="cat-{cslug}" style="--cat-color:{cvar};">
            <div class="section-header">
                <div class="section-header-left">
                    <span class="cat-dot" style="background:{cvar};"></span>
                    <h2>{escape_html(cat)}<span class="cat-badge">{len(cat_tools)} 款</span></h2>
                </div>
                <a class="cat-more-link" href="/category/{cslug}/">查看分类页</a>
            </div>
            <p class="tools-index-cat-desc">{_intro} —— {len(cat_tools)} 款，其中 {free_in_cat} 款免费可用</p>
            <div class="tools-index-grid">
{rows}            </div>
        </section>\n'''

    # ── 分类快捷导航 ──
    chips = ''
    for c in ordered:
        chips += (f'<a class="tools-index-chip" href="#cat-{get_category_slug(c)}">'
                  f'<span class="tools-index-chip-dot" style="background:{get_category_color_var(c)};"></span>'
                  f'{escape_html(c)}<b>{len(by_cat[c])}</b></a>')

    # ── 2026 热门工具区（承接品牌/新品词）──
    hot_rows = ''.join(_row(t) for t in hot_tools)
    hot_section = ''
    if hot_rows:
        hot_section = f'''        <section class="home-section cat-section" id="hot" style="--cat-color:var(--primary);">
            <div class="section-header">
                <div class="section-header-left">
                    <span class="cat-dot" style="background:var(--primary);"></span>
                    <h2>{build.BUILD_YEAR} 热门 AI 工具<span class="cat-badge">HOT</span></h2>
                </div>
                <a class="cat-more-link" href="/ranking/">查看排行榜</a>
            </div>
            <div class="tools-index-grid">
{hot_rows}            </div>
        </section>\n'''

    # ── GEO 摘要（speakable）──
    geo_answer = (f'<strong>本站共收录 {n} 款 AI 工具</strong>（截至 {today_iso}），覆盖 {len(ordered)} 大分类'
                  f'（{top_cats}等），其中 {free_n} 款提供免费使用。{build.BUILD_YEAR} 年热度靠前的 '
                  f'DeepSeek V4、ChatGPT 5.6、Kimi 3、GPT Live、Qwen 3.8 Max、Gemini 等均已收录，'
                  f'每款工具标注评分、价格与访问热度，点击工具名称即可进入详情页查看评测与使用建议。')

    # ── FAQ ──
    faqs = [
        ('这里收录了多少款 AI 工具？多久更新一次？',
         f'当前共收录 {n} 款 AI 工具，覆盖 {len(ordered)} 个分类，最后更新于 {today_iso}。'
         f'工具库每日更新，新工具上线后会同步补充到对应分类与首页。'),
        ('最近最火的 AI 工具有哪些？',
         f'根据站内热度与搜索趋势，{build.BUILD_YEAR} 年 7-8 月关注度靠前的有 DeepSeek V4、ChatGPT 5.6、'
         f'Kimi 3、GPT Live、Qwen 3.8 Max、Gemini 等。本页顶部“{build.BUILD_YEAR} 热门 AI 工具”区可一键直达对应详情页。'),
        ('有哪些免费好用的 AI 工具？',
         f'本站收录的 {n} 款工具中，{free_n} 款提供免费使用（含“免费额度”模式）。'
         f'点击页首“只看免费”筛选即可快速浏览，或前往免费工具排行榜查看推荐。'),
        ('国内可以直接用的 AI 工具有哪些？',
         '文心一言、豆包、Kimi、DeepSeek、通义千问、腾讯混元等国产 AI 工具均可直接使用，'
         '每款工具的详情页都标注了中文可用性与访问方式。'),
        ('什么是 MCP？哪些 AI 工具支持 MCP？',
         'MCP（Model Context Protocol，模型上下文协议）是让 AI 模型连接外部工具与数据的开放标准。'
         '本站收录了 Chrome DevTools MCP、浏览器 MCP 等开发者工具，可在 AI 开发分类下找到。'),
        ('如何快速找到适合自己的 AI 工具？',
         '先按顶部分类导航定位场景（AI对话、AI编程、AI视频等），再结合评分、价格与访问热度筛选；'
         '每款工具的详情页都包含功能说明、价格模式与编辑评测，可据此对比。'),
        ('这些 AI 工具都是免费的吗？',
         f'不全是。当前 {free_n} 款提供免费使用，其余为付费或“免费额度+订阅”模式；'
         f'每款工具卡片与详情页都标注了价格模式（免费/免费试用/付费）。'),
        ('AI工具宝箱收录工具的标准是什么？',
         '优先收录真实可用、对中文用户友好、有稳定更新与良好口碑的 AI 工具；'
         '所有工具均由编辑团队筛选与评测，收录数据每日校准。'),
    ]
    faq_html = ''
    faq_schema = []
    for q, a in faqs:
        faq_html += f'<div class="faq-item"><div class="faq-q">{escape_html(q)}</div><div class="faq-a">{escape_html(a)}</div></div>\n'
        faq_schema.append({"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}})

    # ── ItemList 结构化数据（全量 name+url，头部按评分/热度带 description）──
    def _score(t):
        try:
            r = float(extract_rating_num(t.get('rating', '')) or 0)
        except Exception:
            r = 0.0
        v = str(t.get('visits', ''))
        try:
            vv = float(v.replace('万', '')) * 10000 if '万' in v else float(v or 0)
        except Exception:
            vv = 0.0
        return (r, vv)
    top25 = {t.get('slug') for t in sorted(tools, key=_score, reverse=True)[:25]}
    item_elems = []
    for i, t in enumerate(tools, 1):
        it = {"@type": "ListItem", "position": i,
              "name": t.get('name', ''),
              "url": f"{site}/tools/{t.get('slug', '')}/"}
        if t.get('slug') in top25 and t.get('description'):
            it['description'] = t['description'][:160]
        item_elems.append(it)

    breadcrumb_sd = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": f"{site}/"},
            {"@type": "ListItem", "position": 2, "name": "全部AI工具", "item": f"{site}/tools/"},
        ],
    }
    collection_sd = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": _title,
        "description": _meta_desc,
        "url": f"{site}/tools/",
        "inLanguage": "zh-CN",
        "datePublished": today_iso,
        "dateModified": today_iso,
        "isPartOf": {"@type": "WebSite", "name": "AI工具宝箱", "url": f"{site}/"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱", "url": f"{site}/"},
        "speakable": {"@type": "SpeakableSpecification",
                      "cssSelector": [".geo-answer", ".tools-index-sub"]},
        "mainEntity": {
            "@type": "ItemList",
            "name": "全部AI工具榜单",
            "numberOfItems": n,
            "itemListElement": item_elems,
        },
    }
    faq_sd = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_schema}
    website_sd = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "AI工具宝箱",
        "alternateName": "aitoollab.cn",
        "url": f"{site}/",
        "inLanguage": "zh-CN",
        "description": "收录全部 AI 工具的中文导航与评测平台",
    }
    json_ld = '\n'.join(
        f'    <script type="application/ld+json">{json.dumps(sd, ensure_ascii=False)}</script>'
        for sd in (breadcrumb_sd, collection_sd, faq_sd, website_sd)
    )

    page_css = """
.tools-index-hero .section-header h1{font-size:32px;font-weight:800;letter-spacing:-0.5px;}
.tools-index-sub{font-size:15px;color:var(--text-muted);margin:-6px 0 14px;}
.tools-index-hero,.cat-section,.faq-section{scroll-margin-top:220px !important;}
.geo-stats{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0 6px;}
.geo-stat{flex:1;min-width:118px;background:var(--surface);border:1px solid var(--border-light);border-radius:var(--radius-md);padding:14px 18px;text-align:center;}
.geo-stat b{display:block;font-size:24px;font-weight:800;color:var(--primary);line-height:1.2;}
.geo-stat span{font-size:12.5px;color:var(--text-muted);}
.tools-index-chips{display:flex;flex-wrap:nowrap;overflow-x:auto;gap:8px;position:sticky;top:185px;z-index:150;background:var(--body-bg);padding:4px 2px 10px;margin:4px -2px 24px;scrollbar-width:none;-webkit-overflow-scrolling:touch;}
@media (max-width:768px){.tools-index-chips{top:158px}}
.tools-index-chips::-webkit-scrollbar{display:none;}
.tools-index-chip{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;font-size:13.5px;font-weight:600;color:var(--text-main);background:var(--surface);border:1px solid var(--border-light);border-radius:var(--radius-pill);text-decoration:none;transition:var(--transition);flex:0 0 auto;}
.tools-index-chip:hover{border-color:var(--primary);color:var(--primary);box-shadow:var(--shadow-xs);}
.tools-index-chip b{font-size:11px;font-weight:700;background:rgba(0,166,79,0.08);color:var(--primary);padding:1px 7px;border-radius:8px;}
.tools-index-chip-dot{width:8px;height:8px;border-radius:50%;}
.cat-more-link{font-size:13px;font-weight:600;color:var(--primary);text-decoration:none;white-space:nowrap;}
.cat-more-link:hover{text-decoration:underline;}
.tools-index-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;}
.tools-index-row{display:flex;align-items:center;gap:10px;padding:10px 12px;background:var(--surface);border:1px solid var(--border-light);border-radius:var(--radius-md);text-decoration:none;color:inherit;transition:var(--transition);}
.tools-index-row:hover{border-color:var(--primary);box-shadow:var(--shadow-sm);transform:translateY(-1px);}
.tools-index-icon{flex-shrink:0;display:flex;align-items:center;}
.tools-index-main{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px;}
.tools-index-name{font-size:14px;font-weight:700;color:var(--text-main);display:flex;align-items:center;gap:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.tools-index-name .rating-inline{margin-left:0;}
.tools-index-desc{font-size:12.5px;color:var(--text-muted);line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.tools-index-meta{display:flex;align-items:center;gap:8px;flex-shrink:0;}
.tools-index-meta .visits{flex:none;font-size:12px;color:var(--gray-400,#94a3b8);text-align:right;}
.tools-index-cat-desc{font-size:13px;color:var(--text-muted);margin:-6px 0 14px;}
.tools-filter{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0 4px;}
.tools-filter-btn{font-size:13.5px;font-weight:600;padding:8px 18px;border-radius:var(--radius-pill);border:1px solid var(--border-light);background:var(--surface);color:var(--text-muted);cursor:pointer;transition:var(--transition);}
.tools-filter-btn.active{background:var(--primary);border-color:var(--primary);color:#fff;}
.tools-filter-btn:hover{border-color:var(--primary);color:var(--primary);}
.tools-filter-btn.active:hover{color:#fff;}
@media (min-width:1280px){.tools-index-grid{grid-template-columns:repeat(3,minmax(0,1fr));}}
@media (max-width:960px){
  .tools-index-grid{grid-template-columns:1fr;}
  .tools-index-chips{top:98px;padding:6px 2px 10px;margin:4px -2px 22px;}
  .tools-index-hero .section-header h1{font-size:24px;}
}
@media (max-width:640px){.tools-index-meta .visits{display:none;}}
""" + build.TOOL_LIKE_CSS

    filter_js = """
<script>
(function(){
  var btns = document.querySelectorAll('.tools-filter-btn');
  function apply(mode){
    var rows = document.querySelectorAll('.tools-index-row');
    for (var i = 0; i < rows.length; i++){
      var isFree = rows[i].querySelector('.price-pill.free') !== null;
      rows[i].style.display = (mode === 'free' && !isFree) ? 'none' : '';
    }
    for (var j = 0; j < btns.length; j++){
      var on = btns[j].getAttribute('data-filter') === mode;
      btns[j].classList.toggle('active', on);
      btns[j].setAttribute('aria-pressed', on ? 'true' : 'false');
    }
  }
  for (var k = 0; k < btns.length; k++){
    btns[k].addEventListener('click', function(){ apply(this.getAttribute('data-filter')); });
  }
})();
</script>
"""

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_title}</title>
    <meta name="description" content="{_meta_desc}">
    <meta name="keywords" content="{_keywords}">
    <link rel="canonical" href="{site}/tools/">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{_title}">
    <meta property="og:description" content="{_meta_desc}">
    <meta property="og:url" content="{site}/tools/">
    <meta property="og:image" content="{site}/images/og/aitoolbox-og.png">
    <meta property="og:locale" content="zh_CN">
    <meta property="og:site_name" content="AI工具宝箱">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{_title}">
    <meta name="twitter:description" content="{_meta_desc}">
    <meta name="twitter:image" content="{site}/images/og/aitoolbox-og.png">
    <style>{build.CRITICAL_CSS}</style>
    <style>{page_css}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript>
<link rel="stylesheet" href="/css/ai-widget.css?v={build.WIDGET_CSS_VERSION}">
{json_ld}
{build.BAIDU_TONGJI}
</head>
<body data-page-type="tools">
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <span>全部AI工具</span>
    </nav>

    <main class="container">
        <section class="section tools-index-hero">
            <div class="section-header">
                <h1>全部AI工具大全</h1>
            </div>
            <p class="tools-index-sub">{n} 款 AI 工具合集 · {len(ordered)} 大分类导航 · {free_n} 款免费可用 · 每日更新推荐</p>
            <div class="geo-answer" style="margin:14px 0 6px;padding:14px 18px;background:linear-gradient(135deg,#f0fdf4,#ecfdf5);border:1px solid #bbf7d0;border-left:4px solid #22c55e;border-radius:10px;font-size:14.5px;line-height:1.9;color:#14532d;">
                {geo_answer}
            </div>
            <div class="tools-filter" role="group" aria-label="价格筛选">
                <button type="button" class="tools-filter-btn active" data-filter="all" aria-pressed="true">全部工具</button>
                <button type="button" class="tools-filter-btn" data-filter="free" aria-pressed="false">只看免费</button>
            </div>
            <div class="geo-stats">
                <div class="geo-stat"><b>{n}</b><span>款收录工具</span></div>
                <div class="geo-stat"><b>{len(ordered)}</b><span>大分类</span></div>
                <div class="geo-stat"><b>{free_n}</b><span>款免费可用</span></div>
                <div class="geo-stat"><b>{week_new}</b><span>本周新增</span></div>
            </div>
        </section>

        <nav class="tools-index-chips" aria-label="分类快捷导航">{chips}</nav>

        {hot_section}

        {sections}

        <section class="home-section faq-section" id="faq">
            <div class="section-header">
                <div class="section-header-left"><h2>常见问题</h2></div>
            </div>
            {faq_html}
        </section>

        <div class="ads-slot ads-slot-content-bottom"></div>
    </main>

    <footer class="footer">
        <p>© {build.BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · {build.ICP_BEIAN}</p>
    </footer>
    {build.BACK_TO_TOP_BLOCK}
    {filter_js}
    <script src="/js/ai-likes.js?v={build.LIKES_JS_VERSION}" defer></script>
    <script src="/js/ai-assistant.js?v={build.WIDGET_JS_VERSION}" defer></script>
    <script src="/ads/loader.js" defer></script>
</body>
</html>'''
    return _collapse_blank_lines(html)

def build_index_page(tools, articles):
    import build  # 延迟：build 完全加载后解析
    # 生成静态首页
    index_html_template = os.path.join(build.BASE_DIR, 'index.html')
    with open(index_html_template, 'r', encoding='utf-8') as f:
        html = f.read()

    from datetime import datetime
    today_iso = datetime.now().strftime('%Y-%m-%d')

    # 同步 CSS 缓存版本号（index.html 作为模板时保留旧版本，需强制刷新）
    html = re.sub(r'style\.(?:min\.)?css\?v=[^"\'\)]+', f'style.min.css?v={build.CSS_VERSION}', html)
    # 同步 main.js 缓存版本号（内容哈希，自动生成）
    html = re.sub(r'/js/main\.js\?v=[^"\'\)]+', f'/js/main.js?v={build.JS_VERSION}', html)
    # 同步挂件脚本缓存版本号（ai-likes.js / ai-assistant.js，nginx 对 /js/ 缓存 30 天）
    html = re.sub(r'/js/ai-likes\.js(?:\?v=[^"\'\)]+)?', f'/js/ai-likes.js?v={build.LIKES_JS_VERSION}', html)
    html = re.sub(r'/js/ai-assistant\.js(?:\?v=[^"\'\)]+)?', f'/js/ai-assistant.js?v={build.WIDGET_JS_VERSION}', html)
    # P1-5 首页注入 AI 助手挂件（样式 + 脚本，幂等）
    if 'ai-widget.css' not in html:
        html = html.replace(
            '</head>',
            f'<link rel="stylesheet" href="/css/ai-widget.css?v={build.WIDGET_CSS_VERSION}">\n</head>',
            1,
        )
    if '/js/ai-assistant.js?v=' not in html:
        html = html.replace(
            '</body>',
            f'<script src="/js/ai-assistant.js?v={build.WIDGET_JS_VERSION}" defer></script>\n</body>',
            1,
        )

    # v6.9：移除旧版「内容Tab板块」里的 AI实战 页（已由独立 PRACTICE 区块替代，避免重复注入）
    # 幂等：已清理过的模板不再命中。导航按钮 + 实战面板（含其标记块）一并移除。
    html = re.sub(r'\s*<button class="tab-card" data-tab="practice">[\s\S]*?</button>', '', html, count=1)
    html = re.sub(r'\s*<!-- AI实战Tab[\s\S]*?<!-- PRACTICE_ITEMS_END -->\s*</div>', '', html, count=1)

    # ── 分类入口：左侧 sidebar / 移动端 cat-btn 恢复为纯导航 <button> ──
    # 上一版曾把"更多 ›"塞进侧边栏，会遮挡类目名；现改为：sidebar 仅做页内滚动导航，
    # "更多 ›"真实栏目页链接改由右侧类目区块标题（main.js 动态生成的 .cat-more-link）提供。
    # 此处把上一版写入的 <a class="..." href="/category/..."> 规范回 <button>（幂等：已是 button 则不动）。
    def _revert_cat_entry(m):
        cls = m.group(1)            # sidebar-cat / cat-btn
        extra = m.group(2) or ''    # 可能含 ' active'
        cat = m.group(3)
        style = m.group(4)
        label = m.group(5)
        if cat == 'all':
            return m.group(0)
        active = ' active' if 'active' in extra else ''
        style_attr = f' style="{style}"' if style else ''
        return f'<button class="{cls}{active}" data-category="{cat}"{style_attr}>{label}</button>'

    html = re.sub(
        r'<a class="(sidebar-cat|cat-btn)([^"]*)" href="/category/[^"]*/" data-category="([^"]+)"'
        r'(?: style="([^"]*)")?>\s*<span class="sc-label">(.*?)</span>'
        r'\s*<span class="sc-more">[^<]*</span>\s*</a>',
        _revert_cat_entry, html, flags=re.S)

    # 清理上一版遗留的废弃 cat-more-style（侧边栏 sc-more 样式，已不再使用，幂等）
    html = re.sub(r'<style id="cat-more-style">.*?</style>\s*', '', html, flags=re.S)

    # ── 注入右侧类目区块"查看更多"链接样式（首页专用，幂等，避免重复注入）──
    if 'id="home-cat-more-style"' not in html:
        cat_more_css = '''
<style id="home-cat-more-style">
.cat-more-link {
  display: inline-block;
  font-size: 13px; font-weight: 600; color: var(--primary);
  text-decoration: none; white-space: nowrap; flex: none; align-self: center;
  padding: 5px 14px; border-radius: 999px;
  background: rgba(var(--primary-rgb, 99, 102, 241), 0.10);
  border: 1px solid rgba(var(--primary-rgb, 99, 102, 241), 0.22);
  transition: background .15s ease, color .15s ease, border-color .15s ease;
}
.cat-more-link:hover {
  background: rgba(var(--primary-rgb, 99, 102, 241), 0.18);
  border-color: rgba(var(--primary-rgb, 99, 102, 241), 0.35);
  text-decoration: none;
}
.cat-more-link::after { content: ' ›'; font-weight: 700; margin-left: 2px; }
@media (max-width: 640px) {
  .cat-more-link { font-size: 12px; padding: 4px 10px; }
}
</style>
'''
        html = html.replace('</head>', cat_more_css + '\n</head>', 1)

    # ── 注入「热门榜 TOP30」紧凑小网格样式（首页专用，幂等）──
    hot_mini_css = '''
<style id="home-hot-mini-style">
#hotGrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px 10px;
}
.hot-mini {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 12px 8px; border-radius: 12px; text-decoration: none; color: inherit;
  background: rgba(127,127,127,0.06);
  border: 1px solid rgba(127,127,127,0.12);
  transition: transform .12s ease, box-shadow .12s ease, background .12s ease;
}
.hot-mini:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0,0,0,0.10);
  background: rgba(127,127,127,0.10);
}
.hot-mini-logo {
  width: 30px; height: 30px; border-radius: 8px; object-fit: contain;
  background: rgba(255,255,255,0.65); padding: 2px;
}
.hot-mini-logo-fallback {
  width: 30px; height: 30px; border-radius: 8px; flex: none;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; color: #fff; line-height: 1;
}
.hot-mini-name {
  font-size: 12.5px; font-weight: 600; text-align: center; line-height: 1.2;
  max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.hot-mini-meta { font-size: 11px; color: var(--text-muted, #64748b); }
@media (max-width: 640px) {
  #hotGrid { grid-template-columns: repeat(auto-fill, minmax(98px, 1fr)); gap: 10px 8px; }
  .hot-mini-name { font-size: 12px; }
}
</style>
'''
    # 幂等但允许更新：先移除旧块再注入最新样式（index.html 模板已含旧块会导致幂等跳过）
    html = re.sub(r'<style id="home-hot-mini-style">.*?</style>\s*', '', html, flags=re.S)
    html = html.replace('</head>', hot_mini_css + '\n</head>', 1)

    # ── 工具卡片HTML（委托共享函数）──
    def make_card_html(t, i):
        return make_tool_card_html(t, i)

    # ── 第二区块：热门榜 TOP30 紧凑小网格（按访问量降序，评分作展示）──
    def _parse_visits(v):
        if not v:
            return 0
        s = str(v).strip()
        try:
            if '亿' in s:
                return float(s.replace('亿', '')) * 1e8
            if '万' in s:
                return float(s.replace('万', '')) * 1e4
            return float(s)
        except Exception:
            return 0
    def _parse_rating(r):
        if not r:
            return 0.0
        m = re.search(r'[\d.]+', str(r))
        return float(m.group()) if m else 0.0
    hot_sorted = sorted(
        [t for t in tools if t.get('published', True)],
        key=lambda t: _parse_visits(t.get('visits')),
        reverse=True
    )[:12]
    hot_html = ''
    for t in hot_sorted:
        slug = t.get('slug', '')
        name = (t.get('name') or '').strip()
        name_esc = name.replace('"', '&quot;')
        rating_num = _parse_rating(t.get('rating'))
        visits = (t.get('visits') or '').strip()
        ext, icon = resolve_icon(slug)
        if icon:
            logo_html = ('<img class="hot-mini-logo" src="%s" alt="%s" loading="lazy" '
                         'width="30" height="30" onerror="this.style.visibility=\'hidden\'">' % (icon, name_esc))
        else:
            emoji = escape_html(t.get('emoji') or (name[:1] if name else '?'))
            color = t.get('color', '#4f46e5')
            logo_html = '<div class="hot-mini-logo-fallback" style="background:%s">%s</div>' % (color, emoji)
        hot_html += (
            '<a class="hot-mini" href="/tools/%s/" title="%s">'
            '%s'
            '<span class="hot-mini-name">%s</span>'
            '<span class="hot-mini-meta">★ %.1f · %s</span>'
            '</a>' % (slug, name_esc, logo_html, name, rating_num, visits)
        )
    html = replace_between_tags(html, '<div class="tools-grid" id="hotGrid">', hot_html)
    # 区块标题同步更新为「热门榜 TOP30」
    html = html.replace('热门榜 TOP30<span>HOT 30</span>',
                        '热门榜 TOP12<span>HOT 12</span>')
    html = html.replace('&#x1F525; 热门推荐<span>HOT PICKS</span>',
                        '热门榜 TOP12<span>HOT 12</span>')
    html = html.replace('热门推荐<span>HOT PICKS</span>',
                        '热门榜 TOP12<span>HOT 12</span>')

    def _tool_show_date(t):
        """版块展示用日期: published_date > created_date"""
        return str(t.get('published_date') or t.get('created_date') or '')[:10]

    # ── 第二点五区块：最新发布（按 published_date 降序，created_date 兜底，最多3个）──
    # v6-2 调整: 最近更新区块改为展示「每日新发布」的最新3款工具
    hot_slugs = set(t['slug'] for t in hot_sorted)
    recent_tools = sorted(
        [t for t in tools if _tool_show_date(t)],
        key=lambda t: _tool_show_date(t),
        reverse=True
    )
    # 去重：排除已出现在热门中的工具
    recent_tools = [t for t in recent_tools if t['slug'] not in hot_slugs][:3]
    recent_html = ''
    if recent_tools:
        for t in recent_tools:
            _slug = t.get('slug', '')
            _name = escape_html(t.get('name', ''))
            _cat = escape_html(t.get('category', ''))
            _desc = escape_html((t.get('description') or '')[:70])
            _price = escape_html(str(t.get('price', '免费')))
            _d = _tool_show_date(t)
            try:
                _dp = _d.split('-')
                _date_disp = f'{int(_dp[1]):02d}/{int(_dp[2]):02d}' if len(_dp) == 3 else _d
            except Exception:
                _date_disp = _d
            _, _icon = resolve_icon(_slug)
            if _icon:
                _icon_html = f'<img class="release-logo" src="{_icon}" alt="{_name}" loading="lazy" width="44" height="44">'
            else:
                _icon_html = f'<div class="release-logo release-logo-fallback">{escape_html(t.get("emoji") or _name[:1])}</div>'
            recent_html += (
                f'<a class="release-item" href="/tools/{_slug}/">'
                f'{_icon_html}'
                f'<div class="release-body">'
                f'<div class="release-head"><span class="release-name">{_name}</span><span class="release-date">{_date_disp}</span></div>'
                f'<p class="release-desc">{_desc}</p>'
                f'<div class="release-meta"><span>{_cat}</span><span>{_price}</span></div>'
                f'</div>'
                f'</a>'
            )
    else:
        recent_html = '<p style="color:var(--text-light);padding:20px 0;">暂无最新发布 ~</p>\n'

    html = replace_between_tags(html, '<div class="tools-grid" id="recentGrid">', recent_html)
    # 如果最近更新为空，隐藏recentSection
    if not recent_tools:
        html = html.replace('<section class="home-section recent-section" id="recentSection">',
                            '<section class="home-section recent-section" id="recentSection" style="display:none;">')

    # ── 第三区块：全部工具（首屏8个静态，剩余懒加载） ──
    all_tools_html = ''
    for i, t in enumerate(tools[:8]):
        all_tools_html += make_card_html(t, i)
    html = replace_between_tags(html, '<div class="tools-grid" id="toolsGrid">', all_tools_html)

    # ── AI前沿Tab新闻卡片：从articles.json动态获取最新5篇 ──
    def parse_article_date(d):
        """统一解析多种日期格式，缺省年份补2026"""
        from datetime import datetime
        d = d.strip()
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d'):
            try:
                return datetime.strptime(d, fmt)
            except:
                continue
        # 只有月/日格式，补2026年（避免Python 3.15 breaking change）
        try:
            dt = datetime.strptime('2026/' + d, '%Y/%m/%d')
            return dt
        except:
            pass
        try:
            dt = datetime.strptime('2026年' + d, '%Y年%m月%d日')
            return dt
        except:
            pass
        return datetime.min
    sorted_articles = sorted(articles, key=lambda a: parse_article_date(a.get('date', '')), reverse=True)
    
    # ── 广告/推广列表（穿插在新闻之间，凤凰网风格）──
    NEWS_ADS = [
        {"title": "2026年免费AI工具大盘点：这12款国产工具零成本上手", "url": "/articles/ai-free-tools-china-2026/"},
        {"title": "Cursor vs Copilot vs Windsurf 2026终极对比：我三家都用了一年", "url": "/articles/cursor-vs-copilot-vs-windsurf-2026/"},
        {"title": "AI数据分析工具实测：我用同一份数据测了5款，免费的通义千问比ChatGPT还快", "url": "/articles/ai-data-analysis-tools-real-test-202606/"},
        {"title": "AI写作工具推荐：从日报周报到万字长文，这6款覆盖你所有场景", "url": "/articles/ai-writing-tools-2026-guide/"},
    ]
    
    news_html = ''
    # 标签统一走 content_type（与「AI实战教程/深度评测」区块同源）。
    # 2026-08-14 修复：旧 tag_names 按 category 映射且漏了「AI工具教程」等分类，
    # 导致教程文章在 AI前沿 里被 fallback 误标成「AI资讯」，与 AI实战教程 区块的「教程」自相矛盾。
    _ct_tag = {'AI教程': '教程', 'AI评测': 'AI评测', 'AI资讯': 'AI资讯', '行业分析': 'AI洞察'}
    for idx, a in enumerate(sorted_articles[:5]):
        d = a.get('date', '')
        # 统一显示为 MM/DD
        display_date = d
        if '-' in d and len(d) == 10:
            parts = d.split('-')
            display_date = f'{int(parts[1]):02d}/{int(parts[2]):02d}'
        elif '/' in d:
            parts = d.split('/')
            if len(parts) == 3:
                display_date = f'{int(parts[0]):02d}/{int(parts[1]):02d}'
        tag = _ct_tag.get(build.article_content_type(a), 'AI资讯')
        news_html += f'''                                <a class="news-card-item" href="/articles/{a['slug']}/">
                                    <span class="news-card-date">{display_date}</span>
                                    <span class="news-card-title">{escape_html(a['title'])}</span>
                                    <span class="news-card-tag">{tag}</span>
                                </a>
'''
        # 在第2篇新闻后插入1条推广（当前隐藏待启用）
        if idx == 1:
            ad = NEWS_ADS[0]
            news_html += f'''                                <a class="news-card-item news-card-ad" href="{ad['url']}" style="display:none">
                                    <span class="news-card-date">推广</span>
                                    <span class="news-card-title">{ad['title']}</span>
                                    <span class="news-card-tag ad-tag">推荐</span>
                                </a>
'''
    # 替换新闻卡片（保留"更多文章"链接）
    news_re = re.compile(r'<!-- NEWS_CARDS_START -->[\s\S]*?<!-- NEWS_CARDS_END -->')
    html = news_re.sub(f'<!-- NEWS_CARDS_START -->\n{news_html}                                <!-- NEWS_CARDS_END -->', html)

    # ── AI辞典Tab词典卡片：按发布时间倒序取已发布最新8条（2026-08-20 动态化）──
    # 原逻辑 dict_terms[:8] 取数组头 8 条永远固定；现改为 published_date 倒序，
    # 每日发布自动化写入新词条的 published_date 后，首页板块自动轮换。
    # 无日期的基础词条（最早批次）沉底不占首页位，靠 /dict/ 索引页全量入口兜底。
    dict_html = ''
    dict_terms = []
    dict_data_path = os.path.join(build.DATA_DIR, 'dict_terms.json')
    if os.path.exists(dict_data_path):
        with open(dict_data_path, 'r', encoding='utf-8') as f:
            all_dict = json.load(f)
            dict_terms = [t for t in all_dict if t.get('published', True)]
    dict_terms.sort(key=lambda t: t.get('published_date') or '2000-01-01', reverse=True)
    for idx, term in enumerate(dict_terms[:8]):
        new_badge = '<span class="badge-new">NEW</span>' if idx < 2 else ''
        _pd = (term.get('published_date') or '').strip()
        _pd_display = ''
        if len(_pd) == 10:
            _pp = _pd.split('-')
            try:
                _pd_display = f'{int(_pp[1]):02d}/{int(_pp[2]):02d}'
            except Exception:
                _pd_display = ''
        dict_html += f'''                                <a class="dict-card-item" href="/dict/{term['slug']}/">
                                    <div class="dict-card-icon">{term['emoji']}</div>
                                    <div class="dict-card-body">
                                        <h4>{escape_html(term['term'])} {new_badge}</h4>
                                        <p>{escape_html(term['brief'])}</p>
                                        <span class="dict-card-date">{_pd_display}</span>
                                    </div>
                                </a>
'''
    dict_re = re.compile(r'<!-- DICT_CARDS_START -->[\s\S]*?<!-- DICT_CARDS_END -->')
    html = dict_re.sub(f'<!-- DICT_CARDS_START -->\n{dict_html}                                <!-- DICT_CARDS_END -->', html)

    # ── 编辑实测 · 今日推荐（v6；2026-08-12 修复：日期与内容必须同源）──
    def _fmt_md(d):
        try:
            p = d.split('-')
            if len(p) == 3:
                return f'{int(p[1]):02d}/{int(p[2]):02d}'
        except Exception:
            pass
        return d
    _picks_path = os.path.join(build.DATA_DIR, 'homepage_picks.json')
    _picks_date = datetime.now().strftime('%Y-%m-%d')

    def _load_picks_file():
        try:
            return json.load(open(_picks_path, encoding='utf-8')) if os.path.exists(_picks_path) else {}
        except Exception:
            return {}

    def _pick_text_corrupt(p):
        # 编码损坏检测：CJK 被 ASCII 化后会出现连续问号（如 PowerShell 管道写坏）或替换符
        for _s in (p.get('reason'), p.get('tag')):
            if isinstance(_s, str) and ('\ufffd' in _s or re.search(r'\?{3,}', _s) is not None):
                return True
        return False

    _pd = _load_picks_file()
    _picks_broken = any(_pick_text_corrupt(p) for p in _pd.get('picks', []))
    # 自动模式：推荐过期或文案编码损坏时，先刷新当日推荐再构建
    # （根因：deploy.sh 曾把候选池生成放在构建之后；其他自动化只跑 build.py 不生成候选池；
    #   2026-08-13 增补：数据被 ASCII 化产生问号时强制重建，避免坏文案上线）
    if _pd.get('auto') and (str(_pd.get('date', '')) != _picks_date or _picks_broken):
        _sub_env = os.environ.copy()
        _sub_env.setdefault('PYTHONIOENCODING', 'utf-8')
        _sub_env.setdefault('PYTHONUTF8', '1')
        _picks_run = subprocess.run(
            [sys.executable, os.path.join(build.BASE_DIR, 'scripts', 'generate_picks_candidates.py')],
            capture_output=True, text=True, encoding='utf-8', env=_sub_env)
        if _picks_run.returncode == 0:
            print(f'[picks] 已刷新为 {_picks_date} 推荐（过期或文案损坏自动重建）')
            _pd = _load_picks_file()
            _picks_broken = any(_pick_text_corrupt(p) for p in _pd.get('picks', []))
        else:
            print(f'[picks] 自动刷新今日推荐失败(exit {_picks_run.returncode})，沿用现有推荐：')
            print((_picks_run.stderr or _picks_run.stdout or '')[-300:])
    _picks = []
    _picks_date = str(_pd.get('date', _picks_date))
    _tool_map = {t['slug']: t for t in tools}
    for _p in _pd.get('picks', []):
        if _pick_text_corrupt(_p):
            print(f"[picks] 跳过编码损坏的推荐条目: {_p.get('slug')}")
            continue
        _t = _tool_map.get(_p.get('slug'))
        if _t:
            _picks.append((_t, str(_p.get('reason', '')), str(_p.get('tag', '编辑实测'))))
    # 兜底：损坏条目被跳过或推荐不足 3 个时，用热门榜补足，保证推荐区不空（2026-08-13）
    if len(_picks) < 3:
        _seen = {_t.get('slug') for _t, _, _ in _picks}
        for _t in hot_sorted:
            if _t.get('slug') in _seen:
                continue
            _picks.append((_t, '热门实测 · 数据驱动选型', '编辑实测'))
            _seen.add(_t.get('slug'))
            if len(_picks) >= 3:
                break
    picks_html = ''
    for _i, (_t, _reason, _tag) in enumerate(_picks):
        _slug = _t.get('slug', '')
        _name = escape_html(_t.get('name', ''))
        _cat = escape_html(_t.get('category', ''))
        _price = escape_html(str(_t.get('price', '免费')))
        _, _icon = resolve_icon(_slug)
        if _icon:
            _icon_html = f'<img src="{_icon}" class="pick-logo" alt="{_name}" loading="lazy" width="48" height="48">'
        else:
            _icon_html = f'<div class="pick-logo pick-logo-fallback">{escape_html(_t.get("emoji") or _name[:1])}</div>'
        picks_html += (
            f'<a class="pick-card" href="/tools/{_slug}/" data-slug="{_slug}">\n'
            f'      {_icon_html}\n'
            f'      <div class="pick-body">\n'
            f'        <div class="pick-head"><span class="pick-name">{_name}</span><span class="pick-tag">{escape_html(_tag)}</span></div>\n'
            f'        <p class="pick-reason">{escape_html(_reason)}</p>\n'
            f'        <div class="pick-meta"><span>{_cat}</span><span>{_price}</span></div>\n'
            f'      </div>\n'
            f'    </a>\n'
        )
    picks_re = re.compile(r'<!-- PICKS_START -->[\s\S]*?<!-- PICKS_END -->')
    html = picks_re.sub(f'<!-- PICKS_START -->\n{picks_html}<!-- PICKS_END -->', html)
    html = re.sub(r'(<span class="picks-date" id="picksDate">)[^<]*(</span>)',
                  r'\g<1>' + _fmt_md(_picks_date) + ' 精选' + r'\g<2>', html)

    # ── 编辑实测 · 深度评测（v6；2026-08-08 改用 content_type 字段）──
    _reviews = [a for a in articles if build.article_content_type(a) == 'AI评测']
    _reviews = sorted(_reviews, key=lambda a: parse_article_date(a.get('date', '')), reverse=True)[:6]
    reviews_html = ''
    for _a in _reviews:
        # 标签与入选标准一致：统一用 content_type（之前误用 category 映射，导致评测区贴出"AI资讯/教程"）
        _rtag = 'AI评测'
        reviews_html += (
            f'<a class="review-item" href="/articles/{_a["slug"]}/">\n'
            f'        <span class="review-date">{_fmt_md(_a.get("date", ""))}</span>\n'
            f'        <span class="review-title">{escape_html(_a["title"])}</span>\n'
            f'        <span class="review-tag">{_rtag}</span>\n'
            f'    </a>\n'
        )
    reviews_re = re.compile(r'<!-- REVIEWS_START -->[\s\S]*?<!-- REVIEWS_END -->')
    html = reviews_re.sub(f'<!-- REVIEWS_START -->\n{reviews_html}<!-- REVIEWS_END -->', html)

    # ── AI实战教程（v6.9：独立区块，填充真实教程；无内容则整块隐藏；2026-08-08 改用 content_type）──
    _tutorials = [a for a in articles if build.article_content_type(a) == 'AI教程']
    _tutorials = sorted(_tutorials, key=lambda a: parse_article_date(a.get('date', '')), reverse=True)[:6]
    if _tutorials:
        practice_html = ''
        for _a in _tutorials:
            practice_html += (
                f'<a class="practice-item" href="/articles/{_a["slug"]}/">\n'
                f'            <span class="practice-item-title">{escape_html(_a["title"])}</span>\n'
                f'            <span class="practice-item-tag">教程</span>\n'
                f'        </a>\n'
            )
        practice_re = re.compile(r'<!-- PRACTICE_ITEMS_START -->[\s\S]*?<!-- PRACTICE_ITEMS_END -->')
        html = practice_re.sub(f'<!-- PRACTICE_ITEMS_START -->\n{practice_html}<!-- PRACTICE_ITEMS_END -->', html)
        # 模板默认隐藏独立区块，有教程内容才展示
        html = html.replace('<section class="home-section practice-section" id="practiceSection" style="display:none;">',
                            '<section class="home-section practice-section" id="practiceSection">', 1)
    else:
        html = html.replace('<section class="home-section practice-section" id="practiceSection">',
                            '<section class="home-section practice-section" id="practiceSection" style="display:none;">', 1)

    # ── 首页价值条统计数字（v6）──
    _review_cnt = sum(1 for a in articles if build.article_content_type(a) == 'AI评测')
    _cmp_dir = os.path.join(build.BASE_DIR, 'compare')
    try:
        _compare_cnt = len([_d for _d in os.listdir(_cmp_dir)
                            if os.path.isdir(os.path.join(_cmp_dir, _d)) and _d != '_template'])
    except Exception:
        _compare_cnt = 0
    html = re.sub(r'(<b id="statTools">)[^<]*(</b>)', r'\g<1>' + str(len(tools)) + r'\g<2>', html)
    html = re.sub(r'(<b id="statReviews">)[^<]*(</b>)', r'\g<1>' + str(_review_cnt) + r'\g<2>', html)
    html = re.sub(r'(<b id="statCompares">)[^<]*(</b>)', r'\g<1>' + str(_compare_cnt) + r'\g<2>', html)

    # 工具数量显示 — 用re.sub替换（模板中可能已有内容如"共 100+ 款"）
    html = re.sub(r'<span class="tool-count" id="toolCount">.*?</span>', f'<span class="tool-count" id="toolCount">共 {len(tools)} 款</span>', html)

    # 轻量化工具数据（首页JS只需展示字段）
    # 这些字段的完整内容在各自独立的工具详情页（静态HTML）中，不影响SEO
    LIGHTWEIGHT_KEYS = {'name', 'slug', 'emoji', 'color', 'description', 'category', 'subcategory',
                        'tags', 'rating', 'visits', 'badge', 'url', 'price', 'platform', 'created_date'}
    def tool_icon_path(slug):
        """首页JS懒加载图标路径：复用 resolve_icon() 统一解析。"""
        _, web_path = resolve_icon(slug)
        return web_path
    def make_lightweight(tool_list):
        out = []
        for t in tool_list:
            d = {k: v for k, v in t.items() if k in LIGHTWEIGHT_KEYS}
            d['icon'] = tool_icon_path(t.get('slug', ''))
            out.append(d)
        return out

    # P0-2（2026-08-09）：紧凑序列化（无缩进）+ 移除 __REMAINING_TOOLS__。
    # __REMAINING_TOOLS__ 与 __ALL_TOOLS__ 高度重叠（tools[8:] 是其子集），
    # 且全站 JS 无任何消费方，删除后 tools-data.js 体积再减半。
    all_tools_json = json.dumps(make_lightweight(tools), ensure_ascii=False, separators=(',', ':'))
        
    articles_html = ''
    for a in articles[:6]:
        # 统一日期显示格式为 MM/DD
        d = a.get('date', '')
        if '-' in d and len(d) == 10:
            parts = d.split('-')
            display_date = f'{int(parts[1]):02d}/{int(parts[2]):02d}'
        else:
            display_date = d
        articles_html += f'''                        <li>
                            <span class="date">{display_date}</span>
                            <a class="title" href="/articles/{a['slug']}/">{escape_html(a['title'])}</a>
                        </li>\n'''
    
    # ── 注入新类目 sidebar / 移动端按钮（幂等，2026-08-05）──
    # 首页模板自举自上一版 index.html（build_index_page 读 index.html 作模板），
    # 新类目按钮不会自动出现，需每次构建时补齐；已存在则跳过。
    _new_cat_btns = [
        # 2026-08-06: 去掉 emoji（节省 sidebar 空间），分类名直接作为按钮文本
        ("AI学习", "", "var(--cat-learn)"),
        ("AI检测", "", "var(--cat-detect)"),
        ("AI提示词", "", "var(--cat-prompt)"),
    ]
    _missing_side = [b for b in _new_cat_btns if f'class="sidebar-cat" data-category="{b[0]}"' not in html]
    if _missing_side:
        _side_ins = ''.join(
            f'<button class="sidebar-cat" data-category="{n}" style="--dot: {c}">{e} {n}</button>'
            for n, e, c in _missing_side)
        html = re.sub(r'<button class="sidebar-cat" data-category="AI提示词"',
                      _side_ins + r'<button class="sidebar-cat" data-category="AI提示词"',
                      html, count=1)
    _missing_mob = [b for b in _new_cat_btns if f'class="cat-btn" data-category="{b[0]}"' not in html]
    if _missing_mob:
        _mob_ins = ''.join(
            f'<button class="cat-btn" data-category="{n}">{e} {n}</button>'
            for n, e, c in _missing_mob)
        html = re.sub(r'<button class="cat-btn" data-category="AI提示词"',
                      _mob_ins + r'<button class="cat-btn" data-category="AI提示词"',
                      html, count=1)

    # 动态生成热门分类列表
    category_counts = get_category_stats(tools)
    categories_html = ''
    # 按照 index.html 中的顺序
    ordered_categories = ["AI对话", "AI写作", "AI绘画", "AI编程", "AI视频", "AI音频", "AI办公", "AI设计", "AI搜索", "AI翻译", "AI自动化", "AI效率", "AI智能体", "AI开发", "AI行业应用", "AI学习", "AI检测", "AI提示词"]
    for category in ordered_categories:
        count = category_counts.get(category, 0)
        # 假设分类页面路径为 /category/slug/index.html
        category_slug = get_category_slug(category)
        categories_html += f'''                        <li><a href="/category/{category_slug}/">{category} ({count})</a></li>\n'''

    # 更新页脚链接
    footer_links_html = '''            <a href="/about.html">关于我们</a>
            <a href="/contact.html">联系方式</a>
            <a href="/favorites.html">我的收藏</a>
            <a href="/privacy.html">隐私政策</a>
            <a href="/links.html">友情链接</a>
            <a href="mailto:AIToolLabTeam@gmail.com">投稿合作</a>'''

    # 替换工具数量（动态计算）
    all_tools_count = 0
    all_tools_data = load_tools()
    all_tools_count = len(all_tools_data)
    if all_tools_count > 100:
        count_text = f'已收录 {all_tools_count // 100 * 100}+ 工具'
    else:
        count_text = f'已收录 {all_tools_count} 款工具'
    html = re.sub(r'每日更新 · 已收录 \d+\+ (?:款 )?工具', f'每日更新 · {count_text}', html)
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

    # 替换内容
    html = re.sub(r'(<ul id="articleList">)[\s\S]*?(</ul>)', lambda m: m.group(1) + '\n' + articles_html + '                    </ul>', html)
    html = re.sub(r'(<ul id="categoryList">)[\s\S]*?(</ul>)', lambda m: m.group(1) + '\n' + categories_html + '                    </ul>', html)
    html = re.sub(r'(<div class="footer-links">)[\s\S]*?(</div>)', lambda m: m.group(1) + '\n' + footer_links_html + '\n        </div>', html)
    
    # 生成外部工具数据文件（避免首页内联 4.7MB JSON）
    tools_data_js_path = os.path.join(build.BASE_DIR, 'js', 'tools-data.js')
    os.makedirs(os.path.dirname(tools_data_js_path), exist_ok=True)
    _subdef = get_subcat_def()
    _subcat_json = json.dumps(_subdef, ensure_ascii=False, separators=(',', ':'))
    _cat_slug_json = json.dumps(build.CATEGORY_SLUG_MAP, ensure_ascii=False, separators=(',', ':'))
    with open(tools_data_js_path, 'w', encoding='utf-8') as f:
        f.write(f'window.__ALL_TOOLS__ = {all_tools_json};\n')
        f.write(f'window.__SUBCATEGORIES__ = {_subcat_json};\n')
        f.write(f'window.__CATEGORY_SLUG_MAP__ = {_cat_slug_json};\n')
    print(f'[OK] js/tools-data.js ({os.path.getsize(tools_data_js_path)//1024}KB)')

    # 移除旧的内联 __ALL_TOOLS__ / __REMAINING_TOOLS__ 脚本（避免重复；REMAINING 段自 P0-2 起不再生成，兼容清理旧模板）
    html = re.sub(r'<script>\s*window\.__ALL_TOOLS__\s*=\s*\[[\s\S]*?\];\s*\n?(?:\s*window\.__REMAINING_TOOLS__\s*=\s*\[[\s\S]*?\];?\s*)?</script>', '', html)

    # 移除旧的 tools-data.js 引用（避免重复注入）— 支持带defer和不带defer的
    html = re.sub(r'<script\s+src="/js/tools-data\.js(\?[^"]*)?"\s*(defer)?\s*></script>\s*', '', html)
    # 移除旧的 favorites.js 引用（避免重复注入；历史构建曾累积 80+ 条）
    html = re.sub(r'<script\s+src="/js/favorites\.js(\?[^"]*)?"\s*(defer)?\s*></script>\s*', '', html)
    # 同时清理 tools-data.js 上方的引导注释（避免 4166 只清 <script> 留下注释造成累积）
    html = re.sub(r'<!--\s*JS defer 加载[^\n]*tools-data\.js[^\n]*-->\s*\n?', '', html)

    # 移除所有已有的百度统计代码片段（无论占位符还是真实代码），避免重复叠加
    html = re.sub(r'<script>\s*var _hmt\s*=\s*_hmt\s*\|\|\s*\[\];\s*\(function\(\)\s*\{[\s\S]*?hm\.src\s*=\s*"[^"]*";[\s\S]*?\}\)\(\);?\s*</script>', '', html)
    html = re.sub(r'<!--\s*BAIDU_TONGJI_PLACEHOLDER\s*-->', '', html)
    # 同时清理"百度统计（异步加载...）"引导注释（避免 4169 只清 <script> 留下注释造成累积）
    html = re.sub(r'<!--\s*百度统计（异步加载[^\n]*-->\s*\n?', '', html)

    # 清理历史烤入的 AdSense enable_page_level_ads 手动 push（旧构建产物残留）。
    # 该 push 会与 AdSense 后台 Auto ads 自动注入冲突，触发
    # "Only one 'enable_page_level_ads' allowed per page" 报错。现在 Auto ads 改由后台控制，
    # 代码不再手动 push，故构建时强制剥离残留的手动 push 脚本。
    html = re.sub(
        r'<script>\s*\(adsbygoogle\s*=\s*window\.adsbygoogle\s*\|\|\s*\[\]\)\.push\(\{\s*'
        r'google_ad_client:\s*"[^"]*",\s*enable_page_level_ads:\s*true\s*\}\);\s*</script>\s*',
        '', html)

    # 收集所有动态head注入内容（带注释，确保注释与代码对齐）
    dynamic_head = ''
    dynamic_head += '<!-- JS defer 加载：tools-data.js，不阻塞渲染 -->\n'
    dynamic_head += f'<script src="/js/tools-data.js?v={int(time.time())}" defer></script>\n'
    dynamic_head += f'<script src="/js/favorites.js?v={int(time.time())}" defer></script>\n'
    dynamic_head += '\n'

    # 注入 Google AdSense 库脚本 + Auto ads 初始化（静态不变量写入模板，不由 inject_ads.py 每次动态注入）
    # 2026-07-31 修复：adsbygoogle.js 国内被墙 → google.com/recaptcha iframe 超时 20s+ 拖垮加载。
    # enabled=false 时从模板中剥离历史注入的脚本（站点验证仅需 meta 标签，不影响 AdSense 验证）。
    html = re.sub(
        r'\s*<script[^>]*src="https://pagead2\.googlesyndication\.com/'
        r'pagead/js/adsbygoogle\.js[^"]*"[^>]*></script>\s*',
        '\n', html, flags=re.IGNORECASE)
    if 'adsbygoogle.js' not in html:
        _ads_cfg = {}
        try:
            ap = os.path.join(build.BASE_DIR, 'ads', 'config.json')
            if os.path.isfile(ap):
                _ads_cfg = json.load(open(ap, encoding='utf-8'))
        except Exception:
            pass
        _adsense = _ads_cfg.get('adsense', {})
        if _adsense.get('enabled'):
            _pid = _adsense.get('publisherId', '')
            if _pid:
                # 仅加载 AdSense 库脚本。Auto ads（页级自动广告）由 AdSense 后台开启控制，
                # 此处【不再】手动 push enable_page_level_ads——否则会与后台自动注入冲突，
                # 在控制台报 "Only one 'enable_page_level_ads' allowed per page" 错误。
                dynamic_head += f'    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={_pid}" crossorigin="anonymous"></script>\n'

    dynamic_head += '<!-- 百度统计（异步加载，不阻塞渲染） -->\n'

    # 注入 OG 标签（如果缺失 og:url）
    if 'og:url' not in html:
        dynamic_head += '<meta property="og:url" content="https://www.aitoollab.cn/">\n'

    # 注入百度统计代码
    dynamic_head += f'{build.BAIDU_TONGJI}\n'

    # 注入 Bing Webmaster 验证标签（如果缺失）
    BING_VERIFY = '    <meta name="msvalidate.01" content="D2B58E242903570E029A957ECDFF1E05" />'
    if 'msvalidate.01' not in html:
        dynamic_head += f'{BING_VERIFY}\n'

    # 统一替换 BUILD_DYNAMIC_HEAD 占位符（首页模板专用）
    if '<!-- BUILD_DYNAMIC_HEAD -->' in html:
        html = html.replace('<!-- BUILD_DYNAMIC_HEAD -->', dynamic_head)
    else:
        # 非首页模板，fallback到</head>
        html = html.replace('</head>', dynamic_head + '</head>')

    # 确保返回顶部按钮存在（兜底注入）
    if 'id="backToTop"' not in html:
        BACK_TO_TOP_HTML = '''
    <button id="backToTop" aria-label="返回顶部">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="18 15 12 9 6 15"></polyline>
        </svg>
    </button>'''
        html = html.replace('</body>', BACK_TO_TOP_HTML + '\n</body>')

    # BUG1修复：不再注入内联backToTop脚本，main.js已包含完整逻辑
    # 清理可能存在的内联返回顶部脚本（防止重复）
    html = re.sub(r'<script>\s*// 返回顶部按钮[\s\S]*?</script>\s*', '', html)
    html = re.sub(r'<script>\s*\(function\(\)\{\s*var b=document\.getElementById\("backToTop"\)[\s\S]*?\}\)\(\);\s*</script>\s*', '', html)

    # 首页按分类浏览钻取区已移除：改为左侧导航子类目树

    # 替换导航为最新版本（确保含AI词典等新增入口）
    old_nav_start = '    <nav class="global-nav" aria-label="全局导航">'
    old_nav_end = '    </nav>'
    start_idx = html.find(old_nav_start)
    end_idx = html.find(old_nav_end, start_idx) + len(old_nav_end) if start_idx >= 0 else -1
    if start_idx >= 0 and end_idx > start_idx:
        html = html[:start_idx] + build.GLOBAL_NAV + html[end_idx:]

    return html
