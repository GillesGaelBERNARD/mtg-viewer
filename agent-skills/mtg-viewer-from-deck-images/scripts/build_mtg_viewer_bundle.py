#!/usr/bin/env python3
import argparse
import base64
import datetime as dt
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.scryfall.com"
UNUSABLE_IMAGE_STATUSES = {"missing", "placeholder"}
BASIC_NAMES = {
    "Plains",
    "Island",
    "Swamp",
    "Mountain",
    "Forest",
    "Wastes",
    "Snow-Covered Plains",
    "Snow-Covered Island",
    "Snow-Covered Swamp",
    "Snow-Covered Mountain",
    "Snow-Covered Forest",
}
LAST_REQUEST_AT = 0.0
MIN_REQUEST_INTERVAL = 0.16
SAVE_VERSION = 3
MANA_COLORS = ("W", "U", "B", "R", "G")
PRODUCED_MANA_SYMBOLS = (*MANA_COLORS, "C")
MANA_COLOR_LABELS = {
    "W": "White",
    "U": "Blue",
    "B": "Black",
    "R": "Red",
    "G": "Green",
}
PLUS_ONE_COUNTER_BUCKET_ID = "plus-one-counters"
PLUS_ONE_COUNTER_MATCH = (
    "counter-matters",
    "plus-one-plus-one-counters",
    "plus-one-plus-one-counter",
    "p1p1-counters",
    "p1p1-counter",
    "proliferate",
)
PLUS_ONE_COUNTER_TEXT_RE = re.compile(r"\+1/\+1 counters?|plus one plus one counters?|proliferate", re.IGNORECASE)
MOJIBAKE_MARK_RE = re.compile(r"[\u00c2\u00c3\u00c5\u00e2]")
UNKNOWN_NAME_RE = re.compile(r"[?\ufffd]")


def throttle():
    global LAST_REQUEST_AT
    elapsed = time.monotonic() - LAST_REQUEST_AT
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    LAST_REQUEST_AT = time.monotonic()


def request_json(url, data=None):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "codex-mtg-viewer-skill/1.0"})
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
        req.data = body
    last_error = None
    for attempt in range(3):
        throttle()
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < 2:
                retry_after = error.headers.get("Retry-After")
                wait = int(retry_after) if retry_after and retry_after.isdigit() else 60
                time.sleep(wait)
                continue
            last_error = error
            break
    if last_error is None:
        raise RuntimeError("Request failed before an HTTP response was available.")
    detail = last_error.read().decode("utf-8", errors="replace")
    try:
        payload = json.loads(detail)
        raise RuntimeError(payload.get("details") or payload.get("message") or detail) from last_error
    except json.JSONDecodeError:
        raise RuntimeError(detail or str(last_error)) from last_error


def request_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "codex-mtg-viewer-skill/1.0"})
    throttle()
    with urllib.request.urlopen(req, timeout=90) as response:
        content_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0]
        return content_type, response.read()


def repair_mojibake_text(value):
    text = str(value or "")
    if not MOJIBAKE_MARK_RE.search(text):
        return text
    try:
        decoded = text.encode("cp1252").decode("utf-8")
    except UnicodeError:
        return text
    return decoded if re.search(r"[\u00c0-\u024f\u2018-\u201d]", decoded) else text


def clean_name(value):
    text = repair_mojibake_text(value).replace("\u00a0", " ")
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", text.strip()))


def read_text_file(path):
    data = Path(path).read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def parse_line(line, line_no):
    raw = line.split("#", 1)[0].strip()
    if not raw:
        return []
    parts = [part.strip() for part in raw.split("|")]
    head = parts[0]
    match = re.match(r"^(?:(\d+)\s*[xX]?\s+)?(.+?)\s*$", head)
    if not match:
        raise ValueError(f"Line {line_no}: cannot parse {line!r}")
    count = int(match.group(1) or "1")
    printed = clean_name(match.group(2))
    meta = {}
    for part in parts[1:]:
        if "=" not in part:
            raise ValueError(f"Line {line_no}: metadata must be key=value: {part!r}")
        key, value = part.split("=", 1)
        meta[key.strip().lower()] = clean_name(value)
    lang = meta.get("lang", "")
    canonical = meta.get("name", "")
    return [{"count": count, "printed": printed, "lang": lang, "canonical": canonical, "line_no": line_no}]


def parse_decklist(path):
    entries = []
    for line_no, line in enumerate(read_text_file(path).splitlines(), 1):
        entries.extend(parse_line(line, line_no))
    return entries


