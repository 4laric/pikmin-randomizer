#include "pc_p2_original_pelplant_native.h"
#include "pc_p2_pose_family.h"
#include "pc_p2_flyer_coll.h"
#include "teki.h"
#include "Pellet.h"
#include "Generator.h"
#include "Graphics.h"
#include "Camera.h"
#include "Collision.h"
#include "Stickers.h"
#include "Interactions.h"
#include "pc_p2_receipt_host.h"
#include "pc_p2_original_actor.h"
#include "pc_p2_original_drop_engine.h"
#include "pc_p2_original_pelplant_blend.h"
#include "pc_p2_original_pelplant_code.h"
#include "pc_p2_original_pelplant_geometry.h"
#include "sysNew.h"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <set>
#include <cstdio>
#include <cstdlib>
extern Matrix4f invCamMat;

namespace p2original { namespace pelplant {
namespace {
// idle callbacks may arrive with SYSHEAP_NULL after PlugPikiApp::idle.
// Own only our resource/birth allocation scope and restore its caller's heap.
struct AppHeapScope {
 int previous;
 AppHeapScope():previous(gsys->setHeap(SYSHEAP_App)){}
 ~AppHeapScope(){gsys->setHeap(previous);}
};
const char* names[]={"damage3","dead3","grow1","grow2","wait1","wait2","wait3","bgrow1","bdamage1","bdead1"};
const char* joints[]={"world_root","bodyjnt1","bodyjnt2","bodyeff","headchn","headjnt","headeff","tubomi"};
std::set<Native*>& natives(){static std::set<Native*> instances;return instances;}
void fail(const std::string& error){std::fprintf(stderr,"P2_ORIGINAL_PELPLANT refusal: %s\n",error.c_str());std::abort();}
int amountIndex(unsigned n){return n==1?0:n==5?1:n==10?2:n==20?3:-1;}
float headScale(unsigned n){return n==1?1:n==5?2:n==10?3.5f:4.8f;}
bool reject(std::string& e,const char* text){e=text;return false;}
u32 pelletId(unsigned amount,int color){char c=color==0?'b':color==1?'r':'y';return (u32('p')<<24)|(u32(c)<<16)|(u32('0'+amount/10)<<8)|u32('0'+amount%10);}
struct Sample {int frame;std::array<Matrix4f,8> joint;std::array<bool,8> present{};};
struct Clip {int duration=0;std::vector<int> frames;std::vector<Shape*> shapes;std::vector<Sample> samples;};
struct Track {
 unsigned motion=4;float frame=0,blendTime=0;bool blend=false;
 P2FlyerColl collision;
 Matrix4f capture;
 u32 pelletFlags=0;
 bool nativeDying=false;
 std::unique_ptr<Geometry> geometry;
 p2pose::Track presented;
 p2pose::Pose blendLeft,blendRight,blendResult;
};
}
struct Native::Impl final:Engine {
 std::function<bool(unsigned)> met;
 Provider provider;
 Resources resource;
 std::array<std::array<Clip,10>,4> variants;
 std::array<p2posefamily::Bank,4> banks;
 std::array<p2poseload::Shared,4> owners;
 std::array<p2flyer::Sphere,6> spheres;
 std::array<std::array<char,5>,6> colliderIds{},colliderCodes{};
 std::array<int,6> collJoint{};
 std::map<Creature*,std::unique_ptr<Track>> tracks;
 std::map<Pellet*,Host*> cargo;
 bool loaded=false;
 std::function<bool(Creature*,std::string&)> death;
 std::function<bool(Creature*,std::string&,std::string&)> registryIdentity;
 std::function<void(Pellet*,unsigned,bool)> onOnion;
 P2ReceiptHostHandle ledger=nullptr;
 explicit Impl(std::function<bool(unsigned)> fn):met(std::move(fn)),provider(*this){
  registryIdentity=[](Creature* actor,std::string& durable,std::string& e){
   unsigned source=0,token=0;InstanceIdentity identity;
   if(!originalActors().query(actor,source,token,&identity)||source!=0||!token||identity.catalog.empty())return reject(e,"Pelplant birth lacks actual original registry identity");
   durable=identity.catalog+":"+std::to_string(identity.generator)+":"+std::to_string(identity.ordinal)+":"+std::to_string(identity.epoch)+":"+std::to_string(identity.activation);return true;
  };
 }
 int clipIndex(const std::string& name){for(int i=0;i<10;++i)if(name==names[i])return i;return -1;}
 bool load(std::string& e){
  if(loaded)return true;
  if(!gsys||!tekiMgr||!pelletMgr||!met)return reject(e,"Pelplant native managers or first-met provider unavailable");
  std::ifstream index("p2-pelplant-resources.txt");std::string word,name,stem;int count,duration;
  if(!(index>>word)||word!="P2_PELPLANT_RESOURCES_2")return reject(e,"Pelplant size resource index missing");
  const unsigned amounts[]={1,5,10,20};
  for(int variant=0;variant<4;++variant){
  unsigned amount;std::string bankPath,jointPath;
  if(!(index>>word>>amount>>bankPath>>jointPath)||word!="variant"||amount!=amounts[variant]
    ||bankPath!="p2-pelplant-size"+std::to_string(amount)+"-bank.txt"
    ||jointPath!="p2-pelplant-size"+std::to_string(amount)+"-joints.txt")return reject(e,"invalid Pelplant size variant");
  auto& clips=variants[variant];auto& bank=banks[variant];auto& shared=owners[variant];
  std::ifstream in(bankPath);
  if(!(in>>word)||word!="P2_PELPLANT_BANK_1")return reject(e,"Pelplant physical bank missing or wrong version");
  std::size_t total=0;std::array<bool,10> seen{};
  for(int n=0;n<10;++n){
   if(!(in>>word>>name>>count>>duration>>stem)||word!="clip")return reject(e,"malformed Pelplant physical clip");
   int index=clipIndex(name);if(index<0||seen[index]||count<2||count>64||duration<2||duration>10000||stem!="flora_Pelplant_size"+std::to_string(amount)+"_"+name)return reject(e,"invalid Pelplant physical clip identity");
   seen[index]=true;auto& clip=clips[index];clip.duration=duration;
   if(!(in>>word>>name)||word!="frames"||name!=names[index])return reject(e,"missing Pelplant frame list");
   for(int j=0;j<count;++j){int frame;if(!(in>>frame))return reject(e,"truncated Pelplant frames");clip.frames.push_back(frame);}
   if(!p2posefamily::Bank::validFrames(clip.frames,count,duration))return reject(e,"invalid Pelplant sampled frames");
   if(!(in>>word>>name>>stem)||word!="events"||name!=names[index])return reject(e,"missing Pelplant authored event row");
   const bool waiting=index>=4&&index<=6;
   if(stem!=(waiting?"0:0,29:1":"-"))return reject(e,"Pelplant authored event table changed");
   if(!p2posefamily::loadFamilyClip(bank,names[index],"flora_Pelplant_size"+std::to_string(amount)+"_"+std::string(names[index]),count,duration,clip.frames,shared,total,clip.shapes,e))return false;
   if(!bank.clip(names[index]))return reject(e,"Pelplant physical pose vectors unresolved");
   for(int frame:clip.frames){Sample sample;sample.frame=frame;for(auto& matrix:sample.joint)matrix.makeIdentity();clip.samples.push_back(sample);}
  }
  if(in>>word)return reject(e,"trailing Pelplant bank data");
  std::ifstream jointFile(jointPath);
  if(!(jointFile>>word)||word!="P2_PELPLANT_JOINTS_1")return reject(e,"Pelplant physical joint bank missing");
  std::array<bool,6> colliderSeen{};bool parameters=false;
  while(jointFile>>word){
   if(word=="joint"){
    int frame;std::string joint;if(!(jointFile>>name>>frame>>joint))return reject(e,"truncated Pelplant joint");int index=clipIndex(name),j=-1;
    for(int k=0;k<8;++k)if(joint==joints[k])j=k;
    if(index<0||j<0)return reject(e,"unknown Pelplant joint or motion");
    auto& samples=clips[index].samples;auto sample=std::find_if(samples.begin(),samples.end(),[frame](const Sample& s){return s.frame==frame;});
    if(sample==samples.end()||sample->present[j])return reject(e,"duplicate or unsampled Pelplant joint");
    for(int r=0;r<3;++r)for(int c=0;c<4;++c){float value;if(!(jointFile>>value)||!std::isfinite(value))return reject(e,"invalid Pelplant joint matrix");sample->joint[j].mMtx[r][c]=value;}
    sample->present[j]=true;
   }else if(word=="collider"){
    int index,joint,parent,attribute;std::string id,special;float x,y,z,radius;
    if(!(jointFile>>index>>joint>>parent>>id>>special>>attribute>>x>>y>>z>>radius)||index<0||index>=6||colliderSeen[index]
       ||joint<0||joint>=8||parent>=index||parent<-1||attribute!=0||id.size()!=4||special.size()!=4||!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z)||!std::isfinite(radius)||radius<=0)return reject(e,"invalid Pelplant retail collider");
    // Anonymous retail IDs repeat; give only those internal lookup names so
    // P2FlyerColl::part(i) resolves all six distinct authored spheres.
    if(id=="none")id="p00"+std::to_string(index);
    auto& sphere=spheres[index];sphere.parent=parent;std::copy(id.begin(),id.end(),colliderIds[index].begin());std::copy(special.begin(),special.end(),colliderCodes[index].begin());sphere.id=colliderIds[index].data();sphere.code=colliderCodes[index].data();sphere.offset={x,y,z};sphere.radius=radius;collJoint[index]=joint;colliderSeen[index]=true;
   }else if(word=="parameters"){
    if(parameters||!(jointFile>>resource.parameters.maxHealth>>resource.parameters.smallToMiddle>>resource.parameters.middleToFull>>resource.parameters.colorPeriod))return reject(e,"invalid Pelplant retail parameters");parameters=true;
   }else return reject(e,"unknown Pelplant physical bank row");
  }
  for(const auto& clip:clips)for(const auto& sample:clip.samples)for(bool present:sample.present)if(!present)return reject(e,"Pelplant joint sample incomplete");
  for(bool seen:colliderSeen)if(!seen)return reject(e,"Pelplant collider tree incomplete");
  if(std::string(spheres[1].id)!="head"||std::string(spheres[1].code)!="s__0"||!parameters)return reject(e,"Pelplant head vulnerability part unresolved");
  resource.model=resource.root=resource.head=resource.neck=resource.collider=true;resource.clips.fill(true);
    }
  if(index>>word)return reject(e,"trailing Pelplant size index");
  loaded=true;return true;
 }
 bool resources(Resources& out,std::string& e)override{
  AppHeapScope heap;
  if(!load(e))return false;
  for(const auto& bank:banks)if(!bank.owner()||!Geometry::admits(*bank.owner()))return reject(e,"Pelplant owned geometry requires a static flattened single-joint bank");
  auto* chassis=tekiMgr->getTekiShapeObject(TEKI_Palm);
  if(!chassis||!chassis->mShape||!chassis->mAnimMgr||!tekiMgr->getTekiParameters(TEKI_Palm)||!tekiMgr->getStrategy(TEKI_Palm))return reject(e,"Pelplant native chassis shape/animation/parameters/strategy not preloaded before course admission");
  if(!ledger)ledger=pc_p2_receipt_host_open("p2-original-pelplant-onion.txt");if(!ledger)return reject(e,"Pelplant ordinary Onion observation ledger invalid");
  const unsigned amounts[]={1,5,10,20};
  for(int a=0;a<4;++a)for(int c=0;c<3;++c){u32 id=pelletId(amounts[a],c);auto* cfg=pelletMgr->getConfig(id);
   if(!cfg||!pelletMgr->pcEnsureShape(id)||cfg->mPelletColor()!=c||cfg->mCarryMinPikis()<=0||cfg->mCarryMaxPikis()<cfg->mCarryMinPikis()||cfg->mMatchingOnyonSeeds()<=0||cfg->mNonMatchingOnyonSeeds()<=0)return reject(e,"Pelplant configured number pellet shape/carry/yield parameters unavailable");
   resource.numberConfigs[a][c]=true;
  }
  out=resource;return true;
 }
 bool identity(Host& h,std::string& durable,std::string& e)override{if(!registryIdentity)return reject(e,"Pelplant original registry identity callback absent");if(!registryIdentity(h.creature,durable,e))return false;return pc_p2_receipt_host_valid(durable.c_str())?true:reject(e,"Pelplant durable original identity invalid");}
 bool reserve(unsigned roots,const std::array<unsigned,4>& pellets,std::string& e)override{
  unsigned count=0;for(unsigned n:pellets)count+=n;
  if(tekiMgr->getMax()-tekiMgr->getSize()<int(roots)||pelletMgr->getMax()-pelletMgr->getSize()<int(count))return reject(e,"Pelplant actual native actor/pellet pool capacity insufficient");
  if(!tekiMgr->hasModel(TEKI_Palm)||!tekiMgr->getTekiShapeObject(TEKI_Palm))return reject(e,"Pelplant manager chassis has not been initialized");return true;
 }
 bool allocate(Host& h,const Position& position,float facing,std::string& e)override{
  AppHeapScope heap;
  Teki* actor=tekiMgr->newTeki(TEKI_Palm);if(!actor)return reject(e,"Pelplant real manager allocation failed");
  h.creature=actor;tracks.emplace(actor,std::make_unique<Track>());
  // newTeki::init performs only Creature::init; initialize the chassis's
  // presentation/cleanup fields explicitly without Palm reset/startAI.
  actor->clearTekiOptions();actor->clearCreaturePointers();
  actor->mTekiShape=tekiMgr->getTekiShapeObject(TEKI_Palm);
  actor->mTekiAnimator->init(&actor->mTekiShape->mAnimContext,actor->mTekiShape->mAnimMgr,tekiMgr->mMotionTable);
  actor->mDeadState=0;actor->mStateID=0;actor->mStoredDamage=0;actor->mDamageCount=0;actor->_3A4=0;
  actor->mPellet=nullptr;actor->mCollisionRadius=55;actor->mSize=45;
  for(int i=0;i<4;++i)actor->mParticleGenerators[i]=nullptr;
  actor->mGenerator=h.generator;actor->mSRT.t.set(position.x,position.y,position.z);actor->mFaceDirection=facing;
  actor->mGrid.updateGrid(actor->mSRT.t);actor->mGrid.updateAIGrid(actor->mSRT.t,false);
  actor->mSRT.r.set(0,facing,0);actor->mSRT.s.set(1,1,1);actor->mHealth=actor->mMaxHealth=h.parameters.maxHealth;
  actor->mVelocity.set(0,0,0);actor->setCreatureFlag(CF_DisableMovement);actor->setCreatureFlag(CF_IsAiDisabled);
  actor->clearTekiOption(BTeki::TEKI_OPTION_GRAVITATABLE);actor->setTekiOption(BTeki::TEKI_OPTION_VISIBLE);
  actor->setTekiOption(BTeki::TEKI_OPTION_ATARI);actor->setTekiOption(BTeki::TEKI_OPTION_ALIVE);
  actor->setTekiOption(BTeki::TEKI_OPTION_SHAPE_VISIBLE);
  auto& blendTrack=*tracks.at(actor);const auto* base=banks[0].basePose();
  if(!base||!Geometry::admits(*banks[0].owner()))return reject(e,"Pelplant private geometry static admission failed");
  blendTrack.geometry=std::make_unique<Geometry>(*banks[0].owner());
  blendTrack.presented.shape=&blendTrack.geometry->shape;blendTrack.presented.size(*base);
  blendTrack.blendLeft=blendTrack.blendRight=blendTrack.blendResult=*base;
  if(!tracks.at(actor)->collision.bind(actor,spheres.data(),6))return reject(e,"Pelplant retail collider allocation failed");return true;
 }
 bool captureNumber(Host& h,unsigned amount,int c,Pellet*& out,std::string& e)override{
  AppHeapScope heap;
  out=pelletMgr->newNumberPellet(c,amountIndex(amount));if(!out)return reject(e,"configured Pelplant number pellet birth failed");
  auto* track=tracks.at(h.creature).get();
  out->init(h.creature->mSRT.t);out->startAI(0);
  track->pelletFlags=out->mCreatureFlags;
  out->setCreatureFlag(CF_SkipPhysicsAndCollision);out->setCreatureFlag(CF_DisableMovement);out->setCreatureFlag(CF_IsAiDisabled);
  cargo[out]=&h;return true;
 }
 bool pelletColor(Pellet* pellet,int c,std::string& e)override{
  auto found=cargo.find(pellet);if(found==cargo.end())return reject(e,"Pelplant color update lacks owned captured pellet");
  auto* cfg=pelletMgr->getConfig(pelletId(found->second->initial.amount,c));auto* shape=pelletMgr->pcEnsureShape(pelletId(found->second->initial.amount,c));
  if(!cfg||!shape)return reject(e,"Pelplant cycle color physical resource unresolved");pellet->mConfig=cfg;pellet->mShapeObject=shape;return true;
 }
 bool metColor(unsigned color)const override{return met(color);}
 bool motion(Host& h,unsigned animation,bool blend,std::string&)override{auto& t=*tracks.at(h.creature);
  // Our source blend owns the whole transition. Discard the generic renderer's
  // cached Full pose so it cannot fade back to Full when WaitSmall begins.
  if(blend)t.presented.view.reset();
  t.motion=animation;t.frame=0;t.blend=blend;t.blendTime=0;return true;}
 bool flags(Host& h,bool vulnerable,bool living,bool cullable,float radius,std::string&)override{
  if(!std::isfinite(radius)||radius<=0)return false;
  h.cullable=cullable;h.lodRadius=radius;
  auto* actor=static_cast<BTeki*>(h.creature);if(vulnerable)actor->clearTekiOption(BTeki::TEKI_OPTION_INVINCIBLE);else actor->setTekiOption(BTeki::TEKI_OPTION_INVINCIBLE);
  if(living)actor->setTekiOption(BTeki::TEKI_OPTION_ORGANIC);else actor->clearTekiOption(BTeki::TEKI_OPTION_ORGANIC);return true;
 }
 bool flick(Host& h,std::string&)override{std::vector<Creature*> snapshot;Stickers attached(h.creature);Iterator it(&attached);CI_LOOP(it)snapshot.push_back(*it);
  for(Creature* p:snapshot){InteractFlick flick(h.creature,10,0,-1000);p->stimulate(flick);}return true;}
 bool commonResources(const CatalogRow& row,std::string& e)override{return pc_p2_original_drop_resources(row,e);}
 bool deathProcedure(Host& h,std::string& e)override{
  // EnemyBase throws common items at death entry, independently of the
  // captured number pellet released by Pelplant's death-animation END.
  auto* actor=static_cast<BTeki*>(h.creature);
  if(!pc_p2_original_spawn_items(actor)){e="Pelplant death lost original registry ownership";return false;}
  actor->clearTekiOption(BTeki::TEKI_OPTION_ORGANIC);return true;
 }
 bool endCapture(Host& h,Pellet* pellet,std::string&)override{auto& t=*tracks.at(h.creature);pellet->mCreatureFlags=t.pelletFlags;pellet->mVelocity.set(0,0,0);cargo.erase(pellet);return true;}
 bool killPlant(Host& h,std::string&)override{static_cast<BTeki*>(h.creature)->clearTekiOption(BTeki::TEKI_OPTION_ALIVE);return true;}
 bool cleanup(Host& h,std::string&)override{
  auto track=tracks.find(h.creature);if(track==tracks.end())return true;
  if(h.captured){cargo.erase(h.captured);h.captured->kill(false);h.captured=nullptr;}
  std::string ignored;
  flick(h,ignored); // Detach ordinary stickers before collider retirement.
  track->second->collision.detach(static_cast<BTeki*>(h.creature));
  // Native manager kill belongs to the course's coordinated retirement hook;
  // provider removes its typed state before invoking the actual native funnel.
  const bool dying=track->second->nativeDying;
  tracks.erase(track);if(!dying)h.creature->kill(false);return true;
 }
 Matrix4f localSample(const Clip& clip,float sourceFrame,int joint){
  const float frame=std::min(sourceFrame,float(clip.duration-1));std::size_t left=0;while(left+1<clip.samples.size()&&clip.samples[left+1].frame<=frame)++left;
  std::size_t right=std::min(left+1,clip.samples.size()-1);float w=right==left?0:(frame-clip.samples[left].frame)/float(clip.samples[right].frame-clip.samples[left].frame);
  Matrix4f local;local.makeIdentity();for(int r=0;r<3;++r)for(int c=0;c<4;++c)local.mMtx[r][c]=clip.samples[left].joint[joint].mMtx[r][c]*(1-w)+clip.samples[right].joint[joint].mMtx[r][c]*w;
  return local;
 }
 Matrix4f sampled(Host& h,int joint){auto& t=*tracks.at(h.creature);auto& clips=variants[h.captured?amountIndex(h.initial.amount):0];
  Matrix4f local=localSample(clips[t.motion],t.frame,joint);
  if(t.blend){Matrix4f end=localSample(clips[4],t.frame,joint);std::array<float,12> a,b,result;
   for(int r=0;r<3;++r)for(int c=0;c<4;++c){a[r*4+c]=local.mMtx[r][c];b[r*4+c]=end.mMtx[r][c];}
   if(!blendJoint(a,b,witherWeight(t.blendTime),result))fail("Pelplant wither joint blend invalid");
   for(int r=0;r<3;++r)for(int c=0;c<4;++c)local.mMtx[r][c]=result[r*4+c];
  }
  Matrix4f root,world;root.makeSRT(Vector3f(1,1,1),Vector3f(0,h.creature->mFaceDirection,0),h.creature->mSRT.t);root.multiplyTo(local,world);return world;
 }
 void follow(Host& h){auto& t=*tracks.at(h.creature);float scale=h.captured?headScale(h.initial.amount):1;
  for(int i=0;i<6;++i){CollPart* part=t.collision.part(i);if(!part)continue;Matrix4f world=sampled(h,collJoint[i]);
   float offsetScale=i==1?scale:1;auto offset=spheres[i].offset;
   part->mCentre.set(world.mMtx[0][3]+offsetScale*(world.mMtx[0][0]*offset.x+world.mMtx[0][1]*offset.y+world.mMtx[0][2]*offset.z),
    world.mMtx[1][3]+offsetScale*(world.mMtx[1][0]*offset.x+world.mMtx[1][1]*offset.y+world.mMtx[1][2]*offset.z),
    world.mMtx[2][3]+offsetScale*(world.mMtx[2][0]*offset.x+world.mMtx[2][1]*offset.y+world.mMtx[2][2]*offset.z));part->mRadius=spheres[i].radius*offsetScale;
   Matrix4f cameraRotation,jointRotation;cameraRotation.makeIdentity();jointRotation=world;
   jointRotation.mMtx[0][3]=jointRotation.mMtx[1][3]=jointRotation.mMtx[2][3]=0;
   for(int r=0;r<3;++r)for(int c=0;c<3;++c)cameraRotation.mMtx[r][c]=invCamMat.mMtx[c][r];
   cameraRotation.multiplyTo(jointRotation,part->mJointMatrix);
  }
  if(h.captured){Matrix4f head=sampled(h,5),offset;offset.makeSRT(Vector3f(1/scale,1/scale,1/scale),Vector3f(0,1.57079632679f,-1.57079632679f),Vector3f(12,0,0));head.multiplyTo(offset,t.capture);
   h.captured->mSRT.t.set(t.capture.mMtx[0][3],t.capture.mMtx[1][3],t.capture.mMtx[2][3]);h.captured->mWorldMtx=t.capture;
  }
 }
};
Native::Native(std::function<bool(unsigned)> met):m(std::make_unique<Impl>(std::move(met))){natives().insert(this);}
Native::~Native(){if(m->provider.size())fail("Native provider destroyed before owned course cleanup");if(m->ledger)pc_p2_receipt_host_close(m->ledger);natives().erase(this);}
Provider& Native::provider(){return m->provider;}
bool Native::geometryOwnershipControl(std::string& e){
 if(!m->loaded||m->provider.size())return reject(e,"geometry ownership control requires loaded banks and no live family");
 // Warm the renderer's exact-registration vector before measuring ownership.
 for(auto& bank:m->banks){if(!bank.owner()||!bank.basePose()||!Geometry::admits(*bank.owner()))return reject(e,"geometry control static bank unresolved");
  Shape unsupported=*bank.owner();unsupported.mJointCount=2;if(Geometry::admits(unsupported))return reject(e,"geometry control admitted an articulated bank");
  unsupported=*bank.owner();unsupported.mEnvelopeCount=1;if(Geometry::admits(unsupported))return reject(e,"geometry control admitted weighted geometry");
  Geometry geometry(*bank.owner());if(!p2pose::write(geometry.shape,*bank.basePose()))return reject(e,"geometry control warmup write failed");}
 const auto before=piki_pc_allocation_stats();
 for(unsigned pass=0;pass<32;++pass)for(auto& bank:m->banks){
  const Shape& shared=*bank.owner();const Vector3f original=shared.mVertexList[0];
  Geometry geometry(shared);p2pose::Pose changed=*bank.basePose();changed.positions[0].x+=1;
  if(geometry.shape.mVertexList==shared.mVertexList||geometry.shape.mNormalList==shared.mNormalList
    ||geometry.shape.mJointList==shared.mJointList||geometry.shape.mCurrentAnimation==shared.mCurrentAnimation
    ||geometry.shape.mMaterialList!=shared.mMaterialList||geometry.shape.mMeshList!=shared.mMeshList
    ||!(geometry.shape.mShapeFlags&ShapeFlags::AlwaysRedraw)||!p2pose::write(geometry.shape,changed)
    ||shared.mVertexList[0].x!=original.x||shared.mVertexList[0].y!=original.y||shared.mVertexList[0].z!=original.z)
   return reject(e,"owned geometry aliases mutable bank storage or loses borrowed resources");
 }
 const auto after=piki_pc_allocation_stats();
 if(before.liveBlocks!=after.liveBlocks||before.liveBytes!=after.liveBytes||before.unknownFrees!=after.unknownFrees)
  return reject(e,"owned geometry repeated disposal allocation checkpoint differs");
 std::printf("P2_ORIGINAL_PELPLANT_GEOMETRY_OWNERSHIP cycles=128 live_blocks=%zu live_bytes=%zu borrowed_materials=1 owned_mutable_storage=1 disposal=1\n",after.liveBlocks,after.liveBytes);
 e.clear();return true;
}
bool Native::owns(const Creature* actor)const{return m->tracks.count(const_cast<Creature*>(actor))!=0;}
bool Native::captured(const Pellet* pellet)const{return m->cargo.count(const_cast<Pellet*>(pellet))!=0;}
bool Native::updateCaptured(Pellet* pellet){auto it=m->cargo.find(pellet);if(it==m->cargo.end())return false;m->follow(*it->second);return true;}
bool Native::tick(BTeki* actor,float dt,std::string& e){Host* h=m->provider.lookup(actor);if(!h)return false;
 // Owned update bypasses Creature::update; retain its ordinary spatial/search
 // maintenance without running the borrowed Palm AI or movement.
 actor->mGrid.updateGrid(actor->mSRT.t);actor->mGrid.updateAIGrid(actor->mSRT.t,false);
 auto& t=*m->tracks.at(actor);const unsigned motion=t.motion;const float previous=t.frame;t.frame+=dt*30;
 Event event=Event::None;if(t.blend){t.blendTime+=dt;if(t.blendTime>=1)event=Event::EndBlend;}
 else if(t.frame>=m->variants[0][motion].duration){event=Event::End;if(motion>=4&&motion<=6){t.frame=std::fmod(t.frame,float(m->variants[0][motion].duration));event=Event::LoopEnd;}}
 else if(previous<29&&t.frame>=29&&motion>=4&&motion<=6)event=Event::LoopEnd;
 if(!m->provider.tick(actor,dt,event,e))return false;
 actor->mStoredDamage=0;actor->mHealth=h->health;t.presented.advance(dt);m->follow(*h);
 if(h->dead){if(!m->death)return reject(e,"Pelplant completed death lacks coordinated course retirement");return m->death(actor,e);}return true;
}
bool Native::draw(BTeki* actor,Graphics& gfx,const Matrix4f& view){Host* h=m->provider.lookup(actor);if(!h||!gfx.mCamera)return false;auto& t=*m->tracks.at(actor);auto& clip=m->variants[h->captured?amountIndex(h->initial.amount):0][t.motion];
 // Presentation-only equivalent: keep the typed simulation/capture clock
 // independent of this client's frustum, as required by the native port.
 if(h->cullable&&!gfx.mCamera->isPointVisible(actor->getBoundingSphereCentre(),h->lodRadius))return true;
 gfx.useMatrix(Matrix4f::ident,0);
 auto& bank=m->banks[h->captured?amountIndex(h->initial.amount):0];Shape* shape=nullptr;
 if(t.blend){const auto* start=bank.clip(names[t.motion]);const auto* end=bank.clip("wait1");
  if(!start||!end||!samplePose(start->poses,start->frames,t.frame,t.blendLeft)
    ||!samplePose(end->poses,end->frames,t.frame,t.blendRight)
    ||!p2pose::blendInto(t.blendLeft,t.blendRight,witherWeight(t.blendTime),t.blendResult)
    ||!p2pose::write(t.geometry->shape,t.blendResult))fail("Pelplant wither visible geometry blend invalid");
  shape=&t.geometry->shape;
 }else {const auto* entry=bank.clip(names[t.motion]);
  float frame=std::min(t.frame,float(clip.duration-1));if(entry&&p2motion::isDeathClip(names[t.motion]))frame=std::min(frame,entry->holdFrame);
  if(entry&&p2pose::present(t.presented,names[t.motion],entry->poses.size(),[entry](std::size_t i)->const p2pose::Pose&{return entry->poses[i];},
      entry->frames,frame,p2motion::tunables(),entry->seamContinuous).ok)shape=&t.geometry->shape;
 }
 if(!shape){std::size_t best=0;for(std::size_t i=1;i<clip.frames.size();++i)if(std::fabs(float(clip.frames[i])-t.frame)<std::fabs(float(clip.frames[best])-t.frame))best=i;shape=clip.shapes[best];}
 shape->updateAnim(gfx,view,nullptr,actor);shape->drawshape(gfx,*gfx.mCamera,nullptr);return true;
}
bool Native::drawCaptured(Pellet* pellet,Graphics& gfx,const Matrix4f& view){auto it=m->cargo.find(pellet);if(it==m->cargo.end()||!gfx.mCamera)return false;
 Matrix4f transform;gfx.mCamera->mLookAtMtx.multiplyTo(m->tracks.at(it->second->creature)->capture,transform);
 // Same native context preparation as ordinary Pellet::doRender. Shape joint
 // overrides refer to these shared contexts; init/startAI alone is insufficient.
 gfx.useMatrix(Matrix4f::ident,0);pellet->mAnimator.updateContext();
 float c=pellet->mConfig->mPelletColor();pellet->mAnimatedMaterials.animate(&c);
 pellet->mShapeObject->mShape->updateAnim(gfx,transform,nullptr,nullptr);pellet->mShapeObject->mShape->drawshape(gfx,*gfx.mCamera,&pellet->mAnimatedMaterials);return true;
}
void Native::forgetPellet(Pellet* pellet){m->cargo.erase(pellet);m->provider.forgetPellet(pellet);}
void Native::onDeath(std::function<bool(Creature*,std::string&)> callback){m->death=std::move(callback);}
void Native::onIdentity(std::function<bool(Creature*,std::string&,std::string&)> callback){m->registryIdentity=std::move(callback);}
void Native::onOnion(std::function<void(Pellet*,unsigned,bool)> callback){m->onOnion=std::move(callback);}
bool Native::observeOnion(Pellet* pellet,unsigned& token,bool& duplicate){std::string identity;
 if(!m->provider.onion(pellet,token,duplicate,&identity))return false;
 auto result=pc_p2_receipt_host_grant(m->ledger,"original","enemy:0",identity.c_str(),"onion");
 if(result==P2ReceiptHostResult::Error)fail("Pelplant ordinary Onion ledger write failed");
 duplicate=duplicate||result==P2ReceiptHostResult::Duplicate;
 if(m->onOnion)m->onOnion(pellet,token,duplicate);return true;
}
void Native::forgetCreature(Creature* actor){Host* h=m->provider.lookup(actor);if(!h)return;
 m->tracks.at(actor)->nativeDying=true;std::string e;if(!m->provider.release(actor,h->token,e))fail(e);
}
} }
namespace {
using p2original::pelplant::Native;
Native* owner(const Creature* actor){for(Native* n:p2original::pelplant::natives())if(n->owns(actor))return n;return nullptr;}
Native* cargoOwner(const Pellet* p){for(Native* n:p2original::pelplant::natives())if(n->captured(p))return n;return nullptr;}
void require(bool ok,const std::string& e){if(!ok)p2original::pelplant::fail(e);}
}
bool pc_p2_original_pelplant_update(BTeki* actor){Native* n=owner(actor);if(!n)return false;std::string e;require(n->tick(actor,gsys->getFrameTime(),e),e);return true;}
bool pc_p2_original_pelplant_refresh(BTeki* actor,Graphics& gfx){
 Native* n=owner(actor);if(!n)return false;
 if(!gfx.mCamera)return true;
 // Route before TaiPalmStrategy::draw: that borrowed strategy writes its
 // own mTargetPosition into the actor before drawTekiShape is reached.
 Matrix4f root,view;root.makeSRT(actor->mSRT.s,Vector3f(0,actor->mFaceDirection,0),actor->mSRT.t);
 gfx.mCamera->mLookAtMtx.multiplyTo(root,view);
 n->draw(actor,gfx,view);return true;
}
bool pc_p2_original_pelplant_draw(BTeki* actor,Graphics& gfx,const Matrix4f& view){Native* n=owner(actor);return n&&n->draw(actor,gfx,view);}
bool pc_p2_original_pelplant_damage(BTeki* actor,float damage,unsigned nativeCode){Native* n=owner(actor);if(!n)return false;auto special=p2original::pelplant::sourceCode(nativeCode);std::string e;require(n->provider().damage(actor,damage,nativeCode?special.data():nullptr,e),e);return true;}
bool pc_p2_original_pelplant_stick(BTeki* actor,unsigned nativeCode){Native* n=owner(actor);if(!n)return false;auto special=p2original::pelplant::sourceCode(nativeCode);std::string e;require(n->provider().stick(actor,nativeCode?special.data():nullptr,e),e);return true;}
bool pc_p2_original_pelplant_captured(const Pellet* p){return cargoOwner(p)!=nullptr;}
bool pc_p2_original_pelplant_capture_update(Pellet* p){Native* n=cargoOwner(p);return n&&n->updateCaptured(p);}
bool pc_p2_original_pelplant_capture_draw(Pellet* p,Graphics& gfx,const Matrix4f& view){Native* n=cargoOwner(p);return n&&n->drawCaptured(p,gfx,view);}
bool pc_p2_original_pelplant_onion(Pellet* p,unsigned& token,bool& duplicate){for(Native* n:p2original::pelplant::natives())if(n->observeOnion(p,token,duplicate))return true;return false;}
void pc_p2_original_pelplant_forget_pellet(Pellet* p){for(Native* n:p2original::pelplant::natives())n->forgetPellet(p);}
void pc_p2_original_pelplant_forget_teki(BTeki* actor){Native* n=owner(actor);if(n)n->forgetCreature(actor);}
