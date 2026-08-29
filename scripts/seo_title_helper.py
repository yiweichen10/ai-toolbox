# -*- coding: utf-8 -*-
import re
import hashlib


def _stable_idx(key: str, n: int) -> int:
    """跨进程稳定的轮询下标（2026-08-29 修复，勿改回内置 hash）。

    原实现用 abs(hash(slug)) % n，而 Python 的 str hash 受 PYTHONHASHSEED 随机化影响：
    每个 Python 进程启动 seed 都不同 → 同一 slug 每次构建选中的话术不同 →
    实测约 65 个工具页的 meta description 每次构建随机漂移。
    危害：① 违反 AGENTS.md 硬性规则 4「构建必须稳定可复现」；
    ② 搜索引擎每次抓取拿到不同摘要，页面被认为内容不稳定；
    ③ 这些页每天被判定为变更、白白重传。
    改用 md5 → 跨进程/跨平台/跨版本恒定。
    """
    if n <= 0:
        return 0
    digest = hashlib.md5((key or "").encode("utf-8")).hexdigest()
    return int(digest, 16) % n

"""
意图驱动标题引擎 — 为 AI工具宝箱 工具详情页生成差异化 Title / Meta / long_tail。

设计原则（2026-07-25）：
- Google 为「查询」排名，不为「模板」排名。固定 {name}评测2026 骨架是规模化模板内容特征。
- long_tail 字段是「用户真实会搜的自然话术种子」，由工具属性（分类/价格/竞品）自动推断，零人工。
- 有 long_tail 用真实种子；没有走分类意图桶兜底，保证全站每页标题不同、且都像人写的。
- H1 交给调用方处理（纯品牌名），本模块只管 Title / Meta / long_tail 文本。

关键：每个意图桶内部也必须「多话术轮询」，否则又会退化成另一种单一模板
（初版对比意图占 89%、价格意图占 90% 就是教训）。

slug_info 参数：{slug: tool_dict} 或兼容旧式 {slug: name_str}。
  传 tool_dict 时可做「同分类竞品」约束，避免跨类硬凑对比（如 AI视频 vs Canva AI）。

用法：
    from seo_title_helper import gen_long_tail, build_title, build_meta
"""

# 价格意图话术池（freemium/免费工具占多数，必须多话术分散，否则又成单一模板）
PRICE_TAILS = [
    "免费吗？核心功能与定价一览",
    "免费版够用吗",
    "有免费额度吗？定价详解",
    "免费和付费区别大吗",
]

# 对比意图话术池（同分类强竞品才触发，X 不同时已天然差异化）
COMPARE_TAILS = [
    "vs {rival}：哪个更适合你",
    "和 {rival} 比哪个强",
    "{rival} 平替？实测对比",
]

# 每分类 2-3 个「尾部短语」（不含品牌名、不含年份），按 slug 哈希轮询，保证同分类相邻工具不同。
# 这是默认兜底话术池，价格/对比意图优先于它，但仅当条件命中才覆盖。
CAT_TAILS = {
    "AI编程": ["代码生成实测：好用吗", "值得程序员入手吗", "怎么提升 coding 效率"],
    "AI对话": ["是什么？对话能力实测", "好用吗？和主流模型对比", "新手怎么上手"],
    "AI视频": ["视频生成效果实测", "做短视频体验如何", "出片质量实测"],
    "AI设计": ["设计能力提升实测", "免费版够用吗", "新手设计指南"],
    "AI绘画": ["出图质量实测", "怎么画出好图", "模型对比实测"],
    "AI效率": ["能提升多少效率", "好用吗？真实体验", "日常提效指南"],
    "AI办公": ["办公场景实测", "职场人怎么用", "功能实测对比"],
    "AI音频": ["音频处理实测", "怎么用", "效果对比实测"],
    "AI写作": ["写作效果实测", "新手写作指南", "和竞品比如何"],
    "AI开发": ["开发提效实测", "值得团队用吗", "怎么集成到工作流"],
    "AI行业应用": ["是什么？行业落地实测", "好用吗？真实案例", "怎么用"],
    "AI搜索": ["搜索体验实测", "怎么搜得更准", "和竞品比如何"],
    "AI智能体": ["是什么？智能体实测", "好用吗？搭建体验", "新手怎么搭"],
    "AI自动化": ["自动化能力实测", "怎么用", "流程对比实测"],
    "AI翻译": ["翻译准确度实测", "怎么用", "多语言对比实测"],
}

