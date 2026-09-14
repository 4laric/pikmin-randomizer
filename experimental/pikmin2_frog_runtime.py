"""Private Frog arena runtime probe. Injected lethal attacks are explicitly labelled."""
import argparse,json,os,re,subprocess
from pathlib import Path
from scripts import build_pikmin2_fixture as builder
from experimental.pikmin2_frog_arena import prepare
from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial

APP=r'''class RoomApp : public PlugPikiApp {
 int observed=0,frames=0;Teki* frogs[4]={};bool hit[2]={};
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<15000,"frog startup timeout");
 if(frames%120==0){std::printf("P2_FROG_GATE frame=%d ready=%d pause=%d ui=%d movie=%d\n",frames,int(pc_p2_preview_cargo_free_ready()),int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),int(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive));std::fflush(stdout);}
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 ++observed;
 if(observed==1){
 for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
 std::ifstream input("frog-positions.txt");unsigned id;int type,registered;float x,y,z;int count=0;
 while(input>>id>>type>>registered>>x>>y>>z){
 Teki* actor=nullptr;int matches=0;Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70==id){actor=a;++matches;}}
 require(matches==1&&actor->mTekiType==type&&id>=201001&&id<=201004,"frog type/identity");
 Vector3f birth=actor->mPersonality->mPosition,gen=actor->mGenerator->getPos();
 require(std::fabs(birth.x-x)<.02&&std::fabs(birth.y-y)<.02&&std::fabs(birth.z-z)<.02,"frog birth XYZ");
 require(std::fabs(gen.x-x)<.02&&std::fabs(gen.y-y)<.02&&std::fabs(gen.z-z)<.02,"frog generator XYZ");
 require(bool(pc_p2_frog_name(actor))==bool(registered),"frog registration/control");
 float raw_health=actor->mTekiParams->getF(TPF_Life),want_health=registered?pc_p2_frog_param_f(actor,TPF_Life,raw_health):raw_health;
 require(actor->getParameterF(TPF_Life)==want_health,"frog health mismatch (source for registered, P1 for controls)");
 frogs[id-201001]=actor;++count;
 std::printf("P2_FROG_BIRTH id=%u type=%d registered=%d x=%.3f y=%.3f z=%.3f\n",id,type,registered,birth.x,birth.y,birth.z);}
 require(count==4,"frog roster missing");require(cameraMgr&&cameraMgr->mCamera,"frog camera missing");cameraMgr->mCamera->setTarget(frogs[0]);
 }
 if(observed==80){
  const bool want[4]={true,true,false,false};int before=0;
  for(int i=0;i<4;++i)if(bool(pc_p2_frog_name(static_cast<PelletView*>(frogs[i])))==want[i])++before;
  require(before==4,"pre-cleanup registration");
  pc_p2_frog_reset();
  int cleared=0;for(int i=0;i<4;++i)if(!pc_p2_frog_name(static_cast<PelletView*>(frogs[i])))++cleared;
  require(cleared==4,"stale registration rejected after reset");
  pc_p2_frog_setup();
  int reentry=0;for(int i=0;i<4;++i)if(bool(pc_p2_frog_name(static_cast<PelletView*>(frogs[i])))==want[i])++reentry;
  require(reentry==4,"re-entry registration rebuilt");
  std::printf("P2_FROG_CLEANUP registered_before=%d cleared=%d reentry=%d\n",before,cleared,reentry);std::fflush(stdout);}
 if(observed==180)cameraMgr->mCamera->setTarget(frogs[1]);
 if(observed==120)capture("frog-live.ppm");if(observed==300)capture("marofrog-live.ppm");
 for(int i=0;i<4;++i){auto* a=frogs[i];if(observed<=360)require(a->isAlive(),"frog unexpectedly died before attack");
 if(observed%15==0&&observed<=360){auto p=a->getPosition();std::printf("P2_FROG_TICK id=%d motion=%d counter=%.4f x=%.4f y=%.4f z=%.4f\n",201001+i,a->mTekiAnimator->getCurrentMotionIndex(),a->mTekiAnimator->getCounter(),p.x,p.y,p.z);}}
 if(observed>=360){for(int i=0;i<2;++i)if(!hit[i]&&frogs[i]->isAlive()&&!frogs[i]->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE)){
 hit[i]=frogs[i]->stimulate(InteractAttack(n,nullptr,10000,false));std::printf("P2_FROG_INJECTED_ATTACK id=%d accepted=%d\n",201001+i,int(hit[i]));}}
 if(observed==450)cameraMgr->mCamera->setTarget(frogs[0]);
 if(observed==570)capture("frog-corpse.ppm");
 if(observed==600)cameraMgr->mCamera->setTarget(frogs[1]);
 if(observed==720){capture("marofrog-corpse.ppm");require(hit[0]&&hit[1],"frog legal attacks not accepted");int bodies=0;
 Iterator p(pelletMgr);CI_LOOP(p){Pellet* body=static_cast<Pellet*>(*p);if(body->isAlive()&&(body->mPelletView==static_cast<PelletView*>(frogs[0])||body->mPelletView==static_cast<PelletView*>(frogs[1])))++bodies;}
 require(bodies==2,"frog native corpses missing");require(frogs[2]->isAlive()&&frogs[3]->isAlive(),"P1 controls died");std::puts("PASS P2_FROG_RUNTIME birth4 controls2 corpses2 injected_attack=1");std::fflush(stdout);std::_Exit(0);}
 std::fflush(stdout);return result;
 }};
'''

