"""Tests for experimental.pikmin2_minihoudai_assets (lane rd-p2-minihoudai-extractor, #849).

Fail-closed behavior is hermetic (no disc needed). Real-ISO tests are gated on
the legal local GPVE01 disc and prove the extraction satisfies the existing
family installer contract (``_read_identity_source(source, 78, 'MiniHoudai')``
plus the ``p2-groink-teki.txt`` actor sidecar). No retail bytes are committed.
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experimental import pikmin2_minihoudai_assets as minihoudai  # noqa: E402

ISO = Path('C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso')
NEEDS_ISO = pytest.mark.skipif(not ISO.is_file(), reason='no local GPVE01 disc image')

HEX64 = __import__('re').compile(r'^[0-9a-f]{64}$')


def test_rejects_missing_iso(tmp_path):
    with pytest.raises(ValueError):
        minihoudai.extract(tmp_path / 'missing.iso', tmp_path / 'out')


def test_rejects_existing_output(tmp_path):
    out = tmp_path / 'out'
    out.mkdir()
    with pytest.raises(ValueError):
        minihoudai.extract(tmp_path / 'missing.iso', out)


def test_rejects_bad_pose_limit(tmp_path):
    for bad in (1, 9, '3', 3.0, None):
        with pytest.raises(ValueError):
            minihoudai.extract(tmp_path / 'missing.iso', tmp_path / 'out', bad)


def test_pose_names_are_deterministic_and_slot_ordered():
    assert minihoudai.pose_name('walk', 0) == 'minihoudai_walk_00.mod'
    assert minihoudai.pose_name('attack1', 12) == 'minihoudai_attack1_12.mod'


@NEEDS_ISO
def test_extract_satisfies_installer_identity_contract(tmp_path):
    out = tmp_path / 'MiniHoudai'
    result = minihoudai.extract(ISO, out)
    identity = json.loads((out / 'identity.json').read_text(encoding='utf-8'))
    assert identity == {'schema': 1, 'source_id': 78, 'enum_name': 'MiniHoudai'}
    assert (result['species'], result['enemy_id'], result['enum_name']) == \
        ('MiniHoudai', 78, 'MiniHoudai')
    # The existing family installer pre-flight is authoritative for the contract.
    from experimental.pikmin2_family_install import _validate_minihoudai
    _validate_minihoudai(out)


@NEEDS_ISO
def test_extract_manifest_shape_and_pose_slots(tmp_path):
    out = tmp_path / 'MiniHoudai'
    result = minihoudai.extract(ISO, out)
    assert result['schema'] == 1 and result['native_ready'] is False
    assert result['disc_id'] == 'GPVE01'
    assert HEX64.fullmatch(result['model_sha256'])
    assert result['joints'].count('kuti') == 1
    assert result['muzzle_joint'] == result['joints'].index('kuti')
    assert result['general']['health'] == 1200.0
    assert len(result['clips']) == 8
    for clip in result['clips']:
        assert HEX64.fullmatch(clip['sha256'])
        assert clip['source_frames'] >= 1
        if clip['status'] == 'converted':
            # Contiguous _00.. slots, one muzzle sample per pose.
            expected = [minihoudai.pose_name(Path(clip['file']).stem, i)
                        for i in range(len(clip['poses']))]
            assert [p['file'] for p in clip['poses']] == expected
            assert [s['frame'] for s in clip['muzzle_samples']] == \
                [p['frame'] for p in clip['poses']]
            for pose in clip['poses']:
                assert (out / pose['file']).is_file()
                assert pose['sha256'] == hashlib.sha256(
                    (out / pose['file']).read_bytes()).hexdigest()
        else:
            assert clip['unsupported_reason']
    assert sum(len(c['poses']) for c in result['clips']) == 24
    # Source metadata preserved verbatim alongside the manifest.
    for name in ('enemy.bmd', 'enemyparm.txt', 'enemycoll.txt',
                 'enemyanimmgr.txt', 'enemystoneinfo.txt',
                 'fixed-enemyparm.txt', 'minihoudai.json'):
        assert (out / name).is_file()
    stored = json.loads((out / 'minihoudai.json').read_text(encoding='utf-8'))
    assert stored == json.loads(json.dumps(result, sort_keys=True))


@NEEDS_ISO
def test_extract_is_deterministic(tmp_path):
    first = tmp_path / 'first'
    second = tmp_path / 'second'
    minihoudai.extract(ISO, first)
    minihoudai.extract(ISO, second)
    left = sorted(p.relative_to(first).as_posix() for p in first.rglob('*') if p.is_file())
    right = sorted(p.relative_to(second).as_posix() for p in second.rglob('*') if p.is_file())
    assert left == right
    for name in left:
        assert (first / name).read_bytes() == (second / name).read_bytes()


@NEEDS_ISO
def test_adapter_stages_sidecar_from_extraction(tmp_path):
    from experimental.pikmin2_family_install import _adapt_minihoudai
    source = tmp_path / 'MiniHoudai'
    minihoudai.extract(ISO, source)
    run = tmp_path / 'run'
    run.mkdir()
    receipt = _adapt_minihoudai(source, run, [(1254096625, 'MiniHoudai')])
    assert receipt['species'] == 'MiniHoudai' and receipt['source_id'] == 78
    sidecar = run / 'p2-groink-teki.txt'
    assert sidecar.is_file()
    assert sidecar.read_text(encoding='ascii').split()[0] == 'P2_GROINK_TEKI_1'
    with pytest.raises(Exception):
        _adapt_minihoudai(source, run, [(1, 'Sokkuri')])
