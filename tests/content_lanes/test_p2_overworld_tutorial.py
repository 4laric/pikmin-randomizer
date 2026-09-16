"""P0 tests for the Valley of Repose import contract (issue #148).

All stage-table bytes below are synthetic and minimal: they exercise the
importer boundary (decode/select/validate/fail-closed), never retail values.
No test claims terrain, placements, or playability.
"""
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_adapter():
    # Reserved lane files use hyphenated names, so load by path.
    path = (ROOT / 'experimental' / 'content_lanes'
            / 'p2-overworld-tutorial.py')
    spec = importlib.util.spec_from_file_location(
        'p2_overworld_tutorial_adapter', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tutorial = _load_adapter()
from experimental.pikmin2_regional_audit import stage_cave_links

TUTORIAL_DOC = """1
{
  name tutorial
  end
  0
  0
  1
  {t_01} 7 tutorial_1.txt
  7
}
"""

FOREST_ONLY_DOC = """1
{
  name forest
  end
  0
  0
  0
  5
}
"""


def parsed(doc=TUTORIAL_DOC):
    return stage_cave_links(doc)


class DecodeTests(unittest.TestCase):
    def test_decode_round_trip(self):
        data = TUTORIAL_DOC.encode('shift_jis')
        self.assertEqual(tutorial.decode_stages(data), TUTORIAL_DOC)

    def test_decode_rejects_bad_input(self):
        for bad in (None, 'text', b'', bytearray()):
            with self.assertRaises(ValueError):
                tutorial.decode_stages(bad)

    def test_decode_rejects_bad_encoding(self):
        with self.assertRaises(UnicodeDecodeError):
            tutorial.decode_stages(b'\x80not-shift-jis')


class LinkSelectionTests(unittest.TestCase):
    def test_selects_only_tutorial_course(self):
        doc = ('2\n{\n name tutorial\n end\n 0\n 0\n'
               ' 1\n {t_01} 7 tutorial_1.txt\n 7\n}\n'
               '{\n name forest\n end\n 0\n 0\n 0\n 5\n}')
        links = tutorial.tutorial_links(stage_cave_links(doc))
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]['course_id'], 'tutorial')
        self.assertEqual(links[0]['source_path'],
                         'user/Mukki/mapunits/caveinfo/tutorial_1.txt')

    def test_missing_tutorial_course_raises(self):
        with self.assertRaises(ValueError):
            tutorial.tutorial_links(parsed(FOREST_ONLY_DOC))

    def test_links_are_copies(self):
        links = parsed()
        selected = tutorial.tutorial_links(links)
        selected[0]['course_id'] = 'mutated'
        self.assertEqual(links[0]['course_id'], 'tutorial')


class SurfaceTotalTests(unittest.TestCase):
    def test_reads_declared_total(self):
        self.assertEqual(tutorial.tutorial_surface_total(TUTORIAL_DOC), 7)

    def test_missing_course_raises(self):
        with self.assertRaises(ValueError):
            tutorial.tutorial_surface_total(FOREST_ONLY_DOC)

    def test_duplicate_course_raises(self):
        doc = TUTORIAL_DOC + '{\n name tutorial\n end\n 0\n 0\n 0\n 7\n}'
        doc = '2\n' + doc.split('\n', 1)[1]
        with self.assertRaises(ValueError):
            tutorial.tutorial_surface_total(doc)

    def test_truncated_tables_raise(self):
        for doc in ('1\n{\n name tutorial\n end\n 0\n}',
                    '1\n{\n name tutorial\n end\n 0\n 0\n 9\n {t_01} 7 tutorial_1.txt\n 7\n}',
                    '1\n{\n name tutorial\n end\n 0\n 0\n 1\n {t_01} 7 tutorial_1.txt\n}'):
            with self.assertRaises(ValueError):
                tutorial.tutorial_surface_total(doc)

    def test_non_numeric_total_raises(self):
        doc = TUTORIAL_DOC.replace('\n  7\n}', '\n  seven\n}')
        with self.assertRaises(ValueError):
            tutorial.tutorial_surface_total(doc)


