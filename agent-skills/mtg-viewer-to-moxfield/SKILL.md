---
name: mtg-viewer-to-moxfield
description: "Convert MTG Table Viewer / mtg-viewer JSON save files into paste-ready Moxfield decklists. Use when Codex needs to export one .mtg-viewer.json file or a folder of viewer saves to simple Moxfield-compatible quantity text, preserving commander cards as a Commander section."
---

# MTG Viewer To Moxfield

## Workflow

Use `scripts/mtg_viewer_to_moxfield.py` for deterministic conversion.

Run on one save:

```powershell
python .\mtg-viewer-to-moxfield\scripts\mtg_viewer_to_moxfield.py `
  .\all_my_mtg_viewer_decks\cimetiere-mtg-viewer.json `
  --output .\moxfield_decklists\cimetiere-moxfield.txt
```

Run on a folder:

```powershell
python .\mtg-viewer-to-moxfield\scripts\mtg_viewer_to_moxfield.py `
  .\all_my_mtg_viewer_decks `
  --output-dir .\all_my_mtg_viewer_decks\moxfield_decklists
```

## Output Rules

- Prefer expanded `cards[]` from the viewer save because it preserves `isCommander`.
- Fall back to compact `decklist` lines only if `cards[]` is absent or empty.
- Emit canonical English card names from `card.name`; fall back to `requestedName`.
- Group duplicate card names into `N Card Name` lines while preserving first-seen order.
- Put cards with `isCommander: true` under `Commander` only. Never repeat commander cards under `Deck`; Moxfield imports that as a duplicated card and can create a 101-card Commander deck.
- Do not include comments or metadata in generated decklist files, so each file can be pasted directly into Moxfield.

## Verification

After conversion, parse every output text file and check:

- The total quantity equals the source physical card count from `cards[]`, or the source compact `decklist` count when using fallback mode.
- Commander cards are present exactly once in the `Commander` section.
- The script exits nonzero on missing files, invalid JSON, or cards without usable names.
