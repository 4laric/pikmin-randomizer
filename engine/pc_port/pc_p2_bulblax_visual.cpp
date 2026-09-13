#include "pc_p2_bulblax_visual.h"
#include "pc_p2_bulblax_visual_policy.h"
#include "pc_p2_animation.h"
#include "pc_p2_display_clock.h"
#include "pc_bbft.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include <SDL.h>
#include <fstream>
#include <map>
#include <cstdio>
#include <cstdlib>
namespace {
p2bulblax::Profile profile;std::map<size_t,std::vector<Shape*>> shapes;std::map<size_t,p2display::Clock> clocks;size_t total=0;std::set<std::pair<size_t,size_t>> logged;
void fail(){std::fputs("P2_BULBLAX_VISUAL invalid profile/model\n",stderr);std::abort();}
Shape* load(const std::string& name,std::vector<unsigned char>& reference,size_t& clipBytes){
 std::ifstream in("assets/dataDir/courses/pikmin2room/"+name,std::ios::binary|std::ios::ate);if(!in)fail();auto size=in.tellg();
 if(size<=0||size>1024*1024||clipBytes+size_t(size)>1024*1024||total+size_t(size)>16*1024*1024)fail();
 clipBytes+=size_t(size);total+=size_t(size);in.seekg(0);std::vector<unsigned char> data(size_t(size),0),resources;
 if(!in.read(reinterpret_cast<char*>(data.data()),size)||!p2animation::resources(data,resources))fail();
 if(!reference.empty()&&reference!=resources)fail();reference=resources;
 Shape* shape=gameflow.loadShape(("courses/pikmin2room/"+name).c_str(),true);if(!shape)fail();
 for(int i=0;i<shape->mTexAttrCount;++i)if(shape->mTexAttrList[i].mTexture)shape->mTexAttrList[i].mTexture->attach();return shape;
}
}
void pc_p2_bulblax_visual_reset(){profile={};shapes.clear();clocks.clear();total=0;logged.clear();}
void pc_p2_bulblax_visual_setup(){
 pc_p2_bulblax_visual_reset();if(!pc_pikipelago_room_preview())return;
 std::ifstream in("p2-bulblax-visual.txt");if(!in)return;
 try{profile=p2bulblax::read(in);}catch(...){fail();}
 std::map<int,std::vector<unsigned char>> resources;
 // Validate/copy the entire bank in the host. Load only clips selected by this
 // explicit display profile, so unused boss poses do not consume App heap.
 for(const auto& d:profile.displays){if(shapes.count(d.clip))continue;const auto& clip=profile.clips[d.clip];size_t bytes=0;
 for(size_t i=0;i<clip.frames.size();++i){char name[100];std::snprintf(name,sizeof(name),"bulblax_%s_%s_%02u.mod",p2bulblax::species(clip.enemy),clip.name.c_str(),unsigned(i));shapes[d.clip].push_back(load(name,resources[clip.enemy],bytes));}}
 const auto started=SDL_GetTicks();for(const auto& item:shapes)if(!clocks[item.first].start(profile.clips[item.first].duration,started))fail();
 for(const auto& d:profile.displays){const auto& c=profile.clips[d.clip];std::printf("P2_BULBLAX_VISUAL_READY id=%u enemy=%d species=%s clip=%s xyz=%.6f,%.6f,%.6f yaw=%.3f scale=1 noninteractive=1\n",d.id,c.enemy,p2bulblax::species(c.enemy),c.name.c_str(),d.x,d.y,d.z,d.yaw);}
}
void pc_p2_bulblax_visual_draw(Graphics& gfx){
 if(profile.displays.empty()||!gfx.mCamera)return;
 gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx,gfx.mCamera->mFov,gfx.mCamera->mAspectRatio,gfx.mCamera->mNear,gfx.mCamera->mFar,1.f);gfx.useMaterial(nullptr);gfx.setDepth(true);
 const auto tick=SDL_GetTicks();
 for(auto& item:clocks){const auto status=item.second.update(tick);if(status==p2display::Advance::Invalid)fail();if(status==p2display::Advance::RecoveredGap)std::printf("P2_BULBLAX_CLOCK visual_gap_seek clip=%u\n",unsigned(item.first));}
 for(const auto& d:profile.displays){const auto& c=profile.clips[d.clip];size_t pose=c.index(float(clocks.at(d.clip).frame()));Shape* shape=shapes.at(d.clip)[pose];
 Matrix4f world,view;world.makeSRT(Vector3f(1,1,1),Vector3f(0,d.yaw*0.0174532925199433f,0),Vector3f(d.x,d.y,d.z));gfx.mCamera->mLookAtMtx.multiplyTo(world,view);shape->updateAnim(gfx,view,nullptr,nullptr);shape->drawshape(gfx,*gfx.mCamera,nullptr);
 if(logged.insert({d.clip,pose}).second)std::printf("P2_BULBLAX_VISUAL_DRAW enemy=%d clip=%s pose=%u source_frame=%d noninteractive=1\n",c.enemy,c.name.c_str(),unsigned(pose),c.frames[pose]);}
}
