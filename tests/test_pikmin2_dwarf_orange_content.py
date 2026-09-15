import hashlib
import json
import struct

import pytest

from experimental.pikmin2_dwarf_orange_bank import (
    BANK_JSON, BANK_TXT, PROFILE, PROFILE_TXT)
from experimental.pikmin2_dwarf_orange_content import content_manifest, write_content_manifest
from experimental.pikmin2_staging import StagingError, load_manifest, stage, stage_session_content, verify_manifest

CLIPS = (('wait1', 75), ('move1', 55), ('attack', 90), ('dead', 90), ('flick', 80))


def mod_bytes():
    def chunk(tag, payload):
        return struct.pack('>II', tag, len(payload)) + payload
    return chunk(32, b'material') + chunk(34, b'texture') + chunk(48, b'event') + chunk(65535, b'')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture(tmp_path):
    bank = tmp_path / 'bank'
    bank.mkdir()
    motions = {}
    files = {}
    rows = []
    for name, duration in CLIPS:
        frames = [0, duration // 2, duration - 1]
        motions[name] = {'poses': 3, 'source_frames': duration, 'frames': frames,
                         'event_frames': [frames[1]]}
        rows.append(f"{name} 3 {duration} {' '.join(map(str, frames))}")
        for i in range(3):
            data = mod_bytes()
            (bank / f'dwarf_orange_{name}_{i:02}.mod').write_bytes(data)
            files[f'dwarf_orange_{name}_{i:02}.mod'] = sha(data)
    (bank / PROFILE_TXT).write_bytes(PROFILE.encode('ascii'))
    (bank / BANK_TXT).write_bytes(('\n'.join(['P2_DWARF_ORANGE_BANK_1'] + rows) + '\n').encode('ascii'))
    metadata = {'schema': 1, 'species': 'BlueKochappy', 'source_id': 44, 'health': 250,
                'motions': motions, 'file_sha256': files}
    (bank / BANK_JSON).write_text(json.dumps(metadata, indent=2))
    return bank


def test_content_manifest_serves_source_44_and_stages(tmp_path):
    bank = fixture(tmp_path)
    manifest = content_manifest(bank)
    assert manifest['identities'] == [44]
    kinds = sorted((e['destination'], e['kind']) for e in manifest['entries'])
    assert ('p2-dwarf-orange-bank.txt', 'config') in kinds
    assert ('p2-dwarf-orange-profile.txt', 'config') in kinds
    models = [e for e in manifest['entries'] if e['kind'] == 'model']
    assert len(models) == 15
    assert all(e['destination'].startswith('dataDir/courses/pikmin2room/dwarf_orange_')
               for e in models)
    assert set(len(e['sha256']) == 64 for e in manifest['entries']) == {True}
    report = verify_manifest(manifest, base=tmp_path)
    assert report['ok'] and report['summary']['entries'] == len(manifest['entries'])
    dest = tmp_path / 'staged'
    receipt = stage(manifest, dest, base=tmp_path)
    assert receipt['summary']['staged'] == len(manifest['entries'])
    assert (dest / 'p2-dwarf-orange-bank.txt').is_file()
    assert (dest / 'dataDir/courses/pikmin2room/dwarf_orange_attack_01.mod').is_file()


def test_write_manifest_roundtrip(tmp_path):
    bank = fixture(tmp_path)
    path = tmp_path / 'content.json'
    write_content_manifest(bank, path)
    loaded = load_manifest(path)
    assert loaded == content_manifest(bank)
    assert loaded['identities'] == [44]


def test_stage_session_content_requires_identity_coverage(tmp_path):
    bank = fixture(tmp_path)
    path = tmp_path / 'content.json'
    write_content_manifest(bank, path)
    dest = tmp_path / 'run'
    receipt = stage_session_content(path, dest, base=tmp_path, required_identities=[44])
    assert receipt['identities'] == ['44']
    with pytest.raises(StagingError, match='45'):
        stage_session_content(path, dest / 'other', base=tmp_path, required_identities=[45])


def test_tampered_visual_bank_refused(tmp_path):
    bank = fixture(tmp_path)
    (bank / 'dwarf_orange_attack_01.mod').write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='MOD|hash mismatch'):
        content_manifest(bank)


def test_wrong_identity_refused(tmp_path):
    bank = fixture(tmp_path)
    metadata = json.loads((bank / BANK_JSON).read_text())
    metadata['species'] = 'KumaKochappy'
    (bank / BANK_JSON).write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match='identity'):
        content_manifest(bank)


def test_token_drift_refused(tmp_path):
    bank = fixture(tmp_path)
    (bank / PROFILE_TXT).write_bytes(PROFILE.replace('health 250', 'health 251').encode('ascii'))
    with pytest.raises(ValueError, match='drifted'):
        content_manifest(bank)