
file_path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    # line indices are 0-based, so line 507 is index 506
    if 506 <= i <= 611:
        if line.startswith('        '):
            new_lines.append(line[4:])
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Done')
