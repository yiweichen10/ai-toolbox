# -*- coding: utf-8 -*-
"""全站后处理注入器（模块2，2026-08-24 从 build.py 抽离）。

包含：
  - _clean_all_broken_links
  - inject_site_logo / inject_favicon / inject_global_nav / inject_fav_fab
  - inject_footer_links / inject_pwa / inject_adsense_meta / inject_baidu_tongji
  - inject_rss_link / inject_hreflang
  - EXCLUSIVE_SECTIONS / build_section_hub / inject_section_hub

依赖 build.py 顶层常量（BASE_DIR/SITE_LOGO_MARK/GLOBAL_NAV 等）与
build_lib.html_utils.escape_html，均用延迟 import 避免循环依赖。
"""
import os
import re
import json

from build_lib.html_utils import escape_html


def _cfg():
    """延迟导入 build.py 顶层常量，避免模块级循环依赖。"""
    from build import (
        BASE_DIR, SITE_LOGO_MARK, GLOBAL_NAV, DARK_MODE_HTML,
        GLOBAL_SEARCH_HTML, GLOBAL_SEARCH_CSS, FOOTER_LINKS_HTML, BAIDU_TONGJI,
    )
    return dict(BASE_DIR=BASE_DIR, SITE_LOGO_MARK=SITE_LOGO_MARK, GLOBAL_NAV=GLOBAL_NAV,
                DARK_MODE_HTML=DARK_MODE_HTML, GLOBAL_SEARCH_HTML=GLOBAL_SEARCH_HTML,
                GLOBAL_SEARCH_CSS=GLOBAL_SEARCH_CSS, FOOTER_LINKS_HTML=FOOTER_LINKS_HTML,
                BAIDU_TONGJI=BAIDU_TONGJI)


def _write_if_changed(path, text):
    """内容相同就不写盘（2026-08-28）。

    注入器每次构建都会遍历全站 HTML，无条件重写会让上千个"其实没变"的文件 mtime 抖动，
    增量发布（deploy_fast.sh）就没法靠差异圈定要上传的文件，rsync 也要白扫一遍。
    返回 True 表示确实写了盘。"""
    try:
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as _f:
                if _f.read() == text:
                    return False
    except OSError:
        pass
    with open(path, 'w', encoding='utf-8') as _f:
        _f.write(text)
    return True


def _clean_all_broken_links():
    """全站兜底：所有 HTML 页面中指向未发布/不存在工具/文章的链接降级为纯文本（2026-08-07）。"""
    from build_lib.render_tool import clean_broken_tool_links
    fixed = 0
    BASE_DIR = _cfg()['BASE_DIR']
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in ('.git', 'assets', 'images', 'css', 'js', 'ads', 'news', 'backups')]
        for fn in files:
            if not fn.endswith('.html'):
                continue
            p = os.path.join(root, fn)
            try:
                with open(p, encoding='utf-8') as f:
                    html = f.read()
            except Exception:
                continue
            # 2026-08-13（Bing 4xx 修复）：/tools/{slug}/index.html 等非规范内链统一为目录形式
            html = re.sub(
                r'(href=")([^"#?]*?)/index\.html(")',
                lambda m: m.group(0) if m.group(2).startswith(('http://', 'https://', '//', 'mailto:', 'javascript:'))
                else m.group(1) + m.group(2) + '/' + m.group(3),
                html,
            )
            new = clean_broken_tool_links(html)
            if new != html:
                _write_if_changed(p, new)
                fixed += 1
    return fixed


