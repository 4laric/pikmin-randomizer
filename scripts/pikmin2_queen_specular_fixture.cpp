// Private Queen renderer acceptance: audited diffuse UV1 + real source BTK.
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
#include "pc_p2_specular_layer.h"
#include <fstream>
#include "Dolphin/gx.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "system.h"
#include <cstdio>
#include <cstdlib>

static void require(bool ok,const char* why){if(!ok){std::printf("FAIL QUEEN_SPECULAR %s\n",why);std::fflush(nullptr);std::_Exit(1);}}
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
 int frames=0,ready=0;Shape* model=nullptr;p2material::Bank bank;
public:
 int idle()override{
  int result=PlugPikiApp::idle();require(++frames<1200,"startup timeout");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_ready()||!naviMgr||!naviMgr->getNavi()||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++ready;
  if(!model){
   const int heap=gsys->setHeap(SYSHEAP_App);
   model=gameflow.loadShape("courses/pikmin2room/bulblax_Queen_wait1_00.mod",true);require(model,"model missing");
   for(int i=0;i<model->mTexAttrCount;++i)if(model->mTexAttrList[i].mTexture)model->mTexAttrList[i].mTexture->attach();
   gsys->setHeap(heap);
   std::ifstream input("p2-queen-specular.txt");bank=p2material::read(input);
   require(bank.duration==30&&bank.tracks.size()==1,"source animation");
   std::printf("QUEEN_SPECULAR_READY materials=%d source_btk=%s\n",model->mMaterialCount,bank.source.c_str());
  }
  return result;
 }
 void draw(Graphics& gfx)override{
  PlugPikiApp::draw(gfx);if(ready<120||!model)return;
  require(gfx.mCamera,"camera");
  capture("queen-scene.ppm");
  gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx,gfx.mCamera->mFov,gfx.mCamera->mAspectRatio,gfx.mCamera->mNear,gfx.mCamera->mFar,1.f);
  gfx.setDepth(true);gfx.useMaterial(nullptr);
  Matrix4f world,view;auto position=naviMgr->getNavi()->mSRT.t+Vector3f(0,0,0);
  world.makeSRT(Vector3f(.7f,.7f,.7f),Vector3f(0,0,0),position);gfx.mCamera->mLookAtMtx.multiplyTo(world,view);
  // PlugPikiApp's HUD leaves 2D lighting active. Install a controlled light7
  // for this isolated post-HUD comparison, not a claim of retail light parity.
  GXLightObj highlight;GXInitSpecularDir(&highlight,0.f,0.f,-1.f);
  GXInitLightAttn(&highlight,1.f,0.f,0.f,1.f,0.f,0.f);
  GXInitLightColor(&highlight,GXColor{96,96,96,255});GXLoadLightObjImm(&highlight,GX_LIGHT7);
  GXSetChanMatColor(GX_COLOR1A1,GXColor{255,255,255,255});
  GXSetChanAmbColor(GX_COLOR1A1,GXColor{0,0,0,0});
  auto render=[&](double frame,bool enabled,const char* path){
   pc_gfx_flush_batch();glClearColor(0,0,0,1);glDepthMask(GL_TRUE);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
   model->updateAnim(gfx,view,nullptr,nullptr);p2material::Sample sample;
   require(p2material::sample(bank,0,frame,sample),"sample");
   require(p2material::drawSpecular(*model,gfx,1,1,sample,enabled),"specular draw");return capture(path);
  };
  auto baseline=render(0,false,"queen-diffuse.ppm"),first=render(0,true,"queen-frame0.ppm"),
       changed=render(10,true,"queen-frame10.ppm"),again=render(0,true,"queen-frame0-repeat.ppm"),
       baselineAgain=render(0,false,"queen-diffuse-repeat.ppm");
  require(first==again&&baseline==baselineAgain,"same-frame replay changed pixels");
  std::size_t visible=0,different=0,contribution=0;
  for(std::size_t i=0;i<first.size();++i){visible+=first[i]>8;different+=first[i]!=changed[i];contribution+=first[i]!=baseline[i];}
  std::printf("QUEEN_SPECULAR_RENDER visible_channels=%zu animated_channels=%zu specular_channels=%zu replay_equal=1\n",visible,different,contribution);
  require(visible>100&&different>100&&contribution>100,"specular contribution or animation invisible");
  std::puts("PASS QUEEN_SPECULAR_RENDER");
  std::fflush(nullptr);std::_Exit(0);
 }
};
int main(int argc,char** argv){
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();SDL_SetHint("SDL_WINDOW_NO_ACTIVATION_WHEN_SHOWN","1");
 pc_gpu_preference_apply();_putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);
 require(pc_pikipelago_room_preview(),"requires room preview");if(!pc_window_init("Queen specular fixture",960,720))return 3;
 SDL_HideWindow(SDL_GL_GetCurrentWindow());pc_settings_init();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();
 gsys->run(new MaterialApp());return 0;
}
