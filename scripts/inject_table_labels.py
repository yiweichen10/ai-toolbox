#!/usr/bin/env python3
# scripts/inject_table_labels.py
# 给文章正文裸 <table> 的每个 <td> 注入 data-label="列名"（取自对应 <th> 纯文本），
# 配合移动端卡片式 CSS（style.css 768px 断点），手机端表格转为堆叠卡片，无需横滑。
# 只改 <td> 属性，不碰其他内容。每个被修改文件先备份为 .bak。
import re, os, glob, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
TARGET_DIRS = [
    os.path.join(ROOT, "articles"),
    os.path.join(ROOT, "tools"),
    os.path.join(ROOT, "category"),
    os.path.join(ROOT, "compare"),
    os.path.join(ROOT, "alternatives"),
    os.path.join(ROOT, "ranking"),
    os.path.join(ROOT, "live"),
]

def plain(text):
    return re.sub(r"<[^>]+>", "", text).strip()

def process_table(table_html):
    # 提取 thead 列名（纯文本）
    thead_m = re.search(r"<thead>.*?</thead>", table_html, re.S)
    headers = []
    if thead_m:
        headers = [plain(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", thead_m.group(0), re.S)]
    # 只处理 tbody
    tbody_m = re.search(r"(<tbody>)(.*?)(</tbody>)", table_html, re.S)
    if not tbody_m:
        return table_html
    body = tbody_m.group(2)
    def repl_tr(tr_m):
        tr = tr_m.group(0)
        row_idx = [0]
        def repl_td(td_m):
            i = row_idx[0]
            row_idx[0] += 1
            attrs = td_m.group(1)
            content = td_m.group(2)
            label = headers[i].replace('"', "&quot;") if i < len(headers) else ""
            if attrs.strip():
                return f'<td data-label="{label}"{attrs}>{content}</td>'
            return f'<td data-label="{label}">{content}</td>'
        return re.sub(r"<td([^>]*)>(.*?)</td>", repl_td, tr, flags=re.S)
    new_body = re.sub(r"<tr>.*?</tr>", repl_tr, body, flags=re.S)
    return table_html[:tbody_m.start(2)] + new_body + table_html[tbody_m.end(2):]

def inject(html):
    # 仅当存在无 data-label 的 td 时才处理
    if not re.search(r"<td>", html):
        return html, False
    new_html, n = re.subn(r"<table>.*?</table>", lambda m: process_table(m.group(0)), html, flags=re.S)
    return new_html, n > 0

def main():
    changed = 0
    scanned = 0
    for d in TARGET_DIRS:
        if not os.path.isdir(d):
            continue
        for fp in glob.glob(os.path.join(d, "**", "index.html"), recursive=True):
            scanned += 1
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    html = f.read()
            except Exception:
                continue
            # 已经全部有 data-label 就跳过
            if "<td data-label=" in html:
                continue
            new_html, did = inject(html)
            if did:
                bak = fp + ".20260804.bak"
                if not os.path.exists(bak):
                    shutil.copy2(fp, bak)
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(new_html)
                changed += 1
    print(f"扫描 {scanned} 个 index.html，注入 data-label 的文件: {changed}")

if __name__ == "__main__":
    main()