DEFAULT_TAILS = ["评测：优缺点与真实体验", "好用吗？功能实测", "怎么用？新手指南"]


def gen_long_tail(tool, slug_info=None):
    """根据工具属性推断 long_tail 尾部短语（不含品牌名、不含年份）。

    意图优先级（每个桶内部多话术轮询，避免退化成单一模板）：
      1) 价格：price 含「免费」→ 价格话术池轮询
      2) 对比：related 中存在「同分类」短名竞品（≤8字）→ 对比话术池轮询
      3) 兜底：分类话术池，按 slug 哈希轮询

    slug_info: {slug: tool_dict} 或 {slug: name_str}。为 None 时跳过对比意图。
    """
    slug = tool.get("slug", "")
    cat = tool.get("category", "")
    price = str(tool.get("price", ""))
    related = tool.get("related") or []
    name = tool.get("name", "")

    # 1) 价格意图（多话术轮询）
    if "免费" in price:
        return PRICE_TAILS[_stable_idx(slug, len(PRICE_TAILS))]

    # 2) 对比意图（仅同分类强竞品，避免跨类硬凑；多话术轮询）
    if slug_info:
        for r in related:
            rt = slug_info.get(r)
            if isinstance(rt, dict):
                rn = rt.get("name")
                rcat = rt.get("category")
            else:
                rn = rt
                rcat = cat  # 旧式 name map 兼容，不约束同分类
            if rn and 2 <= len(rn) <= 8 and rn != name and rcat == cat:
                tpl = COMPARE_TAILS[_stable_idx(slug + r, len(COMPARE_TAILS))]
                return tpl.format(rival=rn)

    # 3) 分类话术兜底
    pool = CAT_TAILS.get(cat, DEFAULT_TAILS)
    return pool[_stable_idx(slug, len(pool))]


_TIME_NOISE = re.compile(
    r"\d{4}年|GPT-[\d.]+|V\d+(\.\d+)?|Gen-[\d.]+|Sonnet\s*\d+|"
    r"Fable\s*\d+|Opus\s*\d+|版本\s*\d+|Claude\s*(?:Sonnet|Fable|Opus)\s*\d+",
    re.I,
)
_PREFIX_CLEAN = re.compile(r"^(是一款|是一个|是|推出的|旗下)")


