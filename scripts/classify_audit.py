# -*- coding: utf-8 -*-
"""
分类校正审计脚本（只读，不改 tools.json）
作用：对现有工具跑"分类指纹规则 + tag 类目冲突"，产出疑似错分清单供人工 review。
输出：data/classify_audit_YYYY-MM-DD.json + 控制台可读报告。

判定逻辑（保守，宁漏勿错）：
  1. 每个工具 text = name + description + tags文本，统一小写
  2. 按类目强/中关键词打分（强=3，中=2）
  3. tag 中若含已知类目名 → 仅作交叉验证（描述独立支撑才采信，避免 tag 标错误报）
  4. inferred = 描述关键词最高分类（tag 不计入打分，只交叉验证）
  5. 标记疑似：
       HIGH   : 当前类目得分=0 且 某类目强信号>=3（当前无任何支撑）
       MEDIUM : 当前类目得分 < 他类强信号(>=3)（边界冲突，如 agent vs 自动化）
       TAGCONFLICT: tag 类目与 category 冲突，且描述独立支撑该 tag 类目
"""
import json, os, datetime

DATA = os.path.join(os.path.dirname(__file__), '..', 'data', 'tools.json')

# 类目关键词指纹：3=强(低误报)，2=中
RULES = {
    'AI智能体': {'s': ['智能体', 'agent框架', '多智能体', 'autonomous agent', 'ai agent', 'agent平台', '数字员工', '多代理', '智能体平台', 'agentic'],
                  'm': ['自主', 'agent']},
    'AI自动化': {'s': ['工作流', 'rpa', '浏览器自动化', '流程自动化', 'workflow automation', '自动化工作流', '无代码自动化', '低代码自动化'],
                  'm': ['自动化', '编排', '定时任务']},
    'AI编程':   {'s': ['代码生成', '代码补全', '编程助手', '代码助手', '代码审查', '写代码', 'github copilot', 'ide', 'copilot'],
                  'm': ['编程', '程序员', '软件开发', '调试']},
    'AI开发':   {'s': ['大模型平台', '模型托管', '向量数据库', '向量', 'embedding', '嵌入', 'rag', '检索增强', '语义检索', '知识库', '推理引擎', '大模型服务', '模型推理', '向量检索', '推理平台', 'api网关', 'fine-tune', '微调', 'llmops', 'rag平台', '模型部署', 'gpu云', '算力平台'],
                  'm': ['模型服务', '开发者平台', '模型api', 'ai平台', '知识库']},
    'AI写作':   {'s': ['写作', '文案', '文章生成', '润色', '改写', 'copywriting', '小红书文案', '公众号', '邮件撰写', '爆款文案', '提纲'],
                  'm': ['创作', '草稿', '小说', '博客']},
    'AI绘画':   {'s': ['文生图', 'text to image', '插画', '头像生成', 'ai作画', 'stable diffusion', 'midjourney', '图像生成', '生图', '绘画', '画图', '绘图'],
                  'm': ['配图', '艺术画', '二次元']},
    'AI设计':   {'s': ['logo', '海报', 'ui设计', '幻灯片', '排版', 'banner', '商标', '视觉设计', 'ppt设计', '封面设计', '原型设计'],
                  'm': ['设计', '配色', '网页设计']},
    'AI视频':   {'s': ['文生视频', 'text to video', '数字人', '口播', '视频剪辑', '混剪', '视频生成', '换脸', '视频换脸'],
                  'm': ['短视频', 'ai视频', '配音视频']},
    'AI音频':   {'s': ['配音', 'tts', '音乐生成', '变声', '声音克隆', '播客', '语音合成', '语音生成'],
                  'm': ['音频', '语音', '音乐', '音效', '唱歌']},
    'AI办公':   {'s': ['表格', 'excel', '会议纪要', '思维导图', '演示文稿', 'ppt制作', '文档处理', '脑图', 'word'],
                  'm': ['办公', '文档', '笔记', '幻灯片', 'office']},
    'AI效率':   {'s': ['浏览器插件', '提示词', 'prompt', '知识管理', '第二大脑', '效率工具', '摘要工具', '总结助手'],
                  'm': ['效率', '插件', '总结', '摘要', '个人助手']},
    'AI对话':   {'s': ['聊天机器人', 'chatbot', '聊天助手', '对话机器人', '问答机器人', '通用助手'],
                  'm': ['对话', '聊天', '问答']},
    'AI搜索':   {'s': ['聚合搜索', '学术搜索', '问答搜索', '搜索引擎', 'search engine', '检索'],
                  'm': ['搜索']},
    'AI翻译':   {'s': ['翻译', 'translate', '中英互译', '多语言翻译'],
                  'm': ['多语言', '本地化']},
    'AI行业应用': {'s': ['医疗', '法律', '金融', '招聘', '客服', '营销', '电商', '机器人', '具身', '人形机器人', '面试', '销售', '税务', '合同', '简历', '教育', '律所', '问诊'],
                  'm': ['行业', '垂直', '企业应用']},
}

