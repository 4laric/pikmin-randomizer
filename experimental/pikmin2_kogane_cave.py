"""Lane 17 cave treasure override and relocation for the reward beetles (#168/#219).

Host-side model of the source cave behavior around the audited drop tables in
``experimental.pikmin2_kogane_assets``:

- ``createTreasureItem`` (Kogane.cpp:386-414) runs before every table entry. On
  the first flip a cave beetle carrying a treasure (``mPelletDropCode``) drops
  that treasure, forces the escape timer and skips the normal table.
- The third flip forces the escape (``mAppearTimer = 12800``, KoganeState.cpp:
  260-265), after which the beetle burrows away instead of dropping again.
- An unflipped cave beetle (``mHitCount == 0``) that reaches Disappear
  re-registers through ``Cave::randMapMgr`` and resurfaces (Kogane.cpp:250-262)
  instead of dying; :func:`relocation_outcome` classifies that relocation
  against the final death.

This module never duplicates the drop table: every table resolution goes through
``drop_for``. See ``docs/PIKMIN2_KOGANE_REWARDS.md``.
"""
from experimental.pikmin2_kogane_assets import DROP_TABLES, MAX_FLIPS, drop_for

UNFLIPPED = 0
RELOCATION = 'relocate'
DEATH = 'death'


def _species(species):
    if species not in DROP_TABLES:
        raise ValueError('Unknown beetle species: ' + repr(species))
    return species


def _flag(name, value):
    if type(value) is not bool:
        raise ValueError('Invalid %s flag: %r' % (name, value))
    return value


def treasure_override(species, flip, carried_treasure):
    """Return the carried cave treasure instead of the table on the first flip.

    ``flip`` is the 1-based source flip count. Returns ``None`` for any later
    flip or when the beetle carries no treasure (``carried_treasure is None``).
    """
    _species(species)
    if type(flip) is not int or not 1 <= flip <= MAX_FLIPS:
        raise ValueError('Flip out of range: ' + repr(flip))
    if flip == 1 and carried_treasure is not None:
        return carried_treasure
    return None


def relocates(flip_count, in_cave):
    """True for an unflipped cave beetle that reaches Disappear.

    ``flip_count`` is the source ``mHitCount``: only ``0`` (never flipped) and a
    cave spawn relocate via ``Cave::randMapMgr``; a flipped beetle just burrows.
    """
    if type(flip_count) is not int or flip_count < 0:
        raise ValueError('Invalid flip count: ' + repr(flip_count))
    _flag('cave', in_cave)
    return in_cave and flip_count == UNFLIPPED


def relocation_outcome(flip_count, in_cave):
    """Classify a beetle reaching Disappear as a relocation or a final death.

    Only an unflipped cave beetle relocates (``Cave::randMapMgr`` re-register,
    Kogane.cpp:250-262); every other beetle burrows away for good. Returns a
    structured ``{'flip': flip_count, 'relocate': bool, 'outcome':
    'relocate'|'death'}`` so callers do not re-derive the rule.
    """
    relocate = relocates(flip_count, in_cave)
    return {'flip': flip_count, 'relocate': relocate,
            'outcome': RELOCATION if relocate else DEATH}


def resolve_flip(species, flip, in_cave=False, demo_flag=False, carried_treasure=None):
    """Resolve one source flip into a structured outcome.

    ``flip`` is the source hit count after the event: ``0`` is the unflipped
    Disappear path (the relocation candidate) and ``1..MAX_FLIPS`` are actual
    flips. The returned dict has ``flip``, the resolved ``drop`` (``None`` when a
    treasure overrides it or nothing was flipped), the overriding ``treasure``,
    the forced ``escape`` (True from the third flip on) and ``relocate`` (True
    only for the unflipped cave case).
    """
    _species(species)
    if type(flip) is not int or not 0 <= flip <= MAX_FLIPS:
        raise ValueError('Flip out of range: ' + repr(flip))
    _flag('cave', in_cave)
    _flag('demo', demo_flag)
    treasure = treasure_override(species, flip, carried_treasure) if flip else None
    drop = None if flip == UNFLIPPED or treasure is not None else drop_for(species, flip - 1, in_cave, demo_flag)
    return {
        'flip': flip,
        'drop': drop,
        'treasure': treasure,
        'escape': flip >= MAX_FLIPS,
        'relocate': relocates(flip, in_cave),
    }
