"""MiniHoudai78 correlated natural generated-birth observer (lane muse-groink, #500).

Pure log predicates over a native run log: no native root, assets, or lane
paths required. A natural gate-1 birth for the mobile Gatling Groink
(source ID 78) requires the SAME generated actor to appear in all three
places with agreeing identity:

1. ``P2_SEED_RESOLVE source_id=78 target=<uid>`` (seed bridge resolve),
2. ``P2_PLACEMENT_SLOT generator=<g> slot=<uid>`` (placement probe, same uid),
3. ``P2_GROINK_CARCASS_READY generator=<g> ...`` plus
   ``P2_GROINK_CARCASS_BECOME generator=<g> ...`` (the Groink sidecar actually
   bound and birthed that generator).

Supporting evidence for the mobile firing variant (the projectile
corridor/helper contract: MiniHoudaiShotGun 3-shell swept-bomb corridor) is
``P2_GROINK_ATTACK_FIRE`` plus a sweep/strike PASS marker in the same log.
The corridor alone never closes gate 1.

Fail-closed negatives: a Frog-vehicle bind without resolve/slot agreement is
not a MiniHoudai birth; a pedestal ``source_id=97`` resolve on the same
generator belongs to FminiHoudai (out of scope), never to 78; a slot uid that
disagrees with the resolve target fails the join.
"""
import re

SOURCE_ID = 78
PEDESTAL_SOURCE_ID = 97

_SEED_RESOLVE_RE = re.compile(r'P2_SEED_RESOLVE\s+source_id=(\d+)\s+target=(\d+)')
_PLACEMENT_SLOT_RE = re.compile(r'P2_PLACEMENT_SLOT\s+generator=(\d+)\s+slot=(\d+)')
_CARCASS_READY_RE = re.compile(r'P2_GROINK_CARCASS_READY\s+generator=(\d+)')
_CARCASS_BECOME_RE = re.compile(r'P2_GROINK_CARCASS_BECOME\s+generator=(\d+)')
# Headless marker-contract fixture emits the same join with a MUSE prefix.
_MUSE_RESOLVE_RE = re.compile(r'P2_MUSE_GROINK_RESOLVE\s+source_id=(\d+)\s+target=(\d+)')
_MUSE_SLOT_RE = re.compile(r'P2_MUSE_GROINK_SLOT\s+generator=(\d+)\s+slot=(\d+)')
_MUSE_SIDECAR_RE = re.compile(r'P2_MUSE_GROINK_SIDECAR\s+generator=(\d+)')

_ATTACK_FIRE = 'P2_GROINK_ATTACK_FIRE'
_SWEEP_PASS = 'P2_GROINK_FLIGHT_SWEEP_PASS'
_STRIKE_PASS = 'P2_GROINK_STRIKE_PASS'


def seed_targets(text, source_id=SOURCE_ID):
    """All resolve targets claimed for ``source_id``, in log order."""
    return [m.group(2) for m in _SEED_RESOLVE_RE.finditer(text)
            if int(m.group(1)) == source_id]


def placement_slots(text):
    """Map of generator id -> slot uid from placement probe markers."""
    slots = {}
    for match in _PLACEMENT_SLOT_RE.finditer(text):
        slots[match.group(1)] = match.group(2)
    return slots


def bound_generators(text):
    """Generators with both READY and BECOME carcass markers (actually born)."""
    ready = {m.group(1) for m in _CARCASS_READY_RE.finditer(text)}
    become = {m.group(1) for m in _CARCASS_BECOME_RE.finditer(text)}
    return ready & become


def shell_corridor(text):
    """Projectile-corridor support: fired volley plus a sweep/strike PASS."""
    return {
        'attack_fire': _ATTACK_FIRE in text,
        'sweep_or_strike': _SWEEP_PASS in text or _STRIKE_PASS in text,
    }


def correlated_birth(text, generator, source_id=SOURCE_ID, corridor_required=True):
    """Gate-1 verdict for one generator: the full correlated join.

    ``generator`` is the arena generator id as a string or int. Every check
    is a byte-substring/regex test over the log, so stripping any marker
    flips its check. Returns an ordered dict of bools plus ``gate1``.
    """
    gid = str(generator)
    targets = seed_targets(text, source_id)
    slots = placement_slots(text)
    bound = bound_generators(text)
    corridor = shell_corridor(text)

    resolve = len(targets) > 0
    slot_agrees = resolve and slots.get(gid) in targets
    bound_here = gid in bound
    corridor_ok = corridor['attack_fire'] and corridor['sweep_or_strike']

    checks = {
        'seed_resolve': resolve,
        'slot_agrees': slot_agrees,
        'actor_bound': bound_here,
        'corridor_fire': corridor['attack_fire'],
        'corridor_sweep': corridor['sweep_or_strike'],
    }
    checks['gate1'] = slot_agrees and bound_here and (corridor_ok if corridor_required else True)
    return checks


def pedestal_confusion(text, generator):
    """True when generator <g> is claimed by a pedestal-97 resolve.

    Such a log must never count toward source 78, even if the carcass
    markers are present (the sidecar policy is shared by both variants).
    """
    gid = str(generator)
    targets97 = seed_targets(text, PEDESTAL_SOURCE_ID)
    slots = placement_slots(text)
    return gid in bound_generators(text) and slots.get(gid) in targets97


def muse_contract(text, generator, source_id=SOURCE_ID):
    """Same join for the headless marker-contract fixture log.

    The fixture proves the sidecar parser + slot/resolve wiring
    deterministically; it is labeled injected/contract evidence, never a
    natural gameplay birth.
    """
    gid = str(generator)
    targets = [m.group(2) for m in _MUSE_RESOLVE_RE.finditer(text)
               if int(m.group(1)) == source_id]
    slots = {}
    for match in _MUSE_SLOT_RE.finditer(text):
        slots[match.group(1)] = match.group(2)
    sidecar = {m.group(1) for m in _MUSE_SIDECAR_RE.finditer(text)}
    birth = 'P2_MUSE_GROINK_BIRTH_POLICY births=' in text
    resolve = len(targets) > 0
    slot_agrees = resolve and slots.get(gid) in targets
    checks = {
        'resolve': resolve,
        'slot_agrees': slot_agrees,
        'sidecar_parsed': gid in sidecar,
        'birth_policy': birth,
    }
    checks['contract'] = all(checks.values())
    return checks
