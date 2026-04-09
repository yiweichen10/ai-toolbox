#!/usr/bin/env python3
"""
程序化对比页生成器 (Programmatic Compare Pages Generator)
=========================================================
Phase 2 核心脚本：自动从 tools.json 中的工具组合，批量生成对比页面

功能：
1. 预定义热门对比组合（高搜索量词）
2. 自动发现同分类工具交叉对比
3. 调用 AI API 生成高质量对比文案
4. 输出 compare_data.json 供 build.py 构建静态HTML

使用方式：
    # 生成所有对比页数据
    python scripts/generate_compare_pages.py
    
    # 仅预览会生成多少个对比页
    python scripts/generate_compare_pages.py --dry-run
    
    # 强制重新生成（忽略已有缓存）
    python scripts/generate_compare_pages.py --force
    
    # 只生成特定工具相关的对比
    python scripts/generate_compare_pages.py --tool chatgpt
"""

import json
import os
import sys
import re
import time
from datetime import datetime
from itertools import combinations

# ── 路径配置 ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'tools.json')
OUTPUT_FILE = os.path.join(BASE_DIR, 'data', 'compare_data.json')
STATE_FILE = os.path.join(BASE_DIR, 'data', '_compare_state.json')

# ── AI API 配置（复用现有 DeepSeek-V3） ───────────────────
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
API_KEY = "sk-necmvkjjvnysmuelonjjdkwzrmepuqtempxyghojejkvqzne"
MODEL = "Pro/deepseek-ai/DeepSeek-V3.2"

# ============================================================
# 预定义热门对比组合（基于搜索量和用户需求）
# 这些是"必做"的高价值对比词
# ============================================================
HOT_COMPARES = [
    # AI对话类 — 搜索量最大
    ["chatgpt", "claude"],           # ChatGPT vs Claude — 全球AI双雄
    ["chatgpt", "deepseek"],         # ChatGPT vs DeepSeek — 中美对决（中文蓝海）
    ["claude", "deepseek"],          # Claude vs DeepSeek — 长文本 vs 性价比
    ["kimi", "doubao"],              # Kimi vs 豆包 — 国产双子星
    ["kimi", "tongyi"],              # Kimi vs 通义千问
    ["deepseek", "kimi"],            # DeepSeek vs Kimi — 国产最强之争
    ["chatgpt", "kimi"],             # ChatGPT vs Kimi — 海外vs国产
    ["deepseek", "doubao", "tongyi"], # 国产三巨头横评
    
    # AI绘画类
    ["midjourney", "sd"],            # Midjourney vs Stable Diffusion
    ["midjourney", "dalle"],          # Midjourney vs DALL-E
    ["midjourney", "keling"],         # Midjourney vs 可灵（国产AI视频/绘画）
    ["sd", "dalle"],                  # SD vs DALL-E
    ["keling", "runway"],             # 可灵 vs Runway（AI视频）
    
    # AI编程类
    ["cursor", "copilot"],            # Cursor vs GitHub Copilot
    ["cursor", "windsurf"],           # Cursor vs Windsurf
    ["copilot", "windsurf"],          # Copilot vs Windsurf
    
    # AI音乐类
    ["suno", "udio"],                 # Suno vs Udio
    
    # 跨类别热门对比
    ["chatgpt", "gemini"],            # ChatGPT vs Gemini
    ["midjourney", "comfyui"],        # Midjourney vs ComfyUI
]

# ── 对比维度模板（用于AI prompt） ─────────────────────────
COMPARE_DIMENSIONS = {
    "AI对话": ["回答准确性", "上下文理解", "中文能力", "代码能力", "写作质量", "响应速度", "价格性价比", "免费额度"],
    "AI绘画": ["画面质量", "风格多样性", "提示词理解", "控制精度", "生成速度", "价格", "易用性"],
    "AI编程": ["代码准确度", "语言支持", "IDE集成", "上下文理解", "智能补全", "调试能力", "价格"],
    "AI音乐": ["音质", "音乐性", "风格覆盖", "歌词理解", "控制精度", "生成速度", "免费额度"],
    "AI视频": ["视频质量", "一致性", "时长限制", "生成速度", "控制能力", "价格", "中文支持"],
    "通用": ["核心功能", "使用体验", "价格", "适合人群", "局限性"],
}


