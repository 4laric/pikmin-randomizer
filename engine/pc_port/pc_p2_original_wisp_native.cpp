#include "pc_p2_original_wisp_native.h"
#include "pc_p2_original_wisp_clock.h"
#include "pc_p2_original_egg_native.h"
#include "pc_p2_pose_family.h"
#include "pc_p2_original_pelplant_geometry.h"
#include "pc_p2_flyer_coll.h"
#include "pc_p2_original_actor.h"
#include "pc_p2_navi_select.h"
#include "teki.h"
#include "Generator.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "MapMgr.h"
#include "CreatureProp.h"
#include "ObjType.h"
#include "Graphics.h"
#include "Camera.h"
#include "Collision.h"
#include "Stickers.h"
#include "Interactions.h"
#include "sysNew.h"
#include <fstream>
#include <set>
#include <cstdio>
#include <cstdlib>
extern Matrix4f invCamMat;
namespace p2original { namespace wisp { namespace {
bool fail(std::string& e,const char* s){e=s;return false;}
struct Heap {int before;Heap():before(gsys->setHeap(SYSHEAP_App)){}~Heap(){gsys->setHeap(before);}};
std::set<Native*>& instances(){static std::set<Native*> all;return all;}
const char* names[]={"waitl","damage","run","appear1","hide1"};
const int durations[]={100,35,10,30,30};
struct Sample {Matrix4f water,body;};
struct Motion {int duration=0;std::vector<int> frames;std::vector<Key> keys;std::vector<Shape*> shapes;std::vector<Sample> joints;};
struct Track {unsigned motion=3;Clock clock;Matrix4f water,body;Vector3f target{0,0,0};p2originalresource::SourceIdentity cargo;bool cargoKnown=false,eggBorn=false;CreatureProp* borrowedProps=nullptr;std::unique_ptr<CreatureProp> props;P2FlyerColl collision;std::unique_ptr<pelplant::Geometry> geometry;p2pose::Track presented;};
}
struct Native::Impl final:Engine {
 Services& services;Provider provider;Resources resource;bool loaded=false;
 p2posefamily::Bank bank{"ORIGINAL_WISP"};p2poseload::Shared shared;
 std::array<Motion,5> motions;std::array<p2flyer::Sphere,2> spheres;
 std::map<Creature*,std::unique_ptr<Track>> tracks;
 float acceleration=0,mapRadius=0,mapOffset=0,wallReflection=0;
 explicit Impl(Services& s):services(s),provider(*this){}
 bool load(std::string& e){
  if(loaded)return true;
  if(!gsys||!tekiMgr||!pikiMgr||!mapMgr)return fail(e,"Qurione actual managers unavailable");
  auto* chassis=tekiMgr->getTekiShapeObject(TEKI_Palm);
  if(!chassis||!chassis->mShape||!chassis->mAnimMgr||!tekiMgr->getTekiParameters(TEKI_Palm)||!tekiMgr->getStrategy(TEKI_Palm))return fail(e,"Qurione inert allocation chassis not preloaded before stage start");
  if(!services.eggResources(e))return false;
  motions={};bank.reset();shared={};std::ifstream in("p2-original-wisp-bank.txt");std::string word;
  if(!(in>>word)||word!="P2_ORIGINAL_WISP_BANK_1")return fail(e,"Qurione original authored bank missing");
  std::size_t total=0;
  for(unsigned k=0;k<5;++k){auto& motion=motions[k];std::string name,stem;int count,events;
   if(!(in>>word>>name>>count>>motion.duration>>stem>>events)||word!="clip"||name!=names[k]||motion.duration!=durations[k]||count!=(k==1?5:4)||events!=(k==0||k==2?2:k==1?1:0)||stem!="original_wisp_"+name)return fail(e,"Qurione authored clip row invalid");
   if(!(in>>word)||word!="events")return fail(e,"Qurione authored key table missing");
   for(int i=0;i<events;++i){Key key;if(!(in>>key.frame>>key.type))return fail(e,"Qurione key table truncated");motion.keys.push_back(key);}
   if((k==1&&(motion.keys[0].frame!=5||motion.keys[0].type!=2))||((k==0||k==2)&&(motion.keys[0].frame!=0||motion.keys[0].type!=0||motion.keys[1].frame!=motion.duration-1||motion.keys[1].type!=1)))return fail(e,"Qurione literal authored key events changed");
   if(!(in>>word)||word!="frames")return fail(e,"Qurione source frame list missing");
   for(int i=0;i<count;++i){int f;if(!(in>>f))return fail(e,"Qurione frame list truncated");motion.frames.push_back(f);}
   if(!p2posefamily::Bank::validFrames(motion.frames,count,motion.duration)||!p2posefamily::loadFamilyClip(bank,name,stem,count,motion.duration,motion.frames,shared,total,motion.shapes,e))return false;
   for(int i=0;i<count;++i){Sample sample;sample.water.makeIdentity();sample.body.makeIdentity();
    for(int j=0;j<2;++j){std::string joint;if(!(in>>word>>joint)||word!="joint"||joint!=(j?"body_jnt2":"water"))return fail(e,"Qurione source attachment sample missing");auto& m=j?sample.body:sample.water;
     for(int r=0;r<3;++r)for(int c=0;c<4;++c)if(!(in>>m.mMtx[r][c])||!std::isfinite(m.mMtx[r][c]))return fail(e,"Qurione nonfinite joint matrix");}
    motion.joints.push_back(sample);
   }
  }
  auto& p=resource.parameters;
  if(!(in>>word>>p.flightHeight>>p.pitchRate>>p.pitchAmplitude>>p.deathRate>>p.deathTime>>p.moveSpeed>>p.viewAngle>>p.sightRadius>>p.health)||word!="parameters")return fail(e,"Qurione source parameters missing");
  if(!(in>>word>>acceleration>>mapRadius>>mapOffset>>wallReflection)||word!="physics"||acceleration!=.1f||mapRadius!=15||mapOffset!=0||wallReflection!=.5f)return fail(e,"Qurione literal source physical properties missing");
  for(int i=0;i<2;++i){int parent;float x,y,z,radius;if(!(in>>word>>parent>>x>>y>>z>>radius)||word!="collider"||parent!=(i?0:-1)||!std::isfinite(radius)||radius<=0||!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z))return fail(e,"Qurione source collider invalid");spheres[i]={i?"q001":"q000",i?"_t__":"____",radius,{x,y,z},parent};}
  if(in>>word)return fail(e,"Qurione trailing bank data");
  if(!bank.owner()||!bank.basePose()||!pelplant::Geometry::admits(*bank.owner()))return fail(e,"Qurione owned flattened geometry unavailable");
  resource.model=resource.collider=resource.waterJoint=resource.glowJoint=resource.egg=true;resource.motions.fill(true);loaded=true;
  if(!services.presentationReady())std::puts("P2_ORIGINAL_WISP_PRESENTATION_DEFERRED source_jpa=0 source_audio=0 mechanics=required");
  return true;
 }
 bool resources(Resources& out,std::string& e)override{Heap heap;if(!load(e))return false;out=resource;return true;}
 bool reserve(unsigned wisps,unsigned eggs,std::string& e)override{
  if(tekiMgr->getMax()-tekiMgr->getSize()<int(wisps)||!tekiMgr->hasModel(TEKI_Palm))return fail(e,"Qurione actual carrier capacity unavailable");
  return services.reserveEggs(eggs,e);
 }
 bool allocate(Host& h,const Position& p,float dir,std::string& e)override{
  Heap heap;auto* actor=tekiMgr->newTeki(TEKI_Palm);if(!actor){e.clear();return true;}h.creature=actor;
  auto track=std::make_unique<Track>();track->water.makeIdentity();track->body.makeIdentity();tracks.emplace(actor,std::move(track));
  actor->clearTekiOptions();actor->clearCreaturePointers();actor->mTekiShape=tekiMgr->getTekiShapeObject(TEKI_Palm);
  actor->mTekiAnimator->init(&actor->mTekiShape->mAnimContext,actor->mTekiShape->mAnimMgr,tekiMgr->mMotionTable);
  actor->mDeadState=0;actor->mStateID=0;actor->mStoredDamage=0;actor->mDamageCount=0;actor->_3A4=0;actor->mPellet=nullptr;
  for(int i=0;i<4;++i)actor->mParticleGenerators[i]=nullptr;
  actor->mGenerator=h.generator;actor->mSRT.t.set(p.x,p.y,p.z);actor->mFaceDirection=dir;actor->mSRT.r.set(0,dir,0);actor->mSRT.s.set(1,1,1);
  actor->mHealth=actor->mMaxHealth=h.parameters.health;actor->mVelocity.set(0,0,0);actor->mCollisionRadius=25;actor->mSize=25;
  actor->resetCreatureFlag(CF_DisableMovement);actor->resetCreatureFlag(CF_SkipPhysicsAndCollision);
  actor->mVolatileVelocity.set(0,0,0);actor->mIsFrozen=false;
  actor->setCreatureFlag(CF_IsFlying);actor->setCreatureFlag(CF_IsAiDisabled);actor->setInsideView();
  actor->setTekiOption(BTeki::TEKI_OPTION_VISIBLE);actor->setTekiOption(BTeki::TEKI_OPTION_ALIVE);actor->setTekiOption(BTeki::TEKI_OPTION_INVINCIBLE);
  auto& t=*tracks.at(actor);t.geometry=std::make_unique<pelplant::Geometry>(*bank.owner());t.presented.shape=&t.geometry->shape;t.presented.size(*bank.basePose());
  t.borrowedProps=actor->mProps;t.props=std::make_unique<CreatureProp>();t.props->mCreatureProps.mBounceFactor.mValue=wallReflection;t.props->mCreatureProps.mAcceleration.mValue=acceleration;actor->mProps=t.props.get();actor->mCollisionRadius=mapRadius;
  if(!t.collision.bind(actor,spheres.data(),2))return fail(e,"Qurione actual source collision bind failed");
  follow(h);return true;
 }
 bool attachEgg(Host& h,Creature*& egg,std::string& e)override{auto& t=*tracks.at(h.creature);if(!services.capturedEpochIdentity(h.row,h.generator,h.ordinal,t.cargo,e))return false;if(t.cargo.fingerprint.empty()||t.cargo.uid!=h.row.enemy.uid||t.cargo.ordinal!=h.ordinal||!t.cargo.activation)return fail(e,"Qurione authoritative cargo identity invalid");t.cargoKnown=true;auto p=h.creature->getPosition();if(!services.attachEgg(h.creature,&t.water,{p.x,p.y,p.z},h.facing,egg,e))return false;t.eggBorn=egg!=nullptr;return true;}
 bool setPosition(Host& h,const Position& p,std::string&)override{h.creature->mSRT.t.set(p.x,p.y,p.z);follow(h);return true;}
 bool facing(Host& h,float dir,std::string&)override{h.creature->mFaceDirection=dir;h.creature->mSRT.r.set(0,dir,0);follow(h);return true;}
 bool flags(Host& h,bool atari,bool hidden,bool,bool alive,std::string&)override{
  auto* a=static_cast<BTeki*>(h.creature);
  if(atari)a->setTekiOption(BTeki::TEKI_OPTION_ATARI);else a->clearTekiOption(BTeki::TEKI_OPTION_ATARI);
  if(hidden)a->clearTekiOption(BTeki::TEKI_OPTION_SHAPE_VISIBLE);else a->setTekiOption(BTeki::TEKI_OPTION_SHAPE_VISIBLE);
  if(alive)a->setTekiOption(BTeki::TEKI_OPTION_ALIVE);else a->clearTekiOption(BTeki::TEKI_OPTION_ALIVE);
  // Source disables animation culling at init, and Dead/Drop also disable AI
  // culling; retain actual always-active carrier movement throughout its life.
  a->setInsideView();return true;
 }
 bool motion(Host& h,unsigned animation,bool stopped,std::string& e)override{if(animation>=5)return fail(e,"Qurione invalid literal source animation");auto& t=*tracks.at(h.creature);t.motion=animation;t.clock.start(stopped);follow(h);return true;}
 bool effect(Host& h,const char* operation,std::string& e)override{return services.effect(h.creature,operation,h.scale,tracks.at(h.creature)->body,e);}
 bool appear(const Host& h,bool& out,std::string&)override{
  out=false;auto p=h.creature->getPosition();const float angle=h.parameters.viewAngle*3.14159265358979323846f/180;
  auto candidate=[&](Creature* c){if(!c||!c->isAlive())return false;auto q=c->getPosition();float dx=q.x-p.x,dz=q.z-p.z;float a=std::atan2(dx,dz)-h.facing;while(a>3.14159265f)a-=6.2831853f;while(a<-3.14159265f)a+=6.2831853f;return std::fabs(a)<=angle&&dx*dx+dz*dz<h.parameters.sightRadius*h.parameters.sightRadius;};
  if(naviMgr)for(auto* n:pc_p2_navis())if(candidate(n)){out=true;return true;}
  Iterator it(pikiMgr);CI_LOOP(it){auto* piki=static_cast<Piki*>(*it);if(piki&&!piki->isStickToMouth()&&candidate(piki)){out=true;return true;}}
  return true;
 }
 bool visible(const Host& h,bool& out,std::string& e)override{
  if(!gsys||!gsys->mGraphics||!gsys->mGraphics->mCamera)return fail(e,"Qurione actual frame camera unavailable for source visibility");
  auto it=tracks.find(h.creature);if(it==tracks.end())return fail(e,"Qurione source visibility lost actual collider");
  auto* root=it->second->collision.part(0);if(!root)return fail(e,"Qurione source visibility root sphere unavailable");
  // Retail updateSpheres takes the actual root CollPart sphere. Visibility is
  // its physical sphere against the viewport, independent of presentation flags.
  out=gsys->mGraphics->mCamera->isPointVisible(root->mCentre,root->mRadius);e.clear();return true;
 }
 bool position(const Host& h,Position& p,std::string&)override{auto v=h.creature->getPosition();p={v.x,v.y,v.z};return true;}
 bool floor(const Position& p,float& y,std::string& e)override{return egg::sourceGroundHeight(p,y,e);}
 bool velocity(Host& h,const Position& v,std::string&)override{auto* a=static_cast<BTeki*>(h.creature);auto& t=*tracks.at(a);t.target.set(v.x,0,v.z);if(h.state==State::Dead){t.target.set(v.x,v.y,v.z);a->mVelocity.set(t.target);}else if(h.state==State::Move&&t.motion==0)a->mVelocity.y=v.y;return true;}
 bool releaseEgg(Host& h,Creature* egg,std::string& e)override{follow(h);return services.detachEgg(egg,e);}
 bool kill(Host& h,std::string& e)override{
  auto* a=static_cast<BTeki*>(h.creature);
  // Death belongs to original source generator, not host corpse/AP rewards.
  if(a->mGenerator){if(a->mGenerator!=h.generator)return fail(e,"Qurione source generator changed");a->mGenerator->informDeath(a);a->mGenerator=nullptr;}
  if(h.egg&&!services.destroyCapturedEgg(h.egg,e))return false;
  h.egg=nullptr;forgetTrack(a);provider.retiredNative(a);a->kill(false);return true;
 }
 void forgetTrack(Creature* actor){auto i=tracks.find(actor);if(i!=tracks.end()){i->second->collision.detach(static_cast<BTeki*>(actor));actor->mProps=i->second->borrowedProps;tracks.erase(i);}}
 bool cleanup(Host& h,std::string& e)override{
  auto* a=h.creature;if(h.egg&&!services.destroyCapturedEgg(h.egg,e))return false;h.egg=nullptr;
  std::vector<Creature*> attached;Stickers stickers(a);Iterator it(&stickers);CI_LOOP(it)attached.push_back(*it);
  for(auto* p:attached){InteractFlick flick(a,0,0,-1000);p->stimulate(flick);}
  // Course cleanup retires physical bodies without consuming source deaths.
  // Actual death path above commits informDeath explicitly before nulling.
  a->mGenerator=nullptr;forgetTrack(a);a->kill(false);return true;
 }
 void follow(Host& h){auto& t=*tracks.at(h.creature);const auto& m=motions[t.motion];float frame=std::min(t.clock.frame,float(m.duration-1));std::size_t a=0;while(a+1<m.frames.size()&&m.frames[a+1]<=frame)++a;std::size_t b=std::min(a+1,m.frames.size()-1);float w=a==b?0:(frame-m.frames[a])/float(m.frames[b]-m.frames[a]);Matrix4f root;root.makeSRT(h.creature->mSRT.s,Vector3f(0,h.creature->mFaceDirection,0),h.creature->mSRT.t);
  for(int j=0;j<2;++j){Matrix4f local;local.makeIdentity();const auto& ma=j?m.joints[a].body:m.joints[a].water;const auto& mb=j?m.joints[b].body:m.joints[b].water;for(int r=0;r<3;++r)for(int c=0;c<4;++c)local.mMtx[r][c]=(1-w)*ma.mMtx[r][c]+w*mb.mMtx[r][c];root.multiplyTo(local,j?t.body:t.water);}
  for(int k=0;k<2;++k){auto* part=t.collision.part(k);if(!part)continue;auto off=spheres[k].offset;const auto& world=t.body;part->mCentre.set(world.mMtx[0][3]+world.mMtx[0][0]*off.x+world.mMtx[0][1]*off.y+world.mMtx[0][2]*off.z,world.mMtx[1][3]+world.mMtx[1][0]*off.x+world.mMtx[1][1]*off.y+world.mMtx[1][2]*off.z,world.mMtx[2][3]+world.mMtx[2][0]*off.x+world.mMtx[2][1]*off.y+world.mMtx[2][2]*off.z);part->mRadius=spheres[k].radius*std::max({std::fabs(h.creature->mSRT.s.x),std::fabs(h.creature->mSRT.s.y),std::fabs(h.creature->mSRT.s.z)});Matrix4f cameraRotation,jointRotation=world;cameraRotation.makeIdentity();for(int r=0;r<3;++r){jointRotation.mMtx[r][3]=0;for(int c=0;c<3;++c)cameraRotation.mMtx[r][c]=invCamMat.mMtx[c][r];}cameraRotation.multiplyTo(jointRotation,part->mJointMatrix);}
 }
};
Native::Native(Services& s):m(std::make_unique<Impl>(s)){instances().insert(this);}
Native::~Native(){if(!m->tracks.empty()){std::fputs("Qurione destroyed with live source actors\n",stderr);std::abort();}instances().erase(this);}
Provider& Native::provider(){return m->provider;}
bool Native::owns(const Creature* a)const{return m->tracks.count(const_cast<Creature*>(a))!=0;}
bool Native::capturedSourceIdentity(Creature* parent,p2originalresource::SourceIdentity& out,std::string& e)const{
 auto* h=m->provider.lookup(parent);if(!h)return fail(e,"Qurione cargo identity outside actual source host");
 p2originalresource::SourceIdentity source;
 if(!m->services.capturedEpochIdentity(h->row,h->generator,h->ordinal,source,e))return false;
 if(source.fingerprint.empty()||source.uid!=h->row.enemy.uid||source.ordinal!=h->ordinal||!source.activation)return fail(e,"Qurione cargo incarnation differs from authoritative original parent");
 out=std::move(source);e.clear();return true;
}
bool Native::capturedIdentity(Creature* parent,std::string& out,std::string& e)const{
 p2originalresource::SourceIdentity source;if(!capturedSourceIdentity(parent,source,e))return false;
 out=source.fingerprint+":"+std::to_string(source.uid)+":"+std::to_string(source.ordinal)+":"+std::to_string(source.epoch)+":"+std::to_string(source.activation)+":Egg:0";e.clear();return true;
}
bool Native::snapshot(BTeki* a,Snapshot& out,std::string& e)const{
 auto* h=m->provider.lookup(a);if(!h||!owns(a))return fail(e,"Qurione checkpoint outside actual source host");
 const auto& t=*m->tracks.at(a);unsigned source=0,token=0;Snapshot s;
 if(!originalActors().query(a,source,token,&s.identity)||source!=16||token!=h->token||!t.cargoKnown)return fail(e,"Qurione checkpoint missing full original association");
 s.state=h->state;s.spawnIndex=h->spawnIndex;s.motion=t.motion;s.spawn[0]=h->spawn[0];s.spawn[1]=h->spawn[1];s.position={a->mSRT.t.x,a->mSRT.t.y,a->mSRT.t.z};s.velocity={a->mVelocity.x,a->mVelocity.y,a->mVelocity.z};s.targetVelocity={t.target.x,t.target.y,t.target.z};s.facing=h->facing;s.pitch=h->pitch;s.timer=h->timer;s.scale=h->scale;s.dead=h->dead;s.released=h->released;s.eggBorn=t.eggBorn;s.cargo=t.cargo;s.clock=t.clock;
 s.atari=a->getTekiOption(BTeki::TEKI_OPTION_ATARI);s.hidden=!a->getTekiOption(BTeki::TEKI_OPTION_SHAPE_VISIBLE);s.alive=a->getTekiOption(BTeki::TEKI_OPTION_ALIVE);s.cullable=h->state!=State::Drop&&h->state!=State::Dead;
 if(!preflightRestore(a,s,e))return false;
 out=std::move(s);e.clear();return true;
}
bool Native::preflightRestore(BTeki* a,const Snapshot& s,std::string& e)const{
 auto* h=m->provider.lookup(a);if(!h||!owns(a)||s.motion>=m->motions.size())return fail(e,"Qurione checkpoint restore outside actual source host");
 unsigned source=0,token=0;InstanceIdentity identity;
 if(!originalActors().query(a,source,token,&identity)||source!=16||token!=h->token||!(identity==s.identity))return fail(e,"Qurione checkpoint full source incarnation mismatch");
 const auto& clip=m->motions[s.motion];if(!validateSnapshot(s,h->initial,clip.duration,clip.keys,e))return false;
 for(unsigned i=0;i<2;++i)if(s.spawn[i].x!=h->spawn[i].x||s.spawn[i].y!=h->spawn[i].y||s.spawn[i].z!=h->spawn[i].z)return fail(e,"Qurione checkpoint changed immutable source endpoints");
 if(s.state==State::Dead&&(s.targetVelocity.x!=0||s.targetVelocity.z!=0||s.targetVelocity.y!=h->parameters.deathRate))return fail(e,"Qurione checkpoint source death target invalid");
 auto& t=*m->tracks.at(a);const auto& c=t.cargo;
 if(!t.cargoKnown||c.fingerprint!=s.cargo.fingerprint||c.uid!=s.cargo.uid||c.ordinal!=s.cargo.ordinal||c.epoch!=s.cargo.epoch||c.activation!=s.cargo.activation||t.eggBorn!=s.eggBorn)return fail(e,"Qurione checkpoint authoritative cargo outcome mismatch");
 Creature* cargo=nullptr;if(!m->services.checkpointEgg(s.cargo,s.eggBorn,s.released,a,&t.water,cargo,e))return false;
 if((!s.eggBorn&&cargo)||(s.eggBorn&&!s.released&&!cargo)||cargo==a)return fail(e,"Qurione checkpoint Egg graph association invalid");
 e.clear();return true;
}
bool Native::applyRestore(BTeki* a,const Snapshot& s,std::string& e){
 if(!preflightRestore(a,s,e))return false;
 auto* h=m->provider.lookup(a);auto& t=*m->tracks.at(a);Creature* cargo=nullptr;
 // Resolve before any mutation. The SAVE owner serializes graph preflight/apply;
 // the resolver only checks existing bodies and the actual water capture link.
 if(!m->services.checkpointEgg(s.cargo,s.eggBorn,s.released,a,&t.water,cargo,e))return false;
 h->state=s.state;h->spawnIndex=s.spawnIndex;h->spawn[0]=s.spawn[0];h->spawn[1]=s.spawn[1];h->facing=s.facing;h->pitch=s.pitch;h->timer=s.timer;h->scale=s.scale;h->dead=s.dead;h->released=s.released;h->egg=s.released?nullptr:cargo;
 a->mSRT.t.set(s.position.x,s.position.y,s.position.z);a->mFaceDirection=s.facing;a->mSRT.r.set(0,s.facing,0);a->mVelocity.set(s.velocity.x,s.velocity.y,s.velocity.z);t.target.set(s.targetVelocity.x,s.targetVelocity.y,s.targetVelocity.z);t.motion=s.motion;t.clock=s.clock;
 m->flags(*h,s.atari,s.hidden,s.cullable,s.alive,e);a->mStoredDamage=0;a->mHealth=h->parameters.health;m->follow(*h);e.clear();return true;
}
void Native::forget(BTeki* a){auto* h=m->provider.lookup(a);if(h&&h->egg){std::string e;if(!m->services.destroyCapturedEgg(h->egg,e)){std::fprintf(stderr,"Qurione attached Egg cleanup refusal: %s\n",e.c_str());std::abort();}h->egg=nullptr;}m->forgetTrack(a);m->provider.retiredNative(a);}
bool Native::flyingCollision(BTeki* a,Creature* collider,std::string& e){bool piki=collider&&collider->mObjType==OBJTYPE_Piki&&static_cast<Piki*>(collider)->getState()==PIKISTATE_Flying;return m->provider.flyingCollision(a,piki,e);}
bool Native::tick(BTeki* a,float dt,std::string& e){Heap heap;auto* h=m->provider.lookup(a);if(!h||!std::isfinite(dt)||dt<0)return fail(e,"Qurione tick outside original source or invalid delta");auto& t=*m->tracks.at(a);a->setInsideView();a->mGrid.updateGrid(a->mSRT.t);a->mGrid.updateAIGrid(a->mSRT.t,false);
 auto& motion=m->motions[t.motion];int key=t.clock.advance(dt,motion.duration,motion.keys);m->follow(*h);Event event=key==2?Event::ReleaseEgg:key==1000?Event::End:Event::None;
 if(!m->provider.tick(a,dt,event,e))return false;
 // kill may synchronously release Host and Track. Never use prior references.
 if(!owns(a))return true;
 // Owned update bypasses borrowed host AI/animation. Use actual native map
 // movement/collision once with gravity disabled for the retail flying actor.
 a->mHasCollChangedVelocity=0;a->mCollisionOccurred=0;
 auto& motor=*m->tracks.at(a);a->mVelocity.set(a->mVelocity+(motor.target-a->mVelocity)*(dt/m->acceleration));
 MoveTrace trace(a->mSRT.t,a->mVelocity,m->mapRadius,true);trace.mP2WallThreshold=true;mapMgr->traceMove(a,trace,dt);a->mSRT.t.set(trace.mPosition);a->mVelocity.set(trace.mVelocity);
 if(!owns(a))return true;
 h=m->provider.lookup(a);a->mStoredDamage=0;a->mHealth=h->parameters.health;auto& live=*m->tracks.at(a);live.presented.advance(dt);m->follow(*h);return true;
}
bool Native::draw(BTeki* a,Graphics& gfx,const Matrix4f& view,std::string& e){auto* h=m->provider.lookup(a);if(!h||!gfx.mCamera)return fail(e,"Qurione draw outside actual host");if(h->state==State::Stay)return true;auto& t=*m->tracks.at(a);const auto* clip=m->bank.clip(names[t.motion]);float frame=std::min(t.clock.frame,float(m->motions[t.motion].duration-1));if(!clip||!p2pose::present(t.presented,names[t.motion],clip->poses.size(),[clip](std::size_t i)->const p2pose::Pose&{return clip->poses[i];},clip->frames,frame,p2motion::tunables(),clip->seamContinuous).ok)return fail(e,"Qurione authored pose presentation failed");gfx.useMatrix(Matrix4f::ident,0);auto& shape=t.geometry->shape;shape.updateAnim(gfx,view,nullptr,a);shape.drawshape(gfx,*gfx.mCamera,nullptr);return true;}
} }
namespace {
p2original::wisp::Native* owner(const BTeki* a){for(auto* n:p2original::wisp::instances())if(n->owns(a))return n;return nullptr;}
void require(bool okay,const std::string& e){if(!okay){std::fprintf(stderr,"P2_ORIGINAL_WISP refusal: %s\n",e.c_str());std::abort();}}
}
bool pc_p2_original_wisp_owns(const BTeki* a){return owner(a)!=nullptr;}
bool pc_p2_original_wisp_update(BTeki* a){auto* n=owner(a);if(!n)return false;std::string e;require(n->tick(a,gsys->getFrameTime(),e),e);return true;}
bool pc_p2_original_wisp_refresh(BTeki* a,Graphics& gfx){auto* n=owner(a);if(!n)return false;if(!gfx.mCamera)return true;Matrix4f root,view;root.makeSRT(a->mSRT.s,Vector3f(0,a->mFaceDirection,0),a->mSRT.t);gfx.mCamera->mLookAtMtx.multiplyTo(root,view);std::string e;require(n->draw(a,gfx,view,e),e);return true;}
bool pc_p2_original_wisp_collision(BTeki* a,Creature* collider){auto* n=owner(a);if(!n)return false;std::string e;require(n->flyingCollision(a,collider,e),e);return true;}
void pc_p2_original_wisp_forget(BTeki* a){auto* n=owner(a);if(n)n->forget(a);}
