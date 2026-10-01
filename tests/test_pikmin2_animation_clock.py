"""Focused tests for the sampled-animation clock/event contract (#431, parent #128)."""
import math

import pytest

from experimental.pikmin2_animation_clock import (CLOCK_MAGIC, CONSUMERS, Batch, Clock,
                                                  SampleClip, bank_clips, manifest_clip,
                                                  parse_clock_bank, render_clock_bank)
from experimental.pikmin2_animation import sample_frames

POSE_FRAMES = (0, 10, 20, 29)
DURATION = 30


def clip(name='wait1', poses=POSE_FRAMES, events=(), duration=DURATION,
         loop_begin=0, loop_end=-1):
    return SampleClip(name, duration, tuple(poses), tuple(events), loop_begin, loop_end)


def native_nearest(frames, duration, source_frame):
    """Exact nearest in frame units; ties keep the lower index (native tie-break)."""
    source = min(max(float(source_frame), 0.0), float(duration - 1))
    best = 0
    for index in range(1, len(frames)):
        if abs(frames[index] - source) < abs(frames[best] - source):
            best = index
    return best


def collect(clock, deltas):
    seen = []
    for delta in deltas:
        batch = clock.advance(delta)
        if not batch:
            raise AssertionError('unexpected ' + str(batch.error))
        seen.extend(batch.events)
    return seen


def test_canonical_round_trip_is_byte_stable():
    original = clip(events=((2, 'hit'), (16, 'land')), loop_begin=10, loop_end=30)
    text = render_clock_bank([original])
    assert text.startswith((CLOCK_MAGIC + ' 1\n').encode('ascii'))
    parsed = parse_clock_bank(text.decode('ascii'))
    assert parsed == [original]
    assert render_clock_bank(parsed) == text


def test_manifest_clip_carries_sample_frames_and_events():
    record = {
        'name': 'move1', 'source_frames': 90,
        'poses': [{'frame': frame} for frame in sample_frames(90, 6)],
        'events': [(8, 2), {'frame': 88, 'type': 3}],
    }
    built = manifest_clip(record)
    assert built.poses == tuple(sample_frames(90, 6))
    assert built.events == ((8, '2'), (88, '3'))
    assert built.pose_index(8) == 0 and built.pose_index(88) == 5


def test_pose_index_matches_native_nearest_semantics():
    target = clip(events=((6, 'hit'),))
    for source in range(DURATION):
        assert target.pose_index(source) == native_nearest(POSE_FRAMES, DURATION, source)
    assert target.pose_index(-5) == 0
    assert target.pose_index(999) == 3


def test_invalid_source_frame_is_rejected():
    with pytest.raises(ValueError):
        clip().pose_index(float('nan'))


def test_pose_selection_is_independent_of_event_history():
    poses = (0, 10, 20, 29)
    quiet = clip(name='a', poses=poses, events=())
    busy = clip(name='b', poses=poses, events=((3, 'x'), (7, 'y'), (23, 'z')))
    quiet_clock, busy_clock = Clock(), Clock()
    quiet_clock.start(quiet)
    busy_clock.start(busy)
    for source in range(0, DURATION):
        quiet_clock.seek(source)
        busy_clock.seek(source)
        assert quiet_clock.pose_index() == busy_clock.pose_index() == quiet.pose_index(source)
    busy_clock.start(busy)
    crossed = collect(busy_clock, [1] * DURATION)
    assert [event.key for event in crossed] == ['x', 'y', 'z']
    assert [event.frame for event in crossed] == [3, 7, 23]


def test_advance_emits_crossed_events_once_in_source_order():
    target = clip(events=((0, 'start'), (5, 'mid'), (5, 'mid2'), (29, 'end')))
    clock = Clock()
    clock.start(target)
    seen = collect(clock, [1] * DURATION)
    assert [(event.frame, event.key) for event in seen] == [
        (0, 'start'), (5, 'mid'), (5, 'mid2'), (29, 'end')]
    assert clock.finished()
    assert collect(clock, [1, 1]) == []


