#!/usr/bin/env python3
"""为工具生成高质量的 FAQ（基于真实搜索需求）"""
import json
import os
import random
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
TOOLS_JSON_PATH = os.path.join(DATA_DIR, 'tools.json')

def generate_intelligent_faq(tool):
    """基于工具特点生成高质量的 FAQ"""
    name = tool.get('name', '')
    category = tool.get('category', '')
    price = tool.get('price', '')
    platform = tool.get('platform', '')
    pros = tool.get('pros', [])
    features = tool.get('features', [])
    description = tool.get('description', '')
    
    faqs = []
    
    # 1. 价格和性价比分析（针对不同价格策略）
    if '免费' in price or 'free' in price.lower():
        faqs.append({
            "question": f"{name} 是免费的吗？有哪些付费功能？",
            "answer": f"{name} 提供免费版本，{price}。付费版通常解锁更多功能、提升使用限制或提供高级服务。建议先试用免费版，根据实际需求决定是否升级。"
        })
    elif '$' in price or '¥' in price or '元' in price:
        faqs.append({
            "question": f"{name} 值得付费吗？和免费工具相比有什么优势？",
            "answer": f"{name} 价格为 {price}。相比免费工具，它的主要优势包括：{'、'.join(pros[:3])}。如果你是重度用户或对输出质量要求高，付费版本通常能带来更好的体验和效率。"
        })
    
    # 2. 功能对比和使用场景（基于分类）
    if category == "AI对话":
        faqs.append({
            "question": f"{name} 和 ChatGPT/Claude 有什么区别？什么时候用它更好？",
            "answer": f"{description}。相比通用型助手，{name} 在{'、'.join(features[:2])}方面可能有特色功能。如果你的需求集中在这些领域，或者需要{'、'.join(pros[:2])}，{name} 可能更适合。"
        })
    elif category == "AI绘画":
        faqs.append({
            "question": f"{name} 生成的图片质量如何？什么情况下选择它而不是 Midjourney？",
            "answer": f"{name} {description}。如果你重视{'、'.join(features[:2])}，或者需要{'、'.join(pros[:2])}，可以考虑选择它。不同的工具在不同风格、不同场景下表现不同，建议多对比测试。"
        })
    elif category == "AI编程":
        faqs.append({
            "question": f"{name} 能替代 GitHub Copilot 吗？在什么场景下更合适？",
            "answer": f"{name} {description}。相比 GitHub Copilot，它在{'、'.join(pros[:2])}方面可能有优势。如果你主要开发{'、'.join(features[:2])}相关的项目，或者需要{pros[0] if pros else '更灵活的代码生成'}，可以试试 {name}。"
        })
    elif category == "AI视频":
        faqs.append({
            "question": f"{name} 生成的视频可以商用吗？版权方面有什么限制？",
            "answer": f"关于版权，{name} 的具体政策请查看官网的使用条款。一般来说，付费用户通常享有更宽松的使用权限，但不同平台对商用、分发的限制不同。建议在商用前仔细阅读条款，或联系客服确认。"
        })
    
    # 3. 实用技巧（基于功能特点）
    if 'prompt' in description.lower() or '提示词' in description:
        faqs.append({
            "question": f"使用 {name} 时有什么提示词技巧？",
            "answer": f"使用 {name} 时，建议：1）使用清晰、具体的描述，避免模糊表达；2）提供足够的背景信息和上下文；3）通过迭代优化逐步接近想要的结果；4）参考官方提供的示例或最佳实践。"
        })
    
    if pros and any('速度' in p or '快' in p for p in pros):
        faqs.append({
            "question": f"{name} 的生成速度如何？如何提高效率？",
            "answer": f"{name} 在生成速度方面表现不错（{pros[0] if pros else ''}）。为了提高效率，建议：1）选择合适的输出质量和尺寸；2）批量处理相似任务；3）提前准备好素材和文案。"
        })
    
    # 4. 平台和兼容性（实用问题）
    if 'Windows' in platform or 'Mac' in platform or '桌面' in platform:
        faqs.append({
            "question": f"{name} 支持哪些操作系统？在手机上能用吗？",
            "answer": f"{name} 支持的平台：{platform}。具体来说，桌面端可以在 Windows/Mac/Linux 上使用，移动端可能需要通过网页版或专用 App。建议访问官网确认最新支持的平台和系统版本。"
        })
    
    # 5. 数据安全和隐私（重要问题）
    faqs.append({
        "question": f"{name} 会保存我的数据吗？数据安全有保障吗？",
        "answer": f"数据安全是 AI 工具的重要考量。{name} 通常会收集使用数据用于模型训练和服务改进（具体政策请查看隐私条款）。如果处理敏感信息，建议：1）了解其数据存储和处理方式；2）必要时使用隐私模式或本地部署版本；3）遵守数据保护法规。"
    })
    
    # 6. 适用人群和场景（帮助用户判断）
    faqs.append({
        "question": f"{name} 适合什么人使用？新手也能上手吗？",
        "answer": f"{description}。它适合：1）{'、'.join(features[:2])}相关从业者；2）需要{'、'.join(pros[:2])}的用户；3）想提高{category}效率的个人或团队。对于新手，建议先从官方教程和示例入手，逐步探索功能。"
    })
    
    # 返回前 3-5 个 FAQ
    random.shuffle(faqs)
    return faqs[:random.randint(3, 5)]

def main():
    print(f"[{datetime.now()}] 开始重新生成高质量 FAQ...")
    
    with open(TOOLS_JSON_PATH, 'r', encoding='utf-8') as f:
        tools = json.load(f)
    
    # 只为已发布的工具生成 FAQ
    published_tools = [t for t in tools if t.get('published', False)]
    print(f"将为 {len(published_tools)} 个已发布工具生成高质量 FAQ")
    
    for tool in published_tools:
        faqs = generate_intelligent_faq(tool)
        tool['faq'] = faqs
        print(f"  - {tool['name']}: {len(faqs)} 个 FAQ")
    
    with open(TOOLS_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(tools, f, ensure_ascii=False, indent=4)
    
    print(f"[OK] 已完成 {len(published_tools)} 个工具的 FAQ 生成")
    print(f"下一步：运行 python build.py 重新生成页面")

if __name__ == '__main__':
    main()