def load_tools():
    """加载工具数据，返回已发布的工具列表"""
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        tools = json.load(f)
    return [t for t in tools if t.get('published', False)]


def get_tool_by_slug(tools, slug):
    """通过slug查找工具"""
    for t in tools:
        if t['slug'] == slug:
            return t
    return None


def load_state():
    """加载已生成的对比状态"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"generated": {}, "last_updated": None}


def save_state(state):
    """保存状态"""
    state["last_updated"] = datetime.now().isoformat()
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def call_ai(prompt, max_tokens=4000):
    """调用DeepSeek-V3 API生成内容"""
    import urllib.request
    
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是一个专业的AI工具评测编辑，擅长深度对比分析不同AI工具的优劣势。你的对比文章有数据、有观点、有明确结论。输出中文。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }).encode('utf-8')
    
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"  [API Error] {e}")
        return None


def generate_compare_prompt(tools_in_compare):
    """
    为一组工具生成对比文章的prompt
    tools_in_compare: 工具对象列表
    """
    n = len(tools_in_compare)
    tool_names = " vs ".join([t['name'] for t in tools_in_compare])
    slugs = [t['slug'] for t in tools_in_compare]
    
    # 判断主分类
    categories = [t.get('category', '通用') for t in tools_in_compare]
    primary_cat = max(set(categories), key=categories.count)  # 出现最多的分类
    dimensions = COMPARE_DIMENSIONS.get(primary_cat, COMPARE_DIMENSIONS["通用"])
    
    # 收集每个工具的关键信息
    tool_infos = ""
    for t in tools_in_compare:
        tool_infos += f"""
【{t['name']}】
- 简介：{t.get('description', 'N/A')}
- 价格：{t.get('price', 'N/A')}
- 优点：{' | '.join(t.get('pros', [])) if t.get('pros') else 'N/A'}
- 缺点：{' | '.join(t.get('cons', [])) if t.get('cons') else 'N/A'}
- 核心功能：{' | '.join(t.get('features', [])[:5]) if t.get('features') else 'N/A'}
"""

    prompt = f"""请写一篇深度对比评测文章：{tool_names} 全面对比（2026年最新版）

## 要求：
1. 文章字数2500-3000字
2. 必须是**原创深度分析**，不要泛泛而谈
3. 要有明确的观点和结论（"谁更适合什么场景"）
4. 用具体的使用场景和例子说明，不要只列参数
5. 包含以下维度的对比：{"、".join(dimensions)}

## 工具基本信息：
{tool_infos}

## 文章结构要求：

### 标题
写一个吸引点击的SEO标题（包含工具名+"2026"+"对比/评测"，25-30字）

### 副标题
一句话概括这篇对比的核心结论

### 一、快速结论（给没时间的读者）
用3句话说清楚：各自最适合谁？总体推荐哪个？

### 二、核心参数对比表
做一个表格对比关键参数（价格、免费额度、核心优势、最佳场景等）

### 三、维度逐一深度对比
对每个维度给出：
- 具体表现描述
- 各自得分（满分5星）
- 实际使用场景举例

### 四、真实使用场景推荐
列出4-6个典型使用场景，每个场景推荐最合适的工具及理由

### 五、总结与购买建议
按人群/预算/需求给出明确建议

### 六、常见问题FAQ
准备3-4个用户最可能问的问题并回答

## 输出格式（严格JSON）：
{{
    "title": "文章标题",
    "subtitle": "副标题",
    "slug": "{'-'.join(slugs)}",
    "meta_description": "meta描述（150字符以内，包含关键词）",
    "keywords": ["关键词1", "关键词2", ...],
    "quick_verdict": {{
        "overall_winner": "综合推荐",
        "best_for_beginners": "新手推荐",
        "best_value": "性价比之选",
        "best_for_pro": "专业用户推荐"
    }},
    "content": "完整Markdown正文",
    "faq": [
        {{"question": "问题", "answer": "回答"}}
    ],
    "compared_tools": [{slugs}],
    "compare_category": "{primary_cat}",
    "last_updated": "{datetime.now().strftime('%Y-%m-%d')}"
}}
"""
    return prompt


def generate_alternatives_prompt(tool):
    """为单个工具生成替代方案页面的prompt"""
    slug = tool['slug']
    category = tool.get('category', '通用')
    dimensions = COMPARE_DIMENSIONS.get(category, COMPARE_DIMENSIONS["通用"])
    
    prompt = f"""请写一篇"{tool['name']}"的替代方案推荐文章（2026年最新版）

