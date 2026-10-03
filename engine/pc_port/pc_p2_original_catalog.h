#pragma once
#include "pc_p2_original_spawn_plan.h"
#include <cstdint>
#include <functional>
#include <map>
#include <set>
#include <tuple>
namespace p2original {
enum class SourceForm { SurfaceGenEnemy, CaveTekiInfo };
struct CatalogRow {
 std::string course,member,sourceKey;unsigned index=0; EnemyRecord enemy;
 SourceForm sourceForm=SourceForm::SurfaceGenEnemy;
 unsigned caveFloor=0,caveRow=0;std::string caveSourceSha256;
};
unsigned originalGeneratorUid(const std::string& sourceKey);
struct InstanceIdentity {
 std::string catalog; unsigned generator=0,ordinal=0; std::uint64_t epoch=0,activation=1;
 bool operator==(const InstanceIdentity& b)const{return catalog==b.catalog&&generator==b.generator&&ordinal==b.ordinal&&epoch==b.epoch&&activation==b.activation;}
 bool operator<(const InstanceIdentity& b)const{return std::tie(catalog,generator,ordinal,epoch,activation)<std::tie(b.catalog,b.generator,b.ordinal,b.epoch,b.activation);}
};
// Logical IDs never contain addresses. Native pointers below are transient
// associations only. Cache serialization and original provider dispatch are
// separate integration responsibilities.
class Catalog {
public:
 Catalog()=default;
 Catalog(const Catalog&)=delete;
 Catalog&operator=(const Catalog&)=delete;
 // Epoch persistence/respawn authorization belongs to the native cache adapter.
 // This component only prevents identity reuse within this owning session.
 using Capability=std::function<bool(const CatalogRow&,std::string&)>;
 bool install(const std::string& fingerprint,const std::vector<CatalogRow>&,const Capability&,std::string&);
 const CatalogRow* find(unsigned uid)const;
 const std::string& fingerprint()const{return mFingerprint;}
 const std::map<unsigned,CatalogRow>& rows()const{return mRows;}
 bool bindGenerator(const void* generator,unsigned uid,std::uint64_t& handle,std::string&);
 bool generatorUid(const void* generator,std::uint64_t handle,unsigned& uid)const;
 bool forgetGenerator(const void* generator,std::uint64_t handle);
 bool bind(const void* actor,unsigned uid,unsigned ordinal,std::uint64_t epoch,std::uint64_t& handle,std::string&);
 // Normal RAM course entry regenerates remaining actors even without a
 // source respawn reset. Activation distinguishes those fresh incarnations.
 // A full fresh-process checkpoint restore uses its exact saved activation.
 bool bindActivation(const void* actor,unsigned uid,unsigned ordinal,std::uint64_t epoch,std::uint64_t activation,std::uint64_t& handle,std::string&);
 bool lookup(const void* actor,std::uint64_t handle,InstanceIdentity&)const;
 bool forget(const void* actor,std::uint64_t handle);
private:
 struct Binding {std::uint64_t handle;InstanceIdentity identity;};
 std::string mFingerprint;std::map<unsigned,CatalogRow> mRows;
 std::map<const void*,Binding> mActors;std::uint64_t mNextHandle=1;
 std::set<InstanceIdentity> mUsed;
 struct GeneratorBinding {unsigned uid;std::uint64_t handle;};
 std::map<const void*,GeneratorBinding> mGenerators;
};
}
