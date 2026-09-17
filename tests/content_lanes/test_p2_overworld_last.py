'''Focused P0 tests for the p2-overworld-last import contract (issue 151).

Retail-shaped inputs below are SYNTHETIC fixtures in the OBSERVED retail grammar
(brace blocks, end-of-line comments, no farm keyword, brace-wrapped cave ids,
literal end trailer); they assert no retail fact. The recorded real-source test
runs only when the staged legal stages.txt is present.'''

import importlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

adapter = importlib.import_module('experimental.content_lanes.p2-overworld-last')

CANON = Path(__file__).resolve().parents[9]
REAL_STAGES = (CANON / 'output' / 'workflow' / 'autofill' / 'planning-shards' /
    'overworld-last' / 'prepared' / 'last-p0-output' / 'stages.txt')
REAL_SHA256 = '4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8'


def syn_course(name, start, angle, limits, loops, caves, ground):
    lines = ['# synthetic ' + name + ' fixture', chr(123)]
    lines += ['name ' + name, 'folder courses/' + name, 'abe_folder user/Abe/courses/' + name]
    lines += ['model ' + name + '.mod', 'collision ' + name + '.col', 'waterbox ' + name + '.wbx']
    lines += ['mapcode ' + name + '.mpc', 'route ' + name + '.rte']
    lines += ['start ' + start, 'startangle ' + angle, 'end', str(len(limits))]
    lines.extend(limits)
    lines.append(str(len(loops)))
    lines.extend(loops)
    lines.append(str(len(caves)))
    lines.extend(caves)
    lines += [str(ground), chr(125)]
    return chr(10).join(lines)


def syn_stages():
    last = syn_course('last', '10.0 20.0 30.0', '45.0',
        ['LimitA 1 10 3', 'LimitB 5 15 2'], ['LoopA 1 30 1'],
        ['{caveA1} 2 caveA1.txt', '{caveA2} 0 caveA2.txt'], 7)
    names = ['tutorial', 'forest', 'yakushima', 'test_map']
    body = chr(10).join(syn_course(n, '0 0 0', '0', ['L 0 0 0'], [], ['{c} 0 c.txt'], 0) for n in names[:3])
    tail = syn_course('test_map', '0 0 0', '0', ['L 0 0 0'], [], ['{c} 0 c.txt'], 0)
    return '5 # number of courses' + chr(10) + body + chr(10) + last + chr(10) + tail + chr(10)

SYNTHETIC_STAGES = syn_stages()


