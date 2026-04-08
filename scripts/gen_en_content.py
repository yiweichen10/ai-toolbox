#!/usr/bin/env python3
"""
gen_en_content.py — Batch generate native English SEO content for tools_en.json
Uses SiliconFlow DeepSeek-V3 API. Supports resume on failure.
"""

import json
import requests
import time
import os
import sys
import re

# ─── Config ───────────────────────────────────────────────────────────
API_KEY = "sk-necmvkjjvnysmuelonjjdkwzrmepuqtempxyghojejkvqzne"
BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL = "deepseek-ai/DeepSeek-V3"
MAX_TOKENS = 4096
REQUEST_DELAY = 3  # seconds between API calls
MAX_RETRIES = 3
PROGRESS_FILE = "data/_en_content_progress.json"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_FILE = os.path.join(BASE_DIR, "data", "tools_en.json")
PROGRESS_PATH = os.path.join(BASE_DIR, PROGRESS_FILE)


def call_api(system_prompt, user_prompt, max_retries=MAX_RETRIES):
    """Call SiliconFlow API with retry logic."""
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
            resp = requests.post(BASE_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content
        except Exception as e:
            print(f"  API error (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
            else:
                return None


def generate_tool_content(tool):
    """Generate all content fields for a single tool."""
    name = tool["name"]
    category = tool.get("category", "AI Tools")
    url = tool.get("url", "")
    price = tool.get("price", "")
    platform = tool.get("platform", "")
    emoji = tool.get("emoji", "🔧")
    tags = tool.get("tags", [])
    existing_desc = tool.get("description", "")

    system_prompt = """You are an expert tech writer and SEO content specialist. You write native, professional English content for an AI tools directory website. Your writing is factual, helpful, and optimized for search engines without being spammy. You NEVER translate from Chinese — all content is originally written in English based on real knowledge of these AI tools."""

    user_prompt = f"""Generate comprehensive native English SEO content for the AI tool "{name}".

**Tool Info:**
- Name: {name}
- Category: {category}
- Website: {url}
- Pricing: {price}
- Platform: {platform}
- Tags: {', '.join(t.get('text', str(t)) if isinstance(t, dict) else str(t) for t in tags)}
- Current brief description: {existing_desc}

**Requirements — return ONLY valid JSON (no markdown fences, no comments):**
{{
  "description": "SEO-optimized description, 100-150 characters, include primary keyword naturally. No emoji.",
  "pros": ["pro1", "pro2", "pro3", "pro4"],
  "cons": ["con1", "con2", "con3"],
  "faq": [
    {{"q": "question about {name}", "a": "detailed answer 40-80 words"}},
    {{"q": "another practical question", "a": "detailed answer 40-80 words"}}
  ],
  "content": "## What is {name}?\\n\\nIntro paragraph (50-80 words) explaining what this tool is and who it's for.\\n\\n## Key Features\\n\\n- Feature 1: description\\n- Feature 2: description\\n- Feature 3: description\\n- Feature 4: description\\n\\n## Pricing\\n\\nDetails about pricing tiers, free plan availability, and value for money.\\n\\n## Pros & Cons\\n\\nBrief summary of main advantages and limitations.\\n\\n## {name} vs Alternatives\\n\\nCompare with 2-3 competing tools. What makes this tool stand out?\\n\\n## Best For\\n\\nWho should use this tool? Specific use cases.\\n\\n## Verdict\\n\\nFinal recommendation. Is it worth trying? (30-50 words)\\n\\nTotal content: 800-1200 words."
}}

**Critical rules:**
1. Write in NATIVE English — never translate from Chinese
2. Include relevant long-tail keywords naturally (e.g., "free AI tool for X", "X alternative", "best AI for Y")
3. Be factual and specific — mention real features, real pricing
4. content field uses Markdown format with ## headings
5. Escape all quotes and special characters properly in JSON
6. Return ONLY the JSON object, nothing else"""

    raw = call_api(system_prompt, user_prompt)
    if not raw:
        return None

    # Clean up response — remove markdown fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)

    try:
        result = json.loads(cleaned)
        return result
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        print(f"  Raw response (first 500 chars): {cleaned[:500]}")
        return None


def load_progress():
    """Load progress file if it exists."""
    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed": [], "failed": []}


def save_progress(progress):
    """Save progress file."""
    with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def main():
    print("=" * 60)
    print("gen_en_content.py — Native English Content Generator")
    print("=" * 60)

    # Load tools
    with open(TOOLS_FILE, "r", encoding="utf-8") as f:
        tools = json.load(f)
    print(f"Loaded {len(tools)} tools from tools_en.json")

    # Load progress
    progress = load_progress()
    completed_set = set(progress["completed"])
    print(f"Already completed: {len(completed_set)} tools")

    # Find tools that need content
    pending = []
    for i, tool in enumerate(tools):
        name = tool["name"]
        if name in completed_set:
            continue
        tool_json = json.dumps(tool)
        if "[AUTO-GENERATE]" in tool_json or not tool.get("content") or "[AUTO-GENERATE]" in tool.get("content", ""):
            pending.append((i, tool))

    if not pending:
        print("\n✅ All tools already have content! Nothing to do.")
        return

    print(f"Pending: {len(pending)} tools need content generation\n")

    success_count = 0
    fail_count = 0

    for idx, (i, tool) in enumerate(pending):
        name = tool["name"]
        print(f"[{idx+1}/{len(pending)}] Generating content for: {name}")

        result = generate_tool_content(tool)

        if result:
            # Update tool fields
            tools[i]["description"] = result.get("description", tool.get("description", ""))
            tools[i]["pros"] = result.get("pros", tool.get("pros", []))
            tools[i]["cons"] = result.get("cons", tool.get("cons", []))
            tools[i]["faq"] = result.get("faq", tool.get("faq", []))
            tools[i]["content"] = result.get("content", tool.get("content", ""))

            # Save after each tool
            with open(TOOLS_FILE, "w", encoding="utf-8") as f:
                json.dump(tools, f, ensure_ascii=False, indent=2)

            progress["completed"].append(name)
            if name in progress["failed"]:
                progress["failed"].remove(name)
            save_progress(progress)

            success_count += 1
            print(f"  ✅ Success ({success_count} done, {len(pending) - idx - 1} remaining)")
        else:
            progress["failed"].append(name)
            save_progress(progress)
            fail_count += 1
            print(f"  ❌ Failed ({fail_count} failures)")

        # Rate limiting
        if idx < len(pending) - 1:
            time.sleep(REQUEST_DELAY)

    # Summary
    print("\n" + "=" * 60)
    print(f"Generation complete!")
    print(f"  ✅ Success: {success_count}")
    print(f"  ❌ Failed: {fail_count}")

    if progress["failed"]:
        print(f"\nFailed tools: {', '.join(progress['failed'])}")
        print("Re-run this script to retry failed tools.")

    # Verify
    with open(TOOLS_FILE, "r", encoding="utf-8") as f:
        tools = json.load(f)
    remaining = sum(1 for t in tools if "[AUTO-GENERATE]" in json.dumps(t))
    print(f"\nTools still needing content: {remaining}")
    print("=" * 60)


if __name__ == "__main__":
    main()
