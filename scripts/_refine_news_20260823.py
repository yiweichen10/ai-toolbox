# -*- coding: utf-8 -*-
import json, os, re, shutil

P = "data/news_2026-08-23.json"
BAK = P + ".20260823.bak"
shutil.copy2(P, BAK)

d = json.load(open(P, encoding="utf-8"))

# 跨天去重：删除与 08-22 同事件的 [007] 蚂蚁百灵 Weight Cache Daemon（08-22 已覆盖同 lmsys 源）
# 其余 7 条无同日/跨天重复，全部保留，仅提炼 + 充实硬数字。

# 逐条提炼（title 事件化≤30字；summary 事实浓缩≤80字含硬数字）
refined = {
    "20260823-001": {
        "title": "第二届世界人形机器人运动会开幕",
        "summary": "第二届世界人形机器人运动会开幕，666 支队伍、2056 台机器人参赛，队伍数较首届增 138%，天工 Ultra 百米 9.39 秒破博尔特纪录。",
    },
    "20260823-002": {
        "title": "llm 0.33 发布",
        "summary": "llm 0.33 发布，升级 OpenAI 库至 3.x，HTTP 客户端由 httpx 换为 httpx2，embed 新增 --key 参数支持多密钥。",
    },
    "20260823-003": {
        "title": "自建全自主托管代理软件工厂",
        "summary": "作者用一条提示词让 AI 智能体自主完成建库、测试到部署上线，环境基于 Coolify 自托管沙箱隔离，唯一成本每月 £20 Codex 订阅。",
    },
    "20260823-004": {
        "title": "研究揭示 AI 智能体为何受益技能",
        "summary": "普林斯顿与 UCSD 经 8135 次测试发现，技能靠程序性引导提升智能体表现，约 65.7% 案例奏效。",
    },
    "20260823-005": {
        "title": "神秘 Ox Alpha 模型限免上架",
        "summary": "OpenRouter 上线匿名模型 Ox Alpha 免费 1 周，DeepSWE 得分约 80% 超 Claude Fable 5 的 65%，线索指向智谱。",
    },
    "20260823-006": {
        "title": "前沿 AI 实验室未公布失控遏制方案",
        "summary": "Guidelight 研究显示五大前沿实验室大多未公开失控模型遏制计划，OpenAI 评分最高，Anthropic 与 Meta 最低。",
    },
    "20260823-008": {
        "title": "别再开发 TUI 了",
        "summary": "作者用 Claude 等模型构建原生 Mac 应用，几乎不手写 UI，靠提示词生成 SwiftUI 并嵌入 LLM 智能体，认为终端界面已无必要。",
    },
}

# 删除 007（跨天重复）
d = [it for it in d if it["id"] != "20260823-007"]

# 应用提炼 + 重排 id
out = []
for i, it in enumerate(d, 1):
    rid = f"20260823-{i:03d}"
    r = refined.get(it["id"], {})
    it["id"] = rid
    if "title" in r: it["title"] = r["title"]
    if "summary" in r: it["summary"] = r["summary"]
    out.append(it)

# 校验
EMPTY = ["建议关注", "可关注", "推荐关注", "感兴趣可", "值得一试", "欢迎", "敬请期待"]
xc = re.compile(r"[a-zA-Z0-9]+[\u4e00-\u9fff]|[\u4e00-\u9fff]+[a-zA-Z0-9]+")
for it in out:
    t, s = it["title"], it["summary"]
    assert len(t) <= 30, f"title too long ({len(t)}): {t}"
    assert len(s) <= 80, f"summary too long ({len(s)}): {s}"
    assert not any(w in s for w in EMPTY), f"empty-word in summary: {s}"
    assert "x.com" not in it["source_url"] and "twitter.com" not in it["source_url"], f"x.com remains: {it['source_url']}"
    # 粘连检查（数字+汉字 或 汉字+字母数字相邻视为粘连，排除正常"数字+单位"如 倍/秒/%/token）
    bad = xc.findall(s)
    # 允许带单位的数字写法，简单报粘连供人工看
    print(f"[{it['id']}] title={len(t)} summary={len(s)} 粘连候选={bad}")

json.dump(out, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
json.loads(open(P, encoding="utf-8").read())
print(f"\nOK: {len(out)} 条，已写回 {P}，备份 {BAK}")
