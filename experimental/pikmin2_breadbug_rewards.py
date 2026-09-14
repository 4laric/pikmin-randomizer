"""Lane 18 consumer of the lane-06 reward/receipt contract (#168/#220/#441).

Builds the PanModoki / OoPanModoki reward descriptors on the shared
``experimental.pikmin2_receipts`` schema and proves exactly-once grant plus
restart persistence for the breadbug/nest family.

Scope: host-side reward bookkeeping only. It does not implement the native
contested-cargo behavior (that remains the lane-06/engine-gated next slice) and
never reads or mutates a Pikmin 2 save. See ``docs/PIKMIN2_BREADBUG_ACTOR_RUNTIME.md``.
"""
from experimental import pikmin2_receipts as receipts

FAMILY = 'breadbug'
SMALL = 'enemy:38'          # PanModoki (small Breadbug)
GIANT = 'enemy:40'          # OoPanModoki (Giant Breadbug, source boss)
NEST_ALIAS = 'alias:39'     # PanModokiNest alias (non-spawnable)
PANHOUSE = 'helper:83'      # PanHouse helper nest
HELPERS = (NEST_ALIAS, PANHOUSE)


def descriptors():
    """Lane 18 reward descriptors using the shared ``p2-reward-descriptor-v1`` schema.

    Small Breadbug drops an ordinary Pikmin pellet on the Onion ledger; the
    Giant Breadbug defeat yields its carryable carcass as an ordinary AP check.
    Helpers/aliases deliberately have no descriptor.
    """
    return receipts.validate_descriptors([
        {'version': receipts.SCHEMA_VERSION, 'identity': SMALL, 'family': FAMILY,
         'drop': 'pellet', 'ledger': receipts.LEDGER_ONION, 'value': 1, 'count': 1},
        {'version': receipts.SCHEMA_VERSION, 'identity': GIANT, 'family': FAMILY,
         'drop': 'corpse', 'ledger': receipts.LEDGER_AP, 'value': 1, 'count': 1},
    ])


def registry():
    """Return a lane-06 ``RewardRegistry`` seeded with the breadbug descriptors."""
    return receipts.RewardRegistry(descriptors())


def _descriptor(identity):
    for descriptor in descriptors():
        if descriptor['identity'] == identity:
            return descriptor
    return None


def grant_defeat(ledger, seed, identity, actor, encounter):
    """Grant one breadbug defeat reward; True only on the first occurrence.

    Helpers and aliases are rejected outright: they must never earn a check.
    """
    if identity in HELPERS:
        raise ValueError('Helper/alias identities never earn rewards: ' + identity)
    if _descriptor(identity) is None:
        raise ValueError('Unknown breadbug reward identity: ' + identity)
    return ledger.grant(seed, identity, actor, encounter)


def resolve_encounters(ledger, seed, encounters):
    """Grant an ordered encounter sequence; return the identities newly granted.

    ``encounters`` is an iterable of ``(identity, actor, encounter)``. Revisiting
    the same actor/encounter in the same seed grants nothing the second time.
    """
    granted = []
    for identity, actor, encounter in encounters:
        if grant_defeat(ledger, seed, identity, actor, encounter):
            granted.append(identity)
    return granted


def reconcile_runs(expected_checks):
    """Reconcile the family descriptors against the expected ordinary checks."""
    return registry().reconcile_all(expected_checks)
