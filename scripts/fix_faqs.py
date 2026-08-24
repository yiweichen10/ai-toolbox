"""
为所有工具生成高质量的针对性FAQ，替换模板化的垃圾FAQ。
每个FAQ必须具体、有信息量，能真正帮助用户做决策。
"""
import json
import re

# 高质量FAQ - 基于每个工具的实际特性和用户真实问题
QUALITY_FAQS = {
    "ChatGPT": [
        {
            "question": "ChatGPT免费版和Plus版有什么区别？值得付费吗？",
            "answer": "免费版可以使用GPT-5基础功能，有次数限制。Plus版（$20/月）可无限制使用GPT-5、DALL-E 4图片生成、GPTs创建、高级语音对话等。如果你每天重度使用AI辅助工作和学习，Plus版物超所值；偶尔使用的话免费版足够。"
        },
        {
            "question": "ChatGPT在国内怎么用？",
            "answer": "ChatGPT在国内需要通过科学上网访问。也可以使用官方API接口接入第三方客户端。国内用户也可以考虑DeepSeek、Kimi、豆包等国产替代品，功能接近且无需翻墙。"
        },
        {
            "question": "ChatGPT和Claude哪个更好？",
            "answer": "各有所长。ChatGPT在多模态能力、插件生态、GPTs市场方面更强；Claude在长文本处理（1000K上下文）、代码质量、写作水平方面更优。建议都试试，根据具体需求选择。日常对话选ChatGPT，长文档和代码选Claude。"
        },
        {
            "question": "ChatGPT能处理哪些类型的文件？",
            "answer": "ChatGPT支持上传PDF、Word、Excel、PPT、图片、音频、视频等多种格式。可以分析文档内容、提取数据、总结要点、生成图表等。Plus版支持更大的文件和更多的分析次数。"
        }
    ],
    "Claude": [
        {
            "question": "Claude和ChatGPT哪个更适合写代码？",
            "answer": "Claude在代码审查、重构和大型项目理解方面表现更好，尤其是超长代码文件的处理。ChatGPT在快速生成代码片段和小功能实现上更方便。如果你需要AI阅读和理解整个代码库，Claude的1000K上下文窗口是碾压级优势。"
        },
        {
            "question": "Claude的Artifacts功能是什么？怎么用？",
            "answer": "Artifacts是Claude独有的功能，可以让AI生成的内容（网页、图表、文档、代码）直接在对话中预览和交互。比如让Claude做一个网页，它会生成一个可运行的预览版本，不需要复制代码到编辑器。"
        },
        {
            "question": "Claude免费版有什么限制？",
            "answer": "免费版可以使用Claude 4基础模型，但有每日使用次数限制，上下文长度限制在100K。Pro版（$20/月）提供Claude 4完整功能、1000K超长上下文、优先访问新功能和项目功能。"
        },
        {
            "question": "Claude的安全性比ChatGPT好吗？",
            "answer": "Claude由Anthropic开发，公司以AI安全为核心使命。Claude在减少幻觉、拒绝有害请求、保持回答准确性方面确实比ChatGPT表现更好。对于企业用户和需要可靠信息的场景，Claude更值得信赖。"
        }
    ],
    "天工AI": [
        {
            "question": "天工AI和ChatGPT有什么区别？",
            "answer": "天工AI的最大特色是AI搜索功能，能实时联网检索信息并整合回答，类似Perplexity。而ChatGPT在通用对话、代码生成和多模态能力上更强。天工AI的优势在于国内直连免费、中文搜索生态好。"
        },
        {
            "question": "天工AI免费吗？有什么限制？",
            "answer": "天工AI基础版完全免费，日常使用足够。搜索和对话功能免费使用，部分高级功能（如长文档分析、AI绘画等）可能有次数限制。Pro版提供更多额度和优先响应。"
        },
        {
            "question": "天工AI的AI搜索怎么用？",
            "answer": "直接在天工AI对话框中输入问题，它会自动联网搜索并给出带引用来源的回答。适合查最新资讯、做研究、对比产品等需要实时信息的场景。回答会标注信息来源，方便核实。"
        },
        {
            "question": "天工AI是谁开发的？",
            "answer": "天工AI由昆仑万维（Opera浏览器母公司）开发，基于自研的Skywork大模型。昆仑万维是国内较早布局大模型的公司之一，天工模型多次在中文评测中排名前列。"
        }
    ],
    "DALL-E 3": [
        {
            "question": "DALL-E 3怎么用？需要单独付费吗？",
            "answer": "DALL-E 3集成在ChatGPT中，不需要单独注册。免费版ChatGPT每天可以生成2张DALL-E 3图片，ChatGPT Plus用户（$20/月）可以无限制生成。也可以通过OpenAI API按量付费使用。"
        },
        {
            "question": "DALL-E 3和Midjourney哪个好？",
            "answer": "DALL-E 3的优势是理解自然语言能力强（直接用中文描述即可）、使用门槛低（在ChatGPT里直接用）、文字渲染准确。Midjourney的优势是画质更顶级、艺术感更强、风格控制更精细。新手选DALL-E 3，追求极致画质选Midjourney。"
        },
        {
            "question": "DALL-E 3生成的图片可以商用吗？",
            "answer": "ChatGPT Plus用户生成的图片可以商用，OpenAI将生成内容的权利转让给用户。免费版的使用条款可能有限制，建议查看OpenAI最新的使用政策。"
        },
        {
            "question": "DALL-E 3能生成文字图片吗？",
            "answer": "可以，DALL-E 3在图片中渲染文字的能力是AI绘画工具中最强的之一。你可以在prompt中指定要显示的文字，比如'一张带有'Hello World'文字的霓虹灯牌'，生成的文字准确率很高。"
        }
    ],
    "秒画": [
        {
            "question": "秒画怎么用？需要付费吗？",
            "answer": "秒画是商汤科技推出的AI绘画工具，通过网页访问 miaohua.sensetime.com 即可使用。新用户有免费体验额度，之后需要按量或订阅付费。支持中文prompt直接输入，上手非常简单。"
        },
        {
            "question": "秒画和其他AI绘画工具相比有什么优势？",
            "answer": "秒画最大的优势是中文prompt原生支持，不需要翻译成英文。作为商汤科技的产品，底层模型在中文理解和东方美学风格方面有特色。适合国内用户快速出图、社交媒体素材制作等场景。"
        },
        {
            "question": "秒画生成的图片可以商用吗？",
            "answer": "秒画的商用政策取决于你的订阅等级。付费用户通常享有商用授权，免费用户建议查看官方使用条款。用于个人学习和非商业用途通常没有问题。"
        },
        {
            "question": "秒画支持哪些图片尺寸？",
            "answer": "秒画支持多种常用比例，包括1:1方形、16:9横屏、9:16竖屏、4:3、3:4等。竖屏图片特别适合小红书、抖音等国内社交平台的封面制作。"
        }
    ],
    "Cursor": [
        {
            "question": "Cursor和GitHub Copilot哪个更好？",
            "answer": "Cursor是独立的AI代码编辑器（基于VS Code），AI能力更深地集成在编辑器中，支持整个项目的上下文理解。GitHub Copilot是VS Code插件，轻量但功能相对基础。重度编程用户推荐Cursor，轻度辅助推荐Copilot。"
        },
        {
            "question": "Cursor免费吗？",
            "answer": "Cursor有免费版，每月有2000次AI补全和50次高级请求。Pro版$20/月，提供无限次AI补全和高级请求。对于专业开发者，Pro版性价比很高。"
        },
        {
            "question": "Cursor支持哪些编程语言？",
            "answer": "Cursor支持几乎所有主流编程语言，包括Python、JavaScript/TypeScript、Java、C/C++、Go、Rust、PHP等。它基于VS Code，所以VS Code的所有语言支持和插件都能用。"
        },
        {
            "question": "Cursor能导入我现有的VS Code配置吗？",
            "answer": "可以，Cursor兼容VS Code的设置、插件和快捷键。安装Cursor后可以一键导入VS Code的配置，几乎零迁移成本。你的VS Code插件、主题、设置都可以直接使用。"
        }
    ],
    "Midjourney": [
        {
            "question": "Midjourney怎么用？为什么要在Discord里？",
            "answer": "Midjourney通过Discord平台使用，在Discord频道输入/imagine命令加描述即可生成图片。虽然对新手不太友好，但Discord的社区生态非常丰富，可以看别人的作品、学习prompt技巧。也有第三方网站封装了Midjourney API，提供网页版使用。"
        },
        {
            "question": "Midjourney V7和之前的版本有多大提升？",
            "answer": "V7版本实现了照片级画质输出，在细节质感、光影表现、人物真实感方面大幅提升。还改进了风格一致性控制，可以让同一角色在不同场景中保持一致的外观。风格参考功能也更强大。"
        },
        {
            "question": "Midjourney必须付费吗？没有免费试用吗？",
            "answer": "Midjourney从2024年起取消了免费试用，最低$10/月的基础版。不过可以通过官方活动偶尔获得试用机会，或者使用第三方平台（如某些国内平台）体验类似功能。"
        },
        {
            "question": "Midjourney生成的图片版权归属谁？",
            "answer": "根据Midjourney的服务条款，付费用户对生成的图片拥有使用权利，包括商用。但不能声称是人类的创作。Midjourney不主张生成图片的版权，但具体法律情况因地区而异。"
        }
    ],
    "Kimi": [
        {
            "question": "Kimi有什么特别的优势？",
            "answer": "Kimi最大的优势是超长文本处理能力，支持200万字超长上下文，可以一次性阅读整本书、大量论文或超长代码文件。而且完全免费、国内直连、中文理解优秀，是国产AI助手中综合素质最好的之一。"
        },
        {
            "question": "Kimi免费吗？",
            "answer": "Kimi基础版完全免费，注册即可使用。支持对话、搜索、文件分析等核心功能。付费版提供更长上下文和更快的响应速度，但免费版已能满足大多数用户需求。"
        },
        {
            "question": "Kimi能读多长的文档？",
            "answer": "Kimi支持上传200万字以内的超长文档，相当于几十本书的内容。可以上传PDF、Word、TXT、Excel等格式。特别适合学术研究、长文分析、合同审查等需要处理大量文字的场景。"
        },
        {
            "question": "Kimi和豆包哪个好？",
            "answer": "Kimi在长文本处理和深度分析方面更强，适合学术、文档处理场景。豆包（字节跳动）在语音交互、AI角色扮演方面更有特色。两者都免费且国内直连，建议根据使用场景选择。"
        }
    ],
    "豆包": [
        {
            "question": "豆包和ChatGPT有什么区别？",
            "answer": "豆包是字节跳动推出的AI助手，最大的区别是豆包在国内可以直接使用，不需要翻墙。豆包在语音交互、AI角色对话、多模态理解方面有特色。ChatGPT在代码生成、GPTs生态和多模态能力上更强。"
        },
        {
            "question": "豆包有哪些功能？",
            "answer": "豆包支持智能对话、AI搜索、语音通话、图片理解、文档分析、AI角色扮演、AI写作等功能。特色功能包括和AI角色的语音实时通话、AI绘画（集成在豆包中）、以及丰富的AI角色预设。"
        },
        {
            "question": "豆包免费吗？",
            "answer": "豆包基础功能完全免费，包括对话、搜索、文件分析等。部分高级功能（如AI绘画的某些模型）可能需要付费或消耗积分。日常使用基本不需要花钱。"
        }
    ],
    "DeepSeek": [
        {
            "question": "DeepSeek有什么特别之处？",
            "answer": "DeepSeek以开源和低成本著称，DeepSeek-V3和R1模型的性能接近GPT-4级别，但训练成本极低。DeepSeek-R1在数学推理和代码生成方面表现优异。所有模型开源，可以本地部署，企业用户可以自由使用。"
        },
        {
            "question": "DeepSeek免费吗？",
            "answer": "DeepSeek网页版和App完全免费使用，没有次数限制。API价格也非常便宜，是国内最实惠的大模型API之一。开源模型可以免费下载和本地部署。"
        },
        {
            "question": "DeepSeek和ChatGPT哪个强？",
            "answer": "在数学推理和代码生成方面，DeepSeek-R1可以和GPT-4媲美甚至超越。在通用对话、多模态能力、插件生态方面，ChatGPT仍然领先。考虑到DeepSeek完全免费且开源，性价比极高。"
        },
        {
            "question": "DeepSeek能本地部署吗？",
            "answer": "可以，DeepSeek模型完全开源，支持本地部署。蒸馏版的小模型（如1.5B、7B）可以在普通电脑上运行。完整版模型需要较强的GPU。开源让企业可以私有化部署，保护数据安全。"
        }
    ],
    "Notion AI": [
        {
            "question": "Notion AI需要额外付费吗？",
            "answer": "Notion AI是Notion的附加功能，需要额外订阅。已有Notion付费计划的话，AI功能$10/月（按年$96）。如果只用免费版Notion，需要先购买付费计划再加AI。不过Notion AI集成在文档编辑流程中，体验很流畅。"
        },
        {
            "question": "Notion AI能做什么？",
            "answer": "Notion AI可以帮你写文档、总结长文、翻译、提炼要点、生成表格、润色文字、改写语气等。最方便的是直接在Notion页面中调用，不需要切换工具。适合知识管理和文档工作流重的用户。"
        },
        {
            "question": "Notion AI和ChatGPT有什么区别？",
            "answer": "ChatGPT是通用AI对话助手，功能更全面。Notion AI专注于文档和知识管理场景，直接集成在你的笔记中。如果你已经重度使用Notion做知识管理，Notion AI更方便；如果只是偶尔需要AI辅助，ChatGPT更划算。"
        }
    ],
    "文心一言": [
        {
            "question": "文心一言有什么优势和特色？",
            "answer": "文心一言是百度推出的AI助手，最大优势是与百度搜索生态深度整合，搜索能力强。在中文理解、中国文化知识方面训练充分。支持文生图、代码生成、文档分析等功能。"
        },
        {
            "question": "文心一言免费吗？",
            "answer": "文心一言基础版免费使用，有每日次数限制。付费版提供更多额度、更快的响应速度和更强大的模型。百度网盘等百度生态产品有时会赠送文心一言额度。"
        },
        {
            "question": "文心一言的AI绘画功能怎么样？",
            "answer": "文心一言内置的AI绘画功能（文心一格）在中文描述理解方面表现不错，支持国风、水墨等东方风格。在精度和多样性方面相比Midjourney和DALL-E 3还有差距，但日常使用够用。"
        }
    ],
    "千问": [
        {
            "question": "千问是什么？谁开发的？",
            "answer": "千问（通义千问）是阿里巴巴推出的AI助手，基于通义大模型。已开源多个版本模型，在代码生成、数学推理方面表现突出。集成在阿里云生态中，适合开发者和企业用户。"
        },
        {
            "question": "千问免费吗？",
            "answer": "千问网页版和App免费使用。开源模型可以免费下载部署。通过阿里云百炼平台调用API也有免费额度。是国产大模型中性价比最高的选择之一。"
        },
        {
            "question": "千问和DeepSeek哪个好？",
            "answer": "两者都是优秀的开源模型。千问（Qwen）在多语言和长文本方面有优势，且与阿里云生态深度整合。DeepSeek在数学推理和代码方面更突出，API价格更低。建议根据具体使用场景选择，也可以都试试。"
        }
    ],
    "Runway": [
        {
            "question": "Runway能生成什么样的视频？",
            "answer": "Runway以文生视频和图生视频闻名。Gen-3 Alpha模型可以生成4-10秒的高质量视频片段，支持文字描述生成视频、图片转动态视频、视频风格迁移等。适合广告、短视频、概念预览等场景。"
        },
        {
            "question": "Runway的价格怎么样？",
            "answer": "Runway基础版$15/月，可生成约125个视频片段。标准版$35/月，额度更多且支持更高分辨率。视频生成消耗算力较大，相比图片生成更贵。但相比请制作团队，成本仍然很低。"
        },
        {
            "question": "Runway和Sora哪个更好？",
            "answer": "Sora（OpenAI）在视频质量和时长方面更先进，但目前对公众开放有限。Runway是目前最成熟的商用AI视频工具，功能全面、稳定性好。如果你现在就需要生成视频，Runway是最佳选择。"
        }
    ],
    "Suno": [
        {
            "question": "Suno能生成完整的歌曲吗？",
            "answer": "可以，Suno可以生成完整的2分钟左右歌曲，包含歌词、人声演唱和音乐伴奏。你只需要描述想要的风格和主题，或者自己写歌词，Suno就能生成一首完整的歌曲。支持多种风格：流行、摇滚、电子、古典、中国风等。"
        },
        {
            "question": "Suno免费吗？",
            "answer": "Suno免费版每天可以生成10首歌曲。Pro版$10/月，生成250首/月。Premier版$30/月，生成1000首/月。免费版已经够日常娱乐使用，商用需要付费版。"
        },
        {
            "question": "Suno生成的音乐可以商用吗？",
            "answer": "免费版生成的音乐不能商用。Pro和Premier版用户拥有生成音乐的商用使用权。如果你需要用AI音乐做背景音乐、广告配乐等商业用途，需要订阅付费版。"
        }
    ],
    "Perplexity": [
        {
            "question": "Perplexity和普通搜索引擎有什么区别？",
            "answer": "普通搜索引擎返回一堆网页链接让你自己看，Perplexity直接给你整理好的答案，并标注信息来源。相当于AI帮你读完所有相关网页然后写一份总结报告。搜索效率大幅提升，特别适合做研究和调研。"
        },
        {
            "question": "Perplexity免费版够用吗？",
            "answer": "免费版可以使用标准搜索模式，每天有次数限制。Pro版$20/月可以使用更强的模型（如Claude 3、GPT-4）、Pro搜索（更深入的研究）、文件上传分析等。日常简单查询免费版够用，深度研究建议Pro版。"
        },
        {
            "question": "Perplexity和天工AI搜索有什么区别？",
            "answer": "功能类似，都是AI搜索。Perplexity的英文信息源更丰富、答案质量更高；天工AI的中文搜索更好、国内直连免费。中文内容搜索推荐天工AI，英文内容或学术研究推荐Perplexity。"
        }
    ],
    "Gemini": [
        {
            "question": "Gemini和ChatGPT哪个好？",
            "answer": "Gemini是Google推出的AI助手，最大的优势是与Google搜索和Google生态深度整合，信息获取能力强。在多模态理解（同时理解文字、图片、视频）方面也很强。ChatGPT在代码生成和插件生态方面更成熟。"
        },
        {
            "question": "Gemini免费吗？",
            "answer": "Gemini基础版免费使用，集成在Google生态中。Advanced版$20/月，使用更强的Gemini Ultra模型，支持更多功能和更大的上下文。如果你使用Google全家桶，Gemini体验会更流畅。"
        },
        {
            "question": "Gemini能访问Google搜索吗？",
            "answer": "可以，Gemini与Google搜索深度整合，可以实时获取最新网络信息。这是相比很多AI助手的优势——搜索能力由全球最大的搜索引擎支撑，信息覆盖面广、时效性强。"
        }
    ],
    "Stable Diffusion": [
        {
            "question": "Stable Diffusion免费吗？需要什么配置？",
            "answer": "Stable Diffusion完全开源免费。但需要一定的硬件配置：至少需要NVIDIA显卡8GB显存（推荐12GB+）。没有好显卡的话，可以使用云端部署服务（如商汤的SenseNova等），按量付费。"
        },
        {
            "question": "Stable Diffusion和Midjourney哪个好？",
            "answer": "Stable Diffusion免费开源、可本地部署、自定义性强（海量模型和LoRA），但需要技术能力和好显卡。Midjourney付费但使用简单、画质顶级、开箱即用。技术用户选SD，追求效率选MJ。"
        },
        {
            "question": "Stable Diffusion怎么上手？",
            "answer": "推荐使用WebUI（如AUTOMATIC1111）或ComfyUI作为界面。新手可以先在云端平台（如Google Colab免费GPU）体验，再考虑本地部署。社区有大量教程和预设模型可以学习使用。"
        }
    ],
    "Canva AI": [
        {
            "question": "Canva AI能做什么设计？",
            "answer": "Canva AI覆盖几乎所有日常设计需求：社交媒体图片、海报、演示文稿、视频、logo、名片、简历等。AI功能包括一键生成设计、魔法调整、背景移除、文字生成图片等。适合非设计师快速出图。"
        },
        {
            "question": "Canva AI免费吗？",
            "answer": "Canva基础版免费，有大量模板可用。AI功能大部分需要付费版（Pro $13/月），包括AI图片生成、魔法调整等高级功能。但基础的设计编辑和模板使用是完全免费的。"
        },
        {
            "question": "Canva AI和Photoshop AI哪个好？",
            "answer": "Canva AI面向非专业用户，模板多、操作简单、在线使用。Photoshop AI面向专业设计师，功能更强大、控制更精细。如果你不是专业设计师，Canva AI效率更高。"
        }
    ],
    "Sora": [
        {
            "question": "Sora可以生成多长的视频？",
            "answer": "Sora目前可以生成最长1分钟的高清视频。根据OpenAI的演示，视频质量非常高，场景连贯性和物理准确性都很出色。不过目前Sora仍在逐步开放中，普通用户可能还需要等待。"
        },
        {
            "question": "Sora怎么用？",
            "answer": "Sora通过OpenAI平台使用，目前主要面向ChatGPT Plus和Pro用户。在ChatGPT中描述你想要的视频场景，Sora会生成对应的视频。也可能通过独立的Sora网站访问。"
        }
    ],
    "Pika": [
        {
            "question": "Pika能生成什么样的视频？",
            "answer": "Pika专注于短视频生成，可以生成3-4秒的AI视频片段。支持文生视频、图生视频、视频编辑（局部修改、扩展画面）。特色功能包括口型同步（lip sync）和音效生成。适合社交媒体短视频创作。"
        },
        {
            "question": "Pika免费吗？",
            "answer": "Pika有免费额度（初始250积分），Pro版$10/月（1050积分）。生成一个视频消耗约30积分，所以免费版大约能生成8个视频。付费版性价比不错。"
        }
    ],
    "ElevenLabs": [
        {
            "question": "ElevenLabs的AI配音效果怎么样？",
            "answer": "ElevenLabs是目前最自然的AI语音合成工具，支持中文、英文等29种语言。声音逼真度高，情感表达自然，几乎听不出是AI生成。支持声音克隆（上传几秒音频即可克隆声线）。"
        },
        {
            "question": "ElevenLabs有中文声音吗？",
            "answer": "有，ElevenLabs支持高质量的中文语音合成，包括男声和女声。还可以通过声音克隆功能，用你自己的声音或任何中文音频创建自定义声音。中文发音和语调自然度在AI工具中领先。"
        }
    ],
    "HeyGen": [
        {
            "question": "HeyGen能做什么？",
            "answer": "HeyGen是AI视频生成工具，核心功能是AI数字人视频。你可以输入文字，选择一个AI虚拟人像，自动生成口型匹配的真人效果视频。支持30+语言翻译，可以创建多语言版本的视频。"
        },
        {
            "question": "HeyGen和D-ID有什么区别？",
            "answer": "功能类似，都是AI数字人视频。HeyGen的视频质量更高、模板更丰富、支持视频翻译。D-ID操作更简单、价格更低。如果要制作高质量的营销视频，选HeyGen；简单头像动画选D-ID。"
        }
    ],
    "DeepL": [
        {
            "question": "DeepL和Google翻译哪个好？",
            "answer": "在中文英互译和欧洲语言翻译方面，DeepL的质量明显优于Google翻译。翻译更自然流畅，不像机器翻译。DeepL免费版有限制（每月3个文档），Google翻译完全免费。追求质量选DeepL，日常快速翻译选Google。"
        },
        {
            "question": "DeepL免费吗？",
            "answer": "DeepL翻译器（网页版和桌面版）免费使用，有文本长度限制。DeepL Pro（$10/月起）解锁无限翻译、文档翻译、API访问等。对于偶尔翻译的用户，免费版完全够用。"
        }
    ],
    "GitHub Copilot": [
        {
            "question": "GitHub Copilot和Cursor哪个好？",
            "answer": "Cursor是独立编辑器，AI能力更深（支持项目级上下文），体验更沉浸。GitHub Copilot是VS Code插件，轻量灵活，可以配合你现有的VS Code环境。重度编程推荐Cursor，想在VS Code里轻度辅助推荐Copilot。"
        },
        {
            "question": "GitHub Copilot有免费版吗？",
            "answer": "GitHub Copilot对开源项目维护者、学生和认证的教育用户免费。普通用户$10/月或$100/年。企业版$39/月。相比Cursor的$20/月，Copilot价格更低。"
        }
    ],
    "Gamma": [
        {
            "question": "Gamma能自动生成PPT吗？",
            "answer": "可以，Gamma可以根据主题描述自动生成完整的演示文稿，包括内容、排版和配图。支持从大纲生成、从文档生成、从模板修改。生成速度很快，几分钟就能得到一份专业的PPT。"
        },
        {
            "question": "Gamma免费吗？",
            "answer": "Gamma有免费版，可以创建有限的演示文稿。Pro版$10/月，解锁更多AI生成次数和高级模板。对于偶尔做PPT的用户，免费版基本够用。"
        }
    ],
    "腾讯元宝": [
        {
            "question": "腾讯元宝有什么特色功能？",
            "answer": "腾讯元宝深度整合了微信搜一搜、微信公众号文章等腾讯生态内容。支持文档分析、AI搜索、AI写作等。特色在于能搜索和引用微信生态的内容，这是其他AI助手做不到的。"
        },
        {
            "question": "腾讯元宝免费吗？",
            "answer": "腾讯元宝基础功能免费使用，有每日使用额度。作为腾讯推出的产品，可能会和腾讯会员等体系联动。日常使用免费版足够。"
        }
    ],
    "可灵AI": [
        {
            "question": "可灵AI能生成什么类型的视频？",
            "answer": "可灵AI是快手推出的视频生成模型，支持文生视频和图生视频。可以生成2-5秒的高质量视频片段，在人物动作、面部表情方面表现突出。特别适合做短视频、动画和创意内容。"
        },
        {
            "question": "可灵AI免费吗？",
            "answer": "可灵AI有免费体验额度，新用户注册送一定积分。每天也有免费生成次数。超出免费额度后需要付费。相比海外视频生成工具，可灵AI的价格更友好。"
        }
    ],
    "智谱清言": [
        {
            "question": "智谱清言和ChatGPT有什么区别？",
            "answer": "智谱清言基于GLM大模型，是清华系团队开发的。最大优势是国内直连免费，中文能力强。支持AI搜索、文档分析、代码生成、AI绘画等功能。在中文场景下，效果接近ChatGPT。"
        },
        {
            "question": "智谱清言免费吗？",
            "answer": "智谱清言基础版免费使用，支持核心功能。付费版提供更长的上下文、更快的响应和更多功能。API调用也有免费额度。是国产大模型中综合实力最强的之一。"
        }
    ],
    "讯飞星火": [
        {
            "question": "讯飞星火有什么优势？",
            "answer": "讯飞星火由科大讯飞开发，在语音识别和语音合成方面有独特优势。支持语音对话、实时语音翻译、会议纪要生成等。深度整合了讯飞的语音技术积累，在语音交互场景表现最好。"
        },
        {
            "question": "讯飞星火适合什么人用？",
            "answer": "特别适合需要语音交互的用户：会议记录、语音输入、语音翻译、有声内容创作等。也适合教育场景，讯飞有丰富的教育资源和工具。"
        }
    ],
    "Grok": [
        {
            "question": "Grok是什么？和ChatGPT有什么区别？",
            "answer": "Grok是xAI（Elon Musk创立）推出的AI助手，集成在X（原Twitter）平台中。最大特色是实时访问X平台的最新推文和新闻，信息时效性极强。风格更幽默直接，没有那么多审查限制。"
        },
        {
            "question": "Grok怎么用？",
            "answer": "Grok通过X平台使用，需要X Premium订阅（$16/月起）。也可以通过独立网站grok.com访问。如果你是X的重度用户，Grok的实时信息获取能力很有价值。"
        }
    ],
    "NotebookLM": [
        {
            "question": "NotebookLM是什么？怎么用？",
            "answer": "NotebookLM是Google推出的AI学习工具。你上传文档（PDF、网页、YouTube视频等），它会基于你的资料回答问题、生成摘要、创建学习指南。特别适合学生和研究人员处理大量资料。"
        },
        {
            "question": "NotebookLM免费吗？",
            "answer": "NotebookLM完全免费使用，通过Google账号登录即可。支持上传多个文档创建笔记本，AI基于你的笔记内容回答问题。是学习辅助工具中性价比最高的选择。"
        }
    ],
    "Bolt.new": [
        {
            "question": "Bolt.new能做什么？",
            "answer": "Bolt.new是全栈AI开发工具，通过自然语言描述即可生成完整的Web应用。AI会自动编写前端（React）、后端和数据库代码，并在浏览器中实时预览。适合快速原型开发和MVP验证。"
        },
        {
            "question": "Bolt.new和Cursor有什么区别？",
            "answer": "Bolt.new更偏向快速原型，描述需求即可生成完整应用，适合非开发者。Cursor是代码编辑器，更适合有编程基础的人精细开发。想要快速验证想法用Bolt.new，想要深度开发用Cursor。"
        }
    ],
    "Windsurf": [
        {
            "question": "Windsurf是什么？",
            "answer": "Windsurf是Codeium推出的AI代码编辑器，和Cursor类似。特色在于Cascade功能——AI可以连续执行多步骤操作，自动处理依赖关系。价格更便宜（$15/月），是Cursor的有力竞争者。"
        },
        {
            "question": "Windsurf和Cursor哪个好？",
            "answer": "Cursor生态更成熟、用户更多、AI能力略强。Windsurf价格更低（$15 vs $20）、Cascade流程自动化更流畅。两者都基于VS Code，可以都试试再决定。"
        }
    ],
    "Grammarly AI": [
        {
            "question": "Grammarly只能检查英文语法吗？",
            "answer": "Grammarly主要针对英文语法、拼写和写作风格检查。在英文写作方面的AI辅助是行业最好的。对中文等其他语言的支持有限。如果你的工作需要大量英文写作，Grammarly是必备工具。"
        },
        {
            "question": "Grammarly免费版够用吗？",
            "answer": "免费版提供基础语法和拼写检查，足够日常使用。Premium版（$12/月）提供高级写作建议、语气调整、抄袭检测等。对于需要写正式英文邮件、论文、报告的用户，Premium版值得投资。"
        }
    ],
    "WPS AI": [
        {
            "question": "WPS AI能做什么？",
            "answer": "WPS AI集成在WPS Office中，可以AI辅助写作文档、生成PPT大纲、分析Excel数据、总结PDF内容等。最适合需要在Office办公场景中使用AI的用户，不需要切换工具。"
        },
        {
            "question": "WPS AI免费吗？",
            "answer": "WPS AI有免费体验额度，深度使用需要WPS会员。价格比Microsoft Copilot便宜。如果你已经使用WPS办公，AI功能可以作为增值服务。"
        }
    ],
    "Character AI": [
        {
            "question": "Character AI是什么？",
            "answer": "Character AI是一个AI角色对话平台。你可以和AI扮演的各种角色聊天，包括名人、虚构角色、或者自定义角色。支持创建自己的AI角色，设定性格和背景故事。娱乐性很强。"
        },
        {
            "question": "Character AI免费吗？",
            "answer": "Character AI基础功能完全免费。付费版c.ai+（$10/月）可以跳过等待队列、更快的响应、提前体验新功能。免费版功能已经很完整，付费版主要是体验优化。"
        }
    ],
    "Poe": [
        {
            "question": "Poe是什么？",
            "answer": "Poe是Quora推出的AI聚合平台，在一个界面中可以访问多个AI模型：GPT-4、Claude、Gemini、Llama等。不需要分别注册各个AI服务，一个平台搞定所有主流AI模型。"
        },
        {
            "question": "Poe免费吗？",
            "answer": "Poe有免费额度，每天可以有限次使用各AI模型。订阅版（$20/月）提供无限次使用。如果你需要频繁切换不同AI模型，Poe比分别订阅各服务更划算。"
        }
    ],
    "n8n": [
        {
            "question": "n8n是什么？和Zapier有什么区别？",
            "answer": "n8n是开源的工作流自动化工具，和Zapier功能类似但更灵活。n8n可以自托管（免费），数据完全自己掌控。Zapier是SaaS服务，使用更简单但有月费。技术团队选n8n，非技术用户选Zapier。"
        },
        {
            "question": "n8n免费吗？",
            "answer": "n8n社区版完全免费，可以自托管在自己服务器上。n8n Cloud（云端版）有免费额度（每月5个工作流），付费版$24/月起。自托管版功能完整无限制，只需要自己的服务器。"
        }
    ],
    "Coze": [
        {
            "question": "Coze是什么？能做什么？",
            "answer": "Coze是字节跳动推出的AI Bot开发平台。可以通过拖拽方式创建AI聊天机器人，不需要编程。支持添加插件、知识库、工作流等。创建的Bot可以发布到豆包、微信公众号等平台。"
        },
        {
            "question": "Coze免费吗？",
            "answer": "Coze基础功能免费使用，包括创建Bot、添加插件和知识库。API调用有免费额度。适合想快速创建AI助手但不懂编程的用户。"
        }
    ],
    "Dify": [
        {
            "question": "Dify是什么？",
            "answer": "Dify是开源的LLM应用开发平台，可以快速搭建AI应用：聊天机器人、知识库问答、AI Agent等。支持多种大模型，提供可视化的工作流编排。适合企业和开发者构建AI应用。"
        },
        {
            "question": "Dify和Coze有什么区别？",
            "answer": "Dify更偏技术向，适合开发者构建复杂的AI应用，支持私有化部署。Coze更偏用户向，拖拽式操作适合非技术人员快速创建聊天机器人。企业级应用推荐Dify，简单Bot推荐Coze。"
        }
    ],
    "Zapier AI": [
        {
            "question": "Zapier AI能做什么？",
            "answer": "Zapier AI让自动化更智能。可以用自然语言描述想要的自动化流程，AI自动帮你配置。支持5000+应用的连接。比如'收到邮件时自动总结并发送到Slack'，一句话就能搞定。"
        },
        {
            "question": "Zapier有免费版吗？",
            "answer": "Zapier有免费版，支持100次任务/月和5个Zap。付费版$20/月起，解锁更多任务量和高级功能。对于简单的自动化需求，免费版够用。"
        }
    ],
    "v0.dev": [
        {
            "question": "v0.dev能做什么？",
            "answer": "v0.dev是Vercel推出的AI前端代码生成工具。通过文字描述或截图即可生成高质量的React/Next.js前端代码和UI组件。生成的代码直接可用，支持一键部署。适合快速开发前端界面。"
        },
        {
            "question": "v0.dev免费吗？",
            "answer": "v0.dev有免费额度（每月一定的生成次数），付费版$20/月提供更多生成次数。适合前端开发者快速生成UI组件，非开发者也能用它快速搭建网页界面。"
        }
    ],
    "Adobe Firefly": [
        {
            "question": "Adobe Firefly和Midjourney哪个好？",
            "answer": "Firefly的优势是与Photoshop/Illustrator等Adobe工具深度集成，商业使用更安全（只用授权素材训练）。画质不如Midjourney顶级，但稳定性好。专业设计师推荐Firefly（版权安全），追求极致画质选Midjourney。"
        },
        {
            "question": "Adobe Firefly免费吗？",
            "answer": "Firefly网页版有25个免费积分/月。Creative Cloud订阅用户可以使用更完整的Firefly功能。独立订阅Firefly $5/月起。"
        }
    ],
    "Lovable": [
        {
            "question": "Lovable能做什么？",
            "answer": "Lovable是AI全栈开发工具，类似Bolt.new。通过描述需求自动生成完整的Web应用，包括前端UI、后端逻辑和数据库。支持从Figma设计稿直接生成代码。适合快速开发和MVP验证。"
        },
        {
            "question": "Lovable和Bolt.new哪个好？",
            "answer": "功能类似。Lovable在UI设计和Figma集成方面更强，Bolt.new在开发速度和代码质量方面略优。两者都是$20/月，建议都试试看哪个更适合你的工作流。"
        }
    ],
    "Luma AI": [
        {
            "question": "Luma AI能做什么？",
            "answer": "Luma AI的核心功能是3D场景和视频生成。可以用手机扫描真实物体生成3D模型，或用AI生成3D视频。Dream Machine模型可以生成高质量的视频。适合3D创作者和视频创作者。"
        }
    ],
    "Ideogram": [
        {
            "question": "Ideogram有什么特色？",
            "answer": "Ideogram以在图片中准确渲染文字著称，是AI绘画工具中文字生成最准确的之一。适合需要制作含有文字的图片：logo、海报、封面、表情包等。免费用户每天可以生成一定数量的图片。"
        }
    ],
    "CapCut AI": [
        {
            "question": "CapCut AI能做什么？",
            "answer": "CapCut（剪映国际版）的AI功能包括：AI自动剪辑、智能字幕、AI配音、背景替换、人像抠图等。集成在视频编辑工作流中，一键完成原本耗时的操作。适合短视频创作者提升效率。"
        }
    ],
    "Photoroom": [
        {
            "question": "Photoroom适合什么人用？",
            "answer": "Photoroom专注于电商产品图处理。一键去除背景、AI生成专业拍摄场景、批量处理。最适合淘宝、拼多多、亚马逊等平台的电商卖家处理商品图片，不需要专业摄影就能获得高质量产品图。"
        }
    ],
    "Leonardo AI": [
        {
            "question": "Leonardo AI和Midjourney哪个好？",
            "answer": "Leonardo AI有免费额度（每天150 tokens），支持更多自定义设置和训练自己的模型。Midjourney画质更顶级但纯付费。预算有限选Leonardo AI，追求最佳画质选Midjourney。"
        }
    ],
    "Opus Clip": [
        {
            "question": "Opus Clip能做什么？",
            "answer": "Opus Clip是AI视频剪辑工具，可以自动从长视频中提取精彩片段，生成短视频。AI会分析视频内容，找出最吸引人的片段，自动添加字幕和排版。适合把播客、直播、演讲等长内容变成短视频。"
        }
    ],
    "Descript": [
        {
            "question": "Descript能做什么？",
            "answer": "Descript让视频和音频编辑像编辑文档一样简单。它会自动转录语音为文字，你可以通过编辑文本来剪辑音视频。还支持AI去除填充词（嗯、啊）、自动生成字幕、克隆声音等功能。"
        }
    ],
    "Synthesia": [
        {
            "question": "Synthesia能做什么？",
            "answer": "Synthesia是AI数字人视频制作工具，可以创建专业级的AI讲解视频。输入文字选择一个虚拟人像，AI生成口型匹配的视频。支持140+语言，适合企业培训、营销视频、产品介绍等场景。"
        }
    ],
    "即時設計AI": [
        {
            "question": "即时设计AI是什么？",
            "answer": "即时设计是国产的在线UI设计工具，类似Figma。AI功能可以自动生成UI布局、填充真实内容、智能排版。完全中文界面，国内直连，对国内设计师非常友好。"
        }
    ],
    "稿定设计AI": [
        {
            "question": "稿定设计AI能做什么？",
            "answer": "稿定设计AI集成在国内设计平台稿定设计中，支持AI抠图、AI扩图、AI消除、AI换背景等。模板丰富，特别适合社交媒体图片、电商素材、海报等中国本土设计场景。"
        }
    ],
    "飞书智能助手": [
        {
            "question": "飞书智能助手能做什么？",
            "answer": "飞书智能助手集成在飞书办公平台中，可以AI辅助写文档、总结会议纪要、分析飞书表格、智能搜索飞书知识库等。适合使用飞书的企业团队，AI直接融入日常工作流。"
        }
    ],
    "秘塔AI搜索": [
        {
            "question": "秘塔AI搜索和普通搜索有什么区别？",
            "answer": "秘塔AI搜索直接返回整理好的答案和引用来源，不需要逐个点开网页。支持学术搜索模式，特别适合论文研究和学术写作。无广告、无追踪，注重隐私保护。"
        }
    ],
    "纳米AI搜索": [
        {
            "question": "纳米AI搜索是什么？",
            "answer": "纳米AI搜索是360推出的AI搜索引擎（原360AI搜索升级版）。整合360搜索的中文网页索引，搜索结果中文覆盖面广。完全免费，国内直连，适合中文信息搜索。"
        }
    ],
    "Claude Code": [
        {
            "question": "Claude Code是什么？怎么用？",
            "answer": "Claude Code是Anthropic推出的AI编程助手，运行在终端中。它可以直接读写文件、执行命令、理解整个代码库。和Cursor不同，Claude Code是纯终端工具，适合喜欢命令行的开发者。"
        },
        {
            "question": "Claude Code和Cursor有什么区别？",
            "answer": "Claude Code在终端中运行，直接操作文件系统和git，适合后端和DevOps场景。Cursor是GUI编辑器，可视化更直观，适合前端和全栈开发。两者可以互补使用。"
        }
    ],
    "OpenAI Codex": [
        {
            "question": "OpenAI Codex是什么？",
            "answer": "OpenAI Codex是OpenAI推出的云端AI编程环境。在安全的沙盒中，AI可以编写、运行和调试代码。支持多种语言和框架，适合快速原型开发和代码实验。"
        }
    ],
    "Otter.ai": [
        {
            "question": "Otter.ai能做什么？",
            "answer": "Otter.ai是AI会议记录工具，可以实时转录会议音频为文字，自动生成会议纪要。支持识别不同说话人、生成摘要、分享会议记录。支持Zoom、Google Meet、Teams等主流会议平台的集成。"
        }
    ],
    "Fireflies.ai": [
        {
            "question": "Fireflies.ai和Otter.ai哪个好？",
            "answer": "功能类似。Fireflies.ai在CRM集成（Salesforce、HubSpot）方面更强，适合销售团队。Otter.ai在实时转录和协作方面更好，适合通用场景。两者都提供AI会议纪要功能。"
        }
    ],
    "Speechify": [
        {
            "question": "Speechify能做什么？",
            "answer": "Speechify是AI文字转语音工具，可以将任何文本（文章、PDF、网页）转化为自然的有声读物。支持多种AI声音，包括名人声音（如Snoop Dogg）。适合阅读障碍者、通勤中想'听书'的人。"
        }
    ],
    "Tome": [
        {
            "question": "Tome能做什么？",
            "answer": "Tome是AI演示文稿生成工具，可以快速创建精美的PPT。输入主题，AI自动生成内容、排版和配图。适合快速制作商业提案、产品介绍、故事叙述等演示文稿。"
        }
    ],
    "Arc浏览器": [
        {
            "question": "Arc浏览器有什么特别之处？",
            "answer": "Arc浏览器以创新的界面设计和AI集成著称。Airspaces功能自动整理标签页，Arc Max用AI提升浏览效率（如自动重命名标签、预览链接）。设计美观，适合追求高效浏览体验的用户。"
        }
    ],
    "Remove.bg": [
        {
            "question": "Remove.bg免费吗？",
            "answer": "Remove.bg有免费版，可以处理预览分辨率图片。Pro版$9/月起，可以下载高清原图、批量处理、使用API。电商卖家和设计师建议Pro版，偶尔用用免费版足够。"
        }
    ],
    "LiblibAI": [
        {
            "question": "LiblibAI是什么？",
            "answer": "LiblibAI（哩布哩布AI）是国内最大的AI绘画模型分享和在线生成平台。提供大量中文优化的Stable Diffusion模型、LoRA和素材。支持在线生成，不需要本地部署，对国内用户很友好。"
        }
    ],
    "Copy.ai": [
        {
            "question": "Copy.ai能做什么？",
            "answer": "Copy.ai是AI营销文案工具，可以快速生成各种营销内容：广告文案、邮件、社交媒体帖子、产品描述、博客文章等。提供大量预设模板，填入关键词即可生成专业文案。"
        }
    ],
    "QuillBot": [
        {
            "question": "QuillBot能做什么？",
            "answer": "QuillBot是AI写作辅助工具，核心功能是改写和润色。可以将一段文字改写成不同的语气和风格，还有语法检查、摘要生成、翻译等功能。学生写论文、内容创作者都很适用。"
        }
    ],
    "Writesonic": [
        {
            "question": "Writesonic能做什么？",
            "answer": "Writesonic是AI内容创作平台，可以生成博客文章、广告文案、产品描述、社交媒体内容等。支持SEO优化建议，帮助内容在搜索引擎中排名更好。适合内容营销团队和自媒体创作者。"
        }
    ],
    "Krea AI": [
        {
            "question": "Krea AI有什么特色？",
            "answer": "Krea AI的特色是实时AI画布，可以边画边让AI补全和增强。支持实时生成、风格迁移、高清放大等功能。适合设计师和插画师在创作过程中实时获得AI辅助。"
        }
    ],
    "Freepik AI": [
        {
            "question": "Freepik AI能做什么？",
            "answer": "Freepik是知名设计素材平台，AI功能包括AI图片生成、AI背景替换、AI智能裁剪等。结合Freepik的海量素材库，可以快速创作设计作品。适合需要素材+AI生成结合的设计师。"
        }
    ],
    "Recraft": [
        {
            "question": "Recraft能做什么？",
            "answer": "Recraft是专为设计师打造的AI矢量图生成工具。生成的图片是矢量格式（SVG），可以无损缩放。支持品牌风格一致性，适合logo、图标、插画等专业设计场景。"
        }
    ],
    "Flux": [
        {
            "question": "Flux是什么？",
            "answer": "Flux是Black Forest Labs（Stable Diffusion原始团队成员创立）推出的AI图片生成模型。在文字渲染、人体结构和画面质量方面表现优秀，部分指标超越DALL-E 3和Midjourney。开源版本可免费使用。"
        }
    ],
    "Pixverse": [
        {
            "question": "Pixverse能做什么？",
            "answer": "Pixverse是AI视频生成工具，支持文生视频和图生视频。特色是可以生成一致性较好的角色视频，适合做系列短片、动画角色等。对中国用户的中文prompt支持较好。"
        }
    ],
    "Fliki": [
        {
            "question": "Fliki能做什么？",
            "answer": "Fliki是AI视频制作工具，可以将文字/博客/推文自动转换为短视频。AI自动匹配素材、生成配音和字幕。适合内容创作者快速将文字内容转化为视频，发布到TikTok/YouTube等平台。"
        }
    ],
    "Tensor.Art": [
        {
            "question": "Tensor.Art是什么？",
            "answer": "Tensor.Art是一个在线AI绘画平台，提供大量Stable Diffusion模型和LoRA。特色是社区分享和在线生图，不需要自己部署SD。有免费额度，界面友好，对新手很友好。"
        }
    ],
    "360智脑": [
        {
            "question": "360智脑是什么？",
            "answer": "360智脑是360公司推出的AI助手，整合了360搜索的安全搜索能力。支持AI对话、搜索、文档分析等功能。特色在于网络安全相关的内容和知识，国内直连免费。"
        }
    ],
    "Brandmark": [
        {
            "question": "Brandmark能做什么？",
            "answer": "Brandmark是AI Logo设计工具，输入品牌名称和关键词，AI自动生成多个Logo方案。支持自定义配色和图标，生成多种尺寸和格式。适合创业者和小企业快速设计品牌Logo。"
        }
    ],
    "Make": [
        {
            "question": "Make和Zapier有什么区别？",
            "answer": "功能类似，都是工作流自动化平台。Make的优势是可视化流程更直观、价格更低（免费版1000次操作/月）、支持更复杂的逻辑。Zapier的应用集成更多、使用更简单。技术用户推荐Make。"
        }
    ],
    "Raycast AI": [
        {
            "question": "Raycast AI是什么？",
            "answer": "Raycast是Mac上的效率启动器（替代Spotlight），内置AI功能。可以通过快捷键随时调用AI助手、翻译、生成代码等。适合Mac重度用户提升日常操作效率。"
        }
    ],
    "Beautiful.ai": [
        {
            "question": "Beautiful.ai能做什么？",
            "answer": "Beautiful.ai是AI演示文稿设计工具，自动调整排版和设计，确保每页幻灯片都美观专业。添加内容时AI自动优化布局。适合不会设计的商务人士制作高质量PPT。"
        }
    ],
    "Napkin AI": [
        {
            "question": "Napkin AI能做什么？",
            "answer": "Napkin AI可以将文字内容自动转化为信息图表和可视化图表。输入一段文字，AI生成流程图、思维导图、对比图等可视化内容。适合报告、演示和知识分享。"
        }
    ],
    "Looka": [
        {
            "question": "Looka能做什么？",
            "answer": "Looka是AI品牌设计工具，可以一键生成Logo、品牌色、名片、社交媒体头图等全套品牌视觉方案。输入品牌名称和偏好风格，AI自动生成完整品牌形象。适合创业者快速建立品牌。"
        }
    ],
    "Murf AI": [
        {
            "question": "Murf AI能做什么？",
            "answer": "Murf AI是AI配音工具，提供120+种AI声音，支持多种语言。可以将文字转化为专业配音，适合视频旁白、广告配音、有声读物、产品演示等。声音自然度很高。"
        }
    ],
    "Krisp": [
        {
            "question": "Krisp能做什么？",
            "answer": "Krisp是AI噪音消除工具，可以在通话中实时消除背景噪音（键盘声、狗叫声、交通噪音等）。适用于Zoom、Teams等会议软件。免费版每周120分钟，对远程工作者非常实用。"
        }
    ],
    "Cleanvoice": [
        {
            "question": "Cleanvoice能做什么？",
            "answer": "Cleanvoice是AI音频编辑工具，可以自动去除录音中的填充词（嗯、啊、你知道的）、口水声、长时间的停顿等。适合播客制作者、视频创作者快速清理音频。"
        }
    ],
    "Consensus": [
        {
            "question": "Consensus能做什么？",
            "answer": "Consensus是AI学术搜索引擎，专门搜索和分析学术论文。输入研究问题，AI从论文中提取答案并给出证据级别。帮研究者快速了解学术共识，省去大量阅读论文的时间。"
        }
    ],
    "Phind": [
        {
            "question": "Phind是什么？",
            "answer": "Phind是面向开发者的AI搜索引擎。输入编程问题，AI从技术文档、Stack Overflow等来源搜索并给出带代码示例的回答。比通用搜索引擎对开发者更友好。"
        }
    ],
    "You.com": [
        {
            "question": "You.com是什么？",
            "answer": "You.com是AI搜索引擎，特色是搜索结果中直接展示AI整理的答案，同时保留传统搜索结果。支持选择不同的AI模型（GPT-4、Claude等）来回答问题。注重隐私保护，不追踪用户。"
        }
    ],
    "Comet": [
        {
            "question": "Comet能做什么？",
            "answer": "Comet是AI客户服务工具，用AI自动分析和归类客户反馈。支持整合多个客服渠道（邮件、聊天、社交媒体），AI自动识别客户情绪和问题类型，帮助团队提升服务质量。"
        }
    ],
    "Fathom": [
        {
            "question": "Fathom能做什么？",
            "answer": "Fathom是AI会议助手，自动记录Zoom会议并生成摘要。免费版功能完整，支持自动转录、标记关键决策、生成可分享的会议记录。不需要会议后花时间整理纪要。"
        }
    ],
    "MiniMax": [
        {
            "question": "MiniMax能做什么？",
            "answer": "MiniMax（海螺AI）是中国AI公司推出的产品，特色是AI语音通话和AI角色扮演。可以和AI进行逼真的语音对话，支持创建自定义AI角色。视频生成能力也比较突出。"
        }
    ],
    "Veo": [
        {
            "question": "Veo是什么？",
            "answer": "Veo是Google DeepMind推出的AI视频生成模型，可以生成高质量的1080p视频。支持电影级画质和复杂的镜头运动。目前主要通过Google的AI平台（如VideoFX）体验。"
        }
    ],
    "Supabase AI": [
        {
            "question": "Supabase AI能做什么？",
            "answer": "Supabase是开源的Firebase替代品，AI功能可以辅助数据库设计。用自然语言描述数据需求，AI自动生成数据库表结构和SQL查询。适合全栈开发者快速搭建后端。"
        }
    ],
}

def main():
    with open('data/tools.json', 'r', encoding='utf-8') as f:
        tools = json.load(f)

    updated_count = 0
    not_updated = []

    for tool in tools:
        name = tool['name']
        if name in QUALITY_FAQS:
            faqs = QUALITY_FAQS[name]
            # Ensure faqs is a list
            if isinstance(faqs, dict):
                faqs = [faqs]
            tool['faq'] = faqs
            updated_count += 1
            print(f"  [FAQ] {name}: {len(faqs)} questions")
        else:
            not_updated.append(name)

    with open('data/tools.json', 'w', encoding='utf-8') as f:
        json.dump(tools, f, ensure_ascii=False, indent=4)

    print(f"\n共更新 {updated_count} 个工具的FAQ")
    if not_updated:
        print(f"未更新的工具: {', '.join(not_updated)}")

if __name__ == '__main__':
    main()
