# MTG Deck Table Viewer

Version: v0.3

A single-file Magic: The Gathering deck viewer for organizing decks and visualizing their stats, with automation and intuitive UI.

Paste a decklist, get cards images automatically loaded and categorized, visualize the stats, then drag cards around and edit your deck.

It runs fully locally/offline once images are fetched.

Highly portable: single file browser app and single file deck save.

![Loaded table overview](screenshots/overview.png)

## Features

3 tabs: Tabletop deck view, Stats, Utility buckets.

### Automated and interactive tabletop deck view
- Imports card images from Scryfall by card name.
- Groups cards into creature, vehicle, spacecraft, planeswalker, enchantment, artifact, instant, ritual, other, and land areas.
- Aligns non-land cards by mana value.
- Supports manually overriding the mana value (i.e., for X, XX cards you plan to ideally cast at a given MV).
- Keeps lands on the right side of the table.
- Supports free dragging, stack snapping, and between-card insertion while preserving visible stack spacing.
- Shows a face switch on double-faced cards so you can view the other side.
- Lets held cards temporarily rise to the top for inspection, then return to their stack layer on release.
- Adds/removes individual cards.
- Includes Undo, Redo, and Reset Positions controls. Undo stores the last five changes.
- Saves and imports `.mtg-viewer.json` bundles containing the decklist, card placement, and Scryfall image URLs, with optional embedded images for offline use.
- Provides pan, zoom, fit, and center controls for large deck layouts.

![Move history controls](screenshots/zoom.png)

### Deck stats
- Stats view for deck summary, mana curve, type counts, color demand/sources, utility bucket counts, and stats-only custom categories.
- Custom stats categories let you count tags such as Equipment without changing tabletop placement or utility buckets.

![Loaded table overview](screenshots/stats_view.png)

### Utility buckets
- Automated utility Buckets such as Ramp, Card Draw, Removal, Board Wipe, Protection, Tutor, Graveyard, LifeGain, etc. detected from Scryfall Oracle Tags.
- Custom utility Buckets, with manual per-card or multi-card bucket editing.
- View that shows card references grouped by utility bucket, supports the same inspection/zoom behavior as the table, and lets you drag cards between buckets to edit assignments.

![Loaded table overview](screenshots/buckets_view.png)

![Loaded table overview](screenshots/edit_buckets_view.png)

## Usage

Open `mtg-viewer.html` in a browser.

Paste a decklist in this format:

```text
1 Birds of Paradise
1 Sol Ring
1 Command Tower
```

The viewer loads one visual card per non-empty decklist line. Scryfall fetches are paced so large lists load steadily instead of hammering the API.

1 click save/import.

## Controls

### Tabletop deck view
- Drag a card to move it.
- Use Add Card to append one card to the current table.
- Right-click a card to override its mana value for table columns, bucket placement, and stats, or remove it after confirmation.
- Drop near another card to snap into that stack.
- Hold Shift while dropping to place freely without snapping.
- Hold a card to bring it forward temporarily; release to return it to its stack layer.
- Use the small face number on double-faced cards, or double-click the card, to flip sides.
- Hold right-click and draw rectangle to select and move multiple cards.
- Use Undo, Redo, and Reset Positions to manage manual layout and add/remove changes.
- Use Save / Export to write a portable table save to your device. Choose whether to embed images for offline imports.
- Use Import Save to reload a saved decklist, card placement, and either embedded images or Scryfall image URLs.

### Utilitiy buckets views

- To edit buckets: right click on card or move card around categories
- Click on a card or category in the menu to focus the view

## Notes

This is a static HTML/CSS/JavaScript app. It does not require a build step or store deck data on a server.

Save files are plain JSON with the `.mtg-viewer.json` extension. Browsers that support the File System Access API open a save-location dialog; other browsers use their normal download flow. Saves always keep image URLs; embedding images makes the file larger but lets imports show cards offline.

Card data and images are loaded from the public Scryfall API. Magic: The Gathering card names, text, and images belong to their respective rights holders.

## AI Agent Skill

The repo also includes a separate Codex skill at `agent-skills/mtg-viewer-from-deck-images/`. It guides an AI agent through creating `.mtg-viewer.json` saves from physical deck photos, including language-preserving Scryfall images, duplicate audits, offline image embedding, and multi-face card images.

## Limitations

Opinionated automated categories (equivalent to one way I layout physical cards out to visualize a deck)

## To Dos
1. More controls for categories
2. Automated land sorting
