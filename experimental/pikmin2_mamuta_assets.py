"""Local Mamuta (Miulin, enemy ID 54) source model/animation assets and behavior reference.

Source audit: docs/PIKMIN2_MAMUTA_AUDIT.md (issue #214, parent #168). Extraction
follows the sheargrub lane: bounded rigid pose sampling, parameter text preserved,
hashes recorded for reproducibility. No native behavior substitution.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_convert import blocks, decode, u16, u32, write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_skinning import draw_matrices
from experimental.pikmin2_animation import sample_frames
from experimental.pikmin2_snow_policy import animation_events, parameter_groups

SPECIES = 'Miulin'
MODEL_PATH = f'enemy/data/{SPECIES}/model.szs'
ANIM_PATH = f'enemy/data/{SPECIES}/anim.szs'
PARM_SOURCE = 'enemy/parm/enemyParms.szs'
PARM_PREFIX = 'miulin/'
METADATA_FILES = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt', 'enemystoneinfo.txt')

# AnimID order from include/Game/Entities/Miulin.h:254-265; clip names are the
# source-registered basenames (retail: attack0/attack1/attack4/dead/flick/move/type5/wait/waitact).
EXPECTED_CLIPS = ('attack0.bca', 'attack1.bca', 'attack4.bca', 'dead.bca', 'flick.bca',
                  'move.bca', 'type5.bca', 'wait.bca', 'waitact.bca')
ANIM_ID_BY_CLIP = {'attack0.bca': 0, 'attack1.bca': 1, 'attack4.bca': 2, 'dead.bca': 3,
                   'flick.bca': 4, 'move.bca': 5, 'type5.bca': 6, 'wait.bca': 7, 'waitact.bca': 8}

# ProperParms header defaults, include/Game/Entities/Miulin.h:222-229 ('ip01','fp03'-'fp08').
PROPER_PARM_KEYS = ('ip01', 'fp03', 'fp04', 'fp05', 'fp06', 'fp07', 'fp08')
PROPER_PARM_DEFAULTS = {'ip01': 100, 'fp03': 20.0, 'fp04': 2.0, 'fp05': 2.0,
                        'fp06': 10.0, 'fp07': 30.0, 'fp08': 25.0}

# Non-lethal attack contract, miulinState.cpp:264-330 and interactPiki.cpp:377-442.
BURY_VERTICAL_BAND = 20.0       # maxY/minY around the attack point, miulinState.cpp:273-274
PIKI_BURY_DAMAGE = 0.0          # InteractBury(enemy, 0.0f) for Pikmin, miulinState.cpp:292
NAVI_BURY_DAMAGE = 5.0          # InteractBury(enemy, 5.0f) for captains, miulinState.cpp:312
BURIED_PIKMIN_CAP_US = 99       # GameStat::mePikis >= 99 rejects burial, interactPiki.cpp:382-384

# EnemyParmsBase GeneralParms keys, include/Game/EnemyParmsBase.h:55-94.
GENERAL_PARM_FIELDS = {'fp00': 'health', 'fp09': 'territory_radius', 'fp10': 'home_radius',
                       'fp11': 'private_radius', 'fp14': 'search_distance', 'fp15': 'search_angle',
                       'fp16': 'shake_chance', 'fp17': 'shake_knockback', 'fp18': 'shake_damage',
                       'fp19': 'shake_range', 'fp22': 'attack_radius', 'fp24': 'attack_damage',
                       'fp29': 'alert_duration', 'fp30': 'life_before_alert'}

STATE_IDS = {'wait': 0, 'walk': 1, 'attackstart': 2, 'attacking': 3, 'attackend': 4,
             'turn': 5, 'flick': 6, 'dead': 7}  # Miulin.h:20-31

TEXT = 'P2_MAMUTA_1\nnonlethal bury_attack\npiki_damage 0\nnavi_damage 5\nvertical_band 20\n'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def joints(model):
    """Joint names from the model JNT1 block; shared with the sheargrub lane approach."""
    data = blocks(model)['JNT1']
    count = u16(data, 8)
    offset = u32(data, 20)
    if offset + 4 > len(data) or u16(data, offset) != count:
        raise ValueError('Invalid joint name table')
    names = []
    for i in range(count):
        entry = offset + 4 + 4 * i
        if entry + 4 > len(data):
            raise ValueError('Truncated joint table')
        start = offset + u16(data, entry + 2)
        if start >= len(data):
            raise ValueError('Invalid joint name offset')
        end = data.find(b'\0', start)
        if end < 0:
            raise ValueError('Unterminated joint name')
        names.append(data[start:end].decode('ascii'))
    return names


def attack_band_hit(piki_dy, sqr_distance_xz, attack_radius):
    """StateAttacking KEYEVENT_2 hit test: |dy| < 20 band and XZ distance < attack radius.

    miulinState.cpp:273-294; applies to live Pikmin not stuck to the Mamuta.
    """
    if not all(map(math.isfinite, (piki_dy, sqr_distance_xz, attack_radius))):
        raise ValueError('Nonfinite attack test input')
    if attack_radius <= 0 or sqr_distance_xz < 0:
        raise ValueError('Invalid attack geometry')
    return abs(piki_dy) < BURY_VERTICAL_BAND and sqr_distance_xz < attack_radius ** 2


def attack_start_eligible(sqr_distance_xz, angle_radians, attack_radius, min_attack_range,
                          continuous_press_angle_degrees):
    """isAttackStart cone + squared-distance band test, miulin.cpp:170-214.

    True when the target is inside the continuous-press cone and its squared XZ
    distance lies within min_range^2 - radius^2 < d^2 < min_range^2 + radius^2
    (the source squares both parameters before comparing, miulin.cpp:172-186).
    """
    values = (sqr_distance_xz, angle_radians, attack_radius, min_attack_range)
    if not all(map(math.isfinite, values)) or sqr_distance_xz < 0:
        raise ValueError('Nonfinite attack-start input')
    if abs(angle_radians) > math.radians(continuous_press_angle_degrees):  # PI*(DEG2RAD*deg), DEG2RAD=1/180
        return False
    atk = attack_radius ** 2
    center = min_attack_range ** 2
    return center - atk < sqr_distance_xz < center + atk


def bury_outcome(invincible, buried_pikis, bald_triangle, might_bury, sprout_mgr_available,
                 sprout_birth_ok, region='US'):
    """InteractBury::actPiki receiver decision, interactPiki.cpp:377-442.

    Returns 'reject' (no state change), 'walk' (Pikmin sent to Walk after failed
    sprout birth), or 'convert' (flower-stage same-kind sprout planted; original
    Pikmin killed with CKILL_DontCountAsDeath).
    """
    if region not in ('US', 'PAL'):
        raise ValueError('Unsupported region')
    if type(buried_pikis) is not int or not 0 <= buried_pikis <= 1000:
        raise ValueError('Invalid buried Pikmin count')
    if invincible:
        return 'reject'
    if buried_pikis >= BURIED_PIKMIN_CAP_US:
        return 'reject'
    if bald_triangle or not might_bury or not sprout_mgr_available:
        return 'walk'
    return 'convert' if sprout_birth_ok else 'walk'


def wait_transition(health, is_start_walk, attack_start, needs_turn):
    """StateWait::exec transition table, miulinState.cpp:59-77.

    Dead is checked first, then attack, then turn, else walk. Returns None when
    no target was acquired (remain in Wait).
    """
    if not is_start_walk:
        return None
    if health <= 0:
        return 'dead'
    if attack_start:
        return 'attackstart'
    if needs_turn:
        return 'turn'
    return 'walk'


def lifecycle_flags(can_appear_day_end=False, has_no_info=False):
    """Registry flag contract, enemyInfo.cpp:88 and enemyInfo.h:29-40.

    Miulin carries EFlag_CanBeSpawned|2|EFlag_UseOwnID only: it is excluded from
    GeneralEnemyMgr::prepareDayendEnemies clearing (generalEnemyMgr.cpp:923-941)
    and its Piklopedia lost/defeated counters are tracked (zukan2D.cpp:2181 blinds
    the lost counter display only).
    """
    return {'can_be_spawned': True, 'uses_own_id': True,
            'can_appear_day_end': can_appear_day_end, 'has_no_info': has_no_info,
            'prepare_dayend_clears': can_appear_day_end,
            'piklopedia_tracks_stats': not has_no_info,
            'zukan_blinds_pikmin_lost': True}


def profile(parameters, events):
    general, proper = parameters[1], parameters[2]
    unknown = set(proper) - set(PROPER_PARM_KEYS)
    if unknown:
        raise ValueError(f'Unexpected Mamuta proper parameters: {sorted(unknown)}')
    for key, default in PROPER_PARM_DEFAULTS.items():
        if key not in proper:
            raise ValueError(f'Missing Mamuta proper parameter {key}')
    clips = sorted(events)
    if tuple(clips) != EXPECTED_CLIPS:
        raise ValueError(f'Unexpected Mamuta clip set: {clips}')
    for clip in clips:
        if ANIM_ID_BY_CLIP[clip] is None:
            raise ValueError(f'Unmapped Mamuta clip {clip}')
    return {'schema': 1, 'species': SPECIES, 'enemy_id': 54,
            'general': {name: general[key] for key, name in GENERAL_PARM_FIELDS.items()
                        if key in general},
            'proper_defaults': dict(PROPER_PARM_DEFAULTS),
            'proper_retail': {k: proper[k] for k in PROPER_PARM_KEYS},
            'clips': events,
            'attack_contract': {'kind': 'bury', 'piki_damage': PIKI_BURY_DAMAGE,
                                'navi_damage': NAVI_BURY_DAMAGE,
                                'vertical_band': BURY_VERTICAL_BAND,
                                'buried_cap_us': BURIED_PIKMIN_CAP_US},
            'implemented_delta': 'Source assets and reference semantics only; no native Mamuta behavior substitution.'}


def extract(iso, output, pose_limit=3):
    if type(pose_limit) is not int or not 2 <= pose_limit <= 8:
        raise ValueError('Pose limit must be 2..8')
    output.mkdir(parents=True, exist_ok=False)
    index = disc_files(iso)
    hashes = {}
    with iso.open('rb') as disc:
        def read(path):
            at, size = index[path]
            disc.seek(at)
            raw = disc.read(size)
            if len(raw) != size:
                raise ValueError('Truncated disc resource')
            hashes[path] = sha(raw)
            return raw
        model = archive_files(read(MODEL_PATH))['enemy.bmd']
        motions = archive_files(read(ANIM_PATH))
        params = archive_files(read(PARM_SOURCE))
    root = output / SPECIES
    root.mkdir()
    (root / 'enemy.bmd').write_bytes(model)
    names = joints(model)
    metadata = {}
    for name in METADATA_FILES:
        raw = params[PARM_PREFIX + name]
        (root / name).write_bytes(raw)
        metadata[name] = sha(raw)
    events = animation_events((root / 'enemyanimmgr.txt').read_text(encoding='shift_jis'))
    parameters = parameter_groups((root / 'enemyparm.txt').read_text(encoding='shift_jis'))
    result = profile(parameters, events)
    modelpath = root / 'enemy.bmd'
    clips = []
    for clip in sorted(events, key=lambda c: ANIM_ID_BY_CLIP[c]):
        raw = motions[clip]
        (root / clip).write_bytes(raw)
        entry = dict(file=clip, anim_id=ANIM_ID_BY_CLIP[clip], events=events[clip],
                     sha256=sha(raw), status='unsupported', poses=[])
        try:
            duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
            entry['source_frames'] = duration
            for i, frame in enumerate(sample_frames(duration, pose_limit)):
                _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                name = Path(clip).stem + f'_{i:02}.mod'
                matrices = draw_matrices(blocks(model), pose)
                decoded = decode(model, True, bake_rigid=True, draw_matrices=matrices)
                conversion = write_model(decoded, root / name, 'enemy.bmd')
                conversion['weighted_pose_baked'] = True
                conversion['source'] = 'enemy.bmd'
                conversion['output'] = name
                (root / Path(name).with_suffix('.json')).write_text(json.dumps(conversion, indent=2) + '\n')
                entry['poses'].append(dict(file=name, frame=frame, sha256=sha((root / name).read_bytes()),
                                           conversion=conversion))
            entry['status'] = 'converted'
        except ValueError as error:
            entry['unsupported_reason'] = str(error)
        clips.append(entry)
    tex = blocks(model)['TEX1']
    result.update(model_sha256=sha(model), joints=names, embedded_texture_count=u16(tex, 8),
                  metadata_sha256=metadata, animation_family=SPECIES, clips=clips,
                  runtime_status='unsupported; source assets only')
    result['source_sha256'] = hashes
    result['limitations'] = [
        'Sampled rigid poses with approximate materials; no skeletal playback or event execution.',
        'Bury conversion, flower sprouting and flick receivers are documented references, not native behavior.',
        'Collision and parameter text preserved; no mesh-bound guesses.',
        'ShijimiChou side birth, territory AI and save/floor lifecycle remain unimplemented natively.']
    (output / 'mamuta.json').write_text(json.dumps(result, indent=2) + '\n')
    (output / 'p2-mamuta.txt').write_text(TEXT)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=3)
    args = parser.parse_args()
    result = extract(args.iso, args.output, args.pose_limit)
    print(json.dumps({'joints': len(result['joints']), 'clips': len(result['clips']),
                      'converted': sum(c['status'] == 'converted' for c in result['clips'])}))
