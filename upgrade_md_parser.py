import os

path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\scripts\build.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = 'def markdown_to_html(md):'
end_marker = "return '\\n'.join(result)"

start_idx = content.find(start_marker)
# Find the first occurrence of the end marker AFTER the start marker
end_idx = content.find(end_marker, start_idx)

if start_idx != -1 and end_idx != -1:
    new_func = r'''def markdown_to_html(md):
    """将Markdown转换为简单HTML (增强版)"""
    if not md:
        return ''
    # 统一换行符
    html = md.replace('\r\n', '\n')
    
    # 确保表格和标题前后有换行符，方便正则匹配
    html = re.sub(r'([^\n])\n\|', r'\1\n\n|', html)
    
    # 代码块
    html = re.sub(r'```(\w*)\n([\s\S]*?)```', lambda m: '<pre><code>' + m.group(2).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</code></pre>', html)
    
    # 表格 (改进正则，支持无前导换行的情况)
    def table_replace(m):
        header = m.group(1)
        sep = m.group(2)
        body = m.group(3)
        headers = [c.strip() for c in header.split('|') if c.strip()]
        rows = body.strip().split('\n')
        table = '<div class="table-container"><table><thead><tr>'
        for h in headers:
            table += f'<th>{h}</th>'
        table += '</tr></thead><tbody>'
        for row in rows:
            cells = [c.strip() for c in row.split('|') if c.strip()]
            if not cells: continue
            table += '<tr>'
            for c in cells:
                table += f'<td>{c}</td>'
            table += '</tr>'
        table += '</tbody></table></div>'
        return table
    html = re.sub(r'(?:^|\n)(\|.+\|)\n(\|[-:| ]+\|)\n((?:\|.+\|(?:$|\n))+)', table_replace, html)
    
    # 标题 (增加 # H1 支持)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    
    # 引用
    html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
    
    # 加粗/斜体/行内代码
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    
    # 链接
    html = re.sub(r'\[([^\]]+)\]\((/[^)]+)\)', r'<a href="\2">\1</a>', html)
    html = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', html)
    
    # 列表
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', html, flags=re.MULTILINE)
    html = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul>\1</ul>', html)
    
    # 分隔线
    html = html.replace('\n---\n', '\n<hr>\n')
    
    # 段落
    lines = html.split('\n')
    result = []
    in_p = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_p:
                result.append('</p>')
                in_p = False
            continue
            
        is_tag = (stripped.startswith('<h') or stripped.startswith('<ul') or 
                  stripped.startswith('</ul') or stripped.startswith('<li') or 
                  stripped.startswith('<table') or stripped.startswith('</table') or 
                  stripped.startswith('<div') or stripped.startswith('</div') or 
                  stripped.startswith('<pre') or stripped.startswith('</pre') or 
                  stripped.startswith('<blockquote') or stripped.startswith('</blockquote') or 
                  stripped.startswith('<hr'))
        
        if is_tag:
            if in_p:
                result.append('</p>')
                in_p = False
            result.append(line)
        else:
            if not in_p:
                result.append('<p>' + line)
                in_p = True
            else:
                result.append('<br>' + line)
    if in_p:
        result.append('</p>')
    return '\n'.join(result)'''
    
    # Replace the whole block
    final_content = content[:start_idx] + new_func + content[end_idx + len(end_marker):]
    with open(path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    print("Successfully upgraded markdown_to_html")
else:
    print(f"Markers not found: start={start_idx}, end={end_idx}")
