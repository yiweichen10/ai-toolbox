"""
修复"字母图标"：tools.json 中的工具如果只有 PNG (icon.horse 单字母 favicon)，
从 Simple Icons CDN 下载高清品牌 SVG 替换。

用法: python scripts/fix_letter_icons.py [--dry-run]
"""
import os
import sys
import json
import urllib.request
import urllib.error

ICON_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets', 'icons')
SIMPLE_ICONS_BASE = 'https://cdn.jsdelivr.net/npm/simple-icons@latest/icons'

# Simple Icons slug 映射（我们的 slug → Simple Icons slug）
SI_MAP = {
    'amazon': 'amazon',
    'android': 'android',
    'apple': 'apple',
    'binance': 'binance',
    'canva': 'canva',
    'claude': 'claude',
    'cursor': 'cursor',
    'deepseek': 'deepseek',
    'discord': 'discord',
    'docker': 'docker',
    'figma': 'figma',
    'github': 'github',
    'github-copilot': 'githubcopilot',
    'google': 'google',
    'google-cloud': 'googlecloud',
    'grafana': 'grafana',
    'hugging-face': 'huggingface',
    'instagram': 'instagram',
    'intel': 'intel',
    'jetbrains': 'jetbrains',
    'kimi': 'kimi',
    'kubernetes': 'kubernetes',
    'linkedin': 'linkedin',
    'meta': 'meta',
    'microsoft': 'microsoft',
    'microsoft-copilot': 'microsoftcopilot',
    'mistral-ai': 'mistral',
    'netflix': 'netflix',
    'notion': 'notion',
    'nvidia': 'nvidia',
    'openai': 'openai',
    'paypal': 'paypal',
    'pinterest': 'pinterest',
    'postman': 'postman',
    'python': 'python',
    'quora': 'quora',
    'reddit': 'reddit',
    'rust': 'rust',
    'shopify': 'shopify',
    'slack': 'slack',
    'spotify': 'spotify',
    'stack-overflow': 'stackoverflow',
    'telegram': 'telegram',
    'tesla': 'tesla',
    'tiktok': 'tiktok',
    'twitch': 'twitch',
    'twitter': 'x',  # X/Twitter
    'uber': 'uber',
    'v0': 'v0',
    'whatsapp': 'whatsapp',
    'wordpress': 'wordpress',
    'youtube': 'youtube',
    'zoom': 'zoom',
}

# 特殊品牌不在 Simple Icons → 直接用 OpenAI / 其他可用 SVG 做 fallback
# 或用直接 URL
FALLBACK_MAP = {
    'chatgpt': 'openai',
    'chatgpt-work': 'openai',
    'midjourney': 'midjourney',  # 试试 Simple Icons
    'midjourney-scanner': 'midjourney',
    'perplexity': 'perplexity',
    'anthropic': 'anthropic',
    'anthropic-console': 'anthropic',
    'character-ai': 'characterdotai',
    'bolt-new': 'boltdotnew',
    'lovable': 'lovable',
    'windsurf': 'windsurf',
    'augment-code': 'augment',
    'devin': 'devin',
    'manus': 'manus',
    'cline': 'cline',
}

# 直接从 URL 下载（非 Simple Icons 格式）
DIRECT_URLS = {}


def load_tool_slugs():
    tools_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'tools.json')
    with open(tools_path, encoding='utf-8') as f:
        tools = json.load(f)
    return {t['slug'] for t in tools}


def download_icon(url, target_path):
    """下载 SVG，返回 (success, message)"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                data = resp.read()
                if not data.startswith(b'<svg') and not data.startswith(b'<?xml'):
                    return False, f'not SVG ({data[:50]})'
                with open(target_path, 'wb') as f:
                    f.write(data)
                return True, f'{len(data)}B'
            return False, f'HTTP {resp.status}'
    except urllib.error.HTTPError as e:
        return False, f'HTTP {e.code}'
    except Exception as e:
        return False, str(e)[:60]


def remove_old_pngs(slug):
    """删除所有旧 PNG"""
    removed = []
    for ext in ['.png', '.ico']:
        p = os.path.join(ICON_DIR, f'{slug}{ext}')
        if os.path.exists(p):
            os.remove(p)
            removed.append(f'{slug}{ext}')
    return removed


def main():
    dry_run = '--dry-run' in sys.argv
    
    # 只处理实际存在的工具
    tool_slugs = load_tool_slugs()
    
    # 确定需要修复的 slug：有 PNG 但无 SVG 的
    needs_fix = []
    for slug in sorted(tool_slugs):
        has_svg = os.path.exists(os.path.join(ICON_DIR, f'{slug}.svg'))
        has_png = os.path.exists(os.path.join(ICON_DIR, f'{slug}.png'))
        if has_png and not has_svg:
            needs_fix.append(slug)
    
    if not needs_fix:
        print("✅ 所有工具都已有 SVG 图标，无需修复")
        return 0
    
    print(f"⚠️ {len(needs_fix)} 个工具只有 PNG（可能是字母 favicon），尝试替换为 SVG")
    if dry_run:
        print("🔍 DRY RUN — 仅预览\n")
    
    fixed = 0
    skipped = 0
    failed = []
    
    for slug in needs_fix:
        svg_target = os.path.join(ICON_DIR, f'{slug}.svg')
        
        # Step 1: 查 Simple Icons 映射
        si_slug = SI_MAP.get(slug) or FALLBACK_MAP.get(slug)
        
        if si_slug:
            url = f'{SIMPLE_ICONS_BASE}/{si_slug}.svg'
            if dry_run:
                print(f"  [DRY] {slug} ← simple-icons:{si_slug}")
                fixed += 1
            else:
                ok, msg = download_icon(url, svg_target)
                if ok:
                    print(f"  ✅ {slug} ← simple-icons:{si_slug} ({msg}) — SVG优先于旧PNG")
                    fixed += 1
                else:
                    print(f"  ❌ {slug} ← simple-icons:{si_slug} → {msg}")
                    failed.append(f'{slug} (SI:{si_slug}: {msg})')
            continue
        
        # Step 2: 直接 URL
        direct_url = DIRECT_URLS.get(slug)
        if direct_url:
            if dry_run:
                print(f"  [DRY] {slug} ← direct")
                fixed += 1
            else:
                ok, msg = download_icon(direct_url, svg_target)
                if ok:
                    print(f"  ✅ {slug} ← direct ({msg}) — SVG优先于旧PNG")
                    fixed += 1
                else:
                    print(f"  ❌ {slug} ← direct → {msg}")
                    failed.append(f'{slug} (direct: {msg})')
            continue
        
        # Step 3: 无来源，跳过
        skipped += 1
    
    print(f"\n{'='*60}")
    print(f"  结果: {fixed} 修复" + (' (dry-run)' if dry_run else '') + f", {skipped} 跳过(无来源), {len(failed)} 失败")
    if failed:
        for f in failed[:10]:
            print(f"    ❌ {f}")
    print(f"{'='*60}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
