"""Compile-and-run gate for the lane-11 dedicated Mother Bulbmin path (#131).

Compiles the sub-slice-3 harness tools/test_p2_bulbmin_mother.cpp against the
native pc_port headers and requires its PASS banner. The harness is an
engine-double: it proves a labeled mother identity is registered, the source
ten-body birthChildren flock is driven, one body is whistled into the captain
ownership table, mother death releases only wild dependents, and the cave save
filter keeps only whistled Bulbmin on a descent and drops all on an exit. There
is no LeafChappy model and no rendered run; skips when the native copy or g++ is
absent.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LANES = (
    'native-sub3-mother',
    'native-sub3-follow',
    'native-sub3-states',
    'native-submerged',
    'native-sub2-bulbmin',
    'native-sub-bulbmin',
)


def _compiler():
    found = shutil.which('g++')
    if found:
        return found
    fallback = Path('C:/msys64/mingw64/bin/g++.exe')
    return str(fallback) if fallback.is_file() else None


def _source_root():
    for lane in LANES:
        for base in (ROOT, *ROOT.parents):
            port = base / 'output' / lane / 'pc_port'
            tools = port.parent / 'tools'
            if (port / 'pc_p2_bulbmin.h').is_file() and \
                    (tools / 'test_p2_bulbmin_mother.cpp').is_file():
                return port, tools
    for base in (ROOT / 'engine', ROOT / 'native'):
        port = base / 'pc_port'
        tools = base / 'tools'
        if (port / 'pc_p2_bulbmin.h').is_file() and \
                (tools / 'test_p2_bulbmin_mother.cpp').is_file():
            return port, tools
    return None, None


def test_bulbmin_mother_harness_builds_and_passes(tmp_path):
    port, tools = _source_root()
    if port is None:
        pytest.skip('native dedicated Mother Bulbmin harness is not present')
    compiler = _compiler()
    if compiler is None:
        pytest.skip('g++ required for native mother harness')

    exe = tmp_path / 'test_p2_bulbmin_mother.exe'
    subprocess.run(
        [compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
         '-I', str(port), str(tools / 'test_p2_bulbmin_mother.cpp'),
         '-o', str(exe)],
        check=True, capture_output=True, text=True)
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    assert 'PASS P2_BULBMIN_MOTHER' in run.stdout


def test_bulbmin_mother_is_wired_additively():
    sources = []
    for lane in LANES:
        for base in (ROOT, *ROOT.parents):
            root = base / 'output' / lane
            bulbmin = root / 'pc_port' / 'pc_p2_bulbmin.cpp'
            preview = root / 'pc_port' / 'pc_p2_preview.cpp'
            header = root / 'pc_port' / 'pc_p2_bulbmin.h'
            if bulbmin.is_file() and preview.is_file() and header.is_file():
                sources.append((header.read_text(errors='replace'),
                                bulbmin.read_text(errors='replace'),
                                preview.read_text(errors='replace')))
    for base in (ROOT / 'engine', ROOT / 'native'):
        bulbmin = base / 'pc_port' / 'pc_p2_bulbmin.cpp'
        preview = base / 'pc_port' / 'pc_p2_preview.cpp'
        header = base / 'pc_port' / 'pc_p2_bulbmin.h'
        if bulbmin.is_file() and preview.is_file() and header.is_file():
            sources.append((header.read_text(errors='replace'),
                            bulbmin.read_text(errors='replace'),
                            preview.read_text(errors='replace')))
    if not sources:
        pytest.skip('native dedicated Mother Bulbmin sources not present')

    # Dedicated registration API plus its opt-in preview wiring.
    assert any('registerMother' in header and 'motherDied' in header
               for header, _, _ in sources)
    assert any('pc_p2_bulbmin_attach_mother_ex' in bulbmin
               for _, bulbmin, _ in sources)
    assert any('pc_p2_bulbmin_attach_dedicated_mother' in preview
               for _, _, preview in sources)
    # The prior Kochappy auto-attach path stays wired (default behavior).
    assert any('pc_p2_bulbmin_attach_mother' in preview
               and 'pc_p2_kochappy_first_registered' in preview
               for _, _, preview in sources)
