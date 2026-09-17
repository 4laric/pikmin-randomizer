"""Focused P0 tests for the ch_ABEM_LeafChappy import contract (#550)
plus the P1 runtime import layer below (same issue, worker muse-l52)."""
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
import copy
import tempfile
import unittest
from pathlib import Path

import experimental.content_lanes.p2_challenge_ch_abem_leafchappy as ch

ENEMIES = {'Chappy', 'KareOoinu_s'}
TREASURES = {'gem_one'}
LANES_PLAN = Path('docs/PIKMIN_CONTENT_IMPORT_LANES.json')
INVENTORY = Path('docs/PIKMIN2_CONTENT_INVENTORY.json')


def stage_text(floors=2):
    head = '{ {c000} 4 %d {_eof} } %d\n' % (floors, floors)
    body = ''
    for i in range(floors):
        body += ('{ {f000} 4 %d {f001} 4 %d {f008} -1 pool.txt {f015} 4 0 {_eof} }\n'
                 '{ 1 Chappy 10 1 }\n{ 0 }\n{ 0 }\n' % (i, i))
    return head + body


def baseline_details():
    import json
    lanes = json.loads(LANES_PLAN.read_text(encoding='utf-8'))
    entry = next(l for l in lanes['lanes']
                 if l['lane'] == 'p2-challenge-ch_abem_leafchappy')
    return copy.deepcopy(entry['details'])


class HashPinTests(unittest.TestCase):
    def test_pin_format_and_triple_consistency(self):
        self.assertRegex(ch.SOURCE_SHA256, r'^[0-9a-f]{64}$')
        self.assertTrue(ch.hash_pin_consistency(str(LANES_PLAN), str(INVENTORY)))

    def test_pin_drift_fails_closed(self):
        import json
        lanes = json.loads(LANES_PLAN.read_text(encoding='utf-8'))
        for lane in lanes['lanes']:
            if lane['lane'] == 'p2-challenge-ch_abem_leafchappy':
                lane['source_sha256'] = '0' * 64
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'lanes.json'
            bad.write_text(json.dumps(lanes))
            with self.assertRaises(ValueError):
                ch.hash_pin_consistency(str(bad), str(INVENTORY))
            with self.assertRaises(ValueError):
                ch.hash_pin_consistency(str(LANES_PLAN), str(Path(tmp) / 'missing.json'))

    def test_verify_hash_logic(self):
        with self.assertRaises(ValueError):
            ch.verify_source_hash(b'wrong bytes for this stage')
        with self.assertRaises(ValueError):
            ch.verify_source_hash(b'')
        with self.assertRaises(ValueError):
            ch.verify_source_hash(None)
        self.assertEqual(len(ch.sha256_bytes(b'abc')), 64)
        with self.assertRaises(ValueError):
            ch.sha256_bytes('abc')


class MetadataTests(unittest.TestCase):
    def test_embedded_baseline_validates(self):
        result = ch.validate_stage_metadata(dict(ch.BASELINE_METADATA))
        self.assertEqual(result['starting_pikmin'], 30)
        self.assertEqual(result['floor_seconds'], [85.0, 100.0])
        self.assertEqual(result['ui_index'], 17)
        self.assertEqual((result['bitter_sprays'], result['spicy_sprays']), (1, 1))
        self.assertEqual(result['treasure_count_field'], 11)

    def test_live_lane_entry_agrees(self):
        report = ch.metadata_agreement(baseline_details())
        self.assertTrue(report['agrees'], report['mismatches'])

    def test_malformed_metadata_fails_closed(self):
        good = dict(ch.BASELINE_METADATA)
        zero = [[0, 0, 0]] * 7
        cases = [
            dict(good, floors=1),
            dict(good, floors='2'),
            dict(good, pikmin_by_native_color_and_maturity=[[0, 0, 0]] * 6 + [[[0]]]),
            dict(good, pikmin_by_native_color_and_maturity=[[0, 0, 0]] * 6),
            dict(good, pikmin_by_native_color_and_maturity=zero),
            dict(good, pikmin_by_native_color_and_maturity='matrix'),
            dict(good, legacy_time=-5),
            dict(good, legacy_time='nan'),
            dict(good, legacy_time='x'),
            dict(good, bitter_sprays=-1),
            dict(good, spicy_sprays=100),
            dict(good, treasure_count_field='x'),
            dict(good, ui_index=30),
            dict(good, ui_index=-1),
            dict(good, floor_seconds=[]),
            dict(good, floor_seconds=[85.0]),
            dict(good, floor_seconds=[85.0, 0]),
            dict(good, floor_seconds=['x']),
        ]
        for details in cases:
            with self.subTest(details=str(details)[:70]), self.assertRaises(ValueError):
                ch.validate_stage_metadata(details)
        broken = dict(good)
        del broken['ui_index']
        with self.assertRaises(ValueError):
            ch.validate_stage_metadata(broken)
        with self.assertRaises(ValueError):
            ch.validate_stage_metadata('not-a-mapping')

    def test_agreement_detects_drift(self):
        drifted = dict(ch.BASELINE_METADATA, spicy_sprays=9)
        report = ch.metadata_agreement(drifted)
        self.assertFalse(report['agrees'])
        drifted = dict(ch.BASELINE_METADATA, floor_seconds=(85.0, 999.0))
        self.assertFalse(ch.metadata_agreement(drifted)['agrees'])
        drifted = dict(ch.BASELINE_METADATA,
                       pikmin_by_native_color_and_maturity=tuple([0, 0, 0] for _ in range(7)))
        with self.assertRaises(ValueError):
            ch.metadata_agreement(drifted)


