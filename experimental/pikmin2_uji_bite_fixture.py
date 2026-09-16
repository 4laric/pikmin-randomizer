"""Male UjiB normal bite/eat stimulus; no direct motion or damage forcing."""
import argparse,hashlib,json,math,os,re,struct,subprocess
from experimental.pikmin2_collision import ground_height
from pathlib import Path
from experimental import pikmin2_uji_animation_fixture as visual
from experimental.pikmin2_uji_grounded_fixture import stage as base_stage
from experimental.pikmin2_uji_animation_install import install
from experimental.pikmin2_generator_pose import write_position
from scripts.preview_pikmin2_room import records

HOOK=r'''
#include "pc_p2_sheargrub.h"
#include "Pcam/Camera.h"
#include "Pcam/CameraManager.h"
static bool biteFixture(Navi* n){
 static int ticks=0,step=0,repairs=0;static Teki* male=nullptr;static Piki* prey=nullptr;static bool bitten=false,eaten=false,attached=false;
 require(++ticks<3600,"natural male bite/eat timeout");n->mNeutralTime=0;
 if(!step){Iterator enemies(tekiMgr);int count=0;CI_LOOP(enemies){auto* t=static_cast<Teki*>(*enemies);unsigned id;int value;if(pc_p2_sheargrub_receipt(t,id,value)){require(id==61000&&value==2,"male source identity");male=t;++count;}}require(count==1,"one source male required");
 Iterator pikis(pikiMgr);count=0;CI_LOOP(pikis){auto* p=static_cast<Piki*>(*pikis);if(p->isAlive()){prey=p;++count;}}require(count==1,"one natural prey required");repairs=playerState->getCurrParts();
 for(int slot=0;slot<10;++slot){Vector3f pos=pc_p2_preview_treasure()->getSlotGlobalPos(slot,0);float dx=pos.x-male->mSRT.t.x,dz=pos.z-male->mSRT.t.z;float distance=std::sqrt(dx*dx+dz*dz);require(distance<80,"bait slot outside source attack/perception range");std::printf("P2_UJI_BAIT_SLOT slot=%d xyz=%.2f,%.2f,%.2f distance=%.2f\n",slot,pos.x,pos.y,pos.z,distance);}
 prey->mActiveAction->abandon(nullptr);prey->mActiveAction->mCurrActionIdx=PikiAction::Transport;prey->mActiveAction->mChildActions[PikiAction::Transport].initialise(pc_p2_preview_treasure());prey->mMode=PikiMode::TransportMode;std::puts("P2_UJI_BAIT normal_transport_task=1");
 walkGoals.clear();for(float x:{200.f,425.f,595.f,820.f,1000.f})walkGoals.push_back(Vector3f(x,0,0));walkGoals.push_back(Vector3f(1000,0,-170));walkGoals.push_back(Vector3f(1000,0,0));walkGoals.push_back(Vector3f(200,0,0));secondFloor=true;walkPoint=0;phase=1;n->mKontroller=new FixtureController();step=1;capture("uji-bite-start.ppm");}
 require(cameraMgr&&cameraMgr->mCamera,"observer camera missing");cameraMgr->mCamera->setTarget(male);
 static bool biteCapture=false,eatCapture=false;
 if(male->mStateID==6&&!biteCapture){capture("uji-natural-bite.ppm");biteCapture=true;}
 if(male->mStateID==7&&!eatCapture){capture("uji-natural-eat.ppm");eatCapture=true;}
 if(ticks%150==0){auto* c=n->mNaviCamera;std::printf("P2_UJI_OBSERVER camera=%.2f,%.2f,%.2f focus=%.2f,%.2f,%.2f fov=%.2f target_visible=%d\n",c->mPosition.x,c->mPosition.y,c->mPosition.z,c->mFocus.x,c->mFocus.y,c->mFocus.z,c->mFov,int(c->isPointVisible(male->mSRT.t,20)));}
 bitten=bitten||male->mStateID==6;eaten=eaten||male->mStateID==7;attached=attached||male->getCreaturePointer(2)==prey;
 if(ticks%150==0)std::printf("P2_UJI_BITE_TRACE state=%d motion=%d prey_alive=%d mouth=%d captain=%.1f,%.1f prey=%.1f,%.1f\n",male->mStateID,male->mTekiAnimator->getCurrentMotionIndex(),int(prey->isAlive()),int(male->getCreaturePointer(2)==prey),n->mSRT.t.x,n->mSRT.t.z,prey->mSRT.t.x,prey->mSRT.t.z);
 if(bitten&&eaten&&attached&&!prey->isAlive()){require(pc_p2_preview_pokos()==0&&playerState->getCurrParts()==repairs,"bite economy changed");capture("uji-bite-complete.ppm");std::puts("PASS Uji natural bite/eat: bite_state6 eat_state7 mouth_attachment1 prey_dead1 pokos0 repairs_unchanged");std::fflush(stdout);std::_Exit(0);}
 std::fflush(stdout);return true;
}
'''


