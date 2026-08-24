# -*- coding: utf-8 -*-
"""TTS 朗读起点门禁（2026-08-17）。

事故：文章页正文上方"本文提到的工具/相关工具"卡被 TTS 读进朗读（从"🔧 本文提到的工具"开始）。
根因：推荐卡位于 <article data-tts> 容器内，tts-reader.js 的跳过名单未覆盖。
修复：js/tts-reader.js 跳过 .related-tools；build.py 给推荐卡加 tts-skip 显式标记。
本门禁保证两类修复都不回退：JS 规则存在 + 所有 data-tts 容器内的推荐卡都带 tts-skip。
"""

import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIRS = ('articles', 'tools', 'compare', 'ranking', 'quiz', 'dict', 'news', 'live')
FAIL = 0


def rel(p):
    return os.path.relpath(p, BASE)


# 1) JS 侧必须保留 .related-tools 跳过规则
js_path = os.path.join(BASE, 'js', 'tts-reader.js')
try:
    js = open(js_path, encoding='utf-8').read()
    if ".related-tools" not in js or "tts-skip" not in js:
        print(f'[FAIL] {rel(js_path)} 缺少 .related-tools / tts-skip 跳过规则')
        FAIL += 1
except OSError as e:
    print(f'[FAIL] 无法读取 {rel(js_path)}: {e}')
    FAIL += 1

# 2) 构建产物里，data-tts 容器内的 related-tools / article-top-tools 必须带 tts-skip
ARTICLE_PAT = re.compile(r'<article[^>]*data-tts[^>]*>(.*?)</article>', re.S)
CLS_PAT = re.compile(r'<div class="([^"]*related-tools[^"]*)"[^>]*>')

scanned = 0
for root, _dirs, files in os.walk(BASE):
    if root == BASE or os.path.dirname(root) == BASE:
        if not any(os.path.basename(root) == d for d in OUTPUT_DIRS):
            continue
    if '\\_' in root or '/_' in root:
        continue
    for fn in files:
        if not fn.endswith('.html'):
            continue
        p = os.path.join(root, fn)
        try:
            h = open(p, encoding='utf-8').read()
        except (OSError, UnicodeDecodeError):
            continue
        if 'data-tts' not in h:
            continue
        scanned += 1
        for m in ARTICLE_PAT.finditer(h):
            inner = m.group(1)
            for cm in CLS_PAT.finditer(inner):
                cls = cm.group(1)
                if 'tts-skip' not in cls:
                    print(f'[FAIL] {rel(p)}: data-tts 内 <div class="{cls}"> 缺 tts-skip')
                    FAIL += 1

if FAIL:
    print(f'\n结果: {FAIL} 项失败（扫描 {scanned} 个 data-tts 页面）')
    sys.exit(1)
print(f'\n结果: 通过（扫描 {scanned} 个 data-tts 页面，JS 规则与 tts-skip 均就位）')
