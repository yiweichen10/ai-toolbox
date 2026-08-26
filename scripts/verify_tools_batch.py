#!/usr/bin/env python3
"""
verify_tools_batch.py — 全量工具联网核查系统

架构: 本脚本 = 状态管理 + 批控; Agent = 联网核实执行器。
Agent 每批 N 个工具, 用 WebSearch/WebFetch 核实后, 将结果 JSON 传给 --apply 回写。

工作流:
  1. python verify_tools_batch.py --init          # 一次性初始化核查状态
  2. python verify_tools_batch.py --next 10        # 输出下一批 10 个待核查工具
  3. [Agent 联网核实, 产出 results.json]
  4. python verify_tools_batch.py --apply results.json  # 回写 tools.json
  5. 重复 2-4 直到全部完成
  6. python verify_tools_batch.py --status         # 随时查看进度

核查原则:
  - URL 红线: 必须是品牌官方域名, 禁止 www.{slug}.com 猜测
  - 未知留白: 无官网明确来源的字段留空, 不编任何数字/价格/功能
  - 冲突存疑: 多源信息冲突 -> conflict=true, 不标 content_verified
  - 可见字段回写: confidence=high 且无 conflict 时, 用核实值覆盖 price/rating/pros/cons/faq/tags/description/features/category 等可见字段; 否则仅留 verified_* 审计轨迹不覆盖
  - 编造数据纠正: 编造星级 rating 一律改为"暂无评分"(除非有真实来源); 死链 related 在 --apply 外另有规整脚本清理
"""

import json
import os
import sys
import argparse
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_JSON = os.path.join(BASE_DIR, 'data', 'tools.json')
STATE_JSON = os.path.join(BASE_DIR, 'data', 'verify_state.json')

TODAY = datetime.now().strftime('%Y-%m-%d')

# ============================================================
# 优先级规则: 决定核查顺序
# ============================================================
PRIORITY_KEYWORDS = [
    # P0: 大牌AI产品 + 首页热门
    'chatgpt', 'claude', 'gemini', 'copilot', 'midjourney', 'dall-e', 'stable-diffusion',
    'cursor', 'kimi', 'doubao', 'deepseek', 'qwen', 'hunyuan', 'ernie', 'spark',
    'windsurf', 'bolt', 'v0', 'lovable', 'replit', 'github',
    'runway', 'pika', 'sora', 'kling', 'suno', 'udio', 'elevenlabs',
    'notion', 'canva', 'figma', 'photoshop',
    'perplexity', 'gemini-deep-research',
    'comfyui', 'automatic1111',
    # P1: 知名/高流量
    'gamma', 'beautiful', 'descript', 'synthesia', 'heygen', 'invideo',
    'jasper', 'copy.ai', 'writesonic', 'rytr',
    'otter', 'fireflies', 'fathom',
    'mistral', 'llama', 'grok',
    'ideogram', 'leonardo', 'recraft',
    'make', 'zapier', 'n8n',
]


def priority_score(tool):
    """计算核查优先级, 分数越高越优先"""
    score = 0
    slug = (tool.get('slug') or '').lower()
    name = (tool.get('name') or '').lower()

    # 关键词匹配
    for kw in PRIORITY_KEYWORDS:
        if kw in slug or kw in name:
            score += 100
            break

    # badged 热门工具
    badge = tool.get('badge', {})
    if isinstance(badge, dict) and badge.get('type') == 'hot':
        score += 50

    # 有 version 相关内容的工具 (版本型工具容易过时)
    desc = (tool.get('description') or '')
    if any(v in desc for v in ['2026', 'GPT-5', 'Claude', 'Sonnet', 'Fable', 'Opus',
                                 '3.0', '4.0', '5.0', '5.5', '5.6',
                                 'v2', 'v3', 'v4', 'v5']):
        score += 30

    # 价格明确写的 (容易过时, 需要核查)
    if tool.get('price'):
        score += 10

    # 从未核查过的优先
    if not tool.get('last_verified'):
        score += 20

    return score


