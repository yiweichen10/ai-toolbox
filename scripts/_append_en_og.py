"""Append English OG image functions to gen_seo_images.py"""
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
target = os.path.join(BASE_DIR, 'scripts', 'gen_seo_images.py')

APPEND_CODE = r'''

# =============================================================================
# English OG image functions
# Images saved as {slug}-en-og.png — separate from Chinese {slug}-og.png
# =============================================================================

def make_og_image_en(tool, all_tools):
    """English OG Image for tool pages - 1200x630."""
    name       = tool['name']
    emoji      = tool.get('emoji', '\U0001f6e0\ufe0f')
    color      = tool.get('color', '#667eea')
    category   = tool.get('category', 'AI Tools')
    rating     = tool.get('rating', '\u2b50 4.5')
    price      = tool.get('price', '')
    desc       = tool.get('description', '')
    short_desc = desc[:90] + ('...' if len(desc) > 90 else '')

    related_names = []
    if tool.get('related'):
        for r_slug in tool['related'][:2]:
            r = next((t for t in all_tools if t['slug'] == r_slug), None)
            if r:
                related_names.append(r['name'])
    vs_html = ("<div class='vs-line'>vs " + escape_html(' &middot; '.join(related_names)) + "</div>") if related_names else ''

    pros = tool.get('pros', [])[:3]
    pros_html = ''.join('<div class="pro-item">&#10003; ' + escape_html(p[:50]) + '</div>' for p in pros)

    html = (
        '<!DOCTYPE html>\n'
        '<html lang="en"><head><meta charset="UTF-8">\n'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">\n'
        '<style>\n'
        '* { margin:0; padding:0; box-sizing:border-box; }\n'
        'body { margin:0; width:1200px; height:630px; font-family:"Inter",sans-serif; }\n'
        '.card {\n'
        '  width:1200px; height:630px;\n'
        '  background: linear-gradient(135deg, ' + color + '18 0%, ' + color + '30 50%, ' + color + '18 100%);\n'
        '  display:flex; flex-direction:column; justify-content:center; align-items:center;\n'
        '  position:relative; overflow:hidden;\n'
        '}\n'
        '.bg-circle { position:absolute; border-radius:50%; opacity:0.07; background:' + color + '; }\n'
        '.c1 { width:500px; height:500px; top:-150px; right:-150px; }\n'
        '.c2 { width:350px; height:350px; bottom:-100px; left:-100px; }\n'
        '.content { position:relative; z-index:1; text-align:center; padding:0 80px; max-width:1000px; }\n'
        '.badge {\n'
        '  display:inline-block; background:' + color + '; color:#fff;\n'
        '  padding:6px 22px; border-radius:20px;\n'
        '  font-size:13px; font-weight:700; letter-spacing:0.5px; margin-bottom:20px;\n'
        '  text-transform:uppercase;\n'
        '}\n'
        '.emoji { font-size:64px; margin-bottom:12px; line-height:1; }\n'
        '.title {\n'
        '  color:#1e293b; font-size:58px; font-weight:900; line-height:1.15;\n'
        '  margin-bottom:12px; letter-spacing:-1px;\n'
        '}\n'
        '.subtitle {\n'
        '  color:#475569; font-size:18px; font-weight:400; margin-bottom:16px;\n'
        '  max-width:700px; margin-left:auto; margin-right:auto; line-height:1.5;\n'
        '}\n'
        '.vs-line { color:#94a3b8; font-size:14px; margin-bottom:20px; }\n'
        '.info-row { display:flex; justify-content:center; gap:16px; margin-bottom:20px; }\n'
        '.info-item {\n'
        '  background:rgba(255,255,255,0.85);\n'
        '  padding:10px 24px; border-radius:10px;\n'
        '  font-size:15px; color:#334155; font-weight:600;\n'
        '}\n'
        '.pros-row { display:flex; justify-content:center; gap:12px; flex-wrap:wrap; }\n'
        '.pro-item {\n'
        '  background:rgba(255,255,255,0.7); border-radius:8px;\n'
        '  padding:6px 16px; font-size:13px; color:#334155; font-weight:500;\n'
        '}\n'
        '.brand { position:absolute; bottom:22px; right:36px; color:#64748b; font-size:13px; font-weight:600; }\n'
        '.domain { position:absolute; bottom:22px; left:36px; color:#94a3b8; font-size:13px; }\n'
        '</style></head>\n'
        '<body>\n'
        '<div class="card">\n'
        '  <div class="bg-circle c1"></div>\n'
        '  <div class="bg-circle c2"></div>\n'
        '  <div class="content">\n'
        '    <div class="badge">' + escape_html(category) + '</div>\n'
        '    <div class="emoji">' + emoji + '</div>\n'
        '    <div class="title">' + escape_html(name) + '</div>\n'
        '    <div class="subtitle">' + escape_html(short_desc) + '</div>\n'
        '    ' + vs_html + '\n'
        '    <div class="info-row">\n'
        '      <div class="info-item">' + rating + '</div>\n'
        '      <div class="info-item">' + escape_html(price.split('+')[0].strip()) + '</div>\n'
        '    </div>\n'
        '    <div class="pros-row">' + pros_html + '</div>\n'
        '  </div>\n'
        '  <div class="brand">AI Tool Lab</div>\n'
        '  <div class="domain">aitoolbox.hk</div>\n'
        '</div>\n'
        '</body></html>'
    )
    return html


def make_article_og_image_en(article):
    """English OG Image for article pages - 1200x630."""
    title    = article.get('title', '')
    category = article.get('category', 'AI Tools')
    date_str = article.get('dateFull', article.get('date', ''))
    desc     = article.get('description', '')
    short_desc = desc[:110] + ('...' if len(desc) > 110 else '')

    if ':' in title:
        main_title, sub_title = title.split(':', 1)
        main_title = main_title.strip()
        sub_title  = sub_title.strip()
    else:
        main_title = title[:50] + ('...' if len(title) > 50 else '')
        sub_title  = ''

    sub_html  = ('<div class="sub-title">' + escape_html(sub_title[:70]) + '</div>') if sub_title else ''
    desc_html = ('<div class="desc">' + escape_html(short_desc) + '</div>') if short_desc else ''

    html = (
        '<!DOCTYPE html>\n'
        '<html lang="en"><head><meta charset="UTF-8">\n'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">\n'
        '<style>\n'
        '* { margin:0; padding:0; box-sizing:border-box; }\n'
        'body { margin:0; width:1200px; height:630px; font-family:"Inter",sans-serif; }\n'
        '.card {\n'
        '  width:1200px; height:630px;\n'
        '  background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #334155 100%);\n'
        '  display:flex; flex-direction:column; justify-content:center;\n'
        '  position:relative; overflow:hidden; padding:64px 80px;\n'
        '}\n'
        '.grid-bg {\n'
        '  position:absolute; inset:0; opacity:0.025;\n'
        '  background-image: linear-gradient(#fff 1px, transparent 1px),\n'
        '                    linear-gradient(90deg, #fff 1px, transparent 1px);\n'
        '  background-size: 40px 40px;\n'
        '}\n'
        '.accent-line { position:absolute; left:0; top:0; bottom:0; width:6px; background:linear-gradient(180deg,#3b82f6,#8b5cf6); }\n'
        '.badge {\n'
        '  display:inline-flex; align-items:center; gap:8px;\n'
        '  background:#1e293b; border:1px solid #334155;\n'
        '  padding:5px 16px; border-radius:6px;\n'
        '  font-size:13px; color:#94a3b8; font-weight:600;\n'
        '  letter-spacing:0.3px; margin-bottom:28px; width:fit-content; text-transform:uppercase;\n'
        '}\n'
        '.badge-dot { width:6px; height:6px; border-radius:50%; background:#3b82f6; }\n'
        '.main-title {\n'
        '  color:#f8fafc; font-size:48px; font-weight:900; line-height:1.2;\n'
        '  max-width:900px; margin-bottom:10px; letter-spacing:-0.5px;\n'
        '}\n'
        '.sub-title {\n'
        '  color:#94a3b8; font-size:22px; font-weight:400; line-height:1.5;\n'
        '  max-width:800px; margin-bottom:20px;\n'
        '}\n'
        '.desc {\n'
        '  color:#64748b; font-size:16px; line-height:1.6;\n'
        '  max-width:750px; margin-bottom:32px;\n'
        '  border-left:3px solid #3b82f6; padding-left:18px;\n'
        '}\n'
        '.meta-row { display:flex; gap:24px; align-items:center; }\n'
        '.meta-item { color:#475569; font-size:14px; font-weight:500; }\n'
        '.meta-sep { color:#334155; }\n'
        '.brand { position:absolute; bottom:26px; right:40px; color:#3b82f6; font-size:14px; font-weight:700; }\n'
        '</style></head>\n'
        '<body>\n'
        '<div class="card">\n'
        '  <div class="grid-bg"></div>\n'
        '  <div class="accent-line"></div>\n'
        '  <div class="badge"><span class="badge-dot"></span>' + escape_html(category.upper()) + '</div>\n'
        '  <div class="main-title">' + escape_html(main_title) + '</div>\n'
        '  ' + sub_html + '\n'
        '  ' + desc_html + '\n'
        '  <div class="meta-row">\n'
        '    <span class="meta-item">' + escape_html(date_str) + '</span>\n'
        '    <span class="meta-sep">&middot;</span>\n'
        '    <span class="meta-item">AI Tool Lab</span>\n'
        '    <span class="meta-sep">&middot;</span>\n'
        '    <span class="meta-item">aitoolbox.hk</span>\n'
        '  </div>\n'
        '  <div class="brand">AI Tool Lab</div>\n'
        '</div>\n'
        '</body></html>'
    )
    return html


def generate_en_og_images(force=False):
    """Generate English OG images for all EN tools/articles. Saves as {slug}-en-og.png."""
    tools_en_path    = os.path.join(DATA_DIR, 'tools_en.json')
    articles_en_path = os.path.join(DATA_DIR, 'articles_en.json')
    if not os.path.exists(tools_en_path):
        print('[EN OG] tools_en.json not found, skipping.')
        return
    if not os.path.exists(articles_en_path):
        print('[EN OG] articles_en.json not found, skipping.')
        return

    with open(tools_en_path,    encoding='utf-8') as f:
        tools_en = json.load(f)
    with open(articles_en_path, encoding='utf-8') as f:
        articles_en = json.load(f)

    published = [t for t in tools_en if t.get('published', False)]
    og_dir    = os.path.join(IMAGES_DIR, 'og')
    os.makedirs(og_dir, exist_ok=True)

    print(f'[EN OG] {len(published)} tools, {len(articles_en)} articles')
    success = skipped = 0

    for tool in published:
        slug     = tool['slug']
        out_path = os.path.join(og_dir, f'{slug}-en-og.png')
        if os.path.exists(out_path) and not force:
            print(f'  [SKIP] {slug}-en-og.png')
            skipped += 1
            continue
        print(f'  [GEN]  {slug}-en-og.png ...', end='', flush=True)
        ok = generate_image(make_og_image_en(tool, published), out_path)
        print(' OK' if ok else ' FAIL')
        if ok: success += 1

    for article in articles_en:
        slug     = article['slug']
        out_path = os.path.join(og_dir, f'{slug}-en-og.png')
        if os.path.exists(out_path) and not force:
            print(f'  [SKIP] {slug}-en-og.png')
            skipped += 1
            continue
        print(f'  [GEN]  {slug}-en-og.png ...', end='', flush=True)
        ok = generate_image(make_article_og_image_en(article), out_path)
        print(' OK' if ok else ' FAIL')
        if ok: success += 1

    print(f'[EN OG] Done: {success} generated, {skipped} skipped.')
'''

# Check if already appended
existing = open(target, encoding='utf-8').read()
if 'make_og_image_en' in existing:
    print('Already appended, skipping.')
else:
    with open(target, 'a', encoding='utf-8') as f:
        f.write(APPEND_CODE)
    print('Appended EN OG functions to gen_seo_images.py')
