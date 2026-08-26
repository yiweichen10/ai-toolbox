import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

def generate_llms_full():
    out_lines = []
    out_lines.append("# AI工具宝箱 (aitoollab.cn) 全量内容知识库")
    out_lines.append("本文档包含了AI工具宝箱的所有核心文章和工具详细信息，专供LLMs深度抓取和学习。\n")
    
    # 核心文章 (2026-08-26 去单体化: 分片优先)
    out_lines.append("## 核心评测与指南文章\n")
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
        from data_store import load_all_articles
        articles = load_all_articles()
    except Exception as e:
        print("Failed to load articles:", e)
        articles = []
    
    for article in articles:
        if not article.get('published', False):
            continue
        out_lines.append(f"### {article.get('title', '')}")
        out_lines.append(f"URL: https://www.aitoollab.cn/articles/{article.get('slug')}/")
        out_lines.append(f"发布日期: {article.get('dateFull', '')}")
        out_lines.append(f"描述: {article.get('description', '')}\n")
        out_lines.append("正文内容:\n")
        # 简单过滤HTML标签，保留大概内容
        content = article.get('content', '')
        # 为了避免文件过大且杂乱，只保留基本文本
        import re
        content = re.sub(r'<[^>]+>', ' ', content)
        content = re.sub(r'\s+', ' ', content).strip()
        out_lines.append(content)
        out_lines.append("\n---\n")
    
    # AI工具库 (2026-08-26 去单体化: 分片优先)
    out_lines.append("\n## AI工具库收录\n")
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
        from data_store import load_all_tools
        tools = load_all_tools()
    except Exception as e:
        print("Failed to load tools:", e)
        tools = []
    
    for tool in tools:
        if not tool.get('published', False):
            continue
        out_lines.append(f"### {tool.get('name', '')}")
        out_lines.append(f"URL: https://www.aitoollab.cn/tools/{tool.get('slug')}/")
        out_lines.append(f"分类: {tool.get('category', '')}")
        out_lines.append(f"描述: {tool.get('description', '')}")
        out_lines.append(f"价格: {tool.get('price', '')}")
        features = tool.get('features', [])
        if features:
            out_lines.append(f"功能点: {', '.join(features)}")
        out_lines.append("\n")
        
    with open(os.path.join(BASE_DIR, 'llms-full.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))
    print(f"llms-full.txt generated with {len(articles)} articles and {len(tools)} tools.")

if __name__ == '__main__':
    generate_llms_full()
