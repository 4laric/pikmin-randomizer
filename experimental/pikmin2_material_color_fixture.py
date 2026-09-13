"""Real BRK curves on a retained model: rendered change and material restoration."""
from pathlib import Path
import shutil
from scripts.build_pikmin2_fixture import build_fixture
from scripts.preview_pikmin2_room import overlay
from experimental.pikmin2_crossfade_fixture import run

APP=r'''
class MaterialApp final:public PlugPikiApp {
 int frames=0,ready=0;Shape* model=nullptr;p2color::Bank bank;p2color::Binding binding;
public:
 int idle()override{
  int result=PlugPikiApp::idle();require(++frames<1200,"startup timeout");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_ready()||!naviMgr||!naviMgr->getNavi()||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++ready;
  if(!model){
   int heap=gsys->setHeap(SYSHEAP_App);model=gameflow.loadShape("courses/pikmin2room/snow_wait1_00.mod",true);require(model,"model");
   for(int i=0;i<model->mTexAttrCount;++i)if(model->mTexAttrList[i].mTexture)model->mTexAttrList[i].mTexture->attach();gsys->setHeap(heap);
   std::ifstream in("material-color.txt");bank=p2color::read(in);require(bank.tracks.size()==1,"one source track");
   std::vector<p2color::Target> targets;const auto& t=bank.tracks[0];
   for(int i=0;i<model->mMaterialCount;++i)if((model->mMaterialList[i].mFlags&MATFLAG_PVW)&&model->mMaterialList[i].mTevInfo){
    auto& tev=*model->mMaterialList[i].mTevInfo;require(tev.mTevStageCount==1,"diagnostic single stage");
    // Explicit diagnostic material: texture * animated C0. The existing Snow
    // combiner does not consume C0; this is not Crawbster material parity.
    auto& c=tev.mTevStages[0].mTevColorCombiner;c.mInArgA=15;c.mInArgB=8;c.mInArgC=2;c.mInArgD=15;c.mTevOp=0;c.mBias=0;c.mScale=0;c.mDoClamp=1;c.mOutReg=0;
    targets.push_back({t.material,t.kind,t.reg,unsigned(i),0});
   }
   require(binding.bind(bank,*model,targets,1),"explicit diagnostic binding");
   std::printf("COLOR_READY source=%s material=%s kind=%u reg=%u targets=%zu diagnostic_remap=1\n",bank.source.c_str(),t.material.c_str(),t.kind,t.reg,targets.size());
  }return result;
 }
 void draw(Graphics& gfx)override{
  PlugPikiApp::draw(gfx);if(ready<120||!model)return;require(gfx.mCamera,"camera");
  gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx,gfx.mCamera->mFov,gfx.mCamera->mAspectRatio,gfx.mCamera->mNear,gfx.mCamera->mFar,1.f);gfx.setDepth(true);gfx.useMaterial(nullptr);
  Matrix4f world,view;world.makeSRT(Vector3f(5,5,5),Vector3f(0,0,0),naviMgr->getNavi()->mSRT.t+Vector3f(0,20,0));gfx.mCamera->mLookAtMtx.multiplyTo(world,view);
  auto state=[&](){std::vector<int> out;for(int i=0;i<model->mMaterialCount;++i){auto* tev=model->mMaterialList[i].mTevInfo;if(!tev)continue;
   for(const auto& r:tev->mTevColRegs){const auto& c=r.mAnimatedColor;out.insert(out.end(),{c.r,c.g,c.b,c.a});}for(const auto& c:tev->mKonstColors)out.insert(out.end(),{c.r,c.g,c.b,c.a});}return out;};
  auto render=[&](double frame,const char* path,bool animate){
   pc_gfx_flush_batch();glClearColor(0,0,0,1);glDepthMask(GL_TRUE);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);model->updateAnim(gfx,view,nullptr,nullptr);auto before=state();
   if(animate)require(binding.draw(bank,*model,gfx,frame,1),"color draw");else{gfx.useMaterial(nullptr);model->drawshape(gfx,*gfx.mCamera,nullptr);gfx.useMaterial(nullptr);}
   require(before==state(),"shared colors changed");return capture(path);
  };
  auto bare=render(0,"color-bare.ppm",false),first=render(0,"color-first.ppm",true),middle=render(bank.duration/2.0,"color-middle.ppm",true),repeat=render(0,"color-repeat.ppm",true),after=render(0,"color-bare-after.ppm",false);
  require(first==repeat&&bare==after,"replay or restore image");auto saved=state();require(!binding.draw(bank,*model,gfx,0,2)&&!binding.draw(bank,*model,gfx,bank.duration+1,1)&&state()==saved,"stale/invalid draw");
  binding.reset();require(!binding.draw(bank,*model,gfx,0,1),"reset");size_t changed=0,visible=0;
  for(size_t i=0;i<first.size();++i){changed+=first[i]!=middle[i];visible+=first[i]>8;}
  require(changed>100&&visible>100,"animation invisible");std::printf("PASS CROSSFADE_RENDER MATERIAL_COLOR_RENDER changed=%zu visible=%zu replay=1 restored=1 stale_refused=1\n",changed,visible);std::fflush(nullptr);std::_Exit(0);
 }
};
'''

def build(native,build_dir,output,head):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    source=(Path(__file__).resolve().parents[1]/'scripts/pikmin2_material_binding_fixture.cpp').read_text()
    start=source.index('class MaterialApp final:');end=source.index('int main(',start)
    source='#include "pc_p2_color_binding.h"\n#include <fstream>\n'+source[:start]+APP+source[end:]
    (output/'fixture.cpp').write_text(source)
    return build_fixture(build_dir,native,output/'fixture.cpp',output/'build',head)

def stage(source,bank,output):
    source=source.resolve();output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    overlay(source/'assets',output/'assets',{})
    shutil.copyfile(source/'p2-pod.txt',output/'p2-pod.txt')
    shutil.copyfile(bank/'material-color.txt',output/'material-color.txt')
    return output