class DecodeBoundaryTests(unittest.TestCase):
    def test_two_floor_stage_decodes(self):
        parsed = ch.decode_source(stage_text(), ENEMIES, TREASURES)
        self.assertEqual(parsed['floor_count'], 2)
        self.assertEqual(ch.occupied_floors(parsed), [1, 2])
        coverage = ch.validate_floor_coverage(parsed)
        self.assertEqual(coverage, [{'floor': 1, 'covered': True},
                                    {'floor': 2, 'covered': True}])

    def test_missing_text_and_references_fail_closed(self):
        for bad in ('', '   ', None):
            with self.assertRaises(ValueError):
                ch.decode_source(bad, ENEMIES, TREASURES)
        with self.assertRaises(ValueError):
            ch.decode_source(stage_text(), None, TREASURES)
        with self.assertRaises(ValueError):
            ch.decode_source(stage_text(), ENEMIES, None)

    def test_malformed_definitions_fail_closed(self):
        good = stage_text()
        cases = [
            good.replace('{ {c000} 4 2 {_eof} } 2', '{ {c000} 4 3 {_eof} } 2'),
            good.replace('{f008} -1 pool.txt', '{f008} 4 pool.txt'),
            good.replace('pool.txt', '../pool.txt'),
            good.replace('Chappy 10 1', 'Nope 10 1'),
            good.replace('Chappy 10 1', 'Chappy x 1'),
            good + ' trailing',
            good[:-2],
        ]
        for text in cases:
            with self.subTest(text=text[:60]), self.assertRaises(ValueError):
                ch.decode_source(text, ENEMIES, TREASURES)

    def test_wrong_floor_count_breaks_coverage(self):
        for count in (1, 3):
            parsed = ch.decode_source(stage_text(floors=count), ENEMIES, TREASURES)
            with self.assertRaises(ValueError):
                ch.validate_floor_coverage(parsed)

    def test_occupied_floors_rejects_non_struct(self):
        for bad in (None, {}, {'floors': None}, {'floors': [{'first_floor': 0, 'last_floor': 1}]}):
            with self.assertRaises(ValueError):
                ch.occupied_floors(bad)


class SourceBoundaryTests(unittest.TestCase):
    def test_missing_source_file_exact_error(self):
        with self.assertRaisesRegex(ValueError, 'Source unavailable'):
            ch.read_source_file('user/Mukki/mapunits/caveinfo/ch_ABEM_LeafChappy.txt')

    def test_missing_iso_exact_prerequisite(self):
        with self.assertRaisesRegex(ValueError, 'retail ISO not present'):
            ch.read_iso_entry('output/pikmin2-runtime/pikmin2-source-test.iso')

    def test_non_retail_iso_rejected(self):
        with tempfile.NamedTemporaryFile(suffix='.iso', delete=False) as handle:
            handle.write(b'\x00' * 0x500)
            path = handle.name
        try:
            with self.assertRaisesRegex(ValueError, 'US GPVE01'):
                ch.read_iso_entry(path)
        finally:
            Path(path).unlink()

    def test_hash_needs_bytes(self):
        self.assertEqual(len(ch.sha256_bytes(b'abc')), 64)
        with self.assertRaises(ValueError):
            ch.sha256_bytes('abc')


