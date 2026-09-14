"""Lane 19 (#221) cargo staging: exact Pod profile text, package loading and guards."""
import hashlib
import struct

import pytest

from experimental.pikmin2_mamuta_rules import (
    POD_PACKAGE_FILES, POD_TREASURE_GENERATOR, POD_TREASURE_NAME, POD_TREASURE_POSITION,
    append_treasure_record, cargo_profile, enable_cargo, find_pod_package,
    load_pod_package, parse_cargo_profile, validate_treasure_record)


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


def test_parse_cargo_profile_roundtrips_and_rejects_malformed():
    text = cargo_profile('dia_a_red', 180, 15, 25, 2)
    assert parse_cargo_profile(text) == dict(
        treasure='dia_a_red', money=180, weight=15, capacity=25, corpse_value=2, profile=text)
    for bad in ('', 'P2_POD_1 dia_a_red 180 15 25\n', 'P2_POD_2\ndia_a_red 180 15 25\nKochappy 2\n',
                'P2_POD_1\ndia_a_red 180 15 25\nDwarf 2\n', 'P2_POD_1\ndia_a_red x 15 25\nKochappy 2\n'):
        with pytest.raises(ValueError):
            parse_cargo_profile(bad)


def _package(tmp_path, treasure=b'model', pod=b'pod'):
    root = tmp_path / 'package'
    root.mkdir()
    (root / 'p2-pod.txt').write_text(cargo_profile('dia_a_red', 180, 15, 25, 2))
    (root / 'treasure.mod').write_bytes(treasure)
    (root / 'pod.mod').write_bytes(pod)
    return root


def test_load_pod_package_hashes_and_economy(tmp_path):
    root = _package(tmp_path)
    loaded = load_pod_package(root)
    assert loaded['treasure'] == 'dia_a_red' and loaded['corpse_value'] == 2
    assert loaded['treasure_model_sha256'] == hashlib.sha256(b'model').hexdigest()
    assert loaded['pod_model_sha256'] == hashlib.sha256(b'pod').hexdigest()
    assert loaded['profile'] == cargo_profile('dia_a_red', 180, 15, 25, 2)


def test_load_pod_package_fails_closed_on_missing_members(tmp_path):
    root = _package(tmp_path)
    (root / 'pod.mod').unlink()
    with pytest.raises(FileNotFoundError):
        load_pod_package(root)
    with pytest.raises(FileNotFoundError):
        find_pod_package([tmp_path / 'absent', root])


def test_find_pod_package_returns_first_complete(tmp_path):
    root = _package(tmp_path)
    found = find_pod_package([tmp_path / 'absent', root])
    assert found['path'] == str(root)
    assert set(POD_PACKAGE_FILES) <= {p.name for p in root.iterdir()}


def _stage(tmp_path, model=b'model', pod=b'pod'):
    run = tmp_path / 'run'
    (run / 'assets/dataDir/courses/pikmin2room').mkdir(parents=True)
    (run / 'assets/dataDir/courses/pikmin2room/treasure.mod').write_bytes(model)
    (run / 'assets/dataDir/courses/pikmin2room/pod.mod').write_bytes(pod)
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    return run, hashlib.sha256(model).hexdigest(), hashlib.sha256(pod).hexdigest()


def test_enable_cargo_switches_cargo_free_to_pod(tmp_path):
    run, sha, pod_sha = _stage(tmp_path)
    info = enable_cargo(run, treasure='dia_a_red', money=180, weight=15, capacity=25,
                        corpse_value=2, treasure_model_sha256=sha, pod_model_sha256=pod_sha)
    assert info['treasure'] == 'dia_a_red' and info['treasure_model_sha256'] == sha
    assert info['pod_model_sha256'] == pod_sha
    assert not (run / 'p2-cargo-free.txt').exists()
    assert (run / 'p2-pod.txt').read_text() == (
        'P2_POD_1\ndia_a_red 180 15 25\nKochappy 2\n')


def test_enable_cargo_refuses_without_cargo_free(tmp_path):
    run, sha, pod_sha = _stage(tmp_path)
    (run / 'p2-cargo-free.txt').unlink()
    with pytest.raises(ValueError):
        enable_cargo(run, treasure='dia_a_red', money=180, weight=15, capacity=25,
                     corpse_value=2, treasure_model_sha256=sha, pod_model_sha256=pod_sha)


def test_enable_cargo_refuses_existing_pod_or_bad_models(tmp_path):
    run, sha, pod_sha = _stage(tmp_path)
    (run / 'p2-pod.txt').write_text('existing')
    with pytest.raises(ValueError):
        enable_cargo(run, treasure='dia_a_red', money=180, weight=15, capacity=25,
                     corpse_value=2, treasure_model_sha256=sha, pod_model_sha256=pod_sha)
    (run / 'p2-pod.txt').unlink()
    with pytest.raises(ValueError):
        enable_cargo(run, treasure='dia_a_red', money=180, weight=15, capacity=25,
                     corpse_value=2, treasure_model_sha256='0' * 64, pod_model_sha256=pod_sha)
    with pytest.raises(ValueError):
        enable_cargo(run, treasure='dia_a_red', money=180, weight=15, capacity=25,
                     corpse_value=2, treasure_model_sha256=sha, pod_model_sha256='0' * 64)


def _record(generator, model=b'50rp', name=POD_TREASURE_NAME, position=POD_TREASURE_POSITION):
    record = bytearray(120)
    record[0:8] = b'    0.0v'
    struct.pack_into('<I', record, 8, generator)
    record[16:48] = name.encode('ascii').ljust(32, b'\0')
    record[80:84] = model
    struct.pack_into('>6f', record, 48, *position, 0, 0, 0)
    return bytes(record)


def _gen(records):
    return b'1.0v' + b'\0' * 16 + struct.pack('>I', len(records)) + b''.join(records)


def _run_with_gen(tmp_path, records):
    run = tmp_path / 'run'
    (run / 'assets/dataDir/stages/chal0').mkdir(parents=True)
    (run / 'assets/dataDir/stages/chal0/default.gen').write_bytes(_gen(records))
    return run


def test_validate_treasure_record_requires_pr05_and_fields():
    placement = validate_treasure_record(_record(POD_TREASURE_GENERATOR))
    assert placement['model_id'] == 'pr05'
    assert placement['generator'] == POD_TREASURE_GENERATOR
    assert placement['position'] == list(POD_TREASURE_POSITION)
    with pytest.raises(ValueError):
        validate_treasure_record(_record(POD_TREASURE_GENERATOR, model=b'zzzz'))


def test_append_treasure_record_appends_single_pr05(tmp_path):
    run = _run_with_gen(tmp_path, [_record(1, model=b'zzzz', name='existing actor')])
    placement = append_treasure_record(run, _record(POD_TREASURE_GENERATOR))
    assert placement['generator'] == POD_TREASURE_GENERATOR
    data = (run / 'assets/dataDir/stages/chal0/default.gen').read_bytes()
    assert struct.unpack_from('>I', data, 20)[0] == 2
    assert data.count(b'50rp') == 1


def test_append_treasure_record_refuses_second_pr05(tmp_path):
    run = _run_with_gen(tmp_path, [_record(1)])
    with pytest.raises(ValueError):
        append_treasure_record(run, _record(POD_TREASURE_GENERATOR))
    run2 = _run_with_gen(tmp_path / 'second', [_record(POD_TREASURE_GENERATOR)])
    with pytest.raises(ValueError):
        append_treasure_record(run2, _record(POD_TREASURE_GENERATOR))
