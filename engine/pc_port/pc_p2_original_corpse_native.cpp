#include "pc_p2_original_corpse_native.h"
#include "pc_p2_original_actor.h"
#include "Pellet.h"
#include "PelletView.h"
#include "teki.h"
#include "GoalItem.h"
#include "Matrix4f.h"
#include "system.h"
#include "Collision.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <map>
namespace {
struct Binding {std::uint64_t handle;const p2original::CorpseProfile* profile;CollPart* sphere=nullptr;bool updateActive=true,stickEnabled=true;};
std::map<const Pellet*,Binding> bindings;
// Profiles contain only persistent literal values: no App-heap model/config links.
std::map<unsigned,PelletConfig*> configs;
std::map<unsigned,ObjCollInfo*> collisionNodes;
std::unique_ptr<p2original::CorpseLedger> ledger;
std::unique_ptr<p2original::CorpseDeathPolicy> deathPolicy;
std::string ledgerCatalog;
[[noreturn]] void fault(const std::string& e){std::fprintf(stderr,"P2_ORIGINAL_CORPSE_FAIL %s\n",e.c_str());std::abort();}
bool fail(std::string& e,const char* s){e=s;return false;}
Creature* creature(PelletView* view){return view?dynamic_cast<Creature*>(view):nullptr;}
PelletConfig* config(const p2original::CorpseProfile& p){
 auto i=configs.find(p.source);if(i!=configs.end())return i->second;
 // These small immutable configs persist across App-heap reset/reentry.
 const int old=gsys->setHeap(SYSHEAP_Sys);
 PelletConfig* c=new PelletConfig;gsys->setHeap(old);
 c->mModelId.setID(0x50320000u|p.source);c->mPelletId=c->mModelId;
 c->mPelletName.mValue=String(p.name,0);
 c->mPelletType.mValue=PELTYPE_Corpse;c->mPelletColor.mValue=PELCOLOR_NULL;
 c->mCarryMinPikis.mValue=int(p.minimum);c->mCarryMaxPikis.mValue=int(p.maximum);
 c->mMatchingOnyonSeeds.mValue=int(p.seeds);c->mNonMatchingOnyonSeeds.mValue=int(p.seeds);
 c->mCarryInfoHeight.mValue=p.height;c->mPelletScale.mValue=1.0f;
 c->mUseDynamicMotion.mValue=0;c->mAnimSoundID.mValue=-1;
 configs.emplace(p.source,c);return c;
}
void ensureLedger(const std::string& catalog){
 if(ledger&&ledgerCatalog==catalog)return;
 std::string e;if(!pc_p2_original_corpse_new_session(catalog,e))fault(e);
}
}
bool pc_p2_original_corpse_resources(unsigned source,std::string& e){
 if(p2original::corpseDisabled(source)){e.clear();return true;}
 const auto* p=p2original::corpseProfile(source);
 if(!p)return fail(e,"original source has no audited corpse profile");
 if(!pelletMgr||!gsys)return fail(e,"original corpse native manager is unavailable");
 if(!p->minimum||p->maximum<p->minimum||p->maximum>128||!p->seeds||p->pickRadius<=0||p->height<=0)
  return fail(e,"original corpse profile cannot fit native physical slots");
 config(*p);e.clear();return true;
}
bool pc_p2_original_corpse_leaves(BTeki* actor,bool ordinary){
 unsigned source=0,token=0;p2original::InstanceIdentity id;
 if(!p2original::originalActors().query(actor,source,token,&id))return ordinary;
 if(p2original::corpseDisabled(source))return false;
 std::string e;if(!pc_p2_original_corpse_resources(source,e))fault(e);
 ensureLedger(id.catalog);return deathPolicy->ordinaryAllowed(id);
}
PelletConfig* pc_p2_original_corpse_config(PelletView* view,PelletConfig* ordinary){
 unsigned source=0,token=0;p2original::InstanceIdentity id;
 if(!p2original::originalActors().query(creature(view),source,token,&id))return ordinary;
 std::string e;if(p2original::corpseDisabled(source))fault("no-corpse original source attempted to birth a corpse");
 if(!pc_p2_original_corpse_resources(source,e))fault(e);
 ensureLedger(id.catalog);if(!deathPolicy->ordinaryAllowed(id))fault("StoneShatter original activation attempted a normal corpse birth");
 return config(*p2original::corpseProfile(source));
}
void pc_p2_original_corpse_born(Pellet* pellet,PelletView* view){
 unsigned source=0,token=0;p2original::InstanceIdentity id;
 if(!p2original::originalActors().query(creature(view),source,token,&id))return;
 const auto* p=p2original::corpseProfile(source);if(!p)fault("unaudited original corpse birth");
 ensureLedger(id.catalog);std::uint64_t h=0;std::string e;
 if(!ledger->birth(pellet,id,source,p->seeds,h,e))fault(e);
 ObjCollInfo* node=nullptr;auto n=collisionNodes.find(source);
 if(n!=collisionNodes.end())node=n->second;
 else {const int old=gsys->setHeap(SYSHEAP_Sys);node=new ObjCollInfo;gsys->setHeap(old);
  node->mId.setID('cent');node->mCode.setID('____');node->mRadius=p->pickRadius;
  node->mCentrePosition.set(0,0,0);node->mJointIndex=-1;collisionNodes.emplace(source,node);}
 // Reuse the Pellet pool's own CollInfo/parts. Farming cannot allocate a new
 // App-heap tree for every corpse; source descriptors are bounded and static.
 auto* tree=pellet->mPelletCollInfo;tree->initInfoTree(node);
 CollPart* sphere=tree->getSphere('cent');if(!sphere)fault("original corpse collision allocation failed");
 const bool updateActive=sphere->mIsUpdateActive,stickEnabled=sphere->mIsStickEnabled;
 sphere->mIsUpdateActive=false;sphere->mIsStickEnabled=false;
 pellet->mCollInfo=tree;bindings.emplace(pellet,Binding{h,p,sphere,updateActive,stickEnabled});
 std::printf("P2_ORIGINAL_CORPSE_BIRTH source=%u uid=%u ordinal=%u epoch=%llu activation=%llu min=%u max=%u seeds=%u\n",
 source,id.generator,id.ordinal,(unsigned long long)id.epoch,(unsigned long long)id.activation,p->minimum,p->maximum,p->seeds);
}
const p2original::CorpseProfile* pc_p2_original_corpse_profile(const Pellet* pellet){auto i=bindings.find(pellet);return i==bindings.end()?nullptr:i->second.profile;}
void pc_p2_original_corpse_forget(Pellet* pellet){
 auto i=bindings.find(pellet);if(i==bindings.end())return;
 if(!ledger||!ledger->forgetPellet(pellet,i->second.handle))fault("corpse retirement lost its receipt binding");
 // CollInfo::initInfo does not reinitialize these flags on pool reuse.
 // Restore the borrowed native part before a P1/number pellet can reuse it.
 i->second.sphere->mIsUpdateActive=i->second.updateActive;
 i->second.sphere->mIsStickEnabled=i->second.stickEnabled;
 bindings.erase(i);
}
bool pc_p2_original_corpse_onion(Pellet* pellet,GoalItem* onion,unsigned& grant){
 auto i=bindings.find(pellet);if(i==bindings.end()){
  if(pellet&&pellet->mConfig&&(pellet->mConfig->mModelId.mId&0xffff0000u)==0x50320000u)
   fault("source corpse suction outlived its native receipt binding");
  return false;
 }
 if(!onion||onion->mObjType!=OBJTYPE_Goal)fault("original corpse receipt requires actual Onion");
 std::string e;if(!ledger->deliver(pellet,i->second.handle,grant,e))fault(e);
 std::printf("P2_ORIGINAL_CORPSE_ONION source=%u seeds=%u duplicate=%d\n",i->second.profile->source,grant,int(grant==0));
 return true;
}
void pc_p2_original_corpse_position(const Pellet* pellet,Vector3f& pos,float direction){
 const auto* p=pc_p2_original_corpse_profile(pellet);if(!p)return;
 // Retail position: actor origin + half height + rotated authored corpse offset.
 const float s=std::sin(direction),c=std::cos(direction);
 pos.x+=c*p->offsetX+s*p->offsetZ;pos.y+=p->height*0.5f+p->offsetY;
 pos.z+=c*p->offsetZ-s*p->offsetX;
}
void pc_p2_original_corpse_view_matrix(const Pellet* pellet,Matrix4f& matrix){
 const auto* p=pc_p2_original_corpse_profile(pellet);if(!p)return;
 // Retail PelletView::viewMakeMatrix translates only by negative half height.
 Matrix4f local,result;local.makeSRT(Vector3f(1,1,1),Vector3f(0,0,0),Vector3f(0,-p->height*0.5f,0));
 matrix.multiplyTo(local,result);matrix=result;
}
void pc_p2_original_corpse_collision(Pellet* pellet){
 auto i=bindings.find(pellet);if(i==bindings.end())return;
 const auto* p=i->second.profile;Matrix4f world;
 world.makeVQS(pellet->mSRT.t,pellet->mRotationQuat,Vector3f(1,1,1));
 Vector3f offset(0,-p->height*0.5f,0);
 // Frog::viewGetCollTreeOffset overrides the joint0 sphere offset.
 if(p->source==17||p->source==18)offset.add(Vector3f(20,-15,0));
 offset.multMatrix(world);auto* sphere=i->second.sphere;
 sphere->mCentre=offset;sphere->mRadius=p->pickRadius;sphere->mJointMatrix=Matrix4f::ident;
}
bool pc_p2_original_corpse_new_session(const std::string& catalog,std::string& e){
 if(!bindings.empty())return fail(e,"original corpses still own native bodies");
 p2original::CorpseSnapshot empty;empty.catalog=catalog;std::vector<std::uint8_t> bytes;
 if(!p2original::encodeCorpseSnapshot(empty,bytes,e))return false;
 ledger=std::make_unique<p2original::CorpseLedger>(catalog);
 deathPolicy=std::make_unique<p2original::CorpseDeathPolicy>(catalog);ledgerCatalog=catalog;e.clear();return true;
}
bool pc_p2_original_corpse_snapshot(p2original::CorpseSnapshot& out,std::string& e){
 if(!ledger)return fail(e,"original corpse ledger has no explicit catalog session");
 out=ledger->snapshot();e.clear();return true;
}
bool pc_p2_original_corpse_unload(std::string& e){
 if(!bindings.empty())return fail(e,"original corpse physical graph is pending; course unload is unsupported");
 // Remaining configs/descriptors live on SYSHEAP_Sys and contain only literal
 // values. The ledger contains identities/receipts, never App-heap addresses.
 e.clear();return true;
}
bool pc_p2_original_corpse_set_death_cause(BTeki* actor,p2original::CorpseDeathCause cause,std::string& e){
 unsigned source=0,token=0;p2original::InstanceIdentity id;
 if(!p2original::originalActors().query(actor,source,token,&id))return fail(e,"death cause requires an actual original activation");
 if(cause!=p2original::CorpseDeathCause::StoneShatter)return fail(e,"unknown original corpse death cause");
 if(!p2original::corpseProfile(source)&&!p2original::corpseDisabled(source))return fail(e,"death cause source is unaudited");
 if(!p2original::validCorpseIdentity(id,id.catalog))return fail(e,"death cause activation identity is invalid");
 if(ledger&&ledgerCatalog!=id.catalog&&!bindings.empty())return fail(e,"death cause crosses a live native corpse session");
 ensureLedger(id.catalog);
 for(const auto& body:bindings){p2original::CorpseRecord record;
  if(ledger->lookup(body.first,body.second.handle,record)&&record.identity==id)
   return fail(e,"original corpse death cause cannot change after body birth");
 }
 return deathPolicy->select(id,cause,e);
}
