# render_news_dict.py — 快讯页 + 词典页/索引
# 模块10：从 build.py 拆分（2026-08-24）
import os
import re
import json
from datetime import datetime as _dt_build
from urllib.parse import quote as url_quote

from build_lib.html_utils import (
    escape_html, markdown_to_html,
)
from build_lib.data_loaders import (
    load_news_archive, load_articles, _load_dict_terms, get_category_slug,
)
from build_lib.render_tool import (
    make_tool_card_html, build_tool_page, ensure_og_image,
)


def build_news_page(all_tools=None):
    import build  # 延迟：build 完全加载后解析
    if all_tools is None:
        all_tools = load_tools()
    daily, dates = load_news_archive()
    if not dates:
        print('[NEWS] 无快讯数据，跳过')
        return

    today = dates[0]
    today_news = daily[today]
    NEWS_DIR = os.path.join(build.BASE_DIR, 'news')
    SITE = 'https://www.aitoollab.cn'

    # 快讯硬伤门禁（2026-08-15）：构建前检查当天快讯，空摘要/英文标题/空标题 打印醒目警告。
    # 只报告不阻断（快讯页生成优先于质量；"价值提炼"靠生成 prompt 治本，此处只兜底硬伤）。
    try:
        import check_news_quality as _nq
        _nfail = 0
        for _it in today_news:
            _f, _w = _nq.check_one(_it)
            if _f:
                _nfail += 1
                print(f'  [快讯门禁] ✗ {_it.get("id","")}: {"; ".join(_f)} → {( _it.get("title") or "")[:40]}')
        if _nfail:
            print(f'  [快讯门禁] ⚠️ 当天 {len(today_news)} 条中有 {_nfail} 条硬伤，请补 summary / 译标题 / 删空条目')
    except Exception:
        pass

    HEADER = '<header class="header"><div class="header-inner"><a href="/" style="text-decoration:none;"><div class="site-logo">🛠️ AI工具宝箱 <span>每日更新 · 收录工具 持续更新</span></div></a></div></header>'
    FOOTER = f'<footer class="footer"><p>&copy; {build.BUILD_YEAR} AI工具宝箱 · 每日精选优质AI工具 · {build.ICP_BEIAN}</p></footer>'

    CAT_LABEL = {'models':'模型发布','products':'产品发布','industry':'行业动态','opinion':'观点','paper':'论文研究'}
    CAT_COLOR = {'models':'#6366f1','products':'#00A64F','industry':'#f59e0b','opinion':'#ec4899','paper':'#3b82f6'}
    CAT_ORDER = ['models','products','industry','opinion','paper']
    # 栏目 SEO：栏目标题 + 长尾关键词（承接检索词，沉淀权重）
    CAT_SEO = {
        'models':   {'longtail':'最新大模型发布,开源大模型,AI模型上线,大模型汇总,AI基础模型',
                     'desc':'AI工具宝箱每日聚合AI模型发布动态：最新大模型发布、开源模型、模型更新与实测解读一网打尽，覆盖DeepSeek、Qwen、Kimi、Claude、GPT等主流与国产模型，每条附官方来源可溯源，帮你紧跟AI模型进展、把握选型方向。'},
        'products': {'longtail':'最新AI产品,AI工具上线,AI应用发布,AI产品汇总,AI软件更新',
                     'desc':'AI工具宝箱每日聚合AI产品发布动态：最新AI产品、AI应用上线与功能更新一站汇总，覆盖对话、写作、绘画、视频、编程等品类，每条附官方来源可溯源并附一句话使用建议，同时给出免费额度与价格信息供快速判断，帮你及时发现值得试用与收藏的新工具。'},
        'industry': {'longtail':'AI行业新闻,AI行业动态,人工智能资讯,AI公司动态,AI融资并购',
                     'desc':'AI工具宝箱每日聚合AI行业动态：AI公司动态、融资并购、政策监管与产业趋势一站汇总，覆盖OpenAI、谷歌、字节、阿里等国内外大厂与创业公司，每条附官方来源可溯源并附编辑部点评，数据每日更新，帮你高效把握行业风向、发现机会。'},
        'opinion':  {'longtail':'AI观点,AI评论,人工智能思考,AI趋势解读,AI深度评论',
                     'desc':'AI工具宝箱每日聚合AI观点内容：大模型与AI行业趋势解读、深度评论与争议话题分析，观点多元、附事实依据，覆盖技术路线、商业模式与社会影响等维度，既有行业大咖视角也有编辑部独立解读，并附原文链接便于追溯，帮你建立更独立、更立体的判断。'},
        'paper':    {'longtail':'AI论文,最新AI研究,人工智能论文,AI论文解读,机器学习论文',
                     'desc':'AI工具宝箱每日聚合AI论文研究动态：最新AI论文、研究成果与论文解读，覆盖大模型、Agent、多模态、推理优化等方向，每条附论文来源可溯源并附核心结论速览，按研究方向归类便于查阅，帮你高效追踪学术前沿、读懂关键技术突破。'},
    }

    # ── 工具名 → slug 映射（自动内链）──
    _slug_set = set()
    name_map = []
    for _t in all_tools:
        _nm = (_t.get('name') or '').strip()
        _sl = (_t.get('slug') or '').strip()
        if not _nm or not _sl:
            continue
        if len(_nm) < 2:
            continue
        if _nm.isascii() and len(_nm) < 3:
            continue
        name_map.append((_nm, _sl))
        _slug_set.add(_sl)
    _ALIASES = {'Kimi 智能助手': 'kimi', '智谱清言': 'zhipu', '通义千问': 'qwen', '文心一言': 'wenxin'}
    for _anm, _asl in _ALIASES.items():
        if _asl in _slug_set and not any(_anm == _n for _n, _ in name_map):
            name_map.append((_anm, _asl))
    name_map.sort(key=lambda x: -len(x[0]))

    def _linkify(text):
        """在已转义的纯文本中，将工具名替换为站内链接（避免嵌套/重叠）。"""
        matches = []
        for _nm, _sl in name_map:
            _start = 0
            while True:
                _i = text.find(_nm, _start)
                if _i == -1:
                    break
                matches.append((_i, _i + len(_nm), _sl, _nm))
                _start = _i + len(_nm)
        matches.sort(key=lambda m: (m[0], -(m[1] - m[0])))
        out = []
        last = 0
        for _s, _e, _sl, _nm in matches:
            if _s < last:
                continue
            out.append(text[last:_s])
            out.append(f'<a href="/tools/{_sl}/" class="news-inlink">{_nm}</a>')
            last = _e
        out.append(text[last:])
        return ''.join(out)

    def _card(item, first=False, date_ctx=None):
        # 时间线条目（2026-08-16 第三版，对标 ai-bot.cn 移动端：大标题自然换行、无下划线、去卡片盒）
        cat = item.get('category','')
        cl = CAT_LABEL.get(cat,cat)
        cc = CAT_COLOR.get(cat,'#64748b')
        # 标题规范化：去尾部多余标点（快准狠，标题干净利落）
        title = (item.get('title') or '').strip()
        while title and title[-1] in '。！？，、；：…!?.,;: ':
            title = title[:-1].rstrip()
        title_l = _linkify(escape_html(title))
        summary = (item.get('summary') or '').strip()
        src = escape_html(item.get('source',''))
        src_url = item.get('source_url','')
        ts = item.get('published_at','')
        ts_display = ts[:16].replace('T',' ')[5:] if ts else ''  # 08-14 22:27，去年份更简
        date_link = f'<a href="/news/{date_ctx}/" class="news-date-ctx">{date_ctx}</a>' if date_ctx else ''
        sum_html = f'<p class="news-item-summary">{_linkify(escape_html(summary))}</p>' if summary else ''
        readmore = f'<a href="{src_url}" target="_blank" rel="noopener nofollow" class="news-readmore">阅读原文</a>' if src_url else ''
        return f'''            <article class="news-item">
                <i class="news-item-dot" style="background:{cc}"></i>
                <div class="news-item-meta"><span class="news-item-cat" style="color:{cc}">{cl}</span>{f'<time>{ts_display}</time>' if ts_display else ''}</div>
                <h2 class="news-item-title">{title_l}</h2>
                {sum_html}
                <div class="news-item-foot">{f'<span>来源：{src}</span>' if src else ''}{readmore}{date_link}</div>
            </article>'''

    SHARE_CSS = '.news-share{display:flex;gap:8px;align-items:center}.news-share-btn{display:inline-flex;align-items:center;gap:4px;padding:5px 12px;border-radius:6px;border:1px solid #e2e8f0;background:#f8fafc;font-size:13px;color:#475569;cursor:pointer;text-decoration:none;transition:all .15s;font-family:inherit}.news-share-btn:hover{background:#e6f4ed;border-color:#00A64F;color:#00A64F}.news-share label{font-size:13px;color:#94a3b8;margin-right:4px}.news-toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1e293b;color:#fff;padding:10px 20px;border-radius:8px;font-size:13px;z-index:999;opacity:0;transition:opacity .2s}.news-toast.show{opacity:1}[data-theme="dark"] .news-share-btn{background:#1e293b;border-color:#334155;color:#94a3b8}[data-theme="dark"] .news-share-btn:hover{background:rgba(0,166,79,0.12);border-color:#00A64F;color:#00A64F}.news-inlink{color:#00A64F;text-decoration:none;font-weight:600}.news-inlink:hover{text-decoration:none;opacity:.8}[data-theme="dark"] .news-inlink{color:#34d399}.news-catnav{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 4px}.news-catnav-link{display:inline-block;padding:6px 14px;border-radius:20px;background:#f1f5f9;color:#475569;font-size:13px;text-decoration:none;transition:all .15s}.news-catnav-link:hover{background:#e6f4ed;color:#00A64F}[data-theme="dark"] .news-catnav-link{background:#1e293b;color:#94a3b8}[data-theme="dark"] .news-catnav-link:hover{background:rgba(0,166,79,.12);color:#34d399}.news-date-ctx{color:#94a3b8;font-size:12px;text-decoration:none;margin-left:2px}.news-date-ctx:hover{color:#00A64F}[data-page-type="news"] .container{max-width:780px;margin:0 auto;padding:6px 20px 32px}[data-page-type="news"] .breadcrumb{max-width:780px;padding:0 20px;margin:8px auto 8px}[data-page-type="news"] .container.news-index,[data-page-type="news"] .breadcrumb.news-index{max-width:1100px}.news-layout{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:28px;align-items:start}.news-sidebar{position:sticky;top:16px;display:flex;flex-direction:column;gap:18px}.news-side-box{background:var(--surface,#fff);border:1px solid var(--border,#e2e8f0);border-radius:12px;padding:14px 16px}.news-side-title{font-size:14px;font-weight:700;margin:0 0 10px;color:var(--text-main,#1e293b)}.news-day-list{display:flex;flex-direction:column;gap:2px;max-height:380px;overflow-y:auto}.news-day-link{display:flex;justify-content:space-between;align-items:center;padding:8px 10px;border-radius:8px;font-size:13.5px;color:var(--text-main,#1e293b);text-decoration:none;line-height:1.4}.news-day-link:hover{background:#e6f4ed;color:#00A64F}.news-day-link .n{font-size:12px;color:#94a3b8;margin-left:8px;flex-shrink:0}.news-day-block{margin-bottom:28px;scroll-margin-top:200px}.news-day-divider{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 16px;padding:10px 14px 10px 16px;background:linear-gradient(90deg,#f0fdf4 0%,#f0fdf400 100%);border-left:5px solid #00A64F;border-radius:0 8px 8px 0}.news-day-divider .d{font-size:20px;font-weight:800;color:var(--text-main,#1e293b);letter-spacing:.5px}.news-day-divider .wk{display:inline-block;padding:2px 10px;background:#00A64F;color:#fff;font-size:12px;font-weight:700;border-radius:12px;letter-spacing:.5px}.news-day-divider a.news-day-more{margin-left:auto;font-size:12.5px;font-weight:500;color:#00A64F;text-decoration:none;opacity:.8}.news-day-divider a.news-day-more:hover{opacity:1;text-decoration:underline}[data-theme="dark"] .news-side-box{background:#1e293b;border-color:#334155}[data-theme="dark"] .news-day-link{color:#cbd5e1}[data-theme="dark"] .news-day-link:hover{background:rgba(0,166,79,.12);color:#34d399}[data-theme="dark"] .news-day-divider{background:linear-gradient(90deg,rgba(52,211,153,.10) 0%,rgba(52,211,153,0) 100%);border-left-color:#34d399}[data-theme="dark"] .news-day-divider .d{color:#f1f5f9}[data-theme="dark"] .news-day-divider .wk{background:#34d399;color:#0f172a}@media (max-width:900px){.news-layout{grid-template-columns:1fr}.news-sidebar{display:none}.news-day-divider{padding:8px 12px}.news-day-divider .d{font-size:18px}.news-day-block{scroll-margin-top:190px}.news-day-strip{display:flex}}html{scroll-behavior:smooth}[data-page-type="news"] .news-cards{display:block;position:relative;margin:0 0 8px;padding-left:24px;border-left:2px dotted #d8e0ea}.news-item{position:relative;padding:15px 0 17px}.news-item-dot{position:absolute;left:-30px;top:22px;width:11px;height:11px;border-radius:50%;box-shadow:0 0 0 3px var(--body-bg,#fff)}.news-item-meta{display:flex;gap:10px;align-items:baseline;font-size:12.5px;color:#94a3b8;margin-bottom:3px}.news-item-cat{font-weight:600}.news-item-title{font-size:17.5px;font-weight:700;line-height:1.55;margin:0 0 8px;color:var(--text-main,#1e293b)}.news-item-summary{font-size:14px;line-height:1.85;color:var(--text-muted,#475569);margin:0 0 8px}.news-item-foot{display:flex;gap:14px;align-items:center;font-size:12.5px;color:#94a3b8}[data-page-type="news"] .news-readmore{margin-left:auto;color:#00A64F;background:none;padding:0;border-radius:0;font-size:12.5px;font-weight:600;text-decoration:none}[data-page-type="news"] .news-readmore:hover{opacity:.75}.news-day-strip{display:none;gap:8px;overflow-x:auto;padding:2px 2px 12px;margin-bottom:4px;scrollbar-width:none;-webkit-overflow-scrolling:touch}.news-day-strip::-webkit-scrollbar{display:none}.news-day-strip a{flex-shrink:0;padding:5px 13px;border-radius:16px;background:#f1f5f9;color:#475569;font-size:12.5px;text-decoration:none;white-space:nowrap}.news-day-strip a:active{background:#00A64F;color:#fff}[data-theme="dark"] [data-page-type="news"] .news-cards{border-left-color:#334155}[data-theme="dark"] .news-item-title{color:#f1f5f9}[data-theme="dark"] .news-item-summary{color:#94a3b8}[data-theme="dark"] .news-item-dot{box-shadow:0 0 0 3px #0f172a}[data-theme="dark"] [data-page-type="news"] .news-readmore{color:#34d399}[data-theme="dark"] .news-day-strip a{background:#1e293b;color:#94a3b8}@media (max-width:900px){.news-day-strip{display:flex}}'
    SHARE_JS = 'function copyLink(){navigator.clipboard.writeText(location.href).then(function(){var t=document.getElementById("newsToast");t.classList.add("show");setTimeout(function(){t.classList.remove("show")},1800)})}'
    FILTER_JS = f"""(function(){{
    var p=document.querySelectorAll('.news-filter-pill');
    var c=document.querySelectorAll('.news-item');
    var cats={json.dumps(CAT_LABEL)};
    p.forEach(function(b){{b.addEventListener('click',function(e){{e.preventDefault();var f=b.dataset.filter;
    p.forEach(function(x){{x.classList.remove('active')}});b.classList.add('active');
    c.forEach(function(x){{var t=(x.querySelector('.news-item-cat')||{{}}).textContent||'';
    x.style.display=(f==='all'||t===cats[f])?'':'none'}});
    document.querySelectorAll('.news-day-block').forEach(function(s){{
    var any=Array.prototype.some.call(s.querySelectorAll('.news-item'),function(x){{return x.style.display!=='none'}});
    s.style.display=any?'':'none'}})}})}})
}})()"""

    # ── /news/ ──
    pills = ''.join(f'<a href="#{k}" class="news-filter-pill{" active" if k=="all" else ""}" data-filter="{k}">{v}</a>'
                    for k,v in [('all','全部')]+[(c, CAT_LABEL[c]) for c in ['models','products','industry','opinion']])
    # ── /news/ 汇总页：多天连排长页 + 日期隔断 + 右侧栏（2026-08-16 对标 ai-bot.cn/daily-ai-news/）──
    INDEX_DAYS = 30  # 汇总页展示最近 30 天；更早的经日期索引进单期页
    _WEEKDAYS = ['周一','周二','周三','周四','周五','周六','周日']
    def _day_label(ds):
        try:
            _dt = _dt_build.strptime(ds, '%Y-%m-%d')
            return f'{_dt.month}月{_dt.day}日', _WEEKDAYS[_dt.weekday()]
        except Exception:
            return ds, ''
    _labels = {d: _day_label(d) for d in dates}
    index_dates = [d for d in dates[:INDEX_DAYS] if daily[d]]
    day_blocks = []
    for d in index_dates:
        _items = daily[d]
        _dl, _wk = _labels[d]
        _cards_d = ''.join(_card(item, i==0) for i,item in enumerate(_items))
        day_blocks.append(f'''<section class="news-day-block" id="d-{d}">
<h2 class="news-day-divider">{_dl}<span class="wk">{_wk}</span><a href="/news/{d}/" class="news-day-more">{len(_items)}条精选 · 单期页</a></h2>
<div class="news-cards">{_cards_d}</div>
</section>''')
    feed = '\n'.join(day_blocks)
    # 右侧栏：日期索引（锚点跳转当天区块；超出 INDEX_DAYS 的链到单期页）
    _day_links = ''.join(
        f'<a href="#d-{d}" class="news-day-link"><span>{_labels[d][0]} {_labels[d][1]}</span><span class="n">{len(daily[d])}条</span></a>'
        for d in index_dates)
    _older_links = ''.join(
        f'<a href="/news/{d}/" class="news-day-link"><span>{d}</span><span class="n">{len(daily[d])}条</span></a>'
        for d in dates[INDEX_DAYS:INDEX_DAYS+14])

    # 取当天头条摘要作 meta description 钩子
    _ns = today_news[0].get('summary','') if today_news else ''
    _ns = _ns.replace('\n',' ').strip()[:150]
    if not _ns:
        _ns = 'AI行业最新动态'
    built_urls = [f'{SITE}/news/']
    cats_present = sorted({it.get('category') for d in dates for it in daily[d] if it.get('category') in CAT_LABEL},
                          key=lambda c: CAT_ORDER.index(c) if c in CAT_ORDER else 99)
    catnav = ''.join(f'<a href="/news/{c}/" class="news-catnav-link">{CAT_LABEL[c]}</a>' for c in cats_present)
    _total_shown = sum(len(daily[d]) for d in index_dates)
    # 移动端顶部日期条（侧栏在移动端隐藏，锚点导航靠它，2026-08-16 第三轮）
    _strip = ''.join(f'<a href="#d-{d}">{_labels[d][0]}</a>' for d in index_dates[:14])

    index_html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI快讯 - {today} 精选 | AI行业每日动态 - AI工具宝箱</title>
