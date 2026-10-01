"""#895 review fixes: resident budgets, collapsed-frame retry, no sparse fallback, audits."""
import json
import struct

import pytest

from experimental import pikmin2_animation as anim
from experimental import pikmin2_purple as purple


def mod_blob(positions, normals, extra=64):
    """Minimal MOD-shaped bytes: tag 16/17 vector chunks, one opaque chunk, end."""
    out = bytearray()
    for tag, count in ((16, positions), (17, normals)):
        payload = struct.pack('>I', count) + b'\0' * 20 + b'\0' * (12 * count)
        payload += b'\0' * ((-(8 + len(payload))) % 32)
        out += struct.pack('>II', tag, len(payload)) + payload
    payload = b'\0' * (extra - 8)
    out += struct.pack('>II', 80, len(payload)) + payload
    out += struct.pack('>II', 0xFFFF, 0)
    return bytes(out)


def test_shape_slots_mirror_native():
    # p2motion::shapeSlots: evenly spread, first and last included.
    assert anim.shape_slots(16, 4) == [0, 5, 10, 15]
    assert anim.shape_slots(3, 4) == [0, 1, 2]
    assert anim.shape_slots(5, 1) == [0]
    assert anim.shape_slots(0) == []


def test_resident_clip_bytes_counts_slots_and_vectors():
    poses = [mod_blob(100, 90) for _ in range(16)]
    size = len(poses[0])
    assert anim.mod_vector_count(poses[0]) == 190
    # 4 Shape slots at file size + 12 decoded poses at 12 bytes per vector.
    assert anim.resident_clip_bytes(poses) == 4 * size + 12 * 190 * 12
    # A small clip is all Shapes.
    assert anim.resident_clip_bytes(poses[:3]) == 3 * size


def test_approved_budgets_restored():
    from experimental import pikmin2_proxy_assets as proxy
    assert anim.RESIDENT_CLIP_BYTES == 1024 * 1024  # owner-approved (#895)
    assert anim.RESIDENT_TOTAL_BYTES == 48 * 1024 * 1024
    assert proxy.CLIP_BYTES == 1024 * 1024 and proxy.TOTAL_BYTES == 8 * 1024 * 1024
    assert anim.LEGACY_POSE_LIMIT == anim.DEFAULT_POSE_LIMIT == 24


def one_joint_bca(scale):
    """A framed 1-joint, 2-frame BCA whose every axis has constant `scale`."""
    table = 36
    scales = table + 36
    scales += (-scales) % 4
    rotations = scales + 4
    translations = rotations + 4
    body = bytearray(translations + 4)
    body[:4] = b'ANF1'
    struct.pack_into('>HH', body, 10, 2, 1)
    struct.pack_into('>4I', body, 20, table, scales, rotations, translations)
    for axis in range(3):
        for component in range(3):
            struct.pack_into('>HH', body, table + axis * 12 + component * 4, 1, 0)
    struct.pack_into('>f', body, scales, scale)
    struct.pack_into('>h', body, rotations, 0)
    struct.pack_into('>f', body, translations, 0.0)
    data = bytearray(32) + body
    data += b'\0' * ((-len(data)) % 32)
    data[:8] = b'J3D1bca1'
    struct.pack_into('>I', data, 8, len(data))
    return bytes(data)


def test_bca_pose_clamp_mode_keeps_collapsed_joint_invertible():
    raw = one_joint_bca(0.0)
    with pytest.raises(ValueError, match='Singular animation scale'):
        purple.bca_pose(raw, 0, 1, allow_scale=True)
    _, pose = purple.bca_pose(raw, 0, 1, allow_scale=True, singular_scale='clamp')
    floor = purple.COLLAPSED_SCALE_FLOOR
    assert [pose[0][i][i] for i in range(3)] == [floor, floor, floor]
    # Ordinary scales are untouched by clamp mode.
    _, same = purple.bca_pose(one_joint_bca(0.5), 0, 1, allow_scale=True, singular_scale='clamp')
    assert [same[0][i][i] for i in range(3)] == [0.5, 0.5, 0.5]


