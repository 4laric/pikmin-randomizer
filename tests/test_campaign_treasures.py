import hashlib
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from randomizer.campaign_treasures import prepare
from randomizer.purple_campaign import split_records
from tests.test_white_treasure_campaign import goal, framed


class CampaignTreasures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.model = self.root / 'model.mod'; self.model.write_bytes(b'synthetic-model')
        self.pod = self.root / 'pod.mod'; self.pod.write_bytes(b'synthetic-pod')
        self.template = bytearray(84); self.template[:8] = b'    0.0v'
        self.template[72:80] = b'tlep0.0v'; self.template[80:84] = b'50rp'
        self.source = framed([goal()])
        self.entries = {name: dict(dictionary=i+1, value=180+i, minimum=15, maximum=25)
                        for i, name in enumerate(('dia_a_red', 'synthetic_a', 'synthetic_b'))}
        self.patch = patch('randomizer.campaign_treasures.verified_entries', return_value=self.entries)
        self.patch.start(); self.addCleanup(self.patch.stop)

    def prepare(self, requests, **kwargs):
        return prepare({1: self.source}, self.template, requests, self.root / 'catalog',
                       dict.fromkeys(self.entries, self.model), self.pod, **kwargs)

    def test_multiple_actual_records_preserve_source_and_bind_final_generator(self):
        requests = [dict(stage=1, id=name, position=(10+i*50, 20, 300))
                    for i, name in enumerate(('synthetic_a', 'synthetic_b'))]
        result = self.prepare(requests)
        staged = result['stages'][1]
        self.assertEqual(staged[:20], self.source[:20])
        self.assertEqual(staged[24:len(self.source)], self.source[24:])
        rows = split_records(staged); self.assertEqual(len(rows), 3)
        self.assertEqual(struct.unpack_from('>3f', rows[1], 48), (10, 20, 300))
        self.assertEqual(struct.unpack_from('<I', rows[1], 8)[0], 0x54520002)
        descriptor = result['descriptor'].decode().splitlines()
        for row in descriptor[1:]:
            self.assertEqual(row.split()[-1], hashlib.sha256(staged).hexdigest())
        self.assertEqual(result['source_digest'], hashlib.sha256(result['descriptor']).hexdigest())
        self.assertFalse(result['activated'])
        self.assertTrue(all(not fact['physical_delivery_accepted'] for fact in result['facts']))
        self.assertEqual(self.source, framed([goal()]))

    def test_invalid_identity_duplicate_stage_and_positions_refuse_without_source_write(self):
        valid = dict(stage=1, id='synthetic_a', position=(0, 0, 0))
        bad = [dict(valid, id='unknown'), dict(valid, stage=True), dict(valid, stage=5),
               dict(valid, position=(0, float('nan'), 0)), dict(valid, position=(1e300, 0, 0))]
        for request in bad:
            with self.subTest(request=request), self.assertRaises(ValueError): self.prepare([request])
        with self.assertRaises(ValueError): self.prepare([valid, valid])
        with self.assertRaises(ValueError): self.prepare([dict(valid, id='dia_a_red')], white_owned=True)
        self.assertEqual(self.source, framed([goal()]))

    def test_cargo_collision_and_model_change_refuse(self):
        request = dict(stage=1, id='synthetic_a', position=(0, 0, 0))
        existing = bytearray(self.template); struct.pack_into('<I', existing, 8, 0x54520002)
        self.source = framed([goal(), existing])
        with self.assertRaises(ValueError): self.prepare([request])
        self.source = framed([goal()]); self.model.write_bytes(b'')
        with self.assertRaises(ValueError): self.prepare([request])


if __name__ == '__main__': unittest.main()
