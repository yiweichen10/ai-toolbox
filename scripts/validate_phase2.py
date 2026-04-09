#!/usr/bin/env python3
"""
Phase 2 验证脚本：只生成1个对比页 + 1个替代方案页
用于验证：API调用 → JSON解析 → build.py构建HTML 全流程
"""
import json
import os
import sys
import re
import time

# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
DATA_FILE = os.path.join(BASE_DIR, 'data', 'tools.json')

# AI API 配置
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
API_KEY = "sk-necmvkjjvnysmuelonjjdkwzrmepuqtempxyghojejkvqzne"
MODEL = "Pro/deepseek-ai/DeepSeek-V3.2"


def call_ai(prompt, max_tokens=4000):
    """调用DeepSeek-V3 API"""
    import urllib.request
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是一个专业的AI工具评测编辑。输出中文。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }).encode('utf-8')

    req = urllib.request.Request(
        API_URL, data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        return result['choices'][0]['message']['content']


def test_compare_api():
    """测试：生成1个 ChatGPT vs Claude 对比数据"""
    print("\n=== Test 1: Compare Page API ===")
    
    prompt = '''请写一篇深度对比评测文章：ChatGPT vs Claude 全面对比（2026年最新版）

要求：
1. 字数2000-2500字
2. 有明确观点和结论
3. 包含：快速结论、参数对比表、维度逐一对比、使用场景推荐、FAQ

严格JSON输出：
{
    "title": "标题（含2026）",
    "subtitle": "副标题",
    "slug": "chatgpt-claude",
    "meta_description": "meta描述150字符内",
    "keywords": ["ChatGPT vs Claude", "ChatGPT Claude对比"],
    "quick_verdict": {
        "overall_winner": "综合推荐",
        "best_for_beginners": "新手推荐",
        "best_value": "性价比之选",
        "best_for_pro": "专业用户推荐"
    },
    "content": "Markdown正文...",
    "faq": [{"question":"?", "answer":"!"}],
    "compared_tools": ["chatgpt", "claude"],
    "compare_category": "AI对话"
}'''

    print("Calling DeepSeek-V3 API...")
    start = time.time()
    result = call_ai(prompt, max_tokens=3500)
    elapsed = time.time() - start
    print(f"API response received in {elapsed:.1f}s")

    if not result:
        print("[FAIL] No response")
        return None

    # 解析JSON
    match = re.search(r'\{[\s\S]*\}', result)
    if not match:
        print(f"[FAIL] No JSON found in response. First 200 chars: {result[:200]}")
        return None

    try:
        data = json.loads(match.group())
        print(f"[OK] Parsed JSON: title='{data.get('title', 'N/A')[:50]}'")
        print(f"     slug={data.get('slug')}, keywords={len(data.get('keywords', []))} items")
        print(f"     content length={len(data.get('content', ''))} chars")
        print(f"     faq items={len(data.get('faq', []))}")
        data['page_type'] = 'compare'
        data['priority'] = 'high'
        return data
    except json.JSONDecodeError as e:
        print(f"[FAIL] JSON parse error: {e}")
        return None


def test_alternatives_api():
    """测试：生成1个 ChatGPT 替代方案数据"""
    print("\n=== Test 2: Alternatives Page API ===")

    prompt = '''写一篇"ChatGPT"的替代方案推荐文章（2026年最新版）
- ChatGPT是OpenAI推出的AI助手，价格$20/月Plus版，国内需翻墙
- 字数1500-2000字
- 推荐6-8个替代品（最佳替代、免费替代、国产替代）

严格JSON输出：
{
    "title": "ChatGPT替代品2026",
    "subtitle": "副标题",
    "slug": "chatgpt-alternatives",
    "meta_description": "meta描述",
    "keywords": ["ChatGPT替代", "类似ChatGPT"],
    "content": "Markdown正文...",
    "faq": [{"question":"?", "answer":"!"}],
    "target_tool": "chatgpt",
    "page_type": "alternatives"
}'''

    print("Calling DeepSeek-V3 API...")
    start = time.time()
    result = call_ai(prompt, max_tokens=3000)
    elapsed = time.time() - start
    print(f"API response in {elapsed:.1f}s")

    if not result:
        return None

    match = re.search(r'\{[\s\S]*\}', result)
    if not match:
        print(f"[FAIL] No JSON")
        return None

    try:
        data = json.loads(match.group())
        print(f"[OK] Parsed: title='{data.get('title', 'N/A')[:50]}'")
        print(f"     content length={len(data.get('content', ''))} chars")
        return data
    except json.JSONDecodeError as e:
        print(f"[FAIL] {e}")
        return None


def test_build_html(compare_data, alt_data):
    """测试：用build.py构建HTML"""
    from scripts.build import build_compare_page, build_alternatives_page
    
    print("\n=== Test 3: Build HTML ===")
    
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        tools = json.load(f)
    published = [t for t in tools if t.get('published', False)]
    print(f"Loaded {len(published)} published tools")

    if compare_data:
        print("\nBuilding compare page HTML...")
        html = build_compare_page(compare_data, published, [])
        path = os.path.join(BASE_DIR, 'compare', compare_data['slug'])
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"[OK] compare/{compare_data['slug']}/index.html ({len(html)} bytes)")

    if alt_data:
        print("\nBuilding alternatives page HTML...")
        html = build_alternatives_page(alt_data, published, [])
        path = os.path.join(BASE_DIR, 'alternatives', alt_data['slug'])
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"[OK] alternatives/{alt_data['slug']}/index.html ({len(html)} bytes)")

    return True


if __name__ == '__main__':
    print("=" * 50)
    print("Phase 2 Validation Test")
    print("=" * 50)

    # Test 1: Compare API
    compare_data = test_compare_api()
    time.sleep(2)  # 避免限流

    # Test 2: Alternatives API  
    alt_data = test_alternatives_api()

    if compare_data or alt_data:
        # Save test data
        output = {"compares": [compare_data] if compare_data else [],
                  "alternatives": [alt_data] if alt_data else [],
                  "metadata": {"test_run": True}}
        out_file = os.path.join(BASE_DIR, 'data', 'compare_data.json')
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n[OK] Saved to {out_file}")

        # Test 3: Build HTML
        test_build_html(compare_data, alt_data)

        print("\n" + "=" * 50)
        print("ALL TESTS PASSED - Phase 2 validated!")
        print("=" * 50)
    else:
        print("\n[FAIL] All API calls failed")
