"""Corrected-position Uji emergence, legal damage and native corpse haul fixture."""
import argparse
import hashlib
import struct
import json
import os
from pathlib import Path
import re
import subprocess
from experimental.pikmin2_beasts_uji import prepare
from scripts.build_pikmin2_fixture import build_fixture
from scripts.preview_pikmin2_room import records

HOOK=r'''
#include "pc_p2_sheargrub.h"
#include "Interactions.h"
#include "Generator.h"
#include "TekiPersonality.h"
static bool ujiGroundedFixture(Navi* n){
 static int ticks=0,step=0,repairs=0;static Teki* bugs[10]={};static Pellet* bodies[10]={};static bool hit[10]={},crossed[10]={};
 require(++ticks<10000,"grounded Uji timeout");n->mNeutralTime=0;
 if(step==0){
  Iterator it(tekiMgr);int count=0;CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);unsigned id;int value;if(!pc_p2_sheargrub_receipt(t,id,value))continue;require(id>=61000&&id<61010,"unknown grounded Uji ID");int i=id-61000;require(!bugs[i]&&value==(i<4?2:1),"source Uji mapping");bugs[i]=t;++count;}
  require(count==10,"ten source actors required");repairs=playerState->getCurrParts();require(pc_p2_preview_pokos()==0,"dirty Uji economy");
  std::ifstream poses("uji-positions.txt");std::string header;int size;require(bool(poses>>header>>size)&&header=="P2_UJI_POSES_1"&&size==10,"pose framing");
  walkGoals.clear();for(float x:{200.f,425.f,595.f,820.f,1020.f})walkGoals.push_back(Vector3f(x,0,0));
  bool xyzValid=true;
  for(int i=0;i<10;++i){int id;float x,y,z;require(bool(poses>>id>>x>>y>>z)&&id==61000+i,"pose identity");auto* t=bugs[i];
   Vector3f generated=t->mGenerator->getPos();Vector3f born=t->mPersonality->mPosition;
   std::printf("P2_UJI_BIRTH id=%d xyz=%.2f,%.2f,%.2f physics_drift=%.3f,%.3f,%.3f\n",id,born.x,born.y,born.z,t->mSRT.t.x-born.x,t->mSRT.t.y-born.y,t->mSRT.t.z-born.z);
   std::printf("P2_UJI_GROUNDED id=%d xyz=%.2f,%.2f,%.2f expected=%.2f,%.2f,%.2f generator=%.2f,%.2f,%.2f state=%d\n",id,t->mSRT.t.x,t->mSRT.t.y,t->mSRT.t.z,x,y,z,generated.x,generated.y,generated.z,t->mStateID);
   xyzValid=xyzValid&&(std::fabs(born.x-x)<.1&&std::fabs(born.y-y)<.1&&std::fabs(born.z-z)<.1&&std::fabs(generated.x-x)<.1&&std::fabs(generated.y-y)<.1&&std::fabs(generated.z-z)<.1);
   walkGoals.push_back(Vector3f(1020,0,0));walkGoals.push_back(Vector3f(x,0,z));
  }
  require(!(poses>>header),"trailing poses");require(xyzValid,"native birth XYZ mismatch");
  for(auto* t:bugs){float health=t->mHealth;require(t->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE),"initial actor not buried");require(!t->stimulate(InteractAttack(n,nullptr,10000,false))&&t->mHealth==health&&t->mStoredDamage==0,"buried attack accepted");}
  walkGoals.push_back(Vector3f(1020,0,0));secondFloor=true;walkPoint=0;phase=1;n->mKontroller=new FixtureController();capture("uji-grounded-start.ppm");step=1;ticks=0;
 }else if(step==1){
  for(int i=0;i<10;++i)if(!hit[i]&&!bugs[i]->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE)){require(bugs[i]->stimulate(InteractAttack(n,nullptr,10000,false)),"legal attack rejected");hit[i]=true;std::printf("P2_UJI_GROUNDED_HIT id=%d state=%d\n",61000+i,bugs[i]->mStateID);}
  Iterator pellets(pelletMgr);CI_LOOP(pellets){Pellet* p=static_cast<Pellet*>(*pellets);if(!p->isAlive())continue;for(int i=0;i<10;++i)if(p->mPelletView==static_cast<PelletView*>(bugs[i]))bodies[i]=p;}
  int hits=0,found=0;for(int i=0;i<10;++i){hits+=hit[i];found+=bodies[i]!=nullptr;}
  if(ticks%300==0)std::printf("P2_UJI_GROUNDED_PROGRESS hits=%d corpses=%d captain=%.1f,%.1f waypoint=%d\n",hits,found,n->mSRT.t.x,n->mSRT.t.z,walkPoint);
  if(hits==10&&found==10){phase=2;capture("uji-grounded-corpses.ppm");int index=0;Iterator pikis(pikiMgr);CI_LOOP(pikis){Piki* p=static_cast<Piki*>(*pikis);if(!p->isAlive())continue;p->mActiveAction->abandon(nullptr);p->mActiveAction->mCurrActionIdx=PikiAction::Transport;p->mActiveAction->mChildActions[PikiAction::Transport].initialise(bodies[index++%10]);p->mMode=PikiMode::TransportMode;}require(index>=20,"twenty carriers required");step=2;ticks=0;std::puts("P2_UJI_GROUNDED_CORPSES count=10 native_death=1 transport_assigned=1");}
 }else if(step==2){
  for(int i=0;i<10;++i)if(!crossed[i]&&bodies[i]->isAlive()&&bodies[i]->mSRT.t.x<425){crossed[i]=true;std::printf("P2_UJI_GROUNDED_CROSS id=%d\n",61000+i);}
  int value=pc_p2_preview_pokos();if(value==14||value==114){for(bool c:crossed)require(c,"corpse connector crossing missing");require(playerState->getCurrParts()==repairs,"Uji repairs changed");require(value==(pc_p2_preview_treasure()->isAlive()?14:114),"separate cargo100 accounting");capture("uji-grounded-delivered.ppm");std::puts("PASS grounded Uji: XYZ10 buried_reject10 legal_hits10 native_corpses10 connector10 corpse_pokos14 repairs_unchanged");std::fflush(stdout);std::_Exit(0);}
  if(ticks%600==0)std::printf("P2_UJI_GROUNDED_HAUL pokos=%d\n",value);
 }
 std::fflush(stdout);return true;
}
'''


