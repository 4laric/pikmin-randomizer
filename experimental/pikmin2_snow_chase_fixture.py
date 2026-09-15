"""Private TaiTracingAction receiver fixture; physics and FSM remain unmeasured."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

PROBE=r'''
            const bool opted=std::ifstream("p2-snow-chase.txt").good();
            std::printf("P2_TRACE_SETUP opted=%d receiver=TaiTracingAction_act fallback_speed=37\n",int(opted));
            constexpr float pi=3.14159265358979323846f;
            const Vector3f savedTarget=n->getPosition();
            const float savedFacing=enemy->getDirection();
            TaiTracingAction tracing(TekiMotion::Move1,37.f);
            auto untouched=[&](const char* label) {
                const Vector3f before(5,7,9);enemy->mTargetVelocity=before;enemy->setDirection(0.25f);
                require(!tracing.act(*enemy),"tracing unexpectedly requested state transition");
                require(enemy->mTargetVelocity.x==before.x && enemy->mTargetVelocity.y==before.y && enemy->mTargetVelocity.z==before.z && enemy->getDirection()==0.25f,"guard mutated chase state");
                std::printf("P2_TRACE guard=%s pass=1\n",label);
            };
            enemy->setCreaturePointer(0,n);enemy->startMotion(TekiMotion::Wait1);
            require(!enemy->animationFinished() && !tracing.motionStarted(*enemy),"fixture motion guard not established");untouched("motion");
            enemy->startMotion(TekiMotion::Move1);enemy->setCreaturePointer(0,nullptr);
            require(tracing.motionStarted(*enemy),"fixture Move1 not started");untouched("no_target");
            struct Case { const char* name;float facing,x,z,y; };
            const Case cases[]={{"right",0,100,0,7},{"left",0,-100,0,-13},{"ahead",0,0,100,5},{"small",0,17.364818f,98.480774f,9},{"wrap",359,1.74524f,99.98477f,-2}};
            auto check=[&](Teki* actor,const Case& c,bool source,const char* kind) {
                actor->startMotion(TekiMotion::Move1);actor->setCreaturePointer(0,n);actor->setDirection(c.facing*(pi/180.f));
                actor->mTargetVelocity.set(3,c.y,4);n->mSRT.t=actor->getPosition()+Vector3f(c.x,12,c.z);
                const float before=actor->getDirection();float expectedFacing=before;Vector3f expectedVelocity;
                if(source) {
                    float error=std::fmod(actor->calcTargetDirection(n->getPosition())-before,2*pi);if(error<0)error+=2*pi;if(error>=pi)error-=2*pi;
                    expectedFacing=before+std::max(-pi/18,std::min(pi/18,error*0.4f));
                    expectedVelocity.set(50*std::sin(expectedFacing),c.y,50*std::cos(expectedFacing));
                } else BTeki::moveTowardStatic(actor->getPosition(),n->getPosition(),37,expectedVelocity);
                require(!tracing.act(*actor),"tracing unexpectedly transitioned");
                const Vector3f actual=actor->mTargetVelocity;const float angle=actor->getDirection();
                std::printf("P2_TRACE case=%s actor=%s angle=%.7f expected_angle=%.7f vx=%.7f vy=%.7f vz=%.7f expected_x=%.7f expected_y=%.7f expected_z=%.7f\n",c.name,kind,angle*(180.f/pi),expectedFacing*(180.f/pi),actual.x,actual.y,actual.z,expectedVelocity.x,expectedVelocity.y,expectedVelocity.z);
                require(std::fabs(std::remainder(angle-expectedFacing,2*pi))<0.00001f && std::fabs(actual.x-expectedVelocity.x)<0.0002f && actual.y==expectedVelocity.y && std::fabs(actual.z-expectedVelocity.z)<0.0002f,"native tracing output mismatch");
                actor->setCreaturePointer(0,nullptr);
            };
            for(const auto& c:cases)check(enemy,c,opted,"snow");
            Teki* ordinary=tekiMgr->newTeki(TEKI_Chappy);require(ordinary && ordinary!=enemy,"ordinary birth failed");ordinary->reset();
            for(const auto& c:cases)check(ordinary,c,false,"ordinary");
            enemy->clearTekiOption(BTeki::TEKI_OPTION_ALIVE);require(!enemy->isAlive(),"nonliving fixture flag failed");
            for(const auto& c:cases)check(enemy,c,false,"nonliving");enemy->setTekiOption(BTeki::TEKI_OPTION_ALIVE);
            pc_p2_snow_forget(enemy);for(const auto& c:cases)check(enemy,c,false,"forgotten");
            pc_p2_snow_setup();for(const auto& c:cases)check(enemy,c,opted,"reloaded");
            pc_p2_snow_reset();for(const auto& c:cases)check(enemy,c,false,"reset");
            n->mSRT.t=savedTarget;enemy->setDirection(savedFacing);
            std::puts("PASS p2 Snow native tracing receiver");std::fflush(stdout);std::_Exit(0);
'''
CASES=('right','left','ahead','small','wrap')
ACTORS=('snow','ordinary','nonliving','forgotten','reloaded','reset')


def instrument(source):
    anchor='            float points[][2]='
    if source.count(anchor)!=1 or 'P2_TRACE' in source:raise ValueError('Unexpected native fixture')
    return '#include <fstream>\n#include <algorithm>\n#include "TAI/MoveActions.h"\n#include "pc_p2_enemy.h"\n'+source.replace(anchor,PROBE+'\n'+anchor)


def evidence(log,code,opted):
    number=r'([\d.eE+-]+)'
    rows=re.findall(r'P2_TRACE case=(\w+) actor=(\w+) angle='+number+r' expected_angle='+number+r' vx='+number+r' vy='+number+r' vz='+number+r' expected_x='+number+r' expected_y='+number+r' expected_z='+number,log)
    checks={'mode':f'P2_TRACE_SETUP opted={int(opted)} receiver=TaiTracingAction_act fallback_speed=37' in log,
            'motion_guard':'P2_TRACE guard=motion pass=1' in log,'target_guard':'P2_TRACE guard=no_target pass=1' in log,
            'completion':'PASS p2 Snow native tracing receiver' in log}
    for actor in ACTORS:
        matching=[row for row in rows if row[1]==actor]
        checks[actor]=len(matching)==len(CASES) and {row[0] for row in matching}==set(CASES) and all(abs(math.remainder(float(row[2])-float(row[3]),360))<0.001 and all(abs(float(row[i])-float(row[i+3]))<0.0003 for i in (4,5,6)) for row in matching)
    if opted:
        snow={row[0]:row for row in rows if row[1]=='snow'}
        expected_y=dict(zip(CASES,(7,-13,5,9,-2)))
        checks['source_speed_y']=len(snow)==len(CASES) and all(abs(math.hypot(float(row[4]),float(row[6]))-50)<0.001 and float(row[5])==expected_y[name] for name,row in snow.items() if name in expected_y)
        right=snow.get('right');checks['turn_first']=bool(right and abs(float(right[2])-10)<0.001 and abs(float(right[4])-8.6824089)<0.001)
    return {'passed':code==0 and all(checks.values()),'exit_code':code,'checks':checks,'measurements':rows,
            'unmeasured':['natural chase state selection','full physics/collision locomotion','source animation timing'],
            'scope':'Actual TaiTracingAction calls with controlled motion/target state; no movement tick between cases.'}


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
        print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
