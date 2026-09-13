"""Tests for the batch-3 binding evidence validators (#219, native unblock 7faa644)."""
import hashlib
import json

import pytest

from experimental.pikmin2_kogane_runtime import BINDING_IDS, validate_binding, verify_fixed_run


def binding_log(xyz=None, ids=None, draw=True, passline=True, control=(219004, -1, 1)):
    ids = ids or [(219001, 9, 0), (219002, 10, 0), (219003, 11, 0), control]
    xyz = xyz or {219001: (-150., 30., 1850.), 219002: (-50., 30., 1850.),
                  219003: (50., 30., 1850.), 219004: (150., 30., 1550.)}
    lines = [f'P2_KOGANE_ID id={i} source_id={s} control={c}' for i, s, c in ids]
    lines += [f'P2_KOGANE_BIRTH id={i} type=3 x={p[0]:.3f} y={p[1]:.3f} z={p[2]:.3f}'
              for i, p in xyz.items()]
    if draw:
        lines.append('P2_KOGANE_DRAW corpse=0')
    if passline:
        lines.append('PASS P2_KOGANE_RUNTIME births4 alive4 behavior=P1_visual_binding_source_FSM_pending')
    return '\n'.join(lines) + '\n'


def test_binding_ids_contract():
    assert BINDING_IDS == {219001: 9, 219002: 10, 219003: 11, 219004: -1}


def test_validate_binding_accepts_clean_log():
    evidence = validate_binding(binding_log(), 0)
    assert evidence['passed']
    assert all(evidence['checks'].values())
    assert evidence['typed']['219001'] == (9, 0)
    assert evidence['typed']['219004'] == (-1, 1)
    assert 'source FSM' in evidence['unmeasured']


def test_validate_binding_rejects_wrong_source_id():
    log = binding_log(ids=[(219001, 9, 0), (219002, 11, 0), (219003, 10, 0), (219004, -1, 1)])
    evidence = validate_binding(log, 0)
    assert not evidence['passed']
    assert not evidence['checks']['typed_mapping']


def test_validate_binding_rejects_control_registered_as_species():
    log = binding_log(control=(219004, 9, 0))
    assert not validate_binding(log, 0)['passed']


def test_validate_binding_rejects_wrong_xyz():
    xyz = {219001: (-150., 30., 1850.), 219002: (-50., 30., 1850.),
           219003: (50., 30., 1850.), 219004: (150., 30., 1550.5)}
    evidence = validate_binding(binding_log(xyz=xyz), 0)
    assert not evidence['passed']
    assert not evidence['checks']['exact_xyz']


def test_validate_binding_rejects_missing_draw_or_pass():
    assert not validate_binding(binding_log(draw=False), 0)['checks']['draw']
    assert not validate_binding(binding_log(passline=False), 0)['passed']
    assert not validate_binding(binding_log(), 1)['passed']


def fixed_run_dir(tmp_path, tamper=False, passed=True):
    stage = tmp_path / 'stage'
    stage.mkdir()
    files = {'BindingCheck.exe': b'exe', 'Check.cmd': b'cmd', 'arena.json': b'{}',
             'p2-kogane-profile.txt': b'profile', 'p2-kogane-bank.txt': b'bank',
             'p2-kogane-actors.txt': b'actors', 'p2-kogane-native.txt': b'sidecar'}
    hashes = {}
    for name, data in files.items():
        if tamper and name == 'p2-kogane-native.txt':
            data = b'tampered'
        (stage / name).write_bytes(data)
        hashes[name] = hashlib.sha256({'p2-kogane-native.txt': b'sidecar'}.get(name, data)
                                      if tamper else data).hexdigest()
    manifest = {'schema': 1, 'native_head': '7faa64475176658af85e2f558858c6d660cd4d20',
                'command': ['BindingCheck.exe', '--experimental-pikmin2-room'],
                'files': hashes, 'evidence': {'passed': passed, 'checks': {}}}
    (stage / 'fixed-manifest.json').write_text(json.dumps(manifest))
    return stage, hashes


def test_verify_fixed_run_intact(tmp_path):
    stage, hashes = fixed_run_dir(tmp_path)
    receipt = tmp_path / 'kogane-install.json'
    receipt.write_text(json.dumps({'profile_config_sha256': hashes['p2-kogane-profile.txt'],
                                   'bank_config_sha256': hashes['p2-kogane-bank.txt'],
                                   'actors_config_sha256': hashes['p2-kogane-actors.txt']}))
    result = verify_fixed_run(stage, receipt)
    assert result['passed']
    assert result['lane_configs_consumed_unchanged']


def test_verify_fixed_run_tampered_file(tmp_path):
    stage, _ = fixed_run_dir(tmp_path, tamper=True)
    result = verify_fixed_run(stage)
    assert not result['passed']
    assert result['mismatched'] == ['p2-kogane-native.txt']


def test_verify_fixed_run_failed_evidence_rejected(tmp_path):
    stage, _ = fixed_run_dir(tmp_path, passed=False)
    assert not verify_fixed_run(stage)['passed']


def test_verify_fixed_run_lane_config_drift_detected(tmp_path):
    stage, _ = fixed_run_dir(tmp_path)
    receipt = tmp_path / 'kogane-install.json'
    receipt.write_text(json.dumps({'profile_config_sha256': '0' * 64,
                                   'bank_config_sha256': '0' * 64,
                                   'actors_config_sha256': '0' * 64}))
    result = verify_fixed_run(stage, receipt)
    assert not result['passed']
    assert result['lane_configs_consumed_unchanged'] is False


def test_verify_fixed_run_bad_schema_rejected(tmp_path):
    stage = tmp_path / 'stage'
    stage.mkdir()
    (stage / 'fixed-manifest.json').write_text(json.dumps({'schema': 2}))
    with pytest.raises(ValueError, match='schema'):
        verify_fixed_run(stage)
