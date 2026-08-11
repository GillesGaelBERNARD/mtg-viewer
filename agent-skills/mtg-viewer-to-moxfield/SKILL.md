---
name: mtg-viewer-to-moxfield
description: "Convert MTG Table Viewer / mtg-viewer JSON save files into paste-ready Moxfield decklists. Use when Codex needs to export one .mtg-viewer.json file or a folder of viewer saves while preserving commander sections, exact set/collector printings, and foil or etched finishes where available."
---

# MTG Viewer To Moxfield

## Workflow

Use `scripts/mtg_viewer_to_moxfield.py` for deterministic formatting. Current saves contain print metadata directly; for legacy saves, the script resolves missing set/collector fields from their Scryfall IDs unless `--offline` is supplied.

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
- Emit `N Card Name (SET) Collector` for exact printings and append `*F*` or `*E*` for foil or etched cards.
- Resolve missing set/collector fields in legacy saves through their `scryfallId`; warn and fall back to names if Scryfall is unavailable. Use `--offline` to skip enrichment deliberately.
- Group duplicates only when name, set, collector number, and finish all match; preserve first-seen order.
- Put cards with `isCommander: true` under `Commander` only. Never repeat commander cards under `Deck`; Moxfield imports that as a duplicated card and can create a 101-card Commander deck.
- Do not include comments or metadata in generated decklist files, so each file can be pasted directly into Moxfield.
- Moxfield deck text cannot reliably preserve printed language, condition, altered, signed, or misprint state. Those fields remain in `.mtg-viewer.json` saves.

## Verification

After conversion, parse every output text file and check:

- The total quantity equals the source physical card count from `cards[]`, or the source compact `decklist` count when using fallback mode.
- Commander cards are present exactly once in the `Commander` section.
- Distinct printings or finishes of the same card remain distinct output lines.
- The script exits nonzero on missing files, invalid JSON, or cards without usable names.