class TestOverworldLastAdapter(unittest.TestCase):
    def test_synthetic_happy_path(self):
        courses = adapter.parse_stages(SYNTHETIC_STAGES)
        self.assertEqual(len(courses), 5)
        course = adapter.select_course(courses, 'last')
        self.assertEqual(course.index, 3)
        self.assertEqual(adapter.validate_course(course), [])
        closure = adapter.resource_closure(course)
        self.assertEqual(closure['model'], 'courses/last/last.mod')
        self.assertEqual(closure['collision'], 'courses/last/last.col')
        self.assertEqual(closure['waterbox'], 'courses/last/last.wbx')
        self.assertEqual(closure['mapcode'], 'courses/last/last.mpc')
        self.assertNotIn('farm', closure)
        self.assertEqual(closure['route'], 'user/Abe/courses/last/last.rte')
        manifest = adapter.build_manifest(course, '<synthetic>', '0' * 64)
        self.assertFalse(manifest['placements_emitted'])
        self.assertEqual(manifest['course'], 'last')
        self.assertEqual(len(manifest['caves']), 2)
        self.assertEqual(manifest['ground_otakara_max'], 7)
        for item in adapter.REQUIRED_INVENTORY:
            self.assertIn(item, manifest['required_inventory_coverage'])

    def test_missing_source_reports_prerequisite(self):
        with self.assertRaises(adapter.SourceMissingError) as ctx:
            adapter.load_source_bytes('definitely/not/stages.txt')
        self.assertIn('missing prerequisite', str(ctx.exception))
        self.assertIn('no values are invented', str(ctx.exception))

    def test_empty_file_rejected(self):
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages('')

    def test_comments_only_rejected(self):
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages('# nothing but comments' + chr(10) + '# more')
    def test_wrong_course_count_rejected(self):
        bad = SYNTHETIC_STAGES.replace('5 # number of courses', '4 # number of courses', 1)
        with self.assertRaises(adapter.StagesDecodeError) as ctx:
            adapter.parse_stages(bad)
        self.assertIn('expected 5 courses', str(ctx.exception))

    def test_unknown_course_rejected(self):
        courses = adapter.parse_stages(SYNTHETIC_STAGES)
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.select_course(courses, 'nowhere')

    def test_keyword_order_enforced(self):
        bad = SYNTHETIC_STAGES.replace('abe_folder', 'folder', 1)
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages(bad)

    def test_farm_keyword_rejected(self):
        bad = SYNTHETIC_STAGES.replace('mapcode last.mpc', 'mapcode last.mpc' + chr(10) + 'farm last.frm', 1)
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages(bad)

    def test_unknown_keyword_rejected(self):
        bad = SYNTHETIC_STAGES.replace('name tutorial', 'title tutorial', 1)
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages(bad)

    def test_missing_end_trailer_rejected(self):
        bad = SYNTHETIC_STAGES.replace(chr(10) + 'end' + chr(10), chr(10), 1)
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages(bad)

    def test_unbraced_course_rejected(self):
        bad = SYNTHETIC_STAGES.replace('{', '', 1)
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages(bad)

    def test_unbraced_cave_id_rejected(self):
        bad = SYNTHETIC_STAGES.replace('{caveA1}', 'caveA1', 1)
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages(bad)

    def test_bad_integer_rejected(self):
        bad = SYNTHETIC_STAGES.replace(chr(10) + '2' + chr(10) + '{caveA1}', chr(10) + 'ZZ' + chr(10) + '{caveA1}', 1)
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages(bad)

    def test_nonfinite_float_rejected(self):
        bad = SYNTHETIC_STAGES.replace('start 10.0 20.0 30.0', 'start 10.0 nan 30.0', 1)
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages(bad)

    def test_truncated_file_rejected(self):
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages(SYNTHETIC_STAGES[:200])

    def test_trailing_tokens_rejected(self):
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages(SYNTHETIC_STAGES + ' junk')

    def test_duplicate_cave_id_flagged(self):
        courses = adapter.parse_stages(SYNTHETIC_STAGES)
        course = adapter.select_course(courses, 'last')
        course.caves.append(adapter.CaveRow('caveA1', 1, 'dup.txt'))
        defects = adapter.validate_course(course)
        self.assertTrue(any('duplicate cave id' in d for d in defects))

    def test_inverted_day_range_flagged(self):
        courses = adapter.parse_stages(SYNTHETIC_STAGES)
        course = adapter.select_course(courses, 'last')
        course.limit_gen[0].minimum_day = 99
        defects = adapter.validate_course(course)
        self.assertTrue(any('inverted' in d for d in defects))

    def test_negative_otakara_flagged(self):
        courses = adapter.parse_stages(SYNTHETIC_STAGES)
        course = adapter.select_course(courses, 'last')
        course.ground_otakara_max = -1
        defects = adapter.validate_course(course)
        self.assertTrue(any('ground_otakara_max' in d for d in defects))

    def test_empty_path_flagged(self):
        courses = adapter.parse_stages(SYNTHETIC_STAGES)
        course = adapter.select_course(courses, 'last')
        course.paths['model'] = ''
        defects = adapter.validate_course(course)
        self.assertTrue(any('model' in d for d in defects))

    def test_non_utf8_source_rejected(self):
        fd, path = tempfile.mkstemp(suffix='.txt')
        try:
            with os.fdopen(fd, 'wb') as fh:
                fh.write(bytes([255, 254, 0, 105, 110, 118]))
            with self.assertRaises(adapter.StagesDecodeError):
                adapter.decode_course_file(path)
        finally:
            os.unlink(path)

    def test_decode_end_to_end_synthetic_file(self):
        fd, path = tempfile.mkstemp(suffix='.txt')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                fh.write(SYNTHETIC_STAGES)
            course, digest = adapter.decode_course_file(path)
            self.assertEqual(course.name, 'last')
            self.assertEqual(course.index, 3)
            self.assertEqual(len(digest), 64)
        finally:
            os.unlink(path)

    @unittest.skipUnless(REAL_STAGES.is_file(), 'legal stages.txt not staged')
    def test_real_source_last_course(self):
        course, digest = adapter.decode_course_file(str(REAL_STAGES))
        self.assertEqual(digest, REAL_SHA256)
        self.assertEqual((course.name, course.index), ('last', 3))
        self.assertEqual(adapter.validate_course(course), [])
        self.assertEqual([c.cave_id for c in course.caves], ['l_01', 'l_02', 'l_03'])
        self.assertEqual(course.ground_otakara_max, 5)
        closure = adapter.resource_closure(course)
        self.assertEqual(closure['model'], 'user/Kando/map/last/last.bmd')
        manifest = adapter.build_manifest(course, str(REAL_STAGES), digest)
        self.assertFalse(manifest['placements_emitted'])
        self.assertEqual(manifest['source_sha256'], REAL_SHA256)



