"""Tests for the hash-bound beetle install (installed artifacts, not just output/)."""
import hashlib
import json
from pathlib import Path

import pytest

from experimental.pikmin2_kogane_install import (ACTORS_HEADER, ACTORS_TXT, BANK_JSON, BANK_TXT,
                                                 INSTALL_JSON, PROFILE_TXT, install, plan, sha)


def fake_bank(tmp_path, pose_data=b'pose-bytes', poses_per_clip=2, tamper=False, omit_poses=False):
    bank = tmp_path / 'bank'
    (bank / 'shared').mkdir(parents=True)
    clips = []
    expected_events = {'move.bca': [[2, 0], [11, 1]], 'wait.bca': [[0, 0], [14, 1]],
                       'damage.bca': [[5, 2], [7, 3], [29, 4]]}
    for clip_name, events in expected_events.items():
        poses = []
        for i in range(poses_per_clip):
            name = f'{Path(clip_name).stem}_{i:02}.mod'
            data = pose_data + name.encode()
            if not omit_poses:
                (bank / 'shared' / name).write_bytes(data)
            poses.append(dict(file=name, frame=i, sha256=sha(data), conversion={}))
        clips.append(dict(file=clip_name, events=events, sha256=sha(clip_name.encode()),
                          status='converted', source_frames=15, poses=poses))
    manifest = {'schema': 1, 'family': 'Kogane', 'native_ready': False,
                'species': {s: {'enemy_id': i} for s, i in
                            (('kogane', 9), ('wealthy', 10), ('fart', 11))},
                'shared': {'joints': ['null1', 'body'], 'clips': clips}}
    (bank / BANK_JSON).write_text(json.dumps(manifest))
    if tamper:
        first = clips[0]['poses'][0]['file']
        (bank / 'shared' / first).write_bytes(b'tampered')
    return bank


def fake_run(tmp_path):
    run = tmp_path / 'run'
    (run / 'assets/dataDir/courses/pikmin2room').mkdir(parents=True)
    return run


def test_install_writes_verified_artifacts(tmp_path):
    bank = fake_bank(tmp_path)
    run = fake_run(tmp_path)
    receipt = install(bank, run, [219001, 219002, 219003])
    assert receipt['visuals'] == 'installed'
    assert len(receipt['file_sha256']) == 6
    for name, digest in receipt['file_sha256'].items():
        installed = (run / 'assets/dataDir/courses/pikmin2room' / name).read_bytes()
        assert sha(installed) == digest
        # installed bytes identical to the generated bank
        assert installed == (bank / 'shared' / name.replace('kogane_', '', 1)).read_bytes()
    assert sha((run / PROFILE_TXT).read_bytes()) == receipt['profile_config_sha256']
    assert sha((run / BANK_TXT).read_bytes()) == receipt['bank_config_sha256']
    assert sha((run / ACTORS_TXT).read_bytes()) == receipt['actors_config_sha256']
    assert (run / ACTORS_TXT).read_text().startswith(ACTORS_HEADER + ' 3\n')
    assert json.loads((run / INSTALL_JSON).read_text())['generators'] == [219001, 219002, 219003]


def test_profile_tokens_cover_species_contract(tmp_path):
    receipt = install(fake_bank(tmp_path), fake_run(tmp_path), [219001])
    text = (tmp_path / 'run' / PROFILE_TXT).read_text()
    assert text.startswith('P2_KOGANE_PROFILE_1\n')
    for token in ('species kogane 9', 'species wealthy 10', 'species fart 11',
                  'drop kogane 0 surface pellet_PELLET_NUMBER_ONE_1',
                  'drop wealthy 0 surface pellet_PELLET_NUMBER_FIVE_3',
                  'drop fart 0 surface doping_HONEY_Y_3',
                  'flips 3', 'fart_gas_duration 2.5'):
        assert token in text
    bank_text = (tmp_path / 'run' / BANK_TXT).read_text()
    assert 'clip damage.bca 15 5:2,7:3,29:4 poses 2' in bank_text


def test_reinstall_refused(tmp_path):
    bank = fake_bank(tmp_path)
    run = fake_run(tmp_path)
    install(bank, run, [219001])
    with pytest.raises(ValueError, match='Refusing existing'):
        install(bank, run, [219002])


def test_tampered_pose_refused_before_mutation(tmp_path):
    bank = fake_bank(tmp_path, tamper=True)
    run = fake_run(tmp_path)
    with pytest.raises(ValueError, match='hash mismatch'):
        install(bank, run, [219001])
    assert not (run / PROFILE_TXT).exists()
    assert not list((run / 'assets/dataDir/courses/pikmin2room').iterdir())


def test_partial_bank_refused(tmp_path):
    bank = fake_bank(tmp_path)
    first = next((bank / 'shared').glob('*.mod'))
    first.unlink()
    with pytest.raises(ValueError, match='Incomplete'):
        install(bank, fake_run(tmp_path), [219001])


def test_absent_bank_preserves_baseline(tmp_path):
    bank = fake_bank(tmp_path, omit_poses=True)
    run = fake_run(tmp_path)
    receipt = install(bank, run, [219001])
    assert receipt['visuals'] == 'absent_baseline_preserved'
    assert receipt['file_sha256'] == {}
    assert not list((run / 'assets/dataDir/courses/pikmin2room').iterdir())


def test_sibling_generator_overlap_refused(tmp_path):
    run = fake_run(tmp_path)
    (run / 'p2-dwarf-bear-actors.txt').write_text('P2_DWARF_BEAR_ACTORS_1 1\n219001\n')
    with pytest.raises(ValueError, match='overlap'):
        install(fake_bank(tmp_path), run, [219001, 219002])


def test_invalid_generator_ids_rejected(tmp_path):
    bank = fake_bank(tmp_path)
    for ids in ([], [1, 1], [219001, -1], [True], list(range(101))):
        with pytest.raises(ValueError):
            plan(bank, ids)


def test_manifest_identity_drift_rejected(tmp_path):
    bank = fake_bank(tmp_path)
    manifest = json.loads((bank / BANK_JSON).read_text())
    manifest['species']['fart']['enemy_id'] = 12
    (bank / BANK_JSON).write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='species/ID'):
        plan(bank, [219001])


def test_event_frame_drift_rejected(tmp_path):
    bank = fake_bank(tmp_path)
    manifest = json.loads((bank / BANK_JSON).read_text())
    manifest['shared']['clips'][2]['events'][1] = [8, 3]  # drop must fire at frame 7
    (bank / BANK_JSON).write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='event frames'):
        plan(bank, [219001])


def test_non_junction_room_required(tmp_path):
    run = tmp_path / 'run'
    run.mkdir()
    with pytest.raises(ValueError, match='non-junction'):
        install(fake_bank(tmp_path), run, [219001])
