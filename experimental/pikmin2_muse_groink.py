"""MiniHoudai78 correlated natural generated-birth observer (lane muse-groink, #500).

Pure log predicates over a native run log: no native root, assets, or lane
paths required. A natural gate-1 birth for the mobile Gatling Groink
(source ID 78) requires the SAME generated slot uid to appear in all four
places with agreeing identity:

1. ``P2_SEED_RESOLVE source_id=78 target=<uid>`` (seed bridge resolve),
2. ``P2_GENERATED_PLACEMENT source_id=78 target=<uid> ... bound=1``
   (muse-placement l52/#492 narrow native bind path; correlated through the
   reviewed :mod:`experimental.pikmin2_muse_placement` observer, which also
   pins the accepted slot uid),
3. ``P2_PLACEMENT_SLOT generator=<g> slot=<uid>`` (placement probe, same uid),
4. ``P2_GROINK_CARCASS_READY generator=<g> ...`` (the Groink sidecar claimed
   the live generated actor at setup).

A later ``P2_GROINK_CARCASS_BECOME`` (carcass begins at the host's natural
death) is reported separately as ``carcass_began``: it belongs to the
death/revival lifecycle (gates 4/6, preserved l21 evidence), not to the
spawn agreement, and an unattended product run performs no captain input to
start combat.

Projectile corridor/helper contract (MiniHoudaiShotGun 3-shell swept-bomb
corridor, no spawnable helper birth per docs/PIKMIN2_CANNON_GROINK_AUDIT.md)
is reported as support-only evidence: ``P2_GROINK_ATTACK_FIRE`` plus a
sweep/strike PASS where a volley fixture ran. The corridor alone never
closes gate 1, and a natural product birth carries no volley markers (the
generated host is a vehicle actor; shells are a family-run gate, not a
placement constraint).

Fail-closed negatives: a Frog-vehicle bind without resolve/bind/slot
agreement is not a MiniHoudai birth; a ``bound=0`` bind marker
(slot-rejected / bad-request) is a placement refusal, not a bind; a
pedestal ``source_id=97`` resolve on the same generator belongs to
FminiHoudai (out of scope), never to 78; a slot uid that disagrees with the
resolve/bind target fails the join.
"""
import re

from experimental.pikmin2_muse_placement import (
    MUSE_ACCEPTED_SLOT,
    observe_identity as placement_observe,
)

SOURCE_ID = 78
PEDESTAL_SOURCE_ID = 97
ACCEPTED_SLOT = MUSE_ACCEPTED_SLOT[SOURCE_ID]

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


def carcass_ready_generators(text):
    """Generators whose live actor the Groink sidecar claimed at setup."""
    return {m.group(1) for m in _CARCASS_READY_RE.finditer(text)}


def bound_generators(text):
    """Generators with both READY and BECOME carcass markers (carcass began).

    Reported separately from the spawn agreement: BECOME fires at the host's
    natural death, which is death-lifecycle evidence (gates 4/6), not spawn
    evidence. Preserved for the l21 history shape and the headless negatives.
    """
    return carcass_ready_generators(text) & {
        m.group(1) for m in _CARCASS_BECOME_RE.finditer(text)}


def shell_corridor(text):
    """Projectile-corridor support: fired volley plus a sweep/strike PASS."""
    return {
        'attack_fire': _ATTACK_FIRE in text,
        'sweep_or_strike': _SWEEP_PASS in text or _STRIKE_PASS in text,
    }


def correlated_birth(text, generator, source_id=SOURCE_ID):
    """Gate-1 verdict for one generator: the four-way spawn agreement.

    ``generator`` is the arena generator id as a string or int. The
    resolve/bind leg is delegated to the reviewed placement observer, so a
    ``bound=0`` refusal or a non-accepted slot can never pass. Every check
    is a byte-substring/regex test over the log, so stripping any marker
    flips its check. Returns a dict of bools plus ``gate1``.
    """
    gid = str(generator)
    placement = placement_observe(text, source_id)
    slots = placement_slots(text)
    ready = carcass_ready_generators(text)
    begun = bound_generators(text)
    corridor = shell_corridor(text)

    bound_uid = (str(placement['bound_uid'])
                 if placement['bound_uid'] is not None else None)
    slot_agrees = (placement['correlated']
                   and slots.get(gid) == bound_uid)
    sidecar_ready = gid in ready

    checks = {
        'seed_resolve': placement['resolved_uid'] is not None,
        'native_bound': placement['bound'],
        'resolve_bind_correlated': placement['correlated'],
        'refusal_reason': placement['refusal_reason'],
        'slot_agrees': slot_agrees,
        'sidecar_ready': sidecar_ready,
        'carcass_began': gid in begun,
        'corridor_fire': corridor['attack_fire'],
        'corridor_sweep': corridor['sweep_or_strike'],
    }
    checks['gate1'] = bool(placement['correlated'] and slot_agrees and sidecar_ready)
    return checks


def pedestal_confusion(text, generator):
    """True when generator <g> is claimed by a pedestal-97 resolve.

    Such a log must never count toward source 78, even if the carcass
    markers are present (the sidecar policy is shared by both variants).
    """
    gid = str(generator)
    targets97 = seed_targets(text, PEDESTAL_SOURCE_ID)
    slots = placement_slots(text)
    return gid in carcass_ready_generators(text) and slots.get(gid) in targets97


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
