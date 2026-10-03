#include "pc_p2_original_shijimi_native.h"
#include "pc_p2_original_shijimi_state.h"
#include "pc_p2_original_shijimi_honey.h"
#include "pc_p2_shijimi_attachment_native.h"
#include "pc_p2_original_honey_native.h"
#include "pc_p2_original_pelplant_geometry.h"
#include "pc_p2_flyer_coll.h"
#include "teki.h"
#include "Graphics.h"
#include "Camera.h"
#include "MapMgr.h"
#include "PikiMgr.h"
#include "Piki.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "Stickers.h"
#include "Interactions.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <set>
#include <limits>
extern Matrix4f invCamMat;
namespace p2original { namespace shijimi {
namespace {
constexpr float tau=6.2831853071795864769f,pi=3.14159265358979323846f;
struct Heap{int previous;Heap():previous(gsys->setHeap(SYSHEAP_App)){}~Heap(){gsys->setHeap(previous);}};
bool fail(std::string& e,const char* message){e=message;return false;}
[[noreturn]] void refusal(const std::string& e){std::fprintf(stderr,"P2_ORIGINAL_SHIJIMI refusal: %s\n",e.c_str());std::abort();}
std::set<Native*>& instances(){static std::set<Native*> all;return all;}
const p2flyer::Sphere spheres[]={{"none","____",30,{0,0,0},-1},{"none","st__",20,{0,0,0},0}};
float angle(float a){while(a>pi)a-=tau;while(a<-pi)a+=tau;return a;}
float distance(const Vector3f& a,const Position& b){float x=a.x-b.x,z=a.z-b.z;return x*x+z*z;}
struct Track {
 BTeki* actor=nullptr;Child child;ActorState state;
 Position home,goal,fallStart;float pitch=0,pitchAmp=0,fallDir=0,remainder=0;
 bool published=false,dying=false,endKey=false,pendingKill=false,cullable=false;
 std::uint64_t nativeLifetime=0;
 std::unique_ptr<pelplant::Geometry> geometry;P2FlyerColl collision;
};
}
struct Native::Impl final:Engine,StateEngine {
 Scene& scene;ActorRegistry& registry;p2originalresource::honey::Manager& honeyManager;
 p2originalresource::Engine& rng;SourceBank bank;Shape* shape=nullptr;PlantGroups groups;
 std::map<Creature*,std::unique_ptr<Track>> tracks;bool ready=false;unsigned maxObjects=0;
 std::uint64_t nextLifetime=1;
 Impl(Scene& s,ActorRegistry& r,p2originalresource::honey::Manager& h,p2originalresource::Engine& random):scene(s),registry(r),honeyManager(h),rng(random){}
 Track* member(const Identity& id){for(auto& entry:tracks)if(entry.second->child.identity==id)return entry.second.get();return nullptr;}
 Track& track(const ActorState& a){auto* t=member(a.identity);if(!t)refusal("source77 state lost actual native body");return *t;}
 Track* leader(const Track& t){Identity id=t.child.identity;id.child=0;return member(id);}
 bool parent(const InstanceIdentity& id,unsigned source,std::string& e)override{return scene.parent(id,source,e);}
 bool emission(const Group& g,std::string& e)override{return scene.emission(g,e);}
 bool managerAvailable()const override{return ready;}
 float randFloat()override{return rng.randFloat();}
 void discardRand()override{scene.discardRand();}
 bool birth(Child& child,void*& out,std::string& e)override{
  out=nullptr;if(!ready)return fail(e,"source77 raw birth lacks admitted native resources");Heap heap;
  if(member(child.identity))return fail(e,"source77 manager duplicate actual child");
  if(tracks.size()>=maxObjects){e.clear();return true;}
  if(nextLifetime==std::numeric_limits<std::uint64_t>::max())return fail(e,"source77 native incarnation capacity exhausted");
  auto* actor=tekiMgr->newTeki(TEKI_Palm);if(!actor){e.clear();return true;}
  auto t=std::make_unique<Track>();t->actor=actor;t->child=child;t->state.identity=child.identity;t->state.leader=child.identity.child==0;t->nativeLifetime=nextLifetime++;
  tracks.emplace(actor,std::move(t));auto& body=*tracks.at(actor);out=actor;
  // Source setParameters consumes the scale roll even with min=max=1.
  (void)rng.randFloat();
  actor->clearTekiOptions();actor->clearCreaturePointers();actor->mTekiShape=tekiMgr->getTekiShapeObject(TEKI_Palm);
  actor->mTekiAnimator->init(&actor->mTekiShape->mAnimContext,actor->mTekiShape->mAnimMgr,tekiMgr->mMotionTable);
  actor->mDeadState=actor->mStateID=actor->mDamageCount=0;actor->_3A4=0;actor->mStoredDamage=0;actor->mPellet=nullptr;actor->mGenerator=nullptr;
  for(int i=0;i<4;++i)actor->mParticleGenerators[i]=nullptr;
  actor->mSRT.t.set(child.position.x,child.position.y,child.position.z);actor->mSRT.s.set(1,1,1);actor->mFaceDirection=child.facing;actor->mSRT.r.set(0,child.facing,0);
  actor->mVelocity.set(0,0,0);actor->mVolatileVelocity.set(0,0,0);actor->mTargetVelocity.set(0,0,0);actor->mHealth=actor->mMaxHealth=200;
  actor->mCollisionRadius=30;actor->mSize=30;actor->mGroundTriangle=nullptr;
  actor->setCreatureFlag(CF_IsAiDisabled);actor->resetCreatureFlag(CF_DisableMovement);actor->setCreatureFlag(CF_IsFlying);
  for(unsigned option:{BTeki::TEKI_OPTION_VISIBLE,BTeki::TEKI_OPTION_ATARI,BTeki::TEKI_OPTION_ALIVE,BTeki::TEKI_OPTION_SHAPE_VISIBLE,BTeki::TEKI_OPTION_INVINCIBLE})actor->setTekiOption(option);
  actor->clearTekiOption(BTeki::TEKI_OPTION_ORGANIC);actor->clearTekiOption(BTeki::TEKI_OPTION_GRAVITATABLE);
  body.geometry=std::make_unique<pelplant::Geometry>(*shape);
  if(!body.collision.bind(actor,spheres,2))return fail(e,"source77 actual stickable collider allocation failed");
  e.clear();return true;
 }
 bool init(Child& child,void* object,void* actualLeader,std::string& e)override{
  auto i=tracks.find(static_cast<Creature*>(static_cast<BTeki*>(object)));if(i==tracks.end())return fail(e,"source77 init lost raw allocation");auto& t=*i->second;
  auto* l=leader(t);if(!l||l->actor!=actualLeader)return fail(e,"source77 init has foreign group leader");
  t.child=child;t.child.born=t.child.initialized=true;t.home=child.position;t.goal=child.position;t.pitch=rng.randFloat();t.pitchAmp=0;t.fallDir=0;
  const float frame=8*rng.randFloat();if(!bank.motion(t.actor,2,frame,t.geometry->shape,e)||!follow(t,e))return false;
  if(!scene.born(t.actor,child.identity,e))return false;t.published=true;e.clear();return true;
 }
 bool leaderInit(Child&,void* object,std::string& e)override{auto i=tracks.find(static_cast<BTeki*>(object));if(i==tracks.end())return fail(e,"source77 leaderInit lost actual body");return leaderInit(i->second->state,e);}
 bool leaderColor(Child& child,void* object,std::string& e)override{auto i=tracks.find(static_cast<BTeki*>(object));if(i==tracks.end())return fail(e,"source77 leader color lost actual body");i->second->child.color=child.color;e.clear();return true;}
 bool appear(Child& child,void* object,std::string& e)override{auto i=tracks.find(static_cast<BTeki*>(object));if(i==tracks.end())return fail(e,"source77 appearance lost actual body");i->second->child.appearance=child.appearance;return scene.appear(i->first,child.appearance,e);}
 bool abort(const Group& group,std::string& e)override{std::vector<Creature*> actual;for(const auto& pair:tracks)if(pair.second->child.identity.plant==group.plant)actual.push_back(pair.first);for(auto* body:actual)if(!remove(body,e))return false;e.clear();return true;}
 bool sprayMade(Color color)const override{return rng.sprayMade(color==Color::Red?p2originalresource::HoneyKind::Spicy:p2originalresource::HoneyKind::Bitter);}
 bool honey(const Child& child,const Position& position,const Position& velocity,bool& born,std::string& e)override{Creature* actual=nullptr;if(!birthHoney(child,position,velocity,honeyManager,rng,actual,e))return false;born=actual!=nullptr;return true;}
 bool follow(Track& t,std::string& e){
  Matrix4f root,joint;root.makeSRT(t.actor->mSRT.s,Vector3f(0,t.actor->mFaceDirection,0),t.actor->mSRT.t);if(!bank.joint0(t.actor,root,joint,e))return false;
  Matrix4f cameraRotation,rotation;cameraRotation.makeIdentity();
  for(int r=0;r<3;++r)for(int c=0;c<3;++c)cameraRotation.mMtx[r][c]=invCamMat.mMtx[c][r];
  rotation=joint;rotation.mMtx[0][3]=rotation.mMtx[1][3]=rotation.mMtx[2][3]=0;
  Matrix4f attachment;cameraRotation.multiplyTo(rotation,attachment);
  for(int n=0;n<2;++n){auto* part=t.collision.part(n);if(!part)return fail(e,"source77 live collision part missing");part->mCentre.set(joint.mMtx[0][3],joint.mMtx[1][3],joint.mMtx[2][3]);part->mRadius=spheres[n].radius;part->mJointMatrix=attachment;}
  t.actor->mGrid.updateGrid(t.actor->mSRT.t);t.actor->mGrid.updateAIGrid(t.actor->mSRT.t,false);return true;
 }
 void walk(Track& t,const Position& goal,float speed,float factor=.2f,float maxAngle=15){
  float desired=std::atan2(goal.x-t.actor->mSRT.t.x,goal.z-t.actor->mSRT.t.z);float delta=angle(desired-t.actor->mFaceDirection);
  delta=std::max(-maxAngle*pi/180,std::min(maxAngle*pi/180,delta*factor));t.actor->mFaceDirection=angle(t.actor->mFaceDirection+delta);t.actor->mSRT.r.y=t.actor->mFaceDirection;
  t.actor->mTargetVelocity.x=speed*std::sin(t.actor->mFaceDirection);t.actor->mTargetVelocity.z=speed*std::cos(t.actor->mFaceDirection);
 }
 bool trace(Track& t,std::string& e){auto* l=leader(t);if(!l){e.clear();return true;}const auto& p=l->actor->mSRT.t;float height=(t.actor->mSRT.t.y-p.y)*4;float factor=rng.randFloat();if(height>0)factor=-factor;t.goal={p.x+factor*height,p.y+10*factor,p.z+factor*height};return true;}
 bool leaderInit(ActorState& a,std::string& e)override{auto& t=track(a);t.actor->clearTekiOption(BTeki::TEKI_OPTION_ATARI);e.clear();return true;}
 bool nearestPikmin(const ActorState& a)override{const auto& t=track(a);if(!pikiMgr)return false;Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(!p||!p->isAlive())continue;const auto pos=p->getPosition();if(std::fabs(pos.y-t.actor->mSRT.t.y)<=150&&distance(pos,{t.actor->mSRT.t.x,t.actor->mSRT.t.y,t.actor->mSRT.t.z})<180*180)return true;}return false;}
 bool leaderWaiting(const ActorState& a)override{auto* l=leader(track(a));return l&&l->state.phase==Phase::Wait;}
 bool nextGoal(ActorState& a,std::string& e)override{auto& t=track(a);if(!a.leader&&a.phase==Phase::Fly&&a.flyTime<125&&leader(t))return trace(t,e);float radius=100*(.5f*rng.randFloat()+.5f);float theta=tau*rng.randFloat();t.goal={t.home.x+radius*std::sin(theta),t.home.y+50*std::sin(theta),t.home.z+radius*std::cos(theta)};e.clear();return true;}
 bool fly(ActorState& a,std::string& e)override{auto& t=track(a);if(!a.leader)t.cullable=true;t.pitch+=.02f;t.actor->mSRT.t.y+=t.pitchAmp*2;if(t.pitch>1)t.pitch-=1;t.actor->mVelocity.y=0;if(distance(t.actor->mSRT.t,t.goal)<1000)return nextGoal(a,e);walk(t,t.goal,150);t.actor->mSRT.t.y+=.01f*(t.goal.y-t.actor->mSRT.t.y);e.clear();return true;}
 bool fade(ActorState& a,std::string& e)override{return scene.fade(track(a).actor,e);}
 bool fallInit(ActorState& a,std::string& e)override{auto& t=track(a);t.actor->resetCreatureFlag(CF_IsFlying);t.actor->mTargetVelocity.y=-20;t.fallStart={t.actor->mSRT.t.x,t.actor->mSRT.t.y,t.actor->mSRT.t.z};e.clear();return true;}
 bool fall(ActorState& a,std::string& e)override{auto& t=track(a);if(!a.verticalFall){t.fallDir+=.3f;if(t.fallDir>tau)t.fallDir-=tau;float wave=std::sin(t.fallDir);t.actor->mSRT.t.x=t.fallStart.x+5*wave;t.actor->mSRT.t.z=t.fallStart.z+2.5f*wave;t.actor->mSRT.t.y+=wave;}else t.actor->mVelocity.x=t.actor->mVelocity.z=0;t.actor->mVelocity.y=std::max(-70.f,t.actor->mVelocity.y);e.clear();return true;}
 bool fallEnd(const ActorState& a)override{auto& t=track(a);return t.actor->mGroundTriangle||(mapMgr&&t.actor->mSRT.t.y<mapMgr->getMinY(t.actor->mSRT.t.x,t.actor->mSRT.t.z,true)+10);}
 bool deadInit(ActorState& a,std::string& e)override{auto& t=track(a);t.actor->clearTekiOption(BTeki::TEKI_OPTION_ALIVE);t.actor->resetCreatureFlag(CF_IsFlying);t.actor->mVelocity.set(0,0,0);t.actor->mTargetVelocity.set(0,0,0);t.endKey=false;return bank.motion(t.actor,1,0,t.geometry->shape,e);}
 bool deadEndKey(const ActorState& a)override{return track(a).endKey;}
 bool drop(ActorState& a,std::string& e)override{auto& t=track(a);return groups.drop(a.identity,{t.actor->mSRT.t.x,t.actor->mSRT.t.y,t.actor->mSRT.t.z},t.actor->mFaceDirection,false,*this,e);}
 bool leaveInit(ActorState& a,std::string& e)override{auto& t=track(a);t.cullable=true;if(a.leader){auto* n=naviMgr?naviMgr->getActiveNavi():nullptr;if(n){const auto p=n->getPosition();Position goal{p.x-500*std::sin(n->mFaceDirection),p.y,p.z-500*std::cos(n->mFaceDirection)};walk(t,goal,120,1,180);t.actor->mVelocity=t.actor->mTargetVelocity;}}else return trace(t,e);e.clear();return true;}
 bool leave(ActorState& a,std::string& e)override{auto& t=track(a);auto* l=leader(t);if(!a.leader&&l&&l->actor->isAlive()){if(distance(t.actor->mSRT.t,t.goal)<1000&&!trace(t,e))return false;walk(t,t.goal,150);t.actor->mSRT.t.y+=.02f*(t.goal.y-t.actor->mSRT.t.y);t.pitch+=.02f;t.actor->mSRT.t.y+=t.pitchAmp*2;if(t.pitch>1)t.pitch-=1;}else{float rise=t.pitchAmp<0?-1.f:3.f;if(t.pitch>1)t.pitch=0;t.pitch+=t.pitchAmp<0?.05f:.01f;t.actor->mSRT.t.y+=rise*t.pitchAmp;}e.clear();return true;}
 bool stuckPiki(const ActorState& a)override{for(auto* p=track(a).actor->mStickListHead;p;p=p->mNextSticker)if(p->isPiki())return true;return false;}
 bool latchEffectAndShrink(ActorState& a,std::string& e)override{auto& t=track(a);if(!scene.latch(t.actor,t.child.color,e))return false;for(auto* p=t.actor->mStickListHead;p;p=p->mNextSticker)if(p->isPiki())p->mAttachPosition.multiply(.1f);return true;}
 bool leaderLeaving(const ActorState& a)override{auto* l=leader(track(a));return l&&l->state.phase==Phase::Leave;}
 bool outsideTerritory(const ActorState& a)override{auto& t=track(a);return std::fabs(t.actor->mSRT.t.x-t.home.x)>750||std::fabs(t.actor->mSRT.t.z-t.home.z)>750;}
 bool kill(ActorState& a,std::string& e)override{track(a).pendingKill=true;e.clear();return true;}
 bool remove(Creature* actor,std::string& e,bool killBody=true){
  auto i=tracks.find(actor);if(i==tracks.end()){e.clear();return true;}auto& t=*i->second;
  if(t.published&&!scene.retired(actor,t.child.identity,e))return false;
  if(t.published){std::string journalError;if(!groups.retire(t.child.identity,journalError)&&!journalError.empty())return fail(e,"source77 retirement journal lost actual child");}
  auto* l=leader(t);if(!t.state.leader&&l)--l->state.groupCount;
  std::vector<Creature*> stuck;for(auto* p=actor->mStickListHead;p;p=p->mNextSticker)if(p->isPiki())stuck.push_back(p);
  for(auto* p:stuck){InteractFlick flick(actor,0,0,-1000);p->stimulate(flick);}
  scene.forget(actor);bank.forget(actor);t.collision.detach(t.actor);t.dying=true;if(killBody)actor->kill(false);tracks.erase(actor);e.clear();return true;
 }
};
Native::Native(Scene& s,ActorRegistry& r,p2originalresource::honey::Manager& h,p2originalresource::Engine& rng):m(std::make_unique<Impl>(s,r,h,rng)){instances().insert(this);}
Native::~Native(){if(!m->tracks.empty())refusal("source77 manager destroyed before actual body cleanup");instances().erase(this);}
bool Native::prepare(std::string& e){if(!m->tracks.empty())return fail(e,"source77 preparation with live bodies");m->ready=false;if(!gsys||!tekiMgr||!mapMgr||!tekiMgr->hasModel(TEKI_Palm))return fail(e,"source77 native manager/chassis/floor unavailable");Heap heap;auto* chassis=tekiMgr->getTekiShapeObject(TEKI_Palm);if(!chassis||!chassis->mShape||!chassis->mAnimMgr||!m->bank.prepare(m->shape,e)||!m->scene.prepare(e))return false;m->maxObjects=m->scene.cave()?25u:10u;m->ready=true;e.clear();return true;}
bool Native::touched(Creature* plant,unsigned source,const Position& position,float height,std::string& e){unsigned actualSource=0,token=0;InstanceIdentity id;if(!m->registry.query(plant,actualSource,token,&id)||actualSource!=source||!token)return fail(e,"source77 touch lacks actual plant registry binding");Group result;if(!m->groups.touch(id,source,position,height,*m,result,e))return false;Identity leader{id,0,0};if(auto* t=m->member(leader))t->state.groupCount=int(result.sourceGroupCount);return true;}
bool Native::owns(const Creature* actor)const{return m->tracks.count(const_cast<Creature*>(actor))!=0;}
bool Native::captureGenPikiAttachments(Creature* actor,const AttachmentAuthority& authority,GenPikiStickerCapture& out,std::string& e)const{
#if !defined(PIKMIN_ORIGINAL_SENTINEL_ATTACHMENTS) || !PIKMIN_ORIGINAL_SENTINEL_ATTACHMENTS
 (void)actor;(void)authority;(void)out;
 return fail(e,"source77 attachment consumer is not linked with actual party SDK owner");
#else
 auto i=m->tracks.find(actor);if(i==m->tracks.end())return fail(e,"source77 attachment capture requires actual owned body");
 const Identity identity=i->second->child.identity;const auto lifetime=i->second->nativeLifetime;auto* part=i->second->collision.part(1);
 const auto current=[&](){auto found=m->tracks.find(actor);return found!=m->tracks.end()&&m->ready&&found->second->nativeLifetime==lifetime
  &&found->second->child.identity==identity&&found->second->published&&found->second->child.initialized&&!found->second->child.retired
  &&!found->second->dying&&!found->second->pendingKill&&found->second->collision.part(1)==part&&part;};
 if(!current())return fail(e,"source77 attachment capture requires current initialized body/collider");
 // The helper re-reads native topology after membership callbacks. Guard each
 // callback so it cannot continue reading a retired/reused source77 body.
 struct Guard final:AttachmentAuthority {
  const AttachmentAuthority& source;const decltype(current)& live;
  Guard(const AttachmentAuthority& s,const decltype(current)& l):source(s),live(l){}
  bool member(const OriginalPikiOrigin& p,std::string& error)const override{
   if(!live())return fail(error,"source77 owner changed before party authority callback");
   if(!source.member(p,error))return false;
   return live()||fail(error,"source77 owner changed during party authority callback");
  }
 } guarded(authority,current);
 GenPikiStickerCapture next;next.owner=identity;
 if(!captureGenPikiStickers(actor,part,guarded,next.stickers,e)||!current())return fail(e,"source77 attachment capture lost current owner/party relationship");
 out=std::move(next);e.clear();return true;
#endif
}
bool Native::tick(BTeki* actor,float seconds,std::string& e){
 auto i=m->tracks.find(actor);if(i==m->tracks.end())return false;if(!std::isfinite(seconds)||seconds<0||seconds>2)return fail(e,"source77 invalid native delta");Heap heap;auto& t=*i->second;
 // Source culling suppresses FSM, animation-clock and physics updates.
 // Query the actual scene AILOD before advancing any of them.
 bool isCulled=false;if(!m->scene.culling(actor,t.cullable,isCulled,e))return false;
 if(isCulled&&t.cullable){if(!cluster(t.state,*m,e))return false;if(!t.pendingKill&&!culled(t.state,*m,e))return false;return t.pendingKill?m->remove(actor,e):true;}
 actor->Creature::update();std::vector<int> keys;if(!m->bank.advance(actor,t.geometry->shape,seconds,keys,e))return false;t.endKey=t.endKey||std::find(keys.begin(),keys.end(),1000)!=keys.end();
 t.remainder+=seconds*30;while(t.remainder>=1){t.remainder-=1;const Phase previous=t.state.phase;if(!update(t.state,*m,e))return false;if(previous!=Phase::Fly&&t.state.phase==Phase::Fly)t.cullable=false;if(t.pendingKill)return m->remove(actor,e);t.pitchAmp=std::sin(tau*t.pitch);if(!simulate(t.state,*m,e))return false;}
 // EnemyBase ground/flying acceleration: dt / literal s003=.1. Ground
 // retains current vertical speed and applies actual P2 gravity560.
 const float acceleration=seconds/.1f;
 actor->mVelocity.x+=(actor->mTargetVelocity.x-actor->mVelocity.x)*acceleration;
 actor->mVelocity.z+=(actor->mTargetVelocity.z-actor->mVelocity.z)*acceleration;
 if(t.state.phase==Phase::Fall||t.state.phase==Phase::Dead)actor->mVelocity.y-=560*seconds;
 else if(t.state.phase!=Phase::Dead)actor->mVelocity.y+=(actor->mTargetVelocity.y-actor->mVelocity.y)*acceleration;
 actor->moveNew(seconds,false);if(!m->tracks.count(actor))return true;if(!m->follow(t,e))return false;
 if(!cluster(t.state,*m,e))return false;return t.pendingKill?m->remove(actor,e):true;
}
bool Native::draw(BTeki* actor,Graphics& gfx,const Matrix4f& view){auto i=m->tracks.find(actor);if(i==m->tracks.end())return false;if(i->second->state.leader||!gfx.mCamera)return true;auto& geometry=i->second->geometry->shape;gfx.useMatrix(Matrix4f::ident,0);geometry.updateAnim(gfx,view,nullptr,actor);geometry.drawshape(gfx,*gfx.mCamera,nullptr);return true;}
bool Native::collision(BTeki* actor,Creature*,std::string& e){if(!owns(actor))return false;e.clear();return true;}
bool Native::wall(BTeki* actor,const Position& normal,std::string& e){auto i=m->tracks.find(actor);if(i==m->tracks.end())return false;auto& t=*i->second;if(t.state.phase==Phase::Fall)t.state.verticalFall=true;else t.goal={actor->mSRT.t.x+100*normal.x,actor->mSRT.t.y,actor->mSRT.t.z+100*normal.z};e.clear();return true;}
bool Native::consume(const p2originalresource::ChildIdentity& child,std::string& e){Identity id;return honeyOwner(child,id,e)&&m->groups.consume(id,e);}
bool Native::cleanup(std::string& e){std::vector<Creature*> actual;for(const auto& pair:m->tracks)actual.push_back(pair.first);for(auto* body:actual)if(!m->remove(body,e))return false;e.clear();return true;}
void Native::forget(Creature* actor){auto i=m->tracks.find(actor);if(i==m->tracks.end()||i->second->dying)return;std::string e;if(!m->remove(actor,e,false))refusal(e);}
PlantGroups& Native::journal(){return m->groups;}
} }
namespace {
p2original::shijimi::Native* owner(const Creature* c){for(auto* n:p2original::shijimi::instances())if(n->owns(c))return n;return nullptr;}
void checked(bool result,const std::string& e){if(!result)p2original::shijimi::refusal(e);}
}
bool pc_p2_original_shijimi_owned(const Creature* actor){return owner(actor)!=nullptr;}
bool pc_p2_original_shijimi_update(BTeki* actor){auto* n=owner(actor);if(!n)return false;std::string e;checked(n->tick(actor,gsys->getFrameTime(),e),e);return true;}
bool pc_p2_original_shijimi_draw(BTeki* actor,Graphics& g,const Matrix4f& view){auto* n=owner(actor);return n&&n->draw(actor,g,view);}
bool pc_p2_original_shijimi_refresh(BTeki* actor,Graphics& g){auto* n=owner(actor);if(!n)return false;if(!g.mCamera)return true;Matrix4f root,view;root.makeSRT(actor->mSRT.s,Vector3f(0,actor->mFaceDirection,0),actor->mSRT.t);g.mCamera->mLookAtMtx.multiplyTo(root,view);return n->draw(actor,g,view);}
bool pc_p2_original_shijimi_collision(BTeki* actor,Creature* collider){auto* n=owner(actor);if(!n)return false;std::string e;checked(n->collision(actor,collider,e),e);return true;}
bool pc_p2_original_shijimi_wall(BTeki* actor,float x,float y,float z){auto* n=owner(actor);if(!n)return false;std::string e;checked(n->wall(actor,{x,y,z},e),e);return true;}
void pc_p2_original_shijimi_forget(BTeki* actor){auto* n=owner(actor);if(n)n->forget(actor);}
