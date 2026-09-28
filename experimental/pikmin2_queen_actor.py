"""#256 Empress Bulblax (Queen, enemy ID 30) sampled-actor config lane.

Generates and validates the `P2_QUEEN_ACTOR_1` native actor profile consumed
by pc_port/pc_p2_queen.cpp (native worktree branch kimi/p2-queen-actor).
Clip timing is sourced from the #227 machine-checkable behavior reference
(experimental/pikmin2_bulblax_behavior.py), which stays the shared source of
truth: this module raises if a requested clip duration disagrees with the
reference disc streams. Validation mirrors pc_p2_queen_policy.h exactly —
anything this module emits must parse there, and anything it rejects must
fail there too.
"""
import math

from experimental import pikmin2_bulblax_behavior as behavior

CONFIG = 'p2-queen-actor.txt'
MAGIC = 'P2_QUEEN_ACTOR_1'

QUEEN_CLIPS_REQUIRED = ('dead', 'sleep', 'wait1', 'damage', 'flick', 'rolling_l', 'rolling_r', 'born')
BABY_CLIPS_REQUIRED = ('born', 'move', 'dead')
VARIANTS = ('default', 'f_01', 'l_02')

_SPECIES_ID = {'Queen': 30, 'Baby': 31}
_REFERENCE_CLIPS = {'Queen': behavior.QUEEN_CLIPS, 'Baby': behavior.BABY_CLIPS}
# carry stays P1-authoritative; attack/attackfail/deadpress are outside the
# minimal Baby slice implemented by the native actor.
_NATIVE_QUEEN_CLIPS = frozenset(QUEEN_CLIPS_REQUIRED)
_NATIVE_BABY_CLIPS = frozenset(('dead', 'deadpress', 'move', 'born'))


def _check_name(name, allowed):
    if (type(name) is not str or not 1 <= len(name) <= 24
            or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in name)
            or name not in allowed):
        raise ValueError('Invalid clip name %r' % (name,))


def protocol(clips, placements):
    """Serialize a P2_QUEEN_ACTOR_1 profile; strict mirror of the native reader."""
    if not 1 <= len(clips) <= 16 or not 1 <= len(placements) <= 4:
        raise ValueError('Actor budget')
    lines = [MAGIC, str(len(clips))]
    seen = set()
    for c in clips:
        species = c['species']
        name = c['name']
        duration = c['duration']
        frames = c['frames']
        if species not in _SPECIES_ID or (species, name) in seen:
            raise ValueError('Invalid clip identity')
        _check_name(name, _NATIVE_QUEEN_CLIPS if species == 'Queen' else _NATIVE_BABY_CLIPS)
        # Consistency with the #227 reference: durations are the disc streams.
        reference = _REFERENCE_CLIPS[species].get(name)
        if reference is None or type(duration) is not int or duration != reference['frames']:
            raise ValueError('Clip %s/%s duration %r disagrees with the #227 reference'
                             % (species, name, duration))
        if (not isinstance(frames, list) or not 1 <= len(frames) <= 12
                or any(type(f) is not int or not 0 <= f < duration for f in frames)
                or frames != sorted(set(frames))):
            raise ValueError('Invalid clip timing')
        seen.add((species, name))
        lines.append('%d %s %d %d %s'
                     % (_SPECIES_ID[species], name, duration, len(frames), ' '.join(map(str, frames))))
    for need in QUEEN_CLIPS_REQUIRED:
        if ('Queen', need) not in seen:
            raise ValueError('Missing Queen clip %s' % need)
    lines.append(str(len(placements)))
    ids = set()
    for p in placements:
        i = p['placement_id']
        variant = p.get('variant', 'default')
        larvae = p.get('larvae', False)
        xyz = p['xyz']
        yaw = p.get('yaw', 0)
        if type(i) is not int or not 0 <= i <= 0xffffffff or i in ids:
            raise ValueError('Invalid placement identity')
        ids.add(i)
        if variant not in VARIANTS:
            raise ValueError('Unknown variant %r' % (variant,))
        if type(larvae) is not bool:
            raise ValueError('Invalid larvae flag')
        if variant == 'f_01' and larvae:
            raise ValueError('f_01 disables larvae (Queen.cpp:95-100)')
        if (not isinstance(xyz, (list, tuple)) or len(xyz) != 3
                or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 100000 for v in xyz)
                or type(yaw) not in (int, float) or not math.isfinite(yaw) or abs(yaw) > 360):
            raise ValueError('Invalid placement transform')
        if larvae and any(('Baby', need) not in seen for need in BABY_CLIPS_REQUIRED):
            raise ValueError('Larvae placements require the Baby clip set')
        lines.append('%d %s %d %s %s'
                     % (i, variant, int(larvae), ' '.join(format(v, '.9g') for v in xyz), format(yaw, '.9g')))
    return ('\n'.join(lines) + '\n').encode('ascii')


def full_clip_set(sampled_frames):
    """Clip dicts for every native Queen + Baby clip.

    `sampled_frames` maps (species, name) -> list of sampled source frames,
    typically taken from the #235 bank manifest so poses line up with the
    installed models. Durations come from the #227 reference.
    """
    clips = []
    for species, names in (('Queen', _NATIVE_QUEEN_CLIPS), ('Baby', _NATIVE_BABY_CLIPS)):
        for name in sorted(names):
            frames = sampled_frames.get((species, name))
            if frames is None:
                raise ValueError('Missing sampled frames for %s/%s' % (species, name))
            clips.append(dict(species=species, name=name,
                              duration=_REFERENCE_CLIPS[species][name]['frames'], frames=list(frames)))
    return clips
