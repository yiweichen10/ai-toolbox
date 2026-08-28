# -*- coding: utf-8 -*-
"""构建期通用 HTML 工具：折叠空行 / 落盘 / 错误记录 / markdown 渲染 / faq 剥离。

旧单体 build.py 中抽取的纯函数，无业务依赖（仅依赖 DATA_DIR 常量，由调用方注入）。
"""
import os
import re
import time

# 由 build.py 注入（保持兼容）：DATA_DIR
DATA_DIR = None


def set_data_dir(d):
    global DATA_DIR
    DATA_DIR = d


_PRE_BLOCK_RE = re.compile(r'(<pre\b.*?</pre>|<textarea\b.*?</textarea>)', re.S | re.I)


def _collapse_blank_lines(html: str) -> str:
    """折叠连续空行(3+ 换行→1空行), 保护 <pre>/<textarea> 内空白不被压缩。"""
    _store = []
    def _stash(m):
        _store.append(m.group(1))
        return "\x00%d\x00" % (len(_store) - 1)
    html = _PRE_BLOCK_RE.sub(_stash, html)
    html = re.sub(r'\n[ \t]*\n(?:[ \t]*\n)+', '\n\n', html)
    for i, blk in enumerate(_store):
        html = html.replace("\x00%d\x00" % i, blk)
    return html


def _emit(path: str, html: str) -> None:
    """统一 HTML 写盘出口：落盘前折叠多余空行, 所有页面共用, 折叠逻辑只此一处。"""
    # 2026-08-27: 目录不存在时先补建（增量构建 -s 新工具时页目录被删过会 FileNotFoundError）
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 2026-08-28 增量发布依赖：内容逐字节相同则不写盘，保持 mtime 不变。
    # 目的：deploy.sh --fast-article 用"构建后 mtime 变化"精确采集需要上传的文件；
    # 否则增量构建会把上千个"内容没变"的页面也标成变更，增量退化成全量上传。
    body = _collapse_blank_lines(html)
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as _f0:
                if _f0.read() == body:
                    return
    except OSError:
        pass
    # 2026-08-06: 偶发 Errno 22（文件被扫描/同步短暂占用），加重试避免流水线中断
    for _attempt in range(5):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(body)
            return
        except OSError:
            if _attempt == 4:
                raise
            time.sleep(0.4)


def _record_build_error(kind: str, key: str, err: str) -> None:
    """fail-soft 错误记录（2026-08-23）：单页渲染失败时追加到 data/build_errors.json，
    供构建后排查。不抛异常、不阻断其他页面。"""
    try:
        import json as _j
        _p = os.path.join(DATA_DIR, 'build_errors.json')
        _lst = []
        if os.path.exists(_p):
            try:
                with open(_p, 'r', encoding='utf-8') as _f:
                    _lst = _j.load(_f)
                    if not isinstance(_lst, list):
                        _lst = []
            except Exception:
                _lst = []
        _lst.append({'kind': kind, 'key': key, 'error': str(err)[:300]})
        with open(_p, 'w', encoding='utf-8') as _f:
            _j.dump(_lst[-200:], _f, ensure_ascii=False, indent=1)
    except Exception:
        pass  # 错误记录失败不影响构建


def extract_faq_section(md):
    """从工具 markdown 正文剥离"常见问题（FAQ）"小节（P0- 3）。
    返回 (清理后的 markdown, [(question, answer), ...])。"""
    if not md:
        return md, []
    lines = md.split('\n')
    out = []
    faqs = []
    in_faq = False
    q = None
    buf = []

    def flush():
        nonlocal q, buf
        if q is not None:
            ans = '\n'.join(buf).strip()
            if ans:
                faqs.append((q, ans))
        q = None
        buf = []

    for ln in lines:
        stripped = ln.strip()
        if re.match(r'^#{1,4}\s*常见问题', stripped):
            flush()
            in_faq = True
            continue
        if in_faq:
            if re.match(r'^#{1,4}\s+', stripped):
                flush()
                in_faq = False
                out.append(ln)
                continue
            if not stripped:
                if q is not None:
                    buf.append(ln)
                continue
            mq = re.match(r'^\*\*(.+?)\*\*\s*$', stripped)
            if mq:
                flush()
                q = mq.group(1).strip().rstrip('?？:：').strip()
                continue
            mq2 = re.match(r'^\*\*(.+?)\*\*\s*(.+)$', stripped)
            if mq2 and q is None:
                q = mq2.group(1).strip().rstrip('?？:：').strip()
                buf.append(mq2.group(2).strip())
                continue
            if q is not None:
                buf.append(ln)
        else:
            out.append(ln)
    flush()
    return '\n'.join(out), faqs


