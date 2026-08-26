"""扫描工具图标覆盖情况 — Simple Icons + Google Favicons"""
import json, urllib.request, os, re, sys
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# 1. Load tools (2026-08-26 去单体化: 分片优先)
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from data_store import load_all_tools
tools = load_all_tools()

# 2. Fetch Simple Icons index via jsDelivr CDN (mirrors npm)
print("Fetching Simple Icons index via jsDelivr...")
simple_icons = None
urls = [
    'https://cdn.jsdelivr.net/npm/simple-icons@14/_data/simple-icons.json',
    'https://cdn.jsdelivr.net/npm/simple-icons@latest/simple-icons.json',
    'https://cdn.jsdelivr.net/npm/simple-icons@13/_data/simple-icons.json',
]
for url in urls:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            simple_icons = json.loads(resp.read().decode())
        print(f"  OK: {len(simple_icons)} icons from {url}")
        break
    except Exception as e:
        print(f"  FAIL: {url} -> {type(e).__name__}")

if simple_icons is None:
    print("  WARNING: all CDN sources failed, using built-in list")
    known = {
        'openai', 'chatgpt', 'claude', 'anthropic', 'midjourney', 'github', 'githubcopilot',
        'cursor', 'n8n', 'zapier', 'notion', 'canva', 'figma', 'suno', 'elevenlabs',
        'runwayml', 'perplexity', 'deepseek', 'huggingface', 'replicate', 'webflow',
        'framer', 'miro', 'spline', 'semrush', 'google', 'microsoft', 'adobe',
        'webstorm', 'brave', 'arc', 'notebooklm', 'terraform', 'supabase', 'stabilityai',
        'raycast', 'chromadb', 'langchain', 'pinecone', 'qdrant', 'milvus',
        'weaviate', 'lottiefiles', 'descript', 'mintlify', 'pixso', 'jsdesign',
        'duolingo', 'grammarly', 'discord', 'wordpress', 'shopify', 'vercel',
        'netlify', 'slack', 'zoom', 'spotify', 'tiktok', 'youtube', 'twitter',
        'meta', 'amazonwebservices', 'apple', 'alibabacloud', 'tencentqq', 'baidu',
        'bytedance', 'huawei', 'xiaomi', 'mozilla', 'firefox', 'chrome', 'safari',
        'dify', 'coze', 'comfyui', 'upscayl', 'aider', 'tabnine',
        'kimi', 'doubao', 'gemini', 'wps', 'deepl', 'pika', 'veed',
        'removedotbg', 'photoroom', 'otter', 'beautifulai', 'tome', 'fireflies',
        'speechify', 'krisp', 'murf', 'cleanvoice', 'relume', 'gamma',
        'kapwing', 'pictory', 'invideo', 'heygen', 'd-id', 'elai',
        'colossyan', 'synthesia', 'opus', 'looka', 'brandmark', 'scalenut',
        'frase', 'surfer', 'prowritingaid', 'quillbot', 'copyai', 'writesonic',
        'jasper', 'rytr', 'jenni', 'wordtune', 'monica', 'buffer',
    }
    simple_by_slug = {s: {'slug': s, 'hex': '#000000'} for s in known}
    simple_by_title = simple_by_slug
else:
    simple_by_slug = {}
    simple_by_title = {}
    for icon in simple_icons:
        s = icon.get('slug', icon.get('title', '')).lower()
        if s:
            simple_by_slug[s] = icon
        t = icon.get('title', '').lower().strip()
        if t:
            simple_by_title[t] = icon
            simple_by_title[t.replace(' ai', '')] = icon

print(f"  Indexed: {len(simple_by_slug)} brands")

# 3. Domain extraction
def extract_domain(url_str):
    if not url_str:
        return None
    try:
        if not url_str.startswith('http'):
            url_str = 'https://' + url_str
        parsed = urlparse(url_str)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return None

# 4. Match
print("Matching...")
results = {'simple_icons': [], 'favicon_only': [], 'no_match': []}

for tool in tools:
    name = tool['name']
    slug = tool['slug']
    domain = extract_domain(tool.get('url', ''))
    found = None
    name_lower = name.lower().strip()

    # S1: exact name match
    if name_lower in simple_by_title:
        found = simple_by_title[name_lower]

    # S2: slug match
    if not found and slug.lower() in simple_by_slug:
        found = simple_by_slug[slug.lower()]

    # S3: domain root match
    if not found and domain:
        dn = domain.split('.')[0]
        if dn in simple_by_slug:
            found = simple_by_slug[dn]

    # S4: variant matches
    if not found:
        variants = [
            name_lower.replace(' ', ''),
            name_lower.replace(' ', '-'),
            name_lower.replace(' ai', ''),
            re.sub(r'\s+(ai|api|pro|lite|max|code|chat|agent|tool)\s*$', '', name_lower, flags=re.I).strip(),
        ]
        if domain:
            variants.append(domain.split('.')[0])
        for v in variants:
            if v in simple_by_slug:
                found = simple_by_slug[v]
                break
            if v in simple_by_title:
                found = simple_by_title[v]
                break

    if found:
        results['simple_icons'].append({
            'name': name, 'slug': slug, 'domain': domain,
            'simple_slug': found.get('slug', found.get('title', '')),
            'hex': found.get('hex', '#000000'),
        })
    elif domain:
        results['favicon_only'].append({'name': name, 'slug': slug, 'domain': domain})
    else:
        results['no_match'].append({'name': name, 'slug': slug})

# 5. Report
total = len(tools)
si = len(results['simple_icons'])
fv = len(results['favicon_only'])
nm = len(results['no_match'])

print()
print("=" * 70)
print("  ICON COVERAGE REPORT")
print("=" * 70)
print(f"  Total tools:        {total}")
print(f"  Simple Icons:       {si:3d}  ({si*100//total}%)  -- SVG, no HTTP request per icon")
print(f"  Google Favicons:    {fv:3d}  ({fv*100//total}%)  -- PNG, 1 request per icon")
print(f"  No data source:     {nm:3d}  ({nm*100//total}%)  -- fallback to emoji")
print(f"  Real icon coverage: {si+fv:3d}  ({(si+fv)*100//total}%)")
print()

print(f"--- Simple Icons ({si}) ---")
for r in sorted(results['simple_icons'], key=lambda x: x['name'])[:50]:
    hexcode = r.get('hex', '')
    print(f"  {r['name']:<25s} {r['simple_slug']:<30s} {hexcode}")

if fv > 0:
    print(f"\n--- Google Favicons ({fv}) ---")
    for r in results['favicon_only'][:20]:
        print(f"  {r['name']:<25s} {r['domain']}")

if nm > 0:
    print(f"\n--- No Match ({nm}) ---")
    for r in results['no_match'][:15]:
        print(f"  {r['name']}")

# 6. Save
out_path = os.path.join(DATA_DIR, 'icon_coverage.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\nSaved: {out_path}")
