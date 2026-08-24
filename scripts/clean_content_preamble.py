#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clean_content_preamble.py — AI 应答前缀一键清理脚本
====================================================
用途：清理 tools.json / articles.json 中混入正文开头的 AI 应答前缀（生成污染）。
与 build.py 的 _check_content_preamble 拦截器配套：拦截器 fail-fast，本脚本负责修复。

用法：
    python scripts/clean_content_preamble.py            # 扫描并清理（先自动备份）
    python scripts/clean_content_preamble.py --dry-run  # 仅预览，不写文件

清理规则：content 以任一 AI 应答前缀开头时，剥掉该句（至首个空行 \n\n），
         并顺带去除紧随其后的 --- 分隔线残留。其余内容原样保留。
"""
import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# 与 build.py 的 _AI_PREAMBLE_PATTERNS 保持一致（改一处须同步改另一处）
AI_PREAMBLE_PATTERNS = [
    r'^好的，没问题',
    r'^好的，我(?:来|会|将|现在|们|就)',
    r'^当然可以',
    r'^这是一篇符合你',
    r'^这是一篇(?:为您|为你)',
    r'^已为您生成',
    r'^为您撰写',
    r'^根据您的要求',
    r'^让我为您',
    r'^我来为你',
    r'^您好，我(?:是|来|为)',
    r'^很高兴(?:为您|为你)',
    r'^没问题，这是',
    r'^请查收',
    r'^以下是我(?:为您|为你)',
    r'^按照您的要求',
    r'^遵照您的(?:要求|指示)',
    r'^应您的要求',
]
PREAMBLE_RE = [re.compile(p) for p in AI_PREAMBLE_PATTERNS]
# 剥前缀：匹配整句至首个空行（\n\n），再单独清残留 ---
SENTENCE_RE = re.compile(r'^.*?\n\n', re.S)
HR_RE = re.compile(r'^\s*---+\s*', re.S)


def backup(path):
    """备份原文件（铁律#3），返回备份路径。"""
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    bak = f'{path}.{ts}.preamble.bak'
    shutil.copy2(path, bak)
    return bak


def clean_content(content):
    """返回 (是否被清理, 清理后的内容)。"""
    for cre in PREAMBLE_RE:
        if cre.match(content):
            m = SENTENCE_RE.match(content)
            new = content[m.end():] if m else content
            new = HR_RE.sub('', new)
            return True, new
    return False, content


def process_file(path, dry_run):
    """处理单个 JSON 文件，返回 (清理数, 备份路径)。"""
    if not os.path.exists(path):
        print(f'  ⚠️ 不存在，跳过: {path}')
        return 0, None
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    items = data if isinstance(data, list) else list(data.values())
    cleaned = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        c = it.get('content')
        if isinstance(c, str) and c:
            ok, new = clean_content(c)
            if ok:
                name = it.get('slug') or it.get('title') or '?'
                status = '已发布' if it.get('published') else '未发布'
                print(f'  [清理] {status} {name}')
                print(f'      旧头部: {c[:46]!r}')
                print(f'      新头部: {new[:46]!r}')
                if not dry_run:
                    it['content'] = new
                cleaned += 1
    if cleaned and not dry_run:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return cleaned, None
    return cleaned, None


def main():
    ap = argparse.ArgumentParser(description='AI 应答前缀一键清理（与 build.py 拦截器配套）')
    ap.add_argument('--dry-run', action='store_true', help='仅预览，不写文件')
    args = ap.parse_args()

    tool_path = os.path.join(DATA_DIR, 'tools.json')
    article_path = os.path.join(DATA_DIR, 'articles.json')

    print('=== 扫描 AI 应答前缀 ===')
    print(f'数据目录: {DATA_DIR}')
    if not args.dry_run:
        for p in (tool_path, article_path):
            if os.path.exists(p):
                bak = backup(p)
                print(f'已备份: {bak}')
    t_clean, _ = process_file(tool_path, args.dry_run)
    a_clean, _ = process_file(article_path, args.dry_run)
    total = t_clean + a_clean
    print(f'\n共清理 {total} 处（tools={t_clean}, articles={a_clean}）')
    if total:
        print('完成。请重新构建验证：python scripts/build.py --target tools')
    else:
        print('无需清理，内容干净。')
    sys.exit(0 if total >= 0 else 1)


if __name__ == '__main__':
    main()
