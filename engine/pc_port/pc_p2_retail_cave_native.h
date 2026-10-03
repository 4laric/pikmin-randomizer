#pragma once
#include "pc_p2_retail_cave_plan.h"
#include "pc_p2_original_actor.h"
#include <memory>
class Creature;class Generator;struct Vector3f;
namespace p2retail {
struct FamilyOps {
 // Each leaf verifies real resources and whole-family actor/corpse capacity.
 std::function<bool(const std::vector<p2original::CatalogRow>&,std::string&)> prepare;
 std::function<bool(const p2original::CatalogRow&,const Snapshot&,Generator*,unsigned,const Vector3f&,float,Creature*&,bool& suppressed,std::string&)> birth;
 std::function<bool(const p2original::CatalogRow&,Creature*,unsigned,std::string&)> bind;
 std::function<bool(Creature*,unsigned,std::string&)> release;
 std::function<bool(std::string&)> cancel;
 // After registry retirement, before native manager address reuse.
 std::function<bool(Creature*,std::string&)> retired;
 bool retireBeforeRelease=false;
};
// Geometry/stage, Pod/exit and cargo ownership remain with their actual native
// owners. No default/preview implementations exist for any of these callbacks.
class SceneOps {
public:
 virtual ~SceneOps()=default;
 // Actual selected session/revision + installed stage/native serial; no allocation.
 virtual bool owns(const SceneIdentity&)const noexcept=0;
 virtual bool mode(const SceneIdentity&,bool& story,bool& inCave,std::string&)const=0;
 virtual bool preflight(const FloorPlan&,const Snapshot&,std::string&)=0;
 virtual bool begin(const FloorPlan&,const Snapshot&,std::string&)=0;
 // Verify selected live/terminal disposition before any native enemy allocation.
 virtual bool prior(const ContentRow&,const BirthIdentity&,const Snapshot&,LiveBinding&,bool& absent,std::string&)=0;
 virtual bool cargo(const Placement&,const ContentRow&,const BirthIdentity&,const Snapshot&,LiveBinding&,std::string&)=0;
 // Called only after the real leaf returns its population-gated null birth.
 virtual bool suppressed(const ContentRow&,const BirthIdentity&,const Snapshot&,LiveBinding&,std::string&)=0;
 virtual bool absent(const ContentRow&,const BirthIdentity&,const Snapshot&,const LiveBinding&)const=0;
 virtual bool commit(const Snapshot&,std::string&)=0;
 virtual bool canRelease(std::string&)const=0;
 virtual bool release(std::string&)=0;
 virtual bool retired(const BirthIdentity&,const Snapshot&,std::string&)=0;
};
enum class FloorPhase {Empty,Preparing,Installing,Committed,Releasing};
class NativeFloor final:public FloorProvider {
public:
 NativeFloor(FloorPlan,SceneOps&);~NativeFloor();
 NativeFloor(const NativeFloor&)=delete;NativeFloor&operator=(const NativeFloor&)=delete;
 bool family(unsigned source,FamilyOps,std::string&);
 bool familyGroup(const std::vector<unsigned>& sources,FamilyOps,std::string&);
 bool preflight(const CaveDescriptor&,const FloorDefinition&,unsigned,const SceneIdentity&,std::string&)override;
 bool install(const CaveDescriptor&,const FloorDefinition&,unsigned,const SceneIdentity&,
              const std::vector<BirthIdentity>&,std::vector<LiveBinding>&,std::string&)override;
 bool verifyAbsent(const CaveDescriptor&,unsigned,const ContentRow&,const SceneIdentity&,
                   const BirthIdentity&,const LiveBinding&)const override;
 bool commit(const Snapshot&,std::string&)override;
 // Trusted installation lookup for cargo/Pod adapters; raw plan remains rechecked.
 // Read-only actual installed census; revokes before any release/teardown.
 FloorPhase phase()const noexcept;
 bool bindingFacts(Snapshot&,std::uint64_t& floorEpoch,FloorPhase&,std::string&)const;
 bool bindingCurrent(const SceneIdentity&,std::uint64_t floorEpoch)const noexcept;
 bool installed(Snapshot&,std::uint64_t& floorEpoch,std::string&)const;
 bool current(const SceneIdentity&,std::uint64_t floorEpoch)const noexcept;
 bool boundSourceBirth(const Creature*,unsigned token,const p2original::InstanceIdentity&,
                       BirthIdentity&,Snapshot&,FloorPhase&,std::string&)const;
 bool expectedSourceBirth(const Creature*,unsigned token,const p2original::InstanceIdentity&,
                          BirthIdentity&,Snapshot&,std::string&)const;
 // Retained actual parent incarnation after natural death, never an output receipt.
 bool knownSourceBirth(const p2original::InstanceIdentity&,BirthIdentity&,Snapshot&,std::string&)const;
 bool placement(const SceneIdentity&,unsigned row,unsigned ordinal,Placement&,std::string&)const;
 bool canRelease(std::string&)const override;
 bool release(std::string&)override;
 // Actual native forget event, before manager address reuse; not a death poll.
 bool retired(Creature*,std::string&);
private:struct Impl;std::unique_ptr<Impl> m;
};
} // namespace p2retail
bool pc_p2_retail_cave_native_retired(Creature*,std::string&);
