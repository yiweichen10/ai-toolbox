#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEO图片生成脚本 - 为工具页生成信息图和OG Image
生成两种图片：
1. 工具功能信息图 (1200x630) - 用于文章内嵌和图片搜索
2. OG Image (1200x630) - 用于社交分享

图片内容：工具功能亮点、对比表格、评分等（不是页面截图）
"""
import httpx
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')

API = "https://html2png.dev/api/convert"

def escape_html(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def make_tool_infographic(tool, all_tools):
    """生成工具功能信息图 - 1200x630"""
    name = tool['name']
    emoji = tool.get('emoji', '🛠️')
    color = tool.get('color', '#667eea')
    desc = tool.get('description', '')
    category = tool.get('category', '')
    rating = tool.get('rating', '⭐ 4.5')
    price = tool.get('price', '')
    platform = tool.get('platform', '')
    features = tool.get('features', [])[:6]
    pros = tool.get('pros', [])[:3]

    # 截取描述前60字
    short_desc = desc[:60] + ('...' if len(desc) > 60 else '')

    # 功能网格
    feat_html = ''
    for i, f in enumerate(features):
        feat_html += f'''<div class="feat-item">
            <div class="feat-dot" style="background:{color};"></div>
            <span>{escape_html(f)}</span>
        </div>\n'''

    # 优点列表
    pros_html = ''.join(f'<div class="pro-item">+ {escape_html(p)}</div>\n' for p in pros)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;600;700;900&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ margin:0; width:1200px; height:630px; font-family:"Noto Sans SC",sans-serif; background:#0f172a; }}
.card {{
  width:1200px; height:630px;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  display:flex; position:relative; overflow:hidden;
}}
/* 左侧色带 */
.accent-bar {{
  width:8px; height:630px; background:{color}; flex-shrink:0;
}}
/* 主内容 */
.content {{
  flex:1; padding:40px 50px; display:flex; flex-direction:column;
}}
/* 头部 */
.header {{ display:flex; align-items:center; gap:20px; margin-bottom:24px; }}
.tool-icon {{
  width:72px; height:72px; border-radius:18px; background:{color};
  display:flex; align-items:center; justify-content:center; font-size:36px;
}}
.header-text {{ flex:1; }}
.tool-name {{
  color:#f8fafc; font-size:32px; font-weight:900; line-height:1.3;
}}
.tool-meta {{
  color:#94a3b8; font-size:14px; margin-top:4px;
  display:flex; gap:16px;
}}
.meta-tag {{
  background:#1e293b; border:1px solid #334155; border-radius:6px;
  padding:3px 10px; font-size:12px; color:#cbd5e1;
}}
/* 描述 */
.desc {{
  color:#e2e8f0; font-size:15px; line-height:1.6; margin-bottom:24px;
  max-width:700px;
}}
/* 评分和价格 */
.stats {{
  display:flex; gap:20px; margin-bottom:24px;
}}
.stat-card {{
  background:#1e293b; border:1px solid #334155; border-radius:10px;
  padding:12px 20px; text-align:center;
}}
.stat-value {{ color:#f8fafc; font-size:20px; font-weight:700; }}
.stat-label {{ color:#64748b; font-size:11px; margin-top:2px; }}
/* 功能网格 */
.section-title {{
  color:#94a3b8; font-size:12px; font-weight:700; letter-spacing:2px;
  margin-bottom:12px; text-transform:uppercase;
}}
.features-grid {{
  display:grid; grid-template-columns:1fr 1fr; gap:6px 24px; margin-bottom:16px;
}}
.feat-item {{
  display:flex; align-items:center; gap:8px;
  color:#cbd5e1; font-size:13px;
}}
.feat-dot {{ width:6px; height:6px; border-radius:50%; flex-shrink:0; }}
/* 右侧优点面板 */
.side-panel {{
  width:260px; background:#1e293b; border-left:1px solid #334155;
  padding:30px 24px; display:flex; flex-direction:column;
}}
.side-title {{
  color:#94a3b8; font-size:11px; font-weight:700; letter-spacing:2px;
  margin-bottom:16px;
}}
.pro-item {{
  color:#4ade80; font-size:13px; line-height:1.8; font-weight:500;
}}
/* 底部品牌 */
.brand {{
  position:absolute; bottom:16px; right:24px;
  color:#475569; font-size:12px;
}}
</style></head>
<body>
<div class="card">
  <div class="accent-bar"></div>
  <div class="content">
    <div class="header">
      <div class="tool-icon">{emoji}</div>
      <div class="header-text">
        <div class="tool-name">{escape_html(name)}</div>
        <div class="tool-meta">
          <span class="meta-tag">{escape_html(category)}</span>
          <span class="meta-tag">{escape_html(platform)}</span>
          <span class="meta-tag" style="color:{color};border-color:{color};">{rating}</span>
        </div>
      </div>
    </div>
    <div class="desc">{escape_html(short_desc)}</div>
    <div class="stats">
      <div class="stat-card">
        <div class="stat-value" style="color:{color};">{rating.replace('⭐ ', '')}/5</div>
        <div class="stat-label">用户评分</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{escape_html(price.split('+')[0].split('/')[0].strip())}</div>
        <div class="stat-label">起步价格</div>
      </div>
    </div>
    <div class="section-title">核心功能</div>
    <div class="features-grid">{feat_html}</div>
  </div>
  <div class="side-panel">
    <div class="side-title">核心优势</div>
    {pros_html}
    <div style="flex:1;"></div>
    <div style="margin-top:auto;">
      <div style="color:#64748b;font-size:11px;margin-bottom:8px;">访问官网</div>
      <div style="color:{color};font-size:14px;font-weight:600;word-break:break-all;">{escape_html(tool.get('url', '').replace('https://', ''))}</div>
    </div>
  </div>
  <div class="brand">AI工具宝箱 · aitoolbox.hk</div>
</div>
</body></html>'''
    return html


def make_og_image(tool, all_tools):
    """生成 OG Image - 1200x630，用于社交分享"""
    name = tool['name']
    emoji = tool.get('emoji', '🛠️')
    color = tool.get('color', '#667eea')
    category = tool.get('category', '')
    rating = tool.get('rating', '⭐ 4.5')
    price = tool.get('price', '')

    # 找到相关工具做对比
    related_names = []
    if tool.get('related'):
        for r_slug in tool['related'][:3]:
            r = next((t for t in all_tools if t['slug'] == r_slug), None)
            if r:
                related_names.append(r['name'])

    related_html = ' vs '.join(related_names) if related_names else ''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700;900&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ margin:0; width:1200px; height:630px; font-family:"Noto Sans SC",sans-serif; }}
.card {{
  width:1200px; height:630px;
  background: linear-gradient(135deg, {color}22 0%, {color}44 50%, {color}22 100%);
  display:flex; flex-direction:column; justify-content:center; align-items:center;
  position:relative; overflow:hidden;
}}
/* 背景装饰 */
.bg-circle {{
  position:absolute; border-radius:50%; opacity:0.08; background:{color};
}}
.c1 {{ width:400px; height:400px; top:-100px; right:-100px; }}
.c2 {{ width:300px; height:300px; bottom:-80px; left:-80px; }}
.c3 {{ width:200px; height:200px; top:50%; left:50%; transform:translate(-50%,-50%); }}
/* 内容 */
.content {{
  position:relative; z-index:1; text-align:center;
  padding:0 80px;
}}
.badge {{
  display:inline-block; background:{color}; color:#fff;
  padding:6px 20px; border-radius:20px;
  font-size:14px; font-weight:700; margin-bottom:24px;
}}
.emoji {{ font-size:64px; margin-bottom:16px; }}
.title {{
  color:#1e293b; font-size:56px; font-weight:900; line-height:1.3;
  margin-bottom:16px;
}}
.subtitle {{
  color:#475569; font-size:20px; font-weight:500; margin-bottom:24px;
}}
.info-row {{
  display:flex; justify-content:center; gap:24px;
}}
.info-item {{
  background:rgba(255,255,255,0.8); backdrop-filter:blur(10px);
  padding:10px 24px; border-radius:10px;
  font-size:16px; color:#334155; font-weight:600;
}}
.brand {{
  position:absolute; bottom:24px; right:40px;
  color:#64748b; font-size:14px; font-weight:600;
}}
</style></head>
<body>
<div class="card">
  <div class="bg-circle c1"></div>
  <div class="bg-circle c2"></div>
  <div class="bg-circle c3"></div>
  <div class="content">
    <div class="badge">{escape_html(category)}</div>
    <div class="emoji">{emoji}</div>
    <div class="title">{escape_html(name)} 深度评测</div>
    <div class="subtitle">{rating} · {escape_html(price)}</div>
    {"<div style='color:#64748b;font-size:16px;margin-top:8px;'>对比: " + escape_html(related_html) + "</div>" if related_html else ""}
  </div>
  <div class="brand">AI工具宝箱 · aitoolbox.hk</div>
</div>
</body></html>'''
    return html


def generate_image(html, output_path, width=1200, height=630):
    """调用 html2png API 生成图片"""
    try:
        r = httpx.post(
            f"{API}?width={width}&height={height}&deviceScaleFactor=2",
            content=html.encode('utf-8'),
            headers={"Content-Type": "text/html; charset=utf-8"},
            timeout=30
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                img_url = data["url"]
                img_r = httpx.get(img_url, timeout=30)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(img_r.content)
                return True
            else:
                print(f"  API error: {data}")
                return False
        else:
            print(f"  HTTP error: {r.status_code}")
            return False
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def make_article_infographic(article):
    """生成文章信息图 - 1200x630
    设计原则：去AI味 - 用数据说话，有观点，有人味
    """
    title = article.get('title', '')
    category = article.get('category', 'AI工具')
    date = article.get('dateFull', '')
    content = article.get('content', '')

    # 从文章中提取表格数据
    tables = []
    table_pattern = r'\n(\|.+\|)\n(\|[-:| ]+\|)\n((?:\|.+\|\n?)+)'
    import re
    for m in re.finditer(table_pattern, content):
        headers = [c.strip() for c in m.group(1).split('|') if c.strip()][:4]
        rows = m.group(3).strip().split('\n')[:3]
        table_data = {'headers': headers, 'rows': rows}
        tables.append(table_data)

    # 生成表格HTML（最多展示1个表格，精简版）
    table_html = ''
    if tables:
        t = tables[0]
        headers_html = ''.join(f'<th>{escape_html(h)}</th>' for h in t['headers'])
        rows_html = ''
        for row in t['rows'][:3]:
            cells = [c.strip() for c in row.split('|') if c.strip()][:4]
            rows_html += '<tr>' + ''.join(f'<td>{escape_html(c)}</td>' for c in cells) + '</tr>'
        table_html = f'''<table><thead><tr>{headers_html}</tr></thead><tbody>{rows_html}</tbody></table>'''

    # 提取文章中的关键数据点（数字+单位）
    numbers = re.findall(r'(\d+(?:\.\d+)?)([万亿%篇个次元份分钟小时])(?:\w*|)', content)
    stats_html = ''
    if numbers:
        stats_html = '<div class="stats-row">'
        for num, unit in numbers[:4]:
            stats_html += f'''<div class="stat-chip">
                <span class="stat-num">{num}</span>
                <span class="stat-unit">{escape_html(unit)}</span>
            </div>'''
        stats_html += '</div>'

    # 标题精简（取前30字）
    short_title = title[:30] + ('...' if len(title) > 30 else '')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;600;700;900&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ margin:0; width:1200px; height:630px; font-family:"Noto Sans SC",sans-serif; background:#0f172a; }}
.card {{
  width:1200px; height:630px;
  background: linear-gradient(160deg, #0f172a 0%, #1a2332 50%, #0f172a 100%);
  display:flex; position:relative; overflow:hidden;
}}
/* 左侧色带 */
.accent-bar {{
  width:6px; height:630px; background:linear-gradient(180deg, #f59e0b, #ef4444); flex-shrink:0;
}}
/* 内容区 */
.content {{
  flex:1; padding:36px 44px; display:flex; flex-direction:column;
}}
/* 头部 */
.header {{ margin-bottom:20px; }}
.category-tag {{
  display:inline-block; background:#1e293b; border:1px solid #334155;
  padding:3px 12px; border-radius:4px; font-size:12px; color:#94a3b8;
  margin-bottom:10px;
}}
.title {{
  color:#f8fafc; font-size:26px; font-weight:900; line-height:1.4;
  max-width:700px;
}}
/* 数据芯片 */
.stats-row {{
  display:flex; gap:10px; margin-bottom:20px; flex-wrap:wrap;
}}
.stat-chip {{
  background:#1e293b; border:1px solid #334155; border-radius:8px;
  padding:8px 16px; display:flex; align-items:baseline; gap:4px;
}}
.stat-num {{ color:#f59e0b; font-size:22px; font-weight:900; }}
.stat-unit {{ color:#94a3b8; font-size:13px; }}
/* 表格区 */
.table-section {{
  flex:1; background:#1e293b; border:1px solid #334155;
  border-radius:10px; padding:20px; overflow:hidden;
}}
.table-label {{
  color:#64748b; font-size:11px; font-weight:700; letter-spacing:1px;
  margin-bottom:12px;
}}
table {{
  width:100%; border-collapse:collapse; font-size:13px;
}}
th {{
  background:#0f172a; color:#e2e8f0; padding:8px 12px; text-align:left;
  font-weight:600; font-size:12px;
}}
td {{
  color:#cbd5e1; padding:7px 12px; border-bottom:1px solid #334155; font-size:12px;
}}
tr:last-child td {{ border-bottom:none; }}
/* 右侧观点面板 */
.side-panel {{
  width:240px; background:linear-gradient(180deg, #1a2332, #0f172a);
  border-left:1px solid #334155; padding:36px 20px;
  display:flex; flex-direction:column; justify-content:center;
}}
.insight-label {{
  color:#64748b; font-size:11px; font-weight:700; letter-spacing:1px;
  margin-bottom:16px;
}}
.insight-box {{
  background:#1e293b; border-left:3px solid #f59e0b;
  padding:14px 16px; border-radius:0 8px 8px 0; margin-bottom:14px;
}}
.insight-text {{
  color:#e2e8f0; font-size:13px; line-height:1.7; font-weight:500;
}}
.insight-source {{
  color:#64748b; font-size:11px; margin-top:8px;
}}
/* 底部品牌 */
.brand {{
  position:absolute; bottom:14px; left:24px;
  color:#334155; font-size:11px; letter-spacing:0.5px;
}}
</style></head>
<body>
<div class="card">
  <div class="accent-bar"></div>
  <div class="content">
    <div class="header">
      <div class="category-tag">{escape_html(category)} · {escape_html(date)}</div>
      <div class="title">{escape_html(short_title)}</div>
    </div>
    {stats_html}
    {f'''<div class="table-section">
      <div class="table-label">DATA</div>
      {table_html}
    </div>''' if table_html else '<div style="flex:1;"></div>'}
  </div>
  <div class="side-panel">
    <div class="insight-label">KEY INSIGHT</div>
    <div class="insight-box">
      <div class="insight-text">基于实测数据的客观分析</div>
      <div class="insight-source">实测 + 数据 + 经验</div>
    </div>
  </div>
  <div class="brand">AI工具宝箱 · aitoolbox.hk</div>
</div>
</body></html>'''
    return html


def make_article_og_image(article):
    """生成文章OG Image - 1200x630
    设计原则：观点鲜明，有吸引力，不像AI生成的
    """
    title = article.get('title', '')
    category = article.get('category', 'AI工具')
    date = article.get('dateFull', '')
    content = article.get('content', '')

    # 标题拆分（主标题+副标题）
    short_title = title[:22] + ('...' if len(title) > 22 else '')

    # 从文章提取一个最有价值的结论（最后一个##后面的内容，或最后一段）
    conclusion = ''
    # 尝试找"总结"部分
    summary_match = re.search(r'## 总结\s*\n([\s\S]*?)(?:$)', content)
    if summary_match:
        conclusion = summary_match.group(1).strip()
    # 取前80字
    conclusion = conclusion[:80] + ('...' if len(conclusion) > 80 else '') if conclusion else ''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700;900&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ margin:0; width:1200px; height:630px; font-family:"Noto Sans SC",sans-serif; }}
.card {{
  width:1200px; height:630px;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #334155 100%);
  display:flex; flex-direction:column; justify-content:center;
  position:relative; overflow:hidden; padding:60px 80px;
}}
/* 背景网格 */
.grid-bg {{
  position:absolute; inset:0; opacity:0.03;
  background-image: linear-gradient(#fff 1px, transparent 1px),
                    linear-gradient(90deg, #fff 1px, transparent 1px);
  background-size: 40px 40px;
}}
/* 内容 */
.badge {{
  display:inline-block; background:#f59e0b; color:#0f172a;
  padding:5px 14px; border-radius:4px;
  font-size:13px; font-weight:700; margin-bottom:28px; width:fit-content;
}}
.title {{
  color:#f8fafc; font-size:44px; font-weight:900; line-height:1.35;
  max-width:900px; margin-bottom:24px;
}}
.conclusion {{
  color:#94a3b8; font-size:17px; line-height:1.7;
  max-width:800px; margin-bottom:32px;
  border-left:3px solid #f59e0b; padding-left:20px;
}}
.meta-row {{
  display:flex; gap:20px; color:#64748b; font-size:14px;
}}
.brand {{
  position:absolute; bottom:24px; right:40px;
  color:#475569; font-size:13px; font-weight:600;
}}
</style></head>
<body>
<div class="card">
  <div class="grid-bg"></div>
  <div class="badge">{escape_html(category)}</div>
  <div class="title">{escape_html(short_title)}</div>
  {"<div class='conclusion'>" + escape_html(conclusion) + "</div>" if conclusion else ""}
  <div class="meta-row">
    <span>{escape_html(date)}</span>
    <span>·</span>
    <span>AI工具宝箱</span>
    <span>·</span>
    <span>aitoolbox.hk</span>
  </div>
  <div class="brand">AI工具宝箱</div>
</div>
</body></html>'''
    return html


def main():
    import re as _re
    # 加载工具数据
    with open(os.path.join(DATA_DIR, 'tools.json'), 'r', encoding='utf-8') as f:
        tools = json.load(f)

    # 加载文章数据
    articles = []
    articles_path = os.path.join(DATA_DIR, 'articles.json')
    if os.path.exists(articles_path):
        with open(articles_path, 'r', encoding='utf-8') as f:
            articles = json.load(f)

    print(f"共 {len(tools)} 个工具，{len(articles)} 篇文章，开始生成SEO图片...\n")

    success_count = 0

    # 生成工具页图片
    for tool in tools:
        slug = tool['slug']
        name = tool['name']
        print(f"[工具] {name}", flush=True)

        infographic_path = os.path.join(IMAGES_DIR, 'infographics', f'{slug}-infographic.png')
        print(f"  生成信息图...", end='', flush=True)
        infographic_html = make_tool_infographic(tool, tools)
        if generate_image(infographic_html, infographic_path):
            print(f" OK")
            success_count += 1
        else:
            print(f" FAIL")

        og_path = os.path.join(IMAGES_DIR, 'og', f'{slug}-og.png')
        print(f"  生成OG Image...", end='', flush=True)
        og_html = make_og_image(tool, tools)
        if generate_image(og_html, og_path):
            print(f" OK")
            success_count += 1
        else:
            print(f" FAIL")

    # 生成文章页图片
    if articles:
        print(f"\n--- 文章图片 ---")
        for article in articles:
            slug = article['slug']
            title = article.get('title', '')[:20]
            print(f"[文章] {title}...", flush=True)

            infographic_path = os.path.join(IMAGES_DIR, 'infographics', f'{slug}-infographic.png')
            print(f"  生成信息图...", end='', flush=True)
            infographic_html = make_article_infographic(article)
            if generate_image(infographic_html, infographic_path):
                print(f" OK")
                success_count += 1
            else:
                print(f" FAIL")

            og_path = os.path.join(IMAGES_DIR, 'og', f'{slug}-og.png')
            print(f"  生成OG Image...", end='', flush=True)
            og_html = make_article_og_image(article)
            if generate_image(og_html, og_path):
                print(f" OK")
                success_count += 1
            else:
                print(f" FAIL")

    total = len(tools) * 2 + len(articles) * 2
    print(f"\n完成! 生成 {success_count}/{total} 张图片")
    print(f"信息图目录: {os.path.join(IMAGES_DIR, 'infographics')}")
    print(f"OG Image目录: {os.path.join(IMAGES_DIR, 'og')}")


if __name__ == "__main__":
    main()
