"""
全量图标修复：删除损坏图标(HTML/ICO/格式错误)，从 Simple Icons 和 logo CDN 下载真品牌 SVG。
用法: python scripts/repair_all_icons.py [--dry-run]
"""
import os
import sys
import json
import urllib.request
import time

ICON_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets', 'icons')
TOOLS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'tools.json')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'

SIMPLE_ICONS_BASE = 'https://cdn.simpleicons.org'
LOGO_SVGCDN_BASE = 'https://logo.svgcdn.com/logos'

# ============================================================
# COMPREHENSIVE Simple Icons slug mapping
# ============================================================
SI_MAP = {
    # Global AI
    'openai': 'openai', 'chatgpt': 'openai', 'chatgpt-work': 'openai',
    'claude': 'claude', 'claude-fable-5': 'claude',
    'anthropic': 'anthropic', 'anthropic-console': 'anthropic',
    'deepseek': 'deepseek',
    'kimi': 'kimi',
    'cursor': 'cursor',
    'v0': 'v0',
    'gemini': 'gemini', 'gemini-omni': 'gemini',
    'github-copilot': 'githubcopilot',
    'hugging-face': 'huggingface',
    'perplexity': 'perplexity',
    'mistral-ai': 'mistral',
    'x-ai': 'x', 'grok': 'x', 'grok-4-5': 'x',
    
    # Tech giants
    'google': 'google', 'google-cloud': 'googlecloud',
    'microsoft': 'microsoft', 'microsoft-copilot': 'microsoftcopilot',
    'amazon': 'amazon', 'amazon-web-services': 'amazonwebservices',
    'apple': 'apple',
    'meta': 'meta', 'meta-so': 'meta', 'facebook': 'meta',
    'nvidia': 'nvidia',
    'intel': 'intel',
    'amd': 'amd',
    'tesla': 'tesla',
    
    # Chinese AI
    'wenxin-yiyan': 'baidu', 'wenxin-yige': 'baidu', 'wenxin-kuaima': 'baidu',
    'zhipu-chatglm': 'zhipuai',
    'minimax': 'minimax',
    'xinghuo-iflytek': 'iflytek', 'xinghuo-cognitive-model': 'iflytek',
    'qwen-chat': 'alibabacloud', 'qwen3-coder-next': 'alibabacloud',
    'tongyi-lingma': 'alibabacloud', 'tongyi-wanxiang': 'alibabacloud', 'tongyi-efficiency': 'alibabacloud',
    'tencent': 'tencentqq', 'tencent-hunyuan': 'tencentqq', 'tencent-yuanbao': 'tencentqq',
    'tencent-docs-ai': 'tencentqq',
    'baichuan-ai': 'baichuan', 'baichuan-2': 'baichuan',
    'doubao': 'bytedance',
    'jimeng-ai': 'bytedance',
    
    # Development tools
    'github': 'github', 'gitlab': 'gitlab', 'bitbucket': 'bitbucket',
    'docker': 'docker', 'kubernetes': 'kubernetes',
    'jetbrains': 'jetbrains',
    'vscode': 'visualstudiocode', 'visual-studio-code': 'visualstudiocode',
    'zed-editor': 'zedindustries',
    'codebuddy-tengxun': 'tencentqq',
    'sourcegraph-cody': 'sourcegraph',
    'tabnine': 'tabnine',
    
    # Design
    'figma': 'figma', 'canva': 'canva',
    'spline-ai': 'spline',
    'remove-bg': 'removebg',
    
    # Media
    'youtube': 'youtube', 'spotify': 'spotify', 'netflix': 'netflix',
    'twitch': 'twitch', 'tiktok': 'tiktok', 'discord': 'discord',
    'pinterest': 'pinterest', 'reddit': 'reddit', 'instagram': 'instagram',
    'whatsapp': 'whatsapp', 'telegram': 'telegram', 'slack': 'slack',
    'zoom': 'zoom', 'linkedin': 'linkedin',
    
    # Commerce
    'shopify': 'shopify', 'paypal': 'paypal', 'stripe': 'stripe',
    'square': 'square',
    
    # Programming languages
    'python': 'python', 'rust': 'rust', 'go': 'go',
    'typescript': 'typescript', 'javascript': 'javascript',
    'swift': 'swift', 'kotlin': 'kotlin',
    
    # Databases / Infrastructure
    'mongodb': 'mongodb', 'redis': 'redis', 'postgresql': 'postgresql',
    'elasticsearch': 'elasticsearch', 'grafana': 'grafana',
    'nginx': 'nginx', 'cloudflare': 'cloudflare',
    'digitalocean': 'digitalocean', 'vercel': 'vercel', 'netlify': 'netlify',
    'heroku': 'heroku', 'supabase': 'supabase',
    'postman': 'postman', 'notion': 'notion',
    'airtable': 'airtable', 'linear': 'linear',
    
    # More AI
    'comfyui': 'comfyui', 'chroma': 'chroma', 'pinecone': 'pinecone',
    'weaviate': 'weaviate', 'qdrant': 'qdrant',
    'llamaindex': 'llamaindex',
    'bolt-new': 'boltdotnew',
    'lovable': 'lovable',
    'replit': 'replit',
    'krea-ai': 'krea', 'krea-2': 'krea',
    'pika': 'pika',
    'recraft': 'recraft',
    'play-ht': 'playdotht',
    'otter': 'otterdotai',
    'character-ai': 'characterdotai',
    
    # Creative
    'capcut-ai': 'capcut',
    'blender': 'blender',
    'unreal-engine': 'unrealengine',
    'unity': 'unity',
    
    # Other
    'android': 'android', 'arch-linux': 'archlinux',
    'ubuntu': 'ubuntu', 'debian': 'debian', 'fedora': 'fedora',
    'arduino': 'arduino', 'raspberry-pi': 'raspberrypi',
    'firefox': 'firefox', 'chrome': 'googlechrome', 'brave': 'brave',
    'tor': 'torproject', 'signal': 'signal',
    'binance': 'binance', 'coinbase': 'coinbase',
    'wikimedia': 'wikimediafoundation',
    'wordpress': 'wordpress', 'drupal': 'drupal',
    'stack-overflow': 'stackoverflow', 'quora': 'quora',
    'uber': 'uber', 'airbnb': 'airbnb', 'lyft': 'lyft',
    'doordash': 'doordash',
    'sonos': 'sonos',
}

