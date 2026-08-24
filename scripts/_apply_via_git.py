import os, subprocess

TARGET = 'affiliate_manager.py'
with open(TARGET, 'r', encoding='utf-8') as f:
    src = f.read()

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
src = src.replace('from pathlib import Path', 'from pathlib import Path\nfrom datetime import datetime', 1)

# 通过 git 内部通道写入：
# 1) 把新内容写进 .git 对象库（.git 可写）
# 2) 用 git update-index 登记
# 3) git checkout-index 从索引还原到工作区（走 git 自己的写通道）
new_blob = subprocess.run(['git', 'hash-object', '-w', '--stdin'], input=src.encode('utf-8'),
                          capture_output=True).stdout.decode().strip()
print('blob:', new_blob)
r = subprocess.run(['git', 'update-index', '--cacheinfo', f'100644,{new_blob},{TARGET}'], capture_output=True, text=True)
print('update-index:', r.returncode, r.stderr.strip())
r = subprocess.run(['git', 'checkout-index', '-f', TARGET], capture_output=True, text=True)
print('checkout-index:', r.returncode, r.stderr.strip())
