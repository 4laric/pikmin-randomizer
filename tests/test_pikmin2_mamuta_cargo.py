"""Lane 19 (#221) cargo staging: exact Pod profile text and switch guards."""
import hashlib

import pytest

from experimental.pikmin2_mamuta_rules import cargo_profile, enable_cargo


def test_cargo_profile_is_the_native_pod_format():
    assert cargo_profile('dia_a_red', 180, 15, 25, 2) == (
        'P2_POD_1\ndia_a_red 180 15 25\nKochappy 2\n')


def test_cargo_profile_rejects_bad_values():
    with pytest.raises(ValueError):
        cargo_profile('', 180, 15, 25, 2)
    with pytest.raises(ValueError):
        cargo_profile('bad id', 180, 15, 25, 2)
    with pytest.raises(ValueError):
        cargo_profile('dia_a_red', -1, 15, 25, 2)
    with pytest.raises(ValueError):
        cargo_profile('dia_a_red', 180, 0, 25, 2)
    with pytest.raises(ValueError):
        cargo_profile('dia_a_red', 180, 15, 0, 2)
    with pytest.raises(ValueError):
        cargo_profile('dia_a_red', 180, 15, 25, -1)


def _stage(tmp_path, model=b'model'):
    run = tmp_path / 'run'
    (run / 'assets/dataDir/courses/pikmin2room').mkdir(parents=True)
    (run / 'assets/dataDir/courses/pikmin2room/treasure.mod').write_bytes(model)
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    return run, hashlib.sha256(model).hexdigest()


def test_enable_cargo_switches_cargo_free_to_pod(tmp_path):
    run, sha = _stage(tmp_path)
    info = enable_cargo(run, treasure='dia_a_red', money=180, weight=15, capacity=25,
                        corpse_value=2, treasure_model_sha256=sha)
    assert info['treasure'] == 'dia_a_red' and info['treasure_model_sha256'] == sha
    assert not (run / 'p2-cargo-free.txt').exists()
    assert (run / 'p2-pod.txt').read_text() == (
        'P2_POD_1\ndia_a_red 180 15 25\nKochappy 2\n')


def test_enable_cargo_refuses_without_cargo_free(tmp_path):
    run, sha = _stage(tmp_path)
    (run / 'p2-cargo-free.txt').unlink()
    with pytest.raises(ValueError):
        enable_cargo(run, treasure='dia_a_red', money=180, weight=15, capacity=25,
                     corpse_value=2, treasure_model_sha256=sha)


def test_enable_cargo_refuses_existing_pod_or_bad_model(tmp_path):
    run, sha = _stage(tmp_path)
    (run / 'p2-pod.txt').write_text('existing')
    with pytest.raises(ValueError):
        enable_cargo(run, treasure='dia_a_red', money=180, weight=15, capacity=25,
                     corpse_value=2, treasure_model_sha256=sha)
    (run / 'p2-pod.txt').unlink()
    with pytest.raises(ValueError):
        enable_cargo(run, treasure='dia_a_red', money=180, weight=15, capacity=25,
                     corpse_value=2, treasure_model_sha256='0' * 64)
