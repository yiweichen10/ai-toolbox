# -*- coding: utf-8 -*-
"""审核85个重建工具内容 — 2026-08-01
检查项：
1. H2 结构完整性（应为7段：是什么/核心功能/数据/价格/优缺点/FAQ/结论）
2. 各区块是否为空/缺失
3. FAQ 是否为空数组
4. content 是否有异常字符（乱码/重复）
5. 数据来源是否标注
6. verified_* 与基础字段不一致风险
输出：审核报告 JSON + 控制台摘要
"""
import json, re, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
from rebuild_tool_content import build_content
from data_store import load_all_tools

tools = load_all_tools()   # 2026-08-26 去单体化: 分片优先
degraded = json.load(open(os.path.join(BASE, "data", "_degraded_tools_20260801.json"), encoding="utf-8"))["tools"]
targets = [d["slug"] for d in degraded]
tmap = {t["slug"]: t for t in tools}

EXPECTED_H2 = ["是什么", "核心功能", "数据", "价格与平台", "优缺点", "FAQ", "最终结论"]

report = []
issues_total = 0
for slug in targets:
    t = tmap.get(slug)
    if not t:
        report.append({"slug": slug, "issues": ["工具不存在"]})
        issues_total += 1
        continue
    c = t.get("content", "")
    issues = []

    # 1. H2 结构
    h2s = [l.strip() for l in c.split("\n") if l.strip().startswith("## ") and not l.strip().startswith("### ")]
    if len(h2s) < 6:
        issues.append("H2数量不足(%d)" % len(h2s))

    # 2. 各区块存在性
    if "是什么" not in c:
        issues.append("缺'是什么'")
    if "核心功能" not in c:
        issues.append("缺'核心功能'")
    if "价格与平台" not in c and "价格" not in c:
        issues.append("缺'价格与平台'")
    if "优缺点" not in c:
        issues.append("缺'优缺点'")
    if "FAQ" not in c and "常见问题" not in c:
        issues.append("缺'FAQ'")
    if "最终结论" not in c and "总结" not in c:
        issues.append("缺'最终结论'")

    # 3. 数据区块（实测/关键）
    if "实测数据" not in c and "关键数据" not in c:
        issues.append("缺'数据'区块")

    # 4. FAQ 空
    faq = t.get("verified_faq") or t.get("faq") or []
    if not faq:
        issues.append("verified_faq 为空（页面无FAQ）")

    # 5. 字段完整度
    missing_fields = []
    for f in ["verified_what", "verified_price", "verified_features", "verified_pros", "verified_cons"]:
        if not t.get(f):
            missing_fields.append(f)
    if missing_fields:
        issues.append("缺字段: " + ",".join(missing_fields))

    # 6. 异常字符
    if re.search(r"[\ufffd]|None|null|NaN", c):
        issues.append("含异常字符(None/null/乱码)")

    # 7. 内容中 ' 是AI对话领域' 这类模板瑕疵
    if "是" + (t.get("category") or "") + "领域的一款 AI 工具" not in c and (t.get("category")):
        if "领域的一款" not in c:
            issues.append("最终结论模板异常")

    if issues:
        issues_total += 1
    report.append({"slug": slug, "name": t.get("name", ""), "len": len(c), "h2": len(h2s), "issues": issues})

# 输出
clean = [r for r in report if not r["issues"]]
bad = [r for r in report if r["issues"]]
print("总审核: %d | 无问题: %d | 有问题: %d" % (len(report), len(clean), len(bad)))
print()
if bad:
    print("=== 有问题工具 ===")
    for r in bad:
        print("  %-36s %s" % (r["slug"][:36], "; ".join(r["issues"])))

out = os.path.join(BASE, "data", "_rebuild_audit_20260801.json")
json.dump({"total": len(report), "clean": len(clean), "issues": len(bad),
           "report": report}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print()
print("审核报告 -> %s" % out)
