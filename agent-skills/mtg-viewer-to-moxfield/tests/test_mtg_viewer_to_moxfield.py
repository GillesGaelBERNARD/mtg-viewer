from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "mtg_viewer_to_moxfield.py"
SPEC = importlib.util.spec_from_file_location("mtg_viewer_to_moxfield", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class MoxfieldPrintingExportTests(unittest.TestCase):
    def test_renders_exact_printing_and_finish_without_merging_variants(self) -> None:
        data = {
            "deckTitle": "Printing test",
            "cards": [
                {
                    "name": "Sol Ring",
                    "setCode": "cmm",
                    "collectorNumber": "410",
                    "finish": "foil",
                    "isCommander": False,
                },
                {
                    "name": "Sol Ring",
                    "setCode": "cmm",
                    "collectorNumber": "410",
                    "finish": "foil",
                    "isCommander": False,
                },
                {
                    "name": "Sol Ring",
                    "setCode": "c21",
                    "collectorNumber": "263",
                    "finish": "nonfoil",
                    "isCommander": False,
                },
                {
                    "name": "Muldrotha, the Gravetide",
                    "setCode": "fdn",
                    "collectorNumber": "243",
                    "finish": "etched",
                    "isCommander": True,
                },
            ],
        }

        converted = MODULE.convert_data(data, Path("synthetic.mtg-viewer.json"))

        self.assertEqual(
            MODULE.render_deck(converted),
            "Commander\n"
            "1 Muldrotha, the Gravetide (FDN) 243 *E*\n"
            "\n"
            "Deck\n"
            "2 Sol Ring (CMM) 410 *F*\n"
            "1 Sol Ring (C21) 263\n",
        )

    def test_uses_resolved_scryfall_metadata_for_legacy_cards(self) -> None:
        card_id = "da1884db-40cf-4064-9246-3b25c60c46c1"
        data = {
            "cards": [
                {
                    "name": "Muldrotha, the Gravetide",
                    "scryfallId": card_id,
                    "isCommander": True,
                }
            ]
        }

        converted = MODULE.convert_data(
            data,
            Path("legacy.mtg-viewer.json"),
            {card_id: {"set_code": "fdn", "collector_number": "243"}},
        )

        self.assertIn("1 Muldrotha, the Gravetide (FDN) 243", MODULE.render_deck(converted))

    def test_compact_decklist_fallback_keeps_moxfield_print_specifiers(self) -> None:
        data = {
            "decklist": (
                "2 Sol Ring (CMM) 410 *F*\n"
                "1 Braided Net // Braided Quipu (LCI) 47\n"
            )
        }

        converted = MODULE.convert_data(data, Path("compact.mtg-viewer.json"))

        self.assertEqual(
            MODULE.render_deck(converted),
            "Deck\n"
            "2 Sol Ring (CMM) 410 *F*\n"
            "1 Braided Net // Braided Quipu (LCI) 47\n",
        )


if __name__ == "__main__":
    unittest.main()
