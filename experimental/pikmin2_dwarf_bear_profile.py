"""Retail Dwarf Bulbear (KumaKochappy) reference profile; no native install.

Extraction/profile only. Source contract established against the local decomp
(native/pikmin2-research) and a local US GPVE01 revision 0 disc. KumaKochappy is
a concrete spawnable identity (EnemyID 76) with its own FSM, model and
parameters; it shares the Kochappy animation archive and collision file via
enemyInfo resource aliases. Unlike the dwarf bulborbs (KochappyBase line) it is
not a texture variant and carries no breadbug-mimic relation in source.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_snow_policy import animation_events, parameter_groups

SPECIES = 'KumaKochappy'
SOURCE_ID = 76
DISPLAY_NAME = 'Dwarf Bulbear'
PARENT_SPECIES = 'KumaChappy'
PARENT_ID = 35
PARM_PATH = 'kumakochappy/enemyparm.txt'
STONE_PATH = 'kumakochappy/enemystoneinfo.txt'
ANIMATION_PATH = 'kochappy/enemyanimmgr.txt'
COLLISION_PATH = 'kochappy/enemycoll.txt'
MODEL_PATH = 'enemy/data/KumaKochappy/model.szs'
ANIM_PATH = 'enemy/data/Kochappy/anim.szs'
CLIPS = {'attack.bca', 'dead.bca', 'flick.bca', 'move1.bca', 'type1.bca',
         'type5.bca', 'wait1.bca', 'waitact1.bca', 'waitact2.bca'}
GROUPS = ('creature', 'general', 'proper')
FIELDS = {
    'health': ('fp00', 'mHealth', 'health'),
    'move_speed': ('fp06', 'mMoveSpeed', 'world_units_per_second'),
    'turn_gain': ('fp08', 'mTurnSpeed', 'fraction_per_update'),
    'maximum_turn': ('fp28', 'mMaxTurnAngle', 'degrees_per_update'),
    'attack_entry_range': ('fp20', 'mMaxAttackRange', 'world_units'),
    'attack_entry_half_angle': ('fp21', 'mMaxAttackAngle', 'degrees'),
    'attack_hit_radius': ('fp22', 'mAttackRadius', 'world_units'),
    'attack_hit_half_angle': ('fp23', 'mAttackHitAngle', 'degrees'),
    'attack_damage': ('fp24', 'mAttackDamage', 'health'),
    'home_radius': ('fp10', 'mHomeRadius', 'world_units'),
    'search_height': ('fp26', 'mSearchHeight', 'world_units'),
    'sight_radius': ('fp12', 'mSightRadius', 'world_units'),
    'view_angle': ('fp13', 'mViewAngle', 'degrees'),
    'parent_search_distance': ('fp14', 'mSearchDistance', 'world_units'),
    'parent_search_angle': ('fp15', 'mSearchAngle', 'degrees'),
    'shake_chance': ('fp16', 'mShakeChance', 'probability'),
    'shake_knockback': ('fp17', 'mShakeKnockback', 'world_units'),
    'shake_damage': ('fp18', 'mShakeDamage', 'health'),
    'shake_range': ('fp19', 'mShakeRange', 'world_units'),
    'purple_stun_duration': ('fp38', 'mPurplePikiStunDuration', 'seconds'),
}
PROPER_FIELDS = {'white_pikmin_damage': ('fp01', 'mPoisonDamage', 'health')}
# Retail general fp00/fp06/fp38 and proper fp01.
EXPECTED = (500, 60, 5)
EXPECTED_PROPER = 500
# Header defaults that differ from retail (EnemyParmsBase.h / KumaKochappy.h).
HEADER_DEFAULTS = {'health': 100.0, 'move_speed': 80.0, 'turn_gain': 0.1,
                   'attack_entry_range': 70.0, 'attack_entry_half_angle': 15.0,
                   'attack_hit_radius': 70.0, 'attack_hit_half_angle': 15.0,
                   'attack_damage': 10.0, 'home_radius': 15.0, 'search_height': 50.0, 'sight_radius': 200.0,
                   'view_angle': 90.0, 'parent_search_distance': 200.0,
                   'parent_search_angle': 120.0, 'shake_knockback': 300.0,
                   'shake_damage': 0.0, 'shake_range': 120.0, 'shake_chance': 1.0,
                   'purple_stun_duration': 10.0}
HEADER_PROPER_DEFAULT = 300.0  # KumaKochappy::ProperParms mPoisonDamage


def profile(parameters):
    """Strict revision-bounded KumaKochappy profile retaining every raw field."""
    if set(parameters) != set(GROUPS) or any(not isinstance(g, dict) or not g for g in parameters.values()):
        raise ValueError('Expected three nonempty parameter groups')
    if any(not isinstance(k, str) or type(v) not in (float, int) or not math.isfinite(v)
           for g in parameters.values() for k, v in g.items()):
        raise ValueError('Invalid/nonfinite parameter')
    general, proper = parameters['general'], parameters['proper']
    try:
        values = {name: general[key] for name, (key, _, _) in FIELDS.items()}
        poison = proper[PROPER_FIELDS['white_pikmin_damage'][0]]
    except KeyError as error:
        raise ValueError('Missing required parameter') from error
    if (values['health'], values['move_speed'], values['purple_stun_duration']) != EXPECTED:
        raise ValueError('Unsupported retail KumaKochappy profile')
    if poison != EXPECTED_PROPER or set(proper) != {'fp01'}:
        raise ValueError('Unsupported retail KumaKochappy proper parameters')
    result = {'source_id': SOURCE_ID, 'display_name': DISPLAY_NAME, 'source_species': SPECIES,
              'base_class': 'Game::EnemyBase', 'source_fsm': 'KumaKochappy::FSM',
              'parent_species': PARENT_SPECIES, 'parent_source_id': PARENT_ID,
              'own_model': 'KumaKochappy', 'shared_animation': 'Kochappy',
              'shared_collision': 'Kochappy', 'texture_path': None, 'texture_slot': None,
              'parameters': {name: dict(parameters[name]) for name in GROUPS},
              'profile': {name: {'value': value, 'source_group': 'general', 'source_key': FIELDS[name][0],
                                 'source_member': FIELDS[name][1], 'unit': FIELDS[name][2],
                                 'header_default': HEADER_DEFAULTS.get(name, value)}
                          for name, value in values.items()}}
    result['profile']['white_pikmin_damage'] = {
        'value': poison, 'source_group': 'proper',
        'source_key': PROPER_FIELDS['white_pikmin_damage'][0],
        'source_member': PROPER_FIELDS['white_pikmin_damage'][1],
        'unit': 'health', 'header_default': HEADER_PROPER_DEFAULT}
    return result


def audit_source(research):
    """Verify resource/class/parameter mappings against the local source revision."""
    hashes = {}

    def read(path):
        data = (research / path).read_bytes()
        hashes[path] = hashlib.sha256(data).hexdigest()
        return data.decode('utf-8')

    ids = read('include/Game/enemyInfo.h')
    info = read('src/plugProjectYamashitaU/enemyInfo.cpp')
    for species, identity in ((SPECIES, SOURCE_ID), (PARENT_SPECIES, PARENT_ID)):
        if not re.search(r'EnemyID_' + species + r'\s*=\s*' + str(identity) + r'\s*,', ids):
            raise ValueError('Enemy source ID mismatch')
    entry = re.search(r'\{"' + SPECIES + r'"[^}]*\}', info)
    if not entry or '"Kochappy"' not in entry[0] or 'EFlag_CanBeSpawned' not in entry[0]:
        raise ValueError('Missing shared resource source entry')
    header = read('include/Game/Entities/KumaKochappy.h')
    for token in ('struct FSM : public EnemyStateMachine', 'KUMAKOCHAPPY_StateCount',
                  'struct ProperParms', 'ChappyRelation'):
        if token not in header:
            raise ValueError('KumaKochappy class contract changed')
    cpp = read('src/plugProjectNishimuraU/KumaKochappy.cpp')
    for token in ('setFSM(new FSM)', 'setNearestParent', 'ChappyRelation', 'getEnemyMgr(EnemyTypeID::EnemyID_KumaChappy)'):
        if token not in cpp:
            raise ValueError('KumaKochappy behavior contract changed')
    state = read('src/plugProjectNishimuraU/KumaKochappyState.cpp')
    for token in ('StateWalkPath', 'setTargetParentPosition', 'KUMAKOCHAPPYANIM_'):
        if token not in state:
            raise ValueError('KumaKochappy state contract changed')
    mgr = read('src/plugProjectNishimuraU/KumaKochappyMgr.cpp')
    if 'init(new Parms)' not in mgr:
        raise ValueError('KumaKochappy parameter contract changed')
    general_mgr = read('src/plugProjectYamashitaU/generalEnemyMgr.cpp')
    if 'EnemyID_KumaKochappy' not in general_mgr or 'KumaKochappy::Mgr' not in general_mgr:
        raise ValueError('Missing spawnable manager registration')
    parms = read('include/Game/EnemyParmsBase.h')
    for key, member, _ in list(FIELDS.values()) + list(PROPER_FIELDS.values()):
        if not re.search(re.escape(member) + r"\(this, '" + key + r"'", parms + header):
            raise ValueError('Parameter source member mismatch: ' + member)
    read('src/plugProjectYamashitaU/enemyMgrBase.cpp')
    read('include/Game/ChappyRelation.h')
    read('include/Game/Entities/KumaChappy.h')
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
        raw_parm = parm_archive[PARM_PATH]
        hashes[PARM_PATH] = hashlib.sha256(raw_parm).hexdigest()
        parameters = parameter_groups(raw_parm.decode('shift_jis'))
        animation = parm_archive[ANIMATION_PATH]
        hashes[ANIMATION_PATH] = hashlib.sha256(animation).hexdigest()
        collision = parm_archive[COLLISION_PATH]
        hashes[COLLISION_PATH] = hashlib.sha256(collision).hexdigest()
        stone = parm_archive[STONE_PATH]
        hashes[STONE_PATH] = hashlib.sha256(stone).hexdigest()
        events = animation_events(animation.decode('shift_jis'))
        models = archive_files(read(MODEL_PATH))
        motions = archive_files(read(ANIM_PATH))
        if set(events) != CLIPS or set(events) != set(motions):
            raise ValueError('Source animation files and event catalog disagree')
    model = models['enemy.bmd']
    # KumaKochappy has no texture replacement: its model.szs embeds the real TEX1.
    # Keep all exported content private; these are source assets, not a runtime bank.
    output.mkdir(parents=True, exist_ok=False)
    (output / 'source-animation').mkdir()
    (output / 'dwarf-bear.bmd').write_bytes(model)
    for name, data in motions.items():
        (output / 'source-animation' / name).write_bytes(data)
    result = {'schema': 1, 'family': 'KumaKochappy', 'species': SPECIES,
              'source_scope': 'US GPVE01 revision 0 audited local assets',
              'variant': profile(dict(zip(GROUPS, parameters))),
              'source_sha256': hashes, 'research_sha256': source_hashes,
              'shared_animation_events': events,
              'shared_animation_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in motions.items()},
              'exported_model_sha256': hashlib.sha256(model).hexdigest(),
              'cost': {'exported_model_bytes': len(model),
                       'source_animation_bytes': sum(map(len, motions.values())),
                       'sampled_pose_count': 0, 'native_runtime_cost': 'unmeasured'},
              'runtime_status': 'Reference extraction only; no native actors, visual bank, parameter hooks or placements installed.',
              'placement_contract': 'Separate arena generator binding and full effective XYZ; no source yaw applied here.',
              'unimplemented': ['KumaKochappy native visual/profile binding',
                                'parent-following (ChappyRelation) behavior',
                                'source event timing/FSM parity',
                                'natural arena lifecycle and corpse delivery']}
    (output / 'dwarf-bear-profile.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('iso', 'research', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = extract(args.iso, args.research, args.output)
    print(json.dumps({'species': result['species'], 'variant': result['variant']['profile'],
                      'cost': result['cost']}, indent=2))
