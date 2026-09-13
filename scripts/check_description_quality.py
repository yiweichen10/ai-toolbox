#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description 首句质量检查 + 自动修复 —— 源头治理"官方复述型"标题。

用法：
  python scripts/check_description_quality.py            # 全量扫描
  python scripts/check_description_quality.py --new-only # 只看近30天新工具
  python scripts/check_description_quality.py --fail     # A类命中即退出码1（构建门禁用）
  python scripts/check_description_quality.py --fix      # 自动生成 positioning 修复标题（不编造，只用真实字段）
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
# 2026-09-13 修：单体 data/tools.json 已于 2026-08-26 退役，本脚本原先直接读单体 →
# 每次运行必 FileNotFoundError（"文档改了、脚本没跟上"的漏网）。改为分片真源 + data_store 写回。
from data_store import load_all_tools, save_tool  # noqa: E402
# 2026-09-13 修：本脚本原文用 abs(hash(slug)) % n 选模板，与 seo_title_helper 里
# 2026-08-29 已修掉的反模式相同——str hash 受 PYTHONHASHSEED 随机化影响，
# 同一 slug 每次进程选中的模板都不同 → 每次运行写回不同 positioning（违反
# AGENTS.md 硬性规则 4「构建必须稳定可复现」）。改用跨进程恒定的 _stable_idx。
from seo_title_helper import _stable_idx  # noqa: E402

# positioning 总长上限（与 seo_title_helper._quality_fix 的 26 字上限一致）
POS_LIMIT = 26

# 单功能退化模板：两功能拼不下时使用，保证语义完整、不切词
SINGLE_FREE_TPLS = [
    "免费{label}：{f1}",
    "免费{label}，{f1}好用吗",
    "{f1}：免费{label}怎么用",
    "免费{label}推荐：{f1}",
]
SINGLE_NOFREE_TPLS = [
    "{label}：{f1}",
    "{label}推荐：{f1}",
    "{f1}，{label}实测",
    "{label}怎么用？{f1}",
]


def _clip(s, n):
    """收缩纯英文片段：只在空格边界收缩，找不到边界就返回空串（绝不切单词）。"""
    s = (s or "").strip()
    if len(s) <= n:
        return s
    if " " not in s:
        return ""
    return s[:n].rsplit(" ", 1)[0].strip().rstrip(" ：:+-、，,。")

ORG_PAT = re.compile(
    r"(推出的|旗下的|开发的|发布的|打造的|开源的|来自|由 .*?(推出|开发|发布|打造))"
)
BENEFIT = re.compile(
    r"(免费|价格|支持|适合|教程|实测|对比|上线|API|新版本|新手|一键|国内|无需|快速|秒|分钟|跨平台|开源权重|本地部署)"
)

CAT_SHORT = {
    "AI编程": "AI编程工具", "AI对话": "AI助手", "AI绘画": "AI绘画", "AI视频": "AI视频工具",
    "AI写作": "AI写作", "AI设计": "AI设计", "AI效率": "AI效率工具", "AI办公": "AI办公工具",
    "AI搜索": "AI搜索", "AI音频": "AI音频工具", "AI翻译": "AI翻译", "AI智能体": "AI智能体平台",
    "AI自动化": "AI自动化工具", "AI检测": "AI检测工具", "AI学习": "AI学习工具",
    "AI提示词": "AI提示词工具", "AI开发": "AI开发工具", "AI行业应用": "AI工具",
}


_SEG_SPLIT = re.compile(r"[：:（(）)、，,/|｜+＋~～;；]")


def _short_feat(feat, limit=10):
    """取功能名：只取「完整片段」，绝不把中文词切成半截（2026-09-13 治本修复）。

    原实现超长一律 s[:10] 硬切，且只保护英文单词边界 → 中文功能名被切成
    "官方直播与线" / "紧" / "需自备" 这类半截词，拼进 positioning 后就是
    语义残缺的标题（实测 95 个工具命中）。
    现在：按分隔符切片段，按原顺序取第一个长度合适的完整片段；
    没有合适片段就返回 None —— 宁可不生成，也不生成半截词。
    """
    s = re.split(r"[（(]", feat)[0].strip()
    s = s.strip(" ：:+-、，,。")
    if not s:
        return None
    segs = [x.strip(" ：:+-、，,。") for x in _SEG_SPLIT.split(s)]
    segs = [x for x in segs if x]
    if not segs:
        return None
    for c in segs:                      # 原顺序优先，保留主功能名的语义权重
        if not re.search(r"[\u4e00-\u9fffA-Za-z]", c):
            continue                    # 纯数字/符号片段（"500"、"12"）不是功能名
        if 2 <= len(c) <= limit:
            return c
    # 无 ≤limit 的完整片段：纯英文片段可按单词边界安全收缩，中文片段直接放弃
    shortest = min(segs, key=len)
    if shortest.isascii():
        clipped = _clip(shortest, limit)
        if 2 <= len(clipped) <= limit:
            return clipped
    return None


def _pick_feats(feats):
    """多轮选功能：优先短功能，跳过含长英文词的功能，避免半截词。"""
    picked = []
    rounds = [(6, 0), (8, 0), (10, 6)]  # (最大字数, 英文长词阈值; 0=不限制)
    for max_len, max_en in rounds:
        if len(picked) >= 2:
            break
        for f in feats:
            s = _short_feat(f)
            if not s or not (2 <= len(s) <= max_len) or s in picked:
                continue
            en_words = re.findall(r"[A-Za-z0-9+/._-]{6,}", s)
            if max_en and any(len(w) > max_en for w in en_words):
                continue
            picked.append(s)
            if len(picked) >= 2:
                break
    return picked


