#include "pc_p2_original_bridge_native.h"
#include "WorkObject.h"
#include "DynColl.h"
#include "MapMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "SoundMgr.h"
#include "Material.h"
#include "pc_p2_white.h"
#include "pc_p2_purple.h"
#include "Interactions.h"
#include "gameflow.h"
#include "Stream.h"
#include "sysNew.h"
#include "netplay/pc_netplay_sha256.h"
#include <algorithm>
#include <map>
#include <set>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
namespace {
using namespace p2original;
constexpr unsigned type=0x70326272u,version=0x42523031u; // p2br / BR01
std::map<unsigned,BridgeRecord> records;
std::map<const Generator*,unsigned> generators;
std::array<Shape*,3> shapes{};
bool admitted=false;
[[noreturn]] void die(const char* why){std::fprintf(stderr,"P2_ORIGINAL_BRIDGE_FAIL %s\n",why);std::abort();}
const BridgeRecord& row(unsigned uid){auto i=records.find(uid);if(i==records.end())die("source bridge UID absent");return i->second;}
class SourceBridge;
std::vector<SourceBridge*> bodies; // Physical birth order, no address sorting.
std::vector<SourceBridge*> allocations; // PC global new survives stage arena reset.
class SourceBridge final:public Bridge {
public:
 unsigned uid;
 BridgeState state;
 WorkObjectNode* ownedNode=nullptr;
 bool nodeAttached=false;
 explicit SourceBridge(Shape* shape,unsigned id):Bridge(shape,true),uid(id),state(bridgeInitial(row(id))){
  const auto& r=row(uid);_400=r.type==2?4:r.type;
  if(mStageCount!=bridgeStageCount(r.type))die("retail bridge shape stage count mismatch");
  // Converter maps retail room00 joint2 to native leaf4, room01 to leaf6, etc.
  for(int i=0;i<mStageCount*2;++i)mStageJoints[i]=&shape->mJointList[4+2*i];
  mMaxHealth=r.stageLife;mGrid.setNeighbourSize(r.type==2?3:1);
 }
 ~SourceBridge(){
  // No borrowed shape/joint/route/manager dereferences after stage reset.
  delete ownedNode;
  for(int i=0;i<mBuildShape->mCollGroupCount;++i){auto* group=mBuildShape->mCollGroupList[i];delete[] group->mTriangleList;delete group;}
  delete[] mBuildShape->mCollGroupList;delete[] mBuildShape->mVertexList;delete[] mBuildShape->mCollTriList;delete[] mBuildShape->mJointVisibility;delete mBuildShape;
  for(int i=0;i<mAnimatedMaterials.mMatCount;++i)if(mAnimatedMaterials.mMaterials[i].mFlags&MATFLAG_PVW)delete mAnimatedMaterials.mMaterials[i].mTevInfo; // Clone owns header only; stage/texture data borrowed.
  delete[] mAnimatedMaterials.mMaterials;delete[] mStageJoints;delete[] mStageProgressList;delete mSeContext;
 }
 void sync(){
  const auto& r=row(uid);
  for(int i=0;i<mStageCount;++i)mStageProgressList[i]=r.stageLife-state.health[i];
  // Match retail setCurrStage and final-joint collision/visibility exactly.
  for(int i=0;i<mBridgeShape->mJointCount;++i)mBuildShape->mJointVisibility[i]=i<2;
  bool complete=state.stage==mStageCount;
  mBuildShape->mJointVisibility[2]=complete; // final leaf
  for(int i=0;i<mStageCount*2;++i)mBuildShape->mJointVisibility[mStageJoints[i]->mIndex]=!complete&&i<=state.stage*2&&(i%2==1||i==state.stage*2);
  if(mStartWaypoint&&mEndWaypoint){mStartWaypoint->setFlag(complete);mEndWaypoint->setFlag(complete);mStartWaypoint->mFlags&=~WayPointFlags::InWater;mEndWaypoint->mFlags&=~WayPointFlags::InWater;auto p=bridgeStagePosition(r,state.stage);Vector3f z=getBridgeZVec();mStartWaypoint->mPosition.set(p[0]-5*z.x,p[1],p[2]-5*z.z);}
 }
 void startAI(int)override{
  _424=3;mBridgeShape->makeInstance(mAnimatedMaterials,0);
  mWorldMtx.makeSRT(Vector3f(1,1,1),mSRT.r,mSRT.t);mBuildShape->mTransformMtx=mWorldMtx;mapMgr->mCollShapeList->add(mBuildShape);
  mStartWaypoint=routeMgr->findNearestWayPointAll('test',getStartPos());
  auto p=bridgeStagePosition(row(uid),mStageCount-1);Vector3f z=getBridgeZVec();Vector3f end(p[0]+40*z.x,p[1],p[2]+40*z.z);
  mEndWaypoint=routeMgr->findNearestWayPointAll('test',end);
  if(!mStartWaypoint||!mEndWaypoint||mStartWaypoint==mEndWaypoint)die("source bridge needs distinct endpoint routes");
  mStartWaypoint->mFlags|=WayPointFlags::Destination;mEndWaypoint->mFlags|=WayPointFlags::Destination;mEndWaypoint->mPosition=end;
  _3CA=-1;_3CC=0;sync();
 }
 bool isAlive()override{return state.stage!=mStageCount;}
 bool isFinished()override{return state.stage==mStageCount;}
 bool workable(immut Vector3f& p)override{
  if(isFinished())return false;float x,z;getBridgePos(p,x,z);z-=10;float rad=getStageZ(state.stage);
  if(z>rad+10||(z>=0&&z<=rad&&absF(x)>=75)||z< -100||absF(x)>=105)return false;return true;
 }
 bool stimulate(immut Interaction& interaction)override{
  if(!interaction.actCommon(this))return false;
  if(auto* build=dynamic_cast<const InteractBuild*>(&interaction)){
   if(!build->mOwner||build->mOwner->mObjType!=OBJTYPE_Piki||build->mStageIndex!=state.stage)return false;
   bool accepted=bridgeAttack(row(uid),state,build->mProgressRate);sync();return accepted;
  }
  if(auto* damage=dynamic_cast<const InteractBreak*>(&interaction)){bool result=bridgeBreak(row(uid),state,damage->mProgressRate);sync();return result;}
  return false;
 }
 void update()override{
  if(mSeContext)mSeContext->update();mGrid.updateGrid(mSRT.t);mGrid.updateAIGrid(mSRT.t,false);
  if(bridgeTick(row(uid),state)){sync();std::printf("P2_ORIGINAL_BRIDGE_STAGE uid=%u stage=%d complete=%d\n",uid,state.stage,isFinished());}
 }
 void refresh(Graphics& gfx)override{
  // Retail completed odd meshes remain visible while final supplies collision.
  if(isFinished())for(int i=0;i<mStageCount;++i)mBuildShape->mJointVisibility[mStageJoints[2*i+1]->mIndex]=true;
  Bridge::refresh(gfx);
  if(isFinished())for(int i=0;i<mStageCount;++i)mBuildShape->mJointVisibility[mStageJoints[2*i+1]->mIndex]=false;
 }
 void doSave(RandomAccessStream& stream)override{
  std::vector<std::uint8_t> bytes;std::string error;if(!bridgeExport(row(uid),state,bytes,error)||stream.getPending()<int(bytes.size()))die("source bridge save rejected");for(auto v:bytes)stream.writeByte(v);
 }
 void doLoad(RandomAccessStream& stream)override{
  if(stream.getPending()<168)die("truncated source bridge save");std::vector<std::uint8_t> bytes(168);for(auto& v:bytes)v=stream.readByte();BridgeState next;std::string error;if(!bridgeImport(row(uid),bytes,next,error))die(error.c_str());state=next;sync();
 }
 void doKill()override{
  mBuildShape->del();if(mStartWaypoint)mStartWaypoint->setFlag(true);if(mEndWaypoint)mEndWaypoint->setFlag(true);
  bodies.erase(std::remove(bodies.begin(),bodies.end(),this),bodies.end());if(!nodeAttached||!workObjectMgr->originalForget(this))die("source bridge lost physical node");nodeAttached=false;WorkObject::doKill();
 }
};
GenObject* make(){return new GenObjectOriginalBridge;}
void cache(GenObjectOriginalBridge& object,RandomAccessStream& stream,bool write){
 unsigned char bytes[104]{};if(stream.getPending()<104)die("bridge generator cache truncated/full");
 if(write){auto digest=bridgeDigest(row(object.uid));std::memcpy(bytes,"BRC1",4);std::memcpy(bytes+4,digest.data(),64);for(int i=0;i<4;++i)bytes[68+i]=static_cast<unsigned char>(object.uid>>(8*i));pc_netplay_sha::sha256(bytes,72,bytes+72);for(auto v:bytes)stream.writeByte(v);return;}
 for(auto& v:bytes)v=stream.readByte();unsigned char digest[32];pc_netplay_sha::sha256(bytes,72,digest);if(std::memcmp(bytes,"BRC1",4)||std::memcmp(bytes+72,digest,32))die("bridge generator cache checksum/version");unsigned uid=0;for(int i=0;i<4;++i)uid|=unsigned(bytes[68+i])<<(8*i);auto expected=bridgeDigest(row(uid));if(std::memcmp(bytes+4,expected.data(),64))die("bridge generator cache source mismatch");object.uid=uid;
}
}
bool pc_p2_original_bridge_install(const std::vector<p2original::BridgeRecord>& rows,std::string& e){
 if(!records.empty()||!bodies.empty()||admitted||rows.size()>4096){e="bridge authority already installed/too large";return false;}
 std::map<unsigned,p2original::BridgeRecord> next;for(const auto& r:rows){if(!p2original::validateBridge(r,e))return false;if(!next.emplace(r.uid,r).second){e="duplicate source bridge";return false;}}records.swap(next);e.clear();return true;
}
void pc_p2_original_bridge_before_teardown(){
 auto physical=bodies;
 for(auto* b:physical){auto* g=b->mGenerator;b->mGenerator=nullptr;b->kill(false);if(g&&g->mLatestSpawnCreature==b)g->mLatestSpawnCreature=nullptr;}
 for(auto* b:allocations){auto* g=b->mGenerator;if(g&&g->mLatestSpawnCreature==b)g->mLatestSpawnCreature=nullptr;b->mGenerator=nullptr;b->mSearchContext.exit();b->mStartWaypoint=nullptr;b->mEndWaypoint=nullptr;}
}
void pc_p2_original_bridge_unload(){if(!bodies.empty())die("bridge live teardown required before unload");for(auto* b:allocations)if(b->nodeAttached||b->mGenerator||b->mSearchContext.mMgr)die("bridge allocation still attached before unload");for(auto* b:allocations)delete b;allocations.clear();generators.clear();records.clear();shapes.fill(nullptr);admitted=false;}
void pc_p2_original_bridge_register(){auto* f=GenObjectFactory::factory;if(!f)die("bridge factory missing");for(int i=0;i<f->mSpawnerCount;++i)if(f->mSpawnerInfo[i].mID==type)return;if(f->mSpawnerCount>=f->mMaxSpawners)die("bridge factory capacity");f->registerMember(type,make,"original P2 bridge",version);}
GenObjectOriginalBridge::GenObjectOriginalBridge():GenObject(type,"original P2 bridge"){}
void GenObjectOriginalBridge::doRead(RandomAccessStream& stream){if(mVersion!=version)die("bridge adapter version");if(!Generator::ramMode){uid=unsigned(stream.readInt());row(uid);}}
void GenObjectOriginalBridge::doWrite(RandomAccessStream& stream){if(!Generator::ramMode){row(uid);stream.writeInt(int(uid));}}
void GenObjectOriginalBridge::ramLoadParameters(RandomAccessStream& stream){cache(*this,stream,false);}
void GenObjectOriginalBridge::ramSaveParameters(RandomAccessStream& stream){cache(*this,stream,true);}
void GenObjectOriginalBridge::updateUseList(Generator*,int){row(uid);}
bool pc_p2_original_bridge_preflight(const std::vector<Generator*>& list,std::string& e){
 if(admitted||!bodies.empty()||list.size()!=records.size()||!workObjectMgr||!mapMgr||!routeMgr||!gsys){e="bridge admission needs complete source inventory and physical managers";return false;}
 std::map<const Generator*,unsigned> next;std::set<unsigned> seen;
 for(auto* g:list){auto* o=g?dynamic_cast<GenObjectOriginalBridge*>(g->mGenObject):nullptr;if(!o||!records.count(o->uid)||!seen.insert(o->uid).second){e="unknown/duplicate bridge generator";return false;}const auto& r=row(o->uid);
  if(g->mCarryOverFlags!=r.reserved||g->mRespawnInterval!=r.resurrectionDays||g->mDayLimit!=r.dayLimit){e="bridge source metadata mismatch";return false;}
  Vector3f start(r.position[0]+r.offset[0],r.position[1]+r.offset[1],r.position[2]+r.offset[2]);auto p=p2original::bridgeStagePosition(r,p2original::bridgeStageCount(r.type)-1);float yaw=r.rotation[1]*0.017453292519943295f;Vector3f end(p[0]+40*std::sin(yaw),p[1],p[2]+40*std::cos(yaw));
  if(!g->isExpired()){auto* a=routeMgr->findNearestWayPointAll('test',start);auto* b=routeMgr->findNearestWayPointAll('test',end);if(!a||!b||a==b){e="bridge endpoint route absent/distinctness failure";return false;}}
  if(!shapes[r.type]){char path[128];std::snprintf(path,sizeof(path),"p2-original/bridges/type%d.mod",r.type);auto* stream=gsys->openFile(path,true,true);if(!stream){e="converted retail bridge geometry missing";return false;}stream->close();shapes[r.type]=gameflow.loadShape(path,true);if(!shapes[r.type]||shapes[r.type]->mJointCount!=1+2*(2+2*p2original::bridgeStageCount(r.type)-1)||shapes[r.type]->mBaseRoomCount!=2*p2original::bridgeStageCount(r.type)+1){e="retail bridge geometry topology mismatch";return false;}}
  next.emplace(g,o->uid);
 }
 for(const auto& entry:next){auto* g=const_cast<Generator*>(entry.first);const auto& r=row(entry.second);g->mGenPosition.set(r.position[0],r.position[1],r.position[2]);g->mGenOffset.set(r.offset[0],r.offset[1],r.offset[2]);g->_70=r.uid;}
 generators.swap(next);admitted=true;e.clear();return true;
}
Creature* GenObjectOriginalBridge::birth(BirthInfo& info){
 auto g=generators.find(info.mGenerator);if(!admitted||g==generators.end()||g->second!=uid||info.mGenerator->mGenObject!=this)die("bridge birth without full admission");for(auto* b:bodies)if(b->uid==uid)die("duplicate bridge incarnation");const auto& r=row(uid);
 int previous=gsys->setHeap(SYSHEAP_App);auto* b=new SourceBridge(shapes[r.type],uid);allocations.push_back(b);b->mSRT.r.set(0,r.rotation[1]*0.017453292519943295f,0);b->mFaceDirection=b->mSRT.r.y;Vector3f p(r.position[0]+r.offset[0],r.position[1]+r.offset[1],r.position[2]+r.offset[2]);b->init(p);b->mGenerator=info.mGenerator;b->ownedNode=workObjectMgr->originalAdoptNode(b);b->nodeAttached=true;bodies.push_back(b);b->startAI(0);gsys->setHeap(previous);std::printf("P2_ORIGINAL_BRIDGE_BIRTH uid=%u type=%d stages=%d retail_geometry=1\n",uid,r.type,b->mStageCount);return b;
}
bool pc_p2_original_bridge_generator_init(Generator* g,bool& handled,std::string& e){
 auto* o=g?dynamic_cast<GenObjectOriginalBridge*>(g->mGenObject):nullptr;handled=o!=nullptr;if(!handled)return true;if(!admitted||!generators.count(g)||generators.at(g)!=o->uid){e="bridge init without full inventory";return false;}g->mAliveCount=0;g->mLatestSpawnCreature=nullptr;if(!g->isExpired()&&!Generator::ramMode){BirthInfo info;info.mGenerator=g;g->mLatestSpawnCreature=o->birth(info);g->mAliveCount=1;}e.clear();return true;
}
bool pc_p2_original_bridge_generator_load(Generator* g,RandomAccessStream& stream,bool& handled,std::string& e){
 auto* o=g?dynamic_cast<GenObjectOriginalBridge*>(g->mGenObject):nullptr;handled=o!=nullptr;if(!handled)return true;if(!admitted||!generators.count(g)||generators.at(g)!=o->uid||g->mLatestSpawnCreature||stream.getPending()<168){e="bridge load lacks fresh admitted generator/payload";return false;}
 std::vector<std::uint8_t> bytes(168);for(auto& v:bytes)v=stream.readByte();p2original::BridgeState next;if(!p2original::bridgeImport(row(o->uid),bytes,next,e))return false;if(g->isExpired()){g->mLatestSpawnCreature=nullptr;g->mAliveCount=0;return true;}BirthInfo info;info.mGenerator=g;auto* b=static_cast<SourceBridge*>(o->birth(info));b->state=next;b->sync();g->mLatestSpawnCreature=b;g->mAliveCount=1;e.clear();return true;
}
bool pc_p2_original_bridge_owned(const Creature* c){return std::find(bodies.begin(),bodies.end(),c)!=bodies.end();}
float pc_p2_original_bridge_work_damage(Piki* p){
 if(!p||!pikiMgr||!pikiMgr->mPikiParms)die("source bridge work lacks actual Pikmin parameters");
 if(pc_p2_is_white(p))return pc_p2_white_attack();if(pc_p2_is_purple(p))return pc_p2_purple_attack();
 auto& parms=pikiMgr->mPikiParms->mPikiParms;return p->mColor==Red?parms.mRedAttackPower():p->mColor==Blue?parms.mBlueAttackPower():parms.mYellowAttackPower();
}
bool pc_p2_original_bridge_stage_position(const Bridge* b,int stage,Vector3f& out){for(auto* body:bodies)if(body==b){auto p=p2original::bridgeStagePosition(row(body->uid),stage);out.set(p[0],p[1],p[2]);return true;}return false;}
bool pc_p2_original_bridge_stage_finished(const Bridge* b,int stage,bool& out){for(auto* body:bodies)if(body==b){out=stage<0||stage>=body->mStageCount||stage<body->state.stage;return true;}return false;}
std::vector<PcOriginalBridgeLink> pc_p2_original_bridge_links(){std::vector<PcOriginalBridgeLink> out;for(auto* b:bodies){const auto& r=row(b->uid);out.push_back({r.sourceSha+":"+r.sourceKey,{b->mSRT.t.x,b->mSRT.t.y,b->mSRT.t.z},b->state.stage});}return out;}
bool pc_p2_original_bridge_stage(const std::string& id,int& stage){for(auto* b:bodies){const auto& r=row(b->uid);if(id==r.sourceSha+":"+r.sourceKey){stage=b->state.stage;return true;}}return false;}
bool pc_p2_original_bridge_snapshot(const Creature* c,p2original::BridgeState& s,std::string& id){for(auto* b:bodies)if(b==c){s=b->state;const auto& r=row(b->uid);id=r.sourceSha+":"+r.sourceKey;return true;}return false;}
