#pragma once
#include "pc_p2_original_spawn_plan.h"
#include <cstdint>
#include <functional>
#include <map>
#include <set>
#include <tuple>
namespace p2original {
struct CatalogRow {std::string course,member,sourceKey;unsigned index=0; EnemyRecord enemy;};
unsigned originalGeneratorUid(const std::string& sourceKey);
struct InstanceIdentity {
 std::string catalog; unsigned generator=0,ordinal=0; std::uint64_t epoch=0;
 bool operator==(const InstanceIdentity& b)const{return catalog==b.catalog&&generator==b.generator&&ordinal==b.ordinal&&epoch==b.epoch;}
 bool operator<(const InstanceIdentity& b)const{return std::tie(catalog,generator,ordinal,epoch)<std::tie(b.catalog,b.generator,b.ordinal,b.epoch);}
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
 bool bindGenerator(const void* generator,unsigned uid,std::uint64_t& handle,std::string&);
 bool generatorUid(const void* generator,std::uint64_t handle,unsigned& uid)const;
 bool forgetGenerator(const void* generator,std::uint64_t handle);
 bool bind(const void* actor,unsigned uid,unsigned ordinal,std::uint64_t epoch,std::uint64_t& handle,std::string&);
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
