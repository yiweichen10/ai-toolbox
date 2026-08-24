import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
build_py = os.path.join(BASE_DIR, 'scripts', 'build.py')

with open(build_py, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修复 CSS 渲染阻塞
css_orig = r'(^[ \t]*.*?)(<link rel="stylesheet" href="/css/style.css">)(.*?)$'
css_new = r'\1<link rel="preload" href="/css/style.css" as="style">\3\n\1<link rel="stylesheet" href="/css/style.css" media="print" onload="this.media=&quot;all&quot;">\3\n\1<noscript><link rel="stylesheet" href="/css/style.css"></noscript>\3'
content = re.sub(css_orig, css_new, content, flags=re.MULTILINE)

# 2. 为文章页添加 Markdown alternate
canonical_orig = r'<link rel="canonical" href="https://www.aitoollab.cn/articles/\{slug\}/">'
canonical_new = r'<link rel="canonical" href="https://www.aitoollab.cn/articles/{slug}/">\n    <link rel="alternate" type="text/markdown" href="https://www.aitoollab.cn/articles/{slug}/{slug}.md">'
content = re.sub(canonical_orig, canonical_new, content)

# 3. 增强 GEO Schema：添加 Dataset (如果包含特定关键词或表格)
# We can inject this safely right before schema generation.
# In build_article_page, there is:
# structured_data = json.dumps(structured_data_dict, ensure_ascii=False)
schema_orig = "structured_data = json.dumps(structured_data_dict, ensure_ascii=False)"
schema_new = """
    # GEO 增强: 如果正文包含评测/对比/表格数据，则注入 Dataset
    _text_lower = article.get('content', '').lower()
    if '<table>' in _text_lower or '评测' in _text_lower or '对比' in _text_lower:
        structured_data_dict['@graph'] = structured_data_dict.get('@graph', [])
        if not structured_data_dict['@graph']:
            # 如果原本没有 graph，先把原本的自己放进去
            _self_copy = structured_data_dict.copy()
            _self_copy.pop('@graph', None)
            structured_data_dict.clear()
            structured_data_dict['@context'] = "https://schema.org"
            structured_data_dict['@graph'] = [_self_copy]
        
        structured_data_dict['@graph'].append({
            "@type": "Dataset",
            "name": f"{escape_html(article['title'])} 评测数据集",
            "description": f"本文中包含的AI工具客观评测及对比数据。{escape_html(article.get('description', ''))}",
            "url": f"https://www.aitoollab.cn/articles/{slug}/",
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "creator": {
                "@type": "Organization",
                "name": "AI工具宝箱编辑组"
            }
        })
        
    structured_data = json.dumps(structured_data_dict, ensure_ascii=False)
"""
if "structured_data = json.dumps(structured_data_dict" in content:
    content = content.replace(schema_orig, schema_new.strip(), 1)
else:
    print("Schema replace string not found, skipping GEO Schema enhancement.")

# 4. 生成 markdown 文件
write_orig_1 = """        with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)"""
write_new_1 = """        with open(os.path.join(dir_path, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        try:
            import re as _re
            md_text = f"# {target_article.get('title', '')}\\n\\n" + target_article.get('content', '')
            md_text = _re.sub(r'<[^>]+>', ' ', md_text)
            with open(os.path.join(dir_path, f"{slug}.md"), 'w', encoding='utf-8') as f:
                f.write(md_text)
        except:
            pass"""
content = content.replace(write_orig_1, write_new_1)

write_orig_2 = """            with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(html)"""
write_new_2 = """            with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(html)
            try:
                import re as _re
                md_text = f"# {article.get('title', '')}\\n\\n" + article.get('content', '')
                md_text = _re.sub(r'<[^>]+>', ' ', md_text)
                with open(os.path.join(out_dir, f"{slug}.md"), 'w', encoding='utf-8') as f:
                    f.write(md_text)
            except:
                pass"""
content = content.replace(write_orig_2, write_new_2)

with open(build_py, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied to build.py successfully!")
