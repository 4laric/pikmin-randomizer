// P2 small Breadbug appearance on an opted-in P1 Collec. P1 gameplay remains authoritative.
#include "pc_p2_breadbug_actor.h"
#include "pc_p2_breadbug_contest_host.h"
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
// Small Breadbug (PanModoki, source 38) contest-consumer parameters. The P1
// TEKI_Collec host drags at carry power 2, so the squad needs two Pikmin to
// out-pull it (maxThreshold=2); identity uses lane-06's onion:p2:38:<stage>.
const unsigned CONTEST_SOURCE_ID=38;
const int CONTEST_STAGE=0;      // preview arena placeholder; campaign stage is lane-06/integration
const int CONTEST_MIN_THRESHOLD=1,CONTEST_MAX_THRESHOLD=2;
const float CONTEST_FREEZE_SECONDS=0.5f;
const int CONTEST_REQUIRED_CARRIERS=1,CONTEST_MAX_CARRIERS=0;
struct Motion {int duration=0;std::vector<int> frames;std::vector<Shape*> shapes;};
struct BreadbugProxyActor {unsigned id;unsigned started;int lastMotion=-1;bool logged=false;int loggedCargo=-99;bool lastHeld=false;int lastCarriers=-1;int contestHandle=0;int lastOutcome=-1;bool ownerDiedLogged=false;bool deathLogged=false;};
std::map<BTeki*,BreadbugProxyActor> actors;Motion motions[2];
// Generator ids the last setup() opted in. File-static (not setup-local) so the
// per-tick rebirth scan can re-register a generator rebirth without a manager
// recreation; cleared by reset() so no stale stage identity survives teardown.
std::set<unsigned> wantedIds;
Motion cargoMotions[2];bool cargoEnabled=false;int probeCarriers=-1;
const char* reasonName(int r){switch(r){case 1:return "interrupted";case 2:return "owner_died";case 3:return "carrier_lost";case 4:return "timeout";case 5:return "revisit";default:return "none";}}
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
void pc_p2_breadbug_actor_reset(){actors.clear();wantedIds.clear();for(auto& motion:motions)motion=Motion{};for(auto& motion:cargoMotions)motion=Motion{};cargoEnabled=false;probeCarriers=-1;pc_p2_breadbug_contest_reset_all();}
void pc_p2_breadbug_actor_forget(BTeki* actor){
 auto found=actors.find(actor);if(found==actors.end())return;
 auto& state=found->second;
 // Lifecycle observability: the real death funnel (BTeki::doKill) and pool
 // slot reuse (TekiMgr::newTeki) both pass through here. dead_state tells
 // them apart: >=1 is the death funnel, 0 is slot reuse of a live actor.
 std::printf("P2_BREADBUG_ACTOR_FORGET generator=%u had_handle=%d dead_state=%d\n",state.id,int(state.contestHandle!=0),actor->mDeadState);
 if(state.contestHandle){if(!state.ownerDiedLogged)pc_p2_breadbug_contest_owner_died(state.contestHandle);pc_p2_breadbug_contest_destroy(state.contestHandle);state.contestHandle=0;} // no handle leak on despawn
 actors.erase(found);
}
void pc_p2_breadbug_actor_probe_carriers(int count){
 probeCarriers=count;
 if(count>=0){
  // The labelled injection is confessed by the module itself, not the fixture, so
  // the validator can trust the confession without trusting the driver.
  for(auto& entry:actors){
   std::printf("P2_BREADBUG_CONTEST_PROBE generator=%u carriers=%d injected=1\n",entry.second.id,count);
  }
 }
}
void pc_p2_breadbug_actor_probe_revisit(){
 for(auto& entry:actors){
  auto& state=entry.second;
  const bool hadHandle=state.contestHandle!=0;
  if(hadHandle){pc_p2_breadbug_contest_revisit(state.contestHandle);pc_p2_breadbug_contest_destroy(state.contestHandle);} // no Stolen-outcome handle leak
  std::printf("P2_BREADBUG_REVISIT generator=%u rearmed=%d\n",state.id,int(hadHandle));
  state.contestHandle=0;state.lastOutcome=-1;state.ownerDiedLogged=false;
 }
}
void pc_p2_breadbug_actor_setup(){
 pc_p2_breadbug_actor_reset();if(!pc_pikipelago_room_preview())return;std::ifstream in("p2-breadbug-actor.txt");if(!in)return;
 std::string word;if(!(in>>word)||word!="P2_BREADBUG_ACTOR_PROXY_1"||!tekiMgr)fail();
 for(int k=0;k<2;++k){int count;auto& motion=motions[k];if(!(in>>word>>motion.duration>>count)||word!=(k?"move":"wait")||motion.duration<2||motion.duration>10000||count<2||count>12)fail();
  for(int i=0;i<count;++i){int frame;if(!(in>>frame)||frame<0||frame>=motion.duration||(i&&frame<=motion.frames.back()))fail();motion.frames.push_back(frame);}
  if(motion.frames.front()!=0||motion.frames.back()!=motion.duration-1)fail();
 }
 int count;if(!(in>>count)||count<1||count>8)fail();wantedIds.clear();
 for(int i=0;i<count;++i){unsigned long long id;int kind;if(!(in>>id>>kind)||id>0xffffffffULL||kind!=TEKI_Collec||!wantedIds.insert(unsigned(id)).second)fail();}
 if(in>>word)fail();std::set<unsigned> found;
 Iterator it(tekiMgr);CI_LOOP(it){Teki* actor=static_cast<Teki*>(*it);if(!actor||!actor->mGenerator)continue;unsigned id=actor->mGenerator->_70;if(!wantedIds.count(id))continue;
  if(actor->mTekiType!=TEKI_Collec||!found.insert(id).second)fail();actors.emplace(actor,BreadbugProxyActor{id,SDL_GetTicks()});
  std::printf("P2_BREADBUG_ACTOR_READY generator=%u native_type=8 xyz=%.6f,%.6f,%.6f behavior=P1_Collec_proxy\n",id,actor->mSRT.t.x,actor->mSRT.t.y,actor->mSRT.t.z);
 }
 if(found!=wantedIds)fail();
 if(!pc_p2_breadbug_contest_open("p2-breadbug-contest-receipts.txt"))fail();
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
 const float now=SDL_GetTicks()*0.001f;
 for(auto& entry:actors){
  BTeki* actor=entry.first;auto& state=entry.second;
  Pellet* held=actor->getCreaturePointer(2)&&actor->getCreaturePointer(2)->isObjType(OBJTYPE_Pellet)?static_cast<Pellet*>(actor->getCreaturePointer(2)):nullptr;
  if(actor->mDeadState || !actor->isAlive()){
   if(!state.deathLogged){
    state.deathLogged=true;
    // Residual death observation: the real funnel (BTeki::doKill) erases this
    // entry through forget() before the next tick, so reaching here means
    // death bypassed doKill (labelled injection) or forget has not run yet.
    // corpse reads the dieSoon() product (becomePellet sets mPellet for
    // LeaveCorpse types such as Collec); held reads the pre-release pointer.
    Creature* deadHeld=actor->getCreaturePointer(2);
    const int heldIsPellet=deadHeld&&deadHeld->isObjType(OBJTYPE_Pellet)?1:0;
    std::printf("P2_BREADBUG_ACTOR_DEATH generator=%u corpse=%d held=%d\n",state.id,int(actor->mPellet!=nullptr),heldIsPellet);
   }
   if(state.contestHandle&&!state.ownerDiedLogged){
    state.ownerDiedLogged=true;
    if(held){held->endStickTeki(actor);}actor->clearCreaturePointer(2);actor->stopParticleGenerator(2);
    pc_p2_breadbug_contest_owner_died(state.contestHandle);
    std::printf("P2_BREADBUG_OWNER_DIED generator=%u released=%d reason=OwnerDied\n",state.id,int(held!=nullptr));
    pc_p2_breadbug_contest_destroy(state.contestHandle);state.contestHandle=0;
   }
   continue;
  }
  if(held){
   // Legacy read-only observation marker FIRST, so the natural carriers value is
   // logged before the contest update samples it (the validator cross-checks each
   // pre-grant CONTEST_UPDATE carriers against this latest legacy carriers value).
   if(!state.lastHeld||carriers(held)!=state.lastCarriers){state.lastHeld=true;state.lastCarriers=carriers(held);std::printf("P2_BREADBUG_CONTEST generator=%u native_power=%g carriers=%d\n",state.id,PROXY_CARRY_POWER,state.lastCarriers);}
   if(!state.contestHandle){
    std::string sourceToken="nest:"+std::to_string(state.id);
    state.contestHandle=pc_p2_breadbug_contest_create((int)CONTEST_SOURCE_ID,CONTEST_STAGE,sourceToken.c_str(),CONTEST_MIN_THRESHOLD,CONTEST_MAX_THRESHOLD,CONTEST_FREEZE_SECONDS,CONTEST_REQUIRED_CARRIERS,CONTEST_MAX_CARRIERS);
    if(state.contestHandle){
     pc_p2_breadbug_contest_begin(state.contestHandle,now);state.lastOutcome=-1;state.ownerDiedLogged=false;
     std::printf("P2_BREADBUG_CONTEST_BEGIN generator=%u identity=%s max=%d\n",state.id,pc_p2_breadbug_contest_identity(state.contestHandle),CONTEST_MAX_THRESHOLD);
    }
   }
   if(state.contestHandle){
    const int n=(probeCarriers>=0)?probeCarriers:carriers(held);
    std::vector<std::string> tokenStore;std::vector<const char*> tokenPtrs;std::vector<int> strengths;
    for(int i=0;i<n;++i){tokenStore.push_back("piki:"+std::to_string(i));strengths.push_back(1);}
    for(auto& t:tokenStore)tokenPtrs.push_back(t.c_str());
    const int outcome=pc_p2_breadbug_contest_update(state.contestHandle,now,n?tokenPtrs.data():nullptr,n?strengths.data():nullptr,n);
    if(outcome!=state.lastOutcome){
     state.lastOutcome=outcome;
     const char* os=outcome==0?"held":(outcome==1?"stolen":"released");
     std::printf("P2_BREADBUG_CONTEST_UPDATE generator=%u carriers=%d outcome=%s\n",state.id,n,os);
      if(outcome==1){
       held->endStickTeki(actor);actor->clearCreaturePointer(2);actor->stopParticleGenerator(2);
       actor->mReturnStateID=actor->mStateID;actor->mStateID=3;actor->mIsStateReady=true; // resume wandering after losing the tug
       std::printf("P2_BREADBUG_CONTEST_STOLEN generator=%u carriers=%d released=1\n",state.id,n);
       std::string slot="g"+std::to_string(state.id);
       const int grant=pc_p2_breadbug_contest_grant(state.contestHandle,"p2-preview",slot.c_str(),"contest");
       if(grant==1)std::printf("P2_BREADBUG_CONTEST_GRANT generator=%u identity=%s granted=1\n",state.id,pc_p2_breadbug_contest_identity(state.contestHandle));
       else if(grant==2)std::printf("P2_BREADBUG_CONTEST_GRANT generator=%u identity=%s granted=0 duplicate=1\n",state.id,pc_p2_breadbug_contest_identity(state.contestHandle));
       pc_p2_breadbug_contest_destroy(state.contestHandle);state.contestHandle=0;state.lastOutcome=-1; // Stolen is terminal: the next grab starts a fresh tug
      }
     if(outcome==2){
      // Timeout/release is terminal for this contest; drop the handle so the next grab starts a fresh tug (the ledger keeps exactly-once durable).
      pc_p2_breadbug_contest_destroy(state.contestHandle);state.contestHandle=0;state.lastOutcome=-1;
     }
    }
   }
  } else {
   state.lastHeld=false;
   // Lost the cargo while the contest was still Held (delivered to its nest, or
   // the carriers were pulled off) — not a Stolen/timeout, which already destroy
   // their handle. Interrupt + destroy so the next grab begins a fresh tug.
   if(state.contestHandle){
    pc_p2_breadbug_contest_interrupt(state.contestHandle);
    const int reason=pc_p2_breadbug_contest_reason(state.contestHandle);
    std::printf("P2_BREADBUG_CONTEST_INTERRUPT generator=%u reason=%s\n",state.id,reasonName(reason));
    pc_p2_breadbug_contest_destroy(state.contestHandle);state.contestHandle=0;state.lastOutcome=-1;
   }
  }
 }
 // Natural re-entry scan: a generator rebirth after death is a live TEKI_Collec
 // carrying a wanted generator id that this registry no longer tracks LIVE.
 // (A dead entry persists in the map for LeaveCorpse deaths because no doKill
 // runs; only live bindings count.) Re-register it here so cleanup/re-entry
 // evidences without a manager recreation (no reset/setup call) and without
 // touching another family. Stale dead same-id entries are erased inside
 // (replaced_stale=1) so exactly one live binding results.
 size_t liveTracked=0;
 for(auto& entry:actors){BTeki* known=entry.first;if(known&&!known->mDeadState&&known->isAlive())++liveTracked;}
 if(liveTracked<wantedIds.size()&&tekiMgr){
  Iterator scan(tekiMgr);CI_LOOP(scan){
   Teki* cand=static_cast<Teki*>(*scan);
   if(!cand||!cand->mGenerator)continue;
   const unsigned id=cand->mGenerator->_70;
   if(!wantedIds.count(id))continue;
   if(cand->mTekiType!=TEKI_Collec)continue;
   if(cand->mDeadState||!cand->isAlive())continue;
   if(actors.find(cand)!=actors.end())continue;
   bool replaced=false,duplicate=false;
   for(auto jt=actors.begin();jt!=actors.end();){
    if(jt->second.id!=id){++jt;continue;}
    BTeki* old=jt->first;
    if(old&&!old->mDeadState&&old->isAlive()){duplicate=true;break;}
    jt=actors.erase(jt);replaced=true;
   }
   if(duplicate){std::printf("P2_BREADBUG_ACTOR_DUPLICATE generator=%u\n",id);continue;}
   actors.emplace(cand,BreadbugProxyActor{id,SDL_GetTicks()});
   std::printf("P2_BREADBUG_ACTOR_REBIRTH generator=%u native_type=8 xyz=%.6f,%.6f,%.6f replaced_stale=%d\n",id,cand->mSRT.t.x,cand->mSRT.t.y,cand->mSRT.t.z,int(replaced));
  }
 }
}
int pc_p2_breadbug_actor_tracked_count(){int n=0;for(auto& entry:actors){BTeki* actor=entry.first;if(actor&&!actor->mDeadState&&actor->isAlive())++n;}return n;}
bool pc_p2_breadbug_actor_is_tracked(BTeki* actor){return actor&&actors.find(actor)!=actors.end();}
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
