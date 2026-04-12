import json

tools = json.load(open('data/tools.json','r',encoding='utf-8'))

# Slugs to remove (duplicate tools that already exist with different names)
dup_slugs = [
    'suno-ai',           # Suno already exists
    'runway-ml',         # Runway already exists
    'midjourney-v7',     # Midjourney already exists
    'stable-diffusion-3',# Stable Diffusion already exists
    'google-gemini',     # Gemini already exists
    'microsoft-copilot-2',# Copilot（微软）already exists
    'anthropic-claude',  # Claude already exists
    'cursor-2',          # Cursor already exists
    'grammarly',         # Grammarly AI already exists
    'jasper-ai',         # Jasper already exists
    'gamma-ai',          # Gamma already exists
    'tome-ai',           # Tome already exists
    'make-2',            # Make already exists
    'kling-ai-2',        # 可灵AI already exists
]

before = len(tools)
tools = [t for t in tools if t['slug'] not in dup_slugs]
after = len(tools)
removed = before - after

with open('data/tools.json','w',encoding='utf-8') as f:
    json.dump(tools, f, ensure_ascii=False, indent=2)

published = len([t for t in tools if t['published']])
unpublished = len([t for t in tools if not t['published']])
print(f"Removed {removed} duplicates")
print(f"Total: {after} (published={published}, unpublished={unpublished})")
print(f"Unpublished can support ~{unpublished//3} days")
