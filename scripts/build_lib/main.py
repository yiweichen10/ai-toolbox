# main.py — 构建调度入口（模块11：收尾）
# 从 build.py 拆分（2026-08-24）。build.py 退化为薄壳：from build_lib.main import main; main()
import os
import sys
import subprocess
import argparse
import time
import json
from datetime import datetime

from build_lib.html_utils import (_collapse_blank_lines, _record_build_error, _emit)
from build_lib.injectors import (inject_global_nav, inject_site_logo, inject_footer_links, inject_pwa,
                          inject_favicon, inject_hreflang, inject_adsense_meta, inject_baidu_tongji,
                          inject_fav_fab, inject_rss_link, inject_section_hub, _clean_all_broken_links)
from build_lib.data_loaders import (load_tools, load_articles, get_published_tool_slugs, get_category_slug,
                          load_compare_data, load_quiz_data, load_ranking_data, load_live_data, load_news_archive)
from build_lib.render_tool import (make_tool_card_html, build_tool_page, ensure_og_image, get_category_stats)
from build_lib.render_article import (build_article_page, build_article_list_pages, build_article_category_pages, generate_rss)
from build_lib.render_category import (build_category_page, build_subcategory_page, _build_category_index_page, get_subcat_def)
from build_lib.render_compare import (build_compare_page, build_alternatives_page, build_quiz_page, _build_ranking_index_page, _build_compare_index_page, _build_alternatives_index_page)
from build_lib.render_live import (build_live_page,)
from build_lib.render_ranking import (build_ranking_page,)
from build_lib.render_news_dict import (build_news_page, build_dict_page, _build_dict_index_page)
from build_lib.data_loaders import (_load_dict_terms,)
from build_lib.render_index import (build_index_page, build_tools_index_page)
from build_lib.sitemap_push import (generate_sitemap, push_to_indexnow, push_to_baidu, _push_single_url)


def _post_process_all():
    """全站后处理注入链（2026-08-28 从 build_target 抽出，全量与增量共用同一份）。

    背景：增量构建 -s 的文章分支原先只调了 8 个注入器，漏了 inject_fav_fab /
    inject_rss_link / inject_section_hub 与全站坏链清理，导致"增量产物 != 全量产物"
    （新页缺板块导航簇、缺 RSS 声明、坏链未降级）。现在两条路径必须走同一个函数，
    改注入器只改这一处。"""
    # 后处理：注入全局导航栏到所有HTML文件
    inject_global_nav()
    # 后处理：全站头部标识统一为新品牌图形（宝箱 + AI 星光）
    inject_site_logo()
    # 后处理：为内页 footer 补上站内链接（P0-5）
    inject_footer_links()
    # 后处理：PWA manifest（P1-5）
    inject_pwa()
    # 后处理：注入静态收藏悬浮按钮（首屏可见，不再等 JS）
    inject_fav_fab()
    # 后处理：注入favicon图标引用
    inject_favicon()
    # 后处理：注入 hreflang 标签（中英文站互链）
    inject_hreflang()
    inject_adsense_meta()
    inject_baidu_tongji()
    # 后处理：全站注入 RSS 声明
    inject_rss_link()
    # 后处理：注入独占板块导航簇（#13 板块互链）
    inject_section_hub()

    # 后处理：全站坏链兜底（2026-08-13：移出"仅推送时执行"分支，任何构建都清理死链）
    _fixed = _clean_all_broken_links()
    if _fixed:
        print(f'[坏链清理] 已修复 {_fixed} 个页面中的坏链')


