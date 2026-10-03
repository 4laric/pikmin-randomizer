#include "pc_midday_render_graph.h"
#include "pc_midday_world_resources.h"
#include "Material.h"
#include <algorithm>
#include <exception>
#include <new>
namespace pc_midday {
namespace {
size_t nativeSize(RenderKind kind){switch(kind){case RenderKind::Materials:return sizeof(Material);case RenderKind::Tev:return sizeof(PVWTevInfo);case RenderKind::Textures:return sizeof(PVWTextureData);}return 0;}
bool visit(RenderKind kind,void* p,ActorArchive& ar){switch(kind){case RenderKind::Materials:return world_material_fields(*static_cast<Material*>(p),ar);case RenderKind::Tev:return world_tev_fields(*static_cast<PVWTevInfo*>(p),ar);case RenderKind::Textures:return world_texture_data_fields(*static_cast<PVWTextureData*>(p),ar);}return false;}
bool schema(RenderKind kind,const ActorFields& fields,std::vector<FieldSchema>& out,std::string& e){switch(kind){case RenderKind::Materials:return world_material_schema(fields,"",out,e);case RenderKind::Tev:return world_tev_schema(fields,"",out,e);case RenderKind::Textures:return world_texture_data_schema(fields,"",out,e);}return false;}
}
bool captureRenderGraph(u64 generation,const std::vector<RenderObservation>& source,const std::set<u64>& required,const RenderResolverFactory& factory,RenderGraph& out,std::string& e){
 if(!factory){e="render resource resolver unavailable";return false;}
 if(!validateRenderInventory(generation,source,required,e))return false;
 // Validate ranges before dereferencing native observations. Links are observed
 // below; the complete plan is validated before any payload capture is exposed.
 std::map<const void*,const RenderObservation*> addresses;
 for(const auto& node:source){if(node.elementSize!=nativeSize(node.kind)||!node.address||!node.count||node.count>256||!addresses.emplace(reinterpret_cast<const void*>(node.address),&node).second){e="native render factory layout invalid";return false;}}
 std::map<const PVWTevInfo*,std::pair<const RenderObservation*,u32>> tevElements;
 for(const auto& node:source)if(node.kind==RenderKind::Tev)for(u32 slot=0;slot<node.count;++slot)tevElements.emplace(reinterpret_cast<const PVWTevInfo*>(node.address+slot*node.elementSize),std::make_pair(&node,slot));
 std::vector<RenderLink> links;
 for(const auto& node:source)if(node.kind==RenderKind::Materials){auto* materials=reinterpret_cast<Material*>(node.address);
  for(u32 i=0;i<node.count;++i){auto& m=materials[i];RenderLink link;link.materials=node.id;link.slot=i;link.pvw=(m.mFlags&MATFLAG_PVW)!=0;
   if(link.pvw){auto tev=tevElements.find(m.mTevInfo);if(tev==tevElements.end()){e="native material has untracked TEV alias";return false;}link.tev=tev->second.first->id;link.tevSlot=tev->second.second;link.textureCount=m.mTextureInfo.mTextureDataCount;
    // Zero count must not read an indeterminate pointer from original asset read.
    if(link.textureCount){auto tex=addresses.find(m.mTextureInfo.mTextureData);if(tex==addresses.end()||tex->second->kind!=RenderKind::Textures){e="native material has untracked texture alias";return false;}link.textures=tex->second->id;}
   }links.push_back(link);
  }
 }
 RenderGraph next;if(!planRenderGraph(generation,source,links,required,next,e))return false;
 for(size_t n=0;n<source.size();++n){const auto& node=source[n];auto& saved=next.nodes[n];saved.payloads.reserve(node.count);
  for(u32 slot=0;slot<node.count;++slot){auto* resolver=factory(node.id,slot);if(!resolver){e="render allocation lacks typed scene resolver";return false;}
   ActorFields fields;FieldArchive ar(Mode::Capture,fields,*resolver,e,0);
   if(!visit(node.kind,reinterpret_cast<void*>(node.address+slot*node.elementSize),ar)||!ar.finish())return false;
   if(node.kind==RenderKind::Materials){
    auto link=std::find_if(links.begin(),links.end(),[&](const RenderLink& x){return x.materials==node.id&&x.slot==slot;});
    if(link==links.end()){e="native material link disappeared";return false;}
    if(link->pvw){auto tev=fields.find("tev");if(tev==fields.end()||tev->second.target.owner||tev->second.target.resource!=link->tev||tev->second.target.slot!=link->tevSlot){e="logical TEV alias disagrees with native canonical inventory";return false;}
     for(u32 i=0;i<link->textureCount;++i){auto tex=fields.find("texture."+std::to_string(i));if(tex==fields.end()||tex->second.target.owner||tex->second.target.resource!=link->textures||tex->second.target.slot!=i){e="logical texture alias disagrees with native canonical inventory";return false;}}
    }
   }
   std::vector<FieldSchema> descriptors;ActorBytes payload;
   if(!schema(node.kind,fields,descriptors,e)||!validate_actor_fields(fields,descriptors,*resolver,e)||!encode_actor_fields(fields,payload,e))return false;
   saved.payloads.push_back(std::move(payload));
  }
 }
 out=std::move(next);e.clear();return true;
}
struct IsolatedRenderAllocations::Impl {
 ConstructorFence* fence=nullptr;
 RenderGraph layout;
 std::map<u64,std::unique_ptr<Material[]>> materials;
 std::map<u64,std::unique_ptr<PVWTevInfo[]>> tevs;
 std::map<u64,std::unique_ptr<PVWTextureData[]>> textures;
 ~Impl(){if(!materials.empty()||!tevs.empty()||!textures.empty()){std::string e;if(!fence||!fence->held()||!pc_sim_rng_constructor_suppression(true,e))std::terminate();}}
};
IsolatedRenderAllocations::IsolatedRenderAllocations()=default;
IsolatedRenderAllocations::~IsolatedRenderAllocations()=default;
bool IsolatedRenderAllocations::heldBy(const ConstructorFence& f)const{return impl_&&impl_->fence==&f&&f.held();}
bool IsolatedRenderAllocations::matchesLayout(const RenderGraph& graph)const{
 if(!impl_||impl_->layout.generation!=graph.generation||impl_->layout.nodes.size()!=graph.nodes.size()||impl_->layout.links.size()!=graph.links.size())return false;
 for(size_t i=0;i<graph.nodes.size();++i){const auto& a=impl_->layout.nodes[i];const auto& b=graph.nodes[i];if(a.id!=b.id||a.factory!=b.factory||a.kind!=b.kind||a.count!=b.count||a.contentRoot!=b.contentRoot)return false;}
 for(size_t i=0;i<graph.links.size();++i){const auto& a=impl_->layout.links[i];const auto& b=graph.links[i];if(a.materials!=b.materials||a.slot!=b.slot||a.pvw!=b.pvw||a.tev!=b.tev||a.textures!=b.textures||a.textureCount!=b.textureCount||a.tevSlot!=b.tevSlot)return false;}
 return true;
}
void* IsolatedRenderAllocations::allocation(u64 id)const{if(!impl_)return nullptr;auto m=impl_->materials.find(id);if(m!=impl_->materials.end())return m->second.get();auto t=impl_->tevs.find(id);if(t!=impl_->tevs.end())return t->second.get();auto x=impl_->textures.find(id);return x==impl_->textures.end()?nullptr:x->second.get();}
bool IsolatedRenderAllocations::prepare(const RenderGraph& graph,const RestoreGate& gate,ConstructorFence& fence,std::string& e,size_t failAt){
 if(impl_||!fence.held()||!pc_sim_rng_constructor_suppression(true,e)){if(e.empty())e="render allocation requires fresh owner and exact physical fence";return false;}
 if(!gate.freshProcess||!gate.paused||!gate.zeroInput||!gate.birthEffectsSuppressed||!gate.rewardsSuppressed||!gate.rngDrawsSuppressed||!gate.audioVoicesSuppressed){e="render allocation requires all paused restore gates";return false;}
 if(graph.nodes.size()>4096){e="render allocation inventory exceeds bound";return false;}
 // Revalidate ID/topology independently, without treating saved addresses as wire data.
 std::vector<RenderObservation> layout;std::set<u64> ids;uintptr_t address=1;
 for(const auto& node:graph.nodes){auto size=nativeSize(node.kind);layout.push_back({node.id,node.factory,node.kind,node.count,address,size,node.contentRoot});address+=size*node.count;ids.insert(node.id);if(node.payloads.size()!=node.count){e="render payload coverage incomplete";return false;}}
 RenderGraph plan;if(!planRenderGraph(graph.generation,layout,graph.links,ids,plan,e))return false;
 try{size_t attempts=0;auto point=[&]{if(++attempts==failAt)throw std::bad_alloc();};point();auto staged=std::make_unique<Impl>();staged->fence=&fence;staged->layout=std::move(plan);
  for(const auto& node:graph.nodes){point();switch(node.kind){case RenderKind::Materials:staged->materials.emplace(node.id,std::make_unique<Material[]>(node.count));break;case RenderKind::Tev:staged->tevs.emplace(node.id,std::make_unique<PVWTevInfo[]>(node.count));break;case RenderKind::Textures:staged->textures.emplace(node.id,std::make_unique<PVWTextureData[]>(node.count));break;}}
  impl_=std::move(staged);e.clear();return true;
 }catch(const std::exception& x){e=std::string("render allocation failed: ")+x.what();return false;}
}
}
