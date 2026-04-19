#!/usr/bin/env python3
"""
MiniMax M2.7 vs M2.5 文章质量对比测试
使用相同主题、相同prompt，分别调用两个模型生成文章
"""

import json, sys, os, time, re
from openai import OpenAI
import anthropic

sys.stdout.reconfigure(encoding='utf-8')

# ===== M2.5 配置（硅基流动） =====
SF_API_KEY = "sk-zydoafoxobsgevqsokahnvpqxrlxprdmjswahfxjybwhtfhk"
SF_BASE_URL = "https://api.siliconflow.cn/v1"
SF_MODEL = "Pro/MiniMaxAI/MiniMax-M2.5"

# ===== M2.7 配置（MiniMax官方 - Anthropic兼容） =====
MX_API_KEY = "sk-cp-xo-iwq2IP0CUD-JaimO2DPnf8yJw_QkVEswaN3J_1t3PJs5oSOQifmdHKMwivFKB20TXNan3C0-zS5X-kR9OB1XYoKf1Bm-IqW4vgw7r6WIp6OIwZ7L7Fs8"
MX_BASE_URL = "https://api.minimaxi.com/anthropic"
MX_MODEL = "MiniMax-M2.7"

MAX_TOKENS = 6000
TEMPERATURE = 0.8

# ===== 统一 System Prompt =====
SYSTEM_PROMPT = """你是一位资深科技博主，擅长写接地气、有实测数据、观点明确的AI工具对比文章。

## 写作风格要求
- 语气像朋友聊天，不要教科书式的说教
- 有具体数据和个人真实体验
- 结论明确，不和稀泥
- 适当使用口语化表达

## 禁止内容
- 禁止AI味词汇：强大的、智能的、高效的、全面的、一键生成、显著提升、大幅优化
- 禁止废话句式：首先/其次/最后、此外、另外、让我们一起来看看
- 禁止自指向：本文将、这篇文章

## 文章结构（实测数据型）
开头 → 为什么写这篇 → 3个实测段落 → 对比表格 → 踩坑经验 → FAQ(3问答) → 总结

## 内链要求
在文章中自然插入3-5个工具内链，格式：[工具名](https://www.aitoolbox.hk/tools/工具slug/)
"""

# ===== 测试主题 =====
TEST_TOPIC = "实测Claude Code vs Cursor：2026年AI编程工具到底选哪个"
TEST_TYPE = "A"  # 实测数据型

# 构造用户prompt
USER_PROMPT = f"""请写一篇{TEST_TOPIC}的实测对比文章。

要求：
1. 以"深度用户"视角，写出真实使用体验
2. 必须有具体数据：响应速度、代码正确率、使用场景等
3. 给出明确的推荐结论
4. 包含对比表格（markdown格式）
5. 有踩坑经验（至少2条）
6. 有FAQ部分（3个问答）
7. 文中插入3-5个内链，链接到相关AI工具页面

字数：2000-3000字
"""

def call_sf_api(topic, prompt, model):
    """调用硅基流动API（M2.5）"""
    client = OpenAI(api_key=SF_API_KEY, base_url=SF_BASE_URL)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"主题：{topic}\n\n{prompt}"}
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        return resp.choices[0].message.content, resp.usage
    except Exception as e:
        return f"Error: {e}", None

def call_mx_api(topic, prompt, model):
    """调用MiniMax官方API（M2.7）- 使用Anthropic SDK"""
    client = anthropic.Anthropic(
        api_key=MX_API_KEY,
        base_url=MX_BASE_URL
    )
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"主题：{topic}\n\n{prompt}"}
            ]
        )
        # 解析Anthropic格式响应
        text_content = ""
        for block in resp.content:
            if block.type == 'text':
                text_content += block.text
        # Anthropic返回的是usage类，不是标准dict
        usage_info = type('obj', (object,), {
            'prompt_tokens': getattr(resp.usage, 'input_tokens', 0),
            'completion_tokens': getattr(resp.usage, 'output_tokens', 0)
        })()
        return text_content, usage_info
    except Exception as e:
        return f"Error: {e}", None

