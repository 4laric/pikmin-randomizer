#include "pc_p2_original_egg_native.h"
#include "pc_p2_original_drop_engine.h"
#include "pc_p2_pose_family.h"
#include "pc_p2_original_pelplant_geometry.h"
#include "pc_p2_flyer_coll.h"
#include "teki.h"
#include "Generator.h"
#include "ObjType.h"
#include "MapMgr.h"
#include "Graphics.h"
#include "Camera.h"
#include "Collision.h"
#include "Stickers.h"
#include "Interactions.h"
#include "sysNew.h"
#include "netplay/pc_netplay_sha256.h"
#include <fstream>
#include <set>
#include <cstdio>
#include <cstdlib>
extern Matrix4f invCamMat;
namespace p2original { namespace egg { namespace {
struct Heap {int before;Heap():before(gsys->setHeap(SYSHEAP_App)){}~Heap(){gsys->setHeap(before);}};
bool fail(std::string& e,const char* s){e=s;return false;}
std::set<Native*>& instances(){static std::set<Native*> all;return all;}
struct Sample {int frame=0;std::array<Matrix4f,2> joint;};
struct Track {
 float frame=0;bool stopped=true;Matrix4f* capture=nullptr;
 bool hasDependentIdentity=false;p2originalresource::SourceIdentity dependentIdentity;
 P2FlyerColl collision;std::unique_ptr<pelplant::Geometry> geometry;p2pose::Track presented;
};
}
std::string digest(const std::string& bytes){unsigned char result[32];pc_netplay_sha::sha256(bytes.data(),bytes.size(),result);const char* hex="0123456789abcdef";std::string out;for(unsigned char b:result){out+=hex[b>>4];out+=hex[b&15];}return out;}
bool readBytes(const std::string& path,std::string& out,std::string& e){std::ifstream in(path,std::ios::binary);if(!in)return fail(e,"Egg authenticated resource file unavailable");in.seekg(0,std::ios::end);const auto size=in.tellg();if(size<0||size>16*1024*1024)return fail(e,"Egg authenticated resource byte size invalid");in.seekg(0);std::string bytes(static_cast<std::size_t>(size),'\0');if(!bytes.empty()&&!in.read(&bytes[0],bytes.size()))return fail(e,"Egg authenticated resource byte read failed");out=std::move(bytes);return true;}
bool sourceGroundHeight(Position p,float& height,std::string& e){
 if(!mapMgr||!mapMgr->mMapModel||!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z))return fail(e,"Egg source map query unavailable");
 bool found=false;float highest=0;
 for(CollGroup* group=mapMgr->getCollGroupList(p.x,p.z,false);group;group=group->mNextCollGroup){
  for(int i=0;i<group->mTriCount;++i){auto* triangle=group->mTriangleList[i];if(!triangle||triangle->mTriangle.mNormal.y<=0)continue;
   Vector3f point(p.x,p.y,p.z);if(triangle->inTriClampTo(point)&&std::isfinite(point.y)&&(!found||point.y>highest)){highest=point.y;found=true;}
  }
 }
 if(!found)return fail(e,"Egg source floor query has no authored static triangle");
 height=highest;e.clear();return true;
}
struct Native::Impl final:Engine {
 Services& services;Provider provider;Resources resource;bool loaded=false;
 p2posefamily::Bank bank{"ORIGINAL_EGG"};p2poseload::Shared shared;
 std::vector<int> frames;std::vector<Shape*> shapes;std::vector<Sample> samples;
 std::array<p2flyer::Sphere,2> spheres;std::array<int,2> jointIndices{};
 std::map<Creature*,std::unique_ptr<Track>> tracks;
 p2originalresource::EggContents contentsState;P2EggConfig config;
 unsigned fieldReserved=0,capturedReserved=0;
 std::string resourceFingerprint;
 explicit Impl(Services& s):services(s),provider(*this){}
 bool load(std::string& e){
  if(loaded)return true;
  if(!gsys||!tekiMgr)return fail(e,"Egg actual managers unavailable");
  auto* chassis=tekiMgr->getTekiShapeObject(TEKI_Palm);
  if(!chassis||!chassis->mShape||!chassis->mAnimMgr||!tekiMgr->getTekiParameters(TEKI_Palm)||!tekiMgr->getStrategy(TEKI_Palm))return fail(e,"Egg inert allocation chassis not preloaded before stage start");
  if(!services.contentsReady(e))return false;
  if(!services.breakEffectsReady(e)){std::printf("P2_ORIGINAL_EGG_PRESENTATION_DEFERRED source_jpa=0 source_audio=0 mechanics=required\n");e.clear();}
  frames.clear();shapes.clear();samples.clear();bank.reset();shared={};
  std::ifstream in("p2-original-egg-bank.txt");std::string word,name,stem;int count=0,duration=0;
  if(!(in>>word)||word!="P2_ORIGINAL_EGG_BANK_1")return fail(e,"Egg original physical bank missing");
  if(!(in>>word>>name>>count>>duration>>stem)||word!="clip"||name!="damage1"||count!=6||duration!=30||stem!="original_egg_damage1")return fail(e,"Egg authored damage1 clip row invalid");
  if(!(in>>word)||word!="frames")return fail(e,"Egg sampled frame list missing");
  for(int i=0;i<count;++i){int frame;if(!(in>>frame))return fail(e,"Egg sampled frame list truncated");frames.push_back(frame);}
  if(frames!=std::vector<int>({0,6,12,17,23,29}))return fail(e,"Egg source pose sample indices changed");
  std::size_t total=0;
  if(!p2posefamily::loadFamilyClip(bank,name,stem,count,duration,frames,shared,total,shapes,e))return false;
  for(int frame:frames){Sample sample;sample.frame=frame;
   for(int joint=0;joint<2;++joint){sample.joint[joint].makeIdentity();
    if(!(in>>word>>name)||word!="joint"||name!=(joint?"egg":"root"))return fail(e,"Egg root/egg authored joint sample missing");
    for(int r=0;r<3;++r)for(int c=0;c<4;++c)if(!(in>>sample.joint[joint].mMtx[r][c])||!std::isfinite(sample.joint[joint].mMtx[r][c]))return fail(e,"Egg authored joint matrix invalid");
   }samples.push_back(sample);
  }
  if(!(in>>word>>resource.parameters.health>>config.singleNectarChance>>config.doubleNectarChance>>config.mititesChance>>config.spicyChance>>config.bitterChance>>config.forcedDropType)||word!="parameters")return fail(e,"Egg source health/drop parameters missing");
  int checkSpray=0;if(!(in>>checkSpray)||checkSpray<0||checkSpray>1||config.forcedDropType<0||config.forcedDropType>7)return fail(e,"Egg source forced/drop spray controls invalid");
  config.health=resource.parameters.health;config.checkHasSpray=checkSpray!=0;
  for(float v:{config.singleNectarChance,config.doubleNectarChance,config.mititesChance,config.spicyChance,config.bitterChance})if(!std::isfinite(v)||v<0||v>1)return fail(e,"Egg source drop chance invalid");
  for(int i=0;i<2;++i){int parent=0,joint=0;float x=0,y=0,z=0,radius=0;
   if(!(in>>word>>parent>>joint>>x>>y>>z>>radius)||word!="collider"||parent!=(i?0:-1)||joint!=(i?0:1)||!std::isfinite(radius)||radius<=0||!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z))return fail(e,"Egg source collider invalid");
   spheres[i]={"none","____",radius,{x,y,z},parent};jointIndices[i]=joint;
  }
  if(in>>word)return fail(e,"Egg trailing bank data");
  if(!bank.owner()||!pelplant::Geometry::admits(*bank.owner())||!bank.clip("damage1"))return fail(e,"Egg flattened owned source geometry unavailable");
  std::string bytes,qualified;if(!readBytes("p2-original-egg-bank.txt",bytes,e))return false;qualified=digest(bytes);
  for(int i=0;i<6;++i){if(!readBytes(p2poseload::stemPath(true,"original_egg_damage1",i),bytes,e))return false;qualified+=digest(bytes);}
  resourceFingerprint=digest(qualified);
  resource.parametersLoaded=resource.model=resource.collider=resource.motion=resource.contents=resource.breakEffects=resource.capture=true;loaded=true;e.clear();return true;
 }
 bool resources(Resources& out,std::string& e)override{Heap heap;if(!load(e))return false;fieldReserved=capturedReserved=0;out=resource;return true;}
 bool commonResources(const CatalogRow& row,std::string& e)override{return pc_p2_original_drop_resources(row,e);}
 bool capacity(unsigned field,unsigned dependencies,std::string& e){if(!tekiMgr->hasModel(TEKI_Palm)||tekiMgr->getMax()-tekiMgr->getSize()<int(field+dependencies))return fail(e,"Egg complete field/captured actor capacity unavailable");return true;}
 bool reserve(unsigned n,std::string& e)override{if(!capacity(n,capturedReserved,e))return false;fieldReserved=n;return true;}
 bool reserveCaptured(unsigned n,std::string& e)override{if(!capacity(fieldReserved,n,e))return false;capturedReserved=n;return true;}
 bool allocate(Host& h,const Position& p,float facing,std::string& e)override{
  Heap heap;auto* actor=tekiMgr->newTeki(TEKI_Palm);if(!actor){e.clear();return true;}h.creature=actor;
  auto t=std::make_unique<Track>();tracks.emplace(actor,std::move(t));
  actor->clearTekiOptions();actor->clearCreaturePointers();actor->mTekiShape=tekiMgr->getTekiShapeObject(TEKI_Palm);
  actor->mTekiAnimator->init(&actor->mTekiShape->mAnimContext,actor->mTekiShape->mAnimMgr,tekiMgr->mMotionTable);
  actor->mDeadState=0;actor->mStateID=0;actor->mStoredDamage=0;actor->mDamageCount=0;actor->_3A4=0;actor->mPellet=nullptr;
  for(int i=0;i<4;++i)actor->mParticleGenerators[i]=nullptr;
  actor->mGenerator=h.generator;actor->mSRT.t.set(p.x,p.y,p.z);actor->mFaceDirection=facing;actor->mSRT.r.set(0,facing,0);actor->mSRT.s.set(1,1,1);
  actor->mLastPosition=actor->mSRT.t;actor->mGroundTriangle=nullptr;
  actor->mHealth=actor->mMaxHealth=resource.parameters.health;actor->mVelocity.set(0,0,0);actor->mTargetVelocity.set(0,0,0);
  actor->mCollisionRadius=15;actor->mSize=15;actor->setCreatureFlag(CF_DisableMovement);actor->setCreatureFlag(CF_IsAiDisabled);
  actor->setTekiOption(BTeki::TEKI_OPTION_VISIBLE);actor->setTekiOption(BTeki::TEKI_OPTION_ATARI);actor->setTekiOption(BTeki::TEKI_OPTION_ALIVE);actor->setTekiOption(BTeki::TEKI_OPTION_SHAPE_VISIBLE);
  auto& track=*tracks.at(actor);track.geometry=std::make_unique<pelplant::Geometry>(*bank.owner());track.presented.shape=&track.geometry->shape;track.presented.size(*bank.basePose());
  if(!track.collision.bind(actor,spheres.data(),2))return fail(e,"Egg source collider binding failed");follow(h);return true;
 }
 bool initialize(Host& h,std::string& e)override{
  auto* actor=static_cast<BTeki*>(h.creature);
  // GenObjectEnemy birthArg -> EnemyMgrBase::birth mDropGroup is literal byte.
  unsigned drop=h.dependent?0:h.row.enemy.birthType;
  if(drop>5)return fail(e,"Egg unsupported literal source DropGroup");
  h.dropGroup=drop>=1&&drop<=5;
  if(!h.dropGroup){float y=0;Position query{actor->mSRT.t.x,actor->mSRT.t.y+20,actor->mSRT.t.z};
   if(!services.groundHeight(query,y,e))return false;
   if(!std::isfinite(y))return fail(e,"Egg actual source floor query invalid");actor->mSRT.t.y=y;actor->mLastPosition=actor->mSRT.t;
  }
  follow(h);return true;
 }
 bool flags(Host& h,const Flags& f,std::string&)override{
  auto* actor=static_cast<BTeki*>(h.creature);
  if(f.invulnerable)actor->setTekiOption(BTeki::TEKI_OPTION_INVINCIBLE);else actor->clearTekiOption(BTeki::TEKI_OPTION_INVINCIBLE);
  if(f.living)actor->setTekiOption(BTeki::TEKI_OPTION_ORGANIC);else actor->clearTekiOption(BTeki::TEKI_OPTION_ORGANIC);
  if(f.constrained)actor->setCreatureFlag(CF_DisableMovement);else actor->resetCreatureFlag(CF_DisableMovement);
  // Always suppress Palm AI; native update owns Egg physics and motion.
  actor->setCreatureFlag(CF_IsAiDisabled);return true;
 }
 bool motion(Host& h,bool restart,bool stopped,std::string&)override{auto& t=*tracks.at(h.creature);if(restart)t.frame=0;t.stopped=stopped;return true;}
 bool capturedIdentity(Creature* parent,std::string& identity,std::string& e)override{return services.capturedIdentity(parent,identity,e);}
 bool startCapture(Host& h,Creature* parent,void* matrix,std::string& e)override{
  auto& t=*tracks.at(h.creature);p2originalresource::SourceIdentity identity;
  if(!services.capturedSourceIdentity(parent,identity,e))return false;
  if(identity.fingerprint.size()!=64||(identity.uid&0xff000000u)!=0x52000000u||!identity.epoch||!identity.activation)return fail(e,"Egg capture lacks full authoritative parent source incarnation");
  t.dependentIdentity=identity;t.hasDependentIdentity=true;t.capture=static_cast<Matrix4f*>(matrix);auto* actor=static_cast<BTeki*>(h.creature);
  actor->mSRT.t.set(t.capture->mMtx[0][3],t.capture->mMtx[1][3],t.capture->mMtx[2][3]);actor->mVelocity.set(0,0,0);actor->mTargetVelocity.set(0,0,0);follow(h);return true;
 }
 bool endCapture(Host& h,std::string&)override{tracks.at(h.creature)->capture=nullptr;return true;}
 bool update(Host& h,float dt,std::string& e)override{
  auto* actor=static_cast<BTeki*>(h.creature);auto& t=*tracks.at(h.creature);
  if(t.capture){actor->mSRT.t.set(t.capture->mMtx[0][3],t.capture->mMtx[1][3],t.capture->mMtx[2][3]);actor->mVelocity.set(0,0,0);actor->mTargetVelocity.set(0,0,0);}
  else if(!h.flags.constrained){actor->mTargetVelocity=actor->mGroundTriangle?Vector3f(0,0,0):actor->mVelocity;actor->moveNew(dt);if(!tracks.count(actor)){e.clear();return true;}}
  actor->mGrid.updateGrid(actor->mSRT.t);actor->mGrid.updateAIGrid(actor->mSRT.t,false);follow(h);return true;
 }
 bool contents(Host& h,std::string& e)override{
  p2originalresource::SourceIdentity identity;
  if(h.dependent){auto& t=*tracks.at(h.creature);if(!t.hasDependentIdentity)return fail(e,"Egg contents missing captured source incarnation");identity=t.dependentIdentity;}
  else if(!services.sourceIdentity(h,identity,e))return false;
  auto p=h.creature->getPosition();p2originalresource::ContentsRecord record;
  return contentsState.generate(identity,config,{p.x,p.y,p.z},services,record,e);
 }
 bool breakEffects(Host& h,std::string& e)override{return services.breakEffects(h.creature,e);}
 bool kill(Host& h,std::string&)override{h.creature->kill(false);return true;}
 bool cleanup(Host& h,std::string&)override{
  auto it=tracks.find(h.creature);if(it==tracks.end())return true;
  std::vector<Creature*> attached;Stickers stickers(h.creature);Iterator iterator(&stickers);CI_LOOP(iterator)attached.push_back(*iterator);
  for(auto* p:attached){InteractFlick flick(h.creature,0,0,-1000);p->stimulate(flick);}
  it->second->capture=nullptr;it->second->collision.detach(static_cast<BTeki*>(h.creature));tracks.erase(it);
  // Scene disposal is not StateWait destruction. Detach WITHOUT informDeath.
  h.creature->mGenerator=nullptr;h.creature->kill(false);return true;
 }
 Matrix4f root(Host& h){auto& t=*tracks.at(h.creature);Matrix4f result;if(t.capture)result=*t.capture;else result.makeSRT(h.creature->mSRT.s,Vector3f(0,h.creature->mFaceDirection,0),h.creature->mSRT.t);return result;}
 bool context(Host& h,SnapshotContext& out,std::string& e)const{
  auto it=tracks.find(h.creature);if(!loaded||it==tracks.end()||resourceFingerprint.empty()||!bank.clip("damage1")||frames!=std::vector<int>({0,6,12,17,23,29})||samples.size()!=6)return fail(e,"Egg snapshot source bank/physical resources unavailable");
  SnapshotContext next;next.resourceFingerprint=resourceFingerprint;next.maxHealth=resource.parameters.health;next.dependent=h.dependent;next.dropGroup=h.dropGroup;
  if(h.dependent){if(!it->second->hasDependentIdentity||h.creature->mGenerator)return fail(e,"Egg snapshot dependent identity/generator boundary invalid");next.identity=it->second->dependentIdentity;}
  else {
   if(!h.token||!h.generator||h.creature->mGenerator!=h.generator||!services.sourceIdentity(h,next.identity,e))return fail(e,"Egg snapshot standalone exact generator/incarnation unresolved");
   if(next.identity.uid!=h.row.enemy.uid||next.identity.ordinal!=h.ordinal)return fail(e,"Egg snapshot source identity belongs to another physical row/ordinal");
  }
  if(h.captured){if(!h.parent||!it->second->capture||!services.capturedSourceIdentity(h.parent,next.actualParent,e))return fail(e,"Egg snapshot actual source capture graph unresolved");
   for(int r=0;r<3;++r)for(int c=0;c<4;++c)if(!std::isfinite(it->second->capture->mMtx[r][c]))return fail(e,"Egg snapshot capture matrix nonfinite");
   next.actualCaptureBound=true;next.capturePosition={it->second->capture->mMtx[0][3],it->second->capture->mMtx[1][3],it->second->capture->mMtx[2][3]};
  }else if(it->second->capture||h.parent)return fail(e,"Egg independent body retains native capture pointer");
  out=std::move(next);e.clear();return true;
 }
 void follow(Host& h){auto& t=*tracks.at(h.creature);float frame=std::min(t.frame,29.0f);std::size_t a=0;while(a+1<samples.size()&&samples[a+1].frame<=frame)++a;std::size_t b=std::min(a+1,samples.size()-1);float w=a==b?0:(frame-samples[a].frame)/float(samples[b].frame-samples[a].frame);Matrix4f worldRoot=root(h);
  for(int k=0;k<2;++k){Matrix4f local,world;local.makeIdentity();int j=jointIndices[k];for(int r=0;r<3;++r)for(int c=0;c<4;++c)local.mMtx[r][c]=(1-w)*samples[a].joint[j].mMtx[r][c]+w*samples[b].joint[j].mMtx[r][c];worldRoot.multiplyTo(local,world);
   auto* part=t.collision.part(k);if(!part)continue;auto off=spheres[k].offset;
   part->mCentre.set(world.mMtx[0][3]+world.mMtx[0][0]*off.x+world.mMtx[0][1]*off.y+world.mMtx[0][2]*off.z,world.mMtx[1][3]+world.mMtx[1][0]*off.x+world.mMtx[1][1]*off.y+world.mMtx[1][2]*off.z,world.mMtx[2][3]+world.mMtx[2][0]*off.x+world.mMtx[2][1]*off.y+world.mMtx[2][2]*off.z);
   part->mRadius=spheres[k].radius;Matrix4f cameraRotation,jointRotation=world;cameraRotation.makeIdentity();for(int r=0;r<3;++r){jointRotation.mMtx[r][3]=0;for(int c=0;c<3;++c)cameraRotation.mMtx[r][c]=invCamMat.mMtx[c][r];}cameraRotation.multiplyTo(jointRotation,part->mJointMatrix);
  }
 }
};
Native::Native(Services& s):m(std::make_unique<Impl>(s)){instances().insert(this);}
Native::~Native(){if(!m->tracks.empty()||m->provider.size()){std::fprintf(stderr,"Egg native destroyed with owned actors\n");std::abort();}instances().erase(this);}
Provider& Native::provider(){return m->provider;}
bool Native::owns(const Creature* actor)const{return m->tracks.count(const_cast<Creature*>(actor))!=0;}
p2originalresource::EggContents& Native::contents(){return m->contentsState;}
void Native::forget(BTeki* actor){auto it=m->tracks.find(actor);if(it!=m->tracks.end()){it->second->capture=nullptr;it->second->collision.detach(actor);m->tracks.erase(it);}m->provider.retiredNative(actor);}
bool Native::tick(BTeki* actor,float dt,std::string& e){Heap heap;auto* h=m->provider.lookup(actor);if(!h||!std::isfinite(dt)||dt<0)return fail(e,"Egg native update outside provider");auto& t=*m->tracks.at(actor);Event event=Event::None;
 if(!t.stopped){t.frame+=30*dt;if(t.frame>=30){t.frame=30;event=Event::End;}}
 if(!m->provider.tick(actor,dt,event,e))return false;
 // Actual kill may have synchronously removed Host and Track.
 h=m->provider.lookup(actor);if(!h||!m->tracks.count(actor))return true;
 actor->mHealth=h->health;actor->mStoredDamage=0;m->tracks.at(actor)->presented.advance(dt);m->follow(*h);return true;
}
bool Native::world(BTeki* actor,Matrix4f& out,std::string& e)const{auto* h=m->provider.lookup(actor);if(!h||!m->tracks.count(actor))return fail(e,"Egg native world outside provider");out=m->root(*h);return true;}
bool Native::identity(BTeki* actor,p2originalresource::SourceIdentity& out,std::string& e)const{auto* h=m->provider.lookup(actor);auto t=m->tracks.find(actor);if(!h||t==m->tracks.end())return fail(e,"Egg source identity outside provider");if(h->dependent){if(!t->second->hasDependentIdentity)return fail(e,"Egg source capture identity unresolved");out=t->second->dependentIdentity;e.clear();return true;}return m->services.sourceIdentity(*h,out,e);}
bool Native::captureLink(BTeki* actor,Creature*& actualParent,void*& actualMatrix,std::string& e)const{
 auto* h=m->provider.lookup(actor);auto it=m->tracks.find(actor);
 if(!h||it==m->tracks.end()||!h->dependent||!h->captured||!h->parent||!it->second->capture||!it->second->hasDependentIdentity)return fail(e,"Egg capture link outside actual owned captured dependency");
 SnapshotContext context;if(!m->context(*h,context,e))return false;
 if(!context.actualCaptureBound||!(context.identity==context.actualParent))return fail(e,"Egg capture link lacks matching bound source incarnation/matrix");
 actualParent=h->parent;actualMatrix=it->second->capture;e.clear();return true;
}
bool Native::snapshot(BTeki* actor,Snapshot& out,std::string& e)const{
 auto* h=m->provider.lookup(actor);auto it=m->tracks.find(actor);if(!h||it==m->tracks.end())return fail(e,"Egg snapshot outside owned physical body");SnapshotContext context;if(!m->context(*h,context,e))return false;
 Snapshot next;next.identity=context.identity;next.resourceFingerprint=context.resourceFingerprint;
 next.position={actor->mSRT.t.x,actor->mSRT.t.y,actor->mSRT.t.z};next.velocity={actor->mVelocity.x,actor->mVelocity.y,actor->mVelocity.z};next.targetVelocity={actor->mTargetVelocity.x,actor->mTargetVelocity.y,actor->mTargetVelocity.z};next.scale={actor->mSRT.s.x,actor->mSRT.s.y,actor->mSRT.s.z};next.facing=actor->mFaceDirection;
 next.health=h->health;next.flickTimer=h->flickTimer;next.flags=h->flags;next.sourceFrame=it->second->frame;next.stopped=it->second->stopped;
 next.dependent=h->dependent;next.captured=h->captured;next.falling=h->falling;next.dropGroup=h->dropGroup;next.contentsGenerated=h->contentsGenerated;next.effectsEmitted=h->effectsEmitted;next.killRequested=h->killRequested;
 if(h->captured){next.hasParent=true;next.parentIdentity=context.actualParent;}
 if(!validateSnapshot(next,context,e))return false;out=std::move(next);e.clear();return true;
}
bool Native::preflight(BTeki* actor,const Snapshot& saved,std::string& e)const{auto* h=m->provider.lookup(actor);if(!h)return fail(e,"Egg restore preflight outside owned body");SnapshotContext context;if(!m->context(*h,context,e))return false;return validateSnapshot(saved,context,e);}
bool Native::apply(BTeki* actor,const Snapshot& saved,std::string& e){
 if(!preflight(actor,saved,e))return false;
 auto* h=m->provider.lookup(actor);auto& t=*m->tracks.at(actor);
 // Preflight already validated the existing capture graph. This assignment
 // never captures/releases/births/kills a creature or informs its generator.
 h->health=saved.health;h->flickTimer=saved.flickTimer;h->flags=saved.flags;h->falling=saved.falling;h->contentsGenerated=saved.contentsGenerated;h->effectsEmitted=saved.effectsEmitted;h->killRequested=saved.killRequested;
 actor->mSRT.t.set(saved.position.x,saved.position.y,saved.position.z);actor->mLastPosition=actor->mSRT.t;actor->mSRT.s.set(saved.scale.x,saved.scale.y,saved.scale.z);actor->mFaceDirection=saved.facing;actor->mSRT.r.set(0,saved.facing,0);
 actor->mVelocity.set(saved.velocity.x,saved.velocity.y,saved.velocity.z);actor->mTargetVelocity.set(saved.targetVelocity.x,saved.targetVelocity.y,saved.targetVelocity.z);actor->mHealth=saved.health;actor->mMaxHealth=h->parameters.health;actor->mStoredDamage=0;actor->mGroundTriangle=nullptr;
 t.frame=saved.sourceFrame;t.stopped=saved.stopped;std::string ignored;m->flags(*h,saved.flags,ignored);m->follow(*h);actor->mGrid.updateGrid(actor->mSRT.t);actor->mGrid.updateAIGrid(actor->mSRT.t,false);e.clear();return true;
}
bool Native::draw(BTeki* actor,Graphics& gfx,const Matrix4f& view,std::string& e){auto* h=m->provider.lookup(actor);if(!h||!gfx.mCamera)return fail(e,"Egg native draw outside provider");auto& t=*m->tracks.at(actor);const auto* clip=m->bank.clip("damage1");float frame=std::min(t.frame,29.0f);
 if(!clip||!p2pose::present(t.presented,"damage1",clip->poses.size(),[clip](std::size_t i)->const p2pose::Pose&{return clip->poses[i];},clip->frames,frame,p2motion::tunables(),clip->seamContinuous).ok)return fail(e,"Egg source pose drawing failed");
 gfx.useMatrix(Matrix4f::ident,0);auto& shape=t.geometry->shape;shape.updateAnim(gfx,view,nullptr,actor);shape.drawshape(gfx,*gfx.mCamera,nullptr);return true;
}
} }
namespace {
p2original::egg::Native* owner(BTeki* actor){for(auto* n:p2original::egg::instances())if(n->owns(actor))return n;return nullptr;}
void require(bool okay,const std::string& e){if(!okay){std::fprintf(stderr,"P2_ORIGINAL_EGG refusal: %s\n",e.c_str());std::abort();}}
}
bool pc_p2_original_egg_update(BTeki* actor){auto* n=owner(actor);if(!n)return false;std::string e;require(n->tick(actor,gsys->getFrameTime(),e),e);return true;}
bool pc_p2_original_egg_refresh(BTeki* actor,Graphics& gfx){auto* n=owner(actor);if(!n)return false;if(!gfx.mCamera)return true;Matrix4f world,view;std::string e;require(n->world(actor,world,e),e);gfx.mCamera->mLookAtMtx.multiplyTo(world,view);require(n->draw(actor,gfx,view,e),e);return true;}
bool pc_p2_original_egg_damage(BTeki* actor,float amount,float flick,bool& accepted){auto* n=owner(actor);if(!n)return false;std::string e;accepted=n->provider().damage(actor,amount,flick,e);require(e.empty(),e);return true;}
bool pc_p2_original_egg_press(BTeki* actor,bool& accepted){auto* n=owner(actor);if(!n)return false;std::string e;accepted=n->provider().press(actor,e);require(e.empty(),e);return true;}
bool pc_p2_original_egg_bounce(BTeki* actor){auto* n=owner(actor);if(!n)return false;std::string e;require(n->provider().bounce(actor,e),e);return true;}
bool pc_p2_original_egg_collision(BTeki* actor,const CollEvent& event){auto* n=owner(actor);if(!n)return false;std::string e;require(n->provider().collision(actor,event.mCollider,event.mCollider&&event.mCollider->mObjType==OBJTYPE_Teki,e),e);return true;}
void pc_p2_original_egg_forget(BTeki* actor){auto* n=owner(actor);if(n)n->forget(actor);}
