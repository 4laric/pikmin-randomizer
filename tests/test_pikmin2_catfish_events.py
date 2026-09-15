"""Focused tests for the Catfish (EnemyID 26) gameplay event mapping."""

from experimental.pikmin2_animation_clock import Clock, parse_clock_bank, render_clock_bank
from experimental.pikmin2_aquatic_assets import EXPECTED_EVENTS
from experimental.pikmin2_catfish_events import ACTIONS, action, dispatch_actions, catfish_clips

NON_GAMEPLAY_CLIPS = ('move1', 'type5', 'wait1', 'waitact2', 'dead')


def test_authored_table_maps_to_expected_actions():
    table = EXPECTED_EVENTS['Catfish']
    assert table['attack'] == [[17, 2], [75, 3]]
    assert table['flick'] == [[25, 2], [47, 3]]
    assert action('attack', '2') == 'bite'
    assert action('attack', '3') == 'swallow'
    assert action('flick', '2') == 'flick'
    assert action('flick', '3') == 'restore'


def test_non_gameplay_clips_map_to_none():
    for clip_name in NON_GAMEPLAY_CLIPS:
        for frame, key in EXPECTED_EVENTS['Catfish'][clip_name]:
            assert action(clip_name, str(key)) is None


def test_actions_limited_to_gameplay_clips():
    assert set(ACTIONS) == {'attack', 'flick'}


def test_clock_bank_round_trip_reproduces_clips():
    clips = list(catfish_clips().values())
    assert len(clips) == 7
    text = render_clock_bank(clips)
    parsed = parse_clock_bank(text.decode('ascii'))
    assert parsed == clips
    assert render_clock_bank(parsed) == text


def test_frame_skip_emits_exactly_once_in_order():
    clock = Clock()
    clock.start(catfish_clips()['attack'])
    batch = clock.advance(200)
    assert [(event.frame, event.key) for event in batch.events] == [(17, '2'), (75, '3')]
    assert dispatch_actions('attack', batch.events) == ['bite', 'swallow']
    assert dispatch_actions('attack', [(17, '2'), (75, '3')]) == ['bite', 'swallow']
    assert clock.advance(10).events == ()


def test_pause_emits_nothing_and_frame_stays_put():
    clock = Clock()
    clock.start(catfish_clips()['attack'])
    clock.pause(True)
    assert clock.advance(200).events == ()
    assert clock.frame() == 0.0
    clock.pause(False)
    assert dispatch_actions('attack', clock.advance(20).events) == ['bite']


def test_interruption_discards_pending_swallow_and_fires_flick():
    clock = Clock()
    clock.start(catfish_clips()['attack'])
    assert [(event.frame, event.key) for event in clock.advance(20).events] == [(17, '2')]
    clock.start(catfish_clips()['flick'])
    batch = clock.advance(60)
    assert [(event.frame, event.key) for event in batch.events] == [(25, '2'), (47, '3')]
    assert dispatch_actions('flick', batch.events) == ['flick', 'restore']
    clock.start(catfish_clips()['attack'])
    batch = clock.advance(200)
    assert [(event.frame, event.key) for event in batch.events] == [(17, '2'), (75, '3')]
    assert dispatch_actions('attack', batch.events) == ['bite', 'swallow']
