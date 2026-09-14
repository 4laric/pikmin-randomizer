"""Compile-and-run gate for the lane-11 Bulbmin engine bridge (#131).

Compiles tools/test_p2_bulbmin_bridge.cpp against the native pc_port headers
and requires its PASS banner, then checks the bridge is registered and called
additively. Skips when no g++ or no native copy of the sources is present, so it
passes before lane 01 exports the work into engine/.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _port_candidates():
    yield ROOT / 'engine' / 'pc_port'
    yield ROOT / 'native' / 'pc_port'
    for lane in ('native-sub-bulbmin', 'native-sub2-bulbmin'):
        for base in (ROOT, *ROOT.parents):
            yield base / 'output' / lane / 'pc_port'


def _compiler():
    found = shutil.which('g++')
    if found:
        return found
    fallback = Path('C:/msys64/mingw64/bin/g++.exe')
    return str(fallback) if fallback.is_file() else None


def _source_root():
    for port in _port_candidates():
        if (port / 'pc_p2_bulbmin.h').is_file():
            tools = port.parent / 'tools'
            if (tools / 'test_p2_bulbmin_bridge.cpp').is_file():
                return port, tools
    return None, None


def test_bulbmin_bridge_builds_and_passes(tmp_path):
    port, tools = _source_root()
    if port is None:
        pytest.skip('native Bulbmin bridge is not present')
    compiler = _compiler()
    if compiler is None:
        pytest.skip('g++ required for native bridge')

    exe = tmp_path / 'test_p2_bulbmin_bridge.exe'
    subprocess.run(
        [compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
         '-I', str(port), str(tools / 'test_p2_bulbmin_bridge.cpp'),
         '-o', str(exe)],
        check=True, capture_output=True, text=True)
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    assert 'PASS P2_BULBMIN_BRIDGE' in run.stdout


def test_bulbmin_bridge_is_registered_additively():
    sources = []
    for base in (ROOT, *ROOT.parents):
        cmake = base / 'output' / 'native-sub-bulbmin' / 'CMakeLists.txt'
        preview = base / 'output' / 'native-sub-bulbmin' / 'pc_port' / 'pc_p2_preview.cpp'
        if cmake.is_file() and preview.is_file():
            sources.append((cmake.read_text(errors='replace'),
                            preview.read_text(errors='replace')))
    for base in (ROOT / 'engine', ROOT / 'native'):
        cmake = base / 'CMakeLists.txt'
        preview = base / 'pc_port' / 'pc_p2_preview.cpp'
        if cmake.is_file() and preview.is_file():
            sources.append((cmake.read_text(errors='replace'),
                            preview.read_text(errors='replace')))
    if not sources:
        pytest.skip('native Bulbmin bridge sources not present')

    assert any('pc_port/pc_p2_bulbmin.cpp' in cmake for cmake, _ in sources)
    assert any('pc_p2_bulbmin_setup();' in preview for _, preview in sources)


def _lane_files():
    """(bulbmin.cpp, preview.cpp, navi.cpp, pikiMgr.cpp, kochappy.cpp)."""
    for base in (ROOT, *ROOT.parents):
        root = base / 'output' / 'native-sub2-bulbmin'
        bulbmin = root / 'pc_port' / 'pc_p2_bulbmin.cpp'
        if not bulbmin.is_file():
            continue
        yield (
            bulbmin.read_text(errors='replace'),
            (root / 'pc_port' / 'pc_p2_preview.cpp').read_text(errors='replace'),
            (root / 'src' / 'plugPikiKando' / 'navi.cpp').read_text(errors='replace'),
            (root / 'src' / 'plugPikiKando' / 'pikiMgr.cpp').read_text(errors='replace'),
            (root / 'pc_port' / 'pc_p2_kochappy.cpp').read_text(errors='replace'),
        )


def test_bulbmin_driver_is_wired_additively():
    files = list(_lane_files())
    if not files:
        pytest.skip('native lane-11 Bulbmin driver sources not present')
    assert any('pc_p2_bulbmin_drive_birth' in bulbmin
               and 'pc_p2_bulbmin_attach_mother' in bulbmin
               for bulbmin, _, _, _, _ in files)
    # The birth hook is called from the existing Chappy/Kochappy registration.
    assert any('pc_p2_bulbmin_attach_mother' in preview
               and 'pc_p2_kochappy_first_registered' in preview
               for _, preview, _, _, _ in files)
    # The real whistle path and the dependent-forget lifecycle are hooked.
    assert any('pc_p2_bulbmin_call_pikis' in navi for _, _, navi, _, _ in files)
    assert any('pc_p2_bulbmin_forget' in pikimgr for _, _, _, pikimgr, _ in files)
    assert any('pc_p2_bulbmin_proxy_forget' in kochappy
               and 'pc_p2_kochappy_first_registered' in kochappy
               for _, _, _, _, kochappy in files)
