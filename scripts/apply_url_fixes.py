#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 _verify_batches/result_*.json 的核验结果，机械修正 data/tools.json 中
「URL错误且已给出明确正确官网」的工具 url 字段。

安全边界：
- 仅修正 url_ok == False 且 url_correct 是具体 http(s) 网址（非"待查"/空）的项。
- 仅对 published==True 的工具生效（本任务只核已发布工具）。
- 不改 content/price/platform（那些属于内容幻觉，需联网重写，另行分批处理）。
- 修正前必须先有 data/tools.json.<date>.bak 备份（本脚本不负责备份）。
"""
import os as _os  # 2026-08-28 单体退役拦截（AGENTS.md「数据架构：分片即真源，单体已退役」）
if not _os.path.exists(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                                       "data", "tools.json")):
    raise SystemExit("[已停用] 本脚本按已退役的单体 data/tools.json | data/articles.json 读写；"
                     "真源是分片 data/tools/*.json + data/articles/*.json，"
                     "改数据请走 scripts/data_store.py 的 load_all_*/save_* 后再用。")
# --- 单体退役拦截 end ---
import json, glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULT_DIR = os.path.join(ROOT, "scripts", "_verify_batches")
TOOLS_PATH = os.path.join(ROOT, "data", "tools.json")

URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)

def load_tools():
    with open(TOOLS_PATH, encoding="utf-8") as f:
        d = json.load(f)
    if isinstance(d, dict):
        return d, d.get("tools", [])
    return {"tools": d}, d

def main():
    data, tools = load_tools()
    by_slug = {t.get("slug"): t for t in tools if t.get("slug")}

    fixes = []          # (slug, name, old_url, new_url)
    skipped_no_url = 0  # url_ok False 但 url_correct 无可应用值
    skipped_pub = 0     # 未发布
    skipped_notfound = 0
    seen = set()

    for fp in sorted(glob.glob(os.path.join(RESULT_DIR, "result_b*.json"))):
        try:
            rb = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        for it in rb.get("tools", []):
            slug = it.get("slug")
            if not slug:
                continue
            if slug in seen:
                continue  # 同 slug 多批次出现时以首个为准（不重复改）
            seen.add(slug)
            if it.get("url_ok") is not False:
                continue
            new_url = (it.get("url_correct") or "").strip()
            if not URL_RE.match(new_url):
                skipped_no_url += 1
                continue
            t = by_slug.get(slug)
            if not t:
                skipped_notfound += 1
                continue
            if not t.get("published"):
                skipped_pub += 1
                continue
            old_url = t.get("url", "")
            if old_url.rstrip("/") == new_url.rstrip("/"):
                continue
            t["url"] = new_url
            fixes.append((slug, t.get("name", ""), old_url, new_url))

    # 写回
    with open(TOOLS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"应用 URL 修正: {len(fixes)} 个")
    print(f"跳过(无可用正确URL): {skipped_no_url} | 未发布: {skipped_pub} | 未找到slug: {skipped_notfound}")
    print("-" * 80)
    for slug, name, old, new in fixes:
        print(f"  [{slug}] {name}\n    {old}\n    -> {new}")
    print("-" * 80)
    print(f"已写回 {TOOLS_PATH}")

if __name__ == "__main__":
    main()
