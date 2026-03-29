import json
import os
import random
from datetime import datetime

# 配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
TOOLS_JSON_PATH = os.path.join(DATA_DIR, 'tools.json')

# FAQ 生成配置
FAQ_CATEGORIES = {
    "AI对话": [
        "这个工具是免费的吗？",
        "支持中文对话吗？",
        "和 ChatGPT 相比有什么优势？",
        "支持文件上传吗？",
        "如何提升对话质量？"
    ],
    "AI绘画": [
        "生成的图片可以商用吗？",
        "支持哪些图片风格？",
        "生成的图片有水印吗？",
        "一次能生成多少张图片？",
        "图片生成速度如何？"
    ],
    "AI编程": [
        "支持哪些编程语言？",
        "代码准确率如何？",
        "能集成到 IDE 中吗？",
        "和 GitHub Copilot 相比如何？",
        "适合新手程序员吗？"
    ],
    "AI写作": [
        "能生成多长的文章？",
        "支持哪些写作风格？",
        "生成的内容可以商用吗？",
        "有字数限制吗？",
        "如何提升生成质量？"
    ],
    "AI视频": [
        "生成的视频有水印吗？",
        "能生成长视频吗？",
        "支持哪些视频格式？",
        "视频生成速度如何？",
        "生成的视频可以商用吗？"
    ],
    "AI音频": [
        "支持哪些音频格式？",
        "语音质量如何？",
        "能识别多语种吗？",
        "有使用限制吗？",
        "适合什么场景使用？"
    ],
    "AI办公": [
        "支持哪些文档格式？",
        "能处理多页文档吗？",
        "生成的内容可以商用吗？",
        "有文件大小限制吗？",
        "适合什么办公场景？"
    ],
    "AI设计": [
        "支持哪些设计格式？",
        "有素材库吗？",
        "可以导出源文件吗？",
        "支持团队协作吗？",
        "有设计模板吗？"
    ],
    "AI搜索": [
        "数据更新频率如何？",
        "支持哪些搜索引擎？",
        "搜索结果准确吗？",
        "有广告吗？",
        "适合什么搜索场景？"
    ],
    "AI翻译": [
        "支持哪些语言互译？",
        "翻译准确率如何？",
        "支持文档翻译吗？",
        "有字数限制吗？",
        "能翻译专业术语吗？"
    ],
    "AI自动化": [
        "支持哪些平台？",
        "有使用限制吗？",
        "适合什么自动化场景？",
        "需要编程基础吗？",
        "能定时执行任务吗？"
    ],
    "AI效率": [
        "能提升多少效率？",
        "有学习成本吗？",
        "适合什么行业？",
        "支持团队协作吗？",
        "有数据统计功能吗？"
    ]
}

def generate_faq(tool):
    """为工具生成 FAQ"""
    category = tool.get("category", "AI对话")
    name = tool.get("name", "该工具")
    
    # 根据分类选择对应的问题
    questions = FAQ_CATEGORIES.get(category, FAQ_CATEGORIES["AI对话"])
    
    # 随机选择 3-5 个问题
    num_faq = random.randint(3, min(5, len(questions)))
    selected_questions = random.sample(questions, num_faq)
    
    faq_list = []
    for q in selected_questions:
        # 生成对应答案（基于工具描述生成）
        answer = generate_answer(q, tool)
        faq_list.append({
            "question": q,
            "answer": answer
        })
    
    return faq_list

def generate_answer(question, tool):
    """根据问题生成答案"""
    name = tool.get("name", "该工具")
    description = tool.get("description", "")
    price = tool.get("price", "请查看官网")
    url = tool.get("url", "")
    
    if "免费" in question:
        if "免费" in price or "Free" in price:
            return f"{name} 提供免费版本，部分高级功能可能需要付费。"
        else:
            return f"{name} 的收费方式为 {price}，具体请访问官网 {url} 了解详情。"
    elif "中文" in question:
        return f"{name} 支持中文输入和输出，可以很好地处理中文内容。"
    elif "优势" in question:
        return f"{name} 的主要优势是：{description[:50]}..."
    elif "商用" in question:
        return f"根据 {name} 的使用条款，生成的商业用途请查看官方说明。"
    elif "水印" in question:
        return f"关于水印问题，请查看 {name} 的最新功能介绍。"
    elif "格式" in question:
        return f"{name} 支持多种常见格式，具体请参考官网 {url}。"
    elif "限制" in question:
        return f"{name} 的使用限制请查看官网 {url} 的说明。"
    elif "速度" in question:
        return f"{name} 的处理速度较快，能满足日常使用需求。"
    else:
        return f"关于此问题，建议访问 {name} 官网 {url} 获取最新信息。"

def main():
    print(f"[{datetime.now()}] 开始为工具添加 FAQ...")
    
    # 读取 tools.json
    if not os.path.exists(TOOLS_JSON_PATH):
        print(f"错误: {TOOLS_JSON_PATH} 文件不存在。")
        return
    
    with open(TOOLS_JSON_PATH, 'r', encoding='utf-8') as f:
        tools = json.load(f)
    
    updated_count = 0
    for tool in tools:
        if 'faq' not in tool or not tool.get('faq'):
            # 生成 FAQ
            faq = generate_faq(tool)
            tool['faq'] = faq
            updated_count += 1
            print(f"  - 为 {tool['name']} 生成 {len(faq)} 个 FAQ")
    
    # 保存更新后的数据
    with open(TOOLS_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(tools, f, ensure_ascii=False, indent=4)
    
    print(f"[{datetime.now()}] 已为 {updated_count} 个工具生成 FAQ。")

if __name__ == '__main__':
    main()
