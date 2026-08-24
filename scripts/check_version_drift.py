#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检测 tools.json 中"工具名版本"与"内容实际描述的版本"不一致的陈腐内容。
逻辑：
  1. 从工具 name/slug 提取产品族 + 版本号（如 GLM-5.2 -> 族 GLM, 版本 (5,2)）
  2. 在 content / faq / seo_keywords 中提取同一产品族出现的所有版本号
  3. 取内容"主版本"（H1 / seo_keywords 中出现的版本，缺失则取最高频）
  4. 若 内容主版本 < 工具名版本 -> 判定为"版本漂移/陈腐"（内容写的是旧版）
  5. 若 内容主版本 > 工具名版本 -> 提示"工具可能需要更名/拆分"
仅扫描 name 中含版本号的工具，其余跳过。
"""
import json, re, sys

TOOLS = "data/tools.json"

# 产品族 -> 名称中用于锚定的关键字（小写）
FAMILIES = {
    "GLM": ["glm"],
    "GPT": ["gpt"],
    "Claude": ["claude"],
    "Kimi": ["kimi"],
    "DeepSeek": ["deepseek"],
    "Qwen": ["qwen", "通义千问", "通义"],
    "Gemini": ["gemini"],
    "Llama": ["llama"],
    "Grok": ["grok"],
    "Mistral": ["mistral"],
    "文心": ["ernie", "文心"],
    "混元": ["hunyuan", "混元"],
    "豆包": ["doubao", "豆包"],
    "阶跃": ["step-", "阶跃"],
    "MiniMax": ["minimax"],
    "星火": ["spark", "星火"],
    "Yi": ["yi-"],
    "Phi": ["phi-"],
    "Command": ["command"],
}

VER_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


def parse_ver(s):
    m = VER_RE.search(s)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))


def family_of(name, slug):
    blob = (name + " " + slug).lower()
    for fam, kws in FAMILIES.items():
        for kw in kws:
            if kw in blob:
                return fam
    return None


def versions_in(text, family_kws):
    """返回文本中匹配该产品族的所有版本元组列表"""
    out = []
    low = text.lower()
    for kw in family_kws:
        # 族关键字后紧跟版本号
        for m in re.finditer(re.escape(kw) + r"\s*[-]?\s*(\d+\.\d+(?:\.\d+)?)", low):
            v = parse_ver(m.group(1))
            if v:
                out.append(v)
    return out


def main():
    d = json.load(open(TOOLS, encoding="utf-8"))
    tools = d if isinstance(d, list) else d.get("tools", [])
    drift, rename_hint = [], []
    scanned = 0
    for t in tools:
        name = t.get("name", "") or ""
        slug = t.get("slug", "") or ""
        fam = family_of(name, slug)
        if not fam:
            continue
        # 工具名版本
        name_ver = parse_ver(name) or parse_ver(slug)
        if not name_ver:
            continue
        scanned += 1
        content = t.get("content", "") or ""
        faq = t.get("faq", []) or []
        faq_blob = " ".join((f.get("question", "") + " " + f.get("answer", "")) for f in faq if isinstance(f, dict))
        kw_blob = " ".join(t.get("seo_keywords", []) or [])
        blob = content + "\n" + faq_blob + "\n" + kw_blob

        # H1（内容首行 # 标题）
        h1 = ""
        for line in content.splitlines():
            if line.startswith("# "):
                h1 = line[2:]
                break
        h1_ver = parse_ver(h1) if h1 else None

        # seo 关键词主版本
        kw_ver = None
        for kw in (t.get("seo_keywords", []) or []):
            v = parse_ver(kw)
            if v:
                kw_ver = v
                break

        # 内容中出现的所有版本
        all_vers = versions_in(blob, FAMILIES[fam])
        # 主版本：H1 > seo关键词 > 最高频
        from collections import Counter
        cnt = Counter(all_vers)
        dominant = h1_ver or kw_ver or (cnt.most_common(1)[0][0] if cnt else None)

        if dominant is None:
            continue
        if dominant < name_ver:
            # 内容主版本更旧 -> 陈腐
            drift.append({
                "slug": slug, "name": name, "family": fam,
                "name_ver": ".".join(map(str, name_ver[:2])),
                "content_ver": ".".join(map(str, dominant[:2])),
                "h1": h1[:60],
                "all_versions_in_content": sorted({".".join(map(str, v[:2])) for v in all_vers}),
            })
        elif dominant > name_ver:
            rename_hint.append({
                "slug": slug, "name": name, "family": fam,
                "name_ver": ".".join(map(str, name_ver[:2])),
                "content_ver": ".".join(map(str, dominant[:2])),
            })

    print(f"扫描含版本号的工具: {scanned} 个")
    print(f"\n🔴 版本漂移(内容写旧版) 命中: {len(drift)} 个")
    for x in drift:
        print(f"  - {x['name']} ({x['slug']})  名={x['name_ver']} 内容主版本={x['content_ver']}"
              f"  H1='{x['h1']}'  内容版本集={x['all_versions_in_content']}")
    print(f"\n🟡 内容比名更新(可能需更名) 命中: {len(rename_hint)} 个")
    for x in rename_hint:
        print(f"  - {x['name']} ({x['slug']})  名={x['name_ver']} 内容主版本={x['content_ver']}")
    # 输出 JSON 供后续修复脚本消费
    json.dump({"drift": drift, "rename_hint": rename_hint},
              open("scripts/_version_drift_report.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
