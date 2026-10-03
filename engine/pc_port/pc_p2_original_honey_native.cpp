#include "pc_p2_original_honey_native.h"
#include "pc_p2_original_pelplant_geometry.h"
#include "Creature.h"
#include "CreatureProp.h"
#include "CreatureCollPart.h"
#include "Collision.h"
#include "Graphics.h"
#include "Camera.h"
#include "Piki.h"
#include "PikiState.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviState.h"
#include "NaviMgr.h"
#include "PaniAnimator.h"
#include "PaniPikiAnimator.h"
#include "Msg.h"
#include "Interactions.h"
#include "CPlate.h"
#include "sysNew.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <set>
#include <functional>
namespace p2originalresource { namespace honey {
namespace {
bool fail(std::string& e,const char* why){e=why;return false;}
void require(bool ok,const std::string& e){if(!ok){std::fprintf(stderr,"P2_ORIGINAL_HONEY refusal: %s\n",e.c_str());std::abort();}}
bool same(const ChildIdentity& a,const ChildIdentity& b){return a==b;}
bool finite(P2EggVec3 p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);}
bool valid(const ChildIdentity& id){return validChildIdentity(id);}
std::set<const Creature*>& honeyBodies(){static std::set<const Creature*> all;return all;}
struct AppHeap {int previous;AppHeap():previous(gsys->setHeap(SYSHEAP_App)){}~AppHeap(){gsys->setHeap(previous);}};
}
class Actor final:public Creature {
public:
 Policy policy;ChildIdentity identity;Engine& rng;Services& services;
 Resources resource;std::unique_ptr<p2original::pelplant::Geometry> geometry;
 // External fixed arrays avoid CollInfo's otherwise unowned heap allocations.
 // Honey permits no stickers; the body is retained until receiver/search refs
 // retire before these actual source single-sphere parts are destroyed.
 CollInfo ownedCollision{0};CollPart ownedParts[10];u32 ownedIds[10]{};ObjCollInfo ownedNode;
 SearchData searchData[8];std::function<void(Creature*)> receiverContact;
 bool firstConsumption=false;unsigned references=0;
 Actor(CreatureProp& prop,const Resources& r,Services& s,Engine& random,const ChildOutcome& child,HoneyKind kind,bool birthRng=true)
 :Creature(&prop),identity(child.identity),rng(random),services(s),resource(r){
  init(Vector3f(child.position.x,child.position.y,child.position.z));
  mSearchBuffer.init(searchData,8);
  mObjType=OBJTYPE_NULL;mGenerator=nullptr;mHealth=1;mVelocity.set(child.velocity.x,child.velocity.y,child.velocity.z);
  mCollisionRadius=7.5f;mSRT.s.set(1.5f,1.5f,1.5f);mSRT.r.set(0,0,0);
  geometry=std::make_unique<p2original::pelplant::Geometry>(*r.sourceShape);
  ownedNode.mId.setID('hony');ownedNode.mCode.setID('____');ownedNode.mRadius=15;ownedNode.mCentrePosition.set(0,0,0);ownedNode.mJointIndex=0;
  geometry->shape.mCollisionInfo.mChild=&ownedNode;mCollInfo=&ownedCollision;mCollInfo->initInfo(&geometry->shape,ownedParts,ownedIds);mCollInfo->disableStick();
  if(auto* part=mCollInfo->getBoundingSphere()){part->mIsUpdateActive=false;part->mCentre=mSRT.t;part->mRadius=15;}
  // Exact ItemHoney init(nullptr): default type RNG draw before Egg overwrites.
  if(birthRng)(void)rng.randFloat();policy.kind=kind;
  float scale=kind==HoneyKind::Nectar?1.5f:1.75f;mSRT.s.set(scale,scale,scale);
  honeyBodies().insert(this);
 }
 ~Actor(){honeyBodies().erase(this);services.forget(*this);}
 bool isAlive()override{return policy.alive();}
 bool isVisible()override{return policy.alive();}
 bool isAtari()override{return policy.alive();}
 bool needFlick(Creature*)override{return false;}
 bool needShadow()override{return false;}
 bool isOrganic()override{return false;}
 float getBoundingSphereRadius()override{return 15;}
 float getCentreSize()override{return 15;}
 Vector3f getBoundingSphereCentre()override{return mSRT.t;}
 Vector3f getCentre()override{return mSRT.t;}
 bool followCollider(std::string& e){P2EggVec3 centre;if(!services.collisionCentre(*this,centre,e))return false;if(!finite(centre))return fail(e,"Honey source joint0 collider centre invalid");if(auto* part=mCollInfo->getBoundingSphere()){part->mCentre.set(centre.x,centre.y,centre.z);part->mRadius=15;}return true;}
 bool beginMotion(std::string& e){return services.motion(*this,policy.motion(),e)&&followCollider(e);}
 void bounceCallback()override{if(policy.bounce()){mVelocity.set(0,0,0);std::string e;require(beginMotion(e),e);services.presentation(*this,"PSSE_EV_WORK_HONEY_DROP/THoneydown");}}
 bool absorb(std::string& e){
  if(!policy.absorbable()){e.clear();return false;}
  if(!firstConsumption){if(!services.consumed(identity,e))return false;firstConsumption=true;}
  bool shrink=policy.phase==Phase::Shrink;policy.absorb();
  if(!shrink&&!beginMotion(e))return false;e.clear();return true;
 }
 void collisionCallback(immut CollEvent& c)override{
  if(!c.mCollider)return;auto* other=c.mCollider;bool touched=policy.jiggling;
  if(policy.contact(other->mVelocity.x,other->mVelocity.z,other->mObjType==OBJTYPE_Piki,other->mObjType==OBJTYPE_Navi,honeyBodies().count(other)!=0)){std::string e;require(beginMotion(e),e);}
  if(!touched&&policy.jiggling)services.presentation(*this,"PSSE_PL_TOUCH_HONEY");
  if(receiverContact)receiverContact(other);
 }
 void update()override{
  if(!isAlive())return;std::string e;float dt=gsys->getFrameTime();
  if(policy.phase==Phase::Fall){mVelocity.y-=dt*resource.gravity;moveNew(dt,false);}else mVelocity.set(0,0,0);
  // ItemHoney::doAI default CheckHellArg; Creature::checkHell 0x8013BC24.
  if(mSRT.t.y < -500.0f){kill(false);return;}
  mGrid.updateGrid(mSRT.t);mGrid.updateAIGrid(mSRT.t,false);
  std::vector<int> events;require(services.advance(*this,geometry->shape,dt,events,e),e);
  // Retail Bounce/Touch/Shrink react to every emitted source key event.
  for(int unused:events){(void)unused;if(policy.key()){if(!isAlive()){kill(false);return;}require(beginMotion(e),e);}}
  require(followCollider(e),e);
  // Use real native collider intersections. Creature::collisionCheck is private
  // and applies the P1 physical response; Honey source disables collision flick.
  // Deliver only actual contacts to our source FSM/receiver, never proximity.
  Iterator contacts(&mSearchBuffer);CI_LOOP(contacts){Creature* other=*contacts;if(!other||!other->isAlive()||!other->isAtari()||other->isGrabbed())continue;Vector3f delta;CollPart* ours=nullptr;CollPart* theirs=nullptr;bool hit=false;
   if(other->mCollInfo&&other->mCollInfo->hasInfo())hit=mCollInfo->checkCollision(other->mCollInfo,&ours,&theirs,delta);
   else {ours=mCollInfo->checkCollision(other,delta);hit=ours!=nullptr;}
   if(hit){CollEvent event(other,theirs,ours);collisionCallback(event);}
  }
 }
 void refresh(Graphics& gfx)override{
  if(!isAlive()||!gfx.mCamera)return;Matrix4f root,view;root.makeSRT(mSRT.s,Vector3f(0,0,0),mSRT.t);
  gfx.mCamera->mLookAtMtx.multiplyTo(root,view);gfx.useMatrix(Matrix4f::ident,0);geometry->shape.updateAnim(gfx,view,nullptr,this);geometry->shape.drawshape(gfx,*gfx.mCamera,nullptr);
 }
 void doKill()override{policy.phase=Phase::Dead;mHealth=0;mVelocity.set(0,0,0);}
};
HoneyKind kind(const Actor& a){return a.policy.kind;}
const ChildIdentity& identity(const Actor& a){return a.identity;}
P2EggVec3 position(const Actor& a){return {a.mSRT.t.x,a.mSRT.t.y,a.mSRT.t.z};}
float scale(const Actor& a){return a.mSRT.s.x;}
Phase phase(const Actor& a){return a.policy.phase;}
bool actorWorld(const Actor& a,Matrix4f& world,std::string& e){if(!finite(position(a))||!std::isfinite(scale(a))||scale(a)<=0)return fail(e,"Honey source world transform invalid");world.makeSRT(a.mSRT.s,Vector3f(0,0,0),a.mSRT.t);e.clear();return true;}
Shape& shape(Actor& a){return a.geometry->shape;}
Creature& creature(Actor& a){return a;}
struct Manager::Impl {
 Services& services;Resources resource;CreatureProp prop;bool ready=false,staged=false;
 std::vector<std::unique_ptr<Actor>> actors;
 std::vector<Snapshot> history;
 struct PikiReceiver final:public PikiState {
  Actor& target;Piki* piki;Drink drink;ReceiverClock clock;bool active=true,growing=false,skipWasSet=false;int growMotion=0;unsigned sourceMotion=0;
  PikiReceiver(Actor& a,Piki* p):PikiState(PIKISTATE_Absorb,"P2_HONEY_ABSORB"),target(a),piki(p){++target.references;}
  ~PikiReceiver(){--target.references;}
  void init(Piki* p)override{skipWasSet=p->isCreatureFlag(CF_SkipPhysicsAndCollision);p->setCreatureFlag(CF_SkipPhysicsAndCollision);p->turnTo(target.mSRT.t);p->startMotion(PaniMotionInfo(PIKIANIM_Mizunomi,p),PaniMotionInfo(PIKIANIM_Mizunomi));}
  void stop(Piki* p){p->mFSM->transit(p,PIKISTATE_Normal);}
  void grow(Piki* p){growing=true;mStateID=PIKISTATE_GrowUp;sourceMotion=target.rng.randFloat()>0.5f?1:2;growMotion=sourceMotion==1?PIKIANIM_GrowUp1:PIKIANIM_GrowUp2;clock.reset();drink.finishing=false;p->startMotion(PaniMotionInfo(growMotion,p),PaniMotionInfo(growMotion));}
  void exec(Piki* p)override{
   p->mVelocity.x=p->mVelocity.z=0;p->mTargetVelocity.set(0,0,0);
   const bool wasGrowing=growing;
   bool okay=clock.advance(target.resource.receiverClips[sourceMotion],gsys->getFrameTime()*30,drink.finishing,[&](int key){sourceKey(p,key);return active&&growing==wasGrowing;});
   require(okay,"Honey authored Piki receiver clock invalid");if(!active||growing!=wasGrowing||growing)return;
   if(drink.shouldAbsorb(target.isAlive())){std::string e;(void)target.absorb(e);require(e.empty(),e);drink.absorbedOnce();}
   drink.pikiTick();
  }
  void procAnimMsg(Piki*,MsgAnim*)override{} // native P1 motion has no mechanical authority
  void sourceKey(Piki* p,int key){
   if(growing){if(key==2&&p->mHappa!=Flower){p->setFlower(Flower);if(p->mMode==PikiMode::FormationMode&&p->mNavi&&p->mNavi->mPlateMgr)p->mNavi->mPlateMgr->changeFlower(p);}if(key==1000)stop(p);return;}
   if(key==0)drink.loopStart();
   else if(key==1&&drink.pikiLoopEnd(target.isAlive(),target.policy.phase==Phase::Shrink))p->mPikiAnimMgr.finishMotion(p);
   else if(key==1000){if(drink.absorbed)grow(p);else stop(p);}
  }
  void cleanup(Piki* p)override{active=false;if(!skipWasSet)p->resetCreatureFlag(CF_SkipPhysicsAndCollision);}
 };
 struct NaviReceiver final:public NaviState {
  Actor& target;Navi* navi;Services& services;Drink drink;ReceiverClock clock;bool active=true;unsigned captain=0;
  // Private instance state; not registered globally or used as a restore ID.
  NaviReceiver(Actor& a,Navi* n,Services& s,unsigned index):NaviState(NAVISTATE_Count),target(a),navi(n),services(s),captain(index){++target.references;}
  ~NaviReceiver(){--target.references;}
  void init(Navi* n)override{n->turnTo(target.mSRT.t);n->startMotion(PaniMotionInfo(PIKIANIM_Mizunomi,n),PaniMotionInfo(PIKIANIM_Mizunomi));services.camera(n,true);}
  void exec(Navi* n)override{
   n->mVelocity.x=n->mVelocity.z=0;n->mTargetVelocity.set(0,0,0);
   require(clock.advance(target.resource.receiverClips[3],gsys->getFrameTime()*30,drink.finishing,[&](int key){sourceKey(n,key);return active;}),"Honey authored Navi receiver clock invalid");if(!active)return;
   if(drink.shouldAbsorb(target.isAlive())){std::string e;(void)target.absorb(e);require(e.empty(),e);drink.absorbedOnce();}
  }
  void procAnimMsg(Navi*,MsgAnim*)override{}
  void sourceKey(Navi* n,int key){
   if(key==0)drink.loopStart();
   else if(key==1&&drink.naviLoopEnd(target.isAlive(),target.policy.phase==Phase::Shrink))n->mNaviAnimMgr.finishMotion(n);
   else if(key==1000){if(drink.absorbed){std::string e;require(services.sprayCompleted(target.identity,captain,target.policy.kind,e),e);}n->mStateMachine->transit(n,NAVISTATE_Walk);}
  }
  void cleanup(Navi* n)override{active=false;services.camera(n,false);}
 };
 std::vector<std::unique_ptr<PikiReceiver>> pikis;std::vector<std::unique_ptr<NaviReceiver>> navis;
 explicit Impl(Services& s):services(s){}
 Actor* find(const Creature* c)const{for(const auto& a:actors)if(a.get()==c)return a.get();return nullptr;}
 void reap(){pikis.erase(std::remove_if(pikis.begin(),pikis.end(),[](const auto& p){return !p->active;}),pikis.end());navis.erase(std::remove_if(navis.begin(),navis.end(),[](const auto& n){return !n->active;}),navis.end());}
};
Manager::Manager(Services& s):m(std::make_unique<Impl>(s)){}
Manager::~Manager(){if(!m->actors.empty()||!m->pikis.empty()||!m->navis.empty()){std::fprintf(stderr,"Honey manager destroyed before actual course cleanup\n");std::abort();}}
bool Manager::preflight(std::string& e){
 if(!m->actors.empty())return fail(e,"Honey preflight while source actors owned");
 if(!gsys)return fail(e,"Honey native system unavailable");Resources r;if(!m->services.resources(r,e)||!m->services.receiversReady(e))return false;
 if(!r.sourceShape||!p2original::pelplant::Geometry::admits(*r.sourceShape)||!r.collider||!std::isfinite(r.gravity)||r.gravity<=0)return fail(e,"Honey source model/collider/gravity unresolved");
 for(const auto& clip:r.receiverClips)if(!clip.valid())return fail(e,"Honey actual P2 receiver clip timing unresolved");
 for(unsigned k:{1u,2u}){bool action=false;for(const auto& event:r.receiverClips[k].keys)if(event.type==2)action=true;if(!action)return fail(e,"Honey actual P2 Growup KEYEVENT_2 absent");}
 for(unsigned clip:{0u,3u,4u,5u,6u})if(!r.clips[clip])return fail(e,"Honey source clip unresolved");
 m->resource=r;m->ready=true;e.clear();return true;
}
bool Manager::birth(HoneyKind kind,const ChildOutcome& child,Engine& rng,Creature*& out,std::string& e){
 out=nullptr;if(!m->ready)return fail(e,"Honey native manager not prepared");
 if(!valid(child.identity)||!finite(child.position)||!finite(child.velocity)||static_cast<int>(kind)<0||static_cast<int>(kind)>2)return fail(e,"Honey invalid source birth");
 for(const auto& a:m->actors)if(same(a->identity,child.identity)){if(a->policy.kind!=kind)return fail(e,"Honey source birth kind conflict");out=a->isAlive()?a.get():nullptr;e.clear();return true;}
 for(const auto& row:m->history)if(same(row.identity,child.identity)){if(row.kind!=kind)return fail(e,"Honey source history kind conflict");e.clear();return true;}
 m->reap();
 // Dead bodies remain stable while an absorbing actor still references them.
 for(auto i=m->actors.begin();i!=m->actors.end();)if(!(*i)->isAlive()&&!(*i)->references&&(*i)->removable()){Snapshot row;row.identity=(*i)->identity;row.kind=(*i)->policy.kind;row.phase=Phase::Dead;row.firstConsumption=(*i)->firstConsumption;m->history.push_back(row);invalidateSearch();i=m->actors.erase(i);}else ++i;
 if(m->actors.size()>=24){e.clear();return true;} // genuine FixedSizeItemMgr null birth, no init RNG
 AppHeap heap;auto actor=std::make_unique<Actor>(m->prop,m->resource,m->services,rng,child,kind);
 if(!actor->beginMotion(e))return false;out=actor.get();Actor* actual=actor.get();actor->receiverContact=[this,actual](Creature* other){std::string error;if(other->mObjType==OBJTYPE_Piki)(void)start(static_cast<Piki*>(other),actual,error);else if(other->mObjType==OBJTYPE_Navi)(void)start(static_cast<Navi*>(other),actual,error);require(error.empty(),error);};m->actors.push_back(std::move(actor));e.clear();return true;
}
bool Manager::owns(const Creature* c)const{return m->find(c)!=nullptr;}
bool Manager::beginStaged(std::string& e){if(!m->ready||m->staged||!m->actors.empty()||!m->history.empty()||!m->pikis.empty()||!m->navis.empty())return fail(e,"Honey stage requires prepared empty manager");m->staged=true;e.clear();return true;}
bool Manager::preflightPublishStaged(std::string& e)const{if(!m->ready||!m->staged||!m->pikis.empty()||!m->navis.empty())return fail(e,"Honey stage not prepared or carries receivers");AppHeap heap;for(const auto& actor:m->actors){if(!validChildIdentity(actor->identity)||actor->references)return fail(e,"Honey staged body identity/references invalid");if(actor->isAlive()){std::string animation;if(!m->services.captureAnimation(*actor,animation,e)||!m->services.validateAnimation(actor->policy.phase,animation,e))return false;}}e.clear();return true;}
void Manager::publishStaged()noexcept{m->staged=false;}
void Manager::abortStaged()noexcept{if(!m->staged)return;std::string e;bool okay=cleanup(e);require(okay&&e.empty(),e);}
bool Manager::absorb(Creature* c,std::string& e){if(m->staged)return fail(e,"Honey source stage unpublished");auto* a=m->find(c);return a?a->absorb(e):fail(e,"absorb target is not actual original Honey");}
bool Manager::start(Piki* p,Creature* c,std::string& e){
 if(m->staged)return fail(e,"Honey source stage unpublished");
 auto* a=m->find(c);e.clear();if(!a||!p||!p->isAlive()||p->getState()!=PIKISTATE_Normal||p->mHappa==Flower||a->policy.kind!=HoneyKind::Nectar||!a->policy.absorbable())return false;
 for(const auto& r:m->pikis)if(r->active&&r->piki==p)return false;
 AppHeap heap;auto r=std::make_unique<Impl::PikiReceiver>(*a,p);r->setMachine(p->mFSM);if(auto* old=p->getCurrState())old->cleanup(p);p->setCurrState(r.get());r->init(p);m->pikis.push_back(std::move(r));return true;
}
bool Manager::start(Navi* n,Creature* c,std::string& e){
 if(m->staged)return fail(e,"Honey source stage unpublished");
 auto* a=m->find(c);e.clear();if(!a||!n||!n->isAlive()||!n->getCurrState()||n->getCurrState()->getID()!=NAVISTATE_Walk||a->policy.kind==HoneyKind::Nectar||!a->policy.absorbable())return false;
 for(const auto& r:m->navis)if(r->active&&r->navi==n)return false;
 unsigned captain;if(!m->services.captainIndex(n,captain,e)||captain>1)return fail(e,"Honey actual captain index unresolved");
 AppHeap heap;auto r=std::make_unique<Impl::NaviReceiver>(*a,n,m->services,captain);r->setMachine(n->mStateMachine);n->getCurrState()->cleanup(n);n->setCurrState(r.get());r->init(n);m->navis.push_back(std::move(r));return true;
}
bool Manager::contact(Creature* c,Creature* other,std::string& e){
 if(m->staged)return fail(e,"Honey source stage unpublished");
 auto* a=m->find(c);if(!a||!other)return fail(e,"Honey contact outside actual bodies");
 if(!owns(other)){CollEvent event(other,nullptr,nullptr);a->collisionCallback(event);}
 e.clear();if(other->mObjType==OBJTYPE_Piki){(void)start(static_cast<Piki*>(other),c,e);return e.empty();}if(other->mObjType==OBJTYPE_Navi){(void)start(static_cast<Navi*>(other),c,e);return e.empty();}return true;
}
void Manager::forget(Piki* p){for(auto& r:m->pikis)if(r->piki==p){r->active=false;r->piki=nullptr;}m->reap();}
void Manager::forget(Navi* n){for(auto& r:m->navis)if(r->navi==n){r->active=false;r->navi=nullptr;}m->reap();}
bool Manager::cleanup(std::string& e){
 for(auto& r:m->pikis)if(r->active&&r->piki&&r->piki->getCurrState()==r.get())r->piki->mFSM->transit(r->piki,PIKISTATE_Normal);
 for(auto& r:m->navis)if(r->active&&r->navi&&r->navi->getCurrState()==r.get())r->navi->mStateMachine->transit(r->navi,NAVISTATE_Walk);
 m->pikis.clear();m->navis.clear();invalidateSearch();for(auto& a:m->actors)if(a->isAlive())a->kill(false);m->actors.clear();m->history.clear();m->ready=false;m->staged=false;e.clear();return true;
}
bool Manager::snapshot(std::vector<Snapshot>& out,std::string& e)const{
 for(const auto& p:m->pikis)if(p->active)return fail(e,"Honey snapshot requires Piki absorption/growth to finish");
 for(const auto& n:m->navis)if(n->active)return fail(e,"Honey snapshot requires Navi absorption to finish");
 std::vector<Snapshot> next=m->history;
 for(const auto& a:m->actors){Snapshot row;row.identity=a->identity;row.kind=a->policy.kind;row.phase=a->policy.phase;row.firstConsumption=a->firstConsumption;row.jiggling=a->policy.jiggling;row.position={a->mSRT.t.x,a->mSRT.t.y,a->mSRT.t.z};row.velocity={a->mVelocity.x,a->mVelocity.y,a->mVelocity.z};if(a->isAlive()&&!m->services.captureAnimation(*a,row.animation,e))return false;next.push_back(std::move(row));}
 out=std::move(next);e.clear();return true;
}
bool Manager::restore(const std::vector<Snapshot>& rows,Engine& rng,std::string& e){
 if(!m->ready||!m->actors.empty()||!m->history.empty()||!m->pikis.empty()||!m->navis.empty())return fail(e,"Honey restore requires prepared empty original course");
 std::set<ChildIdentity> seen;unsigned alive=0;
 for(const auto& row:rows){if(!valid(row.identity)||!finite(row.position)||!finite(row.velocity)||static_cast<int>(row.kind)<0||static_cast<int>(row.kind)>2||static_cast<int>(row.phase)<0||static_cast<int>(row.phase)>5||!seen.insert(row.identity).second)return fail(e,"invalid Honey source snapshot");if(row.phase!=Phase::Dead){++alive;if(!m->services.validateAnimation(row.phase,row.animation,e))return false;}else if(!row.animation.empty())return fail(e,"dead Honey carries live animation");if(row.phase==Phase::Shrink&&!row.firstConsumption)return fail(e,"shrinking Honey missing actual consumption");}
 if(alive>24)return fail(e,"Honey restored source count exceeds actual manager capacity");
 std::vector<std::unique_ptr<Actor>> next;std::vector<Snapshot> dead;
 AppHeap heap;
 for(const auto& row:rows){if(row.phase==Phase::Dead){dead.push_back(row);continue;}ChildOutcome child;child.identity=row.identity;child.position=row.position;child.velocity=row.velocity;auto a=std::make_unique<Actor>(m->prop,m->resource,m->services,rng,child,row.kind,false);a->policy.phase=row.phase;a->policy.jiggling=row.jiggling;a->firstConsumption=row.firstConsumption;if(!m->services.restoreAnimation(*a,row.animation,e)||!a->followCollider(e))return false;Actor* actual=a.get();a->receiverContact=[this,actual](Creature* other){std::string error;if(other->mObjType==OBJTYPE_Piki)(void)start(static_cast<Piki*>(other),actual,error);else if(other->mObjType==OBJTYPE_Navi)(void)start(static_cast<Navi*>(other),actual,error);require(error.empty(),error);};next.push_back(std::move(a));}
 m->actors=std::move(next);m->history=std::move(dead);e.clear();return true;
}
Creature* Manager::getCreature(int i){return !m->staged&&i>=0&&i<int(m->actors.size())?m->actors[i].get():nullptr;}
int Manager::getFirst(){return 0;}int Manager::getNext(int i){return i+1;}bool Manager::isDone(int i){return m->staged||i>=int(m->actors.size());}
int Manager::getSize(){if(m->staged)return 0;int n=0;for(const auto& a:m->actors)if(a->isAlive())++n;return n;}
void Manager::update(){if(m->staged)return;invalidateSearch();if(pikiMgr)search(pikiMgr);if(naviMgr)search(naviMgr);for(auto& a:m->actors)a->update();m->reap();}
void Manager::refresh(Graphics& gfx){if(m->staged)return;for(auto& a:m->actors)a->refresh(gfx);}
} }
