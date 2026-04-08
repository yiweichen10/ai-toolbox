import json

with open('data/tools_en.json', encoding='utf-8') as f:
    tools = json.load(f)

skip_names = ['秒画', 'LiblibAI', '即时设计AI', 'Arc浏览器', '秘塔AI搜索', 'MiniMax']
filtered = [t for t in tools if t['name'] not in skip_names]
with open('data/tools_en.json', 'w', encoding='utf-8') as f:
    json.dump(filtered, f, indent=2, ensure_ascii=False)

print(f'Filtered to {len(filtered)} tools (removed {len(tools)-len(filtered)})')
need_content = [t for t in filtered if '[AUTO-GENERATE]' in t.get('description','')]
print(f'Tools needing English content: {len(need_content)}')
for t in need_content:
    name = t['name']
    cat = t['category']
    slug = t['slug']
    print(f"  {name} | {cat} | {slug}")
