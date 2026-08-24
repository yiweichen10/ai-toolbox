#!/usr/bin/env python3
"""2026-08-20 AI词典扩库：追加59条新词条（published=false，待每日自动发布）

背景：词库 124 条（116 已发布 + 8 待发布）即将发完，本次基于全网调研
（AIpedia 2026 术语表 / AI.com.tw 200 术语 / 2026 爆火 AI 名词 / 大模型趋势报告等）
交叉验证，按「新技术即新词条」逻辑补齐 2025-2026 新兴概念 + 高频缺失词，共 59 条。

来源文件（3 个 Agent 并行编写，均已校验）：
- data/dict_expansion_A.json（23 条：智能体/工程化 + 训练/推理）
- data/dict_expansion_B.json（18 条：模型架构 + 生成/多模态）
- data/dict_expansion_C.json（18 条：硬件/算力 + 安全/治理 + RAG）

用法：python scripts/add_dict_terms_20260820.py
前置：data/dict_terms.json 已备份（dict_terms.json.20260820.bak）
"""
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_PATH = os.path.join(BASE_DIR, 'data', 'dict_terms.json')

def main():
    # 读取三份扩充数据
    new_terms = []
    for f in ['dict_expansion_A.json', 'dict_expansion_B.json', 'dict_expansion_C.json']:
        path = os.path.join(BASE_DIR, 'data', f)
        with open(path, encoding='utf-8') as fp:
            data = json.load(fp)
        new_terms.extend(data)
        print(f'读取 {f}: {len(data)} 条')

    # 载入现有词库
    with open(DICT_PATH, encoding='utf-8') as fp:
        terms = json.load(fp)
    existing_slugs = {t['slug'] for t in terms}
    print(f'现有词库: {len(terms)} 条')

    # 防冲突
    added = 0
    skipped = 0
    for t in new_terms:
        if t['slug'] in existing_slugs:
            print(f'  [跳过] slug 已存在: {t["slug"]}')
            skipped += 1
            continue
        t['published'] = False
        terms.append(t)
        existing_slugs.add(t['slug'])
        added += 1

    with open(DICT_PATH, 'w', encoding='utf-8') as fp:
        json.dump(terms, fp, ensure_ascii=False, indent=2)

    published = sum(1 for t in terms if t.get('published'))
    pending = len(terms) - published
    print(f'\n✅ 追加完成: 新增 {added} 条, 跳过 {skipped} 条')
    print(f'词库总量: {len(terms)} 条（已发布 {published} / 待发布 {pending}）')

if __name__ == '__main__':
    main()
