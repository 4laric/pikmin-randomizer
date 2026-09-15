"""Compile-and-run plus live-source seam gate for the lane 12 slot-0 captain/squad adapter.

Tests 1-2 mirror tests/test_pikmin2_captain_adapter.py and
tests/test_pikmin2_captain_squad_split.py: compile the standalone engine-double
test against the native pc_port headers with -Werror and require its PASS banner.

Tests 3-4 read the full native worktree sources (pc_port/ and src/plugPikiKando/)
without compiling, so CI catches a missing LIVE seam that the exported engine/
mirror may not yet carry. A marker is only a failure when its file is present in
some tree but the marker is absent; if the file is absent everywhere, we skip.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_LIVE_TREE = Path('C:/Users/alari/pikmin-randomizer/output/dsw/native-l12')


def _port_candidates():
    # Prefer the exported engine/ tree, then the shared native/ checkout, then
    # the lane's private full worktree (live hooks live here).
    yield ROOT / 'engine' / 'pc_port'
    yield ROOT / 'native' / 'pc_port'
    yield _LIVE_TREE / 'pc_port'
    for base in (ROOT, *ROOT.parents):
        yield base / 'output' / 'native-l12' / 'pc_port'


def _tree_roots():
    # TREE roots: each contains pc_port/ and src/plugPikiKando/.
    roots = [ROOT / 'engine', ROOT / 'native', _LIVE_TREE]
    for base in (ROOT, *ROOT.parents):
        candidate = base / 'output' / 'native-l12'
        if candidate.is_dir():
            roots.append(candidate)
    seen = set()
    ordered = []
    for root in roots:
        key = str(root)
        if key not in seen:
            seen.add(key)
            ordered.append(root)
    return ordered


def _compiler():
    found = shutil.which('g++')
    if found:
        return found
    fallback = Path('C:/msys64/mingw64/bin/g++.exe')
    return str(fallback) if fallback.is_file() else None


def _source_root(header, tool):
    for port in _port_candidates():
        if (port / header).is_file():
            tools = port.parent / 'tools'
            if (tools / tool).is_file():
                return port, tools
    return None, None


def _compile_and_run(port, tools, tool, exe):
    compiler = _compiler()
    if compiler is None:
        pytest.skip('g++ required for native contract')
    env = dict(os.environ)
    bin_dir = str(Path(compiler).resolve().parent)
    if bin_dir not in env.get('PATH', ''):
        env['PATH'] = bin_dir + os.pathsep + env.get('PATH', '')
    subprocess.run(
        [compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
         '-I', str(port), str(tools / tool), '-o', str(exe)],
        check=True, capture_output=True, text=True, env=env)
    return subprocess.run([str(exe)], capture_output=True, text=True,
                          timeout=30, env=env)


def test_captain_adapter_engine_double(tmp_path):
    port, tools = _source_root('pc_p2_captain.h', 'test_p2_captain_adapter.cpp')
    if port is None:
        pytest.skip('native lane 12 captain adapter headers not present')
    run = _compile_and_run(
        port, tools, 'test_p2_captain_adapter.cpp',
        tmp_path / 'test_p2_captain_adapter.exe')
    assert run.returncode == 0, run.stderr
    assert 'PASS P2_CAPTAIN_ADAPTER' in run.stdout


def test_captain_policy_engine_double(tmp_path):
    port, tools = _source_root('pc_p2_captain_policy.h', 'test_p2_captain_policy.cpp')
    if port is None:
        pytest.skip('native lane 12 captain policy headers not present')
    run = _compile_and_run(
        port, tools, 'test_p2_captain_policy.cpp',
        tmp_path / 'test_p2_captain_policy.exe')
    assert run.returncode == 0, run.stderr
    assert 'PASS P2_CAPTAIN_POLICY' in run.stdout


def test_captain_live_hooks_present():
    roots = _tree_roots()
    checks = [
        ('pc_port/pc_p2_captain.cpp', [
            'setup_from_navi_mgr(', 'capture_captain(', 'capture_actor(',
            'drop_captured(', 'captain_handle(']),
        ('pc_port/pc_p2_captain.h', [
            'captain_handle(', 'captive_count(', 'navi_dead(']),
        ('src/plugPikiKando/naviState.cpp', [
            'informOrimaDead(', 'getAliveOrima']),
        ('src/plugPikiKando/gameCoreSection.cpp', [
            'setup_from_navi_mgr(']),
    ]
    groups = []
    for rel, markers in checks:
        copies = [root / rel for root in roots if (root / rel).is_file()]
        if copies:
            groups.append((rel, markers, [c.read_text(errors='replace') for c in copies]))
    if not groups:
        pytest.skip('live captain/squad hook sources not present in any tree')
    for rel, markers, texts in groups:
        for marker in markers:
            assert any(marker in text for text in texts), (
                f'{rel}: missing live seam {marker!r}')


def test_live_adapter_setup_is_idempotent_source_check():
    roots = _tree_roots()
    headers = [root / 'pc_port' / 'pc_p2_captain.h'
               for root in roots if (root / 'pc_port' / 'pc_p2_captain.h').is_file()]
    sources = [root / 'pc_port' / 'pc_p2_captain.cpp'
               for root in roots if (root / 'pc_port' / 'pc_p2_captain.cpp').is_file()]
    if not headers or not sources:
        pytest.skip('native captain adapter idempotency sources not present')
    assert any('bound()' in h.read_text(errors='replace') for h in headers)
    assert any('if (adapter.bound()) return true;' in c.read_text(errors='replace')
               for c in sources)
