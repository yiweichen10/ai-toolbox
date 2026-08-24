# -*- coding: utf-8 -*-
"""2026-08-21 快讯一次性提炼脚本（备份 + 改写 + 自校验 + 质量检查一体）"""
import json, io, os, re, sys, shutil

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DATA = "data/news_2026-08-21.json"
BAK = DATA + ".20260821.bak"

# 备份
if not os.path.exists(BAK):
    shutil.copy2(DATA, BAK)
    print(f"✅ 已备份 -> {BAK}")
else:
    print(f"⏭️  备份已存在，跳过")

with open(DATA, encoding="utf-8") as f:
    news = json.load(f)

# 改写映射：id -> (title, summary)
REFINE = {
    "20260821-001": (
        "Mistral 推出 Agentic Search 多步检索",
        "Mistral 用 search、open、navigate、read、grep 五工具循环检索，让模型在长文档与多来源中查找、定位并验证信息。",
    ),
    "20260821-002": (
        "阿里发布 Qwen-UI-Agent GUI 智能体",
        "阿里巴巴正式推出 Qwen-UI-Agent，一个以真实世界为中心的 GUI 智能体基座模型，覆盖移动端、电脑端、网页端及深度搜索（DeepSearch）环境。",
    ),
    "20260821-003": (
        "Claude Code 初创公司指南：五大规则与创始人洞见",
        "Anthropic 发布面向初创公司的 Claude Code 指南，基于十余家高增长公司调研，总结“人人皆可交付、自动化繁琐工作、信任但验证”等五大规则。",
    ),
    "20260821-004": (
        "OpenAI 首席财务官称最迟 2027 年上市",
        "OpenAI 首席财务官称最迟 2027 年上市，6 月已秘密提交 IPO；本季度年化营收增长 35%、企业级 50%，AI 编程与办公产品周活 2000 万。",
    ),
    "20260821-005": (
        "AlloyDB ScaNN 扩至 100 亿向量",
        "AlloyDB ScaNN 支持超 100 亿向量，四层树架构查询复杂度从 O(N^1/2) 降至 O(N^1/4)，p95 延迟 51 毫秒、召回率 95%。",
    ),
    "20260821-006": (
        "HF 发布 LFM2.5 DSpark 草稿模型",
        "Hugging Face 发 LFM2.5 DSpark 草稿：投机解码不损质量，GPU 吞吐提升 3.18 倍、端侧 2.87 倍；草稿约 300M 参数。",
    ),
    "20260821-007": (
        "Claude Computer Use 全面可用",
        "Anthropic 宣布 Computer Use、Skills API、Files API 全面可用，新增浏览器操作工具，智能体可操作软件并调用团队技能。",
    ),
    "20260821-008": (
        "Anthropic 发布 Claude Academy",
        "Anthropic 发布 Claude Academy，面向全球数百万用户，课程含 4D AI Fluency Framework 与持续学习项目。",
    ),
}

changed = 0
for n in news:
    rid = n["id"]
    if rid in REFINE:
        t, s = REFINE[rid]
        if n["title"] != t or n["summary"] != s:
            n["title"], n["summary"] = t, s
            changed += 1

with open(DATA, "w", encoding="utf-8") as f:
    json.dump(news, f, ensure_ascii=False, indent=2)

# ===== 自校验 =====
with open(DATA, encoding="utf-8") as f:
    data2 = json.load(f)
assert len(data2) == len(news) == 8, "条数异常"

BAD_WORDS = ["建议关注", "可关注", "推荐关注", "感兴趣可", "值得一试", "欢迎", "敬请期待"]
XCOM = re.compile(r"(x\.com|twitter\.com)", re.I)
STICKY = re.compile(r"[\u4e00-\u9fff][A-Za-z0-9]|[A-Za-z0-9][\u4e00-\u9fff]")

print(f"\n修改 {changed} 条，共 {len(data2)} 条。逐条质量检查：")
ok = True
for i, n in enumerate(data2):
    t, s = n["title"], n["summary"]
    issues = []
    if len(t) > 30:
        issues.append(f"标题超长 {len(t)}")
    if len(s) > 80:
        issues.append(f"摘要超长 {len(s)}")
    if any(w in s for w in BAD_WORDS):
        issues.append("含空话词")
    if XCOM.search(n.get("source_url", "")):
        issues.append("x.com 残留")
    if STICKY.search(s):
        issues.append("中英粘连")
    if not re.search(r"[0-9]|[A-Za-z]{3,}", s):
        issues.append("无具体信息")
    if issues:
        ok = False
        print(f"  ✗ [{i}] {t} -> {', '.join(issues)}")
    else:
        print(f"  ✓ [{i}] title={len(t)}字 summary={len(s)}字 | {t}")

print("\n" + ("✅ 全部通过" if ok else "⚠️ 存在问题需修复"))
