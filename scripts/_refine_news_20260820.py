# -*- coding: utf-8 -*-
"""一次性：2026-08-20 快讯提炼浓缩 + 跨天去重 + x.com 换源。
- 备份 -> 提炼 title/summary -> 删 OpenRouter(与08-17同事件) -> 换源 x.com -> 重排 id -> json.loads 自校验
"""
import json, shutil, os, sys

fp = 'data/news_2026-08-20.json'
bak = fp + '.20260820.bak'
if not os.path.exists(bak):
    shutil.copy(fp, bak)
    print('已备份:', bak)

with open(fp, encoding='utf-8') as f:
    items = json.load(f)

print('原始条数:', len(items))

# ---- 跨天去重：OpenRouter 加入 Stripe 与 08-17「Stripe 70 亿美元收购 OpenRouter」同一事件 ----
items = [n for n in items if 'OpenRouter' not in n['title']]
print('去重后条数:', len(items))

# ---- 提炼映射（按标题关键字定位）----
refine = {
    'GLM-5.3': {
        'title': '智谱 GLM-5.3 上线：AA 指数 60 分并列开源第一',
        'summary': 'GLM-5.3 API 即日开放，擅长复杂编码与防御性网络安全；单任务成本为旗舰最低，API 定价与 GLM-5.2 持平，权重下周五开源。',
    },
    'DeepSeek-V4-Pro': {
        'title': 'DeepSeek-V4-Pro H20 优化逼近 B300',
        'summary': 'LMSYS 在 H20 优化 1.6 万亿参数 MoE 推理：单节点 271 tokens/s，B300 为 383.7 tokens/s，差 1.42 倍。',
    },
    'LFM2.5': {
        'title': 'Liquid AI LFM2.5 量化版恢复 97% 精度',
        'summary': 'Liquid AI 推 LFM2.5 四款 Q4_0 检查点（230M 至 2.6B），经量化感知蒸馏训练，保持原生速度，恢复 BF16 精度损失 97%。',
    },
    'smolvm': {
        'title': 'smolvm 1.8.3 实测：硬件隔离沙箱跑不可信代码',
        'summary': 'smolvm 1.8.3 用硬件隔离 VM 沙箱运行不可信 Python/JS：离线镜像、无网络执行均正常，冷启动 0.6-1.5 秒，热执行约 50 毫秒。',
    },
    'FastMetal': {
        'title': 'FastMetal 让 Mac 本地 30 秒生成视频',
        'summary': 'FastMetal 让 Mac 本地 30 秒生成 5 秒 480P 视频，无需 CUDA 与云端，仅占 3.9 GiB 内存。',
        'source': 'GitHub：hao-ai-lab/FastVideo',
        'source_url': 'https://github.com/hao-ai-lab/FastVideo',
    },
    'BenchDrift': {
        'title': 'IBM 论文：措辞改写致 LLM 分数波动 74.7%',
        'summary': 'IBM BenchDrift 框架：不改答案改写同一问题，8 模型 3 基准分数平均波动 74.7 个百分点，高置信区间丢 18.5% 正确回答。',
        'source': 'arXiv：IBM Research 论文',
        'source_url': 'https://arxiv.org/html/2608.11694v1',
    },
    'Ornith': {
        'title': 'Ornith-1.5 发布：从自我构建到自我优化',
        'summary': 'Ornith-1.5 将 Ornith-1.0 的自我构建框架扩展为完整自我优化闭环：模型自主提出任务、生成任务专属脚手架并产出解决方案用于强化学习。',
    },
}

# 按 refine 顺序重排 items（保留原始类别标签等字段），应用提炼
ordered = []
for key, upd in refine.items():
    for n in items:
        if key in n['title']:
            n['title'] = upd['title']
            n['summary'] = upd['summary']
            if 'source' in upd:
                n['source'] = upd['source']
                n['source_url'] = upd['source_url']
            ordered.append(n)
            break
    else:
        print('WARN 未匹配:', key)

# 重排 id
for i, n in enumerate(ordered, 1):
    n['id'] = '20260820-%03d' % i

with open(fp, 'w', encoding='utf-8') as f:
    json.dump(ordered, f, ensure_ascii=False, indent=2)

# ---- 自校验 ----
with open(fp, encoding='utf-8') as f:
    data = json.load(f)
assert len(data) == len(ordered), '条数不一致'
empty_words = ['建议关注', '可关注', '推荐关注', '感兴趣可', '值得一试', '欢迎', '敬请期待']
for n in data:
    assert len(n['title']) <= 30, '标题超30字: %s' % n['title']
    assert len(n['summary']) <= 80, '摘要超80字: %s' % n['summary']
    for w in empty_words:
        assert w not in n['summary'], '摘要含空话词: %s' % w
    assert 'x.com' not in n.get('source_url', '') and 'twitter.com' not in n.get('source_url', ''), 'x.com 残留: %s' % n['id']
print('自校验通过: %d 条' % len(data))
for n in data:
    print(' ', n['id'], n['title'], '|', len(n['summary']), '字 |', n.get('source'))
