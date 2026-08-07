---
name: mtg-deck-strategy-generator
description: "Analyze an mtg-viewer V3 JSON save file (V2 autoBucketFacts, leaf buckets, commander identity, multi-bucket anchors) and synthesize a concise, insightful Magic: The Gathering deck strategy guide in Markdown without altering or mutating the JSON deck file."
---

# MTG Deck Strategy Generator

## Rule

Read the `.mtg-viewer.json` or `.json` deck save file in a strictly read-only manner. Do NOT edit or modify the JSON deck save file. Analyze the extracted V2 granular bucket facts (`autoBucketFacts`) and synthesize a concise, insightful Markdown strategy document (`strategy_<deck_title>.md`) saved in the same directory as the deck. Keep the Markdown concise (~15–20 lines), actionable, and specific to the deck's card interactions and commander synergy. Exclude legacy vague bucket names ("synergy", "payoff", "finisher").

## Workflow

1. **Extract Deck Facts & V2 Granular Buckets**:
   - Run `python <skill-folder>/scripts/summarize_deck.py "<path_to_deck_json>"`
   - Parses the JSON save and outputs a structured JSON summary (commander, card counts, avg CMC, category breakdown, labeled v2 leaf bucket counts, multi-bucket anchor cards).

2. **Synthesize Strategy in Markdown**:
   - Read the extracted facts and interpret the deck's specific themes, primary engine loops, card synergies, and piloting tips.
   - Write a concise `strategy_<deck_title>.md` file in the deck folder with the following structure:

```markdown
# 🃏 Strategy: <Deck Title>
**Commander:** <Commander Name> (<Color Identity>)

### 🎯 Primary Plan & Win Conditions
<2-3 sentences explaining the core deck objective, primary win condition, and how the commander drives the game plan with specific key cards>

### ⚡ Key Engine Loops
- **<Loop 1 Name>:** <Card A> + <Card B> → <Specific interaction / engine output>
- **<Loop 2 Name>:** <Card C> + <Card D> → <Specific interaction / engine output>

### 📊 Deck Balance & Key Pillars
- **Core Pillars:** <Pillar 1> (<Count>), <Pillar 2> (<Count>), <Pillar 3> (<Count>), <Pillar 4> (<Count>)

### 💡 Opening Hand & Piloting Tips
- **Keep:** <Specific opening hand requirements e.g. 3 lands matching colors, 1 early setup card, 1 draw/engine piece>
- **Watch Out:** <Key weakness/vulnerability and how the deck's protection/interaction responds>
```

3. **Verify Output**:
   - Confirm `strategy_<deck_title>.md` exists, is concise and insightful, and that the `.mtg-viewer.json` file was untouched.