def inject_site_logo():
    """后处理（2026-08-10）：全站头部标识统一为新品牌图形。"""
    SITE_LOGO_MARK = _cfg()['SITE_LOGO_MARK']
    BASE_DIR = _cfg()['BASE_DIR']
    pat_icon = re.compile(r'<div class="site-logo">[^<]*?AI工具宝箱')
    pat_svg = re.compile(r'<div class="site-logo"><svg class="site-logo-mark"[^>]*>.*?</svg>\s*AI工具宝箱', re.S)
    pat_h1 = re.compile(r'<a href="/" style="text-decoration:none;"><h1>[^<]*?AI工具宝箱')
    pat_h1_svg = re.compile(
        r'<a href="/" style="text-decoration:none;"><h1><svg class="site-logo-mark"[^>]*>.*?</svg>\s*AI工具宝箱',
        re.S,
    )
    pat_div_plain = re.compile(r'<a href="/" style="text-decoration:none;"><div>[^<]*?AI工具宝箱')
    replaced = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for fname in files:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                new = pat_svg.sub(
                    '<div class="site-logo">' + SITE_LOGO_MARK + ' AI工具宝箱', content
                )
                new = pat_icon.sub(
                    '<div class="site-logo">' + SITE_LOGO_MARK + ' AI工具宝箱', new
                )
                new = pat_h1_svg.sub(
                    '<a href="/" style="text-decoration:none;"><h1>' + SITE_LOGO_MARK + ' AI工具宝箱', new
                )
                new = pat_h1.sub(
                    '<a href="/" style="text-decoration:none;"><h1>' + SITE_LOGO_MARK + ' AI工具宝箱', new
                )
                new = pat_div_plain.sub(
                    '<a href="/" style="text-decoration:none;"><div>' + SITE_LOGO_MARK + ' AI工具宝箱', new
                )
                if new != content:
                    _write_if_changed(fpath, new)
                    replaced += 1
            except Exception:
                pass
    if replaced:
        print(f'[Post] 站点头部标识已统一更新 ({replaced} 个 HTML 文件)')
    return replaced


def inject_favicon():
    """后处理：为所有HTML文件注入favicon图标引用标签"""
    BASE_DIR = _cfg()['BASE_DIR']
    favicon_html = '    <link rel="icon" href="/favicon.ico">\n'
    old_patterns = [
        '    <link rel="icon" type="image/x-icon" href="/favicon.ico">\n'
        '    <link rel="icon" type="image/png" sizes="32x32" href="/aitoollab-icon-32.png">\n'
        '    <link rel="apple-touch-icon" href="/aitoollab-icon-256.png">\n'
        '    <meta name="theme-color" content="#14306B">\n',
    ]
    injected = 0
    cleaned = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for fname in files:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                changed = False
                for pat in old_patterns:
                    if pat in content:
                        content = content.replace(pat, '')
                        changed = True
                        cleaned += 1
                if 'favicon.ico' not in content and '</head>' in content:
                    content = content.replace('</head>', favicon_html + '</head>', 1)
                    changed = True
                    injected += 1
                if changed:
                    _write_if_changed(fpath, content)
            except Exception:
                pass
    if cleaned > 0:
        print(f'[Post] Cleaned old favicon tags from {cleaned} HTML files.')
    if injected > 0:
        print(f'[Post] Injected favicon links into {injected} HTML files.')
    return injected


def inject_global_nav():
    """后处理：注入全局导航栏 + 搜索条 + 暗色切换。"""
    BASE_DIR = _cfg()['BASE_DIR']
    GLOBAL_NAV = _cfg()['GLOBAL_NAV']
    DARK_MODE_HTML = _cfg()['DARK_MODE_HTML']
    GLOBAL_SEARCH_HTML = _cfg()['GLOBAL_SEARCH_HTML']
    GLOBAL_SEARCH_CSS = _cfg()['GLOBAL_SEARCH_CSS']
    nav_html = GLOBAL_NAV
    dark_html = DARK_MODE_HTML
    search_html = GLOBAL_SEARCH_HTML
    search_css = GLOBAL_SEARCH_CSS
    injected = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for fname in files:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                modified = False
                if '</header>' in content and 'class="global-nav"' not in content:
                    content = content.replace('</header>', nav_html + '\n    </header>', 1)
                    modified = True
                has_own_search = 'id="searchInput"' in content or 'class="error-search"' in content
                if '</header>' in content and not has_own_search and 'id="globalSearchBar"' not in content:
                    content = content.replace('</header>', '</header>\n' + search_html, 1)
                    modified = True
                if '</head>' in content and 'id="global-search-style"' not in content and 'id="globalSearchBar"' in content:
                    content = content.replace('</head>', search_css + '\n</head>', 1)
                    modified = True
                if '</body>' in content and 'id="darkModeToggle"' not in content:
                    content = content.replace('</body>', dark_html + '\n</body>', 1)
                    modified = True
                if modified:
                    _write_if_changed(fpath, content)
                    injected += 1
            except Exception:
                pass
    if injected > 0:
        print(f'[Post] Injected global nav + search bar + dark mode into {injected} HTML files.')
    return injected


