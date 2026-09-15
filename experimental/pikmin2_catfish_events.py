"""Catfish (EnemyID 26, Water Dumple) gameplay event mapping.

Maps the disc-audited Catfish animation key events onto the authoritative
sampled-animation clock contract. Gameplay actions are the bite/swallow native
events plus the flick knockback/restore pair; every other clip/type is
non-gameplay (None).
"""
from experimental.pikmin2_animation import sample_frames
from experimental.pikmin2_animation_clock import SampleClip
from experimental.pikmin2_aquatic_assets import EXPECTED_EVENTS

ACTIONS = {'attack': {'2': 'bite', '3': 'swallow'}, 'flick': {'2': 'flick', '3': 'restore'}}

# Representative durations for contract tests only; the native runtime table
# and the generated bank are authoritative.
CLIP_DURATIONS = {
    'attack': 90,
    'dead': 60,
    'flick': 55,
    'move1': 30,
    'type5': 35,
    'wait1': 30,
    'waitact2': 45,
}

LOOPING_CLIPS = ('move1', 'wait1')

POSE_LIMIT = 6


def action(clip, key):
    """Gameplay action name for a (clip, key) pair, or None."""
    return ACTIONS.get(clip, {}).get(str(key))


def catfish_clips():
    """Build the Catfish SampleClip set from EXPECTED_EVENTS['Catfish']."""
    clips = {}
    for name, events in EXPECTED_EVENTS['Catfish'].items():
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
