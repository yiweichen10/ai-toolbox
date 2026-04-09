#!/usr/bin/env python3
"""
enhance_en_content.py — Enhance tool content from ~370 words to 800+ words
Uses SiliconFlow DeepSeek-V3 API. Supports resume on failure.
"""

import json
import requests
import time
import os
import re
import random

# ─── Config ───────────────────────────────────────────────────────────
API_KEY = "sk-necmvkjjvnysmuelonjjdkwzrmepuqtempxyghojejkvqzne"
BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL = "Pro/deepseek-ai/DeepSeek-V3.2"
MAX_TOKENS = 5000
DELAY_MIN = 5
DELAY_MAX = 10
MAX_RETRIES = 3
API_TIMEOUT = 300
PROGRESS_FILE = "data/_en_enhance_progress.json"
MIN_WORDS = 700

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_FILE = os.path.join(BASE_DIR, "data", "tools_en.json")
PROGRESS_PATH = os.path.join(BASE_DIR, PROGRESS_FILE)


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


def enhance_content(tool):
    """Take existing tool content and enhance it to 800+ words."""
    name = tool["name"]
    existing_content = tool.get("content", "")
    existing_faq = tool.get("faq", [])
    url = tool.get("url", "")
    price = tool.get("price", "")
    category = tool.get("category", "")

    system_prompt = """You are an expert tech writer and SEO content specialist for an AI tools directory (aitoolbox.hk). You enhance existing tool reviews to be more comprehensive and SEO-optimized. You write native, professional English. You NEVER translate from Chinese."""

    faq_text = ""
    for item in existing_faq:
        if isinstance(item, dict):
            faq_text += f"Q: {item.get('q','')}\nA: {item.get('a','')}\n\n"

    user_prompt = f"""Enhance the following AI tool review for "{name}" from {len(existing_content.split())} words to 800-1200 words.

**Tool Info:**
- Name: {name}
- Category: {category}
- Website: {url}
- Pricing: {price}

**EXISTING CONTENT (enhance and expand this — keep all good parts, add more depth):**
{existing_content}

**EXISTING FAQ:**
{faq_text}

**Requirements for enhanced content:**
1. Keep the same Markdown structure (## headings)
2. Significantly expand each section with more specific details:
   - What Is section: add more context about the company, founding story, target users
   - Key Features: expand to 6-8 features with detailed explanations
   - Add a new "How to Use {name}" section with step-by-step guidance
   - Pricing: add more details about each plan, free tier specifics, annual vs monthly
   - Pros & Cons: expand each point with specific examples
   - Add "{name} vs Alternatives" section comparing with 2-3 competitors
   - Add "Who Should Use {name}" section
   - Verdict: make more detailed
3. Include relevant long-tail keywords naturally (e.g., "free alternative to {name}", "{name} for [use case]")
4. Target: 800-1200 words total
5. Keep all Markdown formatting (##, ###, -, **, etc.)

Return ONLY the enhanced Markdown content. No JSON, no explanation, no wrapper."""

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
    print("enhance_en_content.py — Tool Content Enhancer")
    print("=" * 60)

    with open(TOOLS_FILE, "r", encoding="utf-8") as f:
        tools = json.load(f)
    print(f"Loaded {len(tools)} tools")

    progress = load_progress()
    completed_set = set(progress["completed"])
    print(f"Already enhanced: {len(completed_set)}")

    # Find tools that need enhancement
    pending = []
    for i, tool in enumerate(tools):
        name = tool["name"]
        if name in completed_set:
            continue
        content = tool.get("content", "")
        word_count = len(content.split()) if content else 0
        if word_count < MIN_WORDS:
            pending.append((i, tool, word_count))

    if not pending:
        print("\nAll tools already have 700+ words!")
        return

    # Apply batch filter
    if args.batch > 0:
        start = (args.batch - 1) * args.size
        end = start + args.size
        pending = pending[start:end]
        print(f"Batch {args.batch}: tools {start+1}-{start+len(pending)}")

    print(f"Pending: {len(pending)} tools below {MIN_WORDS} words\n")

    success_count = 0
    fail_count = 0

    for idx, (i, tool, old_wc) in enumerate(pending):
        name = tool["name"]
        print(f"[{idx+1}/{len(pending)}] Enhancing: {name} ({old_wc} words -> 800+)")

        enhanced = enhance_content(tool)

        if enhanced and len(enhanced.split()) >= 500:
            tools[i]["content"] = enhanced
            new_wc = len(enhanced.split())

            # Save after each tool
            with open(TOOLS_FILE, "w", encoding="utf-8") as f:
                json.dump(tools, f, ensure_ascii=False, indent=2)

            progress["completed"].append(name)
            save_progress(progress)

            success_count += 1
            print(f"  OK! {old_wc} -> {new_wc} words ({success_count} done)")
        else:
            progress["failed"].append(name)
            save_progress(progress)
            fail_count += 1
            print(f"  FAILED ({fail_count} failures)")

        if idx < len(pending) - 1:
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            print(f"  Waiting {delay:.1f}s...")
            time.sleep(delay)

    # Summary
    print("\n" + "=" * 60)
    print(f"Enhancement complete!")
    print(f"  Enhanced: {success_count}")
    print(f"  Failed: {fail_count}")

    # Final stats
    with open(TOOLS_FILE, "r", encoding="utf-8") as f:
        tools = json.load(f)
    words = [len(t.get("content", "").split()) for t in tools]
    print(f"\nContent word count stats:")
    print(f"  Min: {min(words)}, Max: {max(words)}, Avg: {sum(words)//len(words)}")
    print(f"  <500: {sum(1 for w in words if w<500)}")
    print(f"  500-700: {sum(1 for w in words if 500<=w<700)}")
    print(f"  700-1000: {sum(1 for w in words if 700<=w<1000)}")
    print(f"  >1000: {sum(1 for w in words if w>=1000)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