def inject_fav_fab():
    """后处理：全站注入静态收藏悬浮按钮（#favFab）。"""
    BASE_DIR = _cfg()['BASE_DIR']
    fab_html = '    <a id="favFab" class="fav-fab" href="/favorites.html" title="我的收藏" aria-label="我的收藏">☆ <b>0</b></a>\n'
    injected = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for fname in files:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
            if 'id="favFab"' in content or 'id="favList"' in content:
                continue
            if '</body>' not in content:
                continue
            content = content.replace('</body>', fab_html + '</body>', 1)
            _write_if_changed(fpath, content)
            injected += 1
    if injected > 0:
        print(f'[Post] Injected static fav-fab into {injected} HTML files.')
    return injected


def inject_footer_links():
    """后处理（P0-5，2026-08-09）：为 footer 补上站内链接。"""
    BASE_DIR = _cfg()['BASE_DIR']
    FOOTER_LINKS_HTML = _cfg()['FOOTER_LINKS_HTML']
    injected = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for fname in files:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
            if 'footer-links' in content or '<footer class="footer' not in content:
                continue
            idx = content.find('<footer class="footer')
            p_end = content.find('</p>', idx)
            if p_end == -1:
                continue
            content = content[:p_end + 4] + '\n' + FOOTER_LINKS_HTML + content[p_end + 4:]
            try:
                _write_if_changed(fpath, content)
                injected += 1
            except Exception:
                continue
    if injected > 0:
        print(f'[Post] Injected footer links into {injected} HTML files.')
    return injected


def inject_pwa():
    """后处理（P1-5，2026-08-09）：全站注入 PWA manifest / theme-color / apple-touch-icon + SW 注册。"""
    BASE_DIR = _cfg()['BASE_DIR']
    tags = ('    <link rel="manifest" href="/manifest.json">\n'
            '    <meta name="theme-color" content="#00A64F">\n'
            '    <link rel="apple-touch-icon" href="/assets/icons/pwa-192.png">')
    sw_register = ('''    <script>
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function () {
            navigator.serviceWorker.register('/sw.js').catch(function () {});
        });
    }
    </script>''')
    injected = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for fname in files:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
            if '<head' in content and 'rel="manifest"' not in content:
                content = content.replace('</head>', '    ' + tags + '\n</head>', 1)
            if '</body>' in content and 'navigator.serviceWorker.register' not in content:
                content = content.replace('</body>', sw_register + '\n</body>', 1)
            try:
                _write_if_changed(fpath, content)
                injected += 1
            except Exception:
                continue
    if injected > 0:
        print(f'[Post] Injected PWA manifest into {injected} HTML files.')
    return injected


def inject_adsense_meta():
    """后处理：注入 AdSense 站点验证 meta 标签。"""
    BASE_DIR = _cfg()['BASE_DIR']
    import re as _re_am
    ADSENSE_META = '<meta name="google-adsense-account" content="ca-pub-5521852210294377">'
    _head_re = _re_am.compile(r'<head[^>]*>')
    injected = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for fname in files:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
            if 'google-adsense-account' in content or '<head' not in content:
                continue
            content = _head_re.sub(lambda m: m.group(0) + '\n    ' + ADSENSE_META, content, count=1)
            try:
                _write_if_changed(fpath, content)
                injected += 1
            except Exception:
                pass
    if injected > 0:
        print(f'[Post] Injected AdSense verify meta into {injected} HTML files.')
    return injected


def inject_baidu_tongji():
    """后处理（2026-08-14）：全站注入百度统计代码。"""
    BASE_DIR = _cfg()['BASE_DIR']
    BAIDU_TONGJI = _cfg()['BAIDU_TONGJI']
    _skip_dirs = ('.git', '.cleanup_backup', 'backups', 'ads', 'assets', 'images', 'css', 'js', 'news')
    injected = 0
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in _skip_dirs]
        for fname in files:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
            if 'hm.baidu.com' in content or '<head' not in content:
                continue
            if '</head>' not in content:
                continue
            content = content.replace('</head>', BAIDU_TONGJI + '\n</head>', 1)
            try:
                _write_if_changed(fpath, content)
                injected += 1
            except Exception:
                pass
    if injected > 0:
        print(f'[Post] Injected Baidu Tongji code into {injected} HTML files.')
    return injected


def inject_rss_link():
    """后处理：为全站 HTML 注入 RSS 声明（幂等）。"""
    BASE_DIR = _cfg()['BASE_DIR']
    RSS_LINK = '<link rel="alternate" type="application/rss+xml" title="AI工具宝箱 AI动态 RSS" href="/rss.xml">'
    injected = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for fname in files:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
            if '<head' not in content:
                continue
            if 'application/rss+xml' in content:
                # 已存在 RSS 声明 → 更新文案（非跳过），让标题更名自动生效、不留旧残留
                content = re.sub(r'<link[^>]*application/rss\+xml[^>]*>', RSS_LINK, content, count=1)
            else:
                content = re.sub(r'<head[^>]*>', lambda m: m.group(0) + '\n    ' + RSS_LINK, content, count=1)
            try:
                _write_if_changed(fpath, content)
                injected += 1
            except Exception:
                pass
    if injected > 0:
        print(f'[Post] Injected RSS link into {injected} HTML files.')
    return injected


