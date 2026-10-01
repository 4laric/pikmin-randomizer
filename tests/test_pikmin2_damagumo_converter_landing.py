'''Pinned-hash landing verification tests (#685). All inputs synthetic;XXno disc, runtime or shared writes.'''

import json
import sys
import tempfile
import unittest
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import experimental.pikmin2_damagumo_converter_landing as lane


def record(name, sha):
    return {'name': name, 'path': 'X' + name, 'sha256': sha}


class PinTests(unittest.TestCase):
    def test_pins_cover_three_artifacts(self):
        self.assertEqual(set(lane.PINS), {'damagumo-family.json',
            'Demon/enemy.bmd', 'damagumo-slot-312004.json'})
        for sha in lane.PINS.values():
            self.assertEqual(len(sha), 64)
    def test_source_commits_are_full_shas(self):
        self.assertEqual(len(lane.SOURCE_COMMITS), 2)
        for sha in lane.SOURCE_COMMITS:
            self.assertEqual(len(sha), 40)

class VerifyTests(unittest.TestCase):
    def test_hash_match_and_crlf_canonical(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'a.json'
            target.write_bytes(b'{' + chr(10).encode() + b'}' + chr(13).encode() + chr(10).encode())
            want = hashlib.sha256(b'{\n}\n').hexdigest()
            rec = lane.verify_artifact(temp, 'a.json', want)
            self.assertEqual(rec['line_endings'], 'crlf')
    def test_missing_file_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(lane.ArtifactError):
                lane.verify_artifact(temp, 'gone.json', '0' * 64)
    def test_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'a.json'
            target.write_bytes(b'data')
            with self.assertRaises(lane.ArtifactError):
                lane.verify_artifact(temp, 'a.json', '1' * 64)



class ContractTests(unittest.TestCase):
    def good(self):
        slot = {'slot': 312004, 'source_id': 56, 'arena_binding': '312004 Damagumo',
                'schema': 1, 'model_sha256': lane.PINS['Demon/enemy.bmd']}
        profile = {'enemy_id': 56, 'joint_count': 15, 'embedded_texture_count': 4,
                   'model_sha256': lane.PINS['Demon/enemy.bmd'],
                   'animation_rows': {'landing': [0, 69], 'wait': [0, 75], 'flick': [0, 69]}}
        return slot, {'profiles': {'56': profile}}

    def test_clean_contract_and_interface(self):
        slot, family = self.good()
        self.assertEqual(lane.check_contract(slot, family), [])
        self.assertEqual(lane.check_interface(slot), [])

    def test_drifts_rejected(self):
        slot, family = self.good()
        bad = dict(slot, slot=999)
        self.assertTrue(lane.check_contract(bad, family))
        bad = dict(slot, arena_binding='nope')
        self.assertTrue(lane.check_interface(bad))
        prof = dict(family['profiles']['56'], joint_count=14)
        fam2 = {'profiles': {'56': prof}}
        self.assertTrue(lane.check_contract(slot, fam2))
        rows = dict(family['profiles']['56']['animation_rows'], wait=[0, 1])
        prof2 = dict(family['profiles']['56'], animation_rows=rows)
        self.assertTrue(lane.check_contract(slot, {'profiles': {'56': prof2}}))

    def test_packet_requires_all_pinned_files(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(lane.ArtifactError):
                lane.build_packet(temp, str(Path(temp) / 'packet.json'))
            (Path(temp) / 'damagumo-family.json').write_text('X', encoding='utf-8')
            (Path(temp) / 'Demon').mkdir()
            with self.assertRaises(lane.ArtifactError):
                lane.build_packet(temp, str(Path(temp) / 'packet.json'))


if __name__ == '__main__':
    unittest.main()
