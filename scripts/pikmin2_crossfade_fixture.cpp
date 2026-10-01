// Private renderer acceptance; no player executable or save changes.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "gl/pc_opengl.h"
#include "pc_gfx.h"
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "Camera.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "MoviePlayer.h"
#include "PlayerState.h"
#include "Demo.h"
#include "teki.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_p2_preview.h"
#include "pc_p2_enemy.h"
#include "pc_p2_skin.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "system.h"
#include <fstream>
#include <cstdio>
#include <cstdlib>
static void require(bool ok,const char* why){if(!ok){std::printf("FAIL CROSSFADE %s\n",why);std::fflush(nullptr);std::_Exit(1);}}
static std::vector<unsigned char> capture(const char* path){
 pc_gfx_flush_batch();glFinish();GLint v[4];glGetIntegerv(GL_VIEWPORT,v);require(v[2]>0&&v[3]>0,"viewport");
 std::vector<unsigned char> pixels(size_t(v[2])*v[3]*3);glPixelStorei(GL_PACK_ALIGNMENT,1);
 glReadPixels(v[0],v[1],v[2],v[3],GL_RGB,GL_UNSIGNED_BYTE,pixels.data());require(glGetError()==GL_NO_ERROR,"readback");
 FILE* out=std::fopen(path,"wb");require(out,"capture");std::fprintf(out,"P6\n%d %d\n255\n",v[2],v[3]);
 for(int y=v[3]-1;y>=0;--y)std::fwrite(pixels.data()+size_t(y)*v[2]*3,1,size_t(v[2])*3,out);std::fclose(out);return pixels;
}
static float difference(const p2pose::Pose& a,const p2pose::Pose& b){
 require(a.positions.size()==b.positions.size()&&a.normals.size()==b.normals.size(),"pose sizes");float error=0;
 for(bool normals:{false,true}){const auto& x=normals?a.normals:a.positions;const auto& y=normals?b.normals:b.positions;
 for(size_t i=0;i<x.size();++i)error=std::max(error,std::max(std::fabs(x[i].x-y[i].x),std::max(std::fabs(x[i].y-y[i].y),std::fabs(x[i].z-y[i].z))));}return error;
}
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
  BTeki* actor=nullptr;Iterator enemies(tekiMgr);CI_LOOP(enemies){auto* t=static_cast<Teki*>(*enemies);if(pc_p2_enemy_name(t)){actor=t;break;}}
  require(actor&&gfx.mCamera,"Snow actor");
  std::ifstream jf("p2-snow-joints.txt"),mf("p2-snow-skin.txt");auto bank=p2attach::read(jf);auto mesh=p2skin::read(mf);require(bank&&mesh,"bank");
  p2attach::Instance oracle;auto token=oracle.bind(bank);p2attach::Instance::Pose from;
  p2pose::Pose expected;expected.positions.resize(mesh->positions.size());expected.normals.resize(mesh->normals.size());
  gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx,gfx.mCamera->mFov,gfx.mCamera->mAspectRatio,gfx.mCamera->mNear,gfx.mCamera->mFar,1.f);gfx.setDepth(true);gfx.useMaterial(nullptr);
  Matrix4f world,view;world.makeSRT(Vector3f(3,3,3),Vector3f(0,0,0),naviMgr->getNavi()->mSRT.t);gfx.mCamera->mLookAtMtx.multiplyTo(world,view);
  auto render=[&](int motion,float phase,float seconds,const char* path,bool corpse=false){
   actor->startMotion(motion);actor->mTekiAnimator->setCounter(phase*(actor->mTekiAnimator->getFrameCount()-1));
   pc_p2_snow_update(actor,seconds);pc_gfx_flush_batch();glClearColor(0,0,0,1);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
   require(pc_p2_snow_draw(actor,gfx,view,corpse),"draw");auto pixels=capture(path);
   p2pose::Pose actual;std::string clip;float frame;bool carried;require(pc_p2_snow_geometry(actor,actual,clip,frame,carried),"geometry");
   std::printf("CROSSFADE_SAMPLE clip=%s frame=%.4f file=%s\n",clip.c_str(),frame,path);return std::make_pair(actual,pixels);
  };
  // Clear any transition accumulated during autonomous startup through a snap state.
  render(TekiMotion::Flick,0,0,"reset.ppm");auto idle=render(TekiMotion::Wait1,0,0,"idle.ppm");
  require(oracle.sample(token,bank->clip("wait1"),0,p2attach::Affine{},1)&&oracle.capture(token,from),"idle oracle");
  auto begin=render(TekiMotion::Move1,.3f,0,"walk-start.ppm");require(difference(idle.first,begin.first)==0,"start continuity");
  auto half=render(TekiMotion::Move1,.3f,.075f,"walk-half.ppm");
  const float walkFrame=.3f*(bank->clips[bank->clip("move1")].duration-1);
  require(oracle.sample(token,bank->clip("move1"),walkFrame,p2attach::Affine{},1,false,false,nullptr,0,&from,.5f)&&p2skin::deform(*mesh,oracle,token,expected),"half oracle");
  require(difference(expected,half.first)<.0002f&&difference(idle.first,half.first)>.01f,"half geometry");
  auto repeat=render(TekiMotion::Move1,.3f,0,"walk-repeat.ppm");require(difference(half.first,repeat.first)==0&&half.second==repeat.second,"duplicate draw");
  gameflow.mPauseAll=true;auto paused=render(TekiMotion::Move1,.3f,1,"paused.ppm");gameflow.mPauseAll=false;require(paused.second==half.second,"pause");
  require(oracle.capture(token,from),"interrupt snapshot");auto interrupt=render(TekiMotion::Attack,.4f,0,"attack-start.ppm");require(difference(interrupt.first,half.first)==0,"interruption");
  auto attack=render(TekiMotion::Attack,.4f,.15f,"attack-end.ppm");
  require(oracle.sample(token,bank->clip("attack"),.4f*(bank->clips[bank->clip("attack")].duration-1),p2attach::Affine{},1)&&p2skin::deform(*mesh,oracle,token,expected),"attack oracle");require(difference(expected,attack.first)<.0002f,"attack endpoint");
  auto death=render(TekiMotion::Dead,.5f,0,"death.ppm");require(oracle.sample(token,bank->clip("dead"),.5f*(bank->clips[bank->clip("dead")].duration-1),p2attach::Affine{},1)&&p2skin::deform(*mesh,oracle,token,expected),"death oracle");require(difference(expected,death.first)<.0002f,"death snap");
  size_t visible=0,changed=0;for(size_t i=0;i<half.second.size();++i){visible+=half.second[i]>8;changed+=half.second[i]!=idle.second[i];}
  require(visible>100&&changed>100,"visible transition");std::printf("PASS CROSSFADE_RENDER visible=%zu changed=%zu replay_equal=1 endpoints=1 interrupted=1 pause=1 death_snap=1\n",visible,changed);std::fflush(nullptr);std::_Exit(0);
 }
};
int main(int argc,char** argv){
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();SDL_SetHint("SDL_WINDOW_NO_ACTIVATION_WHEN_SHOWN","1");
 pc_gpu_preference_apply();_putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);
 require(pc_pikipelago_room_preview(),"requires preview");if(!pc_window_init("Snow crossfade fixture",960,720))return 3;
 SDL_HideWindow(SDL_GL_GetCurrentWindow());pc_settings_init();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new CrossfadeApp());return 0;
}
