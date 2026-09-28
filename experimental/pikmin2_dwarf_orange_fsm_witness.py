"""Dwarf Orange FSM combat witness: one natural 250 HP run that eats and swallows.

Reuses the lane-13 combat observer (captain reposition + free-squad deployment,
``experimental.pikmin2_dwarf_orange_runtime``) and adds a few-Pikmin observation
squad plus Pikmin AttackMode orders so the source FSM survives long enough to run
its full attack chain: frame-8 InteractAttack bite + eatPikmin, frame-88
swallowPikmin, then natural death and host_escape_now corpse. It writes no enemy
health, state, target or animation.

Usage::

    py -3.12 -m experimental.pikmin2_dwarf_orange_fsm_witness build ...
    py -3.12 -m experimental.pikmin2_dwarf_orange_fsm_witness run ...
"""
import argparse
import json
import os
from pathlib import Path

from experimental.pikmin2_dwarf_orange_runtime import build_fixture_for, instrument as orange_instrument, positions

# Natural few-Pikmin encounter stimulus. The base overlay spawns 20 reds within
# ~30 units of the source actor, which kill it before the source attack cycle
# (bite -> eat frame 8 -> swallow frame 88) can complete. This observer relocates
# all but the first 3 starting Pikmin to a distant idle point at tick 2, then
# keeps the captain near the actor and orders only the near Pikmin into
# AttackMode. It writes no enemy health, state, target or animation: the 3-Pikmin
# damage is the real Pikmin attack path, so the enemy survives long enough to
# exercise the eat/swallow receiver naturally.
WITNESS = (
    'if(observed==2){int kept=0;Iterator sq(pikiMgr);CI_LOOP(sq){Piki* p=static_cast<Piki*>(*sq);'
    'if(!p->isAlive())continue;if(kept<3){++kept;continue;}'
    'Vector3f far(-400.0f+(kept%5)*8.0f,30.0f,1800.0f+(kept/5)*8.0f);far.y=mapMgr->getMinY(far.x,far.z,true);'
    'p->resetPosition(far);++kept;}'
    'std::printf("P2_KOCHAPPY_FSM_WITNESS throttle kept=3\\n");std::fflush(stdout);}'
    'if(observed>=8 && observed%30==0){'
    'int alive=0,attack=0;Iterator sq(pikiMgr);CI_LOOP(sq){Piki* p=static_cast<Piki*>(*sq);if(!p->isAlive())continue;++alive;'
    'const Vector3f pp=p->getPosition();const Vector3f rp=red->getPosition();const float dx=pp.x-rp.x,dz=pp.z-rp.z;'
    'if(dx*dx+dz*dz>40000.0f)continue;'
    'if(p->mMode==PikiMode::AttackMode){++attack;continue;}'
    'p->mActiveAction->abandon(nullptr);p->mActiveAction->mCurrActionIdx=PikiAction::Attack;'
    'p->mActiveAction->mChildActions[PikiAction::Attack].initialise(red);p->mMode=PikiMode::AttackMode;++attack;}'
    'Vector3f cpos=red->getPosition()+Vector3f(0,0,40);cpos.y=mapMgr->getMinY(cpos.x,cpos.z,true);n->resetPosition(cpos);'
    'std::printf("P2_KOCHAPPY_FSM_WITNESS tick=%d alive=%d attack=%d visible=%d health=%.1f\\n",'
    'observed,alive,attack,int(red->isVisible()),red->mHealth);std::fflush(stdout);}'
)


def instrument(source):
    transformed = orange_instrument(source)
    anchor = 'require(count==20,"expected20Pikmin");}'
    if transformed.count(anchor) != 1:
        raise ValueError('Unexpected witness anchor')
    # The source actor EATS Pikmin, so the alive count at the tick-240 deployment
    # is below 20; relax the legacy assertion so the run reaches DONE instead of
    # aborting after the eat/swallow/dead/corpse markers are already captured.
    relaxed = 'require(count>=17,"expected17Pikmin");}'
    transformed = transformed.replace(anchor, relaxed)
    return transformed.replace(relaxed, relaxed + WITNESS)


def evidence(log, code):
    """FSM-path gate: the natural eat -> swallow -> dead -> corpse chain."""
    eaten = any(line.startswith('P2_KOCHAPPY_EAT ') and ' eaten=1' in line
                for line in log.splitlines())
    swallowed = any(line.startswith('P2_KOCHAPPY_SWALLOW ') and ' swallowed=1' in line
                    for line in log.splitlines())
    checks = {
        'completion': 'DONE P2_DWARF_ORANGE_COMBAT' in log,
        'identity_ready': 'P2_ENEMY_READY species=BlueKochappy source_id=44' in log,
        'bank_loaded': 'P2_DWARF_ORANGE_BANK' in log,
        'birth_control': log.count('P2_DWARF_ORANGE_ARENA_BIRTH ') == 2,
        'window': '960x540' in log,
        'fsm_walk': 'P2_KOCHAPPY_STATE generator=211001 state=walk' in log,
        'attack_bite': 'P2_KOCHAPPY_ATTACK generator=211001 frame=8' in log,
        'eat': eaten,
        'swallow': swallowed,
        'dead': 'P2_KOCHAPPY_DEAD generator=211001 source_id=44' in log,
        'corpse': 'P2_KOCHAPPY_CORPSE generator=211001' in log,
        'no_extinction': 'Extinction' not in log,
    }
    return dict(passed=code == 0 and all(checks.values()), checks=checks, exit_code=code,
                scope='natural few-Pikmin combat (no injected enemy state); bite at frame 8 eats a Pikmin '
                      'and frame 88 swallows it, then real Pikmin damage kills the actor and births a corpse',
                unmeasured=['transport/reward', 'cleanup/re-entry', 'P2 attack receivers beyond eat/swallow'])


def build(native, build_dir, output, head):
    return build_fixture_for(instrument, native, build_dir, output, head)


def run(stage, exe, output, timeout=120):
    from experimental.pikmin2_animation_profile import capture_command
    stage = Path(stage).resolve()
    output = Path(output).resolve()
    positions(stage)
    os.environ.setdefault('PIKMIN_P2_ROOM_WINDOW', '960x540')
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           stage, output, timeout)
    report = evidence((output / 'native.log').read_text(errors='replace'), meta['exit_code'])
    report['capture'] = meta
    (output / 'evidence.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    for name in ('native', 'build-dir', 'output'):
        b.add_argument('--' + name, type=Path, required=True)
    b.add_argument('--head', required=True)
    r = sub.add_parser('run')
    for name in ('stage', 'exe', 'output'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--timeout', type=int, default=120)
    args = parser.parse_args()
    if args.command == 'build':
        print(build(args.native, args.build_dir, args.output, args.head))
    else:
        print(run(args.stage, args.exe, args.output, args.timeout).get('passed'))
