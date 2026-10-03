#include "pc_p2_original_armor.h"
#include "pc_p2_original_drop.h"
#include <cmath>
namespace p2original { namespace armor {
namespace {
bool fail(std::string& e,const char* why){e=why;return false;}
bool same(const CatalogRow& a,const CatalogRow& b){
 const auto& x=a.enemy;const auto& y=b.enemy;
 return a.course==b.course&&a.member==b.member&&a.sourceKey==b.sourceKey&&a.index==b.index
 &&x.source==y.source&&x.uid==y.uid&&x.birthType==y.birthType&&x.count==y.count&&x.deathCount==y.deathCount&&x.spawnType==y.spawnType
 &&x.position.x==y.position.x&&x.position.y==y.position.y&&x.position.z==y.position.z
 &&x.offset.x==y.offset.x&&x.offset.y==y.offset.y&&x.offset.z==y.offset.z
 &&x.directionDegrees==y.directionDegrees&&x.appearRadius==y.appearRadius&&x.enemySize==y.enemySize
 &&x.treasureCode==y.treasureCode&&x.pelletColor==y.pelletColor&&x.pelletSize==y.pelletSize
 &&x.pelletMinimum==y.pelletMinimum&&x.pelletMaximum==y.pelletMaximum&&x.pelletProbability==y.pelletProbability
 &&x.generatorVersion==y.generatorVersion&&x.generatorTail==y.generatorTail;
}
}
bool admits(const CatalogRow& row,std::string& e){
 const auto& r=row.enemy;
 if(r.source!=15)return fail(e,"original Armor adapter requires source 15");
 if(!validateOriginalRecord(r,e)||!validateOriginalDrop(r,e))return false;
 if(row.course.empty()||row.member.empty()||row.sourceKey!=row.course+"/"+row.member+"#"+std::to_string(row.index)||r.uid!=originalGeneratorUid(row.sourceKey))return fail(e,"original Armor source-key UID mismatch");
 if(r.treasureCode)return fail(e,"original Armor treasure provider unavailable");
 if(r.generatorVersion!="????"||!r.generatorTail.empty())return fail(e,"original Armor requires literal ???? empty generator payload");
 if(r.birthType!=0)return fail(e,"original Armor non-ground birth is not implemented");
 e.clear();return true;
}
bool Provider::preflight(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mHosts.empty())return fail(e,"original Armor preflight with live actors");
 mPrepared=mReserved=false;mRows.clear();mRemaining.clear();mBorn.clear();
 std::map<unsigned,CatalogRow> admitted;std::set<unsigned> sources;
 // Validate the entire request before allocating any physical resource.
 for(const auto& r:rows){if(!admits(r,e))return false;
  if(!admitted.emplace(r.enemy.uid,r).second)return fail(e,"duplicate original Armor generator");sources.insert(r.enemy.source);}
 if(sources.empty())return fail(e,"empty original Armor request");
 if(!mEngine.resources(sources,e))return false;
 for(const auto& r:rows)if(!mEngine.commonResources(r,e))return false;
 mRows=std::move(admitted);mPrepared=true;e.clear();return true;
}
bool Provider::reserve(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mPrepared||mReserved||!mHosts.empty())return fail(e,"original Armor reservation requires fresh preflight");
 std::set<unsigned> seen;std::map<unsigned,unsigned> remaining;unsigned total=0;
 for(const auto& r:rows){auto i=mRows.find(r.enemy.uid);
  if(i==mRows.end()||!same(i->second,r)||!seen.insert(r.enemy.uid).second)return fail(e,"original Armor reservation changed catalog");
  const unsigned n=r.enemy.count-r.enemy.deathCount;remaining[r.enemy.uid]=n;total+=n;}
 if(seen.size()!=mRows.size())return fail(e,"original Armor reservation omitted rows");
 if(!mEngine.reserve(rows,total,e))return false;
 mRemaining=std::move(remaining);mReserved=true;e.clear();return true;
}
bool Provider::birth(const CatalogRow& row,Generator* generator,unsigned ordinal,const Position& p,float facing,Creature*& out,std::string& e){
 out=nullptr;auto admitted=mRows.find(row.enemy.uid);auto remaining=mRemaining.find(row.enemy.uid);
 if(!mReserved||admitted==mRows.end()||remaining==mRemaining.end()||!remaining->second||!same(admitted->second,row))return fail(e,"original Armor birth without unchanged reservation");
 if(!generator||ordinal>=row.enemy.count||mBorn[row.enemy.uid].count(ordinal)||!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z)||!std::isfinite(facing))return fail(e,"invalid original Armor physical birth");
 for(const auto& h:mHosts)if(h.second.generator==generator&&h.second.ordinal==ordinal)return fail(e,"duplicate original Armor ordinal");
 Host h;h.row=row;h.generator=generator;h.ordinal=ordinal;
 mBorn[row.enemy.uid].insert(ordinal);--remaining->second; // Even a failed null physical attempt is permanently consumed.
 const bool born=mEngine.allocate(h,p,facing,e);out=h.actor;
 if(out){if(mHosts.count(out)){out=nullptr;return fail(e,"original Armor allocation reused owned address");}mHosts.emplace(out,std::move(h));}
 return born;
}
bool Provider::bind(const CatalogRow& row,Creature* actor,unsigned token,std::string& e){
 auto h=mHosts.find(actor);if(h==mHosts.end()||!token||h->second.token||!same(row,h->second.row))return fail(e,"original Armor bind lacks physical ownership");
 h->second.token=token;return mEngine.bind(h->second,e);
}
bool Provider::release(Creature* actor,unsigned token,std::string& e){
 auto i=mHosts.find(actor);if(i==mHosts.end())return fail(e,"original Armor release lacks physical ownership");
 if(i->second.token!=token)return fail(e,"original Armor release token mismatch");
 // Native kill calls retired synchronously. Keep a value copy through cleanup.
 Host h=i->second;if(!mEngine.cleanup(h,e))return false;
 mHosts.erase(actor);e.clear();return true;
}
void Provider::retired(Creature* actor){mHosts.erase(actor);}
} }
