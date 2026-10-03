#include "pc_p2_original_egg.h"
#include <algorithm>
#include <cmath>
#include <tuple>
namespace p2original { namespace egg { namespace {
bool fail(std::string& e,const char* s){e=s;return false;}
bool finite(Position p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);}
bool same(const CatalogRow& a,const CatalogRow& b){
 const auto& x=a.enemy;const auto& y=b.enemy;
 return std::tie(a.course,a.member,a.sourceKey,a.index,x.source,x.uid,x.birthType,x.count,x.deathCount,x.spawnType,
 x.position.x,x.position.y,x.position.z,x.offset.x,x.offset.y,x.offset.z,x.directionDegrees,x.appearRadius,x.enemySize,
 x.treasureCode,x.pelletColor,x.pelletSize,x.pelletMinimum,x.pelletMaximum,x.pelletProbability,x.generatorVersion,x.generatorTail)
 ==std::tie(b.course,b.member,b.sourceKey,b.index,y.source,y.uid,y.birthType,y.count,y.deathCount,y.spawnType,
 y.position.x,y.position.y,y.position.z,y.offset.x,y.offset.y,y.offset.z,y.directionDegrees,y.appearRadius,y.enemySize,
 y.treasureCode,y.pelletColor,y.pelletSize,y.pelletMinimum,y.pelletMaximum,y.pelletProbability,y.generatorVersion,y.generatorTail);
}
} // namespace
bool decode(const CatalogRow& r,std::string& e){
 if(r.enemy.source!=37||r.enemy.generatorVersion!="????"||!r.enemy.generatorTail.empty())return fail(e,"Egg requires literal source37 inherited ???? empty tail");
 return validateOriginalRecord(r.enemy,e);
}
bool Provider::preflight(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mHosts.empty())return fail(e,"Egg resources still own actors");
 mPrepared=mReserved=false;mAdmitted.clear();mRemaining.clear();mUsed.clear();mDependentUsed.clear();mCapturedRemaining=0;
 Resources r;if(!mEngine.resources(r,e))return false;
 if(!r.parametersLoaded||!std::isfinite(r.parameters.health)||r.parameters.health<=0||!r.model||!r.collider||!r.motion||!r.contents||!r.breakEffects||!r.capture)return fail(e,"Egg authored model/parameters/collision/capture/contents/effects unresolved");
 std::map<unsigned,CatalogRow> next;
 for(const auto& row:rows){if(row.enemy.source!=37)continue;
  if(!decode(row,e)||!mEngine.commonResources(row,e))return false;
  if(!next.emplace(row.enemy.uid,row).second)return fail(e,"duplicate original Egg UID");
 }
 mAdmitted=std::move(next);mResources=r;mPrepared=true;e.clear();return true;
}
bool Provider::reserve(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mPrepared||mReserved||!mHosts.empty())return fail(e,"Egg reserve requires fresh preparation");
 std::map<unsigned,unsigned> next;unsigned count=0;
 for(const auto& row:rows){if(row.enemy.source!=37)continue;auto it=mAdmitted.find(row.enemy.uid);
  if(it==mAdmitted.end()||!same(it->second,row)||next.count(row.enemy.uid))return fail(e,"Egg reservation catalog changed");
  next[row.enemy.uid]=row.enemy.count;count+=row.enemy.count;
 }
 if(next.size()!=mAdmitted.size())return fail(e,"Egg reservation omitted original rows");
 if(!mEngine.reserve(count,e))return false;
 mRemaining=std::move(next);mReserved=true;e.clear();return true;
}
bool Provider::reserveCaptured(unsigned n,std::string& e){
 if(!mPrepared||!mHosts.empty()||mCapturedRemaining)return fail(e,"Egg dependencies require resource preparation before births");
 if(!mEngine.reserveCaptured(n,e))return false;
 mCapturedRemaining=n;e.clear();return true;
}
bool Provider::init(Host& h,std::string& e){
 h.parameters=mResources.parameters;h.health=h.parameters.health;
 if(!mEngine.initialize(h,e))return false;
 h.flags.constrained=!h.dropGroup;
 return mEngine.flags(h,h.flags,e)&&mEngine.motion(h,true,true,e);
}
bool Provider::birth(const CatalogRow& row,Generator* generator,unsigned ordinal,const Position& p,float facing,Creature*& out,std::string& e){
 out=nullptr;auto admitted=mAdmitted.find(row.enemy.uid);auto left=mRemaining.find(row.enemy.uid);
 if(!mReserved||!generator||admitted==mAdmitted.end()||!same(admitted->second,row)||left==mRemaining.end()||!left->second||ordinal>=row.enemy.count||!finite(p)||!std::isfinite(facing)||mUsed.count({row.enemy.uid,ordinal}))return fail(e,"Egg birth outside original reservation");
 auto host=std::make_unique<Host>();host->row=row;host->generator=generator;host->ordinal=ordinal;
 bool born=mEngine.allocate(*host,p,facing,e);out=host->creature;
 if(!out){if(born){--left->second;mUsed.emplace(row.enemy.uid,ordinal);e.clear();}return born;}
 if(mHosts.count(out))return fail(e,"Egg allocator reused owned root");
 Host* h=host.get();mHosts.emplace(out,std::move(host));
 if(!born||!init(*h,e))return false;
 --left->second;mUsed.emplace(row.enemy.uid,ordinal);e.clear();return true;
}
Host* Provider::lookup(Creature* actor){auto it=mHosts.find(actor);return it==mHosts.end()?nullptr:it->second.get();}
void Provider::retiredNative(Creature* actor){mHosts.erase(actor);}
bool Provider::bind(const CatalogRow& row,Creature* actor,unsigned token,std::string& e){
 auto* h=lookup(actor);if(!h||h->dependent||h->token||!token||!same(h->row,row))return fail(e,"Egg original binding mismatch");
 for(const auto& entry:mHosts)if(entry.second->token==token)return fail(e,"Egg original token duplicate");
 h->token=token;e.clear();return true;
}
bool Provider::release(Creature* actor,unsigned token,std::string& e){
 auto* h=lookup(actor);if(!h||h->token!=token)return fail(e,"Egg release token mismatch");
 if(!mEngine.cleanup(*h,e))return false;
 mHosts.erase(actor);e.clear();return true;
}
bool Provider::attach(Creature* parent,void* matrix,const Position& p,float facing,Creature*& out,std::string& e){
 out=nullptr;if(!mPrepared||!mCapturedRemaining||!parent||!matrix||!finite(p)||!std::isfinite(facing))return fail(e,"captured Egg lacks actual parent/matrix/reservation");
 std::string identity;if(!mEngine.capturedIdentity(parent,identity,e))return false;
 if(identity.empty()||mDependentUsed.count(identity))return fail(e,"captured Egg incarnation identity missing or duplicate");
 auto host=std::make_unique<Host>();host->dependent=true;host->parent=parent;host->dependentIdentity=identity;
 bool born=mEngine.allocate(*host,p,facing,e);out=host->creature;
 if(!out){if(born){--mCapturedRemaining;mDependentUsed.insert(identity);e.clear();}return born;}
 if(mHosts.count(out))return fail(e,"captured Egg allocator reused owned root");
 Host* h=host.get();mHosts.emplace(out,std::move(host));
 if(!born||!init(*h,e)||!mEngine.startCapture(*h,parent,matrix,e))return false;
 h->captured=true;h->flags.constrained=true;h->flags.invulnerable=true;h->flags.cullable=false;h->flags.living=false;
 if(!mEngine.flags(*h,h->flags,e))return false;
 --mCapturedRemaining;mDependentUsed.insert(identity);e.clear();return true;
}
bool Provider::detach(Creature* actor,std::string& e){
 Host* h=lookup(actor);if(!h||!h->dependent||!h->captured)return fail(e,"Egg capture release outside owned capture");
 if(!mEngine.endCapture(*h,e))return false;
 h->captured=false;h->parent=nullptr;h->falling=true;h->flags.constrained=false;h->flags.cullable=true;h->flags.living=true;
 // Retail onEndCapture does not clear EB_Invulnerable. Contact still breaks it.
 if(!mEngine.flags(*h,h->flags,e))return false;
 e.clear();return true;
}
bool Provider::tick(Creature* actor,float dt,Event event,std::string& e){
 Host* h=lookup(actor);if(!h||(!h->dependent&&!h->token)||!std::isfinite(dt)||dt<0)return fail(e,"Egg update lacks source identity or valid delta");
 if(!mEngine.update(*h,dt,e))return false;
 // Native out-of-world physics can retire the actual body synchronously.
 // Such retirement is not Egg StateWait destruction or contents generation.
 h=lookup(actor);if(!h){e.clear();return true;}
 if(h->health<=0){
  if(!h->contentsGenerated){if(!mEngine.contents(*h,e))return false;h->contentsGenerated=true;}
  if(!h->effectsEmitted){if(!mEngine.breakEffects(*h,e))return false;h->effectsEmitted=true;}
  // kill may retire/free this Host synchronously. Never dereference afterward.
  h->killRequested=true;return mEngine.kill(*h,e);
 }
 if(h->flickTimer>=1){if(!mEngine.motion(*h,false,false,e))return false;h->flickTimer=0;}
 if(event==Event::End&&!mEngine.motion(*h,true,true,e))return false;
 e.clear();return true;
}
bool Provider::damage(Creature* actor,float amount,float flick,std::string& e){
 auto* h=lookup(actor);if(!h||!std::isfinite(amount)||amount<0||!std::isfinite(flick)||flick<0)return fail(e,"invalid Egg damage callback");
 if(!h->flags.invulnerable){h->health=std::max(0.0f,h->health-amount);h->flickTimer+=flick;}
 // Inherited EnemyBase callback returns true even when addDamage is blocked.
 e.clear();return true;
}
bool Provider::press(Creature* actor,std::string& e){if(!lookup(actor))return fail(e,"Egg press outside provider");e.clear();return false;}
bool Provider::breakOnContact(Host& h,std::string& e){
 h.health=0;h.flags.lifeGauge=true;return mEngine.flags(h,h.flags,e);
}
bool Provider::bounce(Creature* actor,std::string& e){auto* h=lookup(actor);if(!h)return fail(e,"Egg bounce outside provider");if(h->falling||h->dropGroup)return breakOnContact(*h,e);e.clear();return true;}
bool Provider::collision(Creature* actor,Creature* other,bool teki,std::string& e){auto* h=lookup(actor);if(!h)return fail(e,"Egg collision outside provider");if(h->dropGroup&&other&&!teki)return breakOnContact(*h,e);e.clear();return true;}
} }
