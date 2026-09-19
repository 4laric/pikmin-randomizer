'''Focused tests for the forest_1 legal-asset verifier/stager (#681).
All inputs are synthetic; no disc, runtime or shared writes.'''

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import experimental.pikmin2_forest1_legal_assets as lane


class MemberReadTests(unittest.TestCase):
    def test_present_absent_and_short_read(self):
        with tempfile.TemporaryDirectory() as temp:
            iso = Path(temp) / 'iso.bin'
            iso.write_bytes(b'HEADER' + b'PAYLOAD')
            members = {'m/a': (6, 7)}
            data, rec = lane.read_member(iso, 'm/a', members)
            self.assertEqual(data, b'PAYLOAD')
            self.assertEqual(rec['status'], 'PRESENT')
            self.assertEqual(rec['size'], 7)
            self.assertEqual(rec['sha256'], lane.sha256_bytes(b'PAYLOAD'))
            data, rec = lane.read_member(iso, 'm/none', members)
            self.assertIsNone(data)
            self.assertEqual(rec['status'], 'ABSENT')
            self.assertIn('failed_read', rec)
            data, rec = lane.read_member(iso, 'm/a', {'m/a': (6, 999)})
            self.assertIsNone(data)
            self.assertIn('short read', rec['failed_read'])



class ValidateTests(unittest.TestCase):
    def base(self):
        return {'schema': 'p2-forest1-legal-assets-1', 'cave': 'forest_1',
                'present': [{'member': 'm/a', 'sha256': '0' * 64}],
                'absent': [{'member': 'm/b', 'failed_read': 'absent from disc index'}]}

    def test_valid_packet(self):
        self.assertEqual(lane.validate_packet(self.base())['cave'], 'forest_1')

    def test_bad_schema_and_cave(self):
        p = self.base()
        p['schema'] = 'other'
        with self.assertRaises(ValueError):
            lane.validate_packet(p)
        p = self.base()
        p['cave'] = 'other'
        with self.assertRaises(ValueError):
            lane.validate_packet(p)

    def test_present_missing_sha_rejected(self):
        p = self.base()
        p['present'] = [{'member': 'm/a'}]
        with self.assertRaises(ValueError):
            lane.validate_packet(p)

    def test_absent_needs_exact_failed_read(self):
        p = self.base()
        p['absent'] = [{'member': 'm/b', 'status': 'ABSENT'}]
        with self.assertRaises(ValueError):
            lane.validate_packet(p)

    def test_non_sha256_digest_rejected(self):
        p = self.base()
        p['present'] = [{'member': 'm/a', 'sha256': 'deadbeef'}]
        with self.assertRaises(ValueError):
            lane.validate_packet(p)



class StageTests(unittest.TestCase):
    def _packet(self, iso):
        return {'schema': 'p2-forest1-legal-assets-1', 'cave': 'forest_1',
                'present': [{'member': 'm/a', 'status': 'PRESENT', 'offset': 0,
                            'size': 3, 'sha256': lane.sha256_bytes(b'AAA')}],
                'absent': [{'member': 'm/x', 'status': 'ABSENT',
                            'failed_read': 'absent from disc index'}]}

    def test_stage_writes_exact_bytes_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            iso = Path(temp) / 'iso.bin'
            iso.write_bytes(b'AAABBB')
            members = {'m/a': (0, 3)}
            out = Path(temp) / 'staged'
            manifest = lane.stage(self._packet(iso), iso, members, out)
            self.assertEqual((out / 'm/a').read_bytes(), b'AAA')
            self.assertEqual(manifest['staged'][0]['sha256'], lane.sha256_bytes(b'AAA'))
            written = json.loads((out / 'staged-manifest.json').read_text())
            self.assertEqual(len(written['staged']), 1)

    def test_stage_rejects_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            iso = Path(temp) / 'iso.bin'
            iso.write_bytes(b'AAABBB')
            packet = self._packet(iso)
            packet['present'][0]['sha256'] = '1' * 64
            with self.assertRaises(ValueError):
                lane.stage(packet, iso, {'m/a': (0, 3)}, Path(temp) / 'staged')



class ClosureTests(unittest.TestCase):
    def test_enumerate_units_names_only(self):
        text = '1 { 1 synthetic 2 3 1 0 1 2 0 0 1 4 1 170.5 1 1 1 2 0 5 1 170.5 0 1 }'
        self.assertEqual(lane.enumerate_units(text), ['synthetic'])

    def test_unit_and_course_members(self):
        self.assertEqual(lane.unit_asset_members('u'),
                         ['user/Mukki/mapunits/arc/u/arc.szs',
                          'user/Mukki/mapunits/arc/u/texts.szs'])
        self.assertIn('user/Kando/map/forest/arc.szs', lane.course_members())
        self.assertIn('user/Abe/map/forest/route.txt', lane.course_members())

    def test_pools_and_absent_probes_declared(self):
        self.assertEqual(sorted(p for _, _, p in lane.FLOOR_POOLS),
                         sorted(['1_units_cent3_tsuchi.txt',
                                 '1_units_cent2_tsuchi.txt',
                                 '2_ABE_norhiba_blkhiba_tsuchi.txt',
                                 '2_ABE_mid1_nor3_tsuchi.txt',
                                 '1_units_boss_tsuchi.txt']))
        self.assertTrue(lane.ABSENT_PROBES)


class NoInventionTests(unittest.TestCase):
    def test_every_record_is_present_or_exact_absent(self):
        packet = {'schema': 'p2-forest1-legal-assets-1', 'cave': 'forest_1',
                  'present': [{'member': 'm/a', 'sha256': '0' * 64}],
                  'absent': [{'member': 'm/b', 'failed_read': 'absent from disc index'}]}
        lane.validate_packet(packet)
        for record in packet['present']:
            self.assertIn('sha256', record)
        for record in packet['absent']:
            self.assertTrue(record['failed_read'])


if __name__ == '__main__':
    unittest.main()
