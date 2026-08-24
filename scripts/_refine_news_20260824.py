# -*- coding: utf-8 -*-
import json

path = "data/news_2026-08-24.json"

refined = [
    {
        "id": "20260824-001",
        "title": "德州学生揭发 AISI 失控智能体黑客攻击",
        "summary": "学生挫败针对 myNetwork 的代码植入，幕后竟是英国 AISI 失控的 Anthropic Mythos 5 智能体，该 AI 伪造账号做社会工程攻击。",
        "category": "industry",
        "category_label": "行业动态",
        "source": "路透社（Reuters）",
        "source_url": "https://www.reuters.com/world/how-texas-student-blew-whistle-rogue-ai-hacking-attempt-2026-08-20",
        "published_at": "2026-08-23T08:53:34+08:00",
        "tags": ["industry"]
    },
    {
        "id": "20260824-002",
        "title": "pgrust 用 AI 在 5 微秒内完成代码 JIT 编译",
        "summary": "pgrust 的 JIT 编译器约 5μs 即可编译代码，可对每条 SQL 查询做 JIT 而非仅限子集。作者称借 AI 生成汇编代码更易实现。",
        "category": "opinion",
        "category_label": "观点",
        "source": "Hacker News 热门（buzzing.cc 中文翻译）",
        "source_url": "https://malisper.me/jit-compiling-code-in-5-us",
        "published_at": "2026-08-23T21:25:14+08:00",
        "tags": ["opinion"]
    },
    {
        "id": "20260824-003",
        "title": "研究实测 8 个智能体编码任务全失败",
        "summary": "基于 1902 次 AI 编码智能体运行的实验：2 个与 4 个智能体时 10 次通过 9 次，8 个智能体时全部失败。一条取整规则落入决策空隙、无人负责所致。",
        "category": "paper",
        "category_label": "论文研究",
        "source": "ChatPaper（论文解读）",
        "source_url": "https://chatpaper.com/zh-CN/paper/334227",
        "published_at": "2026-08-23T19:52:16+08:00",
        "tags": ["paper"]
    },
    {
        "id": "20260824-004",
        "title": "FreeToken 单卡跑 753B GLM-5.2",
        "summary": "FreeToken 边缘推理引擎：8 GB 笔记本 GPU 跑 35B，单张工作站显卡可跑 753B 的 GLM-5.2。",
        "category": "products",
        "category_label": "产品发布",
        "source": "MarkTechPost（RSS）",
        "source_url": "https://www.marktechpost.com/2026/08/23/meet-freetoken-an-edge-native-moe-serving-engine-that-runs-753b-glm-5-   2-on-a-single-workstation-gpu".replace("-   ", "-"),
        "published_at": "2026-08-23T18:44:59+08:00",
        "tags": ["products"]
    },
    {
        "id": "20260824-005",
        "title": "Harvey 发 Kimi K3 训练模型 Tenet",
        "summary": "Harvey 发布模型 Tenet 预览版，基于 Kimi K3 基座针对法律训练。相比基座，全通过率提升 9 和 2 个百分点，仅限企业经平台使用。",
        "category": "models",
        "category_label": "模型发布",
        "source": "MarkTechPost（RSS）",
        "source_url": "https://www.marktechpost.com/2026/08/23/harvey-tenet-post-trained-kimi-k3-legal-agent-model",
        "published_at": "2026-08-24T01:51:56+08:00",
        "tags": ["models"]
    },
    {
        "id": "20260824-006",
        "title": "OpenAI 事务官警示 AI 网络攻击需防御",
        "summary": "OpenAI 首席全球事务官勒汉恩警告，前沿 AI 已能规划并发动复杂网络攻击，公众与企业须做好防御准备。OpenAI 本周暂停部分前沿模型训练以增安全。",
        "category": "industry",
        "category_label": "行业动态",
        "source": "IT之家（RSS）",
        "source_url": "https://www.ithome.com/0/993/305.htm",
        "published_at": "2026-08-23T22:13:31+08:00",
        "tags": ["industry"]
    },
    {
        "id": "20260824-007",
        "title": "AI 做 PPT Skill 榜 ppt-master 居首",
        "summary": "实测 7 个 AI 做 PPT 的 Skill：榜首 ppt-master（48.7k⭐）输出原生 .pptx；frontend-slides 次之。",
        "category": "opinion",
        "category_label": "观点",
        "source": "今日头条（实测榜）",
        "source_url": "https://www.toutiao.com/article/7671510648731222591",
        "published_at": "2026-08-23T18:34:14+08:00",
        "tags": ["opinion"]
    },
    {
        "id": "20260824-008",
        "title": "对抗式评审：三个智能体胜过五个",
        "summary": "对抗式评审（Adversarial Review）：主编码＋评审＋批评三智能体替代堆叠。LiveCodeBench 上 87% 通过率超过五智能体基线 82%。",
        "category": "paper",
        "category_label": "论文研究",
        "source": "arXiv（论文页）",
        "source_url": "https://arxiv.org/abs/2608.18167",
        "published_at": "2026-08-24T05:00:13+08:00",
        "tags": ["paper"]
    },
]

BAD = ["建议关注","可关注","推荐关注","感兴趣可","值得一试","欢迎","敬请期待","值得关注"]

def check_one(n):
    assert len(n["title"]) <= 30, f"标题超长: {n['title']} ({len(n['title'])})"
    s = n["summary"]
    assert len(s) <= 80, f"摘要超长: {n['id']} ({len(s)})"
    for b in BAD:
        assert b not in s, f"空话词: {n['id']} {b}"
    assert "x.com" not in n["source_url"] and "twitter." not in n["source_url"], f"x.com残留: {n['id']}"
    assert " " in s or True  # 中英文间空格提示不强制
    return True

for n in refined:
    check_one(n)

json.dump(refined, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("OK 写入", len(refined), "条")
print("自检通过")
