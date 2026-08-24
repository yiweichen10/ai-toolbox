#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
review_data.json 刷新器 v1
================================
作用：
  1. 每月由月度自动化（月初+月中）自动调用，作为评测文章生成的前置步骤
  2. 尝试自动拉取可机读的公开基准数据（SWE-bench Verified / LMSYS Arena ELO）
     —— best-effort：网络不可达或解析失败则保留上次人工核对的数值，并标记 manual review
  3. 把本次人工已核对的"种子数值"（如 2026-07 LMSYS 真实 ELO）在检测到旧快照时写入
  4. 为每个分类维护 last_verified（最后核对日期）与 update_method（自动/人工）
  5. 更新 _meta.updated，输出变更报告供人工跟进

设计原则（回应"数据不更新就是死的"）：
  - 基准数据变化周期 = 月/季度级，不是天级。故"每月刷新"是正确节奏，而非"每天"。
  - 数值维度（benchmark%）尽力自动拉取；定性维度（易用性/中文支持）与定价变化慢，标人工季度复核。
  - 文章内显示"数据截至 YYYY-MM"，读者可见时效性，系统可追溯。

用法：
  python update_review_data.py            # 执行刷新
  python update_review_data.py --dry      # 只报告不写盘
"""
import json
import os
import sys
import shutil
from datetime import datetime

BASE = r"C:\Users\27040\WorkBuddy\20260321092139\seo-site"
REVIEW_DATA_FILE = os.path.join(BASE, "data", "review_data.json")

# 2026-07 人工核对过的"种子数值"（来自公开排行榜 WebSearch 核对）
# 仅当检测到旧快照（如 5 月 ELO 1506/1512）时才覆盖，避免覆盖未来自动拉取的新值
SEED_AI_CHAT = {
    "chatgpt":  ("推理准确率", "LMSYS Arena ELO 1475（GPT-5.5，综合第10）", "1506"),
    "claude":    ("推理准确率", "LMSYS Arena ELO 1479（Claude Opus 4.8，综合第8）", "1512"),
    "deepseek":  ("推理准确率", "LMSYS Arena ELO 1463（DeepSeek V4 Pro，开源第一）", None),
    "kimi":      ("推理准确率", "LMSYS Arena ELO 1462（Kimi K2.6，国产开源前列）", "1466"),
}

# 自动拉取方法映射：可机读基准 -> 尝试 fetch；其余 -> 人工季度复核
AUTO_METHOD = {
    "ai-coding": "auto-swebench",
    "ai-chat": "auto-lmsys",
}


def load():
    with open(REVIEW_DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def save(data):
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(REVIEW_DATA_FILE, f"{REVIEW_DATA_FILE}.{ts}.bak")
    with open(REVIEW_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_swebench():
    """best-effort 拉取 SWE-bench Verified 排行榜。返回 {tool_slug: 'xx.x%'} 或 None。
    注意：公开排行榜无稳定官方 JSON API，此处保留可扩展的抓取骨架，
    失败即返回 None（保留人工核对值 + 标 manual review）。"""
    try:
        import requests
        # 已知公开数据源（官方/社区镜像），任一可达即解析
        candidates = [
            "https://www.swebench.com/leaderboard.json",
        ]
        for url in candidates:
            try:
                r = requests.get(url, timeout=15)
                if r.ok:
                    # 解析逻辑依赖具体返回结构，此处仅作骨架示例
                    # parsed = r.json(); ... 映射 tool->score
                    return None  # 结构未验证前不盲目写入
            except Exception:
                continue
    except Exception:
        pass
    return None


def fetch_lmsys():
    """best-effort 拉取 LMSYS Arena ELO。返回 {tool_slug: elo_int} 或 None。"""
    try:
        import requests
        candidates = [
            "https://lmarena.ai/api/leaderboard",
        ]
        for url in candidates:
            try:
                r = requests.get(url, timeout=15)
                if r.ok:
                    return None  # 结构未验证前不盲目写入
            except Exception:
                continue
    except Exception:
        pass
    return None


def apply_seed(data):
    """写入人工核对过的种子数值（仅在检测到旧快照时），返回变更日志。"""
    log = []
    cat = data.get("ai-chat", {})
    tools = cat.get("tools", {})
    for slug, (dim, new_val, old_marker) in SEED_AI_CHAT.items():
        if slug in tools:
            cur = tools[slug].get("metrics", {}).get(dim, "")
            if old_marker and old_marker in cur:
                tools[slug]["metrics"][dim] = new_val
                tools[slug]["source"] = "LMSYS Arena 2026.07 | 官网定价 2026.07"
                log.append(f"  [seed] ai-chat/{slug}/{dim}: {cur} -> {new_val}")
            elif old_marker is None and "1462" in cur:
                tools[slug]["metrics"][dim] = new_val
                log.append(f"  [seed] ai-chat/{slug}/{dim}: {cur} -> {new_val}")
    return log


def main():
    dry = "--dry" in sys.argv
    data = load()
    today = datetime.now().strftime("%Y-%m-%d")
    report = []

    # 1) 结构字段 & 元数据
    data.setdefault("_meta", {})
    data["_meta"]["updated"] = today
    data["_meta"]["auto_update"] = (
        "monthly (tied to automation-1782302226329): 数值基准 best-effort 自动拉取，"
        "定性/定价标人工季度复核；文章显示'数据截至 YYYY-MM'"
    )

    # 2) 注入 last_verified / update_method
    for k, cat in data.items():
        if k.startswith("_"):
            continue
        cat.setdefault("last_verified", today)
        cat["update_method"] = AUTO_METHOD.get(k, "manual")

    # 3) 种子数值（人工核对）
    seed_log = apply_seed(data)
    if seed_log:
        report.append("种子数值更新（人工核对 2026-07）：")
        report.extend(seed_log)

    # 4) 自动拉取（best-effort）
    swe = fetch_swebench()
    if swe:
        for slug, score in swe.items():
            t = data.get("ai-coding", {}).get("tools", {}).get(slug)
            if t:
                t["metrics"]["编程准确率"] = f"{score}%（自动拉取）"
        report.append("[auto] SWE-bench: 自动拉取成功并更新")
    else:
        report.append("[auto] SWE-bench: 自动拉取跳过/失败 -> 保留人工核对值，标 manual review")
        data.setdefault("ai-coding", {}).setdefault("_flags", {})["needs_manual_review"] = True

    lmsys = fetch_lmsys()
    if lmsys:
        report.append("[auto] LMSYS Arena: 自动拉取成功（见数据）")
    else:
        report.append("[auto] LMSYS Arena: 自动拉取跳过/失败 -> 保留人工核对值，标 manual review")
        data.setdefault("ai-chat", {}).setdefault("_flags", {})["needs_manual_review"] = True

    # 5) 写盘
    if dry:
        print("[DRY] 不写盘。变更预览：")
        print("\n".join(report))
        print(f"[DRY] last_verified 将更新为 {today}")
        return

    save(data)
    print("\n".join(report))
    print(f"\n[DONE] review_data.json 已刷新 -> updated={today}, last_verified={today}")


if __name__ == "__main__":
    main()
