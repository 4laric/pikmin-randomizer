#include "pc_midday_render_graph.h"
#include <limits>
namespace pc_midday {
bool validateRenderInventory(u64 generation,const std::vector<RenderObservation>& source,const std::set<u64>& required,std::string& e){
 if(!generation||source.size()>4096||required.size()>4096||required.count(0)){e="render graph generation/inventory invalid";return false;}
 std::map<u64,const RenderObservation*> ids;
 std::map<uintptr_t,uintptr_t> ranges;
 for(const auto& node:source){
  if(!node.id||!node.factory||!required.count(node.id)||!ids.emplace(node.id,&node).second||!node.count||node.count>256||!node.address||!node.elementSize){e="render allocation identity/count invalid";return false;}
  if(node.kind!=RenderKind::Materials&&node.kind!=RenderKind::Tev&&node.kind!=RenderKind::Textures){e="unknown render allocation kind";return false;}
  if(node.contentRoot&&node.kind!=RenderKind::Tev){e="only full prototype TEV arrays may be additional capture roots";return false;}
  if(node.count>std::numeric_limits<size_t>::max()/node.elementSize){e="render allocation span overflow";return false;}
  size_t bytes=node.count*node.elementSize;
  if(bytes>std::numeric_limits<uintptr_t>::max()-node.address){e="render allocation address overflow";return false;}
  uintptr_t end=node.address+bytes;auto upper=ranges.lower_bound(node.address);
  if((upper!=ranges.end()&&upper->first<end)||(upper!=ranges.begin()&&std::prev(upper)->second>node.address)){e="render canonical allocations overlap";return false;}
  ranges.emplace(node.address,end);
 }
 if(ids.size()!=required.size()){e="render allocation inventory incomplete";return false;}
 e.clear();return true;
}
bool planRenderGraph(u64 generation,const std::vector<RenderObservation>& source,const std::vector<RenderLink>& links,const std::set<u64>& required,RenderGraph& out,std::string& e){
 if(!validateRenderInventory(generation,source,required,e))return false;
 std::map<u64,const RenderObservation*> ids;RenderGraph next;next.generation=generation;size_t materialSlots=0;
 for(const auto& node:source){ids.emplace(node.id,&node);next.nodes.push_back({node.id,node.factory,node.kind,node.count,{},node.contentRoot});if(node.kind==RenderKind::Materials)materialSlots+=node.count;}
 if(links.size()!=materialSlots){e="render material inventory incomplete";return false;}
 std::set<std::pair<u64,u32>> slots;std::set<u64> reached;
 for(const auto& link:links){
  auto m=ids.find(link.materials);
  if(m==ids.end()||m->second->kind!=RenderKind::Materials||link.slot>=m->second->count||!slots.emplace(link.materials,link.slot).second){e="render material link foreign/duplicated";return false;}
  if(!link.pvw){if(link.tev||link.textures||link.textureCount||link.tevSlot){e="non-PVW material exposes uninitialized PVW storage";return false;}}
  else{
   auto tev=ids.find(link.tev);
   if(tev==ids.end()||tev->second->kind!=RenderKind::Tev||link.tevSlot>=tev->second->count){e="render material TEV allocation missing";return false;}
   reached.insert(link.tev);
   if(!link.textureCount){if(link.textures){e="empty texture array has an identity";return false;}}
   else{auto tex=ids.find(link.textures);if(tex==ids.end()||tex->second->kind!=RenderKind::Textures||tex->second->count!=link.textureCount){e="render texture allocation/count mismatch";return false;}reached.insert(link.textures);}
  }
 }
 for(const auto& node:source)if(node.kind!=RenderKind::Materials&&!node.contentRoot&&!reached.count(node.id)){e="unreachable mutable render allocation";return false;}
 next.links=links;out=std::move(next);e.clear();return true;
}
}
