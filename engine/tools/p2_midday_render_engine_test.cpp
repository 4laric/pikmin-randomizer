// Actual initialized captain Material/TEV/texture capture and isolated staged
// allocation/backing/bind/disposal. No complete world or fresh-process resume.
#include "system.h"
#include "App.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "pc_midday_render_prototypes.h"
#include "NaviState.h"
#include "PikiMgr.h"
#include "GameStat.h"
#include "ItemMgr.h"
#include "PikiHeadItem.h"
#include "ObjType.h"
#include "Node.h"
#include "MoviePlayer.h"
#include "pc_midday_render_mutable.h"
#include "pc_midday_world_resources.h"
#include "GlobalShape.h"
#include "Shape.h"
#include "PlayerState.h"

#include "Material.h"
#include "UtEffect.h"
#include "sysNew.h"
#include "pc_midday_constructor.h"
#include "pc_bbft.h"
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "pc_coop.h"
#include "pc_randomizer.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <SDL2/SDL.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <tuple>
using namespace pc_midday;
namespace {
unsigned checks=0;
void require(bool ok,const std::string& e){++checks;if(!ok){std::printf("FAIL MIDDAY_RENDER %s\n",e.c_str());std::fflush(nullptr);std::_Exit(1);}}
void requireError(bool ok,const char* step,const std::string& e){require(ok,std::string(step)+": "+e);}
using Nodes=std::vector<std::tuple<const CoreNode*,const CoreNode*,const CoreNode*>>;
Nodes generatorRoots(){Nodes out;std::set<const CoreNode*>seen;require(gameflow.mFlowManager!=nullptr,"flow root initialized");for(auto*n=gameflow.mFlowManager->mChild;n;n=n->mNext){require(seen.size()<4096&&seen.insert(n).second,"bounded generator roots");out.emplace_back(n,n->mNext,n->mParent);}return out;}
bool same(const LogicalRef&a,const LogicalRef&b){return a.owner==b.owner&&a.resource==b.resource&&a.slot==b.slot;}
bool equalGraphs(const RenderGraph&a,const RenderGraph&b){if(a.generation!=b.generation||a.nodes.size()!=b.nodes.size()||a.links.size()!=b.links.size())return false;for(size_t i=0;i<a.nodes.size();++i){const auto&x=a.nodes[i];const auto&y=b.nodes[i];if(x.id!=y.id||x.factory!=y.factory||x.kind!=y.kind||x.count!=y.count||x.contentRoot!=y.contentRoot||x.payloads!=y.payloads)return false;}for(size_t i=0;i<a.links.size();++i){const auto&x=a.links[i];const auto&y=b.links[i];if(x.materials!=y.materials||x.slot!=y.slot||x.pvw!=y.pvw||x.tev!=y.tev||x.textures!=y.textures||x.textureCount!=y.textureCount||x.tevSlot!=y.tevSlot)return false;}return true;}
bool sameHeap(const PikiPcAllocationStats&a,const PikiPcAllocationStats&b){return a.liveBlocks==b.liveBlocks&&a.liveBytes==b.liveBytes&&a.unknownFrees==b.unknownFrees;}
void heapTrace(const char* phase,size_t index,const PikiPcAllocationStats&before,const PikiPcAllocationStats&after){const bool exact=sameHeap(before,after);std::printf("MIDDAY_RENDER_HEAP phase=%s index=%zu before_blocks=%zu after_blocks=%zu before_bytes=%zu after_bytes=%zu before_unknown=%zu after_unknown=%zu\n",phase,index,before.liveBlocks,after.liveBlocks,before.liveBytes,after.liveBytes,before.unknownFrees,after.unknownFrees);require(exact,"native stage disposal returns exact heap baseline");}
struct Row {u64 id=0;RenderKind kind=RenderKind::Materials;BaseShape* model=nullptr;std::vector<u32> slots;void* source=nullptr;u32 count=0;bool contentRoot=false;};
struct TypedPointerLess {bool operator()(const std::pair<RefKind,const void*>&a,const std::pair<RefKind,const void*>&b)const{if(a.first!=b.first)return unsigned(a.first)<unsigned(b.first);return std::less<const void*>()(a.second,b.second);}};
struct Entry {RefKind role;const void* source;LogicalRef logical;bool owned=false;};
// Actual cursor clones plus the two captains' shared initialized body prototype.
// This renderer subset is deliberately not the complete scene asset registry.
struct Inventory {
 std::vector<Row> rows;std::map<const void*,u64> bases;std::map<std::pair<RefKind,const void*>,Entry,TypedPointerLess> entries;std::map<std::pair<u64,u32>,Entry> logical;
 RenderDescriptorIndex descriptors;u64 nextContent=100000;unsigned sharedArrays=0,sharedBodyArrays=0,clonedTevs=0;std::map<const void*,std::set<int>> textureOwners;
 const Row& row(u64 id)const{auto p=std::find_if(rows.begin(),rows.end(),[&](const Row&r){return r.id==id;});require(p!=rows.end(),"known fixture canonical row");return *p;}
 void registerEntry(RefKind role,const void* p,LogicalRef r,bool owned){if(!p)return;auto key=std::make_pair(role,p);auto it=entries.find(key);if(it!=entries.end()){require(same(it->second.logical,r)&&it->second.owned==owned,"physical reference has one canonical typed identity");return;}Entry e{role,p,r,owned};require(logical.emplace(std::make_pair(r.resource,r.slot),e).second,"unique logical resource element");entries.emplace(key,e);}
 void content(RefKind role,const void* p){if(!p)return;if(entries.count({role,p}))return;registerEntry(role,p,{0,nextContent++,0},false);}
 LogicalRef identity(RefKind role,const void* p)const{if(!p)return {};auto it=entries.find({role,p});require(it!=entries.end(),"source-defined typed pointer registered");return it->second.logical;}
 u64 add(RenderKind kind,void* p,u32 count,BaseShape&model,std::vector<u32> slots,bool root=false){require(p&&count&&count<=256&&rows.size()<4096,"bounded actual allocation observation");auto it=bases.find(p);if(it!=bases.end()){const auto&r=row(it->second);require(r.kind==kind&&r.count==count&&r.contentRoot==root,"shared allocation exact kind/extent");return r.id;}u64 id=rows.size()+1;rows.push_back({id,kind,&model,std::move(slots),p,count,root});bases.emplace(p,id);std::string e;requireError(root?descriptors.declareTevArray(100+id,model,e):descriptors.declare(100+id,kind,model,rows.back().slots,e),"actual installed factory",e);if(kind==RenderKind::Tev)for(u32 i=0;i<count;++i)registerEntry(RefKind::PVWTevInfo,&static_cast<PVWTevInfo*>(p)[i],{0,id,i},true);if(kind==RenderKind::Textures)for(u32 i=0;i<count;++i)registerEntry(RefKind::PVWTextureData,&static_cast<PVWTextureData*>(p)[i],{0,id,i},true);return id;}
 void census(const ConstructorFence& fence){require(naviMgr->getNaviCount()==2,"two actual initialized captain owners required");
 auto* first=naviMgr->getNavi(0);auto* second=naviMgr->getNavi(1);
 require(first&&second&&first!=second&&first->mNaviShapeObject&&first->mNaviShapeObject==second->mNaviShapeObject,"actual distinct captains share identical native body ShapeObject");
 auto* body=first->mNaviShapeObject->mShape;
 require(body&&body==second->mNaviShapeObject->mShape&&body->mMaterialCount>0&&body->mMaterialCount<=256&&body->mTevInfoCount>0&&body->mTevInfoCount<=256&&body->mTexAttrCount>=0&&body->mTexAttrCount<=4096&&(!body->mTexAttrCount||body->mTexAttrList),"actual initialized shared body model and complete allocation extents");
 std::vector<u32> bodySlots;for(int i=0;i<body->mMaterialCount;++i)bodySlots.push_back(i);
 PrototypeShapeBinding binding;binding.content=99999;binding.model=body;
 binding.tevs=add(RenderKind::Tev,body->mTevInfoList,body->mTevInfoCount,*body,{},true);binding.tevFactory=100+binding.tevs;
 binding.materials=add(RenderKind::Materials,body->mMaterialList,body->mMaterialCount,*body,bodySlots);binding.materialFactory=100+binding.materials;
 for(int i=0;i<body->mMaterialCount;++i){auto& mat=body->mMaterialList[i];content(RefKind::TexAttr,mat.mAttribute);content(RefKind::Texture,mat.mTexture);content(RefKind::Texture,mat.mEnvMapTexture);
  if(!(mat.mFlags&MATFLAG_PVW))continue;
  require(mat.mTevInfoIndex<u32(body->mTevInfoCount)&&mat.mTevInfo==&body->mTevInfoList[mat.mTevInfoIndex],"body material exact original TEV element");
  const auto count=mat.mTextureInfo.mTextureDataCount;if(!count)continue;auto* p=mat.mTextureInfo.mTextureData;
  const auto id=add(RenderKind::Textures,p,count,*body,{u32(i)});binding.textures.push_back({u32(i),id,100+id});
  // Both real consumers reference this exact shared model allocation. No cursor
  // texture is invented and no makeInstance/init/update callback is invoked.
  for(int captain=0;captain<2;++captain){auto* n=naviMgr->getNavi(captain);require(n->mNaviShapeObject->mShape==body&&n->mNaviShapeObject->mShape->mMaterialList[i].mTextureInfo.mTextureData==p,"shared texture is the exact initialized body allocation for each real captain");textureOwners[p].insert(captain);}
  for(u32 t=0;t<count;++t){require(p[t].mSourceAttrIndex<u32(body->mTexAttrCount)&&p[t].mTextureAttribute==&body->mTexAttrList[p[t].mSourceAttrIndex]&&p[t].mTexture==p[t].mTextureAttribute->mTexture,"initialized texture content pointers agree with actual loader bindings");content(RefKind::TexAttr,p[t].mTextureAttribute);content(RefKind::Texture,p[t].mTexture);}
 }
 for(const auto& owners:textureOwners)if(owners.second.size()==2)++sharedBodyArrays;
 require(sharedBodyArrays>0,"actual shared body texture allocation coverage");
 PrototypeRenderCensus bodyCensus;std::string e;requireError(observePrototypeRender(7,{binding},fence,bodyCensus,e),"complete actual body prototype census",e);
 require(bodyCensus.observations.size()==rows.size()&&bodyCensus.required==required(),"prototype observer covers every canonical body allocation exactly");
 for(const auto& observed:bodyCensus.observations){const auto&r=row(observed.id);require(observed.factory==100+r.id&&observed.kind==r.kind&&observed.count==r.count&&observed.address==reinterpret_cast<uintptr_t>(r.source)&&observed.contentRoot==r.contentRoot,"prototype observer and native physical inventory agree");}
for(int captain=0;captain<2;++captain){auto*n=naviMgr->getNavi(captain);require(n!=nullptr,"actual captain exists");auto&m=n->mAnimatedMaterials;require(m.mModel&&m.mModel==GlobalShape::cursorShape&&m.mMaterials&&m.mMatCount>0&&m.mMatCount<=256,"actual initialized cursor array/model");std::vector<u32> slots;std::set<u32> unique;for(int i=0;i<m.mMatCount;++i){const auto slot=m.mMaterials[i].mIndex;require(slot<u32(m.mModel->mMaterialCount)&&unique.insert(slot).second,"source selected material slot unique/in-range");slots.push_back(slot);}add(RenderKind::Materials,m.mMaterials,m.mMatCount,*m.mModel,slots);
  for(int i=0;i<m.mMatCount;++i){auto&mat=m.mMaterials[i];content(RefKind::TexAttr,mat.mAttribute);content(RefKind::Texture,mat.mTexture);content(RefKind::Texture,mat.mEnvMapTexture);if(!(mat.mFlags&MATFLAG_PVW))continue;auto&source=m.mModel->mMaterialList[mat.mIndex];require(mat.mTevInfo&&mat.mTevInfo!=source.mTevInfo,"observed real per-instance TEV clone");const bool newClone=!bases.count(mat.mTevInfo);add(RenderKind::Tev,mat.mTevInfo,1,*m.mModel,{mat.mIndex});if(newClone)++clonedTevs;const auto count=mat.mTextureInfo.mTextureDataCount;if(!count)continue;require(mat.mTextureInfo.mTextureData==source.mTextureInfo.mTextureData&&count==source.mTextureInfo.mTextureDataCount,"actual shared source texture provenance/extent");auto*p=mat.mTextureInfo.mTextureData;auto&owners=textureOwners[p];owners.insert(captain);add(RenderKind::Textures,p,count,*m.mModel,{mat.mIndex});for(u32 t=0;t<count;++t){content(RefKind::TexAttr,p[t].mTextureAttribute);content(RefKind::Texture,p[t].mTexture);}}
 }
 for(const auto& owners:textureOwners)if(owners.second.size()==2)++sharedArrays;
 require(clonedTevs>=2&&sharedArrays>0,"both real cursor TEV clones and actual shared body texture allocation required");}
 std::vector<RenderObservation> observations(const IsolatedRenderAllocations* owner=nullptr)const{std::vector<RenderObservation> out;for(const auto&r:rows){const size_t stride=r.kind==RenderKind::Materials?sizeof(Material):r.kind==RenderKind::Tev?sizeof(PVWTevInfo):sizeof(PVWTextureData);void*p=owner?owner->allocation(r.id):r.source;require(p!=nullptr,"actual row allocation exists");out.push_back({r.id,100+r.id,r.kind,r.count,reinterpret_cast<uintptr_t>(p),stride,r.contentRoot});}return out;}
 std::set<u64> required()const{std::set<u64>out;for(const auto&r:rows)out.insert(r.id);return out;}
};
struct Expected {FieldSchema schema;const void* source=nullptr;LogicalRef logical;};
struct Resolver:LogicalResolver {
 const Inventory& inventory;u64 id;u32 slot;const IsolatedRenderAllocations*owner;const bool* foreign;
 Resolver(const Inventory&i,u64 n,u32 s,const IsolatedRenderAllocations*o,const bool*f):inventory(i),id(n),slot(s),owner(o),foreign(f){}
 bool expected(const char* key,Expected& x,std::string& e)const{
  const auto&r=inventory.row(id);if(slot>=r.count){e="fixture source slot out of extent";return false;}const std::string k(key);
  auto set=[&](RefKind role,const char* type,bool nullable,ReferenceOwnership ownership,const void*p){x.schema=FieldSchema::ref(key,role,nullable,type,ownership);x.source=p;x.logical=inventory.identity(role,p);return true;};
  if(r.kind==RenderKind::Materials){const auto&m=static_cast<const Material*>(r.source)[slot];if(k=="mAttribute")return set(RefKind::TexAttr,"TexAttr",true,ReferenceOwnership::Content,m.mAttribute);if(k=="mTexture")return set(RefKind::Texture,"Texture",true,ReferenceOwnership::Content,m.mTexture);if(k=="mEnvMapTexture")return set(RefKind::Texture,"Texture",true,ReferenceOwnership::Content,m.mEnvMapTexture);if(m.mFlags&MATFLAG_PVW){if(k=="tev")return set(RefKind::PVWTevInfo,"PVWTevInfo",false,ReferenceOwnership::AnyLive,m.mTevInfo);if(k.rfind("texture.",0)==0){for(u32 i=0;i<m.mTextureInfo.mTextureDataCount;++i)if(k=="texture."+std::to_string(i))return set(RefKind::PVWTextureData,"PVWTextureData",false,ReferenceOwnership::Content,&m.mTextureInfo.mTextureData[i]);}}}
  if(r.kind==RenderKind::Textures){const auto&t=static_cast<const PVWTextureData*>(r.source)[slot];if(k=="mTextureAttribute")return set(RefKind::TexAttr,"TexAttr",true,ReferenceOwnership::Content,t.mTextureAttribute);if(k=="mTexture")return set(RefKind::Texture,"Texture",true,ReferenceOwnership::Content,t.mTexture);}
  e="unknown fixture schema key/concrete source role";return false;
 }
 void* address(const Expected&x,bool inject=false)const{if(!x.source)return nullptr;const auto&e=inventory.logical.at({x.logical.resource,x.logical.slot});if(!owner||!e.owned||(inject&&foreign&&*foreign))return const_cast<void*>(x.source);void*p=owner->allocation(x.logical.resource);if(e.role==RefKind::PVWTevInfo)return &static_cast<PVWTevInfo*>(p)[x.logical.slot];if(e.role==RefKind::PVWTextureData)return &static_cast<PVWTextureData*>(p)[x.logical.slot];return nullptr;}
 bool identify(const char*k,RefKind role,const void*p,LogicalRef&out,std::string&e)override{Expected x;if(!expected(k,x,e)||x.schema.reference!=role||p!=address(x)){e="captured fixture pointer is not exact source-derived typed slot";return false;}out=x.logical;return true;}
 bool validate(const char*k,RefKind role,const LogicalRef&r,std::string&e)const override{Expected x;return expected(k,x,e)&&x.schema.reference==role&&same(r,x.logical);}
 bool validateTyped(const FieldSchema&s,const LogicalRef&r,std::string&e)const override{Expected x;if(!expected(s.key.c_str(),x,e)||s.category!=FieldCategory::Reference||s.reference!=x.schema.reference||s.targetType!=x.schema.targetType||s.nullable!=x.schema.nullable||s.ownership!=x.schema.ownership||!s.ownerLink.empty()||s.strength!=ReferenceStrength::Weak||!same(r,x.logical)){e="fixture exact key/type/ownership/slot contract differs from actual source";return false;}return true;}
 bool resolve(const char*k,RefKind role,const LogicalRef&r,void*&out,std::string&e)override{Expected x;if(!expected(k,x,e)||role!=x.schema.reference||!same(r,x.logical))return false;out=address(x,true);return true;}
 bool identifyHandle(const char*,RefKind,u32,LogicalRef&,std::string&)override{return false;}
 bool resolveHandle(const char*,RefKind,const LogicalRef&,u32&,std::string&)override{return false;}
};
struct Resolvers {
 std::map<std::pair<u64,u32>,std::unique_ptr<Resolver>> values;
 Resolvers(const Inventory&i,const IsolatedRenderAllocations*owner=nullptr,const bool*foreign=nullptr){for(const auto&r:i.rows)for(u32 s=0;s<r.count;++s)values.emplace(std::make_pair(r.id,s),std::make_unique<Resolver>(i,r.id,s,owner,foreign));}
 LogicalResolver* get(u64 id,u32 slot){auto i=values.find({id,slot});return i==values.end()?nullptr:i->second.get();}
};
void run(){
 auto*captains=naviMgr;auto*pikis=pikiMgr;auto*items=itemMgr;auto*player=playerState;const auto generators=generatorRoots();std::array<Navi*,2> actors{naviMgr->getNavi(0),naviMgr->getNavi(1)};require(actors[0]&&actors[1],"actual two captain roots");auto* bodyObject=actors[0]->mNaviShapeObject;auto* body=bodyObject?bodyObject->mShape:nullptr;require(body!=nullptr,"actual captain body root exists");auto* bodyMaterials=body->mMaterialList;auto* bodyTevs=body->mTevInfoList;const auto bodyMaterialCount=body->mMaterialCount,bodyTevCount=body->mTevInfoCount;
 std::array<ShapeDynMaterials,2> roots; // Named readonly view, no actor/material copying.
 for(size_t i=0;i<2;++i){roots[i].mModel=actors[i]->mAnimatedMaterials.mModel;roots[i].mMaterials=actors[i]->mAnimatedMaterials.mMaterials;roots[i].mMatCount=actors[i]->mAnimatedMaterials.mMatCount;roots[i].mNext=actors[i]->mAnimatedMaterials.mNext;}
 std::string error;PcSimRngCheckpoint before,after;requireError(pc_sim_rng_capture(before,error),"real RNG before",error);ConstructorFence fence;requireError(fence.begin(error),"real SDL/RNG/reward constructor fence",error);
 Inventory inventory;inventory.census(fence);Resolvers sourceResolvers(inventory);auto sourceFactory=[&](u64 id,u32 slot){return sourceResolvers.get(id,slot);};const auto sourceObservations=inventory.observations();const auto required=inventory.required();RenderGraph graph;requireError(captureRenderGraph(7,sourceObservations,required,sourceFactory,graph,error),"actual initialized source render capture",error);requireError(inventory.descriptors.validate(graph,error),"real installed asset factory compare",error);RestoreGate gate{true,true,true,true,true,true,true};
 const size_t failureSites=graph.nodes.size()+1;unsigned failures=0;
 for(size_t fail=1;fail<=failureSites;++fail){const auto beforeHeap=piki_pc_allocation_stats();{
  std::string e;IsolatedRenderAllocations owner;require(!owner.prepare(graph,gate,fence,e,fail)&&!owner.allocation(graph.nodes.front().id)&&e.rfind("render allocation failed:",0)==0,"each explicit real native owning allocation boundary refuses without partial roots");++failures;
  RenderGraph current;requireError(captureRenderGraph(7,sourceObservations,required,sourceFactory,current,e),"source recapture after failed native construction",e);require(equalGraphs(graph,current),"failure leaves all source mutable payloads/aliases unchanged");
 }const auto afterHeap=piki_pc_allocation_stats();heapTrace("failure",fail,beforeHeap,afterHeap);}
 for(size_t round=0;round<2;++round){const auto beforeHeap=piki_pc_allocation_stats();{
  std::string e;IsolatedRenderAllocations owner;requireError(owner.prepare(graph,gate,fence,e),"actual isolated native render construction",e);requireError(inventory.descriptors.initializeBacking(graph,owner,fence,e),"actual installed immutable backing",e);require(owner.backingReady()&&!owner.mutableReady(),"unbound native owners remain unavailable for consumers");
  bool foreign=true;Resolvers stagedResolvers(inventory,&owner,&foreign);auto stagedFactory=[&](u64 id,u32 slot){return stagedResolvers.get(id,slot);};
  RenderGraph wrongElement=graph;auto arrayLink=std::find_if(wrongElement.links.begin(),wrongElement.links.end(),[&](const RenderLink& link){return link.pvw&&inventory.row(link.tev).contentRoot&&inventory.row(link.tev).count>1;});require(arrayLink!=wrongElement.links.end(),"actual full TEV array element coverage");arrayLink->tevSlot=(arrayLink->tevSlot+1)%inventory.row(arrayLink->tev).count;
  require(!bindRenderMutable(wrongElement,owner,inventory.descriptors,stagedFactory,fence,e)&&!owner.mutableReady(),"valid in-range foreign TEV element refused before Apply");requireError(inventory.descriptors.matchesInitializedBacking(graph,owner,fence,e),"element refusal preserves actual backing",e);
  require(!bindRenderMutable(graph,owner,inventory.descriptors,stagedFactory,fence,e)&&!owner.mutableReady(),"source TEV/texture addresses cannot masquerade as owned staged aliases");foreign=false;
  RenderGraph bad=graph;auto texture=std::find_if(bad.nodes.rbegin(),bad.nodes.rend(),[](const RenderNode&n){return n.kind==RenderKind::Textures;});require(texture!=bad.nodes.rend(),"real texture payload coverage");ActorFields fields;requireError(decode_actor_fields(texture->payloads.back(),fields,e),"decode actual late geometry fixture",e);fields.at("mSourceAttrIndex").bits^=1;requireError(encode_actor_fields(fields,texture->payloads.back(),e),"encode late foreign immutable geometry",e);require(!bindRenderMutable(bad,owner,inventory.descriptors,stagedFactory,fence,e)&&!owner.mutableReady(),"late valid payload geometry refusal before Apply");requireError(inventory.descriptors.matchesInitializedBacking(graph,owner,fence,e),"negative binds leave actual owned backing intact",e);
  requireError(bindRenderMutable(graph,owner,inventory.descriptors,stagedFactory,fence,e),"actual cached typed mutable bind",e);require(owner.mutableReady(),"complete actual native named-field bind ready");require(!bindRenderMutable(graph,owner,inventory.descriptors,stagedFactory,fence,e),"second Apply refused");
  RenderGraph observed;const auto stagedObservations=inventory.observations(&owner);requireError(captureRenderGraph(7,stagedObservations,required,stagedFactory,observed,e),"actual native staged named-field readback",e);require(equalGraphs(graph,observed),"all native Material/three-register TEV/texture payloads and canonical aliases roundtrip exactly");
  std::set<const void*> cloned;std::map<u64,const void*> shared;for(const auto&link:graph.links)if(link.pvw){auto&m=static_cast<Material*>(owner.allocation(link.materials))[link.slot];require(m.mTevInfo==&static_cast<PVWTevInfo*>(owner.allocation(link.tev))[link.tevSlot]&&m.mTevInfo!=&static_cast<PVWTevInfo*>(inventory.row(link.tev).source)[link.tevSlot],"real TEV reference binds exact owned array element");cloned.insert(m.mTevInfo);if(link.textureCount){require(m.mTextureInfo.mTextureData==owner.allocation(link.textures)&&m.mTextureInfo.mTextureData!=inventory.row(link.textures).source,"real texture binds private canonical array");auto inserted=shared.emplace(link.textures,m.mTextureInfo.mTextureData);require(inserted.second||inserted.first->second==m.mTextureInfo.mTextureData,"shared mutable texture aliases retain identical destination");}}
  require(cloned.size()>=2&&!shared.empty(),"actual distinct TEV/shared texture destinations covered");RenderGraph current;requireError(captureRenderGraph(7,sourceObservations,required,sourceFactory,current,e),"actual source recapture after bind",e);require(equalGraphs(graph,current),"typed bind never mutates actual live source assets");
 }const auto afterHeap=piki_pc_allocation_stats();heapTrace("disposal",round,beforeHeap,afterHeap);}
 for(size_t i=0;i<2;++i){const auto&m=actors[i]->mAnimatedMaterials;require(naviMgr->getNavi(i)==actors[i]&&m.mModel==roots[i].mModel&&m.mMaterials==roots[i].mMaterials&&m.mMatCount==roots[i].mMatCount&&m.mNext==roots[i].mNext,"live captain material root topology unchanged");}
 require(actors[0]->mNaviShapeObject==bodyObject&&actors[1]->mNaviShapeObject==bodyObject&&bodyObject->mShape==body&&body->mMaterialList==bodyMaterials&&body->mTevInfoList==bodyTevs&&body->mMaterialCount==bodyMaterialCount&&body->mTevInfoCount==bodyTevCount,"shared live body root and original arrays unchanged");
 require(naviMgr==captains&&pikiMgr==pikis&&itemMgr==items&&playerState==player&&generatorRoots()==generators,"live manager/player/generator roots unchanged");requireError(fence.finish(false,error),"actual fence abort after native disposal",error);requireError(pc_sim_rng_capture(after,error),"actual RNG after",error);require(before.profile==after.profile&&before.simState==after.simState&&before.cosmeticState==after.cosmeticState&&before.simDraws==after.simDraws&&before.cosmeticDraws==after.cosmeticDraws,"actual RNG exact after constructors/binds/disposal and abort");
 std::printf("PASS MIDDAY_RENDER checks=%u injected_failures=%u disposal_rounds=2 native_constructors=1 backing=1 typed_bind=1 heap_exact=1 actual_captains=2 cloned_tevs=%u shared_texture_arrays=%u shared_body_texture_arrays=%u source_unchanged=1 synthetic_descriptors=0 fresh_process_resume=0\n",checks,failures,inventory.clonedTevs,inventory.sharedArrays,inventory.sharedBodyArrays);std::fflush(nullptr);std::_Exit(0);
}
class TestApp:public PlugPikiApp {
 std::chrono::steady_clock::time_point started=std::chrono::steady_clock::now();
public:int idle()override {
 require(std::chrono::steady_clock::now()-started<std::chrono::seconds(55),"bounded startup");
 if(naviMgr&&naviMgr->getActiveNavi()){auto*n=naviMgr->getActiveNavi();if(GameStat::orimaDead||n->mHealth<=1||(n->getCurrState()&&n->getCurrState()->getID()==NAVISTATE_Dead)){std::printf("P2_FIXTURE_CAPTAIN_DOWN outcome=BLOCKED\n");std::fflush(nullptr);std::_Exit(86);}}
 int result=PlugPikiApp::idle();if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_randomizer_ready()||!naviMgr||!pikiMgr||!itemMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 auto*n=naviMgr->getActiveNavi();if(!n||!n->getCurrState()||n->getCurrState()->getID()!=NAVISTATE_Walk)return result;
 int count=0;Iterator it(pikiMgr);for(it.first();!it.isDone();it.next())++count;if(count!=20)return result;
 run();return result;
 }
};
}
int main(int argc,char**argv){
 SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1",1);SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();
 pc_sim_rng_note_main_thread();std::string error;requireError(pc_sim_rng_begin_offline(0x68,0x168,error),"portable bootstrap",error);
 pc_gpu_preference_apply();pc_bbft_init(argc,argv);require(pc_randomizer_enabled(),"ordinary generated assets required");
 if(!pc_window_init("Midday render resources fixture",960,540))return 3;
 pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();int w=0,h=0;SDL_GetWindowSize(SDL_GL_GetCurrentWindow(),&w,&h);require(w==960&&h==540,"960x540 baseline");
 pc_coop_set_pending(false);gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new TestApp());return 0;
}
