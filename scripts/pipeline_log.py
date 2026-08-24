#!/usr/bin/env python3
"""pipeline_log.py — 流水线状态写入工具
自动化任务跑完后调用，写入今日流水线状态到 data/_pipeline.json，
然后 gen_cms.py 生成的 cms.html 就能看到实时状态。

用法:
  python scripts/pipeline_log.py <task_id> ok "标题" "详情"
  python scripts/pipeline_log.py <task_id> error "标题" "错误信息"

task_id:
  seo_article    — SEO 文章生成
  dict_release   — AI 词典发布
  ai_news        — AI 快讯采集
  tool_release   — 工具发布
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE_FILE = os.path.join(BASE_DIR, 'data', '_pipeline.json')

TASK_NAMES = {
    'seo_article': 'SEO 文章',
    'dict_release': 'AI 词典',
    'ai_news': 'AI 快讯',
    'tool_release': '工具发布',
}


def main():
    if len(sys.argv) < 3:
        print('用法: python scripts/pipeline_log.py <task_id> <ok|error> [title] [detail]')
        print(f'可用 task_id: {", ".join(TASK_NAMES.keys())}')
        sys.exit(1)

    task_id = sys.argv[1]
    status = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else ''
    detail = sys.argv[4] if len(sys.argv) > 4 else ''

    if task_id not in TASK_NAMES:
        print(f'[ERROR] 未知 task_id: {task_id}')
        print(f'可用: {", ".join(TASK_NAMES.keys())}')
        sys.exit(1)

    if status not in ('ok', 'error', 'running'):
        print(f'[ERROR] 未知状态: {status} (可用: ok, error, running)')
        sys.exit(1)

    today = datetime.now(CST).strftime('%Y-%m-%d')
    now = datetime.now(CST).strftime('%H:%M')

    # 读或初始化
    try:
        with open(PIPELINE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"today": today, "refreshed_at": "", "tasks": []}

    # 如果日期不对，重置
    if data.get('today') != today:
        data = {
            "today": today,
            "refreshed_at": datetime.now(CST).isoformat(),
            "tasks": [
                {"time": "--:--", "task_id": tid, "task_name": tname, "status": "pending", "title": "", "detail": ""}
                for tid, tname in TASK_NAMES.items()
            ]
        }

    # 确保所有 4 个 task 存在
    existing_ids = {t['task_id'] for t in data.get('tasks', [])}
    for tid, tname in TASK_NAMES.items():
        if tid not in existing_ids:
            data['tasks'].append({
                "time": "--:--", "task_id": tid, "task_name": tname,
                "status": "pending", "title": "", "detail": ""
            })

    # 更新目标 task
    for task in data['tasks']:
        if task['task_id'] == task_id:
            task['time'] = now
            task['status'] = status
            task['title'] = title
            task['detail'] = detail
            break

    data['refreshed_at'] = datetime.now(CST).isoformat()

    with open(PIPELINE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    emoji = '✅' if status == 'ok' else ('❌' if status == 'error' else '⚡')
    print(f'{emoji} 流水线记录: [{now}] {TASK_NAMES[task_id]} → {status.upper()}' + (f' ({title})' if title else ''))


if __name__ == '__main__':
    main()