def inject_hreflang():
    """后处理：为中文站页面注入 hreflang 标签指向英文站对应页面。"""
    BASE_DIR = _cfg()['BASE_DIR']
    import re as _re_hl
    en_tools_json = os.path.join(os.path.dirname(BASE_DIR), 'seo-site-en', 'data', 'tools_en.json')
    en_articles_json = os.path.join(os.path.dirname(BASE_DIR), 'seo-site-en', 'data', 'articles_en.json')
    en_tool_slugs = set()
    en_article_slugs = set()
    try:
        with open(en_tools_json, 'r', encoding='utf-8') as f:
            en_tool_slugs = set(t.get('slug', '') for t in json.load(f))
        with open(en_articles_json, 'r', encoding='utf-8') as f:
            en_article_slugs = set(a.get('slug', '') for a in json.load(f))
    except Exception:
        pass
    EN_DOMAIN = 'https://aitoolbox.hk'
    canonical_re = _re_hl.compile(r'(<link rel="canonical" href="[^"]+">)')
    en_path_re_tool = _re_hl.compile(r'^/tools/([^/]+)/$')
    en_path_re_article = _re_hl.compile(r'^/articles/([^/]+)/$')
    skip_prefixes = ('/compare/', '/alternatives/', '/quiz/', '/ranking/', '/live/')
    updated = skipped = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for fname in files:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
            if 'hreflang' in content:
                continue
            m = canonical_re.search(content)
            if not m:
                skipped += 1
                continue
            rel = '/' + os.path.relpath(fpath, BASE_DIR).replace('\\', '/')
            if fname == 'index.html':
                rel_path = rel[:-len('index.html')] if len(rel) > 1 else '/'
            else:
                rel_path = rel
            en_path = None
            mt = en_path_re_tool.match(rel_path)
            if mt:
                if mt.group(1) in en_tool_slugs:
                    en_path = rel_path
            else:
                ma = en_path_re_article.match(rel_path)
                if ma:
                    if ma.group(1) in en_article_slugs:
                        en_path = rel_path
                elif any(rel_path.startswith(p) for p in skip_prefixes):
                    en_path = None
                else:
                    en_path = rel_path
            if not en_path:
                skipped += 1
                continue
            en_url = f'{EN_DOMAIN}{en_path}'
            zh_url = f'https://www.aitoollab.cn{en_path}'
            hreflang_block = (
                f'\n    <link rel="alternate" hreflang="en" href="{en_url}">'
                f'\n    <link rel="alternate" hreflang="zh-CN" href="{zh_url}">'
                f'\n    <link rel="alternate" hreflang="x-default" href="{en_url}">'
            )
            new_content = content[:m.end()] + hreflang_block + content[m.end():]
            try:
                _write_if_changed(fpath, new_content)
                updated += 1
            except Exception:
                pass
    if updated > 0:
        print(f'[Post] Injected hreflang into {updated} HTML files ({skipped} skipped).')
    return updated


EXCLUSIVE_SECTIONS = [
    {'key': 'news',         'slug': 'news',         'name': 'AI动态',       'emoji': '📰', 'desc': '每日AI行业最新动态'},
    {'key': 'dict',         'slug': 'dict',         'name': 'AI词典',       'emoji': '📖', 'desc': 'AI专业术语白话解读'},
    {'key': 'live',         'slug': 'live',         'name': '实时面板',     'emoji': '📡', 'desc': 'AI工具实时热度数据'},
    {'key': 'ranking',      'slug': 'ranking',      'name': '工具排行',     'emoji': '📊', 'desc': '多维度的AI工具排名'},
    {'key': 'compare',      'slug': 'compare',      'name': '对比评测',     'emoji': '⚖️', 'desc': '主流AI工具横向对比'},
    {'key': 'alternatives', 'slug': 'alternatives', 'name': '替代方案',     'emoji': '🔄', 'desc': '寻找最佳平替工具'},
    {'key': 'quiz',         'slug': 'quiz',         'name': 'AI工具选择器', 'emoji': '🎯', 'desc': '测一测你该用哪款'},
]