def _build_tool_incremental(tool, published_tools, articles, tools_by_category, no_push=False):
    import build  # 延迟：build 完全加载后解析
    """工具页 slug 增量：只重建该工具页 + 受影响聚合页（分类/子类目/全部工具/首页含搜索索引/排行）。

    2026-08-29 补齐三项（此前是半成品，从未被自动化使用过）：
      ① 子类目页 + category 总入口 —— 新工具落在子类目时计数会变，漏建会缺入口。
      ② 全站后处理注入 `_post_process_all()` —— 原实现明确"不调注入"，新页会缺
         全局导航/RSS/PWA/fav-fab/坏链清理，与 08-21「漏注入丢全站广告」是同型风险。
      ③ 全量 sitemap 重生成 —— 原实现只 `_push_single_url()` 推送单条 URL 而不写
         sitemap.xml，新工具缺席 sitemap → deploy 门禁「sitemap 覆盖全部已发布工具」会拦。
    收尾与文章 -s 分支保持同一套（注入 + 全量 sitemap），保证「增量产物 == 板块产物」。

    no_push: 2026-08-24 语义统一——--no-push 时跳过推送（原无条件 _push_single_url）。"""
    slug = tool['slug']
    print(f'\n[增量构建] 仅构建工具: {tool.get("name")} ({slug})')
    # 交叉链接所需辅助数据
    compare_data = load_compare_data()
    all_compares = compare_data.get('compares', [])
    all_alternatives = compare_data.get('alternatives', [])
    ranking_data = load_ranking_data()
    all_rankings = ranking_data.get('rankings', [])
    # 1. 该工具页
    _emit(os.path.join(build.BASE_DIR, 'tools', slug, 'index.html'),
          build_tool_page(tool, published_tools, articles, all_compares, all_alternatives, all_rankings))
    print(f'[OK] tools/{slug}/index.html')
    # 2. 该分类页
    cat = tool.get('category')
    if cat and cat in tools_by_category:
        cslug = get_category_slug(cat)
        _emit(os.path.join(build.BASE_DIR, 'category', cslug, 'index.html'),
              build_category_page(cat, tools_by_category[cat], all_categories=tools_by_category))
        print(f'[OK] category/{cslug}/index.html')

    # 2.5 子类目独立页 + category 总入口（2026-08-29 补齐：
    #     新工具若落在子类目，子类目页与总入口的计数/列表必须同步，否则缺入口）
    _subdef = get_subcat_def()
    _sub_slug = (tool.get('subcategory') or '').strip()
    if _subdef and _sub_slug:
        _flat_tools = [t for ts in tools_by_category.values() for t in ts]
        for _parent_slug, _pdata in _subdef.items():
            _subcats = _pdata.get('subcats') or {}
            if _sub_slug not in _subcats:
                continue
            _sub_tools = [t for t in _flat_tools if t.get('subcategory') == _sub_slug]
            if not _sub_tools:
                continue
            _parent_name = _pdata.get('name', _parent_slug)
            _sub_dir = os.path.join(build.BASE_DIR, 'category', _sub_slug)
            os.makedirs(_sub_dir, exist_ok=True)
            _parent_count = len([t for t in _flat_tools if t.get('category') == _parent_name])
            _html = build_subcategory_page(_parent_slug, _parent_name, _sub_slug,
                                           _subcats[_sub_slug], _sub_tools, parent_count=_parent_count)
            _emit(os.path.join(_sub_dir, 'index.html'), _html)
            print(f'[OK] category/{_sub_slug}/index.html (子类目, {len(_sub_tools)}款)')
    try:
        _emit(os.path.join(build.BASE_DIR, 'category', 'index.html'),
              _build_category_index_page(tools_by_category))
        print('  [OK] category/index.html (总入口页)')
    except Exception as e:
        print(f'  [FAIL] category/index.html: {e}')

    # 3. 全部工具大全页
    _emit(os.path.join(build.BASE_DIR, 'tools', 'index.html'), build_tools_index_page(published_tools))
    print(f'[OK] tools/index.html')
    # 4. 首页（同时重建搜索索引 js/tools-data.js）
    _emit(os.path.join(build.BASE_DIR, 'index.html'), build_index_page(published_tools, articles))
    print(f'[OK] index.html (含搜索索引)')
    # 5. 排行页（数量少，全量重建保证一致）
    for rd in all_rankings:
        rslug = rd.get('slug', 'unknown')
        _emit(os.path.join(build.BASE_DIR, 'ranking', rslug, 'index.html'),
              build_ranking_page(rd, published_tools, articles))
    try:
        _emit(os.path.join(build.BASE_DIR, 'ranking', 'index.html'), _build_ranking_index_page(all_rankings))
    except Exception as e:
        print(f'  [FAIL] ranking/index.html: {e}')
    print(f'[OK] ranking/* ({len(all_rankings)} 页)')
    # 6. 重建 news 页并收集 news_urls（2026-08-29）
    #    ⚠️ 必须在 _post_process_all() **之前**：build_news_page 是渲染动作，
    #    放在注入之后会把刚注入的 导航/RSS/PWA/板块导航簇 覆盖掉（实测 news 页与
    #    -t news 产物 50 处不一致）。与文章 -s 分支（先渲染 line 212、后注入 line 258）保持一致。
    news_urls = build_news_page(published_tools) or []

    # 7. 全站后处理注入（2026-08-29 补齐：与全量/文章增量共用同一份，
    #    否则新页缺 全局导航/站点标识/footer/PWA/fav-fab/favicon/hreflang/RSS/板块导航簇/坏链清理）
    _post_process_all()

    # 8. 全量 sitemap 重生成（2026-08-29 补齐：参数必须与全量分支逐一对应，
    #    原实现只推单条 URL 不写文件 → 新工具缺席 sitemap，会被 deploy 门禁拦下）
    quiz_data = load_quiz_data()
    all_quizzes = quiz_data.get('quizzes', [])
    live_data = load_live_data()
    all_lives = live_data.get('live_pages', [])
    dict_terms = [t for t in _load_dict_terms() if t.get('published', True)]
    sitemap = generate_sitemap(published_tools, articles,
                               [get_category_slug(cat) for cat in tools_by_category.keys()],
                               all_compares, all_alternatives, all_quizzes, all_rankings,
                               all_lives, dict_terms, news_urls=news_urls if news_urls else None)
    with open(os.path.join(build.BASE_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(sitemap)
    print(f'[OK] sitemap.xml ({len(published_tools)} tools + {len(articles)} articles + '
          f'{len(all_compares)} compares + {len(all_alternatives)} alternatives + '
          f'{len(all_quizzes)} quizzes + {len(all_rankings)} rankings + {len(all_lives)} live + '
          f'{len(dict_terms)} dict)')

    # 8. 推送新 URL（2026-08-24 语义：--no-push 时跳过）
    if not no_push:
        _push_single_url(f'https://www.aitoollab.cn/tools/{slug}/index.html')
    print(f'\n[完成] 增量构建: 1 工具页 + 分类页/子类目页 + 聚合页 + 全站注入 + 全量 sitemap')
    return True

def build_target(target, slug=None, no_push=False):
    import build  # 延迟：build 完全加载后解析
    """
    构建指定目标或全部页面。
    target: 'all' | 'articles' | 'tools' | 'live' | 'sitemap' | 'index' | 'pseo' | 'ranking'
    slug: 指定文章slug，仅构建该文章页+列表页+sitemap（增量构建模式）
    """
    # ═══════════════════════════════════════════════════════
    # 2026-08-26 去单体化(任务#7): 删除 build 前聚合兜底 sync_mono_from_shards。
    # 单体 tools.json/articles.json 已退役, 数据真源为分片 data/tools/*.json + data/articles/*.json,
    # 读取统一走 load_tools()/load_articles()(分片优先)。不再重建单体。
    # ═══════════════════════════════════════════════════════

    # 加载数据（目录优先，回退单体）
    all_tools = load_tools()
    # 填充 slug->name 映射，供标题引擎对比意图取竞品名
    build._SLUG_MAP.clear()
    build._SLUG_MAP.update({t['slug']: t for t in all_tools if t.get('slug')})
    articles = load_articles()
    # AI 应答前缀拦截（fail-fast）：脏内容绝不进线上
    build._check_content_preamble(all_tools, articles)
    # 按日期降序排列（最新文章在前），date格式兼容 "MM/DD" 和 "YYYY-MM-DD"
    def _article_date_key(a):
        d = a.get('date', '')
        try:
            if '-' in d and len(d) == 10:
                # YYYY-MM-DD 格式
                parts = d.split('-')
                return (int(parts[0]), int(parts[1]), int(parts[2]))
            elif '/' in d:
                # MM/DD 格式
                parts = d.split('/')
                return (2026, int(parts[0]), int(parts[1]))  # MM/DD格式默认2026年
            return (0, 0, 0)
        except:
            return (0, 0, 0)
    articles.sort(key=_article_date_key, reverse=True)
    # 新文章自动归类（2026-08-08）：缺失 content_type 时补齐并落盘，新增文章无需手工维护
    build.ensure_article_content_types(articles)
    # 生成全站快讯 RSS（/rss.xml）
    generate_rss(articles)

    # 过滤出已发布的工具
    published_tools = [tool for tool in all_tools if tool.get('published', False)]# === AI-NEWS-DATA-BEGIN ===
    # 快讯数据加载
    import glob as _gb_ns
    _ns_daily = {}
    for _fp in sorted(_gb_ns.glob(os.path.join(build.BASE_DIR, "data", "news_*.json")), reverse=True):
        try:
            _dstr = os.path.basename(_fp).replace("news_", "").replace(".json", "")
            _ns_daily[_dstr] = json.load(open(_fp, "r", encoding="utf-8"))
        except Exception:
            continue
# === AI-NEWS-DATA-END ===
    # 快讯数据加载
    import glob as _gb_ns
    _ns_daily = {}
    for _fp in sorted(_gb_ns.glob(os.path.join(build.BASE_DIR, "data", "news_*.json")), reverse=True):
        try:
            _dstr = os.path.basename(_fp).replace("news_", "").replace(".json", "")
            _ns_daily[_dstr] = json.load(open(_fp, "r", encoding="utf-8"))
        except Exception:
            continue

    print(f"检测到 {len(all_tools)} 个工具，其中 {len(published_tools)} 个已发布。")

    # ── 全站动态常量（P0：入口计算一次，全站各模板引用）──
    build.TOOL_COUNT = len(published_tools)
    build.CAT_COUNT  = len({t.get('category') for t in published_tools if t.get('category')})
    build.ART_COUNT  = len(articles)
    print(f"动态常量：build.TOOL_COUNT={build.TOOL_COUNT}, build.CAT_COUNT={build.CAT_COUNT}, build.ART_COUNT={build.ART_COUNT}, build.BUILD_YEAR={build.BUILD_YEAR}")

    # 按分类分组工具（增量构建也需要）
    tools_by_category = {}
    for tool in published_tools:
        category = tool.get('category')
        if category:
            if category not in tools_by_category:
                tools_by_category[category] = []
            tools_by_category[category].append(tool)

    # ═══════════════════════════════════════════════════════
    # 增量构建模式：只构建指定slug的文章
    # ═══════════════════════════════════════════════════════
    if slug:
        target_article = next((a for a in articles if a['slug'] == slug), None)
        if not target_article:
            # 工具页 slug 增量：改一个工具只重建它 + 受影响聚合页（用哪建哪）
            target_tool = next((t for t in published_tools if t['slug'] == slug), None)
            if target_tool:
                return _build_tool_incremental(target_tool, published_tools, articles, tools_by_category, no_push=no_push)
            print(f'[ERROR] 未找到文章或工具: {slug}')
            return False
        print(f'\n[增量构建] 仅构建文章: {target_article["title"]}')

        # 交叉链接所需辅助数据（2026-08-28 修复）：增量分支原先不加载 compare/quiz/ranking/live/news，
        # 直接 generate_sitemap 会少掉 130+ 条 URL（实测 1137 → 1000），把 sitemap 写残。
        _cmp = load_compare_data()
        all_compares = _cmp.get('compares', [])
        all_alternatives = _cmp.get('alternatives', [])
        all_quizzes = load_quiz_data().get('quizzes', [])
        all_rankings = load_ranking_data().get('rankings', [])
        all_lives = load_live_data().get('live_pages', [])
        news_urls = build_news_page(published_tools) or []

        def _emit_article(art):
            _d = os.path.join(build.BASE_DIR, 'articles', art['slug'])
            os.makedirs(_d, exist_ok=True)
            _emit(os.path.join(_d, 'index.html'), build_article_page(art, articles, published_tools))
            try:
                import re as _re
                _md = f"# {art.get('title', '')}\n\n" + art.get('content', '')
                _md = _re.sub(r'<[^>]+>', ' ', _md)
                with open(os.path.join(_d, f"{art['slug']}.md"), 'w', encoding='utf-8') as _f:
                    _f.write(_md)
            except Exception:
                pass
            print(f"[OK] articles/{art['slug']}/index.html")

        _emit_article(target_article)

        # 1) 上一篇/下一篇邻居：新文章插入日期序后，前后两页的分页链接必须重算（否则邻居"下一篇"仍指向旧页）
        _idx = next((i for i, _a in enumerate(articles) if _a['slug'] == slug), None)
        if _idx is not None:
            for _n in (_idx - 1, _idx + 1):
                if 0 <= _n < len(articles) and articles[_n]['slug'] != slug:
                    _emit_article(articles[_n])

        # 2) related_tools 指向的工具页：工具页会挂「相关文章」卡（render_tool.py related-card），
        #    不重建就会漏掉新文章的入口
        _tool_by_slug = {t['slug']: t for t in published_tools}
        for _tslug in (target_article.get('related_tools') or []):
            _t = _tool_by_slug.get(_tslug)
            if _t:
                _emit(os.path.join(build.BASE_DIR, 'tools', _tslug, 'index.html'),
                      build_tool_page(_t, published_tools, articles, all_compares, all_alternatives, all_rankings))
                print(f"[OK] tools/{_tslug}/index.html (相关文章)")

        # 3) 首页：「最近更新 / 资讯卡」引用文章列表，不重建首页就没有新文章入口
        _emit(os.path.join(build.BASE_DIR, 'index.html'), build_index_page(published_tools, articles))
        print('[OK] index.html (首页)')

        # 4) 文章分页列表页 + 内容分类页
        total_pages = build_article_list_pages(articles)
        print(f'[OK] 文章列表页已更新 ({total_pages} 页)')
        build_article_category_pages(articles)

        # 5) 全站后处理链：与全量构建共用 _post_process_all()（2026-08-28 修复：
        #    原增量分支漏了 inject_fav_fab / inject_rss_link / inject_section_hub / 坏链清理）
        _post_process_all()

        # 6) 全量 sitemap：参数必须与全量分支逐一对应
        dict_terms = [t for t in _load_dict_terms() if t.get('published', True)]
        sitemap = generate_sitemap(published_tools, articles, [get_category_slug(cat) for cat in tools_by_category.keys()],
                                    all_compares, all_alternatives, all_quizzes, all_rankings, all_lives, dict_terms,
                                    news_urls=news_urls if news_urls else None)
        with open(os.path.join(build.BASE_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
            f.write(sitemap)
        print(f'[OK] sitemap.xml ({len(published_tools)} tools + {len(articles)} articles + {len(all_compares)} compares + {len(all_quizzes)} quizzes + {len(all_rankings)} rankings + {len(dict_terms)} dict)')

        # 推送新URL到百度和IndexNow（2026-08-24：--no-push 时跳过）
        if not no_push:
            _push_single_url(f'https://www.aitoollab.cn/articles/{slug}/index.html')

        print(f'\n[完成] 增量构建: 1篇文章 + 邻居/工具页/首页/列表页 + 全量 sitemap')
        return True

    # 加载所有辅助数据（后续推送和sitemap需要）
    compare_data = load_compare_data()
    all_compares = compare_data.get('compares', [])
    all_alternatives = compare_data.get('alternatives', [])
    quiz_data = load_quiz_data()
    all_quizzes = quiz_data.get('quizzes', [])
    ranking_data = load_ranking_data()
    all_rankings = ranking_data.get('rankings', [])
    live_data = load_live_data()
    all_lives = live_data.get('live_pages', [])

    compare_count = 0
    alt_count = 0
    quiz_count = 0
    ranking_count = 0
    live_count = 0
    total_pages = 0

    # ═══════════════════════════════════════════════════════
    # 分类页（index 时生成，或 all 时生成）
    # ═══════════════════════════════════════════════════════
    if target in ('all', 'index', 'tools'):
        for category_name, tools_in_category in tools_by_category.items():
            try:
                category_slug = get_category_slug(category_name)
                dir_path = os.path.join(build.BASE_DIR, 'category', category_slug)
                os.makedirs(dir_path, exist_ok=True)
                html = build_category_page(category_name, tools_in_category, all_categories=tools_by_category)
                _emit(os.path.join(dir_path, 'index.html'), html)
                print(f'[OK] category/{category_slug}/index.html')
            except Exception as e:
                # fail-soft（2026-08-23）：单分类页渲染失败仅跳过+记录，不拖垮整次构建
                print(f'[FAIL] category/{category_name}/: {e}')
                _record_build_error('category', category_name, str(e))

        # 子类目独立页（扁平URL，独立SEO入口）；按 subcategory 字段过滤
        _subdef = get_subcat_def()
        if _subdef:
            _flat_tools = [t for ts in tools_by_category.values() for t in ts]
            for _parent_slug, _pdata in _subdef.items():
                _parent_name = _pdata.get('name', _parent_slug)
                for _sub_slug, _sdata in _pdata.get('subcats', {}).items():
                    _sub_tools = [t for t in _flat_tools if t.get('subcategory') == _sub_slug]
                    if not _sub_tools:
                        continue
                    _sub_dir = os.path.join(build.BASE_DIR, 'category', _sub_slug)
                    os.makedirs(_sub_dir, exist_ok=True)
                    _parent_count = len([t for t in _flat_tools if t.get('category') == _parent_name])
                    _html = build_subcategory_page(_parent_slug, _parent_name, _sub_slug, _sdata, _sub_tools, parent_count=_parent_count)
                    _emit(os.path.join(_sub_dir, 'index.html'), _html)
                    print(f'[OK] category/{_sub_slug}/index.html (子类目, {len(_sub_tools)}款)')

        # 生成 category/index.html 总入口页（列出所有分类）
        try:
            cat_index_html = _build_category_index_page(tools_by_category)
            _emit(os.path.join(build.BASE_DIR, 'category', 'index.html'), cat_index_html)
            print('  [OK] category/index.html (总入口页)')
        except Exception as e:
            print(f'  [FAIL] category/index.html: {e}')

        # 生成 tools/index.html 全部AI工具大全页（SEO+GEO 总入口）
        try:
            tools_index_html = build_tools_index_page(published_tools)
            _emit(os.path.join(build.BASE_DIR, 'tools', 'index.html'), tools_index_html)
            print(f'  [OK] tools/index.html (全部AI工具大全, {len(published_tools)}款)')
        except Exception as e:
            print(f'  [FAIL] tools/index.html: {e}')

    # ═══════════════════════════════════════════════════════
    # 工具页
    # ═══════════════════════════════════════════════════════
    if target in ('all', 'tools'):
        for tool in published_tools:
            slug = tool['slug']
            try:
                dir_path = os.path.join(build.BASE_DIR, 'tools', slug)
                os.makedirs(dir_path, exist_ok=True)
                html = build_tool_page(tool, published_tools, articles, all_compares, all_alternatives, all_rankings)
                _emit(os.path.join(dir_path, 'index.html'), html)
                print(f'[OK] tools/{slug}/index.html')
            except Exception as e:
                # fail-soft（2026-08-23）：单工具页渲染失败仅跳过+记录，不拖垮整次构建
                print(f'[FAIL] tools/{slug}/: {e}')
                _record_build_error('tool', slug, str(e))

    # ═══════════════════════════════════════════════════════
    # 文章页
    # ═══════════════════════════════════════════════════════
    if target in ('all', 'articles'):
        for article in articles:
            slug = article['slug']
            try:
                dir_path = os.path.join(build.BASE_DIR, 'articles', slug)
                os.makedirs(dir_path, exist_ok=True)
                html = build_article_page(article, articles, published_tools)
                _emit(os.path.join(dir_path, 'index.html'), html)
                print(f'[OK] articles/{slug}/index.html')
            except Exception as e:
                # fail-soft（2026-08-23）：单文章页渲染失败仅跳过+记录，不拖垮整次构建
                print(f'[FAIL] articles/{slug}/: {e}')
                _record_build_error('article', slug, str(e))

        # 文章分页列表页
        total_pages = build_article_list_pages(articles)
        build_article_category_pages(articles)

    # ═══════════════════════════════════════════════════════
    # Phase 2+3: 对比页和替代方案页（pSEO）
    # ═══════════════════════════════════════════════════════
    if target in ('all', 'pseo'):
        if all_compares:
            print(f'\n[Phase2] Generating compare pages ({len(all_compares)})...')
            for cp in all_compares:
                cslug = cp.get('slug', 'unknown')
                dir_path = os.path.join(build.BASE_DIR, 'compare', cslug)
                os.makedirs(dir_path, exist_ok=True)
                try:
                    html = build_compare_page(cp, published_tools, articles,
                                              existing_compare_slugs={c.get('slug') for c in all_compares})
                    _emit(os.path.join(dir_path, 'index.html'), html)
                    print(f'  [OK] compare/{cslug}/index.html')
                    compare_count += 1
                except Exception as e:
                    print(f'  [FAIL] compare/{cslug}/: {e}')

        if all_alternatives:
            print(f'\n[Phase3] Generating alternatives pages ({len(all_alternatives)})...')
            for alt in all_alternatives:
                aslug = alt.get('slug', 'unknown')
                dir_path = os.path.join(build.BASE_DIR, 'alternatives', aslug)
                os.makedirs(dir_path, exist_ok=True)
                try:
                    html = build_alternatives_page(alt, published_tools, articles)
                    _emit(os.path.join(dir_path, 'index.html'), html)
                    print(f'  [OK] alternatives/{aslug}/index.html')
                    alt_count += 1
                except Exception as e:
                    print(f'  [FAIL] alternatives/{aslug}/: {e}')

        # 生成 compare/index.html 总入口页
        try:
            compare_index_html = _build_compare_index_page(all_compares)
            _emit(os.path.join(build.BASE_DIR, 'compare', 'index.html'), compare_index_html)
            print('  [OK] compare/index.html (总入口页)')
        except Exception as e:
            print(f'  [FAIL] compare/index.html: {e}')

        # 生成 alternatives/index.html 总入口页
        try:
            alt_index_html = _build_alternatives_index_page(all_alternatives)
            _emit(os.path.join(build.BASE_DIR, 'alternatives', 'index.html'), alt_index_html)
            print('  [OK] alternatives/index.html (总入口页)')
        except Exception as e:
            print(f'  [FAIL] alternatives/index.html: {e}')

        # Quiz
        if all_quizzes:
            print(f'\n[Phase4] Generating quiz pages ({len(all_quizzes)})...')
            for qd in all_quizzes:
                qslug = qd.get('slug', 'unknown')
                is_main = qd.get('target_url') == '/quiz/' or qslug == 'ai-tool-finder-2026'
                if is_main:
                    dir_path = os.path.join(build.BASE_DIR, 'quiz')
                else:
                    dir_path = os.path.join(build.BASE_DIR, 'quiz', qslug)
                os.makedirs(dir_path, exist_ok=True)
                try:
                    html = build_quiz_page(qd, published_tools, articles)
                    _emit(os.path.join(dir_path, 'index.html'), html)
                    loc = f'quiz/' if is_main else f'quiz/{qslug}/'
                    print(f'  [OK] {loc}index.html')
                    quiz_count += 1
                except Exception as e:
                    loc = f'quiz/' if is_main else f'quiz/{qslug}/'
                    print(f'  [FAIL] {loc}: {e}')

    # ═══════════════════════════════════════════════════════
    # Phase 5: Ranking Pages（独立条件，支持 --target ranking）
    # ═══════════════════════════════════════════════════════
    if target in ('all', 'ranking', 'pseo'):
        if all_rankings:
            print(f'\n[Phase5] Generating ranking pages ({len(all_rankings)})...')
            for rd in all_rankings:
                rslug = rd.get('slug', 'unknown')
                # 所有ranking统一生成到 ranking/{slug}/ 子目录
                dir_path = os.path.join(build.BASE_DIR, 'ranking', rslug)
                os.makedirs(dir_path, exist_ok=True)
                try:
                    html = build_ranking_page(rd, published_tools, articles)
                    _emit(os.path.join(dir_path, 'index.html'), html)
                    loc = f'ranking/{rslug}/'
                    print(f'  [OK] {loc}index.html')
                    ranking_count += 1
                except Exception as e:
                    loc = f'ranking/{rslug}/'
                    print(f'  [FAIL] {loc}: {e}')

        # 生成 ranking/index.html 总入口页（跳转到综合榜 + 列出所有榜单）
        try:
            ranking_index_html = _build_ranking_index_page(all_rankings)
            _emit(os.path.join(build.BASE_DIR, 'ranking', 'index.html'), ranking_index_html)
            print('  [OK] ranking/index.html (总入口页)')
        except Exception as e:
            print(f'  [FAIL] ranking/index.html: {e}')

    # ═══════════════════════════════════════════════════════
    # Phase 5b: Live Dashboard
    # ═══════════════════════════════════════════════════════
    if target in ('all', 'live', 'pseo'):
        if all_lives:
            print(f'\n[Phase5b] Generating live dashboard pages ({len(all_lives)})...')
            dashboard_html = None
            for lp in all_lives:
                lslug = lp.get('slug', 'unknown')
                dir_path = os.path.join(build.BASE_DIR, 'live', lslug)
                os.makedirs(dir_path, exist_ok=True)
                try:
                    html = build_live_page(live_data, lp, published_tools, articles)
                    _emit(os.path.join(dir_path, 'index.html'), html)
                    if lslug == 'dashboard':
                        dashboard_html = html
                    print(f'  [OK] live/{lslug}/index.html')
                    live_count += 1
                except Exception as e:
                    print(f'  [FAIL] live/{lslug}/: {e}')

            if dashboard_html:
                _emit(os.path.join(build.BASE_DIR, 'live', 'index.html'), dashboard_html)
                print(f'  [OK] live/index.html (dashboard)')

    # ═══════════════════════════════════════════════════════
    # AI词典
    # ═══════════════════════════════════════════════════════

# === AI-NEWS-BUILD-BEGIN ===
    # ===== 快讯页 =====
    news_urls = []
    # 2026-08-29：改为「所有构建方式都重建快讯页」（原仅 all / news 分支）。
    #   ① 板块构建（-t tools / -t index 等）原先不重建 → news_urls 为空 → 产出的 sitemap
    #      缺整个快讯板块，实测 -t tools 只出 1101 条而全量 1148 条（差 47），
    #      即每天 08:30 的工具发布都会把线上 sitemap 写残，直到周日全量才恢复。
    #   ② 必须在**渲染阶段**（早于 _post_process_all）执行：build_news_page 是渲染动作，
    #      放在注入之后会把刚注入的 导航/RSS/PWA/板块导航簇 覆盖掉（实测 49 页产物不一致）。
    #   ③ -t none 语义是「只做后处理注入、不重建页面」，故排除。
    if target != 'none':
        news_urls = build_news_page(published_tools) or []
# === AI-NEWS-BUILD-END ===

    if target in ('all', 'dict'):
        dict_terms = [t for t in _load_dict_terms() if t.get('published', True)]
        if dict_terms:
            print(f'\n[Dict] Generating dict pages ({len(dict_terms)} published terms)...')
            # 词典总入口页
            dict_index_html = _build_dict_index_page(dict_terms)
            dir_path = os.path.join(build.BASE_DIR, 'dict')
            os.makedirs(dir_path, exist_ok=True)
            _emit(os.path.join(dir_path, 'index.html'), dict_index_html)
            print(f'  [OK] dict/index.html (总入口页)')

            # 各词条详情页
            for i, term in enumerate(dict_terms):
                slug = term['slug']
                term_dir = os.path.join(build.BASE_DIR, 'dict', slug)
                os.makedirs(term_dir, exist_ok=True)
                html = build_dict_page(term, dict_terms, i)
                _emit(os.path.join(term_dir, 'index.html'), html)
                print(f'  [OK] dict/{slug}/index.html')

    # ═══════════════════════════════════════════════════════
    # 静态首页
    # ═══════════════════════════════════════════════════════
    if target in ('all', 'index', 'tools'):
        index_html = build_index_page(published_tools, articles)
        _emit(os.path.join(build.BASE_DIR, 'index.html'), index_html)
        print(f'[OK] index.html (Static Pre-rendered)')

    _post_process_all()  # 2026-08-28：与增量构建共用同一份后处理链

    # ═══════════════════════════════════════════════════════
    # sitemap + 推送（每次都执行）
    # ═══════════════════════════════════════════════════════
    if target != 'none':  # 2026-08-13：--no-push 也生成 sitemap（本地验证不更新 sitemap 是坑），仅跳过推送
        dict_terms = [t for t in _load_dict_terms() if t.get('published', True)]
        sitemap = generate_sitemap(published_tools, articles, [get_category_slug(cat) for cat in tools_by_category.keys()],
                                    all_compares, all_alternatives,
                                    all_quizzes,
                                    all_rankings,
                                    all_lives,
                                    dict_terms,
                                    news_urls=news_urls if news_urls else None)
        with open(os.path.join(build.BASE_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
            f.write(sitemap)
        print(f'[OK] sitemap.xml ({len(published_tools)} tools + {len(articles)} articles + {len(tools_by_category)} categories + {total_pages} article pages + {compare_count} compares + {alt_count} alternatives + {quiz_count} quizzes + {ranking_count} rankings + {live_count} live + {len(dict_terms)} dict)')

        # 收集需要推送的链接
        push_cache_file = os.path.join(build.BASE_DIR, '.baidu_pushed.json')
        pushed_urls = set()
        if os.path.exists(push_cache_file):
            with open(push_cache_file, 'r', encoding='utf-8') as f:
                pushed_urls = set(json.load(f))
        
        all_urls = ["https://www.aitoollab.cn/", "https://www.aitoollab.cn/tools/"]# === AI-NEWS-URL-BEGIN ===
        # 快讯URL加入推送列表
        if news_urls:
            all_urls.extend(news_urls)
# === AI-NEWS-URL-END ===
        for tool in published_tools:
            all_urls.append(f"https://www.aitoollab.cn/tools/{tool['slug']}/")
        for article in articles:
            all_urls.append(f"https://www.aitoollab.cn/articles/{article['slug']}/")
        # 文章内容分类页（2026-08-08）
        for _cp in build.ARTICLE_CATEGORY_PAGES:
            all_urls.append(f"https://www.aitoollab.cn/articles/{_cp['slug']}/")
        for category_name in tools_by_category.keys():
            category_slug = get_category_slug(category_name)
            all_urls.append(f"https://www.aitoollab.cn/category/{category_slug}/")
        for cp in (all_compares or []):
            cslug = cp.get('slug', '')
            if cslug:
                all_urls.append(f"https://www.aitoollab.cn/compare/{cslug}/")
        for alt in (all_alternatives or []):
            aslug = alt.get('slug', '')
            if aslug:
                all_urls.append(f"https://www.aitoollab.cn/alternatives/{aslug}/")
        for qd in (all_quizzes or []):
            qslug = qd.get('slug', '')
            if qslug:
                is_main = (qd.get('target_url') == '/quiz/') or qslug == 'ai-tool-finder-2026'
                all_urls.append(f"https://www.aitoollab.cn/quiz{'' if is_main else '/' + qslug + '/'}")
        for rd in (all_rankings or []):
            rslug = rd.get('slug', '')
            if rslug:
                all_urls.append(f"https://www.aitoollab.cn/ranking/{rslug}/")
        for lp in (all_lives or []):
            lslug = lp.get('slug', '')
            if lslug:
                all_urls.append(f"https://www.aitoollab.cn/live/{lslug}/")

        # AI词典URL
        if dict_terms:
            all_urls.append("https://www.aitoollab.cn/dict/")
            for term in dict_terms:
                all_urls.append(f"https://www.aitoollab.cn/dict/{term['slug']}/")

        new_urls = [u for u in all_urls if u not in pushed_urls]
        
        if no_push:
            print(f"\n[--no-push] 跳过推送（sitemap 已更新，共 {len(all_urls)} 个 URL）")
        elif new_urls:
            print(f"\nPushing {len(new_urls)} new URLs to Baidu...")
            push_result = push_to_baidu(new_urls)
            if push_result:
                pushed_urls.update(new_urls)
                try:
                    with open(push_cache_file, 'w', encoding='utf-8') as f:
                        json.dump(list(pushed_urls), f)
                except OSError as e:
                    print(f'[WARN] 百度推送缓存写失败（幂等，可忽略）：{e}')
        else:
            print(f"\nNo new URLs to push. ({len(all_urls)} total, all already pushed)")

        # IndexNow 推送
        indexnow_cache_file = os.path.join(build.BASE_DIR, '.indexnow_pushed.json')
        indexnow_pushed = set()
        if os.path.exists(indexnow_cache_file):
            with open(indexnow_cache_file, 'r', encoding='utf-8') as f:
                indexnow_pushed = set(json.load(f))

        new_indexnow_urls = [u for u in all_urls if u not in indexnow_pushed]
        if no_push:
            pass
        elif new_indexnow_urls:
            print(f"\nPushing {len(new_indexnow_urls)} new URLs via IndexNow (Bing/Yandex)...")
            if push_to_indexnow(new_indexnow_urls):
                indexnow_pushed.update(new_indexnow_urls)
                try:
                    with open(indexnow_cache_file, 'w', encoding='utf-8') as f:
                        json.dump(list(indexnow_pushed), f)
                except OSError as e:
                    print(f'[WARN] IndexNow 缓存写失败（幂等，可忽略）：{e}')
        else:
            print(f"\nIndexNow: No new URLs to push. ({len(all_urls)} total, all already pushed)")
        
        print(f'\nDone! Target={target} | {len(published_tools)} tools + {len(articles)} articles + {quiz_count} quizzes + {ranking_count} rankings + {live_count} live')

def main():
    import build  # 延迟：build 完全加载后解析
    # Windows GBK 控制台兜底（2026-08-09 机制化修复）：Python 打印 emoji/中文
    # 不再抛 UnicodeEncodeError。历史反复踩坑，不要删除。
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    # 内部信息泄漏前置检查（2026-08-05：入库模板曾把"收录来源/ai-bot.cn（"写进对外字段，
    # 机制化拦截：构建前扫描 tools.json 对外字段，有违规即中止构建，防止内部溯源泄漏到线上）
    try:
        _leak_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'check_internal_leak.py')
        # 2026-08-09 修复：Windows 下子进程默认用 GBK 输出，父进程按 utf-8 解码会抛
        # UnicodeDecodeError（reader thread 崩溃），导致守卫误判/构建异常。
        _sub_env = os.environ.copy()
        _sub_env['PYTHONIOENCODING'] = 'utf-8'
        _leak_run = subprocess.run([sys.executable, _leak_script],
                                   capture_output=True, text=True, encoding='utf-8', env=_sub_env)
        # 2026-08-06 修复：区分「真实泄漏(exit 1)」与「检查器自身故障(exit 2 或崩溃)」。
        # 旧逻辑 returncode != 0 一律拦截，且只打印 stdout，导致守卫脚本 traceback(走 stderr)
        # 时拦截信息为空白、每日发布流水线被静默卡死且无法诊断。
        if _leak_run.returncode == 1:
            print('[build][拦截] 内部信息泄漏检查未通过，中止构建：')
            print(_leak_run.stdout or '')
            print(_leak_run.stderr or '')
            raise SystemExit(1)
        elif _leak_run.returncode != 0:
            print(f'[build][警告] 内部信息泄漏检查器自身异常(exit {_leak_run.returncode})，'
                  f'本次跳过检查继续构建，请尽快修复检查器：')
            print(_leak_run.stdout or '')
            print(_leak_run.stderr or '')
    except FileNotFoundError:
        pass  # 检查脚本缺失不阻塞构建
    # 构建前数据校验闸（G3，2026-08-23）：脏数据（缺必填/重复 slug/格式错误）在进渲染前拦下。
    # 与 check_internal_leak 同款子进程模式：ERROR 级（exit 1）中止构建，WARN 级不阻断。
    try:
        _val_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'validate_data.py')
        if os.path.isfile(_val_script):
            _val_env = os.environ.copy()
            _val_env['PYTHONIOENCODING'] = 'utf-8'
            _val_run = subprocess.run([sys.executable, _val_script],
                                      capture_output=True, text=True, encoding='utf-8', env=_val_env)
            for _line in (_val_run.stdout or '').strip().splitlines()[-6:]:
                print('[validate]', _line)
            if _val_run.returncode == 1:
                print('[build][拦截] 数据校验未通过，中止构建（请修复 data/*.json 后重试）')
                raise SystemExit(1)
    except FileNotFoundError:
        pass  # 校验脚本缺失不阻塞构建
    parser = argparse.ArgumentParser(description='AI工具宝箱 SSG 构建脚本')
    parser.add_argument('--target', '-t',
                        choices=['all', 'articles', 'tools', 'live', 'pseo', 'ranking', 'index', 'sitemap', 'dict', 'news', 'none'],
                        default='all',
                        help='构建目标（默认 all）：all=全量, articles=仅文章, tools=仅工具, live=仅Live面板, pseo=对比/替代/Quiz/排名/Live, ranking=仅排名, index=首页+分类, sitemap=仅推送, dict=仅AI词典, none=仅构建HTML不推送')
    parser.add_argument('--slug', '-s',
                        type=str, default=None,
                        help='增量构建：仅构建指定slug的文章页+列表页+sitemap')
    parser.add_argument('--no-push',
                        action='store_true',
                        help='只构建 HTML，不推送 sitemap/IndexNow/百度（本地验证用，等价 -t none 但会正常重建页面）')
    args = parser.parse_args()
    build_target(args.target, slug=args.slug, no_push=args.no_push)

    # 2026-08-13 机制化：构建完自动补跑广告/CPS 注入（幂等，重复跑无副作用）。
    # 背景：广告加载器不在模板里，是构建后由 scripts/inject_ads.py 单独注入的；
    # 多个自动化（版本监控/词典/快讯/发文章等）只调 build.py，重建后页面会丢失 loader，
    # 一旦直接上传就把"无广告页面"推上线（2026-08-13 线上事故根因）。
    # 现在 build.py 作为唯一出口，保证任何入口（手动/自动化/deploy）构建完都自动注入。
    try:
        _inj_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'inject_ads.py')
        if os.path.isfile(_inj_script):
            _inj_env = os.environ.copy()
            _inj_env['PYTHONIOENCODING'] = 'utf-8'
            _inj_env['PYTHONUTF8'] = '1'
            _inj_run = subprocess.run([sys.executable, _inj_script],
                                      capture_output=True, text=True, encoding='utf-8', env=_inj_env)
            for _line in (_inj_run.stdout or '').strip().splitlines()[-3:]:
                print('[ads]', _line)
            if _inj_run.returncode != 0:
                print('[ads][警告] inject_ads 自动注入异常(exit %d)：' % _inj_run.returncode)
                print((_inj_run.stderr or _inj_run.stdout or '')[-300:])
                # 2026-08-19 兜底：inject_ads 进程被系统终止（曾出现 0xC0000402）时，
                # 正在写入的文件可能被截断为 0 字节。崩溃后立即扫描内容页 0 字节文件，
                # 发现则明确报错并中止构建，防止 0 字节页面带病进入部署链路。
                _zero_files = []
                for _zroot, _zdirs, _zfiles in os.walk(build.BASE_DIR):
                    _ztop = os.path.relpath(_zroot, build.BASE_DIR).split(os.sep)[0] if _zroot != build.BASE_DIR else ''
                    if _ztop and _ztop not in ('tools', 'articles', 'category', 'compare', 'ranking', 'quiz', 'dict', 'news', 'live', 'alternatives'):
                        continue
                    for _zf in _zfiles:
                        if not _zf.endswith('.html'):
                            continue
                        _zp = os.path.join(_zroot, _zf)
                        try:
                            if os.path.getsize(_zp) == 0:
                                _zero_files.append(os.path.relpath(_zp, build.BASE_DIR))
                        except OSError:
                            pass
                if _zero_files:
                    print('[ads][中止] inject_ads 崩溃后检测到 %d 个 0 字节内容页，中止构建：' % len(_zero_files))
                    for _z in _zero_files[:20]:
                        print('  -', _z)
                    raise SystemExit(1)
    except FileNotFoundError:
        pass  # 注入脚本缺失不阻塞构建
