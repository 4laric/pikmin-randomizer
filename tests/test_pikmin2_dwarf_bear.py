import hashlib
import json
import struct
from pathlib import Path

import pytest

from experimental.pikmin2_dwarf_bear_profile import (
    EXPECTED, EXPECTED_PROPER, FIELDS, GROUPS, PARENT_ID, PARENT_SPECIES, SPECIES,
    audit_source, profile)
from experimental.pikmin2_dwarf_bear_bank import (
    HEADER, PROFILE, event_frames, parse_bank, sample_with_events, validate_files)


def parameters():
    general = {'fp00': 500.0, 'fp06': 60.0, 'fp08': 0.4, 'fp28': 10.0,
               'fp20': 35.0, 'fp21': 25.0, 'fp22': 38.0, 'fp23': 25.0, 'fp24': 10.0,
               'fp10': 80.0, 'fp26': 100.0, 'fp12': 150.0, 'fp13': 180.0,
               'fp14': 400.0, 'fp15': 180.0, 'fp16': 1.0, 'fp17': 50.0,
               'fp18': 1.0, 'fp19': 17.0, 'fp38': 5.0}
    return {'creature': {'s000': 0.5}, 'general': general, 'proper': {'fp01': 500.0}}


def test_profile_identity_and_values():
    result = profile(parameters())
    assert result['source_id'] == 76
    assert result['display_name'] == 'Dwarf Bulbear'
    assert result['source_species'] == SPECIES == 'KumaKochappy'
    assert result['base_class'] == 'Game::EnemyBase'
    assert result['source_fsm'] == 'KumaKochappy::FSM'
    assert (result['parent_species'], result['parent_source_id']) == (PARENT_SPECIES, PARENT_ID) == ('KumaChappy', 35)
    assert result['own_model'] == 'KumaKochappy'
    assert result['shared_animation'] == 'Kochappy'
    assert result['texture_path'] is None  # no breadbug-mimic texture swap
    assert result['profile']['health']['value'] == EXPECTED[0] == 500
    assert result['profile']['move_speed']['value'] == EXPECTED[1] == 60
    assert result['profile']['purple_stun_duration']['value'] == EXPECTED[2] == 5
    assert result['profile']['white_pikmin_damage']['value'] == EXPECTED_PROPER == 500
    assert result['profile']['white_pikmin_damage']['header_default'] == 300.0
    assert result['profile']['attack_entry_range']['value'] == 35.0
    assert result['profile']['parent_search_distance']['source_member'] == 'mSearchDistance'
    assert result['profile']['search_height']['source_member'] == 'mSearchHeight'


@pytest.mark.parametrize('bad', ['missing_group', 'empty_group', 'nan', 'boolean', 'missing_key',
                                 'health', 'speed', 'stun', 'poison', 'proper_extra'])
def test_invalid_profile(bad):
    data = parameters()
    if bad == 'missing_group':
        del data['proper']
    elif bad == 'empty_group':
        data['creature'] = {}
    elif bad in ('nan', 'boolean'):
        data['general']['fp99'] = float('nan') if bad == 'nan' else True
    elif bad == 'missing_key':
        del data['general']['fp26']
    elif bad == 'poison':
        data['proper']['fp01'] = 300.0
    elif bad == 'proper_extra':
        data['proper']['fp02'] = 1.0
    else:
        data['general'][{'health': 'fp00', 'speed': 'fp06', 'stun': 'fp38'}[bad]] = 123.0
    with pytest.raises(ValueError):
        profile(data)


