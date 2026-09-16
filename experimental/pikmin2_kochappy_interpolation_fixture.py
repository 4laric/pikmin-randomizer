"""Hidden real-bank Dwarf Red interpolation acceptance, staged without prior saves."""
from pathlib import Path
import shutil
import struct
from scripts.preview_pikmin2_room import overlay, records
from scripts.build_pikmin2_fixture import build_fixture
from experimental.pikmin2_crossfade_fixture import run

APP=r'''
class CrossfadeApp final:public PlugPikiApp {
 int frames=0,ready=0;
public:
 int idle()override{
  int result=PlugPikiApp::idle();require(++frames<1200,"startup timeout");
  if(playerState)for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(pc_p2_preview_ready()&&naviMgr&&naviMgr->getNavi()&&!gameflow.mPauseAll&&!gameflow.mIsUIOverlayActive)++ready;return result;
 }
 void draw(Graphics& gfx)override{
  PlugPikiApp::draw(gfx);if(ready<120)return;
  std::vector<BTeki*> actors;Iterator enemies(tekiMgr);CI_LOOP(enemies){auto* t=static_cast<Teki*>(*enemies);if(pc_p2_kochappy_name(t))actors.push_back(t);}
  require(actors.size()==2&&gfx.mCamera,"two registered actors");
  std::ifstream manifest("p2-kochappy-bank.txt");std::vector<p2animation::Clip> clips;require(p2kochappy::bank(manifest,clips),"bank");
  std::map<std::string,std::vector<p2pose::Baked>> bank;
  for(const auto& c:clips)for(int i=0;i<c.count;++i){char path[160];std::snprintf(path,sizeof(path),"assets/dataDir/courses/pikmin2room/kochappy_%s_%02d.mod",c.name.c_str(),i);
   std::ifstream file(path,std::ios::binary);std::vector<unsigned char> raw((std::istreambuf_iterator<char>(file)),{});p2pose::Baked pose;require(p2pose::decodeBaked(raw,pose),"decode");bank[c.name].push_back(std::move(pose));}
  gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx,gfx.mCamera->mFov,gfx.mCamera->mAspectRatio,gfx.mCamera->mNear,gfx.mCamera->mFar,1.f);gfx.setDepth(true);gfx.useMaterial(nullptr);
  Matrix4f world,view;world.makeSRT(Vector3f(3,3,3),Vector3f(0,0,0),naviMgr->getNavi()->mSRT.t);gfx.mCamera->mLookAtMtx.multiplyTo(world,view);
  auto render=[&](BTeki* actor,const char* name,float sourceFrame,const char* path,bool corpse=false){
   int motion=std::string(name)=="dead"?TekiMotion::Dead:std::string(name)=="attack"?TekiMotion::Attack:std::string(name)=="move1"?TekiMotion::Move1:std::string(name)=="flick"?TekiMotion::Flick:TekiMotion::Wait1;
   const p2animation::Clip* clip=nullptr;for(const auto& c:clips)if(c.name==name)clip=&c;require(clip,"clip");
   actor->startMotion(motion);actor->mTekiAnimator->setCounter(sourceFrame/(clip->duration-1)*(actor->mTekiAnimator->getFrameCount()-1));
   pc_gfx_flush_batch();glClearColor(0,0,0,1);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);require(pc_p2_kochappy_draw(actor,gfx,view,corpse),"draw");auto pixels=capture(path);
   p2pose::Pose actual;std::string label;float frame;bool carried;require(pc_p2_kochappy_geometry(actor,actual,label,frame,carried),"geometry");require(label==name&&carried==corpse,"clock identity");
   p2pose::Interval span;require(p2pose::bracket(clip->frames,frame,span),"bracket");const auto& a=bank[name][span.left].pose;const auto& b=bank[name][span.right].pose;
   require(a.positions.size()==actual.positions.size()&&a.normals.size()==actual.normals.size(),"counts");
   for(size_t i=0;i<a.positions.size();++i){auto want=p2pose::mix(a.positions[i],b.positions[i],span.weight),got=actual.positions[i];require(std::fabs(want.x-got.x)<.0001f&&std::fabs(want.y-got.y)<.0001f&&std::fabs(want.z-got.z)<.0001f,"positions");}
   for(size_t i=0;i<a.normals.size();++i){auto got=actual.normals[i];p2pose::Vec want,x,y;require(p2pose::unit(a.normals[i],x)&&p2pose::unit(b.normals[i],y),"normals");if(!p2pose::unit(p2pose::mix(x,y,span.weight),want))want=span.weight<=.5f?x:y;if(span.weight==0)want=a.normals[i];require(std::fabs(want.x-got.x)<.0001f&&std::fabs(want.y-got.y)<.0001f&&std::fabs(want.z-got.z)<.0001f,"normal interpolation");}
   std::printf("KOCHAPPY_SAMPLE clip=%s frame=%.5f left=%zu right=%zu weight=%.5f\n",name,frame,span.left,span.right,span.weight);return std::make_pair(actual,pixels);
  };
  auto control=render(actors[1],"wait1",0,"control.ppm");
  size_t changed=0,visible=0;
  for(const auto& clip:clips){float middle=(clip.frames[0]+clip.frames[1])*.5f;
   const auto prefix=clip.name;auto first=render(actors[0],clip.name.c_str(),0,(prefix+"-start.ppm").c_str());
   auto half=render(actors[0],clip.name.c_str(),middle,(prefix+"-half.ppm").c_str());
   gameflow.mPauseAll=true;auto repeat=render(actors[0],clip.name.c_str(),middle,(prefix+"-repeat.ppm").c_str());gameflow.mPauseAll=false;
   require(half.second==repeat.second&&difference(half.first,repeat.first)==0,"pause/replay");
   for(size_t i=0;i<half.second.size();++i){visible+=half.second[i]>8;changed+=half.second[i]!=first.second[i];}
   render(actors[0],clip.name.c_str(),clip.duration-1,(prefix+"-end.ppm").c_str());
  }
  render(actors[0],"dead",0,"corpse.ppm",true);
  p2pose::Pose untouched;std::string name;float frame;bool corpse;require(pc_p2_kochappy_geometry(actors[1],untouched,name,frame,corpse)&&difference(untouched,control.first)==0,"actor isolation");
  pc_p2_kochappy_forget(actors[0]);require(!pc_p2_kochappy_geometry(actors[0],untouched,name,frame,corpse),"forget");pc_p2_kochappy_reset();require(!pc_p2_kochappy_geometry(actors[1],untouched,name,frame,corpse),"reset");
  require(visible>100&&changed>100,"visible interpolation");std::printf("PASS CROSSFADE_RENDER KOCHAPPY_INTERPOLATION clips=5 isolated=2 endpoints=1 pause_replay=1 reset=1 visible=%zu changed=%zu\n",visible,changed);std::fflush(nullptr);std::_Exit(0);
 }
};
'''