def cache_key(entry, default_lang):
    return json.dumps(
        {
            "printed": entry["printed"],
            "lang": entry["lang"] or default_lang,
            "canonical": entry["canonical"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def load_resolve_cache(path):
    if not path:
        return {}
    cache_path = Path(path)
    if not cache_path.exists():
        return {}
    return json.loads(cache_path.read_text(encoding="utf-8"))


def save_resolve_cache(path, cache):
    if not path:
        return
    cache_path = Path(path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def image_uri_from_object(card):
    images = card.get("image_uris") or {}
    uri = images.get("normal") or images.get("large") or images.get("png") or images.get("small")
    return uri or ""


def card_image_uri(card):
    uri = image_uri_from_object(card)
    if uri:
        return uri
    for face in card.get("card_faces") or []:
        uri = image_uri_from_object(face)
        if uri:
            return uri
    return ""


def has_usable_image(card):
    return bool(card_image_uri(card)) and card.get("image_status", "") not in UNUSABLE_IMAGE_STATUSES


def usable_card_image_uri(card):
    return card_image_uri(card) if has_usable_image(card) else ""


def exact_print_match(data, printed):
    folded = printed.casefold()
    for card in data:
        if clean_name(card.get("printed_name") or "").casefold() == folded:
            return card
    for card in data:
        if clean_name(card.get("name") or "").casefold() == folded:
            return card
    for card in data:
        for face in card.get("card_faces") or []:
            if clean_name(face.get("printed_name") or "").casefold() == folded:
                return card
            if clean_name(face.get("name") or "").casefold() == folded:
                return card
    return data[0] if data else None


def has_unknown_name_chars(name):
    return bool(UNKNOWN_NAME_RE.search(str(name or "")))


def scryfall_unknown_name_pattern(name):
    parts = []
    for char in clean_name(name):
        if char in {"?", "\ufffd"}:
            parts.append(".")
        elif char.isspace():
            parts.append(r"\s+")
        else:
            parts.append(re.escape(char).replace("/", r"\/"))
    return "".join(parts)


def best_search_result(data):
    for card in data:
        if has_usable_image(card):
            return card
    return data[0] if data else None


def search_printed_pattern(printed, lang="any"):
    pattern = scryfall_unknown_name_pattern(printed)
    if not pattern:
        raise RuntimeError(f"No usable search pattern for {printed}")
    query = f"lang:{lang or 'any'} name:/^{pattern}$/"
    url = f"{API}/cards/search?q={urllib.parse.quote(query)}&unique=prints"
    data = request_json(url).get("data") or []
    card = best_search_result(data)
    if not card:
        raise RuntimeError(f"No printed-name match for {printed}")
    return card


def search_printed(printed, lang):
    query = f'lang:{lang} "{printed}"'
    url = f"{API}/cards/search?q={urllib.parse.quote(query)}&unique=prints"
    try:
        data = request_json(url).get("data") or []
    except RuntimeError:
        if has_unknown_name_chars(printed):
            return search_printed_pattern(printed, lang)
        raise
    card = exact_print_match(data, printed)
    if not card:
        raise RuntimeError(f"No {lang} print for {printed}")
    return card


def named_card(name):
    clean = clean_name(name)
    last_error = None
    for mode in ("exact", "fuzzy"):
        url = f"{API}/cards/named?{mode}={urllib.parse.quote(clean)}"
        try:
            return request_json(url)
        except RuntimeError as error:
            last_error = error
    if has_unknown_name_chars(clean):
        return search_printed_pattern(clean, "any")
    raise last_error


def same_language_print(card, lang):
    oracle_id = card.get("oracle_id")
    if not oracle_id or not lang:
        return card
    query = f"oracleid:{oracle_id} lang:{lang}"
    url = f"{API}/cards/search?q={urllib.parse.quote(query)}&unique=prints"
    try:
        data = request_json(url).get("data") or []
    except RuntimeError:
        return card
    with_real_image = [item for item in data if has_usable_image(item)]
    if with_real_image:
        return with_real_image[0]
    return card


def resolve_entry(entry, default_lang):
    lang = entry["lang"] or default_lang
    printed = entry["printed"]
    if entry["canonical"]:
        canonical = named_card(entry["canonical"])
        chosen = same_language_print(canonical, lang)
        return canonical, chosen
    if lang:
        chosen = search_printed(printed, lang)
        canonical = named_card(chosen["name"])
        if not has_usable_image(chosen):
            chosen = same_language_print(canonical, lang)
        return canonical, chosen
    canonical = named_card(printed)
    return canonical, canonical


def data_uri_for(url):
    content_type, data = request_bytes(url)
    return f"data:{content_type};base64,{base64.b64encode(data).decode('ascii')}"


def image_data_for(uri, embed_images):
    return data_uri_for(uri) if embed_images and uri else ""


def viewer_faces(card, fallback_name, embed_images):
    if not has_usable_image(card):
        return []
    faces = []
    for index, face in enumerate(card.get("card_faces") or []):
        uri = image_uri_from_object(face)
        if not uri:
            continue
        faces.append(
            {
                "name": clean_name(face.get("printed_name") or face.get("name") or f"{fallback_name} face {index + 1}"),
                "imageUri": uri,
                "sourceImageUri": uri,
                "imageData": image_data_for(uri, embed_images),
            }
        )
    if len(faces) > 1:
        return faces

    uri = usable_card_image_uri(card)
    if not uri:
        return []
    return [
        {
            "name": clean_name(card.get("printed_name") or card.get("name") or fallback_name),
            "imageUri": uri,
            "sourceImageUri": uri,
            "imageData": image_data_for(uri, embed_images),
        }
    ]


def category_for(type_line):
    text = type_line.lower()
    if "land" in text:
        return "lands"
    if "creature" in text:
        return "creatures"
    if "planeswalker" in text:
        return "planeswalkers"
    if "enchantment" in text:
        return "enchantments"
    if "artifact" in text or "equipment" in text:
        return "artifacts"
    if "instant" in text:
        return "instants"
    if "sorcery" in text:
        return "sorcery"
    return "others"


def symbol_array(card, key, allowed):
    value = card.get(key) or []
    if not isinstance(value, list):
        return []
    found = {str(item).strip().upper() for item in value if str(item).strip().upper() in allowed}
    return [item for item in allowed if item in found]


def color_array(card, key):
    return symbol_array(card, key, MANA_COLORS)


def produced_mana_array(card, key):
    return symbol_array(card, key, PRODUCED_MANA_SYMBOLS)


def oracle_text(card):
    if card.get("oracle_text"):
        return str(card.get("oracle_text") or "")
    return "\n".join(str(face.get("oracle_text") or "") for face in card.get("card_faces") or [] if face.get("oracle_text"))


def mana_cost(card):
    if card.get("mana_cost"):
        return str(card.get("mana_cost") or "")
    return "".join(str(face.get("mana_cost") or "") for face in card.get("card_faces") or [] if face.get("mana_cost"))


def auto_bucket_ids(*cards):
    text_parts = []
    tag_slugs = []
    for card in cards:
        if not card:
            continue
        text_parts.extend([oracle_text(card), str(card.get("type_line") or "")])
        tag_slugs.extend(str(tag or "").lower() for tag in card.get("oracle_tags") or [])

    buckets = []
    text = "\n".join(text_parts)
    if PLUS_ONE_COUNTER_TEXT_RE.search(text):
        buckets.append(PLUS_ONE_COUNTER_BUCKET_ID)
    elif any(any(token in slug for token in PLUS_ONE_COUNTER_MATCH) for slug in tag_slugs):
        buckets.append(PLUS_ONE_COUNTER_BUCKET_ID)
    return buckets


def requested_name_for_save(requested, chosen):
    printed = clean_name(chosen.get("printed_name") or "")
    return printed if has_unknown_name_chars(requested) and printed else clean_name(requested)


def viewer_card(card_id, requested, canonical, chosen, order, embed_images):
    card_name = canonical.get("name") or chosen.get("name") or requested
    requested_name = requested_name_for_save(requested, chosen)
    faces = viewer_faces(chosen, card_name, embed_images)
    active_face = faces[0] if faces else {}
    image_uri = active_face.get("imageUri") or usable_card_image_uri(chosen)
    image_data = active_face.get("imageData") or image_data_for(image_uri, embed_images)
    type_line = canonical.get("type_line") or chosen.get("type_line") or ""
    buckets = auto_bucket_ids(canonical, chosen)
    return {
        "id": f"card-{order:03d}-{card_id}",
        "scryfallId": chosen.get("id") or canonical.get("id") or "",
        "requestedName": requested_name,
        "name": card_name,
        "imageUri": image_uri,
        "sourceImageUri": image_uri,
        "imageData": image_data,
        "faces": faces,
        "activeFaceIndex": 0,
        "typeLine": type_line,
        "manaValue": int(canonical.get("cmc") or chosen.get("cmc") or 0),
        "manualManaValue": None,
        "manaCost": mana_cost(canonical) or mana_cost(chosen),
        "oracleText": oracle_text(canonical) or oracle_text(chosen),
        "oracleId": canonical.get("oracle_id") or chosen.get("oracle_id") or "",
        "colors": color_array(canonical, "colors") or color_array(chosen, "colors"),
        "colorIdentity": color_array(canonical, "color_identity") or color_array(chosen, "color_identity"),
        "producedMana": produced_mana_array(chosen, "produced_mana") or produced_mana_array(canonical, "produced_mana"),
        "category": category_for(type_line),
        "tableCategory": "",
        "isCommander": False,
        "utilityBuckets": list(buckets),
        "autoBuckets": list(buckets),
        "oracleTags": [],
        "statsCategories": [],
        "bucketEdited": False,
        "error": "" if image_uri else "Image not found",
        "order": order,
        "initialOrder": order,
        "bucketOrder": order,
        "manualPosition": None,
        "zIndex": "",
    }


def land_mana_group_label(card):
    produced = card.get("producedMana") or []
    colors = [symbol for symbol in produced if symbol in MANA_COLORS]
    if len(colors) == len(MANA_COLORS):
        return "Any Color"
    if not colors:
        return "Colorless"
    if len(colors) == 1:
        return MANA_COLOR_LABELS[colors[0]]
    return "/".join(colors)


def audit(cards, decklist_lines):
    names = [card["name"] for card in cards]
    counts = {}
    for name in names:
        counts[name] = counts.get(name, 0) + 1
    ids = [card["id"] for card in cards]
    nonbasic_dupes = {name: count for name, count in counts.items() if count > 1 and name not in BASIC_NAMES}
    basics = {name: counts[name] for name in BASIC_NAMES if name in counts}
    missing_images = [card["name"] for card in cards if not card.get("imageUri")]
    embedded = sum(1 for card in cards if card.get("imageData"))
    embedded_faces = sum(1 for card in cards for face in card.get("faces", []) if face.get("imageData"))
    land_groups = {}
    for card in cards:
        if card.get("category") != "lands":
            continue
        label = land_mana_group_label(card)
        land_groups[label] = land_groups.get(label, 0) + 1
    return {
        "cards": len(cards),
        "uniqueCardIds": len(set(ids)),
        "decklistRows": decklist_lines,
        "uniqueNames": len(counts),
        "nonBasicDuplicates": nonbasic_dupes,
        "basicCounts": basics,
        "landManaGroups": land_groups,
        "missingImages": missing_images,
        "embeddedImages": embedded,
        "embeddedFaceImages": embedded_faces,
    }


def main():
    parser = argparse.ArgumentParser(description="Build an mtg-viewer save from an audited decklist.")
    parser.add_argument("--decklist", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--default-lang", default="")
    parser.add_argument("--embed-images", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.11, help="Delay between Scryfall calls.")
    parser.add_argument("--cache", default="", help="Optional JSON cache for Scryfall resolution data.")
    args = parser.parse_args()

    entries = parse_decklist(args.decklist)
    cards = []
    order = 1
    cache = {}
    resolve_cache = load_resolve_cache(args.cache)
    for entry in entries:
        key = (entry["printed"], entry["lang"] or args.default_lang, entry["canonical"])
        disk_key = cache_key(entry, args.default_lang)
        if key not in cache and disk_key in resolve_cache:
            cached = resolve_cache[disk_key]
            cache[key] = cached["canonical"], cached["chosen"]
        if key not in cache:
            try:
                cache[key] = resolve_entry(entry, args.default_lang)
                resolve_cache[disk_key] = {
                    "canonical": cache[key][0],
                    "chosen": cache[key][1],
                }
                save_resolve_cache(args.cache, resolve_cache)
            except Exception as error:
                raise RuntimeError(
                    f"Line {entry['line_no']}: cannot resolve {entry['printed']!r}"
                    f" lang={entry['lang'] or args.default_lang or 'default'}"
                    f" name={entry['canonical'] or '(none)'}: {error}"
                ) from error
            time.sleep(args.sleep)
        canonical, chosen = cache[key]
        for copy_index in range(entry["count"]):
            requested = entry["printed"]
            cards.append(viewer_card(f"{len(cards) + 1:03d}", requested, canonical, chosen, order, args.embed_images))
            order += 1

    decklist_lines = [f"{entry['count']} {entry['printed']}" for entry in entries]

    bundle = {
        "app": "mtg-table-viewer",
        "version": SAVE_VERSION,
        "savedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "offlineImages": bool(args.embed_images),
        "deckTitle": args.title,
        "strategyNotes": "",
        "decklist": "\n".join(decklist_lines),
        "customBuckets": [],
        "customTableSections": [],
        "customStatsCategories": [],
        "layout": {
            "nextOrder": len(cards) + 1,
            "nextBucketOrder": len(cards) + 1,
            "z": 30 + len(cards),
            "labelsHidden": False,
            "showSubtypes": False,
            "activeSubtypeSections": [],
            "activeBucketFilter": "",
            "camera": {"x": 0, "y": 0, "scale": 0.84},
        },
        "cards": cards,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = audit(cards, len(decklist_lines))
    summary["output"] = str(output)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["missingImages"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
