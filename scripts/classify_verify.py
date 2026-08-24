# -*- coding: utf-8 -*-
"""
分类审计核实辅助：把 classify_audit 的嫌疑池 + 每条工具的完整 description 导出，
供人工逐条判定「改 / 不改 / 待定」。
输出：data/classify_verify_YYYY-MM-DD.txt
"""
import json, os, datetime

BASE = os.path.join(os.path.dirname(__file__), '..', 'data')
AUDIT = os.path.join(BASE, f"classify_audit_{datetime.date.today().isoformat()}.json")
TOOLS = os.path.join(BASE, 'tools.json')

def main():
    with open(AUDIT, encoding='utf-8') as f:
        audit = json.load(f)
    with open(TOOLS, encoding='utf-8') as f:
        tools = {t['name']: t for t in json.load(f)}

    lines = []
    lines.append(f'# 分类审计核实视图  {audit["generated"]}  共 {audit["suspect_count"]} 条嫌疑')
    lines.append(f'# 格式: [序号] 置信 | 现类目 → 推断类目 | 工具名')
    lines.append(f'#         desc: 描述(截断160字)')
    lines.append('=' * 72)

    for i, s in enumerate(audit['suspects'], 1):
        t = tools.get(s['name'], {})
        desc = (t.get('description', '') or '')[:160]
        lines.append(f'[{i:3d}] {s["confidence"]:11s} | {s["current"]} → {s["inferred"]} | {s["name"]}')
        lines.append(f'      desc: {desc}')
        lines.append(f'      理由: {s["reason"]}')
        lines.append('')

    out = os.path.join(BASE, f"classify_verify_{datetime.date.today().isoformat()}.txt")
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'已导出核实视图: {out}  ({len(audit["suspects"])} 条)')

if __name__ == '__main__':
    main()
