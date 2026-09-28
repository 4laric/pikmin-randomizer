"""Private native turn receiver acceptance; not a locomotion/FSM simulation."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

PROBE=r'''
            const bool opted=std::ifstream("p2-snow-turn.txt").good();
            const float dt=NSystem::getFrameTime();
            require(std::isfinite(dt) && dt>0 && dt<0.1f,"unexpected native delta time");
            std::printf("P2_TURN_SETUP opted=%d dt=%.9f receiver=BTeki_turnToward\n",int(opted),dt);
            constexpr float pi=3.14159265358979323846f;
            struct Case { const char* name;float facing,target,speed; };
            const Case cases[]={
                {"positive_cap",0,90,1.8f},{"negative_cap",0,-90,1.8f},
                {"proportional",0,10,0.1f},{"negative_small",0,-10,0.1f},
                {"wrap",359,1,0.1f},{"half_turn",0,180,1.8f},
                {"arrival",0,0.5f,1.8f},{"already_facing",25,25,1.8f},
                {"different_speed",0,90,0.3f},
            };
            auto check=[&](BTeki* actor,const Case& c,bool source,const char* kind) {
                const float facing=c.facing*(pi/180.f),target=c.target*(pi/180.f),arrival=c.speed*dt;
                actor->setDirection(facing);
                float expected=0;bool expectedArrived=false;
                if(source) {
                    float error=std::fmod(target-facing,2*pi);if(error<0)error+=2*pi;if(error>=pi)error-=2*pi;
                    expectedArrived=std::fabs(error)<arrival;
                    float delta=expectedArrived?error:std::max(-pi/18,std::min(pi/18,error*0.4f));
                    expected=facing+delta;
                } else {
                    float current=NMathF::roundAngle(facing),nearer=NMathF::calcNearerDirection(current,target),amount=arrival;
                    if(nearer>current){if(nearer-current<amount){amount=nearer-current;expectedArrived=true;}expected=current+amount;}
                    else {if(current-nearer<amount){amount=current-nearer;expectedArrived=true;}expected=current-amount;}
                }
                const bool actualArrived=actor->turnToward(target,c.speed);
                const float actual=actor->getDirection();
                const float error=std::remainder(actual-expected,2*pi);
                std::printf("P2_TURN case=%s actor=%s angle=%.7f expected=%.7f arrived=%d expected_arrived=%d\n",c.name,kind,actual*(180.f/pi),expected*(180.f/pi),int(actualArrived),int(expectedArrived));
                require(std::isfinite(actual) && std::fabs(error)<0.00001f && actualArrived==expectedArrived,"native turning response mismatch");
            };
            const float savedDirection=enemy->getDirection();
            for(const auto& c:cases)check(enemy,c,opted,"snow");
            Teki* ordinary=tekiMgr->newTeki(TEKI_Chappy);require(ordinary && ordinary!=enemy,"ordinary birth failed");ordinary->reset();
            for(const auto& c:cases)check(ordinary,c,false,"ordinary");
            std::puts("P2_TURN ordinary=pass");
            enemy->clearTekiOption(BTeki::TEKI_OPTION_ALIVE);
            require(!enemy->isAlive(),"nonliving probe flag did not clear");
            for(const auto& c:cases)check(enemy,c,false,"nonliving");
            enemy->setTekiOption(BTeki::TEKI_OPTION_ALIVE);
            std::puts("P2_TURN nonliving=pass");
            pc_p2_snow_forget(enemy);
            for(const auto& c:cases)check(enemy,c,false,"forgotten");
            std::puts("P2_TURN forget=pass");
            pc_p2_snow_setup();
            for(const auto& c:cases)check(enemy,c,opted,"reloaded");
            std::puts("P2_TURN reload=pass");
            pc_p2_snow_reset();
            for(const auto& c:cases)check(enemy,c,false,"reset");
            std::puts("P2_TURN reset=pass");
            enemy->setDirection(savedDirection);
            std::puts("PASS p2 Snow native turn receiver");std::fflush(stdout);std::_Exit(0);
'''

CASES=('positive_cap','negative_cap','proportional','negative_small','wrap','half_turn','arrival','already_facing','different_speed')
ACTORS=('snow','ordinary','nonliving','forgotten','reloaded','reset')


def instrument(source):
    anchor='            float points[][2]='
    if source.count(anchor)!=1 or 'P2_TURN' in source:raise ValueError('Unexpected native room source')
    return '#include <fstream>\n#include <algorithm>\n#include "pc_p2_enemy.h"\n'+source.replace(anchor,PROBE+'\n'+anchor)


def evidence(log,code,opted):
    rows=re.findall(r'P2_TURN case=(\w+) actor=(\w+) angle=([\d.eE+-]+) expected=([\d.eE+-]+) arrived=([01]) expected_arrived=([01])',log)
    mode=re.search(r'P2_TURN_SETUP opted=([01]) dt=([\d.eE+-]+) receiver=BTeki_turnToward',log)
    checks={'mode':bool(mode and (mode[1]=='1')==opted and 0<float(mode[2])<0.1),
            'completion':'PASS p2 Snow native turn receiver' in log}
    for actor in ACTORS:
        matching=[row for row in rows if row[1]==actor]
        checks[actor]=len(matching)==len(CASES) and {row[0] for row in matching}==set(CASES) and all(abs(math.remainder(float(row[2])-float(row[3]),360))<0.001 and row[4]==row[5] for row in matching)
    for marker in ('ordinary','nonliving','forget','reload','reset'):checks[marker+'_marker']=f'P2_TURN {marker}=pass' in log
    if opted:
        from experimental.pikmin2_snow_turn import step
        snow={row[0]:row for row in rows if row[1]=='snow'}
        inputs=((0,90,1.8),(0,-90,1.8),(0,10,0.1),(0,-10,0.1),(359,1,0.1),(0,180,1.8),(0,0.5,1.8),(25,25,1.8),(0,90,0.3))
        wanted={name:step(math.radians(facing),math.radians(target),speed*float(mode[2])) for name,(facing,target,speed) in zip(CASES,inputs)} if mode else {}
        checks['source_outcomes']=bool(wanted) and all(name in snow and abs(math.remainder(float(snow[name][2])-math.degrees(value[0]),360))<0.001 and (snow[name][4]=='1')==value[1] for name,value in wanted.items())
    return {'passed':code==0 and all(checks.values()),'exit_code':code,'checks':checks,'measurements':rows,
            'unmeasured':['natural P2 turn-state selection','complete locomotion','source180 completion'],
            'scope':'Direct native turn receiver calls; controlled actor state, no simulation tick between probes.'}


def run(assets,converted,pod,snow,policy,exe,output,seconds=60):
    from experimental.pikmin2_snow_lifecycle import prepare
    from experimental.pikmin2_snow_turn import install
    from experimental.pikmin2_animation_profile import capture_command
    expected=hashlib.sha256(exe.read_bytes()).hexdigest();output.mkdir(parents=True,exist_ok=False)
    stage=prepare(assets,converted,pod,snow,output/'prepared')
    if policy:install(policy,stage)
    metadata=capture_command([str(exe.resolve()),'--experimental-pikmin2-room'],stage,output/'capture',seconds)
    result=evidence((output/'capture/native.log').read_text(errors='replace'),metadata['exit_code'],policy is not None)
    result['binary_identity']=metadata.get('executable_sha256')==expected;result['executable_sha256']=expected;result['passed'] &= result['binary_identity']
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
