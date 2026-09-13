from pathlib import Path

from experimental.pikmin2_receivers_runtime import readings, validate

_SAMPLE = (
    "P2_RECV_SQUAD alive=20 reds=20\n"
    "P2_RECV_ATTACK id=349001 accepted=1 health=130.0 stored=100000.0 "
    "state=6 motion=2 invincible=0 observed=200\n"
    "P2_RECV_ATTACK id=349001 accepted=1 health=0.0 stored=100000.0 "
    "state=10 motion=2 invincible=0 observed=201\n"
    "P2_RECV_IMMUNITY id=349006 pre_invincible=0 accepted=0 "
    "health_before=130.0 health_after=130.0\n"
    "P2_RECV_ELEMENT red_fire=0 blue_fire=1 blue_bubble=0 red_bubble=1\n"
    "PASS P2_RECEIVERS_RUNTIME\n")


def test_readings_parse():
    squad, attacks, immunity, element = readings(_SAMPLE)
    assert squad == [('20', '20')]
    assert attacks[0][:3] == ('349001', '1', '130.0')
    assert attacks[1][2] == '0.0'
    assert immunity == [('349006', '0', '0', '130.0', '130.0')]
    assert element == [('0', '1', '0', '1')]


def test_validate_passes_on_full_receiver_evidence():
    evidence = validate(_SAMPLE, 0)
    assert evidence['passed'] is True
    assert all(evidence['checks'].values())


def test_validate_flags_missing_damage_application():
    text = _SAMPLE.replace('health=0.0 stored=100000.0', 'health=130.0 stored=200000.0')
    evidence = validate(text, 0)
    assert evidence['checks']['attack_queued'] is True
    assert evidence['checks']['damage_applied'] is False
    assert evidence['passed'] is False


def test_validate_flags_broken_immunity_gate():
    text = _SAMPLE.replace('accepted=0 health_before=130.0 health_after=130.0',
                           'accepted=1 health_before=130.0 health_after=0.0')
    evidence = validate(text, 0)
    assert evidence['checks']['immunity_gate'] is False


def test_validate_flags_inverted_elemental_immunity():
    text = _SAMPLE.replace('red_fire=0 blue_fire=1 blue_bubble=0 red_bubble=1',
                           'red_fire=1 blue_fire=0 blue_bubble=1 red_bubble=0')
    evidence = validate(text, 0)
    assert evidence['checks']['elemental_immunity'] is False


def test_validate_requires_live_squad():
    text = _SAMPLE.replace('alive=20 reds=20', 'alive=0 reds=0')
    evidence = validate(text, 0)
    assert evidence['checks']['squad_live'] is False


def test_engine_queue_then_apply_anchors_present():
    """The explanation depends on interactDefault queueing and makeDamaged applying."""
    src = Path(__file__).resolve().parents[1] / 'engine/src/plugPikiNakata'
    queue = (src / 'tekibteki.cpp').read_text(errors='replace')
    apply = queue
    assert 'mStoredDamage += attack->mDamage' in queue
    assert 'mHealth -= mStoredDamage' in apply
    teki_h = (src.parents[1] / 'include/teki.h').read_text(errors='replace')
    assert 'damage waiting to be applied' in teki_h


def test_import_does_not_replace_other_fixture_instrumentation():
    import importlib
    from experimental import pikmin2_batch2_runtime as south
    from experimental import pikmin2_north_runtime as north
    from experimental import pikmin2_receivers_runtime as receiver
    original_south, original_north = south.instrument, north.instrument
    importlib.reload(receiver)
    assert south.instrument is original_south
    assert north.instrument is original_north
