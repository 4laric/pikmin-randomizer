"""Focused tests for the Hana (EnemyID 84) gameplay event mapping."""

import pytest

from experimental.pikmin2_animation_clock import Clock, parse_clock_bank, render_clock_bank
from experimental.pikmin2_ground_inverts_assets import EXPECTED_EVENTS
from experimental.pikmin2_hana_events import ACTIONS, action, dispatch_actions, hana_clips

GAMEPLAY = {
    ('attack1', '2'): 'bite',
    ('attack1', '3'): 'swallow',
    ('flick', '2'): 'flick',
}

NON_GAMEPLAY_CLIPS = ('move1', 'type1', 'waitact1', 'attack2', 'type5', 'dead', 'wait2')


def test_authored_table_maps_to_expected_actions():
    table = EXPECTED_EVENTS['Hana']
    assert table['attack1'] == [[18, 2], [71, 3]]
    assert table['flick'] == [[50, 2]]
    for clip_name, events in table.items():
        for frame, key in events:
            key = str(key)
            assert action(clip_name, key) == GAMEPLAY.get((clip_name, key))
    assert action('attack1', '2') == 'bite'
    assert action('attack1', '3') == 'swallow'
    assert action('flick', '2') == 'flick'


def test_all_non_gameplay_clips_map_to_none():
    for clip_name in NON_GAMEPLAY_CLIPS:
        for frame, key in EXPECTED_EVENTS['Hana'][clip_name]:
            assert action(clip_name, str(key)) is None
    assert set(ACTIONS) == {'attack1', 'flick'}


def test_clock_bank_round_trip_reproduces_clips():
    clips = list(hana_clips().values())
    assert len(clips) == 9
    text = render_clock_bank(clips)
    parsed = parse_clock_bank(text.decode('ascii'))
    assert parsed == clips
    assert render_clock_bank(parsed) == text


def test_frame_skip_emits_exactly_once_in_order():
    clock = Clock()
    clock.start(hana_clips()['attack1'])
    batch = clock.advance(200)
    assert [(event.frame, event.key) for event in batch.events] == [(18, '2'), (71, '3')]
    assert dispatch_actions('attack1', batch.events) == ['bite', 'swallow']
    assert clock.advance(10).events == ()


def test_pause_emits_nothing_and_frame_stays_put():
    clock = Clock()
    clock.start(hana_clips()['attack1'])
    clock.pause(True)
    assert clock.advance(200).events == ()
    assert clock.frame() == 0.0
    clock.pause(False)
    assert dispatch_actions('attack1', clock.advance(20).events) == ['bite']


def test_interruption_discards_pending_bite_and_fires_flick_once():
    clock = Clock()
    clock.start(hana_clips()['attack1'])
    assert clock.advance(10).events == ()
    clock.start(hana_clips()['flick'])
    batch = clock.advance(60)
    assert [(event.frame, event.key) for event in batch.events] == [(50, '2')]
    assert dispatch_actions('flick', batch.events) == ['flick']
