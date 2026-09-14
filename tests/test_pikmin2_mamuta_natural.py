"""Lane 19 (#221/#168) natural-observation tests: marker classification and instrumentation."""
from pathlib import Path

import pytest

from experimental.pikmin2_mamuta_natural_runtime import FIXTURE, instrument


def _natural_log(*, approached=1, died=0, corpse=0, carried=0, goal=0, plants=0, reset=True, desync=False):
    lines = [
        'P2_MAMUTA_RULES enabled cap=99 navi_damage=5.0 vertical_band=20',
        'P2_MAMUTA_READY generator=221001 native_type=24 xyz=-150.000000,30.000000,1850.000000 P1_proxy_static_anchors_no_P2_planting',
        'P2_MAMUTA_NATURAL_BIRTH id=221001 type=24 squad=10 color=red',
        'P2_MAMUTA_NATURAL_APPROACH target=-150.0,1870.0 actor=-150.0,1850.0',
        'P2_MAMUTA_NATURAL_OBSERVE tick=30 state=7 health=2424.8 navi=-150.0,1900.0 squad=10 min=55.0 states=00000080',
    ]
    lines += ['P2_MAMUTA_PLANT kind=1 happa=2 planted=1'] * plants
    lines += [
        f'P2_MAMUTA_NATURAL_APPROACH_RESULT approached={approached} min=12.0 states=00000d80',
        'P2_MAMUTA_NATURAL_PLANTED planted=2 bury_states=2',
        f'P2_MAMUTA_NATURAL_RESULT died={died} died_tick=2000 corpse={corpse} carried={carried} goal={goal} control_alive=1 squad=2',
    ]
    if reset:
        lines.append('P2_MAMUTA_NATURAL_RESET')
    if desync:
        lines.append('[PC GX] DESYNC something')
    lines.append('PASS P2_MAMUTA_NATURAL_RUNTIME observe approach reset')
    return '\n'.join(lines) + '\n'


def test_natural_validate_accepts_observed_approach_and_reset():
    from scripts.pikmin2_mamuta_natural_native import validate
    evidence = validate(_natural_log(plants=2, died=1, corpse=1, carried=1, goal=1))
    assert evidence['approached'] is True
    assert evidence['natural_plants'] == 2
    assert evidence['died'] is True and evidence['corpse'] is True
    assert evidence['died_tick'] == 2000
    assert evidence['classify']['natural_flick_bury'] == 'PASS'
    assert evidence['classify']['natural_kill'] == 'PASS'
    assert evidence['classify']['natural_carry'] == 'PASS'
    assert evidence['classify']['reset_reentry'] == 'PASS'


def test_natural_validate_classifies_absent_behavior_unproven():
    from scripts.pikmin2_mamuta_natural_native import validate
    evidence = validate(_natural_log(plants=0, died=0, corpse=0, carried=1, goal=0))
    assert evidence['classify']['natural_flick_bury'] == 'UNPROVEN'
    assert evidence['classify']['natural_kill'] == 'UNPROVEN'
    assert evidence['classify']['natural_corpse'] == 'UNPROVEN'
    assert evidence['classify']['natural_carry'] == 'PARTIAL'


def test_natural_validate_rejects_missing_approach_or_reset_or_desync():
    from scripts.pikmin2_mamuta_natural_native import validate
    with pytest.raises(ValueError):
        validate(_natural_log(approached=0))
    with pytest.raises(ValueError):
        validate(_natural_log(reset=False))
    with pytest.raises(ValueError):
        validate(_natural_log(desync=True))


def test_instrument_replaces_room_app_with_natural_fixture(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source = (root / 'scripts/pikmin2_mamuta_rules_fixture.inc').read_text()
    # Sanity: the natural fragment is on disk and mentions the lane markers.
    fixture = (root / FIXTURE).read_text()
    assert 'P2_MAMUTA_NATURAL_BIRTH' in fixture
    assert 'P2_MAMUTA_NATURAL_RESULT' in fixture
    assert 'P2_MAMUTA_FIXTURE_BURY' not in fixture
    # Instrument a minimal stand-in to prove the splice boundary is exact.
    probe = ('class RoomApp : public PlugPikiApp {\n int idle() override { return 0; }\n};\n'
             'int main(int argc,char** argv) { return 0; }\n')
    spliced = instrument(probe, root)
    assert 'P2_MAMUTA_NATURAL_BIRTH' in spliced
    assert 'class RoomApp : public PlugPikiApp {' in spliced
    assert spliced.rstrip().endswith('int main(int argc,char** argv) { return 0; }')
    assert 'pc_p2_mamuta_rules.h' in spliced
    assert source  # keep the rules fixture referenced for the lane's fixture family
