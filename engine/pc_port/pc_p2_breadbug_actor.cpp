// P2 small Breadbug appearance on an opted-in P1 Collec. P1 gameplay remains authoritative.
#include "pc_p2_breadbug_actor.h"
#include "pc_p2_animation.h"
#include "pc_p2_breadbug_cargo_phase.h"
#include "pc_bbft.h"
#include "teki.h"
#include "Teki.h"
#include "Pellet.h"
#include "Piki.h"
#include "Stickers.h"
#include "ObjType.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include <SDL.h>
#include <map>
#include <set>
#include <vector>
#include <string>
#include <fstream>
#include <cmath>
#include <cstdlib>
#include <cstdio>
namespace {
// P1 TEKI_Collec host carry power (taicollec.cpp:509): the proxy drags cargo at
// 2.0, while the P2 PanModokiBase contest strength for the same pellet is
// (min+max)/2. The two scales are reported separately, never conflated.
const float PROXY_CARRY_POWER=2.0f;
struct Motion {int duration=0;std::vector<int> frames;std::vector<Shape*> shapes;};
struct BreadbugProxyActor {unsigned id;unsigned started;int lastMotion=-1;bool logged=false;int loggedCargo=-99;bool lastHeld=false;int lastCarriers=-1;};
std::map<BTeki*,BreadbugProxyActor> actors;Motion motions[2];
Motion cargoMotions[2];bool cargoEnabled=false;
void fail(){std::fputs("P2_BREADBUG_ACTOR invalid P1 proxy profile\n",stderr);std::abort();}
int carriers(Pellet* pellet){
 Stickers stuckList(pellet);Iterator it(&stuckList);int count=0;CI_LOOP(it){if((*it)->isPiki())++count;}return count;
}
Shape* load(const std::string& name){
 std::ifstream in("assets/dataDir/courses/pikmin2room/"+name,std::ios::binary|std::ios::ate);if(!in)fail();auto size=in.tellg();if(size<=0||size>16*1024*1024)fail();in.seekg(0);
 std::vector<unsigned char> bytes(size_t(size),0),resources;if(!in.read(reinterpret_cast<char*>(bytes.data()),size)||!p2animation::resources(bytes,resources))fail();
 Shape* shape=gameflow.loadShape(("courses/pikmin2room/"+name).c_str(),true);if(!shape)fail();
 for(int i=0;i<shape->mTexAttrCount;++i)if(shape->mTexAttrList[i].mTexture)shape->mTexAttrList[i].mTexture->attach();return shape;
}
}
void pc_p2_breadbug_actor_reset(){actors.clear();for(auto& motion:motions)motion=Motion{};for(auto& motion:cargoMotions)motion=Motion{};cargoEnabled=false;}
void pc_p2_breadbug_actor_forget(BTeki* actor){actors.erase(actor);}
void pc_p2_breadbug_actor_setup(){
 pc_p2_breadbug_actor_reset();if(!pc_pikipelago_room_preview())return;std::ifstream in("p2-breadbug-actor.txt");if(!in)return;
 std::string word;if(!(in>>word)||word!="P2_BREADBUG_ACTOR_PROXY_1"||!tekiMgr)fail();
 for(int k=0;k<2;++k){int count;auto& motion=motions[k];if(!(in>>word>>motion.duration>>count)||word!=(k?"move":"wait")||motion.duration<2||motion.duration>10000||count<2||count>12)fail();
  for(int i=0;i<count;++i){int frame;if(!(in>>frame)||frame<0||frame>=motion.duration||(i&&frame<=motion.frames.back()))fail();motion.frames.push_back(frame);}
  if(motion.frames.front()!=0||motion.frames.back()!=motion.duration-1)fail();
 }
 int count;if(!(in>>count)||count<1||count>8)fail();std::set<unsigned> wanted;
 for(int i=0;i<count;++i){unsigned long long id;int kind;if(!(in>>id>>kind)||id>0xffffffffULL||kind!=TEKI_Collec||!wanted.insert(unsigned(id)).second)fail();}
 if(in>>word)fail();std::set<unsigned> found;
 Iterator it(tekiMgr);CI_LOOP(it){Teki* actor=static_cast<Teki*>(*it);if(!actor||!actor->mGenerator)continue;unsigned id=actor->mGenerator->_70;if(!wanted.count(id))continue;
  if(actor->mTekiType!=TEKI_Collec||!found.insert(id).second)fail();actors.emplace(actor,BreadbugProxyActor{id,SDL_GetTicks()});
  std::printf("P2_BREADBUG_ACTOR_READY generator=%u native_type=8 xyz=%.6f,%.6f,%.6f behavior=P1_Collec_proxy\n",id,actor->mSRT.t.x,actor->mSRT.t.y,actor->mSRT.t.z);
 }
 if(found!=wanted)fail();
 for(int k=0;k<2;++k)for(size_t i=0;i<motions[k].frames.size();++i){char name[80];std::snprintf(name,sizeof(name),"breadbug_actor_%s_%02u.mod",k?"move":"wait",unsigned(i));motions[k].shapes.push_back(load(name));}
 std::ifstream bank("p2-breadbug-cargo.txt");if(bank){
  if(!(bank>>word)||word!="P2_BREADBUG_CARGO_1")fail();
  for(int k=0;k<2;++k){auto& motion=cargoMotions[k];int count;
   if(!(bank>>word>>motion.duration>>count)||word!=(k?"hide":"back")||motion.duration!=49||count<2||count>12)fail();
   for(int i=0;i<count;++i){int frame;if(!(bank>>frame)||frame<0||frame>=49||(i&&frame<=motion.frames.back()))fail();motion.frames.push_back(frame);}
   if(motion.frames.front()!=0||motion.frames.back()!=48)fail();
   for(int required:(k?std::vector<int>{20}:std::vector<int>{10,39})) {bool present=false;for(int f:motion.frames)present|=f==required;if(!present)fail();}
  }
  if(bank>>word)fail();
  for(int k=0;k<2;++k)for(size_t i=0;i<cargoMotions[k].frames.size();++i){char name[80];std::snprintf(name,sizeof(name),"breadbug_cargo_%s_%02u.mod",k?"hide":"back",unsigned(i));cargoMotions[k].shapes.push_back(load(name));}
  cargoEnabled=true;
 }
}
void pc_p2_breadbug_actor_tick(){
 if(actors.empty())return;
 for(auto& entry:actors){
  BTeki* actor=entry.first;auto& state=entry.second;
  Pellet* held=actor->getCreaturePointer(2)&&actor->getCreaturePointer(2)->isObjType(OBJTYPE_Pellet)?static_cast<Pellet*>(actor->getCreaturePointer(2)):nullptr;
  if(!held){state.lastHeld=false;continue;} // read-only: the P1 host owns the cargo, the proxy only observes it
  const int n=carriers(held);
  if(!state.lastHeld||n!=state.lastCarriers){
   state.lastHeld=true;state.lastCarriers=n;
   std::printf("P2_BREADBUG_CONTEST generator=%u native_power=%g carriers=%d\n",state.id,PROXY_CARRY_POWER,n);
  }
 }
}
bool pc_p2_breadbug_actor_draw(BTeki* actor,Graphics& gfx,const Matrix4f& view){
 auto found=actors.find(actor);if(found==actors.end()||!actor->isAlive()||!gfx.mCamera)return false;
 auto& state=found->second;
 if(cargoEnabled){
  int nativeState=actor->mStateID;auto* anim=actor->mTekiAnimator;
  p2breadbugcargo::Selection selected{p2breadbugcargo::Fallback,0};
  if(nativeState==9)selected={p2breadbugcargo::Hidden,0};
  else if(anim&&anim->getFrameCount()>1){
   int motion=anim->getCurrentMotionIndex();bool matches=(nativeState==8?motion==TekiMotion::Type3:motion==TekiMotion::Move2);
   float start=0,end=0;if(matches&&(nativeState==5||nativeState==6)){start=anim->getKeyValueByKeyType(0);end=anim->getKeyValueByKeyType(1);}
   selected=p2breadbugcargo::select(nativeState,actor->getCreaturePointer(2)!=nullptr,matches,anim->getCounter(),anim->getFrameCount(),start,end);
  }
  if(selected.kind!=p2breadbugcargo::Fallback){
   if(state.loggedCargo!=nativeState){std::printf("P2_BREADBUG_CARGO_VISUAL generator=%u state=%d kind=%d source_frame=%.3f native_counter=%.3f\n",state.id,nativeState,int(selected.kind),selected.frame,anim?anim->getCounter():0);state.loggedCargo=nativeState;}
   if(selected.kind==p2breadbugcargo::Hidden)return true;
   auto& motion=cargoMotions[int(selected.kind)];size_t best=0;
   for(size_t i=1;i<motion.frames.size();++i)if(std::fabs(float(motion.frames[i])-selected.frame)<std::fabs(float(motion.frames[best])-selected.frame))best=i;
   Shape* shape=motion.shapes[best];shape->updateAnim(gfx,view,nullptr,actor);shape->drawshape(gfx,*gfx.mCamera,nullptr);return true;
  }
 }
 const int kind=actor->mVelocity.x*actor->mVelocity.x+actor->mVelocity.z*actor->mVelocity.z>1.f?1:0;
 if(kind!=state.lastMotion){state.lastMotion=kind;state.started=SDL_GetTicks();}
 auto& motion=motions[kind];const float frame=std::fmod(float(SDL_GetTicks()-state.started)*.03f,float(motion.duration));size_t best=0;
 for(size_t i=1;i<motion.frames.size();++i)if(std::fabs(float(motion.frames[i])-frame)<std::fabs(float(motion.frames[best])-frame))best=i;
 Shape* shape=motion.shapes[best];shape->updateAnim(gfx,view,nullptr,actor);shape->drawshape(gfx,*gfx.mCamera,nullptr);
 if(!state.logged){std::printf("P2_BREADBUG_ACTOR_DRAW generator=%u visual_proxy no_P2_FSM\n",state.id);state.logged=true;}return true;
}
