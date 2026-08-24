# -*- coding: utf-8 -*-
"""
append_blocks.py — 给已有结构的内容补区块
=====================================================
背景：部分工具已有 H2 结构和结论，但缺 FAQ。
策略：保留现有 content 全文，在末尾追加：
  ## 常见问题（FAQ）—— 数据从 verified_faq 取（无则跳过）

⚠️ 铁律（2026-08-02 整改）：禁止在 content 中追加「数据来源」链接列表！
source_urls / verified_url 是给 AI 核实时看的参考数据，只允许存留在
tools.json 的 source_urls 字段中，绝不能渲染到线上页面。

用法：
  python append_blocks.py --list data/_batch3_x.json            # 执行
  python append_blocks.py --list data/_batch3_x.json --dry-run  # 预览
"""
import json, os, sys, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(BASE, "data", "tools.json")


def append_blocks(t):
    """在现有 content 末尾追加缺失的 FAQ / 数据来源 区块，返回 (新content, 追加了什么)"""
    c = t.get("content", "")
    name = t.get("name", "")
    added = []

    # 1. FAQ
    faq = t.get("verified_faq") or t.get("faq") or []
    has_faq = ("FAQ" in c) or ("常见问题" in c)
    if faq and not has_faq:
        block = ["", "## 常见问题（FAQ）", ""]
        for qa in faq:
            q = qa.get("q") or qa.get("question") or ""
            a = qa.get("a") or qa.get("answer") or ""
            if q and a:
                block.append("**" + str(q) + "**")
                block.append("")
                block.append(str(a))
                block.append("")
        if len(block) > 3:
            c = c.rstrip() + "\n" + "\n".join(block)
            added.append("FAQ")

    # 2. 数据来源 —— 已移除（2026-08-02 整改）
    # source_urls / verified_url 仅供 AI 核实参考，禁止渲染到线上页面。
    # 历史遗留的「## 数据来源」链接列表已从 126 个工具 content 中批量清除。

    return c, added


def main():
    dry = "--dry-run" in sys.argv
    i = sys.argv.index("--list")
    list_file = sys.argv[i + 1]

    tools = json.load(open(TOOLS, encoding="utf-8"))
    lf = json.load(open(list_file, encoding="utf-8"))
    targets = [x["slug"] for x in lf["tools"]] if isinstance(lf, dict) and "tools" in lf else lf

    results = []
    for slug in targets:
        t = next((x for x in tools if x["slug"] == slug), None)
        if not t:
            continue
        old = t.get("content", "")
        new, added = append_blocks(t)
        if not dry:
            t["content"] = new
        h2 = sum(1 for l in new.split("\n") if l.strip().startswith("## "))
        results.append({"slug": slug, "old_len": len(old), "new_len": len(new), "h2": h2, "added": added})

    if not dry:
        bak = os.path.join(BASE, "data", "tools.json.20260801-append3.bak")
        if os.path.exists(bak):
            bak = os.path.join(BASE, "data", "tools.json.20260801-append3-%s.bak" % datetime.datetime.now().strftime("%H%M%S"))
        os.rename(TOOLS, bak)
        json.dump(tools, open(TOOLS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("已写回 %d 个，备份 -> %s" % (len(results), bak))
    else:
        print("DRY-RUN")

    print()
    n_faq = sum(1 for r in results if "FAQ" in r["added"])
    n_src = sum(1 for r in results if "来源" in r["added"])
    print("补FAQ: %d | 补来源: %d | 无变化: %d" % (n_faq, n_src, len(results) - n_faq - n_src))
    for r in results:
        print("  %-30s 旧%d->新%d H2=%d %s" % (r["slug"][:30], r["old_len"], r["new_len"], r["h2"], r["added"]))


if __name__ == "__main__":
    main()
