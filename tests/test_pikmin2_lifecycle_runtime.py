"""Instrumentation tests for the reusable lifecycle fixture (#397)."""
import pytest

import experimental.pikmin2_lifecycle_runtime as lifecycle

SYNTHETIC = ("class RoomApp : public PlugPikiApp {\n"
             " int frames=0;\n"
             "};\n"
             "int main(int argc,char** argv) {\n"
             ' if(!pc_window_init("P2 room integration fixture",960,720))return 3;\n'
             " return 0; }\n")


def test_instrument_replaces_roomapp_and_keeps_main():
    source = lifecycle.instrument(SYNTHETIC)
    assert 'class RoomApp : public PlugPikiApp {' in source
    assert 'int main(' in source
    for marker in ('P2_LIFECYCLE_BIRTH', 'P2_LIFECYCLE_DEATH', 'P2_LIFECYCLE_REENTRY',
                   'PASS P2_LIFECYCLE_RUNTIME', 'Experimental preview window set to'):
        assert marker in source
    assert source.index('P2_LIFECYCLE_BIRTH') < source.index('int main(')
    assert 'int frames=0;\n};' not in source


def test_instrument_rejects_missing_anchor():
    with pytest.raises(ValueError):
        lifecycle.instrument('int main() { return 0; }\n')


def test_instrument_rejects_double_instrumentation():
    once = lifecycle.instrument(SYNTHETIC)
    with pytest.raises(ValueError):
        lifecycle.instrument(once)


def test_instrument_is_deterministic():
    assert lifecycle.instrument(SYNTHETIC) == lifecycle.instrument(SYNTHETIC)


def test_instrument_has_no_fixture_forget_call():
    source = lifecycle.instrument(SYNTHETIC)
    assert '__REGISTERED_EXPR__' not in source
    assert '__REBIND_CALL__' not in source
    # The engine is the only forget authority; the fixture must never call a
    # family *_forget directly (the seam runs pc_p2_forget_teki in doKill).
    assert 'pc_p2_batch2_forget(' not in source
    assert 'pc_p2_long_legs_forget(' not in source
    # slice 3: movement is the first-born actor's own locomotion.
    assert 'resetPosition(' not in source


def test_dwarf_orange_hooks_route_to_its_module():
    source = lifecycle.instrument(SYNTHETIC, family='dwarf-orange')
    assert '#include "pc_p2_dwarf_orange.h"' in source
    assert 'pc_p2_dwarf_orange_registered(deadPtr)' in source
    assert 'pc_p2_dwarf_orange_setup();' in source
    assert 'pc_p2_batch2_forget(' not in source
    assert 'pc_p2_dwarf_orange_forget(' not in source
    # scene teardown drives the host exitStage.
    assert 'lifecycleFindCore(' in source
    assert 'exitStage()' in source


def test_sokkuri_hooks_route_to_its_module():
    source = lifecycle.instrument(SYNTHETIC, family='sokkuri')
    assert '#include "pc_p2_sokkuri.h"' in source
    assert 'pc_p2_sokkuri_registered(deadPtr)' in source
    assert 'pc_p2_sokkuri_count()' in source
    assert 'pc_p2_sokkuri_setup();' in source
    assert 'pc_p2_sokkuri_forget(' not in source
    assert 'lifecycleFindCore(' in source


# A single-cycle manager-reset good log: natural first-born movement line is
# emitted BEFORE the first lethal attack/death.
_ONE_ACTOR_MANIFEST = {
    'control': 'P1 Chappy',
    'actors': [{'generator': 1, 'native_teki_type': 3, 'species': 'Houdai',
                'expected_xyz': [0.0, 0.0, 0.0]}],
}

_BASE_PASS_LOG = (
    'P2_LIFECYCLE_BIRTH id=1 type=3 registered=1 invincible=0 x=0.000 y=0.000 z=0.000\n'
    'P2_LIFECYCLE_TARGET id=1\n'
    'P2_LIFECYCLE_MOVE id=1 dist=5.000\n'
    'P2_LIFECYCLE_ATTACK id=1 accepted=1 health=-1.0\n'
    'P2_LIFECYCLE_DEATH id=1 frame=240\n'
    'P2_LIFECYCLE_CLEANUP id=1 alive=0\n'
    'P2_LIFECYCLE_FORGET id=1 registered_at_death=1\n'
    'P2_LIFECYCLE_FORGET id=1 registered_after_dispose=0 engine=doKill\n'
    'P2_LIFECYCLE_RESPAWN_INJECT id=1 generator=1\n'
    'P2_LIFECYCLE_REENTRY id=1 frame=500 reused=1\n'
    'P2_LONG_LEGS_BIND generator=1 species=Houdai pose=bind\n'
    'P2_LONG_LEGS_BIND generator=1 species=Houdai pose=bind\n'
    'P2_LONG_LEGS_DRAW corpse=0 species=Houdai pose=bind\n'
    'P2_LIFECYCLE_SUMMARY family=1 alive=1 moved=1 death=240 reentry=500 reused=1 control=1\n'
    'PASS P2_LIFECYCLE_RUNTIME\n'
)


