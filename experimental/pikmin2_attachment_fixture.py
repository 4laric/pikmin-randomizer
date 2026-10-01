"""Private native Snow mouth-prop and damage-volume demonstration (#358)."""
from pathlib import Path
from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial
from scripts.build_pikmin2_fixture import build_fixture

PROBE = r'''
#include "pc_p2_attachments.h"
#include "pc_p2_enemy.h"
#include "Interactions.h"
#include <fstream>
static bool attachmentFixture(Navi* n){
 static unsigned ticks=0;static Teki* enemy=nullptr;static Pellet* prop=nullptr;
 static p2attach::Instance instance;static p2attach::DamageVolume volume;
 static std::shared_ptr<const p2attach::Bank> bank;static p2attach::Token token=0;
 static p2attach::Affine frozen;static float frozenFrame=0;static Vector3f original;
 static p2attach::Vec first;static double moved=0;static int mouth=-1;
 if(!enemy){
  if(gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return true;
  Iterator it(tekiMgr);CI_LOOP(it){auto* e=static_cast<Teki*>(*it);if(pc_p2_enemy_name(e)){enemy=e;break;}}
  require(enemy,"missing Snow");std::ifstream file("attachments.txt");bank=p2attach::read(file);require(bool(bank),"attachment bank rejected");
  std::ifstream visual("p2-snow.txt");std::vector<p2animation::Clip> clips;require(p2animation::parse(visual,clips),"visual timing");
  require(clips.size()==bank->clips.size(),"clip count mismatch");
  for(const auto& c:clips){int index=bank->clip(c.name);require(index>=0,"missing attachment clip");const auto& b=bank->clips[index];require(b.frames==c.frames&&b.duration==c.duration,"visual/attachment timing mismatch");}
  token=instance.bind(bank);mouth=bank->joint("kamu");require(token&&mouth>=0,"mouth binding");
  prop=pc_p2_preview_treasure();require(prop,"missing attachment prop");original=prop->mSRT.t;
  prop->mSRT.s.set(.1f,.1f,.1f);n->mKontroller=new FixtureController();
  n->resetPosition(enemy->mSRT.t+Vector3f(70,0,70));
  for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
  std::puts("P2_ATTACHMENT_SETUP source_joint=kamu prop=native_treasure fixture_owned=1 radius_world=8");
 }
 const char* name=nullptr;float frame=0;require(pc_p2_snow_clock(enemy,name,frame),"authoritative clock");
 p2pose::Pose geometry;std::string drawnClip;float drawnFrame;bool corpse;
 if(!pc_p2_snow_geometry(enemy,geometry,drawnClip,drawnFrame,corpse))return true;
 // This engine advances animation after drawing. The sample committed at the
 // preceding idle boundary must match the geometry drawn by this idle call.
 static std::string expectedClip;static float expectedFrame=0;
 if(!expectedClip.empty())require(drawnClip==expectedClip&&std::fabs(drawnFrame-expectedFrame)<.001f,"committed attachment/render clock mismatch");
 expectedClip=name;expectedFrame=frame;
 p2attach::Affine owner;for(int r=0;r<3;++r)for(int c=0;c<4;++c)owner.m[r][c]=enemy->mWorldMtx.mMtx[r][c];
 ++ticks;const bool paused=ticks>100&&ticks<=130;
 require(instance.sample(token,bank->clip(name),frame,owner,ticks,paused),"joint evaluation");
 p2attach::Affine socket;require(instance.socket(token,mouth,socket),"mouth unavailable");
 const auto center=p2attach::point(socket,{0,0,0});
 if(ticks==1)first=center;
 moved=std::max(moved,double(std::fabs(center.x-first.x)+std::fabs(center.y-first.y)+std::fabs(center.z-first.z)));
 prop->mSRT.t.set(center.x,center.y,center.z);prop->mVelocity.set(0,0,0);prop->mTargetVelocity.set(0,0,0);
 require(std::fabs(prop->mSRT.t.x-center.x)<.0001f&&std::fabs(prop->mSRT.t.y-center.y)<.0001f&&std::fabs(prop->mSRT.t.z-center.z)<.0001f,"prop did not follow mouth");
 if(ticks==80)capture("attachment-moving.ppm");
 if(ticks==100){frozen=socket;frozenFrame=frame;gameflow.mPauseAll=true;}
 if(paused){
  require(std::fabs(frame-frozenFrame)<.001f,"native animation advanced while paused");
  for(int r=0;r<3;++r)for(int c=0;c<4;++c)require(socket.m[r][c]==frozen.m[r][c],"paused attachment moved");
  require(!volume.contact(instance,token,1,bank->clip(name),mouth,{0,0,0},8,0,10001,901,center),"paused volume damaged");
  if(ticks==130){gameflow.mPauseAll=false;std::puts("P2_ATTACHMENT_PAUSE_PASS ticks=30");}
 }
 if(ticks==160){
  require(moved>.01,"mouth did not animate");
  const int clip=bank->clip(name);n->resetPosition(Vector3f(center.x,center.y,center.z));
  const float before=n->mHealth;require(before>2,"captain health too low");
  require(!volume.contact(instance,token,1,clip,mouth,{0,0,0},8,0,10001,901,{center.x+100,center.y,center.z}),"outside target accepted");
  require(volume.contact(instance,token,1,clip,mouth,{0,0,0},8,0,10001,901,{n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z}),"inside target refused");
  require(n->stimulate(InteractAttack(enemy,nullptr,1,false)),"native receiver refused damage");
  require(std::fabs(n->mHealth-(before-1))<.001f,"native health delta");
  require(!volume.contact(instance,token,1,clip,mouth,{0,0,0},8,0,10001,901,center),"duplicate contact accepted");
  std::printf("P2_ATTACHMENT_NATIVE_DAMAGE before=%f after=%f duplicate=0 moved=%f\n",before,n->mHealth,moved);
  // Explicit owner-death signal releases the prop; natural Snow death is covered separately.
  require(instance.sample(token,clip,frame,owner,ticks+1,false,true),"death signal");
  require(!instance.socket(token,mouth,socket),"dead owner retained attachment");
  require(!volume.contact(instance,token,2,clip,mouth,{0,0,0},8,0,10001,901,center),"dead owner dealt damage");
  prop->mSRT.t=original;instance.reset();require(!instance.socket(token,mouth,socket),"reset retained handle");
  const auto fresh=instance.bind(bank);require(fresh!=token&&!instance.socket(token,mouth,socket),"stale generation accepted");
  std::puts("PASS animated attachments: moving native prop, shared draw clock, native pause, damage receiver, duplicate rejection, death release and stale generation");
  std::fflush(nullptr);std::_Exit(0);
 }
 return true;
}
'''


