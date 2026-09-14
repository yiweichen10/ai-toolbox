# -*- coding: utf-8 -*-
"""2026-09-14 快讯要点提炼（一次性脚本，留痕可回滚）

改动：
- 001 标题精简 + summary 事实浓缩
- 002 数字全角逗号修正（2，000 → 2000）
- 003 标题纠正（原文误标 Google CEO，实为微软 CEO 纳德拉）+ x.com 换源网易/IT之家
- 004/005/006/007/008 标题与摘要压缩至规范
- 全部 8 条新增 commentary 原创评注
"""
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FP = os.path.join(BASE, "data", "news_2026-09-14.json")

PATCH = {
    0: dict(
        title="Agent 长任务上下文工程：四类机制对抗溢出与目标丢失",
        summary="Agent harness 层对抗长任务上下文溢出的 4 类机制：预算与卸载、压缩、todo-state 复述、跨会话记忆，覆盖 token 超限与目标漂移。",
        commentary="四类机制的价值是把上下文管理从提示词技巧变成系统工程：预算与卸载决定成本上限，压缩和 todo 复述决定长任务稳定性。做多步 Agent 的团队可对照自查 harness 缺了哪一环。",
    ),
    1: dict(
        title="胡塞组织被指用 Claude Code 开发导弹制导软件",
        summary="Anthropic 9 月威胁报告称，评估关联胡塞组织的也门小组用 Claude Code 开发制导火箭、射程超 2000 公里弹道导弹与 R2000 滑翔载具软件。",
        commentary="把前沿模型用于武器研发已从假设变成案例，且由模型厂商主动披露并归因。能力越强，使用条款与出口管制的执行成本越高，这会成为上市前最受审视的合规风险之一。",
    ),
    2: dict(
        title="微软 CEO 纳德拉支持 AI 审慎发展并公布 MAI 准则",
        summary="微软 CEO 纳德拉发文支持 AI 审慎发展、赞同“独立审计”，将于 9 月 14 日公布自研 MAI 模型《行为准则》并公开征求意见。",
        commentary="这是继 Amodei 提案、Altman 表态后第三家跟进，从个人主张变成大厂承诺，独立审计才有落地可能。纳德拉把“企业自控模型权重”写进方案，实质是替 Azure 生态争取模型中立的位置。",
        source="网易（IT之家）",
        source_url="https://www.163.com/dy/article/L6P5D6S60511B8LM.html",
    ),
    3: dict(
        title="ElevenLabs 发布 Music v2.5 音乐模型",
        summary="ElevenLabs 发布 Music v2.5，应用与 API 同步开放并保留免费档；47885 组盲测中听众多数更偏好 v2.5，R&B、Soul 与 Rock 提升最明显。",
        commentary="音乐生成的竞争点已从能不能唱转向混音与编曲审美，盲测胜出说明评分层面接近人类偏好。免费档保留意味着用音乐获客、用 API 变现，创作者成本不会立刻上升。",
    ),
    4: dict(
        title="Claude Fable 5.1 破解 370 年未解密码",
        summary="Claude Fable 5.1 用 44 分钟、176k tokens 破解 Cyphral Distich——这串 64 个数字的密码自 1899 年起被列为未解问题。",
        commentary="历史密码是检验推理深度的天然考卷：答案唯一、无需监督、无法靠猜。这类成果对厂商是最省钱的宣传，但密码破译与加密破解的边界会被监管反复追问。",
    ),
    5: dict(
        title="AllSpark 开源 Iris 系列搜索智能体",
        summary="AllSpark 开源 Iris-mini（35B）与 Iris-pro（397B）搜索智能体，基于 Qwen3.6 与 Qwen3.5 底座，训练配方公开。",
        commentary="搜索智能体是今年最卷的方向之一，直接公开训练配方说明壁垒正从训练技巧转向数据与环境。对自建检索的团队，35B 档的 mini 版是性价比最高的落点。",
    ),
    6: dict(
        title="FT：Anthropic 预计连续第二季度调整后盈利",
        summary="FT 报道 Anthropic 将连续第二个季度调整后盈利，Q2 营收超 115 亿美元（同比增 14 倍），7 月底 ARR 达 650 亿美元，毛利率超 80%。",
        commentary="上市前最难回答的是烧钱换增长能不能停。Anthropic 用运营利润转正作答，但 2025 年净亏损仍近 420 亿美元，且毛利率口径剔除了模型训练成本与 Amazon 分成——要盯口径而不是数字。",
        source="新浪财经（环球市场播报）",
        source_url="https://finance.sina.com.cn/stock/usstock/c/2026-09-14/doc-inirtwie9750438.shtml",
    ),
    7: dict(
        title="曝 Anthropic 选定纳斯达克，目标估值 2 万亿",
        summary="Business Insider 称，Anthropic 已选定纳斯达克上市，计划 10 月中旬启动路演，目标估值约 2 万亿美元，将超 SpaceX 1.77 万亿美元纪录。",
        commentary="从 9 月 5 日拟 10 月路演到今天选定纳斯达克，上市节奏一周内明显加快。2 万亿估值对应 650 亿美元 ARR 约 30 倍市销率，能否站住取决于企业 API 收入能否继续翻倍。",
    ),
}

items = json.load(open(FP, encoding="utf-8"))
assert len(items) == 8, len(items)
# 先备份原文件（保留采集原始版，脚本可重复执行）
if not os.path.exists(FP + ".bak"):
    shutil.copy2(FP, FP + ".bak")

DATE = "2026-09-14"
for i, it in enumerate(items):
    p = PATCH[i]
    for k, v in p.items():
        it[k] = v
    it["id"] = f"{DATE.replace('-', '')}-{i + 1:03d}"

for it in items:
    print(f"{it['id']} T{len(it['title'])} S{len(it['summary'])} C{len(it['commentary'])} | {it['title']}")

with open(FP, "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

# 读回校验
chk = json.load(open(FP, encoding="utf-8"))
assert len(chk) == 8
assert all(x.get("title") and x.get("summary") and x.get("commentary") for x in chk)
print("OK 写入并读回校验通过:", FP)
