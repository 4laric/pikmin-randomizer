#include "pc_p2_material_binding.h"
#include "Shape.h"
#include "Graphics.h"
#include "Camera.h"
#include <optional>

namespace p2material {
namespace {
bool storage(Material& material){
 if(!(material.mFlags & MATFLAG_PVW))return false;
 const auto& info=material.mTextureInfo;
 return info.mTextureDataCount==1&&info.mTexGenDataCount==1&&info.mTextureData&&info.mTexGenData;
}
struct CacheScope {
 Graphics& gfx;
 explicit CacheScope(Graphics& g):gfx(g){gfx.useMaterial(nullptr);}
 ~CacheScope(){gfx.useMaterial(nullptr);}
};
}
void Binding::reset(){
 bank_=nullptr;shape_=nullptr;materials_=nullptr;materialCount_=0;generation_=0;entries_.clear();
}
bool Binding::bind(const Bank& bank,Shape& shape,const std::vector<Target>& targets,std::uint64_t generation){
 reset();
 if(!generation||!valid(bank)||targets.empty()||targets.size()>128||!shape.mMaterialList||shape.mMaterialCount<=0)return false;
 std::vector<Entry> candidate;
 std::set<unsigned> hosts;
 std::set<std::size_t> covered;
 std::set<const void*> textures,generators;
 for(const auto& target:targets){
  if(target.slot!=0||target.hostMaterial>=static_cast<unsigned>(shape.mMaterialCount)||!hosts.insert(target.hostMaterial).second)return false;
  std::size_t track=0;
  for(;track<bank.tracks.size();++track)if(bank.tracks[track].material==target.material&&bank.tracks[track].slot==target.slot)break;
  if(track==bank.tracks.size())return false;
  Material& material=shape.mMaterialList[target.hostMaterial];
  if(!storage(material))return false;
  auto& info=material.mTextureInfo;
  if(!textures.insert(info.mTextureData).second||!generators.insert(info.mTexGenData).second)return false;
  // Drawing the whole shape also visits unbound materials. Reject their aliases
  // so an unanimated material cannot acquire this target's transform indirectly.
  for(int other=0;other<shape.mMaterialCount;++other){
   if(static_cast<unsigned>(other)==target.hostMaterial)continue;
   auto& peer=shape.mMaterialList[other];if(!(peer.mFlags & MATFLAG_PVW))continue;
   if(peer.mTextureInfo.mTextureData==info.mTextureData||peer.mTextureInfo.mTexGenData==info.mTexGenData)return false;
  }
  // Validation scope is restored before returning; nothing is drawn here.
  Sample first;
  if(!sample(bank,track,0,first))return false;
  {ScopedSrt probe(material,first);if(!probe.applied())return false;}
  covered.insert(track);
  candidate.push_back({track,target.hostMaterial,info.mTextureData,info.mTexGenData});
 }
 if(covered.size()!=bank.tracks.size())return false;
 bank_=&bank;shape_=&shape;materials_=shape.mMaterialList;materialCount_=shape.mMaterialCount;
 generation_=generation;entries_=std::move(candidate);return true;
}
bool Binding::draw(const Bank& bank,Shape& shape,Graphics& gfx,double frame,std::uint64_t generation)const{
 // Identity checks precede all stored-pointer dereferences. A generation token
 // prevents recycled scene addresses from reviving an old binding.
 if(!ready()||bank_!=&bank||shape_!=&shape||generation_!=generation||!gfx.mCamera||
    materials_!=shape.mMaterialList||materialCount_!=shape.mMaterialCount)return false;
 std::array<Sample,128> samples;
 for(std::size_t i=0;i<entries_.size();++i){
  const auto& entry=entries_[i];Material& material=shape.mMaterialList[entry.host];
  if(!storage(material)||material.mTextureInfo.mTextureData!=entry.texture||material.mTextureInfo.mTexGenData!=entry.generator||
     !sample(bank,entry.track,frame,samples[i]))return false;
 }
 // All samples succeed before mutation. If a later scope refuses its target,
 // optional destruction restores every earlier target without drawing.
 std::array<std::optional<ScopedSrt>,128> scopes;
 for(std::size_t i=0;i<entries_.size();++i){
  scopes[i].emplace(shape.mMaterialList[entries_[i].host],samples[i]);
  if(!scopes[i]->applied())return false;
 }
 CacheScope cache(gfx);
 shape.drawshape(gfx,*gfx.mCamera,nullptr);
 return true;
}
}
