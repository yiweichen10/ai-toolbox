#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_affiliate_bak.py — 修复 8899 管理台"保存定位"Permission denied 问题
==========================================================================
背景（2026-08-15）：
    affiliate_manager.py 的 save_positioning_for_site() 在写回 tools.json 前，
    先把原文件复制到固定名备份 tools.json.positioning.bak。
    固定名 = 每次都要"覆盖旧文件"，在部分环境（沙箱/同步盘/文件被占用）下
    抛 PermissionError(13) 中断整个保存动作 —— 管理台报"保存失败"。

修复：
    备份名改为带时间戳的多版本（tools.json.positioning.YYYYMMDD-HHMMSS.bak）：
    每次写新文件，永不撞锁；顺带升级为多版本历史，可回滚任意一天。

用法：
    python scripts/patch_affiliate_bak.py
    运行后重启管理台：python affiliate_manager.py

幂等：已打过补丁会提示跳过，可重复运行。
"""
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(BASE_DIR, "affiliate_manager.py")

# 旧代码块（固定名备份）
OLD_BLOCK = '''    # 备份原文件
    bak = fpath.with_name(fpath.stem + ".json.positioning.bak")
    shutil.copy2(fpath, bak)'''

# 新代码块（时间戳多版本备份）
NEW_BLOCK = '''    # 备份原文件（2026-08-15 改为带时间戳的多版本备份）：
    # 原固定名 tools.json.positioning.bak 每次保存都要"覆盖旧文件"，
    # 在受限环境（沙箱/同步盘/文件被占用）下 Permission denied 直接中断保存；
    # 时间戳名每次写新文件，永不撞锁，且保留多版本历史可回滚任意一天。
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = fpath.with_name(f"{fpath.stem}.json.positioning.{ts}.bak")
    shutil.copy2(fpath, bak)'''

# 需要补的 import（当前文件没有 datetime）
IMPORT_ANCHOR = "from pathlib import Path"
IMPORT_NEW = "from pathlib import Path\nfrom datetime import datetime"


def main():
    print(f"目标文件: {TARGET}")
    if not os.path.exists(TARGET):
        print(f"❌ 文件不存在: {TARGET}")
        sys.exit(1)

    with open(TARGET, "r", encoding="utf-8") as f:
        src = f.read()

    changed = False

    # 1. 备份逻辑替换
    if OLD_BLOCK in src:
        src = src.replace(OLD_BLOCK, NEW_BLOCK)
        print("✅ 备份逻辑已替换为时间戳多版本")
        changed = True
    elif NEW_BLOCK in src:
        print("⏭️  备份逻辑已是新版本，跳过")
    else:
        print("⚠️  未找到旧备份代码块（可能已被手工改过），跳过替换")

    # 2. 补 datetime import
    if "from datetime import datetime" in src:
        print("⏭️  datetime 已导入，跳过")
    elif IMPORT_ANCHOR in src:
        src = src.replace(IMPORT_ANCHOR, IMPORT_NEW, 1)
        print("✅ 已补 datetime 导入")
        changed = True
    else:
        print("⚠️  未找到 import 锚点，需手工补 datetime 导入")

    if not changed:
        print("\n⏹  无改动，退出")
        return

    # 写回（本脚本在用户环境运行，无沙箱限制）
    with open(TARGET, "w", encoding="utf-8", newline="") as f:
        f.write(src)

    # 校验：语法检查 + 确认补丁落盘
    import py_compile
    try:
        py_compile.compile(TARGET, doraise=True)
        print("✅ 语法校验通过")
    except py_compile.PyCompileError as e:
        print(f"❌ 语法校验失败: {e}")
        sys.exit(1)

    with open(TARGET, "r", encoding="utf-8") as f:
        check = f.read()
    if "json.positioning.{ts}.bak" in check and "from datetime import datetime" in check:
        print("\n🎉 补丁完成！")
        print("下一步：重启管理台  python affiliate_manager.py")
        print("验证：保存一次定位 → 应生成 data/tools.json.positioning.<时间戳>.bak 且保存成功")
    else:
        print("\n⚠️  补丁落盘校验未通过，请检查文件")


if __name__ == "__main__":
    main()
