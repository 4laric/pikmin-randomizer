#include "pc_p2_original_actor.h"
#include <utility>
namespace p2original {
namespace { bool fail(std::string& e,const char* s){e=s;return false;} }
bool ActorRegistry::install(const std::string& fingerprint,const std::vector<CatalogRow>& rows,const Catalog::Capability& capability,std::string& error){
 if(!mActors.empty())return fail(error,"original actors still own family tokens");
 // Catalog itself also refuses any live generator bindings. Never reset the
 // token high-water while another native owner can retain an old family key.
 return mCatalog.install(fingerprint,rows,capability,error);
}
bool ActorRegistry::generator(const Generator* g,unsigned uid,std::uint64_t& h,std::string& e){return mCatalog.bindGenerator(g,uid,h,e);}
bool ActorRegistry::retireGenerator(const Generator* g,std::uint64_t h){return mCatalog.forgetGenerator(g,h);}
bool ActorRegistry::actor(const Creature* actor,unsigned uid,unsigned ordinal,std::uint64_t epoch,unsigned& token,std::uint64_t& handle,std::string& error){
 return actorActivation(actor,uid,ordinal,epoch,1,token,handle,error);
}
bool ActorRegistry::actorActivation(const Creature* actor,unsigned uid,unsigned ordinal,std::uint64_t epoch,std::uint64_t activation,unsigned& token,std::uint64_t& handle,std::string& error){
 if(mNextToken>0x53ffffffu||mActors.count(actor))return fail(error,"original family token capacity/address already bound");
 // Reserve our bookkeeping BEFORE Catalog::bind, which retires logical IDs
 // permanently. Allocation failure must not consume a durable graph identity.
 auto inserted=mActors.emplace(actor,Entry{0,0});
 std::uint64_t candidate=0;
 try {if(!mCatalog.bindActivation(actor,uid,ordinal,epoch,activation,candidate,error)){mActors.erase(inserted.first);return false;}}
 catch(...){mActors.erase(inserted.first);throw;}
 const unsigned next=mNextToken++;
 inserted.first->second=Entry{candidate,next};token=next;handle=candidate;error.clear();return true;
}
bool ActorRegistry::query(const Creature* actor,unsigned& source,unsigned& token,InstanceIdentity* identity)const{
 auto i=mActors.find(actor);if(i==mActors.end())return false;
 InstanceIdentity value;if(!mCatalog.lookup(actor,i->second.handle,value))return false;
 const auto* row=mCatalog.find(value.generator);if(!row)return false;
 source=row->enemy.source;token=i->second.token;if(identity)*identity=std::move(value);return true;
}
bool ActorRegistry::retire(const Creature* actor,std::uint64_t handle){
 auto i=mActors.find(actor);if(i==mActors.end()||i->second.handle!=handle)return false;
 if(!mCatalog.forget(actor,handle))return false;
 mActors.erase(i);return true;
}
ActorRegistry& originalActors(){static ActorRegistry registry;return registry;}
}
bool pc_p2_original_actor_source(const Creature* actor,unsigned& source){unsigned token=0;return p2original::originalActors().query(actor,source,token);}
unsigned pc_p2_original_actor_token(const Creature* actor){unsigned source=0,token=0;return p2original::originalActors().query(actor,source,token)?token:0;}
