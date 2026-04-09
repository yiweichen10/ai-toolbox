#!/usr/bin/env python3
"""
gen_en_articles.py — Generate 20 native English SEO articles for aitoolbox.hk/en
Uses SiliconFlow DeepSeek-V3 API. Supports resume on failure.
"""

import json
import requests
import time
import os
import re
import random
from datetime import date

# ─── Config ───────────────────────────────────────────────────────────
API_KEY = "sk-necmvkjjvnysmuelonjjdkwzrmepuqtempxyghojejkvqzne"
BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL = "Pro/deepseek-ai/DeepSeek-V3.2"
MAX_TOKENS = 8000
DELAY_MIN = 5
DELAY_MAX = 10
MAX_RETRIES = 3
API_TIMEOUT = 300
PROGRESS_FILE = "data/_en_articles_progress.json"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_FILE = os.path.join(BASE_DIR, "data", "articles_en.json")
TOOLS_FILE = os.path.join(BASE_DIR, "data", "tools_en.json")
PROGRESS_PATH = os.path.join(BASE_DIR, PROGRESS_FILE)

# ─── 20 article topics from keyword strategy ─────────────────────────
ARTICLE_TOPICS = [
    {
        "title": "Best AI Tools for Students: 20+ Tools You Actually Need in 2026",
        "slug": "best-ai-tools-for-students-2026",
        "category": "AI Tools",
        "keywords": "AI tools for students, best AI for students, student AI tools, AI for college",
        "target_word_count": 2000,
        "description": "Discover the best AI tools for students in 2026. From essay writing to math solving, we tested 20+ tools that actually help students save time and boost grades.",
    },
    {
        "title": "Free AI Image Generators With No Watermark (Tested & Ranked 2026)",
        "slug": "free-ai-image-generators-no-watermark",
        "category": "AI Image",
        "keywords": "free AI image generator no watermark, AI art generator free, best free AI art",
        "target_word_count": 1800,
        "description": "Tired of watermarked AI images? We tested 15+ free AI image generators and ranked the best ones with no watermark. See real examples and comparisons.",
    },
    {
        "title": "20 Best Free ChatGPT Alternatives in 2026 (No Credit Card)",
        "slug": "best-free-chatgpt-alternatives-2026",
        "category": "AI Chat",
        "keywords": "free ChatGPT alternatives, ChatGPT alternative free, AI chatbot free, best AI chat",
        "target_word_count": 2200,
        "description": "Looking for free ChatGPT alternatives? We compared 20 AI chatbots with free tiers — no credit card required. Find the best alternative for your needs.",
    },
    {
        "title": "AI Tools for Small Business: The Complete 2026 Guide",
        "slug": "ai-tools-for-small-business-2026",
        "category": "AI Tools",
        "keywords": "AI tools for small business, small business AI, AI for entrepreneurs, business AI tools",
        "target_word_count": 2000,
        "description": "The ultimate guide to AI tools for small business in 2026. Learn which tools save time, cut costs, and help you compete with bigger companies.",
    },
    {
        "title": "Best AI Tools for Beginners: Where to Start in 2026",
        "slug": "best-ai-tools-for-beginners-2026",
        "category": "AI Tools",
        "keywords": "AI tools for beginners, best AI for beginners, easy AI tools, start using AI",
        "target_word_count": 1800,
        "description": "New to AI? This beginner-friendly guide covers the easiest AI tools to start using today. No tech skills required — just practical tools that save time.",
    },
    {
        "title": "Free Midjourney Alternatives That Actually Work (2026)",
        "slug": "free-midjourney-alternatives-2026",
        "category": "AI Image",
        "keywords": "free Midjourney alternative, Midjourney free alternative, AI art tool free, image generator like Midjourney",
        "target_word_count": 1800,
        "description": "Can't afford Midjourney? These 10 free alternatives produce stunning AI art. We compared quality, speed, and features side by side with real examples.",
    },
    {
        "title": "AI Tools for Content Creators: Save 10+ Hours Per Week",
        "slug": "ai-tools-for-content-creators-2026",
        "category": "AI Tools",
        "keywords": "AI tools for content creators, content creator AI, AI for YouTubers, AI for creators",
        "target_word_count": 2000,
        "description": "Content creators are using AI to work smarter, not harder. Discover the AI tools that help YouTubers, bloggers, and social media creators save 10+ hours weekly.",
    },
    {
        "title": "Best AI Writing Tools Compared: Grammarly vs Jasper vs Writesonic (2026)",
        "slug": "ai-writing-tools-compared-2026",
        "category": "AI Writing",
        "keywords": "AI writing tools compared, Grammarly vs Jasper, best AI writing tool, AI writing assistant",
        "target_word_count": 2000,
        "description": "Grammarly vs Jasper vs Writesonic — which AI writing tool is best in 2026? We compared features, pricing, output quality, and real-world use cases.",
    },
    {
        "title": "AI Productivity Tools: Build Your Ultimate 2026 Workflow",
        "slug": "ai-productivity-tools-2026-workflow",
        "category": "AI Productivity",
        "keywords": "AI productivity tools, AI workflow, productivity AI, best AI for productivity",
        "target_word_count": 2000,
        "description": "Build a complete AI-powered productivity workflow in 2026. We show you which tools to combine for maximum efficiency at work and in daily life.",
    },
    {
        "title": "Best Free AI Video Generators in 2026 (Ranked & Tested)",
        "slug": "best-free-ai-video-generators-2026",
        "category": "AI Video",
        "keywords": "free AI video generator, AI video maker free, best AI video tool, text to video AI free",
        "target_word_count": 1800,
        "description": "Want to create videos with AI for free? We tested 12+ AI video generators and ranked the best ones. See real output examples and compare features.",
    },
    {
        "title": "AI Tools for Teachers: Automate Grading, Lesson Plans & More",
        "slug": "ai-tools-for-teachers-2026",
        "category": "AI Tools",
        "keywords": "AI tools for teachers, AI for education, teacher AI tools, AI grading tools",
        "target_word_count": 1800,
        "description": "Teachers are using AI to save hours on grading, lesson planning, and admin work. Discover the best AI tools for educators in 2026.",
    },
    {
        "title": "Best AI Coding Assistants Compared (2026): Cursor vs Copilot vs Claude Code",
        "slug": "best-ai-coding-assistants-2026",
        "category": "AI Coding",
        "keywords": "AI coding assistant, best AI for coding, Cursor vs Copilot, AI code generator",
        "target_word_count": 2200,
        "description": "Which AI coding assistant is best in 2026? We compared Cursor, GitHub Copilot, Claude Code, and more on speed, accuracy, and real coding tasks.",
    },
    {
        "title": "Free AI Tools No Sign Up Required (Instant Access 2026)",
        "slug": "free-ai-tools-no-sign-up-2026",
        "category": "AI Tools",
        "keywords": "free AI tools no sign up, AI tools no registration, instant AI tools, use AI without account",
        "target_word_count": 1800,
        "description": "No time to create accounts? These 15+ AI tools work instantly with no sign up required. Just open and start using them right away.",
    },
    {
        "title": "AI Tools for Marketers: The Complete 2026 Toolkit",
        "slug": "ai-tools-for-marketers-2026",
        "category": "AI Tools",
        "keywords": "AI tools for marketers, marketing AI tools, AI for marketing, digital marketing AI",
        "target_word_count": 2000,
        "description": "The complete AI toolkit for marketers in 2026. From copywriting to SEO to ad optimization — discover which tools give you the biggest competitive edge.",
    },
    {
        "title": "ChatGPT vs Gemini vs Claude: Which AI Chatbot Is Best in 2026?",
        "slug": "chatgpt-vs-gemini-vs-claude-2026",
        "category": "AI Chat",
        "keywords": "ChatGPT vs Gemini vs Claude, best AI chatbot 2026, AI chatbot comparison, which AI is best",
        "target_word_count": 2200,
        "description": "ChatGPT, Gemini, or Claude? We put the three biggest AI chatbots head to head in writing, coding, research, and reasoning. See which one wins.",
    },
    {
        "title": "Best AI Presentation Tools for 2026: Create Slides in Minutes",
        "slug": "best-ai-presentation-tools-2026",
        "category": "AI Office",
        "keywords": "AI presentation tool, AI slide maker, AI PowerPoint, create slides with AI",
        "target_word_count": 1600,
        "description": "Create professional presentations in minutes with AI. We compared the best AI slide makers — from Gamma to Beautiful.ai to Canva AI.",
    },
    {
        "title": "AI Resume Builders: Create a Professional Resume in Minutes",
        "slug": "ai-resume-builders-2026",
        "category": "AI Tools",
        "keywords": "AI resume builder, resume AI tool, AI resume maker, create resume with AI",
        "target_word_count": 1500,
        "description": "Need a resume fast? These AI resume builders create professional, ATS-friendly resumes in minutes. We tested the best ones for 2026.",
    },
    {
        "title": "Best AI Voice Generators & Text to Speech Tools (2026)",
        "slug": "best-ai-voice-generators-tts-2026",
        "category": "AI Audio",
        "keywords": "AI voice generator, text to speech AI, best TTS, AI voice maker, realistic AI voice",
        "target_word_count": 1800,
        "description": "From ElevenLabs to Speechify, we compared the best AI voice generators and text to speech tools. Hear real samples and find the best one for your needs.",
    },
    {
        "title": "AI Tools for Real Estate Agents: Close More Deals in 2026",
        "slug": "ai-tools-for-real-estate-agents-2026",
        "category": "AI Tools",
        "keywords": "AI tools for real estate, real estate AI, AI for realtors, property AI tools",
        "target_word_count": 1600,
        "description": "Real estate agents using AI close more deals. Discover the AI tools that help with listing descriptions, virtual staging, lead generation, and client communication.",
    },
    {
        "title": "Best AI Translation Tools Compared (2026): DeepL vs Google vs More",
        "slug": "best-ai-translation-tools-2026",
        "category": "AI Translation",
        "keywords": "AI translation tool, best AI translator, DeepL vs Google Translate, AI translation compared",
        "target_word_count": 1800,
        "description": "Which AI translation tool is most accurate? We tested DeepL, Google Translate, and other AI translators with real texts in 10+ languages.",
    },
]