def build_section_hub(current_key):
    """生成『独占板块』导航簇HTML（排除当前板块）。返回 '' 表示无兄弟板块。"""
    siblings = [s for s in EXCLUSIVE_SECTIONS if s['key'] != current_key]
    if not siblings:
        return ''
    cards = ''
    for s in siblings:
        cards += (
            f'<a href="/{s["slug"]}/" class="section-hub-card">'
            f'<span class="sh-emoji">{s["emoji"]}</span>'
            f'<span class="sh-body">'
            f'<span class="sh-name">{escape_html(s["name"])}</span>'
            f'<span class="sh-desc">{escape_html(s["desc"])}</span>'
            f'</span></a>\n'
        )
    return (
        f'<section class="section-hub" aria-label="相关AI工具板块">\n'
        f'  <h3>🔗 探索更多 AI 工具板块</h3>\n'
        f'  <p class="section-hub-sub">除了本板块，AI工具宝箱还有这些独家内容板块，帮你从不同角度发现好工具。</p>\n'
        f'  <div class="section-hub-grid">{cards}</div>\n'
        f'</section>'
    )


def inject_section_hub():
    """后处理：向独占板块页注入板块导航簇。"""
    BASE_DIR = _cfg()['BASE_DIR']
    section_keys = {s['key'] for s in EXCLUSIVE_SECTIONS}
    injected = skipped = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for fname in files:
            if not fname.endswith('.html'):
                continue
            rel = os.path.relpath(os.path.join(root, fname), BASE_DIR).replace('\\', '/')
            top = rel.split('/', 1)[0]
            if top not in section_keys:
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
            if 'class="section-hub"' in content:
                skipped += 1
                continue
            hub = build_section_hub(top)
            if not hub:
                skipped += 1
                continue
            if '</main>' in content:
                content = content.replace('</main>', hub + '\n</main>', 1)
            elif '</body>' in content:
                content = content.replace('</body>', hub + '\n</body>', 1)
            else:
                skipped += 1
                continue
            try:
                _write_if_changed(fpath, content)
                injected += 1
            except Exception:
                pass
    if injected > 0:
        print(f'[Post] Injected section-hub into {injected} exclusive-section pages ({skipped} skipped).')
    return injected


PROMO_BANNER_VERSION = 'tpb:v2'   # 片段版本戳：旧版页面被自动剥离并升级为新版（避免"注入后永不升级"）
# 「已是最新版」的判定标记：四件套必须全在，缺任何一件都视为需要重注入
# （2026-09-10 踩坑：只看 tpb:v2 戳会误判——HTML/CSS 已带戳但 body JS 未注入，
#   导致横幅拿到配置却无法绑定关闭按钮，且此后永远跳过注入）
PROMO_BANNER_MARKERS = (
    'class="top-promo-banner"',        # ① HTML 骨架
    'id="top-promo-banner-style"',     # ② 样式
    'tpbClosedAt',                     # ③ head 预隐藏脚本
    'var CONFIG_URLS',                 # ④ body 配置脚本
)

PROMO_BANNER_HTML = '''        <!-- 顶部推广横幅条 [tpb:v2]（PC端 header 内 logo 右侧，移动端独占一行；文案/链接由 /reco/tpb.json 驱动，后台改完秒级生效） -->
        <div class="top-promo-banner" id="topPromoBanner">
            <div class="tpb-inner">
                <a href="https://teamorouter.cn/?i=bf8975d059" target="_blank" rel="nofollow noopener" class="tpb-link">
                    <span class="tpb-icon">&#9889;</span>
                    <span class="tpb-text">一个免费白嫖 GLM 5.3 Flash 牛来 + Codex 的宝藏入口 &#8594;</span>
                </a>
                <button type="button" class="tpb-close" aria-label="关闭横幅">&#10005;</button>
            </div>
        </div>'''

# head 内同步脚本：body 渲染前用「关闭记忆」给 <html> 加 class 预隐藏（零闪烁）。
# 阈值用 24h 兜底（≥ 任何可配置冷却值），真实冷却小时数由 body 脚本 fetch 配置后精确判定，
# 未超时则移除该 class 恢复显示。这样无需重建站点即可调整冷却时间。
PROMO_BANNER_HEAD_JS = '''<script>try{var t=+localStorage.getItem('tpbClosedAt');if(t&&Date.now()-t<864e5)document.documentElement.classList.add('tpb-remembered-closed')}catch(e){}</script>'''

