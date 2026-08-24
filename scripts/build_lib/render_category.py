# render_category.py — 分类页/子分类页/分类索引
# 模块6：从 build.py 拆分（2026-08-24）
import os
import re
import json
from datetime import datetime as _dt_build

from build_lib.html_utils import (
    escape_html, _emit, _collapse_blank_lines,
)
from build_lib.data_loaders import (get_category_slug,)
from build_lib.render_tool import (
    make_tool_card_html, tool_icon_html, get_category_stats, resolve_icon,
)


def _build_category_index_page(tools_by_category):
    import build  # 延迟：build 完全加载后解析
    """生成 category/index.html 总入口页：分类宫格卡片（点击进入类目），卡片样式对齐首页热门榜 TOP30 的 hot-mini 紧凑小卡片"""
    # 分类排序：固定顺序在前，其余按名称
    ordered_categories = ["AI对话", "AI写作", "AI绘画", "AI编程", "AI视频", "AI音频", "AI办公", "AI设计", "AI搜索", "AI翻译", "AI自动化", "AI效率", "AI智能体", "AI开发", "AI行业应用", "AI学习", "AI检测", "AI提示词", "去中心化AI"]
    category_emojis = {
        "AI对话": "💬", "AI写作": "✍️", "AI绘画": "🎨", "AI编程": "💻",
        "AI视频": "🎬", "AI音频": "🎵", "AI办公": "📁", "AI设计": "🎯",
        "AI搜索": "🔍", "AI翻译": "🌐", "AI自动化": "⚙️", "AI效率": "⚡",
        "AI智能体": "🤖", "AI开发": "🛠️", "AI行业应用": "🏢",
        "AI学习": "📚", "AI检测": "🕵️", "AI提示词": "💬", "去中心化AI": "🔗",
    }
    # 分类徽标底色（对齐全站 --cat-* 色板）
    category_colors = {
        "AI对话": "#10b981", "AI写作": "#00C250", "AI绘画": "#f59e0b",
        "AI编程": "#3b82f6", "AI视频": "#ef4444", "AI音频": "#8b5cf6",
        "AI办公": "#0ea5e9", "AI设计": "#ec4899", "AI搜索": "#14b8a6",
        "AI翻译": "#22c55e", "AI自动化": "#f97316", "AI效率": "#a855f7",
        "AI智能体": "#a855f7", "AI开发": "#3b82f6", "AI行业应用": "#0ea5e9",
        "AI学习": "#6366f1", "AI检测": "#ef4444", "AI提示词": "#8b5cf6", "去中心化AI": "#FF6B35",
    }
    cat_names = [c for c in ordered_categories if c in tools_by_category]
    cat_names += [c for c in tools_by_category if c not in ordered_categories]

    total_cats = len(tools_by_category)
    total_tools = sum(len(v) for v in tools_by_category.values())

    # 分类卡片：hot-mini 紧凑小卡片（对齐首页热门榜结构：彩色图标块 + 名称 + 元信息），点击进入对应类目页
    cards_html = ''
    for cat_name in cat_names:
        cat_slug = get_category_slug(cat_name)
        emoji = category_emojis.get(cat_name, '📂')
        color = category_colors.get(cat_name, '#4f46e5')
        count = len(tools_by_category[cat_name])
        cards_html += (
            '<a class="hot-mini" href="/category/%s/" title="%s">'
            '<div class="hot-mini-logo-fallback" style="background:%s">%s</div>'
            '<span class="hot-mini-name">%s</span>'
            '<span class="hot-mini-meta">%d 款工具</span>'
            '</a>\n' % (cat_slug, escape_html(cat_name), color, emoji, escape_html(cat_name), count)
        )

    # ═══════════════════════════════════════════════════════════════════════
    # SEO + GEO 强化（2026-08-03）
    # 背景：文章页/工具详情页已做完 SEO+GEO，唯独分类线是空白。此前本枢纽页
    #       零 schema、零 OG、零面包屑，正文仅 hero 两句 + 卡片宫格（薄内容），
    #       且 19 个子类目在枢纽层不可见，只能从父分类页进入。
    # 目标：① 搜索引擎能理解"这是覆盖 N 个分类 / M 款工具的集合页"；
    #       ② AI 引擎（豆包/Kimi/元宝/ChatGPT）能直接抽取分类事实作答并引用本站。
    # 手法：结构化事实（速查表 + ItemList）+ 直接答案段 + FAQ + 时效信号。
    # ═══════════════════════════════════════════════════════════════════════
    _today_iso = _dt_build.now().strftime('%Y-%m-%d')
    _SITE = 'https://www.aitoollab.cn'

    # 各分类典型使用场景 —— GEO 关键：让 AI 能回答"XX 场景该用哪类工具"
    category_scenes = {
        "AI对话": "日常问答、资料整理、写作与代码辅助",
        "AI写作": "公众号文案、营销稿、论文润色与改写",
        "AI绘画": "插画创作、电商配图、海报与概念设计",
        "AI编程": "代码补全、Bug修复、单元测试与重构",
        "AI视频": "短视频成片、数字人口播、字幕与剪辑",
        "AI音频": "语音合成、音频转写、配乐与降噪",
        "AI办公": "PPT生成、表格处理、会议纪要与文档总结",
        "AI设计": "UI设计、原型图、Logo与品牌视觉",
        "AI搜索": "联网搜索、文献检索、带引用来源的问答",
        "AI翻译": "文档翻译、字幕翻译、多语言本地化",
        "AI自动化": "工作流编排、数据同步、跨应用自动执行",
        "AI效率": "笔记管理、任务规划、信息聚合与提效",
        "AI智能体": "任务型Agent、自动调研、多步骤任务执行",
        "AI开发": "模型调用、向量数据库、AI应用开发框架",
        "AI行业应用": "医疗、法律、教育、电商等垂直场景",
    }

    def _top_tools(_lst, n=3):
        """按评分取该分类代表工具（GEO：具体工具名比抽象描述更易被 AI 引用）"""
        try:
            _s = sorted(_lst, key=lambda t: float(extract_rating_num(t.get('rating', '')) or 0), reverse=True)
        except Exception:
            _s = _lst
        return [t.get('name', '') for t in _s[:n] if t.get('name')]

    # ── GEO 速查表：分类 / 工具数 / 典型场景 / 代表工具 ──
    # 表格是 AI 引擎抽取引用率最高的结构，比散落的卡片有效得多
    table_rows = ''
    for cat_name in cat_names:
        _cslug = get_category_slug(cat_name)
        _clist = tools_by_category[cat_name]
        _scene = category_scenes.get(cat_name, f'{cat_name}相关场景')
        _reps = _top_tools(_clist, 3)
        _reps_txt = '、'.join(escape_html(r) for r in _reps) if _reps else '持续收录中'
        table_rows += (
            '<tr>'
            f'<td><a href="/category/{_cslug}/"><strong>{escape_html(cat_name)}</strong></a></td>'
            f'<td style="text-align:center;">{len(_clist)}</td>'
            f'<td>{escape_html(_scene)}</td>'
            f'<td>{_reps_txt}</td>'
            '</tr>\n'
        )

    # ── 子类目入口：19 个细分场景此前在枢纽页不可见（只能从父分类页进）──
    _subdef = get_subcat_def()
    subcat_block_html = ''
    _subcat_total = 0
    for _p_slug, _pdata in _subdef.items():
        _subs = _pdata.get('subcats', {})
        if not _subs:
            continue
        _subcat_total += len(_subs)
        _p_name = _pdata.get('name', _p_slug)
        _links = ''.join(
            f'<a href="/category/{_s}/" class="subcat-pill">{escape_html(_sd.get("name", ""))}</a>'
            for _s, _sd in _subs.items()
        )
        subcat_block_html += (
            f'<div class="subcat-row"><span class="subcat-parent">'
            f'<a href="/category/{_p_slug}/">{escape_html(_p_name)}</a></span>{_links}</div>\n'
        )
    subcat_section_html = ''
    if subcat_block_html:
        subcat_section_html = f'''    <section class="cat-section" id="subcats">
        <h2>按细分场景查找（{_subcat_total} 个子类目）</h2>
        <p class="cat-section-desc">主分类偏宽泛时，可直接进入更精准的细分场景页面。</p>
{subcat_block_html}    </section>
'''

    # ── FAQ（GEO 核心）：纯文本答案，同时供页面渲染与 FAQPage schema 使用 ──
    _by_size = sorted(cat_names, key=lambda c: len(tools_by_category[c]), reverse=True)
    _top5_txt = '、'.join(f'{c}（{len(tools_by_category[c])}款）' for c in _by_size[:5])
    _all_cats_txt = '、'.join(cat_names)
    faq_items = [
        (
            "AI工具一共分为哪些类别？",
            f"AI工具宝箱把收录的 {total_tools} 款 AI 工具划分为 {total_cats} 个主分类，"
            f"分别是：{_all_cats_txt}。其中工具数量最多的是 {_top5_txt}。"
            f"每个主分类下还有更细的子类目，可按具体使用场景进一步筛选。"
        ),
        (
            "新手第一次用AI工具，应该从哪一类开始？",
            "建议从 AI对话 类工具入手，这类工具通用性最强，问答、写作、翻译、代码解释都能覆盖，"
            "无需学习成本。熟悉之后再按你的具体工作场景切入垂直分类：做内容选 AI写作、做图选 AI绘画、"
            "写代码选 AI编程、做汇报选 AI办公。"
        ),
        (
            "这些AI工具分类里有免费的吗？",
            "有。绝大多数分类都同时收录免费与付费工具，常见形式是免费额度加付费订阅。"
            "每款工具的详情页都标注了价格模式（免费/免费试用/付费），分类页支持按评分与热度排序，"
            "可优先查看标注免费的工具。"
        ),
        (
            "怎么快速找到最适合自己的AI工具？",
            "三个办法：一是用本页的分类速查表，按典型使用场景直接定位分类；"
            "二是进入子类目页，场景更精准；三是使用站内的 AI 工具选择器，回答几个问题后由系统推荐。"
            "如果已经锁定两三款候选，可以看对比页做横向比较。"
        ),
        (
            "分类和工具库多久更新一次？",
            f"工具库每日更新，分类结构随新工具收录动态调整。本页数据最后更新于 {_today_iso}，"
            f"当前共 {total_cats} 个主分类、{_subcat_total} 个子类目、{total_tools} 款工具。"
        ),
    ]
    faq_html = ''.join(
        f'<details class="cat-faq-item"><summary>{escape_html(_q)}</summary>'
        f'<div class="cat-faq-a"><p>{escape_html(_a)}</p></div></details>\n'
        for _q, _a in faq_items
    )

    # 新手入口分类：优先 AI对话（通用性最强），缺失时退回工具数最多的分类
    # 注意 slug 由 get_category_slug 生成（AI对话 → ai-chat），不可硬编码拼音
    _entry_cat = "AI对话" if "AI对话" in tools_by_category else (_by_size[0] if _by_size else "")
    _entry_link = (
        f'<a href="/category/{get_category_slug(_entry_cat)}/">{escape_html(_entry_cat)}</a>'
        if _entry_cat else '任一主分类'
    )

    # ── 结构化数据：用 json.dumps 生成，避免 f-string 大括号转义出错 ──
    _breadcrumb_sd = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": f"{_SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "AI工具分类", "item": f"{_SITE}/category/"},
        ],
    }
    _collection_sd = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"AI工具推荐与导航大全 - {total_cats}大分类{total_tools}款AI工具",
        "description": f"AI工具宝箱按使用场景划分的 {total_cats} 个 AI 工具分类，"
                       f"共收录 {total_tools} 款工具，覆盖对话、写作、绘画、编程、视频等全领域。",
        "url": f"{_SITE}/category/",
        "inLanguage": "zh-CN",
        "dateModified": _today_iso,
        "isPartOf": {"@type": "WebSite", "name": "AI工具宝箱", "url": f"{_SITE}/"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱", "url": f"{_SITE}/"},
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": [".geo-answer", ".cat-section h2"],
        },
        "mainEntity": {
            "@type": "ItemList",
            "name": f"AI工具{total_cats}大分类",
            "numberOfItems": total_cats,
            "itemListOrder": "https://schema.org/ItemListOrderDescending",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": _i + 1,
                    "name": f"{_c}工具",
                    "url": f"{_SITE}/category/{get_category_slug(_c)}/",
                    "description": f"{category_scenes.get(_c, _c + '相关场景')}，"
                                   f"收录 {len(tools_by_category[_c])} 款工具。",
                }
                for _i, _c in enumerate(_by_size)
            ],
        },
    }
    _faq_sd = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": _q,
                "acceptedAnswer": {"@type": "Answer", "text": _a},
            }
            for _q, _a in faq_items
        ],
    }
    _breadcrumb_json = json.dumps(_breadcrumb_sd, ensure_ascii=False)
    _collection_json = json.dumps(_collection_sd, ensure_ascii=False)
    _faq_json = json.dumps(_faq_sd, ensure_ascii=False)

    # ── Title / Description（2026-08-03 重写）──
    # 说明：站内未接关键词工具，以下词根为经验判断（覆盖"分类/大全/导航/合集"四类
    #       常见搜法 + 数字增强点击率），非搜索量数据验证结果。接入 GSC 后应回头校准。
    _page_title = f'AI工具推荐与导航大全 {total_cats}大分类 {total_tools}款 {build.BUILD_YEAR}'
    _page_desc = (f'{build.BUILD_YEAR}年AI工具推荐与导航大全：按使用场景划分为{total_cats}个主分类、'
                  f'{_subcat_total}个细分场景，共收录{total_tools}款AI工具（含免费工具）。'
                  f'涵盖AI对话、AI写作、AI绘画、AI视频、AI编程等全领域，'
                  f'每个分类附工具数量、典型场景与代表工具，帮你快速定位需要的AI工具。')
    _page_kw = (f'AI工具推荐,AI工具导航,AI工具大全,AI工具分类,AI工具有哪些,'
                f'AI软件分类,AI工具推荐{build.BUILD_YEAR},免费AI工具')

    # ── 页面内联样式：hot-mini（对齐首页热门榜 TOP30）+ 分类宫格容器 ──
    # 注意：固定宽度（沿用 .cat-grid 原样式 max-width:960px 居中），不做全屏自动宽度
    page_css = '''<style id="cat-page-hot-mini-style">
#catMiniGrid {
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
  #catMiniGrid { grid-template-columns: repeat(auto-fill, minmax(98px, 1fr)); gap: 10px 8px; padding: 0 14px; }
  .hot-mini-name { font-size: 12px; }
}
/* ── SEO+GEO 区块样式（2026-08-03 新增）── */
.cat-section {
  max-width: 960px; margin: 28px auto 0; padding: 0 14px;
}
.cat-section h2 {
  font-size: 20px; font-weight: 700; margin: 0 0 8px;
}
.cat-section-desc {
  font-size: 14px; color: var(--text-muted, #64748b); margin: 0 0 14px; line-height: 1.7;
}
.geo-answer {
  max-width: 960px; margin: 20px auto 0; padding: 16px 18px;
  background: rgba(0,166,79,0.06);
  border: 1px solid rgba(0,166,79,0.22);
  border-left: 4px solid #00A64F;
  border-radius: 10px; font-size: 15px; line-height: 1.85;
}
.geo-answer strong { color: #00A64F; }
.cat-table-wrap { overflow-x: auto; }
.cat-table {
  width: 100%; border-collapse: collapse; font-size: 14px;
  background: rgba(127,127,127,0.03); border-radius: 10px; overflow: hidden;
}
.cat-table th, .cat-table td {
  padding: 10px 12px; text-align: left;
  border-bottom: 1px solid rgba(127,127,127,0.14);
}
.cat-table th {
  background: rgba(127,127,127,0.08); font-weight: 600; white-space: nowrap;
}
.cat-table tr:last-child td { border-bottom: none; }
.cat-table a { color: #00A64F; text-decoration: none; }
.cat-table a:hover { text-decoration: underline; }
.subcat-row {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
  padding: 9px 0; border-bottom: 1px dashed rgba(127,127,127,0.18);
}
.subcat-row:last-child { border-bottom: none; }
.subcat-parent {
  min-width: 96px; font-weight: 600; font-size: 13.5px;
}
.subcat-parent a { color: inherit; text-decoration: none; }
.subcat-pill {
  display: inline-block; padding: 3px 11px; border-radius: 20px;
  background: rgba(58,91,217,0.08); border: 1px solid rgba(58,91,217,0.18);
  color: #3a5bd9; text-decoration: none; font-size: 12.5px;
}
.subcat-pill:hover { background: rgba(58,91,217,0.16); }
.cat-faq-item {
  border: 1px solid rgba(127,127,127,0.16); border-radius: 10px;
  margin-bottom: 8px; background: rgba(127,127,127,0.03);
}
.cat-faq-item summary {
  cursor: pointer; padding: 12px 16px; font-weight: 600; font-size: 14.5px;
  list-style: none;
}
.cat-faq-item summary::-webkit-details-marker { display: none; }
.cat-faq-item summary::before { content: "Q "; color: #00A64F; font-weight: 700; }
.cat-faq-a { padding: 0 16px 14px; font-size: 14px; line-height: 1.85; color: var(--text-muted, #475569); }
.cat-faq-a p { margin: 0; }
.cat-updated {
  max-width: 960px; margin: 18px auto 0; padding: 0 14px;
  font-size: 12.5px; color: var(--text-muted, #94a3b8);
}
@media (max-width: 640px) {
  .cat-section h2 { font-size: 18px; }
  .cat-table th, .cat-table td { padding: 8px 9px; font-size: 13px; }
  .subcat-parent { min-width: 100%; }
}
</style>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(_page_title)}</title>
    <meta name="description" content="{escape_html(_page_desc)}">
    <meta name="keywords" content="{escape_html(_page_kw)}">
    <link rel="canonical" href="{_SITE}/category/">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{escape_html(_page_title)}">
    <meta property="og:description" content="{escape_html(_page_desc)}">
    <meta property="og:url" content="{_SITE}/category/">
    <meta property="og:image" content="{_SITE}/images/og/aitoolbox-og.png">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:locale" content="zh_CN">
    <meta property="og:site_name" content="AI工具宝箱">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(_page_title)}">
    <meta name="twitter:description" content="{escape_html(_page_desc)}">
    <meta name="twitter:image" content="{_SITE}/images/og/aitoolbox-og.png">
    <style>{build.CRITICAL_CSS}</style>
{page_css}
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript>
    <script type="application/ld+json">{_breadcrumb_json}</script>
    <script type="application/ld+json">{_collection_json}</script>
    <script type="application/ld+json">{_faq_json}</script>
{build.BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <span>AI工具分类</span>
    </nav>

    <div class="cat-hero">
        <h1>📂 AI工具分类大全</h1>
        <p>共 <strong>{total_cats}</strong> 个主分类 · <strong>{_subcat_total}</strong> 个细分场景 · 收录 <strong>{total_tools}</strong> 款工具</p>
        <p>按场景挑选，点击进入查看该分类下全部工具的评测与对比。</p>
    </div>

    <div class="geo-answer">
        <p>AI工具宝箱把目前收录的 <strong>{total_tools} 款 AI 工具</strong>按使用场景划分为
        <strong>{total_cats} 个主分类</strong>与 <strong>{_subcat_total} 个细分子类目</strong>。
        主分类包括{escape_html(_all_cats_txt)}。
        如果你不确定该从哪里开始，通用场景优先看 {_entry_link}，
        再按具体工作内容进入垂直分类；下方速查表列出了每个分类的工具数量、典型使用场景与代表工具。</p>
    </div>

    <div class="cat-grid" id="catMiniGrid">
{cards_html}    </div>

    <section class="cat-section" id="cat-table">
        <h2>AI工具分类速查表（{total_cats}大分类对照）</h2>
        <p class="cat-section-desc">按典型使用场景快速定位分类，代表工具按用户评分排序。</p>
        <div class="cat-table-wrap">
        <table class="cat-table">
            <thead>
                <tr><th>分类</th><th>工具数</th><th>典型使用场景</th><th>代表工具</th></tr>
            </thead>
            <tbody>
{table_rows}            </tbody>
        </table>
        </div>
    </section>

{subcat_section_html}    <section class="cat-section" id="faq">
        <h2>关于AI工具分类的常见问题</h2>
{faq_html}    </section>

    <p class="cat-updated">本页数据最后更新：{_today_iso} · 工具库每日更新</p>

    <div class="cat-back">
        <a href="/">← 返回首页，查看更多精选工具</a>
    </div>
    <footer class="footer">
        <p>© {build.BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · {build.ICP_BEIAN}</p>
        <div class="footer-links">
            <a href="/about.html">关于我们</a>
            <a href="/contact.html">联系方式</a>
            <a href="/privacy.html">隐私政策</a>
            <a href="/links.html">友情链接</a>
        </div>
        <p>用AI提升效率，让每个人都能享受技术红利。</p>
    </footer>
    {build.BACK_TO_TOP_BLOCK}
</body>
</html>'''
    return html