def gen_positioning(tool):
    """从工具自身 description 提炼一句话功能定位，作为标题种子。
    不依赖百度原词，从根上杜绝跨实体噪声（车/档次/4:3/缓存）。"""
    # 尊重显式定位覆盖（按工具指定干净标题尾，避免通用引擎对
    # 「品牌名（英文副标）——功能定位」长句在词中间硬截断失真）
    explicit = (tool.get("positioning") or "").strip()
    if explicit:
        return _quality_fix(explicit[:30].strip(" ，,。:："), tool.get("name") or "", tool.get("category") or "", min_len=4)
    desc = (tool.get("description") or "").strip()
    cat = (tool.get("category") or "").strip()
    name = (tool.get("name") or "").strip()
    # 取第一句（到句号/感叹/问号/换行）
    seg = re.split(r"[。！？!?\n]", desc)
    raw = seg[0].strip() if seg and seg[0].strip() else desc
    # 剔除年份/版本号噪声（GPT-5.6 / V7 / Gen-4 / Sonnet 5 ...）
    raw = _TIME_NOISE.sub("", raw).strip(" ，,。.：:")
    # 去除括号及内部内容（如 "（后独立为 Amp Inc）"）
    raw = re.sub(r"[（(][^）)]*[）)]", "", raw).strip(" ，,。.：:")
    # 去掉开头的品牌名重复（如 "AIVA是一款..." → "是一款..."）
    if name and raw.startswith(name):
        raw = raw[len(name):].strip(" ，,。:：是一款是一个是")
    # 去掉冗余前缀
    raw = _PREFIX_CLEAN.sub("", raw).strip(" ，,。:：")
    # 破折号 —— 处理：应对「品牌名（副标）——功能定位」结构，
    # 拼接为「品牌 定位」而非在词中间硬截断（修复「——AI」断词失真）
    if "——" in raw:
        parts = raw.split("——")
        before = parts[0].strip()
        after = "——".join(parts[1:]).strip()
        # 去掉 before 里与标题头重复的 name（如 CodeBuddy），避免品牌名重复
        if name and name in before:
            before = before.replace(name, "").strip(" ，,。:： ")
        before = before.strip(" ，,。:： ")
        after = after.strip(" ，,。:： ")
        if before and after:
            raw = (before + " " + after).strip()
        else:
            raw = (before or after).strip()
        raw = re.sub(r"\s+", " ", raw)
    # 优先在分隔符（中/英文逗号、顿号）处取精炼定位，避免截断在词中间
    cuts = [m.start() for m in re.finditer(r"[，、,]", raw)]
    pos = None
    for c in cuts:
        if c >= 4:
            pos = c
            break
    if pos is None and cuts:
        pos = cuts[0] if cuts[0] >= 2 else None
    comma_cut = None  # 逗号/顿号截断结果；≤30字时作为最终定位（语义完整，不再二次硬截）
    if pos is not None:
        cand = raw[:pos].strip(" ，,。:：的")
        if len(cand) >= 4:
            raw = cand
            comma_cut = cand
    # 逗号/句号是语义边界：截断结果 ≤30 字直接采用，不做二次硬截断
    # （避免「自主智能体“AI 员工”」这类 22~30 字的完整关键词组合被二次截掉）
    if comma_cut is None or len(comma_cut) > 30:
        # 仍过长：依次在空格（英文词边界）、「的」（中文定语边界）、硬截断 22 字收尾
        if len(raw) > 22:
            sp = raw.rfind(" ")
            if 4 < sp <= 22:
                raw = raw[:sp].rstrip(" ，,。:：的")
            else:
                de = raw.rfind("的")
                if 8 < de <= 22:
                    raw = raw[:de].rstrip(" ，,。:：")
                else:
                    raw = raw[:22].rstrip(" ，,。:：的")
    # 清理标题中的引号类符号（" " 「 」 『 』 等直接删除，不换成其他符号）：
    # title 已含 name + 功能定位，符号占位过多；引号内的关键词保留文字本身
    raw = _strip_quotes(raw)
    # ===== 2026-08-06 标题质量修复（全站四类问题，响应工具页标题扫描）=====
    raw = _quality_fix(raw, name, cat, min_len=6)
    if not raw or len(raw) < 4:
        raw = f"{cat}工具" if cat else "AI工具"
    return raw


def _quality_fix(raw, name, cat, min_len=6):
    """标题尾质量兜底：品牌重复 / 坏结尾 / 过短 / 过长。自动与手填 positioning 共用。"""
    if not raw:
        return raw
    # 1) 品牌名重复：tail 中出现 name 完整词时移除（如 "AI 图表生成工具 Napkin AI" → "AI 图表生成工具"）。
    #    仅处理 len>=4 的 name，且要求词边界，避免 "Vida" 误伤 "VidAI"、"Mem" 误伤 "Memory"。
    if name and len(name) >= 4:
        _brand_pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", re.I)
        if _brand_pat.search(raw):
            raw = _brand_pat.sub("", raw)
            raw = re.sub(r"\s+", " ", raw).strip(" ，,。:：")
            # 品牌在句首被移除后可能出现 "是一款/是一个" 残留前缀
            raw = _PREFIX_CLEAN.sub("", raw).strip(" ，,。:：")
    # 2) 尾部连接词/助词残留（"Gemini Deep Research 是"、"XX 的"）
    raw = re.sub(r"(\u7684|\u548c|\u4e0e|\u53ca|\u5e76|\u4ee5\u53ca|\u662f|\u4e3a|\u5728|\u5bf9)$", "", raw)
    raw = raw.strip(" ，,。:：")
    # 3) 过短 → 分类话术兜底（"本地优先"/"用于构建"/"AI平台" 等残废 tail）
    if len(raw) < min_len:
        pool = CAT_TAILS.get(cat, DEFAULT_TAILS)
        raw = pool[_stable_idx(name or "tool", len(pool))]
    # 4) 过长 → 在 12~26 字区间找语义断点（空格/的），否则硬截 24
    if len(raw) > 26:
        head = raw[:26]
        sp = head.rfind(" ")
        if 12 <= sp <= 26:
            raw = head[:sp]
        else:
            de = head.rfind("\u7684")
            if 12 <= de <= 26:
                raw = head[:de]
            else:
                raw = head[:24]
        raw = raw.strip(" ，,。:：")
    return raw


