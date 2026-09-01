# render_tool.py — 工具相关渲染（图标/卡片/工具页/对比/替代/链接清理）
# 模块4：从 build.py 拆分（2026-08-24）
import os
import re
import json
import random
from datetime import datetime, timedelta

from build_lib.html_utils import (
    escape_html, extract_faq_section, markdown_to_html,
)
from build_lib.data_loaders import (
    get_category_slug, get_published_tool_slugs, load_articles, _LINK_STOPWORDS,
)

# 停运提示里展示的"核实日期"。必须是固定值：若用当天日期，每次构建都会改这两个页面的文案，
# 破坏构建可复现性。新增死链到 build.BROKEN_URLS 时，同步把本日期更新为复核当天。
DEAD_LINK_NOTICE_DATE = '2026-09-01'


def resolve_icon(slug):
    import build  # 延迟：build 完全加载后解析 build 级符号
    """统一图标解析：返回 (ext, web_path) 或 (None, '')。
    所有页面（详情/首页/JS）共用此函数，保证图标路径一致。
    ext: '.svg' | '.png' | None
    """
    if not slug:
        return None, ''
    for ext in ('.svg', '.png'):
        local_path = os.path.join(build.BASE_DIR, 'assets', 'icons', slug + ext)
        if os.path.exists(local_path):
            return ext, f'/assets/icons/{slug}{ext}'
    # 回退：同品牌图标（解决版本升级后旧图标丢失问题）
    # 匹配规则：① 精确品牌基础图标（如 seedance.png / minimax.png）；
    #          ② 同品牌带版本号图标（如 glm-5-1.png / kling-ai.svg）。
    # 例：glm-5-2 无 glm-5-2.svg，自动复用 glm-5-1.png；seedance-2-0 复用 seedance.png。
    if '-' in slug:
        brand = slug.split('-')[0]
        if brand and brand != slug:
            icons_dir = os.path.join(build.BASE_DIR, 'assets', 'icons')
            try:
                cands = []
                for fn in os.listdir(icons_dir):
                    stem, ext = os.path.splitext(fn)
                    if ext.lstrip('.') in ('svg', 'png') and (stem == brand or stem.startswith(brand + '-')):
                        cands.append(fn)
                if cands:
                    # 优先精确品牌基础图标，其次同品牌其它版本/系列图标
                    cands.sort(key=lambda f: (0 if os.path.splitext(f)[0] == brand else 1, f))
                    fn = cands[0]
                    return os.path.splitext(fn)[1], f'/assets/icons/{fn}'
            except FileNotFoundError:
                pass
    return None, ''

def tool_icon_html(tool, large=False, size=None):
    """生成工具图标HTML。依赖 resolve_icon() 统一解析，本地无图标则回退 emoji+色块。
    size: 'sm'(30px 侧边栏/推荐) | 'md'(48px 卡片) | 'lg'(76px 详情)。large=True 等价于 'lg'。"""
    slug = tool.get('slug', '')
    if not slug:
        return ''
    if size is None:
        size = 'lg' if large else 'md'
    cls = {'sm': 'tool-icon-real-sm', 'md': 'tool-icon-real', 'lg': 'tool-icon-real-lg'}.get(size, 'tool-icon-real')
    ext, web_path = resolve_icon(slug)
    if ext:
        return f'<img src="{web_path}" class="{cls}" alt="{escape_html(tool.get("name",""))}" loading="lazy" width="48" height="48">'
    # 回退: emoji + 色块
    if size == 'lg':
        return f'<div class="tool-icon-lg" style="background:{tool.get("color","#4f46e5")};">{tool.get("emoji","")}</div>'
    return f'<div class="tool-icon" style="background:{tool.get("color","#4f46e5")};">{tool.get("emoji","")}</div>'

CATEGORY_COLOR_MAP = {
    'AI对话': ('chat', '#10b981'),
    'AI写作': ('write', '#6366f1'),
    'AI绘画': ('image', '#f59e0b'),
    'AI编程': ('code', '#3b82f6'),
    'AI视频': ('video', '#ef4444'),
    'AI音频': ('audio', '#8b5cf6'),
    'AI办公': ('office', '#0ea5e9'),
    'AI设计': ('design', '#ec4899'),
    'AI搜索': ('search', '#14b8a6'),
    'AI翻译': ('trans', '#22c55e'),
    'AI自动化': ('auto', '#f97316'),
    'AI效率': ('eff', '#a855f7'),
    'AI智能体': ('agent', '#a855f7'),
    'AI开发': ('dev', '#3b82f6'),
    'AI行业应用': ('industry', '#0ea5e9'),
    '去中心化AI': ('decentralized', '#FF6B35'),
}
def get_category_color_var(category_name):
    """返回类目对应的CSS变量引用，如 var(--cat-chat)"""
    entry = CATEGORY_COLOR_MAP.get(category_name)
    if entry:
        return f'var(--cat-{entry[0]})'
    return 'var(--primary)'

def get_category_glow_styles(category_name):
    """返回内联 style 中的 glow 三件套: --glow / --glow-hover / --glow-border"""
    entry = CATEGORY_COLOR_MAP.get(category_name)
    if entry:
        hexc = entry[1]
        return f'--glow:rgba({_hex_to_rgb(hexc)},0.08);--glow-hover:rgba({_hex_to_rgb(hexc)},0.16);--glow-border:rgba({_hex_to_rgb(hexc)},0.25)'
    return '--glow:rgba(99,102,241,0.08);--glow-hover:rgba(99,102,241,0.16);--glow-border:rgba(99,102,241,0.25)'

