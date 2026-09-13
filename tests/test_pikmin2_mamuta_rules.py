"""Mamuta batch-4 (#221) rules tests: profile staging, squad record, log markers."""
import json
import struct
from pathlib import Path

import pytest

from experimental.pikmin2_mamuta_rules import (
    P2_REFERENCE, RULES_NAME, RULES_TOKEN, SQUAD_COLOR, SQUAD_COUNT,
    SQUAD_FORMATION, SQUAD_GENERATOR, SQUAD_NAME, SQUAD_POSITION,
    parse_plant_events, rules_profile, stage_rules,
    squad_record, validate_plant_events, validate_rules_profile, validate_squad)

ASSETS = Path('C:/Users/alari/bbft/dist/cohesion/pikmin/assets')
IMPORTED = Path('C:/Users/alari/pikmin-randomizer/output/mamuta-second/imported')


def test_rules_profile_exact_token():
    assert rules_profile() == 'P2_MAMUTA_RULES_1\n'


def test_p2_reference_constants_match_audit():
    assert P2_REFERENCE == dict(piki_damage=0.0, navi_damage=5.0, planted_cap_us=99,
                                vertical_band=20.0, kill_flag='CKILL_DontCountAsDeath')


def test_stage_rules_writes_marker_and_refuses_overwrite(tmp_path):
    result = stage_rules(tmp_path)
    assert result['token'] == RULES_TOKEN
    assert (tmp_path / RULES_NAME).read_text() == rules_profile()
    assert validate_rules_profile(tmp_path)
    with pytest.raises(ValueError):
        stage_rules(tmp_path)


def test_validate_rules_profile_rejects_malformed(tmp_path):
    for bad in ('', 'P2_MAMUTA_RULES_2\n', 'P2_MAMUTA_RULES_1 extra\n'):
        (tmp_path / RULES_NAME).write_text(bad)
        with pytest.raises(ValueError):
            validate_rules_profile(tmp_path)


def test_squad_generator_id_reserved_and_distinct():
    assert SQUAD_GENERATOR == 221003
    assert SQUAD_GENERATOR not in (221001, 221002)


def test_local_squad_record_roundtrip():
    if not ASSETS.exists():
        pytest.skip('Requires local user-owned assets')
    record = squad_record(ASSETS)
    placement = validate_squad(record)
    assert placement['generator'] == SQUAD_GENERATOR
    assert placement['count'] == SQUAD_COUNT == 10
    assert placement['color'] == 'red' and SQUAD_COLOR == 1
    assert placement['formation'] == SQUAD_FORMATION == 2
    assert placement['position'] == list(SQUAD_POSITION)
    assert struct.unpack_from('<I', record, 8)[0] == SQUAD_GENERATOR
    assert record[16:48].rstrip(b'\0').decode('ascii') == SQUAD_NAME


def test_local_prepare_stages_rules_and_squad(tmp_path):
    if not (ASSETS.exists() and IMPORTED.exists()):
        pytest.skip('Requires local user-owned assets and batch-1 import')
    from experimental.pikmin2_mamuta_rules import prepare
    run = prepare(ASSETS, IMPORTED, tmp_path)
    assert validate_rules_profile(run)
    info = json.loads((run / 'arena.json').read_text())
    assert info['rules']['token'] == RULES_TOKEN
    assert info['squad']['generator'] == SQUAD_GENERATOR
    assert info['gates']['starting_squad'].startswith('staged (explicit 10-red')
    ids = [a['generator'] for a in info['actors']]
    assert len(ids) == len(set(ids)) == 3
    gen = (run / 'assets/dataDir/stages/chal0/default.gen').read_bytes()
    from scripts.preview_pikmin2_room import records
    practice_count = len(records(ASSETS / 'dataDir/stages/practice/default.gen'))
    # The explicit lane squad suppresses the mandatory 20-red overlay squad.
    assert struct.unpack_from('>I', gen, 20)[0] == practice_count + 3


