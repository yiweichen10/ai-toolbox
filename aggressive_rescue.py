import re
path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\generate_articles.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the most common broken string endings: ?, at the end of a line
# and similar issues
content = re.sub(r'([^\"])\?,?\n', r'\1",\n', content)
content = re.sub(r'([^\"])\?,\n', r'\1",\n', content)
content = re.sub(r'([^\"])\?\n', r'\1"\n', content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Aggressive rescue of generate_articles.py performed.")
