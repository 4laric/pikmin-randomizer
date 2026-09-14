import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows job/lease runner')
SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/p2_gl_lane.py'


@pytest.fixture
def runner():
    spec = importlib.util.spec_from_file_location('gl_lane', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cross_process_leases_and_exclusive_rollback(runner, tmp_path):
    # B remains available while A is held; exclusive fails without retaining B.
    with runner.leases(tmp_path, ['A']):
        with runner.leases(tmp_path, ['B']):
            pass
        code = "import sys;sys.path.insert(0,sys.argv[1]);from p2_gl_lane import leases;from pathlib import Path\nwith leases(Path(sys.argv[2]),['A']): pass"
        child = subprocess.run([sys.executable, '-c', code, str(SCRIPT.parent), str(tmp_path)], capture_output=True)
        assert child.returncode != 0
        with pytest.raises(RuntimeError, match='Busy'):
            with runner.leases(tmp_path, ['A', 'B']):
                pass
        with runner.leases(tmp_path, ['B']):
            pass
    with runner.leases(tmp_path, ['A', 'B']):
        pass


def test_b_review_and_hash_required(runner, tmp_path):
    work = tmp_path / 'run'
    work.mkdir()
    exe = Path(sys.base_prefix) / 'python.exe'
    spec = dict(executable=str(exe), cwd=str(work), sha256=hashlib.sha256(exe.read_bytes()).hexdigest(), timeout_seconds=1)
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match='reviewed'):
        runner.checked_spec(path, 'B', tmp_path)
    spec['sha256'] = '0'*64
    path.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match='hash'):
        runner.checked_spec(path, 'A', tmp_path)


def test_timeout_kills_descendants_and_releases(runner, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'shared_output', lambda: tmp_path)
    work=tmp_path/'run'
    work.mkdir()
    marker=work/'escaped.txt'
    grandchild=f"import time;from pathlib import Path;time.sleep(3);Path({str(marker)!r}).write_text('escaped')"
    child=f"import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',{grandchild!r}]);time.sleep(30)"
    exe=Path(sys.base_prefix) / 'python.exe'
    spec=dict(executable=str(exe),cwd=str(work),sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
              timeout_seconds=0.5,args=['-c',child])
    path=tmp_path/'spec.json'
    path.write_text(json.dumps(spec))
    assert runner.run(path,'A')==124
    import time
    time.sleep(3.2)
    assert not marker.exists()
    with runner.leases(tmp_path/'gl-lanes',['A','B']):
        pass


def test_nonzero_exit_recorded(runner, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'shared_output', lambda: tmp_path)
    work=tmp_path/'run'
    work.mkdir()
    exe=Path(sys.base_prefix) / 'python.exe'
    path=tmp_path/'spec.json'
    path.write_text(json.dumps(dict(executable=str(exe),cwd=str(work),
        sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),timeout_seconds=5,args=['-c','raise SystemExit(7)'])))
    assert runner.run(path,'A')==7
    report=json.loads(next((tmp_path/'gl-lanes').glob('run-*/result.json')).read_text())
    assert report['status']=='failed'

