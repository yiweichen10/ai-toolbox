import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

API_KEY = "sk-necmvkjjvnysmuelonjjdkwzrmepuqtempxyghojejkvqzne"
BASE_URL = "https://api.siliconflow.cn/v1"

def generate(prompt, max_tokens=2500):
    data = json.dumps({
        "model": "deepseek-ai/DeepSeek-V3",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]

ARTICLES = [
    {
        "title": "如何注册和使用Midjourney：从零开始的完整教程（2026版）",
        "slug": "how-to-use-midjourney-2026",
        "description": "Midjourney怎么注册？Discord怎么用？生成图片有哪些技巧？本教程覆盖从注册到出图的完整流程，附涨价后最新价格信息。",
        "keywords": "Midjourney注册,Midjourney教程,Discord使用,AI绘图,Midjourney充值",
        "category": "AI绘画",
        "prompt": '''你是一位真实使用Midjourney超过一年的用户，写一篇实战教程。

主题：如何注册和使用Midjourney（完整入门教程）

要求：
- 面向完全零基础的小白，不要假设读者懂任何技术术语
- 语气像真实用户在分享经验，有个性，不刻板
- 直接给出具体操作步骤，不要废话
- 结尾要有真实的坑和建议

文章结构：
1. 开场：真实使用场景切入（凌晨2点睡不着用Midjourney画了一幅画之类的）
2. 注册部分：Discord账号注册 + Midjourney服务器加入（具体步骤）
3. 出图基础：第一个命令怎么输入，什么是/imagine
4. 进阶技巧：如何让图片更精准，关键词怎么写
5. 避坑指南：新手最常犯的错误
6. 结尾：真实感受和建议

字数：800-1000字。直接写正文，不要标题，不要分章节标题。'''
    },
    {
        "title": "国内用户如何用Claude：注册、充值、实战技巧（2026完整攻略）",
        "slug": "how-to-use-claude-in-china-2026",
        "description": "Claude在国内怎么注册？需要科学上网吗？如何充值Claude Pro？和ChatGPT相比有什么优势？这篇攻略全部讲清楚。",
        "keywords": "Claude注册,Claude国内,Claude充值,Claude vs ChatGPT,AI对话",
        "category": "AI对话",
        "prompt": '''你是一位深度使用Claude和ChatGPT的程序员，写一篇对比型实战教程。

主题：国内用户如何用Claude（注册+使用+充值完整攻略）

要求：
- 面向国内用户，诚实说明哪些步骤需要科学上网
- 不吹不黑，真实对比Claude和ChatGPT的优劣
- 语气像真人说话，有个性
- 有具体步骤，有真实踩坑经验

文章结构：
1. 开场：为什么我选择Claude而不是ChatGPT（真实原因）
2. 注册流程：需要什么条件，国内手机号可以吗
3. 充值指南：Claude Pro值不值，20美元花得值吗
4. 核心功能：Artifacts怎么玩，文档分析怎么用
5. 和ChatGPT的真实对比：各自适合什么场景
6. 结尾：我的选择建议

字数：800-1000字。直接写正文，不要标题。'''
    },
    {
        "title": "如何用Suno创作自己的歌曲：零基础音乐创作入门（2026实测）",
        "slug": "how-to-use-suno-music-creation-2026",
        "description": "Suno怎么用？能不能写中文歌？免费额度够不够用？生成的音乐能商用吗？这篇实测告诉你所有答案。",
        "keywords": "Suno教程,Suno注册,Suno写歌,AI音乐创作,AI作曲",
        "category": "AI音频",
        "prompt": '''你是一位音乐爱好者，最近迷上了用AI创作歌曲，写一篇分享型教程。

主题：零基础用Suno创作自己的歌曲（入门教程）

要求：
- 面向零基础用户，对音乐制作一窍不通也可以上手
- 语气轻松自然，像在跟朋友分享有趣发现
- 有真实使用过程，不是功能介绍列表
- 结尾分享真实感受

文章结构：
1. 开场：我是怎么发现Suno的，凌晨用它生成了一首"赛博情歌"
2. 入门：注册，最简单的生成方式，中文歌能不能做
3. 进阶：怎么写歌词，如何选风格
4. 真实体验：生成10首后的感受（好的和失望的都说）
5. 商用问题：免费版能商用吗，付费值不值
6. 结尾彩蛋：最疯狂的一次实验

字数：800-1000字。直接写正文，不要标题。'''
    },
    {
        "title": "Cursor vs GitHub Copilot vs Windsurf 2026：谁才是编程最佳AI伴侣？",
        "slug": "cursor-vs-copilot-vs-windsurf-2026",
        "description": "三大AI编程工具横评：Cursor、GitHub Copilot、Windsurf哪个更好用？价格差多少？真实项目测试结果告诉你答案。",
        "keywords": "Cursor,GitHub Copilot,Windsurf,AI编程,编程工具对比",
        "category": "AI编程",
        "prompt": '''你是一位有8年编程经验的全栈工程师，最近三个工具都深度使用过，写一篇真实对比评测。

主题：Cursor vs GitHub Copilot vs Windsurf 2026 真实对比评测

要求：
- 真实项目测试结果，不是功能列表对比
- 每个工具说出最喜欢的一个功能和最讨厌的一个问题
- 价格也要对比，免费的能不能满足需求
- 结论要明确，不要"各有优劣"这种废话

文章结构：
1. 开场：我是怎么从Copilot跳槽到Cursor，又同时用Windsurf的
2. 三工具各自的最强场景（用真实项目举例）
3. 价格对比：免费版够用吗，付费值不值
4. 最大槽点：每个工具最让我崩溃的瞬间
5. 结论：不同人群分别推荐哪个
6. 结尾：未来预测

字数：900-1100字。直接写正文，不要标题。'''
    },
]

print(f"Generating {len(ARTICLES)} articles...\n")
for i, art in enumerate(ARTICLES, 1):
    print(f"[{i}/{len(ARTICLES)}] Generating: {art['title']}")
    content = generate(art["prompt"])
    print(f"  Raw length: {len(content)} chars")
    art["content"] = content
    print(f"  Done.\n")

print("All articles generated. Saving...")

# Save to temp file for later humanization
output = {}
for art in ARTICLES:
    output[art["slug"]] = {
        "title": art["title"],
        "slug": art["slug"],
        "description": art["description"],
        "keywords": art["keywords"],
        "category": art["category"],
        "content": art["content"]
    }

with open("_article_drafts.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print("Drafts saved to _article_drafts.json")