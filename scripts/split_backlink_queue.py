# -*- coding: utf-8 -*-
"""把 backlink_push_queue/YYYY-MM-DD.md 拆成"一份文件 = 一条发布内容"。

产出：
    backlink_push_queue/ready/csdn/<slug>.md      （标题+标签+全文+转载声明）
    backlink_push_queue/ready/zhihu/<slug>.md     （浓缩回答，含文末原文链接）
    backlink_push_queue/ready/wechat/<slug>.md    （公众号草稿骨架：标题/摘要/提纲）

用法：
    python scripts/split_backlink_queue.py [YYYY-MM-DD]   # 默认今天
"""

import os
import re
import sys
import datetime

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = __import__("io").TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE_DIR = os.path.join(BASE_DIR, "backlink_push_queue")
READY_DIR = os.path.join(QUEUE_DIR, "ready")


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    src = os.path.join(QUEUE_DIR, f"{day}.md")
    if not os.path.exists(src):
        print(f"找不到队列文件：{src}")
        return 1
    with open(src, encoding="utf-8") as f:
        content = f.read()

    # 按 "## N. 标题" 切文章，再按 "### 平台版" 切平台
    articles = re.split(r"\n## \d+\. ", content)[1:]
    made = []
    for art in articles:
        title = art.split("\n", 1)[0].strip()
        slug_match = re.search(r"原文：https://www\.aitoollab\.cn/articles/([^/]+)/", art)
        slug = slug_match.group(1) if slug_match else re.sub(r"[^\w\u4e00-\u9fff]+", "-", title)[:60]
        blocks = re.split(r"\n### ", art)
        for block in blocks[1:]:
            head, _, body = block.partition("\n")
            head = head.strip()
            body = body.strip()
            if not body:
                continue
            if head.startswith("公众号"):
                sub = "wechat"
            elif head.startswith("知乎"):
                sub = "zhihu"
            elif head.startswith("CSDN"):
                sub = "csdn"
            else:
                continue
            d = os.path.join(READY_DIR, sub)
            os.makedirs(d, exist_ok=True)
            out = os.path.join(d, f"{slug}.md")
            with open(out, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n{body}\n")
            made.append(out)

    print(f"[OK] 共生成 {len(made)} 个文件：")
    for m in made:
        print(f"  - {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