def _hex_to_rgb(hexc):
    """将 #10b981 转为 '16,185,129'"""
    h = hexc.lstrip('#')
    if len(h) == 3:
        h = ''.join(c*2 for c in h)
    return f'{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}'

def get_price_info(tool):
    """从 tool 数据提取价格信息，返回 (css_class, text)
    兼容两种 tags 格式：字符串列表 ['免费可用'] 或 字典列表 [{'type':'free','text':'免费可用'}]"""
    tags = tool.get('tags', [])
    price = tool.get('price', '')
    # 找免费标签（兼容 str / dict 两种格式）
    for tag in tags:
        if isinstance(tag, dict):
            if tag.get('type') == 'free':
                txt = tag.get('text', '')
                if '免费' in txt or 'Free' in txt.lower() or '开源' in txt:
                    return ('free', txt)
                return ('free', '免费可用')
        elif isinstance(tag, str):
            if '免费' in tag or 'Free' in tag.lower() or '开源' in tag:
                return ('free', tag)
    # 从 price 字段判断
    if price:
        if '免费' in price or 'Free' in price.lower():
            return ('free', '免费可用')
        if '开源' in price:
            return ('free', '开源免费')
    return ('paid', '付费')

def extract_rating_num(rating_str):
    """从 '⭐ 4.9' 提取 '4.9'"""
    if not rating_str:
        return ''
    import re as _re
    m = _re.search(r'[\d.]+', str(rating_str))
    return m.group(0) if m else ''

def make_tool_card_html(tool, i):
    """生成 Logo 光晕版工具卡片 HTML（DESIGN.md v2）"""
    slug = tool.get('slug', '')
    name = escape_html(tool.get('name', ''))
    category = escape_html(tool.get('category', ''))
    desc = escape_html(tool.get('description', ''))
    rating_num = extract_rating_num(tool.get('rating', ''))
    glow_styles = get_category_glow_styles(tool.get('category', ''))
    price_cls, price_text = get_price_info(tool)
    visits = tool.get('visits', '')
    _visits_card = str(visits or '').strip()
    if _visits_card.lower() in ('', '暂无数据', '0', 'none', 'n/a', 'na', '-', '未知', '无'):
        _visits_card = ''  # 2026-08-31：列表卡片不外露 N/A 类无数据值
    else:
        _visits_card = f'<span class="visits">{escape_html(_visits_card)}</span>'

    icon_html = tool_icon_html(tool)

    # Badge（防御：badge 可能是字符串而非 dict，归一化避免 AttributeError 崩溃）
    badge_data = tool.get('badge') or {}
    if isinstance(badge_data, str):
        badge_data = {'type': 'pick', 'text': badge_data}
    if badge_data and badge_data.get('text') and badge_data.get('type'):
        badge_html = f'<span class="badge badge-{badge_data["type"]}">{badge_data["text"]}</span>'
    else:
        badge_html = ''

    rating_disp = f'<span class="rating-inline">★ {rating_num}</span>' if rating_num else ''

    return f'''                        <a href="/tools/{slug}/" class="tool-card-link" style="text-decoration:none;color:inherit;">
                        <article class="tool-card fade-in" style="animation-delay: {round(i * 0.05, 2)}s;{glow_styles}">
                            <div class="logo-home">
                                {icon_html}
                            </div>
                            <div class="name-row">
                                <span class="name">{name}</span> {badge_html}
                                {rating_disp}
                            </div>
                            <div class="category">{category}</div>
                            <p class="desc">{desc}</p>
                            <div class="footer-row">
                                <span class="price-pill {price_cls}">{price_text}</span>
                                {_visits_card}
                            </div>
                        </article>
                        </a>\n'''

def ensure_og_image(slug, data_obj=None, is_article=False, is_dict=False):
    import build  # 延迟：build 完全加载后解析 build 级符号
    """检查OG图片是否存在，不存在则自动生成。返回og_image URL或空字符串。"""
    og_image_local = os.path.join(build.BASE_DIR, 'images', 'og', f'{slug}-og.png')
    og_image_url = f'https://www.aitoollab.cn/images/og/{slug}-og.png'
    if os.path.exists(og_image_local):
        return og_image_url
    # 自动生成（Pillow 中文版，移植英文站专业设计）
    try:
        from gen_og_images_cn import make_article_og, make_tool_og, make_dict_og
        if is_dict and data_obj:
            make_dict_og(data_obj, og_image_local)
        elif is_article and data_obj:
            make_article_og(data_obj, og_image_local)
        elif data_obj and not is_article:
            make_tool_og(data_obj, og_image_local)
        else:
            return ''
        if os.path.exists(og_image_local):
            print(f'  [OG] 自动生成: {slug}-og.png')
            return og_image_url
        else:
            print(f'  [OG] 生成失败: {slug}-og.png')
            return ''
    except Exception as e:
        print(f'  [OG] 生成异常: {slug} - {e}')
        return ''