class PacketTests(unittest.TestCase):
    def test_packet_is_metadata_only(self):
        packet = ch.summarize(dict(ch.BASELINE_METADATA), None)
        self.assertEqual(packet['schema'], ch.SCHEMA)
        self.assertEqual(packet['stage'], 'ch_ABEM_LeafChappy')
        self.assertEqual(packet['floor_coverage'], 2)
        self.assertTrue(packet['baseline_agrees'])
        self.assertEqual(packet['source_sha256'], None)
        self.assertIn('withheld', packet['source_status'])
        self.assertFalse(packet['playable'])
        self.assertFalse(packet['retail_generation'])
        self.assertEqual(packet['stage_metadata']['starting_pikmin'], 30)
        self.assertTrue(any('#136' in blocker for blocker in packet['blockers']))
        self.assertNotIn('enemies', packet['stage_metadata'])
        self.assertNotIn('placements', packet)

    def test_verified_pin_status(self):
        packet = ch.summarize(dict(ch.BASELINE_METADATA), ch.SOURCE_SHA256)
        self.assertIn('hash-verified', packet['source_status'])



# ---- P1 runtime import layer (issue #550, worker muse-l52) ----
import importlib.util
import json
ROOT = _Path(__file__).resolve().parents[2]
# Extends the P0 contract above: real-source manifest, host entry,
# run staging and marker validation reusing the P0 decode helpers.
def _load_adapter():
    path = (ROOT / "experimental" / "content_lanes"
            / "p2-challenge-ch_abem_leafchappy.py")
    spec = importlib.util.spec_from_file_location(
        "p1_leafchappy_adapter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p1 = _load_adapter()
from experimental.content_lanes import p2_challenge_ch_abem_leafchappy as p0

ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")
HAVE_ISO = ISO.is_file()

HOST_CHAIN = """P2_CHALLENGE_MODE_BOOT cave=ch_ABEM_LeafChappy ui_index=17
P2_CHALLENGE_MODE_TICK cave=ch_ABEM_LeafChappy ui_index=17
P2_CHALLENGE_MODE_TICK cave=ch_ABEM_LeafChappy ui_index=17
P2_CHALLENGE_MODE_DONE end=none score=485
"""


def real_bytes():
    return p0.read_iso_entry(str(ISO))


def real_manifest():
    return p1.stage_manifest(iso_path=str(ISO))


class ManifestTests(unittest.TestCase):
    def test_exactly_one_source(self):
        with self.assertRaises(ValueError):
            p1.stage_manifest()
        with self.assertRaises(ValueError):
            p1.stage_manifest(raw_bytes=b"x", iso_path=str(ISO))

    def test_tampered_bytes_rejected(self):
        with self.assertRaises(ValueError):
            p1.stage_manifest(raw_bytes=b"not the stage")

    @unittest.skipUnless(HAVE_ISO, "retail ISO not present")
    def test_real_manifest_fields(self):
        manifest = real_manifest()
        self.assertEqual(manifest["schema"], "p2-challenge-import-p1-1")
        self.assertEqual(manifest["stage_id"], "ch_ABEM_LeafChappy")
        self.assertEqual(manifest["source_sha256"], p0.SOURCE_SHA256)
        self.assertEqual(len(manifest["floors"]), 2)
        self.assertEqual(manifest["starting_squad"], 30)
        self.assertEqual(manifest["ui_index"], 17)
        self.assertEqual(manifest["floor_seconds"], [85.0, 100.0])
        self.assertEqual((manifest["bitter_sprays"], manifest["spicy_sprays"]),
                         (1, 1))
        self.assertEqual(manifest["treasure_count_field"], 11)


class HostEntryTests(unittest.TestCase):
    @unittest.skipUnless(HAVE_ISO, "retail ISO not present")
    def test_entry_shape_matches_native_struct(self):
        entry = p1.host_stage_entry(real_manifest())
        self.assertEqual(entry["caveId"], "ch_ABEM_LeafChappy")
        self.assertEqual(entry["uiIndex"], 17)
        self.assertEqual(entry["floorCount"], 2)
        self.assertEqual(len(entry["floorSeconds"]), 8)
        self.assertEqual(entry["floorSeconds"][:2], [85.0, 100.0])
        self.assertEqual(len(entry["roster"]), 7)
        self.assertTrue(all(len(row) == 3 for row in entry["roster"]))
        self.assertEqual(sum(sum(row) for row in entry["roster"]), 30)

    def test_bad_roster_rejected(self):
        manifest = {"starting_roster": [[1]], "floor_seconds": [1.0],
                    "floors": [{}], "ui_index": 1, "bitter_sprays": 0,
                    "spicy_sprays": 0}
        with self.assertRaises(ValueError):
            p1.host_stage_entry(manifest)


class LayoutTests(unittest.TestCase):
    @unittest.skipUnless(HAVE_ISO, "retail ISO not present")
    def test_layout_writes_four_files(self):
        manifest = real_manifest()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            paths = p1.stage_run_layout(manifest, out)
            for key in ("stage", "squad", "expected", "manifest"):
                self.assertTrue(Path(paths[key]).is_file())
            expected = json.loads(Path(paths["expected"]).read_text())
            self.assertEqual(expected["reference_score_zero_receipt"], 485)

    def test_layout_refuses_existing_dir(self):
        manifest = {"starting_roster": [[0] * 3] * 7,
                    "floor_seconds": [85.0, 100.0], "floors": [{}, {}],
                    "stage_id": "x", "ui_index": 17, "bitter_sprays": 1,
                    "spicy_sprays": 1}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Exception):
                p1.stage_run_layout(manifest, tmp)


