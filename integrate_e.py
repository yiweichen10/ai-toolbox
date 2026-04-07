import os

path = r'C:\Users\27040\WorkBuddy\20260321092139\seo-site\generate_articles.py'
with open(path, 'rb') as f:
    content = f.read()

# 1. Add PROMPTS_E before ALL_PROMPTS
prompts_e_text = u'''
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
        "lang": "en",
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
'''.encode('utf-8')

all_prompts_marker = b'ALL_PROMPTS = ('
if all_prompts_marker in content:
    content = content.replace(all_prompts_marker, prompts_e_text + b'\nALL_PROMPTS = (')

# 2. Update ALL_PROMPTS content
old_all_prompts_end = b"[(p, 'C') for p in PROMPTS_C]"
new_all_prompts_end = b"[(p, 'C') for p in PROMPTS_C] +\n    [(p, 'E') for p in PROMPTS_E]"
content = content.replace(old_all_prompts_end, new_all_prompts_end)

# 3. Update type_order in select_next_article
old_type_order = b"type_order = ['A', 'B', 'C']"
new_type_order = b"type_order = ['E', 'A', 'B', 'C']" # English first for now
content = content.replace(old_type_order, new_type_order)

# 4. Update argparse choices in main
old_choices = b"choices=['A', 'B', 'C']"
new_choices = b"choices=['A', 'B', 'C', 'E']"
content = content.replace(old_choices, new_choices)

with open(path, 'wb') as f:
    f.write(content)

print("Successfully integrated Type E (English) logic and prompts into generate_articles.py")