def inject_internal_links(html, current_slug='', max_links=5):
    import build  # 延迟：build 完全加载后解析 build 级符号
    """在正文 HTML 的文本节点中，把提到的其他工具名替换为指向 /tools/slug/ 的内链。
    规则：
    - 每个工具（slug）在单页内最多内链一次（仅首次出现时），避免重复内链。
    - 只处理标签之间的纯文本，跳过已在 <a> 内的文本，避免破坏标签或嵌套 <a>。
    """
    if not html:
        return html
    link_map = build.get_tool_link_map()
    parts = re.split(r'(<[^>]+>)', html)
    in_link = False
    count = 0
    linked_slugs = set()  # 已内链的 slug，保证单页内同一工具只链一次
    for i, part in enumerate(parts):
        if not part:
            continue
        if part.startswith('<'):
            if re.match(r'<a\b', part, re.I) and 'href' in part:
                in_link = True
            elif part.startswith('</a>'):
                in_link = False
            continue
        if in_link or count >= max_links:
            continue
        for name, slug in link_map:
            if slug == current_slug or slug in linked_slugs:
                continue
            if name in _LINK_STOPWORDS or len(name) < 3:
                continue
            pat = build._get_link_pat(name)
            m = pat.search(part)
            if m:
                matched = m.group(0)
                repl = f'<a href="/tools/{slug}/" class="ilink">{matched}</a>'
                part = part[:m.start()] + repl + part[m.end():]
                parts[i] = part
                count += 1
                linked_slugs.add(slug)
                break  # 替换后跳出：避免后续短工具名在新插入的<a>内嵌套匹配
    return ''.join(parts)

# 2026-08-24：art_slugs 模块级缓存（load_articles 无缓存，全站坏链清理 1153 文件每文件重读 articles.json
# 是 85s 主因）。单进程构建内文章数据不变，缓存安全；进程内数据变更需重置为 None。
_CLEAN_BROKEN_ART_SLUGS = None

def clean_broken_tool_links(html):
    import build  # 延迟：build 完全加载后解析 build 级符号
    """把指向未发布/不存在工具/文章的链接降级为纯文本，避免 404（2026-08-07 修复）。
    覆盖 /tools/<slug>/、/tools/<slug>/index.html、/articles/<slug>/、带域名的完整 URL。
    2026-08-08 修复：/articles/ 下的非文章路径（分类页 reviews/tutorials/analysis、
    列表分页 page/N）不是文章链接，不能被降级——正则收紧为 URL 到 slug 即结束，
    并对已知分类页 slug 白名单放行。"""
    global _CLEAN_BROKEN_ART_SLUGS
    if _CLEAN_BROKEN_ART_SLUGS is None:
        try:
            _CLEAN_BROKEN_ART_SLUGS = {a.get('slug') for a in load_articles()}
        except Exception:
            _CLEAN_BROKEN_ART_SLUGS = set()
    art_slugs = _CLEAN_BROKEN_ART_SLUGS
    # published slug 集合：get_published_tool_slugs 自带模块级缓存，无需处理
    published = get_published_tool_slugs()
    # /articles/ 下的非文章目录（内容分类页），保持链接
    _valid_article_dirs = {cp['slug'] for cp in build.ARTICLE_CATEGORY_PAGES} | {'page'}

    def _fix(m):
        kind = m.group(1)   # 'tools' 或 'articles'
        slug = m.group(2)   # 实际 slug
        if kind == 'tools' and slug in published:
            return m.group(0)
        if kind == 'articles' and (slug in art_slugs or slug in _valid_article_dirs):
            return m.group(0)
        return m.group(3)  # 降级为纯文本，保留链接文字

    return re.sub(
        r'<a\s[^>]*?href="[^"]*?/(tools|articles)/([A-Za-z0-9._\-]+)(?:/index\.html|/(?:\?[^"]*)?)?"[^>]*>(.*?)</a>',
        _fix, html, flags=re.I | re.S)

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

def build_tool_title(tool):
    import build  # 延迟：build 完全加载后解析 build 级符号
    """功能定位流标题：从工具自身 description 提炼定位，不依赖百度原词（消除跨实体噪声）。"""
    name = tool['name']
    pos = build.gen_positioning(tool)
    return build.build_title(name, pos, build.BUILD_YEAR)

def build_tool_cross_links(tool, all_compares=None, all_alternatives=None, all_rankings=None):
    """生成工具页『相关对比/替代/排行』区块，救活孤岛详情页（P0-6）。"""
    slug = tool['slug']
    cat = tool.get('category', '')
    cards = ''
    # P0-3（2026-08-09）：同名不同 slug 的对比/替代页只保留一个，避免用户看到重复链接
    seen_titles = set()

    # 本工具参与的对比页
    for c in (all_compares or []):
        if slug in c.get('compared_tools', []) and c.get('slug'):
            _t = (c.get('title') or '').strip()
            if _t and _t in seen_titles:
                continue
            seen_titles.add(_t)
            cards += (f'<a href="/compare/{c["slug"]}/" class="cross-link-card">'
                      f'⚖️ {escape_html(_t)}</a>\n')

    # 以本工具为目标的替代页
    for a in (all_alternatives or []):
        if a.get('target_tool') == slug and a.get('slug'):
            _t = (a.get('title') or '').strip()
            if _t and _t in seen_titles:
                continue
            seen_titles.add(_t)
            cards += (f'<a href="/alternatives/{a["slug"]}/" class="cross-link-card">'
                      f'🔄 {escape_html(_t)}</a>\n')

    # 本分类的排行榜
    for r in (all_rankings or []):
        if r.get('type') == 'category' and r.get('category') == cat and r.get('slug'):
            cards += (f'<a href="/ranking/{r["slug"]}/" class="cross-link-card">'
                      f'📊 {escape_html(r["title"])}</a>\n')
            break

    if not cards:
        return ''
    return f'''<div class="related-tools tool-cross-links">
        <h3>🔗 {escape_html(tool["name"])} 相关对比、替代与排行</h3>
        <div class="related-grid">{cards}</div>
    </div>'''

