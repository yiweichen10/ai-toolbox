# -*- coding: utf-8 -*-
"""2026-09-12 AI 快讯要点提炼（Agent 亲自执行，一次性脚本）"""
import io, json, os, sys

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FP = os.path.join(BASE, 'data', 'news_2026-09-12.json')

ITEMS = [
    {
        "title": "DeepSeek V4.1-Flash 缓存输入降价 7 倍",
        "summary": "实测显示 V4.1-Flash 缓存命中输入价格降至约 1/7、输出降约 2/3；9 月 14 日 12 时起，发往 v4-pro 的请求将强制路由至该模型并按新价计费。",
        "commentary": "最实际的变化是成本结构：账单里缓存命中往往占大头，降一个数量级意味着长会话、多轮 Agent 能直接跑而不用精打细算。强制路由则意味着 9 月 14 日后仍按老模型参数写的调用会静默换模型，做稳定性评估的团队需提前重测输出一致性。",
        "source": "公众号：卡尔的AI沃茨",
        "source_url": "https://mp.weixin.qq.com/s?__biz=Mzg3MTk3NzYzNw%3D%3D&mid=2247511119&idx=1&sn=0f53b5017e41b16afc9b201966ce2bda",
    },
    {
        "title": "DeepSeek V4.1-Flash 架构曝光",
        "summary": "第三方架构还原显示，V4.1-Flash 采用 20 层因果编码器加 20 层解码器的 CED 双塔：总参数量 552B，读长文本仅激活约 8B，生成阶段激活 16B。",
        "commentary": "CED 双塔把读写拆成两套激活路径，读长文档只花 8B 算力，这是长上下文成本能压下来的结构性原因，而不是靠 KV 缓存省一点显存。做私有化部署时，文档问答与批量生成可共用一份权重、跑出两条成本曲线，容量规划比只看总参数量靠谱。",
        "source": "X：阿易 AI Notes (@AYi_AInotes)",
        "source_url": "https://x.com/AYi_AInotes/status/2098544573077184826",
    },
    {
        "title": "月之暗面瞄准年底 20 亿美元年化营收",
        "summary": "据 Bloomberg 报道，月之暗面目标年底年化营收达 20 亿美元，为 8 月运行率的两倍，主要受益于今夏发布的 K3 模型。",
        "commentary": "年化 20 亿美元放在国内大模型公司里属头部位置，且一个季度翻倍，说明 K3 的付费转化在真实发生。如果增长主要来自 API 与订阅而非一次性定制合同，这类收入的可预测性明显更高，也会直接影响它在下一轮融资里的议价空间。",
        "source": "TechCrunch：AI（RSS）",
        "source_url": "https://techcrunch.com/2026/09/11/kimi-maker-moonshot-ai-targets-2-billion-in-annual-revenue",
    },
    {
        "title": "多伦多大学演示可自主扩散的 LLM 蠕虫",
        "summary": "多伦多大学预印本演示 LLM 蠕虫：借用被感染主机的 GPU 跑本地模型，自主发现漏洞并跨主机扩散，无需外部 C&C，在混合测试网中自主运行 7 天。",
        "commentary": "关键不是蠕虫本身，而是推理算力来自受害者自己的显卡，攻击者边际成本接近零，也没有可封堵的控制服务器。当前实现比传统蠕虫慢、日志噪音大，容易被行为监控抓到；但防御思路已经变了：补丁管理挡不住会自己挑漏洞的代码，微隔离加主机级异常检测才起作用。",
        "source": "World Cyber News",
        "source_url": "https://www.worldcybernews.com/articles/1008",
    },
    {
        "title": "蚂蚁开源 Ling-3.0-flash-VL 多模态模型",
        "summary": "蚂蚁百灵开源首个原生多模态模型 Ling-3.0-flash-VL：总参 124B、单次推理激活 5.5B、上下文 256K，原生支持图像/文本/视频输入，采用 MIT 许可。",
        "commentary": "视觉反馈闭环是这条发布里最值得看的点：模型把一次性生成改成观察、行动、验证、修正的循环，生成网页时能对照渲染结果自己改代码。引用分数要留意版本：官方引的是 AA v4.1.1 口径的 42 分，AA 现行榜单只给 25 分。",
        "source": "腾讯新闻（IT时代网）",
        "source_url": "https://new.qq.com/rain/a/20260909A05BS900",
    },
    {
        "title": "OpenAI 开放 Agents API 公测",
        "summary": "OpenAI 开放 Agents API 公测：以 Codex harness 托管云端 Agent，编排与上下文由 OpenAI 承担，沙箱可自带或接 E2B 等 9 家。",
        "commentary": "把 Codex 内部的编排层做成公开 API，等于把长跑 Agent 不崩这件最耗工程的活外包出去。代价是编排层锁在 OpenAI 的版本节奏上：想做多模型路由的团队，更该拿走 GitHub 上的开源 harness。",
        "source": "OpenAI：官网",
        "source_url": "https://openai.com/index/introducing-the-agents-api/",
    },
    {
        "title": "GPT Image 2.5 双版本包揽图像榜前二",
        "summary": "GPT Image 2.5 双版本包揽图像榜前二：Flare 生成中位耗时由 142.9 秒降至 52.7 秒，价格维持每百万输出 token 30 美元。",
        "commentary": "速度比画质更能改变用法：单图从 142.9 秒压到 52.7 秒，设计师才可能把出图放进即时迭代的循环。风险在榜单样本，前两名票数只有 3000 上下，远少于 GPT Image 2 的近 8 万，排名还需时间沉淀。",
        "source": "HuggingNews",
        "source_url": "https://huggingnews.com/ai/openai-gpt-image-25-takes-top-2-arena-spots-and-cuts-generation-time-63p-41329de6",
    },
    {
        "title": "GPT-Rosalind 结束研究预览向机构开放",
        "summary": "OpenAI 宣布 GPT-Rosalind 结束研究预览，通过 API 与 Codex 向审核通过的全球机构开放，可跨论文与实验数据推理、权衡靶点证据并规划实验。",
        "commentary": "从受控研究预览转为面向机构开放，说明 OpenAI 对生物双用途风险的审核流程已经跑通，用组织身份与安全合规做门槛，而不是一刀切禁掉。对国内团队实际影响有限：开放仍是审核制，能立刻用上的还是 Codex 里那套生命科学插件与公开数据库连接。",
        "source": "AGI Hunt",
        "source_url": "https://agihunt.info/en/p/1a0922d9c7844e62607e45c8eb3",
    },
]

