#include "pc_p2_original_piki_native.h"
#include "pc_p2_original_piki_origin.h"
#include "pc_p2_original_piki_physical.h"
#include "pc_p2_original_piki_recruit.h"
#include "pc_p2_original_progress.h"
#include "pc_p2_original_group_engine.h"
#include "PikiMgr.h"
#include "Stream.h"
#include "netplay/pc_sim_rng.h"
#include <map>
#include <set>
#include <algorithm>
#include <cstdio>
#include <cstdlib>

namespace {
constexpr unsigned type=0x70327069u,version=0x4f503031u;
p2original::PikiManifest atlas;
std::set<unsigned> selected;
std::map<Generator*,unsigned> bindings;
std::set<Generator*> generated;
bool admitted=false;
bool reject(std::string& e,const char* s){e=s;return false;}
[[noreturn]] void fatal(const char* s){std::fprintf(stderr,"P2_ORIGINAL_PIKI_NATIVE_FAIL %s\n",s);std::abort();}
const p2original::PikiSourceRecord* row(unsigned uid){for(const auto& r:atlas.rows)if(r.spawn.uid==uid)return &r;return nullptr;}
std::map<unsigned,int> selectedExpiry;
int calendarLimit(const p2original::PikiSourceRecord& r){auto found=selectedExpiry.find(r.spawn.uid);return found==selectedExpiry.end()?r.dayLimit:found->second;}
GenObject* make(){return new GenObjectOriginalPiki;}
struct Provider final:p2original::PikiSpawnProvider {
 const p2original::PikiSourceRecord& source;std::uint64_t activation;
 Provider(const p2original::PikiSourceRecord& s,std::uint64_t a):source(s),activation(a){}
 bool prepare(const p2original::PikiSpawnRecord& r,std::string& e)override{
  if(&r!=&source.spawn||!pikiMgr||!pikiMgr->mPikiParms)return reject(e,"original Piki physical manager unavailable");e.clear();return true;
 }
 float randomUnit()override{return pc_sim_randf(1.0f);}
 p2original::PikiBirthResult birth(unsigned attempt,const std::array<float,3>& position,bool wild,std::string& e)override{
  OriginalPikiBody body;body.origin={source.sourceKey,source.spawn.uid,attempt,activation,atlas.catalog};
  body.state={std::uint8_t(source.spawn.species),wild,wild};Piki* out=nullptr;
  return pc_p2_original_piki_physical_birth(body,position,out,e);
 }
};
}
bool pc_p2_original_piki_install(const p2original::PikiManifest& manifest,const std::vector<unsigned>& active,std::string& e,const std::map<unsigned,int>& effectiveExpiry){
 if(!atlas.rows.empty()||admitted||!bindings.empty()||!p2original::originalProgress().ready()
  ||manifest.campaign!=p2original::originalProgress().snapshot().campaign)return reject(e,"original Piki install lacks selected campaign authority or fresh scene");
 std::string encoded;if(!p2original::writePikiManifest(manifest,encoded,e))return false;
 std::vector<OriginalPikiSource> sources;std::set<unsigned> all,next;
 for(const auto& r:manifest.rows){all.insert(r.spawn.uid);sources.push_back({r.sourceKey,r.spawn.uid,r.spawn.count,std::uint8_t(r.spawn.species)});}
 for(unsigned uid:active)if(!all.count(uid)||!next.insert(uid).second)return reject(e,"original active Piki census unknown or duplicate UID");
 std::map<unsigned,int> expiry;
 if(!effectiveExpiry.empty()&&effectiveExpiry.size()!=next.size())return reject(e,"original Piki calendar expiry census incomplete");
 for(const auto& value:effectiveExpiry){
  if(!next.count(value.first)||value.second< -1)return reject(e,"original Piki calendar expiry unknown or invalid");
  const auto source=std::find_if(manifest.rows.begin(),manifest.rows.end(),[&](const auto& r){return r.spawn.uid==value.first;});
  const int limit=source->dayLimit==-1?value.second:(value.second==-1?source->dayLimit:std::min(source->dayLimit,value.second));
  expiry.emplace(value.first,limit);
 }
 for(const auto& source:manifest.rows)if(next.count(source.spawn.uid)
  &&(source.sourceKey.find("/nonloop/")!=std::string::npos||source.sourceKey.find("/loop/")!=std::string::npos)
  &&!effectiveExpiry.count(source.spawn.uid))return reject(e,"limited original Piki source requires authenticated declared calendar expiry");
 if(!pc_p2_original_piki_origin_install(manifest.catalog,sources,e))return false;
 if(!pc_p2_original_piki_recruit_bind(manifest.campaign,manifest.catalog,e))return false;
 atlas=manifest;selected=std::move(next);selectedExpiry=std::move(expiry);e.clear();return true;
}
bool pc_p2_original_piki_preflight(const std::vector<Generator*>& inventory,std::string& e){
 if(admitted||atlas.rows.empty()||inventory.size()!=selected.size()||!pikiMgr||!pikiMgr->mPikiParms)return reject(e,"original Piki preflight requires complete selected inventory and physical manager");
 std::map<Generator*,unsigned> next;std::set<unsigned> seen;
 for(auto* g:inventory){auto* o=g?dynamic_cast<GenObjectOriginalPiki*>(g->mGenObject):nullptr;
  if(!o||!selected.count(o->uid)||!seen.insert(o->uid).second||g->readFromRam())return reject(e,"original Piki cached/duplicate/unknown member refused");
  const auto& r=*row(o->uid);
  if(g->_70!=r.spawn.uid||g->mCarryOverFlags!=r.reserved)return reject(e,"original Piki common source metadata mismatch");
  // Full selected-source SAVE transport is not yet qualified. Do not produce
  // an unrepresentable native cache record or silently recreate saved bodies.
  if(r.reserved)return reject(e,"original Piki carry flags require qualified typed cache transport");
  next.emplace(g,o->uid);
 }
 for(const auto& binding:next){const auto& r=*row(binding.second);binding.first->mRespawnInterval=r.resurrectionDays;binding.first->mDayLimit=calendarLimit(r);}
 bindings=std::move(next);admitted=true;e.clear();return true;
}
bool pc_p2_original_piki_generator_init(Generator* g,bool& handled,std::string& e){
 handled=g&&dynamic_cast<GenObjectOriginalPiki*>(g->mGenObject);if(!handled){e.clear();return true;}
 auto i=bindings.find(g);if(!admitted||i==bindings.end()||generated.count(g))return reject(e,"original Piki generator not admitted or already consumed");
 const auto& r=*row(i->second);const auto day=p2original::originalProgress().context().day;
 const int limit=calendarLimit(r);
 if(limit!=-1&&std::int64_t(day)>std::int64_t(limit)){generated.insert(g);g->mAliveCount=0;g->mLatestSpawnCreature=nullptr;e.clear();return true;}
 std::uint64_t activation=0;if(!pc_p2_original_incarnation_next(r.spawn.uid,activation,e))return false;
 Provider provider(r,activation);const auto& s=p2original::originalProgress().snapshot();p2original::PikiSpawnResult result;
 // Retain consumption even on a partial physical failure; never retry the
 // same source activation or rewind its RNG draws/living body ownership.
 generated.insert(g);
 if(!p2original::spawnOriginalPiki(r.spawn,{s.met,s.boot,false},provider,result,e))return false;
 g->mAliveCount=0;g->mLatestSpawnCreature=nullptr;e.clear();return true;
}
void pc_p2_original_piki_unload(){admitted=false;bindings.clear();generated.clear();selected.clear();selectedExpiry.clear();atlas={};pc_p2_original_piki_recruit_unbind();}
void pc_p2_original_piki_register(){auto* f=GenObjectFactory::factory;if(!f)fatal("factory unavailable");for(int i=0;i<f->mSpawnerCount;++i)if(f->mSpawnerInfo[i].mID==type)return;if(f->mSpawnerCount>=f->mMaxSpawners)fatal("factory full");f->registerMember(type,make,"original P2 GenPiki",version);}
GenObjectOriginalPiki::GenObjectOriginalPiki():GenObject(type,"original P2 GenPiki"){}
void GenObjectOriginalPiki::doRead(RandomAccessStream& s){if(mVersion!=version||Generator::ramMode)fatal("unsupported Piki adapter/cache version");unsigned next=unsigned(s.readInt());if(!row(next)||!selected.count(next))fatal("Piki UID not selected from immutable atlas");uid=next;}
void GenObjectOriginalPiki::doWrite(RandomAccessStream& s){if(Generator::ramMode||!row(uid))fatal("unsupported Piki cache or missing source");s.writeInt(int(uid));}
void GenObjectOriginalPiki::ramLoadParameters(RandomAccessStream&){fatal("original Piki RAM cache transport unqualified");}
void GenObjectOriginalPiki::ramSaveParameters(RandomAccessStream&){fatal("original Piki RAM cache transport unqualified");}
Creature* GenObjectOriginalPiki::birth(BirthInfo&){fatal("original Piki attempted generic birth fallback");}
