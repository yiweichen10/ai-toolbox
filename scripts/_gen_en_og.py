"""生成英文文章的OG图片"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OG_DIR   = os.path.join(BASE_DIR, 'images', 'og')

from gen_seo_images import make_article_og_image, generate_image

articles = json.load(open(os.path.join(DATA_DIR, 'articles_en.json'), encoding='utf-8'))

for a in articles:
    slug     = a['slug']
    out_path = os.path.join(OG_DIR, f'{slug}-og.png')
    if os.path.exists(out_path):
        print(f'[SKIP] {slug}-og.png already exists')
        continue
    print(f'[GEN]  {slug}-og.png ...')
    html = make_article_og_image(a)
    ok   = generate_image(html, out_path)
    print(f'  {"OK" if ok else "FAILED"}')