# Alternative logo.svgcdn.com mappings for brands not in Simple Icons
SVGCDN_MAP = {
    'midjourney': 'midjourney',
    'midjourney-scanner': 'midjourney',
    'cursor': 'cursor',
    'lovable': 'lovable',
    'bolt': 'bolt.new',
}

# Direct attempts for high-priority brands
DIRECT_URLS = {
    'midjourney': 'https://logo.svgcdn.com/logos/midjourney.svg',
    'midjourney-scanner': 'https://logo.svgcdn.com/logos/midjourney.svg',
}


def load_tool_slugs():
    with open(TOOLS_PATH, encoding='utf-8') as f:
        return {t['slug'] for t in json.load(f)}


def is_broken(filepath):
    """Check if the icon file is broken (HTML, ICO, or wrong format)"""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        with open(filepath, 'rb') as f:
            head = f.read(20)
    except:
        return True
    
    # HTML content
    if head[:15].lower().startswith(b'<!doctype html') or head[:5].lower().startswith(b'<html'):
        return True
    
    # ICO format (Windows icon, not renderable by browsers)
    if head[:4] in (b'\x00\x00\x01\x00', b'\x00\x00\x02\x00'):
        return True
    
    # PNG-in-SVG or binary-in-SVG
    if ext == '.svg' and not (head.startswith(b'<svg') or head.startswith(b'<?xml')):
        return True
    
    # PNG with non-PNG header
    if ext == '.png' and head[:4] != b'\x89PNG':
        return True
    
    return False


def save_icon(slug, data):
    """Save downloaded icon data, auto-detect SVG vs PNG"""
    ext = '.svg' if (data.startswith(b'<svg') or data.startswith(b'<?xml')) else '.png'
    path = os.path.join(ICON_DIR, f'{slug}{ext}')
    with open(path, 'wb') as f:
        f.write(data)
    return ext


