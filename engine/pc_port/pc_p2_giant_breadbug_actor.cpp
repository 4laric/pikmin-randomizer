// P2 Giant Breadbug native actor on an opted-in P1 Collec bound to its Hollec nest.
// P1 FSM stays authoritative for locomotion/cargo; P2 mechanics (health, press,
// contest, digest heal, defeat throw-up) are layered by this module.
#include "pc_p2_giant_breadbug_actor.h"
#include "pc_p2_animation.h"
#include "pc_p2_purple.h"
#include "pc_bbft.h"
#include "teki.h"
#include "Teki.h"
#include "Pellet.h"
#include "Piki.h"
#include "Stickers.h"
#include "MapMgr.h"
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
// P2 Giant Breadbug parameters (scope ids 38/39/40/83; 39 alias and 83 helper stay non-spawnable).
const float GIANT_HEALTH=2000.0f,GIANT_CARRY_SPEED=45.0f,GIANT_PRESS_DAMAGE=100.0f;
const int GIANT_FREEZE_FRAMES=15; // 0.5 s at source 30 fps
struct Motion {int duration=0;std::vector<int> frames;std::vector<Shape*> shapes;};
struct Digested {int color;int type;};
struct Giant {
 unsigned id,nestId;unsigned started;int lastMotion=-1;bool logged=false;
 int lastState=-1;int freeze=0;bool deadLogged=false;bool healPending=false;
 Pellet* cargo=nullptr;std::vector<Digested> stomach;
};
struct Nest {unsigned id;BTeki* actor=nullptr;bool born=false;bool dead=false;};
std::map<BTeki*,Giant> giants;std::map<BTeki*,Nest> nests;
Motion motions[2];Shape* nestShape=nullptr;
void fail(){std::fputs("P2_GIANT_BREADBUG_ACTOR invalid profile/model\n",stderr);std::abort();}
Shape* load(const std::string& name){
 std::ifstream in("assets/dataDir/courses/pikmin2room/"+name,std::ios::binary|std::ios::ate);if(!in)fail();auto size=in.tellg();if(size<=0||size>16*1024*1024)fail();in.seekg(0);
 std::vector<unsigned char> bytes(size_t(size),0),resources;if(!in.read(reinterpret_cast<char*>(bytes.data()),size)||!p2animation::resources(bytes,resources))fail();
 Shape* shape=gameflow.loadShape(("courses/pikmin2room/"+name).c_str(),true);if(!shape)fail();
 for(int i=0;i<shape->mTexAttrCount;++i)if(shape->mTexAttrList[i].mTexture)shape->mTexAttrList[i].mTexture->attach();return shape;
}
int carriers(Pellet* pellet){
 Stickers stuckList(pellet);Iterator it(&stuckList);int count=0;CI_LOOP(it){if((*it)->isPiki())++count;}return count;
}
}
void pc_p2_giant_breadbug_actor_reset(){giants.clear();nests.clear();for(auto& motion:motions)motion=Motion{};nestShape=nullptr;}
static void defeat(BTeki* actor,Giant& giant);
void pc_p2_giant_breadbug_actor_forget(BTeki* actor){auto found=giants.find(actor);if(found!=giants.end())defeat(actor,found->second);giants.erase(actor);nests.erase(actor);}
void pc_p2_giant_breadbug_actor_setup(){
 pc_p2_giant_breadbug_actor_reset();if(!pc_pikipelago_room_preview())return;std::ifstream in("p2-giant-breadbug-actor.txt");if(!in)return;
 std::string word;if(!(in>>word)||word!="P2_GIANT_BREADBUG_ACTOR_1"||!tekiMgr)fail();
 for(int k=0;k<2;++k){int count;auto& motion=motions[k];if(!(in>>word>>motion.duration>>count)||word!=(k?"move":"wait")||motion.duration<2||motion.duration>10000||count<2||count>12)fail();
  for(int i=0;i<count;++i){int frame;if(!(in>>frame)||frame<0||frame>=motion.duration||(i&&frame<=motion.frames.back()))fail();motion.frames.push_back(frame);}
  if(motion.frames.front()!=0||motion.frames.back()!=motion.duration-1)fail();
 }
 int count;if(!(in>>count)||count<1||count>8)fail();
 std::map<unsigned,unsigned> wanted; // giant generator -> nest generator
 for(int i=0;i<count;++i){unsigned long long id,nest;if(!(in>>id>>nest)||id>0xffffffffULL||nest>0xffffffffULL||id==nest||!wanted.insert({unsigned(id),unsigned(nest)}).second)fail();}
 if(in>>word)fail();
 std::set<unsigned> foundGiants,foundNests;
 Iterator it(tekiMgr);CI_LOOP(it){BTeki* actor=static_cast<BTeki*>(*it);if(!actor||!actor->mGenerator)continue;unsigned id=actor->mGenerator->_70;
  auto match=wanted.find(id);
  if(match!=wanted.end()){
   if(actor->mTekiType!=TEKI_Collec||!foundGiants.insert(id).second)fail();
   actor->mHealth=actor->mMaxHealth=GIANT_HEALTH;
   giants.emplace(actor,Giant{id,match->second,SDL_GetTicks()});
   std::printf("P2_GIANT_BREADBUG_ACTOR_READY generator=%u nest=%u native_type=8 xyz=%.6f,%.6f,%.6f boss=1 bdt=empty_no_music threshold=at_or_above1 health=2000 carryspeed=45 pressdamage=100\n",id,match->second,actor->mSRT.t.x,actor->mSRT.t.y,actor->mSRT.t.z);
   continue;
  }
  for(const auto& pair:wanted)if(pair.second==id){
   if(actor->mTekiType!=TEKI_Hollec||!foundNests.insert(id).second)fail();
   nests.emplace(actor,Nest{id});
  }
 }
 if(foundGiants.size()!=wanted.size()||foundNests.size()!=wanted.size())fail();
 for(int k=0;k<2;++k)for(size_t i=0;i<motions[k].frames.size();++i){char name[80];std::snprintf(name,sizeof(name),"lane_ootake_%s1_%03u.mod",k?"move":"wait",unsigned(motions[k].frames[i]));motions[k].shapes.push_back(load(name));}
 nestShape=load("lane_nest_nest.mod");
}
bool pc_p2_giant_breadbug_actor_press(BTeki* actor,const TekiEvent& event){
 auto found=giants.find(actor);if(found==giants.end())return false;
 if(event.mEventType!=TekiEventType::Pressed||!actor->isAlive())return false;
 Creature* presser=event.mOther;
 if(!presser||!presser->isPiki())return false; // non-piki presses keep native handling
 Piki* piki=static_cast<Piki*>(presser);
 if(pc_p2_is_purple(piki)){
  actor->mHealth-=GIANT_PRESS_DAMAGE;actor->mVelocity=Vector3f(0,0,0);
  std::printf("P2_GIANT_PRESS generator=%u purple=1 damage=100 health=%.1f\n",found->second.id,actor->mHealth);
  if(actor->mHealth<=0.0f)defeat(actor,found->second); // lethal press: throw back digested treasure immediately (updateAI may pause once the death sequence starts)
 } else {
  std::printf("P2_GIANT_PRESS generator=%u purple=0 resisted=1 health=%.1f\n",found->second.id,actor->mHealth);
 }
 return true; // swallow the native P1 400-damage press event either way
}
static void defeat(BTeki* actor,Giant& giant){
 if(giant.deadLogged)return;giant.deadLogged=true;
 Vector3f nest=actor->getNestPosition();
 for(const auto& entry:nests)if(entry.second.id==giant.nestId){nest=entry.first->mSRT.t;break;} // throw back at the bound nest
 std::printf("P2_GIANT_DEFEATED generator=%u thrown_back=%zu\n",giant.id,giant.stomach.size());
 int i=0;for(const Digested& d:giant.stomach){
  if(!pelletMgr)break;Pellet* pellet=pelletMgr->newNumberPellet(d.color,d.type);if(!pellet)break;
  const float angle=float(i)*1.0471975511965976f;
  Vector3f spot(nest.x+40.0f*std::cos(angle),nest.y+5.0f,nest.z+40.0f*std::sin(angle));
  if(mapMgr)spot.y=mapMgr->getMinY(spot.x,spot.z,true)+5.0f;
  pellet->init(spot);pellet->startAI(0);++i;
 }
 if(i)std::printf("P2_GIANT_THROWUP generator=%u pellets=%d nest=%.3f,%.3f,%.3f\n",giant.id,i,nest.x,nest.y,nest.z);
 giant.stomach.clear();
}
void pc_p2_giant_breadbug_actor_tick(){
 if(giants.empty()&&nests.empty())return;
 for(auto& entry:nests){
  Nest& nest=entry.second;BTeki* actor=entry.first;
  if(!nest.born){nest.born=true;std::printf("P2_GIANT_NEST_BIRTH generator=%u xyz=%.3f,%.3f,%.3f\n",nest.id,actor->mSRT.t.x,actor->mSRT.t.y,actor->mSRT.t.z);}
  if(!nest.dead&&!actor->isAlive()){nest.dead=true;std::printf("P2_GIANT_NEST_DEATH generator=%u\n",nest.id);}
 }
 for(auto& entry:giants){
  Giant& giant=entry.second;BTeki* actor=entry.first;
  Pellet* held=actor->getCreaturePointer(2)&&actor->getCreaturePointer(2)->isObjType(OBJTYPE_Pellet)?static_cast<Pellet*>(actor->getCreaturePointer(2)):nullptr;
  if(held)giant.cargo=held;
  const int state=actor->mStateID;
  if(!held&&giant.cargo&&state!=5&&state!=6&&state!=7&&state!=8&&state!=9&&state!=10)giant.cargo=nullptr; // dropped/lost outside the carry-hide chain
  // PelletCarry contest: carriers >= (min+max)/2 steal the cargo back.
  if(held&&held->mConfig){
   const float strength=(held->mConfig->mCarryMinPikis()+held->mConfig->mCarryMaxPikis())*0.5f;
   const int n=carriers(held);
   if(float(n)>=strength){
    held->endStickTeki(actor);actor->clearCreaturePointer(2);actor->stopParticleGenerator(2);
    actor->mReturnStateID=state;actor->mStateID=3;actor->mIsStateReady=true; // resume wandering after losing the cargo
    giant.freeze=GIANT_FREEZE_FRAMES;giant.cargo=nullptr;
    std::printf("P2_GIANT_CONTEST_LOST generator=%u carriers=%d strength=%.1f freeze=0.5s\n",giant.id,n,strength);
   }
  }
  if(giant.freeze>0){--giant.freeze;actor->mVelocity=Vector3f(0,0,0);}
  if(state!=giant.lastState){
   if(state==8&&giant.cargo){ // went underground with cargo: digest it
    int color=giant.cargo->mConfig?giant.cargo->mConfig->mPelletColor():int(PELCOLOR_NULL);
    int type=giant.cargo->mConfig?giant.cargo->mConfig->mPelletType():0;
    giant.stomach.push_back(Digested{color,type});giant.healPending=true;
    std::printf("P2_GIANT_DIGEST generator=%u color=%d type=%d stomach=%zu\n",giant.id,color,type,giant.stomach.size());
    giant.cargo->endStickTeki(actor);actor->clearCreaturePointer(2);actor->stopParticleGenerator(2);
    giant.cargo->kill(false);giant.cargo=nullptr;
   }
   if(giant.healPending&&state==3){ // resurfaced to wander: hide-digest restores health
    giant.healPending=false;actor->mHealth=GIANT_HEALTH;
    std::printf("P2_GIANT_DIGEST_HEAL generator=%u health=%.1f\n",giant.id,actor->mHealth);
   }
   giant.lastState=state;
  }
  if(!actor->isAlive())defeat(actor,giant);
 }
}
bool pc_p2_giant_breadbug_actor_draw(BTeki* actor,Graphics& gfx,const Matrix4f& view){
 auto boundNest=nests.find(actor);
 if(boundNest!=nests.end()){
  if(!actor->isAlive()||!gfx.mCamera||!nestShape)return false;
  Matrix4f world,scaled;world.makeSRT(actor->mSRT.s,actor->mSRT.r,actor->mSRT.t);view.multiplyTo(world,scaled);
  nestShape->updateAnim(gfx,scaled,nullptr,nullptr);nestShape->drawshape(gfx,*gfx.mCamera,nullptr);
  return true;
 }
 auto found=giants.find(actor);if(found==giants.end()||!actor->isAlive()||!gfx.mCamera)return false;
 auto& giant=found->second;
 if(actor->mStateID==9){return true;} // hidden underground: draw nothing (P1 hides natively)
 const int kind=actor->mVelocity.x*actor->mVelocity.x+actor->mVelocity.z*actor->mVelocity.z>1.f?1:0;
 if(kind!=giant.lastMotion){giant.lastMotion=kind;giant.started=SDL_GetTicks();}
 auto& motion=motions[kind];const float frame=std::fmod(float(SDL_GetTicks()-giant.started)*.03f,float(motion.duration));size_t best=0;
 for(size_t i=1;i<motion.frames.size();++i)if(std::fabs(float(motion.frames[i])-frame)<std::fabs(float(motion.frames[best])-frame))best=i;
 Matrix4f world,scaled;world.makeSRT(Vector3f(actor->mSRT.s.x*2,actor->mSRT.s.y*2,actor->mSRT.s.z*2),actor->mSRT.r,actor->mSRT.t);
 view.multiplyTo(world,scaled);
 Shape* shape=motion.shapes[best];shape->updateAnim(gfx,scaled,nullptr,nullptr);shape->drawshape(gfx,*gfx.mCamera,nullptr);
 if(!giant.logged){std::printf("P2_GIANT_BREADBUG_ACTOR_DRAW generator=%u scale=2 texture_matrix_animation=gap_static_frames\n",giant.id);giant.logged=true;}
 return true;
}
