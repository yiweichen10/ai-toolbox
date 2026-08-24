# -*- coding: utf-8 -*-
"""
titleize_content.py — 第二批：纯段落长文标题化（2026-08-01）
=====================================================
背景：54 个工具 H2=0 但有完整长文（coze/dify/opus-clip 等），内容优质，
     不能覆盖重写，只需按段落语义插入 H2 标题，原文一字不改。

规则：按段落关键词匹配语义 → 插入标准 H2：
  价格/费用/收费/免费/定价/付费 → ## 价格与平台
  功能/能力/支持/可以/能够/特性 → ## 核心功能
  优点/优势/亮点/价值 → ## 核心优势
  缺点/不足/局限/限制 → ## 不足与限制
  适合/适用/人群/场景 → ## 适合人群
  使用/建议/提醒/上手 → ## 使用建议
  总结/结论/整体/总的说/从工作流 → ## 最终结论
  第一段 → ## {name} 是什么？

用法：
  python titleize_content.py --list data/_batch2_titleize.json      # 按清单
  python titleize_content.py --list xxx.json --dry-run              # 预览
"""
import json, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(BASE, "data", "tools.json")

# 段落语义 → H2 标题（按优先级，精确关键词）
RULES = [
    (["价格方面", "价格上", "价格清晰", "定价", "费用", "收费", "免费版", "付费", "套餐", "订阅", "按月", "元/月", "$/月", "/月起"], "## 价格与平台"),
    (["FAQ", "常见问题", "问：", "Q："], "## 常见问题（FAQ）"),
    (["不足", "缺点", "局限", "限制", "短板", "但", "然而", "需要提醒"], "## 不足与限制"),
    (["优点", "优势", "亮点", "好处", "价值在于", "的意义", "相比", "需要说明"], "## 核心优势"),
    (["适合人群", "适合谁", "适用人群", "最适合作为", "适合作为", "目标用户", "面向"], "## 适合人群"),
    (["使用建议", "上手", "技巧", "建议先", "建议从", "建议你"], "## 使用建议"),
    (["总结", "结论", "整体看", "总的来看", "从工作流角度", "最后", "说到底"], "## 最终结论"),
    (["核心能力", "功能", "能力", "特性", "支持", "可以", "能够", "内置", "提供", "模式", "协作", "工作流", "平台"], "## 核心功能"),
]

# 段落首句排除词（首段/价格段/结尾段的特殊处理）
def pick_title(p, is_first, is_last):
    if is_first:
        return None  # 首段由外部处理
    if is_last:
        return "## 最终结论"  # 最后一段强制总结
    for kws, t in RULES:
        # "最终结论" 关键词只在非末段时跳过（避免中间段落误配）
        if t == "## 最终结论":
            continue
        if any(k in p for k in kws):
            return t
    return None

def fix_heading_levels(content):
    """修复标题层级：# → ##、### → ##（内容不变，零风险）"""
    out = []
    for l in content.split("\n"):
        s = l.strip()
        if s.startswith("### "):
            out.append("## " + s[4:])
        elif s.startswith("## "):
            out.append(l)
        elif s.startswith("# "):
            out.append("## " + s[2:])
        else:
            out.append(l)
    return "\n".join(out)


def titleize(content, name):
    """对纯段落长文插入 H2 标题，保留全部原文；已有 ###/# 结构的升级为 ##"""
    # 情况1：已有 ## 标题（真H2），跳过
    real_h2 = [l for l in content.split("\n") if l.strip().startswith("## ") and not l.strip().startswith("### ")]
    if real_h2:
        return content, 0

    # 情况2：用 # 或 ### 当标题（层级错误）→ 统一修复为 ##
    if any(l.strip().startswith(("# ", "### ")) for l in content.split("\n")):
        return fix_heading_levels(content), 0

    paras = [p.strip() for p in content.split("\n\n") if p.strip()]
    if not paras:
        return content, 0

    out = []
    added = 0
    used_titles = set()
    n = len(paras)
    for i, p in enumerate(paras):
        if i == 0:
            # 首段标题：若段落首句已含工具名则不重复拼接
            first_para = p.strip()
            tname = name.strip()
            if tname and tname not in first_para[:30]:
                title_text = tname
            else:
                title_text = first_para.split("（")[0].split("(")[0].strip()[:20] or tname or name
            out.append("## {} 是什么？".format(title_text))
            out.append("")
            added += 1
            used_titles.add("## {} 是什么？".format(title_text))
            out.append(p)
            out.append("")
            continue

        # 语义匹配（最后一段强制总结，避免"从工作流角度"在中间段落误配）
        title = pick_title(p, is_first=False, is_last=(i == n - 1))
        if title and title not in used_titles:
            out.append(title)
            out.append("")
            added += 1
            used_titles.add(title)
        out.append(p)
        out.append("")

    return "\n".join(out).strip() + "\n", added


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
        new, added = titleize(old, t.get("name", ""))
        if not dry:
            t["content"] = new
        h2 = sum(1 for l in new.split("\n") if l.strip().startswith("## "))
        results.append({"slug": slug, "old_len": len(old), "new_len": len(new), "h2": h2, "added": added})

    if not dry:
        bak = os.path.join(BASE, "data", "tools.json.20260801-titleize2.bak")
        if os.path.exists(bak):
            import datetime
            bak = os.path.join(BASE, "data", "tools.json.20260801-titleize2-%s.bak" % datetime.datetime.now().strftime("%H%M%S"))
        os.rename(TOOLS, bak)
        json.dump(tools, open(TOOLS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("已写回 %d 个，备份 -> %s" % (len(results), bak))
    else:
        print("DRY-RUN")

    print()
    print("%-30s %8s %8s %4s %4s" % ("slug", "旧字数", "新字数", "H2", "+标题"))
    for r in results:
        print("%-30s %8d %8d %4d %4d" % (r["slug"][:30], r["old_len"], r["new_len"], r["h2"], r["added"]))


if __name__ == "__main__":
    main()
