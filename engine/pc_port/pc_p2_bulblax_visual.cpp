#include "pc_p2_bulblax_visual.h"
#include "pc_p2_bulblax_visual_policy.h"
#include "pc_p2_btk.h"
#include "pc_p2_animation.h"
#include "pc_p2_display_clock.h"
#include "pc_p2_retail_player.h"
#include "pc_bbft.h"
#include "Shape.h"
#include "Joint.h"
#include "System.h"
#include "pc_p2_pose_bank.h"
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
struct Retail {p2retail::Player player;size_t clip=0;unsigned events=0;};
std::map<std::uint32_t,Retail> retail;
bool interpolate=false;
std::map<size_t,std::vector<p2pose::Baked>> baked;
std::map<std::uint32_t,Shape*> mutableShapes;
p2btk::Animation btk;bool btkReady=false;int btkMatrix=0;bool btkLogged=false;
std::string poseName(const p2bulblax::Clip& clip,size_t i) {
 char name[100];std::snprintf(name,sizeof(name),"bulblax_%s_%s_%02u.mod",p2bulblax::species(clip.enemy),clip.name.c_str(),unsigned(i));return name;
}

void fail(){std::fputs("P2_BULBLAX_VISUAL invalid profile/model\n",stderr);std::abort();}
Shape* load(const std::string& name,std::vector<unsigned char>& reference,size_t& clipBytes,size_t clip){
 std::ifstream in("assets/dataDir/courses/pikmin2room/"+name,std::ios::binary|std::ios::ate);if(!in)fail();auto size=in.tellg();
 if(size<=0||size>1024*1024||clipBytes+size_t(size)>1024*1024||total+size_t(size)>16*1024*1024)fail();
 clipBytes+=size_t(size);total+=size_t(size);in.seekg(0);std::vector<unsigned char> data(size_t(size),0),resources;
 if(!in.read(reinterpret_cast<char*>(data.data()),size)||!p2animation::resources(data,resources))fail();
 if(!reference.empty()&&reference!=resources)fail();reference=resources;
 if(interpolate){p2pose::Baked pose;if(!p2pose::decodeBaked(data,pose))fail();
  auto& bank=baked[clip];if(!bank.empty()&&bank.front().topology!=pose.topology)fail();bank.push_back(std::move(pose));}
 Shape* shape=gameflow.loadShape(("courses/pikmin2room/"+name).c_str(),true);if(!shape)fail();
 for(int i=0;i<shape->mTexAttrCount;++i)if(shape->mTexAttrList[i].mTexture)shape->mTexAttrList[i].mTexture->attach();return shape;
}
}
void pc_p2_bulblax_visual_reset(){profile={};shapes.clear();clocks.clear();retail.clear();total=0;logged.clear();mutableShapes.clear();baked.clear();interpolate=false;btk={};btkReady=false;btkMatrix=0;btkLogged=false;}
void pc_p2_bulblax_visual_setup(){
 pc_p2_bulblax_visual_reset();if(!pc_pikipelago_room_preview())return;
 std::ifstream in("p2-bulblax-visual.txt");if(!in)return;
 try{profile=p2bulblax::read(in);}catch(...){fail();}
 std::ifstream option("p2-bulblax-interpolation.txt");
 if(option){std::string magic,extra;if(!(option>>magic)||magic!="P2_BULBLAX_INTERPOLATION_1"||(option>>extra))fail();interpolate=true;}
 // Opt-in BTK texture-matrix source (#239). Absent sidecar -> no effect.
 std::ifstream btkIn("p2-bulblax-btk.txt");
 if(btkIn){std::string magic,file;int matrix=0;if(!(btkIn>>magic>>file>>matrix)||magic!="P2_BULBLAX_BTK_1"||matrix<0||matrix>7)fail();
  std::ifstream bin("assets/dataDir/courses/pikmin2room/"+file,std::ios::binary|std::ios::ate);
  if(bin){auto size=bin.tellg();if(size>0&&size<=64*1024){std::vector<unsigned char> data((size_t)size);bin.seekg(0);
   if(bin.read(reinterpret_cast<char*>(data.data()),size)&&p2btk::parse(data.data(),data.size(),btk)){btkReady=true;btkMatrix=matrix;}}}}
 std::map<int,std::vector<unsigned char>> resources;
 // Validate/copy the entire bank in the host. Load only clips selected by this
 // explicit display profile, so unused boss poses do not consume App heap.
 for(const auto& d:profile.displays){if(shapes.count(d.clip))continue;const auto& clip=profile.clips[d.clip];size_t bytes=0;
 for(size_t i=0;i<clip.frames.size();++i){char name[100];std::snprintf(name,sizeof(name),"bulblax_%s_%s_%02u.mod",p2bulblax::species(clip.enemy),clip.name.c_str(),unsigned(i));shapes[d.clip].push_back(load(name,resources[clip.enemy],bytes,d.clip));}}
 const auto started=SDL_GetTicks();for(const auto& item:shapes)if(!clocks[item.first].start(profile.clips[item.first].duration,started))fail();
 // Optional diagnostic tables. No gameplay receiver is attached to these displays.
 for(const auto& display:profile.displays){const auto& clip=profile.clips[display.clip];
  const std::string path=std::string("p2-bulblax-retail-")+p2bulblax::species(clip.enemy)+".txt";
  std::ifstream events(path);if(!events)continue;
  try{const auto table=p2retail::read(events);bool found=false;
   for(const auto& motion:table.motions)if(motion.name==clip.name+".bca"){
    auto& instance=retail[display.id];instance.clip=display.clip;
    if(motion.duration!=clip.duration||!instance.player.start(motion))fail();found=true;
   }
   if(!found)fail();
  }catch(...){fail();}
  std::printf("P2_BULBLAX_RETAIL_READY enemy=%d clip=%s id=%u\n",clip.enemy,clip.name.c_str(),display.id);
 }
 if(interpolate) for(const auto& d:profile.displays){
  if(!retail.count(d.id))fail(); // Only authoritative, pause-aware source clocks.
  const std::string path="courses/pikmin2room/"+poseName(profile.clips[d.clip],0);
  Shape* shape=gsys->getShape(path.c_str(),path.c_str(),nullptr,true);
  const auto& pose=baked.at(d.clip).front().pose;
  if(!shape || shape->mJointCount!=1 || shape->mVertexCount!=int(pose.positions.size()) || shape->mNormalCount!=int(pose.normals.size()))fail();
  for(int i=0;i<shape->mTexAttrCount;++i)if(shape->mTexAttrList[i].mTexture)shape->mTexAttrList[i].mTexture->attach();
  for(const auto& item:mutableShapes)if(item.second==shape || item.second->mVertexList==shape->mVertexList || item.second->mNormalList==shape->mNormalList)fail();
  for(const auto* source:shapes.at(d.clip))if(source==shape || source->mVertexList==shape->mVertexList || source->mNormalList==shape->mNormalList)fail();
  mutableShapes[d.id]=shape;
  std::printf("P2_BULBLAX_INTERPOLATION_READY id=%u private_model=1\n",d.id);
 }
 for(const auto& d:profile.displays){const auto& c=profile.clips[d.clip];std::printf("P2_BULBLAX_VISUAL_READY id=%u enemy=%d species=%s clip=%s xyz=%.6f,%.6f,%.6f yaw=%.3f scale=1 noninteractive=1\n",d.id,c.enemy,p2bulblax::species(c.enemy),c.name.c_str(),d.x,d.y,d.z,d.yaw);}
}
bool pc_p2_bulblax_visual_frame(std::uint32_t id,float& frame){
 auto it=retail.find(id);if(it==retail.end())return false;frame=it->second.player.frame();return true;
}
bool pc_p2_bulblax_visual_seek(std::uint32_t id,float frame){
 auto it=retail.find(id);return it!=retail.end()&&it->second.player.seek(frame);
}
void pc_p2_bulblax_visual_update(float seconds){
 if(retail.empty())return;
 const float delta=seconds*30.f;
 if(!std::isfinite(delta)||delta<0||delta>1000000)fail();
 for(auto& item:retail){const auto& clip=profile.clips[item.second.clip];
  if(item.second.player.advance(delta,[&](const p2retail::Event& e){
   if(item.second.events<64){++item.second.events;std::printf("P2_BULBLAX_RETAIL_EVENT enemy=%d clip=%s frame=%d type=%d id=%u\n",clip.enemy,clip.name.c_str(),e.frame,e.type,item.first);}
  })!=p2retail::Update::Ok)fail();
 }
}
void pc_p2_bulblax_visual_draw(Graphics& gfx){
 if(profile.displays.empty()||!gfx.mCamera)return;
 gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx,gfx.mCamera->mFov,gfx.mCamera->mAspectRatio,gfx.mCamera->mNear,gfx.mCamera->mFar,1.f);gfx.useMaterial(nullptr);gfx.setDepth(true);
 const auto tick=SDL_GetTicks();
 for(auto& item:clocks){const auto status=item.second.update(tick);if(status==p2display::Advance::Invalid)fail();if(status==p2display::Advance::RecoveredGap)std::printf("P2_BULBLAX_CLOCK visual_gap_seek clip=%u\n",unsigned(item.first));}
 if(btkReady&&!btkLogged){const float src=retail.empty()?float(clocks.begin()->second.frame()):retail.begin()->second.player.frame();
  float bs[3],br[3],bt[3];const float bf=btk.duration>0?std::fmod(src,float(btk.duration)):src;
  if(p2btk::sample(btk,btkMatrix,bf,bs,br,bt)&&(btkLogged=true))std::printf("P2_BULBLAX_BTK matrix=%d source_frame=%.3f scale=%.4f,%.4f,%.4f rot=%.4f,%.4f,%.4f trans=%.4f,%.4f,%.4f\n",btkMatrix,bf,bs[0],bs[1],bs[2],br[0],br[1],br[2],bt[0],bt[1],bt[2]);}
 for(const auto& d:profile.displays){const auto& c=profile.clips[d.clip];auto r=retail.find(d.id);size_t pose=c.index(r==retail.end()?float(clocks.at(d.clip).frame()):r->second.player.frame());Shape* shape=shapes.at(d.clip)[pose];
 if(interpolate){
  p2pose::Interval interval;if(!p2pose::bracket(c.frames,r->second.player.frame(),interval))fail();
  const auto& bank=baked.at(d.clip);const auto& a=bank[interval.left].pose;const auto& b=bank[interval.right].pose;
  shape=mutableShapes.at(d.id);
  // Private scene-heap arrays: no per-frame allocation and no shared source writes.
  for(size_t i=0;i<a.positions.size();++i){auto v=p2pose::mix(a.positions[i],b.positions[i],interval.weight);shape->mVertexList[i].set(v.x,v.y,v.z);}
  for(size_t i=0;i<a.normals.size();++i){p2pose::Vec v;
   if(!p2pose::unit(p2pose::mix(a.normals[i],b.normals[i],interval.weight),v))v=interval.weight<=.5f?a.normals[i]:b.normals[i];
   shape->mNormalList[i].set(v.x,v.y,v.z);}
  BoundBox bounds(shape->mVertexList[0],shape->mVertexList[0]);
  for(int i=1;i<shape->mVertexCount;++i)bounds.expandBound(shape->mVertexList[i]);
  shape->mCourseExtents=bounds;shape->mJointList[0].mBounds=bounds;
  // drawshape/initMesh issues GXSetArray each draw; do not invalidate the whole frame.
 }
 Matrix4f world,view;world.makeSRT(Vector3f(1,1,1),Vector3f(0,d.yaw*0.0174532925199433f,0),Vector3f(d.x,d.y,d.z));gfx.mCamera->mLookAtMtx.multiplyTo(world,view);shape->updateAnim(gfx,view,nullptr,nullptr);shape->drawshape(gfx,*gfx.mCamera,nullptr);
 if(logged.insert({d.clip,pose}).second)std::printf("P2_BULBLAX_VISUAL_DRAW enemy=%d clip=%s pose=%u source_frame=%d noninteractive=1\n",c.enemy,c.name.c_str(),unsigned(pose),c.frames[pose]);}
}

bool pc_p2_bulblax_visual_geometry(std::uint32_t id,p2pose::Pose& out){
 auto it=mutableShapes.find(id);if(it==mutableShapes.end())return false;
 const Shape& shape=*it->second;p2pose::Pose copy;
 for(int i=0;i<shape.mVertexCount;++i){const auto& v=shape.mVertexList[i];
  for(const auto* box:std::initializer_list<const BoundBox*>{&shape.mCourseExtents,&shape.mJointList[0].mBounds})
   if(v.x<box->mMin.x || v.y<box->mMin.y || v.z<box->mMin.z || v.x>box->mMax.x || v.y>box->mMax.y || v.z>box->mMax.z)return false;
 }
 for(int i=0;i<shape.mVertexCount;++i){const auto& v=shape.mVertexList[i];copy.positions.push_back({v.x,v.y,v.z});}
 for(int i=0;i<shape.mNormalCount;++i){const auto& v=shape.mNormalList[i];copy.normals.push_back({v.x,v.y,v.z});}
 out=std::move(copy);return true;
}

