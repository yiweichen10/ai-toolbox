#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''单体退役守卫（2026-08-28 新增）：把「数据真源是分片」这条规则机制化，不靠文档自觉。

背景：2026-08-25 起 load_tools()/load_articles() 改为分片优先；2026-08-26 去单体化彻底删除
data/tools.json 与 data/articles.json（本地与服务器都已清）。但仓库里仍留着几十个历史脚本按
单体路径读写数据：跑它们轻则改动被分片静默覆盖（8/25 踩过的坑），重则把单体重新生成出来，
形成两份真源。本脚本做两件事：
  1) 硬门禁（exit 1）：data/tools.json / data/articles.json 不允许存在；
  2) 软审计（默认只告警）：扫描 scripts/*.py，列出仍以单体为路径的脚本，区分
     可能写单体 与 只读回退/历史一次性脚本。--strict 时把前者也判失败。

用法:
  python scripts/check_mono_retired.py
  python scripts/check_mono_retired.py --strict
退出码: 0 通过 / 1 失败
'''
import argparse
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(BASE, "scripts")
MONO = ["data/tools.json", "data/articles.json"]

REF_RE = re.compile(r'["\'](data[/\\](?:tools|articles)\.json)["\']|["\'](?:tools|articles)\.json["\']')
WRITE_HINT_RE = re.compile(r'(\bopen\([^)]*[\'\"]w[\'\"])|(json\.dump)|(shutil\.move)|(os\.replace)')


def scan_scripts():
    writers, readers, blocked_list = [], [], []
    for name in sorted(os.listdir(SCRIPTS)):
        if not name.endswith('.py') or name == 'check_mono_retired.py':
            continue   # 守卫自身含有拦截块字符串，不能把自己算进去
        try:
            src = io.open(os.path.join(SCRIPTS, name), encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        # 先剔除"单体退役拦截"块本身（它含有单体路径字符串，但不是真引用）
        src = re.sub(r"import os as _os  # 2026-08-28 单体退役拦截.*?# --- 单体退役拦截 end ---\n",
                     "", src, flags=re.S)
        blocked = "单体退役拦截" in io.open(os.path.join(SCRIPTS, name), encoding="utf-8", errors="ignore").read()
        hits = [ln for ln in src.splitlines() if REF_RE.search(ln)]
        if not hits:
            continue
        if blocked:
            blocked_list.append((name, len(hits)))
            continue
        shard_aware = bool(re.search(r'分片优先|shard|data/tools/|data/articles/|load_all_tools|load_all_articles|save_tool|save_article', src))
        maybe_write = any(WRITE_HINT_RE.search(ln) for ln in hits) or re.search(
            r'open\([^)]*(?:TOOLS_JSON|ARTICLES_JSON|TOOLS_JSON_PATH|SRC|P|PATH)[^)]*,\s*[\'\"]w', src)
        rec = (name, len(hits), hits[0].strip()[:90])
        if maybe_write and not shard_aware:
            writers.append(rec)
        else:
            readers.append(rec)
    return writers, readers, blocked_list


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--strict', action='store_true', help='把可能写单体的脚本也判失败')
    args = ap.parse_args()
    fail = False

    print('[mono-check] 1/2 单体文件是否已退役...')
    for rel in MONO:
        if os.path.exists(os.path.join(BASE, rel)):
            print('  [FAIL] %s 又出现了（单体已退役，真源是分片目录）。查是谁写的：改走 '
                  'data_store.save_tool/save_article 后删除该文件' % rel)
            fail = True
        else:
            print('  [OK]   %s 不存在（已退役）' % rel)

    print('[mono-check] 2/2 脚本单体引用审计...')
    writers, readers, blocked = scan_scripts()
    if writers:
        print('  [WARN] %d 个脚本仍以单体为写路径（跑之前必须改成写分片）:' % len(writers))
        for name, n, sample in writers:
            print('    - scripts/%s  (%d 处)  例: %s' % (name, n, sample))
        if args.strict:
            fail = True
    else:
        print('  [OK]   没有『可能写单体』的脚本')
    if blocked:
        print('  [OK]   %d 个一次性历史脚本已加"单体退役拦截"（误跑会显式报错而不是静默改错文件）: %s'
              % (len(blocked), ', '.join(n for n, _ in blocked)))
    if readers:
        print('  [INFO] 另有 %d 个脚本引用单体（只读回退 / 历史一次性脚本，不阻断）: %s%s'
              % (len(readers), ', '.join(n for n, _, _ in readers[:20]), ' ...' if len(readers) > 20 else ''))

    if fail:
        print('[mono-check] 未通过')
        return 1
    print('[mono-check] 通过（数据真源=分片，单体已退役）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
