from pathlib import Path
import shutil
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]
def test_preallocated_interpolation(tmp_path):
    compiler=shutil.which('g++')
    if not compiler:pytest.skip('g++ required')
    exe=tmp_path/'probe.exe'
    subprocess.run([compiler,'-std=c++17','-O2','-Wall','-Wextra','-Werror',
                    '-I'+str(ROOT/'engine/pc_port'),str(ROOT/'engine/tools/test_p2_pose_into.cpp'),'-o',str(exe)],check=True,capture_output=True)
    assert 'PASS preallocated interpolation' in subprocess.check_output([str(exe)],text=True)
