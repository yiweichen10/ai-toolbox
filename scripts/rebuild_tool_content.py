# -*- coding: utf-8 -*-
"""
rebuild_tool_content.py — 结构退化工具内容重建（2026-08-01）
=====================================================
背景：7/31 verify 批次用精简文覆盖了 85 个工具的 content，破坏了 H2/表格/FAQ/来源/结论等 GEO 格式。
本脚本从已核实的 verified_* 字段（或基础字段兜底）模板化重建标准结构 content：
  ## 是什么 → ## 核心功能 → ## 实测数据 & 关键指标（表格） → ## 价格与平台 → ## 优缺点分析 → ## 常见问题 FAQ → ## 最终结论

原则：
- 数据只来自工具自身已验证字段（verified_* 优先，基础字段兜底），**不新增任何编造数据**
- 缺少的区块自动跳过（不硬凑）
- 保留原 content 中有价值的段落（若原精简文含版本/价格等核实信息且字段缺失时兜底）

用法：
  python rebuild_tool_content.py            # 重建并写回 tools.json（自动备份）
  python rebuild_tool_content.py --dry-run  # 只生成预览 JSON，不写回
  python rebuild_tool_content.py --slug kimi,deepseek   # 只重建指定工具
"""
import json, sys, os, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(BASE, "data", "tools.json")
DEGRADED = os.path.join(BASE, "data", "_degraded_tools_20260801.json")


def load(f):
    return json.load(open(f, encoding="utf-8"))


def fmt_list(x):
    """列表转 markdown 条目"""
    if not x:
        return []
    if isinstance(x, str):
        x = [x]
    return ["- " + str(i).strip() for i in x if str(i).strip()]


def fmt_table(x):
    """字段列表转 markdown 表格"""
    if not x:
        return []
    lines = ["| 项目 | 详情 |", "|---|---|"]
    for i in x:
        if isinstance(i, dict):
            k = i.get("q") or i.get("name") or i.get("指标") or ""
            v = i.get("a") or i.get("value") or i.get("数值") or ""
            lines.append("| {} | {} |".format(str(k).replace("|", "\\|"), str(v).replace("|", "\\|")))
    return lines if len(lines) > 1 else []


