"""Hana (EnemyID 84, Creeping Chrysanthemum) gameplay event mapping.

Maps the disc-audited Hana animation key events onto the authoritative
sampled-animation clock contract. Gameplay actions are the bite/swallow/flick
native events; every other clip/type is non-gameplay (None).
"""
from experimental.pikmin2_animation import sample_frames
from experimental.pikmin2_animation_clock import SampleClip
from experimental.pikmin2_ground_inverts_assets import EXPECTED_EVENTS

ACTIONS = {'attack1': {'2': 'bite', '3': 'swallow'}, 'flick': {'2': 'flick'}}

CLIP_DURATIONS = {
    'attack1': 80,
    'dead': 60,
    'flick': 55,
    'move1': 45,
    'type1': 130,
    'type5': 35,
    'wait2': 30,
    'waitact1': 45,
    'attack2': 70,
}

LOOPING_CLIPS = ('move1', 'wait2')

POSE_LIMIT = 6


def action(clip, key):
    """Gameplay action name for a (clip, key) pair, or None."""
    return ACTIONS.get(clip, {}).get(str(key))


def hana_clips():
    """Build the Hana SampleClip set from EXPECTED_EVENTS['Hana']."""
    clips = {}
    for name, events in EXPECTED_EVENTS['Hana'].items():
        duration = CLIP_DURATIONS[name]
        loop_end = duration if name in LOOPING_CLIPS else -1
        poses = tuple(sample_frames(duration, POSE_LIMIT)[:POSE_LIMIT])
        authored = tuple((frame, str(key)) for frame, key in events)
        clips[name] = SampleClip(name, duration, poses, authored, 0, loop_end).validate()
    return clips


def dispatch_actions(clip_name, events):
    """Ordered gameplay action names for a sequence of (frame, key) occurrences."""
    names = []
    for event in events:
        key = event.key if hasattr(event, 'key') else event[1]
        name = action(clip_name, key)
        if name is not None:
            names.append(name)
    return names
