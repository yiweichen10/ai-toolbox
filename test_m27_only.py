#!/usr/bin/env python3
"""单独测试 MiniMax M2.7"""
import sys, os, time, re
import anthropic

sys.stdout.reconfigure(encoding='utf-8')

# ===== M2.7 配置 =====
MX_API_KEY = "sk-cp-xo-iwq2IP0CUD-JaimO2DPnf8yJw_QkVEswaN3J_1t3PJs5oSOQifmdHKMwivFKB20TXNan3C0-zS5X-kR9OB1XYoKf1Bm-IqW4vgw7r6WIp6OIwZ7L7Fs8"
MX_BASE_URL = "https://api.minimaxi.com/anthropic"
MX_MODEL = "MiniMax-M2.7"

MAX_TOKENS = 8000
TEMPERATURE = 0.8

SYSTEM_PROMPT = """你是一位资深科技博主，擅长写接地气、有实测数据、观点明确的AI工具对比文章。"""

USER_PROMPT = """请写一篇"实测Claude Code vs Cursor：2026年AI编程工具到底选哪个"的实测对比文章。

要求：
1. 以"深度用户"视角，写出真实使用体验
2. 必须有具体数据：响应速度、代码正确率、使用场景等
3. 给出明确的推荐结论
4. 包含对比表格（markdown格式）
5. 有踩坑经验（至少2条）
6. 有FAQ部分（3个问答）
7. 文中插入3-5个内链，链接到相关AI工具页面

字数：2000-3000字"""

def test_m27():
    client = anthropic.Anthropic(api_key=MX_API_KEY, base_url=MX_BASE_URL)
    print("🔄 正在调用 MiniMax-M2.7...")

    try:
        resp = client.messages.create(
            model=MX_MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": USER_PROMPT}]
        )

        # 解析响应
        text_content = ""
        thinking_content = ""
        for block in resp.content:
            if block.type == 'text':
                text_content += block.text
            elif block.type == 'thinking':
                thinking_content += block.thinking

        print(f"✅ 生成成功！")
        print(f"   耗时: 未知")
        print(f"   Text长度: {len(text_content)} 字")

        # 保存结果
        output_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(output_dir, 'm27_result.md'), 'w', encoding='utf-8') as f:
            f.write(f"# MiniMax-M2.7 生成文章\n\n")
            f.write(f"## 思考过程 (Thinking)\n{thinking_content}\n\n")
            f.write(f"---\n\n## 正文\n{text_content}")

        print(f"✅ 文章已保存到: {output_dir}/m27_result.md")
        return text_content

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_m27()
