#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全站导航升级：'全部AI工具' 指向 /tools/ 大全页，并新增 '工具分类' 导航项。
对 build.py 未重建的静态页面（404/关于/文章等）做一次幂等替换。"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD = '<a href="/category/" class="gn-item">全部AI工具</a>'
NEW = ('<a href="/tools/" class="gn-item">全部AI工具</a>\n'
       '            <a href="/category/" class="gn-item">工具分类</a>')


def main():
    updated = 0
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs
                   if d not in ('.git', '.playwright-cli', '.cleanup_backup', '.workbuddy', '__pycache__')
                   and '.bak' not in d]
        for fn in files:
            if not fn.endswith('.html'):
                continue
            p = os.path.join(root, fn)
            try:
                with open(p, encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
            if OLD not in content:
                continue
            new_content = content.replace(OLD, NEW)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(new_content)
            updated += 1
            print(f'[nav] {os.path.relpath(p, BASE_DIR)}')
    print(f'nav sweep done: {updated} files updated')


if __name__ == '__main__':
    main()
