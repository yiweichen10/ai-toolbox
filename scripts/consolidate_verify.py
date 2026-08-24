#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并 12 个并行核实 agent 的结果 (result_01..12.json)，
汇总成主报告 verify_report.json / verify_report.md，
并列出需要修正的工具 (FAKE / url_correct=False / desc_issue 非空)。
"""
import json, glob, os

OUT_DIR = "scripts/verify_batches"
results = []
missing = []
for i in range(1, 13):
    fn = os.path.join(OUT_DIR, f"result_{i:02d}.json")
    if not os.path.exists(fn):
        missing.append(i)
        continue
    try:
        data = json.load(open(fn, encoding="utf-8"))
        if isinstance(data, list):
            results.extend(data)
    except Exception as e:
        missing.append(i)
        print(f"解析失败 result_{i:02d}.json: {e}")

print(f"已合并 {len(results)} 条核实记录；缺失批次: {missing if missing else '无'}")

# 汇总
from collections import Counter
verdict_c = Counter(r.get("verdict", "UNCERTAIN") for r in results)
url_bad = [r for r in results if r.get("url_correct") is False]
desc_bad = [r for r in results if r.get("desc_issue")]
fake = [r for r in results if r.get("verdict") == "FAKE"]
uncertain = [r for r in results if r.get("verdict") == "UNCERTAIN"]

master = {
    "total_verified": len(results),
    "verdict_counts": dict(verdict_c),
    "needs_fix": {
        "fake": [{"slug": r["slug"], "name": r["name"], "evidence": r.get("evidence")} for r in fake],
        "wrong_url": [{"slug": r["slug"], "name": r["name"], "recorded_url": r.get("url"),
                       "correct_url": r.get("official_url"), "evidence": r.get("evidence")} for r in url_bad],
        "desc_issue": [{"slug": r["slug"], "name": r["name"], "issue": r.get("desc_issue")} for r in desc_bad],
    },
    "uncertain": [{"slug": r["slug"], "name": r["name"], "evidence": r.get("evidence")} for r in uncertain],
    "records": results,
}
json.dump(master, open(os.path.join(OUT_DIR, "verify_report.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

# Markdown 报告
lines = []
lines.append(f"# aitoollab.cn 已发布工具核实报告\n")
lines.append(f"- 核实总数: **{len(results)}** / 397 已发布")
lines.append(f"- 判定分布: REAL={verdict_c.get('REAL',0)} | FAKE={verdict_c.get('FAKE',0)} | UNCERTAIN={verdict_c.get('UNCERTAIN',0)}")
if missing:
    lines.append(f"- ⚠️ 缺失批次: {missing}（这些批次的 agent 可能未完成，需补跑）")
lines.append("")

if fake:
    lines.append(f"## 🔴 疑似虚假/不存在的工具 ({len(fake)})")
    for r in fake:
        lines.append(f"- **{r['name']}** (`{r['slug']}`) — {r.get('evidence')}")
    lines.append("")

if url_bad:
    lines.append(f"## 🟠 官网 URL 需修正 ({len(url_bad)})")
    for r in url_bad:
        lines.append(f"- **{r['name']}** (`{r['slug']}`)：记录 `{r.get('url')}` → 应为 `{r.get('official_url')}` — {r.get('evidence')}")
    lines.append("")

if desc_bad:
    lines.append(f"## 🟡 描述存在明显错误 ({len(desc_bad)})")
    for r in desc_bad:
        lines.append(f"- **{r['name']}** (`{r['slug']}`)：{r.get('desc_issue')}")
    lines.append("")

if uncertain:
    lines.append(f"## ⚪ 无法确认 (建议人工复核) ({len(uncertain)})")
    for r in uncertain:
        lines.append(f"- **{r['name']}** (`{r['slug']}`) — {r.get('evidence')}")
    lines.append("")

open(os.path.join(OUT_DIR, "verify_report.md"), "w", encoding="utf-8").write("\n".join(lines))
print(f"\n报告已写出: verify_report.json + verify_report.md")
print(f"FAKE={len(fake)}  错误URL={len(url_bad)}  描述错误={len(desc_bad)}  不确定={len(uncertain)}")