PROMO_BANNER_JS = '''<script>
/* tpb:v2 */
(function() {
  // 配置源（2026-09-10）：主路径 /reco/tpb.json —— /ads/ 前缀命中 uBlock/AdGuard 默认规则，
  // 实测线上仅约 30% 请求能到达（/ads/tpb-config.json 440 次 vs 首页 1507 次），
  // 于是"后台改了文案线上看不到"；/reco/ 映射同一物理文件、实测 97% 可达。
  var CONFIG_URLS = ['/reco/tpb.json', '/ads/tpb-config.json'];
  var DEFAULT_COOLDOWN_H = 6;   // 后台未配置时的兜底冷却（小时）

  function fetchCfg(i) {
    if (i >= CONFIG_URLS.length) return Promise.resolve(null);
    return fetch(CONFIG_URLS[i] + '?t=' + Date.now(), { cache: 'no-store' })
      .then(function(r) { return r.ok ? r.json() : null; })
      .catch(function() { return null; })
      .then(function(cfg) { return cfg || fetchCfg(i + 1); });
  }
  // 内容指纹：文案/链接/形态/冷却任一变化 => 视为新广告，忽略旧的关闭记忆
  function fingerprint(cfg) {
    return [cfg.text || '', cfg.url || '', cfg.style || '',
            cfg.cooldownHours == null ? '' : cfg.cooldownHours].join('|');
  }
  function readStore(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function writeStore(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  function initTPB() {
    var b = document.getElementById('topPromoBanner');
    if (!b) return;
    fetchCfg(0).then(function(raw) {
      var cfg = raw || {};
      var hours = (typeof cfg.cooldownHours === 'number' && cfg.cooldownHours >= 0)
        ? cfg.cooldownHours : DEFAULT_COOLDOWN_H;
      var key = fingerprint(cfg);
      var closedAt = +readStore('tpbClosedAt') || 0;
      var lastKey = readStore('tpbKey') || '';
      var remembered = closedAt > 0
        && (Date.now() - closedAt) < hours * 3600000
        && (!lastKey || lastKey === key);
      if (remembered) { b.style.display = 'none'; return; }
      // 记忆过期 / 广告内容已更换：解除 head 阶段预隐藏
      document.documentElement.classList.remove('tpb-remembered-closed');
      b.style.display = '';
      if (cfg.enabled === false) { b.style.display = 'none'; return; }
      if (cfg.style === 'full') b.classList.add('tpb-full');
      if (cfg.text) { var el = b.querySelector('.tpb-text'); if (el) el.textContent = cfg.text; }
      if (cfg.url) { var a = b.querySelector('.tpb-link'); if (a) a.href = cfg.url; }
      var btn = b.querySelector('.tpb-close');
      if (btn) btn.addEventListener('click', function() {
        b.classList.add('tpb-collapsed');
        writeStore('tpbClosedAt', String(Date.now()));
        writeStore('tpbKey', key);
        setTimeout(function() { b.style.display = 'none'; }, 340);
      });
    });
    // 滚动 80px 自动收起，回顶恢复
    var hidden = false;
    window.addEventListener('scroll', function() {
      var y = window.scrollY || window.pageYOffset || 0;
      if (y > 80 && !hidden) { hidden = true; b.classList.add('tpb-collapsed'); }
      else if (y <= 80 && hidden) { hidden = false; b.classList.remove('tpb-collapsed'); }
    }, { passive: true });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTPB);
  } else {
    initTPB();
  }
})();
</script>'''

