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
