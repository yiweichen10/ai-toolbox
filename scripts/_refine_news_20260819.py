# -*- coding: utf-8 -*-
"""2026-08-19 快讯要点提炼（一次性脚本）：标题事件化 + 摘要事实浓缩 + x.com 换源。"""
import json, io, sys, shutil, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SRC = 'data/news_2026-08-19.json'
BAK = 'data/news_2026-08-19.json.20260819.bak'

REFINED = {
    '20260819-001': {
        'title': 'Anthropic 公布 Claude 蛋白质设计实验',
        'summary': 'Mythos Preview 与 Opus 4.8 对 15 个靶点设计蛋白质结合剂，成功 14 个，命中率 22.6%-35.1%。',
    },
    '20260819-002': {
        'title': 'Sentence Transformers v6.0 发布',
        'summary': '新增第四种模型类型 MultiVectorEncoder，可加载 PyLate、ColBERT 与 colpali-engine 检查点，支持晚期交互检索。',
    },
    '20260819-003': {
        'title': '卡兹克发布双向钢人论证 Prompt',
        'summary': '源自 Reddit「让 Claude 真正开始思考」帖，含重述问题、强化正反观点、找关键变量、逼出判断 4 个步骤，作者以选司庆日案例演示。',
    },
    '20260819-004': {
        'title': '研究称智能体记忆需按模型能力校准',
        'summary': '评测八款模型：DeepSeek-V3.2 注入完整指南集完成率 +9.5pp；gpt-oss-120b 精选检索 +16.1pp，仅增 5% token。',
    },
    '20260819-005': {
        'title': 'Mojo 语言正式开源',
        'summary': '采用 Apache 2.0 许可证（含 LLVM 例外），编译器与工具链全部源码已上传 GitHub；上周刚发布 1.0，编译器贡献计划年底开放。',
    },
    '20260819-006': {
        'title': 'Google AI 讲解 agent 技能评测方法',
        'summary': '用开源框架 Inspect AI 与 Harbor 评估 agent 技能，再借 Google Sheets 与 Data Studio 做结果可视化分析。',
    },
    '20260819-007': {
        'title': 'Claude 接入 Gmail 与 Google Drive',
        'summary': '可在 Gmail 起草并发送邮件回复、管理 Google Drive 文件，默认发送前需用户批准；连接器菜单开启，全部付费套餐可用。',
        # x.com 源国内不可访问 → 换同事件可访问媒体报道（引用 Anthropic 原文）
        'source': '9to5Google（媒体报道）',
        'source_url': 'https://9to5google.com/2026/08/18/claude-can-now-send-emails-in-gmail-even-without-your-approval',
    },
    '20260819-008': {
        'title': 'OpenAI 放缓前沿模型开发节奏',
        'summary': '因 Hugging Face 事件与 Astra 可能触及《预备框架》关键网络安全阈值，已暂停最新模型强化学习训练两周并搁置最大规模前沿 RL 运行。',
    },
}

if not os.path.exists(BAK):
    shutil.copyfile(SRC, BAK)
    print('备份 →', BAK)

with open(SRC, encoding='utf-8') as f:
    data = json.load(f)

items = data['items'] if isinstance(data, dict) else data
changed = 0
for it in items:
    r = REFINED.get(it.get('id'))
    if not r:
        print('!! 未匹配 id:', it.get('id'))
        continue
    for k, v in r.items():
        it[k] = v
    changed += 1

with open(SRC, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# 写后自校验
with open(SRC, encoding='utf-8') as f:
    chk = json.load(f)
ci = chk['items'] if isinstance(chk, dict) else chk
print('JSON 合法，条数 =', len(ci), '已更新 =', changed)
BAD = ['建议关注', '可关注', '推荐关注', '感兴趣可', '值得一试', '欢迎', '敬请期待']
for x in ci:
    t, s = x['title'], x['summary']
    flags = []
    if len(t) > 30:
        flags.append('TITLE>30(%d)' % len(t))
    if len(s) > 80:
        flags.append('SUM>80(%d)' % len(s))
    if t.rstrip()[-1] in '。！？.!?,，':
        flags.append('TITLE尾标点')
    for b in BAD:
        if b in s:
            flags.append('空话词:' + b)
    if 'x.com' in x.get('source_url', '') or 'twitter.com' in x.get('source_url', ''):
        flags.append('x.com源残留')
    print('%s T%-2d S%-2d %s %s' % (x['id'], len(t), len(s), t, ('<<< ' + ','.join(flags)) if flags else 'OK'))
