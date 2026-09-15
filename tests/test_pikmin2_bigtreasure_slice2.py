"""Tests for the BigTreasure elemental-receiver runtime-log validator (#246 slice 2).

The validator parses the native lane's real-GL log markers and reports boolean
observations. These tests cover a fully satisfying synthetic log, empty/none
input, the absence of a weapon-count drop, and CRLF/whitespace tolerance.
"""
import experimental.pikmin2_bigtreasure_slice2_validate as validate
from experimental.pikmin2_bigtreasure_slice2_validate import validate_slice2

_BOOL_KEYS = (
    'attack_started',
    'emitted',
    'recv_observed',
    'nonimmune_accepted',
    'immunity_via_handled',
    'phase_advanced',
    'weapon_count_dropped',
)


def test_synthetic_log_reports_all_true():
    lines = [
        'P2_BIGTREASURE_ATTACK_START weapon=elec',
        'P2_BIGTREASURE_ATTACK_EMIT weapon=elec nodes=3',
        'P2_BIGTREASURE_RECV weapon=elec target=piki species=2 accepted=1',
        'P2_BIGTREASURE_RECV weapon=fire target=piki species=1 accepted=0',
        'P2_BIGTREASURE_FSM phase=Stay weapons=4 clip=0',
        'P2_BIGTREASURE_FSM phase=Attack weapons=4 clip=1',
        'P2_BIGTREASURE_FSM phase=DropItem weapons=2 clip=2',
        'some unrelated log line',
    ]
    result = validate_slice2('\n'.join(lines))
    for key in _BOOL_KEYS:
        assert result[key] is True, key
    assert len(result['recv_lines']) == 2


def test_empty_and_none_input_all_false():
    for text in ('', None):
        result = validate_slice2(text)
        for key in _BOOL_KEYS:
            assert result[key] is False, key
        assert result['recv_lines'] == []


def test_received_without_fsm_drop_reports_no_drop():
    text = (
        'P2_BIGTREASURE_RECV weapon=gas target=piki species=4 accepted=0\n'
        'P2_BIGTREASURE_FSM phase=Wait weapons=4 clip=0\n'
        'P2_BIGTREASURE_FSM phase=Flick weapons=4 clip=0\n'
    )
    result = validate_slice2(text)
    assert result['recv_observed'] is True
    assert result['phase_advanced'] is True
    assert result['weapon_count_dropped'] is False


def test_crlf_and_whitespace_tolerant():
    text = (
        'P2_BIGTREASURE_ATTACK_START   weapon=gas\r\n'
        '\tP2_BIGTREASURE_ATTACK_EMIT\tweapon=gas  nodes=2\r\n'
        'P2_BIGTREASURE_RECV weapon=gas target=piki species=4 accepted=1\r\n'
        'P2_BIGTREASURE_FSM phase=PreAttack weapons=3 clip=x\r\n'
        'P2_BIGTREASURE_FSM phase=Attack weapons=1 clip=y\r\n'
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
