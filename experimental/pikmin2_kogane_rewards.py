"""Lane 17 consumer of the lane-06 reward/receipt contract (#168/#219).

Finite, source-table-accurate flip drops for the reward beetles
(Kogane 9 / Wealthy 10 / Doodlebug 11) with exactly-once receipts that survive a
process restart, plus a separate ordinary Onion credit for real collection.

This is host-side reward bookkeeping only. It resolves the audited per-flip drop
table through ``experimental.pikmin2_kogane_cave.resolve_flip`` (which in turn
uses ``experimental.pikmin2_kogane_assets.drop_for``): a carried cave treasure
overrides the first flip, the table covers the rest and the source escape happens
from the third flip. It does not implement the native contested-cargo or gas
behavior. The P1 host has no spray items, so the spicy/bitter demo-flag branches
use their documented nectar fallback. See ``docs/PIKMIN2_KOGANE_REWARDS.md``.
"""
from pathlib import Path

from experimental import pikmin2_kogane_cave as cave
from experimental import pikmin2_receipts as receipts
from experimental.pikmin2_kogane_assets import MAX_FLIPS

FAMILY = 'kogane'
SPECIES = {'kogane': 9, 'wealthy': 10, 'fart': 11}
ENEMY_IDS = (9, 10, 11)
_BY_ID = {9: 'kogane', 10: 'wealthy', 11: 'fart'}

# On-disk flip-receipt sidecar written by pc_p2_kogane.cpp (#168/#219). This is
# a family-local file inside the run directory, deliberately separate from the
# P2 save (lane 01/06 owns that contract).
RECEIPTS_FILENAME = 'p2-kogane-receipts.txt'
RECEIPTS_HEADER = 'P2_KOGANE_RECEIPTS_1'


def identity(enemy_id):
    """Return the shared receipt identity token for one beetle source id."""
    if enemy_id not in ENEMY_IDS:
        raise ValueError('Unknown reward beetle id: ' + repr(enemy_id))
    return 'enemy:' + str(enemy_id)


def parse_receipts(text):
    """Parse and validate the native flip-receipt sidecar into ``{generator: flips}``.

    Mirrors the native loader exactly: the first line must be
    ``P2_KOGANE_RECEIPTS_1``, blank lines are skipped, every other row must be
    ``<generator> <flips>`` with a positive generator and ``1..MAX_FLIPS`` flips,
    and generators must be unique. Raises ``ValueError`` on any drift so callers
    can fail safe (the native loader ignores the whole file instead).
    """
    if not isinstance(text, str):
        raise ValueError('Receipt sidecar must be text')
    lines = text.splitlines()
    if not lines or lines[0] != RECEIPTS_HEADER:
        raise ValueError('Invalid receipt sidecar header')
    result = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 2 or not all(field.isdigit() for field in fields):
            raise ValueError('Invalid receipt sidecar row: ' + line)
        generator, flips = int(fields[0]), int(fields[1])
        if generator < 1 or not 1 <= flips <= MAX_FLIPS:
            raise ValueError('Receipt sidecar value out of range: ' + line)
        if generator in result:
            raise ValueError('Duplicate receipt generator: ' + str(generator))
        result[generator] = flips
    return result


def read_receipts(path):
    """Read the sidecar at ``path``, returning ``{}`` when absent or malformed.

    This is the exact fail-safe of the native ``loadReceipts``: a corrupt or
    missing file yields an empty ledger rather than an error.
    """
    path = Path(path)
    if not path.is_file():
        return {}
    try:
        return parse_receipts(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}



def flip_drop(enemy_id, flip, in_cave=False, demo_flag=False, carried_treasure=None):
    """Resolve the audited source drop for flip ``1..MAX_FLIPS``.

    ``carried_treasure`` is a cave beetle ``mPelletDropCode``; on the first flip
    it replaces the whole table through the lane-17 cave model. Raises
    ``ValueError`` for an unknown beetle, a non-integer flip or a flip beyond the
    source escape (the beetle must be burrowed away, not re-dropped).
    """
    if enemy_id not in ENEMY_IDS:
        raise ValueError('Unknown reward beetle id: ' + repr(enemy_id))
    if type(flip) is not int or not 1 <= flip <= MAX_FLIPS:
        raise ValueError('Flip out of range: ' + repr(flip))
    outcome = cave.resolve_flip(_BY_ID[enemy_id], flip, in_cave, demo_flag, carried_treasure)
    return outcome['treasure'] if outcome['treasure'] is not None else outcome['drop']


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

    def register(self, seed, enemy_id, actor, flip, *, in_cave=False, demo_flag=False,
                 carried_treasure=None):
        """Register one natural flip and return its resolved drop.

        ``granted`` is True only for the first occurrence; a replay/restart
        reports ``granted=False`` and ``drop=None`` for the same event, and a
        flip beyond the escape reports ``escaped=True``. A ``carried_treasure``
        overrides the first flip through the lane-17 cave model.
        """
        if enemy_id not in ENEMY_IDS:
            raise ValueError('Unknown reward beetle id: ' + repr(enemy_id))
        if type(flip) is not int or flip < 1:
            raise ValueError('Invalid flip: ' + repr(flip))
        if flip > MAX_FLIPS:
            return {'flip': flip, 'granted': False, 'escaped': True, 'drop': None}
        drop = flip_drop(enemy_id, flip, in_cave, demo_flag, carried_treasure)
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
