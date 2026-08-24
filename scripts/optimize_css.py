#!/usr/bin/env python3
# scripts/optimize_css.py
# 生成两份产物:
#   css/style.min.css      —— 全量 CSS 压缩版(异步预加载用)
#   css/style.critical.css —— 首屏关键 CSS(内联到 <head>, 消除渲染阻塞)
# 源文件 css/style.css 保留完整注释, 供日常维护.
import re, os, sys

# Windows GBK 控制台兜底（2026-08-09 机制化修复）：打印 emoji/中文不再抛 UnicodeEncodeError。
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
CSS_PATH = os.path.join(HERE, "..", "css", "style.css")


def minify(css: str) -> str:
    """等价压缩: 删块注释 + 压空白 + 符号去空格. 不重排规则, 零语义风险."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)   # 删 /* ... */
    css = re.sub(r"\s+", " ", css)                     # 空白折叠成单空格
    css = re.sub(r"\s*([{}:;,>])\s*", r"\1", css)      # 符号两侧去空格
    css = css.replace(";}", "}")                       # 冗余分号
    return css.strip()


def _check_css_safety(src: str) -> list:
    """压缩前硬门禁: 返回问题清单(空=通过)。杜绝括号不平衡导致 media 块吞规则。"""
    problems = []
    # 1) 全局括号平衡(忽略字符串/注释已删, 安装态 style.css 无裸引号干扰)
    opens, closes = src.count("{"), src.count("}")
    if opens != closes:
        problems.append(f"括号不平衡: {{ = {opens}, }} = {closes}, 差 {opens - closes} 个")
    # 2) 媒体查询块完整性: 每个 @media 必须有配对的 { 与 }
    #    用栈追踪, 定位到行号, 避免"少一个 } 把后续 242 条规则吞进错误块"。
    stack = []  # (block_start_token, line_no)
    lines = src.split("\n")
    for i, line in enumerate(lines, 1):
        s = line
        # 统计该行的 { 和 }
        for ch in s:
            if ch == "{":
                # 记录最近一次开块(粗略: 取行内首个 { 前的选择器/@media)
                stack.append((s.strip()[:40], i))
            elif ch == "}":
                if not stack:
                    problems.append(f"第 {i} 行: 多余的 }} (没有对应的 {{)")
                else:
                    stack.pop()
    if stack:
        # 未闭合的块(最常见: @media 漏写 })
        detail = "; ".join(f"「{tok}…」起始于第 {ln} 行" for tok, ln in stack[:5])
        more = f" 等共 {len(stack)} 个" if len(stack) > 5 else ""
        problems.append("存在未闭合块(漏写 }): " + detail + more)
    return problems


def main():
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        src = f.read()

    # ===== CSS 安全门禁(2026-08-22 事故后新增, 杜绝括号不平衡回档) =====
    problems = _check_css_safety(src)
    if problems:
        print("❌ CSS 安全校验未通过, 已中止压缩, 请先修复 style.css:")
        for p in problems:
            print("   - " + p)
        print("\n提示: 用括号检查定位漏写的 }, 常见位置是 @media 块结尾。")
        sys.exit(1)

    lines = src.split("\n")
    # 首屏关键层(1-indexed 行号 -> index=行号-1):
    #   变量(7) + 暗色基础(67-125) + 重置/html/body(126-146)
    #   + header(152-275) + main layout(277-380) + hero(393-458) + section通用(459-557)
    # 不含工具卡片(558+)/暗色大段覆盖(1594+)/各板块特有/响应式手机覆盖(1432+)
    critical_src = "\n".join(lines[6:557])

    # 文章列表/分类页头部(首屏 h1+RSS 行): 按注释标记从 style.css 截取, 单一来源不重复维护.
    _intro_start = next((i for i, l in enumerate(lines) if l.strip().startswith("/* 文章列表/分类页头部")), None)
    _intro_end = next((i for i, l in enumerate(lines) if l.strip().startswith("/* 文章栏目互链")), None)
    if _intro_start is not None and _intro_end is not None and _intro_end > _intro_start:
        critical_src += "\n" + "\n".join(lines[_intro_start:_intro_end])

    # 手写基础排版: 保证首屏标题/链接/图片立刻有合理样式,
    # 不依赖异步全量(避免标题/正文首屏无样式闪烁).
    extra = """
h1,h2,h3,h4,h5,h6{margin:0 0 .5em;font-weight:800;line-height:1.25;color:var(--text-main)}
p{margin:0 0 1em;line-height:1.7;color:var(--text-main)}
a{color:var(--primary);text-decoration:none}
img{max-width:100%;height:auto}
"""

    critical_css = minify(critical_src + extra)
    full_min = minify(src)

    out_dir = os.path.dirname(CSS_PATH)
    with open(os.path.join(out_dir, "style.critical.css"), "w", encoding="utf-8") as f:
        f.write(critical_css)
    with open(os.path.join(out_dir, "style.min.css"), "w", encoding="utf-8") as f:
        f.write(full_min)

    raw = len(src.encode("utf-8"))
    cm = len(critical_css.encode("utf-8"))
    fm = len(full_min.encode("utf-8"))
    print(f"原始 style.css       : {raw:>7} B ({raw/1024:5.1f} KB)")
    print(f"全量压缩 style.min   : {fm:>7} B ({fm/1024:5.1f} KB)  降幅 {100*(1-fm/raw):4.0f}%")
    print(f"关键内联 critical    : {cm:>7} B ({cm/1024:5.1f} KB)  {'⚠️超过14KB单帧上限' if cm>14*1024 else '✅在14KB内'}")


if __name__ == "__main__":
    main()
