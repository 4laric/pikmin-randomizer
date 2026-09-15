"""Root-side compile/run + source-anchor gates for the BigTreasure elemental
receiver decision (lane 32, #246).

The native slice closes the "detection-only" gap: the ordinary update now maps a
confirmed elemental hit to the source stimulus (InteractFire / InteractGas /
InteractBubble / InteractDenki) and applies it to a live Piki/Navi. The policy
decision itself is engine-free and unit-tested natively.

Compile-and-run follows the pattern of tests/test_pikmin2_lanes_1012_policies.py:
compile the standalone policy test against the lane's private native worktree
headers and require its PASS banner. Skips when g++ or the native files are
absent, so it passes before lane 01 exports them into engine/.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _native_worktree():
    # Lane 32's private native worktree (per the DeepSeek lane brief).
    candidates = (
        ROOT.parent / 'native-l32',          # output/dsw/native-l32
        ROOT / 'native',                     # shared checkout (post-integration)
        ROOT / 'engine',                     # exported engine/ (post-export)
    )
    for base in candidates:
        if (base / 'pc_port' / 'pc_p2_bigtreasure_receiver.h').is_file():
            return base
    return None


def _compiler():
    found = shutil.which('g++')
    if found:
        return found
    fallback = Path('C:/msys64/mingw64/bin/g++.exe')
    return str(fallback) if fallback.is_file() else None


def test_receiver_stimulus_decision_compiles_and_passes(tmp_path):
    base = _native_worktree()
    if base is None:
        pytest.skip('native lane 32 receiver headers not present')
    compiler = _compiler()
    if compiler is None:
        pytest.skip('g++ required for native contract')
    port = base / 'pc_port'
    tools = base / 'tools'
    exe = tmp_path / 'p2_bigtreasure_receiver_test.exe'
    subprocess.run(
        [compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
         '-I', str(port),
         str(tools / 'p2_bigtreasure_receiver_test.cpp'),
         str(port / 'pc_p2_bigtreasure_receiver.cpp'),
         '-o', str(exe)],
        check=True, capture_output=True, text=True)
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    assert 'PASS BIGTREASURE_RECEIVER' in run.stdout


def test_ordinary_update_applies_elemental_receiver():
    base = _native_worktree()
    if base is None:
        pytest.skip('native lane 32 receiver headers not present')
    hardlanes = base / 'pc_port' / 'pc_p2_hardlanes.cpp'
    host = base / 'pc_port' / 'pc_p2_bigtreasure_receiver_host.h'
    if not (hardlanes.is_file() and host.is_file()):
        pytest.skip('native lane 32 receiver wiring not present')
    # The ordinary update applies the stimulus to live Piki and Navi through the
    # shared host helper, closing the prior "detection only" gap.
    assert 'pc_p2_bigtreasure_stimulate_piki' in hardlanes.read_text(errors='replace')
    assert 'pc_p2_bigtreasure_stimulate_navi' in hardlanes.read_text(errors='replace')


def test_receiver_host_emits_shared_p2_stimuli():
    base = _native_worktree()
    if base is None:
        pytest.skip('native lane 32 receiver headers not present')
    host = base / 'pc_port' / 'pc_p2_bigtreasure_receiver_host.h'
    if not host.is_file():
        pytest.skip('native lane 32 receiver host header not present')
    text = host.read_text(errors='replace')
    # The lane maps its four elements onto the shared P2 Pikmin receivers (lane
    # 10/11) instead of inventing a second damage framework.
    for stimulus in ('InteractFire', 'InteractGas', 'InteractBubble', 'InteractDenki'):
        assert stimulus in text


def test_receiver_resolve_maps_every_weapon():
    base = _native_worktree()
    if base is None:
        pytest.skip('native lane 32 receiver headers not present')
    impl = base / 'pc_port' / 'pc_p2_bigtreasure_receiver.cpp'
    if not impl.is_file():
        pytest.skip('native lane 32 receiver implementation not present')
    text = impl.read_text(errors='replace')
    for weapon in ('P2BTWEAPON_Fire', 'P2BTWEAPON_Gas', 'P2BTWEAPON_Water',
                   'P2BTWEAPON_Elec'):
        assert weapon in text
    # Water maps to damage 0 (bubble state replaces damage), per the source.
    assert 'InteractBubble(mOwner, 0.0f)' in text or 'hit.damage = 0.0f' in text
