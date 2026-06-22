---
name: mtg-viewer-from-deck-images
description: "Create MTG Deck Table Viewer save files from physical deck photos, screenshots, or card-spread images. Use when the user provides Magic: The Gathering deck images and wants an .mtg-viewer.json file, offline images, a loaded viewer layout, card-name extraction, Scryfall validation, language-preserving card images, count checks, or duplicate audit."
---

# MTG Viewer From Deck Images

## Rule

Create a viewer save, not just a decklist. Read every physical card visible or implied. Use companion notes in the same folder when present. Preserve printed-language card images when Scryfall has that language; use English names only as stable identifiers. Do not edit the mtg-viewer repo unless the user asks.

## Workflow

1. Inspect source files.
   - View the requested image at high/original detail.
   - List nearby files; open companion notes or alternate photos if they resolve counts/names.
   - Crop/zoom columns, stacks, dice, hidden edges, and unclear titles into temp files outside any repo.

2. Extract a working decklist.
   - Prefer printed card titles exactly as seen.
   - Preserve accents and ligatures exactly: `Sirène dompte-tempête`, `Flibustière à voile volante`, `Équipier inébranlable`, `Persécuteur morne-œil`. Never replace diacritics with ASCII or `?`.
   - Record language per card or pile when visible or inferable. Use Scryfall language codes such as `en`, `fr`, `de`, `es`, `it`, `pt`, `ja`, `ko`, `ru`, `zhs`, `zht`.
   - Map localized titles to Scryfall canonical English names for identity, but keep the localized print for images.
   - Expand physical cards into quantities. Repeated basics are normal. Other duplicates are allowed unless the user or format forbids them.
   - For Commander, report duplicate nonbasics; do not silently delete them.

3. Validate before building.
   - Count physical cards.
   - Count unique names.
   - Report duplicate nonbasics, not as failure unless requested.
   - Resolve every card with Scryfall. Fix spelling by using printed-name search, nearby crop, and known set/art clues.
   - Fail loudly on unresolved or ambiguous cards; do not fill guesses into the save.

4. Build the save.
   - Use `scripts/build_mtg_viewer_bundle.py`.
   - Input lines may be:
     - `1 Sol Ring`
     - `1 Sirène dompte-tempête`
     - `1 <printed localized title> | lang=<scryfall-lang-code>`
     - `1 <printed localized title> | lang=<scryfall-lang-code> | name=<canonical English name>`
     - `4 Forest`
   - Prefer `name=` when a localized title is hard to resolve or several cards share words.
   - Preserve quantity lines in `decklist` (`4 Forest`), but expand `cards[]`; every physical copy must have its own saved card object and unique `id`.
   - Use `--embed-images` when the user wants offline import or when quality matters; this embeds every available non-placeholder card face.
   - Use a clear deck title and save next to the source deck images unless the user gave another destination.
   - Emit the current viewer save shape: `version: 3`, compact quantity `decklist`, `customBuckets`, `customTableSections`, `customStatsCategories`, `layout.activeBucketFilter`, `layout.nextBucketOrder`, `layout.showSubtypes`, `layout.activeSubtypeSections`, card colors, mana value, optional `manualManaValue`, mana cost, oracle text/id, produced mana, detected `category`, `tableCategory`, `isCommander`, utility bucket fields, stats-category fields, bucket order, and face data.
   - Prefill deterministic utility buckets in both `autoBuckets` and `utilityBuckets`; current local heuristic: `plus-one-counters` when oracle text, face text, or oracle tag slugs contain `+1/+1 counter(s)`, `plus one plus one counter(s)`, `proliferate`, or matching counter tag slugs.
   - Set `manualManaValue: null` unless the user explicitly gives an override. Do not infer overrides from where a physical card sat in a photo.

5. Verify output.
   - Parse the saved JSON.
   - Confirm `app == "mtg-table-viewer"`, `version == 3`, card count, unique card ids, compact decklist row count, title, `offlineImages`, embedded image count, embedded face image count, missing images, duplicate report.
   - Optionally import in the viewer or open `mtg-viewer.html` and restore the bundle when layout/visual confidence matters.
   - End with output path and audit facts.

## Image Policy

Choose image URI in this order:
1. Exact same-language print resolved from the visible title or explicit `lang=`.
2. Same-language print with same oracle identity when input used English canonical `name=`.
3. Original Scryfall result language.
4. English default only when same-language art is unavailable.

Treat Scryfall `image_status` values `placeholder` and `missing` as unavailable. If the local-language image is unavailable, use the available English image with no warning.

Within the chosen print, use `normal`, then `large`, then `png`, then `small`; clean zoom rendering makes `normal` readable without `large` file size.

For cards with separate Scryfall face images, export `faces[]`, `activeFaceIndex: 0`, and all face image URLs/data. If a split/adventure card has only a top-level image, export that single image.

## Helper

Run:

```powershell
python <skill-folder>\scripts\build_mtg_viewer_bundle.py `
  --decklist path\decklist.txt `
  --title "Deck Title" `
  --output path\deck.mtg-viewer.json `
  --cache path\scryfall-cache.json `
  --embed-images
```

Use `--default-lang <scryfall-lang-code>` only when most input titles share one printed language and unmarked lines should inherit it. Use per-line `lang=` for mixed-language photos. When language is uncertain, prefer per-line evidence over folder/user locale.

## Done Means

The save imports offline when embedded images were requested, including alternate faces. Every unresolved card is fixed or disclosed. Counts match source evidence. Duplicates are handled according to user/format, not hidden. Repo state remains unchanged unless explicitly requested.
