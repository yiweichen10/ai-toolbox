#!/usr/bin/env python3
"""
gen_article_infographic.py — 文章正文插图生成模块
HTML+CSS 模板 → Playwright 截图 → PNG

设计原则：
  - 数据驱动：传入结构化 JSON 数据，自动生成 HTML
  - 本地渲染：HTML+CSS → Playwright → 干净的文字图表
  - 风格统一：与站内 OG 图同款暗色主题
"""

import json
import os
import subprocess
import sys
import socket
import time
import re

TEMPLATES_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(TEMPLATES_DIR)
OUTPUT_DIR = os.path.join(BASE_DIR, 'images', 'infographics')


# ═══════ HTML 模板 ═══════

CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
html { height: auto; min-height: 0; }
body {
  width: 780px;
  background: linear-gradient(160deg, #0b1120 0%, #111827 40%, #0f172a 100%);
  font-family: -apple-system, "Microsoft YaHei", "PingFang SC", sans-serif;
  padding: 24px 0 0 0; margin: 0;
  display: flex; justify-content: center;
  -webkit-font-smoothing: antialiased;
}
.container { width: 100%; padding: 0 32px; }

.header { display: flex; align-items: center; gap: 16px; margin-bottom: 22px; }
.header-icon {
  width: 48px; height: 48px; border-radius: 14px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 40%, #a78bfa 100%);
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; flex-shrink: 0;
  box-shadow: 0 0 20px rgba(99,102,241,0.25);
}
.header-text h2 { font-size: 20px; font-weight: 800; color: #f1f5f9; letter-spacing: -0.2px; }
.header-text p  { font-size: 12.5px; color: #64748b; margin-top: 3px; letter-spacing: 0.2px; }

.tools-row { display: flex; gap: 12px; margin-bottom: 18px; }
.tool-card {
  flex: 1;
  background: linear-gradient(180deg, rgba(30,41,59,0.9) 0%, rgba(15,23,42,0.95) 100%);
  border-radius: 16px; padding: 20px 14px 16px; text-align: center;
  border: 1px solid rgba(71,85,105,0.3);
  position: relative; overflow: hidden; backdrop-filter: blur(8px);
}
.tool-card::after {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; border-radius: 3px;
}
.tool-card:nth-child(1)::after { background: linear-gradient(90deg, #10b981, #34d399); }
.tool-card:nth-child(2)::after { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.tool-card:nth-child(3)::after { background: linear-gradient(90deg, #3b82f6, #60a5fa); }

.tool-emoji { font-size: 30px; margin-bottom: 8px; display: block; }
.tool-name { font-size: 16px; font-weight: 700; color: #f8fafc; margin-bottom: 2px; }
.tool-sub { font-size: 11px; color: #64748b; }
.tool-badges { margin-top: 10px; display: flex; flex-wrap: wrap; justify-content: center; gap: 5px; }
.badge { padding: 3px 12px; border-radius: 999px; font-size: 11px; font-weight: 600; }
.badge-free { background: rgba(16,185,129,0.15); color: #34d399; }
.badge-score { background: rgba(251,191,36,0.12); color: #fbbf24; }
.badge-best { background: rgba(59,130,246,0.12); color: #60a5fa; }

.table-wrap {
  background: rgba(30,41,59,0.6); border-radius: 16px; overflow: hidden;
  border: 1px solid rgba(71,85,105,0.25);
}
table { width: 100%; border-collapse: collapse; }
thead th {
  padding: 13px 16px; text-align: left;
  font-size: 11.5px; font-weight: 700; color: #64748b;
  background: rgba(15,23,42,0.6); border-bottom: 1px solid rgba(71,85,105,0.2);
  text-transform: uppercase; letter-spacing: 0.8px;
}
thead th:first-child { width: 105px; padding-left: 18px; }
thead th:nth-child(2) { color: #34d399; }
thead th:nth-child(3) { color: #fbbf24; }
thead th:nth-child(4) { color: #60a5fa; }

tbody td {
  padding: 12px 16px; font-size: 13px; color: #cbd5e1;
  border-bottom: 1px solid rgba(51,65,85,0.3); vertical-align: middle;
}
tbody td:first-child { color: #94a3b8; font-weight: 600; white-space: nowrap; padding-left: 18px; }
tbody tr:nth-child(even) td { background: rgba(15,23,42,0.25); }
tbody tr:last-child td { border-bottom: none; }

.score-bar-wrap { display: flex; align-items: center; gap: 10px; }
.score-bar { flex: 1; height: 6px; border-radius: 3px; background: rgba(51,65,85,0.4); overflow: hidden; }
.score-fill { height: 100%; border-radius: 3px; position: relative; }
.score-fill::after {
  content: ''; position: absolute; right: 0; top: 0; bottom: 0;
  width: 6px; border-radius: 3px; background: inherit; filter: brightness(1.4);
}
.g1 { background: linear-gradient(90deg, #059669, #34d399); }
.g2 { background: linear-gradient(90deg, #d97706, #fbbf24); }
.g3 { background: linear-gradient(90deg, #2563eb, #60a5fa); }
.score-val { font-size: 12px; font-weight: 700; color: #94a3b8; width: 34px; text-align: right; }

.feat-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.ftag { padding: 3px 9px; border-radius: 6px; font-size: 11px; font-weight: 600; }
.ftag-yes { background: rgba(16,185,129,0.15); color: #34d399; }
.ftag-no  { background: rgba(51,65,85,0.3); color: #475569; }

.price-highlight { font-weight: 700; font-size: 13px; }
.price-mid { color: #fbbf24; }
.price-free { color: #34d399; }

tbody tr:last-child td { color: #94a3b8; font-size: 11.5px; line-height: 1.5; padding-top: 10px; padding-bottom: 14px; }
tbody tr:last-child td:first-child { color: #64748b; }

.footer {
  display: flex; align-items: center; justify-content: center;
  gap: 8px; padding: 14px 0 0 0; font-size: 11px; color: #475569; letter-spacing: 0.3px;
}
.footer-dot { width: 4px; height: 4px; border-radius: 50%; background: #334155; }
"""


def escape_html(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def make_score_bar(score, max_score=10, color_class='g1'):
    """生成评分条 HTML"""
    pct = min(100, max(0, int(score / max_score * 100)))
    return (
        f'<div class="score-bar-wrap">'
        f'<div class="score-bar"><div class="score-fill {color_class}" style="width:{pct}%"></div></div>'
        f'<span class="score-val">{score}</span>'
        f'</div>'
    )


def build_html(data):
    """
    从结构化数据生成完整 HTML
    
    data = {
        'title': '主流 AI 对话工具横向对比',
        'subtitle': '编辑组实测数据 · 2026 年 6 月更新',
        'icon': '📊',
        'tools': [
            {'name': 'ChatGPT',  'sub': 'OpenAI · GPT-5',  'emoji': '🤖', 'badges': [('免费可用','free'), ('⭐ 4.9','score')]},
            {'name': 'Claude',   'sub': 'Anthropic · Claude 4', 'emoji': '🎭', 'badges': [('免费可用','free'), ('⭐ 4.8','score')]},
            {'name': 'DeepSeek', 'sub': '深度求索 · V3', 'emoji': '👨‍💻', 'badges': [('完全免费','best'), ('⭐ 4.7','score')]},
        ],
        'rows': [
            {'label': '价格', 'type': 'text', 'values': ['Plus $20/月', 'Pro $20/月', '完全免费']},
            {'label': '中文', 'type': 'score', 'values': [8.0, 8.2, 9.5]},
            {'label': '代码', 'type': 'score', 'values': [9.2, 9.0, 8.5]},
            {'label': '上下文', 'type': 'text', 'values': ['128K', '1000K', '128K']},
            {'label': '多模态', 'type': 'tags', 'values': [
                {'yes': ['图片','音频','视频'], 'no': ['3D']},
                {'yes': ['图片','文档'], 'no': ['音频','视频']},
                {'yes': ['图片','文档','代码'], 'no': ['音频']},
            ]},
            {'label': '场景', 'type': 'scene', 'values': [
                '日常对话 · 插件生态 · 多模态创作',
                '长文档分析 · 学术写作 · 代码审查',
                '中文推理 · 编程辅助 · 深度研究',
            ]},
        ],
        'footer': 'AI工具宝箱 实测 · 2026.06 更新 · aitoollab.cn',
    }
    """
    title = escape_html(data.get('title', 'AI工具横向对比'))
    subtitle = escape_html(data.get('subtitle', ''))
    icon = data.get('icon', '📊')
    
    # ── 工具卡片 ──
    tools_html = ''
    tools = data.get('tools', [])
    for tool in tools:
        badges_html = ''
        for text, btype in tool.get('badges', []):
            badges_html += f'<span class="badge badge-{btype}">{escape_html(text)}</span>'
        tools_html += (
            f'<div class="tool-card">'
            f'<span class="tool-emoji">{tool["emoji"]}</span>'
            f'<div class="tool-name">{escape_html(tool["name"])}</div>'
            f'<div class="tool-sub">{escape_html(tool["sub"])}</div>'
            f'<div class="tool-badges">{badges_html}</div>'
            f'</div>'
        )
    
    # ── 表格行 ──
    rows_html = ''
    color_classes = ['g1', 'g2', 'g3']
    
    for row in data.get('rows', []):
        label = escape_html(row['label'])
        rtype = row.get('type', 'text')
        cols_html = ''
        
        for i, val in enumerate(row.get('values', [])):
            cls = color_classes[i % 3]
            if rtype == 'score':
                cols_html += f'<td>{make_score_bar(val, color_class=cls)}</td>'
            elif rtype == 'tags':
                yes_tags = val.get('yes', [])
                no_tags = val.get('no', [])
                tag_parts = ''.join(f'<span class="ftag ftag-yes">{escape_html(t)}</span>' for t in yes_tags)
                tag_parts += ''.join(f'<span class="ftag ftag-no">{escape_html(t)}</span>' for t in no_tags)
                cols_html += f'<td><div class="feat-tags">{tag_parts}</div></td>'
            elif rtype == 'scene':
                cols_html += f'<td>{escape_html(val)}</td>'
            else:
                # 普通文本，检查是否包含免费/付费等
                v = escape_html(str(val))
                if '免费' in v:
                    cols_html += f'<td><span class="price-highlight price-free">{v}</span></td>'
                elif '$' in v or '¥' in v or '/月' in v:
                    cols_html += f'<td><span class="price-highlight price-mid">{v}</span></td>'
                else:
                    cols_html += f'<td style="font-size:13px;">{v}</td>'
        
        rows_html += f'<tr><td>{label}</td>{cols_html}</tr>'
    
    # ── 表头（取前3个工具名）──
    tool_names = [escape_html(t.get('name', '')) for t in tools[:3]]
    while len(tool_names) < 3:
        tool_names.append('')
    thead_html = f'<tr><th>维度</th><th>{tool_names[0]}</th><th>{tool_names[1]}</th><th>{tool_names[2]}</th></tr>'
    
    # ── 底部 ──
    footer = escape_html(data.get('footer', f'AI工具宝箱 实测 · {time.strftime("%Y.%m")} 更新 · aitoollab.cn'))
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><style>{CSS}</style></head>
<body>
<div class="container">
  <div class="header">
    <div class="header-icon">{icon}</div>
    <div class="header-text">
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </div>
  </div>
  <div class="tools-row">{tools_html}</div>
  <div class="table-wrap">
    <table>
      <thead>{thead_html}</thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
  <div class="footer">
    <span>{footer.split('·')[0].strip()}</span>
    <span class="footer-dot"></span>
    <span>{footer.split('·')[1].strip() if '·' in footer else 'aitoollab.cn'}</span>
    <span class="footer-dot"></span>
    <span>aitoollab.cn</span>
  </div>
</div>
</body>
</html>"""


# ═══════ 截图 ═══════

def _kill_port(port):
    try:
        import platform
        if platform.system() == 'Windows':
            subprocess.run(
                f'for /f "tokens=5" %a in (\'netstat -ano ^| findstr :{port} ^| findstr LISTENING\') do taskkill /F /PID %a',
                shell=True, capture_output=True)
    except:
        pass


def _free_port():
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def screenshot_html(html, output_path, width=780):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tmp_dir = os.path.dirname(output_path)
    tmp_html = os.path.join(tmp_dir, '_tmp_infographic.html')
    
    with open(tmp_html, 'w', encoding='utf-8') as f:
        f.write(html)
    
    port = _free_port()
    server = subprocess.Popen(
        [sys.executable, '-m', 'http.server', str(port), '--directory', tmp_dir],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    
    try:
        time.sleep(0.8)
        subprocess.run(f'playwright-cli open --browser=chrome http://localhost:{port}/_tmp_infographic.html',
                      shell=True, capture_output=True, timeout=15)
        time.sleep(1)
        
        # 获取实际高度
        result = subprocess.run('playwright-cli eval "document.body.scrollHeight"',
                               shell=True, capture_output=True, text=True, timeout=10)
        height = 600
        for line in result.stdout.split('\n'):
            if line.strip().isdigit():
                height = max(400, int(line.strip()) + 10)
                break
        
        subprocess.run(f'playwright-cli resize {width} {height}', shell=True, capture_output=True, timeout=5)
        subprocess.run(f'playwright-cli screenshot --filename="{output_path}" --full-page',
                      shell=True, capture_output=True, timeout=15)
        subprocess.run('playwright-cli close', shell=True, capture_output=True, timeout=5)
    finally:
        server.terminate()
        _kill_port(port)
        try:
            os.remove(tmp_html)
        except:
            pass
    
    return os.path.exists(output_path)


# ═══════ 公开接口 ═══════

def generate(data, slug, width=780):
    """生成插图，返回 PNG 路径"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output = os.path.join(OUTPUT_DIR, f'{slug}-infographic.png')
    
    html = build_html(data)
    print(f"  📸 生成插图: {slug}-infographic.png")
    ok = screenshot_html(html, output, width)
    if ok:
        print(f"  ✅ 插图已保存")
        return output
    else:
        print(f"  ❌ 插图生成失败")
        return None


def img_tag(slug, alt='AI工具对比表格'):
    """生成文章内嵌 HTML 标签"""
    return (
        f'<figure class="article-infographic" style="margin:32px 0;text-align:center;">\n'
        f'  <img src="/images/infographics/{slug}-infographic.png" '
        f'alt="{alt}" loading="lazy" width="780" '
        f'style="max-width:100%;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.08);"'
        f'/>\n'
        f'  <figcaption style="margin-top:8px;font-size:13px;color:#94a3b8;">▲ {alt}</figcaption>\n'
        f'</figure>'
    )


def extract_from_content(content):
    """
    从文章 markdown 内容中提取对比数据
    返回 data dict 或 None
    """
    # 尝试找 JSON 块
    json_match = re.search(r'```json\s*\n({[\s\S]*?})\n```', content)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except:
            pass
    return None


# ═══════ CLI ═══════

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='文章插图生成器')
    p.add_argument('--data', required=True, help='JSON 数据文件路径')
    p.add_argument('--slug', required=True, help='文章 slug')
    args = p.parse_args()
    
    with open(args.data, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    result = generate(data, args.slug)
    if result:
        print(f"\n插图已生成: {result}")
        print(f"IMG标签:\n{img_tag(args.slug)}")
    else:
        sys.exit(1)