def source_tree(tmp_path):
    def write(path, text):
        p = tmp_path / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    write('include/Game/enemyInfo.h', 'EnemyID_KumaKochappy = 76,\nEnemyID_KumaChappy = 35,')
    write('src/plugProjectYamashitaU/enemyInfo.cpp',
          '{"KumaKochappy", x, -1, 1, (EFlag_CanBeSpawned), "", "Kochappy", "Kochappy", "", "", "Kochappy", ""}')
    write('include/Game/Entities/KumaKochappy.h',
          'struct FSM : public EnemyStateMachine; KUMAKOCHAPPY_StateCount; struct ProperParms; ChappyRelation* mParentRelation; '
          + ' '.join(f"{m}(this, '{k}'" for k, m, _ in [('fp01', 'mPoisonDamage', 'health')]))
    write('src/plugProjectNishimuraU/KumaKochappy.cpp',
          'setFSM(new FSM); setNearestParent(); ChappyRelation; getEnemyMgr(EnemyTypeID::EnemyID_KumaChappy)')
    write('src/plugProjectNishimuraU/KumaKochappyState.cpp',
          'StateWalkPath; setTargetParentPosition(); KUMAKOCHAPPYANIM_Move')
    write('src/plugProjectNishimuraU/KumaKochappyMgr.cpp', 'init(new Parms)')
    write('src/plugProjectYamashitaU/generalEnemyMgr.cpp', 'EnemyID_KumaKochappy KumaKochappy::Mgr')
    write('include/Game/EnemyParmsBase.h',
          '\n'.join(f"{m}(this, '{k}'" for k, m, _ in
                    [('fp00', 'mHealth', 'u'), ('fp06', 'mMoveSpeed', 'u'), ('fp08', 'mTurnSpeed', 'u'), ('fp28', 'mMaxTurnAngle', 'u'),
                     ('fp20', 'mMaxAttackRange', 'u'), ('fp21', 'mMaxAttackAngle', 'u'), ('fp22', 'mAttackRadius', 'u'),
                     ('fp23', 'mAttackHitAngle', 'u'), ('fp24', 'mAttackDamage', 'u'), ('fp10', 'mHomeRadius', 'u'),
                     ('fp26', 'mSearchHeight', 'u'), ('fp12', 'mSightRadius', 'u'), ('fp13', 'mViewAngle', 'u'),
                     ('fp14', 'mSearchDistance', 'u'), ('fp15', 'mSearchAngle', 'u'), ('fp16', 'mShakeChance', 'u'),
                     ('fp17', 'mShakeKnockback', 'u'), ('fp18', 'mShakeDamage', 'u'), ('fp19', 'mShakeRange', 'u'),
                     ('fp38', 'mPurplePikiStunDuration', 'u')]))
    write('src/plugProjectYamashitaU/enemyMgrBase.cpp', 'source reference')
    write('include/Game/ChappyRelation.h', 'source reference')
    write('include/Game/Entities/KumaChappy.h', 'source reference')


def test_source_audit_hashes(tmp_path):
    source_tree(tmp_path)
    result = audit_source(tmp_path)
    assert len(result) == 11 and all(len(v) == 64 for v in result.values())


@pytest.mark.parametrize('mutation', ['id', 'parent_id', 'fsm', 'relation', 'state', 'parms', 'manager', 'member'])
def test_source_audit_mismatch(tmp_path, mutation):
    source_tree(tmp_path)
    if mutation == 'id':
        p = tmp_path / 'include/Game/enemyInfo.h'
        p.write_text(p.read_text().replace('76', '44'))
    elif mutation == 'parent_id':
        p = tmp_path / 'include/Game/enemyInfo.h'
        p.write_text(p.read_text().replace('35', '36'))
    elif mutation == 'fsm':
        p = tmp_path / 'src/plugProjectNishimuraU/KumaKochappy.cpp'
        p.write_text(p.read_text().replace('setFSM(new FSM)', 'noop()'))
    elif mutation == 'relation':
        p = tmp_path / 'src/plugProjectNishimuraU/KumaKochappy.cpp'
        p.write_text(p.read_text().replace('setNearestParent', 'noParent'))
    elif mutation == 'state':
        p = tmp_path / 'src/plugProjectNishimuraU/KumaKochappyState.cpp'
        p.write_text('no states')
    elif mutation == 'parms':
        p = tmp_path / 'src/plugProjectNishimuraU/KumaKochappyMgr.cpp'
        p.write_text('init(new OtherParms)')
    elif mutation == 'manager':
        p = tmp_path / 'src/plugProjectYamashitaU/generalEnemyMgr.cpp'
        p.write_text('no registration')
    else:
        p = tmp_path / 'include/Game/EnemyParmsBase.h'
        p.write_text(p.read_text().replace('mSearchDistance', 'mSearchDist'))
    with pytest.raises(ValueError):
        audit_source(tmp_path)


EVENTS = {'attack.bca': [{'frame': 8, 'type': 2}, {'frame': 88, 'type': 3}],
          'flick.bca': [{'frame': 31, 'type': 2}],
          'move1.bca': [{'frame': 10, 'type': 0}, {'frame': 39, 'type': 1}],
          'wait1.bca': [{'frame': 10, 'type': 0}, {'frame': 60, 'type': 1}, {'frame': 61, 'type': 2}],
          'dead.bca': []}


