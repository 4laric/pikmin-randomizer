#include "pc_p2_original_foliage.h"
#include <cmath>
#include <set>
namespace p2original { namespace foliage {
namespace {
bool reject(std::string& e,const char* s){e=s;return false;}
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
bool supported(unsigned source){return source==47||source==49||source==88||source==91;}
bool decode(const CatalogRow& row,std::string& e){
 if(!supported(row.enemy.source))return reject(e,"unsupported original foliage source");
 if(!validateOriginalRecord(row.enemy,e))return false;
 if(row.enemy.generatorVersion!="????"||!row.enemy.generatorTail.empty())return reject(e,"Plants default generator requires literal ???? and empty tail");
 // These admitted sources reserve no Spectralid child slot. Their immutable common
 // fields remain in the catalog, but an invulnerable plant never pays drops.
 if(row.enemy.pelletColor==0&&row.enemy.pelletSize==1)return reject(e,"foliage Spectralid sentinel requires a qualified child provider");
 e.clear();return true;
}
bool Provider::preflight(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mHosts.empty())return reject(e,"foliage preflight with live actors");
 mPrepared=mReserved=false;mAdmitted.clear();mRemaining.clear();mResources.clear();
 std::map<unsigned,CatalogRow> admitted;std::map<unsigned,Resources> resources;
 for(const auto& r:rows){if(!supported(r.enemy.source))continue;
  if(!decode(r,e))return false;
  if(!admitted.emplace(r.enemy.uid,r).second)return reject(e,"duplicate original foliage UID");
  // Resource preflight includes authored count-zero rows: absence of a birth
  // does not remove that species from the original manager resource use-list.
  if(!resources.count(r.enemy.source)){Resources bank;
   if(!mEngine.resources(r.enemy.source,bank,e))return false;
   if(!bank.model||!bank.clip||!bank.collider||bank.duration<2||!std::isfinite(bank.health)||bank.health<=0)return reject(e,"original foliage physical bank incomplete");
   resources.emplace(r.enemy.source,bank);
  }
 }
 mAdmitted=std::move(admitted);mResources=std::move(resources);mPrepared=true;e.clear();return true;
}
bool Provider::reserve(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mPrepared||mReserved||!mHosts.empty())return reject(e,"foliage reservation requires fresh preflight");
 std::set<unsigned> seen;std::map<unsigned,unsigned> remaining;unsigned total=0;
 for(const auto& r:rows){if(!supported(r.enemy.source))continue;auto i=mAdmitted.find(r.enemy.uid);
  if(i==mAdmitted.end()||!sameRow(r,i->second)||!seen.insert(r.enemy.uid).second)return reject(e,"foliage reservation changed original catalog");
  unsigned n=r.enemy.count-r.enemy.deathCount;remaining.emplace(r.enemy.uid,n);total+=n;
 }
 if(seen.size()!=mAdmitted.size())return reject(e,"foliage reservation omitted original rows");
 if(!mEngine.reserve(total,e))return false;
 mRemaining=std::move(remaining);mReserved=true;e.clear();return true;
}
Host* Provider::lookup(Creature* c){auto i=mHosts.find(c);return i==mHosts.end()?nullptr:i->second.get();}
const Host* Provider::lookup(const Creature* c)const{auto i=mHosts.find(const_cast<Creature*>(c));return i==mHosts.end()?nullptr:i->second.get();}
bool Provider::birth(const CatalogRow& r,Generator* g,unsigned ordinal,const Position& p,float facing,Creature*& out,std::string& e){
 out=nullptr;auto i=mAdmitted.find(r.enemy.uid);auto n=mRemaining.find(r.enemy.uid);
 if(!mReserved||!g||i==mAdmitted.end()||n==mRemaining.end()||!n->second||!sameRow(r,i->second)||ordinal>=r.enemy.count
  ||!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z)||!std::isfinite(facing))return reject(e,"foliage birth lacks valid original reservation");
 for(const auto& entry:mHosts)if(entry.second->generator==g&&entry.second->ordinal==ordinal)return reject(e,"duplicate foliage generator ordinal");
 auto h=std::make_unique<Host>();h->generator=g;h->ordinal=ordinal;h->row=r;h->position=p;
 if(!mEngine.allocate(*h,p,facing,e)){
  if(h->creature){std::string cleanup;if(!mEngine.cleanup(*h,cleanup)){out=h->creature;mHosts.emplace(out,std::move(h));e+="; cleanup retained: "+cleanup;}}
  return false;
 }
 if(!h->creature)return reject(e,"foliage native allocation returned no actor");
 if(mHosts.count(h->creature))return reject(e,"foliage native allocator reused live actor");
 out=h->creature;mHosts.emplace(out,std::move(h));--n->second;e.clear();return true;
}
bool Provider::bind(const CatalogRow& r,Creature* c,unsigned token,std::string& e){
 auto* h=lookup(c);if(!h||h->token||!token||!sameRow(h->row,r))return reject(e,"foliage registry binding mismatch");
 for(const auto& i:mHosts)if(i.second->token==token)return reject(e,"foliage token already bound");
 h->token=token;e.clear();return true;
}
bool Provider::release(Creature* c,unsigned token,std::string& e){
 auto* h=lookup(c);if(!h||h->token!=token)return reject(e,"foliage release token mismatch");
 if(!mEngine.cleanup(*h,e))return false;
 mHosts.erase(c);e.clear();return true;
}
bool Provider::tick(Creature* c,float dt,bool /*visible*/,std::string& e){
 auto* h=lookup(c);if(!h||!std::isfinite(dt)||dt<0)return reject(e,"invalid foliage animation tick");
 // Plants::doAnimationCullingOff advances every active touched motion;
 // visibility gates model calculation, not the animation clock.
 if(h->active){h->frame+=dt*30;
  if(h->frame>=mResources.at(h->row.enemy.source).duration){h->frame=float(mResources.at(h->row.enemy.source).duration-1);h->active=false;h->touched=false;}}
 e.clear();return true;
}
bool Provider::collision(Creature* c,Creature* collider,bool navi,bool teki,float y,float vx,float vz,bool visible,std::string& e){
 auto* h=lookup(c);if(!h)return reject(e,"foliage collision lacks owned actor");
 if(!collider||teki||!visible||y<h->position.y-5||!(std::fabs(vx)>1||std::fabs(vz)>1)){e.clear();return true;}
 if(navi&&!h->touched){if(!mEngine.touchSound(*h,collider,e))return false;h->touched=true;}
 if(!h->active){h->frame=0;h->active=true;}e.clear();return true;
}
bool Provider::earthquake(Creature* c,std::string& e){auto* h=lookup(c);if(!h)return reject(e,"foliage earthquake lacks owned actor");if(!h->active){h->active=true;h->frame=0;}e.clear();return true;}
} }



