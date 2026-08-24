# -*- coding: utf-8 -*-
"""
generate_compare_batch.py — 批量生成竞品对比内容（数据驱动，不编造）
================================================
1) compares：精选 39 组同分类对比页（compares[]，content 基于已核实字段模板生成）
2) alternatives：17 个热门工具替代方案页（alternatives[]）
3) compare_section：给无配置的热门工具批量配内嵌竞品对比版块（tools.json）
合并写入 compare_data.json / tools.json，自动备份。
"""
import json, shutil, re, datetime
from collections import defaultdict

BASE = "data/"
TODAY = datetime.date.today().isoformat()
CATS = ['AI编程','AI开发','AI对话','AI视频','AI效率','AI设计','AI办公','AI行业应用','AI绘画','AI音频','AI写作','AI智能体','AI搜索','AI自动化','AI翻译']

def load_tools():
    return json.load(open(BASE + "tools.json", encoding="utf-8"))

def fmt_price(t):
    p = str(t.get("price") or "").strip()
    return p if p else "—"

def fmt_feats(t):
    feats = t.get("features") or t.get("verified_features") or []
    if isinstance(feats, str):
        feats = [feats]
    return [str(f).strip() for f in feats][:3]

def rating_num(t):
    m = re.search(r"([\d.]+)", str(t.get("rating") or ""))
    return float(m.group(1)) if m else 0.0

def esc(s):
    return str(s).replace("<", "&lt;").replace(">", "&gt;")

# ---------- 1) 精选对比组合（slug 均已验证存在） ----------
COMPARE_SETS = [
    ("AI对话", ["chatgpt", "claude"]),
    ("AI对话", ["chatgpt", "claude", "deepseek"]),
    ("AI对话", ["deepseek", "kimi"]),
    ("AI对话", ["gemini", "grok"]),
    ("AI对话", ["chatgpt", "gemini"]),
    ("AI对话", ["claude", "deepseek"]),
    ("AI对话", ["kimi", "doubao"]),
    ("AI对话", ["doubao", "qwen-chat"]),
    ("AI编程", ["cursor", "windsurf"]),
    ("AI编程", ["cursor", "github-copilot"]),
    ("AI编程", ["cline", "codex-cli"]),
    ("AI编程", ["replit-ai", "lovable"]),
    ("AI编程", ["bolt.new", "cursor"]),
    ("AI编程", ["github-copilot", "cline"]),
    ("AI编程", ["windsurf", "github-copilot"]),
    ("AI绘画", ["midjourney", "stable-diffusion"]),
    ("AI绘画", ["midjourney", "flux"]),
    ("AI绘画", ["flux", "stable-diffusion"]),
    ("AI绘画", ["dall-e-3", "midjourney"]),
    ("AI绘画", ["magnific-ai", "midjourney"]),
    ("AI视频", ["sora", "runway"]),
    ("AI视频", ["kling-ai", "pika"]),
    ("AI视频", ["vidu-ai", "kling-ai"]),
    ("AI视频", ["heygen", "invideo-ai"]),
    ("AI视频", ["runway", "kaiber"]),
    ("AI视频", ["vidu-ai", "sora"]),
    ("AI音乐", ["suno", "udio"]),
    ("AI音乐", ["suno", "elevenlabs"]),
    ("AI音乐", ["udio", "riffusion"]),
    ("AI音乐", ["elevenlabs", "spark-tts"]),
    ("AI写作", ["jasper", "copy.ai"]),
    ("AI写作", ["writesonic", "copy.ai"]),
    ("AI写作", ["jasper", "writesonic"]),
    ("AI办公", ["notion-ai", "microsoft-copilot"]),
    ("AI办公", ["gamma", "slidesai"]),
    ("AI办公", ["notion-ai", "gamma"]),
    ("AI设计", ["canva-ai", "figma-ai"]),
    ("AI设计", ["canva-ai", "adobe-firefly"]),
    ("AI设计", ["figma-ai", "adobe-firefly"]),
]

ALT_TARGETS = ["chatgpt", "claude", "deepseek", "kimi", "gemini", "cursor", "windsurf",
               "midjourney", "stable-diffusion", "sora", "runway", "vidu-ai", "kling-ai",
               "suno", "udio", "notion-ai", "canva-ai", "jasper"]

