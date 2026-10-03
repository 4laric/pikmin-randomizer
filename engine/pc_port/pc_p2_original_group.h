#pragma once
#include "pc_p2_original_actor.h"
#include "pc_p2_original_lifecycle.h"
namespace p2original {
struct GroupBinding { Generator* generator=nullptr; GeneratorState state; };
// This interface is implemented by admitted physical families. preflight and
// reserve cover the WHOLE original catalog before any placement draw or birth.
// Saved-creature records have a separate typed loader; absence is a refusal.
class GroupProvider {
public:
 virtual ~GroupProvider()=default;
 virtual bool preflight(const std::vector<CatalogRow>&,std::string&)=0;
 virtual bool reserve(const std::vector<CatalogRow>&,std::string&)=0;
 virtual bool birth(const CatalogRow&,Generator*,unsigned,const Position&,float,Creature*&,std::string&)=0;
 virtual bool bind(const CatalogRow&,Creature*,unsigned,std::string&)=0;
 // Release the actual family, including corpse/listener ownership, before
 // registry retirement. False retains the association for explicit recovery.
 virtual bool release(Creature*,unsigned,std::string&)=0;
};
class GroupCourse {
public:
 explicit GroupCourse(ActorRegistry& actors):mActors(actors){}
 GroupCourse(const GroupCourse&)=delete;
 GroupCourse& operator=(const GroupCourse&)=delete;
 // The caller owns provider/resource lifetime until unload succeeds. All
 // bindings must be actual source generators, not surrogate host/AP slots.
 bool install(const std::vector<GroupBinding>&,GroupProvider&,std::string&);
 bool owns(const Generator*)const;
 bool initialize(Generator*,unsigned day,bool disc,const Math&,const std::function<bool(const Position&,float&,std::string&)>& floor,std::string&);
 bool death(Generator*,Creature*,std::string&);
 // Called after actual native family forget, before pool-address reuse.
 bool retiredNative(Creature*,std::string&);
 bool cache(const Generator*,const std::string& fingerprint,std::string& bytes,std::string&)const;
 bool restoreState(Generator*,const std::string& fingerprint,const std::string& bytes,std::string&);
 bool state(const Generator*,GeneratorState&,unsigned& alive)const;
 bool unload(std::string&);
private:
 struct Actor {Creature* pointer=nullptr;unsigned token=0;std::uint64_t handle=0;bool dead=false,released=false,registryBound=false;};
 struct Group {GeneratorState state;std::uint64_t handle=0;bool initialized=false,started=false;std::vector<Actor> actors;};
 ActorRegistry& mActors;GroupProvider* mProvider=nullptr;bool mCleaning=false;std::map<Generator*,Group> mGroups;
};
}
