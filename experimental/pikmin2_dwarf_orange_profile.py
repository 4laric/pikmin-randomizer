"""Retail Dwarf Orange Bulborb (BlueKochappy) reference profile; no native install.

Extraction/profile only. Source contract established against the local decomp
(native/pikmin2-research) and a local US GPVE01 revision 0 disc. BlueKochappy is
a concrete spawnable identity (EnemyID 44) sharing the Kochappy model and
animations and swapping texture image zero; it is not a separate base class.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_enemy import replace_texture_zero
from experimental.pikmin2_kochappy_profile import FIELDS, GROUPS
from experimental.pikmin2_snow_policy import animation_events, parameter_groups

SPECIES = 'BlueKochappy'
SOURCE_ID = 44
DISPLAY_NAME = 'Dwarf Orange Bulborb'
TEXTURE = 'kochappy_body_s3tc.3.bti'
TEXTURE_PATH = f'enemy/data/{SPECIES}/{TEXTURE}'
PARM_PATH = 'bluekochappy/enemyparm.txt'
ANIMATION_PATH = 'kochappy/enemyanimmgr.txt'
COLLISION_PATH = 'kochappy/enemycoll.txt'
MODEL_PATH = 'enemy/data/Kochappy/model.szs'
ANIM_PATH = 'enemy/data/Kochappy/anim.szs'
CLIPS = {'attack.bca', 'dead.bca', 'flick.bca', 'move1.bca', 'type1.bca',
         'type5.bca', 'wait1.bca', 'waitact1.bca', 'waitact2.bca'}
# Retail general fp00/fp06/fp38 (health, move speed, purple stun seconds).
EXPECTED = (250, 60, 5)
# Shared steering/attack profile: fp08/fp28/fp20/fp21.
EXPECTED_SHARED = (0.4, 10, 30, 20)
# Header defaults that differ from retail (EnemyParmsBase.h / KochappyBase.h).
HEADER_DEFAULTS = {'health': 100.0, 'move_speed': 80.0, 'purple_stun_duration': 10.0}


def profile(parameters):
    """Strict revision-bounded BlueKochappy profile retaining every raw field."""
    if set(parameters) != set(GROUPS) or any(not isinstance(g, dict) or not g for g in parameters.values()):
        raise ValueError('Expected three nonempty parameter groups')
    if any(not isinstance(k, str) or type(v) not in (float, int) or not math.isfinite(v)
           for g in parameters.values() for k, v in g.items()):
        raise ValueError('Invalid/nonfinite parameter')
    general = parameters['general']
    try:
        values = {name: general[key] for name, (key, _, _) in FIELDS.items()}
    except KeyError as error:
        raise ValueError('Missing required general parameter') from error
    if (values['health'], values['move_speed'], values['purple_stun_duration']) != EXPECTED:
        raise ValueError('Unsupported retail BlueKochappy profile')
    if (values['turn_gain'], values['maximum_turn'],
            values['attack_entry_range'], values['attack_entry_half_angle']) != EXPECTED_SHARED:
        raise ValueError('Unsupported shared steering/attack profile')
    return {'source_id': SOURCE_ID, 'display_name': DISPLAY_NAME, 'source_species': SPECIES,
            'base_class': 'KochappyBase::Obj', 'source_fsm': 'KochappyBase::FSM',
            'shared_model': 'Kochappy', 'shared_animation': 'Kochappy',
            'shared_collision': 'Kochappy', 'texture_path': TEXTURE_PATH, 'texture_slot': 0,
            'parameters': {name: dict(parameters[name]) for name in GROUPS},
            'profile': {name: {'value': value, 'source_group': 'general', 'source_key': FIELDS[name][0],
                               'source_member': FIELDS[name][1], 'unit': FIELDS[name][2],
                               'header_default': HEADER_DEFAULTS.get(name, value)}
                        for name, value in values.items()}}


def audit_source(research):
    """Verify resource/class/parameter mappings against the local source revision."""
    hashes = {}

    def read(path):
        data = (research / path).read_bytes()
        hashes[path] = hashlib.sha256(data).hexdigest()
        return data.decode('utf-8')

    ids = read('include/Game/enemyInfo.h')
    info = read('src/plugProjectYamashitaU/enemyInfo.cpp')
    parms = read('include/Game/EnemyParmsBase.h')
    base = read('include/Game/Entities/KochappyBase.h')
    if 'KochappyBase::FSM' not in base and 'struct FSM : public EnemyStateMachine' not in base:
        raise ValueError('Missing shared FSM declaration')
    if not re.search(r'EnemyID_' + SPECIES + r'\s*=\s*' + str(SOURCE_ID) + r'\s*,', ids):
        raise ValueError('Enemy source ID mismatch')
    entry = re.search(r'\{"' + SPECIES + r'"[^}]*\}', info)
    if not entry or '"Kochappy"' not in entry[0] or 'EFlag_CanBeSpawned' not in entry[0]:
        raise ValueError('Missing shared resource source entry')
    cpp = read('src/plugProjectYamashitaU/bluekochappy.cpp')
    mgr = read('src/plugProjectYamashitaU/bluekochappyMgr.cpp')
    if any(token not in cpp for token in
           ('new KochappyBase::ProperAnimator', 'setFSM(new KochappyBase::FSM)', 'changeImage(texture, 0)')):
        raise ValueError('Variant behavior/material contract changed')
    if f'/enemy/data/{SPECIES}/{TEXTURE}' not in mgr or 'init(new KochappyBase::Parms)' not in mgr:
        raise ValueError('Variant resource contract changed')
    general_mgr = read('src/plugProjectYamashitaU/generalEnemyMgr.cpp')
    if 'EnemyID_BlueKochappy' not in general_mgr or 'BlueKochappy::Mgr' not in general_mgr:
        raise ValueError('Missing spawnable manager registration')
    for key, member, _ in FIELDS.values():
        if not re.search(re.escape(member) + r"\(this, '" + key + r"'", parms):
            raise ValueError('Parameter source member mismatch: ' + member)
    read('src/plugProjectYamashitaU/kochappyState.cpp')
    read('src/plugProjectYamashitaU/kochappyBase.cpp')
    read('src/plugProjectYamashitaU/kochappyBaseMgr.cpp')
    return hashes


def extract(iso, research, output):
    source_hashes = audit_source(research)
    catalog = disc_files(iso)
    hashes = {}
    with iso.open('rb') as stream:
        def read(path):
            offset, size = catalog[path]
            stream.seek(offset)
            data = stream.read(size)
            if len(data) != size:
                raise ValueError('Truncated disc asset')
            hashes[path] = hashlib.sha256(data).hexdigest()
            return data
        parm_archive = archive_files(read('enemy/parm/enemyParms.szs'))
        parameters = parameter_groups(parm_archive[PARM_PATH].decode('shift_jis'))
        hashes[PARM_PATH] = hashlib.sha256(parm_archive[PARM_PATH]).hexdigest()
        animation = parm_archive[ANIMATION_PATH]
        hashes[ANIMATION_PATH] = hashlib.sha256(animation).hexdigest()
        collision = parm_archive[COLLISION_PATH]
        hashes[COLLISION_PATH] = hashlib.sha256(collision).hexdigest()
        events = animation_events(animation.decode('shift_jis'))
        models = archive_files(read(MODEL_PATH))
        motions = archive_files(read(ANIM_PATH))
        if set(events) != CLIPS or set(events) != set(motions):
            raise ValueError('Source animation files and event catalog disagree')
        texture = read(TEXTURE_PATH)
    orange_model = replace_texture_zero(models['enemy.bmd'], texture)
    # Keep all exported content private; these are source assets, not a runtime bank.
    output.mkdir(parents=True, exist_ok=False)
    (output / 'source-animation').mkdir()
    (output / 'dwarf-orange.bmd').write_bytes(orange_model)
    (output / 'dwarf-orange.bti').write_bytes(texture)
    for name, data in motions.items():
        (output / 'source-animation' / name).write_bytes(data)
    result = {'schema': 1, 'family': 'KochappyBase', 'species': SPECIES,
              'source_scope': 'US GPVE01 revision 0 audited local assets',
              'variant': profile(dict(zip(GROUPS, parameters))),
              'source_sha256': hashes, 'research_sha256': source_hashes,
              'shared_animation_events': events,
              'shared_animation_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in motions.items()},
              'exported_model_sha256': hashlib.sha256(orange_model).hexdigest(),
              'source_model_sha256': hashlib.sha256(models['enemy.bmd']).hexdigest(),
              'cost': {'exported_model_bytes': len(orange_model),
                       'source_animation_bytes': sum(map(len, motions.values())),
                       'sampled_pose_count': 0, 'native_runtime_cost': 'unmeasured'},
              'runtime_status': 'Reference extraction only; no native actors, visual bank, parameter hooks or placements installed.',
              'placement_contract': 'Separate arena generator binding and full effective XYZ; no source yaw applied here.',
              'unimplemented': ['BlueKochappy native visual/profile binding',
                                'source Purple stun reaction', 'source event timing/FSM parity',
                                'natural arena lifecycle and corpse delivery']}
    (output / 'dwarf-orange-profile.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('iso', 'research', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = extract(args.iso, args.research, args.output)
    print(json.dumps({'species': result['species'], 'variant': result['variant']['profile'],
                      'cost': result['cost']}, indent=2))
