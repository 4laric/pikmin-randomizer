"""Compile-and-run gates for the lane 11/12 native policy contracts.

Follows the pattern of tests/test_pikmin2_envmap.py and
tests/test_pikmin2_cargo_uphill.py: compile the standalone policy test against
the native pc_port headers and require its PASS banner. Skips when no g++ or no
native copy of the headers is present, so it passes before lane 01 exports them
into engine/.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _native_root():
    """Native repo root, or None. PIKMIN_NATIVE_ROOT -> P2_NATIVE_PC_PORT(->parent) -> ROOT/native."""
    env = os.environ.get('PIKMIN_NATIVE_ROOT')
    if env and (Path(env) / 'pc_port' / 'pc_p2_species_policy.h').is_file():
        return Path(env).resolve()
    pc = os.environ.get('P2_NATIVE_PC_PORT')
    if pc and (Path(pc) / 'pc_p2_species_policy.h').is_file():
        return Path(pc).resolve().parent
    cand = ROOT / 'native'
    if (cand / 'pc_port' / 'pc_p2_species_policy.h').is_file():
        return cand.resolve()
    return None


def _port_candidates():
    root = _native_root()
    if root is None:
        return []
    return [root / 'pc_port']


_CASES = (
    ('test_p2_captain_policy.cpp', 'PASS P2_CAPTAIN_POLICY'),
    ('test_p2_captain_roster.cpp', 'PASS P2_CAPTAIN_ROSTER'),
    ('test_p2_bulbmin_policy.cpp', 'PASS P2_BULBMIN_POLICY'),
    ('test_p2_species_policy.cpp', 'PASS P2_SPECIES_POLICY'),
    ('test_p2_species_schema.cpp', 'PASS P2_SPECIES_SCHEMA'),
    ('test_p2_elemental_receivers.cpp', 'PASS P2_ELEMENTAL_RECEIVERS'),
    ('test_p2_hazard_reaction.cpp', 'PASS P2_HAZARD_REACTION'),
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
    env = dict(os.environ, PATH=str(Path(compiler).parent) + os.pathsep + os.environ.get('PATH', ''))
    subprocess.run(
        [compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
         '-I', str(port), str(tools / name), '-o', str(exe)],
        check=True, capture_output=True, text=True, env=env)
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30, env=env)
    assert run.returncode == 0, run.stderr
    assert banner in run.stdout


def _interact_battle_candidates():
    root = _native_root()
    if not root:
        return []
    rel = root / 'src' / 'plugPikiKando' / 'interactBattle.cpp'
    return [rel] if rel.is_file() else []


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
    # Electric/gas receivers (#170/#408) route through p2_hazard_reaction.
    assert any('p2_hazard_reaction(pc_p2_species(piki), P2HazardElectric' in p.read_text(errors='replace')
               for p in candidates)
    assert any('p2_hazard_reaction(pc_p2_species(piki), P2HazardGas' in p.read_text(errors='replace')
               for p in candidates)


def _interactions_header_candidates():
    root = _native_root()
    if not root:
        return []
    rel = root / 'include' / 'Interactions.h'
    return [rel] if rel.is_file() else []


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
    root = _native_root()
    if not root:
        return []
    rel = root / 'pc_port' / 'pc_p2_cave.cpp'
    return [rel] if rel.is_file() else []


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


def _native_candidates(*rels):
    root = _native_root()
    if not root:
        return []
    return [p for rel in rels for p in [root / rel] if p.is_file()]


def test_pikmin_reaction_states_declared_and_registered():
    """#170/#408: the P2 electric/gas Pikmin states exist and are reachable."""
    headers = _native_candidates('include/PikiState.h')
    sources = _native_candidates('src/plugPikiKando/pikiState.cpp')
    if not headers or not sources:
        pytest.skip('native PikiState sources not present')
    texts = [p.read_text(errors='replace') for p in headers]
    code = [p.read_text(errors='replace') for p in sources]

    def any_has(pool, anchor):
        return any(anchor in t for t in pool)

    # Source-mirroring enum entries, additive before PIKISTATE_Count.
    assert any_has(texts, 'PIKISTATE_DenkiDying')
    assert any_has(texts, 'PIKISTATE_Panic')
    assert any_has(texts, 'struct PikiDenkiDyingState')
    assert any_has(texts, 'struct PikiPanicState')
    # Registered in PikiStateMachine::init so transit() can reach them.
    assert any_has(code, 'registerState(new PikiDenkiDyingState())')
    assert any_has(code, 'registerState(new PikiPanicState())')
    # The gas state plays the existing death pipeline when the poison expires.
    assert any_has(code, 'PIKISTATE_DenkiDying, "DENKI_DYING"')
    assert any_has(code, 'PIKISTATE_Panic, "PANIC"')


def test_denki_gas_receivers_route_to_p2_states():
    """#170/#408: non-immune receivers use the P2 states, not the P1 proxies."""
    battles = _interact_battle_candidates()
    if not battles:
        pytest.skip('native interactBattle not present')
    texts = [p.read_text(errors='replace') for p in battles]

    def any_has(anchor):
        return any(anchor in t for t in texts)

    # Immunity is still consulted through the lane-11 matrix plus the gas gate.
    assert any_has('p2_hazard_reaction(pc_p2_species(piki), P2HazardElectric')
    assert any_has('p2_hazard_reaction(pc_p2_species(piki), P2HazardGas')
    # The non-immune paths transit to the new P2 states.
    assert any_has('transit(piki, PIKISTATE_DenkiDying)')
    assert any_has('transit(piki, PIKISTATE_Panic)')
    assert any_has('piki->gasInvicible()')


def test_piki_exposes_gas_invincible_gate():
    """#170/#408: the narrow gas gate mirrors source Piki::gasInvicible."""
    pikis = _native_candidates('include/Piki.h')
    if not pikis:
        pytest.skip('native Piki.h not present')
    texts = [p.read_text(errors='replace') for p in pikis]

    def any_has(anchor):
        return any(anchor in t for t in texts)

    assert any_has('bool gasInvicible()')
    assert any_has('setGasInvincible')



