import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
build_py = os.path.join(BASE_DIR, 'scripts', 'build.py')

with open(build_py, 'r', encoding='utf-8') as f:
    content = f.read()

schema_orig = "structured_data = json.dumps(article_schema_data, ensure_ascii=False, indent=2)"
schema_new = """    # GEO 增强: 注入 Dataset 和 citations
    _text_lower = article.get('content', '').lower()
    
    import re as _re_cit
    if _re_cit.search(r'\\[\\d+\\]', _text_lower) or '引用' in _text_lower:
        article_schema_data['citation'] = article_schema_data.get('citation', [])
        article_schema_data['citation'].append({
            "@type": "CreativeWork",
            "name": "参考与实测来源"
        })

    if '<table>' in _text_lower or '评测' in _text_lower or '对比' in _text_lower:
        if '@graph' not in article_schema_data:
            _self_copy = article_schema_data.copy()
            _self_copy.pop('@graph', None)
            article_schema_data.clear()
            article_schema_data['@context'] = "https://schema.org"
            article_schema_data['@graph'] = [_self_copy]
        
        article_schema_data['@graph'].append({
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
        
    structured_data = json.dumps(article_schema_data, ensure_ascii=False, indent=2)"""

if schema_orig in content:
    content = content.replace(schema_orig, schema_new, 1)
    with open(build_py, 'w', encoding='utf-8') as f:
        f.write(content)
    print("GEO Schema enhanced successfully!")
else:
    print("Could not find the target string for schema.")