class ManifestTests(unittest.TestCase):
    def test_build_records_links_total_and_unknown_hash(self):
        manifest = tutorial.build_manifest(TUTORIAL_DOC, parsed())
        self.assertEqual(manifest['schema'], 1)
        self.assertEqual(manifest['course'], 'tutorial')
        self.assertEqual(manifest['issue'], 148)
        self.assertEqual(manifest['source'], 'user/Abe/stages.txt')
        self.assertEqual(manifest['source_sha256'], 'unknown')
        self.assertEqual(len(manifest['cave_links']), 1)
        self.assertEqual(manifest['surface_treasure_total'], 7)
        self.assertTrue(manifest['missing_prerequisites'])
        self.assertEqual(manifest['runtime_dependencies'],
                         [128, 130, 131, 132, 140, 144, 145, 146])
        self.assertEqual(sorted(manifest['required_inventory']),
                         sorted(tutorial.REQUIRED_INVENTORY))
        tutorial.validate_manifest(manifest)

    def test_build_records_real_hash_when_supplied(self):
        sha = hashlib.sha256(TUTORIAL_DOC.encode('shift_jis')).hexdigest()
        manifest = tutorial.build_manifest(TUTORIAL_DOC, parsed(),
                                           source_sha256=sha)
        self.assertEqual(manifest['source_sha256'], sha)
        self.assertEqual(manifest['missing_prerequisites'], [])
        tutorial.validate_manifest(manifest)

    def test_build_rejects_bad_hash(self):
        for bad in ('abc', 'X' * 64, 7, None.__class__):
            with self.assertRaises(ValueError):
                tutorial.build_manifest(TUTORIAL_DOC, parsed(),
                                        source_sha256=bad)

    def test_manifest_has_no_runtime_data(self):
        manifest = tutorial.build_manifest(TUTORIAL_DOC, parsed())
        for banned in ('placements', 'coordinates', 'actors', 'spawns',
                       'playable'):
            self.assertNotIn(banned, manifest)
            for link in manifest['cave_links']:
                self.assertNotIn(banned, link)

    def test_validate_rejects_drift_and_invention(self):
        good = tutorial.build_manifest(TUTORIAL_DOC, parsed())
        mutated = dict(good, course='forest')
        with self.assertRaises(ValueError):
            tutorial.validate_manifest(mutated)
        mutated = dict(good, cave_links=[])
        with self.assertRaises(ValueError):
            tutorial.validate_manifest(mutated)
        mutated = dict(good, surface_treasure_total='7')
        with self.assertRaises(ValueError):
            tutorial.validate_manifest(mutated)
        mutated = dict(good)
        mutated['cave_links'] = [dict(good['cave_links'][0],
                                      placements=[])]
        with self.assertRaises(ValueError):
            tutorial.validate_manifest(mutated)
        mutated = dict(good, source_sha256='unknown',
                       missing_prerequisites=[])
        with self.assertRaises(ValueError):
            tutorial.validate_manifest(mutated)


class ContractSyncTests(unittest.TestCase):
    def test_constants_match_lane_plan(self):
        plan = json.loads((ROOT / 'docs/PIKMIN_CONTENT_IMPORT_LANES.json')
                          .read_text(encoding='utf-8-sig'))
        lane = next(l for l in plan['lanes']
                    if l['lane'] == 'p2-overworld-tutorial')
        self.assertEqual(tutorial.COURSE_ID, lane['details']['course'])
        self.assertEqual(tutorial.SOURCE_PATH, lane['source'])
        self.assertEqual(list(tutorial.REQUIRED_INVENTORY),
                         lane['details']['required_inventory'])
        self.assertEqual(list(tutorial.RUNTIME_DEPENDENCIES),
                         lane['runtime_dependencies'])
        self.assertEqual(tutorial.ISSUE, lane['issue'])
        self.assertEqual(
            ['experimental/content_lanes/p2-overworld-tutorial.py',
             'tests/content_lanes/test_p2_overworld_tutorial.py',
             'docs/content_lanes/p2-overworld-tutorial.md'],
            lane['owned_files'])

    def test_prerequisite_names_exact_missing_source(self):
        prereq = tutorial.source_prerequisite()
        self.assertEqual(prereq['source'], 'user/Abe/stages.txt')
        self.assertIsNone(prereq['recorded_sha256'])
        self.assertEqual(prereq['status'], 'missing-local-source')
        self.assertIn('GPVE01', prereq['disc'] + prereq['header'])


if __name__ == '__main__':
    unittest.main()