CLICHE = ['建议关注', '可关注', '推荐关注', '感兴趣可', '值得一试', '欢迎', '敬请期待']

old = json.load(open(FP, encoding='utf-8'))
assert len(old) == len(ITEMS), f'条数不匹配 {len(old)} vs {len(ITEMS)}'

out = []
for i, (o, n) in enumerate(zip(old, ITEMS)):
    it = dict(o)
    it['id'] = f"20260912-{i+1:03d}"
    it['title'] = n['title']
    it['summary'] = n['summary']
    it['commentary'] = n['commentary']
    it['source'] = n['source']
    it['source_url'] = n['source_url']
    out.append(it)
    assert not it['title'].rstrip().endswith(('。', '.', '！', '!', '？', '?', '，', ',')), f'title 尾标点 {i}'
    for f, lo, hi in (('summary', 20, 90), ('commentary', 60, 120)):
        L = len(it[f])
        flag = '' if lo <= L <= hi else '  <<< 超限'
        print(f'  {it["id"]} {f}={L} title={len(it["title"])}{flag}')
    for w in CLICHE:
        assert w not in it['summary'] and w not in it['commentary'], f'空话词 {w} @{i}'
    # 002 为 x.com 源且无同事件可访问替代源，按规则保留
    assert 'x.com' not in it['source_url'] or i == 1, f'x.com 残留 @{i}'

json.dump(out, open(FP, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'OK 写回 {len(out)} 条 → {FP}')

# 读回自校验
chk = json.load(open(FP, encoding='utf-8'))
assert len(chk) == len(ITEMS)
assert all(k in chk[0] for k in ('id', 'title', 'summary', 'commentary', 'category', 'source', 'source_url', 'published_at'))
print('读回校验通过')