## 工具信息：
- 名称：{tool['name']}
- 简介：{tool.get('description', 'N/A')}
- 价格：{tool.get('price', 'N/A')}
- 优点：{' | '.join(tool.get('pros', [])) if tool.get('pros') else 'N/A'}
- 缺点：{' | '.join(tool.get('cons', [])) if tool.get('cons') else 'N/A'}

## 要求：
1. 字数2000-2500字
2. 推荐8-12个替代方案（分梯队：最佳替代、免费替代、国产替代、特定场景替代）
3. 每个替代品要说明为什么能替代、优缺点、适合谁
4. 给出选择决策树（什么情况选哪个）

## 文章结构：

### 标题
"{tool['name']}最佳替代品2026：X款免费+付费替代方案推荐"

### 一、为什么要找{tool['name']}替代？
（目标用户的痛点，什么情况下需要替代方案）

### 二、最佳替代方案（TOP 5详细对比）
每个包含：名称、简介、对比{tool['name']}的优劣、价格、适合人群、评分

### 三、免费替代推荐（3-5个）
重点推荐真正好用的免费选项

### 四、国产/中文替代（如果有）
针对国内用户的本土化选择

### 五、如何选择？决策指南
不同需求/预算/场景的具体建议

### 六、FAQ（3-4个）