def test_event_frames_lookup():
    assert event_frames(EVENTS, 'attack') == [8, 88]
    assert event_frames(EVENTS, 'dead') == []


def test_sample_preserves_events_and_bounds():
    for clip, duration in [('wait1', 75), ('move1', 55), ('attack', 90), ('dead', 90), ('flick', 80)]:
        frames = sample_with_events(duration, event_frames(EVENTS, clip), 12)
        assert frames[0] == 0 and frames[-1] == duration - 1
        assert all(a < b for a, b in zip(frames, frames[1:]))
        assert set(event_frames(EVENTS, clip)) <= set(frames)
        assert len(frames) <= 24
    with pytest.raises(ValueError):
        sample_with_events(100, list(range(100)), 2)


def bank_text():
    return HEADER + '\n' + ''.join(f'{n} 2 2 0 1\n' for n in ('wait1', 'move1', 'attack', 'dead', 'flick'))


def test_parse_bank_roundtrip_and_order():
    bank = parse_bank(bank_text())
    assert list(bank) == ['wait1', 'move1', 'attack', 'dead', 'flick']
    assert bank['flick'] == {'poses': 2, 'source_frames': 2, 'frames': [0, 1]}


@pytest.mark.parametrize('bad', ['header', 'truncated', 'frames', 'trailing'])
def test_parse_bank_rejects(bad):
    text = bank_text()
    if bad == 'header':
        text = text.replace(HEADER, 'P2_DWARF_ORANGE_BANK_1')
    elif bad == 'truncated':
        text = text.rsplit(' ', 2)[0]
    elif bad == 'frames':
        text = text.replace('dead 2 2 0 1', 'dead 2 2 1 0')
    else:
        text += 'extra\n'
    with pytest.raises(ValueError):
        parse_bank(text)


def mod_blob():
    return b''.join(struct.pack('>II', tag, 0) for tag in (32, 34, 48, 65535))


def test_validate_files_and_exact_byte_writes(tmp_path):
    bank = parse_bank(bank_text())
    blob = mod_blob()
    for name in bank:
        for i in range(2):
            (tmp_path / f'dwarf_bear_{name}_{i:02}.mod').write_bytes(blob)
    paths, total = validate_files(tmp_path, bank)
    assert len(paths) == 10 and total == 10 * len(blob)
    cfg = tmp_path / 'p2-dwarf-bear-profile.txt'
    cfg.write_bytes(PROFILE.encode())
    assert cfg.read_bytes() == PROFILE.encode() and b'\r' not in cfg.read_bytes()
    other = mod_blob() + b'\x00'
    (tmp_path / 'dwarf_bear_attack_01.mod').write_bytes(other)
    with pytest.raises(ValueError):
        validate_files(tmp_path, bank)


def test_build_rejects_bad_inputs(tmp_path):
    imported = tmp_path / 'imported'
    imported.mkdir()
    (imported / 'dwarf-bear-profile.json').write_text(json.dumps(
        {'schema': 1, 'species': 'KumaKochappy', 'exported_model_sha256': '0' * 64,
         'shared_animation_events': {}, 'shared_animation_sha256': {}}))
    (imported / 'dwarf-bear.bmd').write_bytes(b'not the real model')
    from experimental.pikmin2_dwarf_bear_bank import build
    with pytest.raises(ValueError, match='pose limit'):
        build(imported, tmp_path / 'out', pose_limit=0)
    with pytest.raises(ValueError, match='model hash mismatch'):
        build(imported, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()
    data = json.loads((imported / 'dwarf-bear-profile.json').read_text())
    data['species'] = 'BlueKochappy'
    (imported / 'dwarf-bear-profile.json').write_text(json.dumps(data))
    with pytest.raises(ValueError, match='reference import'):
        build(imported, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


def test_build_refuses_existing_output(tmp_path):
    imported = tmp_path / 'imported'
    imported.mkdir()
    (imported / 'dwarf-bear-profile.json').write_text(json.dumps({'schema': 1, 'species': 'Wrong'}))
    from experimental.pikmin2_dwarf_bear_bank import build
    out = tmp_path / 'out'
    out.mkdir()
    with pytest.raises(ValueError):
        build(imported, out)
    assert list(out.iterdir()) == []
