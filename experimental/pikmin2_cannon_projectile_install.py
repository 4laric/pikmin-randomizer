"""Cannon Beetle / projectile batch-2 installation into a private run (#350, parent #169).

Thin binding of :mod:`experimental.pikmin2_batch2_core` to the cannon/projectile
family config. Consumes the batch-1 ``cannon_projectile.json`` manifest (policy
``P2_CANNON_PROJECTILE_1``). Projectile and buried-helper identities are staged
as explicit actors; their lifecycle remains native work (#169/#186).
"""
import argparse
import json
from pathlib import Path

from experimental.pikmin2_batch2_families import FAMILIES
from experimental.pikmin2_batch2_core import install as _install
from experimental.pikmin2_batch2_core import plan as _plan
from experimental.pikmin2_batch2_core import verify_install as _verify

CFG = FAMILIES['cannon']
MANIFEST = CFG['manifest']
POLICY = CFG['policy']
PROFILE_TXT = CFG['profile_txt']
BANK_TXT = CFG['bank_txt']
ACTORS_TXT = CFG['actors_txt']
ACTORS_HEADER = CFG['actors_header']
INSTALL_JSON = CFG['install_json']
ANCHORS = CFG['anchors']


def plan(imported, actors):
    return _plan(CFG, imported, actors)


def install(imported, run, actors):
    return _install(CFG, imported, run, actors)


def verify_install(imported, run, actors):
    return _verify(CFG, imported, run, actors)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('imported', 'run'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--actor', action='append', required=True,
                        help='generator:species, e.g. 350001:Kabuto')
    args = parser.parse_args()
    parsed = [(int(value.split(':')[0]), value.split(':')[1]) for value in args.actor]
    print(json.dumps(install(args.imported, args.run, parsed), sort_keys=True, indent=2))
