"""Lane 19 (#221/#168) Pod-arena tests: marker classification and instrumentation."""
from pathlib import Path

import pytest

from experimental.pikmin2_mamuta_natural_runtime import instrument
from scripts.pikmin2_mamuta_pod_native import ASSISTED_FIXTURE, POD_FIXTURE


def _pod_log(*, assisted=False, died=1, corpse=1, carried=1, goal=1, receipt=True,
             pokos=182, reset=True, desync=False, captain_down=False):
    lines = [
        'P2_MAMUTA_RULES enabled cap=99 navi_damage=5.0 vertical_band=20',
        'P2_MAMUTA_READY generator=221001 native_type=24 xyz=-150.000000,30.000000,1850.000000 P1_proxy_static_anchors_no_P2_planting',
        'P2_POD_READY treasure=dia_a_red value=180 weight=15 capacity=25 pokos=0',
        'P2_MAMUTA_POD_BIRTH id=221001 type=24 squad=14 color=red',
        'P2_MAMUTA_POD_APPROACH target=-150.0,1870.0 actor=-150.0,1850.0',
    ]
    if assisted:
        lines.append('P2_MAMUTA_POD_MODE assisted=1 (direct Transport assignment; not natural pickup)')
    lines.append('P2_MAMUTA_POD_OBSERVE tick=30 state=7 health=2424.8 navi=-150.0,1900.0 squad=10 min=55.0 states=00000080 pokos=0')
    lines.append('P2_MAMUTA_POD_APPROACH_RESULT approached=1 min=12.0 states=00000d80')
    lines.append('P2_MAMUTA_POD_PLANTED planted=2 bury_states=2')
    if captain_down:
        lines.append('P2_MAMUTA_POD_CAPTAIN_DOWN tick=1234 health=0.0')
    if assisted and carried:
        lines.append('P2_MAMUTA_POD_ASSIST carriers=8 assisted=1')
    if receipt:
        lines.append('P2_POD_RECEIPT id=corpse:ujino:mamuta:221001 value=2 new=1 pokos=182 seeds=0')
    if assisted:
        lines.append(f'P2_MAMUTA_POD_RESULT assisted=1 died={died} died_tick=2000 corpse={corpse} '
                     f'carried={carried} goal={goal} pokos={pokos} control_alive=1 squad=2')
    else:
        lines.append(f'P2_MAMUTA_POD_RESULT died={died} died_tick=2000 corpse={corpse} '
                     f'carried={carried} goal={goal} pokos={pokos} control_alive=1 squad=2')
    if reset:
        lines.append('P2_MAMUTA_POD_RESET')
    if desync:
        lines.append('[PC GX] DESYNC something')
    if captain_down:
        lines.append('PASS P2_MAMUTA_POD_RUNTIME captain_down')
    else:
        lines.append('PASS P2_MAMUTA_POD_RUNTIME assisted approach receipt reset' if assisted
                     else 'PASS P2_MAMUTA_POD_RUNTIME observe approach receipt reset')
    return '\n'.join(lines) + '\n'


def test_pod_validate_accepts_natural_receipt():
    from scripts.pikmin2_mamuta_pod_native import validate
    evidence = validate(_pod_log(), assisted=False)
    assert evidence['pod_treasure'] == 'dia_a_red'
    assert evidence['pod_weight'] == 15 and evidence['pod_capacity'] == 25
    assert evidence['died'] is True and evidence['corpse'] is True
    assert evidence['mamuta_receipt'][:2] == ('221001', '2')
    assert evidence['classify']['pod_ready'] == 'PASS'
    assert evidence['classify']['pod_receipt'] == 'PASS'
    assert evidence['classify']['natural_carry'] == 'PASS'
    assert evidence['assisted'] is False


def test_pod_validate_parses_native_prefixed_receipt():
    # Native emits the receipt through pc_p2_preview as "[Pikipelago] P2_POD_RECEIPT
    # id=corpse:mamuta:<gen> ..." (no cave prefix). The parser must not require a
    # line start, or a real natural run is misclassified UNPROVEN.
    from scripts.pikmin2_mamuta_pod_native import validate
    log = _pod_log().replace(
        'P2_POD_RECEIPT id=corpse:ujino:mamuta:221001 value=2 new=1 pokos=182 seeds=0',
        '[Pikipelago] P2_POD_RECEIPT id=corpse:mamuta:221001 value=2 new=1 pokos=2 seeds=0')
    evidence = validate(log)
    assert evidence['classify']['pod_receipt'] == 'PASS'
    assert evidence['mamuta_receipt'][:2] == ('221001', '2')


def test_pod_validate_labels_assisted_transport():
    from scripts.pikmin2_mamuta_pod_native import validate
    evidence = validate(_pod_log(assisted=True, pokos=182), assisted=True)
    assert evidence['assisted'] is True and evidence['assist_markers'] == 1
    assert evidence['classify']['assisted_carry'] == 'PASS'
    assert evidence['classify']['natural_carry'] == 'UNPROVEN'
    assert evidence['classify']['pod_receipt'] == 'PASS'


