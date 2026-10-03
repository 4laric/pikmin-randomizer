#include "pc_p2_original_group.h"
#include <cmath>
namespace p2original {namespace {
bool fail(std::string& e,const char* s){e=s;return false;}
}
bool GroupCourse::install(const std::vector<GroupBinding>& bindings,GroupProvider& provider,std::string& e,bool selectedInventory){
 if(mProvider||!mGroups.empty()||(!selectedInventory&&(bindings.empty()||bindings.size()!=mActors.rows().size())))return fail(e,"original course already owned or empty");
 if(!mFrontier.initialize(mActors.fingerprint(),e))return false;
 std::map<Generator*,Group> next;std::vector<CatalogRow> rows;
 for(const auto& b:bindings){
  const auto* row=mActors.find(b.state.uid);std::string encoded;
  if(!b.generator||!row||row->enemy.count!=b.state.count||!encodeOriginalState(std::string(64,'0'),b.state,encoded,e)||next.count(b.generator))return fail(e,"original group binding/state mismatch");
  for(const auto& old:next)if(old.second.state.uid==b.state.uid)return fail(e,"original generator UID bound twice");
  Group g;g.state=b.state;g.actors.reserve(b.state.count);next.emplace(b.generator,std::move(g));rows.push_back(*row);
 }
 // No RNG or actor birth before every physical family and literal tail/drop
 // has passed admission and whole-course capacity/resource reservation.
 if(!provider.preflight(rows,e)||!provider.reserve(rows,e))return false;
 for(auto& entry:next){
  if(!mActors.generator(entry.first,entry.second.state.uid,entry.second.handle,e)){
   for(const auto& registered:next)if(registered.second.handle)mActors.retireGenerator(registered.first,registered.second.handle);
   return false;
  }
 }
 mGroups.swap(next);mProvider=&provider;e.clear();return true;
}
bool GroupCourse::owns(const Generator* g)const{return mGroups.count(const_cast<Generator*>(g))!=0;}
bool GroupCourse::initialize(Generator* generator,unsigned day,bool disc,const Math& math,const std::function<bool(const Position&,float&,std::string&)>& floor,std::string& e){
 if(mCleaning)return fail(e,"original generation during course disposal");
 auto i=mGroups.find(generator);if(i==mGroups.end()||!mProvider)return fail(e,"unbound original generator");auto& group=i->second;
 if(group.started||group.initialized||!group.actors.empty())return fail(e,"original activation already initialized");
 const auto* row=mActors.find(group.state.uid);if(!row)return fail(e,"original catalog row retired");
 GenerationDecision decision;if(!mFrontier.activate(group.state,day,disc,decision,e))return false;
 if(decision.expired){group.state=decision.next;group.initialized=true;e.clear();return true;}
 const GeneratorState activated=decision.next;
 // Reserve the activation before externally visible construction. An aborted
 // attempt may never replay its retired identities in this owning session.
 group.state=activated;group.started=true;
 if(!decision.generate){
  return fail(e,"original saved-creature payload loader is not implemented");
 }
 EnemyRecord record=row->enemy;record.deathCount=activated.deathCount;
 Math placement=math;placement.mapAvailable=false;SpawnPlan plan;
 if(!planSpawns(record,placement,plan,e))return false;
 if(!plan.positions.empty()&&!floor)return fail(e,"original native floor bridge missing");
 constexpr float degreesToRadians=0.01745329251994329577f;
 for(unsigned ordinal=0;ordinal<plan.positions.size();++ordinal){
  auto position=plan.positions[ordinal];float height=0;
  // Retail performs floor THEN birth per actor, not all floors up front.
  if(!floor(position,height,e)||!std::isfinite(height))return fail(e,"original native floor query failed");
  position.y=height;
  Creature* actor=nullptr;
  const bool born=mProvider->birth(*row,generator,ordinal,position,record.directionDegrees*degreesToRadians,actor,e);
  if(!actor){if(!born)return false;continue;} // Retail null birth consumes placement, not deathCount.
  unsigned existingSource=0,existingToken=0;
  if(mActors.query(actor,existingSource,existingToken))return fail(e,"family birth reused an already bound native actor");
  // Record physical ownership BEFORE registry/family callbacks, including a
  // birth callback that reports failure after creating a native root.
  Actor pending;pending.pointer=actor;group.actors.push_back(pending);
  auto& entry=group.actors.back();
  if(!born)return false;
  if(!mActors.actorActivation(actor,record.uid,ordinal,activated.epoch,activated.activation,entry.token,entry.handle,e))return false;
  entry.registryBound=true;
  if(!mProvider->bind(*row,actor,entry.token,e))return false;
 }
 group.initialized=true;e.clear();return true;
}
bool GroupCourse::death(Generator* generator,Creature* actor,std::string& e){
 auto i=mGroups.find(generator);if(i==mGroups.end())return fail(e,"original death outside bound group");
 for(auto& a:i->second.actors)if(a.pointer==actor){
  // Native kill detaches its generator BEFORE family-forget retirement.
  // Course disposal (including partial construction) is not a gameplay death.
  if(mCleaning){e.clear();return true;}
  if(!i->second.initialized||!a.registryBound||a.released)return fail(e,"original death outside initialized live group");
  if(a.dead)return fail(e,"original actor death already recorded");
  GeneratorState next;
  if(!originalDeath(i->second.state,next,e))return false;
  i->second.state=next;a.dead=true;e.clear();return true;
 }
 return fail(e,"original death belongs to another group");
}
bool GroupCourse::retiredNative(Creature* actor,std::string& e){
 for(auto& group:mGroups)for(auto& a:group.second.actors)if(a.pointer==actor){
  if(a.registryBound&&!mActors.retire(actor,a.handle))return fail(e,"native original association retirement failed");
  a.registryBound=false;a.released=true;a.pointer=nullptr;e.clear();return true;
 }
 e.clear();return true; // Ordinary/AP actor or already retired; idempotent.
}
bool GroupCourse::cache(const Generator* generator,const std::string& fingerprint,std::string& bytes,std::string& e)const{
 if(mCleaning)return fail(e,"original cache during course disposal");
 if(fingerprint!=mActors.fingerprint())return fail(e,"original cache catalog binding changed");
 auto i=mGroups.find(const_cast<Generator*>(generator));if(i==mGroups.end()||!i->second.initialized)return fail(e,"original cache requires completed group");
 return encodeOriginalState(fingerprint,i->second.state,bytes,e);
}
bool GroupCourse::restoreState(Generator* generator,const std::string& fingerprint,const std::string& bytes,std::string& e){
 if(mCleaning)return fail(e,"original cache during course disposal");
 if(fingerprint!=mActors.fingerprint())return fail(e,"original cache catalog binding changed");
 auto i=mGroups.find(generator);if(i==mGroups.end()||i->second.started||i->second.initialized||!i->second.actors.empty())return fail(e,"original cache restore before native group init only");
 GeneratorState next;if(!decodeOriginalState(fingerprint,i->second.state.uid,i->second.state.count,bytes,next,e))return false;
 const auto& source=i->second.state;
 if(next.reserved!=source.reserved||next.resurrectionDays!=source.resurrectionDays||next.dayLimit!=source.dayLimit)return fail(e,"original cache changed literal source metadata");
 i->second.state=next;e.clear();return true;
}
bool GroupCourse::state(const Generator* generator,GeneratorState& out,unsigned& alive)const{
 auto i=mGroups.find(const_cast<Generator*>(generator));if(i==mGroups.end())return false;
 unsigned count=0;for(const auto& a:i->second.actors)if(a.registryBound&&!a.dead)++count;out=i->second.state;alive=count;return true;
}
bool GroupCourse::unload(std::string& e){
 if(mCleaning)return fail(e,"reentrant original course disposal");
 if(!mProvider)return mGroups.empty()?true:fail(e,"original provider lost while course owns actors");
 struct CleanupGuard {bool& flag;bool previous;explicit CleanupGuard(bool& f):flag(f),previous(f){flag=true;}~CleanupGuard(){flag=previous;}} cleanup(mCleaning);
 for(auto group=mGroups.begin();group!=mGroups.end();){
  while(!group->second.actors.empty()){
   auto& a=group->second.actors.back();
   if(!a.released){if(!mProvider->release(a.pointer,a.token,e))return false;a.released=true;}
   if(a.registryBound){if(!mActors.retire(a.pointer,a.handle))return fail(e,"original actor association retirement failed");a.registryBound=false;}
   group->second.actors.pop_back();
  }
  if(!mActors.retireGenerator(group->first,group->second.handle))return fail(e,"original generator retirement failed");
  group=mGroups.erase(group);
 }
 mGroups.clear();mProvider=nullptr;e.clear();return true;
}
bool GroupCourse::decodeFrontier(const std::string& campaign,const std::string& bytes,std::string& e){
 if(mProvider||!mGroups.empty()||mCleaning)return fail(e,"original incarnation adoption requires unloaded scene");
 return mFrontier.decode(campaign,bytes,e);
}
}
