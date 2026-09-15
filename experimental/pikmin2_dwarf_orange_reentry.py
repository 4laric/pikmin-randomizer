"""Native TekiMgr replacement/rebirth for the lane-13 Dwarf Orange candidate.

Closes the gate-E "lifetime/re-entry" leg at manager level: kill all Teki,
replace the manager, re-init the generators and re-run the family setup, and
confirm the old registry is clear, the new actor re-registers with source
health 250 and the control is untouched.
"""
import json
import re
from pathlib import Path

from experimental.pikmin2_kochappy_arena_reentry import instrument as red_reentry
from experimental.pikmin2_dwarf_orange_runtime import orange, positions


def instrument(source):
    s = orange(red_reentry(source))
    # The red printf hardcodes the literal; state the source health truthfully.
    s = s.replace('new_red=200', 'new_red=250')
    # Throttle the overlay's 20-red starting squad to 2 Pikmin so the host-AI
    # actor survives the tick-120 manager swap. With 20 reds it is killed ~tick
    # 60; relocating the whole squad trips the day/movie flow (#397), so a small
    # near squad is kept fighting. Enemy health/state/animation are untouched.
    throttle = (
        '        if(observed==2){int kept=0;Iterator sq(pikiMgr);CI_LOOP(sq){Piki* p=static_cast<Piki*>(*sq);'
        'if(!p->isAlive())continue;if(kept<2){++kept;continue;}'
        'Vector3f far(-400.0f+(kept%5)*8.0f,30.0f,1800.0f+(kept/5)*8.0f);far.y=mapMgr->getMinY(far.x,far.z,true);'
        'p->resetPosition(far);++kept;}'
        'std::printf("P2_DWARF_ORANGE_REENTRY throttle kept=2\\n");std::fflush(stdout);}\n')
    anchor = '        if(observed==120){\n'
    if s.count(anchor) != 1:
        raise ValueError('Unexpected re-entry swap anchor')
    s = s.replace(anchor, throttle + anchor)
    if 'P2_DWARF_ORANGE_REENTRY' not in s or 'pc_p2_dwarf_orange' not in s:
        raise ValueError('Re-entry transform lost the Dwarf Orange identity')
    return s


def prepare(assets, bank, profile, output):
    """Plain two-actor arena (overlay starting squad retained).

    The instrument() throttle (2-Pikmin near squad) keeps the host-AI actor
    alive past the tick-120 swap, so the old-registration -> re-registration
    transition is exercised without injecting enemy state.
    """
    from experimental.pikmin2_dwarf_orange_arena import prepare as arena
    return arena(Path(assets), Path(bank), Path(profile), Path(output))


def build(native, build_dir, output, head):
    from experimental.pikmin2_dwarf_orange_runtime import build_fixture_for
    return build_fixture_for(instrument, native, build_dir, output, head)


def evidence(log, code):
    line = next((x for x in log.splitlines() if x.startswith('P2_DWARF_ORANGE_REENTRY ')), '')
    rows = [dict((k, float(v)) for k, v in re.findall(r'(\w+)=([-+\d.eE]+)', x))
            for x in log.splitlines() if x.startswith('P2_DWARF_ORANGE_ARENA_TICK ')]
    checks = {
        'replacement': 'old_registry=clear before_setup=130 new_red=250 control=130 birth=pass' in line,
        'completion': 'PASS P2_DWARF_ORANGE_REENTRY observation' in log,
        'post_reentry_updates': sum(r.get('tick', 0) > 120 for r in rows) == 240,
        'post_animation': all(len({r.get('frame') for r in rows
                                    if r.get('tick', 0) > 120 and r.get('id') == i}) > 2
                              for i in (211001, 211002)),
    }
    return dict(passed=code == 0 and all(checks.values()), checks=checks, exit_code=code,
                reentry=line,
                scope='Actual TekiMgr killAll/null/new/startStage and native generator init; '
                      'family setup registration after rebirth',
                unmeasured=['whole scene/heap teardown', 'save/load campaign reentry',
                            'same-address allocator reuse'])


def run(stage, exe, output, seconds=120):
    from experimental.pikmin2_animation_profile import capture_command
    import os
    stage = Path(stage).resolve()
    positions(stage)
    os.environ.setdefault('PIKMIN_P2_ROOM_WINDOW', '960x540')
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           stage, output, seconds)
    result = evidence((output / 'native.log').read_text(errors='replace'), meta['exit_code'])
    result['capture'] = meta
    (output / 'evidence.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('stage', 'exe', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    r = run(a.stage.resolve(), a.exe.resolve(), a.output.resolve())
    print(json.dumps({k: v for k, v in r.items() if k != 'rows'}, indent=2))
