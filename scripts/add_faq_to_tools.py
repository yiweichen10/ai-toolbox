#!/usr/bin/env python3
"""为所有工具添加 FAQ 字段并生成常见问题"""
import json
import os
import random
from datetime import datetime

# 配置路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
TOOLS_JSON_PATH = os.path.join(DATA_DIR, 'tools.json')

# 基础 FAQ 问题库
BASE_QUESTIONS = [
    {
        "question": "{name} 免费吗？",
        "answer": "{name} {price}。通常有免费版，部分高级功能可能需要订阅。"
    },
    {
        "question": "{name} 支持中文吗？",
        "answer": "{name} 支持中文输入和输出，在中文内容处理方面表现优秀。"
    },
    {
        "question": "{name} 和其他工具相比有什么优势？",
        "answer": "{name} 的优势包括：{pros}。这些特点使其在同类型工具中脱颖而出。"
    },
    {
        "question": "如何开始使用 {name}？",
        "answer": "访问 {url} 官网，注册或登录账号即可开始使用 {name}。部分工具可能需要下载客户端。"
    },
    {
        "question": "{name} 适合什么人群使用？",
        "answer": "{name} 适合 {category} 领域的用户，无论新手还是专业人士都可以使用。"
    },
    {
        "question": "{name} 有使用限制吗？",
        "answer": "根据您的使用计划，{name} 可能有使用次数限制或功能限制。免费版通常有限制。"
    },
    {
        "question": "{name} 支持哪些平台？",
        "answer": "{name} 支持的平台包括：{platform}。"
    },
    {
        "question": "{name} 的数据安全吗？",
        "answer": "{name} 非常重视数据安全，采用加密技术保护用户数据。请仔细阅读其隐私政策。"
    },
    {
        "question": "{name} 能否离线使用？",
        "answer": "大部分 {category} 工具需要联网使用，部分功能可能支持离线。具体请查看官网说明。"
    },
    {
        "question": "{name} 有什么使用技巧？",
        "answer": "{name} 的使用技巧包括：善于使用提示词、合理配置参数、多实践探索功能等。"
    }
]

# 分类特有问题（如果有的话）
CATEGORY_SPECIFIC_QUESTIONS = {
    "AI对话": [
        {
            "question": "{name} 会记住历史对话吗？",
            "answer": "{name} 通常会记住当前会话的历史对话，但关闭窗口后可能不会保存。"
        },
        {
            "question": "{name} 有什么对话技巧？",
            "answer": "使用清晰、具体的提示词，分解复杂问题，提供足够的背景信息。"
        }
    ],
    "AI绘画": [
        {
            "question": "{name} 生成的图片可以商用吗？",
            "answer": "这取决于 {name} 的使用条款。通常付费用户可以商用，免费版可能有限制。"
        },
        {
            "question": "{name} 支持哪些图片风格？",
            "answer": "{name} 支持多种艺术风格，如写实、卡通、油画、素描等。"
        }
    ],
    "AI编程": [
        {
            "question": "{name} 支持哪些编程语言？",
            "answer": "{name} 支持多种主流编程语言，如 Python、JavaScript、Java、C++ 等。"
        },
        {
            "question": "{name} 能集成到 IDE 吗？",
            "answer": "{name} 通常提供插件，可以集成到 VS Code、JetBrains 等主流 IDE 中。"
        }
    ],
    "AI写作": [
        {
            "question": "{name} 生成的内容可以商用吗？",
            "answer": "{name} 生成的内容通常可以商用，但建议人工审核并修改。具体请参考使用条款。"
        },
        {
            "question": "{name} 支持哪些写作类型？",
            "answer": "{name} 支持多种写作类型，包括文章、邮件、广告文案、社交媒体内容等。"
        }
    ]
}

def generate_faq_for_tool(tool):
    """为单个工具生成 3-5 个 FAQ"""
    faqs = []
    
    # 获取工具基本信息
    name = tool.get('name', '该工具')
    price = tool.get('price', '提供免费版本，部分功能需要订阅')
    category = tool.get('category', '')
    platform = tool.get('platform', 'Web / iOS / Android / 桌面应用')
    url = tool.get('url', '官方网站')
    pros = ', '.join(tool.get('pros', [])[:3])  # 取前3个优点
    
    # 构建基础问题和答案
    question_pool = []
    
    # 添加基础问题（随机选择）
    random.shuffle(BASE_QUESTIONS)
    for q in BASE_QUESTIONS[:5]:  # 先从基础问题中选5个候选
        question_pool.append(q)
    
    # 添加分类特有问题（如果有）
    if category in CATEGORY_SPECIFIC_QUESTIONS:
        category_questions = CATEGORY_SPECIFIC_QUESTIONS[category]
        random.shuffle(category_questions)
        question_pool.extend(category_questions)
    
    # 随机选择 3-5 个最终问题
    random.shuffle(question_pool)
    selected_questions = question_pool[:random.randint(3, 5)]
    
    # 填充实际内容
    for q in selected_questions:
        question = q['question'].format(name=name)
        answer = q['answer'].format(
            name=name,
            price=price,
            category=category,
            platform=platform,
            url=url,
            pros=pros
        )
        faqs.append({
            "question": question,
            "answer": answer
        })
    
    return faqs

def main():
    print(f"[{datetime.now()}] 开始为工具添加 FAQ 功能...")
    
    # 检查文件是否存在
    if not os.path.exists(TOOLS_JSON_PATH):
        print(f"错误: {TOOLS_JSON_PATH} 文件不存在。")
        return
    
    # 读取 tools.json
    with open(TOOLS_JSON_PATH, 'r', encoding='utf-8') as f:
        tools = json.load(f)
    
    if not isinstance(tools, list):
        print(f"错误: tools.json 格式不正确，期望是数组。")
        return
    
    print(f"读取到 {len(tools)} 个工具")
    
    # 为每个工具生成 FAQ
    updated_count = 0
    for tool in tools:
        # 检查是否已有 FAQ 字段
        if 'faq' not in tool:
            faqs = generate_faq_for_tool(tool)
            tool['faq'] = faqs
            updated_count += 1
            print(f"  - 为 {tool.get('name', 'Unknown')} 生成 {len(faqs)} 个 FAQ")
    
    # 写回文件
    with open(TOOLS_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(tools, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 已为 {updated_count} 个工具添加 FAQ 字段（共 {len(tools)} 个工具）")
    print(f"[{datetime.now()}] FAQ 添加任务完成。")

if __name__ == '__main__':
    main()
