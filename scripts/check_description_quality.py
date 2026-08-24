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
TOOLS_FILE = os.path.join(BASE_DIR, "data", "tools.json")

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


def _short_feat(feat):
    """取功能名（去掉括号注释与冒号后细节），≤10 字且不截断英文单词。"""
    s = re.split(r"[（(]", feat)[0].strip()
    s = re.split(r"[:：]", s)[0].strip()          # "Agent 构建：赋能..." → "Agent 构建"
    s = s.strip(" ：:+-、，,。")
    if len(s) > 10:
        cut = s[:10]
        # 英文单词边界保护：若第 11 个字符是英文字母/数字（单词被从中间切断），回退到最近空格
        if len(s) > 10 and (s[10].isascii() and (s[10].isalpha() or s[10].isdigit())):
            sp = cut.rfind(" ")
            if sp > 2:
                return cut[:sp].rstrip(" ：:+-、，,。")
        return cut.rstrip(" ：:+-、，,。")
    return s


def _pick_feats(feats):
    """多轮选功能：优先短功能，跳过含长英文词的功能，避免半截词。"""
    picked = []
    rounds = [(6, 0), (8, 0), (10, 6)]  # (最大字数, 英文长词阈值; 0=不限制)
    for max_len, max_en in rounds:
        if len(picked) >= 2:
            break
        for f in feats:
            s = _short_feat(f)
            if not (2 <= len(s) <= max_len) or s in picked:
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
    f2 = shorts[1] if len(shorts) > 1 else shorts[0]
    slug = tool.get("slug", "")
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
    if "免费" in price:
        tpl = free_tpls[abs(hash(slug)) % len(free_tpls)]
    else:
        tpl = nofree_tpls[abs(hash(slug)) % len(nofree_tpls)]
    pos = tpl.format(label=label, f1=f1, f2=f2)
    # 总长 ≤26 兜底（英文保护：不截断英文单词）
    if len(pos) > 26:
        cut = pos[:26]
        if len(pos) > 26 and (pos[26].isascii() and (pos[26].isalpha() or pos[26].isdigit())):
            sp = cut.rfind(" ")
            if sp > 4:
                return cut[:sp].rstrip(" ：:+-、，,。")
        return cut.rstrip(" ：:+-、，,。")
    return pos


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

    tools = json.load(open(TOOLS_FILE, encoding="utf-8"))
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
            import shutil
            bak = TOOLS_FILE + ".auto-fix.bak"
            shutil.copy2(TOOLS_FILE, bak)
            with open(TOOLS_FILE, encoding="utf-8") as f:
                raw = f.read()
            for slug, pos in fixed:
                needle = f'"slug": "{slug}",'
                if raw.count(needle) != 1:
                    print(f"  !!! {slug} 匹配异常，跳过")
                    continue
                raw = raw.replace(needle, needle + f' "positioning": "{pos}", "auto_positioning": true,', 1)
            with open(TOOLS_FILE, "w", encoding="utf-8") as f:
                f.write(raw)
            json.load(open(TOOLS_FILE, encoding="utf-8"))
            print(f"已写入 {len(fixed)} 个 positioning（备份: {bak}）")
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
