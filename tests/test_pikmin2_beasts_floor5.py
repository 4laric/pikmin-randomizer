import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experimental.pikmin2_beasts_floor5 import ROOM,build,fixture,sha


class Floor5Tests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.package=self.root/'package';room=self.package/'rooms'/ROOM;room.mkdir(parents=True)
        self.files={'room.mod':b'model','room.ini':b'route','collision.json':b'{}'}
        for name,data in self.files.items():(room/name).write_bytes(data)
        self.report=dict(policy='P2_BEASTS_FINAL_FLOORS_1',floors=[dict(floor=5,source_definition=dict(
            parameters=dict(f008='1_units_boss_tsuchi.txt',f007='1',f010='1'),
            enemies=[dict(enemy_id='Queen',carried_treasure='radar_a'),dict(enemy_id='HikariKinoko',carried_treasure=None)]))],
            rooms={ROOM:dict(floor=5,exits_capped=True,output_sha256={n:sha(d) for n,d in self.files.items()})},
            source_sha256={'source':sha(b'disc')})
        (self.root/'iso').write_bytes(b'disc');self.save()
    def save(self):(self.package/'final-floors.json').write_text(json.dumps(self.report))
    def build(self):
        with patch('experimental.pikmin2_beasts_floor5.disc_files',return_value={'source':(0,4)}):
            return build(self.root/'iso',self.package,self.root/'out')
    def test_preserves_source_and_marks_engineering_only(self):
        result=self.build()
        self.assertFalse(result['campaign_entry']);self.assertFalse(result['native_ready'])
        self.assertEqual(result['source_definition']['enemies'][0]['carried_treasure'],'radar_a')
        for name,data in self.files.items():self.assertEqual((self.root/'out'/name).read_bytes(),data)
        with self.assertRaises(FileExistsError):self.build()
    def test_changed_model_and_disc_rejected_before_output(self):
        model=self.package/'rooms'/ROOM/'room.mod';model.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'input changed'):self.build()
        model.write_bytes(self.files['room.mod']);(self.root/'iso').write_bytes(b'evil')
        with self.assertRaisesRegex(ValueError,'provenance'):self.build()
        self.assertFalse((self.root/'out').exists())
    def test_wrong_boss_or_exit_rejected(self):
        source=self.report['floors'][0]['source_definition']
        for key in ('f007','f010','f008'):
            before=source['parameters'][key];source['parameters'][key]='wrong';self.save()
            with self.subTest(key=key),self.assertRaises(ValueError):self.build()
            source['parameters'][key]=before
        source['enemies'][0]['carried_treasure']=None;self.save()
        with self.assertRaises(ValueError):self.build()
    def test_fixture_requires_exact_goal_anchor(self):
        def prepare(source,output):output.write_text('changed fixture')
        with patch('experimental.pikmin2_beasts_floor5.prepare_fixture',side_effect=prepare),self.assertRaises(ValueError):
            fixture(self.root/'source.cpp',self.root/'fixture.cpp')
