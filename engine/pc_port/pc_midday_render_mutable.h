#pragma once
#include "pc_midday_render_descriptors.h"
#include "pc_midday_resolved_fields.h"
namespace pc_midday {
struct PlannedRenderState {u64 id=0;u32 slot=0;RenderKind kind=RenderKind::Materials;ActorFields fields;ResolvedFields pointers;};
using RenderGeometryCheck=std::function<bool(const RenderNode&,u32,const ActorFields&,std::string&)>;
using RenderOwnedAddresses=std::function<bool(u64,u32,std::map<std::string,const void*>&,std::string&)>;
// Pure plan: all payloads and pointer caches complete before any native Apply.
// Production binder below supplies actual installed geometry and owned addresses.
bool planRenderMutable(const RenderGraph&,const RenderGeometryCheck&,const RenderResolverFactory&,
 const RenderOwnedAddresses&,std::vector<PlannedRenderState>&,std::string&);
bool bindRenderMutable(const RenderGraph&,IsolatedRenderAllocations&,const RenderDescriptorIndex&,
 const RenderResolverFactory&,ConstructorFence&,std::string&);
}
