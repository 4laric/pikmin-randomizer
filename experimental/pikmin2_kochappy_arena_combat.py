"""Bounded original-map combat with captain and free-Pikmin placement stimuli."""
import json
import math
from pathlib import Path
import re
import struct
from experimental.pikmin2_kochappy_arena_fixture import instrument as observer,positions


def instrument(source):
    result=observer(source)
    result=result.replace('if(observed==240){std::puts("PASS P2_RED_ARENA observation");std::fflush(stdout);std::_Exit(0);}', '')
    result=result.replace('require(a->isAlive() && !a->mIsFrozen,"arena actor not live/unfrozen");','require(!a->mIsFrozen,"arena actor frozen");')
    marker='        Iterator e(tekiMgr);CI_LOOP(e){Teki* a=static_cast<Teki*>(*e);if(!a->mGenerator)continue;'
    addition=r'''
        static Teki* red=nullptr;static int deadAt=0;
        if(!red){Iterator find(tekiMgr);CI_LOOP(find){Teki* a=static_cast<Teki*>(*find);if(a->mGenerator && a->mGenerator->_70==186001)red=a;}require(red,"Red missing");}
        if(observed==1 || observed==120){Vector3f stimulus=red->getPosition()+Vector3f(observed==1?70:0,0,observed==1?0:80);stimulus.y=mapMgr->getMinY(stimulus.x,stimulus.z,true);n->resetPosition(stimulus);std::printf("P2_RED_COMBAT_STIMULUS tick=%d captain=1\n",observed);}
        if(observed==240){int count=0;Iterator squad(pikiMgr);CI_LOOP(squad){Piki* p=static_cast<Piki*>(*squad);if(!p->isAlive())continue;float angle=float(count)*6.2831853f/20.f;Vector3f point=red->getPosition()+Vector3f(22*std::sin(angle),0,22*std::cos(angle));point.y=mapMgr->getMinY(point.x,point.z,true);p->resetPosition(point);p->changeMode(PikiMode::FreeMode,n);++count;}std::printf("P2_RED_COMBAT_STIMULUS tick=%d free_squad=%d\n",observed,count);require(count==20,"expected20Pikmin");}
        int corpses=0;Iterator cargo(pelletMgr);CI_LOOP(cargo){Pellet* p=static_cast<Pellet*>(*cargo);if(p->mPelletView==static_cast<PelletView*>(red))++corpses;}
        std::printf("P2_RED_COMBAT tick=%d health=%.4f state=%d target=%d x=%.4f y=%.4f z=%.4f corpses=%d\n",observed,red->mHealth,red->mStateID,int(red->getCreaturePointer(0)!=nullptr),red->mSRT.t.x,red->mSRT.t.y,red->mSRT.t.z,corpses);
        if(red->mHealth<200 && observed%30==0)capture("red-combat-damage.ppm");
        if(corpses && !deadAt)deadAt=observed;
        if((deadAt && observed-deadAt>=60) || observed>=1800){capture("red-combat-final.ppm");std::puts("DONE P2_RED_COMBAT");std::fflush(stdout);std::_Exit(0);}
'''
    if result.count(marker)!=1:raise ValueError('Unexpected observer anchor')
    return result.replace(marker,addition+marker)


def prepare(assets,bank,output):
    from experimental.pikmin2_kochappy_arena import prepare as arena
    from scripts.preview_pikmin2_room import records,generator
    from experimental.pikmin2_generator_pose import write_position
    stage=arena(assets,bank,output);path=stage/'assets/dataDir/stages/chal0/default.gen'
    blob=generator(assets);temporary=stage/'template.gen';temporary.write_bytes(blob)
    template=next(r for r in records(temporary) if r[72:76]==b'ikip')
    entries=records(path);used={struct.unpack_from('<I',r,8)[0] for r in entries}
    for i in range(20):
        identity=187000+i
        if identity in used:raise ValueError('Squad ID collision')
        row=bytearray(template);struct.pack_into('<I',row,8,identity);struct.pack_into('>I',row,84,1)
        write_position(row,(-400.+i%5*8,30.,1800.+i//5*8));entries.append(bytes(row))
    path.write_bytes(path.read_bytes()[:20]+struct.pack('>I',len(entries))+b''.join(entries))
    (stage/'combat-stimuli.json').write_text(json.dumps(dict(field_pikmin=20,spawn='free at parked position',captain_reposition_ticks=[1,120],free_squad_deployment_tick=240,enemy_state_health_writes=False),indent=2))
    return stage


def evidence(log,code):
    rows=[dict((k,float(v)) for k,v in re.findall(r'(\w+)=([-+\d.eE]+)',line)) for line in log.splitlines() if line.startswith('P2_RED_COMBAT ')]
    checks={'complete':'DONE P2_RED_COMBAT' in log,'birth_control':log.count('P2_RED_ARENA_BIRTH ')==2,'render':'P2_KOCHAPPY_DRAW corpse=0' in log,'target':any(r.get('target')==1 for r in rows),'damage':any(r.get('health',200)<200 for r in rows),'death_corpse':any(r.get('corpses',0)>0 for r in rows),'corpse_render':'P2_KOCHAPPY_DRAW corpse=1' in log,'chase':any(r.get('state')==11 and r.get('target')==1 for r in rows)}
    metrics={'chase_ticks':sum(r.get('state')==11 and r.get('target')==1 for r in rows),'first_damage_tick':next((r['tick'] for r in rows if r.get('health',200)<200),None),'zero_health_tick':next((r['tick'] for r in rows if r.get('health',200)<=0),None),'corpse_tick':next((r['tick'] for r in rows if r.get('corpses',0)>0),None)}
    return dict(metrics=metrics,passed=code==0 and all(checks.values()),checks=checks,exit_code=code,rows=rows,scope='Captain reposition and20 free Pikmin deployment only; native enemy FSM, health and damage untouched',unmeasured=['player input combat','delivery','P2 FSM parity'])


def run(stage,exe,output,seconds=120):
    from experimental.pikmin2_animation_profile import capture_command
    import hashlib
    positions(stage)
    meta=capture_command([str(exe.resolve()),'--experimental-pikmin2-room'],stage,output,seconds)
    report=evidence((output/'native.log').read_text(errors='replace'),meta['exit_code']);report['capture']=meta
    report['generator_sha256']=hashlib.sha256((stage/'assets/dataDir/stages/chal0/default.gen').read_bytes()).hexdigest()
    (output/'evidence.json').write_text(json.dumps(report,indent=2));return report


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('stage','exe','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--seconds',type=float,default=120)
    a=parser.parse_args();result=run(a.stage.resolve(),a.exe.resolve(),a.output.resolve(),a.seconds);print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
