#include "pc_midday_render_prototypes.h"
#include "Shape.h"
#include "Material.h"
namespace pc_midday {
bool observePrototypeRender(u64 generation,const std::vector<PrototypeShapeBinding>& models,
 const ConstructorFence& fence,PrototypeRenderCensus& out,std::string& e){
 if(!generation||!fence.held()||models.size()>4096){e="prototype census requires bounded stopped source inventory and generation";return false;}
 PrototypeRenderCensus next;next.generation=generation;std::vector<RenderLink> links;
 struct Declaration {RenderKind kind;u64 factory;BaseShape* model;std::vector<u32> slots;bool full;};
 std::vector<Declaration> declarations;
 std::map<const void*,size_t,std::less<const void*>> addresses;
 std::set<u64> contentIds;std::set<const BaseShape*,std::less<const BaseShape*>> shapes;
 auto add=[&](u64 id,u64 factory,RenderKind kind,u32 count,const void* base,size_t size,bool root,bool& fresh){
  if(!id||!factory||!count||count>256||!base){e="prototype allocation binding missing/invalid";return false;}
  auto alias=addresses.find(base);
  if(alias!=addresses.end()){
   const auto& old=next.observations[alias->second];fresh=false;
   if(old.id!=id||old.factory!=factory||old.kind!=kind||old.count!=count||old.elementSize!=size||old.contentRoot!=root){e="prototype physical alias disagrees with canonical allocation binding";return false;}
   return true;
  }
  if(next.observations.size()>=4096||!next.required.insert(id).second){e="prototype identity duplicated or allocation bound exceeded";return false;}
  addresses.emplace(base,next.observations.size());
  next.observations.push_back({id,factory,kind,count,reinterpret_cast<uintptr_t>(base),size,root});fresh=true;return true;
 };
 for(const auto& binding:models){
  if(!binding.content||!binding.model||!contentIds.insert(binding.content).second||!shapes.insert(binding.model).second){e="loaded model content inventory is null/duplicated";return false;}
  auto& model=*binding.model;
  if(model.mMaterialCount<0||model.mMaterialCount>256||model.mTevInfoCount<0||model.mTevInfoCount>256||binding.textures.size()>256){e="loaded model original allocation geometry invalid";return false;}
  bool fresh=false;
  if(model.mTevInfoCount){
   if(!add(binding.tevs,binding.tevFactory,RenderKind::Tev,model.mTevInfoCount,model.mTevInfoList,sizeof(PVWTevInfo),true,fresh))return false;
   if(fresh)declarations.push_back({RenderKind::Tev,binding.tevFactory,&model,{},true});
  }else if(binding.tevs||binding.tevFactory){e="empty model TEV allocation has a fabricated identity";return false;}
  if(!model.mMaterialCount){if(binding.materials||binding.materialFactory||!binding.textures.empty()){e="empty model material inventory has fabricated allocations";return false;}continue;}
  if(!add(binding.materials,binding.materialFactory,RenderKind::Materials,model.mMaterialCount,model.mMaterialList,sizeof(Material),false,fresh))return false;
  bool materialFresh=fresh;
  // Check original root ranges before interpreting the material array.
  if(!validateRenderInventory(generation,next.observations,next.required,e))return false;
  if(fresh){std::vector<u32> slots;for(int i=0;i<model.mMaterialCount;++i)slots.push_back(i);declarations.push_back({RenderKind::Materials,binding.materialFactory,&model,std::move(slots),false});}
  std::map<u32,const PrototypeTextureBinding*> textures;
  for(const auto& texture:binding.textures)if(texture.materialSlot>=u32(model.mMaterialCount)||!textures.emplace(texture.materialSlot,&texture).second){e="prototype texture binding has foreign/duplicated material slot";return false;}
  for(int slot=0;slot<model.mMaterialCount;++slot){
   auto& material=model.mMaterialList[slot];RenderLink link;link.materials=binding.materials;link.slot=slot;link.pvw=(material.mFlags&MATFLAG_PVW)!=0;
   auto texture=textures.find(slot);
   if(link.pvw){
    if(!model.mTevInfoCount||material.mTevInfoIndex>=u32(model.mTevInfoCount)||material.mTevInfo!=&model.mTevInfoList[material.mTevInfoIndex]){e="prototype material TEV element is outside exact original model allocation";return false;}
    link.tev=binding.tevs;link.tevSlot=material.mTevInfoIndex;link.textureCount=material.mTextureInfo.mTextureDataCount;
    if(link.textureCount){
     if(texture==textures.end()){e="prototype nonempty texture allocation omitted from source binding";return false;}
     const auto& row=*texture->second;
     if(!add(row.id,row.factory,RenderKind::Textures,link.textureCount,material.mTextureInfo.mTextureData,sizeof(PVWTextureData),false,fresh))return false;
     if(fresh)declarations.push_back({RenderKind::Textures,row.factory,&model,{u32(slot)},false});
     link.textures=row.id;
    }else if(texture!=textures.end()){e="empty prototype texture allocation has fabricated identity";return false;}
   }else if(texture!=textures.end()){e="non-PVW prototype material has invalid texture binding";return false;}
   if(materialFresh)links.push_back(link);
  }
 }
 RenderGraph plan;
 // Validate every canonical extent/element link before reading TEV/texture
 // descriptor backing, including initialized entries without consumers.
 if(!planRenderGraph(generation,next.observations,links,next.required,plan,e))return false;
 for(const auto& row:declarations){
  if(row.full){if(!next.descriptors.declareTevArray(row.factory,*row.model,e))return false;}
  else if(!next.descriptors.declare(row.factory,row.kind,*row.model,row.slots,e))return false;
 }
 if(!next.descriptors.validate(plan,e))return false;
 out=std::move(next);e.clear();return true;
}
}
