"""Observe normal Snow-proxy FSM targeting and locomotion without enemy overrides."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

SETUP=r'''
            origin=enemy->getPosition();
            Iterator parked(pikiMgr);CI_LOOP(parked){Piki* v=static_cast<Piki*>(*parked);v->resetPosition(Vector3f(-250,mapMgr->getMinY(-250,-250,true),-250));}
            Vector3f stimulus=origin+Vector3f(-70,0,0);stimulus.y=mapMgr->getMinY(stimulus.x,stimulus.z,true);n->resetPosition(stimulus);
            std::printf("P2_NATURAL_SETUP opted=%d state=%d frozen=%u x=%.7f y=%.7f z=%.7f run=%.7f visible=%.7f\n",int(std::ifstream("p2-snow-chase.txt").good()),int(enemy->mStateID),enemy->mIsFrozen,origin.x,origin.y,origin.z,enemy->getParameterF(TPF_RunVelocity),enemy->getParameterF(TPF_VisibleRange));
            phase=91;ticks=0;return result;
'''

OBSERVER=r'''
        if(phase==91) {
            static int chasing=0;static bool retargeted=false;
            const Vector3f pos=enemy->getPosition(),velocity=enemy->mVelocity,desired=enemy->mTargetVelocity;
            const int state=enemy->mStateID,motion=enemy->mTekiAnimator->getCurrentMotionIndex();
            const bool target=enemy->getCreaturePointer(0)==n;
            const float ground=mapMgr->getMinY(pos.x,pos.z,true);
            std::printf("P2_NATURAL tick=%d dt=%.7f state=%d motion=%d frame=%.7f target=%d frozen=%u x=%.7f y=%.7f z=%.7f vx=%.7f vy=%.7f vz=%.7f tx=%.7f ty=%.7f tz=%.7f face=%.7f ground=%.7f stimulus=%d\n",++ticks,gsys->getFrameTime(),state,motion,enemy->mTekiAnimator->getCounter(),int(target),enemy->mIsFrozen,pos.x,pos.y,pos.z,velocity.x,velocity.y,velocity.z,desired.x,desired.y,desired.z,enemy->getDirection(),ground,int(retargeted));
            require(enemy->mIsFrozen==0 && enemy->isAlive(),"natural Snow stopped being live/unfrozen");
            require(std::isfinite(pos.x)&&std::isfinite(pos.y)&&std::isfinite(pos.z)&&std::fabs(pos.y-ground)<5,"natural chase ground failure");
            if(state==11 && motion==TekiMotion::Move1 && target && std::hypot(desired.x,desired.z)>1)++chasing;
            if(!retargeted && chasing>=20){Vector3f stimulus=pos+Vector3f(0,0,80);stimulus.y=mapMgr->getMinY(stimulus.x,stimulus.z,true);n->resetPosition(stimulus);retargeted=true;std::printf("P2_NATURAL_RETARGET after_tick=%d\n",ticks);}
            if(ticks==200){require(chasing>=30 && retargeted,"natural chase insufficient");std::puts("PASS p2 Snow natural chase observation");std::fflush(stdout);std::_Exit(0);}
            return result;
        }
'''


def instrument(source):
    setup='            float points[][2]=';tick='        if(phase==0) {'
    if source.count(setup)!=1 or source.count(tick)!=1 or 'P2_NATURAL' in source:raise ValueError('Unexpected fixture anchors')
    return '#include <fstream>\n'+source.replace(tick,OBSERVER+tick).replace(setup,SETUP+setup)


def evidence(log,code,opted):
    rows=[dict((k,float(v)) for k,v in re.findall(r'(\w+)=([-+\d.eE]+)',line)) for line in log.splitlines() if line.startswith('P2_NATURAL ')]
    setup=next((line for line in log.splitlines() if line.startswith('P2_NATURAL_SETUP ')),'')
    required={'tick','dt','state','motion','frame','target','frozen','x','y','z','vx','vy','vz','tx','ty','tz','face','ground','stimulus'}
    checks={'mode':f'P2_NATURAL_SETUP opted={int(opted)} ' in setup and ' frozen=0 ' in setup,
            'completion':'PASS p2 Snow natural chase observation' in log,'retarget':log.count('P2_NATURAL_RETARGET after_tick=')==1,
            'rows':len(rows)==200 and [r.get('tick') for r in rows]==list(range(1,201)) and all(set(r)==required and all(math.isfinite(v) for v in r.values()) for r in rows)}
    metrics={}
    if checks['rows']:
        chase=[r for r in rows if r['state']==11 and r['motion']==6 and r['target']==1 and math.hypot(r['tx'],r['tz'])>1]
        checks['natural_chase']=len(chase)>=30 and sum(r['stimulus']==0 for r in chase)>=20 and sum(r['stimulus']==1 for r in chase)>=10
        checks['unfrozen']=all(r['frozen']==0 for r in rows)
        checks['ground']=all(abs(r['y']-r['ground'])<5 and 0<r['dt']<.2 for r in rows)
        checks['animation']=len({round(r['frame'],2) for r in chase})>=5
        checks['movement']=max(math.hypot(r['x']-rows[0]['x'],r['z']-rows[0]['z']) for r in rows)>15 and max(math.hypot(r['vx'],r['vz']) for r in chase or rows)>10
        checks['turning']=bool(chase) and max(abs(math.remainder(r['face']-chase[0]['face'],2*math.pi)) for r in chase)>.15
        if opted:checks['source_speed']=bool(chase) and all(abs(math.hypot(r['tx'],r['tz'])-50)<.02 for r in chase)
        metrics={'chase_ticks':len(chase),'states':sorted({int(r['state']) for r in rows}),'maximum_ground_error':max(abs(r['y']-r['ground']) for r in rows),
                 'maximum_displacement':max(math.hypot(r['x']-rows[0]['x'],r['z']-rows[0]['z']) for r in rows),'observed_dt_sum':sum(r['dt'] for r in rows)}
    return {'passed':code==0 and all(checks.values()),'exit_code':code,'checks':checks,'metrics':metrics,'observations':rows,
            'scope':'Normal P1 proxy AI/animation/physics; captain repositioning only supplies targeting stimuli. No enemy state/target/animation writes or direct behavior calls.',
            'unmeasured':['Pikmin 2 FSM parity','uneven terrain','production campaign combat balance']}


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
    execute.add_argument('--policy',type=Path);args=parser.parse_args()
    if args.command=='instrument':
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x') as stream:stream.write(instrument(args.source.read_text()))
    else:
        result=run(args.assets,args.converted,args.pod,args.snow,args.policy,args.exe,args.output)
        print(json.dumps({'passed':result['passed'],'checks':result['checks'],'metrics':result['metrics']},indent=2));raise SystemExit(0 if result['passed'] else 1)