def auto_positioning(tool):
    """从真实字段（category/price/features）生成利益钩子 positioning。
    无可用利益点时返回 None（防编造，标记人工）。"""
    cat = tool.get("category", "")
    price = str(tool.get("price", "") or "")
    feats = [f for f in (tool.get("features") or []) if isinstance(f, str) and f.strip()]
    shorts = _pick_feats(feats)
    if not shorts:
        return None
    label = CAT_SHORT.get(cat, "AI工具")
    f1 = shorts[0]
    f2 = shorts[1] if len(shorts) > 1 else None
    slug = tool.get("slug", "")
    positive = "免费" in price
    # 多句式轮询：避免全站 "免费X：A+B" 单一模板（2026-08-07 模板化风险修复）
    free_tpls = [
        "免费{label}：{f1}+{f2}",
        "免费{label}，{f1}+{f2}好用吗",
        "{f1}+{f2}：免费{label}怎么用",
        "免费{label}推荐：{f1}、{f2}",
    ]
    nofree_tpls = [
        "{label}：{f1}+{f2}",
        "{label}推荐：{f1}、{f2}",
        "{f1}+{f2}，{label}实测",
        "{label}怎么用？{f1}+{f2}",
    ]
    two = free_tpls if positive else nofree_tpls
    one = SINGLE_FREE_TPLS if positive else SINGLE_NOFREE_TPLS
    # 1) 两功能模板：装得下就用（信息量最大）
    if f2:
        tpl = two[_stable_idx(slug, len(two))]
        pos = tpl.format(label=label, f1=f1, f2=f2)
        if len(pos) <= POS_LIMIT:
            return pos
    # 2) 装不下 → 丢掉第二个功能，用单功能模板（绝不切词）
    otpl = one[_stable_idx(slug, len(one))]
    pos = otpl.format(label=label, f1=f1)
    if len(pos) <= POS_LIMIT:
        return pos
    # 3) 兜底：分类话术尾（整词，语义完整）
    fallback = ("免费" if positive else "") + label
    return fallback if len(fallback) <= POS_LIMIT else label


def classify(tool):
    desc = (tool.get("description") or "").strip()
    if not desc:
        return None
    first = re.split(r"[。！？!?\n]", desc)[0].strip()
    if not first:
        return None
    if ORG_PAT.search(first):
        return "A"
    if len(first) >= 8 and not BENEFIT.search(first):
        return "B"
    return None


def main():
    ap = argparse.ArgumentParser(description="description 首句质量检查")
    ap.add_argument("--new-only", action="store_true", help="只看 created_date 近30天的新工具")
    ap.add_argument("--fail", action="store_true", help="A类命中即退出码1（构建门禁）")
    ap.add_argument("--fix", action="store_true", help="自动生成 positioning 修复标题")
    ap.add_argument("--overwrite", action="store_true", help="覆盖已自动生成的 positioning（人工值保留）")
    args = ap.parse_args()

    tools = load_all_tools()
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    a_hits, b_hits = [], []
    fixed, need_manual, skipped_have_pos = [], [], []
    for t in tools:
        created = (t.get("created_date") or "")[:10]
        if args.new_only and (not created or created < cutoff):
            continue
        kind = classify(t)
        if kind == "A":
            a_hits.append((t.get("slug"), (t.get("description") or "").split("。")[0][:45]))
        elif kind == "B":
            b_hits.append((t.get("slug"), (t.get("description") or "").split("。")[0][:45]))
        if args.fix and kind in ("A", "B"):
            if t.get("positioning"):
                if not args.overwrite or not t.get("auto_positioning"):
                    skipped_have_pos.append(t.get("slug"))
                    continue
            pos = auto_positioning(t)
            if pos:
                fixed.append((t.get("slug"), pos))
            else:
                need_manual.append(t.get("slug"))

    scope = "近30天新工具" if args.new_only else "全量"
    print(f"[{scope}] A 组织溯源型: {len(a_hits)} | B 定位复述型: {len(b_hits)}")
    if not args.fix:
        for s, f in a_hits[:20]:
            print(f"  A  {s} | {f}")
        for s, f in b_hits[:10]:
            print(f"  B  {s} | {f}")

    if args.fix:
        print(f"已自动生成 positioning: {len(fixed)} | 已有手动值跳过: {len(skipped_have_pos)} | 缺利益点需人工: {len(need_manual)}")
        if fixed:
            by_slug = {t.get("slug"): t for t in tools}
            written = 0
            for slug, pos in fixed:
                t = by_slug.get(slug)
                if not t:
                    print(f"  !!! {slug} 不在分片真源中，跳过")
                    continue
                t["positioning"] = pos
                t["auto_positioning"] = True
                save_tool(t, indent=2)
                written += 1
            print(f"已写入 {written} 个 positioning（分片真源 data/tools/*.json）")
            # 读回校验：必须能在分片里查回刚写的新值
            back = {x.get("slug"): x for x in load_all_tools()}
            expect = dict(fixed)
            bad = [s for s in expect if (back.get(s) or {}).get("positioning") != expect[s]]
            if bad:
                print(f"  !!! 读回校验失败 {len(bad)} 个: {bad[:5]}")
                sys.exit(1)
            print(f"  [OK] 读回校验通过 {written}/{written}")
            for s, p in fixed[:10]:
                print(f"  {s} -> {p}")
        if need_manual:
            print("需人工补充（无价格/功能信息可提取）:")
            for s in need_manual[:15]:
                print(f"  {s}")

    if args.fail and a_hits:
        print("A类命中 → 退出码1")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