## 输出格式（严格JSON）：
{{
    "title": "{tool['name']}替代品2026：X款免费+付费替代方案推荐",
    "subtitle": "副标题",
    "slug": "{slug}-alternatives",
    "meta_description": "meta描述（150字符内）",
    "keywords": ["{tool['name']}替代", "{tool['name']}类似工具", "{tool['name']}平替", ...],
    "content": "完整Markdown正文",
    "faq": [{{"question": "...", "answer": "..."}}],
    "target_tool": "{slug}",
    "page_type": "alternatives",
    "last_updated": "{datetime.now().strftime('%Y-%m-%d')}"
}}
"""
    return prompt


def build_compare_slug(slugs):
    """从工具slug列表生成对比页slug"""
    return '-'.join(sorted(slugs))


def get_existing_compares():
    """获取已存在的对比数据"""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("compares", [])
    return []


def save_compare_data(data):
    """保存对比数据到JSON"""
    # 确保目录存在
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    force = '--force' in args
    hot_only = '--hot-only' in args  # 只生成预定义的热门对比，不生成自动发现的
    target_tool = None
    if '--tool' in args:
        idx = args.index('--tool')
        if idx + 1 < len(args):
            target_tool = args[idx + 1]
    
    print("=" * 60)
    print("[Compare Pages] Programmatic Compare Page Generator v1.0")
    print("=" * 60)
    
    # 加载数据
    tools = load_tools()
    published_slugs = set([t['slug'] for t in tools])
    print(f"\n[INFO] 已发布工具: {len(tools)} 个")
    
    existing_compares = get_existing_compares()
    existing_slugs = set([c.get('slug', '') for c in existing_compares])
    state = load_state()
    
    # ── 第一步：确定所有需要生成的对比组合 ─────────────
    compare_queue = []
    
    # 1. 预定义热门组合
    for combo in HOT_COMPARES:
        # 过滤掉工具库中不存在的
        valid_slugs = [s for s in combo if s in published_slugs]
        if len(valid_slugs) >= 2:  # 至少2个工具才能对比
            slug = build_compare_slug(valid_slugs)
            
            # 如果指定了target_tool，只生成相关的
            if target_tool and target_tool not in valid_slugs:
                continue
                
            compare_queue.append({
                'type': 'hot',
                'slugs': sorted(valid_slugs),
                'priority': 'high',
                'slug': slug
            })
    
    # 2. 自动发现同分类工具交叉对比
    tools_by_category = {}
    for t in tools:
        cat = t.get('category', '其他')
        if cat not in tools_by_category:
            tools_by_category[cat] = []
        tools_by_category[cat].append(t['slug'])
    
    auto_compares = []
    for cat, slugs in tools_by_category.items():
        if len(slugs) >= 2:
            # 同分类两两组合（排除已有热门组合的）
            for combo in combinations(sorted(slugs), 2):
                slug = build_compare_slug(list(combo))
                if slug not in existing_slugs and slug not in [c['slug'] for c in compare_queue]:
                    
                    if target_tool and target_tool not in combo:
                        continue
                    
                    auto_compares.append({
                        'type': 'auto',
                        'slugs': list(combo),
                        'priority': 'medium',
                        'slug': slug
                    })
    
    # 取自动发现的（避免太多），同分类最多取前10个组合
    # 按分类均匀分配
    if not hot_only:
        auto_compares = auto_compares[:50]  # 上限50个自动对比
        compare_queue.extend(auto_compares)
    else:
        print("[INFO] --hot-only mode: skipping auto-discovered compares")
    
    # ── 第二步：过滤已生成的 ────────────────────────────
    if not force:
        new_compares = [c for c in compare_queue if c['slug'] not in existing_slugs]
        skipped = len(compare_queue) - len(new_compares)
        print(f"[INFO] 新增对比页: {len(new_compares)} 个 (跳过已有 {skipped} 个)")
    else:
        new_compares = compare_queue
        print(f"[INFO] 强制模式: {len(new_compares)} 个对比页")
    
    # 也收集替代方案页（hot_only时只生成有badge的工具的替代方案）
    alternatives_queue = []
    hot_tool_slugs = set()
    for combo in HOT_COMPARES:
        for s in combo:
            hot_tool_slugs.add(s)
    
    for t in tools:
        alt_slug = f"{t['slug']}-alternatives"
        # hot_only模式下只处理热门工具
        if hot_only and t['slug'] not in hot_tool_slugs:
            continue
        if target_tool and t['slug'] != target_tool:
            continue
        if force or alt_slug not in existing_slugs:
            alternatives_queue.append(t)
    
    print(f"[INFO] 替代方案页: {len(alternatives_queue)} 个")
    
    # ── Dry run 模式 ─────────────────────────────────────
    if dry_run:
        print("\n" + "=" * 60)
        print("[DRY RUN] Preview")
        print("=" * 60)
        print(f"\n对比页 ({len(new_compares)} 个)：")
        for c in new_compares[:20]:
            tools_in = [get_tool_by_slug(tools, s)['name'] for s in c['slugs']]
            print(f"  [{'HOT' if c['priority']=='high' else 'AUTO'}] {' vs '.join(tools_in)} -> /compare/{c['slug']}/")
        if len(new_compares) > 20:
            print(f"  ... 还有 {len(new_compares) - 20} 个")
        
        print(f"\n替代方案页 ({len(alternatives_queue)} 个)：")
        for t in alternatives_queue[:10]:
            print(f"  [ALT] {t['name']} -> /alternatives/{t['slug']}/")
        if len(alternatives_queue) > 10:
            print(f"  ... 还有 {len(alternatives_queue) - 10} 个")
        
        total_new = len(new_compares) + len(alternatives_queue)
        total_estimated_tokens = total_new * 3500  # 每篇预估token
        print(f"\n总计新增: {total_new} 个页面")
        print(f"预估API调用次数: {total_new} 次")
        print(f"预估token消耗: ~{total_estimated_tokens:,}")
        return
    
    # ── 第三步：调用AI生成内容 ──────────────────────────
    print(f"\n{'=' * 60}")
    print(f"[GO] Start generating compare pages ({len(new_compares)} compares + {len(alternatives_queue)} alternatives)")
    print(f"{'=' * 60}\n")
    
    all_compares = list(existing_compares)  # 保留已有的
    generated_count = 0
    failed_count = 0
    
    # 生成对比页
    for i, compare_info in enumerate(new_compares):
        slugs = compare_info['slugs']
        tools_in_compare = [get_tool_by_slug(tools, s) for s in slugs]
        
        # 跳过找不到的工具
        if any(t is None for t in tools_in_compare):
            print(f"  [SKIP] 对比页 {compare_info['slug']}: 工具数据不完整")
            continue
        
        tool_names = " vs ".join([t['name'] for t in tools_in_compare])
        priority_mark = '[HOT]' if compare_info['priority'] == 'high' else '[AUTO]'
        print(f"[{i+1}/{len(new_compares)}] {priority_mark} 生成: {tool_names}")
        
        prompt = generate_compare_prompt(tools_in_compare)
        result = call_ai(prompt, max_tokens=4000)
        
        if result:
            # 解析JSON
            try:
                # 提取JSON（处理可能的markdown代码块包裹）
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    compare_data = json.loads(json_match.group())
                    compare_data['page_type'] = 'compare'
                    compare_data['priority'] = compare_info['priority']
                    compare_data['source'] = compare_info['type']
                    all_compares.append(compare_data)
                    generated_count += 1
                    print(f"       [OK] Success: {compare_data.get('title', 'N/A')[:40]}...")
                else:
                    print(f"       [WARN] Response not JSON")
                    failed_count += 1
            except json.JSONDecodeError as e:
                print(f"       [WARN] JSON parse error (compare): {e}")
        else:
            failed_count += 1
        
        # API限速（每2次调用间隔3秒）
        if (i + 1) % 2 == 0 and i < len(new_compares) - 1:
            print("       [WAIT] Sleeping 3s to avoid rate limit...")
            time.sleep(3)
    
    # 生成替代方案页
    print(f"\n--- 生成替代方案页 ---\n")
    alts_generated = 0
    alts_failed = 0
    all_alternatives = []
    
    # 加载已有的替代方案
    existing_data = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    all_alternatives = existing_data.get('alternatives', [])
    existing_alt_slugs = set([a.get('slug', '') for a in all_alternatives])
    
    for i, tool in enumerate(alternatives_queue):
        alt_slug = f"{tool['slug']}-alternatives"
        print(f"[{i+1}/{len(alternatives_queue)}] [ALT] Generate: {tool['name']} alternatives")
        
        prompt = generate_alternatives_prompt(tool)
        result = call_ai(prompt, max_tokens=4000)
        
        if result:
            try:
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    alt_data = json.loads(json_match.group())
                    all_alternatives.append(alt_data)
                    alts_generated += 1
                    print(f"       [OK] Success: {alt_data.get('title', 'N/A')[:40]}...")
                else:
                    print(f"       [WARN] Cannot parse JSON (alt)")
                    alts_failed += 1
            except json.JSONDecodeError as e:
                    print(f"       [WARN] JSON parse error (alt): {e}")
        else:
            alts_failed += 1
        
        if (i + 1) % 2 == 0 and i < len(alternatives_queue) - 1:
            time.sleep(3)
    
    # ── 第四步：保存结果 ─────────────────────────────────
    output_data = {
        "compares": all_compares,
        "alternatives": all_alternatives,
        "metadata": {
            "total_compares": len(all_compares),
            "total_alternatives": len(all_alternatives),
            "newly_generated": generated_count + alts_generated,
            "last_updated": datetime.now().isoformat(),
            "published_tool_count": len(tools),
        }
    }
    
    save_compare_data(output_data)
    
    # 更新state
    state["generated_counts"] = {
        "compares": len(all_compares),
        "alternatives": len(all_alternatives),
    }
    save_state(state)
    
    # ── 打印摘要 ─────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"[OK] Done! Generation report:")
    print(f"{'=' * 60}")
    print(f"  对比页总数:   {len(all_compares)} (新增 {generated_count})")
    print(f"  替代方案总数: {len(all_alternatives)} (新增 {alts_generated})")
    print(f"  失败/跳过:    {failed_count + alts_failed}")
    print(f"  数据文件:     data/compare_data.json")
    print(f"\n下一步: 运行 python scripts/build.py 构建HTML页面")


if __name__ == '__main__':
    main()
