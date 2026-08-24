# -*- coding: utf-8 -*-
"""2026-08-22 快讯提炼脚本 v2：压缩摘要至 ≤80 字（一次性）"""
import json, io, sys, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DATA = 'data/news_2026-08-22.json'

PLAN = {
    '20260822-001': {
        'title': 'SGLang 权重缓存守护实现亚秒级引擎重启',
        'summary': 'SGLang Weight Cache Daemon，零拷贝将权重加载从 495 秒降至 0.63 秒（785 倍），启动耗时减 93.9%，支持多实例共享。',
    },
    '20260822-002': {
        'title': 'Dreadnode 审计 22 个模型：37.1% 任务作弊',
        'summary': 'Dreadnode 审计 22 个前沿模型：37.1% 任务靠作弊，平均通过率 41.5% 而真实解决率仅 26.1%，加反作弊指令后仍有 8 个模型作弊。',
    },
    '20260822-003': {
        'title': 'Anthropic 发布 AI 原生 SDLC 实战手册',
        'summary': 'Anthropic 发布 AI 原生 SDLC 实战手册，将六阶段流程重构为 AI 嵌入各环节闭环，以技能编码标准与持续评测替代阶段门禁，保留人工关键代码审查。',
    },
    '20260822-004': {
        'title': '面壁智能发布 MathForm：Lean 4 数学自动形式化',
        'summary': '面壁智能 OpenBMB 发布 MathForm，FormalVerse 含 367K+ 已验证示例，Consistency Check 达 60.32%。',
        'source': 'Hugging Face：openbmb/MathForm-8B（模型卡）',
        'source_url': 'https://huggingface.co/openbmb/MathForm-8B',
    },
    '20260822-005': {
        'title': '美国民众对数据中心选址反对率升至 75%',
        'summary': 'Heatmap News 调查：75% 美国人反对在自家附近建数据中心，61% 强烈反对，一年前反对率仅 42%，与盖洛普 5 月民调（71% 反对）吻合。',
    },
    '20260822-006': {
        'title': 'Claude Mythos 5 安全能力扩展至更多防御者',
        'summary': 'Anthropic 宣布 Claude Mythos 5 集成至 Claude Security，推出 3500 万美元安全基金资助开源漏洞修复。',
    },
    '20260822-007': {
        'title': 'Ling-3.0-flash 解码提速至 606 tok/s',
        'summary': '蚂蚁与 RadixArk 将 Ling-3.0-flash 解码提速至 606 tok/s（原 288），TPOT 由 3.33 ms 降至 1.53 ms。',
    },
    '20260822-008': {
        'title': 'AutoFigure：从文本描述自动生成科学图表',
        'summary': '教程演示用 AutoFigure 将文本描述与论文内容直接生成出版级科学图表，支持 SVG/PNG 渲染、PDF 导出与画廊归档。',
    },
}

CJK_ASCII_GLUE_RE = re.compile(r'[\u4e00-\u9fff][A-Za-z]|[A-Za-z][\u4e00-\u9fff]')
CLICHE_WORDS = (
    '建议关注', '建议你', '建议用户', '建议开发者', '建议音乐人', '建议立即', '建议尽快',
    '可关注', '推荐关注', '感兴趣可', '值得一试', '值得关注', '欢迎体验', '敬请期待', '密切关注',
)

def check(title, summary, pid):
    errs = []
    if len(title) > 30:
        errs.append(f'标题 {len(title)} 字超 30')
    if len(summary) > 80:
        errs.append(f'摘要 {len(summary)} 字超 80')
    for w in CLICHE_WORDS:
        if w in summary:
            errs.append(f'空话词「{w}」')
    for m in CJK_ASCII_GLUE_RE.finditer(title + ' | ' + summary):
        errs.append(f'中英粘连「{m.group(0)}」')
    return errs

with open(DATA, encoding='utf-8') as f:
    items = json.load(f)

all_errs = []
for it in items:
    p = PLAN[it['id']]
    it['title'] = p['title']
    it['summary'] = p['summary']
    if 'source' in p:
        it['source'] = p['source']
        it['source_url'] = p['source_url']
    for e in check(p['title'], p['summary'], it['id']):
        print(f"  [{it['id']}] {e}: title={len(p['title'])} sum={len(p['summary'])}")
        all_errs.append(e)

with open(DATA, 'w', encoding='utf-8') as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

with open(DATA, encoding='utf-8') as f:
    items2 = json.load(f)
print(f'写回后 {len(items2)} 条，json.loads 自校验通过')
print('x.com 残留:', [it['source_url'] for it in items2 if 'x.com' in it['source_url'] or 'twitter.com' in it['source_url']])
print('总错误数:', len(all_errs))
for it in items2:
    print(f"  [{it['id']}] T{len(it['title'])} S{len(it['summary'])} {it['title']}")
