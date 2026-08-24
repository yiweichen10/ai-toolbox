import json
path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\data\articles.json'
with open(path, 'r', encoding='utf-8') as f:
    articles = json.load(f)

for a in articles:
    if a['slug'] == '2026-ai-tool-roi-benchmark-48-tools-profitability':
        a['lang'] = 'en'
        print("Updated lang to 'en' for ROI Benchmark article.")

with open(path, 'w', encoding='utf-8') as f:
    json.dump(articles, f, ensure_ascii=False, indent=2)
