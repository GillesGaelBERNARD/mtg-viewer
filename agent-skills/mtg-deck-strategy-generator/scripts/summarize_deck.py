#!/usr/bin/env python3
"""
mtg-deck-strategy-generator: Read-Only Deck Data Extractor
Parses mtg-viewer JSON save files and outputs structured deck statistics, leaf bucket distributions,
and multi-bucket anchor cards as a clean JSON summary for LLM strategy synthesis.
"""

import sys
import os
import json
import re
import argparse
from pathlib import Path
from collections import Counter, defaultdict

DISALLOWED_VAGUE_BUCKET_NAMES = {"synergy", "payoff", "finisher", "mana/fix-colors/multiple"}

def clean_bucket_list(bucket_ids):
    if not bucket_ids:
        return []
    cleaned = []
    for b in bucket_ids:
        if not b or not isinstance(b, str):
            continue
        if b.lower() in DISALLOWED_VAGUE_BUCKET_NAMES:
            continue
        cleaned.append(b)
    return list(dict.fromkeys(cleaned))

def extract_deck_data(deck_data):
    deck_title = deck_data.get("deckTitle") or "MTG Commander Deck"
    cards = deck_data.get("cards", [])

    commanders = [c.get("name") for c in cards if c.get("isCommander")]
    alt_commanders = [c.get("name") for c in cards if c.get("isAlternateCommander")]

    if not commanders:
        legendaries = [c.get("name") for c in cards if "Legendary" in (c.get("typeLine") or "") and "Creature" in (c.get("typeLine") or "")]
        if legendaries:
            commanders = [legendaries[0]]

    lands = [c for c in cards if "Land" in (c.get("typeLine") or "")]
    non_lands = [c for c in cards if "Land" not in (c.get("typeLine") or "")]

    non_land_cmc = sum((c.get("manaValue") or c.get("manualManaValue") or 0) for c in non_lands)
    avg_cmc_nonland = round(non_land_cmc / len(non_lands), 2) if non_lands else 0

    category_counts = Counter()
    for c in cards:
        cat = c.get("category") or "others"
        category_counts[cat.capitalize()] += 1

    bucket_card_map = defaultdict(list)
    card_buckets = {}
    card_type_map = {}
    fact_label_map = {}

    for c in cards:
        name = c.get("name")
        card_type_map[name] = c.get("typeLine", "")
        
        b_list = []
        facts = c.get("autoBucketFacts") or []
        if facts:
            for f in facts:
                b_obj = f.get("bucket") or {}
                b_id = b_obj.get("id")
                b_label = b_obj.get("label")
                if b_id and b_id.lower() not in DISALLOWED_VAGUE_BUCKET_NAMES:
                    b_list.append(b_id)
                    if b_label:
                        fact_label_map[b_id] = b_label

        if not b_list:
            raw_b = c.get("utilityBuckets") or c.get("autoBuckets") or []
            b_list = clean_bucket_list(raw_b)

        b_list = clean_bucket_list(b_list)
        card_buckets[name] = b_list
        for b in b_list:
            bucket_card_map[b].append(name)

    anchor_cards = []
    for c in non_lands:
        name = c.get("name")
        b_list = card_buckets.get(name, [])
        if len(b_list) >= 2:
            anchor_cards.append({
                "name": name,
                "type": card_type_map.get(name, ""),
                "cmc": c.get("manaValue", 0),
                "buckets": [fact_label_map.get(b, b) for b in b_list]
            })

    anchor_cards.sort(key=lambda x: len(x["buckets"]), reverse=True)

    custom_buckets = deck_data.get("customBuckets") or []

    bucket_counts_labeled = {}
    for b_id, card_list in bucket_card_map.items():
        label = fact_label_map.get(b_id, b_id)
        bucket_counts_labeled[label] = len(card_list)

    return {
        "deckTitle": deck_title,
        "commander": commanders[0] if commanders else "Unknown Commander",
        "altCommanders": alt_commanders,
        "totalCards": len(cards),
        "landCount": len(lands),
        "nonLandCount": len(non_lands),
        "avgCmcNonland": avg_cmc_nonland,
        "categoryCounts": dict(category_counts),
        "bucketCounts": bucket_counts_labeled,
        "rawBucketCardMap": {b: l for b, l in bucket_card_map.items()},
        "customBuckets": custom_buckets,
        "anchorCards": anchor_cards[:10]
    }

def main():
    parser = argparse.ArgumentParser(description="Extract mtg-viewer JSON deck data.")
    parser.add_argument("json_file", help="Path to .mtg-viewer.json file")
    args = parser.parse_args()

    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"Error: File '{json_path}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        deck_data = json.load(f)

    extracted = extract_deck_data(deck_data)
    print(json.dumps(extracted, indent=2))

if __name__ == "__main__":
    main()