def call_api(system_prompt, user_prompt, max_retries=MAX_RETRIES):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.7,
        "top_p": 0.9
    }
    for attempt in range(max_retries):
        try:
            resp = requests.post(BASE_URL, headers=headers, json=payload, timeout=API_TIMEOUT)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            print(f"  Timeout (attempt {attempt+1}/{max_retries}), retrying in {15*(attempt+1)}s...")
            if attempt < max_retries - 1:
                time.sleep(15 * (attempt + 1))
        except requests.exceptions.ConnectionError as e:
            print(f"  Connection error (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(20 * (attempt + 1))
        except Exception as e:
            print(f"  API error (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(15 * (attempt + 1))
    return None


def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def load_tools():
    """Load tools_en.json for cross-referencing."""
    if os.path.exists(TOOLS_FILE):
        with open(TOOLS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def generate_article(topic, tools):
    """Generate a full SEO article."""
    system_prompt = """You are an expert tech writer and SEO content specialist writing for an AI tools directory website (aitoolbox.hk). You write native, professional English content that is informative, engaging, and optimized for search engines without being spammy.

Your articles follow these rules:
- Hook the reader in the first paragraph with a relatable problem or surprising fact
- Use specific data, real tool names, and concrete examples (never vague)
- Include at least 3-5 internal link opportunities (mention tool names that could link to tool pages)
- End with a clear conclusion and call to action
- Write in a conversational but authoritative tone
- NEVER translate from Chinese — all content is originally written in English"""

    # Build tool context for cross-referencing
    tool_context = ""
    relevant_tools = []
    topic_lower = topic["title"].lower()
    for t in tools:
        name = t.get("name", "")
        cat = t.get("category", "")
        desc = t.get("description", "")
        if any(kw.lower() in topic_lower or kw.lower() in cat.lower() for kw in name.split()):
            relevant_tools.append(f"- {name} ({cat}): {desc[:80]}")
    if relevant_tools:
        tool_context = f"\n\n**Available tools on our site to reference** (use naturally in the article):\n" + "\n".join(relevant_tools[:15])

    user_prompt = f"""Write a comprehensive SEO article with the following specifications:

**Title**: {topic['title']}
**Target word count**: {topic['target_word_count']}+ words
**Meta description**: {topic['description']}
**Target keywords**: {topic['keywords']}

{tool_context}

**Article structure requirements**:

## Introduction (150-200 words)
- Start with a hook (surprising stat, relatable problem, or trend)
- State what the reader will learn
- Include the primary keyword naturally

## Main Body (use 5-8 H2 sections, each 150-300 words)
- Cover the topic comprehensively with specific tools, features, and comparisons
- Include numbered lists, comparison tables where relevant
- Mention specific pricing, features, and real use cases
- Naturally reference tools from our site where appropriate
- Include practical tips and actionable advice

## Comparison Section (if applicable)
- Create a comparison table or structured comparison
- Highlight pros/cons of each option

## FAQ Section (3-5 questions)
- Anticipate reader questions
- Provide concise, helpful answers (40-80 words each)

## Conclusion (100-150 words)
- Summarize key takeaways
- Clear recommendation or next step
- Call to action

**Critical rules**:
1. Write in NATIVE English — never translate
2. Target {topic['target_word_count']}+ words minimum
3. Include primary keyword in first 100 words, naturally throughout
4. Use Markdown formatting (## for H2, ### for H3, - for lists, | for tables)
5. Be specific — real prices, real features, real comparisons
6. Conversational but authoritative tone

Return ONLY the article content in Markdown format. No JSON, no metadata, no explanation."""

    raw = call_api(system_prompt, user_prompt)
    return raw


def load_progress():
    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed": [], "failed": []}


def save_progress(progress):
    with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=0, help="Batch index (0=all, 1=first 5, 2=next 5, etc.)")
    parser.add_argument("--size", type=int, default=5, help="Batch size (default: 5)")
    args = parser.parse_args()

    print("=" * 60)
    print("gen_en_articles.py — English Article Generator")
    print("=" * 60)

    # Load existing articles
    if os.path.exists(ARTICLES_FILE):
        with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
            articles = json.load(f)
        print(f"Loaded {len(articles)} existing articles")
    else:
        articles = []

    existing_slugs = {a["slug"] for a in articles}

    # Load tools for cross-referencing
    tools = load_tools()
    print(f"Loaded {len(tools)} tools for cross-referencing")

    # Load progress
    progress = load_progress()
    completed_slugs = set(progress["completed"])
    print(f"Already completed: {len(completed_slugs)} articles")

    # Find pending articles
    pending = []
    for topic in ARTICLE_TOPICS:
        slug = topic["slug"]
        if slug in completed_slugs or slug in existing_slugs:
            continue
        pending.append(topic)

    if not pending:
        print("\nAll articles already generated!")
        return

    # Apply batch filter
    if args.batch > 0:
        start = (args.batch - 1) * args.size
        end = start + args.size
        pending = pending[start:end]
        print(f"Batch {args.batch}: articles {start+1}-{start+len(pending)}")

    print(f"Pending: {len(pending)} articles to generate\n")

    today = date.today()
    success_count = 0
    fail_count = 0

    for idx, topic in enumerate(pending):
        slug = topic["slug"]
        print(f"[{idx+1}/{len(pending)}] Generating: {topic['title'][:60]}...")

        content = generate_article(topic, tools)

        if content and len(content.split()) > 300:
            article = {
                "title": topic["title"],
                "slug": slug,
                "date": today.strftime("%Y-%m-%d"),
                "dateFull": today.strftime("%B %d, %Y"),
                "category": topic["category"],
                "description": topic["description"],
                "keywords": topic["keywords"],
                "content": content,
            }
            articles.append(article)

            # Save after each article
            with open(ARTICLES_FILE, "w", encoding="utf-8") as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)

            progress["completed"].append(slug)
            save_progress(progress)

            word_count = len(content.split())
            success_count += 1
            print(f"  OK! {word_count} words ({success_count} done, {len(pending)-idx-1} remaining)")
        else:
            progress["failed"].append(slug)
            save_progress(progress)
            fail_count += 1
            print(f"  FAILED ({fail_count} failures)")

        if idx < len(pending) - 1:
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            print(f"  Waiting {delay:.1f}s...")
            time.sleep(delay)

    # Summary
    print("\n" + "=" * 60)
    print(f"Generation complete!")
    print(f"  Success: {success_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Total articles: {len(articles)}")

    if progress["failed"]:
        print(f"\nFailed: {progress['failed']}")

    # Word count stats
    for a in articles[-min(len(articles), success_count):]:
        wc = len(a.get("content", "").split())
        print(f"  {a['slug']}: {wc} words")

    print("=" * 60)


if __name__ == "__main__":
    main()
