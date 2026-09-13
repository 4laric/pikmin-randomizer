"""Long Legs family batch-2 private arena staging (#312, parent #173).

Stages the two lane-owned family members (Houdai/Man-at-Legs, BigFoot/Raging
Long Legs) plus an ordinary P1 control on the original Impact Site via the
shared batch-2 arena builder, installing the batch-1 mesh bank with
:mod:`experimental.pikmin2_long_legs_install`. Long Legs has no teki type in
this engine's ``teki.h``, so the neutral Chappy placement vehicle is used and
identity is not claimed; Damagumo/Beady Long Legs (56) stays with the demon lane.
"""
import argparse
from pathlib import Path

from experimental.pikmin2_batch2_core import P1_CHAPPY_TYPE
from experimental.pikmin2_batch2_core import prepare as _prepare
from experimental.pikmin2_batch2_core import roster as _roster
from experimental.pikmin2_long_legs_install import (MANIFEST, install,
                                                    verify_install)

CFG = dict(
    name='long-legs', parent='#173', manifest=MANIFEST, species={'Houdai': 66, 'BigFoot': 69},
    actors=('Houdai', 'BigFoot'),
    arena_ids=(312001, 312002, 312003),
    arena_species=('Houdai', 'BigFoot', 'P1 Chappy'),
    arena_positions=((-120.0, 30.0, 1850.0), (120.0, 30.0, 1850.0), (240.0, 30.0, 1500.0)),
    arena_proxy={'Houdai': P1_CHAPPY_TYPE, 'BigFoot': P1_CHAPPY_TYPE,
                 'P1 Chappy': P1_CHAPPY_TYPE},
    arena_family={P1_CHAPPY_TYPE: 'Chappy (P1 Dwarf Bulborb)'},
    control='P1 Chappy', source_yaw=None,
    actors_txt='p2-long-legs-actors.txt', install_json='long-legs-install.json',
    gates=('native_identity', 'spawn_exact_xyz', 'control_undisturbed', 'natural_AI',
           'combat', 'death_corpse', 'carrier_recovery', 'reload',
           'ik_leg_stability', 'foot_crush', 'houdai_gun_callback', 'skeletal_playback'),
    blocked={
        'native_identity': 'blocked: no native registration for 66/69 (integration lead #186; '
                           'flagged on #312)',
        'natural_AI': 'blocked: no P1 Long Legs counterpart; Chappy placement vehicle only',
        'combat': 'blocked: crush attacks and damage receivers not ported',
        'death_corpse': 'blocked: corpse/carry behavior not ported',
        'ik_leg_stability': 'blocked: shared IKSystemMgr leg stability not ported',
        'foot_crush': 'blocked: foot press/crush hitboxes not ported',
        'houdai_gun_callback': 'blocked: Man-at-Legs gun callback joints not ported',
        'skeletal_playback': 'blocked: mesh is bind-pose only; no skeletal animation bank'},
    limitations=[
        'Bind-pose mesh decode only; no animation pose bank, skeletal playback or event execution.',
        'Long Legs has no teki type in engine/include/teki.h; the Chappy placement vehicle is '
        'used purely to stage the source mesh and does not claim identity.',
        'Damagumo/Beady Long Legs (56) is owned by the demon lane and is not staged here.',
        'Native IK, crush, gun-callback and reward behavior remain lane work (#173/#186).'])

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
    return _prepare(CFG, assets, imported, output,
                    installer=install, verifier=verify_install)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'imported', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.assets, args.imported, args.output))
