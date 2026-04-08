import os, sys
sys.stdout.reconfigure(encoding='utf-8')
checks = [
    'notion-ai-en-og.png',
    'ai-tools-that-make-money-2026-en-og.png',
    'best-free-ai-tools-2026-en-og.png',
    'chatgpt-en-og.png',
    'claude-en-og.png',
    'midjourney-en-og.png',
    'github-copilot-en-og.png',
]
for f in checks:
    p = os.path.join('images', 'og', f)
    status = 'OK' if os.path.exists(p) else 'MISSING'
    print(f'{f}: {status}')
