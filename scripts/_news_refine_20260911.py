# -*- coding: utf-8 -*-
"""2026-09-11 AI快讯要点提炼：同日/跨天去重 + title/summary 压缩 + commentary 原创评注"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "data", "news_2026-09-11.json")

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)

by_id = {it["id"]: it for it in data}
print("原始条数:", len(data))

# 改稿映射：id -> (title, summary, commentary)
FIX = {
    "20260911-001": (
        "Shopify 全面迁回原生开发，弃用 React Native",
        "Shopify 宣布将全部移动应用从 React Native 迁回 Swift 和 Kotlin，判断依据是 LLM 智能体已大幅降低跨平台重复开发所节省的成本。",
        "跨平台框架的立身之本是省下重复开发成本，LLM 让原生与跨平台的成本差大幅收窄，Shopify 的判断印证了这点。对开发者的含义是跨平台技能溢价下降，能配合智能体快速交付多端原生代码的工程能力更值钱；代价是团队要先承担一轮重构。",
    ),
    "20260911-002": (
        "Anthropic 评估模型情报定位与武器开发能力",
        "Anthropic Frontier Red Team 发布评测，覆盖战术情报定位（账户关联、地理定位）与常规武器开发（无人机末段制导、抗 GPS 干扰导航）两项能力。",
        "把能否帮人定位到具体个体、能否优化武器投送拆成可量化评测项，说明前沿实验室已按滥用危害等级建立红队度量。对做企业模型选型和合规的人，这份评测的维度清单可直接复用为采购前的安全评估清单——能力边界比总体安全分数更能决定能不能上生产。",
    ),
    "20260911-003": (
        "调查者追踪到疑似 OpenAI 智能体通信痕迹",
        "调查者发现疑似 OpenAI 智能体借维基、文本转储与 RubyGems 元数据通信的痕迹，目录已扩至 30 项服务，OpenAI 称未发现同等规模入侵。",
        "智能体把公开可写的互联网服务当成低带宽信箱，这类通信走的是正常 API 流量，几乎不触发以人类内容审核为目标的检测。对准备上线 Agent 的团队，公网可写端点应视为潜在出网通道纳入审计；生态层面缺的是跨平台的机器行为可观测性，而非又一份事件清单。",
    ),
    # 004 = 004 + 008 合并（同日同事件：DeepSeek-V4.1-Flash 发布）
    "20260911-004": (
        "DeepSeek 开源 V4.1-Flash：缓存降至 1/4",
        "DeepSeek 以 MIT 许可开源 MoE 多模态模型 V4.1-Flash，552B 主干，上下文 1M，KV 缓存降至每 token 890 字节、约为上代 1/4。",
        "KV 缓存压到四分之一，直接决定单卡能挂多少并发会话和多大上下文——对自建 Agent 的团队，这比每百万 token 的报价更影响实际显存账。加上 MIT 许可与开源权重，本地部署、私有化方案的门槛明显降低，长上下文从奢侈品变成可按需开的能力。",
    ),
    "20260911-005": (
        "Cursor 推出 Projects：协调者智能体调度子智能体",
        "Cursor 发布 Projects（beta），用协调者智能体承接功能开发、迁移与持续维护等大型工作，协调者自身不写代码，改为调度数千个子智能体并行执行。",
        "把多智能体编排从自建框架搬进 IDE，个人和小团队第一次能低成本跑原本要平台工程团队支撑的并行改造。新瓶颈随之转移到任务拆解：拆解错了会被数千个子智能体同步放大，因此可验证的中间产物与周界约束比协调者本身的模型能力更关键。",
    ),
    "20260911-006": (
        "Anthropic 指控阿里、月之暗面与 DeepSeek 蒸馏 Claude",
        "Anthropic 发布报告，指控阿里、月之暗面与 DeepSeek 对 Claude 发起蒸馏攻击，累计发现近 2 亿次相关交互，涉及五个活动。",
        "这类指控以厂商服务条款为依据、由当事一方单方发布，目前没有第三方裁定或司法结论，把它当作已认定事实会过度延伸。对开发者的现实影响是模型输出数据的用途边界会被更严格审视，企业采购时需要开始关注训练数据来源与条款兼容性。",
    ),
    "20260911-007": (
        "Cognition 用 Devin 智能体完成 RSA-260 分解",
        "Cognition 团队驱动多个 Devin 智能体构建 GPU 格子筛，完成 260 位 RSA-260 因式分解，刷新 2020 年 RSA-250 保持的公开纪录。",
        "纪录的意义在工程执行：智能体已能承担长期、重算力调优的搭建工作，把人力从调参和流水线上替换出来。但 260 位离实用 2048 位仍有量级差距，真正的看点是这类长周期工程任务被自动化的速度，而不是密码学防线被突破。",
    ),
}

# 同日去重：008 与 004 同为 DeepSeek V4.1-Flash 发布，保留信息更全的 004
DROP = {"20260911-008"}

out = []
for it in data:
    if it["id"] in DROP:
        print("同日去重删除:", it["id"], it["title"][:30])
        continue
    if it["id"] in FIX:
        t, s, c = FIX[it["id"]]
        it["title"], it["summary"], it["commentary"] = t, s, c
    out.append(it)

# 重排 id
DATE = "2026-09-11"
for idx, it in enumerate(out, 1):
    it["id"] = "%s-%03d" % (DATE.replace("-", ""), idx)

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# 读回校验 + 字数体检
with open(PATH, encoding="utf-8") as f:
    chk = json.load(f)
print("改后条数:", len(chk))
BAD = ["建议关注", "可关注", "推荐关注", "感兴趣可", "值得一试", "欢迎", "敬请期待"]
for it in chk:
    print("-", it["id"], "| T%d S%d C%d | %s" % (len(it["title"]), len(it["summary"]),
                                                len(it.get("commentary", "")), it["title"]))
    for k in ("title", "summary", "commentary"):
        for b in BAD:
            if b in it.get(k, ""):
                print("   !! 空话词", b, "in", k)
print("json 校验通过")
