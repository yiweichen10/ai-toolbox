#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定点同步 claude-fable-5 长文/FAQ 中残留的 Fable 5.0 口径事实。

背景: 核实流程只覆盖 description/price 等短字段, content 长文与 faq 仍停在旧版本。
本脚本只做「事实句替换」, 不重写全文, 不增删 H2/区块(避免触发 8/01 长文覆盖事故防护)。
所有替换值均来自 2026-09-02 官方页 anthropic.com/claude/fable 与多源交叉核实。
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_store import load_all_tools, save_tool

SLUG = 'claude-fable-5'
NEW_PRICE = ('API $10/百万输入、$50/百万输出 token；提示缓存读取 $0.25/百万 token'
             '（较 Fable 5 降 75%，官方测算典型负载成本降约 25%、高智能体负载最高降约 45%）；'
             'Claude 应用内含于 Pro $20/月、Max $100/月、Team/Enterprise，不在免费层')

REPL = [
    # H2 与首段：版本 + 发布日期
    ('## Claude Fable 5 是什么？',
     '## Claude Fable 5.1 是什么？'),
    ('Claude Fable 5 是 Anthropic 于 2026 年 6 月发布的旗舰级前沿大语言模型，主打长程智能体推理、复杂编程与知识工作，具备自适应思考与 100 万 token 上下文。',
     'Claude Fable 5.1 是 Anthropic 于 2026 年 9 月 1 日发布的旗舰级前沿大语言模型，接替 6 月 9 日发布的 Fable 5，'
     '主打长程智能体推理、复杂编程与知识工作，具备 100 万 token 上下文与自适应思考（默认开启，可按任务难度调节）。'
     'API 标识为 claude-fable-5-1。'),
    # 核心功能
    ('- 100 万 token 上下文 + 自适应思考',
     '- 100 万 token 上下文（最大输出 12.8 万 token）+ 自适应思考（Fable 5.1 起默认开启）'),
    # 关键数据表
    ('| 价格 | API $10/百万输入、$50/百万输出 token（提示缓存享 90% 输入折扣）；Claude 应用内含于 Pro $20/月、Max $100/月、Team/Enterprise，不在免费层 |',
     '| 当前版本 | Claude Fable 5.1（2026-09-01 发布，接替 2026-06-09 的 Fable 5；API 标识 claude-fable-5-1） |\n'
     '| 价格 | ' + NEW_PRICE + ' |'),
    ('| 上下文 | 100 万 token 上下文 + 自适应思考 |',
     '| 上下文 | 100 万 token 上下文（最大输出 12.8 万 token）+ 自适应思考 |'),
    # 价格与平台段
    ('- **价格**：API $10/百万输入、$50/百万输出 token（提示缓存享 90% 输入折扣）；Claude 应用内含于 Pro $20/月、Max $100/月、Team/Enterprise，不在免费层',
     '- **价格**：' + NEW_PRICE),
    # FAQ
    ('不是。它是 Anthropic 的通用旗舰前沿模型（2026-06-09 发布），面向编程与知识工作，并非小说/故事创作专用工具。',
     '不是。它是 Anthropic 的通用旗舰前沿模型（当前为 Fable 5.1，2026-09-01 发布；初代 Fable 5 于 2026-06-09 发布），'
     '面向编程与知识工作，并非小说/故事创作专用工具。'),
    ('通过 Claude 应用（Pro/Max/Team/Enterprise）或 Claude API（模型名 claude-fable-5），不在免费层。',
     '通过 Claude 应用（Pro/Max/Team/Enterprise）或 Claude API（当前模型名 claude-fable-5-1；'
     '旧版 claude-fable-5 退役不早于 2027-06-09），不在免费层。'),
    ('API $10/百万输入、$50/百万输出 token；Claude 应用内含于订阅，不单独计费。',
     'API $10/百万输入、$50/百万输出 token；提示缓存读取 $0.25/百万 token（较 Fable 5 降 75%）；'
     'Claude 应用内含于订阅，不单独计费。'),
    # 最终结论
    ('Claude Fable 5 是AI对话领域的一款 AI 工具，其核心优势在于前沿级编程与长程推理能力。',
     'Claude Fable 5.1 是AI对话领域的一款 AI 工具，其核心优势在于前沿级编程与长程推理能力。'),
    # 结尾溯源
    ('> 提示：以上数据来源于官方发布与公开评测（已核实）；价格与功能可能调整，请以官方最新信息为准。',
     '> 提示：以上数据来源于官方发布页与公开评测（2026-09-02 核实，含 anthropic.com/claude/fable 官方页）；'
     '价格与功能可能调整，请以官方最新信息为准。'),
]


def main():
    tools = load_all_tools()
    t = next((x for x in tools if x.get('slug') == SLUG), None)
    if not t:
        print('未找到', SLUG); sys.exit(1)
    c = t.get('content', '')
    hit, miss = 0, []
    for old, new in REPL:
        if old in c:
            c = c.replace(old, new, 1)
            hit += 1
        else:
            miss.append(old[:40])
    t['content'] = c

    # 字段同步：name 带当前版本号（与 glm-5-2 一致的版本型页面惯例）
    t['name'] = 'Claude Fable 5.1'
    # verified_price 此前是 Fable 5 口径（缓存 90% 折扣），同步为 5.1 口径
    t['verified_price'] = NEW_PRICE
    # verified_faq 此前回写的是旧文案，同步
    t['verified_faq'] = t.get('faq')
    t['content_flags'] = ('已于 2026-09-02 同步：长文/FAQ 的 Fable 5.0 口径（发布日期、缓存读取价 $1/百万、'
                          '模型名 claude-fable-5）已更新为 5.1 口径，并在文末新增「Claude Fable 版本演进对比」小节')
    t['content_blocked'] = False
    t['updated_date'] = '2026-09-02'
    t['last_verified'] = '2026-09-02'
    t['source_urls'] = [
        'https://www.anthropic.com/claude/fable',
        'https://claudefa.st/blog/models/claude-fable-5-1',
        'https://datanorth.ai/news/anthropic-releases-claude-fable-5-1',
        'https://saassentinel.com/2026/09/02/anthropic-cuts-fable-5-1-cache-costs-by-75-as-new-models-target-agentic-workloads',
        'https://news.qq.com/rain/a/20260902A06ZQW00',
    ]

    save_tool(t)
    print(f'替换命中 {hit}/{len(REPL)}，content {len(c)} 字')
    if miss:
        print('未命中(需人工确认):')
        for m in miss:
            print('  -', m)


if __name__ == '__main__':
    main()