def gen_compare_content(cat, tools):
    names = [t["name"] for t in tools]
    r = [rating_num(t) for t in tools]
    win = tools[r.index(max(r))]
    lines = [f"## {names[0]} vs {names[1]}：快速结论",
             f"- **综合表现**：{names[0]}（⭐{r[0]}）与 {names[1]}（⭐{r[1]}）同属{cat}赛道，{win['name']} 编辑评分更高。",
             "- **价格**：" + "；".join(f"{t['name']} {fmt_price(t)}" for t in tools),
             "- **核心功能**：" + "；".join(f"{t['name']}：{'、'.join(fmt_feats(t))}" for t in tools),
             "",
             "## 价格与平台对比",
             "",
             "| 工具 | 价格 | 平台 |",
             "|---|---|---|",
             *[f"| {esc(t['name'])} | {esc(fmt_price(t))} | {esc(str(t.get('platform') or t.get('verified_platform') or '—'))} |" for t in tools],
             "",
             "## 核心功能对比",
             "",
             "| 工具 | 核心功能 |",
             "|---|---|",
             *[f"| {esc(t['name'])} | {esc('、'.join(fmt_feats(t)))} |" for t in tools],
             "",
             "## 如何选择",
             "",
             f"- **选 {tools[0]['name']}**：如果你的重点是 {fmt_feats(tools[0])[0]}，且预算适合 {fmt_price(tools[0])}。",
             f"- **选 {tools[1]['name']}**：如果你的重点是 {fmt_feats(tools[1])[0]}，且预算适合 {fmt_price(tools[1])}。",
             ]
    if len(tools) > 2:
        lines.append(f"- **选 {tools[2]['name']}**：如果你的重点是 {fmt_feats(tools[2])[0]}，且预算适合 {fmt_price(tools[2])}。")
    return "\n".join(lines)

def gen_verdict(tools):
    r = [rating_num(t) for t in tools]
    win = tools[r.index(max(r))]
    free = [t for t in tools if "免费" in str(t.get("price") or "")]
    best_value = (max(free, key=rating_num) if free else win)
    return {"overall_winner": win["name"], "best_value": best_value["name"], "best_for_pro": win["name"]}

def gen_alt_content(target, alts):
    lines = [f"## {target['name']} 最佳替代方案（{target.get('category','')}赛道）",
             "",
             f"{target['name']}（{fmt_price(target)}）是目前{target.get('category','')}领域的代表工具之一。如果你想要其他选择，以下同赛道工具值得考虑：",
             "",
             "| 工具 | 价格 | 一句话亮点 |",
             "|---|---|---|",
             *[f"| {esc(t['name'])} | {esc(fmt_price(t))} | {esc(fmt_feats(t)[0])} |" for t in alts],
             "",
             "## 如何挑选替代",
             "",
             "- **预算有限**：优先选价格含『免费』或更低的工具。",
             "- **功能侧重**：对比各工具的核心功能第一项是否匹配你的需求。",
             "- **平台兼容**：确认替代工具支持你常用的平台（Web/桌面/移动/API）。",
             ]
    return "\n".join(lines)

