import json

with open('data/tools.json', 'r', encoding='utf-8') as f:
    tools = json.load(f)

# All tools with www. prefix
www_tools = [(t['name'], t['url']) for t in tools if t.get('url','').startswith('https://www.')]
print(f'=== www. prefix URLs ({len(www_tools)}) ===')
for name, url in www_tools:
    print(f'  {name}: {url}')

# All tools
print(f'\n=== All tool URLs ({len(tools)} total) ===')
for t in tools:
    print(f"  {t['name']}: {t.get('url','')}")