PROMO_BANNER_CSS = '''<style id="top-promo-banner-style">
/* tpb:v2 */
/* 关闭记忆：渲染前即隐藏，零闪烁 */
.tpb-remembered-closed .top-promo-banner{display:none!important}
.top-promo-banner{padding:8px 12px 0;transition:transform .32s ease,opacity .32s ease;will-change:transform}
.top-promo-banner.tpb-collapsed{transform:translateY(-110%);opacity:0;pointer-events:none}
.tpb-inner{max-width:720px;margin:0 auto;display:flex;align-items:center;justify-content:center;gap:8px;border-radius:999px;padding:7px 10px 7px 16px;background:linear-gradient(135deg,rgba(0,133,58,.93),rgba(5,150,105,.90) 55%,rgba(16,185,129,.86));box-shadow:0 2px 12px rgba(0,83,44,.22);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px)}
/* 全屏通栏形态（tpb-config.json style="full" 时启用） */
.top-promo-banner.tpb-full{padding:0}
.top-promo-banner.tpb-full .tpb-inner{max-width:none;border-radius:0;margin:0;padding:8px 16px;box-shadow:none}
/* PC端：横幅挂在 header-inner 内 logo 右侧。
   刻意不重定义 .header-inner —— 旧版把它覆盖成 padding:12px 20px + max-width:1200px;margin:0 auto，
   宽屏（≥1440）下 header 内容被整体居中、与下方全宽导航错位，看起来像"logo 右移"
   （1920 视口实测 logo x=380 而导航 x=32，右移 348px，2026-09-10 修复）。 */
.header-inner .top-promo-banner{flex:0 1 auto;min-width:0;padding:0;margin-left:auto}
.header-inner .top-promo-banner .tpb-inner{max-width:720px;margin:0 0 0 auto}
.header-inner .site-logo{white-space:nowrap}
.tpb-link{display:flex;align-items:center;gap:8px;color:#fff;text-decoration:none;min-width:0}
.tpb-icon{font-size:15px;flex-shrink:0;transition:transform .15s ease}
.tpb-text{font-size:14px;font-weight:500;letter-spacing:.2px;transition:color .15s ease}
.tpb-link:hover .tpb-text{color:#fbbf24}
.tpb-link:hover .tpb-icon{transform:scale(1.12) rotate(8deg)}
.tpb-close{flex:none;width:22px;height:22px;border:none;border-radius:50%;background:rgba(255,255,255,.16);color:rgba(255,255,255,.9);font-size:13px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;transition:background .15s ease,color .15s ease}
.tpb-close:hover{background:rgba(255,255,255,.3);color:#fff}
[data-theme="dark"] .tpb-inner{background:linear-gradient(135deg,rgba(0,66,35,.95),rgba(4,108,64,.92) 55%,rgba(13,128,84,.90));box-shadow:0 2px 14px rgba(0,0,0,.35)}
/* 移动端（对齐站点 768px 断点）：横幅独占一行；同样不覆盖站点 .header-inner 的 padding/布局 */
@media (max-width:768px){.header-inner{flex-wrap:wrap;row-gap:6px}.header-inner .top-promo-banner{flex:1 1 100%;width:100%;margin-left:0;padding:0}.header-inner .top-promo-banner .tpb-inner{max-width:100%;margin:0}.top-promo-banner{padding:0}.tpb-inner{max-width:100%;padding:6px 8px 6px 12px;gap:6px}.tpb-text{font-size:12.5px}.tpb-icon{font-size:13px}.tpb-close{width:20px;height:20px;font-size:12px}}
@media (max-width:380px){.tpb-text{font-size:11.5px}}
</style>'''


def _scan_div_end(html, open_start):
    """从 `<div …>` 的 '<' 位置开始做标签配对扫描，返回其配对 </div> 之后的索引（找不到返回 -1）。

    为什么不用正则跨块匹配：早期版本横幅的注释文案/结构各不相同（有的没有关闭按钮、有的没有注释），
    用「注释 → button → 两层 div」这类跨块写正则会一路吃到页面里**别的** `</button>`
    （如移动端导航按钮），把 header 整段吞掉（2026-09-10 实测踩到）。配对扫描只看 div 层级，安全。"""
    import re as _re
    depth = 0
    for m in _re.finditer(r'<div\b[^>]*>|</div>', html[open_start:]):
        if m.group(0).startswith('</'):
            depth -= 1
            if depth == 0:
                return open_start + m.end()
        else:
            depth += 1
    return -1


