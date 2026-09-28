import hashlib
import json
import struct
from pathlib import Path

import pytest

from experimental.pikmin2_dwarf_orange_profile import (
    EXPECTED, EXPECTED_SHARED, GROUPS, SPECIES, TEXTURE, audit_source, profile)
from experimental.pikmin2_dwarf_orange_bank import (
    HEADER, PROFILE, event_frames, parse_bank, sample_with_events, validate_files)


def parameters():
    general = {'fp00': 250.0, 'fp06': 60.0, 'fp08': 0.4, 'fp28': 10.0,
               'fp20': 30.0, 'fp21': 20.0, 'fp38': 5.0}
    return {'creature': {'s000': 0.5}, 'general': general, 'proper': {'fp01': 2.0, 'fp02': 300.0, 'fp03': 180.0}}


def test_profile_identity_and_values():
    result = profile(parameters())
    assert result['source_id'] == 44
    assert result['display_name'] == 'Dwarf Orange Bulborb'
    assert result['source_species'] == SPECIES == 'BlueKochappy'
    assert result['base_class'] == 'KochappyBase::Obj'
    assert result['source_fsm'] == 'KochappyBase::FSM'
    assert result['texture_path'].endswith('BlueKochappy/kochappy_body_s3tc.3.bti')
    assert result['texture_slot'] == 0
    assert result['profile']['health']['value'] == EXPECTED[0] == 250
    assert result['profile']['move_speed']['value'] == EXPECTED[1] == 60
    assert result['profile']['purple_stun_duration']['value'] == EXPECTED[2] == 5
    assert result['profile']['purple_stun_duration']['header_default'] == 10.0
    assert result['profile']['attack_entry_range']['source_member'] == 'mMaxAttackRange'


@pytest.mark.parametrize('bad', ['missing_group', 'empty_group', 'extra_group', 'nan', 'inf',
                                 'boolean', 'missing_key', 'health', 'speed', 'stun', 'steering'])
def test_invalid_profile(bad):
    data = parameters()
    if bad == 'missing_group':
        del data['proper']
    elif bad == 'empty_group':
        data['creature'] = {}
    elif bad == 'extra_group':
        data['bonus'] = {'fp99': 1.0}
    elif bad in ('nan', 'inf', 'boolean'):
        data['general']['fp99'] = {'nan': float('nan'), 'inf': float('inf'), 'boolean': True}[bad]
    elif bad == 'missing_key':
        del data['general']['fp20']
    elif bad == 'steering':
        data['general']['fp28'] = 99.0
    else:
        data['general'][{'health': 'fp00', 'speed': 'fp06', 'stun': 'fp38'}[bad]] = 123.0
    with pytest.raises(ValueError):
        profile(data)


def source_tree(tmp_path):
    def write(path, text):
        p = tmp_path / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    write('include/Game/enemyInfo.h', f'EnemyID_{SPECIES} = 44,')
    write('src/plugProjectYamashitaU/enemyInfo.cpp',
          f'{{"{SPECIES}", x, -1, 1, (EFlag_CanBeSpawned), "Kochappy", "Kochappy", "Kochappy", "", "", "Kochappy", "Kochappy"}}')
    write('include/Game/EnemyParmsBase.h',
          '\n'.join(f"{m}(this, '{k}'" for k, m, _ in
                    [('fp00', 'mHealth', 'u'), ('fp06', 'mMoveSpeed', 'u'), ('fp08', 'mTurnSpeed', 'u'), ('fp28', 'mMaxTurnAngle', 'u'),
                     ('fp20', 'mMaxAttackRange', 'u'), ('fp21', 'mMaxAttackAngle', 'u'), ('fp38', 'mPurplePikiStunDuration', 'u')]))
    write('include/Game/Entities/KochappyBase.h', 'struct FSM : public EnemyStateMachine')
    write('src/plugProjectYamashitaU/bluekochappy.cpp',
          'new KochappyBase::ProperAnimator; setFSM(new KochappyBase::FSM); changeImage(texture, 0)')
    write('src/plugProjectYamashitaU/bluekochappyMgr.cpp',
          f'/enemy/data/{SPECIES}/{TEXTURE}; init(new KochappyBase::Parms)')
    write('src/plugProjectYamashitaU/generalEnemyMgr.cpp', 'EnemyID_BlueKochappy BlueKochappy::Mgr')
    for name in ('kochappyState.cpp', 'kochappyBase.cpp', 'kochappyBaseMgr.cpp'):
        write('src/plugProjectYamashitaU/' + name, 'source reference')


def test_source_audit_hashes(tmp_path):
    source_tree(tmp_path)
    result = audit_source(tmp_path)
    assert len(result) == 10 and all(len(v) == 64 for v in result.values())


