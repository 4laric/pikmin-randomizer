#include "pc_p2_original_gas_native.h"
#include "pc_p2_original_gas_clock.h"
#include "pc_p2_original_gas_save.h"
#include "pc_p2_original_drop_engine.h"
#include "pc_p2_original_actor.h"
#include "pc_p2_pose_family.h"
#include "pc_p2_original_pelplant_geometry.h"
#include "pc_p2_flyer_coll.h"
#include "pc_p2_hazard_emitter.h"
#include "pc_p2_species.h"
#include "pc_p2_navi_select.h"
#include "teki.h"
#include "Generator.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Interactions.h"
#include "ObjType.h"
#include "Graphics.h"
#include "Camera.h"
#include "Collision.h"
#include "Stickers.h"
#include "sysNew.h"
#include <fstream>
#include <set>
#include <cstdio>
#include <cstdlib>
extern Matrix4f invCamMat;
namespace p2original { namespace gas { namespace {
struct Heap {int before;Heap():before(gsys->setHeap(SYSHEAP_App)){}~Heap(){gsys->setHeap(before);}};
bool fail(std::string& e,const char* s){e=s;return false;}
std::set<Native*>& instances(){static std::set<Native*> all;return all;}
const char* clips[]={"wait","attack"};
struct Sample {int frame=0;Matrix4f joint;};
struct Motion {int duration=0;std::vector<int> frames;std::vector<Shape*> shapes;std::vector<Sample> joints;};
struct Track {unsigned motion=0;float frame=0;bool finish=false,generatorDeathCommitted=false;P2FlyerColl collision;std::unique_ptr<pelplant::Geometry> geometry;p2pose::Track presented;};
}
struct Native::Impl final:Engine {
 Services& services; Provider provider;
 Resources resource;bool loaded=false;
 p2posefamily::Bank bank{"ORIGINAL_GAS"};p2poseload::Shared shared;
 std::array<Motion,2> motions;
 std::array<p2flyer::Sphere,2> spheres;
 std::map<Creature*,std::unique_ptr<Track>> tracks;
 std::function<bool(Creature*,std::string&)> deathCallback;
 explicit Impl(Services& s):services(s),provider(*this){}
 bool load(std::string& e){
  if(loaded)return true;
  if(!gsys||!tekiMgr||!pikiMgr)return fail(e,"GasHiba real managers unavailable");
  auto* chassis=tekiMgr->getTekiShapeObject(TEKI_Palm);
  if(!chassis||!chassis->mShape||!chassis->mAnimMgr||!tekiMgr->getTekiParameters(TEKI_Palm)||!tekiMgr->getStrategy(TEKI_Palm))return fail(e,"GasHiba inert allocation chassis not preloaded before stage start");
  if(!services.linksReady(e))return false;
  resource.effects=services.sourceEffectsAndSoundsReady();
  if(!resource.effects)std::printf("P2_ORIGINAL_GAS_PRESENTATION_DEFERRED source_jpa=0 source_audio=0 mechanics=required\n");
  // Failed admission may retry after resources are repaired. Discard parsed
  // vectors/borrowed bank owners; never append a second attempt to the first.
  motions={};bank.reset();shared={};
  std::ifstream in("p2-original-gas-bank.txt");std::string word;
  if(!(in>>word)||word!="P2_ORIGINAL_GAS_BANK_1")return fail(e,"GasHiba original physical bank missing");
  std::size_t total=0;
  for(int k=0;k<2;++k){auto& motion=motions[k];std::string name,stem;int count;
   if(!(in>>word>>name>>count>>motion.duration>>stem)||word!="clip"||name!=clips[k]||count!=(k?4:1)||motion.duration!=(k?4:1)||stem!="original_gas_"+name)return fail(e,"invalid GasHiba authored clip row");
   if(!(in>>word)||word!="frames")return fail(e,"GasHiba frame list missing");
   for(int i=0;i<count;++i){int frame;if(!(in>>frame))return fail(e,"GasHiba frame list truncated");motion.frames.push_back(frame);}
   if(!p2posefamily::Bank::validFrames(motion.frames,count,motion.duration))return fail(e,"GasHiba source pose sample indices invalid");
   if(!p2posefamily::loadFamilyClip(bank,name,stem,count,motion.duration,motion.frames,shared,total,motion.shapes,e))return false;
   for(int frame:motion.frames){Sample sample;sample.frame=frame;sample.joint.makeIdentity();if(!(in>>word)||word!="joint")return fail(e,"GasHiba source gasuhiba1 sample missing");
    for(int r=0;r<3;++r)for(int c=0;c<4;++c)if(!(in>>sample.joint.mMtx[r][c])||!std::isfinite(sample.joint.mMtx[r][c]))return fail(e,"invalid GasHiba source joint matrix");
    motion.joints.push_back(sample);
   }
  }
  auto& p=resource.parameters;
  if(!(in>>word>>p.waitTime>>p.activeTime>>p.attackStartTime>>p.stopTime>>p.lodNear>>p.lodMiddle>>p.maxHealth>>p.attackDamage>>p.attackRadius>>p.maxAttackRange>>p.maxAttackAngle)||word!="parameters")return fail(e,"GasHiba exact source parameters missing");
  for(int i=0;i<2;++i){int parent;float x,y,z,radius;
   if(!(in>>word>>parent>>x>>y>>z>>radius)||word!="collider"||parent!=(i?0:-1)||!std::isfinite(radius)||radius<=0||!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z))return fail(e,"GasHiba authored collider invalid");
   spheres[i]={i?"g001":"g000","____",radius,{x,y,z},parent};
  }
  if(in>>word)return fail(e,"GasHiba trailing bank data");
  if(!bank.owner()||!pelplant::Geometry::admits(*bank.owner())||!bank.clip("wait")||!bank.clip("attack"))return fail(e,"GasHiba flattened owned pose geometry unavailable");
  resource.parametersLoaded=resource.model=resource.collider=true;resource.clips.fill(true);loaded=true;return true;
 }
 bool resources(Resources& out,std::string& e)override{Heap heap;if(!load(e))return false;out=resource;return true;}
 bool commonResources(const CatalogRow& row,std::string& e)override{return pc_p2_original_drop_resources(row,e);}
 bool reserve(unsigned n,std::string& e)override{if(tekiMgr->getMax()-tekiMgr->getSize()<int(n)||!tekiMgr->hasModel(TEKI_Palm))return fail(e,"GasHiba actual actor capacity not reserved");return true;}
 bool allocate(Host& h,const Position& p,float facing,std::string& e)override{
  Heap heap;auto* actor=tekiMgr->newTeki(TEKI_Palm);if(!actor){e.clear();return true;}h.creature=actor;
  auto track=std::make_unique<Track>();tracks.emplace(actor,std::move(track));
  actor->clearTekiOptions();actor->clearCreaturePointers();actor->mTekiShape=tekiMgr->getTekiShapeObject(TEKI_Palm);
  actor->mTekiAnimator->init(&actor->mTekiShape->mAnimContext,actor->mTekiShape->mAnimMgr,tekiMgr->mMotionTable);
  actor->mDeadState=0;actor->mStateID=0;actor->mStoredDamage=0;actor->mDamageCount=0;actor->_3A4=0;actor->mPellet=nullptr;
  for(int i=0;i<4;++i)actor->mParticleGenerators[i]=nullptr;
  actor->mGenerator=h.generator;actor->mSRT.t.set(p.x,p.y,p.z);actor->mFaceDirection=facing;
  actor->mSRT.r.set(0,facing,0);actor->mSRT.s.set(1,1,1);actor->mHealth=actor->mMaxHealth=h.health;actor->mVelocity.set(0,0,0);
  actor->mCollisionRadius=20;actor->mSize=20;actor->setCreatureFlag(CF_DisableMovement);actor->setCreatureFlag(CF_IsAiDisabled);
  actor->setTekiOption(BTeki::TEKI_OPTION_VISIBLE);actor->setTekiOption(BTeki::TEKI_OPTION_ATARI);actor->setTekiOption(BTeki::TEKI_OPTION_ALIVE);actor->setTekiOption(BTeki::TEKI_OPTION_SHAPE_VISIBLE);
  auto& t=*tracks.at(actor);t.geometry=std::make_unique<pelplant::Geometry>(*bank.owner());t.presented.shape=&t.geometry->shape;t.presented.size(*bank.basePose());
  if(!t.collision.bind(actor,spheres.data(),2))return fail(e,"GasHiba real source collider bind failed");follow(h);return true;
 }
 bool unitDraw(float& out,std::string&)override{out=gsys->getRand(1);return true;}
 bool flags(Host& h,const Flags& f,std::string&)override{
  auto* actor=static_cast<BTeki*>(h.creature);
  if(f.invulnerable)actor->setTekiOption(BTeki::TEKI_OPTION_INVINCIBLE);else actor->clearTekiOption(BTeki::TEKI_OPTION_INVINCIBLE);
  if(f.living)actor->setTekiOption(BTeki::TEKI_OPTION_ORGANIC);else actor->clearTekiOption(BTeki::TEKI_OPTION_ORGANIC);
  // ALIVE is retained for Dead so it remains visible/owned until course cleanup.
  if(f.untargetable)actor->setCreatureFlag(CF_IsFlying);else actor->resetCreatureFlag(CF_IsFlying);
  return true;
 }
 bool motion(Host& h,unsigned index,std::string& e)override{if(index>1)return fail(e,"invalid GasHiba motion");auto& t=*tracks.at(h.creature);t.motion=index;t.frame=0;t.finish=false;return true;}
 bool finishMotion(Host& h,std::string&)override{tracks.at(h.creature)->finish=true;return true;}
 bool gasEffect(Host& h,bool active,std::string& e)override{return services.gasEffect(h.creature,active,services.surfaceStory(),e);}
 bool updateEffectLod(Host& h,std::string& e)override{return services.effectLod(h.creature,h.parameters.lodNear,h.parameters.lodMiddle,e);}
 bool findLivingLinks(Host& h,void*& bridge,void*& gate,std::string& e)override{bridge=gate=nullptr;if(!services.surfaceStory())return true;return services.livingLinks(h.position,bridge,gate,e);}
 bool bridgeStage(void* bridge,int& stage,std::string& e)override{return services.bridgeStage(bridge,stage,e);}
 bool gateAlive(void* gate,bool& alive,std::string& e)override{return services.gateAlive(gate,alive,e);}
 bool gasScan(Host& h,std::string&)override{
  Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(!p||!p->isAlive())continue;Vector3f pos=p->getPosition();
   if(gasContains(h.position,{pos.x,pos.y,pos.z},h.parameters)&&p2_emitter_accepts(pc_p2_species(p),P2HazardGas,p->gasInvicible())){InteractGas gas(h.creature,h.parameters.attackDamage);p->stimulate(gas);}}
  if(naviMgr)for(Navi* n:pc_p2_navis()){if(!n||!n->isAlive())continue;auto pos=n->getPosition();if(gasContains(h.position,{pos.x,pos.y,pos.z},h.parameters)){InteractGas gas(h.creature,h.parameters.attackDamage);n->stimulate(gas);}}
  return true;
 }
 bool attackSound(Host& h,std::string& e)override{return services.sourceSound(h.creature,"PSSE_EN_GAS_HIBA_VOMIT",e);}
 bool death(Host& h,std::string& e)override{
  auto& t=*tracks.at(h.creature);
  if(!t.generatorDeathCommitted){
   auto* actor=static_cast<BTeki*>(h.creature);
   if(!actor->mGenerator||actor->mGenerator!=h.generator)return fail(e,"GasHiba actual source generator association missing");
   actor->mGenerator->informDeath(actor);actor->mGenerator=nullptr;
   t.generatorDeathCommitted=true;
   if(deathCallback&&!deathCallback(actor,e))return false;
  }
  return services.sourceSound(h.creature,"PSSE_EN_HIBA_STOP",e)&&services.sourceFatalEffect(h.creature,e);
 }
 bool cleanup(Host& h,std::string& e)override{
  auto i=tracks.find(h.creature);if(i==tracks.end())return true;
  if(!services.gasEffect(h.creature,false,services.surfaceStory(),e))return false;
  std::vector<Creature*> attached;Stickers stickers(h.creature);Iterator it(&stickers);CI_LOOP(it)attached.push_back(*it);
  for(auto* p:attached){InteractFlick flick(h.creature,0,0,-1000);p->stimulate(flick);}
  auto* actor=static_cast<BTeki*>(h.creature);
  i->second->collision.detach(actor);tracks.erase(i);
  // Source unload is not gameplay death. Creature::kill normally invokes
  // detachGenerator()->informDeath; GroupCourse owns this teardown instead.
  actor->mGenerator=nullptr;actor->kill(false);return true;
 }
 void follow(Host& h){auto& t=*tracks.at(h.creature);const auto& m=motions[t.motion];float frame=std::min(t.frame,float(m.duration-1));std::size_t a=0;while(a+1<m.joints.size()&&m.joints[a+1].frame<=frame)++a;std::size_t b=std::min(a+1,m.joints.size()-1);float w=a==b?0:(frame-m.joints[a].frame)/float(m.joints[b].frame-m.joints[a].frame);
  Matrix4f local,root,world;local.makeIdentity();for(int r=0;r<3;++r)for(int c=0;c<4;++c)local.mMtx[r][c]=(1-w)*m.joints[a].joint.mMtx[r][c]+w*m.joints[b].joint.mMtx[r][c];
  root.makeSRT(h.creature->mSRT.s,Vector3f(0,h.creature->mFaceDirection,0),h.creature->mSRT.t);root.multiplyTo(local,world);
  for(int k=0;k<2;++k){auto* part=t.collision.part(k);if(!part)continue;auto off=spheres[k].offset;
   part->mCentre.set(world.mMtx[0][3]+world.mMtx[0][0]*off.x+world.mMtx[0][1]*off.y+world.mMtx[0][2]*off.z,world.mMtx[1][3]+world.mMtx[1][0]*off.x+world.mMtx[1][1]*off.y+world.mMtx[1][2]*off.z,world.mMtx[2][3]+world.mMtx[2][0]*off.x+world.mMtx[2][1]*off.y+world.mMtx[2][2]*off.z);
   part->mRadius=spheres[k].radius;Matrix4f cameraRotation,jointRotation=world;cameraRotation.makeIdentity();for(int r=0;r<3;++r){jointRotation.mMtx[r][3]=0;for(int c=0;c<3;++c)cameraRotation.mMtx[r][c]=invCamMat.mMtx[c][r];}cameraRotation.multiplyTo(jointRotation,part->mJointMatrix);
  }
 }
};
Native::Native(Services& services):m(std::make_unique<Impl>(services)){instances().insert(this);}
Native::~Native(){if(!m->tracks.empty()||m->provider.size()){std::fprintf(stderr,"GasHiba destroyed with live source actors\n");std::abort();}instances().erase(this);}
Provider& Native::provider(){return m->provider;}
bool Native::owns(const Creature* actor)const{return m->tracks.count(const_cast<Creature*>(actor))!=0;}
void Native::onDeath(std::function<bool(Creature*,std::string&)> fn){m->deathCallback=std::move(fn);}
void Native::forget(BTeki* actor){auto i=m->tracks.find(actor);if(i!=m->tracks.end()){std::string e;if(!m->services.gasEffect(actor,false,m->services.surfaceStory(),e)){std::fprintf(stderr,"P2_ORIGINAL_GAS forget refusal: %s\n",e.c_str());std::abort();}i->second->collision.detach(actor);m->tracks.erase(i);}m->provider.retiredNative(actor);}
bool Native::tick(BTeki* actor,float dt,std::string& e){Heap heap;auto* h=m->provider.lookup(actor);if(!h)return fail(e,"GasHiba tick outside provider");auto& t=*m->tracks.at(actor);
 actor->mGrid.updateGrid(actor->mSRT.t);actor->mGrid.updateAIGrid(actor->mSRT.t,false);
 // Retail attack has source loop [0,3] and finishMotion exits that loop to
 // duration4 before KEYEVENT_END. Wait is one static frame. No half-clip events.
 Event event=Event::None;
 if(t.motion==1&&advanceAttack(t.frame,dt,t.finish))event=Event::End;
 if(!m->provider.tick(actor,dt,event,e))return false;
 actor->mStoredDamage=0;actor->mHealth=h->health;t.presented.advance(dt);m->follow(*h);return true;
}
bool Native::draw(BTeki* actor,Graphics& gfx,const Matrix4f& view,std::string& e){auto* h=m->provider.lookup(actor);if(!h||!gfx.mCamera)return fail(e,"GasHiba draw outside owned native state");auto& t=*m->tracks.at(actor);const auto* clip=m->bank.clip(clips[t.motion]);
 float frame=std::min(t.frame,float(m->motions[t.motion].duration-1));if(!clip||!p2pose::present(t.presented,clips[t.motion],clip->poses.size(),[clip](std::size_t i)->const p2pose::Pose&{return clip->poses[i];},clip->frames,frame,p2motion::tunables(),clip->seamContinuous).ok)return fail(e,"GasHiba source pose draw failed");
 gfx.useMatrix(Matrix4f::ident,0);auto& shape=t.geometry->shape;shape.updateAnim(gfx,view,nullptr,actor);shape.drawshape(gfx,*gfx.mCamera,nullptr);return true;
}
bool Native::snapshot(BTeki* actor,Snapshot& out,std::string& e)const{
 auto* h=m->provider.lookup(actor);auto t=m->tracks.find(actor);unsigned source=0,token=0;Snapshot next;
 if(!h||t==m->tracks.end()||!originalActors().query(actor,source,token,&next.identity)||source!=21||token!=h->token)return fail(e,"GasHiba checkpoint lacks exact original incarnation");
 next.state=h->state;next.position=h->position;next.facing=actor->mFaceDirection;next.health=h->health;next.timer=h->timer;
 next.sourceFrame=t->second->frame;next.motion=t->second->motion;next.finishMotion=t->second->finish;next.checkLinks=h->checkLinks;next.living=h->flags.living;next.generatorDeathCommitted=t->second->generatorDeathCommitted;
 bool bridge=false;
 if(h->bridge&&(!m->services.linkIdentity(h->bridge,next.bridge,bridge)||!bridge))return fail(e,"GasHiba checkpoint Bridge lost source identity");
 if(h->gate&&(!m->services.linkIdentity(h->gate,next.gate,bridge)||bridge))return fail(e,"GasHiba checkpoint Gate lost source identity");
 out=std::move(next);e.clear();return true;
}
bool Native::restore(BTeki* actor,const Snapshot& saved,std::string& e){
 std::string validated;if(!encodeSnapshot(saved,validated,e))return false;
 Heap heap;auto* h=m->provider.lookup(actor);auto t=m->tracks.find(actor);InstanceIdentity current;unsigned source=0,token=0;
 if(!h||t==m->tracks.end()||!originalActors().query(actor,source,token,&current)||source!=21||token!=h->token||!(current==saved.identity)||saved.motion>1)return fail(e,"GasHiba restore must bind exact saved source incarnation");
 for(float v:{saved.position.x,saved.position.y,saved.position.z,saved.facing,saved.health,saved.timer,saved.sourceFrame})if(!std::isfinite(v))return fail(e,"GasHiba checkpoint nonfinite state");
 const bool dead=saved.state==State::Dead,attack=saved.state==State::Attack;
 if((saved.state!=State::Dead&&saved.state!=State::Wait&&!attack)||saved.health<0||saved.health>h->parameters.maxHealth||saved.timer<0||saved.sourceFrame<0||saved.sourceFrame>m->motions[saved.motion].duration
  ||saved.motion!=(attack?1u:0u)||saved.generatorDeathCommitted!=dead||(dead&&(saved.health!=0||saved.living))
  ||(!saved.bridge.empty()&&!saved.gate.empty())||(saved.checkLinks&&(!saved.bridge.empty()||!saved.gate.empty())))return fail(e,"GasHiba checkpoint state invariants invalid");
 void* bridge=nullptr;void* gate=nullptr;
 if(!saved.bridge.empty()&&!m->services.resolveLink(saved.bridge,true,bridge,e))return false;
 if(!saved.gate.empty()&&!m->services.resolveLink(saved.gate,false,gate,e))return false;
 Flags flags=h->flags;flags.living=saved.living;flags.untargetable=dead;flags.lifeGauge=!dead;flags.invulnerable=dead;flags.damageAnimation=!dead;
 // Physical fields restore without RNG, source births, consumption or death
 // callbacks. The calling checkpoint layer already restored logical counters.
 if(!m->flags(*h,flags,e)||!m->motion(*h,saved.motion,e))return false;
 h->flags=flags;h->state=saved.state;h->position=saved.position;h->health=saved.health;h->timer=saved.timer;h->checkLinks=saved.checkLinks;h->bridge=bridge;h->gate=gate;h->deathReported=dead;h->effectActive=attack;
 auto& track=*t->second;track.frame=saved.sourceFrame;track.finish=saved.finishMotion;track.generatorDeathCommitted=dead;
 actor->mSRT.t.set(saved.position.x,saved.position.y,saved.position.z);actor->mFaceDirection=saved.facing;actor->mSRT.r.set(0,saved.facing,0);actor->mHealth=saved.health;actor->mStoredDamage=0;
 if(dead)actor->mGenerator=nullptr;
 m->follow(*h);if(!m->gasEffect(*h,attack,e))return false;e.clear();return true;
}
} }
namespace {
p2original::gas::Native* owner(BTeki* actor){for(auto* n:p2original::gas::instances())if(n->owns(actor))return n;return nullptr;}
void require(bool okay,const std::string& e){if(!okay){std::fprintf(stderr,"P2_ORIGINAL_GAS refusal: %s\n",e.c_str());std::abort();}}
}
bool pc_p2_original_gas_update(BTeki* actor){auto* n=owner(actor);if(!n)return false;std::string e;bool ok=n->tick(actor,gsys->getFrameTime(),e);require(ok,e);return true;}
bool pc_p2_original_gas_refresh(BTeki* actor,Graphics& gfx){auto* n=owner(actor);if(!n)return false;if(!gfx.mCamera)return true;Matrix4f root,view;root.makeSRT(actor->mSRT.s,Vector3f(0,actor->mFaceDirection,0),actor->mSRT.t);gfx.mCamera->mLookAtMtx.multiplyTo(root,view);std::string e;bool ok=n->draw(actor,gfx,view,e);require(ok,e);return true;}
bool pc_p2_original_gas_damage(BTeki* actor,Creature* attacker,float amount,bool& accepted){auto* n=owner(actor);if(!n)return false;auto p=attacker?attacker->getPosition():Vector3f(0,0,0);std::string e;accepted=n->provider().damage(actor,attacker,attacker&&attacker->mObjType==OBJTYPE_Navi,{p.x,p.y,p.z},amount,e);require(e.empty(),e);return true;}
void pc_p2_original_gas_forget(BTeki* actor){auto* n=owner(actor);if(n)n->forget(actor);}
