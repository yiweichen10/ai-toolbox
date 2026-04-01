import json, sys, os
sys.stdout.reconfigure(encoding='utf-8')

# 读取现有 articles.json
with open('data/articles.json', encoding='utf-8') as f:
    articles = json.load(f)

# 已有的slug
existing_slugs = {a['slug'] for a in articles}
print(f"Existing articles: {len(articles)}, slugs: {list(existing_slugs)}")

# 读取去AI味后的草稿
with open('_articles_humanized.json', encoding='utf-8') as f:
    humanized = json.load(f)

# 读取原始元数据
with open('_article_drafts.json', encoding='utf-8') as f:
    drafts = json.load(f)

# 加上之前生成的 ChatGPT 文章（手动保留那篇去AI味后的内容）
CHATGPT_ARTICLE = {
    "title": "如何用ChatGPT写代码：十年程序员的实战经验分享",
    "slug": "how-to-use-chatgpt-for-coding",
    "description": "凌晨修Bug修到崩溃时随手扔给ChatGPT，5秒出答案。这不是科幻，是真实发生的。十年老程序员分享如何用ChatGPT写出能用的代码。",
    "keywords": "ChatGPT写代码,ChatGPT编程,AI辅助开发,ChatGPT教程",
    "category": "AI编程",
    "content": """上周三凌晨两点，眼皮实在撑不住了，代码里那个诡异的Python报错还没搞定。随手把错误信息扔给ChatGPT，5秒——它就给对了。从那之后我这个十年老程序员，不得不承认：这玩意儿是真的香。

注册那些坑
别被OpenAI的界面吓到，直接去openai.com点Sign up，用Gmail最省事，国内手机号收验证码没问题。充值才是真正的坎——需要一张支持美元的信用卡，Depay虚拟卡在某宝一搜就有教程。不充值的话只能用GPT-3.5，代码能力差太多，建议直接充5美元起步。

第一个真实案例：批量重命名文件
我要写个Python脚本，把文件夹里的所有jpg文件前面加上日期前缀，但`os`模块的用法记不清了。直接问ChatGPT：

> 用Python遍历指定文件夹下所有.jpg文件，在文件名前加上日期前缀，比如20230801_原文件名.jpg，给出完整代码并解释关键步骤

它秒回一段能直接跑的代码，注释写得跟老手写的一样：

```python
import os
from datetime import datetime

folder_path = "/path/to/your/folder"  # 你的实际路径
date_prefix = datetime.now().strftime("%Y%m%d")

for filename in os.listdir(folder_path):
    if filename.endswith(".jpg"):
        new_name = f"{date_prefix}_{filename}"
        os.rename(
            os.path.join(folder_path, filename),
            os.path.join(folder_path, new_name)
        )
        print(f"Renamed: {filename} -> {new_name}")
```

Debug的正确姿势
当代码报错时，把**完整报错信息+相关代码**一起扔给AI。比说我昨天遇到Django报错"OperationalError: no such table"，把错误日志和models.py内容一并发过去，它直接回我："你忘记运行migrate了，先python manage.py makemigrations再migrate。"这种低级错误人查半小时，AI5秒解决。

三个月用下来的真实感受
最崩溃的是：AI偶尔会一本正经地胡说八道，特别是数学计算，代码跑不通是常事。最爽的是：你知道要什么但懒得查文档，它10秒给你写好。

彩蛋：试试对它说"用Python画一只会动的柴犬"，你会回来谢我的。"""
}

ARTICLES_TO_ADD = [
    CHATGPT_ARTICLE,
]

# 合并元数据和去AI味内容
for slug, humanized_content in humanized.items():
    if slug in drafts:
        meta = drafts[slug]
        ARTICLES_TO_ADD.append({
            "title": meta["title"],
            "slug": meta["slug"],
            "description": meta["description"],
            "keywords": meta["keywords"],
            "category": meta["category"],
            "content": humanized_content
        })

added = 0
for art in ARTICLES_TO_ADD:
    if art['slug'] not in existing_slugs:
        articles.append(art)
        added += 1
        print(f"  + Added: {art['title']}")
    else:
        print(f"  - Already exists: {art['slug']}")

print(f"\nAdded {added} new articles. Total: {len(articles)}")

with open('data/articles.json', 'w', encoding='utf-8') as f:
    json.dump(articles, f, ensure_ascii=False, indent=2)

print("Saved to data/articles.json")