# ============================================================
# 状态管理
# ============================================================

def load_tools():
    """分片优先加载(真源 data/tools/*.json), 单体仅作回退(2026-08-26 去单体化)。"""
    try:
        from data_store import load_all_tools
        return load_all_tools()
    except Exception:
        with open(TOOLS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)


def save_tools(d):
    """去单体化后只写分片 data/tools/<slug>.json(一个工具一个文件)。
    单体 tools.json 不再写入/不再备份(2026-08-26 任务#7: 干掉单体)。
    """
    try:
        from data_store import save_tool
    except Exception:
        save_tool = None
    n = 0
    for t in d:
        if not isinstance(t, dict) or not t.get('slug'):
            continue
        if save_tool is not None:
            save_tool(t, indent=2)   # 写分片, 单体存在才同步(删掉单体后自动只写分片)
        else:
            sp = os.path.join(BASE_DIR, 'data', 'tools', f"{t['slug']}.json")
            os.makedirs(os.path.dirname(sp), exist_ok=True)
            with open(sp, 'w', encoding='utf-8') as f:
                json.dump(t, f, ensure_ascii=False, indent=2)
        n += 1
    print(f"[verify] 已写 {n} 个工具分片 (data/tools/*.json), 不再写单体")


def load_state():
    if not os.path.exists(STATE_JSON):
        return {'_meta': {'version': 1, 'created': TODAY}, 'tools': {}}
    with open(STATE_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_state(s):
    with open(STATE_JSON, 'w', encoding='utf-8') as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


# ============================================================
# --init: 初始化核查状态
# ============================================================

def cmd_init():
    tools = load_tools()
    state = load_state()

    slugs_in_state = set(state.get('tools', {}).keys())

    for t in tools:
        slug = t.get('slug')
        if not slug:
            continue
        if slug not in slugs_in_state:
            state['tools'][slug] = {
                'name': t.get('name', slug),
                'status': 'unverified',  # unverified | in_progress | verified | conflict
                'category': t.get('category', ''),
                'priority': priority_score(t),
                'attempts': 0,
                'last_attempt': None,
                'verified_at': None,
                'confidence': None,
                'notes': '',
            }

    state['_meta']['updated'] = TODAY
    state['_meta']['total'] = len(state['tools'])
    save_state(state)

    verified = sum(1 for v in state['tools'].values() if v['status'] == 'verified')
    unverified = sum(1 for v in state['tools'].values() if v['status'] == 'unverified')
    print(f"[init] 状态初始化完成: {state['_meta']['total']} 个工具")
    print(f"  已核查: {verified}")
    print(f"  待核查: {unverified}")


# ============================================================
# --next N: 输出下一批待核查工具
# ============================================================

def cmd_next(batch_size, stale_days=120):
    tools = load_tools()
    state = load_state()
    st = state.get('tools', {})

    # 建 slug->tool 映射
    tool_map = {t['slug']: t for t in tools if t.get('slug')}

    # 新鲜度回收窗口: verified_at 早于该日期的已核工具, 重新纳入复核查
    # 目的: 捕捉"纯暗降/静默调价"(无新闻/无版本动态, 普通版本监控遗漏的场景)
    cutoff = (datetime.now() - timedelta(days=stale_days)).strftime('%Y-%m-%d')

    # 筛选未核查的 + 过期需复核查的(stale verified)
    candidates = []
    for slug, info in st.items():
        if info['status'] in ('unverified', 'conflict'):
            tool = tool_map.get(slug, {})
            # 已裁决的冲突项(已在 tools.json 留 conflict_note, 待最终存疑清单统一处理)不再重选,
            # 把名额让给真正未核查的工具, 避免虚构/已标记条目反复占用批次
            if tool.get('conflict_note'):
                continue
            candidates.append((slug, info, tool))
        elif info['status'] == 'verified' and info.get('verified_at') and info['verified_at'] < cutoff:
            # 已核但超过新鲜度窗口 → 纳入复核查(静默调价/暗降捕捉)
            tool = tool_map.get(slug, {})
            candidates.append((slug, info, tool))

    # 按优先级降序
    candidates.sort(key=lambda x: -x[1].get('priority', 0))

    batch = candidates[:batch_size]

    # 标记为 in_progress
    for slug, info, _ in batch:
        info['status'] = 'in_progress'
        info['last_attempt'] = TODAY
        info['attempts'] = info.get('attempts', 0) + 1
    state['_meta']['updated'] = TODAY
    save_state(state)

    # 输出核查清单 (Agent 读取这个 JSON)
    briefs = []
    for slug, info, tool in batch:
        brief = {
            'slug': slug,
            'name': tool.get('name', slug),
            'priority': info.get('priority', 0),
            'category': tool.get('category', ''),
            'current_url': tool.get('url', ''),
            'current_price': tool.get('price', ''),
            'current_platform': tool.get('platform', ''),
            'current_description': (tool.get('description') or '')[:200],
            'current_features': tool.get('features', [])[:8],
            'verify_items': [
                'official_url',      # 官方真实网址 (Tier-1 官方域名, 交叉验证)
                'publisher',         # 发布方/公司
                'what_is_it',        # 一句话定位
                'price_plans',       # 最新定价/套餐 (官网明确写的, 否则"暂未公开")
                'platforms',         # 平台: Web/API/Desktop/iOS/Android 等
                'core_features',     # 核心功能 3-5 条 (官网明确列出, 禁止编造)
                'rating_source',     # 真实评分来源(官方商店/G2/Capterra/Trustpilot等)或"暂无权威评分"; 现有 rating 多为编造需纠正
                'pros_cons',         # 现有 pros/cons 是否含不实声称(如吹嘘不存在的功能/已过时的缺点), 需修正处
                'faq',               # 现有 faq 中是否有编造事实/过时信息, 需修正处
                'tags',              # 现有 tags 标签是否准确
                'category_check',    # 现有 category 分类是否准确
                'intro_description', # 现有 description 短介绍是否含幻觉(错误状态/定价/平台/过时数字)
                'long_content',      # 现有 content 长文介绍是否含幻觉, 需修正处
            ],
            'instruction': (
                f"请用 WebSearch + WebFetch 核实以上 verify_items。\n"
                f"URL 红线: 必须来自品牌官方域名, 禁止 www.{slug}.com 猜测。\n"
                f"未知留白: 无官网来源的不填, 不编数字/价格/功能。\n"
                f"【评分 rating】本站 rating 为编辑评分(代表该工具受欢迎度/实用度的编辑判断), 保留不剥离。"
                f"请基于真实信号(访问量/市场地位/可查到的用户口碑)判断当前编辑评分是否合理, "
                f"若需调整给出 verified_rating(具体星级如'⭐4.6'); 若查到权威外部评分可填 rating_source 备注, "
                f"但不要编造外部星级, 也不要填'暂无评分'(编辑评分始终保留)。\n"
                f"【pros/cons】逐条核对: 不实声称(吹嘘不存在的功能)或已过时缺点必须修正, 用 verified_pros/verified_cons 给准确列表。\n"
                f"【faq】核对是否有编造事实/过时信息, 用 verified_faq 给准确 QA 列表(原已准确可保留)。\n"
                f"【tags/category】核对标签与分类是否准确, 用 verified_tags/verified_category 纠正。\n"
                f"同时检查现有 description / features / content 长文介绍是否含幻觉"
                f"(错误状态如已停服却称在售、错误定价/平台、过时数字如集成数/语言数/数字人数), "
                f"用 verified_description 给出修正后的准确短介绍(原介绍已准确可填原句); "
                f"【description 首句铁律】第一句必须是\"用户利益句\"而非官方定位: 至少含免费/价格/核心功能/使用场景之一(如\"XX 免费AI助手，支持超长上下文与文档分析\")；禁止\"XX推出的XX工具\"式官方复述开头（标题引擎会把它变成无点击理由的标题）。\n"
                f"price_short 给出回填页面 price 字段的简明准确价(如原价错则必须修正); "
                f"content_flags 列出长文问题; corrected_content 仅在长文有严重幻觉"
                f"(如已停服却称在售)时提供修正全文, 否则留空。\n"
                f"输出格式见下方 results 模板。"
            ),
        }
        briefs.append(brief)

    output = {
        '_meta': {
            'batch_size': len(briefs),
            'date': TODAY,
            'remaining_unverified': sum(1 for v in st.values() if v['status'] in ('unverified', 'conflict')),
        },
        'tools': briefs,
        'results_template': {
            'slug': '<工具slug>',
            'official_url': '<核实后真实网址>',
            'publisher': '<发布方/公司名>',
            'what_is_it': '<一句话定位, 基于官网描述>',
            'price_plans': '<最新定价, 如 Free / Pro $20/mo / Enterprise 询价>',
            'price_short': '<回填到页面 price 字段的简明价, 如 "免费版 + Pro $20/月起" / "€20/月起(云) 自托管免费" / "已停服"; 仅 high 置信且无冲突时回填>',
            'platforms': '<Web, API, iOS, Android, Desktop 等>',
            'core_features': ['<功能1>', '<功能2>', '<功能3>'],
            'verified_rating': '<真实评分, 如"4.3(基于G2 1.2k评测)"或"暂无评分"; 禁止编造星级>',
            'rating_source': '<评分来源URL或"暂无权威评分">',
            'verified_pros': ['<准确优点1>', '<准确优点2>'],
            'verified_cons': ['<准确缺点1>', '<准确缺点2>'],
            'verified_faq': [{'q': '<准确问题>', 'a': '<基于官方事实的答案>'}],
            'verified_tags': ['<准确标签1>', '<准确标签2>'],
            'verified_category': '<准确的分类名(须与现有15类之一一致)>',
            'verified_description': '<修正后的准确短介绍(基于官方事实); 若原介绍已准确可填原句>',
            'content_flags': '<长文 content 中的问题清单, 如"仍称在售/错误定价/过时数字"; 无则留空>',
            'corrected_content': '<仅当长文有严重幻觉(如已停服却称在售)时提供修正全文; 否则留空>',
            'confidence': '<high / medium / low>',
            'conflict': False,
            'conflict_note': '<如多源信息冲突, 在此说明; 否则留空>',
            'source_urls': ['<核实用的URL1>', '<URL2>'],
            'notes': '<Agent 备注, 如官网无定价页、页面404等>',
        },
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


# ============================================================
# --apply results.json: 将核查结果写回 tools.json
# ============================================================

def cmd_apply(results_file):
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)

    if isinstance(results, dict) and 'tools' in results:
        results = results['tools']  # 支持批量格式
    if not isinstance(results, list):
        results = [results]

    tools = load_tools()
    state = load_state()
    tool_map = {t['slug']: t for t in tools}
    st = state.setdefault('tools', {})

    applied = 0
    skipped = 0
    conflicts = 0
    applied_slugs = []

    for r in results:
        slug = r.get('slug')
        if not slug:
            print(f"[apply] 跳过: 缺少 slug")
            skipped += 1
            continue

        tool = tool_map.get(slug)
        if not tool:
            print(f"[apply] 跳过: tools.json 中无 slug={slug}")
            skipped += 1
            continue

        # 写 verified_* 字段 (合并写: 仅当 results 提供非空值才覆盖, 防止部分重跑清空已核实字段)
        if r.get('official_url'):
            tool['verified_url'] = r['official_url']
        if r.get('publisher'):
            tool['verified_publisher'] = r['publisher']
        if r.get('what_is_it'):
            tool['verified_what'] = r['what_is_it']
        if r.get('price_plans'):
            tool['verified_price'] = r['price_plans']
        if r.get('platforms'):
            tool['verified_platform'] = r['platforms']
        # 标记 (先算 ok, 供下方 description/features/content/price 门控)
        tool['last_verified'] = TODAY
        tool['confidence'] = r.get('confidence', 'medium')
        tool['conflict'] = bool(r.get('conflict', False))

        # 门控: 仅 high 置信且无冲突时, 才用核实值覆盖对外可见字段
        ok = (r.get('confidence') == 'high' and not r.get('conflict'))

        # 介绍文案核查: description / features / content 长文
        # 原则: verified_* 审计轨迹始终写入; 仅 ok 时覆盖对外可见字段 (防止 conflict/low 把内部备注写进页面)
        if r.get('core_features'):
            tool['verified_features'] = r['core_features']
            if ok:
                tool['features'] = r['core_features']   # 覆盖原 features 为核实版
        if r.get('verified_description'):
            tool['verified_description'] = r['verified_description']
            if ok:
                tool['description'] = r['verified_description']   # 覆盖原短介绍为准确版
        if r.get('content_flags'):
            tool['content_flags'] = r['content_flags']

        # ===== 长文覆盖防护（2026-08-01 事故修复）=====
        # 背景: 7/31 版本批次用精简 corrected_content(730字) 整体覆盖了 2768 字完整长文,
        #       导致 85 个工具实测数据/FAQ/来源/GEO结构 全部丢失。
        # 原则: verified_* 审计轨迹始终写; 覆盖对外可见 content 前必须通过完整性检查。
        #       不满足检查 → 拒绝覆盖 content, 但保留修正文到 verified_content 供人工复核。
        if r.get('corrected_content'):
            if ok:
                old_content = tool.get('content', '')
                new_content = r['corrected_content']
                old_len, new_len = len(old_content), len(new_content)

                def _h2_count(c):
                    return sum(1 for l in c.split('\n') if l.strip().startswith('## ') and not l.strip().startswith('### '))

                old_h2, new_h2 = _h2_count(old_content), _h2_count(new_content)

                # 防护1: 长度保护 — 新内容 < 原内容50% → 拒绝覆盖
                len_ok = new_len >= old_len * 0.5 or old_len < 300

                # 防护2: 结构保护 — 覆盖后 H2 数 < 原 H2 数 → 拒绝覆盖
                struct_ok = new_h2 >= old_h2 or old_h2 < 3

                # 防护3: 区块保护 — 原含 FAQ/实测数据/来源 且新文缺失 → 拒绝覆盖
                block_ok = True
                for blk, blk_kw in [("FAQ", ["常见问题", "FAQ"]), ("实测", ["实测"]), ("来源", ["来源", "Source"])]:
                    if any(k in old_content for k in blk_kw) and not any(k in new_content for k in blk_kw):
                        block_ok = False
                        break

                # 防护4: 溯源保护 — 覆盖长文必须有来源, 防编造
                sources = r.get('source_urls') or r.get('sources') or []
                trace_ok = bool(sources) or ('来源' in new_content or 'Source' in new_content)

                if len_ok and struct_ok and block_ok and trace_ok:
                    tool['content_flags'] = r.get('content_flags') or '原长文含幻觉, 已重写'
                    tool['content'] = new_content
                else:
                    # 拒绝覆盖: 保留原长文, 修正文存 verified_content 供人工复核
                    tool['verified_content'] = new_content
                    tool['content_flags'] = (r.get('content_flags') or '修正文未通过完整性检查, 已拒绝覆盖') + \
                        ' | 拒绝原因: ' + ';'.join(
                            x for x, okx in [("长度缩水>50%", len_ok), ("H2结构减少", struct_ok), ("关键区块丢失", block_ok), ("无来源", trace_ok)] if not okx)
                    tool['content_blocked'] = True
                    print(f"[apply][防护] {slug}: 拒绝覆盖修正文 (原{old_len}字/H2={old_h2} -> 新{new_len}字/H2={new_h2}, 原因: {';'.join(x for x, okx in [('长度', len_ok), ('结构', struct_ok), ('区块', block_ok), ('溯源', trace_ok)] if not okx)}) 修正文已存 verified_content")
                    skipped += 1
        elif r.get('verified_content'):
            # 历史字段兼容
            tool['verified_content'] = r['verified_content']

        # 价格可见字段回填: 仅 high 置信且无冲突时, 用核实简明价覆盖页面 price
        # (conflict 或 medium/low 不覆盖, 保留原值避免引入不确定信息)
        if (r.get('price_short') and ok):
            tool['price'] = r['price_short']
            tool['price_verified'] = True

        KNOWN_CATS = {'AI编程','AI开发','AI对话','AI视频','AI效率','AI设计','AI办公',
                      'AI行业应用','AI绘画','AI音频','AI写作','AI智能体','AI搜索','AI自动化','AI翻译',
                      'AI学习','AI检测','AI提示词'}

        # rating: 本站编辑评分(代表受欢迎度/实用度的编辑判断), 保留不剥离。
        # 仅当 Agent 给出具体星级评分时才更新; "暂无评分"等不覆盖, 维持编辑评分。
        if r.get('verified_rating'):
            tool['verified_rating'] = r['verified_rating']
            tool['rating_source'] = r.get('rating_source', '')
            if ok and '暂无' not in str(r['verified_rating']):
                tool['rating'] = r['verified_rating']
                tool['rating_verified'] = True
            elif ok:
                tool['rating_verified'] = True  # 已核查, 维持原编辑评分不剥离

        # pros/cons: 逐条核对后覆盖
        if r.get('verified_pros'):
            tool['verified_pros'] = r['verified_pros']
            if ok:
                tool['pros'] = r['verified_pros']
        if r.get('verified_cons'):
            tool['verified_cons'] = r['verified_cons']
            if ok:
                tool['cons'] = r['verified_cons']

        # faq: 核对后覆盖
        if r.get('verified_faq'):
            tool['verified_faq'] = r['verified_faq']
            if ok:
                tool['faq'] = r['verified_faq']

        # tags: 核对后覆盖
        if r.get('verified_tags'):
            tool['verified_tags'] = r['verified_tags']
            if ok:
                tool['tags'] = r['verified_tags']

        # category: 仅在属于标准15类时纠正(防止破坏分类路由)
        if r.get('verified_category'):
            tool['verified_category'] = r['verified_category']
            if ok and r['verified_category'] in KNOWN_CATS:
                tool['category'] = r['verified_category']
        if r.get('conflict_note'):
            tool['conflict_note'] = r['conflict_note']
        tool['source_urls'] = r.get('source_urls', [])
        tool['verify_notes'] = r.get('notes', '')

        # content_verified 仅在 confidence=high 且无冲突时置 true
        if tool['confidence'] == 'high' and not tool['conflict'] and not tool.get('content_blocked'):
            tool['content_verified'] = True
        else:
            tool['content_verified'] = False

        # 如果 URL 变了, 更新原始 url 字段
        old_url = tool.get('url', '')
        new_url = r.get('official_url', '')
        if new_url and new_url != old_url:
            print(f"  URL 更新: {slug} | {old_url} -> {new_url}")
            tool['url'] = new_url
            tool['url_previous'] = old_url

        # 同步 updated_date (2026-08-04 修复: 此前 apply 仅写 last_verified, 未写 updated_date,
        # 导致工具页"更新"日期回落到 created_date, 与"收录"日期相等。Ok=True 意味着数据被认定为
        # 正确版本, 对外可见字段已被覆盖, 此时同步更新日期以反映内容确实更新过。)
        if ok:
            tool['updated_date'] = TODAY

        # 更新 state
        if slug in st:
            st[slug]['status'] = 'conflict' if tool['conflict'] else 'verified'
            st[slug]['verified_at'] = TODAY
            st[slug]['confidence'] = tool['confidence']
            st[slug]['notes'] = r.get('notes', '')

        if tool['conflict']:
            conflicts += 1
        applied += 1
        applied_slugs.append(slug)

    state['_meta']['updated'] = TODAY
    save_tools(tools)   # 2026-08-26 去单体化: 只写分片 data/tools/*.json, 不再写单体
    save_state(state)

    print(f"[apply] 结果: {applied} 已应用, {conflicts} 冲突标记, {skipped} 跳过")


# ============================================================
# --status: 查看核查进度
# ============================================================

def cmd_status():
    state = load_state()
    st = state.get('tools', {})

    total = len(st)
    verified = sum(1 for v in st.values() if v['status'] == 'verified')
    unverified = sum(1 for v in st.values() if v['status'] == 'unverified')
    in_progress = sum(1 for v in st.values() if v['status'] == 'in_progress')
    conflict = sum(1 for v in st.values() if v['status'] == 'conflict')

    print(f"[status] 核查进度 @ {TODAY}")
    print(f"  总计:   {total}")
    print(f"  ✅ 已核查: {verified} ({verified*100//total if total else 0}%)")
    print(f"  🔄 进行中: {in_progress}")
    print(f"  ⚠️ 冲突:   {conflict}")
    print(f"  ⬜ 待核查: {unverified}  ({unverified*100//total if total else 0}%)")

    # 按 category 统计
    cats = {}
    for slug, info in st.items():
        c = info.get('category', '未知')
        if c not in cats:
            cats[c] = {'total': 0, 'verified': 0}
        cats[c]['total'] += 1
        if info['status'] == 'verified':
            cats[c]['verified'] += 1

    print("\n按分类:")
    for c in sorted(cats.keys()):
        d = cats[c]
        pct = d['verified'] * 100 // d['total'] if d['total'] else 0
        bar = '█' * (pct // 5) + '░' * (20 - pct // 5)
        print(f"  {c:10s}  {d['verified']:3d}/{d['total']:<3d}  [{bar}] {pct}%")

    # 列出待核查的高优先级
    print("\n待核查 TOP 10 (按优先级):")
    pending = [(slug, info) for slug, info in st.items()
               if info['status'] in ('unverified', 'conflict')]
    pending.sort(key=lambda x: -x[1].get('priority', 0))
    for slug, info in pending[:10]:
        prio = info.get('priority', 0)
        name = info.get('name', slug)
        status = info['status']
        print(f"  [{status:11s}] P{prio:4d}  {name:30s}  ({slug})")


# ============================================================
# --reset: 重置指定 slug 的状态 (重查用)
# ============================================================

def cmd_reset(slugs):
    state = load_state()
    st = state.get('tools', {})

    for slug in slugs:
        if slug in st:
            st[slug]['status'] = 'unverified'
            st[slug]['verified_at'] = None
            st[slug]['confidence'] = None
            st[slug]['notes'] = 'reset ' + TODAY
            print(f"[reset] {slug} -> unverified")
        else:
            print(f"[reset] {slug} 不在状态文件中")

    state['_meta']['updated'] = TODAY
    save_state(state)


# ============================================================
# --reconcile: 以 tools.json 真相重建 verify_state.json, 并清除"幽灵已核查"
#   幽灵已核查 = content_verified=true 但无 source_urls (旧流程标记, 无可溯源)
#   这些工具重置为 unverified, 重新进入 Agent 自检队列。
# ============================================================

def cmd_reconcile():
    tools = load_tools()
    state = load_state()
    st = state.setdefault('tools', {})

    # 确保 state 含全部 slug
    for t in tools:
        slug = t.get('slug')
        if slug and slug not in st:
            st[slug] = {
                'name': t.get('name', slug),
                'status': 'unverified',
                'category': t.get('category', ''),
                'priority': priority_score(t),
                'attempts': 0, 'last_attempt': None,
                'verified_at': None, 'confidence': None, 'notes': '',
            }

    phantom_reset = []   # content_verified=true 但无 source_urls -> 重置
    kept_verified = []   # 有 source_urls 的真核查, 保留
    kept_conflict = []   # 冲突, 保留

    for t in tools:
        slug = t.get('slug')
        if not slug:
            continue
        info = st[slug]
        has_sources = bool(t.get('source_urls'))
        is_conflict = bool(t.get('conflict'))

        if is_conflict:
            info['status'] = 'conflict'
            info['confidence'] = t.get('confidence') or 'medium'
            info['verified_at'] = t.get('last_verified')
            info['notes'] = t.get('verify_notes', '')
            kept_conflict.append(slug)
            continue

        if t.get('content_verified') and has_sources:
            # 真·Agent 自检产物, 保留
            info['status'] = 'verified'
            info['confidence'] = t.get('confidence') or 'high'
            info['verified_at'] = t.get('last_verified')
            info['notes'] = t.get('verify_notes', '')
            kept_verified.append(slug)
            continue

        if t.get('content_verified') and not has_sources:
            # 幽灵已核查: 旧流程标记, 无可溯源 -> 重置
            t['content_verified'] = False
            t['confidence'] = None
            t['conflict'] = False
            t['conflict_note'] = ''
            t['last_verified'] = None
            info['status'] = 'unverified'
            info['verified_at'] = None
            info['confidence'] = None
            info['notes'] = f"reconciled {TODAY}: 清除幽灵已核查(旧流程无source)"
            phantom_reset.append(slug)
            continue

        # 其余: content_verified=false
        if has_sources:
            # 经 Agent 核查但未达 high (如 medium) -> 标记已核查, 不强制重跑
            info['status'] = 'verified'
            info['confidence'] = t.get('confidence') or 'medium'
            info['verified_at'] = t.get('last_verified')
            info['notes'] = t.get('verify_notes', '')
        else:
            info['status'] = 'unverified'
            info['verified_at'] = None
            info['confidence'] = None

    state['_meta']['updated'] = TODAY
    state['_meta']['total'] = len(st)
    save_state(state)
    if phantom_reset:
        save_tools(tools)   # 回写 tools.json 清除幽灵标记

    verified = sum(1 for v in st.values() if v['status'] == 'verified')
    unverified = sum(1 for v in st.values() if v['status'] == 'unverified')
    conflict = sum(1 for v in st.values() if v['status'] == 'conflict')
    print(f"[reconcile] 已按 tools.json 真相重建状态")
    print(f"  真·已核查(有source): {len(kept_verified)}")
    print(f"  冲突保留:            {len(kept_conflict)}")
    print(f"  幽灵已核查已重置:    {len(phantom_reset)}")
    print(f"  重建后: 已核查 {verified} | 冲突 {conflict} | 待核查 {unverified}")
    if phantom_reset:
        print(f"  重置清单(前20): {phantom_reset[:20]}")


# ============================================================
# main
# ============================================================

def main():
    ap = argparse.ArgumentParser(description='全量工具联网核查批控系统')
    ap.add_argument('--init', action='store_true', help='初始化核查状态')
    ap.add_argument('--next', type=int, metavar='N', help='输出下一批 N 个待核查工具(含过期需复核查的 stale verified)')
    ap.add_argument('--stale-days', type=int, default=120, metavar='D',
                    help='已核查工具超过该天数(默认120)未复核查则重新纳入复核查')
    ap.add_argument('--apply', type=str, metavar='FILE', help='将核查结果 JSON 写回 tools.json')
    ap.add_argument('--status', action='store_true', help='查看核查进度')
    ap.add_argument('--reset', nargs='+', metavar='SLUG', help='重置指定工具状态为 unverified')
    ap.add_argument('--reconcile', action='store_true',
                    help='以 tools.json 真相重建状态, 清除幽灵已核查(无source的content_verified)')
    args = ap.parse_args()

    if args.init:
        cmd_init()
    elif args.next:
        cmd_next(args.next, stale_days=args.stale_days)
    elif args.apply:
        cmd_apply(args.apply)
    elif args.status:
        cmd_status()
    elif args.reset:
        cmd_reset(args.reset)
    elif args.reconcile:
        cmd_reconcile()
    else:
        # 默认显示 status
        cmd_status()


if __name__ == '__main__':
    main()
