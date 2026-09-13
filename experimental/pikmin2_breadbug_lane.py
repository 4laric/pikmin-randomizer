"""Breadbug lane (#213): classification, source-rule reference models, reproducible extraction.

Source anchors (native/pikmin2-research, US GPVE01 rev 0 decomp snapshot):
- IDs: include/Game/enemyInfo.h:97-99 (38/39/40), :142 (83); boss flag list :216.
- Registration: src/plugProjectYamashitaU/enemyInfo.cpp:66-68; resource-name
  alias 39->83 at :168-173. GeneralEnemyMgr constructs PanModoki/OoPanModoki
  managers and a Nest::Mgr only for PanHouse (generalEnemyMgr.cpp:328-335);
  there is no case 39, so ID 39 has no manager and no EnemyInfo table row.
- FSM/states: include/Game/Entities/PanModokiBase.h:29-43; state behavior in
  src/plugProjectMorimuraU/panModokiState.cpp.
- Cargo contest: src/plugProjectKandoU/pelletCarry.cpp:30-60 (pull/pullable).
- Nest ownership: panModoki.cpp:54-75 (birth creates PanHouse), :1520-1526
  (killNest), enemyNest.cpp / enemyNestMgr.cpp (80-frame death fade).
- Defeat recovery: panModoki.cpp:1659-1697 (throwUpEatItem).

No native actor, hook, placement or reward behavior is installed here.
"""
import argparse
import json
import math
from pathlib import Path

from experimental.pikmin2_assets import disc_files, archive_files
from experimental.pikmin2_animation import sample_frames
from experimental.pikmin2_breadbug_assets import (
    sha, parameter_blocks, collision_nodes, target_allowed, carry_strength)
from experimental.pikmin2_convert import blocks, decode, write_model, convert
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_sheargrub_assets import animation_rows, joints
from experimental.pikmin2_skinning import draw_matrices

# PelletCarry state sentinels (include/Game/PelletCarry.h:9-13)
PCS_CARRY = 0
PCS_UNK1 = 1
PCS_UNK2 = 2  # Breadbug drag channel (pelletCarry.cpp usage from panModoki.cpp)
PCS_IDLE = 0xFFFF

MAX_HELD_TREASURES = 15  # PanModokiBase.h:45 PANMODOKI_MaxHeldTreasures
NEST_DEATH_FADE_FRAMES = 80  # enemyNestMgr.cpp:143-152
THROWUP_RING_SPEED = 50.0  # panModoki.cpp:1683-1687
THROWUP_HEIGHT = 10.0  # panModoki.cpp:1677-1678

# Registered IDs owned by this lane. spawnable=False entries must never be
# offered to the randomizer as autonomous creatures.
ENTRIES = {
    38: dict(name='PanModoki', role='creature', spawnable=True, boss=False,
             note='Small Breadbug; own manager PanModoki::Mgr'),
    39: dict(name='PanModokiNest', role='helper_alias', spawnable=False, boss=False,
             note='Resource-name alias only: EnemyInfoFunc::getEnemyResName rewrites 39->83 '
                  '(enemyInfo.cpp:168-173); generator token exists (genEnemy.cpp:532-534) but no '
                  'EnemyInfo row, no manager case and no FSM; spawning it directly has no defined base'),
    40: dict(name='OoPanModoki', role='source_boss', spawnable=True, boss=True,
             note='Giant Breadbug; IS_ENEMY_BOSS (enemyInfo.h:216); own manager OoPanModoki::Mgr'),
    83: dict(name='PanHouse', role='helper_nest', spawnable=False, boss=False,
             note='Nest::Obj; has EnemyInfo row with EFlag_HasNoInfo (enemyInfo.cpp:68) and a '
                  'Nest::Mgr (generalEnemyMgr.cpp:334-335), but is created and killed only by its '
                  'owner Breadbug (panModoki.cpp:54-75,1520-1526); helper, never autonomous'),
}


def classify(enemy_id):
    """Return the lane entry for a registered enemy ID."""
    if type(enemy_id) is not int or enemy_id not in ENTRIES:
        raise ValueError('Unknown Breadbug lane ID')
    return ENTRIES[enemy_id]


def spawnable(enemy_id):
    return classify(enemy_id)['spawnable']


def nest_house_type(owner_id):
    """enemyNest.cpp:60-67: Jigumo owners get the crawmad nest model."""
    if owner_id not in (38, 40, 64):  # 64 = Jigumo (nest alias pair at enemyInfo.cpp:168)
        raise ValueError('No nest ownership for this ID')
    return 0 if owner_id == 64 else 1


