# -*- coding: utf-8 -*-
"""第四轮：给最后 4 个仍低于 1000 字的工具补一句，确保全部进入 1000-1500。"""
import json

PATH = r"C:\Users\27040\WorkBuddy\20260321092139\seo-site\data\tools.json"

add4 = {
    "descript": "它不会替你做所有决定，但能把最枯燥的转录与粗剪，变成几分钟就能收尾的事。",
    "seedance": "真正用熟之后，你会发现它最省心的，是画面和声音不必再分两步去凑。",
    "elevenlabs-dubbing": "先把一条片子跑通，再决定是否把它纳入固定的出海流程，最稳妥。",
    "gen-4-runway": "只要角色和世界观先立住，后续镜头都会自然顺着同一条线生长。",
}

with open(PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

idx = {t.get("slug"): i for i, t in enumerate(data)}
abnormal = []
for slug, add in add4.items():
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

print("四轮后字数异常(应 1000-1500):", abnormal)
for slug in add4:
    print(f"  {slug}: {len(data[idx[slug]]['content'])} 字")
