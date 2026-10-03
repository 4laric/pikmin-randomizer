#pragma once
// #1274. Retail definition provenance is immutable. A descriptor alone grants
// no runtime authority: only a fully installed physical floor can bind a scene.
#include <cstdint>
#include <functional>
#include <set>
#include <string>
#include <vector>

namespace p2retail {
struct ContentRow {
 std::string kind,catalogId,sourceToken,heldTreasure;
 unsigned index; int sourceId; unsigned dropMode,placementType,sourceWeight; bool boss;
 unsigned minimum()const{return placementType==6?sourceWeight:sourceWeight/10;}
 unsigned weight()const{return placementType==6?0:sourceWeight%10;}
};
struct FloorDefinition {
 unsigned index,first,last; std::string unitPool; unsigned gates,caps;
 std::vector<ContentRow> rows;
};
struct CaveDescriptor {
 std::string cave,source,sourceSha256,catalogSha256; unsigned maxFloor;
 std::vector<FloorDefinition> definitions;
};
#include "pc_p2_retail_cave_catalog.inc"

inline const CaveDescriptor* descriptor(const std::string& cave){
 for(const auto& row:retailCatalog())if(row.cave==cave)return &row;
 return nullptr; // including engineeredforest_1 and every engineering alias
}
inline const FloorDefinition* definition(const CaveDescriptor& cave,unsigned floor){
 if(!floor||floor>cave.maxFloor)return nullptr;
 for(const auto& row:cave.definitions)if(floor>=row.first&&floor<=row.last)return &row;
 return nullptr;
}
struct SceneIdentity {
 std::string seed,visit,layoutSha256; std::uint64_t serial=0;
 bool operator==(const SceneIdentity& b)const{return seed==b.seed&&visit==b.visit&&layoutSha256==b.layoutSha256&&serial==b.serial;}
};
struct Snapshot {
 std::string cave,source,sourceSha256,catalogSha256;unsigned floor=0,maxFloor=0;
 SceneIdentity scene;bool story=false,inCave=false;
 bool lastFloor()const{return inCave&&floor!=0&&floor==maxFloor;}
};
struct BirthIdentity {
 // Definition/ordinal identify original source content, never a catalog item
 // used as a generic receipt key. Epoch persists via the owning SAVE consumer.
 unsigned row=0,ordinal=0;std::uint64_t epoch=0;
 std::string instance;
 std::uint64_t activation=0;
 bool operator==(const BirthIdentity& b)const{return row==b.row&&ordinal==b.ordinal&&epoch==b.epoch&&instance==b.instance&&activation==b.activation;}
};
class FloorIdentityAuthority {
public:
 virtual ~FloorIdentityAuthority()=default;
 // Issued by the selected native floor/restore owner, independently of each
 // provider's birth output or receipt. It must verify selected session seed.
 virtual bool expectedBirth(const CaveDescriptor&,unsigned,const SceneIdentity&,
                            unsigned row,unsigned ordinal,BirthIdentity&,std::string&)const=0;
};
enum class BindingState { Live, ConsumedTreasure, RetiredNative, SourceSuppressed };
struct LiveBinding {
 const void* actor=nullptr; BirthIdentity identity;
 BindingState state=BindingState::Live;std::string receipt;
};
// Actual native providers own resources/lifetime. No provider is registered by
// default. Preflight covers all rows, gates/caps, exits, pod, geometry and slots.
class FloorProvider {
public:
 virtual ~FloorProvider()=default;
 virtual bool preflight(const CaveDescriptor&,const FloorDefinition&,unsigned,
                        const SceneIdentity&,std::string&)=0;
 virtual bool install(const CaveDescriptor&,const FloorDefinition&,unsigned,
                      const SceneIdentity&,const std::vector<BirthIdentity>&,
                      std::vector<LiveBinding>&,std::string&)=0;
 // Must release even a partial install; false retains the session for recovery.
 virtual bool release(std::string&)=0;
 // True only for the actual native release event emitted by this owning floor.
 // A caller-supplied nonzero integer is never sufficient boss-drop authority.
 virtual bool verifyHeldRelease(const void*,const BirthIdentity&,const std::string&,
                                std::uint64_t)const{return false;}
 // SAVE-owned canonical receipts/cache prove why an expected source instance
 // is absent on resume. A consumed treasure is never reborn or counted as live.
 virtual bool verifyAbsent(const CaveDescriptor&,unsigned,const ContentRow&,
                           const SceneIdentity&,const BirthIdentity& expected,
                           const LiveBinding&)const{(void)expected;return false;}
};
inline bool hex64(const std::string& s){
 if(s.size()!=64)return false;
 for(char ch:s)if(!((ch>='0'&&ch<='9')||(ch>='a'&&ch<='f')))return false;
 return true;
}
inline std::string instanceKey(const CaveDescriptor& cave,unsigned floor,const ContentRow& row,unsigned ordinal){
 return cave.cave+":floor"+std::to_string(floor)+":"+row.kind+":"+std::to_string(row.index)+":"+std::to_string(ordinal);
}
class FloorSession {
public:
 FloorSession()=default;FloorSession(const FloorSession&)=delete;FloorSession&operator=(const FloorSession&)=delete;
 bool activate(const std::string& cave,unsigned floor,const SceneIdentity& scene,
               bool story,const FloorIdentityAuthority& authority,FloorProvider& provider,std::string& error){
  if(mProvider){error="retail_floor_already_owned";return false;}
  const auto* desc=descriptor(cave);const auto* def=desc?definition(*desc,floor):nullptr;
  if(!def||scene.seed.empty()||scene.visit.empty()||!scene.serial||!hex64(scene.layoutSha256)){
   error="retail_floor_identity";return false;
  }
  // Definition ranges/optional weights need the selected generator output.
  // The first provider is intentionally bounded to individually authored floors.
  if(def->first!=def->last){error="retail_floor_range_needs_selection";return false;}
  if(def->gates||def->caps){error="retail_floor_gate_cap_selection_required";return false;}
  for(const auto& row:def->rows)if(row.weight()){
   error="retail_floor_weighted_selection_required";return false;
  }
  std::vector<BirthIdentity> expectedBirths;
  for(unsigned r=0;r<def->rows.size();++r)for(unsigned ordinal=0;ordinal<def->rows[r].minimum();++ordinal){
   BirthIdentity next;
   if(!authority.expectedBirth(*desc,floor,scene,r,ordinal,next,error))return false;
   if(next.row!=r||next.ordinal!=ordinal||!next.epoch||!next.activation||
      next.instance!=instanceKey(*desc,floor,def->rows[r],ordinal)){
    error="retail_floor_expected_origin";return false;
   }
   expectedBirths.push_back(next);
  }
  if(!provider.preflight(*desc,*def,floor,scene,error))return false;
  mProvider=&provider; // retain ownership even if a partial birth cannot release
  std::vector<LiveBinding> bindings;
  bool installed=provider.install(*desc,*def,floor,scene,expectedBirths,bindings,error);
  std::set<std::string> expected,seen;std::set<const void*> pointers;
  for(const auto& row:def->rows)for(unsigned ordinal=0;ordinal<row.minimum();++ordinal)
   expected.insert(instanceKey(*desc,floor,row,ordinal));
  if(installed){
   for(const auto& binding:bindings){
    const auto& id=binding.identity;
    if(id.row>=def->rows.size()||!id.epoch||
       id.ordinal>=def->rows[id.row].minimum()||
       id.instance!=instanceKey(*desc,floor,def->rows[id.row],id.ordinal)||
       !seen.insert(id.instance).second){
     installed=false;error="retail_floor_incomplete_native_bindings";break;
    }
    const BirthIdentity* expectedBirth=nullptr;
    for(const auto& value:expectedBirths)if(value.row==id.row&&value.ordinal==id.ordinal){expectedBirth=&value;break;}
    if(!expectedBirth||!(id==*expectedBirth)){installed=false;error="retail_floor_origin_mismatch";break;}
    if(binding.state==BindingState::Live){
     if(!binding.actor||!binding.receipt.empty()||!pointers.insert(binding.actor).second){
      installed=false;error="retail_floor_invalid_live_binding";break;
     }
    }else if(binding.actor||binding.receipt.empty()||
             (binding.state==BindingState::ConsumedTreasure&&def->rows[id.row].kind!="loose_treasure")||
             (binding.state==BindingState::SourceSuppressed&&def->rows[id.row].sourceId!=6&&def->rows[id.row].sourceId!=7)||
             !provider.verifyAbsent(*desc,floor,def->rows[id.row],scene,*expectedBirth,binding)){
     installed=false;error="retail_floor_unverified_absent_source";break;
    }
   }
   if(installed&&seen!=expected){installed=false;error="retail_floor_missing_native_content";}
  }
  if(!installed){std::string cleanup;if(provider.release(cleanup))mProvider=nullptr;
   else error+=";release_failed:"+cleanup;
   return false;}
  mSnapshot={desc->cave,desc->source,desc->sourceSha256,desc->catalogSha256,floor,desc->maxFloor,scene,story,true};
  mDefinition=def;mBindings=std::move(bindings);mActive=true;return true;
 }
 bool snapshot(const SceneIdentity& scene,Snapshot& out)const{
  if(!mActive||!(mSnapshot.scene==scene))return false;
  out=mSnapshot;return true;
 }
 bool unload(std::string& error){
  // Revoke authority before touching native content. A failed release cannot
  // grant last-floor/boss authority but keeps provider ownership for retry.
  mActive=false;
  if(mProvider&&!mProvider->release(error))return false;
  mProvider=nullptr;mDefinition=nullptr;mBindings.clear();mSnapshot=Snapshot{};return true;
 }
 bool heldDrop(const SceneIdentity& scene,const void* actor,const std::string& instance,
               const std::string& treasure,std::uint64_t releaseEvent,Snapshot& out,
               bool& boss)const{
  if(!releaseEvent||!snapshot(scene,out))return false;
  for(const auto& binding:mBindings)if(binding.state==BindingState::Live&&binding.actor==actor&&binding.identity.instance==instance){
   const auto& row=mDefinition->rows[binding.identity.row];
   if(row.kind!="enemy"&&row.kind!="cap_enemy")return false;
   if(row.heldTreasure.empty()||row.heldTreasure!=treasure)return false;
   if(!mProvider->verifyHeldRelease(actor,binding.identity,treasure,releaseEvent))return false;
   boss=row.boss;return true;
  }
  return false;
 }
private:
 FloorProvider* mProvider=nullptr;const FloorDefinition* mDefinition=nullptr;
 Snapshot mSnapshot;std::vector<LiveBinding> mBindings;bool mActive=false;
};
} // namespace p2retail
