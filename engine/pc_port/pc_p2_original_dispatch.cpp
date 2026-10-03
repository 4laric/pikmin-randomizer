#include "pc_p2_original_dispatch.h"
namespace p2original { namespace {
bool fail(std::string& e,const char* text){e=text;return false;}
bool same(const CatalogRow& a,const CatalogRow& b){
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
bool Dispatch::add(unsigned source,GroupProvider& provider,const Catalog::Capability& check,std::string& e){
 if(mPrepared||!mOwned.empty()||!check||source>65535||mFamilies.count(source))return fail(e,"original family registration is invalid or already frozen");
 mFamilies.emplace(source,Family{&provider,check});e.clear();return true;
}
unsigned Dispatch::familyKey(unsigned source)const{
 auto* provider=mFamilies.at(source).provider;
 // Deterministic family order is smallest literal source ID, never addresses.
 for(const auto& entry:mFamilies)if(entry.second.provider==provider)return entry.first;
 return source;
}
bool Dispatch::capability(const CatalogRow& row,std::string& e)const{
 auto f=mFamilies.find(row.enemy.source);
 if(f==mFamilies.end()){e="original source provider unavailable: "+std::to_string(row.enemy.source)+" ("+row.sourceKey+")";return false;}
 return f->second.capability(row,e);
}
bool Dispatch::preflight(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mOwned.empty())return fail(e,"original dispatcher still owns physical actors");
 mPrepared=false;mReserved=false;mRows.clear();
 // A selected item/Pikmin-only scene owns no enemy family reservations.
 if(rows.empty()){mPrepared=true;e.clear();return true;}
 // Validate ALL source IDs/tails/UIDs before a physical resource callback.
 Catalog checked;
 if(!checked.install(std::string(64,'0'),rows,[this](const CatalogRow& r,std::string& e){return capability(r,e);},e))return false;
 std::map<unsigned,std::vector<CatalogRow>> groups;
 for(const auto& row:rows)groups[familyKey(row.enemy.source)].push_back(row);
 for(const auto& group:groups)if(!mFamilies.at(group.first).provider->preflight(group.second,e))return false;
 mRows=checked.rows();mPrepared=true;e.clear();return true;
}
bool Dispatch::reserve(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mPrepared||mReserved||rows.size()!=mRows.size())return fail(e,"original dispatcher reservation requires exact preflight inventory");
 std::set<unsigned> seen;std::map<unsigned,std::vector<CatalogRow>> groups;
 for(const auto& row:rows){auto found=mRows.find(row.enemy.uid);
  if(found==mRows.end()||!seen.insert(row.enemy.uid).second||!same(found->second,row))return fail(e,"original dispatcher source changed after admission");
  groups[familyKey(row.enemy.source)].push_back(row);
 }
 for(const auto& group:groups)if(!mFamilies.at(group.first).provider->reserve(group.second,e))return false;
 mReserved=true;e.clear();return true;
}
bool Dispatch::birth(const CatalogRow& row,Generator* generator,unsigned ordinal,const Position& position,float radians,Creature*& out,std::string& e){
 out=nullptr;auto found=mRows.find(row.enemy.uid);
 if(!mReserved||found==mRows.end()||!same(found->second,row)||ordinal>=row.enemy.count)return fail(e,"original dispatcher birth outside reserved source");
 auto* provider=mFamilies.at(row.enemy.source).provider;
 const bool born=provider->birth(row,generator,ordinal,position,radians,out,e);
 if(out){
  // Retain cleanup routing even when a family reports partial birth failure.
  if(mOwned.count(out))return fail(e,"original physical provider reused live actor");
  mOwned.emplace(out,Owned{provider,row.enemy.uid});
 }
 return born;
}
bool Dispatch::bind(const CatalogRow& row,Creature* actor,unsigned token,std::string& e){
 auto found=mOwned.find(actor);auto source=mRows.find(row.enemy.uid);
 if(found==mOwned.end()||source==mRows.end()||found->second.uid!=row.enemy.uid||!same(source->second,row))return fail(e,"original dispatcher bind changed actor source");
 return found->second.provider->bind(row,actor,token,e);
}
bool Dispatch::release(Creature* actor,unsigned token,std::string& e){
 auto found=mOwned.find(actor);if(found==mOwned.end())return fail(e,"original dispatcher release lacks physical ownership");
 auto* provider=found->second.provider;
 if(!provider->release(actor,token,e))return false;
 // The actual native kill can call retired() synchronously.
 mOwned.erase(actor);e.clear();return true;
}
void Dispatch::retired(Creature* actor){mOwned.erase(actor);}
}
