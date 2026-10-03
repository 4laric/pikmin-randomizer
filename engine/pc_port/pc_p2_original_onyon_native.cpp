#include "pc_p2_original_onyon_native.h"
#include "pc_p2_original_onyon_lineage.h"
#include "pc_randomizer.h"
#include "ItemMgr.h"
#include "GoalItem.h"
#include "UfoItem.h"
#include "PlayerState.h"
#include "Route.h"
#include "MapMgr.h"
#include "EffectMgr.h"
#include "Stream.h"
#include "sysNew.h"
#include "netplay/pc_netplay_sha256.h"
#include <map>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <set>
#include <limits>
namespace {
constexpr unsigned type=0x70326f6eu,version=0x4f4e3031u; // p2on / ON01
std::map<unsigned,p2original::OnyonRecord> records;
std::map<const Creature*,unsigned> actors;
std::map<const Creature*,std::uint64_t> incarnations;
std::uint64_t nextIncarnation=1;
std::map<const Generator*,unsigned> generators;
std::function<PcOriginalOnyonProgress()> progress;
std::function<void(int)> notify;
bool admitted=false;
[[noreturn]] void fail(const char* s){std::fprintf(stderr,"P2_ORIGINAL_ONYON_FAIL %s\n",s);std::abort();}
const p2original::OnyonRecord& row(unsigned uid){auto i=records.find(uid);if(i==records.end())fail("onyn UID absent from current original source authority");return i->second;}
GenObject* make(){return new GenObjectOriginalOnyon;}
struct AppHeap {int previous;AppHeap():previous(gsys->setHeap(SYSHEAP_App)){}~AppHeap(){gsys->setHeap(previous);}};
void cache(GenObjectOriginalOnyon& object,RandomAccessStream& stream,bool write){
 unsigned char bytes[104]{};
 if(write){const auto& r=row(object.uid);const auto digest=p2original::onyonDigest(r);std::memcpy(bytes,"ONC1",4);std::memcpy(bytes+4,digest.data(),64);for(unsigned i=0;i<4;++i)bytes[68+i]=static_cast<unsigned char>(object.uid>>(8*i));pc_netplay_sha::sha256(bytes,72,bytes+72);}
 if(stream.getPending()<104)fail("truncated or full original onyn cache stream");
 if(write){for(unsigned char b:bytes)stream.writeByte(b);return;}
 for(auto& b:bytes)b=stream.readByte();unsigned char digest[32];pc_netplay_sha::sha256(bytes,72,digest);
 if(std::memcmp(bytes,"ONC1",4)||std::memcmp(digest,bytes+72,32))fail("original onyn cache checksum/version mismatch");
 unsigned uid=0;for(unsigned i=0;i<4;++i)uid|=unsigned(bytes[68+i])<<(8*i);
 const auto& r=row(uid);const auto expected=p2original::onyonDigest(r);if(std::memcmp(bytes+4,expected.data(),64))fail("original onyn cache typed source changed");object.uid=uid;
}
}
bool pc_p2_original_onyon_install(const std::vector<p2original::OnyonRecord>& rows,std::function<PcOriginalOnyonProgress()> query,std::function<void(int)> onBooted,std::string& e){
 if(!records.empty()||!actors.empty()||!generators.empty()||rows.empty()||rows.size()>4096||!query||!onBooted){e="original onyn authority already installed or callbacks/envelope missing";return false;}
 std::map<unsigned,p2original::OnyonRecord> next;
 for(const auto& r:rows){if(!p2original::validateOnyon(r,e))return false;if(!next.emplace(r.uid,r).second){e="duplicate original onyn UID";return false;}}
 records.swap(next);progress=std::move(query);notify=std::move(onBooted);e.clear();return true;
}
void pc_p2_original_onyon_unload(){admitted=false;actors.clear();incarnations.clear();generators.clear();records.clear();progress={};notify={};}
void pc_p2_original_onyon_register(){auto* f=GenObjectFactory::factory;if(!f)fail("native factory unavailable");for(int i=0;i<f->mSpawnerCount;++i)if(f->mSpawnerInfo[i].mID==type)return;if(f->mSpawnerCount>=f->mMaxSpawners)fail("native factory capacity exhausted");f->registerMember(type,make,"original P2 onyn",version);}
GenObjectOriginalOnyon::GenObjectOriginalOnyon():GenObject(type,"original P2 onyn"){}
void GenObjectOriginalOnyon::doRead(RandomAccessStream& stream){if(mVersion!=version)fail("onyn adapter version mismatch");if(Generator::ramMode)return;unsigned next=unsigned(stream.readInt());row(next);uid=next;}
void GenObjectOriginalOnyon::doWrite(RandomAccessStream& stream){if(Generator::ramMode)return;row(uid);stream.writeInt(int(uid));}
void GenObjectOriginalOnyon::ramLoadParameters(RandomAccessStream& s){cache(*this,s,false);}
void GenObjectOriginalOnyon::ramSaveParameters(RandomAccessStream& s){cache(*this,s,true);}
void GenObjectOriginalOnyon::updateUseList(Generator*,int){const auto& r=row(uid);if(!itemMgr)fail("item manager missing before onyn use-list");itemMgr->addUseList(r.index==4?OBJTYPE_Ufo:OBJTYPE_Goal);}
bool pc_p2_original_onyon_preflight(const std::vector<Generator*>& inventory,std::string& e){
 auto reject=[&](const char* text){e=text;return false;};
 if(admitted||!progress||!notify||!itemMgr||!gsys||!mapMgr||!effectMgr||records.empty()||inventory.size()!=records.size())return reject("original onyn preflight requires complete installed inventory/managers");
 std::set<unsigned> seen;std::set<int> active;const auto state=progress();const auto mask=state.containers;if((mask|state.boot)&~7u)return reject("invalid original container/boot progress");
 std::map<const Generator*,unsigned> bindings;
 for(auto* gen:inventory){auto* object=gen?dynamic_cast<GenObjectOriginalOnyon*>(gen->mGenObject):nullptr;
  if(!object||!records.count(object->uid)||!seen.insert(object->uid).second)return reject("wrong, duplicate or unknown original onyn generator");
  const auto& r=records.at(object->uid);
  if(gen->mCarryOverFlags!=r.reserved||gen->mRespawnInterval!=r.resurrectionDays||gen->mDayLimit!=r.dayLimit)return reject("onyn generator/source common metadata mismatch");
  bindings.emplace(gen,r.uid);
  if(gen->isExpired()||!p2original::onyonEligible(r,mask))continue;
  if(!active.insert(r.index).second)return reject("two eligible original Onyons of one type");
  if(r.index==4?itemMgr->getUfo()!=nullptr:itemMgr->getContainer(r.index)!=nullptr)return reject("proxy landing infrastructure duplicates original onyn");
  Vector3f p(r.position[0]+r.offset[0],r.position[1]+r.offset[1],r.position[2]+r.offset[2]);
  if(!routeMgr||!routeMgr->findNearestWayPoint('test',p,false))return reject("onyn/ship physical route missing");
  if(r.index==4?(!itemMgr->mUfoShape||!itemMgr->mUfoShape->mShape):(!itemMgr->mItemShapes||!itemMgr->mItemShapes[7]||!itemMgr->mItemShapes[7]->mShape))return reject("onyn native family resource missing");
 }
 generators.swap(bindings);admitted=true;e.clear();return true;
}
Creature* GenObjectOriginalOnyon::birth(BirthInfo& info){
 const auto& r=row(uid);
 if(!admitted||!info.mGenerator||info.mGenerator->mGenObject!=this||!itemMgr||!progress||!notify)fail("onyn birth lacks whole-inventory admission/owner/managers/progress");
 auto g=generators.find(info.mGenerator);if(g==generators.end()||g->second!=uid)fail("onyn generator lacks admitted identity binding");
 for(const auto& a:actors)if(a.second==uid)fail("onyn generator attempted duplicate live birth");
 for(const auto& binding:generators)if(binding.first!=info.mGenerator&&binding.second==uid)fail("duplicate onyn source generator");
 const auto state=progress();const auto mask=state.containers;if((mask|state.boot)&~7u)fail("invalid original P2 container/boot progress");
 generators[info.mGenerator]=uid;
 info.mGenerator->_70=uid;info.mGenerator->mCarryOverFlags=r.reserved;info.mGenerator->mRespawnInterval=r.resurrectionDays;info.mGenerator->mDayLimit=r.dayLimit;
 if(!p2original::onyonEligible(r,mask))return nullptr;
 if(r.index==4?itemMgr->getUfo()!=nullptr:itemMgr->getContainer(r.index)!=nullptr)fail("landing infrastructure duplicates an eligible original onyn");
 Vector3f position(r.position[0]+r.offset[0],r.position[1]+r.offset[1],r.position[2]+r.offset[2]);
 if(!routeMgr||!routeMgr->findNearestWayPoint('test',position,false))fail("onyn/ship requires a physical route waypoint");
 if(r.index==4?(!itemMgr->mUfoShape||!itemMgr->mUfoShape->mShape):(!itemMgr->mItemShapes||!itemMgr->mItemShapes[7]||!itemMgr->mItemShapes[7]->mShape))fail("onyn native family resources not preloaded");
 AppHeap heap;Creature* actor=itemMgr->birth(r.index==4?OBJTYPE_Ufo:OBJTYPE_Goal);if(!actor)fail("native onyn allocation failed");
 if(r.index!=4)static_cast<GoalItem*>(actor)->setColorType(r.index);
 actor->init(position);actor->mSRT.r.set(0,r.rotation[1]*0.017453292519943295f,0);actor->mFaceDirection=actor->mSRT.r.y;actor->mGenerator=info.mGenerator;
 if(nextIncarnation==std::numeric_limits<std::uint64_t>::max())fail("original onyn birth incarnation exhausted");
 actors.emplace(actor,uid);incarnations.emplace(actor,nextIncarnation++);actor->startAI(0);
 std::printf("P2_ORIGINAL_ONYON_BIRTH uid=%u index=%d after_boot=%d x=%.6f y=%.6f z=%.6f yaw=%.6f native_family=1 retail_model=0\n",uid,r.index,r.afterBoot,position.x,position.y,position.z,actor->mFaceDirection);
 return actor;
}
bool pc_p2_original_onyon_generator_init(Generator* gen,bool& handled,std::string& e){
 auto* object=gen?dynamic_cast<GenObjectOriginalOnyon*>(gen->mGenObject):nullptr;handled=object!=nullptr;if(!handled)return true;
 if(!admitted||!generators.count(gen)||generators.at(gen)!=object->uid){e="onyn Generator::init without full inventory admission";return false;}
 gen->mAliveCount=0;gen->mLatestSpawnCreature=nullptr;if(gen->isExpired())return true;
 BirthInfo info;info.mGenerator=gen;Creature* actor=object->birth(info);
 if(actor){gen->mLatestSpawnCreature=actor;gen->mAliveCount=1;}e.clear();return true;
}
bool pc_p2_original_onyon_identity(const Creature* actor,std::string& out){auto i=actors.find(actor);if(i==actors.end())return false;const auto& r=row(i->second);out=r.sourceSha+":"+r.sourceKey;return true;}
bool pc_p2_original_onyon_root(const Creature* actor,p2originalonyon::Root& out,std::string& e){
 auto i=actors.find(actor);auto lifetime=incarnations.find(actor);
 if(!admitted||!pc_randomizer_original_session()||i==actors.end()||lifetime==incarnations.end()){
  e="source Onion root lacks current native campaign admission";return false;
 }
 const auto& r=row(i->second);
 const auto* generator=actor?actor->mGenerator:nullptr;
 const auto binding=generators.find(generator);
 const auto* object=generator?dynamic_cast<const GenObjectOriginalOnyon*>(generator->mGenObject):nullptr;
 if(binding==generators.end()||binding->second!=r.uid||!object||object->uid!=r.uid){
  e="source Onion root lost its actual admitted generator binding";return false;
 }
 if(r.index<0||r.index>2||!actor||actor->mObjType!=OBJTYPE_Goal||static_cast<const GoalItem*>(actor)->mOnionColour!=r.index){
  e="source Onion root is not its admitted RGB physical receiver";return false;
 }
 p2originalonyon::Root candidate;candidate.sessionFingerprint=pc_randomizer_session_fingerprint();
 candidate.sourceSha=r.sourceSha;candidate.sourceKey=r.sourceKey;candidate.sourceUid=r.uid;
 candidate.species=static_cast<std::uint8_t>(r.index);candidate.incarnation=lifetime->second;
 if(candidate.sessionFingerprint.size()!=64){e="source Onion root requires a selected immutable campaign";return false;}
 for(char c:candidate.sessionFingerprint)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f'))){e="source Onion root campaign fingerprint invalid";return false;}
 out=std::move(candidate);e.clear();return true;
}
bool pc_p2_original_onyon_campaign_owned(const Creature* actor){return pc_randomizer_original_session()&&actors.count(actor)!=0;}
bool pc_p2_original_onyon_booted(const Creature* actor,bool& out){auto i=actors.find(actor);if(i==actors.end())return false;const auto& r=row(i->second);if(r.index==4)return false;out=bool(progress().boot&(1u<<r.index));return true;}
bool pc_p2_original_onyon_access(const Creature* actor){bool state=false;return pc_p2_original_onyon_booted(actor,state)&&state;}
bool pc_p2_original_onyon_color_access(const Creature* actor,bool apAllowed){bool state=false;return pc_p2_original_onyon_booted(actor,state)?state:apAllowed;}
bool pc_p2_original_onyon_boot(Creature* actor){auto i=actors.find(actor);if(i==actors.end())return false;const auto& r=row(i->second);if(r.index==4)return false;notify(r.index);if(!(progress().boot&(1u<<r.index)))fail("original boot authority rejected native Onion boot");return true;}
