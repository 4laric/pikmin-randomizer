"""Tests for the BigTreasure elemental-receiver runtime-log validator (#246 slice 2).

The validator parses the native lane's real-GL log markers and reports boolean
observations. These tests cover a fully satisfying synthetic log, empty/none
input, the absence of a weapon-count drop, a bare boot sequence, the
handled-set marker, and CRLF/whitespace tolerance.
"""
import experimental.pikmin2_bigtreasure_slice2_validate as validate
from experimental.pikmin2_bigtreasure_slice2_validate import validate_slice2

_BOOL_KEYS = (
    'attack_started',
    'emitted',
    'recv_observed',
    'nonimmune_accepted',
    'immune_rejected',
    'handled_set_held',
    'phase_advanced',
    'weapon_count_dropped',
    'ordinary_attack_started',
    'ordinary_attack_emitted',
    'natural_drop',
)


def test_synthetic_log_reports_all_true():
    lines = [
        'P2_BIGTREASURE_ATTACK_START weapon=elec',
        'P2_BIGTREASURE_ATTACK_EMIT weapon=elec nodes=3',
        'P2_BIGTREASURE_RECV weapon=elec target=piki species=2 accepted=1',
        'P2_BIGTREASURE_RECV weapon=fire target=piki species=1 accepted=0',
        'P2_BIGTREASURE_RECV_HELD weapon=elec target=piki species=2',
        'P2_BIGTREASURE_FSM phase=Stay weapons=4 clip=0',
        'P2_BIGTREASURE_FSM phase=Attack weapons=4 clip=1',
        'P2_BIGTREASURE_DROP_INGRESS weapons=4->3 injected=0',
        'P2_BIGTREASURE_FSM phase=DropItem weapons=2 clip=2',
        'P2_BIGTREASURE_FSM phase=PreAttack weapons=2 clip=3',
        'some unrelated log line',
    ]
    result = validate_slice2('\n'.join(lines))
    for key in _BOOL_KEYS:
        assert result[key] is True, key
    assert result['held_count'] == 1
    assert len(result['recv_lines']) == 2


def test_empty_and_none_input_all_false():
    for text in ('', None):
        result = validate_slice2(text)
        for key in _BOOL_KEYS:
            assert result[key] is False, key
        assert result['held_count'] == 0
        assert result['recv_lines'] == []


def test_received_without_fsm_drop_reports_no_drop():
    text = (
        'P2_BIGTREASURE_RECV weapon=gas target=piki species=4 accepted=0\n'
        'P2_BIGTREASURE_FSM phase=Wait weapons=4 clip=0\n'
        'P2_BIGTREASURE_FSM phase=Flick weapons=4 clip=0\n'
    )
    result = validate_slice2(text)
    assert result['recv_observed'] is True
    assert result['phase_advanced'] is False
    assert result['weapon_count_dropped'] is False


def test_natural_drop_false_when_injected():
    text = 'P2_BIGTREASURE_DROP_INGRESS weapons=4->3 injected=1\n'
    result = validate_slice2(text)
    assert result['natural_drop'] is False


def test_bare_boot_sequence_drops_weapon_without_advancing():
    text = (
        'P2_BIGTREASURE_FSM phase=Stay weapons=4 clip=0\n'
        'P2_BIGTREASURE_FSM phase=Land weapons=3 clip=0\n'
    )
    result = validate_slice2(text)
    assert result['weapon_count_dropped'] is True
    assert result['phase_advanced'] is False


def test_handled_set_held_when_recv_held_present():
    assert validate_slice2('P2_BIGTREASURE_RECV_HELD weapon=elec target=piki species=2\n')[
        'handled_set_held'] is True
    assert validate_slice2('P2_BIGTREASURE_RECV weapon=elec target=piki species=2 accepted=1\n')[
        'handled_set_held'] is False


def test_held_count_counts_each_held_line():
    text = '\n'.join([
        'P2_BIGTREASURE_RECV_HELD weapon=elec target=piki species=2',
        'P2_BIGTREASURE_RECV_HELD weapon=fire target=piki species=1',
        'P2_BIGTREASURE_RECV_HELD weapon=gas target=piki species=4',
    ])
    result = validate_slice2(text)
    assert result['held_count'] == 3
    assert result['handled_set_held'] is True


def test_crlf_and_whitespace_tolerant():
    text = (
        'P2_BIGTREASURE_ATTACK_START   weapon=gas\r\n'
        '\tP2_BIGTREASURE_ATTACK_EMIT\tweapon=gas  nodes=2\r\n'
        'P2_BIGTREASURE_RECV weapon=gas target=piki species=4 accepted=1\r\n'
        'P2_BIGTREASURE_FSM phase=PreAttack weapons=3 clip=x\r\n'
        'P2_BIGTREASURE_FSM phase=Attack weapons=1 clip=y\r\n'
        'P2_BIGTREASURE_FSM phase=DropItem weapons=1 clip=z\r\n'
    )
    result = validate_slice2(text)
    assert result['attack_started'] is True
    assert result['emitted'] is True
    assert result['nonimmune_accepted'] is True
    assert result['phase_advanced'] is True
    assert result['weapon_count_dropped'] is True
    assert result['recv_lines'] == [
        'P2_BIGTREASURE_RECV weapon=gas target=piki species=4 accepted=1',
    ]
