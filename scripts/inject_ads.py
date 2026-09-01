#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inject_ads.py — 给静态站点所有页面注入广告 / CPS 推广加载器

干什么：
  1. 给每个 HTML 页面的 <body> 打上 data-page-type="..."（用于前端按页型加载广告）
  2. 工具页(tool)额外打上 data-category="..."（驱动 CPS 卡按品类匹配）
  3. 在 </body> 前注入 <script src="/ads/loader.js" defer></script>

设计原则：
  - 零侵入 build.py：本脚本在构建完成后单独运行（部署脚本里调用）
  - 幂等：重复运行不会产生重复注入
  - 只处理真实内容页，跳过开发/演示/诊断类页面

用法：
  python scripts/inject_ads.py            # 处理站点根目录
  python scripts/inject_ads.py /path/to  # 处理指定目录（测试用）

前置：站点根目录下需有 ads/loader.js 与 ads/config.json
"""
import os
import re
import sys
import json

# Windows 编码兜底（2026-08-13 补上，AGENTS.md 2026-08-09 铁律）：
# 本脚本直接运行（不经 deploy.sh）时，Windows 控制台默认 GBK，打印 ✅/中文会抛
# UnicodeEncodeError 中断注入——历史上导致"只注入了一个文件就退出"或根本没注入。
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_ROOT = sys.argv[1] if len(sys.argv) > 1 else BASE_DIR

# 2026-09-01 改为 /reco/ 前缀：原 /ads/ 命中 uBlock/AdGuard 默认规则，loader.js 被拦则
# 后续 cps.json / beacon 全部不发（实测配置加载率仅 40%，见 .workbuddy/memory/2026-09-01.md）。
# 物理文件仍在 ads/，由 nginx 的 location ^~ /reco/ 做 alias 映射。
# 同步改动点：scripts/check_ads_injected.py、ads/loader.js 内部 URL、nginx /reco/ 块。
LOADER_TAG = '<script src="/reco/loader.js" defer></script>'
BODY_RE = re.compile(r'<body(\s[^>]*)?>', re.IGNORECASE)

# 仅处理这些顶层目录（真实内容页）
ALLOWED_TOP = {
    'tools', 'articles', 'category', 'compare', 'alternatives',
    'ranking', 'quiz', 'live', 'dict', 'news',
}
# 根目录允许的独立页面
ALLOWED_ROOT = {
    'index.html', 'about.html', 'contact.html', 'privacy.html',
    'links.html', '404.html',
}

# 工具 slug -> category 映射（用于给工具页注入 data-category，驱动 CPS 卡按品类匹配）
_TOOLS_CAT = {}
# 文章 slug -> category 映射（用于给文章页注入 data-category，驱动 CPS 卡按文章分类匹配；2026-08-12 新增）
_ARTICLES_CAT = {}


def load_tools_category():
    global _TOOLS_CAT
    if _TOOLS_CAT:
        return
    try:
        # 2026-08-26 去单体化: 分片优先
        import sys as _sys
        _sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
        from data_store import load_all_tools
        for t in load_all_tools():
            s, c = t.get('slug'), t.get('category')
            if s and c:
                _TOOLS_CAT[s] = c
    except Exception:
        pass


def load_articles_category():
    global _ARTICLES_CAT
    if _ARTICLES_CAT:
        return
    try:
        # 2026-08-26 去单体化: 分片优先
        import sys as _sys
        _sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
        from data_store import load_all_articles
        for a in load_all_articles():
            s = a.get('slug')
            c = a.get('category') or a.get('content_type')
            if s and c:
                _ARTICLES_CAT[s] = c
    except Exception:
        pass


# 万维广告（wwads）静态广告配置
# 与 loader.js 的运行时动态注入不同，wwads 明确要求 div 必须写死在静态 HTML
#（不可由 JS 动态插入，否则广告无法填充），因此这部分代码在部署时直接烤入 HTML。
WWADS_CFG = None


def load_wwads_config():
    global WWADS_CFG
    if WWADS_CFG is not None:
        return WWADS_CFG
    try:
        p = os.path.join(SITE_ROOT, 'ads', 'wwads.json')
        if not os.path.isfile(p):
            p = os.path.join(BASE_DIR, 'ads', 'wwads.json')
        if os.path.isfile(p):
            WWADS_CFG = json.load(open(p, encoding='utf-8'))
        else:
            WWADS_CFG = {}
    except Exception:
        WWADS_CFG = {}
    return WWADS_CFG


# Google AdSense 站点验证 + 投放脚本（注入 <head>，供 AdSense 抓取所有权 & 后续投放）
ADSENSE_CFG = None
ADSENSE_MARKER = 'pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'


def load_adsense_config():
    global ADSENSE_CFG
    if ADSENSE_CFG is not None:
        return ADSENSE_CFG
    try:
        p = os.path.join(SITE_ROOT, 'ads', 'config.json')
        if not os.path.isfile(p):
            p = os.path.join(BASE_DIR, 'ads', 'config.json')
        if os.path.isfile(p):
            cfg = json.load(open(p, encoding='utf-8'))
            ADSENSE_CFG = cfg.get('adsense', {})
        else:
            ADSENSE_CFG = {}
    except Exception:
        ADSENSE_CFG = {}
    return ADSENSE_CFG


def inject_adsense(html):
    """把 AdSense 验证/投放脚本注入 <head>。幂等：已存在则跳过。
    脚本同时在审核期用于验证站点所有权，审核通过后继续用于投放广告。
    若 config.adsense.autoAds=true，则额外注入 Auto ads（页级自动广告）初始化脚本，
    由 Google 自动在所有最佳位置放置广告（需在 AdSense 后台限制格式避免侵入式）。

    2026-07-31 新增：当 config.adsense.enabled=false 时，主动移除页面中已注入的
    adsbygoogle.js 引用 —— adsbygoogle.js 在国内被墙，会触发 google.com/recaptcha
    iframe 超时 20s+ 拖垮全站加载。站点验证只需 meta 标签，无需此脚本。"""
    cfg = ADSENSE_CFG
    if not cfg or not cfg.get('enabled'):
        # 🔴 已禁用：清理历史注入的 adsbygoogle.js（保留站点验证 meta 标签不受影响）
        if ADSENSE_MARKER in html:
            # 匹配 <script async src="...adsbygoogle.js?..."></script>（含属性与换行变化）
            new_html = re.sub(
                r'\s*<script[^>]*src="https://pagead2\.googlesyndication\.com/'
                r'pagead/js/adsbygoogle\.js[^"]*"[^>]*></script>\s*',
                '\n', html, flags=re.IGNORECASE)
            return new_html, (new_html != html)
        return html, False
    pid = cfg.get('publisherId')
    if not pid:
        return html, False
    changed = False
    if ADSENSE_MARKER not in html:
        tag = ('<script async src="https://pagead2.googlesyndication.com/pagead/js/'
               'adsbygoogle.js?client=%s" crossorigin="anonymous"></script>' % pid)
        # 插入到 <head> 与第一个 <meta>/<title> 之间（保证尽早加载），找不到 <head> 则放最前
        m = re.search(r'<head[^>]*>', html, re.IGNORECASE)
        if m:
            html = html[:m.end()] + '\n  ' + tag + '\n' + html[m.end():]
        else:
            html = tag + '\n' + html
        changed = True
    # 注意：不再在代码里手动 push enable_page_level_ads。Auto ads 由 AdSense 后台开启，
    # 代码若再手动 push 会与后台自动注入冲突，触发 "Only one 'enable_page_level_ads'
    # allowed per page" 错误。此处只加载库脚本，后台控制自动广告投放即可。
    return html, changed


def inject_wwads(html, page_type):
    """把万维广告代码按 placements 烤进静态 HTML。wwads 要求 div 必须静态写死，
    不能由 loader.js 运行时注入。幂等：重复运行会清理旧位置再重新注入新位置。
    每个 placement 可带自己的 pageTypes；脚本只在本页有适用 placement 时才注入。"""
    cfg = WWADS_CFG

    changed = False
    # v2(2026-07-22)：wwads 关闭(enabled=false)时，彻底清理历史烤入的标记块与主/避让脚本，确保真正下线
    if '<!-- wwads-begin -->' in html:
        new_html = re.sub(r'<!-- wwads-begin -->.*?<!-- wwads-end -->', '', html, flags=re.DOTALL)
        if new_html != html:
            html = new_html
            changed = True
    for marker in ('cdn.wwads.cn/js/makemoney.js', '/ads/wwads-dodge.js'):
        if marker in html:
            new_html = re.sub(r'<script[^>]*' + re.escape(marker) + r'[^>]*>\s*</script>\s*', '', html)
            if new_html != html:
                html = new_html
                changed = True

    if not cfg or not cfg.get('enabled'):
        return html, changed

    global_page_types = cfg.get('pageTypes', [])
    script_url = cfg.get('script', 'https://cdn.wwads.cn/js/makemoney.js')
    data_id = str(cfg.get('dataId', '397'))
    script_marker = 'cdn.wwads.cn/js/makemoney.js'

    # 找出本页适用的 placements
    applicable = []
    for p in cfg.get('placements', []):
        pts = p.get('pageTypes', global_page_types)
        if page_type in pts:
            applicable.append(p)
    if not applicable:
        return html, False

    changed = False

    # 1) 主脚本：每页仅一个，放 </body> 前（footer 位置，符合 wwads 规范）
    if script_marker not in html:
        tag = '<script type="text/javascript" charset="UTF-8" src="%s" async></script>' % script_url
        html = html.replace('</body>', tag + '\n</body>', 1)
        changed = True

    # 1b) 悬浮广告避让脚本：把右下角按钮顶到 wwads 悬浮广告上方，避免遮挡。
    #     独立注入（不依赖主脚本是否已在），确保已部署过 makemoney.js 的页面也能补上；幂等。
    dodge_marker = '/ads/wwads-dodge.js'
    if dodge_marker not in html:
        dodge = '<script type="text/javascript" src="/ads/wwads-dodge.js" defer></script>'
        html = html.replace('</body>', dodge + '\n</body>', 1)
        changed = True

    # 2) 清理旧的 wwads 标记块（允许重新调整位置而不重复）
    if '<!-- wwads-begin -->' in html:
        new_html = re.sub(r'<!-- wwads-begin -->.*?<!-- wwads-end -->', '', html, flags=re.DOTALL)
        if new_html != html:
            html = new_html
            changed = True

    # 3) 按适用 placements 静态烤入广告 div
    for p in applicable:
        if 'html' in p:
            div = '<!-- wwads-begin -->\n' + p['html'] + '\n<!-- wwads-end -->'
        else:
            layout = p.get('layout', 'horizontal')
            maxw = int(p.get('maxWidth', 350))
            div = ('<!-- wwads-begin -->\n'
                   '<div class="wwads-cn wwads-%s" data-id="%s" '
                   'style="max-width:%dpx; margin:16px auto;"></div>\n'
                   '<!-- wwads-end -->' % (layout, data_id, maxw))
        targets = p.get('target', [])
        inserted = False
        for target in targets:
            if target in html:
                html = html.replace(target, target + '\n' + div, 1)
                inserted = True
                changed = True
                break
        if not inserted:
            # 兜底：若本页没有对应容器，则放到 </body> 前
            html = html.replace('</body>', div + '\n</body>', 1)
            changed = True

    return html, changed


def page_type_for(rel_path):
    """根据相对路径判断页面类型"""
    norm = rel_path.replace(os.sep, '/')
    parts = norm.split('/')
    if norm == 'index.html':
        return 'home'
    top = parts[0]
    if top in ('tools',):
        return 'tool'
    if top == 'articles':
        return 'article'
    if top == 'category':
        return 'category'
    if top == 'compare':
        return 'compare'
    if top == 'alternatives':
        return 'alternatives'
    if top == 'ranking':
        return 'ranking'
    if top == 'quiz':
        return 'quiz'
    if top == 'live':
        return 'live'
    if top == 'dict':
        return 'dict'
    if top == 'news':
        return 'news'
    base = parts[-1]
    if base in ALLOWED_ROOT:
        return 'misc'
    return None


def should_process(rel_path):
    norm = rel_path.replace(os.sep, '/')
    if not norm.endswith('.html'):
        return False, None
    parts = norm.split('/')
    if len(parts) == 1:
        return (parts[0] in ALLOWED_ROOT), (page_type_for(norm) if parts[0] in ALLOWED_ROOT else None)
    if parts[0] in ALLOWED_TOP:
        return True, page_type_for(norm)
    return False, None


def inject(html, page_type, rel=''):
    changed = False

    # 0) AdSense 库脚本（仅加载库，Auto ads 由后台控制；幂等：已存在则跳过）
    new_html, did_a = inject_adsense(html)
    if did_a:
        html = new_html
        changed = True

    # 1) data-page-type + (tool页) data-category
    m = BODY_RE.search(html)
    if m:
        attrs = m.group(1) or ''
        new_attrs = attrs
        if 'data-page-type' not in attrs:
            new_attrs = attrs + ' data-page-type="' + page_type + '"'
        if page_type == 'tool' and 'data-category' not in new_attrs:
            parts = rel.replace(os.sep, '/').split('/')
            slug = parts[1] if len(parts) > 1 else ''
            cat = _TOOLS_CAT.get(slug)
            if cat:
                new_attrs = new_attrs + ' data-category="' + cat + '"'
        if page_type == 'article' and 'data-category' not in new_attrs:
            parts = rel.replace(os.sep, '/').split('/')
            slug = parts[1] if len(parts) > 1 else ''
            cat = _ARTICLES_CAT.get(slug)
            if cat:
                new_attrs = new_attrs + ' data-category="' + cat + '"'
        if new_attrs != attrs:
            new_tag = '<body' + new_attrs + '>'
            html = html[:m.start()] + new_tag + html[m.end():]
            changed = True

    # 2) loader script
    # 旧标签清理（2026-09-01）：模板外来源（历史产物/备份恢复）可能残留 /ads/ 版，先删再注入
    if '<script src="/ads/loader.js" defer></script>' in html:
        html = html.replace('<script src="/ads/loader.js" defer></script>', '')
        changed = True
    if LOADER_TAG not in html:
        html = html.replace('</body>', LOADER_TAG + '\n</body>', 1)
        changed = True

    # 3) 万维广告（静态烤入，不走 loader.js）
    new_html, did_w = inject_wwads(html, page_type)
    if did_w:
        html = new_html
        changed = True

    return html, changed


def main():
    load_tools_category()
    load_articles_category()
    load_wwads_config()
    load_adsense_config()
    if not os.path.isdir(SITE_ROOT):
        print('[inject_ads] 目录不存在:', SITE_ROOT)
        sys.exit(1)

    # 清理历史原子写残留 .tmp（2026-08-19 原子写加固：进程崩溃最多留 .tmp 垃圾，
    # 下次运行自动清掉，避免堆积；只删 .tmp 后缀，不动正式文件）
    _tmp_cleaned = 0
    for _root, _dirs, _files in os.walk(SITE_ROOT):
        for _f in _files:
            if _f.endswith('.tmp'):
                try:
                    os.remove(os.path.join(_root, _f))
                    _tmp_cleaned += 1
                except OSError:
                    pass
    if _tmp_cleaned:
        print('[inject_ads] 清理 %d 个残留 .tmp 文件' % _tmp_cleaned)

    total = 0
    changed = 0
    skipped = 0

    for root, dirs, files in os.walk(SITE_ROOT):
        # 跳过非内容目录（避免扫描依赖/缓存/资源）
        rel_root = os.path.relpath(root, SITE_ROOT)
        top = rel_root.split(os.sep)[0] if rel_root != '.' else ''
        if top and top not in ALLOWED_TOP and top not in ('',):
            # 根目录下的子目录若不在白名单则跳过其递归
            if top not in ALLOWED_ROOT:
                dirs[:] = []
                continue
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), SITE_ROOT)
            ok, ptype = should_process(rel)
            if not ok:
                skipped += 1
                continue
            total += 1
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8') as fh:
                    html = fh.read()
            except Exception as e:
                print('  ⚠️ 读取失败 %s: %s' % (rel, e))
                continue
            # 空文件守卫（2026-08-19 事故：进程被系统终止时 open('w') 截断后未写入，
            # 留下 0 字节文件；若对空文件继续 inject，LOADER_TAG not in '' 恒真 → 误判需注入
            # → 写回仍是空文件却打印 ✅ 假成功。空/极小文件一律跳过并告警，禁止写回。）
            if not html or len(html) < 1024:
                print('  ⚠️ 跳过空/异常小文件 %s (%d B) — 疑似被截断，禁止注入覆盖' % (rel, len(html)))
                continue
            new_html, did = inject(html, ptype, rel)
            if did:
                # 2026-08-06: 偶发 Errno 22（文件短暂占用），加重试
                import time as _t2
                for _attempt in range(5):
                    try:
                        # 原子写（2026-08-19 加固）：先写临时文件再 os.replace 覆盖。
                        # 进程在任何时刻崩溃最多残留 .tmp 垃圾，绝不产生 0 字节正式文件。
                        _tmp = path + '.tmp'
                        with open(_tmp, 'w', encoding='utf-8') as fh:
                            fh.write(new_html)
                        os.replace(_tmp, path)
                        break
                    except OSError:
                        if _attempt == 4:
                            raise
                        _t2.sleep(0.4)
                changed += 1
                print('  ✅ %s  [%s]' % (rel, ptype))

    print('\n[inject_ads] 扫描 %d 个内容页，注入 %d 个，跳过 %d 个非内容页' % (total, changed, skipped))


if __name__ == '__main__':
    main()
