#!/usr/bin/env python3
# scripts/fix_css_refs.py
# 全站兜底: 把所有"同步 stylesheet"引用 <link rel="stylesheet" href="/css/style.css?v=...">
# 升级为: 内联首屏关键CSS + 异步预加载压缩全量CSS(消除渲染阻塞).
# 已用 <link rel="preload" ...> 的页面(由 build.py 模板生成)不会被匹配, 保持不动.
# 同时: 把挂件 JS (/js/ai-assistant.js /js/ai-likes.js) 引用统一加上内容哈希版本号
#   —— nginx 对 /js/ 缓存 30 天 immutable, 不带版本号会导致 JS 更新后用户仍用旧文件。
# 用法: python scripts/fix_css_refs.py
import hashlib
import os, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRIT_PATH = os.path.join(BASE, "css", "style.critical.css")

crit = open(CRIT_PATH, encoding="utf-8").read().strip()

def _file_hash(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()[:10]
    except Exception:
        return "0"

# CSS_VERSION 直接取 style.min.css 内容哈希（与 build.py 的 _file_cache_version 一致，单一事实来源）。
# 历史坑(2026-08-20 修复)：曾用正则从 build.py 源码提取字符串字面量，但 build.py 中
# CSS_VERSION = _file_cache_version(...) 是函数调用形式，正则永远匹配失败 → 永远 fallback
# "20260720b"，导致 news 等页面版本号长期过期、浏览器命中旧缓存拿不到最新样式。
VER = _file_hash(os.path.join(BASE, "css", "style.min.css"))

WIDGET_JS_VERSION = _file_hash(os.path.join(BASE, "js", "ai-assistant.js"))
LIKES_JS_VERSION = _file_hash(os.path.join(BASE, "js", "ai-likes.js"))

REPL = (
    "<style>" + crit + "</style>\n"
    '<link rel="preload" href="/css/style.min.css?v=' + VER + '" as="style" onload="this.rel=\'stylesheet\'">\n'
    '<noscript><link rel="stylesheet" href="/css/style.min.css?v=' + VER + '"></noscript>'
)

# 匹配: <link rel="stylesheet" href="/css/style.css?v=..."> 或 style.min.css, 可选 media="..."
# 匹配: 任意含 href="/css/style.css"(非min) 的 <link> 标签(同步/preload/print 形式皆覆盖)
pat = re.compile(r'<link\b[^>]*href="/css/style\.css(?:\?v=[^"]*)?"[^>]*>')

cnt = 0
js_cnt = 0
css_cnt = 0
for root, _, files in os.walk(BASE):
    if ".git" in root or "node_modules" in root or os.sep + "css" + os.sep in root + os.sep:
        continue
    for fn in files:
        if not fn.endswith(".html"):
            continue
        p = os.path.join(root, fn)
        s = open(p, encoding="utf-8").read()
        s2 = s
        # 仅处理仍是"同步 stylesheet"且未用 min preload 的页面
        if pat.search(s):
            s2 = pat.sub(REPL, s)
            if s2 != s:
                cnt += 1
        # 挂件 JS 引用统一带内容哈希版本（幂等：已有 ?v= 的会刷新为新哈希）
        s3 = re.sub(
            r'(src="/js/ai-assistant\.js)(?:\?v=[^"]*)?(")',
            r'\1?v=' + WIDGET_JS_VERSION + r'\2',
            s2,
        )
        s3 = re.sub(
            r'(src="/js/ai-likes\.js)(?:\?v=[^"]*)?(")',
            r'\1?v=' + LIKES_JS_VERSION + r'\2',
            s3,
        )
        if s3 != s2:
            js_cnt += 1
        # 全量刷新 min.css 版本号（幂等）：任何 style.min.css?v=旧值 → 最新内容哈希。
        # （2026-08-20：news 页残留 20260720b、独立页残留 267c79b026 等过期版本号，
        #   浏览器命中旧缓存拿不到最新样式；统一刷为当前文件哈希，与 build.py 一致。）
        s4 = re.sub(
            r'href="/css/style\.min\.css(?:\?v=[^"]*)?"',
            r'href="/css/style.min.css?v=' + VER + '"',
            s3,
        )
        if s4 != s3:
            css_cnt += 1
        if s4 != s:
            open(p, "w", encoding="utf-8").write(s4)
print(f"fixed {cnt} files: upgraded synchronous <link> to inline-critical + async-preload")
print(f"refreshed style.min.css version hash in {css_cnt} files (stale ?v= → {VER})")
print(f"versioned widget JS in {js_cnt} files")
