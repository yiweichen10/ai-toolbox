# -*- coding: utf-8 -*-
"""第三轮：给仍略低于 1000 字的 8 个工具补一句收尾，使进入 1000-1500 区间。"""
import json

PATH = r"C:\Users\27040\WorkBuddy\20260321092139\seo-site\data\tools.json"

add3 = {
    "descript": "如果你还没用过，挑一段自己的录音试十分钟，体会最直观。",
    "pitch-ai": "对常做对外演示的团队，它值得作为默认工具认真用起来。",
    "seedance": "想上手，从即梦或 Dreamina 里的一次小尝试开始最顺。",
    "krotos-studio": "日常音效这一步，值得让它替你省下反复翻找素材的时间。",
    "deepl-write": "把这道润色关加上，发出去的文字会更稳、也更得体。",
    "notion-ai-meeting": "对 Notion 重度用户，它几乎是顺理成章该补上的那一步。",
    "elevenlabs-dubbing": "出海内容做多语种化时，它可以成为你的常规工序。",
    "gen-4-runway": "对一致性要求高的项目，它值得被放进你的生成流程里。",
}

with open(PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

idx = {t.get("slug"): i for i, t in enumerate(data)}
abnormal = []
for slug, add in add3.items():
    i = idx[slug]
    base = data[i]["content"]
    if not base.rstrip().endswith(("。", "”", "）", '"')):
        base = base.rstrip() + "。"
    data[i]["content"] = base + add
    L = len(data[i]["content"])
    if L < 1000 or L > 1500:
        abnormal.append((slug, L))

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("三轮后字数异常(应 1000-1500):", abnormal)
for slug in add3:
    print(f"  {slug}: {len(data[idx[slug]]['content'])} 字")
