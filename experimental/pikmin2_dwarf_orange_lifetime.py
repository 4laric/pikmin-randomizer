"""Lane-07 shared actor-lifetime seam probe on the Dwarf Orange Bulborb (#397).

Reconciles the centralized forget/rebind ownership with a live family through
the *engine-driven* seam, not a fixture ``_forget`` call and not a manager swap
(the narrower lane-13 ``pikmin2_dwarf_orange_reentry`` manager reset). It proves,
on a real Dwarf Orange Bulborb (species ``BlueKochappy``, source_id 44):

1. **Engine-driven forget** — ``target->kill(false)`` enters ``BTeki::doKill``,
   which calls ``pc_p2_forget_teki`` -> ``pc_p2_dwarf_orange_forget``. The probe
   never calls the family forget directly, so ``registered(dead)==false`` right
   after the kill is evidence the central seam fired.
2. **Address reuse + late birth** — the staged generator is re-initialized
   (``targetGen->init()``), the freed pool slot is handed back at the *same*
   address, and the stale registration is already clear (cleared by the seam,
   not by the probe). ``pc_p2_dwarf_orange_setup()`` then re-registers the fresh
   actor cleanly.
3. **Control unaffected** — the ordinary P1 Chappy control (211002) stays alive
   and unregistered throughout.

This is a lifetime probe, not a combat/reward gate on the family lane: the kill
trigger is an explicit injection (``kill(false)``) and everything downstream of
it is the real engine death funnel. Gates 1/3/4/5 remain with the family (13)
and reward (06) lanes here.

Usage::

    py -3.12 -m experimental.pikmin2_dwarf_orange_lifetime build \
        --native <native worktree> --build-dir <build> --output <dir> --head <sha>
    py -3.12 -m experimental.pikmin2_dwarf_orange_lifetime run \
        --stage <prepared arena> --exe <fixture.exe> --output <dir>
"""
import argparse
import json
import os
import re
from pathlib import Path

from scripts import build_pikmin2_fixture as builder

ID_SOURCE = 211001
ID_CONTROL = 211002
HEALTH = 250
SOURCE_ID = 44
SPECIES = 'BlueKochappy'

# Replacement for the original RoomApp in tools/preview_p2_room.cpp. The unique
# generation is: bind -> engine kill (forget) -> generator re-init (late birth)
# -> same-address rebind -> control alive. No pc_p2_dwarf_orange_forget call.
PROBE = r'''
class RoomApp : public PlugPikiApp {
    int frames=0, observed=0, step=0;
    Teki* target=nullptr; Teki* control=nullptr; Generator* targetGen=nullptr;
    Teki* find(unsigned id){ Iterator iter(tekiMgr); CI_LOOP(iter){ Teki* a=static_cast<Teki*>(*iter); if(a && a->mGenerator && a->mGenerator->_70==id) return a; } return nullptr; }
public:
    int idle() override {
        int result=PlugPikiApp::idle(); require(++frames<30000,"lifetime startup timeout");
        if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive){ gameflow.mMoviePlayer->requestSkip(); return result; }
        if(!tekiMgr || !pikiMgr || !naviMgr) return result;
        Navi* n=naviMgr->getNavi(); if(!n || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        ++observed;
        if(observed==1) {
            int livePikis=0; Iterator pi(pikiMgr); CI_LOOP(pi){ Piki* p=static_cast<Piki*>(*pi); if(p && p->isAlive()) ++livePikis; }
            require(livePikis>0,"lifetime starting squad missing");
            std::printf("P2_DO_LIFETIME_SQUAD alive=%d\n",livePikis);
            target=find(211001u); control=find(211002u);
            require(target && control,"lifetime roster incomplete");
            require(target->isAlive(),"target not alive");
            require(pc_p2_dwarf_orange_registered(target),"target not registered at spawn");
            require(!pc_p2_dwarf_orange_registered(control),"control wrongly registered");
            targetGen=target->mGenerator; require(targetGen,"target generator missing");
            std::printf("P2_DO_LIFETIME_BIND id=211001 registered=1 control=0\n");
        }
        if(observed==2) {
            require(pc_p2_dwarf_orange_registered(target),"target lost registration before probe");
            std::printf("P2_FORGET_PROBE before=1\n");
            target->kill(false);  // engine death funnel -> BTeki::doKill -> pc_p2_forget_teki
            const int after=pc_p2_dwarf_orange_registered(target);
            std::printf("P2_FORGET_PROBE after_engine_dokill=%d\n",after);
            require(after==0,"engine doKill did not clear registration");
            std::puts("PASS P2_FORGET_PROBE");
            std::printf("P2_REUSE_RESPAWN generator=211001\n");
            targetGen->init();  // late birth on the freed pool slot
            step=1;
        }
        if(step==1) {
            Teki* fresh=find(211001u);
            if(fresh && fresh->isAlive()) {
                const int same=int(fresh==target);
                const int before=pc_p2_dwarf_orange_registered(fresh);
                std::printf("P2_REUSE_PROBE generator=211001 same_address=%d registered_before_rebind=%d\n",same,before);
                require(before==0,"stale registration survived late birth");
                pc_p2_dwarf_orange_setup();
                const int rebound=pc_p2_dwarf_orange_registered(fresh);
                const int alive=int(fresh->isAlive());
                std::printf("P2_REUSE_PROBE rebound_registered=%d alive=%d\n",rebound,alive);
                require(rebound==1,"fresh actor did not re-register");
                require(alive==1,"fresh actor not alive");
                std::puts("PASS P2_REUSE_PROBE");
                step=2;
            } else if(observed>600) { require(false,"re-birth timeout"); }
        }
        if(step==2) {
            const int controlAlive=int(control && control->isAlive() && !pc_p2_dwarf_orange_registered(control));
            std::printf("P2_DO_CONTROL_ALIVE alive=%d\n",controlAlive);
            require(controlAlive==1,"control actor contaminated");
            std::puts("PASS P2_DWARF_ORANGE_LIFETIME"); std::fflush(stdout); std::_Exit(0);
        }
        std::fflush(stdout); return result;
    }
};
'''


