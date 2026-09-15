"""Dwarf Orange FSM Dead witness: combat stimulus plus player-equivalent orders.

Reuses the lane-13 combat observer (captain reposition + free-squad deployment,
``experimental.pikmin2_dwarf_orange_runtime``) and adds only Pikmin AttackMode
orders targeting the source actor. It writes no enemy health, state, target or
animation; the kill is the real Pikmin damage path, so the opt-in source FSM
reaches its own Dead state.

Usage::

    py -3.12 -m experimental.pikmin2_dwarf_orange_fsm_witness build ...
    py -3.12 -m experimental.pikmin2_dwarf_orange_fsm_witness run ...
"""
import argparse
from pathlib import Path

from experimental.pikmin2_dwarf_orange_runtime import build_fixture_for, instrument as orange_instrument, run as runtime_run

# Natural few-Pikmin encounter stimulus. The base overlay spawns 20 reds within
# ~30 units of the source actor, which kill it before the source attack cycle
# (bite -> eat frame 8 -> swallow frame 88) can complete. This observer relocates
# all but the first 5 starting Pikmin to a distant idle point at tick 2, then
# keeps the captain near the actor and orders only the near Pikmin into
# AttackMode. It writes no enemy health, state, target or animation: the 5-Pikmin
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
    return transformed.replace(anchor, anchor + WITNESS)


def build(native, build_dir, output, head):
    return build_fixture_for(instrument, native, build_dir, output, head)


def run(stage, exe, output, timeout=120):
    return runtime_run(stage, exe, output, timeout)


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
