import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
CLI = SKILL_ROOT / "scripts" / "deck_evidence.py"


def write_save(path: Path, *, title: str = "Test Deck", cards: list[dict] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "app": "mtg-table-viewer",
        "version": 3,
        "deckTitle": title,
        "strategyNotes": "",
        "customBuckets": [],
        "customStatsCategories": [],
        "layout": {},
        "cards": cards or [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def fact(bucket_id: str, label: str, *, role: str, action: str, kind: str) -> dict:
    return {
        "factId": f"fact-{bucket_id}",
        "abilityId": "ability-1",
        "role": role,
        "action": action,
        "actor": "you",
        "object": {"kind": kind, "name": kind, "types": [kind]},
        "scope": "unspecified",
        "qualifiers": {},
        "bucket": {"id": bucket_id, "label": label, "parents": [], "views": []},
        "evidence": {"ruleId": "test", "faceIndex": 0, "clause": label},
    }


def card(
    name: str,
    *,
    type_line: str,
    mana_value: int,
    mana_cost: str = "",
    oracle_text: str = "",
    buckets: list[str] | None = None,
    facts: list[dict] | None = None,
    commander: bool = False,
    alternate: bool = False,
    produced_mana: list[str] | None = None,
    manual_mana_value: int | None = None,
) -> dict:
    return {
        "id": name.casefold().replace(" ", "-"),
        "name": name,
        "typeLine": type_line,
        "manaValue": mana_value,
        "manualManaValue": manual_mana_value,
        "manaCost": mana_cost,
        "oracleText": oracle_text,
        "producedMana": produced_mana or [],
        "isCommander": commander,
        "isAlternateCommander": alternate,
        "utilityBuckets": buckets or [],
        "autoBuckets": buckets or [],
        "autoBucketFacts": facts or [],
        "statsCategories": [],
        "imageData": "IMAGE_CANARY_" + ("x" * 20_000),
        "faces": [{"name": name, "imageData": "FACE_IMAGE_CANARY"}],
        "secretCanary": "FULL_OBJECT_CANARY",
    }


def strategy_draft(title: str, final_word: str = "first", filler_repetitions: int = 220) -> str:
    sections = [
        f"# {title}",
        "## Theme & Story\nA crew turns every discovery into momentum and tells its story through artifacts.",
        "## Deck Snapshot\nThe curve, card types, and granular buckets show a compact resource engine.",
        "## Mechanical Identity\nThe deck creates resources, reacts to them, and converts those triggers into cards.",
        "## Game Plan\nBuild the engine before committing the commander, then turn repeated triggers into pressure.",
        "## Key Cards\n**Alpha Producer** supplies the resource and **Alpha Trigger** rewards each event.",
        "## Synergies & Engines\n**Alpha Producer** creates the object consumed by the commander-facing trigger engine.",
        "## Combos & Loops\nNo deterministic loop is verified from the available evidence.",
        "## How to Pilot\n### Opening Hand & Mulligans\nKeep mana and an engine piece.\n### Early Game\nDevelop resources.\n### Midgame\nSequence the engine.\n### Late Game\nProtect the payoff and close.",
        "## What to Protect\nProtect the commander and the narrow trigger payoff.",
        "## Weaknesses & Recovery\nRebuild with card advantage after removal.",
        "## Alternate Commanders\nNo alternate commander is configured.",
    ]
    filler = " ".join(["evidence-grounded sequencing guidance"] * filler_repetitions)
    sections.append(f"## Detailed Piloting Notes\n{filler} {final_word}.")
    return "\n\n".join(sections) + "\n"


class DeckEvidenceCliTests(unittest.TestCase):
    def run_cli(self, *args: str, expected_code: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(CLI), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(expected_code, result.returncode, result.stderr)
        return result

    def test_recursive_discovery_validates_saves_and_excludes_other_trees(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "Deck A" / "a.json"
            second = root / "Deck B" / "b.json"
            excluded = root / "others" / "hidden.json"
            write_save(first)
            write_save(second)
            write_save(excluded)
            (root / "not-a-save.json").write_text('{"summary": true}', encoding="utf-8")
            manifest = root / "jobs.json"

            result = self.run_cli(
                "discover",
                str(root),
                "--recursive",
                "--manifest",
                str(manifest),
            )

            status = json.loads(result.stdout)
            jobs = json.loads(manifest.read_text(encoding="utf-8"))["jobs"]
            self.assertEqual(2, status["jobCount"])
            self.assertEqual([str(first.resolve()), str(second.resolve())], [job["source"] for job in jobs])
            self.assertNotIn("hidden.json", manifest.read_text(encoding="utf-8"))

    def test_prepare_emits_compact_app_stats_and_thresholded_granular_evidence(self) -> None:
        create_treasure = fact(
            "tokens/create/treasure", "Create Treasure tokens", role="effect", action="create", kind="token"
        )
        react_treasure = fact(
            "tokens/react-to/enter-treasure",
            "React to Treasure tokens entering",
            role="trigger",
            action="react-to-enter",
            kind="token",
        )
        draw_cards = fact("cards/draw/cards", "Draw cards", role="effect", action="draw", kind="card")
        scry = fact("cards/filter/scry", "Scry", role="effect", action="filter", kind="card")
        cards = [
            card(
                "Captain Evidence",
                type_line="Legendary Creature — Pirate",
                mana_value=4,
                mana_cost="{1}{U}{B}{R}",
                oracle_text="Whenever a Treasure enters, draw a card.",
                buckets=["tokens/react-to/enter-treasure", "cards/draw/cards"],
                facts=[react_treasure, draw_cards],
                commander=True,
            ),
            card(
                "Treasure Maker",
                type_line="Creature — Pirate",
                mana_value=2,
                mana_cost="{1}{R}",
                oracle_text="Create a Treasure token.",
                buckets=["tokens/create/treasure"],
                facts=[create_treasure],
                manual_mana_value=5,
            ),
            card(
                "Second Treasure Maker",
                type_line="Artifact",
                mana_value=2,
                mana_cost="{2}",
                oracle_text="Create a Treasure token.",
                buckets=["tokens/create/treasure"],
                facts=[create_treasure],
            ),
            card(
                "Lonely Scry",
                type_line="Sorcery",
                mana_value=1,
                mana_cost="{U}",
                oracle_text="Scry 2.",
                buckets=["cards/filter/scry"],
                facts=[scry],
            ),
            card(
                "Island",
                type_line="Basic Land — Island",
                mana_value=0,
                oracle_text="{T}: Add {U}.",
                produced_mana=["U"],
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "deck.json"
            write_save(source, title="Evidence Deck", cards=cards)
            session_root = root / "sessions"

            result = self.run_cli("prepare", str(source), "--session-root", str(session_root))

            status = json.loads(result.stdout)
            aggregate_text = Path(status["aggregate"]).read_text(encoding="utf-8")
            aggregate = json.loads(aggregate_text)
            self.assertLessEqual(len(aggregate_text), 40_000)
            self.assertNotIn("IMAGE_CANARY", aggregate_text)
            self.assertNotIn("FULL_OBJECT_CANARY", aggregate_text)
            self.assertNotIn("sourcePath", aggregate_text)
            self.assertNotIn("cardCatalog", aggregate_text)
            self.assertEqual("Evidence Deck", aggregate["deck"]["title"])
            self.assertEqual(["Captain Evidence"], [entry["name"] for entry in aggregate["commanders"]])
            self.assertEqual(5, aggregate["stats"]["cards"])
            self.assertEqual(1, aggregate["stats"]["lands"])
            self.assertEqual("1.00", aggregate["stats"]["averageLandsInOpeningHand"])
            self.assertEqual("3.00", aggregate["stats"]["averageManaValue"])
            self.assertEqual(
                {"0": 0, "1": 1, "2": 1, "3": 0, "4": 1, "5": 1}, aggregate["stats"]["manaCurve"]
            )
            detailed = {entry["id"]: entry for entry in aggregate["granularBuckets"]["detailed"]}
            indexed = {entry["id"]: entry for entry in aggregate["granularBuckets"]["singletonIndex"]}
            self.assertEqual(
                ["Second Treasure Maker", "Treasure Maker"], detailed["tokens/create/treasure"]["cards"]
            )
            self.assertIn("tokens/react-to/enter-treasure", detailed)
            self.assertIn("cards/filter/scry", indexed)
            self.assertNotIn("cards", indexed["cards/filter/scry"])
            self.assertTrue(
                any(
                    edge["fromBucket"] == "tokens/create/treasure"
                    and edge["toBucket"] == "tokens/react-to/enter-treasure"
                    for edge in aggregate["interactionCandidates"]
                )
            )

    def test_query_is_deck_bound_sanitized_and_limited_to_two_rounds(self) -> None:
        producer = fact(
            "tokens/create/treasure", "Create Treasure tokens", role="effect", action="create", kind="token"
        )
        trigger = fact(
            "tokens/react-to/enter-treasure",
            "React to Treasure tokens entering",
            role="trigger",
            action="react-to-enter",
            kind="token",
        )
        alpha_cards = [
            card(
                "Alpha Producer",
                type_line="Creature — Pirate",
                mana_value=2,
                oracle_text="Create a Treasure token.",
                buckets=["tokens/create/treasure"],
                facts=[producer],
            ),
            card(
                "Alpha Trigger",
                type_line="Legendary Creature — Pirate",
                mana_value=3,
                oracle_text="Whenever a Treasure enters, draw a card.",
                buckets=["tokens/react-to/enter-treasure"],
                facts=[trigger],
                commander=True,
            ),
        ]
        beta_cards = [
            card(
                "Beta Canary Card",
                type_line="Legendary Creature — Wizard",
                mana_value=3,
                oracle_text="BETA_ORACLE_CANARY",
                commander=True,
            )
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            alpha_source = root / "alpha.json"
            beta_source = root / "beta.json"
            sessions = root / "sessions"
            write_save(alpha_source, title="Alpha", cards=alpha_cards)
            write_save(beta_source, title="Beta", cards=beta_cards)
            alpha_status = json.loads(
                self.run_cli("prepare", str(alpha_source), "--session-root", str(sessions)).stdout
            )
            self.run_cli("prepare", str(beta_source), "--session-root", str(sessions))
            alpha_session = Path(alpha_status["aggregate"]).parent
            request = root / "request.json"
            request.write_text(
                json.dumps(
                    {
                        "buckets": ["tokens/create/treasure"],
                        "intersections": [
                            ["tokens/create/treasure", "tokens/react-to/enter-treasure"]
                        ],
                        "cards": ["Alpha Producer", "Beta Canary Card"],
                    }
                ),
                encoding="utf-8",
            )
            first_response = root / "first-response.json"

            first = self.run_cli(
                "query",
                str(alpha_session),
                "--request",
                str(request),
                "--response",
                str(first_response),
            )

            first_status = json.loads(first.stdout)
            response_text = first_response.read_text(encoding="utf-8")
            response = json.loads(response_text)
            self.assertEqual(1, first_status["round"])
            self.assertNotIn("Alpha Producer", first.stdout)
            self.assertNotIn("BETA_ORACLE_CANARY", response_text)
            self.assertNotIn("sourcePath", response_text)
            self.assertEqual(["Alpha Producer"], response["buckets"][0]["cards"])
            self.assertEqual(["Alpha Producer"], [entry["name"] for entry in response["cards"]])
            self.assertEqual(["Beta Canary Card"], response["missingCards"])
            self.assertEqual([], response["intersections"][0]["cards"])

            second_response = root / "second-response.json"
            self.run_cli(
                "query",
                str(alpha_session),
                "--request",
                str(request),
                "--response",
                str(second_response),
            )
            third_response = root / "third-response.json"
            exhausted = self.run_cli(
                "query",
                str(alpha_session),
                "--request",
                str(request),
                "--response",
                str(third_response),
                expected_code=2,
            )
            self.assertIn("query-round budget", exhausted.stderr)
            self.assertFalse(third_response.exists())

    def test_write_note_preserves_user_markdown_then_regenerates_its_own_collision_file(self) -> None:
        commander = card(
            "Output Commander",
            type_line="Legendary Creature — Advisor",
            mana_value=3,
            oracle_text="Draw a card.",
            commander=True,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "output.json"
            sessions = root / "sessions"
            write_save(source, title="Output Deck", cards=[commander])
            prepared = json.loads(
                self.run_cli("prepare", str(source), "--session-root", str(sessions)).stdout
            )
            session = Path(prepared["aggregate"]).parent
            intended = Path(prepared["output"])
            intended.write_text("USER AUTHORED\n", encoding="utf-8")
            draft = root / "draft.md"
            draft.write_text(strategy_draft("Output Deck"), encoding="utf-8")

            first = json.loads(
                self.run_cli("write-note", str(session), "--draft", str(draft)).stdout
            )

            actual = Path(first["output"])
            self.assertNotEqual(intended, actual)
            self.assertEqual("USER AUTHORED\n", intended.read_text(encoding="utf-8"))
            generated = actual.read_text(encoding="utf-8")
            self.assertTrue(generated.startswith("<!-- mtg-deck-strategy-notes "))
            self.assertIn("# Output Deck", generated)

            draft.write_text(strategy_draft("Output Deck", final_word="second"), encoding="utf-8")
            second = json.loads(
                self.run_cli("write-note", str(session), "--draft", str(draft)).stdout
            )
            self.assertEqual(str(actual), second["output"])
            self.assertIn("second.", actual.read_text(encoding="utf-8"))

    def test_write_note_rejects_a_draft_without_a_deck_snapshot(self) -> None:
        commander = card(
            "Snapshot Commander",
            type_line="Legendary Creature — Advisor",
            mana_value=3,
            oracle_text="Draw a card.",
            commander=True,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "snapshot.json"
            sessions = root / "sessions"
            write_save(source, title="Snapshot Deck", cards=[commander])
            prepared = json.loads(
                self.run_cli("prepare", str(source), "--session-root", str(sessions)).stdout
            )
            session = Path(prepared["aggregate"]).parent
            draft = root / "draft.md"
            draft.write_text(
                strategy_draft("Snapshot Deck").replace(
                    "## Deck Snapshot\nThe curve, card types, and granular buckets show a compact resource engine.\n\n",
                    "",
                ),
                encoding="utf-8",
            )

            result = self.run_cli(
                "write-note", str(session), "--draft", str(draft), expected_code=2
            )

            self.assertIn("missing required headings", result.stderr)

    def test_write_note_rejects_a_draft_above_the_concise_ceiling(self) -> None:
        commander = card(
            "Concise Commander",
            type_line="Legendary Creature — Advisor",
            mana_value=3,
            oracle_text="Draw a card.",
            commander=True,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "concise.json"
            sessions = root / "sessions"
            write_save(source, title="Concise Deck", cards=[commander])
            prepared = json.loads(
                self.run_cli("prepare", str(source), "--session-root", str(sessions)).stdout
            )
            session = Path(prepared["aggregate"]).parent
            draft = root / "draft.md"
            draft.write_text(
                strategy_draft("Concise Deck", filler_repetitions=500), encoding="utf-8"
            )

            result = self.run_cli(
                "write-note", str(session), "--draft", str(draft), expected_code=2
            )

            self.assertIn("600-1500 words", result.stderr)


if __name__ == "__main__":
    unittest.main()
