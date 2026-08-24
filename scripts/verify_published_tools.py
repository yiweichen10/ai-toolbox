#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
已发布工具全量 Agent 核实 — 结果汇总脚本
=========================================
读取 scripts/_verify_batches/batches.json（分批清单）
读取 scripts/_verify_batches/result_*.json（各批 Agent 核验结果）
输出：
  - scripts/_verify_batches/REPORT.md  人类可读报告
  - scripts/_verify_batches/SUMMARY.json 机器可读汇总

用法：
  python scripts/verify_published_tools.py            # 汇总并出报告
  python scripts/verify_published_tools.py --check    # 仅检查哪些批次还没核完
"""
import json
import os
import glob
import argparse

BASE = os.path.dirname(os.path.abspath(__file__))
BATCH_DIR = os.path.join(BASE, "_verify_batches")


def load_batches():
    p = os.path.join(BATCH_DIR, "batches.json")
    return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else []


def load_results():
    results = {}
    for f in glob.glob(os.path.join(BATCH_DIR, "result_*.json")):
        bid = os.path.basename(f)[len("result_"):-len(".json")]
        try:
            results[bid] = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            print(f"  ⚠️ 读取 {f} 失败: {e}")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="仅检查未完成的批次")
    args = ap.parse_args()

    batches = load_batches()
    results = load_results()

    total_tools = sum(len(b["slugs"]) for b in batches)
    done_batches = set(results.keys())
    pending = [b for b in batches if b["batch_id"] not in done_batches]

    print(f"批次总数: {len(batches)} | 已完成: {len(done_batches)} | 待核: {len(pending)}")
    print(f"工具总数: {total_tools} | 已核工具: {sum(len(results[b['batch_id']].get('tools', [])) for b in batches if b['batch_id'] in results)}")

    if args.check:
        if pending:
            print("待核批次:")
            for b in pending:
                print(f"  {b['batch_id']} {b['category']} ({len(b['slugs'])}个)")
        else:
            print("✅ 全部批次已核完")
        return

    # 汇总
    url_bad, hallu, conflict, low_conf = [], [], [], []
    cat_stat = {}
    all_tools = []
    for b in batches:
        bid = b["batch_id"]
        if bid not in results:
            continue
        for t in results[bid].get("tools", []):
            all_tools.append(t)
            c = b["category"]
            cat_stat.setdefault(c, {"n": 0, "url_bad": 0, "hallu": 0, "conflict": 0})
            cat_stat[c]["n"] += 1
            if not t.get("url_ok"):
                url_bad.append(t)
                cat_stat[c]["url_bad"] += 1
            if t.get("hallucination"):
                hallu.append(t)
                cat_stat[c]["hallu"] += 1
            if t.get("conflict"):
                conflict.append(t)
                cat_stat[c]["conflict"] += 1
            if t.get("confidence") == "low":
                low_conf.append(t)

    # 报告
    lines = []
    lines.append("# 已发布工具全量 Agent 核实报告\n")
    lines.append(f"- 生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- 工具总数: **{total_tools}** | 已核: **{len(all_tools)}** | 批次: {len(batches)}")
    lines.append(f"- **URL 错误(需修)**: {len(url_bad)} 个")
    lines.append(f"- **内容幻觉(需重写)**: {len(hallu)} 个")
    lines.append(f"- **冲突存疑(进人工)**: {len(conflict)} 个")
    lines.append(f"- **低置信(需复核)**: {len(low_conf)} 个\n")

    lines.append("## 按分类统计\n")
    lines.append("| 分类 | 已核 | URL错 | 幻觉 | 冲突 |")
    lines.append("|------|------|-------|------|------|")
    for c, s in sorted(cat_stat.items(), key=lambda x: -(x[1]["hallu"] + x[1]["url_bad"])):
        lines.append(f"| {c} | {s['n']} | {s['url_bad']} | {s['hallu']} | {s['conflict']} |")

    if url_bad:
        lines.append("\n## URL 错误清单（必须修正为真实官网）\n")
        for t in url_bad:
            lines.append(f"- **{t.get('name')}** (`{t.get('slug')}`) 当前: `{t.get('url_current')}`"
                         + (f" → 应改: `{t.get('url_correct')}`" if t.get('url_correct') else " → 应改: 待查")
                         + (f" — {t.get('notes','')}" if t.get('notes') else ""))
    if hallu:
        lines.append("\n## 内容幻觉清单（需 Agent 重写 content/字段）\n")
        for t in hallu:
            fields = ",".join(t.get("hallucination_fields", []) or [])
            lines.append(f"- **{t.get('name')}** (`{t.get('slug')}`) 幻觉字段: {fields}"
                         + (f" — {t.get('notes','')}" if t.get('notes') else ""))
    if conflict:
        lines.append("\n## 冲突存疑清单（进人工裁定）\n")
        for t in conflict:
            lines.append(f"- **{t.get('name')}** (`{t.get('slug')}`) — {t.get('notes','')}")

    if pending:
        lines.append("\n## 未完成批次\n")
        for b in pending:
            lines.append(f"- {b['batch_id']} {b['category']} ({len(b['slugs'])}个)")

    report = "\n".join(lines)
    out_md = os.path.join(BATCH_DIR, "REPORT.md")
    open(out_md, "w", encoding="utf-8").write(report)
    summary = {
        "total_tools": total_tools, "verified": len(all_tools),
        "url_bad": len(url_bad), "hallucination": len(hallu),
        "conflict": len(conflict), "low_conf": len(low_conf),
        "pending_batches": [b["batch_id"] for b in pending],
    }
    open(os.path.join(BATCH_DIR, "SUMMARY.json"), "w", encoding="utf-8").write(
        json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n✅ 报告已写: {out_md}")
    print(f"   汇总: {json.dumps(summary, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
