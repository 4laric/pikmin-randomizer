#pragma once
#include "pc_midday_actor_archive.h"
#include "pc_midday_constructor.h"
#include "pc_midday_restore.h"
#include <functional>
#include <memory>
namespace pc_midday {
enum class RenderKind : u8 { Materials=1, Tev, Textures };
// Addresses are transient source observations, never part of a checkpoint.
struct RenderObservation {
 u64 id=0, factory=0;
 RenderKind kind=RenderKind::Materials;
 u32 count=0;
 uintptr_t address=0;
 size_t elementSize=0;
 // Only source-registered full prototype allocations may be capture roots.
 bool contentRoot=false;
};
struct RenderLink { u64 materials=0;u32 slot=0;bool pvw=false;u64 tev=0,textures=0;u32 textureCount=0;u32 tevSlot=0; };
struct RenderNode {
 u64 id=0,factory=0;RenderKind kind=RenderKind::Materials;u32 count=0;
 std::vector<ActorBytes> payloads;
 bool contentRoot=false;
};
struct RenderGraph {u64 generation=0;std::vector<RenderNode> nodes;std::vector<RenderLink> links;};
bool validateRenderInventory(u64,const std::vector<RenderObservation>&,const std::set<u64>&,std::string&);
// required is supplied by the complete scene factory inventory. No inferred
// completeness, interior-array identity, duplicate aliases or unregistered unreachable nodes.
bool planRenderGraph(u64 generation,const std::vector<RenderObservation>&,
 const std::vector<RenderLink>&,const std::set<u64>& required,RenderGraph&,std::string&);
using RenderResolverFactory=std::function<LogicalResolver*(u64,u32)>;
// Actual native layouts and relationships are observed without writes. The caller
// must hold the stopped initialized scene fence for this entire operation.
bool captureRenderGraph(u64 generation,const std::vector<RenderObservation>&,
 const std::set<u64>& required,const RenderResolverFactory&,RenderGraph&,std::string&);
class IsolatedRenderAllocations {
 struct Impl;std::unique_ptr<Impl> impl_;
 bool backingReady_=false,mutableReady_=false,mutableAttempted_=false;
 friend class RenderDescriptorIndex;
 friend struct RenderBindAccess;
public:
 IsolatedRenderAllocations();~IsolatedRenderAllocations();
 bool prepare(const RenderGraph&,const RestoreGate&,ConstructorFence&,std::string&,size_t failAt=0);
 void* allocation(u64)const;
 bool heldBy(const ConstructorFence&)const;
 bool matchesLayout(const RenderGraph&)const;
 bool backingReady()const{return impl_&&backingReady_;}
 bool mutableReady()const{return impl_&&mutableReady_;}
 // Allocation only: default objects are NOT ready for consumers. Restore still
 // needs installed immutable descriptor setup and complete typed payload bind.
 // Retain this owner and the exact physical fence through abort/destruction.
};
}
