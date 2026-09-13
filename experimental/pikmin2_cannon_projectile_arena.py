"""Cannon Beetle / projectile batch-2 private arena staging (#350, parent #169).

Thin binding of :mod:`experimental.pikmin2_batch2_core` to the cannon/projectile
family. Kabuto/Rkabuto/Fkabuto use the P1 Armored Cannon Beetle (Beatle 17)
ancestor as a placement vehicle and Rock uses the P1 Rolling Boulder (Iwagon 2);
Bomb and Egg use the neutral Chappy vehicle. Identity is not claimed.
"""
import argparse
from pathlib import Path

from experimental.pikmin2_batch2_families import FAMILIES
from experimental.pikmin2_batch2_core import prepare as _prepare
from experimental.pikmin2_batch2_core import roster as _roster

CFG = FAMILIES['cannon']
SPECIES = tuple(CFG['arena_species'])
IDS = tuple(CFG['arena_ids'])
POSITIONS = tuple(CFG['arena_positions'])
PROXY = dict(CFG['arena_proxy'])
FAMILY = dict(CFG['arena_family'])
GATES = tuple(CFG['gates'])
BLOCKED = dict(CFG['blocked'])


def roster(assets):
    return _roster(CFG, assets)


def prepare(assets, imported, output):
    return _prepare(CFG, assets, imported, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'imported', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.assets, args.imported, args.output))
