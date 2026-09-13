"""#289 Emperor Bulblax (KingChappy, enemy ID 53) sampled-actor config lane.

Generates and validates the `P2_KING_ACTOR_1` native actor profile consumed
by pc_port/pc_p2_king.cpp (native worktree branch kimi/p2-king-actor).
Clip timing is sourced from the #227 machine-checkable behavior reference
(experimental/pikmin2_bulblax_behavior.py), which stays the shared source of
truth: this module raises if a requested clip duration disagrees with the
reference disc streams. Validation mirrors pc_p2_king_policy.h exactly —
anything this module emits must parse there, and anything it rejects must
fail there too.
"""
import math

from experimental import pikmin2_bulblax_behavior as behavior

CONFIG = 'p2-king-actor.txt'
MAGIC = 'P2_KING_ACTOR_1'

KING_CLIPS_REQUIRED = ('attack', 'cry', 'damage', 'dead', 'dive', 'flick', 'move1',
                       'type1', 'type2', 'type3', 'wait2', 'waitact1', 'waitact2')
VARIANTS = ('default', 'f_03', 'force_big')

_SPECIES_ID = {'KingChappy': 53}
_REFERENCE_CLIPS = {'KingChappy': behavior.KING_CLIPS}
# carry stays P1-authoritative; the other 13 clips form the native FSM set.
_NATIVE_KING_CLIPS = frozenset(KING_CLIPS_REQUIRED)


def _check_name(name, allowed):
    if (type(name) is not str or not 1 <= len(name) <= 24
            or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in name)
            or name not in allowed):
        raise ValueError('Invalid clip name %r' % (name,))


def _check_xyz(xyz):
    if (not isinstance(xyz, (list, tuple)) or len(xyz) != 3
            or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 100000 for v in xyz)):
        raise ValueError('Invalid placement transform')


def protocol(clips, placements, bombs=()):
    """Serialize a P2_KING_ACTOR_1 profile; strict mirror of the native reader."""
    if not 1 <= len(clips) <= 16 or not 1 <= len(placements) <= 2 or len(bombs) > 4:
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
        _check_name(name, _NATIVE_KING_CLIPS)
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
    for need in KING_CLIPS_REQUIRED:
        if ('KingChappy', need) not in seen:
            raise ValueError('Missing KingChappy clip %s' % need)
    # Two-Emperor scope (the kingChappyMgr cross contract), 1..2 placements.
    lines.append(str(len(placements)))
    ids = set()
    for p in placements:
        i = p['placement_id']
        variant = p.get('variant', 'default')
        xyz = p['xyz']
        yaw = p.get('yaw', 0)
        if type(i) is not int or not 0 <= i <= 0xffffffff or i in ids:
            raise ValueError('Invalid placement identity')
        ids.add(i)
        if variant not in VARIANTS:
            raise ValueError('Unknown variant %r' % (variant,))
        _check_xyz(xyz)
        if type(yaw) not in (int, float) or not math.isfinite(yaw) or abs(yaw) > 360:
            raise ValueError('Invalid placement transform')
        lines.append('%d %s %s %s'
                     % (i, variant, ' '.join(format(v, '.9g') for v in xyz), format(yaw, '.9g')))
    # Actor-local BOMB_Wait bomb stubs (fixture injection channel; enemy ID 36).
    lines.append(str(len(bombs)))
    for b in bombs:
        i = b['bomb_id']
        xyz = b['xyz']
        blast_tick = b.get('external_blast_tick', 0)
        if type(i) is not int or not 0 <= i <= 0xffffffff or i in ids:
            raise ValueError('Invalid bomb identity')
        ids.add(i)
        _check_xyz(xyz)
        if type(blast_tick) is not int or not 0 <= blast_tick <= 1000000:
            raise ValueError('Invalid external blast tick')
        lines.append('%d %s %d' % (i, ' '.join(format(v, '.9g') for v in xyz), blast_tick))
    return ('\n'.join(lines) + '\n').encode('ascii')


def full_clip_set(sampled_frames):
    """Clip dicts for every native KingChappy clip.

    `sampled_frames` maps ('KingChappy', name) -> list of sampled source
    frames, typically taken from the #234 bank manifest so poses line up with
    the installed models. Durations come from the #227 reference.
    """
    clips = []
    for name in sorted(_NATIVE_KING_CLIPS):
        frames = sampled_frames.get(('KingChappy', name))
        if frames is None:
            raise ValueError('Missing sampled frames for KingChappy/%s' % name)
        clips.append(dict(species='KingChappy', name=name,
                          duration=_REFERENCE_CLIPS['KingChappy'][name]['frames'], frames=list(frames)))
    return clips
