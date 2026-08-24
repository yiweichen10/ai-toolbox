"""
全量修正 tools.json 中所有工具的URL为真实官网地址。
必须基于真实产品官网，不能猜测。
"""
import json

URL_FIXES = {
    # === 已验证的真实官网URL ===
    "ChatGPT": "https://chat.openai.com",
    "Claude": "https://claude.ai",
    "Midjourney": "https://www.midjourney.com",
    "GitHub Copilot": "https://github.com/features/copilot",
    "Cursor": "https://cursor.com",
    "Kimi": "https://kimi.moonshot.cn",
    "豆包": "https://www.doubao.com",
    "Notion AI": "https://www.notion.so",
    "Runway": "https://runwayml.com",
    "Stable Diffusion": "https://stability.ai",
    "Suno": "https://suno.com",
    "Canva AI": "https://www.canva.com",
    "Sora": "https://openai.com/sora",
    "Perplexity": "https://www.perplexity.ai",
    "Pika": "https://pika.art",
    "Udio": "https://www.udio.com",
    "Replit AI": "https://replit.com",
    "Jasper": "https://www.jasper.ai",
    "Gamma": "https://gamma.app",
    "ElevenLabs": "https://elevenlabs.io",
    "Gemini": "https://gemini.google.com",
    "DeepSeek": "https://chat.deepseek.com",
    "文心一言": "https://yiyan.baidu.com",
    "千问": "https://tongyi.aliyun.com/qianwen",
    "腾讯元宝": "https://yuanbao.tencent.com",
    "Grok": "https://grok.com",
    "NotebookLM": "https://notebooklm.google.com",
    "HeyGen": "https://www.heygen.com",
    "DeepL": "https://www.deepl.com",
    "DALL-E 3": "https://openai.com/dall-e-3",
    "Adobe Firefly": "https://firefly.adobe.com",
    "可灵AI": "https://klingai.kuaishou.com",
    "Bolt.new": "https://bolt.new",
    "Windsurf": "https://codeium.com/windsurf",
    "Grammarly AI": "https://www.grammarly.com",
    "Copilot（微软）": "https://copilot.microsoft.com",
    "WPS AI": "https://ai.wps.cn",
    "Character AI": "https://character.ai",
    "智谱清言": "https://chatglm.cn",
    "讯飞星火": "https://xinghuo.xfyun.cn",
    "Poe": "https://poe.com",
    "天工AI": "https://www.tiangong-china.com",
    "MiniMax": "https://www.minimaxi.com",
    "Lovable": "https://lovable.dev",
    "v0.dev": "https://v0.dev",
    "Claude Code": "https://docs.anthropic.com/en/docs/claude-code",
    "OpenAI Codex": "https://openai.com/index/introducing-codex",
    "n8n": "https://n8n.io",
    "Coze": "https://www.coze.com",
    "Dify": "https://dify.ai",
    "Zapier AI": "https://zapier.com",
    "Veo": "https://deepmind.google/technologies/veo",
    "Opus Clip": "https://www.opus.pro",
    "Descript": "https://www.descript.com",
    "Synthesia": "https://www.synthesia.io",
    "Luma AI": "https://lumalabs.ai",
    "CapCut AI": "https://www.capcut.com",
    "Ideogram": "https://ideogram.ai",
    "Leonardo AI": "https://leonardo.ai",
    "Freepik AI": "https://www.freepik.com",
    "Krea AI": "https://www.krea.ai",
    "Flux": "https://blackforestlabs.ai",
    "秒画": "https://miaohua.sensetime.com",
    "LiblibAI": "https://www.liblib.art",
    "Copy.ai": "https://www.copy.ai",
    "QuillBot": "https://quillbot.com",
    "Writesonic": "https://writesonic.com",
    "Remove.bg": "https://www.remove.bg",
    "Photoroom": "https://www.photoroom.com",
    "Figma AI": "https://www.figma.com",
    "即时设计AI": "https://js.design",
    "稿定设计AI": "https://www.gaoding.com",
    "Napkin AI": "https://www.napkin.ai",
    "Otter.ai": "https://otter.ai",
    "飞书智能助手": "https://www.feishu.cn",
    "Beautiful.ai": "https://www.beautiful.ai",
    "Tome": "https://tome.app",
    "Fireflies.ai": "https://fireflies.ai",
    "Speechify": "https://speechify.com",
    "Krisp": "https://krisp.ai",
    "Murf AI": "https://murf.ai",
    "Cleanvoice": "https://cleanvoice.ai",
    "Arc浏览器": "https://arc.net",
    "Comet": "https://www.comet.com",
    "秘塔AI搜索": "https://metaso.cn",
    "纳米AI搜索": "https://n.cn",
    "Phind": "https://phindai.org",
    "You.com": "https://you.com",
    "Consensus": "https://consensus.app",
    "Looka": "https://looka.com",
    "Pixverse": "https://pixverse.ai",
    "Fliki": "https://fliki.ai",
    "Tensor.Art": "https://tensor.art",
    "360智脑": "https://ai.360.cn",
    "Raycast AI": "https://www.raycast.com",
    "Brandmark": "https://brandmark.io",
    "Make": "https://www.make.com",
    "Supabase AI": "https://supabase.com",
    "Recraft": "https://www.recraft.ai",
    "Fathom": "https://fathom.video",
}

def main():
    with open('data/tools.json', 'r', encoding='utf-8') as f:
        tools = json.load(f)

    fixed_count = 0
    not_found = []

    for tool in tools:
        name = tool['name']
        if name in URL_FIXES:
            old_url = tool.get('url', '')
            new_url = URL_FIXES[name]
            if old_url != new_url:
                tool['url'] = new_url
                fixed_count += 1
                print(f"  [FIX] {name}: {old_url} → {new_url}")
        else:
            not_found.append(name)

    with open('data/tools.json', 'w', encoding='utf-8') as f:
        json.dump(tools, f, ensure_ascii=False, indent=4)

    print(f"\n共修正 {fixed_count} 个URL")
    if not_found:
        print(f"未匹配的工具: {', '.join(not_found)}")

if __name__ == '__main__':
    main()
