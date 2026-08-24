"""#15 分类规则引擎 — 数据驱动的工具分类建议与校验

读取 data/classification_rules.json（单一数据源），对工具做关键词评分分类，
供 AI工具采集 自动化预分类、以及对现有 tools.json 做分类一致性校验。

用法：
  python scripts/classify_tool.py --validate
      校验 tools.json 现有工具分类是否与规则一致，输出分歧清单
  python scripts/classify_tool.py --name "可灵AI" --desc "快手推出的AI视频生成工具" --tags "AI视频,文生视频"
      对单个工具（新采集）给出建议 category + subcategory
  python scripts/classify_tool.py --text "AI法律合同审查工具"
      直接对一段文本给出建议分类
"""
import json
import os
import argparse
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RULES_FILE = os.path.join(DATA_DIR, 'classification_rules.json')
TOOLS_FILE = os.path.join(DATA_DIR, 'tools.json')


def load_rules():
    with open(RULES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _tokenize(text):
    return re.findall(r'[a-zA-Z]+|[一-鿿]+', (text or '').lower())


def suggest(text, rules):
    """对一段文本返回 (category, subcategory, score, matched)"""
    tokens = set(_tokenize(text))
    raw = (text or '').lower()
    best_cat, best_sub, best_score, best_matched = None, None, 0, []

    special = rules.get('special_rules', [])
    for sp in special:
        for kw in sp.get('match', []):
            if kw.lower() in raw:
                return sp['force_category'], None, 100, [kw]

    for cat, cfg in rules.get('categories', {}).items():
        score = 0
        matched = []
        # 仅用 keywords 评分（examples 仅作 LLM 参考，不参与关键词匹配，避免跨类泄漏）
        kws = cfg.get('keywords', [])
        for kw in kws:
            k = kw.lower()
            if k in raw or k in tokens:
                score += 2
                matched.append(kw)
        if score > best_score:
            best_score, best_cat, best_matched = score, cat, matched
        # 子类
        for sub, subkws in cfg.get('subcats', {}).items():
            s_score = 0
            for kw in subkws:
                k = kw.lower()
                if k in raw or k in tokens:
                    s_score += 2
            if s_score > 0 and s_score >= best_score:
                # 子类仅在父类得分接近时采用
                if best_cat == cat:
                    best_sub = sub
                    best_matched = matched + [f'[{sub}]{w}' for w in subkws if w.lower() in raw]

    return best_cat, best_sub, best_score, best_matched


def tool_text(tool):
    parts = [tool.get('name', ''), tool.get('description', ''), tool.get('category', '')]
    tags = tool.get('tags', [])
    if isinstance(tags, list):
        for tg in tags:
            if isinstance(tg, dict):
                parts.append(tg.get('text', ''))
            else:
                parts.append(str(tg))
    return ' '.join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--validate', action='store_true', help='校验 tools.json 分类一致性')
    ap.add_argument('--name', default='')
    ap.add_argument('--desc', default='')
    ap.add_argument('--tags', default='')
    ap.add_argument('--text', default='')
    args = ap.parse_args()
    rules = load_rules()

    if args.validate:
        with open(TOOLS_FILE, 'r', encoding='utf-8') as f:
            tools = json.load(f)
        mismatches = []
        for t in tools:
            cur_cat = t.get('category', '')
            cur_sub = t.get('subcategory', '')
            sug_cat, sug_sub, score, matched = suggest(tool_text(t), rules)
            if sug_cat and sug_cat != cur_cat and score >= 4:
                mismatches.append({
                    'slug': t.get('slug', '?'),
                    'name': t.get('name', '?'),
                    'current': cur_cat,
                    'suggested': sug_cat,
                    'score': score,
                    'matched': matched[:5],
                })
        print(f'[classify] 校验 {len(tools)} 个工具，发现 {len(mismatches)} 处分类分歧（score≥4）:')
        for m in mismatches:
            print(f'  - {m["name"]} ({m["slug"]}): 当前「{m["current"]}」→ 建议「{m["suggested"]}」 命中{list(m["matched"])}')
        if mismatches:
            out = os.path.join(DATA_DIR, 'classification_mismatches.json')
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(mismatches, f, ensure_ascii=False, indent=2)
            print(f'[classify] 分歧清单已写: {out}')
        return

    # 单工具建议
    if args.text:
        text = args.text
    else:
        text = f'{args.name} {args.desc} {args.tags}'
    if not text.strip():
        print('请提供 --text 或 --name/--desc/--tags')
        return
    cat, sub, score, matched = suggest(text, rules)
    print(f'建议分类: {cat}' + (f' / 子类: {sub}' if sub else ''))
    print(f'置信分: {score}  命中: {list(matched)}')


if __name__ == '__main__':
    main()
