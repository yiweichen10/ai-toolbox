#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用 12 个 agent 生成的 description/content 修正补丁 (patch_01..12.json)
到 data/tools.json。先备份，再逐条应用，输出统计。
"""
import json, os, shutil, glob, datetime

SRC = "data/tools.json"
PATCH_DIR = "scripts/verify_batches"
BAK = f"data/tools.json.{datetime.date.today().strftime('%Y%m%d')}.bak"

def main():
    # 备份
    shutil.copy2(SRC, BAK)
    print(f"已备份 tools.json -> {BAK}")

    d = json.load(open(SRC, encoding="utf-8"))
    tools = d if isinstance(d, list) else d["tools"]
    by = {t["slug"]: t for t in tools}

    applied = 0
    missing = []
    for fn in sorted(glob.glob(os.path.join(PATCH_DIR, "patch_*.json"))):
        try:
            patches = json.load(open(fn, encoding="utf-8"))
        except Exception as e:
            print(f"跳过 {fn}（解析失败）: {e}")
            continue
        for p in patches:
            slug = p.get("slug")
            if slug not in by:
                missing.append(slug)
                continue
            if "description" in p and p["description"]:
                by[slug]["description"] = p["description"]
            if "content" in p and p["content"]:
                by[slug]["content"] = p["content"]
            applied += 1

    json.dump(d, open(SRC, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"已应用补丁: {applied} 条；缺失 slug: {missing if missing else '无'}")
    print("tools.json 已更新（待 build.py 重建 + deploy.sh 部署）")

if __name__ == "__main__":
    main()
