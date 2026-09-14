# -*- coding: utf-8 -*-
"""2026-09-14 存量字段缺陷修复（人工判定，非脚本猜测）

背景：上游 aihot 返回 `"category": null`，旧 fetch 直接透传 → 全库 3 条缺分类。
修复原则（用户拍板）：**不用脚本猜值填补**。这 3 条由人读过正文后判定正确分类再写回，
判定依据逐条写在下方 REASONS 里，可审计、可回滚（改前逐文件 .bak）。

  python scripts/_fix_news_category_20260914.py            # 干跑，只打印
  python scripts/_fix_news_category_20260914.py --apply    # 实际写入
"""
import argparse
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT_LABEL = {'models': '模型发布', 'products': '产品发布', 'industry': '行业动态',
             'opinion': '观点', 'paper': '论文研究'}

# 逐条判定依据（读正文后人工定值，非关键词匹配）
JUDGED = {
    'data/news_2026-09-12.json': {
        '20260912-002': ('models',
                         '正文是 V4.1-Flash 的 CED 双塔架构还原与参数量（552B / 激活 8B / 16B），'
                         '属模型本身的信息披露 → 模型发布'),
        '20260912-008': ('products',
                         '正文是 OpenAI 宣布 GPT-Rosalind 结束研究预览、通过 API 与 Codex 向机构'
                         '开放，重点是"开放/可用"而非论文成果 → 产品发布（此前若按"论文"一词判为'
                         'paper 属误判，正是关键词猜测不可靠的反例）'),
    },
    'data/news_2026-09-14.json': {
        '20260914-003': ('industry',
                         '正文是微软 CEO 纳德拉对 AI 审慎发展的公开表态 + 将公布 MAI 模型行为准则'
                         '征求意见，属政策/治理 → 行业动态'),
    },
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='实际写入（默认干跑）')
    args = ap.parse_args()

    total = 0
    for rel, mapping in JUDGED.items():
        fp = os.path.join(BASE, rel)
        items = json.load(open(fp, encoding='utf-8'))
        changed = []
        for it in items:
            want = mapping.get(it.get('id'))
            if not want:
                continue
            cat, why = want
            if it.get('category') == cat:
                print(f'  [跳过] {rel} {it["id"]} 已是 {cat}')
                continue
            changed.append((it['id'], it.get('category'), cat, why))
            it['category'] = cat
            it['category_label'] = CAT_LABEL[cat]
            it['tags'] = [cat]
        if not changed:
            continue
        for _id, _old, _new, why in changed:
            print(f'  [判定] {rel} {_id}: {_old!r} → {_new}\n         依据：{why}')
        if args.apply:
            shutil.copy2(fp, fp + '.bak')
            with open(fp, 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            back = json.load(open(fp, encoding='utf-8'))  # 写后读回校验
            assert back == items, f'读回不一致：{fp}'
            print(f'  ✅ 已写入并读回校验通过：{rel}')
        else:
            print(f'  (干跑未写入：{rel})')
        total += len(changed)
    print(f'共 {total} 条待/已修复')
    return 0


if __name__ == '__main__':
    sys.exit(main())