def instrument(source):
    anchor='class RoomApp : public PlugPikiApp {';call='        if(cargoCarryFixture(n))return result;'
    if source.count(anchor)!=1 or source.count(call)!=1:raise ValueError('Fixture framing changed')
    return source.replace(anchor,'#include <fstream>\n'+HOOK+'\n'+anchor).replace(call,'        if(ujiGroundedFixture(n))return result;\n'+call)


def validate(log):
    expected={str(i):2 if i<61004 else 1 for i in range(61000,61010)}
    if 'PASS grounded Uji:' not in log:raise ValueError('Incomplete grounded acceptance')
    for marker in ('P2_UJI_BIRTH id=','P2_UJI_GROUNDED id=','P2_UJI_GROUNDED_HIT id=','P2_UJI_GROUNDED_CROSS id='):
        if set(re.findall(re.escape(marker)+r'(\d+)',log))!=set(expected):raise ValueError('Incomplete source identities')
    rows=re.findall(r'P2_POD_RECEIPT id=corpse:[^ ]*uji:(\d+) value=([12]) new=1',log)
    if len(rows)!=10 or {i:int(v) for i,v in rows}!=expected:raise ValueError('Incorrect source corpse credits')
    return dict(native_xyz=10,legal_hits=10,native_corpses=10,connector_crossings=10,corpse_pokos=14,manual_combat=False)


def deterministic_births(path, selected):
    """Private fixture override; preserve every byte except validated radius fields."""
    before=path.read_bytes(); entries=records(path); seen=set(); changed=[]
    block=b'cric0.0v'+bytes(12)+b'p00\x04'+struct.pack('>f',50)+b'\xff'*4
    after=bytearray(before); cursor=24
    for row in entries:
        identity=struct.unpack_from('<I',row,8)[0]
        if identity in selected:
            if identity in seen or row.count(b'cric0.0v')!=1 or row.count(block)!=1:
                raise ValueError('Unexpected fixture circle framing')
            seen.add(identity); offset=cursor+row.index(block)+24
            after[offset:offset+4]=struct.pack('>f',0)
            changed.extend(range(offset,offset+4))
        cursor+=len(row)
    if seen!=set(selected):raise ValueError('Missing fixture actor')
    if any(a!=b and i not in changed for i,(a,b) in enumerate(zip(before,after))):
        raise ValueError('Unexpected fixture mutation')
    report=dict(policy='PRIVATE_CIRCLE_RADIUS_ZERO_1',engineered_choice=True,
        generator_ids=sorted(seen),original_radius=50,fixture_radius=0,
        before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(after).hexdigest())
    path.write_bytes(after)
    return report


def stage(args):
    run=prepare(args.assets,args.assembly,args.pod,args.content,args.uji,args.output/'runs')
    actors=json.loads((run/'beasts-uji-roster.json').read_text())['actors']
    override=deterministic_births(run/'assets/dataDir/stages/chal0/default.gen',{a['generator'] for a in actors})
    (run/'fixture-radius-override.json').write_text(json.dumps(override,indent=2)+'\n')
    (run/'uji-positions.txt').write_text('P2_UJI_POSES_1\n10\n'+''.join(str(a['generator'])+' '+' '.join(map(str,a['position']))+'\n' for a in actors))
    return run


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    b=s.add_parser('build')
    for n in ('native','build','output'):b.add_argument('--'+n,type=Path,required=True)
    b.add_argument('--expected-head',required=True)
    r=s.add_parser('run')
    for n in ('assets','assembly','pod','content','uji','output','exe'):r.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    for n,v in vars(a).items():
        if isinstance(v,Path):setattr(a,n,v.resolve())
    if a.command=='build':
        a.output.mkdir(parents=True,exist_ok=False);cpp=a.output/'grounded.cpp';cpp.write_text(instrument((a.native/'tools/preview_p2_room.cpp').read_text()))
        print(build_fixture(a.build,a.native,cpp,a.output/'linked',a.expected_head)['status'])
    else:
        run=stage(a);print(run,flush=True);env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''),SDL_AUDIODRIVER='dummy')
        with (run/'native.log').open('w') as log:result=subprocess.run([str(a.exe),'--experimental-pikmin2-room'],cwd=run,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=420)
        if result.returncode:raise RuntimeError('Native fixture failed: '+str(run))
        evidence=validate((run/'native.log').read_text());(run/'acceptance.json').write_text(json.dumps(evidence,indent=2)+'\n');print(evidence)


if __name__=='__main__':main()
