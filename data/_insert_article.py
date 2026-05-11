import json

new_article = {
    "title": "Anthropic一口气给华尔街做了10个AI Agent、Gemini 2.5 Pro登顶编程榜、Cloudflare裁1100人拥抱AI：本周AI圈5件大事",
    "slug": "ai-news-weekly-may11-2026",
    "date": "2026-05-11",
    "category": "AI行业动态",
    "tags": ["AI新闻", "Anthropic", "Gemini", "Cloudflare", "AI Agent", "本地AI"],
    "description": "Anthropic发布10个金融行业AI Agent模板、Google Gemini 2.5 Pro I/O登顶WebDev Arena、Cloudflare裁员1100人转向Agentic AI、Local Deep Research开源项目实现95%准确率、Vercel开源Open Agents框架——本周AI圈每件大事都在重塑行业格局。",
    "content": open("_tmp_content.html", "r", encoding="utf-8").read()
}

data = json.load(open("articles.json", "r", encoding="utf-8"))
data.insert(0, new_article)
with open("articles.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"插入成功，当前总篇数: {len(data)}")
