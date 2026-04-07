import os
import re

path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\generate_articles.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 0. Add encoding declaration
if '# -*- coding: utf-8 -*-' not in content:
    content = '# -*- coding: utf-8 -*-\n' + content

# 1. Update ARTICLE_TYPES
article_types_new = '''    'E': {
        'label': 'English Global Content',
        'priority': 0,
        'description': 'English articles for global audience (High Priority for Launch)',
        'keywords_target': 'Global AI trends, ROI, high-intent English keywords',
    },
}'''
content = content.replace('    },' + '\n' + '}', '    },' + '\n' + article_types_new)

# 2. Add PROMPTS_E before ALL_PROMPTS
prompts_e_content = '''
# ================================================================
#  E Category: English Global Content (Outbound strategy)
# ================================================================
PROMPTS_E = [
    {
        "title": "2026 AI Tool ROI Benchmark: 48+ Tools Tested for Real-World Profitability",
        "slug": "2026-ai-tool-roi-benchmark-48-tools-profitability",
        "description": "We rigorously tested 48+ AI tools across content creation, coding, and automation. Here is the definitive ROI report for 2026.",
        "keywords": "AI Tool ROI, best AI tools 2026, profitable AI, AI tools benchmark, AI for business efficiency",
        "category": "Market Trends",
        "prompt": """You are a professional AI industry analyst with a focus on business ROI and practical implementation. Write a high-authority, deep-dive article (2000-3000 words).

Theme: 2026 AI Tool ROI Benchmark: 48+ Tools Tested for Real-World Profitability

Context: It's April 2026. The AI market has shifted from 'hype' to 'utility.' Businesses are cutting subscriptions that don't yield direct returns. We spent 3 months testing 48 tools.

Requirements:
- Categorize tools by: Content Gen, Dev Tools, Automation, and Niche Business Apps.
- Use a 'Hard ROI' vs 'Soft ROI' metric.
- Include a section on 'The 2026 Efficiency Stack.'
- Critical and objective tone. No marketing fluff.

Structure:
## Executive Summary
Summarize the state of AI efficiency in 2026. The era of generic wrappers is over.

## Category 1: Generative Content - Beyond Text
Focus on video and high-fidelity 3D assets. (Sora 2, Kling 3, etc.)

## Category 2: Developer Productivity - The Agentic Shift
Cursor, Windsurf, and the rise of autonomous coding agents.

## Category 3: Business Automation - Connecting the Dots
Make.com, Zapier Central, and multi-agent workflows.

## The ROI Leaderboard (Table)
List top 10 tools with estimated % efficiency gain.

## Conclusion: How to Build Your 2026 AI Strategy
"""
    }
]

'''
if 'ALL_PROMPTS = (' in content:
    content = content.replace('ALL_PROMPTS = (', prompts_e_content + 'ALL_PROMPTS = (')

# 3. Update ALL_PROMPTS
content = content.replace("[(p, 'C') for p in PROMPTS_C]", "[(p, 'C') for p in PROMPTS_C] +\\n    [(p, 'E') for p in PROMPTS_E]")

# 4. Update type_order
content = content.replace("type_order = ['A', 'B', 'C']", "type_order = ['E', 'A', 'B', 'C']")

# 5. Update argparse
content = content.replace("choices=['A', 'B', 'C']", "choices=['A', 'B', 'C', 'E']")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully integrated Type E (English) into generate_articles.py")
