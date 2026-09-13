"""Ground-invertebrate batch-2 private arena staging (#346, parent #165).

Thin binding of :mod:`experimental.pikmin2_batch2_core` to the ground
invertebrate family. Six species plus an ordinary P1 control are staged on the
original Impact Site using the neutral Chappy placement vehicle (no audited P1
counterpart in this engine).
"""
import argparse
from pathlib import Path

from experimental.pikmin2_batch2_families import FAMILIES
from experimental.pikmin2_batch2_core import prepare as _prepare
from experimental.pikmin2_batch2_core import roster as _roster

CFG = FAMILIES['ground']
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
