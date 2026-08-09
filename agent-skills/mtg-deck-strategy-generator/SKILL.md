---
name: mtg-deck-strategy-generator
description: "Analyze an mtg-viewer JSON save file (autoBucketFacts, leaf buckets, strategyNotes, commander identity, multi-bucket anchors) and synthesize a concise, insightful Magic: The Gathering deck strategy guide in Markdown without altering or mutating the JSON deck file."
---

# MTG Deck Strategy Generator

## Rule

Read the `.mtg-viewer.json` or `.json` deck save file in a strictly read-only manner. Do NOT edit or modify the JSON deck save file. Analyze the extracted granular bucket facts (`autoBucketFacts`), user-provided strategy notes (`strategyNotes`), and card metadata to synthesize a concise, insightful Markdown strategy document (`strategy_<deck_title>.md`) saved in the same directory as the deck. Keep the Markdown concise (~15–25 lines), actionable, and specific to the deck's card interactions, user notes, and commander synergy.

## Workflow

1. **Extract Deck Facts, Granular Buckets & Strategy Notes**:
   - Run `python <skill-folder>/scripts/summarize_deck.py "<path_to_deck_json>"`
   - Parses the JSON save and outputs a structured JSON summary containing commander identity, card counts, avg CMC, category breakdown, labeled leaf bucket counts, multi-bucket anchor cards, and any custom `strategyNotes` entered by the user.

2. **Synthesize Strategy in Markdown**:
   - Read the extracted facts and interpret the deck's specific themes, primary engine loops, card synergies, and piloting tips.
   - **Incorporate User Strategy Notes (`strategyNotes`)**: If the JSON file contains `strategyNotes`, prioritize and integrate the user's explicit piloting tips, combo descriptions, and archetype guidance into the Markdown guide (enriching the *Primary Plan*, *Key Engine Loops*, and *Piloting Tips* sections).
   - Write a concise `strategy_<deck_title>.md` file in the deck folder with the following structure:

```markdown
# 🃏 Strategy: <Deck Title>
**Commander:** <Commander Name> (<Color Identity>)

### 🎯 Primary Plan & Win Conditions
<2-3 sentences explaining the core deck objective, primary win condition, and how the commander drives the game plan with specific key cards and user strategy insights>

### ⚡ Key Engine Loops
- **<Loop 1 Name>:** <Card A> + <Card B> → <Specific interaction / engine output>
- **<Loop 2 Name>:** <Card C> + <Card D> → <Specific interaction / engine output>

### ⚓ Multi-Bucket Anchor Cards
- **<Card Name>** (CMC <N>): `<Bucket 1>, <Bucket 2>, <Bucket 3>`

### 📊 Deck Balance & Core Pillars
- **Core Pillars:** <Pillar 1> (<Count>), <Pillar 2> (<Count>), <Pillar 3> (<Count>), <Pillar 4> (<Count>)

### 💡 Opening Hand & Piloting Tips
- **Keep:** <Specific opening hand requirements e.g. 3 lands matching colors, 1 early setup card, 1 draw/engine piece>
- **Watch Out:** <Key weakness/vulnerability and how the deck's protection/interaction responds>
```

3. **Verify Output**:
   - Confirm `strategy_<deck_title>.md` exists, seamlessly blends calculated facts with any user `strategyNotes`, and that the `.mtg-viewer.json` file was untouched.