<meta name="description" content="{escape_html(_ns)}——AI工具宝箱{today}精选{len(today_news)}条AI快讯，覆盖大模型发布、AI产品更新、融资动态与行业政策，每条附官方来源可溯源并提炼要点，帮你高效掌握AI行业动态。">
<meta name="keywords" content="AI快讯,AI新闻,AI日报,AI行业动态,{today}">
<link rel="canonical" href="{SITE}/news/"><style>{build.CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript><style>{SHARE_CSS}</style>
<!-- 百度统计（异步加载，不阻塞渲染） -->
{build.BAIDU_TONGJI}
</head>
<body data-page-type="news">
{HEADER}
<nav class="breadcrumb news-index"><a href="/">首页</a> &raquo; <span>AI快讯</span></nav>
<main class="container news-index">
<div class="news-header"><div class="news-header-top">
<div><h1 class="news-page-title">AI快讯</h1><p class="news-page-date">{today} 更新 · 共{len(dates)}期 · 本页最近{len(index_dates)}天{_total_shown}条</p></div>
<div class="news-share"><label>分享：</label>
<button class="news-share-btn" onclick="copyLink()">微信</button>
<a class="news-share-btn" href="https://service.weibo.com/share/share.php?url={url_quote(SITE+'/news/')}&title={url_quote('AI快讯 - '+today+' 精选')}" target="_blank" rel="noopener">微博</a>
<a class="news-share-btn" href="/rss.xml" target="_blank" rel="noopener">RSS</a>
</div></div>
<div class="news-filter-bar">{pills}</div></div>
<div class="news-day-strip">{_strip}</div>
<div class="news-layout">
<div class="news-feed">{feed}</div>
<aside class="news-sidebar">
<div class="news-side-box"><h3 class="news-side-title">按分类浏览</h3><div class="news-catnav">{catnav}</div></div>
<div class="news-side-box"><h3 class="news-side-title">日期索引</h3><div class="news-day-list">{_day_links}{_older_links}</div></div>
</aside>
</div>
</main>
{FOOTER}
{build.BACK_TO_TOP_BLOCK}
<div id="newsToast" class="news-toast">链接已复制，打开微信粘贴即可分享</div>
<script>{SHARE_JS}</script><script>{FILTER_JS}</script>
</body></html>'''

    os.makedirs(NEWS_DIR, exist_ok=True)
    with open(os.path.join(NEWS_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
    print(f'  [OK] news/index.html (最近{len(index_dates)}天{_total_shown}条)')

    # ── /news/YYYY-MM-DD/ ──
    for d in dates:
        items = daily[d]
        cards_d = ''.join(_card(item, i==0) for i,item in enumerate(items))
        # 取当天头条摘要作 meta description 钩子
        _ns = items[0].get('summary','') if items else ''
        _ns = _ns.replace('\n',' ').strip()[:150]
        if not _ns:
            _ns = 'AI行业最新动态'
        idx = dates.index(d)
        prev = f'<a href="/news/{dates[idx+1]}/" class="news-nav-btn">← {dates[idx+1]}</a>' if idx < len(dates)-1 else ''
        nxt = f'<a href="/news/{dates[idx-1]}/" class="news-nav-btn">{dates[idx-1]} →</a>' if idx > 0 else ''
        title_d = f'{d} AI快讯 · AI行业每日动态 - AI工具宝箱'

        daily_html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_d}</title>
<meta name="description" content="{escape_html(_ns)}——AI工具宝箱{d}精选{len(items)}条AI快讯，覆盖大模型发布、AI产品更新、融资动态与行业政策，每条附官方来源可溯源并提炼要点，帮你高效掌握AI行业动态。">
<meta name="keywords" content="AI快讯,AI新闻,{d}">
<link rel="canonical" href="{SITE}/news/{d}/"><style>{build.CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript><style>{SHARE_CSS}</style>
<!-- 百度统计（异步加载，不阻塞渲染） -->
{build.BAIDU_TONGJI}
</head>
<body data-page-type="news">
{HEADER}
<nav class="breadcrumb"><a href="/">首页</a> &raquo; <a href="/news/">AI快讯</a> &raquo; <span>{d}</span></nav>
<main class="container">
<div class="news-header"><div class="news-header-top">
<div><h1 class="news-page-title">{d} AI快讯</h1><p class="news-page-date">{len(items)}条精选</p></div>
<div class="news-share"><label>分享：</label>
<button class="news-share-btn" onclick="copyLink()">微信</button>
<a class="news-share-btn" href="https://service.weibo.com/share/share.php?url={url_quote(SITE+'/news/'+d+'/')}&title={url_quote(d+' AI快讯')}" target="_blank" rel="noopener">微博</a>
<a class="news-share-btn" href="/rss.xml" target="_blank" rel="noopener">RSS</a>
</div></div>
<div class="news-nav-row">{prev} {nxt}<a href="/news/" class="news-nav-btn news-nav-home">全部快讯</a></div></div>
<div class="news-cards">{cards_d}</div>
<div class="news-nav-row news-nav-bottom">{prev} {nxt}<a href="/news/" class="news-nav-btn news-nav-home">全部快讯</a></div>
</main>
{FOOTER}
{build.BACK_TO_TOP_BLOCK}
<div id="newsToast" class="news-toast">链接已复制，打开微信粘贴即可分享</div>
<script>{SHARE_JS}</script>
</body></html>'''

        dd = os.path.join(NEWS_DIR, d)
        os.makedirs(dd, exist_ok=True)
        with open(os.path.join(dd, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(daily_html)
        built_urls.append(f'{SITE}/news/{d}/')
        print(f'  [OK] news/{d}/index.html ({len(items)}条)')

    # ── /news/{cat}/ 栏目聚合页（独立URL + 长尾词，承接检索）──
    for cat in cats_present:
        cat_items = [(d, it) for d in dates for it in daily[d] if it.get('category') == cat]
        if not cat_items:
            continue
        cl = CAT_LABEL[cat]
        seo = CAT_SEO.get(cat, {})
        longtail = seo.get('longtail', cl)
        desc = seo.get('desc', f'AI工具宝箱每日聚合 {cl} 动态，持续更新。')
        cards_c = ''.join(_card(it, i == 0, date_ctx=d) for i, (d, it) in enumerate(cat_items))
        cat_html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{cl} - 每日更新 | AI行业动态汇总 - AI工具宝箱</title>
<meta name="description" content="{desc}">
<meta name="keywords" content="AI快讯,{cl},{longtail}">
<link rel="canonical" href="{SITE}/news/{cat}/"><style>{build.CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript><style>{SHARE_CSS}</style>
<!-- 百度统计（异步加载，不阻塞渲染） -->
{build.BAIDU_TONGJI}
</head>
<body data-page-type="news">
{HEADER}
<nav class="breadcrumb"><a href="/">首页</a> &raquo; <a href="/news/">AI快讯</a> &raquo; <span>{cl}</span></nav>
<main class="container">
<div class="news-header"><div class="news-header-top">
<div><h1 class="news-page-title">{cl}</h1><p class="news-page-date">{len(cat_items)}条 · 每日更新</p></div>
<div class="news-share"><label>分享：</label>
<button class="news-share-btn" onclick="copyLink()">微信</button>
<a class="news-share-btn" href="https://service.weibo.com/share/share.php?url={url_quote(SITE+'/news/'+cat+'/')}&title={url_quote(cl+' - AI快讯')}" target="_blank" rel="noopener">微博</a>
<a class="news-share-btn" href="/rss.xml" target="_blank" rel="noopener">RSS</a>
</div></div>
<div class="news-catnav">{catnav}</div></div>
<div class="news-cards">{cards_c}</div>
<div class="news-archive"><h3 class="news-archive-title">全部快讯</h3><div class="news-archive-links"><a href="/news/" class="news-date-link">返回汇总</a></div></div>
</main>
{FOOTER}
{build.BACK_TO_TOP_BLOCK}
<div id="newsToast" class="news-toast">链接已复制，打开微信粘贴即可分享</div>
<script>{SHARE_JS}</script>
</body></html>'''
        cd = os.path.join(NEWS_DIR, cat)
        os.makedirs(cd, exist_ok=True)
        with open(os.path.join(cd, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(cat_html)
        built_urls.append(f'{SITE}/news/{cat}/')
        print(f'  [OK] news/{cat}/index.html ({len(cat_items)}条)')

    print(f'[OK] 快讯页完成: {len(dates)}期, {sum(len(v) for v in daily.values())}条, {len(cats_present)}个栏目')
    return built_urls

def build_dict_page(term, all_terms, index):
    import build  # 延迟：build 完全加载后解析
    """生成单个词典术语的详情页"""
    slug = term['slug']
    term_name = term['term']
    en_name = term.get('en', '')
    emoji = term.get('emoji', '📖')
    category = term.get('category', '')
    tags = term.get('tags', [])
    detail = term.get('detail', term.get('brief', ''))
    brief = term.get('brief', '')

    # 转换detail中的markdown为HTML（简单处理：**加粗**、\n换行、代码块、列表）
    def md_to_html(text):
        # 先对纯文本部分做HTML转义
        text = escape_html(text)
        # 恢复被转义的markdown标记并转为HTML
        # 代码块
        text = re.sub(r'```(\w*)\n([\s\S]*?)```', r'<pre><code>\2</code></pre>', text)
        # 行内代码 (注意：转义后 ` 变为 &#96;)
        text = re.sub(r'&#96;([^&#96;]+)&#96;', r'<code>\1</code>', text)
        # 加粗
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # 标题
        lines = text.split('\n')
        result = []
        for line in lines:
            if line.startswith('### '):
                result.append(f'<h3>{line[4:]}</h3>')
            elif line.startswith('## '):
                result.append(f'<h2>{line[3:]}</h2>')
            elif line.startswith('- &lt;strong&gt;') or line.startswith('- <strong>'):
                # 带加粗的列表项，保持HTML
                content = line[2:]
                result.append(f'<li>{content}</li>')
            elif line.startswith('- '):
                result.append(f'<li>{line[2:]}</li>')
            elif line.strip() == '':
                result.append('')
            elif line.startswith('|'):
                result.append(line)
            else:
                result.append(line)
        text = '\n'.join(result)
        # 包裹<li>序列
        text = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul>\n\1</ul>', text)
        # 段落
        text = re.sub(r'\n\n+', '</p><p>', text)
        text = '<p>' + text + '</p>'
        # 清理空段落和不正确的嵌套
        text = re.sub(r'<p>\s*</p>', '', text)
        text = re.sub(r'<p>(\s*<h[23]>)', r'\1', text)
        text = re.sub(r'(</h[23]>)\s*</p>', r'\1', text)
        text = re.sub(r'<p>(\s*<ul>)', r'\1', text)
        text = re.sub(r'(</ul>)\s*</p>', r'\1', text)
        text = re.sub(r'<p>(\s*<pre>)', r'\1', text)
        text = re.sub(r'(</pre>)\s*</p>', r'\1', text)
        return text

    # 预加工：将 **章节标题**： 模式转为 ### 章节标题，让 md_to_html 生成 <h3>
    # 避免 md_to_html 中 <ul> 闭合导致后续 <strong> 失去 <p> 包裹的问题
    detail = re.sub(r'\n\n\*\*(.+?)\*\*：', r'\n\n### \1\n\n', detail)

    detail_html = md_to_html(detail)

    # 后处理：按 <h3> 切分，每段包裹为 section 卡片
    h3_parts = re.split(r'(<h3>[^<]+</h3>)', detail_html)
    if len(h3_parts) > 1:
        intro_html = h3_parts[0]
        sections_html = []
        for i in range(1, len(h3_parts), 2):
            h3_tag = h3_parts[i]
            content = h3_parts[i + 1] if i + 1 < len(h3_parts) else ''
            title_match = re.match(r'<h3>(.+)</h3>', h3_tag)
            if title_match:
                sections_html.append(f'<section class="dict-section"><h3>{title_match.group(1)}</h3>{content}</section>')
            else:
                sections_html.append(h3_tag + content)
        detail_html = intro_html + '\n'.join(sections_html)

    tags_html = ''.join([f'<span>{escape_html(t)}</span>' for t in tags])
    category_html = f'<span class="dict-detail-category">{escape_html(category)}</span>'

    # 侧边栏：快速参考 + 词条导航
    sb_prev = ''
    sb_next = ''
    if index > 0:
        pt = all_terms[index - 1]
        sb_prev = f'<a href="/dict/{pt["slug"]}/">{pt.get("emoji","📖")} {escape_html(pt["term"])}</a>'
    if index < len(all_terms) - 1:
        nt = all_terms[index + 1]
        sb_next = f'<a href="/dict/{nt["slug"]}/">{nt.get("emoji","📖")} {escape_html(nt["term"])}</a>'
    sidebar_html = f'''<aside class="dict-detail-sidebar">
        <div class="dict-quick-facts">
            <h4>快速参考</h4>
            <div class="dict-fact-item">
                <div class="dict-fact-label">英文名</div>
                <div class="dict-fact-value">{escape_html(en_name)}</div>
            </div>
            <div class="dict-fact-item">
                <div class="dict-fact-label">分类</div>
                <div class="dict-fact-value">{escape_html(category)}</div>
            </div>
            <div class="dict-fact-item">
                <div class="dict-fact-label">标签</div>
                <div class="dict-fact-value">{', '.join(escape_html(t) for t in tags)}</div>
            </div>
        </div>
        <div class="dict-side-nav">
            <h4>浏览词条</h4>
            <div class="dict-side-nav-links">
                {sb_prev}
                <a href="/dict/">📖 返回词典首页</a>
                {sb_next}
            </div>
        </div>
    </aside>'''

    # 相关词条（同分类的其他词条，最多6个）
    same_category = [t for t in all_terms if t.get('category') == category and t['slug'] != slug][:6]
    related_html = ''
    if same_category:
        related_cards = ''.join([
            f'<a class="dict-related-card" href="/dict/{t["slug"]}/"><span class="dict-related-emoji">{t.get("emoji","📖")}</span>{escape_html(t["term"])}</a>'
            for t in same_category
        ])
        related_html = f'''        <div class="dict-related">
            <h3>同分类词条</h3>
            <div class="dict-related-grid">
                {related_cards}
            </div>
        </div>'''

    # 底部导航
    prev_link = ''
    next_link = ''
    if index > 0:
        prev_term = all_terms[index - 1]
        prev_link = f'<a href="/dict/{prev_term["slug"]}/">← {escape_html(prev_term["term"])}</a>'
    if index < len(all_terms) - 1:
        next_term = all_terms[index + 1]
        next_link = f'<a href="/dict/{next_term["slug"]}/">{escape_html(next_term["term"])} →</a>'

    title = f'{term_name} - AI词典 - AI工具宝箱'
    description = brief[:150]
    # 2026-08-06：brief 过短时，从 detail（markdown）正文提取真实内容补足，消除 Bing 过短警告
    # 2026-08-13（阶段2.3）：阈值 90 → 115，覆盖 90~114 字的词条描述
    if len(description) < 115 and detail:
        _plain = re.sub(r'<[^>]+>', '', detail)
        _plain = re.sub(r'^#{1,6}[^\n]*$', '', _plain, flags=re.M)
        _plain = re.sub(r'[*_`>|#]', '', _plain)
        _plain = re.sub(r'\s+', '', _plain).strip('：:。.，,；;')
        if _plain and _plain not in description:
            _sep = '' if description.endswith(('。', '！', '？')) else '。'
            description = (description + _sep + _plain)[:160]
        elif _plain:
            description = _plain[:160]
    # 2026-08-13（阶段2.3）：仍不足 115 字时追加词条定位说明
    if len(description) < 115:
        description += '。本词条收录于AI工具宝箱AI词典，附英文对照与关联工具，供AI初学者快速查阅。'
    canonical = f'https://www.aitoollab.cn/dict/{slug}/'
    og_image = ensure_og_image(f'dict-{slug}', {'term': term_name, 'emoji': emoji, 'brief': brief, 'category': category or 'AI词典', 'en': en_name}, is_dict=True)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)}</title>
    <meta name="description" content="{escape_html(description)}">
    <meta name="keywords" content="{escape_html(term_name)},AI词典,AI术语,人工智能概念,{escape_html(en_name)}">
    <link rel="canonical" href="{canonical}">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(description)}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{canonical}">
    {f'<meta property="og:image" content="{og_image}">' if og_image else ''}
    <meta name="twitter:card" content="summary_large_image">
    <style>{build.CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript>
    <!-- BUILD_DYNAMIC_HEAD -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "DefinedTerm",
      "name": "{escape_html(term_name)}",
      "description": "{escape_html(brief)}",
      "inDefinedTermSet": {{
        "@type": "DefinedTermSet",
        "name": "AI工具宝箱 - AI词典"
      }}
    }}
    </script>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;">
                <div class="site-logo">🛠 AI工具宝箱 <span>每日更新 · 已收录 {build.TOOL_COUNT} 款工具</span></div>
            </a>
        </div>
        <nav class="global-nav" aria-label="全局导航">
            <div class="global-nav-inner">
                <a href="/ranking/" class="gn-item">📊 工具排行</a>
                <a href="/quiz/" class="gn-item">🎯 AI工具选择器</a>
                <a href="/live/" class="gn-item">📈 实时面板</a>
                <a href="/compare/" class="gn-item">⚖️ 对比评测</a>
                <a href="/alternatives/" class="gn-item">🔄 替代方案</a>
                <a href="/category/" class="gn-item">📂 全部分类</a>
            </div>
        </nav>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <div class="breadcrumb-inner">
            <a href="/">首页</a>
            <span class="sep">›</span>
            <a href="/dict/">AI词典</a>
            <span class="sep">›</span>
            <span>{escape_html(term_name)}</span>
        </div>
    </nav>

    <main class="dict-detail-page">
        <header class="dict-detail-header">
            <div class="dict-detail-icon">{emoji}</div>
            <h1>{escape_html(term_name)}</h1>
            <div class="dict-detail-en">{escape_html(en_name)}</div>
            {category_html}
            <div class="dict-detail-tags">{tags_html}</div>
        </header>
        <div class="dict-detail-layout">
            <div class="dict-detail-main">
                <article>
                    <div class="dict-detail-body">
                        {detail_html}
                    </div>
                </article>
            </div>
            {sidebar_html}
        </div>
        <nav class="dict-detail-nav">
            {prev_link}
            {next_link}
        </nav>
        {related_html}
    </main>

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

def _build_dict_index_page(terms):
    import build  # 延迟：build 完全加载后解析
    """生成AI词典总入口页 /dict/index.html"""
    # 按分类分组
    categories = {}
    for term in terms:
        cat = term.get('category', '其他')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(term)

    # 分类顺序
    cat_order = ['基础概念', '技术原理', '使用技巧', '基础设施', '前沿概念']
    ordered_cats = [c for c in cat_order if c in categories]
    for c in categories:
        if c not in ordered_cats:
            ordered_cats.append(c)

    sections_html = ''
    for cat in ordered_cats:
        cat_terms = categories[cat]
        cards = ''
        for term in cat_terms:
            cards += f'''                    <a class="dict-list-card" href="/dict/{term['slug']}/">
                        <div class="dict-list-icon">{term.get('emoji', '📖')}</div>
                        <div class="dict-list-body">
                            <h4>{escape_html(term['term'])}</h4>
                            <p>{escape_html(term.get('brief', ''))}</p>
                            <div class="dict-list-en">{escape_html(term.get('en', ''))}</div>
                        </div>
                    </a>
'''
        sections_html += f'''            <section class="dict-category-section">
                <h2 class="dict-category-title">{escape_html(cat)}</h2>
                <div class="dict-list-items">
{cards}                </div>
            </section>
'''

    title = 'AI词典 - AI术语大全 - AI工具宝箱'
    description = (f'AI工具宝箱AI词典：涵盖{len(terms)}个核心人工智能概念，从大语言模型、RAG、Agent、'
                   f'Transformer到微调、向量数据库、多模态，每个术语附通俗解释、英文对照与关联工具，'
                   f'并关联对应AI工具与常见问答，帮你零基础看懂AI技术名词，适合初学者、开发者和产品经理查阅。')
    canonical = 'https://www.aitoollab.cn/dict/'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)}</title>
    <meta name="description" content="{escape_html(description)}">
    <meta name="keywords" content="AI词典,人工智能术语,机器学习概念,深度学习术语,大模型术语,AI基础知识">
    <link rel="canonical" href="{canonical}">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(description)}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{canonical}">
    <style>{build.CRITICAL_CSS}</style>
<link rel="preload" href="/css/style.min.css?v={build.CSS_VERSION}" as="style" onload="this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/css/style.min.css?v={build.CSS_VERSION}"></noscript>
    <!-- BUILD_DYNAMIC_HEAD -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "DefinedTermSet",
      "name": "AI工具宝箱 - AI词典",
      "description": "{escape_html(description)}"
    }}
    </script>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <a href="/" style="text-decoration:none;">
                <div class="site-logo">🛠 AI工具宝箱 <span>每日更新 · 已收录 {build.TOOL_COUNT} 款工具</span></div>
            </a>
        </div>
        <nav class="global-nav" aria-label="全局导航">
            <div class="global-nav-inner">
                <a href="/ranking/" class="gn-item">📊 工具排行</a>
                <a href="/quiz/" class="gn-item">🎯 AI工具选择器</a>
                <a href="/live/" class="gn-item">📈 实时面板</a>
                <a href="/compare/" class="gn-item">⚖️ 对比评测</a>
                <a href="/alternatives/" class="gn-item">🔄 替代方案</a>
                <a href="/category/" class="gn-item">📂 全部分类</a>
            </div>
        </nav>
    </header>

    <nav class="breadcrumb" aria-label="面包屑导航">
        <div class="breadcrumb-inner">
            <a href="/">首页</a>
            <span class="sep">›</span>
            <span>AI词典</span>
        </div>
    </nav>

    <main class="dict-list-page">
        <header class="dict-list-header">
            <h1>📖 AI 词典</h1>
            <p>{len(terms)} 个核心AI概念，从入门到精通，一文读懂人工智能</p>
        </header>
{sections_html}    </main>

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
