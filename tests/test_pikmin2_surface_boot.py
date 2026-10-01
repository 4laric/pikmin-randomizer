"""Strict course dispatch refusals before SDL/content/session startup (#738)."""
import os
from pathlib import Path
import subprocess
import pytest
from scripts.stage_pikmin2_surface_boot import stage_table


def test_private_registration_preserves_existing_table_and_refuses_duplicates():
    original = b'new_map visible { name "Practice" id 0 file stages/practice.ini }\n'
    result = stage_table(original)
    assert result.startswith(original)
    assert result.count(b'file stages/p2_tutorial.ini') == 1
    with pytest.raises(ValueError, match='already registered'):
        stage_table(result)


@pytest.mark.parametrize('arguments', [
    ['--experimental-pikmin2-surface'],
    ['--experimental-pikmin2-surface','forest'],
    ['--experimental-pikmin2-surface','../tutorial'],
    ['--experimental-pikmin2-surface','tutorial','--experimental-pikmin2-surface','tutorial'],
    ['--experimental-pikmin2-surface','tutorial','--experimental-pikmin2-room'],
    ['--experimental-pikmin2-room','--experimental-pikmin2-surface','tutorial'],
    ['--experimental-pikmin2-surface','tutorial','--experimental-challenge-level','0'],
    ['--experimental-challenge-level','0','--experimental-pikmin2-surface','tutorial'],
    ['--experimental-pikmin2-surface','tutorial','--experimental-challenge-stage','ch_NARI_01kusachi'],
    ['--experimental-challenge-stage','ch_NARI_01kusachi','--experimental-pikmin2-surface','tutorial'],
    ['--experimental-pikmin2-surface','tutorial','--randomizer-seed','missing.bootstrap'],
    ['--experimental-pikmin2-surface','tutorial','--bbft-port','1234'],
])
def test_native_dispatch_refuses_foreign_or_conflicting_sessions(arguments, tmp_path):
    value = os.environ.get('P2_SURFACE_EXE')
    if not value:
        pytest.skip('Set P2_SURFACE_EXE to the pinned current private native executable')
    env = dict(os.environ)
    env.pop('BBFT_PORT', None)
    result = subprocess.run([str(Path(value).resolve()), *arguments], cwd=tmp_path,
                            env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2, result.stdout+result.stderr
    assert 'P2_SURFACE_BOOT course=' not in result.stdout
    assert not list(tmp_path.glob('save*'))


def test_native_dispatch_refuses_inherited_bbft_port(tmp_path):
    value = os.environ.get('P2_SURFACE_EXE')
    if not value:
        pytest.skip('Set P2_SURFACE_EXE to the pinned current private native executable')
    result = subprocess.run([str(Path(value).resolve()), '--experimental-pikmin2-surface', 'tutorial'],
                            cwd=tmp_path, env=dict(os.environ, BBFT_PORT='1234'),
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert 'Surface boot cannot use BBFT sessions' in result.stderr
