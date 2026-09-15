"""Compile-and-run gate for the lane-11 cave checkpoint wire format (#131/#112).

Compiles the engine-free native tool that pins `pc_port/pc_p2_cave_transfer.h`
(schema-3 Bulbmin round trip) and requires its PASS banner. Skips when no g++ or
no native copy of the header is present.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_WORKTREES = ('native-lanes1011-elecbug', 'native-submerged', 'native-sub3-states')


def _header_source():
    for base in (ROOT / 'engine', ROOT / 'native', ROOT, *ROOT.parents):
        tools = base / 'tools'
        header = base / 'pc_port' / 'pc_p2_cave_transfer.h'
        if header.is_file() and (tools / 'test_p2_cave_transfer.cpp').is_file():
            return base / 'pc_port', tools / 'test_p2_cave_transfer.cpp'
    for base in (ROOT, *ROOT.parents):
        for worktree in _WORKTREES:
            root = base / 'output' / worktree
            tools = root / 'tools'
            header = root / 'pc_port' / 'pc_p2_cave_transfer.h'
            if header.is_file() and (tools / 'test_p2_cave_transfer.cpp').is_file():
                return root / 'pc_port', tools / 'test_p2_cave_transfer.cpp'
    return None, None


def _compiler():
    found = shutil.which('g++')
    if found:
        return found
    fallback = Path('C:/msys64/mingw64/bin/g++.exe')
    return str(fallback) if fallback.is_file() else None


def test_cave_transfer_round_trip(tmp_path):
    port, source = _header_source()
    if port is None:
        pytest.skip('native pc_p2_cave_transfer.h not present')
    compiler = _compiler()
    if compiler is None:
        pytest.skip('g++ required for native contract')
    exe = tmp_path / 'test_p2_cave_transfer.exe'
    # The MinGW g++ driver and the produced exe both need the toolchain bin
    # directory on PATH (cc1plus/as/ld and the runtime DLLs). An absolute
    # compiler path is not enough: without it g++ exits 1 with no diagnostics.
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).resolve().parent) + os.pathsep + env.get('PATH', '')
    subprocess.run(
        [compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
         '-I', str(port), str(source), '-o', str(exe)],
        check=True, capture_output=True, text=True, env=env)
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30, env=env)
    assert run.returncode == 0, run.stderr
    assert 'PASS P2_CAVE_TRANSFER' in run.stdout