def instrument(source):
 start=source.index('class RoomApp : public PlugPikiApp {');end=source.index('int main(',start)
 return '#include <fstream>\n#include "Generator.h"\n#include "TekiPersonality.h"\n#include "Interactions.h"\n#include "pc_p2_frog.h"\n#include "Pcam/Camera.h"\n#include "Pcam/CameraManager.h"\n'+source[:start]+APP+source[end:]


def instrument_family(source):
 anchor='shape->updateAnim(gfx,matrix,nullptr,actor);'
 if source.count(anchor)!=1:raise ValueError('Frog draw anchor changed')
 return source.replace(anchor,'''static std::set<std::string> seen;int pose=0;if(name){int count=actor->mTekiAnimator->getFrameCount();pose=int(timing[kind].at(name).index(count>1?actor->mTekiAnimator->getCounter()/(count-1):0,corpse));}
 std::string key=std::to_string(kind)+":"+std::to_string(int(corpse))+":"+(name?name:"static")+":"+std::to_string(pose);
 if(seen.insert(key).second)std::printf("P2_FROG_DRAW species=%s corpse=%d clip=%s pose=%d\\n",ids[kind],int(corpse),name?name:"static",pose);
 '''+anchor)

def build(native,build_dir,output,head,resume=False):
    native=native.resolve();build_dir=build_dir.resolve();output=output.resolve()
    room=output/'room.cpp';source=instrument((native/'tools/preview_p2_room.cpp').read_text())
    if resume:
        if (output/'instrumentation.json').exists() or room.read_text()!=source:raise ValueError('Cannot resume completed or changed fixture')
        record=json.loads((output/'baseline/provenance.json').read_text())
        if record.get('status')!='built' or record.get('expected_native_head')!=head or builder.git_state(native)!=record['observed_source']:raise ValueError('Baseline no longer matches source')
        for key in ('inputs','fixture_inputs','configuration_inputs'):builder.check_snapshot(record[key])
    else:
        output.mkdir(parents=True,exist_ok=False);room.write_text(source)
        record=builder.build_fixture(build_dir,native,room,output/'baseline',head)
    family=native/'pc_port/pc_p2_frog.cpp';private=output/'family.cpp';private.write_text(instrument_family(family.read_text()))
    compile=list(record['commands'][-2]);compile=[str(private) if a==str(room) else a for a in compile]
    compile[builder.option_index(compile,'-o')]=str(output/'family.obj')
    compile[builder.option_index(compile,'-MF')]=str(output/'family.d')
    link=list(record['commands'][-1]);targets=[i for i,a in enumerate(link) if a.endswith('-pc_p2_frog.cpp.obj')]
    if len(targets)!=1:raise ValueError('Expected one private family object')
    link[targets[0]]=str(output/'family.obj');link[builder.option_index(link,'-o')]=str(output/'fixture.exe')
    link=[('-Wl,--out-implib,'+str(output/'fixture.dll.a')) if a.startswith('-Wl,--out-implib,') else a for a in link]
    tutorial=native/'src/plugPikiColin/newPikiGame.cpp';tutorial_private=output/'tutorial.cpp';tutorial_private.write_text(instrument_tutorial(tutorial.read_text()))
    tutorial_compile=[str(tutorial_private) if a==str(private) else a for a in compile]
    tutorial_compile[builder.option_index(tutorial_compile,'-o')]=str(output/'tutorial.obj');tutorial_compile[builder.option_index(tutorial_compile,'-MF')]=str(output/'tutorial.d')
    targets=[i for i,a in enumerate(link) if a.endswith('-libpikmin_legacy.a')]
    if len(targets)!=1:raise ValueError('Expected one private legacy archive')
    # The original tutorial translation unit lives in the archive. Supplying its
    # complete replacement first prevents the linker extracting that member.
    link.insert(targets[0],str(output/'tutorial.obj'))
    env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''))
    audit=dict(original_family=builder.snapshot([family,tutorial]),instrumented=builder.snapshot([private,tutorial_private]),commands=[compile,tutorial_compile,link],freshness_checks=[])
    for name,command in [('family-compile',compile),('tutorial-compile',tutorial_compile),('family-link',link)]:
        code,text=builder.run(command,build_dir,env);(output/(name+'.log')).write_text(text)
        if code:raise RuntimeError(name+' failed')
    builder.require_fresh(Path(record['toolchain']['ninja']['path']),build_dir,audit['freshness_checks'])
    builder.check_snapshot(record['inputs']);builder.check_snapshot(record['fixture_inputs']);builder.check_snapshot(record['configuration_inputs']);builder.check_snapshot(audit['original_family']);builder.check_snapshot(audit['instrumented'])
    if builder.git_state(native)!=record['observed_source']:raise RuntimeError('Native changed during private replacement')
    audit['artifacts']=builder.snapshot([output/'fixture.exe',output/'family.obj']);audit['status']='built'
    (output/'instrumentation.json').write_text(json.dumps(audit,indent=2)+'\n')