def analyze_quality(content, model_name):
    """分析文章质量"""
    print(f"\n{'='*60}")
    print(f"📊 {model_name} 文章质量分析")
    print(f"{'='*60}")

    # 字数
    word_count = len(content)
    print(f"字数: {word_count} 字")

    # 段落数
    paragraphs = content.split('\n\n')
    para_count = len([p for p in paragraphs if p.strip()])
    print(f"段落数: {para_count}")

    # 表格数
    table_count = content.count('|---')
    print(f"表格行数: {table_count}")

    # FAQ检测
    faq_count = len([p for p in paragraphs if 'FAQ' in p or '常见问题' in p])
    print(f"FAQ段落: {faq_count}")

    # 内链数
    import re
    link_count = len(re.findall(r'\[([^\]]+)\]\(https://www\.aitoolbox\.hk/tools/([^/]+)/\)', content))
    print(f"内链数: {link_count}")

    # AI味检测
    ai_words = ['强大的', '智能的', '高效', '全面', '一键生成', '显著提升', '大幅优化', '革命性', '颠覆性']
    found_ai = [w for w in ai_words if w in content]
    print(f"AI味词汇: {found_ai if found_ai else '无'}")

    # 踩坑经验检测
    pit_words = ['踩坑', '翻车', '教训', '避坑', '注意', '千万别']
    has_pit = any(w in content for w in pit_words)
    print(f"踩坑经验: {'有' if has_pit else '无'}")

    return {
        'word_count': word_count,
        'para_count': para_count,
        'table_count': table_count,
        'faq_count': faq_count,
        'link_count': link_count,
        'ai_words': found_ai,
        'has_pit': has_pit
    }

def main():
    print("🚀 MiniMax M2.7 vs M2.5 文章质量对比测试")
    print(f"测试主题: {TEST_TOPIC}")
    print("="*60)

    # 生成M2.5文章
    print("\n📝 正在生成 M2.5 文章...")
    start = time.time()
    m25_content, m25_usage = call_sf_api(TEST_TOPIC, USER_PROMPT, SF_MODEL)
    m25_time = time.time() - start
    print(f"⏱️ M2.5 耗时: {m25_time:.1f}秒")

    # 生成M2.7文章
    print("\n📝 正在生成 M2.7 文章...")
    start = time.time()
    m27_content, m27_usage = call_mx_api(TEST_TOPIC, USER_PROMPT, MX_MODEL)
    m27_time = time.time() - start
    print(f"⏱️ M2.7 耗时: {m27_time:.1f}秒")

    # 质量分析
    m25_stats = analyze_quality(m25_content, "M2.5 (硅基流动)")
    m27_stats = analyze_quality(m27_content, "M2.7 (MiniMax官方)")

    # 保存文章
    output_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(output_dir, 'm25_article.md'), 'w', encoding='utf-8') as f:
        f.write(f"# M2.5 生成文章\n\n耗时: {m25_time:.1f}秒\n\n{m25_content}")
    with open(os.path.join(output_dir, 'm27_article.md'), 'w', encoding='utf-8') as f:
        f.write(f"# M2.7 生成文章\n\n耗时: {m27_time:.1f}秒\n\n{m27_content}")

    print(f"\n✅ 文章已保存到: {output_dir}")

    # 对比汇总
    print("\n" + "="*60)
    print("📊 对比汇总")
    print("="*60)
    print(f"{'指标':<15} {'M2.5':<15} {'M2.7':<15}")
    print("-"*45)
    print(f"{'字数':<15} {m25_stats['word_count']:<15} {m27_stats['word_count']:<15}")
    print(f"{'段落数':<15} {m25_stats['para_count']:<15} {m27_stats['para_count']:<15}")
    print(f"{'表格行数':<15} {m25_stats['table_count']:<15} {m27_stats['table_count']:<15}")
    print(f"{'内链数':<15} {m25_stats['link_count']:<15} {m27_stats['link_count']:<15}")
    print(f"{'耗时(秒)':<15} {m25_time:<15.1f} {m27_time:<15.1f}")

    # Token使用
    if m25_usage:
        print(f"\nM2.5 Token: input={m25_usage.prompt_tokens}, output={m25_usage.completion_tokens}")
    if m27_usage:
        print(f"M2.7 Token: input={m27_usage.prompt_tokens}, output={m27_usage.completion_tokens}")

if __name__ == "__main__":
    main()
