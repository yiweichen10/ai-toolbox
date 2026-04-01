import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('data/tools.json', encoding='utf-8') as f:
    tools = json.load(f)

# 每个工具要加的 (问题, 答案) - 用 ASCII-safe 的写法
FAQS_TO_ADD = {
    "chatgpt": [
        ("如何注册ChatGPT账号？",
         "注册流程其实不复杂：1）访问 openai.com 点击 Sign up；2）用Gmail邮箱注册，国内手机号可以收验证码；3）注册完成后建议顺手充值，5美元起步，不充值只能用GPT-3.5，代码能力差很多。充值需要支持美元的信用卡，Depay虚拟卡教程在淘宝一搜就有。"),
        ("如何获取ChatGPT API Key？",
         "获取API Key只需三步：1）登录 openai.com；2）点击右上角账号 - API；3）创建一个新密钥（Create new secret key）。拿到Key后就可以在各种工具和脚本里接入了。注意：这个Key只有第一次显示时会完整看到，记得保存。"),
        ("如何用ChatGPT写代码？",
         "最有效的方式是分步提问：先把你的需求描述清楚，然后把代码报错信息完整贴出来，让它一步步解决。比如：输入'我想写一个Python脚本实现批量重命名文件，但os.rename报错了'，把报错信息一起扔给它，它会给可运行的代码和解释。"),
    ],
    "claude": [
        ("如何注册Claude账号？",
         "访问 anthropic.com/claude，点击 Sign up。用Gmail或苹果账号注册最方便，国内手机号可以接收验证码。注册后有免费额度，约50条消息每月。额度用完想继续使用，需要订阅Claude Pro（20美元每月）。"),
        ("Claude的Artifacts怎么用？",
         "Artifacts是Claude的代码预览功能。当你让Claude生成代码（HTML/CSS/JS/Python等）时，它会在回复下方自动显示一个预览窗口，你可以直接看到代码效果。点击'Copy code'可以直接复制。"),
        ("如何用Claude分析文档？",
         "直接在对话框里上传文件（支持PDF、TXT、CSV等），然后说'帮我分析这个文档'，或者问具体问题如'这篇论文的主要结论是什么'。Claude会阅读完整内容后回答，还可以针对特定段落追问细节。"),
    ],
    "midjourney": [
        ("如何注册Midjourney？",
         "Midjourney不需要独立注册，直接在Discord里使用：1）注册Discord账号；2）加入Midjourney官方Discord服务器；3）进入#newbies频道开始使用。国内用户需要稳定的梯子才能正常访问Discord。"),
        ("如何生成第一张Midjourney图片？",
         "在频道输入框输入 /imagine，然后描述你想生成的内容，比如'A cute cat playing piano, cartoon style'。回车发送，等待约30秒到1分钟，AI会生成4张候选图片。收到结果后可以用U1-U4放大某张图，或V1-V4生成变体。"),
        ("Midjourney会员怎么充值？",
         "Midjourney基础会员10美元每月，可生成约200张图。充值方式：在Discord频道输入 /subscribe 会生成一个订阅链接，用支持美元的信用卡购买。如果没有国际支付条件，淘宝有代充服务，但建议找可信店铺。"),
    ],
    "cursor": [
        ("Cursor免费吗？",
         "Cursor有免费额度，每月50次高级模型（GPT-4、Claude）对话，200次普通模式。对于个人开发来说基本够用。付费计划从20美元每月起步，包含无限高级对话和更多功能。"),
        ("如何用Cursor写第一个项目？",
         "打开Cursor后，点击左上角'New Project'，输入项目名称和描述。Cursor会自动生成基础代码结构，然后你可以在代码编辑器里继续对话，比如'帮我添加用户登录功能'。它支持整个项目的上下文理解，改代码后继续对话它知道你在做什么。"),
        ("Cursor支持哪些编程语言？",
         "主流语言基本都支持，包括Python、JavaScript、TypeScript、Go、Rust、Java、C++等。Python支持最好，代码补全和对话质量最高。前端语言（HTML/CSS/React）支持也很不错。"),
    ],
    "kimi": [
        ("如何开始使用Kimi？",
         "直接访问 moonshot.cn 或下载月之暗面公司的App，用手机号注册即可使用，全程免费。Kimi支持最长20万字的上下文输入，可以一次性扔一整本书给它分析。"),
        ("Kimi能读PDF和Word文档吗？",
         "能。直接在对话框里上传PDF、Word、Excel等文件，然后问相关问题，比如'帮我总结这篇文档的核心观点'。Kimi会读取完整内容后回答，还支持针对特定章节追问。"),
        ("如何用Kimi做内容创作？",
         "最有效的方式是给它一个具体框架，告诉它你的目标受众、风格偏好、内容长度要求。Kimi生成的内容可以直接复制使用，省去排版时间。也可以让它先出大纲，确认后再展开写。"),
    ],
    "github-copilot": [
        ("GitHub Copilot有免费版吗？",
         "学生可以免费申请教育版（用学校邮箱验证），含全部功能。个人用户首月免费，之后14美元每月。不付费也能用基础补全，但体验差很多。教育优惠申请地址：education.github.com。"),
        ("如何在VS Code里启用GitHub Copilot？",
         "1）安装VS Code；2）安装GitHub Copilot扩展；3）登录GitHub账号授权；4）开始编码时，Copilot会自动给出代码补全建议，按Tab键采纳，按Esc拒绝。支持Python、JavaScript、TypeScript、Go、Java等主流语言。"),
    ],
    "suno": [
        ("Suno免费吗？",
         "Suno有免费额度，每天登录送50 credits，能生成约10首歌。付费从10美元每月起步，unlimited generation。免费版生成的音乐有轻微水印，付费版无水印且可商用。"),
        ("如何用Suno生成一首完整的歌？",
         "最简单方式：在输入框里写歌词（也可以不写，让AI随机生成），选择音乐风格（pop/rock/rap等），点击Create。约30秒后生成两首完整歌曲（含旋律、人声、伴奏）。"),
        ("Suno生成的音乐可以商用吗？",
         "付费用户生成的音乐可商用，用于YouTube视频、BGM、游戏等都没问题。免费用户生成的音乐仅供个人研究使用，不能用于商业场景。具体条款在Suno官网的使用协议里有详细说明。"),
    ],
    "stable-diffusion": [
        ("Stable Diffusion免费吗？需要什么配置？",
         "Stable Diffusion完全免费，是开源项目。本地部署需要一台有NVIDIA显卡的电脑，显存至少6GB（推荐8GB以上）。没有合适显卡可以用Hugging Face等在线平台。配置不够强行跑会很慢，一张图可能需要几分钟甚至更久。"),
        ("如何用Stable Diffusion生成高质量图片？",
         "关键词是核心。基础公式：主体描述 + 风格 + 光线 + 画质。比如：'1girl, long hair, sunset beach, cinematic lighting, highly detailed, 8k'。另外要学会用Negative prompt（反向关键词）排除不想要的内容，比如：'low quality, blurry, distorted face'。"),
    ],
    "runway": [
        ("Runway怎么用？",
         "访问 runwayml.com 注册账号，Google账号可以直接登录。登录后进入Gen-2或Gen-3模块，输入文字描述（Text to Video）或上传图片（Image to Video），点击Generate生成视频。每个账号有125 credits免费额度，用完需要付费。"),
        ("Runway免费额度用完怎么办？",
         "免费额度用完后需要订阅付费计划，Standard月费15美元，含585 credits，适合偶尔用用的用户。Pro月租35美元，2250 credits。如果只是偶尔尝鲜，等每月额度重置即可。"),
    ],
    "sora": [
        ("Sora怎么申请使用？",
         "Sora目前还在内测阶段，需要在 openai.com/sora 申请候补名单。申请通过后会自动收到邮件通知。付费ChatGPT Plus用户（20美元每月）目前尚不确定是否有Sora优先访问权限，具体以官方公告为准。"),
        ("Sora生成的视频最长多久？",
         "目前Sora生成的视频最长支持20秒。输入文字描述场景，Sora会生成连贯的视频片段，支持复杂场景、多角色互动和物理效果模拟。实际可用时长取决于提示词的复杂程度。"),
    ],
    "perplexity": [
        ("Perplexity和普通搜索引擎有什么区别？",
         "普通搜索引擎返回一堆网页让你自己消化，Perplexity直接给你整理好的答案，并标注每个信息的来源。你可以追问、可以深挖，比传统搜索效率高很多倍。特别适合做研究、快速了解一个新话题。"),
        ("Perplexity免费版够用吗？",
         "免费版每天有5次Pro搜索（用GPT-4和Claude），普通搜索无限用。对大多数人来说够用了。付费版Pro每天300次Pro搜索，15美元每月，适合需要高频做调研的用户。"),
    ],
    "deepseek": [
        ("DeepSeek免费吗？",
         "DeepSeek基础版完全免费，网页和App都能用。付费是针对API调用，按token计费，价格比OpenAI便宜很多。开发者可以在DeepSeek开放平台申请API Key，用于在自己的应用里接入DeepSeek模型。"),
        ("DeepSeek和ChatGPT哪个强？",
         "在编程和数学推理任务上，DeepSeek V3和GPT-4o水平相当，部分测试甚至更好。中文对话表现也很扎实。差距主要在多模态（图片理解）和Agent生态，ChatGPT的工具调用更成熟。日常使用选DeepSeek够用了。"),
        ("DeepSeek能本地部署吗？",
         "能。DeepSeek是开源模型，可以通过Ollama或vLLM本地部署。DeepSeek-Coder系列特别适合编程任务，在很多编程benchmark上表现优秀。本地部署后完全离线可用，不产生任何API费用。"),
    ],
    "gemini": [
        ("Gemini免费吗？",
         "Gemini基础版免费使用，通过 Google AI Studio 或 Gemini App 访问。API调用有免费额度（每天100次），超出后按量收费。Gemini Advanced需要订阅Google One AI Premium计划，约为20美元每月。"),
        ("Gemini能访问Google搜索吗？",
         "Gemini Advanced版本可以实时搜索网页，基础版在部分场景下也集成了搜索能力。和其他大模型相比，Gemini的实时信息获取是优势之一，生成内容时可以引用最新信息。"),
    ],
    "adobe-firefly": [
        ("Adobe Firefly能商用吗？",
         "Adobe Firefly生成的图片可以商用。Adobe明确表示，使用Firefly生成的内容版权归属用户，不存在训练数据的版权争议。相比之下，Midjourney等工具的商用条款在部分地区仍有争议，Firefly在版权方面更安全。"),
        ("如何用Firefly生成图片？",
         "访问 firefly.adobe.com 或在Photoshop里直接使用。输入文字描述，选择风格模板，点击Generate。Firefly的优势是深度集成Adobe生态，生成后可以直接在Photoshop里继续编辑，非常适合设计师工作流。"),
    ],
    "canva-ai": [
        ("Canva AI免费吗？",
         "Canva有免费版，基础设计功能都能用。AI功能（如Magic Write文本生成、Magic Design智能排版）在免费版有少量额度。Canva Pro（13美元每月）AI功能更完整，无限使用，适合内容创作者和企业。"),
        ("如何用Canva AI做海报？",
         "最简单的方式：告诉Canva AI'帮我设计一张XX活动的海报'，输入主题和风格，它会自动生成多个设计方案供选择。你也可以先选模板，再用AI功能改文案或图片，比从头设计快很多。"),
    ],
    "notion-ai": [
        ("Notion AI需要额外付费吗？",
         "Notion AI需要单独订阅，10美元每月，可加到任意Notion计划上。单独的Notion免费版用户也能试用几次，之后需要订阅。不需要买最贵的Enterprise计划，Plus计划加AI就够了。"),
        ("Notion AI能做什么？",
         "Notion AI最实用的场景：1）帮你写文章草稿或续写；2）总结长文档要点；3）翻译内容；4）优化文字语气（更正式/更简洁）；5）头脑风暴出点子。在工作流里嵌入Notion AI后，很多文字类工作可以直接AI代劳。"),
    ],
    "gamma": [
        ("Gamma能自动生成PPT吗？",
         "能，而且体验非常好。Gamma是专门做AI生成PPT的工具，输入主题描述或粘贴文字内容，它会自动生成一整套幻灯片，包括排版、配色、图标。你还可以自定义风格、上传品牌素材。生成后可以直接在线演示或导出PPT。"),
        ("Gamma免费吗？",
         "免费版可以生成有限数量的PPT，风格选择也受限。付费版Pro月付10美元起，无限生成，开放所有风格和品牌套件功能。对有PPT需求的内容创作者来说，性价比很高。"),
    ],
    "elevenlabs": [
        ("ElevenLabs有中文声音吗？",
         "有。ElevenLabs支持27种语言，包括中文。选择语音时搜索'Chinese'或'中文'，能找到多种风格的中文配音。部分中文声音模型还能保留方言口音特色。选择时可先试听再确定。"),
        ("如何用ElevenLabs做AI配音？",
         "1）注册并登录ElevenLabs；2）选择或克隆声音（也可以用预设声音）；3）粘贴或输入要配音的文字；4）调整语速、语调参数；5）点击生成并下载MP3。生成的音频可以直接用于视频配音、有声书等场景。"),
    ],
    "dall-e-3": [
        ("DALL-E 3和Midjourney哪个好？",
         "两者定位不同。DALL-E 3是OpenAI开发的图片生成模型，集成在ChatGPT里使用，操作简单，画风偏写实和精确，适合做配图、插画。Midjourney生成的图片艺术感更强，风格多样，但需要学习提示词技巧。简单说：想要精确内容选DALL-E，想要艺术效果选Midjourney。"),
        ("如何用DALL-E 3生成图片？",
         "在ChatGPT里直接说'画一张XX图'就行，描述越具体效果越好。比如：'画一张赛博朋克风格的东京夜景，宽屏比例，适合做壁纸'。DALL-E 3会自动理解语境并生成对应图片。每次生成4张，可选其中一张放大或变体。"),
    ],
}

added = 0
for tool in tools:
    slug = tool['slug']
    if slug not in FAQS_TO_ADD:
        continue
    new_faqs = FAQS_TO_ADD[slug]
    existing_qs = {q['question'] for q in tool.get('faq', [])}
    for q, a in new_faqs:
        if q not in existing_qs:
            tool.setdefault('faq', [])
            tool['faq'].append({'question': q, 'answer': a})
            added += 1
            print(f'  + {slug}: {q[:25]}...')

print(f'\nTotal added: {added} FAQ entries')
with open('data/tools.json', 'w', encoding='utf-8') as f:
    json.dump(tools, f, ensure_ascii=False, indent=2)
print('Saved.')