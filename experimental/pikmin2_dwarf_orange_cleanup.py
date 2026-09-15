"""Dwarf Orange natural death -> corpse removal -> family cleanup witness.

Transforms the lane-13 Dwarf Orange P1 corpse-delivery observer
(``experimental.pikmin2_dwarf_orange_delivery``) into a *cleanup* observer: it
delivers the source corpse exactly as the delivery slice does, then holds the
process alive for a bounded number of ticks after the corpse is removed so the
engine death funnel can run ``BTeki::doKill`` -> ``pc_p2_forget_teki`` ->
``pc_p2_dwarf_orange_forget`` / ``pc_p2_kochappy_fsm_forget``. The delivery
observer previously exited on the same tick the corpse was removed, before the
funnel completed.

No enemy state, health, animation or forget is written by this observer; it only
carries the real corpse (delivery stimuli) and waits.
"""
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_kochappy_arena_combat import instrument as combat
from experimental.pikmin2_dwarf_orange_runtime import orange, positions

# Ticks to keep observing after the carried corpse is removed. doKill fires on
# the removal tick or an immediately adjacent one; the window is a safety margin.
HOLD_TICKS = 90

COMBAT_COMPLETION = ('        if((deadAt && observed-deadAt>=60) || observed>=1800){'
                     'capture("red-combat-final.ppm");std::puts("DONE P2_RED_COMBAT");'
                     'std::fflush(stdout);std::_Exit(0);}')

# Same haul as the delivery slice, but after removal runs REMOVED -> POST_REMOVAL
# for HOLD_TICKS before exiting, instead of _Exit on the removal tick.
CLEANUP = r'''
        static Pellet* carried=nullptr;static Vector3f carryOrigin;static float distance=0;static bool reached=false;static int carryTicks=0;static int removedTicks=-1;
        if(!carried && corpses){Iterator find(pelletMgr);CI_LOOP(find){Pellet* p=static_cast<Pellet*>(*find);if(p->mPelletView==static_cast<PelletView*>(red)){carried=p;carryOrigin=p->getPosition();break;}}require(carried,"corpse disappeared before capture");}
        if(carried){
            if(removedTicks<0){
                ++carryTicks;Vector3f p=carried->getPosition();distance=std::max(distance,std::hypot(p.x-carryOrigin.x,p.z-carryOrigin.z));
                reached=reached || carried->getState()==PELSTATE_Goal;
                int transporting=0;Iterator squad(pikiMgr);CI_LOOP(squad){Piki* v=static_cast<Piki*>(*squad);if(v->isAlive() && v->mMode==PikiMode::TransportMode)++transporting;}
                if(carryTicks==1 || carryTicks%60==0)std::printf("P2_RED_P1_HAUL tick=%d state=%d alive=%d distance=%.4f transport=%d goal=%d x=%.4f y=%.4f z=%.4f\n",carryTicks,carried->getState(),int(carried->isAlive()),distance,transporting,int(carried->mTargetGoal!=nullptr),p.x,p.y,p.z);
                if(carryTicks==120 && transporting<carried->mConfig->mCarryMinPikis()){
                    int count=0;Iterator recruits(pikiMgr);CI_LOOP(recruits){Piki* v=static_cast<Piki*>(*recruits);if(!v->isAlive())continue;v->mActiveAction->abandon(nullptr);v->mActiveAction->mCurrActionIdx=PikiAction::Transport;v->mActiveAction->mChildActions[PikiAction::Transport].initialise(carried);v->mMode=PikiMode::TransportMode;++count;}
                    std::printf("P2_RED_P1_TRANSPORT_TASK assigned=%d enemy_state_health_unchanged=1\n",count);
                }
                if(!carried->isAlive()){removedTicks=0;std::printf("P2_RED_P1_REMOVED distance=%.4f\n",distance);std::fflush(stdout);}
                if(carryTicks>=2400){capture("red-p1-stalled.ppm");std::puts("FAIL P2_RED_P1_DELIVERY bounded haul stalled");std::fflush(stdout);std::_Exit(1);}
            } else {
                ++removedTicks;std::printf("P2_RED_P1_POST_REMOVAL tick=%d\n",removedTicks);std::fflush(stdout);
                if(removedTicks>=90){
                    require(reached && distance>100,"P1 corpse removed without route and goal");
                    require(pc_p2_preview_goal()==nullptr && pc_p2_preview_pokos()==-1,"unexpected P2 reward binding");
                    std::printf("PASS P2_RED_P1_CLEANUP distance=%.4f reached=1\n",distance);capture("red-p1-delivery.ppm");std::fflush(stdout);std::_Exit(0);
                }
            }
        }
'''