def test_validate_requires_death_cleanup_and_reentry():
    manifest = {'control': 'P1 Chappy',
                'actors': [{'generator': 1, 'native_teki_type': 3, 'species': 'Houdai',
                            'expected_xyz': [0.0, 0.0, 0.0]},
                           {'generator': 2, 'native_teki_type': 3, 'species': 'P1 Chappy',
                            'expected_xyz': [0.0, 0.0, 0.0]}]}
    text = (
        'P2_LIFECYCLE_BIRTH id=1 type=3 registered=1 invincible=0 x=0.000 y=0.000 z=0.000\n'
        'P2_LIFECYCLE_BIRTH id=2 type=3 registered=0 invincible=0 x=0.000 y=0.000 z=0.000\n'
        'P2_LIFECYCLE_TARGET id=1\n'
        'P2_LIFECYCLE_MOVE id=1 dist=5.000\n'
        'P2_LIFECYCLE_ATTACK id=1 accepted=1 health=0.0\n'
        'P2_LIFECYCLE_DEATH id=1 frame=240\n'
        'P2_LIFECYCLE_CLEANUP id=1 alive=0\n'
        'P2_LIFECYCLE_FORGET id=1 registered_at_death=1\n'
        'P2_LIFECYCLE_FORGET id=1 registered_after_dispose=0 engine=doKill\n'
        'P2_LIFECYCLE_RESPAWN_INJECT id=1 generator=1\n'
        'P2_LIFECYCLE_REENTRY id=1 frame=500 reused=1\n'
        'P2_LONG_LEGS_BIND generator=1 species=Houdai pose=bind\n'
        'P2_LONG_LEGS_BIND generator=1 species=Houdai pose=bind\n'
        'P2_LONG_LEGS_DRAW corpse=0 species=Houdai pose=bind\n'
        'P2_LIFECYCLE_TEARDOWN_MODE mode=manager-reset\n'
        'P2_LIFECYCLE_TEARDOWN refs_before=1 refs_after=0\n'
        'P2_LIFECYCLE_REGISTRY cycle=2 count=1\n'
        'P2_LIFECYCLE_SUMMARY family=1 alive=1 moved=1 death=240 reentry=500 reused=1 control=1\n'
        'PASS P2_LIFECYCLE_RUNTIME\n')
    evidence = lifecycle.validate(text, 0, manifest)
    assert evidence['passed'], evidence['checks']
    assert all(evidence['checks'].values())

    # Missing death must fail even when the run otherwise completes.
    degraded = text.replace('P2_LIFECYCLE_DEATH id=1 frame=240\n', '')
    assert not lifecycle.validate(degraded, 0, manifest)['passed']


def test_current_native_window_entrypoint_is_preserved():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    path = root / 'native/tools/preview_p2_room.cpp'
    if not path.exists(): path = root / 'engine/tools/preview_p2_room.cpp'
    source = path.read_text(encoding='utf-8')
    result = lifecycle.instrument(source)
    assert result.count('pc_window_center();') == source.count('pc_window_center();')
    assert 'pc_p2_batch2_rebind();' in result
    assert 'P2_LIFECYCLE_SQUAD alive=' in result


