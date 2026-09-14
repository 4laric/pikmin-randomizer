"""Lane 18 small-Breadbug proxy contested-cargo observation tests (#168/#220)."""
import pytest

from experimental import pikmin2_breadbug_contest_observation as observation

BIRTH = ('P2_BREADBUG_CARGO_BIRTH xyz=-150.000,35.000,1850.000 '
         'nest=-100.000,30.000,1700.000 distance=150.000 min=1')
TICK = ('P2_BREADBUG_CARGO_TICK tick=30 held=1 state=6 alive=1 '
        'distance=120.000 displacement=30.000 held_frames=30')
RESULT = ('P2_BREADBUG_CARGO_RESULT grabbed=1 held_frames=60 moved=50.000 '
          'progress=30.000 released=1 alive=0')
DRAW = 'P2_BREADBUG_ACTOR_DRAW generator=186081 visual_proxy no_P2_FSM'
ROW = '\n'.join((DRAW, BIRTH, TICK, RESULT))


def test_full_observation_reports_grab_drag_and_release():
    report = observation.observe(ROW)
    assert report['grab_observed'] is True
    assert report['drag_observed'] is True
    assert report['release_observed'] is True
    assert report['observed'] is True
    assert report['held_frames'] == 60
    assert report['displacement'] == 50.0
    assert report['nest_progress'] == 30.0
    assert report['pellet_alive'] is False
    assert report['tick_samples'] == 1


def test_native_offset_and_source_strength_are_reported_separately():
    report = observation.observe(ROW)
    # The P1 proxy drags the pellet at the host carry power of 2, while the P2
    # source contest strength for the same 1..2 red pellet is 1.5.
    assert report['native_offset_power'] == 2.0
    assert report['source_strength'] == 1.5
    assert report['pellet_bounds'] == {'min': 1, 'max': 2}
    # The two scales are not conflated and no P2 contest is claimed.
    assert report['native_offset_power'] != report['source_strength']
    assert report['p2_contest_semantics'] is False
    assert report['native_hook'] is False


def test_native_contest_marker_is_recorded_when_present():
    report = observation.observe(ROW + '\n' + observation.native_marker())
    assert report['native_hook'] is True
    assert report['native_offset_power'] == 2.0
    assert report['source_strength'] == 1.5
    assert report['p2_contest_semantics'] is False


def test_source_strength_uses_the_pellet_bounds():
    assert observation.source_strength() == 1.5
    assert observation.source_strength(10, 20) == 15.0
    with pytest.raises(ValueError, match='Invalid carry bounds'):
        observation.source_strength(2, 1)


def test_no_grab_or_release_is_not_a_completed_observation():
    idle = observation.observe('grabbed=0'.join(ROW.split('grabbed=1')))
    assert idle['grab_observed'] is False
    assert idle['drag_observed'] is False
    assert idle['release_observed'] is False
    assert idle['observed'] is False


def test_missing_or_duplicate_or_mismatched_result_is_rejected():
    with pytest.raises(ValueError, match='Expected one completed P1 cargo observation'):
        observation.observe(BIRTH)
    with pytest.raises(ValueError, match='Expected one completed P1 cargo observation'):
        observation.observe(ROW + '\n' + RESULT)
    with pytest.raises(ValueError, match='Missing native cargo birth marker'):
        observation.observe(RESULT)
    with pytest.raises(ValueError, match='Pellet min mismatch'):
        observation.observe(ROW.replace('min=1', 'min=2'))
