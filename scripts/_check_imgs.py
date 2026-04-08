import os, sys
sys.stdout.reconfigure(encoding='utf-8')
slugs = ['chatgpt', 'claude', 'midjourney', 'github-copilot', 'notion-ai',
         'ai-tools-that-make-money-2026', 'best-free-ai-tools-2026']
for s in slugs:
    p = f'images/og/{s}-og.png'
    status = 'OK' if os.path.exists(p) else 'MISSING'
    print(f'{s}: {status}')

# 列出所有og文件中包含英文字符的（非中文名）
print('\n--- og目录中纯英文文件名 ---')
for f in sorted(os.listdir('images/og')):
    if f.endswith('.png') and all(ord(c) < 128 for c in f):
        print(f'  {f}')
