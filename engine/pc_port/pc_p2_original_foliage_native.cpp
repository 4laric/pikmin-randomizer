#include "pc_p2_original_foliage_native.h"
#include "pc_p2_original_foliage_lod.h"
#include "pc_p2_original_pelplant_geometry.h"
#include "pc_p2_pose_family.h"
#include "pc_p2_flyer_coll.h"
#include "teki.h"
#include "Generator.h"
#include "Graphics.h"
#include "Camera.h"
#include "NaviMgr.h"
#include "pc_coop.h"
#include "netplay/pc_netplay_policy.h"
#include "Collision.h"
#include "SoundID.h"
#include "SoundMgr.h"
#include "Stickers.h"
#include "Interactions.h"
#include <fstream>
#include <sstream>
#include <set>
#include <cstdio>
#include <cstdlib>
extern Matrix4f invCamMat;
extern "C" void pc_gfx_shadow_exclude(int);
namespace p2original { namespace foliage {
namespace {
struct HeapScope {int previous;HeapScope():previous(gsys->setHeap(SYSHEAP_App)){}~HeapScope(){gsys->setHeap(previous);}};
bool reject(std::string& e,const char* text){e=text;return false;}
[[noreturn]] void fail(const std::string& e){std::fprintf(stderr,"P2_ORIGINAL_FOLIAGE refusal: %s\n",e.c_str());std::abort();}
std::set<Native*>& instances(){static std::set<Native*> set;return set;}
struct Bank {
 unsigned source=0;std::string name,stem;int count=0,duration=0;
 float health=0,territory=0,privateRadius=0,home=0,lod=0,floor=0;
 bool params=false,layer=false,postshadow=false;
 std::vector<int> frames;std::vector<Shape*> shapes;
 p2posefamily::Bank poses{"ORIGINAL_FOLIAGE"};p2poseload::Shared shared;
 std::vector<p2flyer::Sphere> spheres;
 std::vector<std::array<char,5>> ids,codes;
 std::vector<int> jointIndices;
 std::map<int,Matrix4f> staticJoints;
};
struct Track {
 Bank* bank=nullptr;bool nativeDying=false,visible=true;
 std::unique_ptr<pelplant::Geometry> geometry;
 P2FlyerColl collision;p2pose::Track presented;
};
}
struct Native::Impl final:Engine {
 Provider provider;std::map<unsigned,std::unique_ptr<Bank>> banks;
 std::map<Creature*,std::unique_ptr<Track>> tracks;bool loaded=false;
 Impl():provider(*this){}
 bool load(std::string& e){
  if(loaded)return true; banks.clear();
  std::ifstream in("foliage-bank.txt");std::string line;
  if(!std::getline(in,line))return reject(e,"original foliage resource bank absent");
  if(!line.empty()&&line.back()=='\r')line.pop_back();
  if(line!="P2_ORIGINAL_FOLIAGE_1")return reject(e,"original foliage resource bank version mismatch");
  while(std::getline(in,line)){
   if(line.empty())continue;std::istringstream row(line);std::string word;unsigned source;
   if(!(row>>word>>source)||!supported(source))return reject(e,"unknown source in original foliage bank");
   if(word=="species"){
    if(banks.count(source))return reject(e,"duplicate original foliage bank");
    auto b=std::make_unique<Bank>();b->source=source;
    if(!(row>>b->name>>b->stem>>b->count>>b->duration)||b->count<2||b->count>64||b->duration<2||b->duration>10000)return reject(e,"invalid original foliage species row");
    const std::string name=source==46?"Tanpopo":source==47?"Clover":source==49?"Ooinu_s":source==51?"Wakame_s":source==52?"Wakame_l":source==80?"Tukushi":source==90?"Zenmai":source==92?"KareOoinu_l":source==91?"KareOoinu_s":"Nekojarashi";
    const std::string stem=source==46?"flora_Tanpopo_tanpopo":source==47?"flora_Clover_clover":source==49?"flora_Ooinu_s_ooinu_s":source==51?"flora_Wakame_s_wakame_s":source==52?"flora_Wakame_l_wakame_l":source==80?"flora_Tukushi_tukushi":source==90?"flora_Zenmai_zenmai":source==92?"flora_KareOoinu_l_karaooinu_l":source==91?"flora_KareOoinu_s_kareooinu_s":"flora_Nekojarashi_nekojarashi";
    if(b->name!=name||b->stem!=stem)return reject(e,"original foliage model identity mismatch");
    banks.emplace(source,std::move(b));
   }else {
    auto it=banks.find(source);if(it==banks.end())return reject(e,"foliage data before species row");auto& b=*it->second;
    if(word=="frames"){
     if(!b.frames.empty())return reject(e,"duplicate foliage sampled frames");
     for(int i=0;i<b.count;++i){int f;if(!(row>>f))return reject(e,"truncated foliage sampled frames");b.frames.push_back(f);}
     if(!p2posefamily::Bank::validFrames(b.frames,b.count,b.duration))return reject(e,"invalid foliage sampled frames");
    }else if(word=="params"){
     if(b.params||!(row>>b.health>>b.territory>>b.privateRadius>>b.home>>b.lod>>b.floor))return reject(e,"invalid foliage common parameters");
     for(float v:{b.health,b.territory,b.privateRadius,b.home,b.lod,b.floor})if(!std::isfinite(v)||v<0)return reject(e,"nonfinite/negative foliage parameter");
     if(b.health<=0||b.lod<=0||b.home<=0||b.privateRadius<=0)return reject(e,"degenerate foliage common parameters");b.params=true;
    }else if(word=="layer"){
     std::string layer;if(b.layer||!(row>>layer)||(source==88?layer!="postshadow":layer!="normal"))return reject(e,"foliage source render layer mismatch");b.layer=true;b.postshadow=layer=="postshadow";
    }else if(word=="joint"){
     int frame,joint;Matrix4f m;m.makeIdentity();if(!(row>>frame>>joint)||frame<0||frame>=b.duration||joint<0||joint>255)return reject(e,"invalid foliage joint identity");
     for(int r=0;r<3;++r)for(int c=0;c<4;++c)if(!(row>>m.mMtx[r][c])||!std::isfinite(m.mMtx[r][c]))return reject(e,"invalid foliage joint matrix");
     if(frame==0&&!b.staticJoints.emplace(joint,m).second)return reject(e,"duplicate foliage initial joint");
    }else if(word=="collider"){
     int index,joint,parent,attr;std::string id,code;p2flyer::Sphere sphere;
     if(!(row>>index>>joint>>parent>>id>>code>>attr>>sphere.offset.x>>sphere.offset.y>>sphere.offset.z>>sphere.radius)
      ||index!=int(b.spheres.size())||index>=p2flyer::kMaxSpheres||joint<0||parent>=index||parent<-1||attr!=0||id.size()!=4||code.size()!=4
      ||!std::isfinite(sphere.radius)||sphere.radius<=0||!std::isfinite(sphere.offset.x)||!std::isfinite(sphere.offset.y)||!std::isfinite(sphere.offset.z))return reject(e,"invalid foliage retail collider");
     if(id=="none")id="f00"+std::to_string(index);
     std::array<char,5> a{},c{};std::copy(id.begin(),id.end(),a.begin());std::copy(code.begin(),code.end(),c.begin());
     b.ids.push_back(a);b.codes.push_back(c);sphere.parent=parent;b.spheres.push_back(sphere);b.jointIndices.push_back(joint);
    }else return reject(e,"unknown foliage resource row");
   }
   if(row>>word)return reject(e,"trailing foliage resource row values");
  }
  if(banks.empty())return reject(e,"empty foliage bank");
  std::size_t total=0;
  for(auto& entry:banks){auto& b=*entry.second;
   if(!b.params||!b.layer||b.frames.empty()||b.spheres.empty())return reject(e,"incomplete foliage physical resource bank");
   if(b.source==92&&(b.territory!=45.f||b.lod!=80.f))return reject(e,"source92 literal sphere LOD mismatch");
   // All admitted plain species have literal anonymous joint-zero trees. Do
   // not admit a truncated Dandelion bank that silently loses its leaf spheres.
   const std::size_t expected=b.source==46?5:2;
   const float rootRadius=(b.source==46||b.source==92)?50.f:b.source==51?10.f:(b.source==47||b.source==49||b.source==91)?30.f:20.f;
   const float childRadius=b.source==92?35.f:b.source==46?25.f:b.source==51?5.f:(b.source==47||b.source==49||b.source==91)?20.f:10.f;
   if(b.spheres.size()!=expected)return reject(e,"foliage literal collider count mismatch");
   for(std::size_t i=0;i<expected;++i){
    const auto& sphere=b.spheres[i];
    const float x=i==2?40.f:i==3?-50.f:i==4?30.f:0.f;
    const float z=i==2?25.f:i==4?-40.f:0.f;
    const float radius=i==0?rootRadius:i==1?childRadius:20.f;
    if(b.jointIndices[i]!=0||sphere.parent!=(i==0?-1:0)||sphere.offset.x!=x||sphere.offset.y!=0||sphere.offset.z!=z||sphere.radius!=radius
     ||std::string(b.codes[i].data())!="____"||std::string(b.ids[i].data())!="f00"+std::to_string(i))return reject(e,"foliage literal collider geometry mismatch");
   }
   for(std::size_t i=0;i<b.spheres.size();++i){if(!b.staticJoints.count(b.jointIndices[i]))return reject(e,"foliage collider joint unresolved");b.spheres[i].id=b.ids[i].data();b.spheres[i].code=b.codes[i].data();}
   if(!p2posefamily::loadFamilyClip(b.poses,b.name,b.stem,b.count,b.duration,b.frames,b.shared,total,b.shapes,e))return false;
   if(!b.poses.ready()||!b.poses.owner()||!pelplant::Geometry::admits(*b.poses.owner()))return reject(e,"foliage geometry requires source flattened single-joint physical bank");
  }
  loaded=true;return true;
 }
 bool visible(const BTeki* actor,const Track& t,Camera& camera)const{
  // Match the maintained camera's simulation-pass visibility policy before
  // consulting presentation planes; local-window culling must not enter netplay.
  if(pc_netplay_present_sim_pass())return pc_netplay_sim_visible(true);
  const auto& b=*t.bank;
  if(!cylinderSource(b.source)){
   Vector3f center=actor->mSRT.t;center.y+=b.territory;
   return camera.isPointVisible(center,b.lod);
  }
  Position position{actor->mSRT.t.x,actor->mSRT.t.y,actor->mSRT.t.z};
  const auto cylinder=sourceCylinder(b.source,position,actor->mFaceDirection,b.home,b.privateRadius);
  for(int i=0;i<camera.mActivePlaneCount;++i){
   const auto* p=camera.mPlanePointers[i];if(!p)continue;
   const auto& plane=p->mPlane;
   if(!cylinderPlaneVisible(cylinder,plane.mNormal.x,plane.mNormal.y,plane.mNormal.z,plane.mOffset))return false;
  }
  return true;
 }
 void simulationVisibility(const BTeki* actor,Track& t){
  if(pc_netplay_present_sim_pass()){t.visible=pc_netplay_sim_visible(true);return;}
  // A second single-player captain does not imply a presented second viewport.
  // Co-op combines initialized native cameras; merged co-op viewport eligibility
  // still needs separate qualification against the rendering owner's policy.
  bool visibleInAny=false;
  if(naviMgr){
   const bool coop=pc_coop_active();
   const int count=coop?naviMgr->getNaviCount():1;
   for(int i=0;i<count;++i){
    auto* navi=coop?naviMgr->getNavi(i):naviMgr->getActiveNavi();
    auto* camera=navi?navi->mNaviCamera:nullptr;
    if(camera&&camera->mActivePlaneCount>0)visibleInAny=visibleInAny||visible(actor,t,*camera);
   }
  }
  t.visible=visibleInAny;
 }
 bool resources(unsigned source,Resources& out,std::string& e)override{
  if(!gsys||!tekiMgr)return reject(e,"foliage native managers unavailable");HeapScope heap;
  if(!load(e))return false;auto i=banks.find(source);if(i==banks.end())return reject(e,"requested original foliage source bank unavailable");
  auto* chassis=tekiMgr->getTekiShapeObject(TEKI_Palm);
  if(!chassis||!chassis->mShape||!chassis->mAnimMgr||!tekiMgr->getTekiParameters(TEKI_Palm)||!tekiMgr->getStrategy(TEKI_Palm))return reject(e,"foliage allocation chassis not preloaded before original admission");
  auto& b=*i->second;out={true,true,true,b.health,unsigned(b.duration)};e.clear();return true;
 }
 bool reserve(unsigned count,std::string& e)override{
  if(!tekiMgr||tekiMgr->getMax()-tekiMgr->getSize()<int(count)||!tekiMgr->hasModel(TEKI_Palm))return reject(e,"foliage actual native pool insufficient or not initialized");e.clear();return true;
 }
 bool allocate(Host& h,const Position& p,float facing,std::string& e)override{
  HeapScope heap;auto* actor=tekiMgr->newTeki(TEKI_Palm);if(!actor)return reject(e,"foliage manager allocation failed");h.creature=actor;
  auto t=std::make_unique<Track>();t->bank=banks.at(h.row.enemy.source).get();tracks.emplace(actor,std::move(t));auto& track=*tracks.at(actor);auto& b=*track.bank;
  actor->clearTekiOptions();actor->clearCreaturePointers();actor->mTekiShape=tekiMgr->getTekiShapeObject(TEKI_Palm);
  actor->mTekiAnimator->init(&actor->mTekiShape->mAnimContext,actor->mTekiShape->mAnimMgr,tekiMgr->mMotionTable);
  actor->mDeadState=actor->mStateID=actor->mDamageCount=0;actor->_3A4=0;actor->mStoredDamage=0;actor->mPellet=nullptr;
  for(int i=0;i<4;++i)actor->mParticleGenerators[i]=nullptr;
  // Surface owns a native generator; genuine cave births deliberately carry
  // no P1 generator. Cave registry associations remain with the floor caller.
  actor->mGenerator=h.generator;actor->mSRT.t.set(p.x,p.y,p.z);actor->mFaceDirection=facing;actor->mSRT.r.set(0,facing,0);actor->mSRT.s.set(1,1,1);
  actor->mHealth=actor->mMaxHealth=b.health;actor->mVelocity.set(0,0,0);actor->mVolatileVelocity.set(0,0,0);actor->mTargetVelocity.set(0,0,0);actor->mCollisionRadius=b.spheres[0].radius;actor->mSize=b.spheres[0].radius;
  actor->setCreatureFlag(CF_DisableMovement);actor->setCreatureFlag(CF_IsAiDisabled);
  for(unsigned option:{BTeki::TEKI_OPTION_VISIBLE,BTeki::TEKI_OPTION_ATARI,BTeki::TEKI_OPTION_ALIVE,BTeki::TEKI_OPTION_SHAPE_VISIBLE,BTeki::TEKI_OPTION_INVINCIBLE})actor->setTekiOption(option);
  actor->clearTekiOption(BTeki::TEKI_OPTION_ORGANIC);actor->clearTekiOption(BTeki::TEKI_OPTION_GRAVITATABLE);
  const auto* base=b.poses.basePose();if(!base)return reject(e,"foliage source base pose absent");
  track.geometry=std::make_unique<pelplant::Geometry>(*b.poses.owner());track.presented.shape=&track.geometry->shape;track.presented.size(*base);
  if(!track.collision.bind(actor,b.spheres.data(),int(b.spheres.size())))return reject(e,"foliage source static collider bind failed");
  follow(actor,track);actor->mGrid.updateGrid(actor->mSRT.t);actor->mGrid.updateAIGrid(actor->mSRT.t,false);e.clear();return true;
 }
 void follow(BTeki* actor,Track& t){
  // Source model/collider matrix is established onInit and never simulated.
  // Re-seat camera-relative collision rotation only; animation never drags it.
  Matrix4f root;root.makeSRT(actor->mSRT.s,Vector3f(0,actor->mFaceDirection,0),actor->mSRT.t);
  auto& b=*t.bank;for(std::size_t i=0;i<b.spheres.size();++i){auto* part=t.collision.part(int(i));if(!part)fail("foliage collider part missing");
   Matrix4f world;root.multiplyTo(b.staticJoints.at(b.jointIndices[i]),world);const auto& s=b.spheres[i];
   part->mCentre.set(world.mMtx[0][3]+world.mMtx[0][0]*s.offset.x+world.mMtx[0][1]*s.offset.y+world.mMtx[0][2]*s.offset.z,
    world.mMtx[1][3]+world.mMtx[1][0]*s.offset.x+world.mMtx[1][1]*s.offset.y+world.mMtx[1][2]*s.offset.z,
    world.mMtx[2][3]+world.mMtx[2][0]*s.offset.x+world.mMtx[2][1]*s.offset.y+world.mMtx[2][2]*s.offset.z);part->mRadius=s.radius;
   Matrix4f cameraRotation;cameraRotation.makeIdentity();for(int r=0;r<3;++r)for(int c=0;c<3;++c)cameraRotation.mMtx[r][c]=invCamMat.mMtx[c][r];
   world.mMtx[0][3]=world.mMtx[1][3]=world.mMtx[2][3]=0;cameraRotation.multiplyTo(world,part->mJointMatrix);
  }
 }
 bool cleanup(Host& h,std::string&)override{
  auto i=tracks.find(h.creature);if(i==tracks.end())return true;
  std::vector<Creature*> snapshot;Stickers stuck(h.creature);Iterator it(&stuck);CI_LOOP(it)snapshot.push_back(*it);
  for(Creature* p:snapshot){InteractFlick flick(h.creature,0,0,-1000);p->stimulate(flick);}
  const bool dying=i->second->nativeDying;i->second->collision.detach(static_cast<BTeki*>(h.creature));tracks.erase(i);
  if(!dying)h.creature->kill(false);return true;
 }
 bool touchSound(Host&,Creature*,std::string&)override{
  // Native equivalent touch-leaf cue; P2 sample bank is not part of this port.
  SeSystem::playPlayerSe(SE_ORIMA_TOUCHPLANTS);return true;
 }
};
Native::Native():m(std::make_unique<Impl>()){instances().insert(this);}
Native::~Native(){if(m->provider.size())fail("foliage provider destroyed with live native roots");instances().erase(this);}
Provider& Native::provider(){return m->provider;}
bool Native::owns(const Creature* c)const{return m->tracks.count(const_cast<Creature*>(c))&&m->provider.lookup(c)!=nullptr;}
bool Native::tick(BTeki* actor,float dt,std::string& e){
 auto* h=m->provider.lookup(actor);if(!h)return false;auto& t=*m->tracks.at(actor);
 m->simulationVisibility(actor,t);
 if(!m->provider.tick(actor,dt,t.visible,e))return false;
 actor->mVelocity.set(0,0,0);actor->mVolatileVelocity.set(0,0,0);actor->mTargetVelocity.set(0,0,0);actor->mStoredDamage=0;actor->mHealth=t.bank->health;
 actor->mSRT.t.set(h->position.x,h->position.y,h->position.z);actor->mGrid.updateGrid(actor->mSRT.t);actor->mGrid.updateAIGrid(actor->mSRT.t,false);
 t.presented.advance(dt);m->follow(actor,t);return true;
}
bool Native::draw(BTeki* actor,Graphics& gfx,const Matrix4f& view,bool postShadow){
 auto* h=m->provider.lookup(actor);if(!h)return false;if(!gfx.mCamera)return true;auto& t=*m->tracks.at(actor);auto& b=*t.bank;
 if(b.postshadow!=postShadow)return true;
 if(!m->visible(actor,t,*gfx.mCamera))return true;
 const auto* clip=b.poses.clip(b.name);if(!clip)fail("foliage pose clip unresolved");
 p2motion::Tunables tune=p2motion::tunables();tune.crossfadeSeconds=0;
 if(!p2pose::present(t.presented,b.name,clip->poses.size(),[clip](std::size_t i)->const p2pose::Pose&{return clip->poses[i];},clip->frames,h->frame,tune,false).ok)fail("foliage source pose presentation failed");
 gfx.useMatrix(Matrix4f::ident,0);pc_gfx_shadow_exclude(1);
 t.geometry->shape.updateAnim(gfx,view,nullptr,actor);t.geometry->shape.drawshape(gfx,*gfx.mCamera,nullptr);
 pc_gfx_shadow_exclude(0);return true;
}
void Native::postShadow(Graphics& gfx){
 if(!gfx.mCamera)return;
 for(const auto& i:m->tracks){if(!i.second->bank->postshadow)continue;auto* actor=static_cast<BTeki*>(i.first);
  Matrix4f root,view;root.makeSRT(actor->mSRT.s,Vector3f(0,actor->mFaceDirection,0),actor->mSRT.t);
  gfx.mCamera->mLookAtMtx.multiplyTo(root,view);draw(actor,gfx,view,true);
 }
}bool Native::collision(BTeki* actor,Creature* collider,std::string& e){
 auto* h=m->provider.lookup(actor);if(!h)return false;auto& t=*m->tracks.at(actor);
 m->simulationVisibility(actor,t);
 return m->provider.collision(actor,collider,collider&&collider->mObjType==OBJTYPE_Navi,collider&&collider->isTeki(),collider?collider->mSRT.t.y:0,collider?collider->mVelocity.x:0,collider?collider->mVelocity.z:0,t.visible,e);
}
bool Native::earthquake(BTeki* actor,std::string& e){return m->provider.earthquake(actor,e);}
void Native::forget(Creature* actor){auto* h=m->provider.lookup(actor);if(!h)return;m->tracks.at(actor)->nativeDying=true;std::string e;if(!m->provider.release(actor,h->token,e))fail(e);}
bool Native::geometryOwnershipControl(std::string& e){
 if(!gsys)return reject(e,"foliage ownership control requires native heap");HeapScope heap;
 if(!m->load(e))return false;for(const auto& i:m->banks){auto& b=*i.second;
  pelplant::Geometry a(*b.poses.owner()),c(*b.poses.owner());const auto* pose=b.poses.basePose();
  if(!pose||!p2pose::write(a.shape,*pose)||a.shape.mVertexList==c.shape.mVertexList||a.shape.mJointList==c.shape.mJointList||a.shape.mCurrentAnimation==c.shape.mCurrentAnimation)return reject(e,"foliage mutable geometry ownership aliased");
 }e.clear();return true;
}
} }
namespace {
using p2original::foliage::Native;
Native* owner(const Creature* c){for(auto* n:p2original::foliage::instances())if(n->owns(c))return n;return nullptr;}
void checked(bool yes,const std::string& e){if(!yes)p2original::foliage::fail(e);}
}
bool pc_p2_original_foliage_owned(const Creature* c){return owner(c)!=nullptr;}
bool pc_p2_original_foliage_update(BTeki* a){auto* n=owner(a);if(!n)return false;std::string e;checked(n->tick(a,gsys->getFrameTime(),e),e);return true;}
bool pc_p2_original_foliage_draw(BTeki* a,Graphics& g,const Matrix4f& v){auto* n=owner(a);return n&&n->draw(a,g,v);}
bool pc_p2_original_foliage_refresh(BTeki* a,Graphics& g){auto* n=owner(a);if(!n)return false;if(!g.mCamera)return true;Matrix4f root,view;root.makeSRT(a->mSRT.s,Vector3f(0,a->mFaceDirection,0),a->mSRT.t);g.mCamera->mLookAtMtx.multiplyTo(root,view);return n->draw(a,g,view);}
bool pc_p2_original_foliage_collision(BTeki* a,Creature* c){auto* n=owner(a);if(!n)return false;std::string e;checked(n->collision(a,c,e),e);return true;}
bool pc_p2_original_foliage_earthquake(BTeki* a){auto* n=owner(a);if(!n)return false;std::string e;checked(n->earthquake(a,e),e);return true;}
void pc_p2_original_foliage_forget(BTeki* a){auto* n=owner(a);if(n)n->forget(a);}


void pc_p2_original_foliage_post_shadow(Graphics& g){for(auto* n:p2original::foliage::instances())n->postShadow(g);}



