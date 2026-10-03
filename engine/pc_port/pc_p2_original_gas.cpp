#include "pc_p2_original_gas.h"
#include <cmath>
#include <set>
#include <tuple>
#include <algorithm>

namespace p2original { namespace gas {
namespace {
bool fail(std::string& e,const char* s){e=s;return false;}
bool same(const CatalogRow& a,const CatalogRow& b){
 const auto& x=a.enemy;const auto& y=b.enemy;
 return std::tie(a.course,a.member,a.sourceKey,a.index,x.source,x.uid,x.birthType,x.count,x.deathCount,x.spawnType,
 x.position.x,x.position.y,x.position.z,x.offset.x,x.offset.y,x.offset.z,x.directionDegrees,x.appearRadius,x.enemySize,
 x.treasureCode,x.pelletColor,x.pelletSize,x.pelletMinimum,x.pelletMaximum,x.pelletProbability,x.generatorVersion,x.generatorTail)
 ==std::tie(b.course,b.member,b.sourceKey,b.index,y.source,y.uid,y.birthType,y.count,y.deathCount,y.spawnType,
 y.position.x,y.position.y,y.position.z,y.offset.x,y.offset.y,y.offset.z,y.directionDegrees,y.appearRadius,y.enemySize,
 y.treasureCode,y.pelletColor,y.pelletSize,y.pelletMinimum,y.pelletMaximum,y.pelletProbability,y.generatorVersion,y.generatorTail);
}
bool valid(const Parameters& p){
 const float values[]={p.waitTime,p.activeTime,p.attackStartTime,p.stopTime,p.lodNear,p.lodMiddle,p.maxHealth,p.attackDamage,p.attackRadius,p.maxAttackRange,p.maxAttackAngle};
 for(float f:values)if(!std::isfinite(f)||f<0)return false;
 return p.maxHealth>0;
}
bool finite(Position p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);}
}
bool decode(const CatalogRow& row,std::string& e){
 if(row.enemy.source!=21)return fail(e,"GasHiba requires literal original source 21");
 if(!validateOriginalRecord(row.enemy,e))return false;
 if(row.enemy.generatorVersion!="????"||!row.enemy.generatorTail.empty())return fail(e,"GasHiba inherited generator requires ???? and empty tail");
 e.clear();return true;
}
bool nearbyLink(Position pipe,Position item){return std::fabs(item.y-pipe.y)<25.0f&&std::fabs(item.x-pipe.x)<75.0f&&std::fabs(item.z-pipe.z)<75.0f;}
bool damageHeight(Position pipe,Position target,const Parameters& p){float y=target.y-pipe.y;return y<p.maxAttackRange&&y>-p.maxAttackAngle;}
bool gasContains(Position pipe,Position target,const Parameters& p){
 if(!(pipe.y+p.maxAttackRange>target.y&&pipe.y-p.maxAttackAngle<target.y))return false;
 float dx=target.x-pipe.x,dz=target.z-pipe.z;
 return dx*dx+dz*dz<p.attackRadius*p.attackRadius;
}
bool Provider::preflight(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mHosts.empty())return fail(e,"GasHiba preflight has owned actors");
 mPrepared=mReserved=false;mAdmitted.clear();mRemaining.clear();mUsed.clear();
 Resources r;if(!mEngine.resources(r,e))return false;
 if(!r.parametersLoaded||!valid(r.parameters)||!r.model||!r.collider||!r.clips[0]||!r.clips[1])return fail(e,"GasHiba source parameters/rig/collider/clips unresolved");
 std::map<unsigned,CatalogRow> admitted;
 for(const auto& row:rows){if(row.enemy.source!=21)continue;
  if(!decode(row,e)||!mEngine.commonResources(row,e))return false;
  if(!admitted.emplace(row.enemy.uid,row).second)return fail(e,"duplicate GasHiba original generator");
 }
 mResources=r;mAdmitted=std::move(admitted);mPrepared=true;e.clear();return true;
}
bool Provider::reserve(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mPrepared||mReserved||!mHosts.empty())return fail(e,"GasHiba reservation requires fresh preflight");
 unsigned count=0;std::set<unsigned> seen;std::map<unsigned,unsigned> remaining;
 for(const auto& row:rows){if(row.enemy.source!=21)continue;auto it=mAdmitted.find(row.enemy.uid);
  if(it==mAdmitted.end()||!same(it->second,row)||!seen.insert(row.enemy.uid).second)return fail(e,"GasHiba reservation catalog changed");
  // Source lifecycle can reset deathCount on a legitimate respawn. Reserve
  // the complete authored count, before any placement or source RNG draws.
  unsigned n=row.enemy.count;count+=n;remaining[row.enemy.uid]=n;
 }
 if(seen.size()!=mAdmitted.size())return fail(e,"GasHiba reservation omitted source rows");
 if(!mEngine.reserve(count,e))return false;
 mRemaining=std::move(remaining);mReserved=true;e.clear();return true;
}
bool Provider::enter(Host& h,State state,std::string& e){
 if(h.state==State::Attack&&state!=State::Attack){if(!mEngine.gasEffect(h,false,e))return false;h.effectActive=false;}
 if(state==State::Dead){
  Flags flags=h.flags;flags.untargetable=true;flags.lifeGauge=false;flags.invulnerable=true;flags.damageAnimation=false;flags.living=false;
  if(!mEngine.flags(h,flags,e))return false;
  h.flags=flags;
  // Keep the physical pipe; source death is not pool retirement.
  if(!h.deathReported){if(!mEngine.death(h,e))return false;h.deathReported=true;}
  if(!mEngine.motion(h,0,e))return false;
 }else if(state==State::Wait){h.timer=0;if(!mEngine.motion(h,0,e))return false;}
 else {h.timer=0;if(!mEngine.motion(h,1,e)||!mEngine.gasEffect(h,true,e))return false;h.effectActive=true;}
 h.state=state;e.clear();return true;
}
bool Provider::birth(const CatalogRow& row,Generator* generator,unsigned ordinal,const Position& p,float facing,Creature*& out,std::string& e){
 out=nullptr;auto admitted=mAdmitted.find(row.enemy.uid);auto remaining=mRemaining.find(row.enemy.uid);
 if(!mReserved||admitted==mAdmitted.end()||!same(admitted->second,row)||remaining==mRemaining.end()||!remaining->second||!generator
  ||ordinal>=row.enemy.count||!finite(p)||!std::isfinite(facing))return fail(e,"GasHiba birth outside original reservation");
 if(mUsed.count({row.enemy.uid,ordinal}))return fail(e,"duplicate GasHiba source ordinal");
 auto h=std::make_unique<Host>();h->row=row;h->generator=generator;h->ordinal=ordinal;h->position=p;h->parameters=mResources.parameters;h->health=h->parameters.maxHealth;
 if(!mEngine.allocate(*h,p,facing,e)){
  if(h->creature){Creature* actor=h->creature;std::string clean;if(!mEngine.cleanup(*h,clean)){mHosts.emplace(actor,std::move(h));out=actor;e+="; cleanup retained: "+clean;}}
  return false;
 }
 if(!h->creature){--remaining->second;mUsed.emplace(row.enemy.uid,ordinal);e.clear();return true;}
 Creature* actor=h->creature;
 if(mHosts.count(actor))return fail(e,"GasHiba allocator reused owned actor");
 Host& host=*h;mHosts.emplace(actor,std::move(h));float draw=0;
 if(!mEngine.flags(host,host.flags,e)||!mEngine.unitDraw(draw,e)||!std::isfinite(draw)||draw<0||draw>1||!enter(host,State::Wait,e)){
  if(e.empty())e="GasHiba initial source RNG invalid";
  std::string clean;if(!release(actor,0,clean)){out=actor;e+="; cleanup retained: "+clean;}return false;
 }
 host.timer=draw*host.parameters.waitTime;--remaining->second;mUsed.emplace(row.enemy.uid,ordinal);out=actor;e.clear();return true;
}
Host* Provider::lookup(Creature* actor){auto it=mHosts.find(actor);return it==mHosts.end()?nullptr:it->second.get();}
void Provider::retiredNative(Creature* actor){mHosts.erase(actor);}
bool Provider::bind(const CatalogRow& row,Creature* actor,unsigned token,std::string& e){
 Host* h=lookup(actor);if(!h||h->token||!token||!same(h->row,row))return fail(e,"GasHiba original binding mismatch");
 for(const auto& entry:mHosts)if(entry.second->token==token)return fail(e,"GasHiba original token already live");
 h->token=token;e.clear();return true;
}
bool Provider::release(Creature* actor,unsigned token,std::string& e){
 Host* h=lookup(actor);if(!h||h->token!=token)return fail(e,"GasHiba release token mismatch");
 if(!mEngine.cleanup(*h,e))return false;
 mHosts.erase(actor);e.clear();return true;
}
bool Provider::living(Host& h,bool initialize,std::string& e){
 Flags flags=h.flags;
 if(initialize&&h.checkLinks){
  void* bridge=nullptr;void* gate=nullptr;if(!mEngine.findLivingLinks(h,bridge,gate,e))return false;
  h.bridge=bridge;h.gate=bridge?nullptr:gate;h.checkLinks=false;flags.living=!h.bridge&&!h.gate;
 }
 if(!flags.living){
  if(h.bridge){int stage=0;if(!mEngine.bridgeStage(h.bridge,stage,e))return false;if(stage!=0)flags.living=true;}
  else if(h.gate){bool alive=true;if(!mEngine.gateAlive(h.gate,alive,e))return false;if(!alive)flags.living=true;}
  else flags.living=true;
 }
 if(flags.living!=h.flags.living){if(!mEngine.flags(h,flags,e))return false;h.flags=flags;}
 return true;
}
bool Provider::tick(Creature* actor,float dt,Event event,std::string& e){
 Host* h=lookup(actor);if(!h||!h->token||!std::isfinite(dt)||dt<0)return fail(e,"invalid GasHiba source tick");
 if(h->state==State::Dead){e.clear();return true;}
 if(h->state==State::Wait){
  h->timer+=dt;if(!living(*h,true,e))return false;
  if(h->health<=0)return enter(*h,State::Dead,e);
  if(h->timer>h->parameters.waitTime)return enter(*h,State::Attack,e);
 }else {
  // Retail checks active timeout BEFORE increment, emission AFTER increment.
  if(h->health<=0||(h->parameters.waitTime>0&&h->timer>h->parameters.activeTime))if(!mEngine.finishMotion(*h,e))return false;
  h->timer+=dt;
  if(!mEngine.updateEffectLod(*h,e)||!living(*h,false,e))return false;
  if(h->timer>h->parameters.attackStartTime&&!mEngine.gasScan(*h,e))return false;
  if(!mEngine.attackSound(*h,e))return false;
  if(event==Event::End)return enter(*h,h->health<=0?State::Dead:State::Wait,e);
 }
 e.clear();return true;
}
bool Provider::damage(Creature* actor,Creature* attacker,bool navi,Position p,float amount,std::string& e){
 Host* h=lookup(actor);if(!h||!finite(p)||!std::isfinite(amount)||amount<0)return fail(e,"invalid GasHiba damage callback");
 e.clear();if(!attacker||navi||!damageHeight(h->position,p,h->parameters))return false;
 if(!h->flags.invulnerable)h->health=std::max(0.0f,h->health-amount);
 return true;
}
} }
