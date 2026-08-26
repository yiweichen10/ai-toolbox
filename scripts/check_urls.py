import json
import os, sys

# 2026-08-26 去单体化: 分片优先
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
from data_store import load_all_tools

tools = load_all_tools()

# All tools with www. prefix
www_tools = [(t['name'], t['url']) for t in tools if t.get('url','').startswith('https://www.')]
print(f'=== www. prefix URLs ({len(www_tools)}) ===')
for name, url in www_tools:
    print(f'  {name}: {url}')

# All tools
print(f'\n=== All tool URLs ({len(tools)} total) ===')
for t in tools:
    print(f"  {t['name']}: {t.get('url','')}")