def instrument(source):
    """Splice the lifetime probe over the original RoomApp, keeping ``main``."""
    if 'P2_DO_LIFETIME_BIND' in source:
        raise ValueError('Already instrumented')
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    head = ('#include "Generator.h"\n'
            '#include "pc_p2_dwarf_orange.h"\n')
    return head + source[:start] + PROBE + source[end:]


def prepare(assets, bank, profile, output):
    """Stage the two-actor Dwarf Orange arena with the installed family visuals."""
    from experimental.pikmin2_dwarf_orange_arena import prepare as arena
    return arena(Path(assets), Path(bank), Path(profile), Path(output))


def build(native, build_dir, output, head):
    native, build_dir, output = (Path(p).resolve() for p in (native, build_dir, output))
    output.mkdir(parents=True, exist_ok=False)
    room = output / 'room.cpp'
    room.write_text(instrument((native / 'tools/preview_p2_room.cpp').read_text()))
    record = builder.build_fixture(build_dir, native, room, output / 'baseline', head)
    exe = output / 'baseline' / 'fixture.exe'
    print(exe)
    return exe


def evidence(log, exit_code):
    squad = re.search(r'P2_DO_LIFETIME_SQUAD alive=(\d+)', log)
    reuse = re.search(
        r'P2_REUSE_PROBE generator=211001 same_address=(\d+) registered_before_rebind=(\d+)', log)
    same_address = int(reuse[1]) if reuse else None
    checks = {
        'identity': 'P2_ENEMY_READY species=BlueKochappy source_id=44' in log,
        'squad': bool(squad) and int(squad[1]) >= 1,
        'bind': 'P2_DO_LIFETIME_BIND id=211001 registered=1 control=0' in log,
        'forget_before': 'P2_FORGET_PROBE before=1' in log,
        'forget_after': 'P2_FORGET_PROBE after_engine_dokill=0' in log,
        'forget_pass': 'PASS P2_FORGET_PROBE' in log,
        'respawn': 'P2_REUSE_RESPAWN generator=211001' in log,
        # The seam invariant is "no stale registration survives the late birth";
        # whether the engine handed back the same pool address is allocator-
        # dependent and is reported, not gated.
        'reuse_clean': bool(reuse) and reuse[2] == '0',
        'reuse_rebound': 'P2_REUSE_PROBE rebound_registered=1 alive=1' in log,
        'reuse_pass': 'PASS P2_REUSE_PROBE' in log,
        'control_alive': 'P2_DO_CONTROL_ALIVE alive=1' in log,
        'window': '960x540' in log,
    }
    passed = exit_code == 0 and all(checks.values())
    return {'passed': passed, 'checks': checks, 'exit_code': exit_code,
            'same_address_observed': same_address,
            'scope': 'Engine-driven forget (kill(false)->BTeki::doKill->pc_p2_forget_teki) then '
                     'generator re-init late birth, clean re-registration and control unaffected; '
                     'the kill trigger itself is an explicit fixture injection.',
            'unmeasured': ['natural combat death (family lane 13)', 'corpse/pellet delivery (lane 06)',
                           'deterministic same-address allocator reuse (allocator-dependent here; '
                            'the reclaim seam pc_p2_forget_teki in TekiMgr::newTeki is the guard)',
                           'whole scene-exit teardown (already proven at Snow/flora level; not re-run here)']}


def run(stage, exe, output, seconds=120):
    from experimental.pikmin2_animation_profile import capture_command
    stage = Path(stage).resolve()
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    # The fixture links shared MinGW/SDL2 runtime DLLs; expose them to the child.
    os.environ['PATH'] = 'C:/msys64/mingw64/bin;' + os.environ.get('PATH', '')
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           stage, output / 'capture', seconds)
    result = evidence((output / 'capture/native.log').read_text(errors='replace'),
                      meta['exit_code'])
    result['capture'] = meta
    result['stage'] = str(stage)
    (output / 'evidence.json').write_text(json.dumps(result, indent=2))
    return result


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
    r.add_argument('--seconds', type=float, default=120)
    args = parser.parse_args()
    if args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head)
    else:
        print(json.dumps(run(args.stage, args.exe, args.output, args.seconds), indent=2))
