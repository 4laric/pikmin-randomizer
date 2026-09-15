"""Tests for the Pikmin 2 Frog/MaroFrog FSM state-machine validator."""

import pytest

from experimental import pikmin2_frog_fsm as m


SAMPLE_LOG = (
    "P2_FROG_READY species=Frog generator=201001\n"
    "P2_FROG_STATE species=Frog generator=201001 state=jump\n"
    "P2_FROG_LAND species=Frog generator=201001\n"
    "P2_FROG_STATE species=MaroFrog generator=999 state=wait\n"
    "some unrelated debug noise\n"
)

LEGAL_COMBAT_TRACE = (
    "P2_FROG_STATE species=Frog generator=1 state=wait\n"
    "P2_FROG_STATE species=Frog generator=1 state=turn\n"
    "P2_FROG_STATE species=Frog generator=1 state=jump\n"
    "P2_FROG_STATE species=Frog generator=1 state=jumpwait\n"
    "P2_FROG_STATE species=Frog generator=1 state=fall\n"
    "P2_FROG_STATE species=Frog generator=1 state=attack\n"
    "P2_FROG_STATE species=Frog generator=1 state=wait\n"
)


def test_parse_states_extracts_in_order_and_ignores_other_lines():
    rows = m.parse_states(SAMPLE_LOG)
    assert rows == [
        {'species': 'Frog', 'generator': 201001, 'state': 'jump'},
        {'species': 'MaroFrog', 'generator': 999, 'state': 'wait'},
    ]


def test_parse_states_raises_on_unknown_state():
    with pytest.raises(ValueError):
        m.parse_states("P2_FROG_STATE species=Frog generator=1 state=flying\n")


def test_validate_accepts_legal_single_actor_trace():
    result = m.validate(m.parse_states(LEGAL_COMBAT_TRACE))
    assert result['passed'] is True
    assert result['checks']['legal_states'] is True
    assert result['checks']['starts_wait'] is True
    assert result['checks']['adjacency'] is True
    assert result['checks']['dead_terminal'] is True
    assert result['errors'] == []


def test_validate_require_combat_passes_on_combat_trace():
    result = m.validate(m.parse_states(LEGAL_COMBAT_TRACE), require_combat=True)
    assert result['passed'] is True
    assert result['checks']['combat'] is True


def test_validate_require_variants_fails_when_species_missing():
    result = m.validate(
        m.parse_states(LEGAL_COMBAT_TRACE),
        require_variants=('Frog', 'MaroFrog'),
    )
    assert result['passed'] is False
    assert result['checks']['variants'] is False


def test_validate_rejects_illegal_adjacency():
    trace = (
        "P2_FROG_STATE species=Frog generator=1 state=wait\n"
        "P2_FROG_STATE species=Frog generator=1 state=gohome\n"
    )
    result = m.validate(m.parse_states(trace))
    assert result['passed'] is False
    assert result['checks']['adjacency'] is False


def test_validate_rejects_non_wait_start():
    result = m.validate(
        m.parse_states("P2_FROG_STATE species=Frog generator=1 state=jump\n")
    )
    assert result['passed'] is False
    assert result['checks']['starts_wait'] is False


def test_validate_rejects_dead_then_later_state():
    trace = (
        "P2_FROG_STATE species=Frog generator=1 state=wait\n"
        "P2_FROG_STATE species=Frog generator=1 state=dead\n"
        "P2_FROG_STATE species=Frog generator=1 state=wait\n"
    )
    result = m.validate(m.parse_states(trace))
    assert result['passed'] is False
    assert result['checks']['dead_terminal'] is False


def test_validate_require_combat_rejects_trace_without_combat():
    trace = (
        "P2_FROG_STATE species=Frog generator=1 state=wait\n"
        "P2_FROG_STATE species=Frog generator=1 state=turn\n"
    )
    result = m.validate(m.parse_states(trace), require_combat=True)
    assert result['passed'] is False
    assert result['checks']['combat'] is False
