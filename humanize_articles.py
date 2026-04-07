"""
去AI味处理脚本 - 基于去AI味技能指南 (修复版)
"""

import re, json, sys
sys.stdout.reconfigure(encoding='utf-8')

# ── AI模式词库 ──────────────────────────────────────────────
FILLER_PHRASES = [
    "值得注意的是", "从某种程度上说", "实际上", "事实上",
    "总的来说", "简单来说", "一言以蔽之",
]

AI_VOCAB = [
    "此外", "与此同时", "进一步", "从而", "因此",
    "然而", "但是", "并且", "同时",
    "显著地", "极大地", "大幅度地",
    "展现出", "体现出", "凸显出", "彰显出",
    "不可或缺", "至关重要", "举足轻重",
    "近年来", "随着时代的发展", "不言而喻",
    "不难发现", "有目共睹",
]

def remove_em_dash(text):
    """把滥用em dash改成句号或逗号"""
    # 仅处理中文字符中间的破折号，且保留换行
    text = re.sub(r'([^\n\s])\s*—\s*([^\n\s])', r'\1 \2', text)
    return text

def fix_rule_of_three(text):
    """把三连结构改自然"""
    patterns = [
        (r'创新、便捷、高效', '既创新又便捷'),
        (r'快速、简单、方便', '快速且使用简单'),
        (r'高效、精准、全面', '高效且精准'),
    ]
    for old, new in patterns:
        text = text.replace(old, new)
    return text

def remove_weasel_words(text):
    """去掉AI爱用的模糊归属词"""
    replacements = [
        ("专家表示", "实际上"),
        ("研究表明", "测试发现"),
        ("数据显示", "实测显示"),
        ("有人认为", ""),
        ("众所周知", ""),
        ("值得注意的是", ""),
        ("不难发现", ""),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text

def fix_filler(text):
    """替换填充词"""
    for phrase in FILLER_PHRASES:
        text = text.replace(phrase, '')
    return text

def fix_ai_vocab(text):
    """替换过度使用的AI词汇"""
    for word in AI_VOCAB:
        text = text.replace(word, '')
    # [修复] 仅清理多余的空格（水平空白），保留换行符
    text = re.sub(r'[ \t]+', ' ', text)
    return text

def fix_not_only_but(text):
    """修复 'Not only...but...' 中文版"""
    text = re.sub(r'不仅[^\n。，]+，[^\n]+也[^\n。，]+', lambda m: m.group(0).replace('，', '。').replace('，', ''), text)
    return text

def fix_specific(text):
    """处理具体问题"""
    # [修复] 不再移除 Markdown 标题和加粗，保留文档结构
    # text = re.sub(r'^### (.+)$', r'\1', text, flags=re.MULTILINE)
    # text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    return text

def humanize(text):
    """去AI味主函数"""
    steps = [
        remove_em_dash,
        fix_rule_of_three,
        remove_weasel_words,
        fix_filler,
        fix_ai_vocab,
        fix_not_only_but,
        fix_specific,
    ]
    for step in steps:
        text = step(text)
    # 清理多余空行，最多保留两个连续换行
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text


# ── 读取草稿并处理 ──────────────────────────────────────────
with open('_article_drafts.json', encoding='utf-8') as f:
    drafts = json.load(f)

print(f"Processing {len(drafts)} drafts...\n")

processed = {}
for slug, art in drafts.items():
    raw = art["content"]
    # 核心修复：如果是英文文章（lang: en），跳过过度破坏的中文词汇处理，只做基础清理
    is_english = art.get('lang') == 'en'
    
    if is_english:
        # 英文仅做换行符清理和基本空格合并
        text = re.sub(r'[ \t]+', ' ', raw)
        text = re.sub(r'\n{3,}', '\n\n', text)
        humanized = text.strip()
    else:
        humanized = humanize(raw)
        
    print(f"[{slug}] ({'EN' if is_english else 'ZH'})")
    print(f"  Original: {len(raw)} chars")
    print(f"  After:   {len(humanized)} chars")
    print(f"  Preview: {humanized[:100].replace('\n', ' ')}...")
    print()
    processed[slug] = humanized

# 保存处理后的结果
with open('_articles_humanized.json', 'w', encoding='utf-8') as f:
    json.dump(processed, f, ensure_ascii=False, indent=2)
print("Humanized drafts saved.")
