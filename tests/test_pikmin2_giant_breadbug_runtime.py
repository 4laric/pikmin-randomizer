import tempfile
import unittest
from pathlib import Path
from experimental.pikmin2_giant_breadbug_runtime import validate,instrument,stage
from scripts.preview_pikmin2_room import records

class RuntimeTests(unittest.TestCase):
    def test_log_requires_reset_reload_both_draws(self):
        text='P2_GIANT_BREADBUG_VISUAL_READY \nP2_GIANT_BREADBUG_VISUAL_DRAW \n'*2+'P2_GIANT_RESET_REQUEST\nP2_GIANT_RELOAD_REQUEST\nP2_GIANT_GROUND \nPASS P2_GIANT_DISPLAY_RUNTIME '
        self.assertTrue(validate(text,0,'wait')['passed'])
        for bad in (text.replace('P2_GIANT_RESET_REQUEST',''),text.replace('P2_GIANT_RELOAD_REQUEST',''),text.replace('P2_GIANT_BREADBUG_VISUAL_DRAW ','',1)):
            self.assertFalse(validate(bad,0,'wait')['passed'])
        self.assertFalse(validate(text,1,'wait')['passed']);self.assertFalse(validate(text,0,'disabled')['passed'])
    def test_disabled_requires_no_display(self):
        text='P2_GIANT_RESET_REQUEST\nP2_GIANT_RELOAD_REQUEST\nPASS P2_GIANT_DISPLAY_RUNTIME '
        self.assertTrue(validate(text,0,'disabled')['passed']);self.assertFalse(validate(text+'P2_GIANT_BREADBUG_VISUAL_DRAW ',0,'disabled')['passed'])
    def test_instrument_owns_only_fixture_app(self):
        text='//prefix\nclass RoomApp : public PlugPikiApp { OLD };\nint main(){}'
        result=instrument(text);self.assertIn('//prefix',result);self.assertIn('int main(){}',result);self.assertNotIn(' OLD ',result)

ASSETS=Path('C:/Users/alari/bbft/dist/cohesion/pikmin/assets')
PROFILE=Path(__file__).resolve().parents[1]/'output/p2-giant-breadbug-binding/profile-a'
@unittest.skipUnless((PROFILE/'giant-breadbug-visual.json').exists() and ASSETS.exists(),'local assets required')
class StageTests(unittest.TestCase):
    def test_private_stage_has_no_enemy_or_cargo_and_delayed_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=stage(ASSETS,PROFILE,Path(tmp),'wait');rows=records(run/'assets/dataDir/stages/chal0/default.gen')
            self.assertFalse(any(r[72:76] in (b'iket',b'tlep') for r in rows))
            self.assertEqual(20,sum(r[72:76]==b'ikip' for r in rows))
            self.assertFalse((run/'p2-giant-breadbug-visual.txt').exists());self.assertTrue((run/'giant-fixture-profile.txt').exists())
            self.assertEqual(b'P2_CARGO_FREE_1\n',(run/'p2-cargo-free.txt').read_bytes())

if __name__=='__main__':unittest.main()
