#include "pc_midday_render_mutable.h"
#include "pc_midday_world_resources.h"
#include <algorithm>
namespace pc_midday {
bool planRenderMutable(const RenderGraph& graph,const RenderGeometryCheck& geometry,const RenderResolverFactory& factory,const RenderOwnedAddresses& owned,std::vector<PlannedRenderState>& out,std::string& e){
 if(!graph.generation||graph.nodes.size()>4096||!geometry||!factory||!owned){e="render mutable planner missing inventory/contracts";return false;}
 std::set<u64> ids;std::map<u64,const RenderNode*> nodes;size_t count=0,bytes=0,materialSlots=0;
 for(const auto& node:graph.nodes){if(!node.id||!node.factory||!ids.insert(node.id).second||!node.count||node.count>256||node.payloads.size()!=node.count||(node.kind!=RenderKind::Materials&&node.kind!=RenderKind::Tev&&node.kind!=RenderKind::Textures)||(node.contentRoot&&node.kind!=RenderKind::Tev)){e="render mutable payload census invalid";return false;}nodes.emplace(node.id,&node);count+=node.count;if(node.kind==RenderKind::Materials)materialSlots+=node.count;for(const auto& payload:node.payloads){if(payload.size()>MaxBytes-bytes){e="render mutable payload exceeds checkpoint byte bound";return false;}bytes+=payload.size();}}
 if(graph.links.size()!=materialSlots){e="mutable render material link census incomplete";return false;}
 std::set<std::pair<u64,u32>> linked;std::set<u64> reached;
 for(const auto& link:graph.links){auto m=nodes.find(link.materials);if(m==nodes.end()||m->second->kind!=RenderKind::Materials||link.slot>=m->second->count||!linked.emplace(link.materials,link.slot).second){e="mutable render link foreign/duplicated";return false;}
  if(!link.pvw){if(link.tev||link.textures||link.textureCount||link.tevSlot){e="non-PVW mutable link has aliases";return false;}continue;}
  auto tev=nodes.find(link.tev);if(tev==nodes.end()||tev->second->kind!=RenderKind::Tev||link.tevSlot>=tev->second->count){e="mutable TEV target absent";return false;}reached.insert(link.tev);
  if(!link.textureCount){if(link.textures){e="empty mutable texture alias has identity";return false;}}
  else{auto tex=nodes.find(link.textures);if(tex==nodes.end()||tex->second->kind!=RenderKind::Textures||tex->second->count!=link.textureCount){e="mutable texture target/count mismatch";return false;}reached.insert(link.textures);}
 }
 for(const auto& node:graph.nodes)if(node.kind!=RenderKind::Materials&&!node.contentRoot&&!reached.count(node.id)){e="mutable render allocation unreachable";return false;}
 std::vector<PlannedRenderState> plan;plan.reserve(count);
 for(const auto& node:graph.nodes)for(u32 slot=0;slot<node.count;++slot){PlannedRenderState next;next.id=node.id;next.slot=slot;next.kind=node.kind;
  if(!decode_actor_fields(node.payloads[slot],next.fields,e)||!geometry(node,slot,next.fields,e))return false;
  std::vector<FieldSchema> schema;
  switch(node.kind){case RenderKind::Materials:if(!world_material_schema(next.fields,"",schema,e))return false;break;case RenderKind::Tev:if(!world_tev_schema(next.fields,"",schema,e))return false;break;case RenderKind::Textures:if(!world_texture_data_schema(next.fields,"",schema,e))return false;break;default:e="unknown mutable render kind";return false;}
  if(node.kind==RenderKind::Materials){auto link=std::find_if(graph.links.begin(),graph.links.end(),[&](const RenderLink& x){return x.materials==node.id&&x.slot==slot;});u32 flags=0;if(link==graph.links.end()||!actor_u32(next.fields,"mFlags",flags,e)||link->pvw!=bool(flags&1)){e="mutable material canonical link mismatch";return false;}
   if(link->pvw){int textureCount=-1;if(!actor_i32(next.fields,"textureCount",textureCount,e)||textureCount!=int(link->textureCount)){e="mutable material texture count differs from canonical allocation";return false;}auto same=[&](const std::string& key,u64 resource,u32 index){auto f=next.fields.find(key);return f!=next.fields.end()&&!f->second.target.owner&&f->second.target.resource==resource&&f->second.target.slot==index;};if(!same("tev",link->tev,link->tevSlot)){e="mutable TEV canonical slot mismatch";return false;}for(u32 i=0;i<link->textureCount;++i)if(!same("texture."+std::to_string(i),link->textures,i)){e="mutable texture canonical slot mismatch";return false;}}
  }
  auto* resolver=factory(node.id,slot);std::map<std::string,const void*> expected;
  if(!resolver||!owned(node.id,slot,expected,e)){if(e.empty())e="mutable render resource catalog unavailable";return false;}
  if(!next.pointers.prepare(next.fields,schema,*resolver,expected,e))return false;
  plan.push_back(std::move(next));
 }
 out=std::move(plan);e.clear();return true;
}
}
