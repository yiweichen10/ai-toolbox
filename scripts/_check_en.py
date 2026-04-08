import sys
sys.stdout.reconfigure(encoding='utf-8')

def check(path, tests):
    c = open(path, encoding='utf-8').read()
    print(f'\n=== {path} ===')
    for name, cond in tests:
        print(f'  {name}: {"OK" if cond(c) else "FAIL"}')

check('en/index.html', [
    ('lang=en', lambda c: 'lang="en"' in c),
    ('AI Tool Lab', lambda c: 'AI Tool Lab' in c),
    ('hreflang', lambda c: 'hreflang' in c),
    ('no AI Tool Box CN', lambda c: 'AI\u5de5\u5177\u5b9d\u7b71' not in c),
    ('en/tools link', lambda c: '/en/tools/chatgpt/' in c),
])
check('en/tools/chatgpt/index.html', [
    ('lang=en', lambda c: 'lang="en"' in c),
    ('Pros heading', lambda c: 'Pros' in c),
    ('hreflang zh-CN', lambda c: 'hreflang' in c),
    ('no CN brand', lambda c: 'AI\u5de5\u5177\u5b9d\u7b71' not in c),
])
check('tools/chatgpt/index.html', [
    ('Chinese unchanged', lambda c: 'AI\u5de5\u5177\u5b9d\u7b71' in c),
    ('lang zh-CN', lambda c: 'zh-CN' in c),
])
