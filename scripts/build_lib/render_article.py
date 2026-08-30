# render_article.py — 文章页/列表/归档/分页/TOC/RSS
# 模块5：从 build.py 拆分（2026-08-24）
import os
import re
import json
from datetime import datetime as _dt_build

from build_lib.html_utils import (
    escape_html, markdown_to_html, extract_faq_section, shift_headings, _emit,
)
from build_lib.render_tool import (
    inject_internal_links, clean_broken_tool_links, tool_icon_html, ensure_og_image,
)
from build_lib.data_loaders import (get_category_slug,)

# 2026-08-30：文章列表卡片标签统一用 content_type 标准名（4 种），与首页 _ct_tag 一致。
# 背景：8/8 曾把 22+ 细分分类归并为 4 类 content_type，但日更脚本持续直写 category 细分值，
# 归并成果被冲掉（现仅 45/200 为标准值）。标签层不再直显原始 category，数据层暂不动。
_CT_DISPLAY = {'AI评测': 'AI工具评测', 'AI教程': 'AI实战教程', 'AI资讯': 'AI资讯', '行业分析': 'AI行业分析'}


def _article_type_label(article):
    """文章列表卡片标签：content_type → 标准显示名（兜底 AI资讯）。"""
    import build  # 延迟导入：避免循环依赖，调用时 build 已加载
    return _CT_DISPLAY.get(build.article_content_type(article), 'AI资讯')


def _get_article_description(article):
    """文章 meta description 兜底链（Fix 1）。
    优先级: description → summary → excerpt → 正文首段(去HTML标签截前100字)。
    仅填补空白字段，不截断/改写已有描述（尊重不覆盖原则）。

    2026-08-06 增强（响应 Bing Webmaster「Meta 描述过短」警告）：
    当已有描述不足 90 字时，追加正文首段真实内容，补足至 120~160 字；
    仍不覆盖已有钩子（保留首句），只是补全信息量。
    """
    import re as _re
    raw = ''
    for _f in ('description', 'summary', 'excerpt'):
        _v = (article.get(_f) or '').strip()
        if _v:
            raw = _v
            break
    if not raw:
        _content = article.get('content', '') or ''
        _plain = _re.sub(r'<[^>]+>', '', _content)
        _plain = _re.sub(r'\s+', '', _plain)
        raw = _plain[:100]
    # 描述过短 → 追加正文首段真实内容补足（保留原钩子）
    # 2026-08-13（阶段2.3）：阈值 90 → 115，覆盖 90~114 字的漏网描述
    if len(raw) < 115:
        _content = article.get('content', '') or ''
        _plain = _re.sub(r'<[^>]+>', '', _content)
        _plain = _re.sub(r'^#{1,6}[^\n]*$', '', _plain, flags=_re.M)  # 去掉 markdown 标题行
        _plain = _re.sub(r'[*_`>|#]', '', _plain)
        _plain = _re.sub(r'\s+', '', _plain).strip('：:。.，,；;')
        if _plain and _plain not in raw:
            _sep = '' if raw.endswith(('。', '！', '？')) else '。'
            raw = (raw + _sep + _plain)[:160]
        elif _plain:
            raw = _plain[:160]
    return raw