def get_subcat_def():
    import build  # 延迟：build 完全加载后解析
    """加载子类目定义 data/subcategories.json → {parent_slug:{name, subcats:{slug:{name,intro,how_to_choose}}}}"""
    if 'subcat_def_cache' not in globals():
        try:
            with open(os.path.join(build.DATA_DIR, 'subcategories.json'), 'r', encoding='utf-8') as f:
                globals()['subcat_def_cache'] = json.load(f)
        except Exception:
            globals()['subcat_def_cache'] = {}
    return globals()['subcat_def_cache']

def build_category_page(category_name, tools_in_category, all_categories=None):
    import build  # 延迟：build 完全加载后解析
    """生成单个分类页的完整HTML

    all_categories: {分类名: [工具]} —— 仅用于生成横向互链（相关分类），可为空。
    """
    category_slug = get_category_slug(category_name)
    
    # 加载分类导言（P0-6）
    try:
        intros_path = os.path.join(build.DATA_DIR, 'category_intros.json')
        if 'category_intros_cache' not in globals():
            with open(intros_path, 'r', encoding='utf-8') as f:
                globals()['category_intros_cache'] = json.load(f)
        category_intros = globals()['category_intros_cache']
    except:
        category_intros = {}
    
    tools_html = ''
    for i, t in enumerate(tools_in_category):
        tools_html += make_tool_card_html(t, i)

    # 子类目导航（仅在当前分类有子类时注入；扁平独立页，非JS tab）
    _subcat_nav_html = ''
    _subdef = get_subcat_def()
    if category_slug in _subdef:
        _sub_links = ''.join(
            f'<a href="/category/{s}/" class="subcat-link" style="display:inline-block;margin:2px 6px 2px 0;padding:4px 12px;background:#eef2fb;border:1px solid #dde4f3;border-radius:20px;color:#3a5bd9;text-decoration:none;font-size:13px;">{escape_html(sd.get("name",""))}</a>'
            for s, sd in _subdef[category_slug].get('subcats', {}).items()
        )
        if _sub_links:
            _subcat_nav_html = (
                '<div class="subcat-nav" style="margin:14px 0 4px;padding:12px 16px;'
                'background:#f6f8fc;border:1px solid #e6ebf3;border-radius:10px;'
                'font-size:14px;color:#556;">按场景筛选：' + _sub_links + '</div>'
            )

    # 分类页H1：强制带"工具"实体词 + 导言插槽（P0-6）
    _cat_h1 = category_name if category_name.endswith('工具') else category_name + '工具'
    # 分类导言：从 JSON 读取，无则用默认占位
    _cat_intro_data = category_intros.get(category_slug, {})
    _cat_intro_html = ''
    if _cat_intro_data.get('intro'):
        _cat_intro_html += _cat_intro_data['intro']
    if _cat_intro_data.get('how_to_choose'):
        _cat_intro_html += '\n' + _cat_intro_data['how_to_choose']
    if not _cat_intro_html.strip():
        _cat_intro_html = f'<p>{build.BUILD_YEAR}年最受欢迎的 <strong>{escape_html(category_name)}工具</strong> 合集，共收录 <strong>{len(tools_in_category)}</strong> 款，覆盖免费与付费。下面按评分与热度排序，帮你快速决策。</p>'

    # ═══════════════════════════════════════════════════════════════════════
    # SEO + GEO 强化（2026-08-03）
    # 原状：CollectionPage 是空壳（无 mainEntity，AI 引擎读不到集合里有哪些工具）、
    #       无 FAQPage、无 speakable、无时效信号、主分类之间零横向互链。
    # ═══════════════════════════════════════════════════════════════════════
    _today_iso = _dt_build.now().strftime('%Y-%m-%d')
    _SITE = 'https://www.aitoollab.cn'
    _cat_n = len(tools_in_category)

    try:
        _ranked = sorted(tools_in_category,
                         key=lambda t: float(extract_rating_num(t.get('rating', '')) or 0),
                         reverse=True)
    except Exception:
        _ranked = list(tools_in_category)

    # ItemList：把集合内容显式喂给搜索/AI 引擎（此前完全缺失，是 GEO 最大短板）
    _item_elems = []
    for _i, _t in enumerate(_ranked[:20]):
        _tslug = _t.get('slug', '')
        _el = {
            "@type": "ListItem",
            "position": _i + 1,
            "name": _t.get('name', ''),
            "url": f"{_SITE}/tools/{_tslug}/" if _tslug else f"{_SITE}/category/{category_slug}/",
        }
        _td = (_t.get('description') or '').strip()
        if _td:
            _el["description"] = _td[:120]
        _item_elems.append(_el)

    _top3 = [t.get('name', '') for t in _ranked[:3] if t.get('name')]
    _top3_txt = '、'.join(_top3) if _top3 else '多款主流工具'

    # ── 分类页标题（5118 2026-08-03 核实后重写）──
    # 结论：① "{分类}工具"精确词在百度指数库多为0，真实头部词是裸分类名（AI视频指数1732等）
    #       ② 各分类真实搜索修饰词不同（制作/公文/PDF/logo/助手…），须差异化
    #       ③ 标题内括号=中性标点零排名价值但占2字符预算 → 删；「- AI工具宝箱」无品牌搜索量 → 删
    # 模板：{修饰后主体} {N}款 {build.BUILD_YEAR}，无括号、无品牌后缀
    _CAT_TITLE_BODY = {
        "AI对话": "AI对话机器人工具推荐",        # 机器人是更真实说法
        "AI写作": "AI公文写作工具推荐",          # 公文写作为热子题
        "AI视频": "AI视频制作工具推荐",          # 制作/生成，移动端巨量
        "AI绘画": "AI绘画免费在线工具推荐",      # 免费/在线
        "AI音频": "AI音频工具推荐",              # ≈0需求，裸名即可
        "AI翻译": "AI PDF翻译工具推荐",          # PDF 为热子题
        "AI搜索": "AI搜索工具推荐",              # 裸名为主，SEO优化放描述
        "AI办公": "AI办公工具推荐",              # 需求中规中矩
        "AI设计": "AI设计工具推荐",              # 改宽泛（20:55）：原"AI logo设计"与子类目ai-brand-design抢词，logo词由子类目承接
        "AI开发": "AI应用开发工具推荐",          # 应用开发
        "AI编程": "AI编程助手推荐",              # 助手是主搜索词
        "AI自动化": "AI自动化工具推荐",          # ≈0需求
        "AI效率": "AI效率工具推荐",              # ≈0需求
        "AI智能体": "AI智能体搭建工具推荐",      # 搭建/平台
        "AI行业应用": "AI行业应用工具推荐",      # ≈0需求
        "AI学习": "AI学习教程与入门网站推荐",    # 5118: AI教程指数191为类目内最高
        "AI检测": "AI检测与论文查重工具推荐",    # 5118: 论文查重808为绝对头部
        "AI提示词": "AI提示词工具与提示词库推荐", # 5118: AI提示词88/提示词143
    }
    _fallback_body = f'{category_name}工具推荐'
    # 三要素定制：category_intros.json 可覆盖 title_body（5118 核量词），无则走内置表
    _cat_title_body = (_cat_intro_data.get('title_body') or
                       _CAT_TITLE_BODY.get(category_name, _fallback_body))
    _cat_title = f"{_cat_title_body} {_cat_n}款 {build.BUILD_YEAR}"

    # FAQ（GEO 核心）：纯文本，页面与 FAQPage schema 共用
    # 三要素定制：category_intros.json 可提供 faq（[问题, 答案] 列表，5118 长尾热词），无则用通用模板
    _cat_faq_custom = _cat_intro_data.get('faq')
    if _cat_faq_custom and isinstance(_cat_faq_custom, list):
        _cat_faq = [tuple(item) for item in _cat_faq_custom if len(item) == 2]
    else:
        _cat_faq = [
            (f"{category_name}工具哪个好用？",
             f"本页收录的 {_cat_n} 款{category_name}工具按用户评分排序，综合评分靠前的是{_top3_txt}。"
             f"具体选哪款取决于你的使用场景和预算，建议先看排在前面的几款的详情页，"
             f"对比功能覆盖、价格模式与上手难度后再决定。"),
            (f"有免费的{category_name}工具吗？",
             f"有。{category_name}分类下同时收录免费与付费工具，常见形式是提供免费额度后再按需订阅。"
             f"每款工具的详情页都标注了价格模式（免费/免费试用/付费），可据此筛选。"),
            (f"怎么挑选适合自己的{category_name}工具？",
             f"三步走：先明确核心需求（要解决什么具体问题），再看工具是否覆盖该场景；"
             f"然后对比价格模式，优先选有免费额度的先试用；最后看实际体验，"
             f"包括中文支持、响应速度和导出格式是否满足要求。"),
            (f"这里收录了多少款{category_name}工具？多久更新？",
             f"当前共收录 {_cat_n} 款{category_name}工具，最后更新于 {_today_iso}。"
             f"工具库每日更新，新工具上线后会同步补充到对应分类。"),
        ]
    _faq_html = ''.join(
        f'<details style="border:1px solid rgba(127,127,127,0.16);border-radius:10px;'
        f'margin-bottom:8px;background:rgba(127,127,127,0.03);">'
        f'<summary style="cursor:pointer;padding:12px 16px;font-weight:600;font-size:14.5px;">'
        f'{escape_html(_q)}</summary>'
        f'<div style="padding:0 16px 14px;font-size:14px;line-height:1.85;color:#475569;">'
        f'<p style="margin:0;">{escape_html(_a)}</p></div></details>\n'
        for _q, _a in _cat_faq
    )
    _faq_section_html = (
        f'<section class="cat-faq" style="margin-top:28px;">'
        f'<h2 style="font-size:20px;font-weight:700;margin:0 0 12px;">'
        f'关于{escape_html(category_name)}工具的常见问题</h2>\n{_faq_html}</section>'
    )

    # 横向互链：主分类之间此前零互链，链接权重只能"子页→枢纽"单向流动
    _related_html = ''
    if all_categories:
        _others = [(c, len(ts)) for c, ts in all_categories.items()
                   if c != category_name and ts]
        _others.sort(key=lambda x: x[1], reverse=True)
        _picked = _others[:8]
        if _picked:
            _pills = ''.join(
                f'<a href="/category/{get_category_slug(_c)}/" '
                f'style="display:inline-block;margin:3px 6px 3px 0;padding:5px 13px;'
                f'background:rgba(58,91,217,0.08);border:1px solid rgba(58,91,217,0.18);'
                f'border-radius:20px;color:#3a5bd9;text-decoration:none;font-size:13px;">'
                f'{escape_html(_c)} <span style="opacity:.6;">{_n}</span></a>'
                for _c, _n in _picked
            )
            _related_html = (
                f'<section class="related-cats" style="margin-top:26px;">'
                f'<h2 style="font-size:18px;font-weight:700;margin:0 0 10px;">浏览其他AI工具分类</h2>'
                f'<div>{_pills}</div>'
                f'<p style="margin-top:10px;font-size:13.5px;">'
                f'<a href="/category/" style="color:#00A64F;">查看全部AI工具分类 →</a></p>'
                f'</section>'
            )

    # 结构化数据：用 json.dumps 生成，避免 f-string 大括号转义出错
    _cat_breadcrumb_sd = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": f"{_SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "全部AI工具", "item": f"{_SITE}/tools/"},
            {"@type": "ListItem", "position": 3, "name": category_name,
             "item": f"{_SITE}/category/{category_slug}/"},
        ],
    }
    _cat_collection_sd = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": _cat_title,
        "description": f"AI工具宝箱收录的 {_cat_n} 款{category_name}工具合集，"
                       f"按评分与热度排序，含免费与付费方案对比。",
        "url": f"{_SITE}/category/{category_slug}/",
        "inLanguage": "zh-CN",
        "dateModified": _today_iso,
        "isPartOf": {"@type": "WebSite", "name": "AI工具宝箱", "url": f"{_SITE}/"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱", "url": f"{_SITE}/"},
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": [".geo-answer", ".category-intro", ".cat-faq h2"],
        },
        "mainEntity": {
            "@type": "ItemList",
            "name": f"{category_name}工具榜单",
            "numberOfItems": _cat_n,
            "itemListOrder": "https://schema.org/ItemListOrderDescending",
            "itemListElement": _item_elems,
        },
    }
    _cat_faq_sd = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": _q,
             "acceptedAnswer": {"@type": "Answer", "text": _a}}
            for _q, _a in _cat_faq
        ],
    }
    _cat_bc_json = json.dumps(_cat_breadcrumb_sd, ensure_ascii=False)
    _cat_cp_json = json.dumps(_cat_collection_sd, ensure_ascii=False)
    _cat_fq_json = json.dumps(_cat_faq_sd, ensure_ascii=False)

    # 三要素定制：category_intros.json 可提供 keywords（5118 相关词），无则用内置模板
    _cat_kw_custom = _cat_intro_data.get('keywords')
    if _cat_kw_custom and isinstance(_cat_kw_custom, list):
        _cat_meta_kw = ','.join(_cat_kw_custom)
    else:
        _cat_meta_kw = (f'{category_name},{category_name}工具,{category_name}软件,免费{category_name},'
                        f'AI工具,{category_name}推荐{build.BUILD_YEAR},AI导航')

    # 2026-08-13（阶段2.3）：分类页描述过短（Bing 阈值约 110 字符）时用分类导言真实内容补足
    _cat_meta = (f'{build.BUILD_YEAR}年最新{category_name}工具合集，收录{len(tools_in_category)}款免费及付费'
                 f'{category_name}软件。包含ChatGPT、Claude等主流AI工具，按评分和热度排名，'
                 f'附使用教程、价格与免费额度及对比评测，数据每日更新，帮你找到最适合的{category_name}工具。')
    if len(_cat_meta) < 115 and _cat_intro_html:
        _cat_plain = re.sub(r'<[^>]+>', '', _cat_intro_html)
        _cat_plain = re.sub(r'\s+', '', _cat_plain).strip(' ：:。.，,；;')
        if _cat_plain:
            _cat_meta = (_cat_meta + '。' + _cat_plain)[:160]

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(_cat_title)}</title>
    <meta name="description" content="{escape_html(_cat_meta)}">
    <meta name="keywords" content="{escape_html(_cat_meta_kw)}">
    <link rel="canonical" href="https://www.aitoollab.cn/category/{category_slug}/">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{escape_html(_cat_title)}">
    <meta property="og:description" content="{escape_html(_cat_meta)}">
    <meta property="og:url" content="https://www.aitoollab.cn/category/{category_slug}/">
    <meta property="og:image" content="https://www.aitoollab.cn/images/og/category-{category_slug}-og.png">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(_cat_title)}">
    <meta name="twitter:description" content="{escape_html(_cat_meta)}">
    <meta name="twitter:image" content="https://www.aitoollab.cn/images/og/category-{category_slug}-og.png">
    <style>{build.CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript>
    <script type="application/ld+json">{_cat_bc_json}</script>
    <script type="application/ld+json">{_cat_cp_json}</script>
    <script type="application/ld+json">{_cat_fq_json}</script>
{build.BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/tools/">全部AI工具</a> &gt; <span>{escape_html(category_name)}</span>
    </nav>

    <main class="container">
        <section class="section">
            <div class="section-header">
                <h1>{escape_html(_cat_h1)}</h1>
            </div>
            <div class="geo-answer" style="margin:14px 0 6px;padding:14px 18px;background:linear-gradient(135deg,#f0fdf4,#ecfdf5);border:1px solid #bbf7d0;border-left:4px solid #22c55e;border-radius:10px;font-size:14.5px;line-height:1.9;color:#14532d;">
                <strong>{escape_html(category_name)}工具是什么？</strong> {escape_html(category_name)}工具指借助大模型与生成式AI完成各类任务的软件服务，本站按用户评分与热度收录 <strong>{_cat_n}</strong> 款，综合评分靠前的有 <strong>{_top3_txt}</strong>，多数提供免费额度，可对比功能与价格后选用。
            </div>
            <div class="category-intro">
{_cat_intro_html}
            </div>
            {_subcat_nav_html}
            <div class="tools-grid">
{tools_html}
            </div>
{_faq_section_html}
{_related_html}
            <p style="margin-top:18px;font-size:12.5px;color:#94a3b8;">本页最后更新：{_today_iso} · 工具库每日更新</p>
        </section>
    </main>

    <footer class="footer">
        <p>© {build.BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · ''' + build.ICP_BEIAN + '''</p>
    </footer>
    ''' + build.BACK_TO_TOP_BLOCK + '''
</body>
</html>'''
    return html

def build_subcategory_page(parent_slug, parent_name, subcat_slug, subcat_data, tools_in_subcat, parent_count=0):
    import build  # 延迟：build 完全加载后解析
    """生成子类目独立页（独立SEO入口，扁平URL：/category/{subcat_slug}/）"""
    subcat_name = subcat_data.get('name', '')
    _h1 = subcat_name if subcat_name.endswith('工具') else subcat_name + '工具'

    _intro = subcat_data.get('intro', '')
    _how = subcat_data.get('how_to_choose', '')
    _intro_html = (_intro + ('\n' + _how if _how else '')) or \
        f'<p>{build.BUILD_YEAR}年最新的 <strong>{escape_html(subcat_name)}工具</strong> 合集，共收录 <strong>{len(tools_in_subcat)}</strong> 款，按评分与热度排序，帮你快速决策。</p>'

    # 子类页顶部导航：返回类目根 + 按场景切换（修复"跳转后丢失场景筛选/无法返回根"问题）
    _subcat_nav_html = ''
    _subdef = get_subcat_def()
    if parent_slug in _subdef:
        _sibs = _subdef[parent_slug].get('subcats', {})
        if _sibs:
            _pills = ''
            for _s, _sd in _sibs.items():
                _nm = escape_html(_sd.get('name', ''))
                if _s == subcat_slug:
                    _pills += (f'<a href="/category/{_s}/" class="subcat-link" '
                               f'style="display:inline-block;margin:2px 6px 2px 0;padding:4px 12px;'
                               f'background:#00A64F;border:1px solid #00A64F;border-radius:20px;'
                               f'color:#fff;text-decoration:none;font-size:13px;font-weight:600;">{_nm} ✓</a>')
                else:
                    _pills += (f'<a href="/category/{_s}/" class="subcat-link" '
                               f'style="display:inline-block;margin:2px 6px 2px 0;padding:4px 12px;'
                               f'background:#eef2fb;border:1px solid #dde4f3;border-radius:20px;'
                               f'color:#3a5bd9;text-decoration:none;font-size:13px;">{_nm}</a>')
            _back = (f'<a href="/category/{parent_slug}/" class="subcat-back" '
                     f'style="display:inline-block;margin-bottom:8px;font-weight:600;color:#00A64F;'
                     f'text-decoration:none;font-size:14px;">'
                     f'← 返回{parent_name}' + (f'（共{parent_count}款）' if parent_count else '') + '</a>')
            _subcat_nav_html = (
                '<div class="subcat-nav" style="margin:14px 0 4px;padding:12px 16px;'
                'background:#f6f8fc;border:1px solid #e6ebf3;border-radius:10px;'
                'font-size:14px;color:#556;">' + _back +
                '<div style="margin-top:8px;">按场景筛选：' + _pills + '</div></div>'
            )

    tools_html = ''.join(make_tool_card_html(t, i) for i, t in enumerate(tools_in_subcat))

    # ═══════════════════════════════════════════════════════════════════════
    # SEO + GEO 强化（2026-08-03）：与主分类页同口径
    # 原状：空壳 CollectionPage（无 mainEntity）、无 FAQPage、无 speakable、
    #       无时效信号、缺 Twitter 卡。
    # ═══════════════════════════════════════════════════════════════════════
    _today_iso = _dt_build.now().strftime('%Y-%m-%d')
    _SITE = 'https://www.aitoollab.cn'
    _sub_n = len(tools_in_subcat)

    # ── 子类目标题（5118 Batch3-5 核实：通用大词竞争激烈，走"长尾优先 + 主词保护"策略）──
    # 三个大词子类目（logo设计/视频剪辑软件/UI设计 指数 464/729/351，正面竞争打不过剪映/PR/设计公司）：
    # 标题保留主词建立相关性（保护主关键词），同时用竞争小的 AI 长尾（免费在线生成/免费/AI剪辑/工具）吃量。
    # 其余子类目走通用模板（无括号无品牌后缀）。
    _SUB_TITLE_OVERRIDE = {
        # ── 3 个金矿（通用大词，长尾优先+主词保护；5118 Batch5）──
        "ai-brand-design": (
            f"AI logo设计工具推荐 免费在线生成 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI logo设计工具合集：收录{_sub_n}款AI logo生成器与免费在线logo设计软件，"
            f"支持AI一键生成品牌logo，按评分与热度排序，帮你快速完成logo设计。"
        ),
        "ai-video-editing": (
            f"AI视频剪辑软件推荐 免费 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI视频剪辑软件合集：收录{_sub_n}款免费AI剪辑工具，"
            f"支持AI视频剪辑、自动字幕、一键成片，替代传统视频剪辑软件，按评分与热度排序。"
        ),
        "ai-ui-design": (
            f"AI UI设计工具推荐 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI UI设计工具合集：收录{_sub_n}款AI界面设计软件，"
            f"支持UI设计、原型设计、在线协作，帮你快速完成App与网页界面设计，按评分与热度排序。"
        ),
        # ── 4 个命名对齐（真实说法指数 > 站内命名；5118 Batch3/4/5）──
        "ai-customer-service": (
            f"AI智能客服工具推荐 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI智能客服工具合集：收录{_sub_n}款AI客服机器人、在线客服系统与电商客服软件，"
            f"支持智能应答、自动回复，按评分与热度排序，帮你搭建高效客服体系。"
        ),
        "ai-robot": (
            f"AI聊天机器人工具推荐 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI聊天机器人工具合集：收录{_sub_n}款聊天机器人、外呼/电话/语音机器人软件，"
            f"支持多轮对话与自动化外呼，按评分与热度排序，适用于客服与营销场景。"
        ),
        "ai-image-editing": (
            f"AI修图工具推荐 免费在线 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI修图工具合集：收录{_sub_n}款免费在线AI图片处理软件，"
            f"支持一键修图、老照片修复、人像美化、图片编辑，按评分与热度排序，帮你快速完成图片处理。"
        ),
        "ai-security": (
            f"AI检测工具推荐 AIGC检测 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI检测工具合集：收录{_sub_n}款AIGC检测、AI率检测软件，"
            f"支持论文查重、内容真伪识别与免费AIGC检测，按评分与热度排序，帮你判断内容是否由AI生成。"
        ),
        # ── 6 个中机会（真实长尾词有量；5118 Batch5）──
        "ai-seo": (
            f"AI SEO工具推荐 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI SEO工具合集：收录{_sub_n}款AI搜索引擎优化软件，"
            f"支持关键词分析、排名查询、SEO综合查询与百度SEO优化，按评分与热度排序，帮你提升网站流量。"
        ),
        "ai-grammar": (
            f"AI语法检查工具推荐 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI语法检查工具合集：收录{_sub_n}款英语语法检查、AI润色与写作校对软件，"
            f"支持在线检查语法错误与润色改写，按评分与热度排序，帮你写出地道的英文。"
        ),
        "ai-marketing-copy": (
            f"AI文案工具推荐 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI文案工具合集：收录{_sub_n}款AI文案生成器与营销文案软件，"
            f"支持小红书文案、广告文案、标题生成，按评分与热度排序，帮你快速产出爆款文案。"
        ),
        "ai-content-writing": (
            f"AI写作助手工具推荐 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI写作助手合集：收录{_sub_n}款智能写作工具，"
            f"支持文章生成、续写、改写与润色，按评分与热度排序，帮你高效完成内容创作，从短文案到长文输出都适用。"
        ),
        "ai-finance": (
            f"AI炒股工具推荐 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI炒股与金融工具合集：收录{_sub_n}款AI理财、量化分析与智能投顾软件，"
            f"支持行情分析、AI选股，按评分与热度排序，助你理性投资。"
        ),
        "ai-recruitment": (
            f"AI面试工具推荐 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI面试工具合集：收录{_sub_n}款AI面试官、模拟面试与智能招聘软件，"
            f"支持AI面试题库、人才筛选，按评分与热度排序，帮你高效完成招聘。"
        ),
        # ── 6 个有量子类目（标题织入真实词；5118 Batch4/5）──
        "ai-legal": (
            f"法律AI工具推荐 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年法律AI工具合集：收录{_sub_n}款AI法律助手、法律大模型与法律文书软件，"
            f"支持合同审查、法律咨询，按评分与热度排序，助你快速处理法律事务。"
        ),
        "ai-medical": (
            f"AI医疗工具推荐 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI医疗工具合集：收录{_sub_n}款医疗AI与医学大模型软件，"
            f"支持辅助诊断、健康咨询，按评分与热度排序，助你了解医疗AI应用，从辅助诊断到健康咨询全面覆盖。"
        ),
        "ai-education": (
            f"AI教育工具推荐 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI教育工具合集：收录{_sub_n}款AI学习与智能教育软件，"
            f"支持AI教学、学习辅导、教育机器人，按评分与热度排序，帮你提升学习效率。"
        ),
        "ai-video-generation": (
            f"AI视频生成工具推荐 免费 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI视频生成工具合集：收录{_sub_n}款免费文生视频与AI视频生成软件，"
            f"支持文本生成视频、数字人播报，按评分与热度排序，帮你快速制作视频。"
        ),
        "ai-digital-human": (
            f"AI数字人工具推荐 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI数字人工具合集：收录{_sub_n}款虚拟数字人制作软件，"
            f"支持数字人直播、带货、客服与播报，按评分与热度排序，帮你打造专属数字分身。"
        ),
        "ai-graphic-design": (
            f"AI平面设计工具推荐 {_sub_n}款 {build.BUILD_YEAR}",
            f"{build.BUILD_YEAR}年AI平面设计工具合集：收录{_sub_n}款AI设计软件与在线海报工具，"
            f"支持海报设计、平面排版、电商素材，按评分与热度排序，帮你快速完成视觉设计。"
        ),
    }
    # geo-answer 实体词：优先用定制主词（与标题一致），无定制时用站内名
    # 例：标题"AI修图工具推荐" → geo-answer 应为"AI修图工具是什么？"而非"AI图像处理工具是什么？"
    _SUB_GEO_NAME = {
        "ai-brand-design": "AI logo设计",
        "ai-video-editing": "AI视频剪辑",
        "ai-ui-design": "AI UI设计",
        "ai-customer-service": "AI智能客服",
        "ai-robot": "AI聊天机器人",
        "ai-image-editing": "AI修图",
        "ai-security": "AI检测",
        "ai-seo": "AI SEO",
        "ai-grammar": "AI语法检查",
        "ai-marketing-copy": "AI文案",
        "ai-content-writing": "AI写作助手",
        "ai-finance": "AI炒股",
        "ai-recruitment": "AI面试",
        "ai-legal": "法律AI",
        "ai-medical": "AI医疗",
        "ai-education": "AI教育",
        "ai-video-generation": "AI视频生成",
        "ai-digital-human": "AI数字人",
        "ai-graphic-design": "AI平面设计",
    }
    _sub_geo_name = _SUB_GEO_NAME.get(subcat_slug, escape_html(subcat_name))

    _sub_override = _SUB_TITLE_OVERRIDE.get(subcat_slug)
    if _sub_override:
        _sub_title, _sub_desc = _sub_override
    else:
        _sub_title = f"{_sub_n}款{escape_html(subcat_name)}工具推荐 {build.BUILD_YEAR}"
        _sub_desc = (f"{build.BUILD_YEAR}年最新{escape_html(subcat_name)}工具合集，"
                     f"收录{_sub_n}款免费及付费{escape_html(subcat_name)}软件。"
                     f"按评分和热度排名，附使用教程和对比评测，"
                     f"帮你找到最适合的{escape_html(subcat_name)}工具。")
    # 2026-08-06：子类目描述统一补全（部分 override 模板偏短，消除 Bing 过短警告）
    if len(_sub_desc) < 110:
        _sub_desc = _sub_desc.rstrip('。') + ("。附价格、免费额度与真实测评，覆盖主流及国产AI工具，"
                                              "帮你快速对比选型，找到最合适的工具。")

    try:
        _sranked = sorted(tools_in_subcat,
                          key=lambda t: float(extract_rating_num(t.get('rating', '')) or 0),
                          reverse=True)
    except Exception:
        _sranked = list(tools_in_subcat)

    _sub_items = []
    for _i, _t in enumerate(_sranked[:20]):
        _tslug = _t.get('slug', '')
        _el = {
            "@type": "ListItem",
            "position": _i + 1,
            "name": _t.get('name', ''),
            "url": f"{_SITE}/tools/{_tslug}/" if _tslug else f"{_SITE}/category/{subcat_slug}/",
        }
        _td = (_t.get('description') or '').strip()
        if _td:
            _el["description"] = _td[:120]
        _sub_items.append(_el)

    _sub_top3 = [t.get('name', '') for t in _sranked[:3] if t.get('name')]
    _sub_top3_txt = '、'.join(_sub_top3) if _sub_top3 else '多款主流工具'

    _sub_faq = [
        (f"{subcat_name}工具哪个好用？",
         f"本页收录 {_sub_n} 款{subcat_name}工具，按用户评分排序，靠前的是{_sub_top3_txt}。"
         f"建议结合具体使用场景和预算，对比前几款的功能覆盖与价格模式后再决定。"),
        (f"{subcat_name}和{parent_name}有什么区别？",
         f"{subcat_name}是{parent_name}下的细分场景。{parent_name}覆盖面更广"
         f"（共 {parent_count} 款工具），而{subcat_name}只聚焦这一具体用途，"
         f"筛选结果更精准。如果需求比较宽泛，可以回到{parent_name}分类浏览全部工具。"),
        (f"这里收录了多少款{subcat_name}工具？多久更新？",
         f"当前共 {_sub_n} 款，最后更新于 {_today_iso}。工具库每日更新，"
         f"新工具上线后会同步归入对应细分场景。"),
    ]
    _sub_faq_html = ''.join(
        f'<details style="border:1px solid rgba(127,127,127,0.16);border-radius:10px;'
        f'margin-bottom:8px;background:rgba(127,127,127,0.03);">'
        f'<summary style="cursor:pointer;padding:12px 16px;font-weight:600;font-size:14.5px;">'
        f'{escape_html(_q)}</summary>'
        f'<div style="padding:0 16px 14px;font-size:14px;line-height:1.85;color:#475569;">'
        f'<p style="margin:0;">{escape_html(_a)}</p></div></details>\n'
        for _q, _a in _sub_faq
    )
    _sub_faq_section = (
        f'<section class="cat-faq" style="margin-top:28px;">'
        f'<h2 style="font-size:20px;font-weight:700;margin:0 0 12px;">'
        f'关于{escape_html(subcat_name)}工具的常见问题</h2>\n{_sub_faq_html}</section>'
    )

    _sub_bc_sd = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": f"{_SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "AI工具分类", "item": f"{_SITE}/category/"},
            {"@type": "ListItem", "position": 3, "name": parent_name,
             "item": f"{_SITE}/category/{parent_slug}/"},
            {"@type": "ListItem", "position": 4, "name": subcat_name,
             "item": f"{_SITE}/category/{subcat_slug}/"},
        ],
    }
    _sub_cp_sd = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"{_sub_n}款{subcat_name}工具推荐{build.BUILD_YEAR}",
        "description": f"AI工具宝箱收录的 {_sub_n} 款{subcat_name}工具合集，"
                       f"隶属{parent_name}分类，按评分与热度排序。",
        "url": f"{_SITE}/category/{subcat_slug}/",
        "inLanguage": "zh-CN",
        "dateModified": _today_iso,
        "isPartOf": {"@type": "WebSite", "name": "AI工具宝箱", "url": f"{_SITE}/"},
        "publisher": {"@type": "Organization", "name": "AI工具宝箱", "url": f"{_SITE}/"},
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": [".geo-answer", ".category-intro", ".cat-faq h2"],
        },
        "mainEntity": {
            "@type": "ItemList",
            "name": f"{subcat_name}工具榜单",
            "numberOfItems": _sub_n,
            "itemListOrder": "https://schema.org/ItemListOrderDescending",
            "itemListElement": _sub_items,
        },
    }
    _sub_fq_sd = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": _q,
             "acceptedAnswer": {"@type": "Answer", "text": _a}}
            for _q, _a in _sub_faq
        ],
    }
    _sub_bc_json = json.dumps(_sub_bc_sd, ensure_ascii=False)
    _sub_cp_json = json.dumps(_sub_cp_sd, ensure_ascii=False)
    _sub_fq_json = json.dumps(_sub_fq_sd, ensure_ascii=False)

    # 三要素定制：subcategories.json 子类目可提供 keywords，无则用内置模板
    _sub_kw_custom = subcat_data.get('keywords')
    if _sub_kw_custom and isinstance(_sub_kw_custom, list):
        _sub_meta_kw = ','.join(_sub_kw_custom)
    else:
        _sub_meta_kw = (f'{subcat_name},{subcat_name}工具,{subcat_name}软件,免费{subcat_name},'
                        f'AI工具,{subcat_name}推荐{build.BUILD_YEAR},AI导航')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(_sub_title)}</title>
    <meta name="description" content="{escape_html(_sub_desc)}">
    <meta name="keywords" content="{escape_html(_sub_meta_kw)}">
    <link rel="canonical" href="https://www.aitoollab.cn/category/{subcat_slug}/">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{escape_html(_sub_title)}">
    <meta property="og:description" content="{escape_html(_sub_desc)}">
    <meta property="og:url" content="https://www.aitoollab.cn/category/{subcat_slug}/">
    <meta property="og:image" content="https://www.aitoollab.cn/images/og/category-{subcat_slug}-og.png">
    <meta property="og:locale" content="zh_CN">
    <meta property="og:site_name" content="AI工具宝箱">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(_sub_title)}">
    <meta name="twitter:description" content="{escape_html(_sub_desc)}">
    <meta name="twitter:image" content="https://www.aitoollab.cn/images/og/category-{subcat_slug}-og.png">
    <style>{build.CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript>
    <script type="application/ld+json">{_sub_bc_json}</script>
    <script type="application/ld+json">{_sub_cp_json}</script>
    <script type="application/ld+json">{_sub_fq_json}</script>
{build.BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/category/{parent_slug}/">{escape_html(parent_name)}</a> &gt; <span>{escape_html(subcat_name)}</span>
    </nav>

    <main class="container">
        <section class="section">
            <div class="section-header">
                <h1>{escape_html(_h1)}</h1>
            </div>
            <div class="geo-answer" style="margin:14px 0 6px;padding:14px 18px;background:linear-gradient(135deg,#f0fdf4,#ecfdf5);border:1px solid #bbf7d0;border-left:4px solid #22c55e;border-radius:10px;font-size:14.5px;line-height:1.9;color:#14532d;">
                <strong>{_sub_geo_name}工具是什么？</strong> {_sub_geo_name}工具指借助大模型与生成式AI完成对应场景任务的软件服务，本站按用户评分与热度收录 <strong>{_sub_n}</strong> 款，综合评分靠前的有 <strong>{_sub_top3_txt}</strong>，多数提供免费额度，可对比功能与价格后选用。
            </div>
            <div class="category-intro">
{_intro_html}
            </div>
            {_subcat_nav_html}
            <div class="tools-grid">
{tools_html}
            </div>
{_sub_faq_section}
            <p style="margin-top:20px;font-size:13.5px;">
                <a href="/category/{parent_slug}/" style="color:#00A64F;">← 返回{escape_html(parent_name)}全部工具</a>
                &nbsp;·&nbsp;
                <a href="/category/" style="color:#00A64F;">查看全部AI工具分类 →</a>
            </p>
            <p style="margin-top:12px;font-size:12.5px;color:#94a3b8;">本页最后更新：{_today_iso} · 工具库每日更新</p>
        </section>
    </main>

    <footer class="footer">
        <p>© {build.BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · ''' + build.ICP_BEIAN + '''</p>
    </footer>
    ''' + build.BACK_TO_TOP_BLOCK + '''
</body>
</html>'''
    return html
