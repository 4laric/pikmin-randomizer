import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from experimental.pikmin2_selected_units import select,import_units


def inputs():
    definition=dict(name='room',doors=[])
    floor=dict(first_floor=1,last_floor=1,parameters={'f008':'pool'})
    catalog=dict(schema=1,caves=[dict(cave_id='test',floors=[floor])],unit_pools={'pool':dict(units=[definition])},source_sha256={})
    dependencies=dict(schema=1,caves=[dict(cave_id='test',floors=[dict(first_floor=1,last_floor=1,unit_pool='pool',unit_candidates=['room'])])])
    return catalog,dependencies


class SelectedUnitTests(unittest.TestCase):
    def test_selection_is_exact_and_deterministic(self):
        c,d=inputs();before=copy.deepcopy((c,d))
        self.assertEqual(select(c,d,'test'),select(c,d,'test'))
        self.assertEqual((c,d),before)
        self.assertEqual(list(select(c,d,'test')[0]),['room'])
        with self.assertRaises(ValueError):select(c,d,'missing')
        d['caves'][0]['floors'][0]['unit_candidates']=[]
        with self.assertRaises(ValueError):select(c,d,'test')

    def test_water_failure_is_recorded_not_approximated(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);c,d=inputs();cp=root/'catalog.json';dp=root/'deps.json'
            cp.write_text(json.dumps(c));d['catalog_sha256']=hashlib.sha256(cp.read_bytes()).hexdigest();dp.write_text(json.dumps(d))
            iso=root/'disc';iso.write_bytes(b'ab')
            files={'user/Mukki/mapunits/arc/room/arc.szs':(0,1),'user/Mukki/mapunits/arc/room/texts.szs':(1,1)}
            def archive(data):return {'view.bmd':b'x'} if data==b'a' else {'waterbox.txt':b'1 { 1 }'}
            with patch('experimental.pikmin2_selected_units.disc_files',return_value=files),patch('experimental.pikmin2_selected_units.archive_files',side_effect=archive),patch('experimental.pikmin2_selected_units.convert') as converter:
                result=import_units(iso,cp,dp,root/'out','test',True)
                unit=result['units']['room']
                self.assertEqual(unit['status'],'unsupported');self.assertFalse(unit['assembly_ready'])
                self.assertIn('Water-volume',unit['failure']);converter.assert_not_called()
                self.assertFalse((root/'out/units/room/room.mod').exists())
                with self.assertRaises(FileExistsError):import_units(iso,cp,dp,root/'out','test')

    def test_stale_dependency_fingerprint_rejected_before_disc_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);c,d=inputs();d['catalog_sha256']='bad'
            cp=root/'c';dp=root/'d';cp.write_text(json.dumps(c));dp.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError,'fingerprint'):import_units(root/'missing',cp,dp,root/'out','test')
