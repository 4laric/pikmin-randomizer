"""Focused P0 contract tests for the ch_MAT_route_rover adapter (#561).

The adapter module is loaded from its file path (no package init is owned by
this lane) and exercised against the real pinned sources: the lane-plan
entry, the inventory stage row and the 30-stage challenge collection with
its hash pins. Positive tests pin actual stage metadata, timers, populations
and collection integrity; negative tests prove fail-closed boundaries for
drifted, duplicated, corrupted or missing inputs. Nothing here generates
placements, scores or completion claims.
"""

import copy
import importlib.util
import json
import unittest
from pathlib import Path


def _root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "docs" / "PIKMIN_CONTENT_IMPORT_LANES.json").is_file():
            return parent
    raise AssertionError("Repository root with content plan not found")


ROOT = _root()

STAGE_SHA256 = "e03eb33a78526adb13eebd08af453555bc9cd219f6a3e624b28a0771ea12cb79"
STAGES_SHA256 = "59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1"


def _load_adapter():
    path = ROOT / "experimental" / "content_lanes" / "p2-challenge-ch_mat_route_rover.py"
    spec = importlib.util.spec_from_file_location("matrouterover_adapter", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ADAPTER = _load_adapter()


def _inputs():
    plan = json.loads((ROOT / "docs" / "PIKMIN_CONTENT_IMPORT_LANES.json")
                      .read_text(encoding="utf-8"))
    plan_entry = next(lane for lane in plan["lanes"]
                      if lane.get("lane") == "p2-challenge-ch_mat_route_rover")
    inventory = json.loads((ROOT / "docs" / "PIKMIN2_CONTENT_INVENTORY.json")
                           .read_text(encoding="utf-8"))
    challenge = inventory["challenge"]
    stage = next(row for row in challenge["stages"]
                 if row.get("cave_id") == "ch_MAT_route_rover")
    return (plan_entry, stage, challenge, inventory["source_sha256"])


class MatRouteRoverContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.args = _inputs()

    def test_real_sources_validate(self):
        result = ADAPTER.packet(*self.args)
        self.assertEqual(result["lane"], "p2-challenge-ch_mat_route_rover")
        self.assertEqual(result["phase"], "P0")
        self.assertEqual(result["identity"]["source_id"], "ch_MAT_route_rover")
        self.assertEqual(result["details"]["floors"], 1)
        self.assertEqual(result["details"]["floor_seconds"], [90.0])
        self.assertEqual(result["details"]["ui_index"], 27)
        self.assertEqual(result["details"]["table_order"], 21)
        self.assertEqual(result["generated"], False)
        self.assertEqual(result["placements"], [])
        self.assertEqual(result["collection"]["stages"], 30)

    def test_ledger_conserves_definitions(self):
        result = ADAPTER.packet(*self.args)
        ledger = result["ledger"]
        self.assertEqual(ledger["starting_pikmin_total"], 60)
        self.assertEqual(ledger["starting_populations"],
                         [{"native_color": 0, "maturity": 2, "count": 20},
                          {"native_color": 1, "maturity": 2, "count": 20},
                          {"native_color": 2, "maturity": 2, "count": 20}])
        self.assertEqual(ledger["floor_timer_total"], 90.0)
        self.assertEqual(ledger["legacy_time"], 300.0)
        self.assertEqual((ledger["bitter_sprays"], ledger["spicy_sprays"]), (2, 2))
        self.assertEqual(ledger["treasure_count_field"], 0)

    def test_floor_coverage_complete(self):
        result = ADAPTER.packet(*self.args)
        coverage = result["floor_coverage"]
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["floors"], 1)
        self.assertEqual(coverage["timer_count"], 1)
        self.assertEqual(coverage["timer_total"], 90.0)
        self.assertEqual(coverage["coverage"], "floor 1..1")

    def test_resource_closure_names_owners(self):
        result = ADAPTER.packet(*self.args)
        closure = result["resource_closure"]
        self.assertEqual(closure["stage definition bytes"]["status"], "pinned-not-read")
        self.assertIn(STAGE_SHA256, closure["stage definition bytes"]["detail"])
        self.assertEqual(closure["stage table ordering"]["status"], "pinned-not-read")
        self.assertIn("#136", closure["starting roster, sprays and timers"]["owner"])
        self.assertEqual(closure["TheKey/hole/geyser, scoring, retry, result semantics"]["status"],
                         "unsupported-reference")

    def test_hash_pins_match_plan(self):
        result = ADAPTER.packet(*self.args)
        self.assertEqual(result["collection"]["stage_sha256"], STAGE_SHA256)
        self.assertEqual(result["collection"]["stages_txt_sha256"], STAGES_SHA256)
        self.assertEqual(result["collection"]["challenge_floor_total"], 59)

    def test_roster_decode_stays_open_and_chal0_not_challenge(self):
        result = ADAPTER.packet(*self.args)
        self.assertIn("no roster values invented", result["floor_roster_decode"])
        self.assertTrue(any("chal0" in blocker for blocker in result["blockers"]))
        self.assertTrue(any("UI index 27" in blocker for blocker in result["blockers"]))

    def test_cli_writes_packet(self):
        import tempfile
        plan_entry, stage, challenge, hashes = self.args
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {}
            for name, value in (("plan.json", plan_entry),
                                ("stage.json", stage),
                                ("collection.json", {"stages": challenge["stages"],
                                                     "source_sha256": hashes})):
                path = root / name
                path.write_text(json.dumps(value), encoding="utf-8")
                files[name] = str(path)
            out = root / "packet.json"
            ADAPTER.main(["--plan-entry", files["plan.json"],
                          "--inventory-stage", files["stage.json"],
                          "--inventory-collection", files["collection.json"],
                          "--output", str(out)])
            packet = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(packet["details"]["floors"], 1)
            self.assertRegex(packet["packet_sha256"], r"[0-9a-f]{64}")

    def test_wrong_lane_and_label_rejected(self):
        plan_entry = copy.deepcopy(self.args[0])
        plan_entry["lane"] = "p2-challenge-ch_mat_flier"
        with self.assertRaises(ValueError):
            ADAPTER.packet(plan_entry, *self.args[1:])
        plan_entry = copy.deepcopy(self.args[0])
        plan_entry["label"] = "P2 Challenge 27: wrong"
        with self.assertRaises(ValueError):
            ADAPTER.packet(plan_entry, *self.args[1:])

    def test_timer_and_floor_drift_rejected(self):
        _, stage, challenge, hashes = self.args
        plan_entry = copy.deepcopy(self.args[0])
        plan_entry["details"]["floor_seconds"] = [999.0]
        with self.assertRaises(ValueError):
            ADAPTER.packet(plan_entry, stage, challenge, hashes)
        bad_stage = copy.deepcopy(stage)
        bad_stage["floors"] = 2
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], bad_stage, challenge, hashes)
        bad_stage = copy.deepcopy(stage)
        bad_stage["floor_seconds"] = []
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], bad_stage, challenge, hashes)

    def test_population_and_spray_drift_rejected(self):
        bad_stage = copy.deepcopy(self.args[1])
        bad_stage["pikmin_by_native_color_and_maturity"][0] = [0, 0, 21]
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], bad_stage, *self.args[2:])
        bad_stage = copy.deepcopy(self.args[1])
        bad_stage["bitter_sprays"] = 9
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], bad_stage, *self.args[2:])
        bad_stage = copy.deepcopy(self.args[1])
        bad_stage["legacy_time"] = 301.0
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], bad_stage, *self.args[2:])

    def test_duplicate_row_and_index_collision_rejected(self):
        _, stage, challenge, hashes = self.args
        dup = copy.deepcopy(challenge)
        dup["stages"] = challenge["stages"] + [copy.deepcopy(stage)]
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], stage, dup, hashes)
        collided = copy.deepcopy(challenge)
        collided["stages"][0]["table_order"] = 21
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], stage, collided, hashes)
        gap = copy.deepcopy(challenge)
        gap["stages"] = gap["stages"][:-1]
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], stage, gap, hashes)

    def test_floor_total_drift_rejected(self):
        _, stage, challenge, hashes = self.args
        broken = copy.deepcopy(challenge)
        broken["stages"][0]["floors"] = broken["stages"][0]["floors"] + 1
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], stage, broken, hashes)

    def test_missing_and_placeholder_hash_rejected(self):
        hashes = dict(self.args[3])
        hashes.pop("user/Mukki/mapunits/caveinfo/ch_MAT_route_rover.txt")
        with self.assertRaises(ValueError):
            ADAPTER.packet(*self.args[:3], hashes)
        hashes = dict(self.args[3])
        hashes["user/Matoba/challenge/stages.txt"] = "0" * 64
        with self.assertRaises(ValueError):
            ADAPTER.packet(*self.args[:3], hashes)

    def test_plan_pin_mismatch_rejected(self):
        plan_entry = copy.deepcopy(self.args[0])
        plan_entry["source_sha256"] = "a" * 64
        with self.assertRaises(ValueError):
            ADAPTER.packet(plan_entry, *self.args[1:])

    def test_corrupt_and_missing_files_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "absent.json"
            with self.assertRaises(ValueError):
                ADAPTER.load_json(missing)
            corrupt = Path(directory) / "corrupt.json"
            corrupt.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ValueError):
                ADAPTER.load_json(corrupt)


