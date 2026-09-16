import hashlib
import json
import struct

import pytest

from experimental.pikmin2_dwarf_bear_bank import (
    BANK_JSON, BANK_TXT, PROFILE, PROFILE_JSON, PROFILE_TXT)
from experimental.pikmin2_dwarf_bear_install import (
    ACTORS_TXT, INSTALL_JSON, install, plan, sha)

CLIPS = (('wait1', 75), ('move1', 55), ('attack', 90), ('dead', 90), ('flick', 80))
IDS = [211101]


def mod_bytes():
    def chunk(tag, payload):
        return struct.pack('>II', tag, len(payload)) + payload
    return chunk(32, b'material') + chunk(34, b'texture') + chunk(48, b'event') + chunk(65535, b'')


def fixture(tmp_path, visuals=True):
    bank = tmp_path / 'bank'
    bank.mkdir()
    profile_dir = tmp_path / 'profile'
    profile_dir.mkdir()
    run = tmp_path / 'run'
    room = run / 'assets/dataDir/courses/pikmin2room'
    room.mkdir(parents=True)
    reference = {'schema': 1, 'species': 'KumaKochappy', 'source_id': 76}
    (profile_dir / PROFILE_JSON).write_text(json.dumps(reference, indent=2))
    motions = {}
    files = {}
    rows = []
    for name, duration in CLIPS:
        frames = [0, duration // 2, duration - 1]
        motions[name] = {'poses': 3, 'source_frames': duration, 'frames': frames,
                         'event_frames': [frames[1]]}
        rows.append(f"{name} 3 {duration} {' '.join(map(str, frames))}")
        if visuals:
            for i in range(3):
                data = mod_bytes()
                (bank / f'dwarf_bear_{name}_{i:02}.mod').write_bytes(data)
                files[f'dwarf_bear_{name}_{i:02}.mod'] = sha(data)
    (bank / PROFILE_TXT).write_bytes(PROFILE.encode('ascii'))
    (bank / BANK_TXT).write_bytes(('\n'.join(['P2_DWARF_BEAR_BANK_1'] + rows) + '\n').encode('ascii'))
    metadata = {'schema': 1, 'species': 'KumaKochappy', 'source_id': 76, 'health': 500,
                'motions': motions,
                'reference_sha256': sha((profile_dir / PROFILE_JSON).read_bytes()),
                'file_sha256': files}
    (bank / BANK_JSON).write_text(json.dumps(metadata, indent=2))
    return bank, profile_dir, run, room


def test_install_exact_byte_configs_and_receipt(tmp_path):
    bank, profile_dir, run, room = fixture(tmp_path)
    receipt = install(bank, profile_dir, run, IDS)
    assert (run / PROFILE_TXT).read_bytes() == PROFILE.encode('ascii')
    assert b'\r' not in (run / PROFILE_TXT).read_bytes()
    assert b'\r' not in (run / BANK_TXT).read_bytes()
    assert (run / ACTORS_TXT).read_bytes() == b'P2_DWARF_BEAR_ACTORS_1 1\n211101\n'
    assert receipt['visuals'] == 'installed' and receipt['species'] == 'KumaKochappy'
    assert receipt['source_id'] == 76 and receipt['health'] == 500
    assert receipt['gameplay_events_executed'] is False
    assert 'ChappyRelation' in receipt['parent_relation']
    assert len(receipt['file_sha256']) == 15
    for name, digest in receipt['file_sha256'].items():
        assert sha((room / name).read_bytes()) == digest
    assert json.loads((run / INSTALL_JSON).read_text()) == receipt


def test_conflict_refused_before_mutation(tmp_path):
    bank, profile_dir, run, room = fixture(tmp_path)
    install(bank, profile_dir, run, IDS)
    before = {p.name: p.read_bytes() for p in room.iterdir()}
    with pytest.raises(ValueError, match='Refusing existing'):
        install(bank, profile_dir, run, [211109])
    assert {p.name: p.read_bytes() for p in room.iterdir()} == before


def test_changed_source_refused_before_mutation(tmp_path):
    bank, profile_dir, run, room = fixture(tmp_path)
    (profile_dir / PROFILE_JSON).write_text('{"schema":1,"species":"KumaKochappy","changed":true}')
    with pytest.raises(ValueError, match='different source import'):
        install(bank, profile_dir, run, IDS)
    assert not (run / PROFILE_TXT).exists() and not list(room.iterdir())


def test_tampered_visual_bank_refused_before_mutation(tmp_path):
    bank, profile_dir, run, room = fixture(tmp_path)
    (bank / 'dwarf_bear_flick_00.mod').write_bytes(b'corrupt')
    with pytest.raises(ValueError):
        install(bank, profile_dir, run, IDS)
    assert not (run / PROFILE_TXT).exists() and not list(room.iterdir())


def test_partial_visual_bank_refused(tmp_path):
    bank, profile_dir, run, room = fixture(tmp_path)
    (bank / 'dwarf_bear_wait1_01.mod').unlink()
    with pytest.raises(ValueError, match='Incomplete/unexpected'):
        install(bank, profile_dir, run, IDS)
    assert not list(room.iterdir())


def test_absent_visual_bank_preserves_baseline(tmp_path):
    bank, profile_dir, run, room = fixture(tmp_path, visuals=False)
    (room / 'baseline.txt').write_bytes(b'original baseline\r\n')
    receipt = install(bank, profile_dir, run, IDS)
    assert receipt['visuals'] == 'absent_baseline_preserved' and receipt['file_sha256'] == {}
    assert (room / 'baseline.txt').read_bytes() == b'original baseline\r\n'
    assert not list(room.glob('*.mod'))


def test_generator_id_overlap_with_sibling_refused(tmp_path):
    bank, profile_dir, run, room = fixture(tmp_path)
    (run / 'p2-dwarf-orange-actors.txt').write_text('P2_DWARF_ORANGE_ACTORS_1 1\n211101\n')
    with pytest.raises(ValueError, match='overlap'):
        install(bank, profile_dir, run, IDS)
    assert not (run / PROFILE_TXT).exists() and not list(room.iterdir())


def test_wrong_bank_identity_refused(tmp_path):
    bank, profile_dir, run, room = fixture(tmp_path)
    metadata = json.loads((bank / BANK_JSON).read_text())
    metadata['source_id'] = 44
    (bank / BANK_JSON).write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match='identity'):
        install(bank, profile_dir, run, IDS)
    assert not list(room.iterdir())


