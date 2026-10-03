#include "pc_p2_original_foliage.h"
#include "pc_p2_retail_cave_context.h"
#include <cmath>
#include <set>
namespace p2original { namespace foliage {
namespace {
bool reject(std::string& e,const char* s){e=s;return false;}
bool sameRow(const CatalogRow& a,const CatalogRow& b){
 const auto& x=a.enemy;const auto& y=b.enemy;
 return a.course==b.course&&a.member==b.member&&a.index==b.index&&a.sourceKey==b.sourceKey
 &&a.sourceForm==b.sourceForm&&a.caveFloor==b.caveFloor&&a.caveRow==b.caveRow&&a.caveSourceSha256==b.caveSourceSha256
 &&x.source==y.source&&x.uid==y.uid&&x.birthType==y.birthType&&x.count==y.count&&x.deathCount==y.deathCount&&x.spawnType==y.spawnType
 &&x.position.x==y.position.x&&x.position.y==y.position.y&&x.position.z==y.position.z
 &&x.offset.x==y.offset.x&&x.offset.y==y.offset.y&&x.offset.z==y.offset.z
 &&x.directionDegrees==y.directionDegrees&&x.appearRadius==y.appearRadius&&x.enemySize==y.enemySize
 &&x.treasureCode==y.treasureCode&&x.pelletColor==y.pelletColor&&x.pelletSize==y.pelletSize
 &&x.pelletMinimum==y.pelletMinimum&&x.pelletMaximum==y.pelletMaximum&&x.pelletProbability==y.pelletProbability
 &&x.generatorVersion==y.generatorVersion&&x.generatorTail==y.generatorTail;
}

}
bool supported(unsigned source){return source==46||source==47||source==49||source==51||source==52||source==80||source==81||source==88||source==90||source==91||source==92;}
bool decode(const CatalogRow& row,std::string& e){
 if(!supported(row.enemy.source))return reject(e,"unsupported original foliage source");
 if(row.sourceForm!=SourceForm::SurfaceGenEnemy||row.caveFloor||row.caveRow||!row.caveSourceSha256.empty())return reject(e,"surface foliage requires surface provenance");
 if(!validateOriginalRecord(row.enemy,e))return false;
 if(row.enemy.generatorVersion!="????"||!row.enemy.generatorTail.empty())return reject(e,"Plants default generator requires literal ???? and empty tail");
 // These admitted sources reserve no Spectralid child slot. Their immutable common
 // fields remain in the catalog, but an invulnerable plant never pays drops.
 if(row.enemy.pelletColor==0&&row.enemy.pelletSize==1)return reject(e,"foliage Spectralid sentinel requires a qualified child provider");
 e.clear();return true;
}
bool caveDecode(const CatalogRow& row,std::string& e){
 if(row.sourceForm!=SourceForm::CaveTekiInfo)return reject(e,"cave foliage requires CaveTekiInfo provenance");
 if(row.enemy.source!=47&&row.enemy.source!=91&&row.enemy.source!=92)return reject(e,"unsupported cave foliage source");
 const auto* cave=p2retail::descriptor(row.course);
 const auto* floor=cave?p2retail::definition(*cave,row.caveFloor):nullptr;
 if(!floor||row.caveRow>=floor->rows.size()||row.member!=cave->source||row.caveSourceSha256!=cave->sourceSha256
  ||row.index!=row.caveFloor*256+row.caveRow||row.sourceKey!=row.course+"/"+row.member+"#"+std::to_string(row.index)
  ||row.enemy.uid!=originalGeneratorUid(row.sourceKey))return reject(e,"unauthenticated cave foliage association");
 const auto& literal=floor->rows[row.caveRow];
 const std::string name=row.enemy.source==47?"Clover":row.enemy.source==91?"KareOoinu_s":"KareOoinu_l";
 if((literal.kind!="enemy"&&literal.kind!="cap_enemy")||literal.sourceId!=int(row.enemy.source)||literal.sourceToken!=name||literal.catalogId!=name
  ||literal.dropMode||!literal.heldTreasure.empty()||literal.boss||literal.weight()||literal.minimum()>10)
  return reject(e,"cave foliage TekiInfo requires unqualified source behavior");
 // Only these association-envelope fields are defined by the cave registry.
 // Reject altered transport defaults without assigning them GenEnemy semantics.
 CatalogRow expected;expected.course=cave->cave;expected.member=cave->source;expected.index=row.index;expected.sourceKey=row.sourceKey;
 expected.sourceForm=SourceForm::CaveTekiInfo;expected.caveFloor=row.caveFloor;expected.caveRow=row.caveRow;expected.caveSourceSha256=cave->sourceSha256;
 expected.enemy.source=unsigned(literal.sourceId);expected.enemy.uid=originalGeneratorUid(expected.sourceKey);expected.enemy.count=literal.minimum();expected.enemy.generatorVersion="CAVE";
 if(!sameRow(row,expected))return reject(e,"cave foliage envelope differs from authenticated TekiInfo");
 e.clear();return true;
}
bool Provider::preflight(const std::vector<CatalogRow>& rows,std::string& e){
 return prepare(rows,false,e);
}
bool Provider::cavePrepare(const std::vector<CatalogRow>& rows,std::string& e){return prepare(rows,true,e);}
bool Provider::prepare(const std::vector<CatalogRow>& rows,bool cave,std::string& e){
 if(!mHosts.empty())return reject(e,"foliage preflight with live actors");
 mPrepared=mReserved=false;mCave=cave;mAdmitted.clear();mRemaining.clear();mResources.clear();
 mUsedCaveOrdinals.clear();mUsedCaveTokens.clear();
 std::map<unsigned,CatalogRow> admitted;std::map<unsigned,Resources> resources;
 for(const auto& r:rows){if(!supported(r.enemy.source))continue;
  if(!(cave?caveDecode(r,e):decode(r,e)))return false;
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
 return reserveMode(rows,false,e);
}
bool Provider::caveReserve(const std::vector<CatalogRow>& rows,std::string& e){return reserveMode(rows,true,e);}
bool Provider::reserveMode(const std::vector<CatalogRow>& rows,bool cave,std::string& e){
 if(!mPrepared||mReserved||!mHosts.empty()||mCave!=cave)return reject(e,"foliage reservation requires fresh matching preflight");
 std::set<unsigned> seen;std::map<unsigned,unsigned> remaining;unsigned total=0;
 for(const auto& r:rows){if(!supported(r.enemy.source))continue;auto i=mAdmitted.find(r.enemy.uid);
  if(i==mAdmitted.end()||!sameRow(r,i->second)||!seen.insert(r.enemy.uid).second)return reject(e,"foliage reservation changed original catalog");
  unsigned n=cave?r.enemy.count:r.enemy.count-r.enemy.deathCount;remaining.emplace(r.enemy.uid,n);total+=n;
 }
 if(seen.size()!=mAdmitted.size())return reject(e,"foliage reservation omitted original rows");
 if(!mEngine.reserve(total,e))return false;
 mRemaining=std::move(remaining);mReserved=true;e.clear();return true;
}
Host* Provider::lookup(Creature* c){auto i=mHosts.find(c);return i==mHosts.end()?nullptr:i->second.get();}
const Host* Provider::lookup(const Creature* c)const{auto i=mHosts.find(const_cast<Creature*>(c));return i==mHosts.end()?nullptr:i->second.get();}
bool Provider::birth(const CatalogRow& r,Generator* g,unsigned ordinal,const Position& p,float facing,Creature*& out,std::string& e){
 return birthMode(r,g,ordinal,p,facing,false,out,e);
}
bool Provider::caveBirth(const CatalogRow& r,Generator* g,unsigned ordinal,const Position& p,float facing,Creature*& out,std::string& e){return birthMode(r,g,ordinal,p,facing,true,out,e);}
bool Provider::birthMode(const CatalogRow& r,Generator* g,unsigned ordinal,const Position& p,float facing,bool cave,Creature*& out,std::string& e){
 out=nullptr;auto i=mAdmitted.find(r.enemy.uid);auto n=mRemaining.find(r.enemy.uid);
 if(!mReserved||mCave!=cave||!g||i==mAdmitted.end()||n==mRemaining.end()||!n->second||!sameRow(r,i->second)||ordinal>=r.enemy.count
  ||!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z)||!std::isfinite(facing))return reject(e,"foliage birth lacks valid original reservation");
 if(cave&&mUsedCaveOrdinals.count({r.enemy.uid,ordinal}))return reject(e,"cave foliage ordinal already consumed in this reservation");
 for(const auto& entry:mHosts)if((cave?entry.second->row.enemy.uid==r.enemy.uid:entry.second->generator==g)&&entry.second->ordinal==ordinal)return reject(e,"duplicate foliage generator ordinal");
 auto h=std::make_unique<Host>();h->generator=cave?nullptr:g;h->ordinal=ordinal;h->row=r;h->position=p;
 if(!mEngine.allocate(*h,p,facing,e)){
  if(h->creature){std::string cleanup;if(!mEngine.cleanup(*h,cleanup)){out=h->creature;mHosts.emplace(out,std::move(h));e+="; cleanup retained: "+cleanup;}}
  return false;
 }
 if(!h->creature)return reject(e,"foliage native allocation returned no actor");
 if(mHosts.count(h->creature))return reject(e,"foliage native allocator reused live actor");
 out=h->creature;mHosts.emplace(out,std::move(h));if(cave)mUsedCaveOrdinals.insert({r.enemy.uid,ordinal});--n->second;e.clear();return true;
}
bool Provider::bind(const CatalogRow& r,Creature* c,unsigned token,std::string& e){
 auto* h=lookup(c);if(!h||h->token||!token||!sameRow(h->row,r))return reject(e,"foliage registry binding mismatch");
 if(h->row.sourceForm==SourceForm::CaveTekiInfo&&mUsedCaveTokens.count(token))return reject(e,"cave foliage token already consumed in this reservation");
 for(const auto& i:mHosts)if(i.second->token==token)return reject(e,"foliage token already bound");
 if(h->row.sourceForm==SourceForm::CaveTekiInfo)mUsedCaveTokens.insert(token);
 h->token=token;e.clear();return true;
}
bool Provider::release(Creature* c,unsigned token,std::string& e){
 auto* h=lookup(c);if(!h||h->token!=token)return reject(e,"foliage release token mismatch");
 if(!mEngine.cleanup(*h,e))return false;
 mHosts.erase(c);e.clear();return true;
}
bool Provider::tick(Creature* c,float dt,bool /*visible*/,std::string& e){
 auto* h=lookup(c);if(!h||!std::isfinite(dt)||dt<0)return reject(e,"invalid foliage animation tick");
 // The bounded native mechanic keeps an active motion advancing offscreen.
 // Retail calls doAnimationCullingOff only while isCullingOff, which also
 // depends on nearby Pikmin. This port has no proved equivalent of that gate;
 // plain visibility must not be substituted for it or claimed as full fidelity.
 if(h->active){h->frame+=dt*30;
  if(h->frame>=mResources.at(h->row.enemy.source).duration){h->frame=float(mResources.at(h->row.enemy.source).duration-1);h->active=false;h->touched=false;}}
 e.clear();return true;
}
bool Provider::collision(Creature* c,Creature* collider,bool navi,bool teki,float y,float vx,float vz,bool visible,std::string& e){
 auto* h=lookup(c);if(!h)return reject(e,"foliage collision lacks owned actor");
 if(!collider||teki||!visible||y<h->position.y-5||!(std::fabs(vx)>1||std::fabs(vz)>1)){e.clear();return true;}
 if(navi&&!h->touched){if(!mEngine.touchSound(*h,collider,e))return false;h->touched=true;}
 if(!activate(*h,collider,e))return false;
 e.clear();return true;
}
bool Provider::activate(Host& h,Creature* collider,std::string& e){
 if(h.active)return true;
 const float previous=h.frame;h.frame=0;
 // Retail startMotion -> virtual touched -> active. A refused child/effect
 // hook must remain recoverable without committing the new motion frame.
 if(!mEngine.touched(h,collider,e)){h.frame=previous;h.active=false;return false;}
 h.active=true;return true;
}
bool Provider::earthquake(Creature* c,std::string& e){auto* h=lookup(c);if(!h)return reject(e,"foliage earthquake lacks owned actor");if(!activate(*h,nullptr,e))return false;e.clear();return true;}
} }