def markdown_to_html(md):
    """将Markdown转换为简单HTML"""
    if not md:
        return ''
    html = md
    # 水平分隔线（---）转为 <hr>，必须放在代码块处理之前，避免误匹配
    html = re.sub(r'\n---\s*\n', '\n<hr>\n', html)
    html = re.sub(r'^---\s*$', '<hr>', html, flags=re.MULTILINE)
    # 代码块
    html = re.sub(r'```(\w*)\n([\s\S]*?)```', lambda m: '<pre><code>' + m.group(2).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</code></pre>', html)
    # 表格
    def table_replace(m):
        header = m.group(1)
        sep = m.group(2)
        body = m.group(3)
        headers = [c.strip() for c in header.split('|') if c.strip()]
        plain_headers = [re.sub(r'<[^>]+>', '', h).strip() for h in headers]
        rows = body.strip().split('\n')
        table = '<table><thead><tr>'
        for h in headers:
            table += f'<th>{h}</th>'
        table += '</tr></thead><tbody>'
        for row in rows:
            cells = [c.strip() for c in row.split('|') if c.strip()]
            table += '<tr>'
            for i, c in enumerate(cells):
                label = plain_headers[i].replace('"', '&quot;') if i < len(plain_headers) else ''
                table += f'<td data-label="{label}">{c}</td>'
            table += '</tr>'
        table += '</tbody></table>'
        return table
    html = re.sub(r'\n(\|.+\|)\n(\|[-:| ]+\|)\n((?:\|.+\|\n?)+)', table_replace, html)
    # 标题（H1/H2/H3）
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    # 引用
    html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
    # 加粗/行内代码
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    # 图片 ![alt](url)（2026-08-17 新增）
    html = re.sub(r'!\[([^\]]*)\]\((https?://[^)]+)\)', r'<img src="\2" alt="\1" loading="lazy">', html)
    html = re.sub(r'!\[([^\]]*)\]\((/[^)]+)\)', r'<img src="\2" alt="\1" loading="lazy">', html)
    # 链接 [text](url)
    html = re.sub(r'\[([^\]]+)\]\((/[^)]+)\)', r'<a href="\2" class="ilink">\1</a>', html)
    html = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'<a href="\2" target="_blank" rel="noopener" class="ext-link">\1</a>', html)
    # 列表：将连续的 <li> 包裹在 <ul> 中
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', html, flags=re.MULTILINE)
    html = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul>\1</ul>', html)
    # 段落：将连续非标签行包裹成p
    lines = html.split('\n')
    result = []
    in_p = False
    for line in lines:
        stripped = line.strip()
        is_tag = stripped.startswith('<h') or stripped.startswith('<ul') or stripped.startswith('</ul') or stripped.startswith('<li') or stripped.startswith('<table') or stripped.startswith('</table') or stripped.startswith('<pre') or stripped.startswith('</pre') or stripped.startswith('<blockquote') or stripped.startswith('</blockquote') or stripped.startswith('<hr') or stripped == ''
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
                result.append(line)
    if in_p:
        result.append('</p>')
    return '\n'.join(result)


def shift_headings(html, up=1):
    """把 h1..h5 整体上移 up 级（h1->h2...）。用于工具页正文与模板H1解耦。"""
    for lvl in range(5, 0, -1):
        nxt = min(lvl + up, 6)
        html = re.sub(rf'<h{lvl}([ >])', rf'<h{nxt}\1', html)
        html = re.sub(rf'</h{lvl}>', f'</h{nxt}>', html)
    return html


def escape_html(text):
    """转义HTML特殊字符（用于属性值）"""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