def build(native, build_dir, output, head):
    output.mkdir(parents=True, exist_ok=False)
    source = (native/'tools/preview_p2_room.cpp').read_text()
    at = source.index('class RoomApp : public PlugPikiApp {')
    source = source[:at] + PROBE + source[at:]
    anchor = 'Navi* n=naviMgr->getNavi();if(!n ||'
    if source.count(anchor) != 1:
        raise ValueError('Unexpected room fixture')
    source = source.replace(anchor, 'Navi* n=naviMgr->getNavi();if(n && attachmentFixture(n))return result;if(!n ||')
    (output/'tutorial-private.inc').write_text(instrument_tutorial((native/'src/plugPikiColin/newPikiGame.cpp').read_text()))
    (output/'room.cpp').write_text('#include "pc_p2_animation.h"\n'+source+'\n#include "tutorial-private.inc"\n')
    return build_fixture(build_dir, native, output/'room.cpp', output/'build', head)


def run(exe, assets, converted, pod, snow, bank, output):
    import hashlib, json, os, shutil, subprocess
    from experimental.pikmin2_snow_lifecycle import prepare
    provenance=json.loads(bank.with_suffix('.json').read_text())
    for key,path in (('bank_sha256',bank),('model_sha256',snow/'snow.bmd'),('timing_sha256',snow/'p2-snow.txt')):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=provenance[key]:
            raise ValueError('Attachment/visual source hash mismatch: '+key)
    visual_metadata=json.loads((snow/'snow.json').read_text())
    if provenance['source_animation_sha256']!={name:entry['sha256'] for name,entry in visual_metadata['motions'].items()}:
        raise ValueError('Attachment/visual animation hashes differ')
    output.mkdir(parents=True, exist_ok=False)
    stage=prepare(assets,converted,pod,snow,output/'stage')
    shutil.copyfile(bank,stage/'attachments.txt')
    (stage/'p2-snow-interpolation.txt').write_text('P2_SNOW_INTERPOLATION_1\n')
    expected=hashlib.sha256(exe.read_bytes()).hexdigest()
    env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''),SDL_AUDIODRIVER='dummy')
    with (stage/'native.log').open('w') as log:
        process=subprocess.Popen([str(exe),'--experimental-pikmin2-room'],cwd=stage,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            process.wait(timeout=90)
        except BaseException:
            process.kill();process.wait();raise
    text=(stage/'native.log').read_text(errors='replace')
    markers=('P2_ATTACHMENT_SETUP','P2_ATTACHMENT_PAUSE_PASS ticks=30','P2_ATTACHMENT_NATIVE_DAMAGE','PASS animated attachments:')
    passed=process.returncode==0 and all(m in text for m in markers) and hashlib.sha256(exe.read_bytes()).hexdigest()==expected
    result=dict(passed=passed,exit_code=process.returncode,exe_sha256=expected,stage=str(stage),
                bank_sha256=hashlib.sha256(bank.read_bytes()).hexdigest(),
                native_log_sha256=hashlib.sha256((stage/'native.log').read_bytes()).hexdigest())
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('build')
    for name in ('native','build-dir','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--head',required=True)
    p=commands.add_parser('run')
    for name in ('exe','assets','converted','pod','snow','bank','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    if a.command=='build':
        build(a.native.resolve(),a.build_dir.resolve(),a.output.resolve(),a.head)
    else:
        result=run(*(getattr(a,n).resolve() for n in ('exe','assets','converted','pod','snow','bank','output')))
        print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
