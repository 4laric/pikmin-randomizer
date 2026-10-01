"""Queen (Empress Bulblax, 30) OWN staging (#256): bank grammar, disc parms,
carcass fallback, private-room replacement, and the installer wiring.

Unit tests only; they are never admission evidence."""
import json
from pathlib import Path

import pytest

from experimental import pikmin2_queen_stage as stage
from experimental.pikmin2_bulblax_assets import DISC_PARMS

QUEEN = {'dead': (140, [[60, 2], [73, 2], [86, 2], [99, 2]]), 'sleep': (210, [[59, 0], [118, 1], [120, 2]]),
         'wait1': (30, [[0, 0], [29, 1]]), 'damage': (50, [[10, 0], [29, 1]]), 'flick': (60, [[40, 2]]),
         'rolling_l': (110, [[20, 0], [67, 2], [69, 1]]), 'rolling_r': (110, [[20, 0], [67, 2], [69, 1]]),
         'born': (28, [[24, 2]]), 'carry': (40, [[10, 0], [29, 1]])}
BABY = {'dead': (100, []), 'deadpress': (80, []), 'move': (12, [[0, 0], [11, 1]]),
        'attack': (70, [[10, 2], [30, 3]]), 'attackfail': (20, []), 'born': (35, [[7, 0], [8, 1]])}


def _tree(root, carry_span=0.2):
    report = {'species': {}}
    lines = ['P2_BULBLAX_BANK_1']
    for species, clips in (('Queen', QUEEN), ('Baby', BABY)):
        general = dict(DISC_PARMS[species]['general'])
        if species == 'Queen':
            general.update(fp14=50.0, fp23=25.0)
        report['species'][species] = {
            'parameter_blocks': [{}, general, dict(DISC_PARMS[species]['proper'])],
            'clips': [{'name': n, 'source_frames': f, 'events': e} for n, (f, e) in clips.items()]}
        lines.append(f'{species} {len(clips)}')
        (root / 'bank' / species).mkdir(parents=True)
        for name, (frames, _) in clips.items():
            lines.append(f'{name} 2 {frames} 0 {frames - 1}')
            for i in range(2):
                pose = stage.pose_name(species, name, i)
                (root / 'bank' / species / pose).write_bytes(b'MOD' + bytes([i]))
                span = carry_span if (species, name) == ('Queen', 'carry') else 200.0
                (root / 'bank' / species / pose.replace('.mod', '.json')).write_text(
                    json.dumps({'bounds': [0, 0, 0, span, span, span]}))
    (root / 'bank' / 'p2-bulblax-bank.txt').write_text('\n'.join(lines) + '\n')
    (root / 'bank' / 'p2-queen-specular.txt').write_text('SPEC\n')
    (root / 'bulblax.json').write_text(json.dumps(report))
    (root / 'identity.json').write_text(json.dumps({'schema': 1, 'source_id': 30, 'enum_name': 'Queen'}))
    return root


def test_plan_writes_disc_parms_clips_and_carcass_fallback(tmp_path):
    planned = stage.plan(_tree(tmp_path / 'Queen'))
    text = planned['bank'].decode('ascii').splitlines()
    assert text[0] == 'P2_QUEEN_BANK_1' and text[-1] == 'end'
    assert 'parm health 5000' in text and 'parm rolling_time 3.5' in text
    assert 'parm shake_off_blow_d 50' in text and 'parm baby_attack_damage 2' in text
    assert 'parm carcass_carry_degenerate 1' in text
    assert 'clip queen rolling_l 110 3 20 0 67 2 69 1 2 0 109' in text
    assert planned['poses'] == 2 * (len(QUEEN) + len(BABY))


def test_usable_carry_poses_emit_no_fallback(tmp_path):
    planned = stage.plan(_tree(tmp_path / 'Queen', carry_span=300.0))
    assert b'carcass_carry_degenerate' not in planned['bank']


def test_non_disc_parm_fails_closed(tmp_path):
    root = _tree(tmp_path / 'Queen')
    report = json.loads((root / 'bulblax.json').read_text())
    report['species']['Queen']['parameter_blocks'][1]['fp00'] = 4000.0
    (root / 'bulblax.json').write_text(json.dumps(report))
    with pytest.raises(stage.QueenStageError):
        stage.plan(root)


def test_stage_replaces_private_room_poses_without_writing_through(tmp_path):
    root = _tree(tmp_path / 'Queen')
    run = tmp_path / 'run'
    room = run / stage.ROOM
    room.mkdir(parents=True)
    shared = tmp_path / 'shared.mod'
    shared.write_bytes(b'OLD')
    old = room / stage.pose_name('Queen', 'dead', 1)
    try:
        old.hardlink_to(shared)
    except OSError:
        old.write_bytes(b'OLD')
    receipt = stage.stage_from(root, run)
    assert receipt['poses'] == 2 * (len(QUEEN) + len(BABY)) and receipt['replaced'] == 1
    assert shared.read_bytes() == b'OLD'
    assert (run / stage.BANK_TXT).is_file() and (run / stage.SPECULAR_TXT).is_file()
    # Idempotent for a byte-identical repeat.
    assert stage.stage_from(root, run)['replaced'] == 0


def test_installer_and_extractor_wiring():
    from experimental.pikmin2_family_install import IDENTITY_FAMILY
    import scripts.p2_prepare_content as prepare
    from randomizer.p2_proxy import load_rows
    assert IDENTITY_FAMILY[30] == 'queen' and IDENTITY_FAMILY['queen'] == 'queen'
    assert prepare.EXTRACTORS[30] == 'extract_queen'
    assert 30 not in {row['source_id'] for row in load_rows()}


def test_baby_31_shares_the_queen_family_and_extracts_under_its_own_enum(tmp_path):
    """#1042: the standalone Bulborb Larva installs through the queen family from a
    ``Baby/`` extractor tree (the Queen extraction under its own enum)."""
    from experimental import pikmin2_family_install as install
    import scripts.p2_prepare_content as prepare
    from randomizer.p2_proxy import load_rows
    assert install.IDENTITY_FAMILY[31] == 'queen' and install.IDENTITY_FAMILY['baby'] == 'queen'
    assert prepare.ENUM_FOR_SOURCE[31] == 'Baby' and prepare.EXTRACTORS[31] == 'extract_baby'
    assert 31 not in {row['source_id'] for row in load_rows()}
    for enum_name, source_id in (('Queen', 30), ('Baby', 31)):
        tree = tmp_path / enum_name
        tree.mkdir()
        (tree / 'identity.json').write_text(json.dumps(
            {'schema': 1, 'source_id': source_id, 'enum_name': enum_name}), encoding='utf-8')
        assert install._bulblax_enum(tree) == enum_name
    wrong = tmp_path / 'Wrong'
    wrong.mkdir()
    (wrong / 'identity.json').write_text(json.dumps(
        {'schema': 1, 'source_id': 31, 'enum_name': 'Kabuto'}), encoding='utf-8')
    with pytest.raises(install.StagingError):
        install._bulblax_enum(wrong)
    # A Baby tree whose identity disagrees with the Baby source id fails closed.
    mismatch = tmp_path / 'Mismatch'
    mismatch.mkdir()
    (mismatch / 'identity.json').write_text(json.dumps(
        {'schema': 1, 'source_id': 30, 'enum_name': 'Baby'}), encoding='utf-8')
    with pytest.raises(install.StagingError):
        install._validate_queen(mismatch)
