path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\generate_articles.py'
with open(path, 'rb') as f:
    lines = f.readlines()

if b'coding: utf-8' not in lines[0] and b'coding: utf-8' not in lines[1]:
    # Insert at line 2
    lines.insert(1, b'# -*- coding: utf-8 -*-\n')
    with open(path, 'wb') as f:
        f.writelines(lines)
    print("Added encoding declaration to generate_articles.py")
else:
    print("Encoding declaration already exists")
