import tempfile
import json
import subprocess
from pathlib import Path
import unittest
from unittest.mock import patch

from experimental.pikmin2_beasts_floor3_runtime import GOALS, fixture, validate, run


def party():
    return dict(health=.625,squad=[dict(species='red' if i<10 else 'purple',maturity=i%3) for i in range(20)])


def evidence():
    lines=['P2_ROOM_CARGO_FREE_READY cargo=0','P2_FLOOR3_SURVEY_READY']
    lines += [f'P2_FLOOR3_POINT index={i} x={x} y=0 z={z} ground=0' for i,(x,z) in enumerate(GOALS)]
    lines += ['P2_BEASTS_PARTY health=0.625 count=20']
    lines += [f'P2_BEASTS_SURVIVOR index={i} species={p["species"]} maturity={p["maturity"]}' for i,p in enumerate(party()['squad'])]
    lines += ['P2_BEASTS_PARTY_END','PASS P2_FLOOR3_SURVEY goals=12 cargo=0 pokos=0 repairs_unchanged=1']
    return '\n'.join(lines)+'\n'


class FloorThreeRuntimeTests(unittest.TestCase):
    def test_merged_floor_profiles_through_runner(self):
        # Synthetic process output tests the merged dispatcher, not native play.
        for floor, bound, correct_profile, accepted in (
            (4, False, True, True), (4, True, True, True),
            (4, True, False, False), (5, False, True, True),
            (5, True, True, False),
        ):
            with self.subTest(floor=floor, bound=bound, profile=correct_profile), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                exe = root / 'fixture.exe'
                exe.write_bytes(b'not an executable: process is mocked')
                report = dict(floor=floor, party=party(), goals=GOALS, input_sha256={})
                log = evidence()
                if bound:
                    token = 'd' * 64
                    report.update(boundary_token=token, native_profile='forest_1',
                                  party_restore_protocol_floor=floor if correct_profile else 3)
                    log = (f'P2_CAVE_READY floor={floor} survivors=20 health=0.625\n'
                           f'P2_BEASTS_ENTRY_READY floor={floor} token={token} descent=disabled\n') + log
                    log = log.replace('P2_FLOOR3_SURVEY_READY',
                                      f'P2_FLOOR3_BOUNDARY_VERIFIED token={token} descent=disabled\nP2_FLOOR3_SURVEY_READY')
                log = log.replace('P2_FLOOR3', f'P2_FLOOR{floor}')
                (root / 'survey.json').write_text(json.dumps(report))

                def process(args, **kwargs):
                    kwargs['stdout'].write(log)
                    return subprocess.CompletedProcess(args, 0)

                with patch('experimental.pikmin2_beasts_floor3_runtime.subprocess.run', side_effect=process):
                    if accepted:
                        result = run(exe, root)
                        self.assertTrue(result['passed'])
                        self.assertEqual(result['survey']['points'], 12)
                        self.assertEqual(result['issue'], 333 if floor == 5 else 334 if bound else 330)
                    else:
                        with self.assertRaises(ValueError):
                            run(exe, root)
                        self.assertFalse(json.loads((root / 'acceptance.json').read_text())['passed'])

    def test_native_evidence_requires_order_ground_and_party(self):
        log=evidence();self.assertEqual(validate(log,party())['points'],12)
        for bad in [log.replace('index=5 x=','index=4 x='),
                    log.replace('y=0 z=','y=8 z=',1),
                    log.replace('x=-85 y=','x=85 y=',1),
                    log.replace('health=0.625','health=1'),
                    log.replace('species=purple','species=red',1),
                    log+'P2_FLOOR3_POINT malformed\n',log+'P2_POD_RECEIPT\n',log+'FAIL injected\n',
                    log.replace('P2_FLOOR3_SURVEY_READY','P2_FLOOR3_SURVEY_READY\nP2_FLOOR3_SURVEY_READY'),
                    log.replace('P2_FLOOR3_POINT index=0','P2_FLOOR3_POINT index=100')]:
            with self.subTest(bad=bad[:80]),self.assertRaises(ValueError):validate(bad,party())

    def test_fixture_anchor_change_and_output_reuse_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'input.cpp';output=root/'fixture.cpp'
            source.write_text('unexpected native source')
            with self.assertRaises(ValueError):fixture(source,output)
            self.assertFalse(output.exists())
            source.write_text('class RoomApp : public PlugPikiApp {\nif(beastsFloor2Enabled && pc_p2_preview_cargo_free_ready()) {\nbeastsFloor2Fixture(n);')
            fixture(source,output)
            self.assertIn('floorThreeSurvey(n);',output.read_text())
            with self.assertRaises(ValueError):fixture(source,output)


if __name__=='__main__':unittest.main()
