#include "pc_midday_render_mutable.h"
#include "pc_midday_world_resources.h"
#include "Material.h"
#include <algorithm>
namespace pc_midday {
struct RenderBindAccess {static bool attempted(const IsolatedRenderAllocations& owner){return owner.mutableAttempted_;}static void begin(IsolatedRenderAllocations& owner){owner.mutableAttempted_=true;}static void ready(IsolatedRenderAllocations& owner){owner.mutableReady_=true;}};
bool bindRenderMutable(const RenderGraph& graph,IsolatedRenderAllocations& owner,const RenderDescriptorIndex& index,const RenderResolverFactory& factory,ConstructorFence& fence,std::string& e){
 if(!owner.heldBy(fence)||!owner.matchesLayout(graph)||!owner.backingReady()||owner.mutableReady()||RenderBindAccess::attempted(owner)){e="mutable render binding requires unbound initialized owned backing/layout/fence";return false;}
 if(!index.matchesInitializedBacking(graph,owner,fence,e))return false;
 if(!pc_sim_rng_constructor_suppression(true,e))return false;
 auto geometry=[&](const RenderNode& node,u32 slot,const ActorFields& fields,std::string& error){return index.validateStateGeometry(node,slot,fields,error);};
 auto addresses=[&](u64 id,u32 slot,std::map<std::string,const void*>& out,std::string& error){
  auto node=std::find_if(graph.nodes.begin(),graph.nodes.end(),[&](const RenderNode& x){return x.id==id;});if(node==graph.nodes.end()){error="mutable render allocation missing";return false;}
  if(node->kind!=RenderKind::Materials)return true;
  auto link=std::find_if(graph.links.begin(),graph.links.end(),[&](const RenderLink& x){return x.materials==id&&x.slot==slot;});if(link==graph.links.end()){error="mutable material source link missing";return false;}
  if(link->pvw){out.emplace("tev",&static_cast<PVWTevInfo*>(owner.allocation(link->tev))[link->tevSlot]);auto* textures=static_cast<PVWTextureData*>(owner.allocation(link->textures));for(u32 i=0;i<link->textureCount;++i)out.emplace("texture."+std::to_string(i),&textures[i]);}
  return true;
 };
 std::vector<PlannedRenderState> plan;if(!planRenderMutable(graph,geometry,factory,addresses,plan,e))return false;
 // Every immutable geometry constraint and pointer cache is prepared first.
 // Any Apply failure invalidates the entire unpublished owner transaction.
 RenderBindAccess::begin(owner);
 for(auto& record:plan){FieldArchive ar(Mode::Apply,record.fields,record.pointers,e,0);bool ok=false;
  switch(record.kind){case RenderKind::Materials:ok=world_material_fields(static_cast<Material*>(owner.allocation(record.id))[record.slot],ar);break;case RenderKind::Tev:ok=world_tev_fields(static_cast<PVWTevInfo*>(owner.allocation(record.id))[record.slot],ar);break;case RenderKind::Textures:ok=world_texture_data_fields(static_cast<PVWTextureData*>(owner.allocation(record.id))[record.slot],ar);break;}
  if(!ok||!ar.finish())return false;
 }
 RenderBindAccess::ready(owner);e.clear();return true;
}
}