def _strip_quotes(raw):
    """删除标题中的成对中文引号/书名号符号，仅保留文字。
    例：'自主智能体“AI 员工”' → '自主智能体AI 员工'；'“第二大脑”' → '第二大脑'。"""
    cleaned = re.sub(r'[“”"「」『』『』]', '', raw)
    # 清理删除引号后可能出现的多余空格/重复空格
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip(" ，,。:：")


def build_title(name, tail, year=None):
    """功能定位流标题：{name} - {功能定位} | AI工具宝箱。year 已弃用（去模板化）。"""
    return f"{name} - {tail} | AI工具宝箱"


def build_meta(name, tail, description, year=None, tool=None):
    """拼 Meta description：品牌 + 功能定位 + 工具简介。

    2026-08-06 增强（响应 Bing Webmaster「Meta 描述过短」警告）：
    - 不再硬截 80 字，让完整简介自然流出（上限 160 字，避免 SERP 截断）；
    - 简介过短（<60字）时，从工具正文首段提取真实文字补充；
    - 仍不足 100 字时，追加价格/平台等真实字段（不编造内容）。
    """
    desc = (description or "").strip()
    text = desc
    # 简介过短 → 用正文首段真实内容补充（跳过 "## XX 是什么？" 标题与 markdown 符号）
    if len(text) < 60 and tool:
        para = _first_content_para(tool)
        if para:
            _tok = lambda s: set(re.findall(r'[\u4e00-\u9fff]{2}', s))
            _dset, _pset = _tok(text), _tok(para)
            _dup = bool(_dset) and len(_dset & _pset) / len(_dset) >= 0.7
            if _dup:
                text = para  # 简介内容已在正文首段，直接用正文避免重复
            elif text:
                sep = "" if text.endswith(("。", "！", "？")) else "。"
                text = (text + sep + para)[:150]
            else:
                text = para
    meta = f"{name} - {tail}：{text}"
    # 仍偏短 → 追加真实字段（价格/平台）
    if len(meta) < 100 and tool:
        extras = []
        price = (tool.get("price") or "").strip()
        platform = (tool.get("platform") or "").strip()
        if price:
            extras.append(f"价格：{price}")
        if platform:
            extras.append(f"支持平台：{platform}")
        if extras:
            _sep = "" if meta.endswith(("。", "！", "？")) else "。"
            meta += _sep + "，".join(extras)
    # 2026-08-13（阶段2.3）：Bing 阈值约 110 字符，仍偏短时追加分类场景真实信息补足
    if len(meta) < 115 and tool:
        _cat = (tool.get("category") or "").strip()
        if _cat:
            _variants = [
                f"覆盖{_cat}场景的核心功能、定价与真实使用体验，帮你快速判断是否值得入手。",
                f"含{_cat}场景功能亮点、价格与上手难度，助你一眼看清适合谁。",
                f"聚焦{_cat}场景，功能、价格、优缺点一次讲清，附实测结论。",
            ]
            _extra = _variants[_stable_idx(tool.get("slug", ""), len(_variants))]
            _sep = "" if meta.endswith(("。", "！", "？")) else "。"
            meta += _sep + _extra
    return meta[:160]


_MD_STRIP_RE = re.compile(r"<[^>]+>")


def _first_content_para(tool):
    """从工具正文取第一段真实文字（跳过 ## 标题与 markdown 符号），供 Meta 兜底。"""
    content = tool.get("content") or ""
    if not content:
        return ""
    plain = _MD_STRIP_RE.sub("", content)
    plain = re.sub(r"^#{1,6}[^\n]*$", "", plain, flags=re.M)  # 去掉 markdown 标题行
    plain = re.sub(r"[*_`>|-]", "", plain)
    plain = re.sub(r"\s+", "", plain).strip("：:。.，,；;")
    if not plain:
        return ""
    # 优先取第一句（句号/感叹/问号结尾），限制在 30~150 字
    for sep in ("。", "！", "？", "!"):
        idx = plain.find(sep)
        if 4 < idx <= 150:
            return plain[: idx + 1]
    return plain[:150]
    return meta
