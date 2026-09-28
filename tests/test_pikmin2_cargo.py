import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from experimental.pikmin2_cargo import read_cargo
from experimental.pikmin2_campaign import allowed_receipts, initial, transition, entry_text, content_identity


class CargoContractTests(unittest.TestCase):
    def test_separate_receipts_reject_legacy_or_wrong_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'p2-pod.txt').write_text('P2_POD_1 dia_a_red 180 15 25 Kochappy 2')
            (root/'p2-cargo.txt').write_text('P2_CARGO_1\n2\n5000 tutorial_1:floor1:citrus citrus 180 15 25\n5001 tutorial_1:floor1:emblem emblem 100 4 8\n')
            with patch('scripts.preview_pikmin2_room.records', return_value=[]):
                allowed = allowed_receipts(root,1)
            self.assertEqual(sum(allowed.values()),280)
            self.assertEqual(len(allowed),2)
            state=initial('a'*64)
            text=entry_text(state,'b'*32).replace('P2_CAVE_ENTRY_1','P2_CAVE_TRANSFER_1')
            next_state=transition(state,'b'*32,text,allowed,allowed)
            self.assertEqual(next_state['receipts'],allowed)
            for receipts in ({'treasure:dia_a_red':180},{'treasure:tutorial_1:floor1:emblem':180}):
                with self.assertRaises(ValueError):transition(state,'b'*32,text,receipts,allowed)

    def test_invalid_or_duplicate_config(self):
        good='5000 tutorial_1:floor1:item model 180 101 101'
        bad=[good+'\n'+good,good.replace('model','../model'),good.replace(' 101 101',' 0 101'),
             good.replace(' 101 101',' 101 129'),good.replace('5000','4294967296'),
             good.replace(' 180 ',' -1 '),good.replace('item','item?'),good+' junk']
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'cargo.txt'
            for row in bad:
                with self.subTest(row=row):
                    path.write_text('P2_CARGO_1\n'+str(len(row.splitlines()))+'\n'+row+'\n')
                    with self.assertRaises(ValueError):read_cargo(path)

    def test_roster_identity_includes_manifest_and_each_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for unit in ('room_north_tutorial_1_snow','room_purple14x14_snow'):
                directory=root/'units'/unit;directory.mkdir(parents=True)
                for name in ('render.mod','collision.json'):(directory/name).write_bytes(b'fixture')
            for name in ('manifest.json','pod.mod','treasure.mod','p2-pod.txt','p2-purple.txt'):(root/name).write_bytes(b'fixture')
            roster=root/'roster';roster.mkdir();(roster/'content.json').write_text('{}')
            model=roster/'treasures'/'emblem'/'treasure.mod';model.parent.mkdir(parents=True);model.write_bytes(b'model')
            baseline=content_identity(root,[root,root],root)
            enabled=content_identity(root,[root,root],root,roster=roster)
            self.assertNotEqual(baseline,enabled)
            model.write_bytes(b'changed')
            self.assertNotEqual(enabled,content_identity(root,[root,root],root,roster=roster))
