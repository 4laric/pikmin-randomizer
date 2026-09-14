"""Lane 18 contested-cargo and release-model tests (#168/#220)."""
import math

import pytest

from experimental import pikmin2_breadbug_contest as contest


def test_carry_strength_matches_the_source_cargo_bounds():
    assert contest.carry_strength(1, 2) == 1.5
    assert contest.carry_strength(10, 20) == 15.0
    with pytest.raises(ValueError, match='Invalid carry bounds'):
        contest.carry_strength(2, 1)


def test_single_pellet_beats_one_carrier_and_loses_to_two():
    assert contest.carriers_win(1, 1, 2) is False
    assert contest.carriers_win(2, 1, 2) is True
    assert contest.carriers_win(0, 1, 2) is False


def test_small_targets_strictly_lighter_and_giant_targets_at_or_above():
    common = dict(already_stuck=False, pellet_carryable=True, treasure_slots=0)
    assert contest.targetable(min_weight=1, weight_limit=11, variant='small', **common) is True
    assert contest.targetable(min_weight=11, weight_limit=11, variant='small', **common) is False
    assert contest.targetable(min_weight=11, weight_limit=1, variant='giant', **common) is True
    assert contest.targetable(min_weight=20, weight_limit=1, variant='giant', **common) is True


def test_eligibility_rejects_stuck_carryable_and_full_slots():
    assert contest.targetable(already_stuck=True, pellet_carryable=True,
                              treasure_slots=0, min_weight=1, weight_limit=11) is False
    assert contest.targetable(already_stuck=False, pellet_carryable=False,
                              treasure_slots=0, min_weight=1, weight_limit=11) is False
    assert contest.targetable(already_stuck=False, pellet_carryable=True,
                              treasure_slots=contest.MAX_TREASURE_SLOTS,
                              min_weight=1, weight_limit=11) is False


def test_release_outcomes_per_source_reason():
    assert contest.release_plan(contest.EAT, held_slots=2)['keeps_slot0_in_nest'] is True
    assert contest.release_plan(contest.EAT, held_slots=0)['keeps_slot0_in_nest'] is False
    dropped = contest.release_plan(contest.DROP, held_slots=1)
    assert dropped['returns_cargo'] and not dropped['cargo_consumed']
    assert contest.release_plan(contest.RECOVER)['returns_cargo'] is True
    assert contest.release_plan(contest.DIGEST)['cargo_consumed'] is True
    with pytest.raises(ValueError, match='Unknown release reason'):
        contest.release_plan('explode')
    with pytest.raises(ValueError, match='exceeds the source slot cap'):
        contest.release_plan(contest.EAT, held_slots=contest.MAX_TREASURE_SLOTS + 1)


def test_throw_up_geometry_uses_ring_except_for_a_single_slot():
    assert contest.throw_up_positions(10, 20, 30, 1) == [(10, 30, 30)]
    spots = contest.throw_up_positions(0, 0, 0, 3)
    assert len(spots) == 3
    for index, (x, y, z) in enumerate(spots):
        angle = 2 * math.pi * index / 3
        assert math.isclose(x, contest.THROW_UP_RING_RADIUS * math.cos(angle))
        assert math.isclose(z, contest.THROW_UP_RING_RADIUS * math.sin(angle))
        assert y == contest.NEST_DROP_HEIGHT


def test_death_recovery_returns_every_held_slot_exactly_once():
    assert contest.reconcile_death(3, 3) == {'held': 3, 'returned': 3, 'lost': 0,
                                             'duplicated': False}
    assert contest.reconcile_death(3, 1)['lost'] == 2
    assert contest.reconcile_death(3, 4)['duplicated'] is True
    with pytest.raises(ValueError, match='Invalid held-slot count'):
        contest.reconcile_death(contest.MAX_TREASURE_SLOTS + 1, 0)
