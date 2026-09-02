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
import json, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 2026-09-01 去单体化: data/tools.json 单体已于 2026-08-26 退役删除,
# 真源是分片 data/tools/<slug>.json, 统一走 data_store.load_all_tools()
from data_store import load_all_tools

REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_version_drift_report.json")

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


def parse_ver_loose(s):
    """支持整数版本号 (如 'Claude Fable 5' -> (5,0,0)); 仍优先 X.Y"""
    v = parse_ver(s)
    if v:
        return v
    m = re.search(r"(?<![\d.])(\d{1,2})(?![\d.])", s or "")
    return (int(m.group(1)), 0, 0) if m else None


def brand_token_of(name):
    """从工具名取品牌锚定词 = 版本号前那个 token
    'Claude Fable 5' -> 'Fable' | 'GLM-5.2' -> 'GLM' | 'Seedance 2.0' -> 'Seedance'
    """
    s = (name or "").strip()
    m = re.match(r"^(.*?)[\s\-]*(\d+(?:\.\d+)*)\s*$", s)
    if not m:
        return None
    head = m.group(1).strip(" -")
    if not head:
        return None
    return head.split()[-1]


def max_ver_after(text, token):
    """文本中 'token 版本号' 的最大版本 (如 'Fable 5.1')"""
    if not token or not text:
        return None
    best = None
    for m in re.finditer(re.escape(token) + r"[\s\-]*(\d+(?:\.\d+)*)", text, re.I):
        v = parse_ver_loose(m.group(1))
        if v and (best is None or v > best):
            best = v
    return best


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
    tools = load_all_tools()
    drift, rename_hint, desc_drift = [], [], []
    scanned = 0
    for t in tools:
        name = t.get("name", "") or ""
        slug = t.get("slug", "") or ""
        fam = family_of(name, slug)

        # ===== 检查 B (2026-09-01 新增): 描述已升级到新版, content 长文/FAQ 仍是旧版 =====
        # 事故样本: claude-fable-5 —— description 已写 5.1(2026-09-01 发布),
        # content/faq 仍写 "2026 年 6 月发布" 的 5.0 口径。原因是核实流程只覆盖短字段。
        # 此检查不依赖 FAMILIES 词表(用名称自带的品牌锚定词), 覆盖面更广。
        btok = brand_token_of(name)
        c_body = (t.get("content") or "") + "\n" + " ".join(
            ((f.get("q") or "") + " " + (f.get("a") or "")) for f in (t.get("faq") or []) if isinstance(f, dict)
        )
        if btok:
            v_desc = max_ver_after(t.get("description") or "", btok)
            v_body = max_ver_after(c_body, btok)
            if v_desc and v_body and v_desc > v_body:
                desc_drift.append({
                    "slug": slug, "name": name, "brand_token": btok,
                    "desc_ver": ".".join(map(str, v_desc[:2])),
                    "content_ver": ".".join(map(str, v_body[:2])),
                    "last_verified": (t.get("last_verified") or "")[:10],
                })

        if not fam:
            continue
        # 工具名版本
        name_ver = parse_ver(name) or parse_ver(slug)
        if not name_ver:
            continue
        scanned += 1
        content = t.get("content", "") or ""
        faq = t.get("faq", []) or []
        # 2026-09-01 修复: 本站 faq 项是 {"q":..., "a":...} 结构,
        # 旧代码只取 question/answer -> 永远空串, FAQ 版本漂移全面漏检
        faq_blob = " ".join(
            ((f.get("question") or f.get("q") or "") + " " + (f.get("answer") or f.get("a") or ""))
            for f in faq if isinstance(f, dict)
        )
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
    print(f"\n🔴🔴 描述已升级但长文/FAQ 未同步(核实流程只改短字段) 命中: {len(desc_drift)} 个")
    for x in sorted(desc_drift, key=lambda z: z["last_verified"], reverse=True):
        print(f"  - {x['name']} ({x['slug']})  描述={x['desc_ver']} 长文={x['content_ver']}"
              f"  last_verified={x['last_verified']}")
    # 输出 JSON 供后续修复脚本消费
    json.dump({"drift": drift, "rename_hint": rename_hint, "desc_drift": desc_drift},
              open(REPORT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n报告: {REPORT}")


if __name__ == "__main__":
    main()
