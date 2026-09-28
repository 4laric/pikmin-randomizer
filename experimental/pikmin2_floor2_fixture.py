"""Private native cargo-free/Violet regression; no shared native edits."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import struct
import re

from experimental.pikmin2_beasts_floor2 import prepare, decode_no_cargo
from scripts.build_pikmin2_fixture import build_fixture

HOOK = r'''
static void floorTwoFixture(Navi* n) {
    static int state=0,timer=0,thrown=0,repairs=0;
    static std::vector<Piki*> original;static Pom* flowers[2]={};
    ++timer;n->mNeutralTime=0;
    require(!pc_p2_preview_ready()&&!pc_p2_preview_treasure()&&pc_p2_preview_cargo_count()==0,"cargo-free treasure leak");
    require(pc_p2_preview_pokos()==0,"cargo-free reward leak");
    if(state==0&&timer>=90){
        for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
        repairs=playerState->getCurrParts();
        Iterator pellets(pelletMgr);CI_LOOP(pellets){Pellet* p=static_cast<Pellet*>(*pellets);require(p->mConfig->mModelId.mId!='pr05',"hidden pr05");}
        Iterator pikis(pikiMgr);CI_LOOP(pikis){Piki* p=static_cast<Piki*>(*pikis);if(p->isAlive())original.push_back(p);}
        Iterator bosses(bossMgr);CI_LOOP(bosses){Boss* b=static_cast<Boss*>(*bosses);if(!b->isAlive()||b->mObjType!=OBJTYPE_Pom)continue;
            require(b->mGenerator&&b->mGenerator->_70>=62000&&b->mGenerator->_70<=62001,"source flower identity");
            int i=b->mGenerator->_70-62000;require(!flowers[i],"duplicate source flower");flowers[i]=static_cast<Pom*>(b);
            float x=i?75:-55,z=i?-95:75;require(std::fabs(b->mSRT.t.x-x)<.1&&std::fabs(b->mSRT.t.z-z)<.1,"source flower relocated");
        }
        require(original.size()==20&&flowers[0]&&flowers[1]&&pc_p2_purples_enabled(),"cargo-free source population");
        phase=2;n->mKontroller=new FixtureController();state=1;timer=0;capture("floor2-start.ppm");
        std::puts("P2_FLOOR2_READY source_ids=62000,62001 flowers=2 cargo=0 pokos=0");
    }else if(state==1){
        if(thrown<10&&timer%20==0){Piki* p=original[thrown];p->changeMode(PikiMode::FreeMode,n);p->mFSM->transit(p,PIKISTATE_Flying);n->throwPiki(p,flowers[thrown/5]->mSRT.t);++thrown;}
        if(thrown==10&&timer>300&&timer%30==0){Pom* flower=nullptr;
            for(Pom* candidate:flowers)if(candidate->isAlive()&&(candidate->getCurrentState()==2||candidate->getCurrentState()==3)){flower=candidate;break;}
            if(flower)for(int i=0;i<10;++i){Piki* p=original[i];
                if(p->isAlive()&&!p->getStickObject()&&p->getState()==PIKISTATE_Normal){p->changeMode(PikiMode::FreeMode,n);p->mFSM->transit(p,PIKISTATE_Flying);n->throwPiki(p,flower->mSRT.t);break;}}}
        int sprouts=0,alive=0;Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){PikiHeadItem* h=static_cast<PikiHeadItem*>(*heads);if(h->isAlive()&&h->mP2Purple)++sprouts;}
        Iterator pikis(pikiMgr);CI_LOOP(pikis){if(static_cast<Piki*>(*pikis)->isAlive())++alive;}
        if(timer%150==0)std::printf("P2_FLOOR2_PROGRESS sprouts=%d alive=%d flower_states=%d,%d\n",sprouts,alive,flowers[0]->getCurrentState(),flowers[1]->getCurrentState());
        if(sprouts==10){require(alive==10&&playerState->getCurrParts()==repairs,"conversion population or repairs changed");
            require(!std::filesystem::exists("treasure-receipt.txt")&&!std::filesystem::exists("p2-economy.txt"),"cargo-free receipt file");
            capture("floor2-converted.ppm");std::puts("PASS floor2 cargo-free: source flowers2 converted10 sprouts, alive10, cargo0 pokos0 repairs unchanged; injected real throws");std::fflush(stdout);std::_Exit(0);}
        require(timer<1800,"floor2 native conversion timeout");
    }
    std::fflush(stdout);
}
'''


def instrument(source):
    anchor='class RoomApp : public PlugPikiApp {'
    guard='if(!pc_p2_preview_ready() || !naviMgr || !pikiMgr || !tekiMgr)return result;'
    call='        if(cargoCarryFixture(n))return result;'
    if any(source.count(s)!=1 for s in (anchor,guard,call)):raise ValueError('Fixture framing changed')
    return source.replace(anchor,'#include <filesystem>\n#include "Generator.h"\n'+HOOK+'\n'+anchor).replace(
        guard,'if(!pc_p2_preview_cargo_free_ready() || !naviMgr || !pikiMgr || !tekiMgr)return result;').replace(
        call,'        floorTwoFixture(n);return result;\n'+call)


def validate(log):
    if 'PASS floor2 cargo-free:' not in log or 'P2_ROOM_CARGO_FREE_READY cargo=0' not in log or 'P2_PURPLE_READY' not in log:
        raise ValueError('Incomplete cargo-free evidence')
    if 'P2_POD_RECEIPT' in log or 'P2_TREASURE_DELIVERED' in log:raise ValueError('Unexpected reward')
    return dict(flowers=2,sprouts=10,remaining_pikmin=10,cargo=0,pokos=0,manual_play=False)


def stage(args):
    run=prepare(args.assets,args.units,args.catalog,args.purple,args.output/'runs',pod=args.pod)
    model=(args.pod/'pod.mod').read_bytes()
    # Start the isolated throwing driver south of both flowers, facing inward.
    # Both flowers remain at their exact source transforms; no actor is teleported in play.
    gen=run/'assets/dataDir/stages/chal0/default.gen';raw=bytearray(gen.read_bytes())
    struct.pack_into('>4f',raw,4,0,0,250,180);gen.write_bytes(raw)
    ini=run/'assets/dataDir/stages/chal0.ini';ini.write_bytes(re.sub(rb'(?m)^navi_start[^\r\n]*',b'navi_start 0.0 250.0',ini.read_bytes()))
    decode_no_cargo((run/'assets/dataDir/stages/chal0/default.gen').read_bytes())
    (run/'fixture-input.json').write_text(json.dumps(dict(pod_sha256=hashlib.sha256(model).hexdigest(),unused_treasure_fields=True,
        captain_start=[0,0,250],captain_yaw=180,engineering_start=True,generator_sha256=hashlib.sha256(raw).hexdigest(),stage_sha256=hashlib.sha256(ini.read_bytes()).hexdigest()))+'\n')
    return run


def run_matrix(args):
    evidence={};env=dict(os.environ,PATH='C:/msys64/mingw64/bin'+os.pathsep+os.environ.get('PATH',''),SDL_AUDIODRIVER='dummy')
    for case in ('missing-opt-in','conflicting-config','success'):
        run=stage(args)
        if case=='missing-opt-in':(run/'p2-cargo-free.txt').unlink()
        if case=='conflicting-config':(run/'p2-cargo.txt').write_text('P2_CARGO_1\n0\n')
        with (run/'native.log').open('w') as out:
            result=subprocess.run([str(args.exe),'--experimental-pikmin2-room'],cwd=run,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=180)
        log=(run/'native.log').read_text(errors='replace')
        evidence[case]=dict(run=str(run),returncode=result.returncode,passed=False)
        (args.output/'partial-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
        if case=='success':
            if result.returncode:raise RuntimeError('Native success case failed: '+str(run))
            validate(log)
        else:
            expected='treasure generator missing' if case=='missing-opt-in' else 'cargo-free preview forbids cargo config'
            if not result.returncode or expected not in log:raise RuntimeError('Incorrect rejection: '+str(run))
        evidence[case]['passed']=True
        (args.output/'partial-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    (args.output/'acceptance.json').write_text(json.dumps(evidence,indent=2)+'\n')
    return evidence


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('build')
    for name in ('native','build','output'):b.add_argument('--'+name,type=Path,required=True)
    b.add_argument('--expected-head',required=True)
    r=sub.add_parser('run')
    for name in ('assets','units','catalog','purple','pod','output','exe'):r.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    for key,value in vars(args).items():
        if isinstance(value,Path):setattr(args,key,value.resolve())
    if args.command=='build':
        args.output.mkdir(parents=True,exist_ok=False);cpp=args.output/'floor2.cpp';cpp.write_text(instrument((args.native/'tools/preview_p2_room.cpp').read_text()))
        print(build_fixture(args.build,args.native,cpp,args.output/'linked',args.expected_head)['status'])
    else:print(json.dumps(run_matrix(args),indent=2))


if __name__=='__main__':main()
