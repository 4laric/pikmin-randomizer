"""Compile-and-run gate for the lane 12 captain/squad engine host adapter.

Follows tests/test_pikmin2_captain_live.py for tree resolution: resolve the
native tree via PIKMIN_NATIVE_ROOT first, then ROOT/native, then ROOT/engine.
Compile the standalone adapter test against the native pc_port headers with
-Werror and require its PASS banner. This is an engine-double test (fake
Navi/Piki host ops), not a live two-captain runtime. Skips when g++ or the
adapter headers are absent from every tree.
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


def test_captain_adapter_engine_double(tmp_path):
    port, tools = _source_root('pc_p2_captain.h', 'test_p2_captain_adapter.cpp')
    if port is None:
        pytest.skip('native lane 12 captain adapter headers not present')
    compiler = _compiler()
    if compiler is None:
        pytest.skip('g++ required for native contract')
    exe = tmp_path / 'test_p2_captain_adapter.exe'
    subprocess.run(
        [str(compiler), '-std=c++17', '-Wall', '-Wextra', '-Werror',
         '-I', str(port), str(tools / 'test_p2_captain_adapter.cpp'), '-o', str(exe)],
        check=True, capture_output=True, text=True, env=_compile_env(compiler))
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30,
                         env=_compile_env(compiler))
    assert run.returncode == 0, run.stderr
    assert 'PASS P2_CAPTAIN_ADAPTER' in run.stdout