def main():
    shutil.copy2(BASE + "compare_data.json", BASE + "compare_data.json.bak_" + TODAY.replace("-", ""))
    shutil.copy2(BASE + "tools.json", BASE + "tools.2026-07-31.bak")

    tools = load_tools()
    T = {t["slug"]: t for t in tools}
    cd = json.load(open(BASE + "compare_data.json", encoding="utf-8"))
    old_slugs = {c.get("slug") for c in cd["compares"]} | {a.get("slug") for a in cd["alternatives"]}
    added_c = added_a = 0

    # --- compares ---
    for cat, slugs in COMPARE_SETS:
        ts = [T[s] for s in slugs if s in T]
        if len(ts) < 2:
            continue
        names = [t["name"] for t in ts]
        slug = "-vs-".join(t["slug"] for t in ts)
        if slug in old_slugs:
            continue
        title = f"{names[0]} vs {names[1]}：{cat}工具全方位对比评测"
        cd["compares"].append({
            "title": title,
            "subtitle": f"{' vs '.join(names)} 谁更适合你？价格/功能/平台一次看清",
            "slug": slug,
            "meta_description": f"2026年{' vs '.join(names)}全方位对比：功能、价格、平台与使用场景深度评测，帮你选对{cat}工具。已收录500款AI工具。",
            "keywords": [f"{names[0]} vs {names[1]}", f"{names[0]}和{names[1]}对比", f"{cat}工具对比", "AI工具评测"],
            "quick_verdict": gen_verdict(ts),
            "content": gen_compare_content(cat, ts),
            "faq": [{"question": f"{names[0]}和{names[1]}哪个更好？",
                     "answer": f"两者同属{cat}赛道：{gen_verdict(ts)['overall_winner']} 编辑评分最高；价格方面 {'、'.join(t['name']+'('+fmt_price(t)+')' for t in ts)}，可按预算和功能侧重选择。"}],
            "compared_tools": [t["slug"] for t in ts],
            "compare_category": cat,
            "page_type": "compare",
            "priority": "high",
            "last_updated": TODAY,
        })
        added_c += 1

    # --- alternatives ---
    by_cat = defaultdict(list)
    for t in tools:
        by_cat[t.get("category", "")].append(t)
    for c in by_cat:
        by_cat[c].sort(key=rating_num, reverse=True)

    for tslug in ALT_TARGETS:
        t = T.get(tslug)
        if not t:
            continue
        cat = t.get("category", "")
        alts = [x for x in by_cat.get(cat, []) if x["slug"] != tslug][:4]
        if len(alts) < 2:
            continue
        slug = f"{tslug}-alternatives"
        if slug in old_slugs:
            continue
        cd["alternatives"].append({
            "title": f"2026年最佳{ t['name'] }替代方案推荐",
            "subtitle": f"{len(alts)}款{cat}同类工具横向对比",
            "slug": slug,
            "meta_description": f"寻找{t['name']}替代品？本文评测2026年{cat}领域{len(alts)}款同类工具的价格与亮点。已收录500款AI工具。",
            "keywords": [f"{t['name']}替代", f"类似{t['name']}", f"{cat}工具"],
            "content": gen_alt_content(t, alts),
            "faq": [{"question": f"{t['name']}有什么替代品？",
                     "answer": f"同赛道可选 {'、'.join(x['name'] for x in alts)}，价格分别 {'、'.join(x['name']+'('+fmt_price(x)+')' for x in alts)}，可按预算与功能选择。"}],
            "target_tool": tslug,
            "page_type": "alternatives",
            "last_updated": TODAY,
        })
        added_a += 1

    cd["metadata"]["updated"] = TODAY
    json.dump(cd, open(BASE + "compare_data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # --- compare_section 内嵌版块：给无配置的热门工具补（rating>=4.0 且同分类有>=3个竞品） ---
    added_s = 0
    for t in tools:
        if t.get("compare_section") and t["compare_section"].get("competitors"):
            continue
        if rating_num(t) < 4.0:
            continue
        cat = t.get("category", "")
        cands = [x for x in by_cat.get(cat, []) if x["slug"] != t["slug"]][:3]
        if len(cands) < 2:
            continue
        t["compare_section"] = {
            "competitors": [x["slug"] for x in cands],
            "verdict": f"{t['name']} 与 {'、'.join(x['name'] for x in cands)} 同属{cat}赛道：{t['name']} 的 {fmt_feats(t)[0]} 是亮点，价格 {fmt_price(t)}；竞品各有侧重，可按预算与功能需求选择。",
        }
        added_s += 1
    json.dump(tools, open(BASE + "tools.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"新增 compares: {added_c} 组 | alternatives: {added_a} 组 | compare_section 内嵌: {added_s} 个")
    print(f"compare_data.json 现: compares={len(cd['compares'])} alternatives={len(cd['alternatives'])}")
    # 校验
    json.load(open(BASE + "compare_data.json", encoding="utf-8"))
    json.load(open(BASE + "tools.json", encoding="utf-8"))
    print("JSON 校验通过")

if __name__ == "__main__":
    main()