def instrument(source):
 anchor='class RoomApp : public PlugPikiApp {';call='        if(cargoCarryFixture(n))return result;'
 if source.count(anchor)!=1 or source.count(call)!=1:raise ValueError('Room fixture anchors changed')
 return source.replace(anchor,HOOK+'\n'+anchor).replace(call,'        if(biteFixture(n))return result;\n'+call)


def stage(args):
 terrain=json.loads((args.assembly/'collision.json').read_text());slots=[]
 for i in range(10):
  x=1055+20*math.sin(2*math.pi*i/10);z=-120+20*math.cos(2*math.pi*i/10);y=ground_height(terrain['vertices'],terrain['triangles'],x,z)
  if y is None or abs(y)>.1:raise ValueError('Bait carry slot has no verified ground')
  slots.append([x,y,z])
 for x,z in ((1055,-120),(1055,-100)):
  y=ground_height(terrain['vertices'],terrain['triangles'],x,z)
  if y is None or abs(y)>.1:raise ValueError('Bait center/prey lacks verified ground')
 run=base_stage(args);path=run/'assets/dataDir/stages/chal0/default.gen';raw=path.read_bytes();kept=[];prey=False
 for row in records(path):
  identity=struct.unpack_from('<I',row,8)[0]
  if 61001<=identity<=61009:continue
  if row[72:76]==b'ikip':
   if prey:continue
   prey=True;row=bytearray(row);write_position(row,(1055,0,-100));row=bytes(row)
  if row[72:76]==b'tlep':
   row=bytearray(row);write_position(row,(1055,0,-120));row=bytes(row)
  kept.append(row)
 if not prey:raise ValueError('Prey template missing')
 header=bytearray(raw[:24]);struct.pack_into('>I',header,20,len(kept));path.write_bytes(header+b''.join(kept))
 (run/'p2-sheargrub.txt').write_bytes(b'P2_SHEARGRUB_1\n1\n61000 UjiB 2\n')
 (run/'bite-stimulus.json').write_text(json.dumps(dict(engineered_subset=True,generator_before_sha256=hashlib.sha256(raw).hexdigest(),generator_after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),male_source_generator=61000,prey_position=[1055,0,-100],cargo_position=[1055,0,-120],predicted_carry_slots=slots,slot_radius_observed=20,source_visible_range=150,source_attack_range=80,injected_task="normal Transport toward heavy cargo",female_bridge='unsupported: no WorkObject bridge',direct_motion_forcing=False,observer_camera="PcamCamera setTarget source male; default FOV/motion; captain route unchanged"),indent=2)+'\n')
 return run


def validate(log,animated):
 if 'PASS Uji natural bite/eat:' not in log:raise ValueError('Native bite/eat incomplete')
 rows=re.findall(r'P2_UJI_VISUAL species=UjiB corpse=0 clip=(\w+) pose=(\d+)',log)
 if animated:
  for clip in ('attack2','eat'):
   if len({p for c,p in rows if c==clip})<2:raise ValueError('Missing changing '+clip+' visual')
 elif not rows or any(c!='static' for c,_ in rows):raise ValueError('Static fallback missing')
 return dict(animated=animated,natural_bite=True,natural_eat=True,mouth_attachment=True,prey_dead=True,pokos=0,female_bridge=False)


def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 b=sub.add_parser('build')
 for n in ('native','build-dir','output'):b.add_argument('--'+n,type=Path,required=True)
 b.add_argument('--head',required=True)
 r=sub.add_parser('run')
 for n in ('assets','assembly','pod','content','uji','output','exe','bank'):r.add_argument('--'+n,type=Path,required=True)
 r.add_argument('--case',choices=('both','static','animated'),default='both')
 a=p.parse_args()
 if a.command=='build':visual.room_instrument=instrument;visual.build(a.native,a.build_dir,a.output,a.head);return
 failures=[]
 for animated in ((False,True) if a.case=='both' else (a.case=='animated',)):
  run=stage(a);print(run,flush=True)
  if animated:install(a.bank,run)
  env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''),SDL_AUDIODRIVER='dummy')
  with (run/'native.log').open('w') as log:res=subprocess.run([str(a.exe.resolve()),'--experimental-pikmin2-room'],cwd=run,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
  if res.returncode:
   failures.append(str(run));(run/'bite-diagnostic.json').write_text(json.dumps(dict(accepted=False,animated=animated,returncode=res.returncode),indent=2)+'\n');continue
  log_text=(run/'native.log').read_text()
  try:evidence=validate(log_text,animated)
  except ValueError as error:
   failures.append(str(run));(run/'bite-diagnostic.json').write_text(json.dumps(dict(accepted=False,animated=animated,native_behavior_pass='PASS Uji natural bite/eat:' in log_text,visual_error=str(error)),indent=2)+'\n');continue
  (run/'bite-acceptance.json').write_text(json.dumps(evidence,indent=2)+'\n');print(evidence,flush=True)

 if failures:raise RuntimeError('Natural bite gates failed: '+', '.join(failures))

if __name__=='__main__':main()
