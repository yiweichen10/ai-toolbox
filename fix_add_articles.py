import os
path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\add_articles.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if 'ARTICLES_TO_ADD.append({' in line:
        new_lines.append('        meta = drafts[slug]\n')
        new_lines.append('        entry = meta.copy()\n')
        new_lines.append('        entry["content"] = humanized_content\n')
        new_lines.append('        if "type" in entry: del entry["type"]\n')
        new_lines.append('        if "prompt" in entry: del entry["prompt"]\n')
        new_lines.append('        ARTICLES_TO_ADD.append(entry)\n')
        skip = True
    elif skip and '})' in line:
        skip = False
    elif not skip:
        # Avoid duplicate meta line if I added it above
        if 'meta = drafts[slug]' in line and 'if slug in drafts:' in lines[new_lines.__len__()-1 if new_lines else 0]:
             continue
        new_lines.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Fixed add_articles.py to preserve all metadata.")
