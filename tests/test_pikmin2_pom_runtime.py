"""Tests for experimental/pikmin2_pom_runtime.py and the native #448 policy.

Pure consistency and protocol checks always run. The native policy test is
compiled and executed with strict MinGW flags when a compiler and the
native-patches/pom header are available; otherwise it is skipped.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from experimental import pikmin2_flora_behavior as fb
from experimental import pikmin2_pom_runtime as pr

ROOT = Path(__file__).resolve().parents[1]

SPECS = [dict(generator=240011, species='RedPom', x=0.0, y=30.0, z=1850.0),
         dict(generator=240012, species='RandPom', x=30.0, y=30.0, z=1850.0),
         dict(generator=240013, species='Pom', x=60.0, y=30.0, z=1850.0)]


class ProtocolTests(unittest.TestCase):
    def test_sidecar_round_trip(self):
        text = pr.pom_sidecar(SPECS).decode('ascii')
        lines = text.splitlines()
        self.assertEqual(lines[0], 'P2_POM_1 3')
        self.assertEqual(lines[1], '240011 RedPom 0.0 30.0 1850.0')
        self.assertEqual(lines[2], '240012 RandPom 30.0 30.0 1850.0')
        self.assertEqual(lines[3], '240013 Pom 60.0 30.0 1850.0')

    def test_sidecar_rejections(self):
        def reject(specs):
            with self.assertRaises(ValueError):
                pr.pom_sidecar(specs)
        reject([])
        reject(SPECS + [dict(SPECS[0])])                                      # duplicate generator
        reject([dict(SPECS[0], generator=1 << 32)])                           # id overflow
        reject([dict(SPECS[0], species='GreenPom')])                          # unknown species
        reject([dict(SPECS[0], x=float('nan'))])                              # non-finite position
        reject([dict(SPECS[0], z=100001)])                                    # position bound

    def test_inject_round_trip_and_rejections(self):
        text = pr.pom_inject([dict(generator=240012, fail_births=2)]).decode('ascii')
        self.assertEqual(text, 'P2_POM_INJECT_1 1\n240012 2\n')
        self.assertEqual(pr.pom_inject([]).decode('ascii'), 'P2_POM_INJECT_1 0\n')

        def reject(entries):
            with self.assertRaises(ValueError):
                pr.pom_inject(entries)
        reject([dict(generator=240012, fail_births=2), dict(generator=240012, fail_births=1)])  # duplicate
        reject([dict(generator=1 << 32, fail_births=1)])                                       # id overflow
        reject([dict(generator=240012, fail_births=-1)])                                       # negative failures
        reject([dict(generator=240012, fail_births=100001)])                                   # bound

    def test_validate_pass_and_fail(self):
        text = (
            'P2_POM_READY generator=240011 species=RedPom source_id=4 colour=1 budget=5 queen=0 x=0.00 y=30.00 z=1850.00\n'
            'P2_POM_READY generator=240012 species=RandPom source_id=8 colour=-1 budget=1 queen=1 x=30.00 y=30.00 z=1850.00\n'
            'P2_POM_BASE_REJECTED generator=240013 species=Pom source_id=82 reason=nonspawnable_base\n'
            'P2_POM_INVULNERABLE generator=240011 invulnerable_after_landing=1\n'
            'P2_POM_INVULNERABLE generator=240012 invulnerable_after_landing=1\n'
            'P2_POM_REFUND generator=240011 species=RedPom thrown_colour=1 used=0 budget=5 slot_refunded=1\n'
            'P2_POM_ACCEPT generator=240011 species=RedPom thrown_colour=0 used=1 budget=5\n'
            'P2_POM_ACCEPT generator=240012 species=RandPom thrown_colour=2 used=1 budget=1\n'
            'P2_POM_CLOSE generator=240011 species=RedPom outcome=shot used=1 budget=5 swallowed=2\n'
            'P2_POM_CLOSE generator=240012 species=RandPom outcome=shot used=1 budget=1 swallowed=1\n'
            'P2_POM_SPROUT generator=240011 species=RedPom count=2 colour=1 body=1 leaf=1\n'
            'P2_POM_SPROUT generator=240012 species=RandPom count=9 colour=0 body=0 leaf=1\n'
            'P2_POM_SPROUT_RETRY generator=240012 species=RandPom owed_remaining=9 requested=9 born=0 item_capacity=1 forced=1\n'
            'P2_POM_SPROUT_SETTLED generator=240012 species=RandPom requested=9 born=9 conservation=1\n'
            'PASS P2_POM_NATIVE accept_refund_close_sprout\n'
        )
        good = pr.validate(text, 0)
        self.assertTrue(good['passed'], good['failed'])
        missing = text.replace('P2_POM_REFUND generator=240011 species=RedPom thrown_colour=1 used=0 budget=5 slot_refunded=1\n', '')
        bad = pr.validate(missing, 0)
        self.assertFalse(bad['passed'])
        self.assertIn('refund', bad['failed'])
        # A Queen that still falls back to the -1 sentinel colour must fail.
        legacy = text.replace('P2_POM_SPROUT generator=240012 species=RandPom count=9 colour=0 body=0 leaf=1',
                              'P2_POM_SPROUT generator=240012 species=RandPom count=9 colour=-1 leaf=1')
        self.assertFalse(pr.validate(legacy, 0)['passed'])
        # A silently dropped birth (no settled conservation) must fail.
        dropped = text.replace('P2_POM_SPROUT_SETTLED generator=240012 species=RandPom requested=9 born=9 conservation=1\n', '')
        self.assertFalse(pr.validate(dropped, 0)['passed'])

    def test_instrument_replaces_room_app(self):
        source = 'prefix\nclass RoomApp : public PlugPikiApp {\n int idle() override { return 0; }\n};\nint main(int, char**) { return 0; }\n'
        out = pr.instrument(source)
        self.assertIn('PASS P2_POM_NATIVE', out)
        self.assertIn('int main(', out)


class ConsistencyTests(unittest.TestCase):
    """Native policy constants must keep matching the #171 behavior model."""

    def test_reference_facts_used_by_the_actor(self):
        self.assertEqual(fb.CANDYPOPS['BluePom']['enemy_id'], 3)
        self.assertEqual(fb.CANDYPOPS['RandPom']['enemy_id'], 8)
        self.assertEqual(fb.POM_PROPER_DISC['ip01'], 5)
        self.assertEqual(fb.POM_PROPER_DISC['ip11'], 1)
        self.assertEqual(fb.POM_PROPER_DISC['ip13'], 9)
        self.assertEqual(fb.POM_PROPER_DISC['fp01'], 1.0)
        self.assertEqual(fb.POM_PROPER_DISC['fp02'], 2.6)
        self.assertEqual(tuple(fb.QUEEN_COLOUR_CYCLE), ('blue', 'red', 'yellow'))
        self.assertEqual(tuple(fb.POM_SPROUT_LAUNCH), (110.0, 750.0, 110.0))
        self.assertEqual(fb.POM_COLOUR_CAP['BlackPom'], 20)
        self.assertEqual(fb.POM_WHITE_FLOWER_GARDEN, 'White Flower Garden')
        self.assertEqual(fb.POM_BASE_ID, 82)
        self.assertFalse(fb.is_spawnable('Pom'))
        # Policy function spot-checks.
        self.assertEqual(fb.candypop_budget('BluePom'), 5)
        self.assertEqual(fb.candypop_budget('RandPom'), 1)
        self.assertEqual(fb.candypop_own_colour('RedPom'), 'red')
        self.assertIsNone(fb.candypop_own_colour('RandPom'))
        self.assertTrue(fb.candypop_refund(species='RedPom', thrown_colour='red'))
        self.assertFalse(fb.candypop_refund(species='RandPom', thrown_colour='red'))
        self.assertTrue(fb.candypop_accept(species='RedPom', slot_pressed=True, armed=True, used_slots=0))
        self.assertFalse(fb.candypop_accept(species='RedPom', slot_pressed=True, armed=True, used_slots=5))
        self.assertEqual(fb.candypop_shot_count(species='RandPom', swallowed=2), 18)
        self.assertEqual(fb.candypop_shot_count(species='RedPom', swallowed=2), 2)
        self.assertEqual(fb.candypop_close(seconds_since_last_swallow=0.5, remain_open_seconds=1.0,
                                           budget_spent=False, pikmin_inside=True), None)
        self.assertEqual(fb.candypop_close(seconds_since_last_swallow=1.0, remain_open_seconds=1.0,
                                           budget_spent=False, pikmin_inside=True), 'shot')
        self.assertEqual(fb.candypop_close(seconds_since_last_swallow=1.0, remain_open_seconds=1.0,
                                           budget_spent=False, pikmin_inside=False), 'reopen')
        self.assertEqual(fb.candypop_queen_colour(elapsed_seconds=2.6, met_colours=('blue', 'red', 'yellow')), 'red')
        self.assertFalse(fb.candypop_spawn_allowed(species='BlackPom', floor=1, cave='Emergence Cave',
                                                   met_colours=(), player_count=20))

    def test_native_policy_executable(self):
        candidates = [ROOT / 'native-patches' / 'pom']
        if os.environ.get('P2_NATIVE_PC_PORT'):
            candidates.append(Path(os.environ['P2_NATIVE_PC_PORT']))
        include = next((c for c in candidates if (c / 'pc_p2_pom_policy.h').is_file()), None)
        compiler = Path('C:/msys64/mingw64/bin/g++.exe')
        if include is None or not compiler.is_file():
            return
        source = ROOT / 'tests' / 'pikmin2_pom_policy.cpp'
        with tempfile.TemporaryDirectory(prefix='p2-pom-policy-') as tmp:
            exe = Path(tmp) / 'pom_policy.exe'
            env = dict(os.environ, PATH=str(compiler.parent) + os.pathsep + os.environ.get('PATH', ''))
            subprocess.run([str(compiler), '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(include),
                            str(source), '-o', str(exe)], check=True, capture_output=True, env=env)
            run = subprocess.run([str(exe)], check=True, capture_output=True, text=True, env=env)
            self.assertIn('PASS', run.stdout)


if __name__ == '__main__':
    unittest.main()
