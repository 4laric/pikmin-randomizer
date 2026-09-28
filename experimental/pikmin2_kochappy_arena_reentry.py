"""Actual TekiMgr replacement and generator rebirth; not a full scene reload."""
import json
import re
from pathlib import Path
from experimental.pikmin2_kochappy_arena_fixture import instrument as observer,positions

CYCLE=r'''
        if(observed==120){
            TekiMgr* oldManager=tekiMgr;Teki* oldRed=nullptr;Generator* generators[2]={nullptr,nullptr};
            Iterator prior(oldManager);CI_LOOP(prior){Teki* a=static_cast<Teki*>(*prior);if(!a->mGenerator)continue;if(a->mGenerator->_70==186001){oldRed=a;generators[0]=a->mGenerator;}if(a->mGenerator->_70==186002)generators[1]=a->mGenerator;}
            require(oldRed && generators[0] && generators[1],"reentry original roster missing");
            oldManager->killAll();tekiMgr=nullptr;
            int previous=gsys->setHeap(SYSHEAP_App);tekiMgr=new TekiMgr();
            require(tekiMgr!=oldManager,"manager instance not replaced");
            require(!pc_p2_kochappy_name(oldRed) && pc_p2_kochappy_max_health(oldRed,130)==130,"old actor registry survived constructor");
            tekiMgr->mUsingType[TEKI_Chappy]=true;tekiMgr->startStage();
            for(Generator* gen:generators)gen->mGenType->init(gen);
            Teki* newRed=static_cast<Teki*>(generators[0]->mLatestSpawnCreature);Teki* control=static_cast<Teki*>(generators[1]->mLatestSpawnCreature);
            require(newRed && control && newRed!=oldRed,"new actor not allocated");
            require(!pc_p2_kochappy_name(newRed) && newRed->getParameterF(TPF_Life)==130 && control->getParameterF(TPF_Life)==130,"new actors inherited registration before setup");
            pc_p2_kochappy_setup();
            require(pc_p2_kochappy_name(newRed) && newRed->mHealth==200 && newRed->getParameterF(TPF_Life)==200,"new Red profile failed");
            require(!pc_p2_kochappy_name(control) && control->mHealth==130 && control->getParameterF(TPF_Life)==130,"new control inherited profile");
            for(int i=0;i<2;++i){Teki* a=i==0?newRed:control;Vector3f b=a->mPersonality->mPosition,g=generators[i]->getPos();require(std::fabs(b.x-g.x)<.02 && std::fabs(b.y-g.y)<.02 && std::fabs(b.z-g.z)<.02,"rebirth position changed");}
            gsys->setHeap(previous);
            std::printf("P2_RED_REENTRY old_manager=%p new_manager=%p old_actor=%p new_actor=%p old_registry=clear before_setup=130 new_red=200 control=130 birth=pass\n",(void*)oldManager,(void*)tekiMgr,(void*)oldRed,(void*)newRed);
        }
'''


def instrument(source):
    result=observer(source)
    anchor='        Iterator e(tekiMgr);CI_LOOP(e){Teki* a=static_cast<Teki*>(*e);if(!a->mGenerator)continue;'
    if result.count(anchor)!=1:raise ValueError('Unexpected observer')
    return result.replace(anchor,CYCLE+anchor).replace('PASS P2_RED_ARENA observation','PASS P2_RED_REENTRY observation')


def evidence(log,code):
    line=next((x for x in log.splitlines() if x.startswith('P2_RED_REENTRY ')), '')
    rows=[dict((k,float(v)) for k,v in re.findall(r'(\w+)=([-+\d.eE]+)',x)) for x in log.splitlines() if x.startswith('P2_RED_ARENA_TICK ')]
    checks={'replacement':'old_registry=clear before_setup=130 new_red=200 control=130 birth=pass' in line,'completion':'PASS P2_RED_REENTRY observation' in log,'post_reentry_updates':sum(r.get('tick',0)>120 for r in rows)==240,'post_animation':all(len({r.get('frame') for r in rows if r.get('tick',0)>120 and r.get('id')==i})>2 for i in (186001,186002))}
    return dict(passed=code==0 and all(checks.values()),checks=checks,exit_code=code,reentry=line,scope='Actual manager killAll/null/new/startStage and native generator init; family setup registration after rebirth',unmeasured=['whole scene/heap teardown','save/load campaign reentry','same-address allocator reuse'])


def run(stage,exe,output,seconds=90):
    from experimental.pikmin2_animation_profile import capture_command
    import hashlib
    positions(stage);meta=capture_command([str(exe.resolve()),'--experimental-pikmin2-room'],stage,output,seconds)
    result=evidence((output/'native.log').read_text(errors='replace'),meta['exit_code']);result['capture']=meta
    result['profile_sha256']=hashlib.sha256((stage/'p2-kochappy-profile.txt').read_bytes()).hexdigest();result['bank_sha256']=hashlib.sha256((stage/'p2-kochappy-bank.txt').read_bytes()).hexdigest()
    (output/'evidence.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('stage','exe','output'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();print(json.dumps(run(a.stage.resolve(),a.exe.resolve(),a.output.resolve()),indent=2))