def build_compare_section_html(tool, tool_map):
    """渲染 A-vs-B 竞品对比小节(数据来自已核查竞品的实时字段, 结论数据驱动)。"""
    cs = tool.get('compare_section')
    if not cs or not cs.get('competitors'):
        return ''
    comps = [tool_map[s] for s in cs['competitors'] if s in tool_map]
    if len(comps) < 2:
        return ''
    rows = [tool] + comps
    head = ('<thead><tr><th>工具</th><th>编辑评分</th><th>价格</th><th>核心功能</th><th>平台</th></tr></thead>')
    body = '<tbody>'
    for i, t in enumerate(rows):
        hl = ' class="compare-current"' if i == 0 else ''
        feats = '、'.join((t.get('features') or [])[:3]) or (t.get('verified_features') or [])[:3] or '—'
        if isinstance(feats, list):
            feats = '、'.join(feats)
        body += (f'<tr{hl}><td><a href="/tools/{t["slug"]}/">'
                 f'{escape_html(t["name"])}</a></td>'
                 f'<td>{escape_html(str(t.get("rating", "")))}</td>'
                 f'<td>{escape_html(str(t.get("price", "")))}</td>'
                 f'<td>{escape_html(str(feats))}</td>'
                 f'<td>{escape_html(str(t.get("platform", "") or t.get("verified_platform", "")))}</td></tr>')
    body += '</tbody>'
    verdict = cs.get('verdict', '')
    return f'''<div class="compare-section">
        <h3>🆚 {escape_html(tool["name"])} 竞品对比</h3>
        <div class="compare-table-wrap"><table>
            {head}{body}
        </table></div>
        <p class="compare-verdict">{escape_html(verdict)}</p>
        <p class="compare-note">* 对比基于已核查的同赛道竞品数据, 编辑评分代表本站对该工具受欢迎度/实用度的评定。</p>
    </div>'''