def _strip_promo_banner(content):
    """剥离旧版横幅片段（HTML/CSS/head JS/body JS），供版本升级重注入。

    历史背景：注入器原先只做「页面已含 banner 就跳过」的幂等判断，
    导致早期注入的旧版片段**永远不会被升级**（2026-09-10 发现：index.html/about.html
    仍是 v1、部分页面甚至缺 banner）。现在改为「版本戳不匹配 → 剥离 + 重注入」。
    每一步都用「坐标 + 就近查找闭合标签」定位，绝不跨块贪婪匹配。"""
    import re as _re

    # 1) 横幅 HTML 块：按 class 定位（老版没有 id），配对扫描 div 层级；循环删除以防多个
    while True:
        m = _re.search(r'<div class="top-promo-banner"[^>]*>', content)
        if not m:
            break
        start = m.start()
        end = _scan_div_end(content, start)
        if end == -1:
            break
        # 顺带吃掉紧邻的注释行（如「<!-- 顶部推广横幅条 … -->」）
        pre = content.rfind('<!--', max(0, start - 400), start)
        if pre != -1 and content.find('-->', pre, start) != -1:
            line_start = content.rfind('\n', 0, pre) + 1
            if content[line_start:pre].strip() == '':
                start = line_start
        content = content[:start] + content[end:]
        content = _re.sub(r'\n{3,}', '\n\n', content, count=1)

    # 2) 样式块
    s = content.find('<style id="top-promo-banner-style">')
    if s != -1:
        e = content.find('</style>', s)
        if e != -1:
            e = content.find('>', e) + 1
            line_start = content.rfind('\n', 0, s) + 1
            content = content[:line_start] + content[e:]

    # 3) 脚本块：head 预隐藏脚本 / body 配置脚本（含旧版 initTPB）
    changed = True
    while changed:
        changed = False
        for marker in ('tpbClosedAt', 'topPromoBanner', 'initTPB'):
            idx = content.find(marker)
            if idx == -1:
                continue
            s = content.rfind('<script', 0, idx)
            if s == -1:
                continue
            if content.find('</script>', s, idx) != -1:
                continue          # marker 不在 script 内（例如残留在 onclick 属性里），不碰
            e = content.find('</script>', idx)
            if e == -1:
                continue
            e = content.find('>', e) + 1
            line_start = content.rfind('\n', 0, s) + 1
            content = content[:line_start] + content[e:]
            changed = True
    return content


def inject_promo_banner():
    """后处理：全站注入顶部推广横幅条（PC端插入 header-inner 内 logo 之后，横幅在右，移动端独占一行）。

    组成：HEAD_JS（关闭记忆同步预隐藏，修闪烁）+ CSS（pill/full 双形态 + 不覆盖站点 header 布局）
          + HTML（header-inner 内）+ JS（fetch /reco/tpb.json 配置驱动 + 冷却记忆 + 滚动收起）。
    配置源：ads/tpb-config.json（物理文件），线上经 nginx `location = /reco/tpb.json` 映射暴露；
            /ads/ 前缀会被 uBlock/AdGuard 默认规则拦掉约 70%，故不再作为主路径。
    幂等：页面片段含 PROMO_BANNER_VERSION 戳则跳过；含旧版片段则先剥离再重注入（可升级）。
    幂等标记：top-promo-banner / top-promo-banner-style / tpbClosedAt / tpb-remembered-closed。"""
    BASE_DIR = _cfg()['BASE_DIR']
    injected = 0
    upgraded = 0
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in ('.git', 'assets', 'images', 'css', 'js', 'ads', 'news', 'backups')]
        for fname in files:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
            has_banner = 'class="top-promo-banner"' in content
            if has_banner and all(mk in content for mk in PROMO_BANNER_MARKERS):
                continue          # 四件套齐全（幂等）
            if has_banner:
                content = _strip_promo_banner(content)   # 残缺/旧版：剥离后按新版重注入
                upgraded += 1
            # 插入 logo </a> 之后（logo在左、横幅在右），移动端独占一行
            if 'class="header-inner"' in content:
                import re as _re
                _m = _re.search(r'class="header-inner"', content)
                _close_a = content.find('</a>', _m.end()) if _m else -1
                if _close_a != -1:
                    _ins = _close_a + 4
                    content = content[:_ins] + '\n' + PROMO_BANNER_HTML + content[_ins:]
                    # head 内：同步关闭记忆检查脚本 + 样式（均幂等）
                    if '</head>' in content:
                        head_inject = ''
                        if 'tpb-remembered-closed' not in content:
                            head_inject += PROMO_BANNER_HEAD_JS + '\n'
                        if 'id="top-promo-banner-style"' not in content:
                            head_inject += PROMO_BANNER_CSS + '\n'
                        if head_inject:
                            content = content.replace('</head>', head_inject + '</head>', 1)
                    # body 末尾：配置驱动 + 滚动收起脚本（按 JS 专有特征串判重，不能用版本戳——
                    # HTML/CSS 片段已含版本戳，会把这条件永远判为 False，JS 永远注不进去）
                    if ('id="topPromoBanner"' in content
                            and 'var CONFIG_URLS' not in content
                            and '</body>' in content):
                        content = content.replace('</body>', PROMO_BANNER_JS + '\n</body>', 1)
                try:
                    _write_if_changed(fpath, content)
                    injected += 1
                except Exception:
                    pass
    if injected > 0:
        print(f'[Post] Injected promo banner into {injected} HTML files '
              f'({upgraded} upgraded from older version).')
    return injected
