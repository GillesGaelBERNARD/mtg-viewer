#!/usr/bin/env python3
"""Convert MTG Viewer JSON saves to paste-ready Moxfield decklists."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


QUANTITY_LINE = re.compile(r"^\s*(\d+)\s+(.+?)\s*$")


@dataclass(frozen=True)
class DeckEntry:
    quantity: int
    name: str


@dataclass(frozen=True)
class ConvertedDeck:
    source: Path
    title: str
    commanders: list[DeckEntry]
    deck: list[DeckEntry]
    source_count: int
    used_fallback_decklist: bool

    @property
    def total_quantity(self) -> int:
        return sum(entry.quantity for entry in self.commanders) + sum(
            entry.quantity for entry in self.deck
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert MTG Viewer JSON saves to Moxfield-compatible decklists."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="A .mtg-viewer.json file or a directory containing viewer saves.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output .txt file when converting one input file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "Directory for generated .txt files. Defaults to "
            "<input-dir>/moxfield_decklists for directory input."
        ),
    )
    parser.add_argument(
        "--pattern",
        default="*mtg-viewer.json",
        help="Glob used for directory input. Default: *mtg-viewer.json",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search directory input recursively.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"{path}: cannot read file: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return data


def clean_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).strip()


def add_quantity(entries: OrderedDict[str, int], name: str, quantity: int = 1) -> None:
    if quantity <= 0:
        return
    entries[name] = entries.get(name, 0) + quantity


def to_entries(entries: OrderedDict[str, int]) -> list[DeckEntry]:
    return [DeckEntry(quantity=quantity, name=name) for name, quantity in entries.items()]


def parse_compact_decklist(decklist: Any, source: Path) -> tuple[list[DeckEntry], int]:
    if not isinstance(decklist, str) or not decklist.strip():
        raise ValueError(f"{source}: no cards[] and no compact decklist fallback")

    entries: OrderedDict[str, int] = OrderedDict()
    total = 0
    for line_number, raw_line in enumerate(decklist.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        match = QUANTITY_LINE.match(line)
        if not match:
            raise ValueError(f"{source}: cannot parse decklist line {line_number}: {line!r}")
        quantity = int(match.group(1))
        name = clean_name(match.group(2).split("|", 1)[0])
        if not name:
            raise ValueError(f"{source}: empty card name on decklist line {line_number}")
        add_quantity(entries, name, quantity)
        total += quantity
    return to_entries(entries), total


def convert_from_cards(
    cards: Iterable[Any],
    source: Path,
) -> tuple[list[DeckEntry], list[DeckEntry], int]:
    commander_entries: OrderedDict[str, int] = OrderedDict()
    deck_entries: OrderedDict[str, int] = OrderedDict()
    total = 0

    for index, card in enumerate(cards, start=1):
        if not isinstance(card, dict):
            raise ValueError(f"{source}: card {index} is not an object")
        name = clean_name(card.get("name")) or clean_name(card.get("requestedName"))
        if not name:
            raise ValueError(f"{source}: card {index} has no usable name")

        is_commander = card.get("isCommander") is True
        if is_commander:
            add_quantity(commander_entries, name)
        else:
            add_quantity(deck_entries, name)
        total += 1

    return to_entries(commander_entries), to_entries(deck_entries), total


def convert_file(path: Path) -> ConvertedDeck:
    data = load_json(path)
    title = clean_name(data.get("deckTitle")) or path.stem
    cards = data.get("cards")

    if isinstance(cards, list) and cards:
        commanders, deck, total = convert_from_cards(cards, path)
        return ConvertedDeck(
            source=path,
            title=title,
            commanders=commanders,
            deck=deck,
            source_count=total,
            used_fallback_decklist=False,
        )

    deck, total = parse_compact_decklist(data.get("decklist"), path)
    return ConvertedDeck(
        source=path,
        title=title,
        commanders=[],
        deck=deck,
        source_count=total,
        used_fallback_decklist=True,
    )


def render_deck(deck: ConvertedDeck) -> str:
    lines: list[str] = []

    if deck.commanders:
        lines.append("Commander")
        lines.extend(f"{entry.quantity} {entry.name}" for entry in deck.commanders)
        lines.append("")

    lines.append("Deck")
    lines.extend(f"{entry.quantity} {entry.name}" for entry in deck.deck)
    return "\n".join(lines) + "\n"


def output_name_for(source: Path) -> str:
    stem = source.name
    for suffix in (".mtg-viewer.json", "-mtg-viewer.json", ".json"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-._")
    return f"{safe or source.stem}-moxfield.txt"


def discover_inputs(path: Path, pattern: str, recursive: bool) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise ValueError(f"{path}: input is not a file or directory")
    iterator = path.rglob(pattern) if recursive else path.glob(pattern)
    files = sorted(candidate for candidate in iterator if candidate.is_file())
    if not files:
        raise ValueError(f"{path}: no files matched {pattern!r}")
    return files


def resolve_outputs(args: argparse.Namespace, input_files: list[Path]) -> dict[Path, Path]:
    if len(input_files) == 1 and args.output:
        return {input_files[0]: args.output}

    if args.output and len(input_files) > 1:
        raise ValueError("--output can only be used with one input file")

    output_dir = args.output_dir
    if output_dir is None:
        if args.input.is_dir():
            output_dir = args.input / "moxfield_decklists"
        else:
            output_dir = args.input.parent

    return {source: output_dir / output_name_for(source) for source in input_files}


def write_index(output_dir: Path, converted: list[tuple[ConvertedDeck, Path]]) -> None:
    if not converted:
        return
    index_path = output_dir / "INDEX.txt"
    lines = ["MTG Viewer to Moxfield decklists", ""]
    for deck, path in converted:
        mode = "fallback decklist" if deck.used_fallback_decklist else "cards"
        lines.append(
            f"{path.name}\t{deck.total_quantity} cards\t"
            f"{len(deck.commanders)} commander lines\tfrom {mode}\t{deck.title}"
        )
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> int:
    args = parse_args()
    try:
        input_files = discover_inputs(args.input, args.pattern, args.recursive)
        outputs = resolve_outputs(args, input_files)
        converted: list[tuple[ConvertedDeck, Path]] = []

        for source in input_files:
            deck = convert_file(source)
            if deck.total_quantity != deck.source_count:
                raise ValueError(
                    f"{source}: output count {deck.total_quantity} does not match "
                    f"source count {deck.source_count}"
                )
            output_path = outputs[source]
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(render_deck(deck), encoding="utf-8")
            converted.append((deck, output_path))

        output_dirs = {path.parent for _, path in converted}
        if len(output_dirs) == 1:
            write_index(next(iter(output_dirs)), converted)

        for deck, output_path in converted:
            commander_count = sum(entry.quantity for entry in deck.commanders)
            deck_count = sum(entry.quantity for entry in deck.deck)
            fallback = " fallback" if deck.used_fallback_decklist else ""
            print(
                f"Wrote {output_path} "
                f"({commander_count} commander, {deck_count} deck,{fallback} "
                f"{deck.total_quantity} total)"
            )
        return 0
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
