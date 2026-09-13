// Private renderer acceptance: real retained UV0 model, synthetic texture track.
// Never install this fixture as the player executable.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "gl/pc_opengl.h"
#include "pc_gfx.h"
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "Camera.h"
#include "Shape.h"
#include "Texture.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "MoviePlayer.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_p2_preview.h"
#include "pc_p2_material_binding.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "system.h"
#include <cstdio>
#include <cstdlib>

static void require(bool ok,const char* why){if(!ok){std::printf("FAIL MATERIAL_BINDING %s\n",why);std::fflush(nullptr);std::_Exit(1);}}
static std::vector<unsigned char> capture(const char* path){
 pc_gfx_flush_batch();glFinish();
 GLint view[4];glGetIntegerv(GL_VIEWPORT,view);
 require(view[2]>0&&view[3]>0&&view[2]<=4096&&view[3]<=4096,"viewport");
 std::vector<unsigned char> pixels(size_t(view[2])*view[3]*3);
 glPixelStorei(GL_PACK_ALIGNMENT,1);glReadPixels(view[0],view[1],view[2],view[3],GL_RGB,GL_UNSIGNED_BYTE,pixels.data());
 require(glGetError()==GL_NO_ERROR,"readback");
 FILE* out=std::fopen(path,"wb");require(out!=nullptr,"capture output");std::fprintf(out,"P6\n%d %d\n255\n",view[2],view[3]);
 for(int y=view[3]-1;y>=0;--y)std::fwrite(pixels.data()+size_t(y)*view[2]*3,1,size_t(view[2])*3,out);
 std::fclose(out);return pixels;
}
class MaterialApp final:public PlugPikiApp {
 int frames=0,ready=0;Shape* model=nullptr;p2material::Bank bank;p2material::Binding binding;
public:
 int idle()override{
  int result=PlugPikiApp::idle();require(++frames<1200,"startup timeout");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_ready()||!naviMgr||!naviMgr->getNavi()||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++ready;
  if(!model){
   const int heap=gsys->setHeap(SYSHEAP_App);
   model=gameflow.loadShape("courses/pikmin2room/snow_wait1_00.mod",true);require(model,"model missing");
   for(int i=0;i<model->mTexAttrCount;++i)if(model->mTexAttrList[i].mTexture)model->mTexAttrList[i].mTexture->attach();
   gsys->setHeap(heap);bank.source=std::string(64,'0');bank.duration=10;bank.attribute=0;
   std::vector<p2material::Target> targets;
   for(int i=0;i<model->mMaterialCount;++i){
    auto& mat=model->mMaterialList[i];auto& info=mat.mTextureInfo;
    if(!(mat.mFlags&MATFLAG_PVW)||info.mTextureDataCount!=1||info.mTexGenDataCount!=1||info.mTexGenData[0].mTexGenSrc!=4)continue;
    p2material::Track t;t.material="fixture_"+std::to_string(i);t.center={.5,.5,0};
    t.curves[0]={{0,1,0,0}};t.curves[1]={{0,1,0,0}};t.curves[2]={{0,0,0,0}};
    t.curves[3]={{0,0,0,0},{10,.35,0,0}};t.curves[4]={{0,0,0,0}};
    bank.tracks.push_back(t);targets.push_back({t.material,0,unsigned(i)});
   }
   require(binding.bind(bank,*model,targets,1),"explicit model binding");
   std::printf("MATERIAL_BINDING_READY materials=%d tracks=%zu synthetic_track=1\n",model->mMaterialCount,bank.tracks.size());
  }
  return result;
 }
 void draw(Graphics& gfx)override{
  PlugPikiApp::draw(gfx);if(ready<120||!model)return;
  require(gfx.mCamera,"camera");
  gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx,gfx.mCamera->mFov,gfx.mCamera->mAspectRatio,gfx.mCamera->mNear,gfx.mCamera->mFar,1.f);
  gfx.setDepth(true);gfx.useMaterial(nullptr);
  Matrix4f world,view;auto position=naviMgr->getNavi()->mSRT.t+Vector3f(0,20,0);
  world.makeSRT(Vector3f(5,5,5),Vector3f(0,0,0),position);gfx.mCamera->mLookAtMtx.multiplyTo(world,view);
  auto render=[&](double frame,const char* path){
   pc_gfx_flush_batch();glClearColor(0,0,0,1);glDepthMask(GL_TRUE);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
   model->updateAnim(gfx,view,nullptr,nullptr);require(binding.draw(bank,*model,gfx,frame,1),"bound draw");return capture(path);
  };
  auto first=render(0,"material-frame0.ppm"),changed=render(10,"material-frame10.ppm"),again=render(0,"material-frame0-repeat.ppm");
  require(first==again,"same-frame phase reset changed pixels");
  std::size_t visible=0,different=0;
  for(std::size_t i=0;i<first.size();++i){visible+=first[i]>8;different+=first[i]!=changed[i];}
  require(visible>100&&different>100,"texture transform invisible");
  binding.reset();require(!binding.draw(bank,*model,gfx,0,1),"reset binding rendered");
  std::printf("PASS MATERIAL_BINDING_RENDER visible_channels=%zu changed_channels=%zu replay_equal=1 reset_refused=1\n",visible,different);
  std::fflush(nullptr);std::_Exit(0);
 }
};
int main(int argc,char** argv){
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();SDL_SetHint("SDL_WINDOW_NO_ACTIVATION_WHEN_SHOWN","1");
 pc_gpu_preference_apply();_putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);
 require(pc_pikipelago_room_preview(),"requires room preview");if(!pc_window_init("Material binding fixture",960,720))return 3;
 SDL_HideWindow(SDL_GL_GetCurrentWindow());pc_settings_init();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();
 gsys->run(new MaterialApp());return 0;
}