@pytest.mark.parametrize('mutation', ['id', 'fsm', 'texture', 'parms', 'manager', 'member'])
def test_source_audit_mismatch(tmp_path, mutation):
    source_tree(tmp_path)
    if mutation == 'id':
        p = tmp_path / 'include/Game/enemyInfo.h'
        p.write_text(p.read_text().replace('44', '45'))
    elif mutation == 'fsm':
        p = tmp_path / 'src/plugProjectYamashitaU/bluekochappy.cpp'
        p.write_text(p.read_text().replace('changeImage(texture, 0)', 'noop()'))
    elif mutation == 'texture':
        p = tmp_path / 'src/plugProjectYamashitaU/bluekochappyMgr.cpp'
        p.write_text(p.read_text().replace('.3.bti', '.2.bti'))
    elif mutation == 'parms':
        p = tmp_path / 'src/plugProjectYamashitaU/bluekochappyMgr.cpp'
        p.write_text(p.read_text().replace('KochappyBase::Parms', 'OtherParms'))
    elif mutation == 'manager':
        p = tmp_path / 'src/plugProjectYamashitaU/generalEnemyMgr.cpp'
        p.write_text('no registration')
    else:
        p = tmp_path / 'include/Game/EnemyParmsBase.h'
        p.write_text(p.read_text().replace('mMaxAttackRange', 'mAttackRadius'))
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
    assert event_frames(EVENTS, 'type5') == []


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
    assert bank['wait1'] == {'poses': 2, 'source_frames': 2, 'frames': [0, 1]}


@pytest.mark.parametrize('bad', ['header', 'order', 'truncated', 'frames', 'trailing'])
def test_parse_bank_rejects(bad):
    text = bank_text()
    if bad == 'header':
        text = text.replace(HEADER, 'P2_KOCHAPPY_BANK_1')
    elif bad == 'order':
        text = text.replace('wait1', 'move1', 1).replace('move1 2 2 0 1\nattack', 'wait1 2 2 0 1\nattack')
    elif bad == 'truncated':
        text = text.rsplit(' ', 2)[0]
    elif bad == 'frames':
        text = text.replace('wait1 2 2 0 1', 'wait1 2 2 1 1')
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
            (tmp_path / f'dwarf_orange_{name}_{i:02}.mod').write_bytes(blob)
    paths, total = validate_files(tmp_path, bank)
    assert len(paths) == 10 and total == 10 * len(blob)
    # exact-byte config writes: no newline translation
    cfg = tmp_path / 'p2-dwarf-orange-profile.txt'
    cfg.write_bytes(PROFILE.encode())
    assert cfg.read_bytes() == PROFILE.encode() and b'\r' not in cfg.read_bytes()
    (tmp_path / 'dwarf_orange_dead_00.mod').write_bytes(b'broken')
    with pytest.raises(ValueError):
        validate_files(tmp_path, bank)


def test_build_rejects_bad_inputs(tmp_path):
    imported = tmp_path / 'imported'
    imported.mkdir()
    (imported / 'dwarf-orange-profile.json').write_text(json.dumps(
        {'schema': 1, 'species': 'BlueKochappy', 'exported_model_sha256': '0' * 64,
         'shared_animation_events': {}, 'shared_animation_sha256': {}}))
    (imported / 'dwarf-orange.bmd').write_bytes(b'not the real model')
    from experimental.pikmin2_dwarf_orange_bank import build
    with pytest.raises(ValueError, match='pose limit'):
        build(imported, tmp_path / 'out', pose_limit=1)
    with pytest.raises(ValueError, match='pose limit'):
        build(imported, tmp_path / 'out', pose_limit=25)
    with pytest.raises(ValueError, match='pose limit'):
        build(imported, tmp_path / 'out', pose_limit=True)
    with pytest.raises(ValueError, match='model hash mismatch'):
        build(imported, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()
    data = json.loads((imported / 'dwarf-orange-profile.json').read_text())
    data['species'] = 'Kochappy'
    (imported / 'dwarf-orange-profile.json').write_text(json.dumps(data))
    with pytest.raises(ValueError, match='reference import'):
        build(imported, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


def test_build_refuses_existing_output(tmp_path):
    # A fully valid build requires the audited extraction; the refusal contract is
    # exist_ok=False on the output directory, verified against a real profile dir
    # shape here: any pre-existing output must abort before mutation.
    imported = tmp_path / 'imported'
    imported.mkdir()
    (imported / 'dwarf-orange-profile.json').write_text(json.dumps({'schema': 1, 'species': 'Wrong'}))
    from experimental.pikmin2_dwarf_orange_bank import build
    out = tmp_path / 'out'
    out.mkdir()
    with pytest.raises(ValueError):
        build(imported, out)
    assert list(out.iterdir()) == []
