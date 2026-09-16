"""Multi-floor checkpoint identity tests (issue #132).

The legacy two-floor Emergence loop is the baseline, never a
reimplementation target: default `floors=2` behavior is pinned
byte-identical, and every extension is exercised with an explicit floor
count. No native build, no level run, no admission claim.
"""
import unittest

from experimental.pikmin2_campaign import (
    MAX_FLOORS,
    entry_text,
    initial,
    transfer_schema,
    transition,
    validate,
)

TOKEN = "a" * 32
CONTENT = "b" * 64


def reds(n, maturity=0):
    return [dict(species="red", maturity=maturity) for _ in range(n)]


def walk(floors, squad_size=2):
    """Drive initial() through every floor; return the exited checkpoint.

    The supervisor writes entries; the native engine answers with transfers,
    so each entry is converted to the transfer header before transition,
    exactly as the room handoff does.
    """
    state = initial(CONTENT)
    for floor in range(1, floors + 1):
        text = entry_text(state, TOKEN, floors).replace(
            "P2_CAVE_ENTRY_", "P2_CAVE_TRANSFER_", 1)
        state = transition(state, TOKEN, text, {}, {}, floors)
    return state


class SchemaBumpTests(unittest.TestCase):
    def test_known_transfer_schemas(self):
        self.assertEqual(transfer_schema("P2_CAVE_TRANSFER_1"), 1)
        self.assertEqual(transfer_schema("P2_CAVE_TRANSFER_2"), 2)
        self.assertEqual(transfer_schema("P2_CAVE_TRANSFER_3"), 3)

    def test_unknown_schema_rejected_never_latest(self):
        # The bump rule: an unknown version is rejected explicitly, never
        # treated as the latest known schema.
        with self.assertRaisesRegex(ValueError, "Unsupported cave transfer schema"):
            transfer_schema("P2_CAVE_TRANSFER_4")
        with self.assertRaisesRegex(ValueError, "Stale or incomplete cave transfer"):
            transfer_schema("P2_CAVE_ENTRY_3")