if __name__ == "__main__":
    unittest.main()

class MatRouteRoverP1ImportTests(unittest.TestCase):
    """P1 import-path tests: squad/entry/manifest writers, marker parser,
    guard record. Pure-Python boundaries; runtime evidence is validated from
    real native logs, never synthesized here."""

    def test_species_rows_map_positionally(self):
        self.assertEqual(
            [ADAPTER.p1_species_for_row(r) for r in (0, 1, 2)], [0, 1, 2])
        for bad in (3, 6, -1, True, "0", None):
            with self.assertRaises(ValueError):
                ADAPTER.p1_species_for_row(bad)

    def test_stage_squad_totals(self):
        squad = ADAPTER.p1_stage_squad()
        self.assertEqual(squad, [(0, 2, 20), (1, 2, 20), (2, 2, 20)])
        self.assertEqual(ADAPTER.p1_squad_total(squad), 60)

    def test_entry_writer_grammar(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "p2-cave-entry.txt"
            result = ADAPTER.p1_write_cave_entry(
                str(path), "767135fd1617a1e9c67520f455e7f369", 1, 1.0,
                ADAPTER.p1_stage_squad())
            self.assertEqual(result["squad_total"], 60)
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0],
                             "P2_CAVE_ENTRY_1 767135fd1617a1e9c67520f455e7f369 1 1.0 60")
            self.assertEqual(len(lines), 61)
            self.assertEqual(lines[1:21], ["0 2"] * 20)
            self.assertEqual(lines[21:41], ["1 2"] * 20)
            self.assertEqual(lines[41:61], ["2 2"] * 20)
            for token, floor, health, squad in (
                    ("", 1, 1.0, ADAPTER.p1_stage_squad()),
                    ("t", 2, 1.0, ADAPTER.p1_stage_squad()),
                    ("t", 1, 0.0, ADAPTER.p1_stage_squad()),
                    ("t", 1, 1.0, [(0, 2, 0)]),
                    ("t", 1, 1.0, [(9, 2, 1)]),
                    ("t", 1, 1.0, [(0, 1, 1)])):
                with self.assertRaises(ValueError):
                    ADAPTER.p1_write_cave_entry(
                        str(path), token, floor, health, squad)

    def test_generate_writer_grammar(self):
        import tempfile
        units = [{"idx": 0, "name": "room_bunki7x7_8_tile", "w": 7, "d": 7,
                  "kind": 1}]
        rooms = [{"idx": 0, "unit": 0, "turn": 0, "ox": 0, "oy": 0, "oz": 0}]
        spawns = [{"id": "KumaChappy", "count": 3}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "p2-cave-generate.txt"
            ADAPTER.p1_write_generate_manifest(
                str(path), "1_units_bunki_2_tile.txt", units, rooms, [], [],
                spawns, "hole")
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("P2_CAVE_GENERATE_1\n"))
            self.assertIn("spawn KumaChappy 3", text)
            self.assertTrue(text.endswith("anchor hole\n"))
            for kw in ("pool", "rooms 1", "doors 0", "links 0", "spawns 1"):
                self.assertIn(kw, text)
            with self.assertRaises(ValueError):
                ADAPTER.p1_write_generate_manifest(
                    str(path), "pool.txt", [], rooms, [], [], spawns, "hole")
            with self.assertRaises(ValueError):
                ADAPTER.p1_write_generate_manifest(
                    str(path), "pool.txt", units, rooms, [], [], spawns,
                    "stairs")
            with self.assertRaises(ValueError):
                ADAPTER.p1_write_generate_manifest(
                    str(path), "pool.txt", units, rooms, [], [],
                    [{"id": "KumaChappy", "count": 0}], "hole")

    def test_layout_builder_from_decoded_packets(self):
        cave = {"floor_count": 1, "floors": [{"enemies": [
            {"enemy_id": "KumaChappy", "source_weight": 10},
            {"enemy_id": "KumaChappy", "source_weight": 10},
            {"enemy_id": "KumaChappy", "source_weight": 10},
            {"enemy_id": "KumaKochappy", "source_weight": 20},
            {"enemy_id": "KumaKochappy", "source_weight": 20}]}]}
        units = {"pool": "user/Mukki/mapunits/units/1_units_bunki_2_tile.txt",
                 "units": [
                     {"name": "item_cap_pipe", "cells": [1, 1], "kind": 0},
                     {"name": "way3_pipe", "cells": [1, 1], "kind": 2},
                     {"name": "way4_pipe", "cells": [1, 1], "kind": 2},
                     {"name": "wayl_pipe", "cells": [1, 1], "kind": 2},
                     {"name": "way2_pipe", "cells": [1, 1], "kind": 2},
                     {"name": "way2x2_pipe", "cells": [1, 2], "kind": 2},
                     {"name": "room_bunki7x7_8_tile", "cells": [7, 7],
                      "kind": 1}]}
        layout = ADAPTER.p1_route_rover_layout(cave, units)
        self.assertEqual(layout["pool"], "1_units_bunki_2_tile.txt")
        self.assertEqual(len(layout["units"]), 7)
        self.assertEqual(layout["rooms"][0]["unit"], 6)
        self.assertEqual(layout["spawns"], [
            {"id": "KumaChappy", "count": 3},
            {"id": "KumaKochappy", "count": 4}])
        self.assertEqual(layout["anchor"], "hole")

    def test_marker_parser_absent_stays_absent(self):
        facts = ADAPTER.p1_parse_markers("nothing here\n")
        self.assertIsNone(facts["window"])
        self.assertEqual(facts["fps"], 0)
        self.assertEqual(facts["generate_markers"], [])
        self.assertEqual(facts["restores"], [])
        log = ("Experimental preview window set to 960x540 windowed and centered\n"
               "[PC Port] FPS: 60\n[PC Port] FPS: 61\n"
               "P2_CAVE_GENERATE_PASS rooms=1 spawns=2 links=0 anchor=hole\n"
               "P2_CAVE_RESTORE species=0 maturity=2\n"
               "P2_CAVE_NAV seq=1 floor=1 captain=1 x=0 y=0 z=0 heading_rad=0 "
               "anchor_x=0 anchor_y=0 anchor_z=0 dx=0 dz=0 horizontal=0 "
               "vertical=0 radius=20 inside=1 state=7 walk=0 safe=1 pause=0 "
               "ui=0 movie=0 day_end=0 completed=0 pod=0 "
               "interaction_eligible=1 marker=ok draws=1\n")
        facts = ADAPTER.p1_parse_markers(log)
        self.assertEqual(facts["window"], "960x540")
        self.assertEqual(facts["fps"], 2)
        self.assertEqual(len(facts["generate_markers"]), 1)
        self.assertEqual(len(facts["restores"]), 1)
        self.assertEqual(facts["nav_lines"], 1)

    def test_guard_record_fail_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "noguard.h"
            bad.write_text("int x = 1;\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                ADAPTER.p1_captain_guard_record(str(bad))
