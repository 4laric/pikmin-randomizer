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


def test_variant_params_match_the_audited_source_values():
    small = contest.variant_params('small')
    giant = contest.variant_params('giant')
    assert (small['health'], giant['health']) == (1100.0, 2000.0)
    assert (small['weight_threshold'], giant['weight_threshold']) == (11, 1)
    assert (small['carry_speed'], giant['carry_speed']) == (35.0, 45.0)
    assert (small['press_damage'], giant['press_damage']) == (200.0, 100.0)
    assert (small['nest_scale'], giant['nest_scale']) == (1.0, 2.0)
    assert giant['purple_only_press'] and not small['purple_only_press']
    # Both Breadbug species share the nest_house_type.
    assert small['nest_house_type'] == giant['nest_house_type'] == contest.NEST_BREADBUG
    # A copy is returned so callers cannot mutate the audited table.
    small['health'] = 0.0
    assert contest.variant_params('small')['health'] == 1100.0
    with pytest.raises(ValueError, match='Unknown breadbug variant'):
        contest.variant_params('medium')


def test_giant_press_is_purple_only():
    assert contest.press_damage('giant', purple=False) == 0.0
    assert contest.press_damage('giant', purple=True) == 100.0
    assert contest.press_damage('small', purple=False) == 200.0
    with pytest.raises(ValueError, match='purple must be a bool'):
        contest.press_damage('giant', purple=1)


def test_arbitration_same_channel_and_idle_accept_the_challenger():
    idle = contest.arbitrate(0.0, 1.5, claim_channel=None)
    assert idle['winner'] == 'challenger' and idle['reason'] == 'idle'
    assert idle['cross_channel'] is False and idle['stall_seconds'] == 0.0
    same = contest.arbitrate(9.0, 1.5, claim_channel=contest.CARRY_CHANNEL,
                             challenger_channel=contest.CARRY_CHANNEL)
    assert same['winner'] == 'challenger' and same['reason'] == 'same_channel'
    assert same['cross_channel'] is False and same['stall_seconds'] == 0.0


def test_arbitration_cross_channel_requires_strictly_greater():
    # Default channels model the Breadbug drag versus the Pikmin carry channel.
    defended = contest.arbitrate(15.0, 14.0)
    assert defended['winner'] == 'claim' and defended['reason'] == 'defended'
    assert defended['cross_channel'] is True and defended['stall_seconds'] == 0.0
    equal = contest.arbitrate(1.5, 1.5)
    assert equal['winner'] == 'claim'  # strictly greater is required
    takeover = contest.arbitrate(1.5, 2.0)
    assert takeover['winner'] == 'challenger' and takeover['reason'] == 'stronger'
    assert takeover['cross_channel'] is True
    assert takeover['stall_seconds'] == contest.TAKEOVER_STALL_SECONDS
    with pytest.raises(ValueError, match='Invalid contest strength'):
        contest.arbitrate(-1.0, 1.0)


def test_contest_frames_transition_from_drag_to_pulled():
    # A 1/2 pellet gives the Breadbug 1.5: one carrier is not enough, two win.
    frames = contest.contest_frames(1.5, [1, 1, 2, 2, 1])
    assert frames == (contest.DRAG, contest.DRAG, contest.PULLED,
                      contest.PULLED, contest.DRAG)
    assert contest.contest_frames(15.0, [14, 15, 16]) == (
        contest.DRAG, contest.DRAG, contest.PULLED)
    with pytest.raises(ValueError, match='Invalid contest strength'):
        contest.contest_frames(1.5, [1, float('nan')])


def test_nest_ownership_is_parent_bound_breadbug_by_default():
    owned = contest.nest_ownership(True, contest.NEST_BREADBUG)
    assert owned == {'owner_alive': True, 'house_type': contest.NEST_BREADBUG,
                     'owner': 'breadbug', 'parent_bound': True, 'active': True}
    dead = contest.nest_ownership(False, contest.NEST_BREADBUG)
    assert dead['active'] is False and dead['parent_bound'] is True
    assert contest.nest_ownership(True, contest.NEST_JIGUMO)['owner'] == 'jigumo'
    with pytest.raises(ValueError, match='owner_alive must be a bool'):
        contest.nest_ownership(1, contest.NEST_BREADBUG)
    with pytest.raises(ValueError, match='Unknown nest house type'):
        contest.nest_ownership(True, 2)


def test_nest_collision_drops_after_eighty_frames():
    assert contest.nest_collision_after_death(0) is True
    assert contest.nest_collision_after_death(79) is True
    assert contest.nest_collision_after_death(80) is False
    assert contest.nest_collision_after_death(1000) is False
    with pytest.raises(ValueError, match='Invalid frames-since-kill'):
        contest.nest_collision_after_death(-1)


def test_coexistence_accepts_disjoint_giant_small_and_nest_roles():
    # Giant 187001 + nest 187002 + one small proxy 186081: every role disjoint.
    assert contest.coexistence_ok([187001], [186081], [187002]) is True
    report = contest.coexistence_report([187001], [186081], [187002])
    assert report['ok'] is True
    assert report['violations'] == []
    assert report['giant_count'] == report['small_count'] == report['nest_count'] == 1
    assert report['pairs'] == [{'giant': 187001, 'nest': 187002}]
    assert report['small_actors_independent'] is True
    # No small actor is also a valid (vacuously independent) arrangement.
    assert contest.coexistence_ok([187001], [], [187002]) is True
    assert contest.coexistence_report([187001], [], [187002])[
        'small_actors_independent'] is True


def test_coexistence_rejects_shared_generator_ids_across_roles():
    # A small actor reused as its own nest is not independent.
    report = contest.coexistence_report([187001], [186081], [186081])
    assert report['ok'] is False
    assert report['small_actors_independent'] is False
    assert any('small and nest share generator ids: 186081' in v
               for v in report['violations'])
    # A giant id claimed as a nest is likewise rejected.
    assert contest.coexistence_ok([187001], [], [187001]) is False
    # A small actor reusing the giant id is rejected.
    assert contest.coexistence_ok([187001], [187001], [187002]) is False


def test_coexistence_requires_one_nest_per_giant_and_a_giant():
    assert contest.coexistence_ok([], [186081], []) is False
    assert contest.coexistence_ok([187001, 187003], [186081], [187002]) is False
    report = contest.coexistence_report([187001, 187003], [186081],
                                        [187002, 187004])
    assert report['ok'] is True
    assert [p['giant'] for p in report['pairs']] == [187001, 187003]


def test_coexistence_rejects_duplicates_and_malformed_ids():
    with pytest.raises(ValueError, match='Duplicate generator id within the small role'):
        contest.coexistence_ok([187001], [186081, 186081], [187002])
    with pytest.raises(ValueError, match='must be an int'):
        contest.coexistence_ok([187001], ['186081'], [187002])
    with pytest.raises(ValueError, match='out of range'):
        contest.coexistence_ok([187001], [contest.MAX_GENERATOR_ID + 1], [187002])
    with pytest.raises(ValueError, match='must be a list or tuple'):
        contest.coexistence_ok([187001], 186081, [187002])
