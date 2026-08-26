import json, os

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'scripts'))
from data_store import save_tools_batch, save_articles_batch

tools = load_all_tools()
by = {t['slug']: t for t in tools}

# (slug, field, old, new)
TEXT = [
    # --- URL 硬伤 ---
    ('microsoft-agent-framework', 'url', 'https://cloud.microsoft.com/agent-framework', 'https://learn.microsoft.com/agent-framework'),
    ('google-adk', 'url', 'https://cloud.google.com/adk', 'https://adk.dev'),

    # --- hermes-agent 数字 ---
    ('hermes-agent', 'content', '六种执行后端', '七种执行后端'),
    ('hermes-agent', 'description', '六种执行后端', '七种执行后端'),
    ('hermes-agent', 'features', '六种执行后端', '七种执行后端'),
    ('hermes-agent', 'content', '200+ 大模型', '300+ 模型'),
    ('hermes-agent', 'description', '200+ 大模型和 40+ 工具', '300+ 模型和 40+ 工具'),

    # --- google-genkit Python(Beta)->Preview ---
    ('google-genkit', 'description', 'Python（Beta）', 'Python（Preview）'),
    ('google-genkit', 'features', 'Python（Beta）', 'Python（Preview）'),
    ('google-genkit', 'content', 'Python（Beta）', 'Python（Preview）'),
    ('google-genkit', 'faq', 'Python（Beta）', 'Python（Preview）'),

    # --- pydantic-ai Gateway 命名 ---
    ('pydantic-ai', 'description', 'Pydantic AI Gateway', 'Logfire AI Gateway'),
    ('pydantic-ai', 'features', 'Pydantic AI Gateway', 'Logfire AI Gateway'),
    ('pydantic-ai', 'content', 'Pydantic AI Gateway', 'Logfire AI Gateway'),

    # --- tencentdb 开源日期 ---
    ('tencentdb-agent-memory', 'description', '2026 年 5 月正式开源', '2026 年 7 月（2.0.0 beta）首次公开开源'),
    ('tencentdb-agent-memory', 'content', '2026 年 5 月正式开源', '2026 年 7 月（2.0.0 beta）首次公开开源'),
    ('tencentdb-agent-memory', 'features', 'Codex、DeepSeek Harness', 'Codex、DeepSeek Harness（规划/即将支持）'),
    ('tencentdb-agent-memory', 'content', 'Codex、DeepSeek Harness', 'Codex、DeepSeek Harness（规划/即将支持）'),

    # --- skrun 10->12 命令 ---
    ('skrun', 'features', '10 条 CLI 命令', '约 12 个 CLI 命令'),
    ('skrun', 'content', '10 条 CLI 命令', '约 12 个 CLI 命令'),

    # --- chatgpt-voice 官方命名 ---
    ('chatgpt-voice', 'price', 'ChatGPT-Live', 'GPT-Live'),
    ('chatgpt-voice', 'positioning', 'ChatGPT-Live', 'GPT-Live'),
    ('chatgpt-voice', 'description', 'ChatGPT-Live', 'GPT-Live'),
    ('chatgpt-voice', 'content', 'ChatGPT-Live', 'GPT-Live'),

    # --- voice-pro 转录/限制 ---
    ('voice-pro', 'features', 'Faster-Whisper/WhisperX', 'Faster-Whisper / Whisper-Timestamped'),
    ('voice-pro', 'price', '（WebUI 有 30 分钟试用限制；官方完整版需购买）',
     '（开源后完全免费、无时长限制；官方 ABUS 商业完整版需购买）'),

    # --- slackbot 30项功能日期 ---
    ('slackbot-ai', 'content', '并宣布 30 项 AI 新功能',
     '（注：这 30 项 AI 新功能实际于 2026 年 3 月 31 日发布，8 月为通过 MCP 接入 Salesforce 平台的滚动更新）并宣布 30 项 AI 新功能'),
    ('slackbot-ai', 'description', '并宣布 30 项 AI 新功能',
     '（注：这 30 项 AI 新功能实际于 2026 年 3 月 31 日发布，8 月为通过 MCP 接入 Salesforce 平台的滚动更新）并宣布 30 项 AI 新功能'),

    # --- NEEDS_REVIEW 软化 ---
    ('soloop', 'description', '前百度产品经理', '前大厂产品经理'),
    ('soloop', 'content', '前百度产品经理', '前大厂产品经理'),
    ('hey-noah', 'pros', '约 17,000 次会议邀请', '大量会议邀请'),
    ('hey-noah', 'content', '约 17,000 次会议邀请', '大量会议邀请'),
    ('atlaso', 'positioning', 'Product Hunt 当日 #3', 'Product Hunt 当日 #3（最终名次在 #3–#4 间波动）'),
    ('atlaso', 'content', 'Product Hunt 当日 #3', 'Product Hunt 当日 #3（最终名次在 #3–#4 间波动）'),
]

# source_urls 特殊处理
SRC_FIX = {
    'github-copilot-sdk': ('copilot-sdk-is-now-generally-available',
                           'https://github.blog/changelog/2026-06-02-copilot-sdk-now-generally-available/'),
    'airtop-ads': ('airtop-auth-2',
                   'https://www.producthunt.com/products/airtop/launches/airtop-for-google-ads-automation'),
}

STR_FIELDS = {'content', 'description', 'positioning', 'price', 'visits', 'url'}
LIST_STR = {'features', 'pros', 'cons', 'tags', 'related', 'seo_keywords', 'source_urls'}


def apply_field(e, field, old, new):
    """对单字段做替换，返回是否命中。"""
    if field in STR_FIELDS:
        v = e.get(field, '')
        if old in v:
            e[field] = v.replace(old, new)
            return True
        return False
    if field in LIST_STR:
        hit = False
        nv = []
        for x in e.get(field, []):
            if old in x:
                nv.append(x.replace(old, new)); hit = True
            else:
                nv.append(x)
        if hit:
            e[field] = nv
        return hit
    if field == 'faq':
        hit = False
        for it in e.get('faq', []):
            for k in ('question', 'answer'):
                if old in it.get(k, ''):
                    it[k] = it[k].replace(old, new); hit = True
        return hit
    return False


miss = []
for slug, field, old, new in TEXT:
    e = by.get(slug)
    if not e:
        miss.append(f'[NO_ENTRY] {slug}'); continue
    if not apply_field(e, field, old, new):
        miss.append(f'[MISS] {slug} / {field} / old="{old}"')

# source_urls
for slug, (bad_sub, good) in SRC_FIX.items():
    e = by.get(slug)
    if not e:
        miss.append(f'[NO_ENTRY] {slug}'); continue
    urls = e.get('source_urls', [])
    new_urls = []
    hit = False
    for u in urls:
        if bad_sub in u:
            new_urls.append(good); hit = True
        else:
            new_urls.append(u)
    if hit:
        e['source_urls'] = new_urls
    else:
        miss.append(f'[SRC_MISS] {slug} / bad_sub="{bad_sub}"')

save_tools_batch(tools)
print('FIX APPLIED. tools.json written.')
print(f'MISS count = {len(miss)}')
for m in miss:
    print('  ', m)
