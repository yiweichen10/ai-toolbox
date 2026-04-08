import sys, re
sys.stdout.reconfigure(encoding='utf-8')

def check_og(path, label):
    c = open(path, encoding='utf-8').read()
    og_url = re.search(r'property="og:url"\s+content="([^"]+)"', c)
    og_img = re.search(r'property="og:image"\s+content="([^"]+)"', c)
    tw_img = re.search(r'name="twitter:image"\s+content="([^"]+)"', c)
    print(f'\n{label}')
    print(f'  og:url   = {og_url.group(1) if og_url else "MISSING"}')
    print(f'  og:image = {og_img.group(1) if og_img else "MISSING"}')
    print(f'  tw:image = {tw_img.group(1) if tw_img else "MISSING"}')

check_og('en/tools/chatgpt/index.html', 'Tool page (chatgpt)')
check_og('en/articles/ai-tools-that-make-money-2026/index.html', 'Article page')
check_og('en/index.html', 'Homepage')