def test_token_drift_refused(tmp_path):
    bank, profile_dir, run, room = fixture(tmp_path)
    (bank / PROFILE_TXT).write_bytes(PROFILE.replace('health 500', 'health 501').encode('ascii'))
    with pytest.raises(ValueError, match='drifted'):
        install(bank, profile_dir, run, IDS)
    assert not list(room.iterdir())


def test_crlf_sources_normalized_to_exact_bytes(tmp_path):
    bank, profile_dir, run, room = fixture(tmp_path)
    (bank / PROFILE_TXT).write_bytes(PROFILE.replace('\n', '\r\n').encode('ascii'))
    (bank / BANK_TXT).write_bytes((bank / BANK_TXT).read_bytes().replace(b'\n', b'\r\n'))
    receipt = install(bank, profile_dir, run, IDS)
    assert (run / PROFILE_TXT).read_bytes() == PROFILE.encode('ascii')
    assert b'\r' not in (run / BANK_TXT).read_bytes()
    assert receipt['profile_config_sha256'] == sha(PROFILE.encode('ascii'))


def test_invalid_generator_ids_refused(tmp_path):
    bank, profile_dir, run, room = fixture(tmp_path)
    with pytest.raises(ValueError, match='unique unsigned'):
        plan(bank, profile_dir, [211101, 211101])
    with pytest.raises(ValueError, match='unique unsigned'):
        plan(bank, profile_dir, [-1])
    assert not list(room.iterdir())