def test_validate_dwarf_orange_engine_forget_and_ready_rebind():
    manifest = {'control': 'P1 Chappy',
                'actors': [{'generator': 211001, 'native_teki_type': 3,
                            'species': 'BlueKochappy',
                            'expected_xyz': [0.0, 0.0, 0.0]},
                           {'generator': 211002, 'native_teki_type': 3,
                            'species': 'P1 Chappy',
                            'expected_xyz': [0.0, 0.0, 0.0]}]}
    text = (
        'P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001\n'
        'P2_LIFECYCLE_BIRTH id=211001 type=3 registered=1 invincible=0 x=0.000 y=0.000 z=0.000\n'
        'P2_LIFECYCLE_BIRTH id=211002 type=3 registered=0 invincible=0 x=0.000 y=0.000 z=0.000\n'
        'P2_LIFECYCLE_TARGET id=211001\n'
        'P2_LIFECYCLE_MOVE id=211001 dist=5.000\n'
        'P2_LIFECYCLE_ATTACK id=211001 accepted=1 health=0.0\n'
        'P2_LIFECYCLE_DEATH id=211001 frame=240\n'
        'P2_LIFECYCLE_CLEANUP id=211001 alive=0\n'
        'P2_LIFECYCLE_FORGET id=211001 registered_at_death=1\n'
        'P2_LIFECYCLE_FORGET id=211001 registered_after_dispose=0 engine=doKill\n'
        'P2_LIFECYCLE_RESPAWN_INJECT id=211001 generator=211001\n'
        'P2_LIFECYCLE_REENTRY id=211001 frame=500 reused=0\n'
        'P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001\n'
        'P2_DWARF_ORANGE_DRAW corpse=0\n'
        'P2_LIFECYCLE_TEARDOWN_MODE mode=manager-reset\n'
        'P2_LIFECYCLE_TEARDOWN refs_before=1 refs_after=0\n'
        'P2_LIFECYCLE_REGISTRY cycle=2 count=1\n'
        'P2_LIFECYCLE_SUMMARY family=1 alive=1 moved=1 death=240 reentry=500 reused=0 control=1\n'
        'PASS P2_LIFECYCLE_RUNTIME\n')
    evidence = lifecycle.validate(text, 0, manifest, name='dwarf-orange')
    assert evidence['passed'], evidence['checks']
    assert evidence['reused_observed'] is False  # allocator handed a fresh slot; not gated


def test_teardown_modes_constant():
    assert lifecycle.TEARDOWN_MODES == ('manager-reset', 'scene-teardown')


