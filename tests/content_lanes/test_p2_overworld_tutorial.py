"""P0 tests for the Valley of Repose import contract (issue #148).

Synthetic stage tables exercise the importer boundary
(decode/select/schedule/coverage/validate/fail-closed). When the local
supported ISO is present, real-source tests pin the observed retail bytes
and decode the tutorial course; they skip cleanly when it is absent. No
test claims terrain, placements, or playability.
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

# Minimal tutorial course: exercises the trailing-total walk.
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

# Full synthetic course: header + both generator tables + story caves + the
# retail `test` placeholder registration.
FULL_DOC = """1
{
  name tutorial
  folder user/Kando/map/tutorial
  abe_folder user/Abe/map/tutorial
  model pra_sample.bmd
  collision collision.bin
  waterbox waterbox.txt
  mapcode mapcode.bin
  route route.txt
  start 0 0 0
  startangle 150
  end
  1
  0-1.txt 0 1 1
  1
  30-39.txt 30 39 39
  4
  {t_01} 3 tutorial_1.txt
  {t_02} 16 tutorial_2.txt
  {t_03} 15 tutorial_3.txt
  {test} 0 caveinfo.txt
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

# Observed pin: US GPVE01 rev 0 user/Abe/stages.txt extracted from the local
# supported ISO and independently corroborated by two sibling overworld lanes.
REAL_STAGES_SHA256 = '4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8'
REAL_STAGES_SIZE = 3275


def parsed(doc=FULL_DOC):
    return stage_cave_links(doc)


class DecodeTests(unittest.TestCase):
    def test_decode_round_trip(self):
        data = FULL_DOC.encode('shift_jis')
        self.assertEqual(tutorial.decode_stages(data), FULL_DOC)

    def test_decode_rejects_bad_input(self):
        for bad in (None, 'text', b'', bytearray()):
            with self.assertRaises(ValueError):
                tutorial.decode_stages(bad)

    def test_decode_rejects_bad_encoding(self):
        with self.assertRaises(UnicodeDecodeError):
            tutorial.decode_stages(b'\x80not-shift-jis')

    def test_sha256_rejects_bad_input(self):
        for bad in (None, 'text', b'', bytearray()):
            with self.assertRaises(ValueError):
                tutorial.sha256_bytes(bad)
        self.assertEqual(tutorial.sha256_bytes(FULL_DOC.encode('shift_jis')),
                         hashlib.sha256(FULL_DOC.encode('shift_jis')).hexdigest())


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

    def test_classification_marks_story_and_placeholder(self):
        rows = tutorial.classify_links(tutorial.tutorial_links(parsed()))
        by_tag = {row['cave_tag']: row for row in rows}
        self.assertEqual(by_tag['t_01']['story_cave_id'], 'tutorial_1')
        self.assertEqual(by_tag['t_01']['classification'], 'story')
        self.assertIsNone(by_tag['test']['story_cave_id'])
        self.assertEqual(by_tag['test']['classification'], 'registered_non_story')


class SurfaceTotalTests(unittest.TestCase):
    def test_reads_declared_total(self):
        self.assertEqual(tutorial.tutorial_surface_total(FULL_DOC), 7)
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


class CourseHeaderTests(unittest.TestCase):
    def test_decodes_authored_header(self):
        header = tutorial.tutorial_header(FULL_DOC)
        self.assertEqual(header['name'], 'tutorial')
        self.assertEqual(header['folder'], 'user/Kando/map/tutorial')
        self.assertEqual(header['abe_folder'], 'user/Abe/map/tutorial')
        self.assertEqual(header['model'], 'pra_sample.bmd')
        self.assertEqual(header['collision'], 'collision.bin')
        self.assertEqual(header['waterbox'], 'waterbox.txt')
        self.assertEqual(header['start'], [0.0, 0.0, 0.0])
        self.assertEqual(header['startangle'], 150.0)

    def test_missing_course_raises(self):
        with self.assertRaises(ValueError):
            tutorial.tutorial_header(FOREST_ONLY_DOC)


class ScheduleTests(unittest.TestCase):
    def test_decodes_both_tables_in_order(self):
        rows = tutorial.tutorial_generator_schedules(FULL_DOC)
        self.assertEqual([r['kind'] for r in rows], ['nonloop', 'loop'])
        self.assertEqual(rows[0]['filename'], '0-1.txt')
        self.assertEqual((rows[0]['first_day'], rows[0]['last_day']), (0, 1))
        self.assertEqual(rows[1]['filename'], '30-39.txt')
        self.assertEqual((rows[1]['first_day'], rows[1]['last_day']), (30, 39))

    def test_filename_day_mismatch_fails_closed(self):
        doc = FULL_DOC.replace('0-1.txt 0 1 1', '5-9.txt 0 1 1')
        with self.assertRaises(ValueError):
            tutorial.tutorial_generator_schedules(doc)

    def test_missing_course_raises(self):
        with self.assertRaises(ValueError):
            tutorial.tutorial_generator_schedules(FOREST_ONLY_DOC)


class CoverageTests(unittest.TestCase):
    def test_complete_story_coverage(self):
        rows = tutorial.classify_links(tutorial.tutorial_links(parsed()))
        coverage = tutorial.story_cave_coverage(rows)
        self.assertTrue(coverage['complete'])
        self.assertEqual([r['story_cave_id'] for r in coverage['rows']],
                         ['tutorial_1', 'tutorial_2', 'tutorial_3'])

    def test_missing_story_cave_is_incomplete(self):
        doc = FULL_DOC.replace('  {t_02} 16 tutorial_2.txt\n', '')
        doc = doc.replace('\n  4\n  {t_01}', '\n  3\n  {t_01}')
        rows = tutorial.classify_links(tutorial.tutorial_links(parsed(doc)))
        coverage = tutorial.story_cave_coverage(rows)
        self.assertFalse(coverage['complete'])
        missing = [r['story_cave_id'] for r in coverage['rows']
                   if not r['linked']]
        self.assertEqual(missing, ['tutorial_2'])


class ManifestTests(unittest.TestCase):
    def test_build_records_metadata_and_unknown_hash(self):
        manifest = tutorial.build_manifest(FULL_DOC, parsed())
        self.assertEqual(manifest['schema'], 1)
        self.assertEqual(manifest['course'], 'tutorial')
        self.assertEqual(manifest['label'], 'Valley of Repose')
        self.assertEqual(manifest['issue'], 148)
        self.assertEqual(manifest['source'], 'user/Abe/stages.txt')
        self.assertEqual(manifest['source_sha256'], 'unknown')
        self.assertIsNone(manifest['stages_sha256'])
        self.assertEqual(manifest['cave_count'], 4)
        self.assertEqual(manifest['surface_treasure_total'], 7)
        self.assertTrue(manifest['story_coverage_complete'])
        self.assertTrue(manifest['missing_prerequisites'])
        self.assertEqual(manifest['runtime_dependencies'],
                         [128, 130, 131, 132, 140, 144, 145, 146])
        self.assertEqual(sorted(manifest['required_inventory']),
                         sorted(tutorial.REQUIRED_INVENTORY))
        self.assertEqual(manifest['playable'], False)
        self.assertEqual(manifest['resource_closure'][0]['path'],
                         'user/Abe/stages.txt')
        tutorial.validate_manifest(manifest)

    def test_build_records_real_hash_when_supplied(self):
        sha = hashlib.sha256(FULL_DOC.encode('shift_jis')).hexdigest()
        manifest = tutorial.build_manifest(FULL_DOC, parsed(),
                                           source_sha256=sha)
        self.assertEqual(manifest['source_sha256'], sha)
        self.assertEqual(manifest['stages_sha256'], sha)
        self.assertEqual(manifest['missing_prerequisites'], [])
        self.assertEqual(manifest['resource_closure'][0]['status'], 'hashed')
        tutorial.validate_manifest(manifest)

    def test_build_rejects_bad_hash(self):
        for bad in ('abc', 'X' * 64, 7, None.__class__):
            with self.assertRaises(ValueError):
                tutorial.build_manifest(FULL_DOC, parsed(),
                                        source_sha256=bad)

    def test_manifest_has_no_runtime_data(self):
        manifest = tutorial.build_manifest(FULL_DOC, parsed())
        self.assertIs(manifest['playable'], False)
        for banned in ('placements', 'coordinates', 'actors', 'spawns'):
            self.assertNotIn(banned, manifest)
            for link in manifest['cave_links']:
                self.assertNotIn(banned, link)

    def test_build_rejects_incomplete_coverage(self):
        doc = FULL_DOC.replace('  {t_03} 15 tutorial_3.txt\n', '')
        with self.assertRaises(ValueError):
            tutorial.build_manifest(doc, parsed(doc))

    def test_validate_rejects_drift_and_invention(self):
        good = tutorial.build_manifest(FULL_DOC, parsed())
        for mutated in (dict(good, course='forest'),
                        dict(good, cave_links=[]),
                        dict(good, surface_treasure_total='7'),
                        dict(good, playable=True),
                        dict(good, cave_count=99),
                        dict(good, source_sha256='unknown',
                             missing_prerequisites=[]),
                        dict(good, generator_schedules=[])):
            with self.assertRaises(ValueError):
                tutorial.validate_manifest(mutated)
        mutated = dict(good)
        mutated['cave_links'] = [dict(good['cave_links'][0], placements=[])]
        with self.assertRaises(ValueError):
            tutorial.validate_manifest(mutated)
        mutated = dict(good)
        mutated['cave_links'] = [dict(good['cave_links'][0],
                                      classification='registered_non_story',
                                      story_cave_id='tutorial_1')]
        with self.assertRaises(ValueError):
            tutorial.validate_manifest(mutated)


@unittest.skipUnless(tutorial.locate_source()['available'],
                     'supported local ISO not present')
class RealSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = tutorial.extract_source_from_iso()
        cls.text = tutorial.decode_stages(cls.raw)
        cls.sha = tutorial.sha256_bytes(cls.raw)
        cls.links = stage_cave_links(cls.text)
        cls.manifest = tutorial.build_manifest(
            cls.text, cls.links, source_sha256=cls.sha)

    def test_observed_retail_pin(self):
        self.assertEqual(len(self.raw), REAL_STAGES_SIZE)
        self.assertEqual(self.sha, REAL_STAGES_SHA256)

    def test_decodes_real_tutorial_metadata(self):
        header = self.manifest['course_header']
        self.assertEqual(header['folder'], 'user/Kando/map/tutorial')
        self.assertEqual(header['abe_folder'], 'user/Abe/map/tutorial')
        self.assertEqual(header['start'], [-357.18, 0.0, 2900.0])
        self.assertEqual(header['startangle'], 150.0)
        self.assertEqual(self.manifest['surface_treasure_total'], 7)
        self.assertEqual(self.manifest['cave_count'], 4)
        self.assertTrue(self.manifest['story_coverage_complete'])

    def test_decodes_real_generator_schedules(self):
        rows = self.manifest['generator_schedules']
        self.assertEqual(sum(1 for r in rows if r['kind'] == 'nonloop'), 7)
        self.assertEqual(sum(1 for r in rows if r['kind'] == 'loop'), 3)
        self.assertEqual(rows[0]['filename'], '0-1.txt')
        self.assertEqual(rows[-1]['filename'], '50-59.txt')

    def test_real_hash_pins_resource_closure(self):
        closure = self.manifest['resource_closure']
        self.assertEqual(closure[0]['sha256'], REAL_STAGES_SHA256)
        self.assertEqual(closure[0]['status'], 'hashed')
        self.assertTrue(all(row['path'].startswith('user/')
                            for row in closure))
        tutorial.validate_manifest(self.manifest)


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

    def test_story_caves_match_inventory(self):
        inv = json.loads((ROOT / 'docs/PIKMIN2_CONTENT_INVENTORY.json')
                         .read_text(encoding='utf-8-sig'))
        caves = {row['id']: row['source'].rsplit('/', 1)[-1]
                 for row in inv['story_caves']
                 if row['id'].startswith('tutorial_')}
        self.assertEqual(tutorial.STORY_CAVES,
                         tuple(sorted(caves.items())))

    def test_prerequisite_names_exact_missing_source(self):
        prereq = tutorial.source_prerequisite()
        self.assertEqual(prereq['source'], 'user/Abe/stages.txt')
        self.assertIsNone(prereq['recorded_sha256'])
        self.assertEqual(prereq['status'], 'missing-local-source')
        self.assertIn('GPVE01', prereq['disc'] + prereq['header'])
        self.assertIn('stages.txt', tutorial.missing_prerequisite())


if __name__ == '__main__':
    unittest.main()