class DefaultRangeTests(unittest.TestCase):
    def test_default_floors_rejects_floor_beyond_2(self):
        state = dict(initial(CONTENT), floor=3, revision=2)
        with self.assertRaisesRegex(ValueError, "Invalid cave destination"):
            validate(state)

    def test_floors_parameter_bounds(self):
        state = initial(CONTENT)
        for bad in (1, 17, 0, -1, "7", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    validate(state, bad)
        validate(state, 16)

    def test_legacy_entry_text_byte_identical(self):
        state = dict(initial(CONTENT), squad=reds(2))
        text = entry_text(state, TOKEN)
        self.assertEqual(text, f"P2_CAVE_ENTRY_1\n{TOKEN}\n1 1 2\n1 0\n1 0\n")
        self.assertNotIn("P2_CAVE_CHAIN", text)

    def test_legacy_two_floor_walk_unchanged(self):
        state = walk(2)
        self.assertEqual((state["status"], state["floor"], state["revision"]), ("exited", 2, 2))


class TrailingDataTests(unittest.TestCase):
    def test_legacy_trailing_line_rejected(self):
        state = dict(initial(CONTENT), squad=reds(2))
        text = entry_text(state, TOKEN).replace("P2_CAVE_ENTRY", "P2_CAVE_TRANSFER")
        with self.assertRaisesRegex(ValueError, "Invalid transfer floor/population"):
            transition(state, TOKEN, text + "0 0\n", {}, {})

    def test_chained_payload_needs_exactly_one_chain_line(self):
        state = dict(initial(CONTENT), squad=reds(2))
        chained = entry_text(
            dict(state, floor=3, revision=2), TOKEN, 7).replace("P2_CAVE_ENTRY", "P2_CAVE_TRANSFER")
        with self.assertRaisesRegex(ValueError, "Invalid transfer floor/population"):
            transition(dict(state, floor=3, revision=2),
                       TOKEN, chained + "P2_CAVE_CHAIN 3 2\n", {}, {}, 7)

    def test_bad_chain_marker_rejected(self):
        state = dict(initial(CONTENT), squad=reds(2))
        chained = entry_text(
            dict(state, floor=3, revision=2), TOKEN, 7).replace("P2_CAVE_ENTRY", "P2_CAVE_TRANSFER")
        broken = chained.replace("P2_CAVE_CHAIN", "P2_CAVE_CHAIM")
        with self.assertRaisesRegex(ValueError, "Invalid transfer floor/population"):
            transition(dict(state, floor=3, revision=2), TOKEN, broken, {}, {}, 7)

    def test_chain_floor_mismatch_rejected(self):
        state = dict(initial(CONTENT), squad=reds(2))
        chained = entry_text(
            dict(state, floor=3, revision=2), TOKEN, 7).replace("P2_CAVE_ENTRY", "P2_CAVE_TRANSFER")
        broken = chained.replace("P2_CAVE_CHAIN 3 2", "P2_CAVE_CHAIN 4 2")
        with self.assertRaisesRegex(ValueError, "Invalid transfer floor/population"):
            transition(dict(state, floor=3, revision=2), TOKEN, broken, {}, {}, 7)

    def test_chain_revision_mismatch_rejected(self):
        state = dict(initial(CONTENT), squad=reds(2))
        chained = entry_text(
            dict(state, floor=3, revision=2), TOKEN, 7).replace("P2_CAVE_ENTRY", "P2_CAVE_TRANSFER")
        broken = chained.replace("P2_CAVE_CHAIN 3 2", "P2_CAVE_CHAIN 3 9")
        with self.assertRaisesRegex(ValueError, "Cave revision chain broken"):
            transition(dict(state, floor=3, revision=2), TOKEN, broken, {}, {}, 7)

    def test_unchained_payload_beyond_floor_2_rejected(self):
        # Mirrors the native legacy parser: unchained payloads stop at floor 2.
        state = dict(initial(CONTENT), squad=reds(2))
        chained = entry_text(
            dict(state, floor=5, revision=4), TOKEN, 7).replace("P2_CAVE_ENTRY", "P2_CAVE_TRANSFER")
        unchained = "\n".join(
            line for line in chained.splitlines() if not line.startswith("P2_CAVE_CHAIN")) + "\n"
        with self.assertRaisesRegex(ValueError, "Invalid transfer floor/population"):
            transition(dict(state, floor=5, revision=4), TOKEN, unchained, {}, {}, 7)


class MultifloorRoundTripTests(unittest.TestCase):
    def test_seven_floor_walk_exits_with_revision_chain(self):
        state = walk(7)
        self.assertEqual(state["status"], "exited")
        self.assertEqual(state["floor"], 7)
        self.assertEqual(state["revision"], 7)
        self.assertEqual(len(state["squad"]), 20)

    def test_chain_line_present_only_beyond_floor_2(self):
        state = initial(CONTENT)
        plain = entry_text(state, TOKEN, 7)
        self.assertNotIn("P2_CAVE_CHAIN", plain)
        deep = entry_text(dict(state, floor=5, revision=4), TOKEN, 7)
        self.assertIn("P2_CAVE_CHAIN 5 4\n", deep)

    def test_mid_walk_checkpoint_validates(self):
        state = initial(CONTENT)
        for floor in range(1, 5):
            text = entry_text(state, TOKEN, 7).replace(
                "P2_CAVE_ENTRY_", "P2_CAVE_TRANSFER_", 1)
            state = transition(state, TOKEN, text, {}, {}, 7)
        validate(state, 7)
        self.assertEqual((state["floor"], state["revision"], state["status"]), (5, 4, "active"))

    def test_wrong_revision_rejected(self):
        state = dict(initial(CONTENT), floor=5, revision=3, squad=reds(2))
        with self.assertRaisesRegex(ValueError, "Invalid cave checkpoint phase"):
            validate(state, 7)

    def test_failed_checkpoint_on_any_floor(self):
        state = dict(initial(CONTENT), floor=5, revision=5, squad=[], health=0.0, status="failed")
        validate(state, 7)
        live_text = entry_text(
            dict(initial(CONTENT), floor=5, revision=4), TOKEN, 7).replace(
                "P2_CAVE_ENTRY_", "P2_CAVE_TRANSFER_", 1)
        with self.assertRaisesRegex(ValueError, "Cave already ended"):
            transition(state, TOKEN, live_text, {}, {}, 7)


class PurpleHeadroomTests(unittest.TestCase):
    def transfer_with(self, floor, staged_purple, transfer_purple, floors=2):
        staged = reds(12) + [dict(species="purple", maturity=0)] * staged_purple
        state = dict(initial(CONTENT), floor=floor,
                     revision=floor - 1, squad=staged)
        validate(state, floors)
        squad = reds(2) + [dict(species="purple", maturity=0)] * transfer_purple
        lines = [f"P2_CAVE_TRANSFER_1", TOKEN,
                 f"{floor} 1.0 {len(squad)}"]
        lines += [f"{['blue', 'red', 'yellow', 'purple', 'white', 'bulbmin'].index(p['species'])} {p['maturity']}"
                  for p in squad]
        if floor > 2:
            lines.append(f"P2_CAVE_CHAIN {floor} {floor - 1}")
        return transition(state, TOKEN, "\n".join(lines) + "\n", {}, {}, floors)

    def test_floor_2_purple_plus_ten_preserved(self):
        state = self.transfer_with(2, staged_purple=1, transfer_purple=11)
        self.assertEqual(state["status"], "exited")

    def test_floor_3_purple_increase_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unexpected cave species increase"):
            self.transfer_with(3, staged_purple=1, transfer_purple=2, floors=7)

    def test_floor_1_purple_increase_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unexpected cave species increase"):
            self.transfer_with(1, staged_purple=0, transfer_purple=1)

    def test_floor_3_purple_stable_accepted(self):
        state = self.transfer_with(3, staged_purple=1, transfer_purple=1, floors=7)
        self.assertEqual((state["status"], state["floor"]), ("active", 4))


if __name__ == "__main__":
    unittest.main()
