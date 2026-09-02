#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""深度审计: 版本型工具的内容同步盲点。
弥补 check_version_drift.py 的 B 检查(max_ver 比对)盲点:
  - 正文里只要提一句新版本号, max_ver 就被拉平, 漂移被掩盖。
  - 本脚本改用「发布日期口径」判定: 描述说 X 月发布, 正文却写更早的 Y 月发布 -> 残留旧版。
"""
import json, re, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_store import load_all_tools

def brand_token_of(name):
    """取名字中【最后一个】版本号前的品牌锚定词, 覆盖版本号在中间的工具
    (如 'GPT-5.6 Sol' -> 'GPT'; 'Seedream 5.0 Pro' -> 'Seedream')。
    原 check_version_drift.py 只认末尾是版本号, 会漏掉这类。"""
    s = (name or "").strip()
    matches = list(re.finditer(r"([A-Za-z\u4e00-\u9fff][\w\u4e00-\u9fff\-]*?)[\s\-]*(\d+(?:\.\d+)*)", s))
    if not matches:
        return None
    m = matches[-1]
    return m.group(1).strip(" -") or None

# 提取 "X 于 2026 年 M 月发布" / "2026 年 M 月发布" 中的月份
DATE_RE = re.compile(r"20\d{2}\s*年\s*(\d{1,2})\s*月")
def min_release_month(text):
    ms = [int(x) for x in DATE_RE.findall(text or "")]
    return min(ms) if ms else None

def max_ver_after(text, token):
    if not token or not text:
        return None
    best = None
    for m in re.finditer(re.escape(token) + r"[\s\-]*(\d+(?:\.\d+)*)", text, re.I):
        parts = [int(p) for p in m.group(1).split(".")]
        while len(parts) < 3:
            parts.append(0)
        v = tuple(parts)
        if best is None or v > best:
            best = v
    return best

tools = load_all_tools()
covered = 0
suspects = []
for t in tools:
    name = t.get("name", "") or ""
    slug = t.get("slug", "") or ""
    btok = brand_token_of(name)
    if not btok:
        continue
    covered += 1
    desc = t.get("description") or ""
    body = (t.get("content") or "") + "\n" + " ".join(
        ((f.get("q") or "") + " " + (f.get("a") or "")) for f in (t.get("faq") or []) if isinstance(f, dict)
    )
    v_desc = max_ver_after(desc, btok)
    v_body = max_ver_after(body, btok)
    # 发布日期口径
    d_month = min_release_month(desc)
    b_month = min_release_month(body)
    flags = []
    if v_desc and v_body and v_desc > v_body:
        flags.append(f"desc_ver>{body_ver} ({'.'.join(map(str,v_desc[:2]))} > {'.'.join(map(str,v_body[:2]))})")
    if d_month and b_month and b_month < d_month:
        flags.append(f"发布日期旧: 描述{d_month}月 vs 正文{b_month}月")
    if flags:
        suspects.append({
            "slug": slug, "name": name, "brand_token": btok,
            "desc_ver": ".".join(map(str, v_desc[:2])) if v_desc else None,
            "body_ver": ".".join(map(str, v_body[:2])) if v_body else None,
            "desc_month": d_month, "body_month": b_month,
            "flags": flags,
            "last_verified": (t.get("last_verified") or "")[:10],
        })

print(f"版本型工具(名字带版本号)总数(=B检查覆盖范围): {covered} 个")
print(f"残留旧版嫌疑(描述/名字新, 正文旧): {len(suspects)} 个")
for x in suspects:
    print(f"  - {x['name']} ({x['slug']}) desc={x['desc_ver']} body={x['body_ver']} "
          f"月{d_month if False else x['desc_month']}->{x['body_month']} flags={x['flags']} verified={x['last_verified']}")
json.dump({"covered": covered, "suspects": suspects},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_audit_version_coverage.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("报告: scripts/_audit_version_coverage.json")