def build_article_page(article, all_articles, all_tools=None):
    import build  # 延迟：build 完全加载后解析 build 级符号
    """生成单个文章页的完整HTML"""
    slug = article['slug']

    # ── 相关工具（通过关键词匹配：标题/描述中提到哪些工具就推哪些）────
    related_tools_html = ''
    related_tools_top_html = ''
    if all_tools:
        article_title = article.get('title', '').lower()
        article_desc = article.get('excerpt', article.get('description', '')).lower()
        article_content = (article.get('content') or article.get('body', '')).lower()
        # 找工具名在文章中出现的工具（只匹配已发布工具，避免未发布工具 404）
        # 2026-08-14：匹配按相关度分三级——标题提到 > 摘要提到 > 正文提到，
        # 保证"最贴切"的工具排最前（正文工具卡只展示前 4 个）。
        # 忽略空格再比对：标题"即梦 AI"也能命中工具名"即梦AI"。
        _norm = lambda s: re.sub(r"\s+", "", s)
        article_title_n = _norm(article_title)
        article_desc_n = _norm(article_desc)
        article_content_n = _norm(article_content)
        matched_tools = []
        for _t in all_tools:
            if not _t.get('published', True):
                continue
            if _norm(_t.get('name', '').lower()) in article_title_n:
                matched_tools.append(_t)
        for _t in all_tools:
            if not _t.get('published', True) or _t in matched_tools:
                continue
            if _norm(_t.get('name', '').lower()) in article_desc_n:
                matched_tools.append(_t)
        for _t in all_tools:
            if not _t.get('published', True) or _t in matched_tools:
                continue
            if _norm(_t.get('name', '').lower()) in article_content_n:
                matched_tools.append(_t)
        # 不够5个则按分类补充（只补充已发布工具）
        if len(matched_tools) < 5:
            article_category = article.get('category', '')
            same_cat_tools = [t for t in all_tools
                             if t.get('category') == article_category
                             and t not in matched_tools
                             and t.get('published', True)]
            for t in same_cat_tools:
                if len(matched_tools) >= 5:
                    break
                matched_tools.append(t)
        # 再不够，取热门工具（只取已发布工具）
        if len(matched_tools) < 5:
            for t in sorted([x for x in all_tools if x.get('published', True)],
                            key=lambda x: x.get('visits', '0'), reverse=True):
                if len(matched_tools) >= 5:
                    break
                if t not in matched_tools:
                    matched_tools.append(t)

        if matched_tools:
            # 2026-08-15：文章页正文内工具卡从"方形居中卡"改为"紧凑横排行条"——
            # 每行 [小图标] 名称 + 分类·免费标签，桌面两列网格/移动端单列，
            # 信息密度高、无大块空白（原 related-card 方形卡 padding:18px 居中留白多）。
            def _rel_tool_row(t, with_free_tag=False):
                _is_free = '免费' in t.get('price', '') or t.get('price', '') == ''
                _tag = '<span class="rel-tag free">免费</span>' if (with_free_tag and _is_free) else ''
                return f'''<a href="/tools/{t['slug']}/" class="rel-tool-row">
                    {tool_icon_html(t, size='sm')}
                    <span class="rel-tool-name">{escape_html(t['name'])}</span>
                    <span class="rel-tool-cat">{escape_html(t.get('category', ''))}{_tag}</span>
                </a>
'''
            cards = ''.join(_rel_tool_row(t) for t in matched_tools[:4])
            # 2026-08-17：朗读守卫——卡在 data-tts 容器内，必须带 tts-skip，
            # 否则 TTS 会从"🔧 相关工具"开始读（check_tts_skip.py 部署门禁强制）
            related_tools_html = f'''<div class="related-tools tts-skip">
            <h3>🔧 相关工具</h3>
            <div class="rel-tool-row-grid">{cards}</div>
        </div>'''
            # 2026-08-18：正文上方工具卡保留，但去掉标题文字"🔧 本文提到的工具"，避免 TTS 朗读也跳过它
            top_cards = ''.join(_rel_tool_row(t, with_free_tag=True) for t in matched_tools[:4])
            related_tools_top_html = f'''<div class="related-tools article-top-tools tts-skip" style="margin:22px 0 26px;">
                <div class="rel-tool-row-grid">{top_cards}</div>
            </div>'''

    # ── 相关文章（v6.9：相关度打分 = 同内容类型 + 标题/标签词重叠 + 时效；2026-08-08 类型替代旧类目）──
    def _rel_score(cand):
        _s = 0
        if build.article_content_type(cand) == build.article_content_type(article):
            _s += 60
        _str_tags = lambda tags: [t for t in (tags or []) if isinstance(t, str)]
        _cur = article.get('title', '') + ' ' + ' '.join(_str_tags(article.get('tags')))
        _cand = cand.get('title', '') + ' ' + ' '.join(_str_tags(cand.get('tags')))
        _tok = lambda t: set(re.findall(r'[\u4e00-\u9fff]{4,}|[A-Za-z][A-Za-z0-9.\-]{3,}', t))
        _s += min(len(_tok(_cur) & _tok(_cand)), 8) * 4
        return _s

    def _rel_date(a):
        try:
            return parse_article_date(a.get('date', ''))
        except Exception:
            return ''

    related_html = ''
    _related_pool = [a for a in all_articles if a['slug'] != slug]
    _related_pool.sort(key=lambda a: (_rel_score(a), _rel_date(a)), reverse=True)
    top_related = _related_pool[:4]
    if top_related:
        cards = ''
        for a in top_related:
            cards += f'''<a href="/articles/{a['slug']}/" class="related-card">
                <div style="font-weight:600;margin-bottom:4px;">{escape_html(a['title'])}</div>
                <div style="font-size:13px;color:#666;">{a.get('dateFull', a.get('date', ''))}</div>
            </a>\n'''
        related_html = f'''<div class="related-tools">
            <h3>📖 相关文章</h3>
            <div class="related-grid">{cards}</div>
        </div>'''

    # ── 文章页侧边栏 HTML ──
    article_sidebar_tools_html = ''
    if all_tools and matched_tools:
        items = ''
        for t in matched_tools[:5]:
            is_free = '免费' in t.get('price', '') or t.get('price', '') == ''
            tag_html = ' <span class="rel-tag free">免费</span>' if is_free else ''
            items += f'''<li class="rel-tool-item">
                {tool_icon_html(t, size='sm')}
                <a href="/tools/{t['slug']}/">{t['name']}</a>{tag_html}
            </li>'''
        if items:
            article_sidebar_tools_html = f'''<div class="sidebar-card twocol-only">
                <h4>🔧 文中提到的工具</h4>
                {items}
            </div>'''

    article_sidebar_related_html = ''
    if top_related:
        items = ''
        for a in top_related[:4]:
            items += f"<li><a href='/articles/{a['slug']}/'>{escape_html(a['title'][:35])}</a></li>"
        article_sidebar_related_html = f'''<div class="sidebar-card twocol-only">
            <h4>📖 相关文章</h4>
            <ul>{items}</ul>
        </div>'''

    # OG Image（自动生成缺失的OG图片）
    og_image = ensure_og_image(slug, data_obj=article, is_article=True)

    # 信息图（文章内嵌）
    infographic_path = os.path.join(build.BASE_DIR, 'images', 'infographics', f'{slug}-infographic.png')
    has_infographic = os.path.exists(infographic_path)
    infographic_html = ''
    if has_infographic:
        infographic_html = f'''<figure class="tool-infographic">
            <img src="/images/infographics/{slug}-infographic.png" alt="{escape_html(article['title'])} - 数据对比信息图" width="1200" height="630" loading="lazy">
            <figcaption>{escape_html(article['title'])} · 核心数据一览</figcaption>
        </figure>'''

    from datetime import datetime
    today_iso = datetime.now().strftime('%Y-%m-%d')
    article_date = article.get('dateFull') or article.get('date') or today_iso
    # 将中文日期（如"2026年4月4日"）转为ISO格式（2026-04-04）
    if article_date and re.match(r'^\d{4}年\d{1,2}月\d{1,2}日$', article_date):
        m = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', article_date)
        article_date = f'{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}'
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
                "item": "https://www.aitoollab.cn/"
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": article_category,
                "item": f"https://www.aitoollab.cn/category/{article_category_slug}/"
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": article['title'],
                "item": f"https://www.aitoollab.cn/articles/{slug}/"
            }
        ]
    }
    breadcrumb_article_json = json.dumps(breadcrumb_article_data, ensure_ascii=False, indent=2)

    # 计算 wordCount（中文字符+英文单词）
    _content_for_wc = (article.get('content') or article.get('body', ''))
    import re as _re_wc
    _chinese_chars = len(_re_wc.findall(r'[\u4e00-\u9fff]', _content_for_wc))
    _english_words = len(_re_wc.findall(r'[a-zA-Z]+', _content_for_wc))
    word_count = _chinese_chars + _english_words

    # 构建增强版 Article Schema
    _article_image_url = og_image if og_image else "https://www.aitoollab.cn/images/logo.png"
    article_schema_data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article['title'],
        "description": _get_article_description(article),
        "datePublished": article_date,
        "dateModified": article_date_modified,
        "inLanguage": "zh-CN",
        "author": {
            "@type": "Organization",
            "name": "AI工具宝箱编辑组",
            "url": "https://www.aitoollab.cn/author/",
            "description": "专注 AI 工具实测与对比研究的独立编辑团队，持续追踪并实测主流 AI 工具",
            "knowsAbout": ["AI工具评测", "AI模型对比", "AEO内容优化", "GEO生成式引擎优化", "AI编程工具", "AI对话模型"]
        },
        "publisher": {
            "@type": "Organization",
            "name": "AI工具宝箱",
            "url": "https://www.aitoollab.cn/",
            "logo": {
                "@type": "ImageObject",
                "url": "https://www.aitoollab.cn/images/logo.png",
                "width": 200,
                "height": 60
            },
            "foundingDate": "2026-03-21",
            "slogan": "实测数据驱动 AI 工具决策",
            "publishingPrinciples": "https://www.aitoollab.cn/about.html",
            "sameAs": ["https://github.com/yiweichen10/ai-toolbox"]
        },
        "image": {
            "@type": "ImageObject",
            "url": _article_image_url,
            "width": 1200,
            "height": 630
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"https://www.aitoollab.cn/articles/{slug}/"
        },
        "abstract": _get_article_description(article),
        "wordCount": word_count,
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": [".article-body h2", ".article-body h3"]
        },
        "about": {
            "@type": "Thing",
            "name": article.get('category', 'AI工具'),
            "description": _get_article_description(article)[:120]
        }
    }

    # 文章页 FAQ Schema（多策略提取Q&A，覆盖各种FAQ写作格式）
    faq_article_schema = ''
    _article_faq_list = []

    # 策略1: Q/A标记匹配（支持 **Q1：**/Q：/### Q1： 等，A前缀可选）
    _faq_raw = _re_wc.findall(
        r'(?:^|\n)[*#]*\s*\*{0,2}[Qq]\d*[：:]\s*([^\n]+?)\s*\*{0,2}\n(?:\*{0,2}[Aa]\d*[：:]\s*)?(.+?)(?=\n[*#]*\s*\*{0,2}[Qq]\d*[：:]|\n## |\Z)',
        _content_for_wc, re.DOTALL
    )

    # 策略2: FAQ段中 **加粗问题？** 后跟答案（无Q前缀）
    if not _faq_raw:
        _faq_start = _content_for_wc.upper().find('FAQ')
        if _faq_start >= 0:
            _faq_section = _content_for_wc[_faq_start:]
            _faq_raw = _re_wc.findall(
                r'\*\*([^*\n]{6,100}[？?])\*\*\s*\n\s*(.+?)(?=\n\*\*[^*\n]{6,100}[？?]\*\*|\n## |\Z)',
                _faq_section, re.DOTALL
            )

    # 策略3: FAQ段中 ### 问题？ 后跟答案（无Q前缀）
    if not _faq_raw:
        _faq_start = _content_for_wc.upper().find('FAQ')
        if _faq_start >= 0:
            _faq_section = _content_for_wc[_faq_start:]
            _faq_raw = _re_wc.findall(
                r'###\s*([^\n]{6,100}[？?])\s*\n\s*(.+?)(?=\n###\s*[^\n]{6,100}[？?]|\n## |\Z)',
                _faq_section, re.DOTALL
            )

    # 策略4: FAQ段中 HTML格式 <h3>问题</h3><p>答案</p>
    if not _faq_raw:
        _faq_start = _content_for_wc.upper().find('FAQ')
        if _faq_start >= 0:
            _faq_section = _content_for_wc[_faq_start:]
            _faq_raw = _re_wc.findall(
                r'<h[34][^>]*>\s*(?:[Qq]\d*[：:]\s*)?([^<]+?)\s*</h[34]>\s*<p>(.+?)</p>',
                _faq_section, re.DOTALL
            )

    # 策略5: FAQ段中 HTML格式 <strong>Q：问题</strong><br>A：答案
    if not _faq_raw:
        _faq_start = _content_for_wc.upper().find('FAQ')
        if _faq_start >= 0:
            _faq_section = _content_for_wc[_faq_start:]
            _faq_raw = _re_wc.findall(
                r'<strong>\s*[Qq]\d*[：:]\s*([^<]+?)\s*</strong>\s*(?:<br\s*/?>)?\s*[Aa]\d*[：:]\s*(.+?)(?=<strong>\s*[Qq]\d*[：:]|</p>|\Z)',
                _faq_section, re.DOTALL
            )

    if _faq_raw:
        for _q, _a in _faq_raw:
            _q = _q.strip()
            _a = _a.strip()
            # 清理Markdown和HTML格式符号
            _q_clean = _re_wc.sub(r'\*\*', '', _q).strip()
            _q_clean = _re_wc.sub(r'<[^>]+>', '', _q_clean).strip()
            _a_clean = _re_wc.sub(r'\*\*', '', _a).strip()
            _a_clean = _re_wc.sub(r'<[^>]+>', '', _a_clean).strip()
            if _q_clean and _a_clean:
                _article_faq_list.append({
                    "@type": "Question",
                    "name": _q_clean,
                    "acceptedAnswer": {"@type": "Answer", "text": _a_clean}
                })

    # 方式2：如果没提取到，使用 article.faq 字段
    if not _article_faq_list and article.get('faq'):
        for f_item in article['faq']:
            _q = f_item.get('question') or f_item.get('q') or ''
            _a = f_item.get('answer') or f_item.get('a') or ''
            if _q.strip() and _a.strip():
                _article_faq_list.append({
                    "@type": "Question",
                    "name": _q,
                    "acceptedAnswer": {"@type": "Answer", "text": _a}
                })
    if _article_faq_list:
        faq_article_schema = f'\n    <script type="application/ld+json">{json.dumps({"@context":"https://schema.org","@type":"FAQPage","mainEntity":_article_faq_list}, ensure_ascii=False)}</script>'

        # GEO 增强: 注入 Dataset 和 citations

    # ── 文章页可见 FAQ 区块（2026-08-19）：faq 字段 → 模板 faq-section 渲染，兼容 q/a 与 question/answer ──
    # 正文已自带「常见问题」小节的旧文章不重复渲染（避免双 FAQ）；无 faq 字段的文章不渲染。
    article_faq_section_html = ''
    _article_body_raw = article.get('content') or article.get('body', '')
    if article.get('faq') and '常见问题' not in _article_body_raw:
        _visible_faq_items = []
        for _f_item in article['faq']:
            _fq = (_f_item.get('question') or _f_item.get('q') or '').strip()
            _fa = (_f_item.get('answer') or _f_item.get('a') or '').strip()
            if _fq and _fa:
                _visible_faq_items.append((_fq, _fa))
        if _visible_faq_items:
            _faq_items_html = ''.join(
                f'<div class="faq-item"><div class="faq-q">{escape_html(q)}</div><div class="faq-a">{markdown_to_html(a)}</div></div>'
                for q, a in _visible_faq_items
            )
            article_faq_section_html = (
                f'<div class="faq-section" id="faq"><h3>❓ 常见问题</h3>{_faq_items_html}</div>'
            )

    _text_lower = article.get('content', '').lower()
    
    import re as _re_cit
    if _re_cit.search(r'\[\d+\]', _text_lower) or '引用' in _text_lower:
        article_schema_data['citation'] = article_schema_data.get('citation', [])
        article_schema_data['citation'].append({
            "@type": "CreativeWork",
            "name": "参考与实测来源"
        })

    if '<table>' in _text_lower or '评测' in _text_lower or '对比' in _text_lower:
        if '@graph' not in article_schema_data:
            _self_copy = article_schema_data.copy()
            _self_copy.pop('@graph', None)
            article_schema_data.clear()
            article_schema_data['@context'] = "https://schema.org"
            article_schema_data['@graph'] = [_self_copy]
        
        article_schema_data['@graph'].append({
            "@type": "Dataset",
            "name": f"{escape_html(article['title'])} 评测数据集",
            "description": f"本文中包含的AI工具客观评测及对比数据。{escape_html(_get_article_description(article))}",
            "url": f"https://www.aitoollab.cn/articles/{slug}/",
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "creator": {
                "@type": "Organization",
                "name": "AI工具宝箱编辑组"
            }
        })
        
    structured_data = json.dumps(article_schema_data, ensure_ascii=False, indent=2)

    # D型文章（操作指南类）自动生成 HowTo Schema
    howto_schema_json = ''
    d_type_keywords = ['指南', '教程', '使用方法', '怎么用', '如何使用', '步骤', '操作', '入门', '上手', '玩法', '如何注册', '如何用']
    is_d_type = any(kw in article.get('title', '') for kw in d_type_keywords)
    if is_d_type:
        content_raw = article.get('content') or article.get('body', '')
        # 提取步骤：支持三种格式
        # 1. Markdown h2: ## 标题
        h2_steps = re.findall(r'^## (.+)$', content_raw, re.MULTILINE)
        # 2. HTML h2: <h2...>标题</h2>
        if not h2_steps:
            h2_steps = re.findall(r'<h2[^>]*>(.*?)</h2>', content_raw, re.IGNORECASE)
            # 去掉HTML标签
            h2_steps = [re.sub(r'<[^>]+>', '', h).strip() for h in h2_steps]
        # 3. 正文中的"第X步"或"步骤X"
        if not h2_steps:
            h2_steps = re.findall(r'第[一二三四五六七八九十\d]+步[：:]\s*(.+?)(?:[。\n]|$)', content_raw)
            if not h2_steps:
                h2_steps = re.findall(r'(第[一二三四五六七八九十\d]+步[：:][^\n。]{2,30})', content_raw)
        # 过滤：只保留包含步骤/操作语义的标题
        step_keywords = ['第', '步', '如何', '怎么', '注册', '安装', '配置', '创建', '部署', '使用', '设置', '登录', '上手', '入门', '操作', '技巧', '方法', '开始', '流程']
        filtered_steps = [h for h in h2_steps if any(sk in h for sk in step_keywords)]
        # 如果过滤后太少（<2步），则用所有非FAQ/总结/避坑的标题
        if len(filtered_steps) < 2:
            skip_keywords = ['FAQ', '总结', '为什么', '常见', '对比', 'vs', '避坑', '前言', '背景']
            filtered_steps = [h for h in h2_steps if not any(sk in h for sk in skip_keywords)]
        if len(filtered_steps) >= 2:
            howto_steps = []
            for i, step_title in enumerate(filtered_steps[:8], 1):  # 最多8步
                howto_steps.append({
                    "@type": "HowToStep",
                    "position": i,
                    "name": step_title,
                    "text": f"按照指南完成：{step_title}"
                })
            howto_schema = {
                "@context": "https://schema.org",
                "@type": "HowTo",
                "name": article['title'],
                "description": _get_article_description(article),
                "totalTime": "PT30M",
                "step": howto_steps
            }
            howto_schema_json = json.dumps(howto_schema, ensure_ascii=False, indent=2)

    # 渲染文章内容，剥离开头重复的H1标题（模板已有<h1>）
    content_md = article.get('content') or article.get('body', '')
    content_md = re.sub(r'^# .+\n?', '', content_md)
    content_html = markdown_to_html(content_md)
    content_html = inject_internal_links(content_html, article.get('slug', ''))
    # [#404修复] 坏链清理：未发布/不存在工具的链接降级为纯文本
    content_html = clean_broken_tool_links(content_html)
    # [#1] 正文标题降级一级，避免与模板<h1>冲突产生多个H1
    content_html = shift_headings(content_html, up=1)
    # [#10] 信息图标记驱动插入：正文有"信息图"引导语(blockquote)则插其后，否则兜底底部
    if has_infographic:
        _m = re.search(r'<blockquote>[\s\S]*?信息图[\s\S]*?</blockquote>', content_html, re.S)
        if _m:
            content_html = content_html[:_m.end()] + '\n' + infographic_html + content_html[_m.end():]
        else:
            content_html = content_html + '\n' + infographic_html

    # ═══════════════════════════════════════════════════════
    # 自动补全 TOC 锚点：如果 h2/h3 缺 id 或 TOC 项缺 <a href>，自动生成
    # （正文标题经 shift_headings 后为 h3，P0-4 起同时支持 h2/h3）
    # ═══════════════════════════════════════════════════════
    h_tags = re.findall(r'<h([23])(?P<attrs>[^>]*)>(?P<text>.+?)</h\1>', content_html)
    # 过滤掉 TOC 内部的标题（目录/本文导航 等，不需要 id）
    body_hs = [(lvl, attrs, text) for lvl, attrs, text in h_tags
               if not any(skip in text for skip in ['目录', '本文导航', '📑'])]

    # Step 1: 给没有 id 的 body 标题自动生成 id
    needs_fix = [(lvl, attrs, text) for lvl, attrs, text in body_hs if 'id=' not in attrs]
    if needs_fix:
        for i, (lvl, attrs, text) in enumerate(needs_fix):
            # 生成稳定的 id：用标题文本做 slug
            section_id = 'section-' + re.sub(r'[^\w\u4e00-\u9fff]+', '-', text.strip()).strip('-').lower()
            # 如果 id 重复，加序号
            existing_ids = set(re.findall(r'id="([^"]+)"', content_html))
            counter = 1
            base_id = section_id
            while section_id in existing_ids:
                section_id = f'{base_id}-{counter}'
                counter += 1
            old_h = f'<h{lvl}{attrs}>{text}</h{lvl}>'
            new_h = f'<h{lvl}{attrs} id="{section_id}">{text}</h{lvl}>'
            content_html = content_html.replace(old_h, new_h, 1)

    # Step 2: 给没有 <a href> 链接的 TOC <li> 项添加锚点
    def _auto_link_toc(content, toc_match_start, toc_match_end):
        """给 TOC 中无链接的 li 项自动添加 <a href>"""
        toc_block = content[toc_match_start:toc_match_end]
        li_pattern = re.compile(r'<li>\s*(.+?)\s*</li>', re.DOTALL)
        items = li_pattern.findall(toc_block)
        has_links = any('<a ' in item for item in items)
        if has_links:
            return content  # 已有链接，跳过

        # 提取所有 h2 的 id 用于匹配
        h2_id_text = re.findall(r'<h2[^>]*id="([^"]+)"[^>]*>(.+?)</h2>', content)
        if len(h2_id_text) != len(items):
            return content  # 数量对不上，不自动匹配

        for (item_text, (h2_id, _)) in zip(items, h2_id_text):
            old = f'<li>{item_text}</li>'
            new = f'<li><a href="#{h2_id}">{item_text.strip()}</a></li>'
            content = content.replace(old, new, 1)
        return content

    # 查找 table-of-contents div
    toc_div_match = re.search(r'<div class="table-of-contents">.*?</div>', content_html, re.DOTALL)
    toc_html = ''
    if toc_div_match:
        content_html = _auto_link_toc(content_html, toc_div_match.start(), toc_div_match.end())
    else:
        # 查找 "本文导航" 后面的 ol
        nav_match = re.search(r'<h2[^>]*>本文导航</h2>\s*<ol>.*?</ol>', content_html, re.DOTALL)
        if nav_match:
            content_html = _auto_link_toc(content_html, nav_match.start(), nav_match.end())
        else:
            # P0-4（2026-08-09）：正文未自带目录时，自动生成"本文目录"（≥3 节才显示）。
            # 正文标题经 shift_headings 后为 h3（h2 少见），两者都支持。
            _toc_headings = (re.findall(r'<h3[^>]*id="([^"]+)"[^>]*>(.+?)</h3>', content_html)
                             or re.findall(r'<h2[^>]*id="([^"]+)"[^>]*>(.+?)</h2>', content_html))
            _toc_items = []
            for _hid, _htext in _toc_headings:
                _t = re.sub(r'<[^>]+>', '', _htext).strip()
                if not _t or any(_sk in _t for _sk in ['目录', '本文导航', '常见问题', 'FAQ', '总结', '声明', '来源', '相关工具', '相关文章', '广告']):
                    continue
                _toc_items.append((_hid, _t))
            if len(_toc_items) >= 3:
                _lis = ''.join(f'<li><a href="#{_hid}">{escape_html(_t)}</a></li>' for _hid, _t in _toc_items)
                toc_html = f'''<nav class="article-toc" aria-label="本文目录">
        <div class="article-toc-title">📑 本文目录</div>
        <ol>{_lis}</ol>
    </nav>'''

    # P0-4（2026-08-09）：上一篇 / 下一篇（all_articles 已按日期降序：i-1 更新、i+1 更旧）
    prev_next_html = ''
    if all_articles:
        for _i, _a in enumerate(all_articles):
            if _a.get('slug') == slug:
                _newer = all_articles[_i - 1] if _i > 0 else None
                _older = all_articles[_i + 1] if _i + 1 < len(all_articles) else None
                _pn = ''
                if _older:
                    _pn += f'<a class="apn-prev" href="/articles/{_older["slug"]}/">← 上一篇：{escape_html(_older.get("title", ""))[:28]}</a>'
                else:
                    _pn += '<span></span>'
                if _newer:
                    _pn += f'<a class="apn-next" href="/articles/{_newer["slug"]}/">下一篇：{escape_html(_newer.get("title", ""))[:28]} →</a>'
                else:
                    _pn += '<span></span>'
                prev_next_html = f'<div class="article-prev-next">{_pn}</div>'
                break

    # 文章页 keywords：优先用显式字段，否则从 tags + category 生成
    _article_keywords = article.get('keywords', '')
    if not _article_keywords:
        _tags = article.get('tags') or []
        _kw_parts = list(_tags[:8])
        _kw_parts.append(article.get('category', ''))
        _kw_parts.append('AI工具')
        _kw_parts.append('AI工具宝箱')
        _article_keywords = ', '.join([k for k in _kw_parts if k])

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(article.get('seo_title', '').strip() or article['title'])}</title>
    <meta name="description" content="{escape_html(_get_article_description(article))}">
    <meta name="keywords" content="{escape_html(_article_keywords)}">
    <link rel="canonical" href="https://www.aitoollab.cn/articles/{slug}/">
    <link rel="alternate" type="text/markdown" href="https://www.aitoollab.cn/articles/{slug}/{slug}.md">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{escape_html(article.get('seo_title', '').strip() or article['title'])}">
    <meta property="og:description" content="{escape_html(_get_article_description(article))}">''' + (f'\n    <meta property="og:image" content="{og_image}">\n    <meta property="og:image:width" content="1200">\n    <meta property="og:image:height" content="630">\n' if og_image else '') + f'''    <meta property="og:url" content="https://www.aitoollab.cn/articles/{slug}/">
    <meta property="og:locale" content="zh_CN">
    <meta property="og:site_name" content="AI工具宝箱">
    <meta property="article:published_time" content="{article_date}">
    <meta property="article:modified_time" content="{article_date_modified}">
    <meta property="article:author" content="AI工具宝箱编辑组">
    <meta property="article:section" content="{escape_html(article_category)}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(article.get('seo_title', '').strip() or article['title'])}">
    <meta name="twitter:description" content="{escape_html(_get_article_description(article))}">''' + (f'\n    <meta name="twitter:image" content="{og_image}">\n' if og_image else '') + f'''    <style>{build.CRITICAL_CSS}</style>
    {build.ARTICLE_EXTRA_CSS}
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript>
    <script type="application/ld+json">{breadcrumb_article_json}</script>
    <script type="application/ld+json">{structured_data}</script>''' + (f'\n    <script type="application/ld+json">{howto_schema_json}</script>' if howto_schema_json else '') + f'''{faq_article_schema}
{build.BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 已收录 {build.TOOL_COUNT}+ 工具</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <span>{escape_html(article.get('category', '文章'))}</span> &gt; <span>{escape_html(article['title'])[:20]}...</span>
    </nav>

    <main class="article-container-wide">
        <div class="content-main">
        <article class="article-body" data-tts>
            <h1 class="article-title">{escape_html(article['title'])}</h1>
            <!-- 2026-08-22 作者卡：对标知乎作者区（头像+昵称+简介+听全文），SEO红线：itemprop=author/Organization 与 time 保留、无 h2/h3、tts-skip -->
            <div class="article-authorbar tts-skip" aria-label="作者信息">
                <div class="author-avatar" aria-hidden="true">
                    <svg viewBox="0 0 24 24" fill="none"><rect x="4" y="4" width="16" height="16" rx="3" stroke="#fff" stroke-width="1.6"/><path d="M8 8h4v4H8zM13 8h3v3h-3zM8 13h3v3H8zM13 13h3v3h-3z" fill="#fff"/></svg>
                </div>
                <div class="author-info">
                    <div class="author-name">
                        <span itemprop="author" itemscope itemtype="https://schema.org/Organization"><a href="/author/" itemprop="url"><span itemprop="name">AI工具宝箱编辑组</span></a></span>
                        <span class="author-badge">官方评测</span>
                        <span class="author-cat-date"><span class="author-cat">AI资讯</span> <time datetime="{article_date}" itemprop="datePublished">{article_date}</time></span>
                        <span class="author-read">阅读 {max(3, len(article.get('content','')) // 400)} 分钟</span>
                    </div>
                    <div class="author-desc-row">
                        <div class="author-desc">AI 工具实测与对比 · 已收录 580+ 款工具</div>
                        <div class="author-tts-slot" aria-hidden="true"></div>
                    </div>
                    <div class="author-meta-mobile" aria-hidden="true">
                        <span class="author-cat">AI资讯</span> <time datetime="{article_date}">{article_date}</time>
                    </div>
                </div>
            </div>
            <div class="tldr-box" style="background:linear-gradient(135deg,#fff8e6,#ffefb8);border-left:4px solid #f5a623;padding:16px 20px;margin-bottom:24px;border-radius:0 8px 8px 0;font-size:14.5px;line-height:1.7;">
                <strong style="color:#c77d00;font-size:15px;">⚡ TL;DR</strong><br>
                <span style="color:#555;">{escape_html(article.get('excerpt') or article.get('description') or article.get('summary', ''))}</span>
            </div>
            {related_tools_top_html}
            {toc_html}{content_html}
            {article_faq_section_html}
            <div style="margin-top:40px;padding:20px;background:#f8f9fa;border-radius:8px;border-left:4px solid #10a37f;">
                <p style="margin:0 0 8px 0;font-size:14px;color:#555;">
                    <strong>关于作者：</strong>本文由 <a href="/author/" style="color:#10a37f;text-decoration:none;">AI工具宝箱编辑组</a> 撰写，团队持续追踪并实测主流 AI 工具，月均订阅支出 $200+，所有评测基于真实长期使用。
                </p>
                <p style="margin:0;font-size:13px;color:#888;">
                    <strong>数据声明：</strong>本文所有数据均标注来源，可溯源核查。发现错误欢迎通过 <a href="/contact.html" style="color:#4285F4;text-decoration:none;">联系页面</a> 反馈，48 小时内核查修正。
                </p>
            </div>
        </article>

            {prev_next_html}

            <div class="content-related">
                {related_tools_html}
                {related_html}
            </div>

            <div class="mobile-ad-inline">📱 继续阅读 · 猜你喜欢</div>
        </div><!-- /.content-main -->

        <div class="page-sidebar-wrap">
        <aside class="page-sidebar">
            <div class="ad-slot ad-slot-large"></div>
            {article_sidebar_tools_html}
            {article_sidebar_related_html}
        </aside>
        </div>
    </main>

    <footer class="footer">
        <p>© {build.BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · ''' + build.ICP_BEIAN + '''</p>
    </footer>
    ''' + build.BACK_TO_TOP_BLOCK + '''
</body>
</html>'''
    return html

def _pagination_html(page_num, total_pages, url_template):
    """生成带数字页码的分页导航（P1-4，2026-08-09）。
    url_template 用 {n} 占位页码，如 '/articles/page/{n}/'。"""
    if total_pages <= 1:
        return '<div class="pagination"><span class="page-info">1 / 1</span></div>'
    def _u(n):
        return url_template.format(n=n)
    html = '<div class="pagination">'
    if page_num > 1:
        html += f'<a href="{_u(page_num - 1)}" class="prev">&larr; 上一页</a>\n'
    window = set(range(max(1, page_num - 2), min(total_pages, page_num + 2) + 1))
    window |= {1, total_pages}
    last = 0
    for n in sorted(window):
        if n - last > 1:
            html += '<span class="page-ellipsis">…</span>\n'
        if n == page_num:
            html += f'<span class="page-num current">{n}</span>\n'
        else:
            html += f'<a class="page-num" href="{_u(n)}">{n}</a>\n'
        last = n
    if page_num < total_pages:
        html += f'<a href="{_u(page_num + 1)}" class="next">下一页 &rarr;</a>\n'
    html += '</div>'
    return html

def build_article_list_pages(articles):
    import build  # 延迟：build 完全加载后解析 build 级符号
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
            articles_html += f'''                        <article class="article-card" style="animation-delay: {round(i * 0.05, 2)}s;">
                            <h3><a href="/articles/{a['slug']}/">{escape_html(a['title'])}</a></h3>
                            <div class="article-meta">
                                <span class="date">{a.get('dateFull', a.get('date', ''))}</span>
                                <span class="category">{escape_html(_article_type_label(a))}</span>
                            </div>
                            <p class="summary">{escape_html(a.get('description', '')[:150])}</p>
                        </article>\n'''
        
        # 生成分页导航 HTML（P1-4：带数字页码）
        pagination_html = _pagination_html(page_num, total_pages, '/articles/page/{n}/')
        
        # 生成链接标签（rel next/prev/canonical）
        # 分页 canonical 全部指向第1页 /articles/，避免重复内容
        if page_num == 1:
            link_tags = f'    <link rel="canonical" href="https://www.aitoollab.cn/articles/">\n'
        else:
            link_tags = f'    <link rel="canonical" href="https://www.aitoollab.cn/articles/">\n'
        if page_num > 1:
            link_tags += f'    <link rel="prev" href="https://www.aitoollab.cn/articles/page/{page_num - 1}/">\n'
        if page_num < total_pages:
            link_tags += f'    <link rel="next" href="https://www.aitoollab.cn/articles/page/{page_num + 1}/">\n'

        # robots标签：第2页及以后 noindex,follow
        robots_tag = ''
        if page_num > 1:
            robots_tag = '    <meta name="robots" content="noindex, follow">\n'

        # 构建列表页结构化数据
        _list_og_image = "https://www.aitoollab.cn/images/logo.png"

        # 日期ISO格式化辅助函数
        def _date_to_iso(d):
            """将'2026年5月6日'转为'2026-05-06'"""
            import re as _re_d
            m = _re_d.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', str(d))
            if m:
                return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
            return str(d)

        # 1) Blog Schema（含author + ISO日期）
        _blog_schema = {
            "@context": "https://schema.org",
            "@type": "Blog",
            "name": "AI工具宝箱 - 最新文章",
            "description": f"AI工具宝箱最新文章列表（第{page_num}页）：收录AI工具实测、使用教程、行业快讯与深度对比评测，覆盖ChatGPT、Claude、DeepSeek、Kimi等主流AI工具，数据每日更新、来源可溯源，帮你快速找到值得读的AI内容。",
            "url": f"https://www.aitoollab.cn/articles/page/{page_num}/",
            "author": {"@type": "Person", "name": "AI工具宝箱编辑组", "url": "https://www.aitoollab.cn/about"},
            "publisher": {
                "@type": "Organization",
                "name": "AI工具宝箱",
                "logo": {"@type": "ImageObject", "url": "https://www.aitoollab.cn/images/logo.png", "width": 200, "height": 60}
            },
            "blogPost": [
                {
                    "@type": "BlogPosting",
                    "headline": a.get('title', ''),
                    "url": f"https://www.aitoollab.cn/articles/{a['slug']}/",
                    "datePublished": _date_to_iso(a.get('dateFull', a.get('date', '')))
                } for a in page_articles
            ]
        }

        # 2) ItemList Schema
        _itemlist_schema = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": f"最新文章 - 第{page_num}页",
            "description": "AI工具文章列表",
            "numberOfItems": len(page_articles),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": a.get('title', ''), "url": f"https://www.aitoollab.cn/articles/{a['slug']}/"} for i, a in enumerate(page_articles)
            ]
        }

        # 3) WebPage Schema（含 speakable + abstract）
        _webpage_schema = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": f"AI工具宝箱 - 最新文章 第{page_num}页",
            "description": f"AI工具宝箱最新文章列表（第{page_num}页）：收录AI工具实测、使用教程、行业快讯与深度对比评测，覆盖ChatGPT、Claude、DeepSeek、Kimi等主流AI工具，数据每日更新、来源可溯源，帮你快速找到值得读的AI内容。",
            "url": f"https://www.aitoollab.cn/articles/page/{page_num}/",
            "abstract": f"AI工具宝箱文章专栏收录原创AI工具深度评测与对比分析，内容涵盖AI写作、AI绘画、AI编程、AI视频等{build.CAT_COUNT}大分类。所有评测均基于编辑组实际测试，含真实性能数据、价格对比和适用场景建议，每周持续更新，累计{build.ART_COUNT}篇。",
            "speakable": {
                "@type": "SpeakableSpecification",
                "cssSelector": [".articles-page-intro", ".articles-list .article-card:first-child h3", ".articles-list .article-card:first-child .summary"]
            },
            "isPartOf": {"@type": "WebSite", "name": "AI工具宝箱", "url": "https://www.aitoollab.cn/"}
        }

        # 4) BreadcrumbList Schema
        _breadcrumb_json = json.dumps({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoollab.cn/"},
                {"@type": "ListItem", "position": 2, "name": "文章列表", "item": "https://www.aitoollab.cn/articles/"}
            ]
        }, ensure_ascii=False)

        _list_schema_json = (json.dumps(_blog_schema, ensure_ascii=False) +
            '</script>\n    <script type="application/ld+json">' +
            json.dumps(_itemlist_schema, ensure_ascii=False) +
            '</script>\n    <script type="application/ld+json">' +
            json.dumps(_webpage_schema, ensure_ascii=False))

        # 生成页面 HTML
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI工具宝箱 - 最新文章 第{page_num}页</title>
    <meta name="description" content="AI工具宝箱最新文章列表（第{page_num}页）：收录AI工具实测、使用教程、行业快讯与深度对比评测，覆盖ChatGPT、Claude、DeepSeek、Kimi等主流AI工具，数据每日更新、来源可溯源，帮你快速找到值得读的AI内容。">
    <meta name="keywords" content="AI工具,AI文章,AI评测,AI教程">
    {robots_tag}{link_tags}    <meta property="og:type" content="blog">
    <meta property="og:title" content="AI工具宝箱 - 最新文章">
    <meta property="og:description" content="AI工具宝箱最新文章列表（第{page_num}页）：收录AI工具实测、使用教程、行业快讯与深度对比评测，数据每日更新，帮你快速找到值得读的AI内容。">
    <meta property="og:url" content="https://www.aitoollab.cn/articles/page/{page_num}/">
    <meta property="og:locale" content="zh_CN">
    <meta property="og:image" content="{_list_og_image}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:site_name" content="AI工具宝箱">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="AI工具宝箱 - 最新文章">
    <meta name="twitter:description" content="AI工具宝箱最新文章列表：AI工具实测、使用教程、行业快讯与深度对比评测，数据每日更新，帮你快速找到值得读的AI内容。">
    <meta name="twitter:image" content="{_list_og_image}">
    <style>{build.CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript>
    <script type="application/ld+json">
{_list_schema_json}
    </script>
    <script type="application/ld+json">
{_breadcrumb_json}
    </script>
{build.BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">&#x1F6E0; AI工具宝箱 <span>每日更新 · 最新资讯</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/articles/page/1/">文章列表</a> &gt; <span>第 {page_num} 页</span>
    </nav>

    <main class="article-container">
        <div class="articles-page-intro">
            <h1 style="margin-bottom:8px;">📝 最新文章</h1>
            <a class="articles-rss-btn" href="/rss.xml" target="_blank" rel="noopener">📡 RSS 订阅</a>
            <p style="font-size:14px;color:#64748b;margin:0;">原创AI工具深度评测与对比，每周更新，累计61篇。</p>
        </div>
        <div class="articles-list">
{articles_html}
        </div>
        
        {pagination_html}
    </main>

    <footer class="footer">
        <p>&#xA9; {build.BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · ''' + build.ICP_BEIAN + '''</p>
    </footer>
    ''' + build.BACK_TO_TOP_BLOCK + '''
</body>
</html>'''

        # 创建目录并保存文件
        dir_path = os.path.join(build.BASE_DIR, 'articles', 'page', str(page_num))
        os.makedirs(dir_path, exist_ok=True)
        _emit(os.path.join(dir_path, 'index.html'), html)
        try:
            import re as _re
            md_text = f"# {target_article.get('title', '')}\n\n" + target_article.get('content', '')
            md_text = _re.sub(r'<[^>]+>', ' ', md_text)
            with open(os.path.join(dir_path, f"{slug}.md"), 'w', encoding='utf-8') as f:
                f.write(md_text)
        except:
            pass

        # 第1页同时输出到 /articles/index.html（文章总入口页）
        if page_num == 1:
            # 修改 canonical 和面包屑指向 /articles/
            entry_html = html.replace(
                'href="https://www.aitoollab.cn/articles/page/1/"',
                'href="https://www.aitoollab.cn/articles/"'
            ).replace(
                'href="/articles/page/1/"',
                'href="/articles/"'
            ).replace(
                '第 1 页',
                '文章总览'
            )
            _emit(os.path.join(build.BASE_DIR, 'articles', 'index.html'), entry_html)
            print(f'[OK] articles/index.html (文章总入口页)')
        print(f'[OK] articles/page/{page_num}/index.html')
    
    return total_pages

def build_article_category_pages(articles):
    import build  # 延迟：build 完全加载后解析 build 级符号
    """生成文章内容分类页（2026-08-08，ROADMAP-TODO 第一阶段）：
    /articles/reviews/（AI工具评测）、/articles/tutorials/（AI实战教程）、
    /articles/analysis/（AI行业分析）。
    每页 10 篇、按日期倒序；复用文章列表页样式；第 2 页起 noindex,follow。"""
    ITEMS_PER_PAGE = 10

    def _pdate(d):
        from datetime import datetime
        d = (d or '').strip()
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d'):
            try:
                return datetime.strptime(d, fmt)
            except Exception:
                continue
        try:
            return datetime.strptime('2026/' + d, '%Y/%m/%d')
        except Exception:
            pass
        try:
            return datetime.strptime('2026年' + d, '%Y年%m月%d日')
        except Exception:
            pass
        return datetime.min

    def _iso(d):
        m = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', str(d))
        if m:
            return '%s-%s-%s' % (m.group(1), m.group(2).zfill(2), m.group(3).zfill(2))
        m2 = re.match(r'^(\d{4}-\d{2}-\d{2})', str(d))
        return m2.group(1) if m2 else _dt_build.now().strftime('%Y-%m-%d')

    built = 0
    for cp in build.ARTICLE_CATEGORY_PAGES:
        cslug = cp['slug']
        ctype = cp['ctype']
        items = [a for a in articles if build.article_content_type(a) == ctype]
        items.sort(key=lambda a: _pdate(a.get('date', '')), reverse=True)
        total_pages = max(1, (len(items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        _base_url = 'https://www.aitoollab.cn/articles/%s/' % cslug
        _og_image = 'https://www.aitoollab.cn/images/logo.png'

        for page_num in range(1, total_pages + 1):
            start_idx = (page_num - 1) * ITEMS_PER_PAGE
            end_idx = min(start_idx + ITEMS_PER_PAGE, len(items))
            page_items = items[start_idx:end_idx]

            articles_html = ''
            for i, a in enumerate(page_items):
                articles_html += f'''                        <article class="article-card" style="animation-delay: {round(i * 0.05, 2)}s;">
                            <h3><a href="/articles/{a['slug']}/">{escape_html(a['title'])}</a></h3>
                            <div class="article-meta">
                                <span class="date">{a.get('dateFull', a.get('date', ''))}</span>
                                <span class="category">{escape_html(_article_type_label(a))}</span>
                            </div>
                            <p class="summary">{escape_html(a.get('description', '')[:150])}</p>
                        </article>\n'''

            pagination_html = _pagination_html(page_num, total_pages, f'/articles/{cslug}/page/{{n}}/')

            # canonical 全部指向第 1 页；第 2 页起 noindex + rel next/prev
            link_tags = f'    <link rel="canonical" href="{_base_url}">\n'
            robots_tag = ''
            if page_num > 1:
                robots_tag = '    <meta name="robots" content="noindex, follow">\n'
                link_tags += f'    <link rel="prev" href="{_base_url}page/{page_num - 1}/">\n'
            if page_num < total_pages:
                link_tags += f'    <link rel="next" href="{_base_url}page/{page_num + 1}/">\n'

            _blog_schema = {
                "@context": "https://schema.org",
                "@type": "Blog",
                "name": cp['h1'] + ' - AI工具宝箱',
                "description": cp['description'],
                "url": _base_url + ('page/%d/' % page_num) if page_num > 1 else _base_url,
                "author": {"@type": "Person", "name": "AI工具宝箱编辑组", "url": "https://www.aitoollab.cn/about"},
                "publisher": {"@type": "Organization", "name": "AI工具宝箱",
                              "logo": {"@type": "ImageObject", "url": _og_image, "width": 200, "height": 60}},
                "blogPost": [
                    {"@type": "BlogPosting", "headline": a.get('title', ''),
                     "url": 'https://www.aitoollab.cn/articles/%s/' % a['slug'],
                     "datePublished": _iso(a.get('dateFull', a.get('date', ''))),
                     "description": (a.get('description') or '')[:200]}
                    for a in page_items
                ],
            }
            _itemlist_schema = {
                "@context": "https://schema.org",
                "@type": "ItemList",
                "name": '%s - 第%d页' % (cp['h1'], page_num),
                "numberOfItems": len(page_items),
                "itemListElement": [
                    {"@type": "ListItem", "position": i + 1, "name": a.get('title', ''),
                     "url": 'https://www.aitoollab.cn/articles/%s/' % a['slug'],
                     "description": (a.get('description') or '')[:200]}
                    for i, a in enumerate(page_items)
                ],
            }
            _webpage_schema = {
                "@context": "https://schema.org",
                "@type": "WebPage",
                "name": '%s - 第%d页' % (cp['h1'], page_num),
                "description": cp['description'],
                "url": (_base_url + 'page/%d/' % page_num) if page_num > 1 else _base_url,
                "isPartOf": {"@type": "WebSite", "name": "AI工具宝箱", "url": "https://www.aitoollab.cn/"},
                "speakable": {
                    "@type": "SpeakableSpecification",
                    "cssSelector": [
                        ".articles-page-intro",
                        ".articles-list .article-card:first-child h3",
                        ".articles-list .article-card:first-child .summary",
                    ],
                },
            }
            _breadcrumb_json = json.dumps({
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "首页", "item": "https://www.aitoollab.cn/"},
                    {"@type": "ListItem", "position": 2, "name": "文章列表", "item": "https://www.aitoollab.cn/articles/"},
                    {"@type": "ListItem", "position": 3, "name": cp['breadcrumb'], "item": _base_url},
                ],
            }, ensure_ascii=False)

            _list_schema_json = (json.dumps(_blog_schema, ensure_ascii=False) +
                                 '</script>\n    <script type="application/ld+json">' +
                                 json.dumps(_itemlist_schema, ensure_ascii=False) +
                                 '</script>\n    <script type="application/ld+json">' +
                                 json.dumps(_webpage_schema, ensure_ascii=False))

            _page_url = ('%spage/%d/' % (_base_url, page_num)) if page_num > 1 else _base_url
            # 分类栏目互链（SEO/GEO：栏目枢纽页互相指向，2026-08-08）
            _hub_links = ''.join(
                '<a href="/articles/%s/">%s</a>' % (_h['slug'], _h['h1'])
                for _h in build.ARTICLE_CATEGORY_PAGES if _h['slug'] != cslug)
            _hub_html = ('<div class="articles-cat-hub"><span>更多栏目</span>%s</div>' % _hub_links) if _hub_links else ''
            html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{cp['page_title']}{'' if page_num == 1 else ' 第%d页' % page_num}</title>
    <meta name="description" content="{escape_html(cp['description'])}">
    <meta name="keywords" content="{escape_html(cp['keywords'])}">
    {robots_tag}{link_tags}    <meta property="og:type" content="blog">
    <meta property="og:title" content="{cp['h1']} - AI工具宝箱">
    <meta property="og:description" content="{escape_html(cp['description'])}">
    <meta property="og:url" content="{_page_url}">
    <meta property="og:locale" content="zh_CN">
    <meta property="og:image" content="{_og_image}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:site_name" content="AI工具宝箱">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{cp['h1']} - AI工具宝箱">
    <meta name="twitter:description" content="{escape_html(cp['description'])}">
    <meta name="twitter:image" content="{_og_image}">
    <style>{build.CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript>
    <script type="application/ld+json">
{_list_schema_json}
    </script>
    <script type="application/ld+json">
{_breadcrumb_json}
    </script>
{build.BAIDU_TONGJI}
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">&#x1F6E0; AI工具宝箱 <span>每日更新 · 最新资讯</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/articles/">文章列表</a> &gt; <span>{cp['breadcrumb']}</span>
    </nav>

    <main class="article-container">
        <div class="articles-page-intro">
            <h1 style="margin-bottom:8px;">{cp['h1']}</h1>
            <a class="articles-rss-btn" href="/rss.xml" target="_blank" rel="noopener">📡 RSS 订阅</a>
            <p style="font-size:14px;color:#64748b;margin:0;">{cp['intro']} 共 {len(items)} 篇。</p>
        </div>
        {_hub_html}
        <div class="articles-list">
{articles_html}
        </div>

        {pagination_html}
    </main>

    <footer class="footer">
        <p>&#xA9; {build.BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · ''' + build.ICP_BEIAN + '''</p>
    </footer>
    ''' + build.BACK_TO_TOP_BLOCK + '''
</body>
</html>'''

            if page_num == 1:
                dir_path = os.path.join(build.BASE_DIR, 'articles', cslug)
                os.makedirs(dir_path, exist_ok=True)
                _emit(os.path.join(dir_path, 'index.html'), html)
                print(f'[OK] articles/{cslug}/index.html ({len(items)} 篇, {total_pages} 页)')
            else:
                dir_path = os.path.join(build.BASE_DIR, 'articles', cslug, 'page', str(page_num))
                os.makedirs(dir_path, exist_ok=True)
                _emit(os.path.join(dir_path, 'index.html'), html)
                print(f'[OK] articles/{cslug}/page/{page_num}/index.html')
        built += 1
    return built

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

def generate_rss(articles):
    import build  # 延迟：build 完全加载后解析 build 级符号
    # 生成全站快讯 RSS（/rss.xml），取最新 50 篇文章
    import email.utils
    if not articles:
        return
    items = []
    for a in articles[:50]:
        slug = a.get('slug', '')
        if not slug:
            continue
        title = escape_html(a.get('title', ''))
        link = f'https://www.aitoollab.cn/articles/{slug}/'
        desc = escape_html((a.get('description') or '')[:200])
        d = str(a.get('date', ''))
        try:
            if len(d) == 10 and d[4] == '-' and d[7] == '-':
                pub = email.utils.format_datetime(_dt_build.strptime(d, '%Y-%m-%d'))
            else:
                pub = email.utils.formatdate(usegmt=True)
        except Exception:
            pub = email.utils.formatdate(usegmt=True)
        items.append(
            f'<item><title>{title}</title><link>{link}</link>'
            f'<guid isPermaLink="false">aitoollab-{slug}</guid>'
            f'<pubDate>{pub}</pubDate><description>{desc}</description></item>'
        )
    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n<channel>\n'
        '<title>AI工具宝箱 - 快讯与评测</title>\n'
        '<link>https://www.aitoollab.cn/</link>\n'
        '<description>AI工具宝箱：AI 工具实测评测、对比分析与行业快讯</description>\n'
        '<language>zh-cn</language>\n'
        + '\n'.join(items) + '\n</channel>\n</rss>\n'
    )
    with open(os.path.join(build.BASE_DIR, 'rss.xml'), 'w', encoding='utf-8') as f:
        f.write(rss)
    print(f'[OK] rss.xml ({len(items)} items)')
