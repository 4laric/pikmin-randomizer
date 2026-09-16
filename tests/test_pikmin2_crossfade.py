"""Compile and exercise the production local-TRS crossfade and skinning headers."""
import shutil
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

def test_native_crossfade(tmp_path):
    compiler = shutil.which('g++')
    if not compiler:
        pytest.skip('g++ required')
    exe = tmp_path / 'crossfade.exe'
    subprocess.run([compiler, '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-I'+str(ROOT/'engine/pc_port'),
                    str(ROOT/'engine/tools/test_p2_crossfade.cpp'), '-o', str(exe)],
                   check=True, capture_output=True)
    assert 'PASS skeletal crossfade' in subprocess.check_output([str(exe)], text=True)
