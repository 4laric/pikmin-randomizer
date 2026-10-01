"""Lane 16 Frog/MaroFrog corpse reward consumer of the lane-06 receipts (#167/#201).

Builds the two concrete source identity reward descriptors on the shared
``experimental.pikmin2_receipts`` schema and proves exactly-once corpse pickup
plus restart persistence for the frog family.

Scope: host-side reward bookkeeping only. It does not implement native corpse
carry, the Onion deposit or any save mutation; those remain lane-01/06-gated.
See ``docs/PIKMIN2_FROG_REWARDS.md``.
"""
from experimental import pikmin2_receipts as receipts
from experimental import pikmin2_frog_behavior as behavior

FAMILY = 'frog'
SPECIES = {'Frog': 17, 'MaroFrog': 18}
IDENTITIES = {name: 'enemy:%d' % source for name, source in SPECIES.items()}
CORPSE_POKOS = {name: behavior.corpse(name)['pokos'] for name in SPECIES}


def identity(species):
    """Return the ``enemy:<id>`` source identity for a frog species name or id."""
    if isinstance(species, int):
        for name, source in SPECIES.items():
            if source == species:
                return IDENTITIES[name]
        raise ValueError('Unknown frog source id: ' + repr(species))
    if species not in IDENTITIES:
        raise ValueError('Unknown frog species: ' + repr(species))
    return IDENTITIES[species]


def descriptors():
    """Lane 16 reward descriptors using the shared ``p2-reward-descriptor-v1`` schema.

    Each species drops its own corpse worth the audited source Pokos on the
    ordinary Onion ledger. No pellet, Pod or invented reward is declared.
    """
    return receipts.validate_descriptors([
        {'version': receipts.SCHEMA_VERSION, 'identity': identity(name),
         'family': FAMILY, 'drop': receipts.DROP_KINDS[0],
         'ledger': receipts.LEDGER_ONION, 'value': CORPSE_POKOS[name], 'count': 1}
        for name in SPECIES
    ])


def registry():
    """Return a lane-06 ``RewardRegistry`` seeded with the frog descriptors."""
    return receipts.RewardRegistry(descriptors())


def carry_route(identity_value):
    """Return the source corpse/carry/Onion fields for one ``enemy:<id>`` identity."""
    return behavior.carry_route(_species(identity_value))


def _species(identity_value):
    for name, source in SPECIES.items():
        if IDENTITIES[name] == identity_value:
            return name
    raise ValueError('Unknown frog reward identity: ' + str(identity_value))


def grant_pickup(ledger, seed, identity_value, actor, encounter):
    """Grant one corpse pickup reward; True only on the first occurrence.

    Only the two concrete source identities earn a reward; unknown identities
    are rejected outright.
    """
    _species(identity_value)
    return ledger.grant(seed, identity_value, actor, encounter)


def resolve_pickups(ledger, seed, events):
    """Grant an ordered pickup sequence; return the identities newly granted.

    ``events`` is an iterable of ``(identity, actor, encounter)``. Revisiting the
    same actor/encounter in the same seed grants nothing the second time.
    """
    granted = []
    for identity_value, actor, encounter in events:
        if grant_pickup(ledger, seed, identity_value, actor, encounter):
            granted.append(identity_value)
    return granted


def reconcile_runs(expected_checks):
    """Reconcile the family descriptors against the expected ordinary checks."""
    return registry().reconcile_all(expected_checks)
