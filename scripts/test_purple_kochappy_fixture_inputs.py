"""Prelaunch refusal tests only; fake bytes never stand in for a game runtime."""
import hashlib,tempfile,unittest
from pathlib import Path
from scripts.run_pikmin2_purple_kochappy import DLLS,runtime_dependencies,controlled_environment

class Inputs(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.source=self.base/'package';self.local=self.base/'consumer'
        self.source.mkdir();self.local.mkdir();self.exe=self.local/'fixture.exe';self.exe.write_bytes(b'not executable, test only')
        self.pin='e'*40;rows=[]
        for name in DLLS:
            payload=('test only '+name).encode();digest=hashlib.sha256(payload).hexdigest()
            (self.source/name).write_bytes(payload);(self.local/name).write_bytes(payload);rows.append(digest+' *./'+name)
        (self.source/'sha256.txt').write_text('\n'.join(rows)+'\n')
        (self.source/'BUILD_INFO.txt').write_text('commit '+self.pin+'\n')
    def test_matching_all_four(self):
        r=runtime_dependencies(self.exe,self.source,self.pin);self.assertEqual(set(r['dlls']),set(DLLS))
    def test_source_missing(self):
        (self.source/'SDL2.dll').unlink()
        with self.assertRaisesRegex(ValueError,'CI runtime DLL'):runtime_dependencies(self.exe,self.source,self.pin)
    def test_source_conflict(self):
        (self.source/'libgcc_s_seh-1.dll').write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError,'CI runtime DLL'):runtime_dependencies(self.exe,self.source,self.pin)
    def test_exe_local_missing(self):
        (self.local/'SDL2.dll').unlink()
        with self.assertRaisesRegex(ValueError,'executable-local DLL'):runtime_dependencies(self.exe,self.source,self.pin)
    def test_exe_local_conflict(self):
        (self.local/'libstdc++-6.dll').write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError,'executable-local DLL'):runtime_dependencies(self.exe,self.source,self.pin)
    def test_manifest_omits_dll(self):
        p=self.source/'sha256.txt';p.write_text('\n'.join(p.read_text().splitlines()[:-1]))
        with self.assertRaisesRegex(ValueError,'manifest missing'):runtime_dependencies(self.exe,self.source,self.pin)
    def test_pin_mismatch(self):
        with self.assertRaisesRegex(ValueError,'source pin'):runtime_dependencies(self.exe,self.source,'0'*40)
    def test_poison_environment(self):
        ambient={'PIKMIN_OTHER':'poison','P2_OTHER':'poison','COOP_FAKE':'poison','p2_lowercase':'poison','NECTAR_SAVE_DIR':'shared','NECTAR_SETTINGS_PATH':'shared','PATH':'system','SystemRoot':'windows'}
        env=controlled_environment(ambient,self.exe,self.source,self.base/'private-save','positive')
        self.assertFalse(any(k in env for k in ('PIKMIN_OTHER','P2_OTHER','COOP_FAKE','p2_lowercase','NECTAR_SETTINGS_PATH')))
        self.assertEqual(env['PIKMIN_P2_TEST_START_DAY'],'5');self.assertEqual(env['PIKMIN_P2_ROOM_WINDOW'],'960x540')
        self.assertEqual(env['SystemRoot'],'windows');self.assertEqual(env['NECTAR_SAVE_DIR'],str((self.base/'private-save').resolve()))
        self.assertNotIn('P2_PURPLE_KOCHAPPY_FORCE_DOWN',env)
    def test_only_selected_negative_flag(self):
        e=controlled_environment({'P2_PURPLE_KOCHAPPY_FORCE_DOWN':'ambient'},self.exe,self.source,self.base/'save','paused-down')
        self.assertNotIn('P2_PURPLE_KOCHAPPY_FORCE_DOWN',e);self.assertEqual(e['P2_PURPLE_KOCHAPPY_PAUSED_DOWN'],'1')

if __name__=='__main__':unittest.main()
