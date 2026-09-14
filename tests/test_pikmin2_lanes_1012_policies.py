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
        for worktree in ('native-sub2-captains', 'native-lanes-1012', 'native-sub-elements'):
            yield base / 'output' / worktree / 'pc_port'


_CASES = (
    ('test_p2_captain_policy.cpp', 'PASS P2_CAPTAIN_POLICY'),
    ('test_p2_captain_roster.cpp', 'PASS P2_CAPTAIN_ROSTER'),
    ('test_p2_bulbmin_policy.cpp', 'PASS P2_BULBMIN_POLICY'),
    ('test_p2_species_policy.cpp', 'PASS P2_SPECIES_POLICY'),
    ('test_p2_species_schema.cpp', 'PASS P2_SPECIES_SCHEMA'),
    ('test_p2_elemental_receivers.cpp', 'PASS P2_ELEMENTAL_RECEIVERS'),
)


def _compiler():
    found = shutil.which('g++')
    if found:
        return found
    fallback = Path('C:/msys64/mingw64/bin/g++.exe')
    return str(fallback) if fallback.is_file() else None


def _source_root(name):
    # Resolve per test file: a lane worktree may carry only a subset of the
    # policy tests, so prefer the first candidate that actually has this one.
    for port in _port_candidates():
        if (port / 'pc_p2_captain_policy.h').is_file():
            # tools/ sits next to pc_port/ in the native tree.
            tools = port.parent / 'tools'
            if (tools / name).is_file():
                return port, tools
    return None, None


@pytest.mark.parametrize('name,banner', _CASES)
def test_lane_policy_contract(name, banner, tmp_path):
    port, tools = _source_root(name)
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


def _interact_battle_candidates():
    found = []
    for base in (ROOT, *ROOT.parents):
        for rel in (base / 'engine/src/plugPikiKando/interactBattle.cpp',
                    base / 'native/src/plugPikiKando/interactBattle.cpp',
                    base / 'output/native-lanes-1012/src/plugPikiKando/interactBattle.cpp',
                    base / 'output/native-sub-elements/src/plugPikiKando/interactBattle.cpp'):
            if rel.is_file() and rel not in found:
                found.append(rel)
    return found


def test_elemental_receivers_consult_species_capability_matrix():
    candidates = _interact_battle_candidates()
    if not candidates:
        pytest.skip('native receiver source not present')
    # Fire and bubble reject their immune species through the lane-11 matrix, so
    # P2 Bulbmin (all-hazard immune) is covered without a new receiver.
    assert any('p2_species_immune(pc_p2_species(piki), P2HazardFire)' in p.read_text(errors='replace')
               for p in candidates)
    assert any('p2_species_immune(pc_p2_species(piki), P2HazardWater)' in p.read_text(errors='replace')
               for p in candidates)
    # Electric/gas receivers (#170/#408) use the same matrix.
    assert any('p2_species_immune(pc_p2_species(piki), P2HazardElectric)' in p.read_text(errors='replace')
               for p in candidates)
    assert any('p2_species_immune(pc_p2_species(piki), P2HazardGas)' in p.read_text(errors='replace')
               for p in candidates)


def _interactions_header_candidates():
    found = []
    for base in (ROOT, *ROOT.parents):
        for rel in (base / 'engine/include/Interactions.h',
                    base / 'native/include/Interactions.h',
                    base / 'output/native-lanes-1012/include/Interactions.h',
                    base / 'output/native-sub-elements/include/Interactions.h'):
            if rel.is_file() and rel not in found:
                found.append(rel)
    return found


def test_denki_gas_receiver_classes_present():
    headers = _interactions_header_candidates()
    if not headers:
        pytest.skip('native Interactions.h not present')
    texts = [p.read_text(errors='replace') for p in headers]

    def any_has(anchor):
        return any(anchor in t for t in texts)

    # Classes exist with the source constructor signatures.
    assert any_has('struct InteractDenki : public Interaction')
    assert any_has('struct InteractGas : public Interaction')
    assert any_has('InteractDenki(Creature* owner, f32 force, Vector3f* direction)')
    assert any_has('InteractGas(Creature* owner, f32 damage)')


def _cave_candidates():
    found = []
    for base in (ROOT, *ROOT.parents):
        for rel in (base / 'engine/pc_port/pc_p2_cave.cpp',
                    base / 'native/pc_port/pc_p2_cave.cpp',
                    base / 'output/native-lanes-1012/pc_port/pc_p2_cave.cpp'):
            if rel.is_file() and rel not in found:
                found.append(rel)
    return found


def test_cave_checkpoint_uses_versioned_schema():
    candidates = _cave_candidates()
    if not candidates:
        pytest.skip('native cave source not present')
    texts = [p.read_text(errors='replace') for p in candidates]

    def any_has(anchor):
        return any(anchor in t for t in texts)

    assert any_has('P2_CAVE_ENTRY_3')
    assert any_has('p2_schema_supports(checkpointSchema,')
    assert any_has('p2_schema_required_for_species')