def download_url(url):
    """Download icon from URL and return data"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.read()
    except Exception as e:
        return None


def main():
    dry_run = '--dry-run' in sys.argv
    tool_slugs = load_tool_slugs()
    
    print("=" * 70)
    print("  全量图标修复：删除损坏 + 下载真品牌 SVG")
    if dry_run:
        print("  ⚠️ DRY RUN")
    print("=" * 70)
    
    # ========================================
    # STEP 1: 扫描并删除所有损坏图标
    # ========================================
    deleted = []
    for f in sorted(os.listdir(ICON_DIR)):
        slug = os.path.splitext(f)[0]
        if slug not in tool_slugs:
            continue
        path = os.path.join(ICON_DIR, f)
        if is_broken(path):
            if dry_run:
                deleted.append(f)
            else:
                try:
                    os.remove(path)
                    deleted.append(f)
                except:
                    print(f"  ⚠️ 无法删除 {f}")
    
    print(f"\n🗑️ 删除损坏图标: {len(deleted)} 个")
    if dry_run:
        for f in deleted[:10]:
            print(f"  [DRY] {f}")
        print(f"  ... 还有 {len(deleted)-10} 个" if len(deleted) > 10 else "")
    
    if not deleted and not dry_run:
        print("  ✅ 没有损坏文件")
    
    # ========================================
    # STEP 2: 从 Simple Icons 下载
    # ========================================
    print(f"\n📦 Step 2: Simple Icons 下载...")
    si_fixed = 0
    for slug, si_slug in sorted(SI_MAP.items()):
        if slug not in tool_slugs:
            continue
        # Skip if already has a good SVG
        svg_path = os.path.join(ICON_DIR, f'{slug}.svg')
        if os.path.exists(svg_path):
            # Verify it's actually SVG
            with open(svg_path, 'rb') as f:
                h = f.read(20)
            if h.startswith(b'<svg') or h.startswith(b'<?xml'):
                continue
        
        url = f'{SIMPLE_ICONS_BASE}/{si_slug}'
        if dry_run:
            si_fixed += 1
            continue
        
        data = download_url(url)
        if data and (data.startswith(b'<svg') or data.startswith(b'<?xml')):
            save_icon(slug, data)
            si_fixed += 1
            if si_fixed % 10 == 0:
                print(f"  ... {si_fixed} 个")
            time.sleep(0.05)  # Rate limit
    
    print(f"  ✅ Simple Icons: {si_fixed} 个" + (' (dry-run)' if dry_run else ''))
    
    # ========================================
    # STEP 3: 从 logo.svgcdn.com 下载
    # ========================================
    print(f"\n📦 Step 3: logo.svgcdn.com 下载...")
    svgcdb_fixed = 0
    for slug, brand in sorted(SVGCDN_MAP.items()):
        if slug not in tool_slugs:
            continue
        svg_path = os.path.join(ICON_DIR, f'{slug}.svg')
        if os.path.exists(svg_path):
            continue
        
        url = f'{LOGO_SVGCDN_BASE}/{brand}.svg'
        if dry_run:
            svgcdb_fixed += 1
            continue
        
        data = download_url(url)
        if data and (data.startswith(b'<svg') or data.startswith(b'<?xml')):
            save_icon(slug, data)
            svgcdb_fixed += 1
    
    print(f"  ✅ logo.svgcdn: {svgcdb_fixed} 个" + (' (dry-run)' if dry_run else ''))
    
    # ========================================
    # STEP 4: 直接 URL 下载
    # ========================================
    print(f"\n📦 Step 4: 直接 URL 下载...")
    direct_fixed = 0
    for slug, url in sorted(DIRECT_URLS.items()):
        if slug not in tool_slugs:
            continue
        svg_path = os.path.join(ICON_DIR, f'{slug}.svg')
        if os.path.exists(svg_path):
            continue
        
        if dry_run:
            direct_fixed += 1
            continue
        
        data = download_url(url)
        if data and (data.startswith(b'<svg') or data.startswith(b'<?xml')):
            save_icon(slug, data)
            direct_fixed += 1
    
    print(f"  ✅ Direct: {direct_fixed} 个" + (' (dry-run)' if dry_run else ''))
    
    # ========================================
    # Final stats
    # ========================================
    print(f"\n{'='*70}")
    total_deleted = len(deleted)
    total_fixed = si_fixed + svgcdb_fixed + direct_fixed
    print(f"  删除: {total_deleted} | 修复: {total_fixed}")
    
    if not dry_run:
        # Count remaining valid files
        valid = 0
        for f in os.listdir(ICON_DIR):
            slug = os.path.splitext(f)[0]
            if slug not in tool_slugs:
                continue
            if not is_broken(os.path.join(ICON_DIR, f)):
                valid += 1
        print(f"  当前有效图标: {valid}/{len(tool_slugs)}")
    
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