def contest_pullable(current_state, current_strength, challenger_strength):
    """PelletCarry::pullable (pelletCarry.cpp:54-60): idle or same-channel is
    always pullable; otherwise strictly greater strength wins the contest."""
    for v in (current_strength, challenger_strength):
        if not math.isfinite(v) or v < 0:
            raise ValueError('Invalid contest strength')
    if current_state == PCS_IDLE or current_state == PCS_UNK2:
        return True
    return challenger_strength > current_strength


def contest_pull(current_state, current_strength, challenger_strength):
    """PelletCarry::pull (pelletCarry.cpp:30-51). Returns the resulting
    (state, strength, timer) after a Breadbug drag attempt."""
    if not math.isfinite(challenger_strength) or challenger_strength < 0:
        raise ValueError('Invalid contest strength')
    if not math.isfinite(current_strength) or current_strength < 0:
        raise ValueError('Invalid contest strength')
    if current_state in (PCS_IDLE, PCS_UNK2):
        return (PCS_UNK2, challenger_strength, 0.0)
    if challenger_strength > current_strength:
        return (PCS_UNK2, challenger_strength, 0.5)  # stall timer on takeover
    return (current_state, current_strength, 0.0)


def endcarry_outcome(pellet_kind, held_count):
    """Obj::endCarry (panModoki.cpp:1322-1357). kind is 'treasure', 'carcass'
    or 'item'. Returns dict(fate, kills_carriers, stored_slot)."""
    if pellet_kind not in ('treasure', 'carcass', 'item'):
        raise ValueError('Unknown pellet kind')
    if type(held_count) is not int or not 0 <= held_count < MAX_HELD_TREASURES:
        raise ValueError('Invalid held count')
    outcome = dict(kills_carriers=True, stored_slot=None)  # stuck Pikmin are killed
    if pellet_kind == 'treasure':
        outcome['stored_slot'] = held_count
        # Slot 0 is kept captured-alive in the nest; later slots are killed
        # then remembered and revived by throwUpEatItem on death.
        outcome['fate'] = 'nest_capture' if held_count == 0 else 'kill_and_record'
    else:
        outcome['fate'] = 'kill'
    return outcome


def throwup_velocities(count, base=(0.0, 0.0, 0.0)):
    """Obj::throwUpEatItem (panModoki.cpp:1659-1697): held treasures re-spawn
    at the nest (home + 10y) with the base throw velocity plus a 50-unit
    radial ring offset; a single treasure gets no radial offset."""
    if type(count) is not int or not 1 <= count <= MAX_HELD_TREASURES:
        raise ValueError('Invalid throwup count')
    if len(base) != 3 or any(not math.isfinite(v) for v in base):
        raise ValueError('Invalid base velocity')
    result = []
    for i in range(count):
        vx, vy, vz = base
        if count != 1:
            angle = (2.0 * math.pi * i) / count
            vx += math.sin(angle) * THROWUP_RING_SPEED
            vz += math.cos(angle) * THROWUP_RING_SPEED
        result.append((vx, vy, vz))
    return result


def _profile(blocks_):
    """Name the general/proper fields the lane relies on; keep raw blocks."""
    general = blocks_[1]
    proper = blocks_[2]
    return dict(
        health=general['fp00'], move_speed=general['fp06'],
        search_distance=general['fp14'], search_angle=general['fp15'],
        proper=dict(nest_scale=proper['fp00'], carry_speed=proper['fp03'],
                    suck_damage=proper['fp04'], press_damage=proper['fp06'],
                    wait_time=proper['fp14'], hide_time=proper['fp15'],
                    walk_anim_speed=proper['fp16'],
                    max_carry_weight=int(proper['ip01'])))


