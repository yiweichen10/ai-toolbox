"""下载所有工具真实图标到本地 assets/icons/
Phase 1: Simple Icons SVG (jsDelivr)
Phase 2: 官网 favicon / DuckDuckGo icon API (多路备选) -> PNG
"""
import json, urllib.request, os, sys, time, ssl

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
ICONS_DIR = os.path.join(BASE_DIR, 'assets', 'icons')
os.makedirs(ICONS_DIR, exist_ok=True)

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def log(msg):
    print(msg, flush=True)

def download(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as r:
            data = r.read()
            if len(data) < 80: return None
            return data
    except:
        return None

# Load coverage
with open(os.path.join(DATA_DIR, 'icon_coverage.json'), 'r', encoding='utf-8') as f:
    coverage = json.load(f)

si_items = coverage.get('simple_icons', [])
fv_items = coverage.get('favicon_only', [])
downloaded = 0
failed = 0
skipped = 0

# ====================
# Phase 1: Simple Icons
# ====================
log(f"\n{'='*60}\n  Phase 1: Simple Icons SVG ({len(si_items)} tools)\n{'='*60}")
for i, item in enumerate(si_items):
    slug = item['slug']
    simple_slug = item.get('simple_slug', '').lower()
    dest = os.path.join(ICONS_DIR, f'{slug}.svg')

    if os.path.exists(dest):
        skipped += 1
        continue

    url = f'https://cdn.jsdelivr.net/npm/simple-icons@14/icons/{simple_slug}.svg'
    data = download(url)
    if data:
        with open(dest, 'wb') as f:
            f.write(data)
        downloaded += 1
        log(f"  [{i+1}/{len(si_items)}] OK  {item['name']}")
    else:
        failed += 1
        log(f"  [{i+1}/{len(si_items)}] MISS {item['name']} ({simple_slug}) -> will try favicon")
    time.sleep(0.05)

# ====================
# Phase 2: Favicons
# ====================
# Combine: favicon_only items + simple_icons that failed
need_favicon = []
for item in fv_items:
    need_favicon.append(item)
# Also add Simple Icons items that failed
for item in si_items:
    slug = item['slug']
    dest_svg = os.path.join(ICONS_DIR, f'{slug}.svg')
    if not os.path.exists(dest_svg):
        need_favicon.append(item)

log(f"\n{'='*60}\n  Phase 2: Favicons ({len(need_favicon)} tools)\n{'='*60}")
for i, item in enumerate(need_favicon):
    slug = item['slug']
    domain = item.get('domain', '')
    dest = os.path.join(ICONS_DIR, f'{slug}.png')

    if os.path.exists(dest):
        skipped += 1
        continue

    if not domain:
        failed += 1
        continue

    data = None
    # Strategy 1: DuckDuckGo icon API (most reliable, returns favicon-sized images)
    ddg_url = f'https://icons.duckduckgo.com/ip3/{domain}.ico'
    data = download(ddg_url, timeout=10)

    # Strategy 2: Direct favicon.ico
    if not data:
        direct_url = f'https://{domain}/favicon.ico'
        data = download(direct_url, timeout=10)

    # Strategy 3: Google Favicons
    if not data:
        google_url = f'https://www.google.com/s2/favicons?domain={domain}&sz=64'
        data = download(google_url, timeout=10)

    if data:
        with open(dest, 'wb') as f:
            f.write(data)
        downloaded += 1
        log(f"  [{i+1}/{len(need_favicon)}] OK  {item['name']} ({domain})")
    else:
        failed += 1
        # Don't spam, only log every 10th failure
        if failed % 10 == 1:
            log(f"  [{i+1}/{len(need_favicon)}] MISS {item['name']} ({domain})")
    time.sleep(0.02)

# ====================
# Summary
# ====================
svg_count = len([f for f in os.listdir(ICONS_DIR) if f.endswith('.svg')])
png_count = len([f for f in os.listdir(ICONS_DIR) if f.endswith('.png')])

log(f"\n{'='*60}")
log(f"  DONE")
log(f"{'='*60}")
log(f"  SVGs:  {svg_count}")
log(f"  PNGs:  {png_count}")
log(f"  Total: {svg_count + png_count}")
log(f"  Dir:   {ICONS_DIR}")
