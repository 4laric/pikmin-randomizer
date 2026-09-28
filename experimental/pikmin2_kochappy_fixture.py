"""Private Red identity/health and lifecycle probes; P1-stage arena remains separate."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

PROBE=r'''
            const bool red=std::ifstream("p2-kochappy-profile.txt").good();
            const bool longRun=std::ifstream("p2-red-lifecycle.txt").good();
            const float fallback=enemy->mTekiParams->getF(TPF_Life),redExpected=red?200.f:fallback;
            require(enemy->mHealth==redExpected && enemy->getParameterF(TPF_Life)==redExpected,"Red initial/max health mismatch");
            const char* identity=pc_p2_enemy_name(enemy);
            require(red?(identity && std::strcmp(identity,"Dwarf Red Bulborb")==0):identity==nullptr,"Red source identity mismatch");
            std::printf("P2_RED_HEALTH opted=%d initial=%.1f max=%.1f fallback=%.1f\n",int(red),enemy->mHealth,enemy->getParameterF(TPF_Life),fallback);
            Teki* control=tekiMgr->newTeki(TEKI_Chappy);require(control && control!=enemy,"ordinary control birth failed");control->reset();
            control->resetPosition(Vector3f(-280,mapMgr->getMinY(-280,-280,true),-280));
            const float controlDefault=control->mTekiParams->getF(TPF_Life);
            require(control->mHealth==controlDefault && control->getParameterF(TPF_Life)==controlDefault && !pc_p2_enemy_name(control),"ordinary control inherited Red profile");
            std::printf("P2_RED_CONTROL initial=%.1f max=%.1f fallback=%.1f name=none\n",control->mHealth,control->getParameterF(TPF_Life),controlDefault);
            if(!longRun){
                pc_p2_kochappy_forget(enemy);require(enemy->getParameterF(TPF_Life)==fallback && !pc_p2_enemy_name(enemy),"Red forget retained registration");std::puts("P2_RED_REGISTRY forget=pass");
                pc_p2_kochappy_setup();require(enemy->mHealth==redExpected && enemy->getParameterF(TPF_Life)==redExpected,"Red reload mismatch");std::puts("P2_RED_REGISTRY reload=pass");
                if(enemy->removable()){
                    tekiMgr->kill(enemy);Teki* reused=tekiMgr->newTeki(TEKI_Chappy);require(reused==enemy,"expected same native slot");reused->reset();
                    require(reused->mHealth==fallback && reused->getParameterF(TPF_Life)==fallback && !pc_p2_enemy_name(reused),"Red native slot reuse leaked");std::puts("P2_RED_REGISTRY slot_reuse=pass");
                }else std::puts("P2_RED_REGISTRY slot_reuse=unmeasured");
                pc_p2_kochappy_reset();require(pc_p2_kochappy_max_health(enemy,fallback)==fallback && !pc_p2_kochappy_name(enemy),"Red reset retained registration");std::puts("P2_RED_REGISTRY reset=pass");
                std::puts("PASS p2 Red health registry");std::fflush(stdout);std::_Exit(0);
            }
'''

CORPSE=r'''
        if(enemy && corpse && phase==6 && corpse->mPelletView==static_cast<PelletView*>(enemy)){
            static bool checked=false;if(!checked){
                require(enemy->getParameterF(TPF_Life)==200 && pc_p2_kochappy_name(enemy),"Red corpse lost identity/max health");
                std::puts("P2_RED_CORPSE max=200 identity=Kochappy");checked=true;
            }
        }
'''


def instrument(source):
    from experimental.pikmin2_snow_lifecycle import instrument as lifecycle
    anchor='            float points[][2]='
    if source.count(anchor)!=1 or 'P2_RED_HEALTH' in source:raise ValueError('Unexpected fixture source')
    camera='            cameraLog(n,"START");capture("p2-room-start.ppm");'
    if source.count(camera)!=1:raise ValueError('Missing native camera anchor')
    source=source.replace(camera,'''            if(ticks<90){
                if(ticks==60){Vector3f near=enemy->getPosition()-Vector3f(70,0,30);near.y=mapMgr->getMinY(near.x,near.z,true);n->resetPosition(near);}
                return result;
            }
'''+camera)
    source=lifecycle(source).replace('P2_SNOW_LIFECYCLE','P2_RED_LIFECYCLE').replace('snow-attack.ppm','red-attack.ppm').replace('snow-death.ppm','red-death.ppm').replace('snow-carried.ppm','red-carried.ppm')
    source=source.replace('        static unsigned snowGenerator=0;',CORPSE+'\n        static unsigned snowGenerator=0;')
    end='require(corpseReachedGoal && corpseDistance>(assembled?1000:100),'
    reset='''pc_p2_kochappy_reset();
                require(!pc_p2_kochappy_name(static_cast<PelletView*>(enemy)) && pc_p2_kochappy_max_health(enemy,130)==130,"post-delivery registry leak");
                std::puts("P2_RED_REGISTRY post_delivery_reset=pass");
                '''
    return '#include <fstream>\n#include <cstring>\n#include "pc_p2_kochappy.h"\n#include "pc_p2_enemy.h"\n'+source.replace(anchor,PROBE+anchor).replace(end,reset+end)


def prepare(assets,converted,pod,bank,output,red=True,lifecycle=False):
    from scripts.preview_pikmin2_room import prepare as room,records
    from experimental.pikmin2_kochappy_bank import install
    stage=room(assets,converted,output)
    private=stage/'assets/dataDir/courses/pikmin2room'
    for name in ('pod.mod','treasure.mod'):(private/name).write_bytes((pod/name).read_bytes())
    (stage/'p2-pod.txt').write_bytes((pod/'p2-pod.txt').read_bytes())
    actors=[]
    gen=stage/'assets/dataDir/stages/chal0/default.gen'
    for entry in records(gen):
        if entry[72:76]!=b'iket':continue
        xyz=struct.unpack_from('>3f',entry,48);offset=struct.unpack_from('>3f',entry,60)
        actors.append({'generator':struct.unpack_from('<I',entry,8)[0],'position':xyz,'offset':offset,'expected_xyz':[a+b for a,b in zip(xyz,offset)],'source_yaw':'unapplied'})
    if len(actors)!=1:raise ValueError('Expected exactly one room scaffold actor')
    from experimental.pikmin2_uji_grounded_fixture import deterministic_births
    normalization=deterministic_births(gen,{actors[0]['generator']})
    if red:install(bank,stage,[actors[0]['generator']])
    if lifecycle:(stage/'p2-red-lifecycle.txt').write_text('1\n')
    manifest={'stage':'private imported room; P1 arena untested','actors':actors,'birth_area_override':normalization,'generator_sha256':hashlib.sha256(gen.read_bytes()).hexdigest(),'bank_sha256':hashlib.sha256((bank/'kochappy-bank.json').read_bytes()).hexdigest()}
    (stage/'red-fixture.json').write_text(json.dumps(manifest,indent=2));return stage,manifest


def evidence(log,code,manifest,red=True,lifecycle=False):
    health=re.search(r'P2_RED_HEALTH opted=([01]) initial=([\d.]+) max=([\d.]+) fallback=([\d.]+)',log)
    control=re.search(r'P2_RED_CONTROL initial=([\d.]+) max=([\d.]+) fallback=([\d.]+) name=none',log)
    checks={'health':False,'ordinary':bool(control and float(control[1])==float(control[2])==float(control[3]))}
    if health:checks['health']=int(health[1])==int(red) and float(health[2])==float(health[3])==(200 if red else float(health[4]))
    if red:
        ready=re.findall(r'P2_ENEMY_READY species=Kochappy source_id=1 native_family=Chappy generator=(\d+) x=([-\d.]+) y=([-\d.]+) z=([-\d.]+) health=200.0 max_health=200.0',log)
        actor=manifest['actors'][0]
        # First setup is spawn acceptance; explicit later profile reload occurs after AI movement.
        checks['spawn_xyz']=bool(ready and int(ready[0][0])==actor['generator'] and all(abs(float(a)-b)<.01 for a,b in zip(ready[0][1:],actor['expected_xyz'])))
        checks['live_visual']='P2_KOCHAPPY_DRAW corpse=0' in log
    if lifecycle:
        for stage in ('attack','death','carried','duplicate_credit'):checks[stage]=f'P2_RED_LIFECYCLE stage={stage}' in log
        checks['corpse']='P2_RED_CORPSE max=200 identity=Kochappy' in log and 'P2_KOCHAPPY_DRAW corpse=1' in log
        checks['reset']='P2_RED_REGISTRY post_delivery_reset=pass' in log
        checks['completion']='PASS p2 room: actors, ground, controller movement, native carry delivery, unchanged repairs, native combat kill, far corpse transport and delivery' in log
    else:
        for stage in ('forget','reload','reset'):checks[stage]=f'P2_RED_REGISTRY {stage}=pass' in log
        checks['completion']='PASS p2 Red health registry' in log
    reused='P2_RED_REGISTRY slot_reuse=pass' in log
    return {'passed':code==0 and all(checks.values()),'exit_code':code,'checks':checks,'slot_reuse':reused,
            'scope':'Private imported-room module validation. Lifecycle assigns Pikmin attack/possibly transport actions; no health-zero kill.',
            'unmeasured':['P1-stage arena','manual natural combat','scene-manager reconstruction']+([] if reused else ['actual manager slot reuse'])}


def run(assets,converted,pod,bank,exe,output,red=True,lifecycle=False,seconds=180):
    from experimental.pikmin2_animation_profile import capture_command
    output.mkdir(parents=True,exist_ok=False);expected=hashlib.sha256(exe.read_bytes()).hexdigest()
    stage,manifest=prepare(assets,converted,pod,bank,output/'prepared',red,lifecycle)
    meta=capture_command([str(exe.resolve()),'--experimental-pikmin2-room'],stage,output/'capture',seconds)
    result=evidence((output/'capture/native.log').read_text(errors='replace'),meta['exit_code'],manifest,red,lifecycle)
    result['executable_sha256']=expected;result['binary_identity']=meta.get('executable_sha256')==expected;result['passed'] &= result['binary_identity'];result['stage']=str(stage);result['manifest']=manifest
    (output/'evidence.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    patch=sub.add_parser('instrument');patch.add_argument('--source',type=Path,required=True);patch.add_argument('--output',type=Path,required=True)
    execute=sub.add_parser('run')
    for name in ('assets','converted','pod','bank','exe','output'):execute.add_argument('--'+name,type=Path,required=True)
    execute.add_argument('--baseline',action='store_true');execute.add_argument('--lifecycle',action='store_true');args=parser.parse_args()
    if args.command=='instrument':
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x') as stream:stream.write(instrument(args.source.read_text()))
    else:
        result=run(args.assets,args.converted,args.pod,args.bank,args.exe,args.output,not args.baseline,args.lifecycle)
        print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
