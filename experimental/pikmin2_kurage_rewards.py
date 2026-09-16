"""Lane 29 Jellyfloat reward consumer of the lane-06 receipts (#243).

Two concrete source identities in the family: Kurage (Lesser Spotted Jellyfloat,
source ID 57) and OniKurage (Greater Spotted Jellyfloat, source ID 72).

Source-fidelity (verified against decomp ``Kurage.cpp:36``, ``enemyBase.cpp``
``onKill``/``deathProcedure``/``throwupItem``): a Jellyfloat **disables
``EB_LeaveCarcass``** and has no family-local reward function. On a natural kill
it throws up a **number pellet** (``pelletMgr->makePelletInitArg(..., mPelletDropCode)``)
during ``throwupItemInDeathProcedure``, plus an optional bitter-honey drop only
when killed while bittered. It does **not** leave a carryable corpse body. The
drop kind is therefore ``pellet``, not ``corpse`` (the roster ``BDT_Normal`` /
``BDT_Strong`` fields only classify the bitter-honey drop, not a Poko value; no
numeric Poko for either ID exists in ``enemyInfo.h``).

The native half of this slice (``native/pc_port/pc_p2_kurage_teki.cpp``) currently
resolves the bound actor's dead-body ``PelletView`` through ``pc_p2_kurage_receipt``
and credits the Pod's configured ``corpseValue`` as ``corpse:kurage:<gen>``. That is
a **labelled P1-proxy approximation**: the P1 frog proxy leaves a carryable body,
whereas the P2 source throws up a number pellet. A source-faithful native
pellet-reward slice (reusing the ``pc_p2_receipt`` ``Ledger::Onion`` ``drop=pellet``
path) is future work. The reward ``value`` stays ``None`` here (Poko derives from
``mPelletDropCode`` / the generator's ``EnemyPelletInfo``, not a per-enemy constant).

Scope: host-side reward bookkeeping only. It does not carry an item, deposit into
an Onion, or mutate a save. See docs/PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md.
"""
from experimental import pikmin2_receipts as receipts

FAMILY = 'jellyfloat'
SPECIES = {'Kurage': 57, 'OniKurage': 72}
IDENTITIES = {name: 'enemy:%d' % source for name, source in SPECIES.items()}
# Source bitter-honey drop classification (roster); not a Poko number.
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

    Each species throws up a number pellet (``drop='pellet'``; value ``None``:
    owned by the experimental Pod / source ``mPelletDropCode`` + ``EnemyPelletInfo``,
    not pinned here) on the ordinary Onion ledger. No corpse, treasure, Pod or
    invented reward is declared.
    """
    return receipts.validate_descriptors([
        {'version': receipts.SCHEMA_VERSION, 'identity': identity(name),
         'family': FAMILY, 'drop': receipts.DROP_KINDS[1],  # 'pellet'
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
    """Grant one pellet pickup reward; True only on the first occurrence.

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
