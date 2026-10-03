#include "pc_p2_original_gate_native.h"
#include "BuildingItem.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "pc_p2_white.h"
#include "pc_p2_purple.h"
#include "Route.h"
#include "MapMgr.h"
#include "EffectMgr.h"
#include "Stream.h"
#include "Msg.h"
#include "sysNew.h"
#include "netplay/pc_netplay_sha256.h"
#include <algorithm>
#include <cmath>
#include <map>
#include <set>
#include <cstdio>
#include <cstdlib>
#include <cstring>
namespace {
using namespace p2original;
constexpr unsigned type=0x70326774u,version=0x47543031u; // p2gt / GT01
struct GateBinding {unsigned uid;GateState state;};
std::map<unsigned,GateRecord> records;
std::vector<unsigned> birthOrder;
std::map<const Generator*,unsigned> generators;
std::map<const Creature*,GateBinding> actors;
bool admitted=false;
[[noreturn]] void die(const char* s){std::fprintf(stderr,"P2_ORIGINAL_GATE_FAIL %s\n",s);std::abort();}
const GateRecord& row(unsigned uid){auto i=records.find(uid);if(i==records.end())die("gate UID absent from original source authority");return i->second;}
GenObject* make(){return new GenObjectOriginalGate;}
void sync(BuildingItem* body,const GateBinding& a){
 const auto& r=row(a.uid);body->mNumStages=3;body->mCurrStage=int(a.state.segmentsDown);
 body->mMaxHealth=r.segmentLife*3;body->mHealth=a.state.phase==GatePhase::Open?0:(2-int(a.state.segmentsDown))*r.segmentLife+a.state.health;
}
void action(BuildingItem* b,GateBinding& a,GateAction next){
 sync(b,a);
 switch(next){
 case GateAction::DamageMotion:b->startMotion(int(a.state.segmentsDown)+3);b->setMotionSpeed(30);break;
 case GateAction::DownMotion:b->startMotion(int(a.state.segmentsDown));b->setMotionSpeed(30);b->startBreakEffect();break;
 case GateAction::Idle:b->stopMotion();b->stopBreakEffect();break;
 case GateAction::Open:b->stopMotion();b->stopBreakEffect();if(b->mSeContext)b->mSeContext->releaseEvent();b->mPlatMgr.release();if(b->mWayPoint)b->mWayPoint->setFlag(true);break;
 case GateAction::None:break;
 }
}
class GateAI final:public SimpleAI {
public:
 void exec(AICreature* c)override{auto i=actors.find(c);if(i==actors.end())die("source gate AI lost identity");auto* b=static_cast<BuildingItem*>(c);i->second.state.animationFrame=b->mItemAnimator.mAnimationCounter;action(b,i->second,gateExec(i->second.state));}
 void procMsg(AICreature* c,Msg* msg)override{
  auto i=actors.find(c);if(i==actors.end())die("source gate animation lost identity");
  if(msg&&msg->mMsgType==MSG_Anim){const auto* key=static_cast<MsgAnim*>(msg)->mKeyEvent;if(key&&key->mEventType==KEY_Finished)action(static_cast<BuildingItem*>(c),i->second,gateAnimationKey(row(i->second.uid),i->second.state));}
 }
};
void restore(BuildingItem* b,GateBinding& a,const GateState& s){
 a.state=s;sync(b,a);if(b->mWayPoint)b->mWayPoint->setFlag(s.phase==GatePhase::Open);
 if(s.phase==GatePhase::Damaged||s.phase==GatePhase::Down){b->startMotion(int(s.segmentsDown)+(s.phase==GatePhase::Damaged?3:0),s.animationFrame);b->setMotionSpeed(30);if(s.phase==GatePhase::Down)b->startBreakEffect();else b->stopBreakEffect();return;}
 b->startMotion(s.phase==GatePhase::Open?2:int(s.segmentsDown));
 if(s.phase==GatePhase::Open){int last=b->mItemAnimator.mAnimInfo->countAKeys()-1;if(last<0)die("gate animation keys missing");b->startMotion(2,b->mItemAnimator.mAnimInfo->getKeyValue(last)-1);b->mPlatMgr.release();}
 b->stopMotion();b->stopBreakEffect();
}
bool nativeFrameValid(const GateState& s,std::string& e){
 if(s.phase!=GatePhase::Damaged&&s.phase!=GatePhase::Down)return true;
 unsigned motion=s.segmentsDown+(s.phase==GatePhase::Damaged?3:0);
 if(!itemMgr||!itemMgr->mItemShapes||!itemMgr->mItemShapes[8]||!itemMgr->mItemShapes[8]->mAnimMgr||!itemMgr->mItemMotionTable||motion>=unsigned(itemMgr->mItemMotionTable->mMotionCount)){e="gate pending state lacks native motion resources";return false;}
 auto* entry=itemMgr->mItemMotionTable->getMotion(int(motion));auto* anim=entry?itemMgr->mItemShapes[8]->mAnimMgr->findAnim(entry->mAnimID):nullptr;
 if(!anim||anim->countAKeys()<1||s.animationFrame>anim->getKeyValue(anim->countAKeys()-1)){e="gate pending animation frame exceeds actual native motion";return false;}
 return true;
}
bool readState(RandomAccessStream& stream,const GateRecord& r,GateState& out,std::string& e){
 if(stream.getPending()<128){e="truncated original gate creature cache";return false;}
 std::vector<std::uint8_t> bytes(128);for(auto& v:bytes)v=stream.readByte();GateState next;if(!gateImport(r,bytes,next,e)||!nativeFrameValid(next,e))return false;out=next;return true;
}
void cache(GenObjectOriginalGate& object,RandomAccessStream& stream,bool write){
 unsigned char bytes[104]{};
 if(write){const auto digest=gateDigest(row(object.uid));std::memcpy(bytes,"GTC1",4);std::memcpy(bytes+4,digest.data(),64);for(unsigned i=0;i<4;++i)bytes[68+i]=static_cast<unsigned char>((object.uid>>(8*i))&255);pc_netplay_sha::sha256(bytes,72,bytes+72);}
 if(stream.getPending()<104)die("truncated or full original gate generator cache");
 if(write){for(auto b:bytes)stream.writeByte(b);return;}
 for(auto& b:bytes)b=stream.readByte();unsigned char digest[32];pc_netplay_sha::sha256(bytes,72,digest);
 if(std::memcmp(bytes,"GTC1",4)||std::memcmp(digest,bytes+72,32))die("gate generator cache checksum/version mismatch");
 unsigned uid=0;for(unsigned i=0;i<4;++i)uid|=unsigned(bytes[68+i])<<(8*i);
 auto expected=gateDigest(row(uid));if(std::memcmp(bytes+4,expected.data(),64))die("gate generator cache source mismatch");object.uid=uid;
}
}
bool pc_p2_original_gate_install(const std::vector<p2original::GateRecord>& rows,std::string& e){
 if(!records.empty()||!actors.empty()||!generators.empty()||rows.empty()||rows.size()>4096){e="gate authority already installed or incomplete";return false;}
 std::map<unsigned,p2original::GateRecord> next;for(const auto& r:rows){if(!p2original::validateGate(r,e))return false;if(!next.emplace(r.uid,r).second){e="duplicate source gate UID";return false;}}
 records.swap(next);e.clear();return true;
}
void pc_p2_original_gate_unload(){admitted=false;actors.clear();generators.clear();records.clear();birthOrder.clear();}
void pc_p2_original_gate_register(){auto* f=GenObjectFactory::factory;if(!f)die("gate native factory missing");for(int i=0;i<f->mSpawnerCount;++i)if(f->mSpawnerInfo[i].mID==type)return;if(f->mSpawnerCount>=f->mMaxSpawners)die("gate factory capacity exhausted");f->registerMember(type,make,"original P2 gate",version);}
GenObjectOriginalGate::GenObjectOriginalGate():GenObject(type,"original P2 gate"){}
void GenObjectOriginalGate::doRead(RandomAccessStream& s){if(mVersion!=version)die("gate adapter version mismatch");if(Generator::ramMode)return;auto next=unsigned(s.readInt());row(next);uid=next;}
void GenObjectOriginalGate::doWrite(RandomAccessStream& s){if(Generator::ramMode)return;row(uid);s.writeInt(int(uid));}
void GenObjectOriginalGate::ramLoadParameters(RandomAccessStream& s){cache(*this,s,false);}
void GenObjectOriginalGate::ramSaveParameters(RandomAccessStream& s){cache(*this,s,true);}
void GenObjectOriginalGate::updateUseList(Generator*,int){row(uid);if(!itemMgr)die("gate item manager absent");itemMgr->addUseList(OBJTYPE_SluiceSoft);itemMgr->addUseList(OBJTYPE_SluiceHard);}
bool pc_p2_original_gate_preflight(const std::vector<Generator*>& list,std::string& e){
 auto reject=[&](const char* s){e=s;return false;};
 if(admitted||!actors.empty()||records.empty()||list.size()!=records.size()||!itemMgr||!itemMgr->mMeltingPotMgr||!gsys||!mapMgr||!routeMgr||!effectMgr)return reject("gate admission needs complete inventory and native managers");
 if(!itemMgr->mItemShapes||!itemMgr->mItemShapes[8]||!itemMgr->mItemShapes[8]->mShape||!itemMgr->mItemShapes[8]->mAnimMgr)return reject("gate family resources missing");
 std::map<const Generator*,unsigned> next;std::set<unsigned> seen;
 for(auto* g:list){auto* o=g?dynamic_cast<GenObjectOriginalGate*>(g->mGenObject):nullptr;if(!o||!records.count(o->uid)||!seen.insert(o->uid).second)return reject("unknown/duplicate/wrong gate generator");const auto& r=row(o->uid);
  if(g->mCarryOverFlags!=r.reserved||g->mRespawnInterval!=r.resurrectionDays||g->mDayLimit!=r.dayLimit)return reject("gate source common metadata mismatch");
  Vector3f p(r.position[0]+r.offset[0],r.position[1]+r.offset[1],r.position[2]+r.offset[2]);if(!g->isExpired()&&!routeMgr->findNearestWayPointAll('test',p))return reject("gate physical route missing");next.emplace(g,r.uid);
 }
 for(const auto& binding:next){auto* g=const_cast<Generator*>(binding.first);const auto& r=row(binding.second);g->mGenPosition.set(r.position[0],r.position[1],r.position[2]);g->mGenOffset.set(r.offset[0],r.offset[1],r.offset[2]);g->_70=r.uid;}
 generators.swap(next);admitted=true;e.clear();return true;
}
Creature* GenObjectOriginalGate::birth(BirthInfo& info){
 const auto& r=row(uid);auto g=generators.find(info.mGenerator);
 if(!admitted||!info.mGenerator||info.mGenerator->mGenObject!=this||g==generators.end()||g->second!=uid)die("gate birth without whole inventory admission");
 for(const auto& a:actors)if(a.second.uid==uid)die("duplicate gate source body");
 int previous=gsys->setHeap(SYSHEAP_App);auto* b=static_cast<BuildingItem*>(itemMgr->birth(r.color?OBJTYPE_SluiceHard:OBJTYPE_SluiceSoft));if(!b)die("gate native allocation failed");
 Vector3f p(r.position[0]+r.offset[0],r.position[1]+r.offset[1],r.position[2]+r.offset[2]);b->mNumStages=3;b->init(p);b->mSRT.r.set(0,r.rotation[1]*0.017453292519943295f,0);b->mFaceDirection=b->mSRT.r.y;b->mGenerator=info.mGenerator;b->mMaxHealth=r.segmentLife*3;
 b->startAI(0);b->mSRT.t=p;b->_448=p;b->mLifeGauge.mPosition=p;b->mLifeGauge.mPosition.y+=110;
 auto binding=actors.emplace(b,GateBinding{uid,gateInitial(r)}).first;birthOrder.push_back(uid);b->mSAICtx.mStateMachine=new GateAI;b->mSAICtx.mCurrentState=nullptr;sync(b,binding->second);gsys->setHeap(previous);
 info.mGenerator->_70=uid;
 std::printf("P2_ORIGINAL_GATE_BIRTH uid=%u color=%d segment_life=%.6f x=%.6f y=%.6f z=%.6f native_family=1 retail_model=0\n",uid,r.color,r.segmentLife,p.x,p.y,p.z);return b;
}
bool pc_p2_original_gate_generator_init(Generator* g,bool& handled,std::string& e){
 auto* o=g?dynamic_cast<GenObjectOriginalGate*>(g->mGenObject):nullptr;handled=o!=nullptr;if(!handled)return true;
 if(!admitted||!generators.count(g)||generators.at(g)!=o->uid){e="gate Generator::init without full admission";return false;}
 g->mAliveCount=0;g->mLatestSpawnCreature=nullptr;if(g->isExpired()||Generator::ramMode){e.clear();return true;}
 BirthInfo info;info.mGenerator=g;g->mLatestSpawnCreature=o->birth(info);g->mAliveCount=g->mLatestSpawnCreature?1:0;e.clear();return true;
}
bool pc_p2_original_gate_generator_load(Generator* g,RandomAccessStream& stream,bool& handled,std::string& e){
 auto* o=g?dynamic_cast<GenObjectOriginalGate*>(g->mGenObject):nullptr;handled=o!=nullptr;if(!handled)return true;
 if(!admitted||!generators.count(g)||generators.at(g)!=o->uid||g->mLatestSpawnCreature){e="gate creature load without fresh admitted generator";return false;}
 GateState state;if(!readState(stream,row(o->uid),state,e))return false;
 if(g->isExpired()){g->mLatestSpawnCreature=nullptr;g->mAliveCount=0;e.clear();return true;}
 BirthInfo info;info.mGenerator=g;auto* b=static_cast<BuildingItem*>(o->birth(info));restore(b,actors.at(b),state);g->mLatestSpawnCreature=b;g->mAliveCount=1;e.clear();return true;
}
bool pc_p2_original_gate_owned(const Creature* c){return actors.count(c)!=0;}
float pc_p2_original_gate_work_damage(Piki* p){
 if(!p||!pikiMgr||!pikiMgr->mPikiParms)die("source gate work has no physical Pikmin parameters");
 if(pc_p2_is_white(p))return pc_p2_white_attack();if(pc_p2_is_purple(p))return pc_p2_purple_attack();
 auto& parms=pikiMgr->mPikiParms->mPikiParms;
 return p->mColor==Red?parms.mRedAttackPower():p->mColor==Blue?parms.mBlueAttackPower():parms.mYellowAttackPower();
}
bool pc_p2_original_gate_damage(BuildingItem* b,float value,bool& handled){auto i=actors.find(b);handled=i!=actors.end();if(!handled)return false;if(i->second.state.phase==GatePhase::Open||!std::isfinite(value)||value<=0||!std::isfinite(i->second.state.damage+value))return false;action(b,i->second,gateDamage(i->second.state,value));return true;}
bool pc_p2_original_gate_save(BuildingItem* b,RandomAccessStream& stream,bool& handled,std::string& e){
 auto i=actors.find(b);handled=i!=actors.end();if(!handled)return true;std::vector<std::uint8_t> bytes;auto state=i->second.state;state.animationFrame=b->mItemAnimator.mAnimationCounter;if(!gateExport(row(i->second.uid),state,bytes,e)||!nativeFrameValid(state,e))return false;if(stream.getPending()<int(bytes.size())){e="gate creature cache full";return false;}for(auto v:bytes)stream.writeByte(v);e.clear();return true;
}
bool pc_p2_original_gate_load(BuildingItem* b,RandomAccessStream& stream,bool& handled,std::string& e){auto i=actors.find(b);handled=i!=actors.end();if(!handled)return true;GateState s;if(!readState(stream,row(i->second.uid),s,e))return false;restore(b,i->second,s);e.clear();return true;}
bool pc_p2_original_gate_forget(BuildingItem* b){
 auto i=actors.find(b);if(i==actors.end())return false;
 if(!itemMgr||!itemMgr->mMeltingPotMgr)die("owned gate retirement lacks node manager");
 for(auto* n=itemMgr->mMeltingPotMgr->mRootNode.mChild;n;n=n->mNext){auto* node=static_cast<CreatureNode*>(n);if(node->mCreature==b){node->del();unsigned uid=i->second.uid;actors.erase(i);birthOrder.erase(std::remove(birthOrder.begin(),birthOrder.end(),uid),birthOrder.end());return true;}}
 die("owned gate retirement lost physical list node");
}
bool pc_p2_original_gate_snapshot(const Creature* b,GateState& s,std::string& id){auto i=actors.find(b);if(i==actors.end())return false;s=i->second.state;s.animationFrame=static_cast<const BuildingItem*>(b)->mItemAnimator.mAnimationCounter;const auto& r=row(i->second.uid);id=r.sourceSha+":"+r.sourceKey;return true;}
std::vector<PcOriginalGateLink> pc_p2_original_gate_links(){
 std::vector<PcOriginalGateLink> links;
 for(unsigned uid:birthOrder)for(const auto& a:actors)if(a.second.uid==uid){const auto& r=row(uid);const auto& p=a.first->mSRT.t;links.push_back(PcOriginalGateLink{r.sourceSha+":"+r.sourceKey,{p.x,p.y,p.z},a.second.state.phase!=GatePhase::Open});break;}
 return links;
}
bool pc_p2_original_gate_alive(const std::string& identity,bool& alive){for(const auto& link:pc_p2_original_gate_links())if(link.identity==identity){alive=link.alive;return true;}return false;}
