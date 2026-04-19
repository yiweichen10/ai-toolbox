"""分析站点外链分布"""
import os, re, sys, json

sys.stdout.reconfigure(encoding='utf-8')
BASE = 'c:/Users/27040/WorkBuddy/20260321092139/seo-site'

def analyze_html(filepath, label):
    content = open(filepath, encoding='utf-8').read()
    title_match = re.search(r'<title>([^<]+)</title>', content)
    title = title_match.group(1) if title_match else label
    ext_links = re.findall(r'href="(https?://[^"]+)"', content)
    own = [l for l in ext_links if 'aitoolbox.hk' in l or 'aitoollab' in l]
    other = [l for l in ext_links if 'aitoolbox.hk' not in l and 'aitoollab' not in l]
    
    # 检查 rel=nofollow
    nofollow_links = re.findall(r'href="(https?://[^"]+)"[^>]*rel="[^"]*nofollow', content)
    
    print(f'\n{label} ({title}):')
    print(f'  总外链: {len(ext_links)}')
    print(f'  站内链接: {len(own)}')
    print(f'  站外链接(无nofollow): {len(other) - len(nofollow_links)}')
    print(f'  站外链接(有nofollow): {len(nofollow_links)}')
    if other:
        unique_other = list(set(other))
        print(f'  站外链接(去重): {len(unique_other)}')
        for l in unique_other:
            has_nf = 'nofollow' in content[content.find(l)-50:content.find(l)+len(l)+50] if l in content else False
            print(f'    {"[NF]" if has_nf else "[DO]"} {l}')

# 1. 首页
analyze_html(os.path.join(BASE, 'index.html'), '首页')

# 2. 工具页（抽样3个）
tool_dir = os.path.join(BASE, 'tools')
tools = sorted([d for d in os.listdir(tool_dir) if os.path.isdir(os.path.join(tool_dir, d))])
for t in tools[:3]:
    fp = os.path.join(tool_dir, t, 'index.html')
    if os.path.exists(fp):
        analyze_html(fp, f'工具页/{t}')

# 3. 文章页（抽样2个）
art_dir = os.path.join(BASE, 'articles')
article_dirs = []
for root, dirs, files in os.walk(art_dir):
    for f in files:
        if f == 'index.html':
            article_dirs.append(root)
    if len(article_dirs) >= 5:
        break

for ad in sorted(article_dirs)[:2]:
    analyze_html(os.path.join(ad, 'index.html'), f'文章页/{os.path.basename(ad)}')

# 4. 全站统计
print('\n' + '='*60)
print('全站外链汇总:')
total_own = 0
total_other = 0
total_nofollow = 0
total_pages = 0

for root, dirs, files in os.walk(BASE):
    # 跳过不需要的目录
    skip = any(s in root for s in ['node_modules', '.git', 'scripts', 'data', '_archive', '__pycache__', '.workbuddy', '.codebuddy'])
    if skip:
        continue
    for f in files:
        if f == 'index.html':
            fp = os.path.join(root, f)
            try:
                content = open(fp, encoding='utf-8').read()
                ext_links = re.findall(r'href="(https?://[^"]+)"', content)
                own = [l for l in ext_links if 'aitoolbox.hk' in l or 'aitoollab' in l]
                other = [l for l in ext_links if 'aitoolbox.hk' not in l and 'aitoollab' not in l]
                total_own += len(own)
                total_other += len(other)
                total_pages += 1
            except:
                pass

print(f'  总页面数: {total_pages}')
print(f'  总站内链接: {total_own}')
print(f'  总站外链接: {total_other}')
print(f'  平均每页站外链接: {total_other/max(total_pages,1):.1f}')
print(f'  外链占比: {total_other/(total_own+total_other)*100:.1f}%')
