"""Compile-and-run gate for the lane 12 per-captain squad split/follow policy.

Follows tests/test_pikmin2_captain_live.py for tree resolution: resolve the
native tree via PIKMIN_NATIVE_ROOT first, then ROOT/native, then ROOT/engine.
Compile the standalone policy test against the native pc_port headers with
-Werror and require its PASS banner. This is a policy/contract test (no
Navi/Piki object), not a live two-captain runtime. Skips when g++ or the policy
headers are absent from every tree.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _native_roots():
    roots = []
    env_root = os.environ.get('PIKMIN_NATIVE_ROOT', '')
    if env_root:
        roots.append(Path(env_root))
    for candidate in (ROOT / 'native', ROOT / 'engine'):
        if candidate.is_dir():
            roots.append(candidate)
    seen = set()
    ordered = []
    for root in roots:
        key = str(root.resolve())
        if key not in seen:
            seen.add(key)
            ordered.append(root)
    return ordered


def _compiler():
    found = shutil.which('g++')
    if found:
        return Path(found)
    fallback = Path('C:/msys64/mingw64/bin/g++.exe')
    return fallback if fallback.is_file() else None


def _compile_env(compiler):
    env = dict(os.environ)
    env['PATH'] = str(compiler.parent) + os.pathsep + env.get('PATH', '')
    return env


def _source_root(port_header, test_source):
    for root in _native_roots():
        port = root / 'pc_port'
        tools = root / 'tools'
        if (port / port_header).is_file() and (tools / test_source).is_file():
            return port, tools
    return None, None


def test_captain_squad_split_policy(tmp_path):
    port, tools = _source_root('pc_p2_squad_policy.h', 'test_p2_squad_policy.cpp')
    if port is None:
        pytest.skip('native lane 12 squad policy headers not present')
    compiler = _compiler()
    if compiler is None:
        pytest.skip('g++ required for native contract')
    exe = tmp_path / 'test_p2_squad_policy.exe'
    subprocess.run(
        [str(compiler), '-std=c++17', '-Wall', '-Wextra', '-Werror',
         '-I', str(port), str(tools / 'test_p2_squad_policy.cpp'), '-o', str(exe)],
        check=True, capture_output=True, text=True, env=_compile_env(compiler))
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    assert 'PASS P2_SQUAD_POLICY' in run.stdout


def _navi_mgr_candidates():
    found = []
    for root in _native_roots():
        p = root / 'src' / 'plugPikiKando' / 'naviMgr.cpp'
        if p.is_file() and p not in found:
            found.append(p)
    return found


def test_inactive_captain_follow_hook_is_gated():
    """The follow hook is present but only reachable with a second Navi."""
    candidates = _navi_mgr_candidates()
    if not candidates:
        pytest.skip('native NaviMgr source not present')
    assert any('update_inactive_captain_follow()' in p.read_text(errors='replace')
               and 'mNumObjects > 1' in p.read_text(errors='replace')
               for p in candidates)