def test_parse_plant_events_full_session():
    log = ('P2_MAMUTA_RULES enabled cap=99 navi_damage=5.0 vertical_band=20\n'
           'P2_MAMUTA_PLANT kind=1 happa=2 planted=57\n'
           'P2_MAMUTA_NAVI damage=5.0 health=45.000\n'
           'P2_MAMUTA_PLANT_REJECT reason=cap99\n')
    events = parse_plant_events(log)
    assert events['enabled'] == 1
    assert events['plants'] == [{'kind': 1, 'happa': 2, 'planted': 57}]
    assert events['navi'] == [{'damage': 5.0, 'health': 45.0}]
    assert events['rejects'] == ['cap99']
    assert validate_plant_events(events)


def test_validate_plant_events_rejects_bad_semantics():
    base = {'enabled': 1, 'plants': [{'kind': 1, 'happa': 2, 'planted': 1}],
            'rejects': [], 'navi': []}
    with pytest.raises(ValueError):
        validate_plant_events(dict(base, enabled=0))
    with pytest.raises(ValueError):
        validate_plant_events(dict(base, plants=[]))
    with pytest.raises(ValueError):
        validate_plant_events(dict(base, plants=[{'kind': 1, 'happa': 1, 'planted': 1}]))
    with pytest.raises(ValueError):
        validate_plant_events(dict(base, navi=[{'damage': 20.0, 'health': 30.0}]))
    with pytest.raises(ValueError):
        validate_plant_events(dict(base, rejects=['terrain']))


def _death_log(*, corpse=1, withview=1, corpse_type=1):
    lines = [
        'P2_MAMUTA_RULES enabled cap=99 navi_damage=5.0 vertical_band=20',
        'P2_MAMUTA_FIXTURE_BIRTH id=221001 type=24 squad=10 color=red',
        'P2_MAMUTA_CARCASS_CONFIG tkmu=1',
        'P2_MAMUTA_PLANT kind=1 happa=2 planted=0',
        'P2_MAMUTA_PLANT kind=1 happa=2 planted=0',
        'P2_MAMUTA_PLANT kind=1 happa=2 planted=0',
        'P2_MAMUTA_FIXTURE_BURY forced=3 planted_before=0',
        'P2_MAMUTA_NAVI damage=5.0 health=95.000',
        'P2_MAMUTA_FIXTURE_NAVI damage=5.0 health=95.000',
        'P2_MAMUTA_PLANT_REJECT reason=cap99',
        'P2_MAMUTA_FIXTURE_CAP rejected_at=99',
        'P2_MAMUTA_FIXTURE_PLANTED planted=3 expected_min=3',
        f'P2_MAMUTA_DEATH_CORPSETYPE corpse_type={corpse_type}',
        'P2_MAMUTA_DEATH_HIT accepted=1 invincible=0 health_before=2259.8 stored=100000.0',
        'P2_MAMUTA_DEATH_DIED tick=151 health=0.0',
        f'P2_MAMUTA_DEATH_PELLETS total=2 withview={withview}',
        f'P2_MAMUTA_DEATH_RESULT died_tick=151 corpse={corpse}',
        'P2_MAMUTA_FIXTURE_RESET',
        'PASS P2_MAMUTA_RULES_RUNTIME bury flower_stage cap99 navi_damage5 death corpse reset',
    ]
    return '\n'.join(lines) + '\n'


def test_native_death_corpse_gate_accepts_observed_carcass():
    from scripts.pikmin2_mamuta_rules_native import validate
    evidence = validate(_death_log())
    assert evidence['death_tick'] == 151
    assert evidence['corpse'] is True
    assert evidence['corpse_pellets_total'] == 2


def test_native_death_gate_requires_corpse_and_corpse_type():
    from scripts.pikmin2_mamuta_rules_native import validate
    with pytest.raises(ValueError):
        validate(_death_log(corpse=0, withview=0))
    with pytest.raises(ValueError):
        validate(_death_log(corpse_type=0))
