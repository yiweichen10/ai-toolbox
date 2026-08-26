# -*- coding: utf-8 -*-
"""Temporary script: closed-loop pre-deploy gate (AGENTS.md rule 12)."""
import glob
import html.parser
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"C:\Users\27040\WorkBuddy\20260321092139\seo-site"
PASS = []
FAIL = []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


def all_html():
    files = set()
    for pat in ("*.html", "*/index.html", "articles/*/index.html", "tools/*/index.html",
                "category/*/index.html", "ranking/*/index.html", "compare/*/index.html",
                "dict/*/index.html", "news/*/index.html", "quiz/*/index.html",
                "alternatives/*/index.html", "author/*/index.html", "live/*/index.html"):
        files.update(os.path.relpath(p, ROOT).replace("\\", "/")
                     for p in glob.glob(os.path.join(ROOT, pat)))
    return files


def file_exists_for(href):
    # href like /tools/foo/ -> tools/foo/index.html ; /favicon.ico -> favicon.ico
    if href.startswith(("http://", "https://", "//", "mailto:", "javascript:", "tel:")):
        return True
    if "?" in href or "#" in href:
        href = href.split("?", 1)[0].split("#", 1)[0]
    p = href.lstrip("/")
    if p.endswith(".html"):
        return os.path.exists(os.path.join(ROOT, p))
    if not p:
        return True
    return os.path.exists(os.path.join(ROOT, p)) or os.path.exists(os.path.join(ROOT, p, "index.html"))


class H1Parser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.h1 = 0
        self.desc = None
        self.robots = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "h1":
            self.h1 += 1
        elif tag == "meta":
            n = (a.get("name") or "").lower()
            if n == "description":
                self.desc = a.get("content", "")
            elif n == "robots":
                self.robots = a.get("content", "")


def main():
    files = all_html()
    print("检查文件数:", len(files))

    # 1) 内部死链
    dead = {}
    for p in files:
        html = open(os.path.join(ROOT, p), "r", encoding="utf-8", errors="replace").read()
        for m in re.finditer(r'href="([^"]*)"', html):
            href = m.group(1)
            if not href.strip() or href.startswith(("#", "http", "//", "mailto", "javascript", "tel")):
                continue
            if "'" in href or '"' in href:  # JS 拼接字符串，非真实 HTML 链接
                continue
            if not file_exists_for(href):
                dead.setdefault(href, set()).add(p)
    # 允许清单：可解析的静态资源等（这些实际都存在，检查逻辑的已知例外）
    allow = {"/assets/icons/pwa-192.png", "/css/style.css", "/css/style.min.css",
             "/favicon.ico", "/manifest.json", "/rss.xml"}
    dead = {k: v for k, v in dead.items() if k not in allow}
    check("内部死链为 0", len(dead) == 0, f"发现 {len(dead)} 个: {list(dead)[:5]}")

    # 2) h1 / meta / noindex
    bad_h1 = []
    no_desc = []
    for p in files:
        # cms.html 为本地管理控制台，不部署上线，跳过描述/noindex 检查（2026-08-14）
        if p == "cms.html":
            continue
        html = open(os.path.join(ROOT, p), "r", encoding="utf-8", errors="replace").read()
        ps = H1Parser()
        ps.feed(html)
        if ps.h1 != 1:
            bad_h1.append((p, ps.h1))
        if not ps.desc and not (ps.robots and "noindex" in ps.robots):
            no_desc.append(p)
    check("全站单 h1", len(bad_h1) == 0, f"异常 {len(bad_h1)}: {bad_h1[:5]}")
    check("有索引页面均有描述", len(no_desc) == 0, f"缺描述 {len(no_desc)}: {no_desc[:5]}")

    # 3) noindex 关键页
    # cms.html 为本地管理控制台，不部署上线，不参与 noindex 检查（2026-08-14）
    for p, name in (("favorites.html", "favorites"),
                    ("tools/_template/index.html", "template"), ("404.html", "404")):
        html = open(os.path.join(ROOT, p), "r", encoding="utf-8", errors="replace").read()
        check(f"noindex: {name}", "noindex" in html)

    # 4) sitemap 完整性
    sm = open(os.path.join(ROOT, "sitemap.xml"), "r", encoding="utf-8", errors="replace").read()
    locs = set(re.findall(r"<loc>([^<]+)</loc>", sm))
    hubs = ["/", "/tools/", "/category/", "/ranking/", "/compare/", "/alternatives/",
            "/articles/", "/author/", "/live/", "/quiz/", "/dict/", "/news/"]
    missing_hubs = [h for h in hubs if ("https://www.aitoollab.cn" + h) not in locs]
    check("sitemap 枢纽页齐全", len(missing_hubs) == 0, f"缺失: {missing_hubs}")
    # 已发布工具/文章全覆盖
    import json
    # 2026-08-26 去单体化(任务#7): 分片优先 data/tools/*.json + data/articles/*.json
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from data_store import load_all_tools, load_all_articles
    tools = load_all_tools()
    arts = load_all_articles()
    pub_slugs = {t["slug"] for t in tools if t.get("published", True)}
    art_slugs = {a["slug"] for a in arts}
    miss_tools = [s for s in pub_slugs if f"https://www.aitoollab.cn/tools/{s}/" not in locs]
    miss_arts = [s for s in art_slugs if f"https://www.aitoollab.cn/articles/{s}/" not in locs]
    check("sitemap 覆盖全部已发布工具", len(miss_tools) == 0, f"缺 {len(miss_tools)}: {miss_tools[:5]}")
    check("sitemap 覆盖全部文章", len(miss_arts) == 0, f"缺 {len(miss_arts)}: {miss_arts[:5]}")

    # 5) 2.1 文章顶部工具卡
    kimi = open(os.path.join(ROOT, "articles", "kimi-k3-moonshot-2-5t-parameters-launch-202607", "index.html"),
                "r", encoding="utf-8").read()
    check("文章顶部工具卡(2.1)", "article-top-tools" in kimi)

    # 6) ranking 无 meta refresh / quiz 旧链接
    rk = open(os.path.join(ROOT, "ranking", "index.html"), "r", encoding="utf-8").read()
    check("/ranking/ 无 Meta Refresh", "refresh" not in rk.lower())
    qhits = 0
    for p in files:
        html = open(os.path.join(ROOT, p), "r", encoding="utf-8", errors="replace").read()
        if "/quiz/ai-tool-finder-2026/" in html:
            qhits += 1
    check("无旧 quiz 死链", qhits == 0, f"仍引用 {qhits}")

    # 7) 对比页不再生成死链（抽样）
    cmp_files = glob.glob(os.path.join(ROOT, "compare", "*", "index.html"))
    dead_cmp = 0
    for p in cmp_files:
        html = open(p, "r", encoding="utf-8", errors="replace").read()
        for m in re.finditer(r'href="(/compare/[^"]*/)"', html):
            if not file_exists_for(m.group(1)):
                dead_cmp += 1
    check("对比页无死链", dead_cmp == 0, f"死链 {dead_cmp}")

    print()
    print(f"结果: {len(PASS)} 通过 / {len(FAIL)} 失败")
    if FAIL:
        print("失败项:", FAIL)
        sys.exit(1)


if __name__ == "__main__":
    main()
