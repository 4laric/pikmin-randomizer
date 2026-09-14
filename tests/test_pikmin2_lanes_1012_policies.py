"""Compile-and-run gates for the lane 11/12 native policy contracts.

Follows the pattern of tests/test_pikmin2_envmap.py and
tests/test_pikmin2_cargo_uphill.py: compile the standalone policy test against
the native pc_port headers and require its PASS banner. Skips when no g++ or no
native copy of the headers is present, so it passes before lane 01 exports them
into engine/.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _port_candidates():
    # Prefer the exported engine/ tree, then the shared native/ checkout, then
    # the lane's private worktree under any output/ ancestor (local evidence).
    yield ROOT / 'engine' / 'pc_port'
    yield ROOT / 'native' / 'pc_port'
    for base in (ROOT, *ROOT.parents):
        yield base / 'output' / 'native-lanes-1012' / 'pc_port'


_CASES = (
    ('test_p2_captain_policy.cpp', 'PASS P2_CAPTAIN_POLICY'),
    ('test_p2_bulbmin_policy.cpp', 'PASS P2_BULBMIN_POLICY'),
    ('test_p2_species_policy.cpp', 'PASS P2_SPECIES_POLICY'),
)


def _compiler():
    found = shutil.which('g++')
    if found:
        return found
    fallback = Path('C:/msys64/mingw64/bin/g++.exe')
    return str(fallback) if fallback.is_file() else None


def _source_root():
    for port in _port_candidates():
        if (port / 'pc_p2_captain_policy.h').is_file():
            # tools/ sits next to pc_port/ in the native tree.
            tools = port.parent / 'tools'
            if (tools / 'test_p2_captain_policy.cpp').is_file():
                return port, tools
    return None, None


@pytest.mark.parametrize('name,banner', _CASES)
def test_lane_policy_contract(name, banner, tmp_path):
    port, tools = _source_root()
    if port is None:
        pytest.skip('native lane 11/12 policy headers not present')
    compiler = _compiler()
    if compiler is None:
        pytest.skip('g++ required for native contract')
    exe = tmp_path / (Path(name).stem + ('.exe' if name.endswith('.cpp') else ''))
    subprocess.run(
        [compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
         '-I', str(port), str(tools / name), '-o', str(exe)],
        check=True, capture_output=True, text=True)
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    assert banner in run.stdout
