# -*- coding: utf-8 -*-
"""一次性：读 affiliate_manager.py → 内存修改 → 写新文件 → os.replace 原子替换"""
import os

TARGET = 'affiliate_manager.py'
with open(TARGET, 'r', encoding='utf-8') as f:
    src = f.read()

# 1. 备份逻辑替换
OLD = '''    # 备份原文件
    bak = fpath.with_name(fpath.stem + ".json.positioning.bak")
    shutil.copy2(fpath, bak)'''
NEW = '''    # 备份原文件（2026-08-15 改为带时间戳的多版本备份）：
    # 原固定名 tools.json.positioning.bak 每次保存都要"覆盖旧文件"，
    # 在受限环境（沙箱/同步盘/文件被占用）下 Permission denied 直接中断保存；
    # 时间戳名每次写新文件，永不撞锁，且保留多版本历史可回滚任意一天。
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = fpath.with_name(f"{fpath.stem}.json.positioning.{ts}.bak")
    shutil.copy2(fpath, bak)'''
assert src.count(OLD) == 1, f'OLD count={src.count(OLD)}'
src = src.replace(OLD, NEW)

# 2. 补 datetime import
assert 'from datetime import datetime' not in src
src = src.replace('from pathlib import Path', 'from pathlib import Path\nfrom datetime import datetime', 1)

# 3. 写新文件（新文件可写）
tmp = TARGET + '.new'
with open(tmp, 'w', encoding='utf-8', newline='') as f:
    f.write(src)

# 4. 原子替换（git 同款机制）
os.replace(tmp, TARGET)
print('REPLACE OK — 补丁已应用')
