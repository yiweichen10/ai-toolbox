#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_ads_injected.py — 部署前守卫：校验内容页都含广告加载器

背景（2026-08-13）：广告加载器是构建后由 inject_ads.py 注入的，不在模板里。
任何"只跑 build.py 没跑 inject_ads.py"的流程都会产出无广告页面；一旦直接上传，
线上文章/资讯页就全部丢广告。本脚本在 deploy.sh 的 inject 步骤后运行，
发现内容页缺 loader 即以非 0 退出码阻止部署（set -e 中断）。

性能设计（2026-08-13）：注入丢失是"系统性问题"（要么整体注入、要么整体丢失，
或编码崩溃导致大片缺失），不是单个页面问题。因此默认用**确定性抽样**：
每个目录取 首/中/尾 + 固定种子随机 2 个，全站只读几十个文件（毫秒级），
1.3 万页规模也零负担。需要全量深查时加 --full（当前 1033 页约 1.3 秒）。

用法：python scripts/check_ads_injected.py [--full]
退出码：0=全部通过，1=存在缺注入的页面（禁止部署）
"""
import os
import sys
import glob
import random

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 与 inject_ads.py 的 ALLOWED_TOP 保持一致
CONTENT_DIRS = ('tools', 'articles', 'category', 'compare', 'alternatives',
                'ranking', 'quiz', 'live', 'dict', 'news')
SAMPLE_PER_DIR = 5


def main():
    full = '--full' in sys.argv[1:]
    pages = []
    for d in CONTENT_DIRS:
        pages.extend(glob.glob(os.path.join(BASE, d, '**', 'index.html'), recursive=True))

    # 抽样：每目录 首/中/尾 + 固定种子随机，保证可复现且覆盖系统性缺失
    if not full:
        by_dir = {}
        for p in pages:
            rel = os.path.relpath(p, BASE)
            top = rel.split(os.sep)[0]
            by_dir.setdefault(top, []).append(p)
        picked = []
        rng = random.Random(20260813)
        for d, fs in sorted(by_dir.items()):
            fs.sort()
            idxs = {0, len(fs) - 1, len(fs) // 2}
            while len(idxs) < min(SAMPLE_PER_DIR, len(fs)):
                idxs.add(rng.randrange(len(fs)))
            picked.extend(fs[i] for i in sorted(idxs))
        pages = picked

    missing = []
    for p in pages:
        try:
            html = open(p, encoding='utf-8').read()
        except Exception as e:
            missing.append((p, '读取失败: %s' % e))
            continue
        if '/ads/loader.js' not in html:
            missing.append((p, '缺少 loader'))
    mode = '全量' if full else '抽样'
    print('校验（%s）%d 个内容页...' % (mode, len(pages)))
    if missing:
        for p, why in missing[:10]:
            print('  ❌ %s (%s)' % (os.path.relpath(p, BASE), why))
        print('共 %d 页缺少广告加载器，禁止部署' % len(missing))
        sys.exit(1)
    if not full:
        print('✅ 抽样校验通过（%d 页全部含 loader；全量深查用 --full）' % len(pages))
    else:
        print('✅ 全量校验通过（%d 页全部含 loader）' % len(pages))
    sys.exit(0)


if __name__ == '__main__':
    main()
