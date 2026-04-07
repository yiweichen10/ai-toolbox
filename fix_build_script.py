path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '''    # 使用pypinyin生成拼音，并转换为连字符连接的小写形式
    pinyin_list = pinyin(category_name, style=Style.NORMAL)
    slug = '-'.join([item[0] for item in pinyin_list if item and item[0].strip()]).lower()'''

new_block = '''    # Using pypinyin if available, otherwise fallback
    if pinyin:
        pinyin_list = pinyin(category_name, style=Style.NORMAL)
        slug = '-'.join([item[0] for item in pinyin_list if item and item[0].strip()]).lower()
    else:
        slug = category_name.lower()'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed build.py pinyin call")
else:
    # Try with \r\n
    old_block_crlf = old_block.replace('\n', '\r\n')
    if old_block_crlf in content:
        content = content.replace(old_block_crlf, new_block.replace('\n', '\r\n'))
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Fixed build.py pinyin call (CRLF)")
    else:
        print("Could not find block in build.py")
