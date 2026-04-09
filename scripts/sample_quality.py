#!/usr/bin/env python3
"""Quick quality check - print sample from Pro V3.2 generated article"""
import json

arts = json.load(open('data/articles_en.json', 'r', encoding='utf-8'))

# Find the comparison article
for a in arts:
    if 'chatgpt-vs-gemini-vs-claude' in a['slug']:
        content = a['content']
        lines = content.split('\n')
        # Print first 60 lines
        print(f"=== {a['title']} ({len(content.split())} words) ===\n")
        for line in lines[:60]:
            print(line)
        print(f"\n... [{len(lines) - 60} more lines]")
        
        # Check for quality signals
        has_tables = '|' in content
        has_numbers = any(c.isdigit() for c in content[:500])
        has_specific = any(kw in content.lower() for kw in ['gpt-4o', 'claude 4', 'gemini 2', 'pricing', 'free tier', 'subscription'])
        print(f"\n=== Quality Signals ===")
        print(f"  Has comparison tables: {has_tables}")
        print(f"  Has specific data/numbers: {has_numbers}")
        print(f"  Has specific product references: {has_specific}")
        break
