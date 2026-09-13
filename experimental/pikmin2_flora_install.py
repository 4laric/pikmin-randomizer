"""Flora / Candypop family batch-2 installation into a private run (#353, parent #171).

Thin binding of :mod:`experimental.pikmin2_batch2_core` to the flora family
config. Consumes the batch-1 ``flora.json`` manifest (policy ``P2_FLORA_1``).
Pelplant and HikariKinoko converted poses are not yet wired to native visual
actors and are excluded from the visual actor set. Native wiring stays with the
integration lead (#186).
"""
import argparse
import json
from pathlib import Path

from experimental.pikmin2_batch2_families import FAMILIES
from experimental.pikmin2_batch2_core import install as _install
from experimental.pikmin2_batch2_core import plan as _plan
from experimental.pikmin2_batch2_core import verify_install as _verify

CFG = FAMILIES['flora']
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
                        help='generator:species, e.g. 353001:BluePom')
    args = parser.parse_args()
    parsed = [(int(value.split(':')[0]), value.split(':')[1]) for value in args.actor]
    print(json.dumps(install(args.imported, args.run, parsed), sort_keys=True, indent=2))