class TestOverworldLastP1SurfaceSession(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='last-p1-')
        self.addCleanup(shutil.rmtree, self.tmp, True)
        courses = adapter.parse_stages(SYNTHETIC_STAGES)
        self.course = adapter.select_course(courses, 'last')
        self.manifest = adapter.build_manifest(self.course, '<synthetic>', '0' * 64)

    def test_contract_module_loads(self):
        contract = adapter.load_surface_contract()
        self.assertEqual(contract.SCHEMA, adapter.SURFACE_SESSION_SCHEMA)
        self.assertIn('begin_day', contract.EVENTS)
        self.assertIn('deliver_receipt', contract.EVENTS)

    def test_stage_run_layout_happy(self):
        staged = adapter.stage_run_layout(self.manifest, self.tmp, source_path='<synthetic>')
        self.assertEqual(staged['schema'], adapter.P1_RUN_SCHEMA)
        self.assertTrue(Path(staged['manifest_path']).is_file())
        self.assertTrue(Path(staged['metadata_path']).is_file())
        metadata = json.loads(Path(staged['metadata_path']).read_text(encoding='utf-8'))
        self.assertEqual(metadata['contract_schema'], 'p2-surface-session-1')
        self.assertEqual(metadata['source_sha256'], '0' * 64)
        self.assertFalse(metadata['ledger_writes'])
        self.assertFalse(metadata['placements_emitted'])
        self.assertEqual(metadata['manifest_sha256'], staged['manifest_sha256'])
        self.assertIn('overworld-last/manifest.json', metadata['staged_files'])

    def test_stage_run_layout_refuses_populated_dir(self):
        adapter.stage_run_layout(self.manifest, self.tmp)
        with self.assertRaises(adapter.StagesDecodeError) as ctx:
            adapter.stage_run_layout(self.manifest, self.tmp)
        self.assertIn('already populated', str(ctx.exception))

    def test_stage_run_layout_refuses_placements(self):
        bad = dict(self.manifest)
        bad['placements_emitted'] = True
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.stage_run_layout(bad, self.tmp)

    def test_stage_run_layout_refuses_wrong_course(self):
        bad = dict(self.manifest)
        bad['course'] = 'forest'
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.stage_run_layout(bad, self.tmp)

    def test_surface_script_covers_boundaries_with_source_cave_id(self):
        script = adapter.surface_session_script(self.manifest)
        covered = {boundary for boundary, _event in script}
        self.assertEqual(covered, set(adapter.BOUNDARIES))
        cave_id = self.manifest['caves'][0]['cave_id']
        enters = [e for _b, e in script if e['type'] == 'enter_cave']
        self.assertTrue(all(e['cave_id'] == cave_id for e in enters))

    def test_surface_script_rejects_bad_start_day(self):
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.surface_session_script(self.manifest, start_day=0)

    def test_drive_surface_session_boundaries(self):
        report = adapter.drive_surface_session(self.manifest)
        self.assertEqual(report['contract_schema'], 'p2-surface-session-1')
        self.assertFalse(report['runtime_claim'])
        self.assertTrue(report['existing_behavior_only'])
        self.assertEqual(report['final_day'], 2)
        for boundary in adapter.BOUNDARIES:
            self.assertEqual(report['boundaries'][boundary]['steps'],
                             len([s for s in report['steps'] if s['boundary'] == boundary]))
        self.assertEqual(report['boundaries']['day_transition']['accepted'], 1)
        self.assertEqual(report['boundaries']['save_reload']['rejected'], 0)
        self.assertEqual(report['boundaries']['receipt_replay']['accepted'], 1)
        self.assertEqual(report['boundaries']['receipt_replay']['rejected'], 1)
        self.assertEqual(report['boundaries']['exit_reentry']['accepted'], 4)

    def test_drive_surface_session_records_missing_integration(self):
        report = adapter.drive_surface_session(self.manifest)
        names = [m['name'] for m in report['missing_integration']]
        self.assertEqual(names, list(adapter.load_surface_contract().MISSING_INTEGRATION))
        self.assertTrue(all(m['ok'] is False for m in report['missing_integration']))
        self.assertTrue(all('not existing behavior' in m['reason'] for m in report['missing_integration']))

    def test_drive_surface_session_schema_mismatch_refused(self):
        original = adapter.SURFACE_SESSION_SCHEMA
        adapter.SURFACE_SESSION_SCHEMA = 'p2-surface-session-999'
        try:
            with self.assertRaises(adapter.SurfaceSessionUnavailableError):
                adapter.drive_surface_session(self.manifest)
        finally:
            adapter.SURFACE_SESSION_SCHEMA = original

    def test_missing_contract_module_reports_prerequisite(self):
        original = adapter.load_surface_contract
        def broken():
            raise adapter.SurfaceSessionUnavailableError('missing integrated contract module')
        adapter.load_surface_contract = broken
        try:
            with self.assertRaises(adapter.SurfaceSessionUnavailableError):
                adapter.drive_surface_session(self.manifest)
        finally:
            adapter.load_surface_contract = original

    def test_p1_missing_source_reports_prerequisite(self):
        with self.assertRaises(adapter.SourceMissingError):
            adapter.decode_course_file('definitely/not/stages.txt')
        with self.assertRaises(adapter.SourceMissingError):
            adapter.load_source_bytes('definitely/not/stages.txt')

    @unittest.skipUnless(REAL_STAGES.is_file(), 'legal stages.txt not staged')
    def test_real_source_p1_stage_and_drive(self):
        course, digest = adapter.decode_course_file(str(REAL_STAGES))
        self.assertEqual(digest, REAL_SHA256)
        manifest = adapter.build_manifest(course, str(REAL_STAGES), digest)
        staged = adapter.stage_run_layout(manifest, self.tmp, source_path=str(REAL_STAGES))
        metadata = json.loads(Path(staged['metadata_path']).read_text(encoding='utf-8'))
        self.assertEqual(metadata['source_sha256'], REAL_SHA256)
        self.assertEqual(metadata['manifest_sha256'], staged['manifest_sha256'])
        report = adapter.drive_surface_session(manifest)
        caves = [c['cave_id'] for c in manifest['caves']]
        self.assertTrue(all(c in {'l_01', 'l_02', 'l_03'} for c in caves))
        self.assertEqual(report['boundaries']['receipt_replay']['rejected'], 1)
        self.assertEqual(report['final_day'], 2)
        self.assertEqual(len(report['missing_integration']), 4)
        self.assertFalse(report['runtime_claim'])

if __name__ == '__main__':
    unittest.main()