def build_tool_page(tool, all_tools, all_articles=None, all_compares=None, all_alternatives=None, all_rankings=None):
    import build  # 延迟：build 完全加载后解析 build 级符号
    """生成单个工具详情页的完整HTML"""
    slug = tool['slug']

    # ── SEO关键词：优先用seo_keywords字段，fallback到模板 ───────────────
    seo_kw_list = tool.get('seo_keywords', [])
    if seo_kw_list:
        seo_kw = ','.join(k.strip() for k in seo_kw_list if k.strip())
    else:
        seo_kw = f"{tool['name']},{tool['name']}评测,{tool['name']}使用教程,{tool.get('category','')},AI工具"

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
            related_cards += f'''<a href="/tools/{r['slug']}/" class="related-card">
                {tool_icon_html(r, size='sm')}
                <div style="font-weight:600;">{r['name']}</div>
                <div style="font-size:13px;color:#666;">{r['category']}</div>
            </a>
'''
        related_html = f'''<div class="related-tools" id="relatedSection">
            <h3>🔗 相关工具推荐</h3>
            <div class="related-grid">{related_cards}</div>
        </div>'''

    # ── 竞品对比小节（A-vs-B, 基于已核查数据）────────────────────────
    _tool_map = {t['slug']: t for t in all_tools}
    compare_html = build_compare_section_html(tool, _tool_map)

    # ── 相关文章（工具页底部推荐2-3篇相关文章）────────────────────────
    related_articles_html = ''
    matched = []
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
                cards += f'''<a href="/articles/{a['slug']}/" class="related-card">
                    <div style="font-weight:600;margin-bottom:4px;">📖 {escape_html(a['title'][:30])}</div>
                    <div style="font-size:13px;color:#666;">{a.get('dateFull', a.get('date', ''))}</div>
                </a>
'''
            related_articles_html = f'''<div class="related-tools">
                <h3>📚 相关文章</h3>
                <div class="related-grid">{cards}</div>
            </div>'''

    # ── 侧边栏 HTML（从同一个 selected/matched 数据生成） ──
    sidebar_tools_html = ''
    if selected:
        items = ''
        for r in selected[:5]:
            is_free = '免费' in r.get('price', '') or r.get('price', '') == ''
            tag_html = ' <span class="rel-tag free">免费</span>' if is_free else ''
            items += f'''<li class="rel-tool-item">
                {tool_icon_html(r, size='sm')}
                <a href="/tools/{r['slug']}/">{r['name']}</a>{tag_html}
            </li>'''
        sidebar_tools_html = f'''<div class="sidebar-card twocol-only">
            <h4>🔧 同类热门工具</h4>
            {items}
        </div>'''

    sidebar_articles_html = ''
    if matched:
        items = ''
        for a in matched[:3]:
            items += f"<li><a href='/articles/{a['slug']}/'>{escape_html(a['title'][:35])}</a></li>"
        sidebar_articles_html = f'''<div class="sidebar-card twocol-only">
            <h4>📖 相关文章</h4>
            <ul>{items}</ul>
        </div>'''

    # 文章内容预处理（P0-3，2026-08-09）：优缺点分析交给独立区块；FAQ 小节交给模板 faq-section。
    # 必须在 FAQ 区块之前执行——FAQ 区块需要 content_faqs 合并去重。
    content_md = tool.get('content', '')
    content_md = re.sub(r'## 优缺点分析[\s\S]*?(?=## \w)', '', content_md)
    content_md = re.sub(r'## 优缺点分析[\s\S]*$', '', content_md)
    content_md, content_faqs = extract_faq_section(content_md)

    # FAQ 区块
    faq_html = ''
    faq_schema = []
    # P0-3（2026-08-09）：合并 tool.faq 字段与正文剥离出的 FAQ，按问题去重。
    _merged_faq = []
    _seen_q = set()
    def _norm_q_key(s):
        # 去重键：去掉尾部标点/空白并小写，避免同一问题因"？/无问号"差异被判为两条
        return re.sub(r'[\s?？:：。.!！]+$', '', s).strip().lower()
    for faq_item in (tool.get('faq') or []):
        _q = (faq_item.get('question') or faq_item.get('q') or '').strip()
        _a = (faq_item.get('answer') or faq_item.get('a') or '').strip()
        _key = _norm_q_key(_q)
        if _q and _a and _key not in _seen_q:
            _seen_q.add(_key)
            _merged_faq.append({'question': _q, 'answer': _a})
    for _q, _a in content_faqs:
        _key = _norm_q_key(_q)
        if _q and _a and _key not in _seen_q:
            _seen_q.add(_key)
            _merged_faq.append({'question': _q, 'answer': _a})
    if _merged_faq:
        for faq_item in _merged_faq:
            question = faq_item['question']
            answer = faq_item['answer']
            faq_html += f'''<div class="faq-item">
                <div class="faq-q">{escape_html(question)}</div>
                <div class="faq-a">{markdown_to_html(answer)}</div>
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
        faq_html = f'''<div class="faq-section">
            <h3>❓ 常见问题</h3>
            {faq_html}
        </div>'''

    # 跨页区块：救活对比/替代/排行孤岛页（P0-7）
    cross_links_html = build_tool_cross_links(tool, all_compares, all_alternatives, all_rankings)

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

    # 徽章（防御：badge 可能是字符串而非 dict，归一化避免 AttributeError 崩溃）
    badge_html = ''
    _b = tool.get('badge')
    if isinstance(_b, str):
        _b = {'type': 'pick', 'text': _b}
    if isinstance(_b, dict) and _b.get('text'):
        badge_color = {'hot': '#ff4444', 'new': '#00aa00', 'pick': '#667eea'}.get(_b.get('type'), '#667eea')
        badge_html = f' <span class="badge" style="background:{badge_color};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;">{_b["text"]}</span>'

    # 平台
    platform_html = ''
    if tool.get('platform'):
        platform_html = f'<div class="tool-meta-item">📦 <strong>平台</strong>：{tool["platform"]}</div>'

    # 访问量短语（2026-08-16 评分行压缩：保留客观硬数据，无数据则不显示，避免"暂无数据"尴尬）
    # 2026-08-31：补 N/A/n/a/NA/none/'-' 等无数据值（实测 19 个工具 visits='N/A' 外露"月访问约N/A"）
    _visits_raw = str(tool.get('visits', '') or '').strip()
    _visits_clause = (f' · 月访问约{_visits_raw}'
                      if _visits_raw and _visits_raw.lower() not in ('暂无数据', '0', 'none', 'n/a', 'na', '-', '未知', '无')
                      else '')

    # 结构化数据
    from datetime import datetime, timedelta
    today_iso = datetime.now().strftime('%Y-%m-%d')
    # 2026-08-01 修复: datePublished 优先用 published_date(首次发布时间), created_date(收录时间)作兜底
    # 字段语义: created_date=入库/收录时间(永不改) | published_date=首次发布时间 | updated_date=最近更新
    date_published = tool.get('datePublished', tool.get('date_published',
                        tool.get('published_date',
                         tool.get('created_date', today_iso))))
    # dateModified：优先用显式"最后更新"字段。
    # 2026-08-01 修复：原只查 dateModified/date_modified/last_updated，漏掉了数据里实际使用的
    # updated_date 字段，导致设置了 updated_date 的工具（如腾讯混元 updated_date=2026-07-26）
    # 其"更新"日期回落到"收录"日，页面上"更新"与"收录"两个日期相等。
    # 注意：绝不能默认用"今天"——否则每次构建所有工具都变今天，被搜索引擎视为作弊，
    # 且会导致"最近一周发布的工具"更新日期全部聚成同一天（2026-07-17 的 bug 根因）
    _date_mod_raw = tool.get('dateModified',
                      tool.get('date_modified',
                       tool.get('last_updated',
                        tool.get('updated_date', ''))))
    if _date_mod_raw:
        date_modified = _date_mod_raw
        # 安全护栏：若更新日早于收录日（数据异常），回退到收录日，避免出现"更新比收录还早"
        _cd_raw = tool.get('created_date') or tool.get('datePublished') or tool.get('date_published')
        if _cd_raw:
            try:
                if datetime.strptime(date_modified[:10], '%Y-%m-%d') < datetime.strptime(_cd_raw[:10], '%Y-%m-%d'):
                    date_modified = _cd_raw[:10]
            except Exception:
                pass
    elif tool.get('published_date') or tool.get('created_date'):
        # 2026-08-01 修复: 无显式更新字段时, dateModified 回落到"发布时间"(published_date)优先,
        # 其次才是收录时间(created_date) —— 避免"更新日期 < 发布日期"的逻辑矛盾
        # (如 wps-ai: 发布2026-07-31, 收录2026-03-26, 若回落收录日会显示"更新3/26早发布7/31")
        _mod_fallback = tool.get('published_date') or tool.get('created_date')
        try:
            _md = datetime.strptime(str(_mod_fallback)[:10], '%Y-%m-%d')
            date_modified = _md.strftime('%Y-%m-%d')
        except Exception:
            date_modified = date_published
    else:
        date_modified = date_published

    # 最终护栏: dateModified 绝不能早于 datePublished（更新不早于发布）
    try:
        if datetime.strptime(str(date_modified)[:10], '%Y-%m-%d') < datetime.strptime(str(date_published)[:10], '%Y-%m-%d'):
            date_modified = str(date_published)[:10]
    except Exception:
        pass

    category_slug_for_schema = get_category_slug(tool.get('category', ''))
    breadcrumb_data = {
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
                "name": "全部工具",
                "item": "https://www.aitoollab.cn/tools/"
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": tool.get('category', ''),
                "item": f"https://www.aitoollab.cn/category/{category_slug_for_schema}/"
            },
            {
                "@type": "ListItem",
                "position": 4,
                "name": tool['name'],
                "item": f"https://www.aitoollab.cn/tools/{slug}/"
            }
        ]
    }

    # 价格/offers数组化（从tool数据提取免费版和付费版两档）
    # 修复问题8：正确解析"免费版+Plus $20/月"这类含"+"的多档价格
    raw_price = tool.get('price', '')
    price_str = str(raw_price).strip()
    import re as _re_price
    offers_data = []

    # 解析价格字符串中的所有价格档位
    # 匹配 $数字/月 或 ¥数字/月 或 数字元/月 等格式
    price_matches = _re_price.findall(r'[\$¥￥]?\s*(\d+(?:\.\d+)?)\s*/?\s*(?:月|month|year|年)', price_str, _re_price.IGNORECASE)

    # 始终有免费版 offer（如果没有明确说"付费"）
    if '免费' in price_str or not price_str or price_str in ('Free', 'free'):
        offers_data.append({
            "@type": "Offer", "name": "免费版", "price": "0",
            "priceCurrency": "USD", "description": f"{tool['name']}免费版基础功能"
        })

    # 解析出的付费档位
    for i, price_num in enumerate(price_matches):
        # 判断货币
        currency = "USD"
        if '¥' in price_str or '￥' in price_str or '元' in price_str:
            currency = "CNY"
        tier_name = "付费版" if i == 0 else f"付费版{i+1}"
        offers_data.append({
            "@type": "Offer", "name": tier_name, "price": price_num,
            "priceCurrency": currency, "description": f"{tool['name']}{tier_name}：{price_str}"
        })

    # 如果没解析出价格且字符串明确说付费，兜底
    if not offers_data and price_str:
        offers_data = [
            {"@type": "Offer", "name": "免费版", "price": "0", "priceCurrency": "USD", "description": f"{tool['name']}免费版基础功能"},
            {"@type": "Offer", "name": "付费版", "price": "0", "priceCurrency": "USD", "description": f"{tool['name']}付费版：{price_str}"}
        ]

    # developer信息（P0 Schema去厂商化：统一为编辑组）
    dev_org = {"@type": "Organization",
                "name": "AI工具宝箱编辑组",
                "url": "https://www.aitoollab.cn/author/",
                "description": "专注 AI 工具实测与对比研究的独立编辑团队"}

    # 修复问题1：ratingCount 使用编辑组实测样本量，不再用厂商visits伪造
    _editorial_rc = int(tool.get('editorial_rating_count') or 1)

    # 修复问题2：applicationCategory 按实际分类映射，不再全部用 ProductivityApplication
    _category_map = {
        'AI对话': 'ChatApplication', 'AI写作': 'WritingApplication', 'AI绘画': 'DesignApplication',
        'AI编程': 'DeveloperApplication', 'AI视频': 'VideoEditingApplication', 'AI音频': 'MusicApplication',
        'AI办公': 'BusinessApplication', 'AI设计': 'DesignApplication', 'AI搜索': 'SearchApplication',
        'AI翻译': 'TranslationApplication', 'AI自动化': 'BusinessApplication', 'AI效率': 'ProductivityApplication',
        'AI智能体': 'ProductivityApplication', 'AI开发': 'DeveloperApplication', 'AI行业应用': 'BusinessApplication'
    }
    _app_category = _category_map.get(tool.get('category', ''), 'ProductivityApplication')

    # 修复问题4：添加 url 字段（工具官网）
    _tool_url = tool.get('url', '')

    # 修复问题5：添加 image 字段（OG图作为工具图）
    _tool_image = f"https://www.aitoollab.cn/images/og/{slug}-og.png"

    software_data = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": tool['name'],
        "url": _tool_url if _tool_url else f"https://www.aitoollab.cn/tools/{slug}/",
        "image": _tool_image,
        "applicationCategory": _app_category,
        "applicationSubCategory": tool.get('category', ''),
        "operatingSystem": tool.get('platform', 'Web'),
        "description": tool['description'],
        "datePublished": date_published,
        "dateModified": date_modified,
        "offers": offers_data,
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": build._parse_rating(tool.get('rating', '')),
            "ratingCount": _editorial_rc,
            "bestRating": 5,
            "worstRating": 1
        },
        "inLanguage": ["zh", "en"]
    }

    # developer信息（始终添加author，无developer时用工具名称兜底）
    software_data["author"] = dev_org

    # 补充 featureList（如有features字段）
    if tool.get('features'):
        software_data["featureList"] = tool['features']

    # 修复问题6：添加 isRelatedTo（同类工具关联，最多5个）
    # 注意：关联工具用 WebSite 类型而非 SoftwareApplication，避免 Google 因缺少 offers 必填字段判为 invalid
    _related_tools = tool.get('related', [])
    if _related_tools and isinstance(_related_tools, list):
        _is_related_to = []
        for rel_slug in _related_tools[:5]:
            if isinstance(rel_slug, str):
                _is_related_to.append({
                    "@type": "WebSite",
                    "name": rel_slug,
                    "url": f"https://www.aitoollab.cn/tools/{rel_slug}/"
                })
        if _is_related_to:
            software_data["isRelatedTo"] = _is_related_to

    # 补充 abstract（取description前160字）
    software_data["abstract"] = tool['description'][:160] if len(tool['description']) > 160 else tool['description']

    # 补充 speakable（TTS语音播报锚点）
    software_data["speakable"] = {
        "@type": "SpeakableSpecification",
        "cssSelector": [".article-body h2", ".article-body h3", ".tool-header-info h2", ".tool-summary"]
    }

    # 修复问题7：优缺点写入 Schema（positiveNotes/negativeNotes）
    _pros = tool.get('pros', [])
    _cons = tool.get('cons', [])
    _rating_num = tool.get('rating_value', 4.0)
    if isinstance(_rating_num, str):
        _rating_num = build._parse_rating(_rating_num)
    else:
        try:
            _rating_num = build._parse_rating(tool.get('rating', '4.0'))
        except Exception:
            _rating_num = 4.0

    _review_body = {
        "@type": "Review",
        "reviewRating": {
            "@type": "Rating",
            "ratingValue": _rating_num,
            "bestRating": 5
        },
        "author": {"@type": "Organization", "name": "AI工具宝箱编辑组"}
    }
    # 优点作为 positiveNotes
    if _pros and isinstance(_pros, list):
        _review_body["positiveNotes"] = {
            "@type": "ItemList",
            "itemListElement": [{"@type": "ListItem", "position": i+1, "name": p} for i, p in enumerate(_pros[:5])]
        }
    # 缺点作为 negativeNotes
    if _cons and isinstance(_cons, list):
        _review_body["negativeNotes"] = {
            "@type": "ItemList",
            "itemListElement": [{"@type": "ListItem", "position": i+1, "name": c} for i, c in enumerate(_cons[:5])]
        }
    software_data["review"] = _review_body

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
    infographic_path = os.path.join(build.BASE_DIR, 'images', 'infographics', f'{slug}-infographic.png')
    has_infographic = os.path.exists(infographic_path)
    infographic_html = ''
    if has_infographic:
        infographic_html = f'''<figure class="tool-infographic">
            <img src="/images/infographics/{slug}-infographic.png" alt="{escape_html(tool['name'])}功能亮点信息图" width="1200" height="630" loading="lazy">
            <figcaption>{escape_html(tool['name'])} 核心功能一览</figcaption>
        </figure>'''

    # CTA 按钮（2026-09-02 改名）：官网可访问 → "访问官网"；
    # 已人工复核确认失效的（build.BROKEN_URLS）→ 不可点击的禁用按钮 + 页面停运提示，绝不出站。
    # 匹配忽略结尾斜杠（数据里 https://x.com/ 与清单里 https://x.com 视为同一条）。
    _tool_link, _is_aff = build.get_tool_link(tool, slug, 'zh')
    _norm_url = lambda u: (u or '').rstrip('/')
    _broken_set = {_norm_url(u) for u in build.BROKEN_URLS}
    build.dead_notice_html = ''
    if _tool_link == '':
        # 空URL（如已下架工具）→ 指向站内同类替代品页面
        build.action_btn_html = '<a href="/tools/gamma/" class="action-btn action-btn-primary">查看替代工具</a>'
    elif _norm_url(_tool_link) in _broken_set:
        build.action_btn_html = (
            '<span class="action-btn action-btn-primary disabled" '
            'aria-disabled="true" title="官网已无法访问，暂不提供跳转">访问官网</span>'
        )
        build.dead_notice_html = (
            '<div class="tool-dead-notice" role="status">⚠️ <strong>官网已无法访问</strong>：'
            f'经 {DEAD_LINK_NOTICE_DATE} 人工复核（含跨境网络复核），{escape_html(tool["name"])} 的官方网站'
            '已停止服务，我们已移除跳转外链，避免您点到死链。以下介绍仅作资料存档，建议改用同类替代工具。</div>'
        )
    else:
        _rel = 'nofollow noopener sponsored' if _is_aff else 'nofollow noopener'
        build.action_btn_html = f'<a href="{_tool_link}" target="_blank" rel="{_rel}" class="action-btn action-btn-primary">访问官网</a>'

    # 文章内容（content_md 已在 FAQ 区块前预处理：优缺点 / FAQ 小节剥离）
    content_html = markdown_to_html(content_md)
    content_html = build.shift_headings(content_html, up=1)   # h1->h2, h2->h3... 正文与模板H1解耦
    content_html = inject_internal_links(content_html, slug)
    # [#404修复] 坏链清理：未发布/不存在工具的链接降级为纯文本
    content_html = clean_broken_tool_links(content_html)

    _tool_title = build_tool_title(tool)
    _tool_title_short = _tool_title.split(' - ')[0]
    _tool_pos = build.gen_positioning(tool)
    _tool_meta = build.build_meta(tool['name'], _tool_pos, tool.get('description', ''), build.BUILD_YEAR, tool=tool)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(_tool_title)}</title>
    <meta name="description" content="{escape_html(_tool_meta)}">
    <meta name="keywords" content="{escape_html(seo_kw)}">
    <link rel="canonical" href="https://www.aitoollab.cn/tools/{slug}/">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{escape_html(_tool_title)}">
    <meta property="og:description" content="{escape_html(_tool_meta)}">
    <meta property="og:url" content="https://www.aitoollab.cn/tools/{slug}/">''' + (f'\n    <meta property="og:image" content="{og_image}">\n    <meta property="og:image:width" content="1200">\n    <meta property="og:image:height" content="630">\n' if og_image else '') + f'''    <meta property="og:locale" content="zh_CN">
    <meta property="og:site_name" content="AI工具宝箱">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape_html(_tool_title_short)} - AI工具宝箱">
    <meta name="twitter:description" content="{escape_html(_tool_meta)}">''' + (f'\n    <meta name="twitter:image" content="{og_image}">' if og_image else '') + f'''
    <style>{build.CRITICAL_CSS}</style>
    <style>{build.TOOL_LIKE_CSS}</style>
    <style>{build.TOOL_ACTION_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript>
<link rel="stylesheet" href="/css/ai-widget.css?v={build.WIDGET_CSS_VERSION}">
    <script type="application/ld+json">{breadcrumb_json}</script>
    <script type="application/ld+json">{structured_data}</script>
    {faq_page_schema}
{build.BAIDU_TONGJI}
</head>
<body data-page-type="tool" data-category="{escape_html(tool.get('category', ''))}" data-ai-tool="{escape_html(tool['name'])}" data-ai-tool-slug="{slug}">
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a>
        </div>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="/">首页</a> &gt; <a href="/tools/">全部工具</a> &gt; <a href="/category/{category_slug_for_schema}/">{escape_html(tool['category'])}</a> &gt; <span>{escape_html(tool['name'])}</span>
    </nav>

    <main class="article-container-wide">
        <div class="content-main">
        <div class="tool-header">
            <div class="tool-header-top">
                {tool_icon_html(tool, large=True)}
                <div class="tool-header-info">
                    <h1>{escape_html(tool['name'])}{badge_html}</h1>
                    <div class="tool-header-meta">编辑评分 {tool['rating']} <span class="rating-note">（受欢迎度/实用度）{_visits_clause}</span></div>
                </div>
            </div>
            <div class="tool-header-desc">
                <p class="subtitle">{escape_html(tool['description'])}</p>
            </div>
            <div class="tool-meta">
                <div class="tool-meta-item">🌐 <strong>官网</strong>：{tool['url'].replace('https://', '')}</div>
                <div class="tool-meta-item">💰 <strong>价格</strong>：{tool.get('price', '')}</div>
                {platform_html}
                <div class="tool-meta-item">🏷️ <strong>分类</strong>：{escape_html(tool['category'])}</div>
                <div class="tool-meta-item tool-meta-dates">📅 <strong>收录</strong> <time datetime="{date_published}" itemprop="datePublished">{date_published}</time> · 🔄 <strong>更新</strong> <time datetime="{date_modified}" itemprop="dateModified">{date_modified}</time></div>
            </div>
            <div class="action-bar">
                {build.action_btn_html}
                <button type="button" class="action-btn action-btn-ghost fav-btn" data-fav-slug="{slug}">☆ 收藏</button>
                <span class="tool-like" role="button" tabindex="0" data-slug="{slug}" aria-label="给 {escape_html(tool['name'])} 点赞" title="好用，点个赞">👍 <b class="tool-like-count">0</b></span>
                <a href="/category/" class="action-btn action-btn-ghost">全部工具</a>
                <button type="button" class="action-btn action-btn-ghost" data-copy-link data-label="复制链接">复制链接</button>
                <a href="/contact.html?tool={slug}" class="action-btn action-btn-ghost" title="价格、链接或信息有误？告诉我们">信息有误？</a>
            </div>
            {build.dead_notice_html}
        </div>

        {features_html}

        <article class="article-body" data-tts>
            <div class="tool-summary">
                <strong>📋 编辑总结</strong><br>
                <span>{escape_html(tool['description'])} {'' if tool.get('price','') in ('','免费') else f'定价：{tool.get('price','')}。'}{'编辑评分：' + tool['rating'] + '。'}</span>
            </div>
            {content_html}
        </article>

        {infographic_html}

        {pros_cons_html}

        {faq_html}

        {compare_html}

        {cross_links_html}

            <div class="content-related">
                {related_html}
                {related_articles_html}
            </div>

            <div class="mobile-ad-inline">📱 继续阅读 · 猜你喜欢</div>
        </div><!-- /.content-main -->

        <div class="page-sidebar-wrap">
        <aside class="page-sidebar">
            <div class="ad-slot ad-slot-large"></div>
            {sidebar_tools_html}
            {sidebar_articles_html}
        </aside>
        </div>
    </main>

    <footer class="footer">
        <p>© {build.BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · ''' + build.ICP_BEIAN + '''</p>
    </footer>
    ''' + build.BACK_TO_TOP_BLOCK + '''
    <script src="/js/ai-likes.js?v={LIKES_JS_VERSION}" defer></script>
    <script src="/js/ai-assistant.js?v={WIDGET_JS_VERSION}" defer></script>
    <script src="/reco/loader.js" defer></script>
</body>
</html>'''
    return html