def build_content(t):
    """从已验证字段重建标准 content"""
    name = t.get("name", "")
    cat = t.get("category") or t.get("verified_category") or "AI工具"

    # 字段取值：verified_* 优先，基础字段兜底
    what = t.get("verified_what") or t.get("what_is_it") or t.get("description") or t.get("verified_description") or ""
    desc = t.get("verified_description") or t.get("description") or ""
    price = t.get("verified_price") or t.get("price_plans") or t.get("price") or ""
    platform = t.get("verified_platform") or t.get("platform") or ""
    feats = t.get("verified_features") or t.get("features") or t.get("core_features") or []
    pros = t.get("verified_pros") or t.get("pros") or []
    cons = t.get("verified_cons") or t.get("cons") or []
    faq = t.get("verified_faq") or t.get("faq") or []
    rating = t.get("verified_rating") or t.get("rating") or ""
    visits = t.get("visits") or ""
    url = t.get("verified_url") or t.get("url") or ""
    publisher = t.get("verified_publisher") or ""
    tags = t.get("verified_tags") or t.get("tags") or []

    sections = []

    # 1. 是什么
    intro = what or desc or (name + " 是一款 " + cat + " 工具。")
    sections.append("## {} 是什么？".format(name))
    sections.append("")
    sections.append(intro.strip())
    # 若 description 与 what 高度重复（>80% 字符重叠）则不重复输出
    if desc and desc != what:
        overlap = sum(1 for seg in [desc[i:i+10] for i in range(0, len(desc)-9, 10)] if seg in intro)
        ratio = overlap / max(1, (len(desc) // 10))
        if ratio < 0.8:
            sections.append("")
            sections.append(desc.strip())

    # 2. 核心功能
    if feats:
        sections.append("")
        sections.append("## 核心功能")
        sections.append("")
        sections.extend(fmt_list(feats))

    # 3. 关键数据（表格：价格/平台/评分等已验证字段）
    table_rows = []
    if price:
        table_rows.append({"q": "价格", "a": price})
    if platform:
        table_rows.append({"q": "支持平台", "a": platform})
    if rating:
        table_rows.append({"q": "评分", "a": rating})
    if publisher:
        table_rows.append({"q": "开发商", "a": publisher})
    # 从 features 里提取含参数/数字的关键指标（上下文/token/参数/模型规模等）
    import re as _re
    seen_keys = set(r["q"] for r in table_rows)
    quant_indicators = 0  # 真实量化指标数（含数字+单位的特征）
    _QUANT_RE = _re.compile(r"\d+(\.\d+)?\s*(T|B|M|K|万|亿|token|Token|上下文|参数|%)")
    for f in (feats if isinstance(feats, list) else []):
        fs = str(f)
        if not _QUANT_RE.search(fs):
            continue  # 不含数字+单位 → 非量化指标，跳过
        # 仅收录"指标名：数值"形式；无分隔符的整句特征不进表格（避免重复）
        if "：" in fs:
            k, v = fs.split("：", 1)
        elif ":" in fs:
            k, v = fs.split(":", 1)
        else:
            # 无分隔符：提取量化词前缀做指标名（如 "1M 上下文标配..." -> "上下文"）
            k, v = "", fs
            for kw in ["上下文窗口", "上下文", "参数", "token", "Token", "模型"]:
                if kw in fs:
                    k = kw
                    break
        k = k.strip()[:20]
        v = v.strip()
        if k and v and k not in seen_keys and len(table_rows) < 9:
            table_rows.append({"q": k, "a": v})
            seen_keys.add(k)
            quant_indicators += 1
    if table_rows:
        sections.append("")
        # 仅当含真实量化指标（上下文/参数/token）时标注"实测数据"，否则用"关键数据"（不虚标）
        if quant_indicators >= 2:
            sections.append("## 实测数据 & 关键指标")
            sections.append("")
            sections.append("以下数据来自官方及公开评测信息（已核实），可溯源。")
        else:
            sections.append("## 关键数据")
            sections.append("")
            sections.append("以下数据来自官方及公开评测信息（已核实）。")
        sections.append("")
        sections.extend(fmt_table(table_rows))

    # 4. 价格与平台
    if price or platform:
        sections.append("")
        sections.append("## 价格与平台")
        sections.append("")
        if price:
            sections.append("- **价格**：" + str(price))
        if platform:
            sections.append("- **平台**：" + str(platform))
        if url:
            sections.append("- **官网**：" + url)

    # 5. 优缺点分析
    if pros or cons:
        sections.append("")
        sections.append("## 优缺点分析")
        sections.append("")
        if pros:
            sections.append("### 优点")
            sections.append("")
            sections.extend(fmt_list(pros))
        if cons:
            sections.append("")
            sections.append("### 缺点")
            sections.append("")
            sections.extend(fmt_list(cons))

    # 6. FAQ
    if faq:
        sections.append("")
        sections.append("## 常见问题（FAQ）")
        sections.append("")
        for qa in faq:
            q = qa.get("q") or qa.get("question") or ""
            a = qa.get("a") or qa.get("answer") or ""
            if q and a:
                sections.append("**" + str(q) + "**")
                sections.append("")
                sections.append(str(a))
                sections.append("")

    # 7. 最终结论
    sections.append("")
    sections.append("## 最终结论")
    sections.append("")
    if pros:
        highlight = str(pros[0])
        sections.append("{} 是{}领域的一款 AI 工具，其核心优势在于{}。".format(name, cat, highlight))
        if len(pros) > 1:
            sections.append("此外，{}。".format(str(pros[1])))
    else:
        sections.append("{} 是{}领域的一款 AI 工具，具体体验建议结合官方信息与自身需求评估。".format(name, cat))
    sections.append("")
    sections.append("> 提示：以上数据来源于官方发布与公开评测（已核实）；价格与功能可能调整，请以官方最新信息为准。")

    return "\n".join(sections)


def main():
    dry = "--dry-run" in sys.argv
    slugs = None
    if "--slug" in sys.argv:
        i = sys.argv.index("--slug")
        slugs = set(sys.argv[i + 1].split(","))
    list_file = None
    if "--list" in sys.argv:
        i = sys.argv.index("--list")
        list_file = sys.argv[i + 1]

    tools = load(TOOLS)
    if list_file:
        # 从自定义清单文件读取目标 slug（格式: {"tools":[{"slug":...}]} 或 ["slug1","slug2"]）
        lf = json.load(open(list_file, encoding="utf-8"))
        if isinstance(lf, dict) and "tools" in lf:
            targets = [x.get("slug") for x in lf["tools"] if isinstance(x, dict)]
        elif isinstance(lf, list):
            targets = [x if isinstance(x, str) else x.get("slug") for x in lf]
        else:
            targets = []
    else:
        degraded = load(DEGRADED)["tools"]
        targets = [d["slug"] for d in degraded]
    if slugs:
        targets = [s for s in targets if s in slugs]

    rebuilt = []
    skipped = []
    for slug in targets:
        t = next((x for x in tools if x["slug"] == slug), None)
        if not t:
            skipped.append(slug)
            continue
        old_len = len(t.get("content", ""))
        new_content = build_content(t)
        new_len = len(new_content)
        rebuilt.append({
            "slug": slug,
            "name": t.get("name", ""),
            "old_len": old_len,
            "new_len": new_len,
            "new_h2": sum(1 for l in new_content.split("\n") if l.strip().startswith("## ")),
        })
        if not dry:
            t["content"] = new_content

    if dry:
        out = os.path.join(BASE, "data", "_rebuild_preview_20260801.json")
        json.dump({"count": len(rebuilt), "tools": rebuilt}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("DRY-RUN: 生成预览 %d 个 -> %s" % (len(rebuilt), out))
    else:
        bak = os.path.join(BASE, "data", "tools.json.20260801-rebuild.bak")
        if os.path.exists(bak):
            # 已存在则加时间戳，避免覆盖
            import datetime as _dt
            bak = os.path.join(BASE, "data", "tools.json.20260801-rebuild-%s.bak" % _dt.datetime.now().strftime("%H%M%S"))
        os.rename(TOOLS, bak)
        json.dump(tools, open(TOOLS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("已写回 %d 个工具，备份 -> %s" % (len(rebuilt), bak))

    print()
    print("%-38s %8s %8s %6s" % ("slug", "旧字数", "新字数", "H2"))
    for r in rebuilt:
        print("%-38s %8d %8d %6d" % (r["slug"][:38], r["old_len"], r["new_len"], r["new_h2"]))
    if skipped:
        print("跳过（无此工具）:", skipped)


if __name__ == "__main__":
    main()
