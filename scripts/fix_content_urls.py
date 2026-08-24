"""
批量修复 tools.json 中 content 字段里引用的虚假网址。
将模板化的 www.工具名.com 替换为真实官网。
"""
import json
import re

# 旧URL -> 新URL 映射（用于content中的替换）
CONTENT_URL_REPLACEMENTS = {
    "www.天工ai.com": "www.tiangong-china.com",
    "www.dall-e-3.com": "openai.com/dall-e-3",
    "www.秒画.com": "miaohua.sensetime.com",
    "www.文心一言.com": "yiyan.baidu.com",
    "www.千问.com": "tongyi.aliyun.com/qianwen",
    "www.腾讯元宝.com": "yuanbao.tencent.com",
    "www.可灵ai.com": "klingai.kuaishou.com",
    "www.copilot-微软.com": "copilot.microsoft.com",
    "www.wps-ai.com": "ai.wps.cn",
    "www.智谱清言.com": "chatglm.cn",
    "www.讯飞星火.com": "xinghuo.xfyun.cn",
    "www.即时设计ai.com": "js.design",
    "www.稿定设计ai.com": "gaoding.com",
    "www.飞书智能助手.com": "feishu.cn",
    "www.arc浏览器.com": "arc.net",
    "www.秘塔ai搜索.com": "metaso.cn",
    "www.纳米ai搜索.com": "n.cn",
    "www.360智脑.com": "ai.360.cn",
    "www.remove.bg.com": "remove.bg",
    "www.figma-ai.com": "figma.com",
    "www.photoroom.com": "photoroom.com",
    "www.gemini.com": "gemini.google.com",
    "www.deepseek.com": "chat.deepseek.com",
    "www.grok.com": "grok.com",
    "www.notebooklm.com": "notebooklm.google.com",
    "www.dall-e-3.com": "openai.com/dall-e-3",
    "www.adobe-firefly.com": "firefly.adobe.com",
    "www.bolt.new.com": "bolt.new",
    "www.windsurf.com": "codeium.com/windsurf",
    "www.grammarly-ai.com": "grammarly.com",
    "www.character-ai.com": "character.ai",
    "www.poe.com": "poe.com",
    "www.minimax.com": "minimaxi.com",
    "www.lovable.com": "lovable.dev",
    "www.v0.dev.com": "v0.dev",
    "www.claude-code.com": "docs.anthropic.com/en/docs/claude-code",
    "www.openai-codex.com": "openai.com/index/introducing-codex",
    "www.n8n.com": "n8n.io",
    "www.coze.com": "coze.com",
    "www.dify.com": "dify.ai",
    "www.zapier-ai.com": "zapier.com",
    "www.veo.com": "deepmind.google/technologies/veo",
    "www.opus-clip.com": "opus.pro",
    "www.synthesia.com": "synthesia.io",
    "www.luma-ai.com": "lumalabs.ai",
    "www.capcut-ai.com": "capcut.com",
    "www.ideogram.com": "ideogram.ai",
    "www.leonardo-ai.com": "leonardo.ai",
    "www.freepik-ai.com": "freepik.com",
    "www.krea-ai.com": "krea.ai",
    "www.flux.com": "blackforestlabs.ai",
    "www.liblibai.com": "liblib.art",
    "www.copy.ai.com": "copy.ai",
    "www.quillbot.com": "quillbot.com",
    "www.writesonic.com": "writesonic.com",
    "www.napkin-ai.com": "napkin.ai",
    "www.otter.ai.com": "otter.ai",
    "www.fireflies.ai.com": "fireflies.ai",
    "www.murf-ai.com": "murf.ai",
    "www.raycast-ai.com": "raycast.com",
    "www.brandmark.com": "brandmark.io",
    "www.supabase-ai.com": "supabase.com",
    "www.recraft.com": "recraft.ai",
    "www.fathom.com": "fathom.video",
    "www.you.com.com": "you.com",
    "www.consensus.com": "consensus.app",
    "www.pixverse.com": "pixverse.ai",
    "www.fliki.com": "fliki.ai",
    "www.tensor.art.com": "tensor.art",
}

def main():
    with open('data/tools.json', 'r', encoding='utf-8') as f:
        tools = json.load(f)

    fix_count = 0
    for tool in tools:
        content = tool.get('content', '')
        if not content:
            continue
        
        new_content = content
        for old_url, new_url in CONTENT_URL_REPLACEMENTS.items():
            # Replace both http and https variants, also with/without www
            new_content = new_content.replace(f"https://{old_url}", f"https://{new_url}")
            new_content = new_content.replace(f"http://{old_url}", f"https://{new_url}")
            # Also replace bare mentions like "访问官网 www.xxx.com"
            new_content = new_content.replace(f"www.{old_url.replace('www.','')}", new_url)
        
        if new_content != content:
            tool['content'] = new_content
            fix_count += 1
            print(f"  [CONTENT FIX] {tool['name']}")

    with open('data/tools.json', 'w', encoding='utf-8') as f:
        json.dump(tools, f, ensure_ascii=False, indent=4)

    print(f"\n共修复 {fix_count} 个工具的content中的虚假URL")

if __name__ == '__main__':
    main()