def test_equivalent_split_and_combined_advances():
    target = clip(events=((4, 'a'), (18, 'b')))
    split, combined = Clock(), Clock()
    split.start(target)
    combined.start(target)
    split_events = collect(split, [1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    combined_events = collect(combined, [10])
    assert split_events == combined_events
    assert split.frame() == combined.frame() == 10


def test_loop_plays_intro_once_and_repeats_loop_region():
    target = clip(poses=POSE_FRAMES, events=((2, 'intro'), (12, 'loop')),
                  duration=DURATION, loop_begin=10, loop_end=30)
    clock = Clock()
    clock.start(target)
    seen = collect(clock, [1] * 50)
    assert [event.key for event in seen].count('intro') == 1
    assert [event.key for event in seen].count('loop') == 2
    assert clock.cycle() == 2
    assert 10 <= clock.frame() < 30


def test_zero_and_paused_advances_emit_nothing():
    clock = Clock()
    clock.start(clip(events=((0, 'start'),)))
    assert clock.advance(0) == Batch(generation=clock.generation(), events=())
    clock.pause(True)
    assert clock.advance(5).events == ()
    assert clock.frame() == 0.0
    clock.pause(False)
    assert [event.key for event in clock.advance(1).events] == ['start']
    assert [event.key for event in clock.advance(1).events] == []


def test_seek_invalidates_batches_and_rejects_bad_destinations():
    target = clip(events=((2, 'hit'),))
    clock = Clock()
    clock.start(target)
    first = clock.advance(3)
    assert [event.key for event in first.events] == ['hit']
    assert clock.current(first)
    assert clock.seek(1)
    assert not clock.current(first)
    stale = clock.advance(5)
    assert [event.frame for event in stale.events] == [2]
    assert not clock.current(first)
    assert not clock.seek(-1)
    assert not clock.seek(float('inf'))
    assert not clock.seek(target.duration + 1)


def test_looping_seek_rejects_loop_end():
    clock = Clock()
    clock.start(clip(loop_begin=10, loop_end=30))
    assert clock.seek(29)
    assert not clock.seek(30)


def test_budget_rejects_without_consuming_state():
    target = clip(poses=(0,), duration=1, events=((0, 'tick'),), loop_begin=0, loop_end=1)
    clock = Clock()
    clock.start(target)
    before = (clock.frame(), clock.cycle())
    batch = clock.advance(300)
    assert not batch and batch.error == 'budget'
    assert (clock.frame(), clock.cycle()) == before


@pytest.mark.parametrize('bad', [
    lambda: SampleClip('', 10, (0,)),
    lambda: SampleClip('wait1', 0, (0,)),
    lambda: SampleClip('wait1', 10, ()),
    lambda: SampleClip('wait1', 10, (0, 4, 4)),
    lambda: SampleClip('wait1', 10, (0, 20)),
    lambda: SampleClip('wait1', 10, (0, 4), ((5, 'a'), (3, 'b'))),
    lambda: SampleClip('wait1', 10, (0, 4), ((6, 'a'),), loop_begin=0, loop_end=6),
    lambda: SampleClip('wait1', 10, (0, 4), loop_begin=5, loop_end=5),
])
def test_invalid_clips_are_rejected(bad):
    with pytest.raises(ValueError):
        bad().validate()


def test_invalid_advance_is_rejected_and_state_preserved():
    clock = Clock()
    clock.start(clip())
    for delta in (-1, float('nan'), float('inf')):
        batch = clock.advance(delta)
        assert not batch and batch.error == 'invalid'
    assert clock.frame() == 0.0


def test_parse_rejects_malformed_clock_bank():
    good = render_clock_bank([clip(events=((2, 'hit'),))]).decode('ascii')
    for bad in ('', 'P2_ANIM_CLOCK_2 0', good + 'clip x', good.replace('event 2 hit', 'event -1 hit')):
        with pytest.raises((ValueError, IndexError)):
            parse_clock_bank(bad)


def test_bank_count_only_rows_are_uniform_and_events_preserved():
    text = ('P2_GROUND_BANK_1\n'
            'species Armor 15\n'
            'clip Armor move1 90 8:2,88:3 poses 6 converted\n')
    samples = bank_clips(text)['Armor']
    assert len(samples) == 1
    built = samples[0]
    assert built.duration == 90 and len(built.poses) == 6
    assert built.poses == tuple(sample_frames(90, 6))
    assert built.events == ((8, '2'), (88, '3'))


def test_consumer_mapping_names_every_adoptable_module():
    for name in ('pc_p2_batch2', 'pc_p2_batch3', 'pc_p2_hardlanes',
                 'pc_p2_long_legs', 'pc_p2_mamuta', 'pc_p2_breadbug_actor'):
        assert name in CONSUMERS
        assert CONSUMERS[name]['source'] and CONSUMERS[name]['adopts']
    assert 'not applicable' in CONSUMERS['pc_p2_long_legs']['adopts']