class MarkerTests(unittest.TestCase):
    def test_room_boot_baseline(self):
        checks = p1.validate_room_boot_log(
            "Experimental preview window set to 960x540 windowed and centered")
        self.assertTrue(checks["window_960x540"])
        self.assertTrue(checks["centered"])
        self.assertTrue(checks["no_extinction"])
        checks = p1.validate_room_boot_log("extinction screen")
        self.assertFalse(checks["no_extinction"])

    @unittest.skipUnless(HAVE_ISO, "retail ISO not present")
    def test_host_chain_correlates(self):
        verdict = p1.validate_host_markers(HOST_CHAIN, real_manifest())
        self.assertTrue(verdict["correlated"])
        self.assertTrue(all(verdict["markers"][k]
                            for k in ("P2_CHALLENGE_MODE_BOOT",
                                      "P2_CHALLENGE_MODE_TICK",
                                      "P2_CHALLENGE_MODE_DONE")))

    @unittest.skipUnless(HAVE_ISO, "retail ISO not present")
    def test_empty_log_is_not_correlated(self):
        verdict = p1.validate_host_markers("nothing here", real_manifest())
        self.assertFalse(verdict["correlated"])

    def test_captain_down_breaks_correlation(self):
        verdict = p1.validate_host_markers(
            HOST_CHAIN + "P2_FIXTURE_CAPTAIN_DOWN tick=1\n",
            {"stage_id": "ch_ABEM_LeafChappy"})
        self.assertFalse(verdict["correlated"])


class ReferenceTests(unittest.TestCase):
    @unittest.skipUnless(HAVE_ISO, "retail ISO not present")
    def test_reference_score(self):
        self.assertEqual(p1.reference_score(real_manifest()), 485)
        self.assertEqual(p1.reference_score(real_manifest(), pokos=10), 585)

    def test_reference_sets_documented(self):
        self.assertIn("LeafChappy", p1.ENEMY_IDS)
        self.assertIn("Egg", p1.ENEMY_IDS)
        self.assertIn("key", p1.TREASURE_IDS)
        self.assertIn("apple", p1.TREASURE_IDS)

    def test_p0_pin_consistent(self):
        self.assertEqual(p0.SOURCE_SHA256,
                         "49cc9076cede949786025b3bcd08ce60362096d8fe8f8b5330c725de4acd2baf")
        self.assertEqual(p0.STAGE_ID, "ch_ABEM_LeafChappy")
        self.assertEqual(p0.UI_INDEX, 17)


if __name__ == "__main__":
    unittest.main()