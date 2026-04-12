import json

tools = json.load(open('data/tools.json','r',encoding='utf-8'))
# Check for tools with similar slugs
slugs = [t['slug'] for t in tools]
names = [t['name'] for t in tools]

# List all tools with their published status
published = [t for t in tools if t['published']]
unpublished = [t for t in tools if not t['published']]

print(f"Published: {len(published)}")
for t in published:
    print(f"  {t['name']} ({t['slug']})")

print(f"\nUnpublished: {len(unpublished)}")
for t in unpublished:
    print(f"  {t['name']} ({t['slug']})")

# Check specific names user mentioned
check_names = ['suno', 'runway', 'midjourney', 'gamma', 'stable diffusion', 'google gemini', 'copilot', 'claude', 'd-id', 'kling', 'cursor', 'grammarly', 'jasper', 'wordtune', 'tome', 'make', 'bardeen', 'hugging']
print("\n--- Checking specific tools ---")
for t in tools:
    name_lower = t['name'].lower()
    for check in check_names:
        if check in name_lower or check in t['slug'].lower():
            print(f"  Found: {t['name']} | slug={t['slug']} | published={t['published']}")
            break
