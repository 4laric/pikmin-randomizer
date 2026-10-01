"""Dweevil family batch-2 private arena staging (#349, parent #170).

Thin binding of :mod:`experimental.pikmin2_batch2_core` to the dweevil family.
Original Impact Site map/collision/routes are preserved; one explicit actor per
dweevil plus an ordinary P1 control. Members have no audited P1 ancestor in this
engine, so the neutral Chappy placement vehicle is used and identity is not
claimed.
"""
import argparse
from pathlib import Path

from experimental.pikmin2_batch2_families import FAMILIES
from experimental.pikmin2_batch2_core import prepare as _prepare
from experimental.pikmin2_batch2_core import roster as _roster

CFG = FAMILIES['dweevil']
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
