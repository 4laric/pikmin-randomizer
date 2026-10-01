"""Lane 19 (#221/#168) Mamuta revisit/re-entry validator tests."""
from pathlib import Path

import pytest

from experimental.pikmin2_mamuta_natural_runtime import instrument
from scripts.pikmin2_mamuta_revisit_native import REVISIT_FIXTURE


def _revisit_log(*, died=1, corpse=1, carried=1, goal=1, prior_pokos=2,
                 receipt='deduped', final_pokos=2, reset=True, desync=False,
                 captain_down=False):
    lines = [
        'P2_MAMUTA_RULES enabled cap=99 navi_damage=5.0 vertical_band=20',
        'P2_MAMUTA_READY generator=221001 native_type=24 xyz=-150.000000,30.000000,1850.000000 P1_proxy_static_anchors_no_P2_planting',
        f'[Pikipelago] P2_POD_READY treasure=dia_a_red value=180 weight=15 capacity=25 pokos={prior_pokos}',
        f'P2_MAMUTA_REVISIT_READY prior_pokos={prior_pokos}',
        'P2_MAMUTA_REVISIT_BIRTH id=221001 type=24 squad=14 color=red',
        'P2_MAMUTA_REVISIT_APPROACH target=-150.0,1870.0 actor=-150.0,1850.0',
        'P2_MAMUTA_REVISIT_OBSERVE tick=30 state=7 health=2424.8 navi=-150.0,1900.0 squad=10 min=55.0 states=00000080 pokos=2',
        'P2_MAMUTA_REVISIT_APPROACH_RESULT approached=1 min=12.0 states=00000d80',
    ]
    if captain_down:
        lines.append('P2_MAMUTA_REVISIT_CAPTAIN_DOWN tick=1234 health=0.0')
    if receipt == 'deduped':
        lines.append('[Pikipelago] P2_POD_RECEIPT id=corpse:mamuta:221001 value=2 new=0 pokos=2 seeds=0')
    elif receipt == 'duplicated':
        lines.append('[Pikipelago] P2_POD_RECEIPT id=corpse:mamuta:221001 value=2 new=1 pokos=4 seeds=0')
    lines.append(f'P2_MAMUTA_REVISIT_RESULT died={died} died_tick=2000 corpse={corpse} '
                 f'carried={carried} goal={goal} pokos={final_pokos} prior_pokos={prior_pokos} '
                 f'control_alive=1 squad=2')
    if reset:
        lines.append('P2_MAMUTA_REVISIT_RESET')
    if desync:
        lines.append('[PC GX] DESYNC something')
    if captain_down:
        lines.append('PASS P2_MAMUTA_REVISIT_RUNTIME captain_down')
    else:
        lines.append('PASS P2_MAMUTA_REVISIT_RUNTIME observe approach receipt_revisit reset')
    return '\n'.join(lines) + '\n'


def test_revisit_validate_accepts_deduped_receipt():
    from scripts.pikmin2_mamuta_revisit_native import validate
    evidence = validate(_revisit_log())
    assert evidence['prior_pokos'] == 2 and evidence['final_pokos'] == 2
    assert evidence['died'] is True and evidence['corpse'] is True and evidence['carried'] is True
    assert evidence['deduped_receipt'][:4] == ('221001', '2', '0', '2')
    assert evidence['classify']['reentry_ready'] == 'PASS'
    assert evidence['classify']['fresh_identity'] == 'PASS'
    assert evidence['classify']['natural_rekill'] == 'PASS'
    assert evidence['classify']['reward_not_duplicated'] == 'PASS'
    assert evidence['classify']['receipt_deduped'] == 'PASS'


def test_revisit_validate_rejects_duplicated_reward():
    from scripts.pikmin2_mamuta_revisit_native import validate
    with pytest.raises(ValueError):
        validate(_revisit_log(receipt='duplicated', final_pokos=4))


def test_revisit_validate_classifies_missing_rekill_unproven():
    from scripts.pikmin2_mamuta_revisit_native import validate
    evidence = validate(_revisit_log(died=0, corpse=0, carried=0, goal=0, receipt=None))
    assert evidence['classify']['natural_rekill'] == 'UNPROVEN'
    assert evidence['classify']['natural_recorpse'] == 'UNPROVEN'
    assert evidence['classify']['natural_recarry'] == 'UNPROVEN'
    # Re-entry and exactly-once still hold even when the proxy does not re-kill.
    assert evidence['classify']['reentry_ready'] == 'PASS'
    assert evidence['classify']['fresh_identity'] == 'PASS'
    assert evidence['classify']['reward_not_duplicated'] == 'PASS'


def test_revisit_validate_classifies_captain_down_block():
    from scripts.pikmin2_mamuta_revisit_native import validate
    evidence = validate(_revisit_log(died=0, corpse=0, carried=0, goal=0, receipt=None,
                                     captain_down=True))
    assert evidence['captain_down'] is True
    assert evidence['classify']['natural_rekill'] == 'BLOCKED(captain_down)'


def test_revisit_validate_rejects_low_prior_pokos():
    from scripts.pikmin2_mamuta_revisit_native import validate
    with pytest.raises(ValueError):
        validate(_revisit_log(prior_pokos=0, final_pokos=0, receipt=None))


def test_revisit_validate_rejects_bad_completion_and_desync():
    from scripts.pikmin2_mamuta_revisit_native import validate
    with pytest.raises(ValueError):
        validate(_revisit_log(reset=False))
    with pytest.raises(ValueError):
        validate(_revisit_log(desync=True))
    with pytest.raises(ValueError):
        validate(_revisit_log(final_pokos=3))


def test_revisit_validate_rekill_and_recarry_flip_to_pass():
    from scripts.pikmin2_mamuta_revisit_native import validate
    evidence = validate(_revisit_log(died=1, corpse=1, carried=1, goal=1, receipt='deduped',
                                     final_pokos=2))
    assert evidence['classify']['natural_rekill'] == 'PASS'
    assert evidence['classify']['natural_recorpse'] == 'PASS'
    assert evidence['classify']['natural_recarry'] == 'PASS'
    assert evidence['classify']['receipt_deduped'] == 'PASS'
    assert evidence['classify']['reward_not_duplicated'] == 'PASS'


def test_revisit_validate_rekill_flip_to_blocked():
    from scripts.pikmin2_mamuta_revisit_native import validate
    evidence = validate(_revisit_log(died=0, corpse=0, carried=0, goal=0, receipt=None,
                                     captain_down=True))
    assert evidence['classify']['natural_rekill'] == 'BLOCKED(captain_down)'


def test_instrument_selects_revisit_fixture():
    root = Path(__file__).resolve().parents[1]
    probe = ('class RoomApp : public PlugPikiApp {\n int idle() override { return 0; }\n};\n'
             'int main(int argc,char** argv) { return 0; }\n')
    compiled = instrument(probe, root, REVISIT_FIXTURE)
    assert 'P2_MAMUTA_REVISIT_READY' in compiled
    assert 'prior_pokos=%d' in compiled
    assert 'P2_MAMUTA_REVISIT_RESULT' in compiled
    assert 'receipt_revisit' in compiled
    assert compiled.rstrip().endswith('int main(int argc,char** argv) { return 0; }')
