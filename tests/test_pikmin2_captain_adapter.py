"""Compile-and-run gate for the lane 12 captain/squad engine host adapter.

Follows tests/test_pikmin2_lanes_1012_policies.py: compile the standalone
adapter test against the native pc_port headers with -Werror and require its
PASS banner. This is an engine-double test (fake Navi/Piki host ops), not a
live two-captain runtime. Skips when g++ or the lane's native copy of the
adapter headers is absent, so it passes before lane 01 exports them.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _port_candidates():
    # Prefer the exported engine/ tree, then the shared native/ checkout, then
    # the lane's private worktree under output/ (local evidence).
    yield ROOT / 'engine' / 'pc_port'
    yield ROOT / 'native' / 'pc_port'
    for base in (ROOT, *ROOT.parents):
        yield base / 'output' / 'native-sub-captains' / 'pc_port'


def _compiler():
    found = shutil.which('g++')
    if found:
        return found
    fallback = Path('C:/msys64/mingw64/bin/g++.exe')
    return str(fallback) if fallback.is_file() else None


def _source_root():
    for port in _port_candidates():
        if (port / 'pc_p2_captain.h').is_file():
            tools = port.parent / 'tools'
            if (tools / 'test_p2_captain_adapter.cpp').is_file():
                return port, tools
    return None, None


def test_captain_adapter_engine_double(tmp_path):
    port, tools = _source_root()
    if port is None:
        pytest.skip('native lane 12 captain adapter headers not present')
    compiler = _compiler()
    if compiler is None:
        pytest.skip('g++ required for native contract')
    exe = tmp_path / 'test_p2_captain_adapter.exe'
    subprocess.run(
        [compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
         '-I', str(port), str(tools / 'test_p2_captain_adapter.cpp'), '-o', str(exe)],
        check=True, capture_output=True, text=True)
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    assert 'PASS P2_CAPTAIN_ADAPTER' in run.stdout
