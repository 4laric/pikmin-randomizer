#include "pc_p2_original_red.h"
#include "pc_p2_original_drop.h"
#include <cmath>
namespace p2original { namespace red { namespace {
bool refuse(std::string& e,const char* text){e=text;return false;}
bool sameRow(const CatalogRow& a,const CatalogRow& b){
 const auto& x=a.enemy;const auto& y=b.enemy;
 return a.course==b.course&&a.member==b.member&&a.index==b.index&&a.sourceKey==b.sourceKey
 &&x.source==y.source&&x.uid==y.uid&&x.birthType==y.birthType&&x.count==y.count&&x.deathCount==y.deathCount&&x.spawnType==y.spawnType
 &&x.position.x==y.position.x&&x.position.y==y.position.y&&x.position.z==y.position.z
 &&x.offset.x==y.offset.x&&x.offset.y==y.offset.y&&x.offset.z==y.offset.z
 &&x.directionDegrees==y.directionDegrees&&x.appearRadius==y.appearRadius&&x.enemySize==y.enemySize
 &&x.treasureCode==y.treasureCode&&x.pelletColor==y.pelletColor&&x.pelletSize==y.pelletSize
 &&x.pelletMinimum==y.pelletMinimum&&x.pelletMaximum==y.pelletMaximum&&x.pelletProbability==y.pelletProbability
 &&x.generatorVersion==y.generatorVersion&&x.generatorTail==y.generatorTail;
}
}
bool capability(const CatalogRow& row,std::string& e){
 if(!validateOriginalRecord(row.enemy,e)||!validateOriginalDrop(row.enemy,e))return false;
 if(row.enemy.source!=1)return refuse(e,"not an original Red Kochappy source");
 if(row.sourceKey.empty()||row.enemy.uid!=originalGeneratorUid(row.sourceKey))return refuse(e,"red source-key UID mismatch");
 if(row.enemy.generatorVersion!="????"||!row.enemy.generatorTail.empty())return refuse(e,"red requires inherited ???? version and empty literal tail");
 if(row.enemy.birthType!=0)return refuse(e,"red nonzero birth type requires a typed birth adapter");
 if(row.enemy.treasureCode)return refuse(e,"red treasure provider unavailable");
 e.clear();return true;
}
bool Provider::preflight(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mHosts.empty())return refuse(e,"red preflight while actors owned");
 mPrepared=mReserved=false;mRows.clear();mBorn.clear();
 std::map<unsigned,CatalogRow> next;
 for(const auto& row:rows)if(!capability(row,e)||!next.emplace(row.enemy.uid,row).second)return refuse(e,"invalid or duplicate original red row");
 if(next.empty())return refuse(e,"empty red catalog");
 if(!mEngine.prepare(rows,e))return false;
 mRows.swap(next);mPrepared=true;e.clear();return true;
}
bool Provider::reserve(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mPrepared||mReserved||rows.size()!=mRows.size())return refuse(e,"red reservation outside exact preflight");
 unsigned count=0;std::set<unsigned> seen;
 for(const auto& row:rows){auto i=mRows.find(row.enemy.uid);if(i==mRows.end()||!sameRow(row,i->second)||!seen.insert(row.enemy.uid).second)return refuse(e,"red reservation changed original row");count+=row.enemy.count;}
 if(!mEngine.reserve(count,e))return false;mReserved=true;e.clear();return true;
}
bool Provider::birth(const CatalogRow& row,Generator* generator,unsigned ordinal,const Position& position,float facing,Creature*& out,std::string& e){
 out=nullptr;auto i=mRows.find(row.enemy.uid);
 if(!mReserved||!generator||i==mRows.end()||!sameRow(row,i->second)||ordinal>=row.enemy.count||mBorn[row.enemy.uid].count(ordinal)
 ||!std::isfinite(position.x)||!std::isfinite(position.y)||!std::isfinite(position.z)||!std::isfinite(facing))return refuse(e,"red birth outside admitted original activation");
 const bool success=mEngine.allocate(row,generator,position,facing,out,e);
 // Track partial native allocations so GroupCourse can release failures.
 if(out){if(mHosts.count(out))return refuse(e,"red allocator reused owned address");mHosts.emplace(out,Host{row,ordinal,0});}
 if(success||out)mBorn[row.enemy.uid].insert(ordinal);return success;
}
bool Provider::bind(const CatalogRow& row,Creature* actor,unsigned token,std::string& e){
 auto i=mHosts.find(actor);if(!token||i==mHosts.end()||i->second.token||!sameRow(row,i->second.row))return refuse(e,"red bind changed original birth");
 i->second.token=token;if(!mEngine.attach(row,actor,i->second.ordinal,token,e))return false;e.clear();return true;
}
bool Provider::release(Creature* actor,unsigned token,std::string& e){
 auto i=mHosts.find(actor);if(i==mHosts.end()){e.clear();return true;}
 if(i->second.token!=token)return refuse(e,"red release token mismatch");
 if(!mEngine.destroy(actor,e))return false;mHosts.erase(actor);e.clear();return true;
}
} }
