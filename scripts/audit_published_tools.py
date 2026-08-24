#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线审计：拉出全部已发布工具，扫描结构性/可疑问题，输出 CSV + 摘要。
不联网。仅做可离线判断的风险标记，供在线核实时优先处理。
"""
import json, re, csv, hashlib
from collections import Counter, defaultdict

SRC = "data/tools.json"
OUT_CSV = "audit_published.csv"

def load():
    d = json.load(open(SRC, encoding="utf-8"))
    tools = d if isinstance(d, list) else d.get("tools", [])
    return [t for t in tools if t.get("published")]

def norm_content(s):
    return re.sub(r"\s+", "", s or "")

def main_label(url):
    m = re.match(r"https?://([^/]+)/?", url or "")
    if not m:
        return ""
    host = m.group(1).lower()
    if host.startswith("www."):
        host = host[4:]
    return host.split(".")[0]

def is_guessed_url(t):
    """启发式：url 主标签 == slug 或 == 去掉空格的 name，且 tld 常见 -> 疑似编造官网"""
    url = t.get("url", "")
    if not url:
        return False
    ml = main_label(url)
    if not ml:
        return False
    slug = (t.get("slug") or "").lower()
    name_token = re.sub(r"[^a-z0-9]", "", (t.get("name") or "").lower())
    tld = re.search(r"\.([a-z]{2,6})$", url.lower())
    common_tld = tld and tld.group(1) in ("com", "cn", "net", "io", "ai", "org")
    if not common_tld:
        return False
    if slug and ml == slug and len(slug) > 3:
        return True
    if name_token and ml == name_token and len(name_token) > 3:
        return True
    return False

def audit():
    pub = load()
    rows = []
    flags_counter = Counter()
    dup_groups = defaultdict(list)
    for t in pub:
        slug = t.get("slug", "")
        name = t.get("name", "")
        url = t.get("url", "")
        desc = t.get("description", "") or ""
        content = t.get("content", "") or ""
        c_len = len(content)
        d_len = len(desc)
        flags = []
        if not content.strip():
            flags.append("EMPTY_CONTENT")
        elif c_len < 400:
            flags.append("SHORT_CONTENT")
        if not desc.strip():
            flags.append("EMPTY_DESC")
        if is_guessed_url(t):
            flags.append("GUESSED_URL")
        if not t.get("price"):
            flags.append("NO_PRICE")
        if not t.get("platform"):
            flags.append("NO_PLATFORM")
        # 厂商提及：description/content 中是否出现常见公司后缀
        text = (desc + " " + content)
        has_company = bool(re.search(r"(公司|科技|团队|开发|推出|旗下|实验室|Inc\.|Labs|Corp|Google|OpenAI|Anthropic|Microsoft|Meta|百度|阿里|腾讯|字节|讯飞|智谱|月之暗面|MiniMax|阶跃|昆仑|百川|DeepSeek|商汤|金山|网易|360)", text))
        if not has_company:
            flags.append("NO_VENDOR_MENTION")
        h = hashlib.md5(norm_content(content).encode()).hexdigest()
        dup_groups[h].append(slug)
        for f in flags:
            flags_counter[f] += 1
        rows.append({
            "slug": slug, "name": name, "category": t.get("category",""),
            "url": url, "content_len": c_len, "desc_len": d_len,
            "flags": ";".join(flags)
        })
    # 重复内容
    dup_count = sum(1 for v in dup_groups.values() if len(v) > 1)
    total_dup_tools = sum(len(v) for v in dup_groups.values() if len(v) > 1)
    # 写 CSV
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["slug","name","category","url","content_len","desc_len","flags"])
        w.writeheader()
        for r in sorted(rows, key=lambda x: (-len(x["flags"].split(";") if x["flags"] else []), x["slug"])):
            w.writerow(r)
    print(f"已发布工具总数: {len(pub)}")
    print("--- 风险标记统计 ---")
    for k, v in flags_counter.most_common():
        print(f"  {k}: {v}")
    print(f"--- 重复内容组: {dup_count} 组, 涉及 {total_dup_tools} 个工具 ---")
    # 列出重复组
    for h, slugs in dup_groups.items():
        if len(slugs) > 1:
            print(f"  重复({len(slugs)}): {', '.join(slugs)}")
    print(f"\nCSV 已写出: {OUT_CSV}")
    # 高危工具（含 GUESSED_URL 或 EMPTY/SHORT）
    high = [r for r in rows if "GUESSED_URL" in r["flags"] or "EMPTY_CONTENT" in r["flags"] or "SHORT_CONTENT" in r["flags"] or "NO_VENDOR_MENTION" in r["flags"]]
    print(f"\n需优先在线核实的高危工具: {len(high)} 个")
    for r in high[:40]:
        print(f"  [{r['slug']}] {r['name']} | {r['url']} | {r['flags']}")

if __name__ == "__main__":
    audit()
