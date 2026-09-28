import json,tempfile,unittest,struct
from pathlib import Path
from experimental.pikmin2_bulblax_visual import protocol,prepare,install,CONFIG
from experimental.pikmin2_bulblax_runtime import validate,stage,placement_evidence
from scripts.preview_pikmin2_room import records

class ProtocolTests(unittest.TestCase):
    def test_native_identity_and_xyz_must_match_both_loads(self):
        row=dict(placement_id=230001,species='Queen',clip='wait1',xyz=[-120,30,1800])
        line='P2_BULBLAX_VISUAL_READY id=230001 enemy=30 species=Queen clip=wait1 xyz=-120,30,1800 yaw=0 scale=1 noninteractive=1\n'
        self.assertTrue(placement_evidence(line*2,[row],True)['exact_source_identity_xyz_yaw'])
        for bad in (line,line+line.replace('id=230001','id=230002'),line+line.replace('1800','1801')):
            with self.assertRaises(ValueError):placement_evidence(bad,[row],True)
    def test_source_identity_timing_and_bad_xyz(self):
        clips=[dict(species='Queen',name='wait1',duration=30,frames=[0,15,29])];rows=[dict(placement_id=230001,species='Queen',clip='wait1',xyz=[1,2,3])]
        text=protocol(clips,rows);self.assertIn(b'30 wait1 30 3 0 15 29',text);self.assertNotIn(b'\r',text)
        for bad in [dict(rows[0],xyz=[float('nan'),0,0]),dict(rows[0],xyz=[100001,0,0]),dict(rows[0],placement_id=-1),dict(rows[0],species='Baby')]:
            with self.assertRaises(ValueError):protocol(clips,[bad])
        with self.assertRaises(ValueError):protocol(clips,rows*2)
        with self.assertRaises(ValueError):protocol([dict(clips[0],frames=[29,15,0])],rows)
    def test_disabled_rejects_spurious_render(self):
        text='P2_BULBLAX_RESET_REQUEST\nP2_BULBLAX_RELOAD_REQUEST\nP2_BULBLAX_GROUND \nred=5 blue=5\nPASS P2_BULBLAX_DISPLAY_RUNTIME '
        self.assertTrue(validate(text,0,'disabled')['passed']);self.assertFalse(validate(text+'P2_BULBLAX_VISUAL_DRAW enemy=30 clip=wait1 pose=0 source_frame=0',0,'disabled')['passed'])

ORIGINAL=Path('C:/Users/alari/pikmin-randomizer/output/p2-kimi-bulblax/output');BANK=ORIGINAL/'p234-bank-run1';MANIFEST=ORIGINAL/'p234-install/bulblax-install.json'
ASSETS=Path('C:/Users/alari/bbft/dist/cohesion/pikmin/assets')
@unittest.skipUnless(MANIFEST.exists(),'local assets required')
class ActualAssetTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def profile(self):p=self.root/'profile';prepare(MANIFEST,BANK,p);return p
    def test_all174_models_exact_reproducible_install(self):
        p=self.profile();other=self.root/'other';prepare(MANIFEST,BANK,other)
        self.assertEqual({str(f.relative_to(p)):f.read_bytes() for f in p.rglob('*') if f.is_file()},{str(f.relative_to(other)):f.read_bytes() for f in other.rglob('*') if f.is_file()})
        run=self.root/'run';(run/'assets/dataDir/courses/pikmin2room').mkdir(parents=True);m=install(p,run,species='Baby')
        self.assertEqual(174,len(list((run/'assets/dataDir/courses/pikmin2room').glob('*.mod'))));self.assertEqual('Baby',m['placements'][0]['species'])
        with self.assertRaises(ValueError):install(p,run)
    def test_tamper_refused_before_write(self):
        p=self.profile();next((p/'models').glob('*.mod')).write_bytes(b'tampered');run=self.root/'run';room=run/'assets/dataDir/courses/pikmin2room';room.mkdir(parents=True)
        with self.assertRaises(ValueError):install(p,run)
        self.assertEqual([],list(room.iterdir()));self.assertFalse((run/CONFIG).exists())
    def test_preserved_source_xyz_and5red5blue_stage(self):
        p=self.profile();run=stage(ASSETS,p,self.root/'stages','KingChappy');rows=records(run/'assets/dataDir/stages/chal0/default.gen');pikis=[r for r in rows if r[72:76]==b'ikip']
        colors=[struct.unpack_from('>I',r,92)[0] for r in pikis];self.assertEqual([1]*5+[0]*5,colors);self.assertFalse(any(r[72:76] in (b'iket',b'tlep') for r in rows))
        m=json.loads((run/'bulblax-stage.json').read_bytes());self.assertEqual([150.,30.,1500.],m['placements'][0]['xyz']);self.assertFalse((run/CONFIG).exists())

if __name__=='__main__':unittest.main()
