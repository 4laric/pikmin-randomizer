"""Lane 29 Jellyfloat corpse reward consumer of the lane-06 receipts (#243).

Two concrete source identities in the family: Kurage (Lesser Spotted Jellyfloat,
source ID 57) and OniKurage (Greater Spotted Jellyfloat, source ID 72). Both drop
a corpse body on the ordinary Onion ledger; the source has no family-local reward
function and ``EnemyBase::onKill`` supplies the body (BDT_Normal for Kurage,
BDT_Strong for OniKurage, per docs/PIKMIN2_ENEMY_ROSTER.json).

The native half of this slice (``native/pc_port/pc_p2_kurage_teki.cpp``) registers
the bound Kurage actor's dead-body ``PelletView`` and resolves it through a new
``pc_p2_kurage_receipt`` hook in the preview Pod delivery path, crediting the
Pod's configured ``corpseValue``. The exact source corpse Poko from ``enemyInfo.h``
is **not pinned here**; the reward ``value`` is left ``None`` in the descriptor so
the experimental Pod owns it, matching the native mamuta/sheargrub corpse pattern.

Scope: host-side reward bookkeeping only. It does not carry a corpse, deposit into
an Onion, or mutate a save. See docs/PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md.
"""
from experimental import pikmin2_receipts as receipts

FAMILY = 'jellyfloat'
SPECIES = {'Kurage': 57, 'OniKurage': 72}
IDENTITIES = {name: 'enemy:%d' % source for name, source in SPECIES.items()}
# Source drop classification (roster), not a fabricated Poko number.
DROP_TYPE = {'Kurage': 'BDT_Normal', 'OniKurage': 'BDT_Strong'}


def identity(species):
    """Return the ``enemy:<id>`` source identity for a Jellyfloat species/id."""
    if isinstance(species, int):
        for name, source in SPECIES.items():
            if source == species:
                return IDENTITIES[name]
        raise ValueError('Unknown Jellyfloat source id: ' + repr(species))
    if species not in IDENTITIES:
        raise ValueError('Unknown Jellyfloat species: ' + repr(species))
    return IDENTITIES[species]


def descriptors():
    """Lane 29 reward descriptors using the shared ``p2-reward-descriptor-v1`` schema.

    Each species drops its own corpse (value ``None``: owned by the experimental
    Pod corpseValue / source enemyInfo, not pinned here) on the ordinary Onion
    ledger. No pellet, Pod or invented reward is declared.
    """
    return receipts.validate_descriptors([
        {'version': receipts.SCHEMA_VERSION, 'identity': identity(name),
         'family': FAMILY, 'drop': receipts.DROP_KINDS[0],
         'ledger': receipts.LEDGER_ONION, 'count': 1}
        for name in SPECIES
    ])


def registry():
    """Return a lane-06 ``RewardRegistry`` seeded with the Jellyfloat descriptors."""
    return receipts.RewardRegistry(descriptors())


def _species(identity_value):
    for name, source in SPECIES.items():
        if IDENTITIES[name] == identity_value:
            return name
    raise ValueError('Unknown Jellyfloat reward identity: ' + str(identity_value))


def grant_pickup(ledger, seed, identity_value, actor, encounter):
    """Grant one corpse pickup reward; True only on the first occurrence.

    Only the concrete source identities earn a reward; unknown identities are
    rejected outright.
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
