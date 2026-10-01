"""Controlled TaiTracingAction commands consumed by regular native physics ticks."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

SETUP = r'''
            enemy->resetPosition(Vector3f(0,mapMgr->getMinY(0,0,true),0));
            enemy->mVelocity.set(0,0,0);enemy->mTargetVelocity.set(0,0,0);
            enemy->mIsFrozen=1;enemy->setCreatureFlag(CF_AIAlwaysActive);enemy->resetCreatureFlag(CF_IsPositionFixed);
            enemy->setDirection(0);enemy->startMotion(TekiMotion::Move1);enemy->setCreaturePointer(0,n);
            n->mIsFrozen=1;n->resetPosition(Vector3f(180,mapMgr->getMinY(180,0,true),0));
            n->mVelocity.set(0,0,0);n->mTargetVelocity.set(0,0,0);
            Iterator parked(pikiMgr);CI_LOOP(parked){Piki* v=static_cast<Piki*>(*parked);v->mIsFrozen=1;v->resetPosition(Vector3f(-250,mapMgr->getMinY(-250,-250,true),-250));v->mVelocity.set(0,0,0);v->mTargetVelocity.set(0,0,0);}
            std::printf("P2_PHYS_SETUP opted=%d ticks=60 ai_frozen=1 acceleration=controlled_native physics=regular\n",int(std::ifstream("p2-snow-chase.txt").good()));
            phase=90;ticks=0;return result;
'''

TICK = r'''
        if(phase==90) {
            const bool opted=std::ifstream("p2-snow-chase.txt").good();
            if(ticks>0) {
                const Vector3f pos=enemy->getPosition(),vel=enemy->mVelocity,desired=enemy->mTargetVelocity;
                const float ground=mapMgr->getMinY(pos.x,pos.z,true);
                std::printf("P2_PHYS_OBS tick=%d dt=%.7f x=%.7f y=%.7f z=%.7f vx=%.7f vy=%.7f vz=%.7f tx=%.7f ty=%.7f tz=%.7f face=%.7f ground=%.7f\n",ticks,gsys->getFrameTime(),pos.x,pos.y,pos.z,vel.x,vel.y,vel.z,desired.x,desired.y,desired.z,enemy->getDirection(),ground);
                require(std::isfinite(pos.x)&&std::isfinite(pos.y)&&std::isfinite(pos.z)&&std::fabs(pos.y-ground)<5,"chase actor left ground");
            }
            if(ticks==60) {
                require(std::hypot(enemy->getPosition().x,enemy->getPosition().z)>20,"chase did not move actor");
                std::puts("PASS p2 Snow chase real physics");std::fflush(stdout);std::_Exit(0);
            }
            if(ticks==30){n->resetPosition(Vector3f(-120,mapMgr->getMinY(-120,120,true),120));n->mVelocity.set(0,0,0);n->mTargetVelocity.set(0,0,0);std::puts("P2_PHYS_RETARGET tick=31");}
            enemy->mTargetVelocity.y=ticks<30?7.f:-3.f;
            TaiTracingAction tracing(TekiMotion::Move1,50.f);
            require(tracing.motionStarted(*enemy)&&enemy->getCreaturePointer(0)==n,"chase fixture precondition lost");
            require(!tracing.act(*enemy),"unexpected tracing transition");
            const Vector3f command=enemy->mTargetVelocity;
            require(std::fabs(std::hypot(command.x,command.z)-50)<0.01f && command.y==(opted?(ticks<30?7.f:-3.f):0.f),"chase command mismatch");
            std::printf("P2_PHYS_CMD tick=%d tx=%.7f ty=%.7f tz=%.7f face=%.7f\n",ticks+1,command.x,command.y,command.z,enemy->getDirection());
            enemy->moveVelocity();
            ++ticks;return result;
        }
'''


def instrument(source):
    setup='            float points[][2]='
    tick='        if(phase==0) {'
    if source.count(setup)!=1 or source.count(tick)!=1 or 'P2_PHYS_' in source:
        raise ValueError('Unexpected native fixture anchors')
    return '#include <fstream>\n#include "TAI/MoveActions.h"\n'+source.replace(tick,TICK+tick).replace(setup,SETUP+setup)


def evidence(log,code,opted):
    def rows(prefix):
        return [dict((key,float(value)) for key,value in re.findall(r'(\w+)=([-+\d.eE]+)',line)) for line in log.splitlines() if line.startswith(prefix)]
    commands=rows('P2_PHYS_CMD ');observations=rows('P2_PHYS_OBS ')
    checks={'mode':f'P2_PHYS_SETUP opted={int(opted)} ticks=60 ai_frozen=1 acceleration=controlled_native physics=regular' in log,
            'completion':'PASS p2 Snow chase real physics' in log,'retarget':log.count('P2_PHYS_RETARGET tick=31')==1}
    for name,data,keys in [('commands',commands,{'tick','tx','ty','tz','face'}),('observations',observations,{'tick','dt','x','y','z','vx','vy','vz','tx','ty','tz','face','ground'})]:
        checks[name]=len(data)==60 and [row.get('tick') for row in data]==list(range(1,61)) and all(set(row)==keys and all(math.isfinite(v) for v in row.values()) for row in data)
    if checks['commands'] and checks['observations']:
        checks['command_speed_y']=all(abs(math.hypot(r['tx'],r['tz'])-50)<.01 and r['ty']==((7 if r['tick']<=30 else -3) if opted else 0) for r in commands)
        checks['consumed_command']=all(all(abs(c[k]-o[k])<.001 for k in ('tx','ty','tz')) for c,o in zip(commands,observations))
        checks['ground']=all(abs(r['y']-r['ground'])<5 and 0<r['dt']<.2 for r in observations)
        checks['motion']=math.hypot(observations[-1]['x'],observations[-1]['z'])>20 and max(math.hypot(r['vx'],r['vz']) for r in observations)>10
        checks['retarget_velocity']=commands[0]['tx']>0 and commands[-1]['tx']<0
    metrics={}
    if checks['observations']:
        previous=(0,0);distance=0
        for row in observations:
            distance+=math.hypot(row['x']-previous[0],row['z']-previous[1]);previous=(row['x'],row['z'])
        metrics={'observed_dt_sum':sum(row['dt'] for row in observations),'horizontal_path_length':distance,
                 'horizontal_net_displacement':math.hypot(*previous),'maximum_ground_error':max(abs(row['y']-row['ground']) for row in observations),
                 'maximum_horizontal_speed':max(math.hypot(row['vx'],row['vz']) for row in observations)}
    return {'passed':code==0 and all(checks.values()),'exit_code':code,'checks':checks,'commands':commands,'observations':observations,'metrics':metrics,
            'scope':'AI/animation frozen; actual TaiTracingAction and one explicit native moveVelocity acceleration call followed by regular engine movement/collision/rotation ticks.',
            'unmeasured':['natural FSM scheduling','source locomotion physics parity','animation timing','uneven terrain navigation']}


def run(assets,converted,pod,snow,policy,exe,output,seconds=60):
    from experimental.pikmin2_snow_lifecycle import prepare
    from experimental.pikmin2_snow_chase import install
    from experimental.pikmin2_animation_profile import capture_command
    expected=hashlib.sha256(exe.read_bytes()).hexdigest();output.mkdir(parents=True,exist_ok=False)
    stage=prepare(assets,converted,pod,snow,output/'prepared')
    if policy:install(policy,stage)
    meta=capture_command([str(exe.resolve()),'--experimental-pikmin2-room'],stage,output/'capture',seconds)
    result=evidence((output/'capture/native.log').read_text(errors='replace'),meta['exit_code'],policy is not None)
    result['binary_identity']=meta.get('executable_sha256')==expected;result['executable_sha256']=expected;result['passed'] &= result['binary_identity']
    (output/'evidence.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    patch=sub.add_parser('instrument');patch.add_argument('--source',type=Path,required=True);patch.add_argument('--output',type=Path,required=True)
    execute=sub.add_parser('run')
    for name in ('assets','converted','pod','snow','exe','output'):execute.add_argument('--'+name,type=Path,required=True)
    execute.add_argument('--policy',type=Path)
    args=parser.parse_args()
    if args.command=='instrument':
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x') as stream:stream.write(instrument(args.source.read_text()))
    else:
        result=run(args.assets,args.converted,args.pod,args.snow,args.policy,args.exe,args.output)
        print(json.dumps({'passed':result['passed'],'checks':result['checks']},indent=2));raise SystemExit(0 if result['passed'] else 1)
