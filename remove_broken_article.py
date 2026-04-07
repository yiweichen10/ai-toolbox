import json
path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\data\articles.json'
with open(path, 'r', encoding='utf-8') as f:
    articles = json.load(f)

# Keep all except the broken one
new_articles = [a for a in articles if a['slug'] != '2026-ai-tool-roi-benchmark-48-tools-profitability']
print(f"Removed 1 article. Original count: {len(articles)}, New count: {len(new_articles)}")

with open(path, 'w', encoding='utf-8') as f:
    json.dump(new_articles, f, ensure_ascii=False, indent=2)
