"""BigFoot sampled pose bank (smoothing pass): config contract and bake loop."""
import pytest

import experimental.pikmin2_long_legs_bank as bank


def test_config_text_contract():
    text = bank.config_text([('wait', 4, [0, 1, 2, 3]), ('dead', 10, [0, 4, 9])])
    assert text.splitlines() == ['P2_LONG_LEGS_ANIMATION_1', 'BigFoot',
                                 'wait 4 4 0 1 2 3', 'dead 3 10 0 4 9']


@pytest.mark.parametrize('frames,duration', [([1, 2], 3), ([0, 1], 5), ([0, 2, 2, 3], 4), ([], 4)])
def test_config_text_rejects_bad_frames(frames, duration):
    with pytest.raises(ValueError):
        bank.config_text([('wait', duration, frames)])


def test_pose_name_matches_native_stem():
    assert bank.pose_name('landing', 7) == 'longlegs_BigFoot_landing_07.mod'


def test_bake_writes_every_clip_and_config(tmp_path, monkeypatch):
    monkeypatch.setattr(bank, 'blocks', lambda model: {'EVP1': b'\0' * 8 + b'\0\x04'})
    monkeypatch.setattr(bank, 'joints', lambda model: ['a', 'b'])
    monkeypatch.setattr(bank, 'bca_pose', lambda raw, frame, count, allow_scale=False: (8, [frame]))
    monkeypatch.setattr(bank, 'draw_matrices', lambda blk, pose: pose)
    monkeypatch.setattr(bank, 'decode', lambda model, *a, **k: k['draw_matrices'])
    monkeypatch.setattr(bank, 'resource_chunks', lambda data: b'same')
    monkeypatch.setattr(bank, 'write_model',
                        lambda decoded, target, name: target.write_bytes(b'MOD' + bytes(decoded)))
    motions = {c + '.bca': b'x' * 64 for c in bank.CLIPS}
    report = bank.bake(b'model', motions, tmp_path / 'out', pose_limit=4)
    assert report['total_poses'] == 16 and report['joints'] == 2
    assert len(list((tmp_path / 'out').glob('longlegs_BigFoot_*.mod'))) == 16
    lines = (tmp_path / 'out' / bank.CONFIG).read_text().splitlines()
    assert lines[:2] == ['P2_LONG_LEGS_ANIMATION_1', 'BigFoot']
    assert [l.split()[0] for l in lines[2:]] == list(bank.CLIPS)
    assert lines[2] == 'wait 4 8 0 2 5 7'


def test_bake_rejects_unweighted_model(tmp_path, monkeypatch):
    monkeypatch.setattr(bank, 'blocks', lambda model: {'EVP1': b'\0' * 10})
    monkeypatch.setattr(bank, 'joints', lambda model: ['a'])
    with pytest.raises(ValueError):
        bank.bake(b'm', {}, tmp_path / 'o')


def test_skin_text_rows(monkeypatch):
    import struct
    drw = bytearray(28)
    struct.pack_into('>H', drw, 8, 2)
    struct.pack_into('>II', drw, 12, 20, 24)
    drw[20] = 0  # rigid -> joint 1
    drw[21] = 1  # envelope 0
    struct.pack_into('>HH', drw, 24, 1, 0)
    ident = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]]
    monkeypatch.setattr(bank, 'blocks', lambda model: {'EVP1': b'', 'DRW1': bytes(drw)})
    monkeypatch.setattr(bank, 'joints', lambda model: ['kosi', 'leg'])
    monkeypatch.setattr(bank, '_envelopes', lambda block, count: ([[(0, 0.25), (1, 0.75)]], [ident, ident]))
    monkeypatch.setattr(bank, 'draw_matrices', lambda blk: None)

    def fake_decode(model, *a, **k):
        k['bindings'].update({9: [(0, (1.0, 2.0, 3.0)), (1, (4.0, 5.0, 6.0))], 10: [(1, (0.0, 1.0, 0.0))]})
    monkeypatch.setattr(bank, 'decode', fake_decode)
    lines = bank.skin_text(b'model').decode('ascii').splitlines()
    assert lines[0] == bank.SKIN_HEADER and lines[1] == 'joints 2'
    assert lines[2].startswith('i 0 1 0 0 0') and lines[3].startswith('i 1 ')
    assert lines[4:7] == ['draws 2', 'd 0 r 1', 'd 1 e 2 0 0.25 1 0.75']
    assert lines[7:10] == ['positions 2', '0 1 2 3', '1 4 5 6']
    assert lines[10:12] == ['normals 1', '1 0 1 0'] and lines[-1] == 'end'