def test_pod_validate_classifies_missing_receipt_unproven():
    from scripts.pikmin2_mamuta_pod_native import validate
    evidence = validate(_pod_log(died=0, corpse=0, carried=0, goal=0, receipt=False, pokos=0))
    assert evidence['classify']['pod_receipt'] == 'UNPROVEN'
    assert evidence['classify']['natural_kill'] == 'UNPROVEN'
    assert evidence['classify']['natural_corpse'] == 'UNPROVEN'
    assert evidence['classify']['natural_carry'] == 'UNPROVEN'


def test_pod_validate_classifies_captain_down_block():
    from scripts.pikmin2_mamuta_pod_native import validate
    evidence = validate(_pod_log(died=0, corpse=0, carried=0, goal=0, receipt=False,
                                 pokos=0, captain_down=True))
    assert evidence['captain_down'] is True
    assert evidence['classify']['natural_kill'] == 'BLOCKED(captain_down)'
    assert evidence['classify']['pod_receipt'] == 'UNPROVEN'


def test_pod_validate_normal_kill_still_passes():
    from scripts.pikmin2_mamuta_pod_native import validate
    evidence = validate(_pod_log(died=1))
    assert evidence['captain_down'] is False
    assert evidence['classify']['natural_kill'] == 'PASS'


def test_pod_validate_no_marker_no_death_unproven():
    from scripts.pikmin2_mamuta_pod_native import validate
    evidence = validate(_pod_log(died=0, corpse=0, carried=0, goal=0, receipt=False, pokos=0))
    assert evidence['captain_down'] is False
    assert evidence['classify']['natural_kill'] == 'UNPROVEN'


def test_pod_validate_rejects_bad_completion_and_assisted_mismatch():
    from scripts.pikmin2_mamuta_pod_native import validate
    with pytest.raises(ValueError):
        validate(_pod_log(reset=False), assisted=False)
    with pytest.raises(ValueError):
        validate(_pod_log(desync=True), assisted=False)
    with pytest.raises(ValueError):
        validate(_pod_log(assisted=False), assisted=True)
    with pytest.raises(ValueError):
        validate(_pod_log(assisted=True), assisted=False)


def test_pod_validate_natural_kill_flip_to_pass():
    from scripts.pikmin2_mamuta_pod_native import validate
    evidence = validate(_pod_log(died=1, corpse=1))
    assert evidence['classify']['natural_kill'] == 'PASS'
    assert evidence['classify']['natural_corpse'] == 'PASS'


def test_pod_validate_natural_kill_flip_to_unproven():
    from scripts.pikmin2_mamuta_pod_native import validate
    evidence = validate(_pod_log(died=0, corpse=0, carried=0, goal=0, receipt=False, pokos=0))
    assert evidence['captain_down'] is False
    assert evidence['classify']['natural_kill'] == 'UNPROVEN'


def test_pod_validate_natural_kill_flip_to_blocked():
    from scripts.pikmin2_mamuta_pod_native import validate
    evidence = validate(_pod_log(died=0, corpse=0, carried=0, goal=0, receipt=False,
                                 pokos=0, captain_down=True))
    assert evidence['classify']['natural_kill'] == 'BLOCKED(captain_down)'


def test_pod_validate_delivery_flip_to_pass():
    from scripts.pikmin2_mamuta_pod_native import validate
    evidence = validate(_pod_log(carried=1, goal=1, receipt=True))
    assert evidence['classify']['natural_carry'] == 'PASS'
    assert evidence['classify']['pod_receipt'] == 'PASS'


def test_pod_validate_delivery_flip_goal_missing():
    from scripts.pikmin2_mamuta_pod_native import validate
    evidence = validate(_pod_log(carried=1, goal=0, receipt=False))
    assert evidence['classify']['natural_carry'] == 'UNPROVEN'
    assert evidence['classify']['pod_receipt'] == 'UNPROVEN'


def test_pod_validate_delivery_flip_not_carried():
    from scripts.pikmin2_mamuta_pod_native import validate
    evidence = validate(_pod_log(carried=0))
    assert evidence['classify']['natural_carry'] == 'UNPROVEN'


def test_instrument_selects_pod_and_assisted_fixtures(tmp_path):
    root = Path(__file__).resolve().parents[1]
    probe = ('class RoomApp : public PlugPikiApp {\n int idle() override { return 0; }\n};\n'
             'int main(int argc,char** argv) { return 0; }\n')
    natural = instrument(probe, root, POD_FIXTURE)
    assisted = instrument(probe, root, ASSISTED_FIXTURE)
    assert 'P2_MAMUTA_POD_BIRTH' in natural and 'P2_MAMUTA_POD_RESULT' in natural
    assert 'P2_MAMUTA_POD_ASSIST' not in natural
    assert 'P2_MAMUTA_POD_ASSIST' in assisted
    assert 'P2_MAMUTA_POD_MODE assisted=1' in assisted
    assert natural != assisted
    assert natural.rstrip().endswith('int main(int argc,char** argv) { return 0; }')