def test_run_cli_accepts_cycles_and_teardown():
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run([sys.executable, '-m', 'experimental.pikmin2_lifecycle_runtime',
                           'run', '--help'],
                          cwd=root, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert '--cycles' in proc.stdout
    assert '--teardown' in proc.stdout
    for mode in lifecycle.TEARDOWN_MODES:
        assert mode in proc.stdout


def test_validate_reports_cycles_and_teardown_fields():
    evidence = lifecycle.validate(_BASE_PASS_LOG, 0, _ONE_ACTOR_MANIFEST)
    assert evidence['cycles'] == 1
    assert evidence['teardown_mode'] == 'manager-reset'
    evidence = lifecycle.validate(_BASE_PASS_LOG, 0, _ONE_ACTOR_MANIFEST,
                                  cycles=3, teardown='scene-teardown')
    assert evidence['cycles'] == 3
    assert evidence['teardown_mode'] == 'scene-teardown'


def _cycle_lines(counts):
    out = ''
    for n, count in enumerate(counts, start=1):
        out += 'P2_LIFECYCLE_CYCLE cycle=%d\n' % n
        out += 'P2_LIFECYCLE_REGISTRY cycle=%d count=%d\n' % (n, count)
    out += 'P2_LIFECYCLE_REWARD pokos=0\n'
    return out


def _teardown_tail(refs_after=0, next_cycle=2):
    """Manager-reset teardown tail: family reset (refs_after=0) + re-entry."""
    return ('P2_LIFECYCLE_TEARDOWN_MODE mode=manager-reset\n'
            + 'P2_LIFECYCLE_TEARDOWN refs_before=1 refs_after=%d\n' % refs_after
            + 'P2_LIFECYCLE_REGISTRY cycle=%d count=1\n' % next_cycle)


def _scene_exit_tail(refs_after=0):
    """Scene-teardown tail: host exitStage (refs_after=0, navi nulled), then exit."""
    return ('P2_LIFECYCLE_TEARDOWN_MODE mode=scene-teardown\n'
            + 'P2_LIFECYCLE_SCENE_EXIT host=exitStage refs_after=%d navi_null=1\n' % refs_after)


def test_validate_multi_cycle_registry_growth_and_reward():
    text = (_BASE_PASS_LOG
            + _cycle_lines([1, 1])
            + _teardown_tail(next_cycle=3))
    evidence = lifecycle.validate(text, 0, _ONE_ACTOR_MANIFEST,
                                  cycles=2, teardown='manager-reset')
    assert evidence['passed'], evidence['checks']
    assert evidence['registry_growth_ok'] is True

    grown = text.replace('P2_LIFECYCLE_REGISTRY cycle=1 count=1',
                         'P2_LIFECYCLE_REGISTRY cycle=1 count=2')
    bad = lifecycle.validate(grown, 0, _ONE_ACTOR_MANIFEST,
                             cycles=2, teardown='manager-reset')
    assert bad['registry_growth_ok'] is False
    assert not bad['passed']

    no_reward = lifecycle.validate(text.replace('P2_LIFECYCLE_REWARD pokos=0\n', ''),
                                   0, _ONE_ACTOR_MANIFEST,
                                   cycles=2, teardown='manager-reset')
    assert not no_reward['passed']


def test_validate_manager_reset_requires_mode_marker():
    full = _BASE_PASS_LOG + _teardown_tail()
    evidence = lifecycle.validate(full, 0, _ONE_ACTOR_MANIFEST)
    assert evidence['passed'], evidence['checks']
    assert evidence['teardown_mode'] == 'manager-reset'
    missing = lifecycle.validate(_BASE_PASS_LOG, 0, _ONE_ACTOR_MANIFEST)
    assert not missing['passed']


def test_validate_move_probe_precedes_first_death():
    before = (
        'P2_LIFECYCLE_BIRTH id=1 type=3 registered=1 invincible=0 x=0.000 y=0.000 z=0.000\n'
        'P2_LIFECYCLE_MOVE id=1 dist=5.000\n'
        'P2_LIFECYCLE_DEATH id=1 frame=240\n'
        'PASS P2_LIFECYCLE_RUNTIME\n')
    assert lifecycle.validate(before, 0, _ONE_ACTOR_MANIFEST)['checks']['moved_first_born'] is True

    after = (
        'P2_LIFECYCLE_BIRTH id=1 type=3 registered=1 invincible=0 x=0.000 y=0.000 z=0.000\n'
        'P2_LIFECYCLE_DEATH id=1 frame=240\n'
        'P2_LIFECYCLE_MOVE id=1 dist=5.000\n'
        'PASS P2_LIFECYCLE_RUNTIME\n')
    assert lifecycle.validate(after, 0, _ONE_ACTOR_MANIFEST)['checks']['moved_first_born'] is False

    too_small = (
        'P2_LIFECYCLE_BIRTH id=1 type=3 registered=1 invincible=0 x=0.000 y=0.000 z=0.000\n'
        'P2_LIFECYCLE_MOVE id=1 dist=0.500\n'
        'P2_LIFECYCLE_DEATH id=1 frame=240\n'
        'PASS P2_LIFECYCLE_RUNTIME\n')
    assert lifecycle.validate(too_small, 0,
                              _ONE_ACTOR_MANIFEST)['checks']['moved_first_born'] is False


def test_validate_single_cycle_registry_growth_not_vacuous():
    missing_reentry = (_BASE_PASS_LOG
                       + 'P2_LIFECYCLE_TEARDOWN_MODE mode=manager-reset\n'
                       + 'P2_LIFECYCLE_TEARDOWN refs_before=1 refs_after=0\n')
    assert lifecycle.validate(missing_reentry, 0, _ONE_ACTOR_MANIFEST,
                              cycles=1)['registry_growth_ok'] is False

    full = _BASE_PASS_LOG + _teardown_tail()
    ok = lifecycle.validate(full, 0, _ONE_ACTOR_MANIFEST, cycles=1)
    assert ok['passed'], ok['checks']
    assert ok['registry_growth_ok'] is True

    leak = lifecycle.validate(_BASE_PASS_LOG + _teardown_tail(refs_after=1),
                              0, _ONE_ACTOR_MANIFEST, cycles=1)
    assert leak['registry_growth_ok'] is False


def test_validate_scene_teardown_requires_zero_refs_after():
    ok = lifecycle.validate(_BASE_PASS_LOG + _scene_exit_tail(),
                            0, _ONE_ACTOR_MANIFEST, teardown='scene-teardown')
    assert ok['passed'], ok['checks']
    assert ok['scene_teardown_ok'] is True

    leak = lifecycle.validate(_BASE_PASS_LOG + _scene_exit_tail(refs_after=1),
                              0, _ONE_ACTOR_MANIFEST, teardown='scene-teardown')
    assert leak['scene_teardown_ok'] is False
    assert not leak['passed']
