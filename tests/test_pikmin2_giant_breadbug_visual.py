import json
import tempfile
import unittest
from pathlib import Path
from experimental.pikmin2_giant_breadbug_visual import prepare, install, CONFIG

ROOT=Path('C:/Users/alari/pikmin-randomizer/output/p2-lifecycle-batch')
SOURCE=ROOT/'breadbug-lane-03'
PROFILE=ROOT/'breadbug-lane-install-01/profile'
PLACEMENTS=[dict(display_id=229001,kind='wait',position=[-150,30,1850],yaw_degrees=0),dict(display_id=229002,kind='nest',position=[150,30,1850],yaw_degrees=0)]

@unittest.skipUnless((PROFILE/'breadbug-lane-profile.json').exists(),'local legal assets required')
class GiantTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def profile(self):
        p=self.root/'profile';prepare(SOURCE,PROFILE,p,PLACEMENTS);return p
    def runpath(self):
        r=self.root/'run';(r/'assets/dataDir/courses/pikmin2room').mkdir(parents=True);return r
    def test_reproducible_install_and_disk_hash(self):
        a=self.profile();b=self.root/'b';prepare(SOURCE,PROFILE,b,PLACEMENTS)
        self.assertEqual({str(p.relative_to(a)):p.read_bytes() for p in a.rglob('*') if p.is_file()},{str(p.relative_to(b)):p.read_bytes() for p in b.rglob('*') if p.is_file()})
        r=self.runpath();m=install(a,r);self.assertEqual((a/CONFIG).read_bytes(),(r/CONFIG).read_bytes());self.assertNotIn(b'\r',(r/CONFIG).read_bytes())
        self.assertEqual(11,len(m['files']));self.assertFalse(m['native_validated'])
        with self.assertRaises(ValueError):install(a,r)
    def test_tamper_rejected_before_writes(self):
        a=self.profile();next((a/'models').glob('*.mod')).write_bytes(b'bad');r=self.runpath()
        with self.assertRaises(ValueError):install(a,r)
        self.assertFalse((r/CONFIG).exists());self.assertEqual([],list((r/'assets/dataDir/courses/pikmin2room').iterdir()))
    def test_invalid_placements(self):
        for rows in [PLACEMENTS+[PLACEMENTS[0]],[dict(PLACEMENTS[0],position=[float('nan'),0,0])],[dict(PLACEMENTS[0],kind='actor')]]:
            with self.assertRaises(ValueError):prepare(SOURCE,PROFILE,self.root/'bad',rows)
    def test_metadata_config_disagreement(self):
        a=self.profile();p=a/'giant-breadbug-visual.json';m=json.loads(p.read_bytes());m['placements'][0]['position'][0]+=1;p.write_text(json.dumps(m));r=self.runpath()
        with self.assertRaises(ValueError):install(a,r)
    def test_source_identity_mismatch(self):
        source=self.root/'source';source.mkdir();raw=(SOURCE/'breadbug-lane.json').read_bytes();(source/'breadbug-lane.json').write_bytes(raw+b' ')
        with self.assertRaises(ValueError):prepare(source,PROFILE,self.root/'bad',PLACEMENTS)

if __name__=='__main__':unittest.main()
