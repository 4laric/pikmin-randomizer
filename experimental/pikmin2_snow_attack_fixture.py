"""Private native attack-entry receiver fixture; no bite/FSM fidelity claim."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

TARGET=r'''
#include <fstream>
#include "pc_p2_enemy.h"
class SnowGateTarget : public Creature {
public:
 bool visible=true,alive=true,buried=false;
 SnowGateTarget():Creature(nullptr) { mStickTarget=nullptr; }
 bool isVisible() override { return visible; }
 bool isAlive() override { return alive; }
 bool isBuried() override { return buried; }
 void refresh(Graphics&) override {}
 void doKill() override {}
};
'''

PROBE=r'''
            const bool opted=std::ifstream("p2-snow-attack.txt").good();
            std::printf("P2_GATE_SETUP opted=%d receiver=BTeki_attackableCreature\n",int(opted));
            SnowGateTarget target;
            const Vector3f origin=enemy->getPosition();
            const float savedDirection=enemy->getDirection();
            constexpr float pi=3.14159265358979323846f;
            auto original=[&](BTeki* actor) {
                if(target.getStickObject()==actor)return false;
                if(!actor->contactCreature(target))return false;
                return actor->calcTargetAngle(target.getPosition())<=NMathF::d2r(actor->getParameterF(TPF_AttackableAngle))/2.f;
            };
            struct Case { const char* name;float distance,y,angle,face; };
            const Case cases[]={
                {"inside",29,0,0,0},{"boundary",30,0,0,0},{"outside",31,0,0,0},
                {"vertical_inside",20,20,0,0},{"vertical_outside",20,23,0,0},
                {"angle_inside",20,0,19.9f,0},{"angle_outside",20,0,20.1f,0},
                {"angle_negative_inside",20,0,-19.9f,0},{"angle_negative_outside",20,0,-20.1f,0},
                {"wrap_inside",20,0,1,359},{"wrap_outside",20,0,21,359},
            };
            auto check=[&](BTeki* actor,const Case& c,bool usePolicy,const char* kind) {
                actor->setDirection(c.face*(pi/180.f));
                target.mSRT.t=origin+Vector3f(c.distance*std::sin(c.angle*(pi/180.f)),c.y,c.distance*std::cos(c.angle*(pi/180.f)));
                target.mGrid.updateGrid(target.mSRT.t);actor->mGrid.updateGrid(actor->mSRT.t);
                const Vector3f delta=target.getPosition()-actor->getPosition();
                const float d2=delta.x*delta.x+delta.y*delta.y+delta.z*delta.z;
                const float angle=actor->calcTargetAngle(target.getPosition());
                const bool source=d2<900.f && std::fabs(std::remainder(angle,2*pi))<=20.f*(pi/180.f);
                const bool expected=usePolicy?source:original(actor);
                const bool actual=actor->attackableCreature(target);
                std::printf("P2_GATE case=%s actor=%s actual=%d expected=%d d2=%.6f angle=%.6f\n",c.name,kind,int(actual),int(expected),d2,angle*(180.f/pi));
                require(actual==expected,"native attack-entry geometry mismatch");
            };
            for(const auto& c:cases)check(enemy,c,opted,"snow");
            enemy->setDirection(0);target.mSRT.t=origin+Vector3f(0,0,10);target.mGrid.updateGrid(target.mSRT.t);
            require(enemy->attackableCreature(target),"eligible target was rejected");
            target.visible=false;require(!enemy->attackableCreature(target),"invisible target accepted");target.visible=true;
            target.alive=false;require(!enemy->attackableCreature(target),"dead target accepted");target.alive=true;
            target.buried=true;require(!enemy->attackableCreature(target),"buried target accepted");target.buried=false;
            target.mStickTarget=enemy;require(!enemy->attackableCreature(target),"self-stuck target accepted");target.mStickTarget=nullptr;
            std::puts("P2_GATE eligibility=pass self_stick=pass");
            Teki* ordinary=tekiMgr->newTeki(TEKI_Chappy);require(ordinary && ordinary!=enemy,"ordinary actor birth failed");ordinary->reset();
            ordinary->resetPosition(origin);
            for(const auto& c:cases)check(ordinary,c,false,"ordinary");
            std::puts("P2_GATE ordinary=pass");
            Teki* recycle=enemy;
            if(!recycle->removable()) {
                // Register the freshly born, unreferenced probe actor through
                // the real bank setup, borrowing identity only during setup.
                auto* generator=enemy->mGenerator;
                enemy->mGenerator=nullptr;ordinary->mGenerator=generator;
                pc_p2_snow_setup();
                enemy->mGenerator=generator;ordinary->mGenerator=nullptr;
                require(pc_p2_enemy_name(static_cast<PelletView*>(ordinary))!=nullptr,"fresh probe Snow registration failed");
                for(const auto& c:cases)check(ordinary,c,opted,"fresh_snow");
                recycle=ordinary;
                std::puts("P2_GATE recycle_target=fresh_registered_actor");
            }
            if(recycle->removable()) {
                tekiMgr->kill(recycle);Teki* reused=tekiMgr->newTeki(TEKI_Chappy);
                require(reused==recycle,"native slot not reused");reused->reset();reused->resetPosition(origin);
                require(!pc_p2_enemy_name(static_cast<PelletView*>(reused)),"reused actor kept Snow identity");
                for(const auto& c:cases)check(reused,c,false,"reused");
                std::puts("P2_GATE slot_reuse=pass");
            } else std::puts("P2_GATE slot_reuse=unmeasured actor_not_removable");
            enemy->setDirection(savedDirection);
            std::puts("PASS p2 Snow native attack-entry receiver");std::fflush(stdout);std::_Exit(0);
'''

CASES=('inside','boundary','outside','vertical_inside','vertical_outside','angle_inside','angle_outside','angle_negative_inside','angle_negative_outside','wrap_inside','wrap_outside')


def instrument(source):
    anchor='            float points[][2]='
    if source.count(anchor)!=1 or source.count('class RoomApp')!=1 or 'P2_GATE' in source:raise ValueError('Unexpected room fixture source')
    return source.replace('class RoomApp',TARGET+'\nclass RoomApp',1).replace(anchor,PROBE+'\n'+anchor)


def evidence(log,code,opted):
    rows=re.findall(r'P2_GATE case=(\w+) actor=(\w+) actual=([01]) expected=([01]) d2=([\d.eE+-]+) angle=([\d.eE+-]+)',log)
    checks={'mode':f'P2_GATE_SETUP opted={int(opted)} receiver=BTeki_attackableCreature' in log,
            'eligibility':'P2_GATE eligibility=pass self_stick=pass' in log,
            'ordinary':'P2_GATE ordinary=pass' in log,'completion':'PASS p2 Snow native attack-entry receiver' in log}
    for kind in ('snow','ordinary'):
        matching=[row for row in rows if row[1]==kind]
        checks[kind+'_cases']=len(matching)==len(CASES) and {r[0] for r in matching}==set(CASES) and all(r[2]==r[3] for r in matching)
    if opted:
        snow=[row for row in rows if row[1]=='snow']
        checks['source_geometry']=all((row[2]=='1')==(float(row[4])<900 and abs(math.remainder(math.radians(float(row[5])),2*math.pi))<=math.radians(20)) for row in snow)
        positive={'inside','vertical_inside','angle_inside','angle_negative_inside','wrap_inside'}
        checks['boundary_outcomes']=all((row[2]=='1')==(row[0] in positive) for row in snow)
    if 'P2_GATE recycle_target=fresh_registered_actor' in log:
        matching=[row for row in rows if row[1]=='fresh_snow']
        checks['fresh_registration_cases']=len(matching)==len(CASES) and {r[0] for r in matching}==set(CASES) and all(r[2]==r[3] for r in matching)
    reuse='P2_GATE slot_reuse=pass' in log
    if reuse:
        matching=[row for row in rows if row[1]=='reused']
        checks['reuse_cases']=len(matching)==len(CASES) and {r[0] for r in matching}==set(CASES) and all(r[2]==r[3] for r in matching)
    return {'passed':code==0 and all(checks.values()),'exit_code':code,'checks':checks,'slot_reuse':reuse,'measurements':rows,
            'unmeasured':([] if reuse else ['native same-address reuse'])+['actual bite hit/capture','P2 attack event timing'],
            'scope':'Actual BTeki receiver with a controlled Creature target; no game tick occurs during probes.'}


def run(assets,converted,pod,snow,policy,exe,output,seconds=60):
    from experimental.pikmin2_snow_lifecycle import prepare
    from experimental.pikmin2_snow_attack import install
    from experimental.pikmin2_animation_profile import capture_command
    expected=hashlib.sha256(exe.read_bytes()).hexdigest();output.mkdir(parents=True,exist_ok=False)
    stage=prepare(assets,converted,pod,snow,output/'prepared')
    if policy:install(policy,stage)
    metadata=capture_command([str(exe.resolve()),'--experimental-pikmin2-room'],stage,output/'capture',seconds)
    result=evidence((output/'capture/native.log').read_text(errors='replace'),metadata['exit_code'],policy is not None)
    result['binary_identity']=metadata.get('executable_sha256')==expected
    result['executable_sha256']=expected;result['passed'] &= result['binary_identity']
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
