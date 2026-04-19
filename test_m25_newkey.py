import requests, time

API_KEY = "sk-yrgzxbdyofrlgouurfiinikjlplmqhxtuydmmbruiajbzfam"
BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL = "Pro/MiniMaxAI/MiniMax-M2.5"

prompt = """你是一位专注于AI工具实测的资深工程师。请为AI工具导航站写一篇Claude Code vs Cursor的深度对比文章。

要求：
1. 字数：2000-3000字
2. 必须包含以下元素：
   - 实测数据表格（响应速度、代码正确率等）
   - 3条踩坑经验（要真实、具体）
   - FAQ部分（3个Q&A）
   - 内链占位符（3-5个，格式：[工具名]）
3. 语言风格：专业但有温度，像真实用户写的
4. 结论要明确，不能两边都不得罪

现在写文章："""

payload = {
    "model": MODEL,
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 4000,
    "temperature": 0.7
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

print(">>> Calling MiniMax-M2.5 (new key)...")
start = time.time()
r = requests.post(BASE_URL, headers=headers, json=payload, timeout=60)
elapsed = time.time() - start

print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    content = data['choices'][0]['message']['content']
    print(f"SUCCESS! Time: {elapsed:.1f}s, Chars: {len(content)}")
    with open("m25_result.md", "w", encoding="utf-8") as f:
        f.write(f"# MiniMax-M2.5 (new key) Article\n\n")
        f.write(f"## Info\n- Model: {MODEL}\n- Time: {elapsed:.1f}s\n- Chars: {len(content)}\n\n---\n\n## Content\n{content}")
    print("Saved to m25_result.md")
else:
    print(f"FAILED: {r.text}")
