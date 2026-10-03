#pragma once
#include "pc_p2_original_corpse_ledger.h"
#include <set>
namespace p2original {
enum class CorpseDeathCause { StoneShatter=1 };
// One-way, address-free policy for this exact source activation. The family
// producer proves the actual retail Stone death boundary before selecting it.
// This is not reward state and has no physical-actor SAVE adapter.
class CorpseDeathPolicy {
public:
 explicit CorpseDeathPolicy(std::string catalog):mCatalog(std::move(catalog)){}
 bool select(const InstanceIdentity& id,CorpseDeathCause cause,std::string& error){
  if(cause!=CorpseDeathCause::StoneShatter||!validCorpseIdentity(id,mCatalog)){
   error="invalid original corpse death cause or activation identity";return false;
  }
  if(mStone.count(id)){error.clear();return true;}
  if(mStone.size()>=corpseSnapshotMaxRecords){error="original corpse death policy capacity exceeded";return false;}
  mStone.insert(id);error.clear();return true;
 }
 bool ordinaryAllowed(const InstanceIdentity& id)const{return validCorpseIdentity(id,mCatalog)&&!mStone.count(id);}
 std::size_t size()const{return mStone.size();}
private:
 std::string mCatalog;
 std::set<InstanceIdentity> mStone;
};
}
