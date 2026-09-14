"""Compile-and-run gate for the lane 12 per-captain squad split/follow policy.

Follows tests/test_pikmin2_captain_adapter.py: compile the standalone
engine-free policy test against the native pc_port headers with -Werror and
require its PASS banner. This is a policy/contract test (no Navi/Piki object),
not a live two-captain runtime. Skips when g++ or the lane's native copy of the
policy headers is absent, so it passes before lane 01 exports them.
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
        yield base / 'output' / 'native-sub3-follow' / 'pc_port'


def _compiler():
    found = shutil.which('g++')
    if found:
        return found
    fallback = Path('C:/msys64/mingw64/bin/g++.exe')
    return str(fallback) if fallback.is_file() else None


def _source_root():
    for port in _port_candidates():
        if (port / 'pc_p2_squad_policy.h').is_file():
            tools = port.parent / 'tools'
            if (tools / 'test_p2_squad_policy.cpp').is_file():
                return port, tools
    return None, None


def test_captain_squad_split_policy(tmp_path):
    port, tools = _source_root()
    if port is None:
        pytest.skip('native lane 12 squad policy headers not present')
    compiler = _compiler()
    if compiler is None:
        pytest.skip('g++ required for native contract')
    exe = tmp_path / 'test_p2_squad_policy.exe'
    subprocess.run(
        [compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
         '-I', str(port), str(tools / 'test_p2_squad_policy.cpp'), '-o', str(exe)],
        check=True, capture_output=True, text=True)
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    assert 'PASS P2_SQUAD_POLICY' in run.stdout


def _navi_mgr_candidates():
    found = []
    for base in (ROOT, *ROOT.parents):
        for rel in (base / 'engine/src/plugPikiKando/naviMgr.cpp',
                    base / 'native/src/plugPikiKando/naviMgr.cpp',
                    base / 'output/native-sub3-follow/src/plugPikiKando/naviMgr.cpp'):
            if rel.is_file() and rel not in found:
                found.append(rel)
    return found


def test_inactive_captain_follow_hook_is_gated():
    """The follow hook is present but only reachable with a second Navi."""
    candidates = _navi_mgr_candidates()
    if not candidates:
        pytest.skip('native NaviMgr source not present')
    assert any('update_inactive_captain_follow()' in p.read_text(errors='replace')
               and 'mNumObjects > 1' in p.read_text(errors='replace')
               for p in candidates)