def instrument(source):
    result = combat(source)
    if result.count(COMBAT_COMPLETION) != 1:
        raise ValueError('Unexpected combat completion anchor')
    transformed = '#include <algorithm>\n' + result.replace(COMBAT_COMPLETION, CLEANUP)
    transformed = orange(transformed)
    if 'P2_DWARF_ORANGE_P1_REMOVED' not in transformed:
        raise ValueError('Cleanup transform lost the Dwarf Orange identity')
    return transformed


def prepare(assets, bank, profile, output):
    from experimental.pikmin2_dwarf_orange_runtime import prepare as combat_prepare
    return combat_prepare(assets, bank, profile, output)


def build(native, build_dir, output, head):
    from experimental.pikmin2_dwarf_orange_runtime import build_fixture_for
    return build_fixture_for(instrument, native, build_dir, output, head)


def evidence(log, code):
    removed = 'P2_DWARF_ORANGE_P1_REMOVED ' in log
    dwarf_forget = 'P2_DWARF_ORANGE_FORGET ' in log
    fsm_forget = 'P2_KOCHAPPY_FSM_FORGET ' in log
    rows = [dict((k, float(v)) for k, v in re.findall(r'(\w+)=([-+\d.eE]+)', line))
            for line in log.splitlines() if line.startswith('P2_DWARF_ORANGE_P1_HAUL ')]
    checks = {
        'birth_control': log.count('P2_DWARF_ORANGE_ARENA_BIRTH ') == 2,
        'fsm_death': 'P2_KOCHAPPY_STATE generator=211001 state=dead' in log
                     and 'P2_KOCHAPPY_DEAD generator=211001 source_id=44 health=0.0' in log,
        'corpse_render': 'P2_DWARF_ORANGE_DRAW corpse=1' in log,
        'transport': any(r.get('transport', 0) > 0 for r in rows),
        'corpse_removed': removed,
        'cleanup_dwarf_orange_forget': dwarf_forget,
        'cleanup_fsm_forget': fsm_forget,
        'completion': 'PASS P2_DWARF_ORANGE_P1_CLEANUP' in log,
    }
    return dict(passed=code == 0 and all(checks.values()), checks=checks, exit_code=code,
                rows=rows, transport_task_injected='P2_DWARF_ORANGE_P1_TRANSPORT_TASK' in log,
                p2_receipt_gate='not applicable: no Pod; ordinary P1 corpse delivery',
                scope='natural FSM combat/death (no injected enemy state) + real corpse carry and removal; '
                      'forget observed on the engine doKill funnel',
                unmeasured=['P2 once-credit/idempotency', 'actual spawned seed yield', 'player-controlled haul'])


def run(stage, exe, output, seconds=180):
    from experimental.pikmin2_animation_profile import capture_command
    stage = Path(stage).resolve()
    output = Path(output).resolve()
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
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    for name in ('native', 'build-dir', 'output'):
        b.add_argument('--' + name, type=Path, required=True)
    b.add_argument('--head', required=True)
    r = sub.add_parser('run')
    for name in ('stage', 'exe', 'output'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--seconds', type=float, default=180)
    args = parser.parse_args()
    if args.command == 'build':
        print(build(args.native, args.build_dir, args.output, args.head))
    else:
        print(json.dumps({k: v for k, v in run(args.stage, args.exe, args.output, args.seconds).items()
                          if k != 'rows'}, indent=2))
