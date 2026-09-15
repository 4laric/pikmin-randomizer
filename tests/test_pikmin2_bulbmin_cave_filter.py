"""Lane 11: Bulbmin cave-checkpoint filter contract (pc_p2_bulbmin_should_save).

Set PIKMIN_NATIVE_ROOT to a native worktree containing the predicate; otherwise these
tests skip. The compiled probe test needs MinGW g++ on PATH."""
import shutil
import subprocess
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _native_root():
    env = os.environ.get('PIKMIN_NATIVE_ROOT')
    candidates = [Path(env)] if env else []
    candidates.append(ROOT / 'native')
    for candidate in candidates:
        if (candidate / 'pc_port' / 'pc_p2_bulbmin.h').is_file():
            return candidate
    pytest.skip('native worktree not found (set PIKMIN_NATIVE_ROOT)')


def _compiler():
    found = shutil.which('g++')
    if found:
        return found
    fallback = Path('C:/msys64/mingw64/bin/g++.exe')
    if fallback.is_file():
        return str(fallback)
    return None


def test_cave_filter_tool_builds_and_passes(tmp_path):
    native = _native_root()
    tool_cpp = native / 'tools' / 'test_p2_bulbmin_cave_filter.cpp'
    header = native / 'pc_port' / 'pc_p2_bulbmin.h'
    if not tool_cpp.is_file() or not header.is_file():
        pytest.skip('native Bulbmin cave-filter tool/header not present')
    compiler = _compiler()
    if compiler is None:
        pytest.skip('g++ required to compile the cave-filter tool')

    exe = tmp_path / 'test_p2_bulbmin_cave_filter.exe'
    subprocess.run(
        [compiler, '-std=c++17', '-Wall', '-Wextra',
         '-I', str(native / 'pc_port'),
         '-I', str(native / 'tools'),
         str(tool_cpp), '-o', str(exe)],
        check=True, capture_output=True, text=True, cwd=str(tmp_path))
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    assert 'PASS P2_BULBMIN_CAVE_FILTER' in run.stdout


def test_predicate_is_declared():
    native = _native_root()
    header = native / 'pc_port' / 'pc_p2_bulbmin.h'
    text = header.read_text(errors='replace')
    assert 'pc_p2_bulbmin_phase' in text
    assert 'pc_p2_bulbmin_should_save' in text


def test_cave_checkpoint_wired_to_filter():
    native = _native_root()
    cave_cpp = native / 'pc_port' / 'pc_p2_cave.cpp'
    text = cave_cpp.read_text(errors='replace')
    assert 'pc_p2_bulbmin_transition' in text