def validate(text,code):
 births=re.findall(r'P2_FROG_BIRTH id=(\d+) type=(\d+) registered=(\d+)',text)
 draws=re.findall(r'P2_FROG_DRAW species=(Frog|MaroFrog) corpse=([01]) clip=(\w+) pose=(\d+)',text)
 natural=re.findall(r'P2_FROG_DRAW species=(Frog|MaroFrog) corpse=([01]) clip=(\w+) pose=(\d+)',text.split('P2_FROG_INJECTED_ATTACK')[0])
 checks=dict(completion=code==0 and 'PASS P2_FROG_RUNTIME ' in text,births=births==[('201001','0','1'),('201002','33','1'),('201003','0','0'),('201004','33','0')],cleanup_reentry='P2_FROG_CLEANUP registered_before=4 cleared=4 reentry=4' in text)
 for species in ('Frog','MaroFrog'):
  own=[d for d in draws if d[0]==species];checks[species+'_live']=any(d[1]=='0' for d in own);checks[species+'_corpse']=any(d[1]=='1' and d[2]=='dead' for d in own);checks[species+'_poses']=len({(d[2],d[3]) for d in natural if d[0]==species and d[1]=='0'})>=2
 return dict(passed=all(checks.values()),checks=checks,draws=draws,unmeasured=['natural combat','transport/rewards','full scene/day reload (manager reset/re-entry covered by cleanup_reentry)','P2 mechanics'])


def run(assets,bank,output,exe):
 stage=prepare(assets,bank,output/'stages');manifest=json.loads((stage/'frog-arena.json').read_text())
 (stage/'frog-positions.txt').write_bytes(''.join(f"{a['generator']} {a['native_type']} {int(i<2)} "+' '.join(map(str,a['position']))+'\n' for i,a in enumerate(manifest['actors'])).encode())
 env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''),SDL_AUDIODRIVER='dummy')
 with (stage/'native.log').open('w') as log:
  try:code=subprocess.run([str(exe.resolve()),'--experimental-pikmin2-room'],cwd=stage,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180).returncode
  except subprocess.TimeoutExpired:code='timeout'
 evidence=validate((stage/'native.log').read_text(errors='replace'),code)
 evidence.update(exit_code=code,executable=builder.snapshot([exe]),arena=builder.snapshot([stage/'frog-arena.json',stage/'frog-positions.txt',stage/'p2-frog.txt']))
 (stage/'runtime-evidence.json').write_text(json.dumps(evidence,indent=2));print(stage,flush=True);print(json.dumps(evidence),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True);b=sub.add_parser('build');r=sub.add_parser('run')
 for n in ('native','build-dir','output'):b.add_argument('--'+n,type=Path,required=True)
 b.add_argument('--head',required=True)
 b.add_argument('--resume',action='store_true')
 for n in ('assets','bank','output','exe'):r.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args()
 if a.command=='build':build(a.native,a.build_dir,a.output,a.head,a.resume)
 else:run(a.assets,a.bank,a.output,a.exe)
