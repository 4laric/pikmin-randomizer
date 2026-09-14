"""Lane 17 consumer of the lane-06 reward/receipt contract (#168/#219).

Finite, source-table-accurate flip drops for the reward beetles
(Kogane 9 / Wealthy 10 / Doodlebug 11) with exactly-once receipts that survive a
process restart, plus a separate ordinary Onion credit for real collection.

This is host-side reward bookkeeping only. It models the audited per-flip drop
table in ``experimental.pikmin2_kogane_assets`` and the source escape after three
flips; it does not implement the native contested-cargo or gas behavior. The P1
host has no cave relocation and no spray items, so the cave branch and the
spicy/bitter demo-flag branches use their documented nectar fallback. See
``docs/PIKMIN2_KOGANE_REWARDS.md``.
"""
from experimental import pikmin2_receipts as receipts
from experimental.pikmin2_kogane_assets import MAX_FLIPS, drop_for

FAMILY = 'kogane'
SPECIES = {'kogane': 9, 'wealthy': 10, 'fart': 11}
ENEMY_IDS = (9, 10, 11)
_BY_ID = {9: 'kogane', 10: 'wealthy', 11: 'fart'}


def identity(enemy_id):
    """Return the shared receipt identity token for one beetle source id."""
    if enemy_id not in ENEMY_IDS:
        raise ValueError('Unknown reward beetle id: ' + repr(enemy_id))
    return 'enemy:' + str(enemy_id)


def flip_drop(enemy_id, flip, in_cave=False, demo_flag=False):
    """Resolve the audited source drop for flip ``1..MAX_FLIPS``.

    Raises ``ValueError`` for an unknown beetle, a non-integer flip or a flip
    beyond the source escape (the beetle must be burrowed away, not re-dropped).
    """
    if enemy_id not in ENEMY_IDS:
        raise ValueError('Unknown reward beetle id: ' + repr(enemy_id))
    if type(flip) is not int or not 1 <= flip <= MAX_FLIPS:
        raise ValueError('Flip out of range: ' + repr(flip))
    return drop_for(_BY_ID[enemy_id], flip - 1, in_cave, demo_flag)


class BeetleFlips:
    """Finite flip accounting for one seed, backed by a lane-06 receipt ledger.

    The source allows at most three drops per beetle, after which it escapes.
    Each distinct ``(seed, actor, flip)`` is granted exactly once, so a repeated
    frame or a reopened process never duplicates a drop. Collection is a second,
    separate exactly-once credit so an uncollected drop is never counted.
    """

    def __init__(self, ledger):
        if not isinstance(ledger, receipts.ReceiptLedger):
            raise ValueError('Expected a lane-06 ReceiptLedger')
        self._ledger = ledger

    def flips(self, seed, enemy_id, actor):
        """Return how many of the source flips are already registered."""
        ident = identity(enemy_id)
        seed_token = receipts.receipt_key(seed, ident, actor, 'probe')[0]
        actor_token = receipts.receipt_key(seed, ident, actor, 'probe')[2]
        return sum(1 for s, i, a, e in self._ledger.receipts
                   if s == seed_token and i == ident and a == actor_token
                   and e.startswith('flip'))

    def escaped(self, seed, enemy_id, actor):
        """True once all three source flips are registered on this actor."""
        return self.flips(seed, enemy_id, actor) >= MAX_FLIPS

    def register(self, seed, enemy_id, actor, flip, *, in_cave=False, demo_flag=False):
        """Register one natural flip and return its resolved drop.

        ``granted`` is True only for the first occurrence; a replay/restart
        reports ``granted=False`` and ``drop=None`` for the same event, and a
        flip beyond the escape reports ``escaped=True``.
        """
        if enemy_id not in ENEMY_IDS:
            raise ValueError('Unknown reward beetle id: ' + repr(enemy_id))
        if type(flip) is not int or flip < 1:
            raise ValueError('Invalid flip: ' + repr(flip))
        if flip > MAX_FLIPS:
            return {'flip': flip, 'granted': False, 'escaped': True, 'drop': None}
        drop = flip_drop(enemy_id, flip, in_cave, demo_flag)
        granted = self._ledger.grant(seed, identity(enemy_id), actor, 'flip%d' % flip)
        return {'flip': flip, 'granted': granted, 'escaped': False,
                'drop': drop if granted else None}

    def collect(self, seed, enemy_id, actor, flip):
        """Credit one collected drop to the ordinary Onion ledger, once."""
        if enemy_id not in ENEMY_IDS:
            raise ValueError('Unknown reward beetle id: ' + repr(enemy_id))
        if type(flip) is not int or not 1 <= flip <= MAX_FLIPS:
            raise ValueError('Invalid flip: ' + repr(flip))
        if not self._ledger.has(seed, identity(enemy_id), actor, 'flip%d' % flip):
            raise ValueError('Cannot collect an unregistered flip')
        return self._ledger.grant(seed, 'collect:' + identity(enemy_id), actor,
                                  'flip%d' % flip)
