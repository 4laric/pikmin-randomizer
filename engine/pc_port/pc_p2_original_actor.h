#pragma once
#include "pc_p2_original_catalog.h"
class Creature;
class Generator;
namespace p2original {
// Independent original-course association. No AP bridge/slot or host fallback.
// Owner must preflight providers/resources before install, then retain this
// registry until every actual actor has retired. Tokens are session-local
// module keys; durable identities are the complete catalog/UID/ordinal/epoch/activation.
class ActorRegistry {
public:
 bool install(const std::string&,const std::vector<CatalogRow>&,const Catalog::Capability&,std::string&);
 bool generator(const Generator*,unsigned,std::uint64_t&,std::string&);
 bool retireGenerator(const Generator*,std::uint64_t);
 bool actor(const Creature*,unsigned,unsigned,std::uint64_t,unsigned&,std::uint64_t&,std::string&);
 bool actorActivation(const Creature*,unsigned uid,unsigned ordinal,std::uint64_t epoch,std::uint64_t activation,unsigned& token,std::uint64_t& handle,std::string&);
 bool query(const Creature*,unsigned& source,unsigned& token,InstanceIdentity* identity=nullptr)const;
 bool retire(const Creature*,std::uint64_t);
 const CatalogRow* find(unsigned uid)const{return mCatalog.find(uid);}
 const std::map<unsigned,CatalogRow>& rows()const{return mCatalog.rows();}
 const std::string& fingerprint()const{return mCatalog.fingerprint();}
private:
 struct Entry {std::uint64_t handle;unsigned token;};
 Catalog mCatalog;std::map<const Creature*,Entry> mActors;
 unsigned mNextToken=0x53000001u;
};
ActorRegistry& originalActors();
}
bool pc_p2_original_actor_source(const Creature*,unsigned& source);
unsigned pc_p2_original_actor_token(const Creature*);
