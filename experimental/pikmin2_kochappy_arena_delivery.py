"""Original-map P1 corpse delivery; deliberately no P2 reward/Pod semantics."""
import json
import re
from pathlib import Path
from experimental.pikmin2_kochappy_arena_combat import instrument as combat,prepare
from experimental.pikmin2_kochappy_arena_fixture import positions

DELIVERY=r'''
        static Pellet* carried=nullptr;static Vector3f carryOrigin;static float distance=0;static bool reached=false;static int carryTicks=0;
        if(!carried && corpses){Iterator find(pelletMgr);CI_LOOP(find){Pellet* p=static_cast<Pellet*>(*find);if(p->mPelletView==static_cast<PelletView*>(red)){carried=p;carryOrigin=p->getPosition();break;}}require(carried,"corpse disappeared before capture");}
        if(carried){
            ++carryTicks;Vector3f p=carried->getPosition();distance=std::max(distance,std::hypot(p.x-carryOrigin.x,p.z-carryOrigin.z));
            reached=reached || carried->getState()==PELSTATE_Goal;
            int transporting=0;Iterator squad(pikiMgr);CI_LOOP(squad){Piki* v=static_cast<Piki*>(*squad);if(v->isAlive() && v->mMode==PikiMode::TransportMode)++transporting;}
            if(carryTicks==1 || carryTicks%60==0)std::printf("P2_RED_P1_HAUL tick=%d state=%d alive=%d distance=%.4f transport=%d goal=%d x=%.4f y=%.4f z=%.4f\n",carryTicks,carried->getState(),int(carried->isAlive()),distance,transporting,int(carried->mTargetGoal!=nullptr),p.x,p.y,p.z);
            if(carryTicks==120 && transporting<carried->mConfig->mCarryMinPikis()){
                int count=0;Iterator recruits(pikiMgr);CI_LOOP(recruits){Piki* v=static_cast<Piki*>(*recruits);if(!v->isAlive())continue;v->mActiveAction->abandon(nullptr);v->mActiveAction->mCurrActionIdx=PikiAction::Transport;v->mActiveAction->mChildActions[PikiAction::Transport].initialise(carried);v->mMode=PikiMode::TransportMode;++count;}
                std::printf("P2_RED_P1_TRANSPORT_TASK assigned=%d enemy_state_health_unchanged=1\n",count);
            }
            if(!carried->isAlive()){
                require(reached && distance>100,"P1 corpse removed without route and goal");require(pc_p2_preview_goal()==nullptr && pc_p2_preview_pokos()==-1,"unexpected P2 reward binding");
                std::printf("PASS P2_RED_P1_DELIVERY distance=%.4f reached=1 p2_receipts=not_applicable\n",distance);capture("red-p1-delivery.ppm");std::fflush(stdout);std::_Exit(0);
            }
            if(carryTicks>=2400){capture("red-p1-stalled.ppm");std::puts("FAIL P2_RED_P1_DELIVERY bounded haul stalled");std::fflush(stdout);std::_Exit(1);}
        }
'''


def instrument(source):
    result=combat(source)
    anchor='        if((deadAt && observed-deadAt>=60) || observed>=1800){capture("red-combat-final.ppm");std::puts("DONE P2_RED_COMBAT");std::fflush(stdout);std::_Exit(0);}'
    if result.count(anchor)!=1:raise ValueError('Unexpected combat completion anchor')
    return '#include <algorithm>\n'+result.replace(anchor,DELIVERY)


def evidence(log,code):
    done=re.search(r'PASS P2_RED_P1_DELIVERY distance=([\d.]+) reached=1 p2_receipts=not_applicable',log)
    rows=[dict((k,float(v)) for k,v in re.findall(r'(\w+)=([-+\d.eE]+)',line)) for line in log.splitlines() if line.startswith('P2_RED_P1_HAUL ')]
    checks={'birth_control':log.count('P2_RED_ARENA_BIRTH ')==2,'corpse_render':'P2_KOCHAPPY_DRAW corpse=1' in log,'transport':any(r.get('transport',0)>0 for r in rows),'route_goal':bool(done and float(done[1])>100)}
    return dict(passed=code==0 and all(checks.values()),checks=checks,exit_code=code,rows=rows,transport_task_injected='P2_RED_P1_TRANSPORT_TASK' in log,p2_receipt_gate='not applicable: no Pod; ordinary P1 corpse delivery',unmeasured=['P2 once-credit/idempotency','actual spawned seed yield','player-controlled haul'])


def run(stage,exe,output,seconds=150):
    from experimental.pikmin2_animation_profile import capture_command
    positions(stage);meta=capture_command([str(exe.resolve()),'--experimental-pikmin2-room'],stage,output,seconds)
    result=evidence((output/'native.log').read_text(errors='replace'),meta['exit_code']);result['capture']=meta
    (output/'evidence.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('stage','exe','output'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();r=run(a.stage.resolve(),a.exe.resolve(),a.output.resolve());print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2))