KNOWN_CATS = set(RULES.keys())

def score_tool(text):
    scores = {c: 0 for c in RULES}
    for cat, kw in RULES.items():
        for k in kw['s']:
            if k in text:
                scores[cat] += 3
        for k in kw['m']:
            if k in text:
                scores[cat] += 2
    return scores

def main():
    with open(DATA, encoding='utf-8') as f:
        tools = json.load(f)

    suspects = []
    for t in tools:
        name = t.get('name', '')
        desc = t.get('description', '') or ''
        tag_texts = [tg.get('text', '') for tg in t.get('tags', []) if isinstance(tg, dict)]
        current = t.get('category', '无')
        text = (name + ' ' + desc + ' ' + ' '.join(tag_texts)).lower()

        kw_scores = score_tool(text)   # 仅基于 name+desc+tag文本关键词（不含 tag 类目加成）

        # tag 类目仅作交叉验证
        tag_cats = [tt for tt in tag_texts if tt in KNOWN_CATS]

        # 推断类目（以描述为主，tag 不计入打分）
        inferred = max(kw_scores, key=kw_scores.get)
        inferred_score = kw_scores[inferred]
        current_score = kw_scores.get(current, 0)

        reason = []
        conf = None

        # 规则A：tag 类目与 category 冲突，且描述独立支撑该 tag 类目（避免 tag 标错 → 误报）
        if tag_cats and current not in tag_cats:
            agree = [tc for tc in tag_cats if kw_scores[tc] >= 3]
            if agree and agree[0] != current:
                conf = 'TAGCONFLICT'
                inferred = agree[0]
                inferred_score = kw_scores[inferred]
                reason.append(f'tag类目={tag_cats} 且描述支撑"{inferred}"，与 category="{current}" 冲突')

        # 规则B：当前类目无任何强支撑，且他类有强信号（基于描述）
        if conf is None and current_score == 0 and inferred_score >= 3 and inferred != current:
            conf = 'HIGH'
            reason.append(f'当前"{current}"无关键词支撑，描述推断应为"{inferred}"')

        # 规则C：边界冲突（当前有弱支撑但不足，他类强信号更高）
        if conf is None and current_score < inferred_score and inferred_score >= 3 and inferred != current:
            conf = 'MEDIUM'
            reason.append(f'边界冲突：当前"{current}"({current_score}) < 推断"{inferred}"({inferred_score})')

        if conf:
            # 收集命中关键词
            hits = []
            for cat in [inferred, current]:
                if cat in RULES:
                    for k in RULES[cat]['s']:
                        if k in text: hits.append(f'{cat}:{k}(强)')
                    for k in RULES[cat]['m']:
                        if k in text: hits.append(f'{cat}:{k}(中)')
            suspects.append({
                'name': name,
                'slug': t.get('slug', ''),
                'current': current,
                'inferred': inferred,
                'current_score': current_score,
                'inferred_score': inferred_score,
                'tag_cats': tag_cats,
                'confidence': conf,
                'reason': '；'.join(reason),
                'matched': hits[:6],
            })

    # 排序：HIGH/TAGCONFLICT 优先
    order = {'TAGCONFLICT': 0, 'HIGH': 1, 'MEDIUM': 2}
    suspects.sort(key=lambda x: (order.get(x['confidence'], 9), -x['inferred_score']))

    out = {
        'generated': datetime.date.today().isoformat(),
        'total_tools': len(tools),
        'suspect_count': len(suspects),
        'by_confidence': {},
        'suspects': suspects,
    }
    for s in suspects:
        out['by_confidence'][s['confidence']] = out['by_confidence'].get(s['confidence'], 0) + 1

    out_path = os.path.join(os.path.dirname(DATA), f"classify_audit_{datetime.date.today().isoformat()}.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # 控制台报告
    print(f'工具总数: {len(tools)}')
    print(f'疑似错分: {len(suspects)} 条  (HIGH={out["by_confidence"].get("HIGH",0)} TAGCONFLICT={out["by_confidence"].get("TAGCONFLICT",0)} MEDIUM={out["by_confidence"].get("MEDIUM",0)})')
    print('=' * 70)
    for s in suspects:
        print(f'[{s["confidence"]:11s}] {s["name"][:24]:24s} | {s["current"]} → {s["inferred"]}')
        print(f'            理由: {s["reason"]}')
        if s['matched']:
            print(f'            命中: {", ".join(s["matched"])}')
        print()

if __name__ == '__main__':
    main()
