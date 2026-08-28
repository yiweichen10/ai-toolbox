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
