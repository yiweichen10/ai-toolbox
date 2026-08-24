path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\generate_articles.py'
with open(path, 'rb') as f:
    content_bytes = f.read()

# Attempt to decode as utf-8, ignoring errors
content_fixed = content_bytes.decode('utf-8', errors='ignore')

# Fix the broken quote at the end of some lines (often due to truncation or bad replacement)
content_fixed = content_fixed.replace('",\ufffd?', '",')
content_fixed = content_fixed.replace('",?', '",')
content_fixed = content_fixed.replace('",\ufffd', '",')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content_fixed)

print("Rescued generate_articles.py (cleaned invalid bytes)")
