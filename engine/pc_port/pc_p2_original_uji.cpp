#include "pc_p2_original_uji.h"
#include "pc_p2_original_drop.h"
#include <cmath>
#include <set>
#include <cstdio>
#include <cstdlib>
namespace p2original { namespace uji {
namespace {
bool refuse(std::string& e,const char* s){e=s;return false;}
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
const char* species(unsigned source){return source==12?"UjiA":source==13?"UjiB":source==14?"Tobi":nullptr;}
int nativeType(unsigned source){return species(source)?int(source)+6:-1;}
bool decode(const CatalogRow& row,std::string& e){
 if(!species(row.enemy.source))return refuse(e,"not an original Uji source");
 if(row.sourceKey!=row.course+"/"+row.member+"#"+std::to_string(row.index)||row.enemy.uid!=originalGeneratorUid(row.sourceKey))return refuse(e,"Uji original UID/sourceKey mismatch");
 if(!validateOriginalDrop(row.enemy,e))return false;
 if(row.enemy.birthType!=0)return refuse(e,"Uji dropped birthType is not implemented");
 if(row.enemy.treasureCode)return refuse(e,"Uji original treasure provider is not implemented");
 if(row.enemy.generatorVersion!="????"||!row.enemy.generatorTail.empty())return refuse(e,"Uji EnemyGeneratorBase requires literal ???? version and empty tail");
 e.clear();return true;
}
Provider::~Provider(){if(!mHosts.empty()){std::fprintf(stderr,"P2_ORIGINAL_UJI provider destroyed with live physical actors\n");std::abort();}}
bool Provider::preflight(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mHosts.empty())return refuse(e,"cannot replace original Uji resources with live actors");
 mPrepared=mReserved=false;mRows.clear();mRemaining.clear();mAttempts.clear();
 std::map<unsigned,CatalogRow> admitted;
 if(rows.empty())return refuse(e,"empty original Uji admission request");
 // Decode all rows before resource callbacks, so a bad later tail is atomic.
 for(const auto& row:rows){if(!species(row.enemy.source))return refuse(e,"non-Uji row supplied to original Uji provider");
  if(!decode(row,e))return false;
  if(!admitted.emplace(row.enemy.uid,row).second)return refuse(e,"duplicate original Uji generator UID");
 }
 for(const auto& entry:admitted)if(!mEngine.resources(entry.second,e))return false;
 mRows=std::move(admitted);mPrepared=true;e.clear();return true;
}
bool Provider::reserve(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mPrepared||mReserved||!mHosts.empty()||rows.empty())return refuse(e,"original Uji reservation requires one completed nonempty preflight");
 mReserved=false;mRemaining.clear();mAttempts.clear();unsigned count=0;std::map<unsigned,unsigned> remaining;
 for(const auto& row:rows){if(!species(row.enemy.source))return refuse(e,"non-Uji row supplied to original Uji reservation");
  auto admitted=mRows.find(row.enemy.uid);
  if(admitted==mRows.end()||!same(admitted->second,row)||!remaining.emplace(row.enemy.uid,row.enemy.count-row.enemy.deathCount).second)return refuse(e,"Uji reservation differs from admitted original rows");
  count+=row.enemy.count-row.enemy.deathCount;
 }
 if(remaining.size()!=mRows.size())return refuse(e,"Uji reservation omitted an admitted row");
 if(!mEngine.reserve(rows,count,e))return false;
 mRemaining=std::move(remaining);mReserved=true;e.clear();return true;
}
bool Provider::birth(const CatalogRow& row,Generator* generator,unsigned ordinal,const Position& p,float facing,Creature*& out,std::string& e){
 out=nullptr;auto admitted=mRows.find(row.enemy.uid);auto remaining=mRemaining.find(row.enemy.uid);
 if(!mReserved||!generator||admitted==mRows.end()||remaining==mRemaining.end()||!remaining->second||!same(admitted->second,row))return refuse(e,"Uji birth lacks unchanged original reservation");
 if(ordinal>=row.enemy.count-row.enemy.deathCount||!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z)||!std::isfinite(facing))return refuse(e,"invalid original Uji ordinal or transform");
 if(mAttempts[row.enemy.uid].count(ordinal))return refuse(e,"original Uji ordinal already attempted");
 mAttempts[row.enemy.uid].insert(ordinal);--remaining->second;
 Host host;host.row=row;host.generator=generator;host.ordinal=ordinal;
 const bool allocated=mEngine.allocate(host,p,facing,e);
 // Retail null birth consumes this placement. A partially constructed real
 // actor is returned to GroupCourse so its cleanup remains authoritative.
 if(!host.actor)return allocated;
 if(!mHosts.emplace(host.actor,host).second)return refuse(e,"Uji allocator reused a live creature");
 out=host.actor;if(allocated)e.clear();return allocated;
}
bool Provider::bind(const CatalogRow& row,Creature* actor,unsigned token,std::string& e){
 Host* host=lookup(actor);if(!host||host->token||!token||!same(host->row,row))return refuse(e,"Uji original registry binding mismatch");
 for(const auto& entry:mHosts)if(entry.second.token==token)return refuse(e,"duplicate Uji registry token");
 host->token=token; // Registry already owns it, including failed native binds.
 return mEngine.bind(*host,e);
}
bool Provider::release(Creature* actor,unsigned token,std::string& e){
 Host* host=lookup(actor);if(!host||host->token!=token)return refuse(e,"Uji cleanup token mismatch");
 Host copy=*host;
 if(!mEngine.cleanup(copy,e))return false;
 mHosts.erase(actor);e.clear();return true;
}
} }
