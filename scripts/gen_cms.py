#!/usr/bin/env python3
"""gen_cms.py — 生成 AI CMS 仪表盘 cms.html
读取全站数据，生成自包含的静态仪表盘 HTML。
使用: python scripts/gen_cms.py
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT = os.path.join(BASE_DIR, 'cms.html')

PIPELINE_FILE = os.path.join(DATA_DIR, '_pipeline.json')

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def ensure_pipeline():
    """读取或创建流水线状态文件"""
    today = datetime.now(CST).strftime('%Y-%m-%d')
    data = load_json(PIPELINE_FILE)
    if not data or data.get('today') != today:
        data = {
            "today": today,
            "refreshed_at": datetime.now(CST).isoformat(),
            "tasks": [
                {"time": "--:--", "task_id": "seo_article",  "task_name": "SEO 文章",   "status": "pending", "title": "", "detail": ""},
                {"time": "--:--", "task_id": "dict_release", "task_name": "AI 词典",    "status": "pending", "title": "", "detail": ""},
                {"time": "--:--", "task_id": "ai_news",      "task_name": "AI 动态",    "status": "pending", "title": "", "detail": ""},
                {"time": "--:--", "task_id": "tool_release", "task_name": "工具发布",   "status": "pending", "title": "", "detail": ""},
            ]
        }
        with open(PIPELINE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def gather_data():
    """收集全站统计数据"""
    now = datetime.now(CST)
    today = now.strftime('%Y-%m-%d')

    # 2026-08-26 去单体化: tools/articles/dict_terms 读分片, 其余文件仍单文件
    try:
        from data_store import load_all_tools, load_all_articles, load_all_dict_terms
        tools = load_all_tools()
        articles = load_all_articles()
        dict_terms = load_all_dict_terms()
    except Exception:
        tools = load_json(os.path.join(DATA_DIR, 'tools.json')) or []
        articles = load_json(os.path.join(DATA_DIR, 'articles.json')) or []
        dict_terms = load_json(os.path.join(DATA_DIR, 'dict_terms.json')) or []
    subcats = load_json(os.path.join(DATA_DIR, 'subcategories.json')) or []
    compare = load_json(os.path.join(DATA_DIR, 'compare_data.json')) or {}

    # Published counts
    pub_tools = [t for t in tools if t.get('published', True)]
    pub_dict = [d for d in dict_terms if d.get('published', True)]
    cats = set(t.get('category', '') for t in pub_tools if t.get('category'))

    # News files
    import glob
    news_files = sorted(glob.glob(os.path.join(DATA_DIR, 'news_*.json')))
    news_dates = [os.path.basename(f).replace('news_', '').replace('.json', '') for f in news_files]

    # PSEO pages
    compares = compare.get('compares', [])
    alternatives = compare.get('alternatives', [])
    quiz = load_json(os.path.join(DATA_DIR, 'quiz_data.json')) or {}
    quizzes = quiz.get('quizzes', [])
    ranking = load_json(os.path.join(DATA_DIR, 'ranking_data.json')) or {}
    rankings = ranking.get('rankings', [])
    live = load_json(os.path.join(DATA_DIR, 'live_data.json')) or {}
    lives = live.get('live_pages', [])

    # Pipeline
    pipeline = ensure_pipeline()

    # URL health
    health = load_json(os.path.join(DATA_DIR, 'url_health_report.json'))

    # Articles sorted by date
    def article_date(a):
        d = a.get('date', '')
        try:
            if '-' in d and len(d) >= 10:
                return d[:10]
            elif '/' in d:
                m, d2 = d.split('/')
                return f"2026-{m.zfill(2)}-{d2.zfill(2)}"
        except:
            pass
        return '0000-00-00'
    articles.sort(key=article_date, reverse=True)

    # Latest 10 items
    latest_articles = articles[:10]
    latest_tools = [t for t in pub_tools if t.get('slug')][:10]

    # Size stats (2026-08-26 去单体化: tools/articles 为分片目录, 统计目录总大小)
    def file_size(path):
        try:
            if os.path.isdir(path):
                return sum(os.path.getsize(os.path.join(path, f)) for f in os.listdir(path) if f.endswith('.json'))
            return os.path.getsize(path)
        except Exception:
            return 0

    return {
        'generated_at': now.strftime('%Y-%m-%d %H:%M:%S CST'),
        'today': today,
        'counts': {
            'tools_total': len(tools),
            'tools_published': len(pub_tools),
            'tools_draft': len(tools) - len(pub_tools),
            'articles': len(articles),
            'dict_total': len(dict_terms),
            'dict_published': len(pub_dict),
            'categories': len(cats),
            'subcategories': len(subcats),
            'news_days': len(news_files),
            'news_latest_date': news_dates[-1] if news_dates else '—',
            'compares': len(compares),
            'alternatives': len(alternatives),
            'quizzes': len(quizzes),
            'rankings': len(rankings),
            'lives': len(lives),
            'pseo_total': len(compares) + len(alternatives) + len(quizzes) + len(rankings) + len(lives),
        },
        'pipeline': pipeline,
        'latest_articles': [{'title': a.get('title',''), 'slug': a.get('slug',''), 'date': a.get('date',''), 'description': a.get('description','')[:80]} for a in latest_articles],
        'latest_tools': [{'name': t.get('name',''), 'slug': t.get('slug',''), 'category': t.get('category',''), 'rating': t.get('rating','')} for t in latest_tools],
        'health': {
            'total': health.get('total_urls', 0) if health else 0,
            'dead': health.get('dead_links', 0) if health else 0,
            'checked_at': health.get('checked_at', '') if health else '',
        },
        'filesizes': {
            'tools_json': file_size(os.path.join(DATA_DIR, 'tools')),
            'articles_json': file_size(os.path.join(DATA_DIR, 'articles')),
            'sitemap': file_size(os.path.join(BASE_DIR, 'sitemap.xml')),
        }
    }


def status_icon(status):
    icons = {'ok': '&#9989;', 'pending': '&#9200;', 'error': '&#10060;', 'running': '&#9889;'}
    return icons.get(status, '&#10067;')


STATUS_LABEL = {'ok': '已完成', 'pending': '待启动', 'error': '出错了', 'running': '运行中'}


def render_card(icon, label, value, sub='', accent='#6c5ce7'):
    sub_html = f'<span class="card-sub">{sub}</span>' if sub else ''
    return f'''
    <div class="card" style="border-top: 3px solid {accent};">
        <div class="card-icon">{icon}</div>
        <div class="card-label">{label}</div>
        <div class="card-value">{value}</div>
        {sub_html}
    </div>'''


def render_pipeline_row(task):
    status = task.get('status', 'pending')
    cls = f'pipeline-{status}'
    icon = status_icon(status)
    label = STATUS_LABEL.get(status, status)
    title = task.get('title', '') or '—'
    detail = task.get('detail', '') or ''
    detail_html = f'<span class="pipeline-detail">{detail}</span>' if detail else ''
    time = task.get('time', '--:--')
    return f'''
    <div class="pipeline-row {cls}">
        <span class="pipeline-time">{time}</span>
        <span class="pipeline-task">{task.get('task_name', '')}</span>
        <span class="pipeline-title">{title}</span>
        {detail_html}
        <span class="pipeline-status">{icon} {label}</span>
    </div>'''


def render_table_row_article(a):
    return f'''
    <tr>
        <td class="td-title" title="{a['title']}">{a['title'][:50]}</td>
        <td class="td-date">{a['date']}</td>
        <td class="td-meta">{a['description'][:60]}</td>
    </tr>'''


def render_table_row_tool(t):
    return f'''
    <tr>
        <td class="td-title" title="{t['name']}">{t['name'][:30]}</td>
        <td class="td-cat">{t['category']}</td>
        <td class="td-meta">{t['rating']}</td>
    </tr>'''


def fmt_size(size_bytes):
    if size_bytes > 1024 * 1024:
        return f'{size_bytes / 1024 / 1024:.1f} MB'
    elif size_bytes > 1024:
        return f'{size_bytes / 1024:.1f} KB'
    return f'{size_bytes} B'


def generate_html(data):
    c = data['counts']
    p = data['pipeline']
    h = data['health']
    fs = data['filesizes']

    pipeline_rows = '\n'.join(render_pipeline_row(t) for t in p.get('tasks', []))
    article_rows = '\n'.join(render_table_row_article(a) for a in data['latest_articles'])
    tool_rows = '\n'.join(render_table_row_tool(t) for t in data['latest_tools'])

    # Health check badge
    health_badge = f'<span class="badge-ok">&#9989; 最近检查: {h["checked_at"][:10]}, 死链 {h["dead"]}/{h["total"]}</span>' if h['total'] > 0 else '<span class="badge-warn">&#9888; 无检查记录</span>'

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>aitoollab.cn · AI CMS 控制台</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    background: #0b0b1a;
    color: #cdd6f4;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    line-height: 1.6;
    min-height: 100vh;
    background-image: radial-gradient(ellipse at 20% 0%, #1a1a3e 0%, transparent 50%);
}}
header {{
    background: #111127;
    border-bottom: 1px solid #252545;
    padding: 20px 32px;
    display: flex; align-items: center; gap: 16px;
    position: sticky; top: 0; z-index: 100;
    backdrop-filter: blur(12px);
}}
header h1 {{ font-size: 22px; font-weight: 700; color: #fff; letter-spacing: -0.5px; }}
header .subtitle {{ font-size: 13px; color: #6c5ce7; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }}
header .refresh {{ margin-left: auto; font-size: 12px; color: #636e72; }}
main {{ max-width: 1320px; margin: 0 auto; padding: 24px 32px 60px; }}

/* Sections */
section {{ margin-bottom: 28px; }}
section h2 {{
    font-size: 15px; font-weight: 600; color: #a0a8c0; text-transform: uppercase;
    letter-spacing: 1px; margin-bottom: 14px;
    display: flex; align-items: center; gap: 8px;
}}
section h2::before {{ content: ''; width: 4px; height: 16px; background: #6c5ce7; border-radius: 2px; }}

/* Stats */
.stats-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 14px; }}
.card {{
    background: #111127; border-radius: 10px; padding: 18px;
    border: 1px solid #252545; transition: border-color 0.2s;
}}
.card:hover {{ border-color: #6c5ce7; }}
.card-icon {{ font-size: 22px; margin-bottom: 6px; }}
.card-label {{ font-size: 12px; color: #636e72; text-transform: uppercase; letter-spacing: 0.5px; }}
.card-value {{ font-size: 28px; font-weight: 700; color: #fff; margin-top: 4px; }}
.card-sub {{ font-size: 11px; color: #45475a; display: block; margin-top: 4px; }}

/* Pipeline */
.pipeline {{ background: #111127; border-radius: 10px; border: 1px solid #252545; padding: 18px 20px; }}
.pipeline-row {{
    display: flex; align-items: center; gap: 16px; padding: 10px 0;
    border-bottom: 1px solid #1a1a35; font-size: 14px;
}}
.pipeline-row:last-child {{ border-bottom: none; }}
.pipeline-time {{ color: #636e72; font-family: 'SF Mono', 'Fira Code', monospace; width: 50px; flex-shrink: 0; }}
.pipeline-task {{ color: #a0a8c0; width: 80px; flex-shrink: 0; font-weight: 600; }}
.pipeline-title {{ color: #cdd6f4; flex: 1; }}
.pipeline-detail {{ color: #636e72; font-size: 12px; }}
.pipeline-status {{ font-size: 13px; white-space: nowrap; }}
.pipeline-ok .pipeline-status {{ color: #a6e3a1; }}
.pipeline-error .pipeline-status {{ color: #f38ba8; }}
.pipeline-running .pipeline-status {{ color: #fab387; }}
.pipeline-pending .pipeline-status {{ color: #636e72; }}
.pipeline-ok {{ background: rgba(166,227,161,0.04); }}
.pipeline-error {{ background: rgba(243,139,168,0.06); }}

/* Content tables */
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
.table-wrap {{
    background: #111127; border-radius: 10px; border: 1px solid #252545;
    padding: 0; overflow-x: auto;
}}
.table-wrap h3 {{
    font-size: 13px; color: #a0a8c0; padding: 14px 16px 0; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.5px;
}}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ padding: 10px 16px; text-align: left; border-bottom: 1px solid #1a1a35; }}
th {{ color: #636e72; font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; background: #0d0d22; }}
.td-title {{ color: #cdd6f4; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.td-date, .td-cat {{ color: #6c5ce7; font-weight: 600; white-space: nowrap; }}
.td-meta {{ color: #636e72; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}

/* Health */
.health-row {{
    display: flex; gap: 14px; flex-wrap: wrap;
}}
.health-item {{
    background: #111127; border-radius: 10px; border: 1px solid #252545;
    padding: 14px 18px; font-size: 13px; flex: 1; min-width: 200px;
}}
.badge-ok {{ color: #a6e3a1; }}
.badge-warn {{ color: #f9e2af; }}

/* Actions */
.actions-row {{
    display: flex; gap: 12px; flex-wrap: wrap;
}}
.btn {{
    background: #1a1a3e; border: 1px solid #252545; color: #a0a8c0;
    padding: 10px 18px; border-radius: 8px; font-size: 13px; cursor: pointer;
    transition: all 0.2s; font-family: inherit;
}}
.btn:hover {{ border-color: #6c5ce7; color: #fff; background: #1f1f45; }}
.btn-code {{
    font-family: 'SF Mono', 'Fira Code', monospace; font-size: 12px;
}}
.btn-accent {{ background: #6c5ce7; border-color: #6c5ce7; color: #fff; }}
.btn-accent:hover {{ background: #7c6cf7; }}

/* Footer */
footer {{
    text-align: center; color: #45475a; font-size: 11px; padding: 20px;
    border-top: 1px solid #1a1a35; margin-top: 40px;
}}

@media (max-width: 768px) {{
    .two-col {{ grid-template-columns: 1fr; }}
    .stats-grid {{ grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); }}
    header {{ flex-wrap: wrap; }}
    main {{ padding: 16px; }}
}}
</style>
</head>
<body>

<header>
    <h1>&#x1f3af; aitoollab.cn</h1>
    <span class="subtitle">AI CMS 控制台</span>
    <span class="refresh">&#128339; 更新于 {data['generated_at']}</span>
</header>

<main>

<!-- Stats -->
<section>
    <h2>&#128200; 全站统计</h2>
    <div class="stats-grid">
        {render_card('&#128736;', '已发布工具', c['tools_published'], f'共 {c["tools_total"]} 个, {c["tools_draft"]} 草稿', '#6c5ce7')}
        {render_card('&#128221;', '文章', c['articles'], '', '#00b894')}
        {render_card('&#128218;', '词典词条', c['dict_published'], f'共 {c["dict_total"]} 个', '#fdcb6e')}
        {render_card('&#128451;', '分类', c['categories'], f'{c["subcategories"]} 子类目', '#e17055')}
        {render_card('&#128240;', '快讯天数', c['news_days'], f'最新 {c["news_latest_date"]}', '#0984e3')}
        {render_card('&#128269;', 'PSEO 页面', c['pseo_total'], f'{c["compares"]} vs. {c["alternatives"]} alt. {c["rankings"]} rank.', '#a29bfe')}
    </div>
</section>

<!-- Pipeline -->
<section>
    <h2>&#128340; 今日流水线 ({data['today']})</h2>
    <div class="pipeline">
        {pipeline_rows}
    </div>
</section>

<!-- Content -->
<section>
    <h2>&#128269; 内容概览</h2>
    <div class="two-col">
        <div class="table-wrap">
            <h3>&#128221; 最近文章</h3>
            <table>
                <thead><tr><th>标题</th><th>日期</th><th>描述</th></tr></thead>
                <tbody>{article_rows}</tbody>
            </table>
        </div>
        <div class="table-wrap">
            <h3>&#128736; 最新工具</h3>
            <table>
                <thead><tr><th>名称</th><th>分类</th><th>评分</th></tr></thead>
                <tbody>{tool_rows}</tbody>
            </table>
        </div>
    </div>
</section>

<!-- Health -->
<section>
    <h2>&#128657; 系统健康</h2>
    <div class="health-row">
        <div class="health-item">
            <div style="color:#636e72; font-size:11px; text-transform:uppercase; letter-spacing:1px;">链接检查</div>
            <div style="margin-top:6px;">{health_badge}</div>
        </div>
        <div class="health-item">
            <div style="color:#636e72; font-size:11px; text-transform:uppercase; letter-spacing:1px;">数据大小</div>
            <div style="margin-top:6px;">
                <span>tools.json: {fmt_size(fs['tools_json'])}</span><br>
                <span>articles.json: {fmt_size(fs['articles_json'])}</span><br>
                <span>sitemap.xml: {fmt_size(fs['sitemap'])}</span>
            </div>
        </div>
        <div class="health-item">
            <div style="color:#636e72; font-size:11px; text-transform:uppercase; letter-spacing:1px;">构建命令</div>
            <div style="margin-top:6px; font-family:monospace; font-size:13px;">
                <div style="color:#a6e3a1;">python scripts/build.py -t all</div>
                <div style="color:#89b4fa;">bash deploy.sh</div>
                <div style="color:#fab387;">python scripts/gen_cms.py</div>
            </div>
        </div>
    </div>
</section>

<!-- Actions -->
<section>
    <h2>&#9889; 快捷操作</h2>
    <div class="actions-row">
        <button class="btn btn-accent" onclick="location.reload()">&#128260; 刷新数据</button>
        <div class="btn btn-code">&#128295; python scripts/build.py -t all</div>
        <div class="btn btn-code">&#128640; bash deploy.sh</div>
        <div class="btn btn-code">&#128269; python scripts/gen_cms.py</div>
    </div>
</section>

</main>

<footer>
    aitoollab.cn AI CMS &middot; 本地仪表盘 &middot; 数据来源: data/*.json &middot; {data['generated_at']}
</footer>

</body>
</html>'''


def main():
    print('[gen_cms] 读取数据...')
    data = gather_data()

    print(f'  工具: {data["counts"]["tools_published"]}/{data["counts"]["tools_total"]}')
    print(f'  文章: {data["counts"]["articles"]}')
    print(f'  词典: {data["counts"]["dict_published"]}/{data["counts"]["dict_total"]}')
    print(f'  PSEO: {data["counts"]["pseo_total"]}')

    print('[gen_cms] 生成 HTML...')
    html = generate_html(data)

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html)

    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f'[gen_cms] ✅ 已生成: {OUTPUT} ({size_kb:.1f} KB)')
    print(f'[gen_cms] 浏览器打开: file:///{OUTPUT.replace(chr(92), "/")}')


if __name__ == '__main__':
    main()
