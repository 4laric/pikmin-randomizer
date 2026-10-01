"""Parity tests for experimental/pikmin2_sarai_capture.

Mirrors native/pc_port/pc_p2_sarai_capture.h: the dependency-free mouth
capture / attachment receiver for Sarai (P2 Swooping Snitchbug, enemy ID 23).
"""
import pytest

from experimental.pikmin2_sarai_capture import (
    MOUTH_SLOTS,
    MOUTH_RADIUS,
    FLICK_KNOCKBACK,
    FLICK_DAMAGE,
    FALLMECK_DAMAGE,
    NO_SLOT,
    capture_eligible,
    select_mouth_captures,
    fall_meck_release_velocity,
    fall_meck_damage,
)


def candidate(**overrides):
    base = dict(alive=True, is_pikmin=True, stuck_to_mouth=False,
                sticker_is_self=False, within_mouth_radius=True)
    base.update(overrides)
    return base


def test_capture_eligible_accepts_default_candidate():
    assert capture_eligible({}) is True
    assert capture_eligible(candidate()) is True


@pytest.mark.parametrize('overrides', [
    dict(alive=False),
    dict(is_pikmin=False),
    dict(stuck_to_mouth=True),
    dict(sticker_is_self=True),
    dict(within_mouth_radius=False),
])
def test_capture_eligible_rejects(overrides):
    assert capture_eligible(candidate(**overrides)) is False


def test_select_mouth_captures_nearest_first():
    candidates = [candidate() for _ in range(4)]
    assert select_mouth_captures(candidates, [9, 4, 1, 25]) == [2, 1]


def test_select_mouth_captures_only_eligible():
    candidates = [candidate(alive=False), candidate(stuck_to_mouth=True), candidate()]
    assert select_mouth_captures(candidates, [0, 0, 0]) == [2]


def test_select_mouth_captures_skips_negative_and_nan():
    candidates = [candidate() for _ in range(4)]
    assert select_mouth_captures(candidates, [float('nan'), -5.0, 3.0, 0.0]) == [3, 2]


def test_select_mouth_captures_invalid_inputs():
    assert select_mouth_captures(None, None) == []
    assert select_mouth_captures([], []) == []
    many = [candidate() for _ in range(65)]
    assert select_mouth_captures(many, [0.0] * 65) == []


def test_fall_meck_release_velocity():
    assert fall_meck_release_velocity(200.0) == -200.0
    assert fall_meck_release_velocity(0.0) == 0.0
    assert fall_meck_release_velocity(-5.0) == -200.0


def test_fall_meck_damage():
    assert fall_meck_damage(10.0) == 10.0
    assert fall_meck_damage(-1.0) == 10.0
    assert fall_meck_damage() == 10.0


def test_constants():
    assert MOUTH_SLOTS == 2
    assert MOUTH_RADIUS == 15
    assert FLICK_KNOCKBACK == 10.0
    assert FLICK_DAMAGE == 0.0
    assert FALLMECK_DAMAGE == 10.0
    assert NO_SLOT == -1