def build(native, build_dir, output, head):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    template=(Path(__file__).resolve().parents[1]/'scripts/pikmin2_crossfade_fixture.cpp').read_text()
    begin=template.index('class CrossfadeApp final:');end=template.index('int main(',begin)
    includes='#include "pc_p2_kochappy.h"\n#include "pc_p2_kochappy_policy.h"\n#include "pc_p2_pose_bank.h"\n#include <map>\n'
    source=includes+template[:begin]+APP+template[end:]
    (output/'fixture.cpp').write_text(source)
    return build_fixture(build_dir,native,output/'fixture.cpp',output/'build',head)

def stage(source,output):
    source=source.resolve();output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    gen=source/'assets/dataDir/stages/chal0/default.gen';raw=gen.read_bytes();rows=records(gen)
    enemies=[r for r in rows if r[72:76]==b'iket'];assert len(enemies)==1
    identity=struct.unpack_from('<I',enemies[0],8)[0];extra=bytearray(enemies[0]);struct.pack_into('<I',extra,8,418002)
    x,y,z=struct.unpack_from('>3f',extra,48);struct.pack_into('>3f',extra,48,x+50,y,z)
    overlay(source/'assets',output/'assets',{'dataDir/stages/chal0/default.gen':raw[:20]+struct.pack('>I',len(rows)+1)+b''.join(rows)+bytes(extra)})
    for name in ('p2-pod.txt','p2-kochappy-profile.txt','p2-kochappy-bank.txt'):shutil.copyfile(source/name,output/name)
    (output/'p2-kochappy-actors.txt').write_text(f'P2_KOCHAPPY_ACTORS_1 2\n{identity}\n418002\n')
    (output/'p2-kochappy-interpolation.txt').write_text('P2_KOCHAPPY_INTERPOLATION_1\n')
    return output