def extract(iso, output, pose_limit=3):
    """Re-extract all three lane species from a local US GPVE01 rev 0 ISO.

    Breadbug: rigid first-pose probe per clip (existing supported path).
    Giant Breadbug: sampled weighted poses via authored EVP1 inverse matrices
    (pikmin2_skinning.draw_matrices); its model carries TEX matrix indices the
    rigid path rejects. Nest: static rigid pose only (no animation bank).
    """
    if type(pose_limit) is not int or not 2 <= pose_limit <= 8:
        raise ValueError('Pose limit must be 2..8')
    index = disc_files(iso)
    output.mkdir(parents=True, exist_ok=False)
    hashes = {}
    result = dict(schema=1, lane=213, native_ready=False, source_sha256=hashes,
                  classification=ENTRIES, species={})
    with iso.open('rb') as disc:
        def read(path):
            offset, size = index[path]
            disc.seek(offset)
            raw = disc.read(size)
            if len(raw) != size:
                raise ValueError('Truncated source')
            hashes[path] = sha(raw)
            return raw

        params = archive_files(read('enemy/parm/enemyParms.szs'))
        for species in ('PanModoki', 'OoPanModoki', 'PanHouse'):
            root = output / species
            root.mkdir()
            model = archive_files(read(f'enemy/data/{species}/model.szs'))['enemy.bmd']
            modelpath = root / 'enemy.bmd'
            modelpath.write_bytes(model)
            names = joints(model)
            metadata = {}
            parsed = {}
            for filename in ('enemyparm.txt', 'enemycoll.txt', 'enemyanimmgr.txt',
                             'enemystoneinfo.txt'):
                key = species.lower() + '/' + filename
                if key not in params:
                    continue
                raw = params[key]
                (root / filename).write_bytes(raw)
                metadata[filename] = sha(raw)
                if filename == 'enemyparm.txt':
                    parsed['parameter_blocks'] = parameter_blocks(raw)
                if filename == 'enemycoll.txt':
                    parsed['collision'] = collision_nodes(raw, len(names))
            entry = dict(model_sha256=sha(model), joints=names,
                         metadata_sha256=metadata, clips=[], static_pose=None,
                         weighted=species == 'OoPanModoki', **parsed)
            if species != 'PanHouse':
                entry['profile'] = _profile(parsed['parameter_blocks'])
                motions = archive_files(read(f'enemy/data/{species}/anim.szs'))
                for row in animation_rows(params[species.lower() + '/enemyanimmgr.txt']
                                          .decode('shift_jis')):
                    raw = motions[row['file']]
                    (root / row['file']).write_bytes(raw)
                    clip = dict(row, sha256=sha(raw), status='source_only', poses=[])
                    try:
                        duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
                        clip['source_frames'] = duration
                        frames = sorted(set(sample_frames(duration, pose_limit))
                                        | {e[0] for e in row['events']})
                        for frame in frames:
                            _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                            name = Path(row['file']).stem + f'_{frame:03}.mod'
                            if species == 'OoPanModoki':
                                matrices = draw_matrices(blocks(model), pose)
                                decoded = decode(model, True, bake_rigid=True,
                                                 draw_matrices=matrices)
                                write_model(decoded, root / name, 'enemy.bmd')
                            else:
                                convert(modelpath, root / name, True,
                                        bake_rigid=True, pose=pose)
                            clip['poses'].append(dict(file=name, frame=frame,
                                                      sha256=sha((root / name).read_bytes())))
                        clip['status'] = 'sampled_poses_converted'
                    except ValueError as error:
                        clip['unsupported_reason'] = str(error)
                    entry['clips'].append(clip)
            else:
                try:
                    convert(modelpath, root / 'nest.mod', True, bake_rigid=True)
                    entry['static_pose'] = dict(file='nest.mod',
                                                sha256=sha((root / 'nest.mod').read_bytes()))
                except ValueError as error:
                    entry['static_pose'] = dict(unsupported_reason=str(error))
            result['species'][species] = entry
    result['limitations'] = [
        'Sampled baked poses and approximate materials; no skeletal/event playback.',
        'Giant texture-matrix animation (J3DMLF_UsePostTexMtx, panModokiMgr.cpp:73-90) '
        'is approximated as static; normals use inverse transpose.',
        'No cargo ownership, nest lifetime, receiver damage, collision installation '
        'or corpse/delivery behavior installed natively.',
        'PanModokiNest 39 remains a resource alias; PanHouse 83 remains helper-only. '
        'Neither is spawnable.',
    ]
    (output / 'breadbug-lane.json').write_text(json.dumps(result, indent=2) + '\n',
                                               encoding='utf-8')
    # Schema-1 compatibility view so the established visual/cargo profile
    # pipeline (pikmin2_breadbug_visual/cargo_bank) can consume this import.
    compat = dict(schema=1, native_ready=False, source_sha256=hashes,
                  species={name: dict(model_sha256=entry['model_sha256'],
                                      joints=entry['joints'], clips=entry['clips'],
                                      static_pose=entry['static_pose'],
                                      metadata_sha256=entry['metadata_sha256'],
                                      parameter_blocks=entry['parameter_blocks'],
                                      collision=entry['collision'])
                           for name, entry in result['species'].items()},
                  limitations=result['limitations'])
    (output / 'breadbugs.json').write_text(json.dumps(compat, indent=2) + '\n',
                                           encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=3)
    args = parser.parse_args()
    r = extract(args.iso, args.output, args.pose_limit)
    print(json.dumps({k: dict(joints=len(v['joints']), clips=len(v['clips']),
                              poses=sum(len(c['poses']) for c in v['clips']),
                              static=bool(v['static_pose'] and v['static_pose'].get('file')))
                      for k, v in r['species'].items()}))
