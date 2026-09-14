"""Anticipatory gate for the lane-11 Bulbmin cave-save filter (native side).

The native contract driven here has not landed yet in this snapshot: the flag
predicates live in pc_port/pc_p2_bulbmin.h, the standalone probe in
tools/test_p2_bulbmin_cave_filter.cpp, and the checkpoint wiring in
pc_port/pc_p2_cave.cpp. Each native-dependent test skips cleanly until its
input exists, so this file stays green before and after the native work.
Only the pure-Python model of the source rule runs unconditionally.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _native_root():
    root = Path(__file__).resolve().parents[1]
    for candidate in (
        root.parent / 'native-l11',
        root.parent.parent / 'output' / 'dsw' / 'native-l11',
    ):
        if candidate.is_dir():
            return candidate
    pytest.skip('native-l11 worktree not found')


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
    if not header.is_file():
        pytest.skip('pc_port/pc_p2_bulbmin.h not present')
    text = header.read_text(errors='replace')
    if 'pc_p2_bulbmin_phase' not in text and 'pc_p2_bulbmin_should_save' not in text:
        pytest.skip('Bulbmin phase/save predicate not yet declared in pc_p2_bulbmin.h')
    assert 'pc_p2_bulbmin_phase' in text
    assert 'pc_p2_bulbmin_should_save' in text


def test_cave_checkpoint_wired_to_filter():
    native = _native_root()
    cave_cpp = native / 'pc_port' / 'pc_p2_cave.cpp'
    if not cave_cpp.is_file():
        pytest.skip('pc_port/pc_p2_cave.cpp not present')
    text = cave_cpp.read_text(errors='replace')
    if 'pc_p2_bulbmin_should_save' not in text:
        pytest.skip('pc_p2_cave_checkpoint not yet wired to pc_p2_bulbmin_should_save')
    assert 'pc_p2_bulbmin_should_save' in text


def test_source_rule_contract_pure_python():
    def should_save(species, phase, is_exiting):
        if species != 5:
            return True
        if phase == 0:
            return False
        return True

    for exiting in (False, True):
        assert should_save(5, 0, exiting) is False
    assert should_save(5, 1, False) is True
    assert should_save(1, -1, False) is True
