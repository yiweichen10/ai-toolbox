import json

a = json.load(open('data/articles.json', 'r', encoding='utf-8'))
for i, art in enumerate(a):
    cat = art.get('category', '?')
    title = art['title'][:60]
    slug = art['slug']
    print(f'{i+1}. [{cat}] {title}')
    print(f'   slug: {slug}')
