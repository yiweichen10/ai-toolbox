# -*- coding: utf-8 -*-
"""
add_tool_guard.py — 新工具入库门禁（防虚构/假数据）
================================================
新工具写入 tools.json 前的强制联网校验：
1) 官方 URL 可达性检查（HTTP 可达、非停放页、非 404）
2) 通过 → 写入 tools.json，但标记 published=False + needs_verification=True，
   并同步 verify_state 为 unverified（进入联网核查队列，未核查不上线）
3) 失败 → 拒绝入库，输出原因

用法:
  python scripts/add_tool_guard.py --name "OpenHands" --slug openhands --url https://github.com/All-Hands-AI/OpenHands
  python scripts/add_tool_guard.py --name X --slug x --url https://x.com --category AI编程 --desc "一句话描述"
  python scripts/add_tool_guard.py --check-url https://xxx.com     # 仅校验 URL

也可 import 复用: from add_tool_guard import validate_new_tool, check_url
"""
import json, os, sys, re, argparse, datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'scripts'))
from data_store import save_tools_batch, save_articles_batch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_JSON = os.path.join(BASE_DIR, "data", "tools.json")
STATE_JSON = os.path.join(BASE_DIR, "data", "verify_state.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# 停放页/失效页特征（命中即判定不可信）
PARKED_MARKERS = [
    "a brand new domain", "this domain is for sale", "domain is parked",
    "parked free", "buy this domain", "sedo.com", "dan.com", "afternic",
    "domain name for sale", "this domain name has been registered",
    "coming soon", "under construction", "404 not found", "page not found",
    "deployment_not_found", "domain may be for sale",
]

def check_url(url, timeout=15):
    """校验官方 URL：返回 (ok, reason, status, sample)。"""
    if not url or not url.startswith(("http://", "https://")):
        return False, "URL 格式不合法", None, ""
    try:
        parsed = urlparse(url)
        if not parsed.netloc or "." not in parsed.netloc:
            return False, "域名不合法", None, ""
    except Exception:
        return False, "URL 解析失败", None, ""

    req = Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    try:
        with urlopen(req, timeout=timeout) as r:
            status = r.status
            raw = r.read(60000).decode("utf-8", errors="ignore").lower()
    except HTTPError as e:
        return False, f"HTTP {e.code}", e.code, ""
    except URLError as e:
        return False, f"网络错误: {e.reason}", None, ""
    except Exception as e:
        return False, f"异常: {e}", None, ""

    if status >= 400:
        return False, f"HTTP {status}", status, ""

    for m in PARKED_MARKERS:
        if m in raw:
            return False, f"疑似停放/失效页（命中特征: {m}）", status, m
    return True, "OK", status, ""

def validate_new_tool(name, slug, url):
    """完整门禁：返回 (ok, message)。"""
    # 1) 基本字段
    if not name or not slug or not url:
        return False, "name/slug/url 均为必填"
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,60}", slug):
        return False, f"slug 不合法（仅小写字母/数字/连字符）: {slug}"

    # 2) 查重
    tools = load_all_tools()
    slugs = {t["slug"] for t in tools}
    names = {t.get("name", "").lower() for t in tools}
    if slug in slugs:
        return False, f"slug 已存在: {slug}（勿重复入库）"
    if name.lower() in names:
        return False, f"同名工具已存在: {name}（勿重复入库）"

    # 3) URL 联网校验
    ok, reason, status, sample = check_url(url)
    if not ok:
        return False, f"URL 校验未通过: {url} -> {reason}"
    return True, f"URL 校验通过（HTTP {status}）"

def add_tool(entry, desc=None, category=None):
    """通过门禁后写入 tools.json + verify_state（标记 unverified）。"""
    tools = load_all_tools()
    state = json.load(open(STATE_JSON, encoding="utf-8"))

    slug = entry["slug"]
    base = {
        "name": entry["name"], "slug": slug,
        "emoji": entry.get("emoji", "🤖"), "color": entry.get("color", "#4A90D9"),
        "description": desc or entry.get("description", ""),
        "category": category or entry.get("category", "AI效率"),
        "tags": entry.get("tags", []),
        "rating": entry.get("rating", "⭐ 4.0"), "visits": "N/A", "badge": None,
        "url": entry["url"], "price": entry.get("price", "暂未公开"),
        "platform": entry.get("platform", "Web"),
        "pros": entry.get("pros", []), "cons": entry.get("cons", []),
        "features": entry.get("features", []), "related": entry.get("related", []),
        "faq": entry.get("faq", []), "seo_keywords": entry.get("seo_keywords", []),
        "content": entry.get("content", ""),
        # 门禁标记：未核查不上线
        "published": False,
        "needs_verification": True,
    }
    tools.append(base)
    save_tools_batch(tools)

    st = state.setdefault("tools", {})
    st[slug] = {"name": entry["name"], "status": "unverified", "category": base["category"],
                "priority": 10, "attempts": 0, "last_attempt": None, "verified_at": None,
                "confidence": None, "notes": "新工具入库，待联网核查（add_tool_guard 门禁通过）"}
    state["_meta"]["updated"] = datetime.date.today().isoformat()
    state["_meta"]["total"] = len(tools)
    json.dump(state, open(STATE_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return slug

def main():
    ap = argparse.ArgumentParser(description="新工具入库门禁")
    ap.add_argument("--name"); ap.add_argument("--slug"); ap.add_argument("--url")
    ap.add_argument("--category", default="AI效率"); ap.add_argument("--desc", default="")
    ap.add_argument("--check-url", dest="check_url_only", default=None)
    args = ap.parse_args()

    if args.check_url_only:
        ok, reason, status, sample = check_url(args.check_url_only)
        print(f"[{'通过' if ok else '拒绝'}] {args.check_url_only} -> {reason}")
        sys.exit(0 if ok else 1)

    if not (args.name and args.slug and args.url):
        print("用法: add_tool_guard.py --name X --slug x --url https://x.com [--category 分类] [--desc 描述]")
        sys.exit(2)

    ok, msg = validate_new_tool(args.name, args.slug, args.url)
    print(f"[{'通过' if ok else '拒绝'}] {msg}")
    if not ok:
        sys.exit(1)

    slug = add_tool({"name": args.name, "slug": args.slug, "url": args.url},
                    desc=args.desc, category=args.category)
    print(f"已入库（未发布，待核查）: {slug} -> tools.json + verify_state(unverified)")

if __name__ == "__main__":
    main()