def test_decode_pose_retries_collapsed_frames_only(monkeypatch):
    calls = []

    def fake_bca(raw, frame, joints, allow_scale=False, singular_scale='error'):
        calls.append(('bca', singular_scale))
        return 2, [[[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 1.0, 0]]]

    monkeypatch.setattr(purple, 'bca_pose', fake_bca)
    import experimental.pikmin2_skinning as skinning
    monkeypatch.setattr(skinning, 'draw_matrices', lambda blocks, pose: ['m'])

    def decode_ok(model, approx, bake_rigid=False, draw_matrices=None, **kw):
        calls.append(('decode', kw.get('singular_normal', 'error')))
        return ({}, {9: []}, [], [])

    decoded, _ = anim.decode_pose(decode_ok, b'm', {}, b'r', 0, 1)
    assert calls == [('bca', 'error'), ('decode', 'error')]
    assert '_normal_policy' not in decoded[0]

    calls.clear()

    def decode_singular(model, approx, bake_rigid=False, draw_matrices=None, **kw):
        policy = kw.get('singular_normal', 'error')
        calls.append(('decode', policy))
        if policy == 'error':
            raise ValueError('Singular normal transform')
        return ({}, {9: []}, [], [])

    decoded, _ = anim.decode_pose(decode_singular, b'm', {}, b'r', 0, 1)
    assert calls == [('bca', 'error'), ('decode', 'error'), ('bca', 'clamp'), ('decode', 'transpose-adjugate')]
    assert decoded[0]['_normal_policy']['collapsed_joint']['scale_floor'] == purple.COLLAPSED_SCALE_FLOOR

    def decode_other(model, approx, bake_rigid=False, draw_matrices=None, **kw):
        raise ValueError('Missing display-list normal')

    with pytest.raises(ValueError, match='Missing display-list normal'):
        anim.decode_pose(decode_other, b'm', {}, b'r', 0, 1)


def test_proxy_sweep_never_falls_back_to_fewer_poses(monkeypatch, tmp_path):
    import scripts.p2_proxy_sweep as sweep
    limits = []

    def fake_extract(iso, enum, source_id, target, pose_limit, row):
        limits.append(pose_limit)
        raise ValueError('X clip a.bca exceeds 1 MiB of resident pose bytes (1100000 bytes) at pose_limit 16')

    monkeypatch.setattr(sweep, 'extract', fake_extract)
    monkeypatch.setattr(sweep, '_failure_record',
                        lambda row, error, limit, iso, seconds: dict(error=error, pose_limit_used=limit))
    record = sweep.sweep_species(tmp_path / 'iso', dict(source_id=1, enum_name='X', pose_limit=16), tmp_path)
    assert limits == [16]
    assert record['pose_limit_used'] == 16 and record['budget_failure'] is True


def test_mamuta_bank_manifest():
    from experimental.pikmin2_mamuta_install import BANK_CLIPS, bank_manifest
    clips = [dict(file=c + '.bca', source_frames=30, events=[dict(frame=4, type=2)],
                  poses=[dict(frame=f) for f in (0, 15, 29)]) for c in BANK_CLIPS]
    text = bank_manifest(dict(clips=clips))
    lines = text.splitlines()
    assert lines[0] == f'P2_MAMUTA_BANK_1 {len(BANK_CLIPS)}'
    assert lines[1] == 'clip wait 30 3 1 frames 0 15 29 events 4'
    legacy = [dict(c, poses=[dict(file='x')]) for c in clips]
    assert bank_manifest(dict(clips=legacy)) is None


def test_density_audit_flags_sparse_rows_and_missing_trailers(tmp_path):
    from scripts.p2_pose_density_audit import audit_run, violations
    room = tmp_path / 'assets/dataDir/courses/pikmin2room'
    room.mkdir(parents=True)
    (tmp_path / 'p2-ground-bank.txt').write_text(
        'P2_GROUND_BANK_1\nspecies Sokkuri 79\n'
        'clip Sokkuri pdead1 90 8:2 poses 4 converted\n'
        'clip Sokkuri run1 24 - poses 16 converted frames '
        + ','.join(str(f) for f in anim.sample_frames(24, 16)) + '\n'
        'species Armor 15\nclip Armor move 20 - poses 16 converted\n')
    blob = mod_blob(10, 10)
    for i in range(4):
        (room / f'ginv_Sokkuri_pdead1_{i:02}.mod').write_bytes(blob)
    for i in range(16):
        (room / f'ginv_Sokkuri_run1_{i:02}.mod').write_bytes(blob)
    clips, setups, _ = audit_run(tmp_path)
    # Armor is not staged in this run (no files): native never loads it.
    assert {c['species'] for c in clips} == {'Sokkuri'}
    bad = violations(clips, setups)
    assert any(v.startswith('density: p2-ground-bank.txt Sokkuri pdead1') for v in bad)
    assert any(v.startswith('trailer: p2-ground-bank.txt Sokkuri pdead1 missing') for v in bad)
    assert not any('run1' in v for v in bad)
    run1 = next(c for c in clips if c['clip'] == 'run1')
    assert run1['trailer'] == 'valid' and run1['explicit_frames']
    assert setups == {'batch2': sum(c['resident_bytes'] for c in clips)}
    json.dumps(clips)
