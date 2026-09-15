# -*- coding: utf-8 -*-
"""2026-09-15 快讯要点提炼（人工判定，非脚本猜值）

本脚本只做「把 Agent 已定稿的文本写回 JSON」这一件事：
  - 删 005（Anthropic 纳斯达克 = 09-14-007 + 09-14-008 的合并重报，无独立新事实）
  - 002 换源 x.com/Arena → AGI Hunt（可访问，含同事实）
  - 004 换源 x.com/SiliconFlow → 同花顺财经（可访问；并修正主体：Hy4 preview 是腾讯混元模型）
  - 逐条重写 title / summary，新增 commentary，重排 id
category / published_at 一律不动（规则要求）。
"""
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FP = os.path.join(BASE, 'data', 'news_2026-09-15.json')

PATCH = {
    '001': dict(
        title='多家 AI 巨头口头同意放缓开发，引发卡特尔争议',
        summary='Altman、Amodei、Hassabis 与 Musk 周末同意放慢 AI 开发，方案含第三方审计与全球放缓协议；批评者称其为压制开源的卡特尔。',
        commentary='口头承诺相比 Amodei 此前提出的 METR 常驻评估者方案，缺的是可验收的执行条款。卡特尔质疑有现实基础：放缓一旦落地，最受益的是已建成算力的头部实验室，追赶者与开源项目的窗口会被压缩。观察点是第三方审计能否形成具体章程。',
    ),
    '002': dict(
        title='DeepSeek V4.1-Flash 登开源模型榜第 3',
        summary='V4.1-Flash 在 Agent Arena 居开源第 3，净提升 +4.87%，每任务 $0.07，比第 2 名低 68%。',
        commentary='Agent Arena 总榜上它列第 12，相对头部闭源模型的 $4.09 至 $4.54 每任务，成本差 58 倍以上而净提升仍保留 35% 至 54%。在可并行、可重试的长时智能体任务里，性价比比峰值能力更能决定选型。',
        source='AGI Hunt',
        source_url='https://agihunt.info/en/e/1a0a0f734b2bf2effa4f2925670',
    ),
    '003': dict(
        title='Apple 发布 Siri AI，今起英文测试版上线',
        summary='Apple 推出全面重构的 Siri AI，支持个人语境理解、屏幕感知、系统级应用操作与跨设备对话；今日起英文测试版上线，下月扩展至法、日、韩、葡、西五种语言。',
        commentary='从语音助手变成能操作系统的代理，是 Apple 首次把系统级操作权限交给模型。对开发者意味着应用需通过系统级接口暴露可被调用的能力；短板是测试版仅英文，多语言要再等一个月，非英语市场短期无法验证真实体验。',
    ),
    '004': dict(
        title='腾讯混元 Hy4 preview 上架硅基流动，1M 上下文',
        summary='腾讯混元 Hy4 preview 上架硅基流动，为平台第 172 款模型；770B 参数、1M 上下文，缓存/输入/输出 0.3/6/18 元每百万 tokens。',
        commentary='定价与腾讯云 TokenHub 一致，等于同一套权重在厂商云与第三方平台同价可调用。对开发者是渠道变多、不必绑单一云；对聚合平台则是把模型齐全度当竞争点，毛利空间被上游定价锁死。',
        source='同花顺财经',
        source_url='https://stock.10jqka.com.cn/20260912/c679848061.shtml',
    ),
    '006': dict(
        title='RubyGems 恶意 gem 借 YARD 执行任意代码',
        summary='作者复盘被指与 OpenAI 机器人相关的 GemStuffer 恶意 gem：借 .yardopts 的 --load 参数，在安装或生成文档时执行任意代码。',
        commentary='看点在攻击面而非事件规模：恶意代码不写在 gem 源码里，而是寄生在文档工具链的加载参数中，只扫包体源码的审计会漏过。对 Ruby 生态的提醒是把这类会触发本地脚本执行的配置文件纳入依赖审计范围。',
    ),
    '007': dict(
        title='实测 Luna 做代码评审成本仅 Astra 的 3.5%',
        summary='Entelligence 用 50 个基准 PR 对比：Luna 找到 69 个 bug、Astra 92 个，成本 $0.20 对 $5.66，精度 74%/96%。',
        commentary='结论是分层而非替代：低风险 PR 交给 Luna，成本降约 28 倍而 bug 捕获率仍有 75%；架构级改动仍需 Astra，漏掉的 23 个 bug 修复成本通常高于评审差价。可行做法是按改动影响面路由模型。',
    ),
    '008': dict(
        title='Anthropic 重构测试影响分析服务应对 CI 压力',
        summary='Anthropic 工程师每季度交付代码量是 2021 至 2025 年均值的 8 倍，80% 由 Claude 编写，六个月内 CI 任务增长 25 倍。',
        commentary='因果方向值得注意：CI 压力不是测试写得多，而是 AI 让提交量涨了 8 倍，测试选择必须先按变更影响裁剪才有意义。对其他团队的参考是引入编码智能体前先量化 CI 容量与单次提交的测试成本。',
    ),
}
DROP = {'005'}  # 与 09-14-007 / 09-14-008 合并重报，无独立新事实


def main():
    shutil.copy2(FP, FP + '.20260915.bak')
    items = json.load(open(FP, encoding='utf-8'))
    src_ids = [it['id'].split('-')[-1] for it in items]
    print('原始:', src_ids)

    out = []
    for it in items:
        k = it['id'].split('-')[-1]
        if k in DROP:
            print(f'  ⟂ 删除 {it["id"]}（{it["title"]}）')
            continue
        p = PATCH[k]
        for f, v in p.items():
            it[f] = v
        out.append(it)

    today = src_ids[0]
    for i, it in enumerate(out, 1):
        it['id'] = f'20260915-{i:03d}'

    json.dump(out, open(FP, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    # 写后读回校验
    back = json.load(open(FP, encoding='utf-8'))
    assert len(back) == len(out), '条数不一致'
    for a, b in zip(out, back):
        assert a == b, f'读回不一致: {a["id"]}'
        need = ('id', 'title', 'summary', 'commentary', 'category', 'source', 'source_url', 'published_at')
        assert all(k in b and b[k] for k in need if k != 'published_at'), f'{b["id"]} 缺字段'
    print(f'✅ 写回 {len(back)} 条并通过读回校验')
    for it in back:
        print(f'  {it["id"]} [{it["category"]}] T={len(it["title"])} S={len(it["summary"])} '
              f'C={len(it["commentary"])} | {it["title"]}')


if __name__ == '__main__':
    main()
