# -*- coding: utf-8 -*-
"""
修复 assets/icons 里「内容格式与扩展名不符」的图标文件：
  - 内容是 ICO（\x00\x00\x01\x00）但扩展名 .png  → 转成真 PNG
  - 内容是 JPG（\xff\xd8\xff）但扩展名 .png       → 转成真 PNG
  - 真 PNG / SVG                                  → 不动

转后所有图标统一为 .svg 或 .png（真 PNG），resolve_icon() 无需改动。
ICO 取最大帧以保清晰度；统一转 RGBA 保留透明。
原文件先备份到 assets/icons/_format_bak/ 再覆盖。
"""
import os
import shutil
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS = os.path.join(BASE_DIR, "assets", "icons")
BAK = os.path.join(ICONS, "_format_bak")
os.makedirs(BAK, exist_ok=True)


def main():
    fixed = skipped = 0
    for f in sorted(os.listdir(ICONS)):
        p = os.path.join(ICONS, f)
        if not f.lower().endswith(".png"):
            continue
        head = open(p, "rb").read(8)
        is_ico = head[:4] == b"\x00\x00\x01\x00"
        is_jpg = head[:3] == b"\xff\xd8\xff"
        if not (is_ico or is_jpg):
            skipped += 1
            continue
        # 备份原文件（按内容类型分子目录，便于回滚）
        sub = os.path.join(BAK, "ico" if is_ico else "jpg")
        os.makedirs(sub, exist_ok=True)
        shutil.copy2(p, os.path.join(sub, f))
        im = Image.open(p)
        if im.format == "ICO":
            frames = []
            try:
                while True:
                    frames.append(im.copy())
                    im.seek(im.tell() + 1)
            except EOFError:
                pass
            if frames:
                im = max(frames, key=lambda x: x.size[0] * x.size[1])
        im = im.convert("RGBA")
        im.save(p, "PNG")
        fixed += 1
        print(f"  修复 {f:28} {('ICO' if is_ico else 'JPG')} -> PNG  ({im.size[0]}x{im.size[1]})")
    print(f"\n修复完成: {fixed} 个转换, {skipped} 个真PNG跳过")
    print(f"原文件备份于: {BAK}")


if __name__ == "__main__":
    main()
