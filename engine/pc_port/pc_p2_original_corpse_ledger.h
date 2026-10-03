#pragma once
#include "pc_p2_original_catalog.h"
#include <cstddef>
#include <functional>
#include <map>
#include <utility>
#include <vector>

namespace p2original {
// Identical runtime/save cap; consumed receipts count toward the bound.
constexpr std::size_t corpsePayloadMaxBytes=1024*1024;
constexpr std::size_t corpseSnapshotMaxRecords=(corpsePayloadMaxBytes-80)/33;
bool validCorpseIdentity(const InstanceIdentity&,const std::string& catalog);
// SAVE schema 1: only logical source identity and reward state. No native
// addresses, transient handles, actor liveness, treasures or Pokos are saved.
struct CorpseRecord {
 InstanceIdentity identity;
 unsigned sourceType=0, yield=0;
 bool consumed=false;
};
struct CorpseSnapshot {
 unsigned schema=1;
 std::string catalog;
 std::vector<CorpseRecord> records;
};
// Codec is bounded and structural, NOT authentication. The SAVE owner must
// authenticate the containing envelope and restore stock in the same transaction.
bool encodeCorpseSnapshot(const CorpseSnapshot&,std::vector<std::uint8_t>&,std::string&);
bool decodeCorpseSnapshot(const std::vector<std::uint8_t>&,CorpseSnapshot&,std::string&);

class CorpseLedger {
public:
 explicit CorpseLedger(std::string catalog):mCatalog(std::move(catalog)){}
 CorpseLedger(const CorpseLedger&)=delete;
 CorpseLedger& operator=(const CorpseLedger&)=delete;
 using Validator=std::function<bool(const CorpseRecord&,std::string&)>;
 // Caller verifies real resource/death creation and audited profile before birth.
 // No population is granted by birth, pointer binding, or restoration.
 bool birth(const void* pellet,const InstanceIdentity&,unsigned sourceType,unsigned yield,
            std::uint64_t& handle,std::string&);
 bool rebind(const void* pellet,const InstanceIdentity&,std::uint64_t& handle,std::string&);
 bool lookup(const void* pellet,std::uint64_t handle,CorpseRecord&)const;
 // Called only at successful ordinary Onion suction. Caller immediately applies
 // grant to stock; duplicate suction succeeds with grant=0. This is single-threaded.
 bool deliver(const void* pellet,std::uint64_t handle,unsigned& grant,std::string&);
 // Actor retirement has no effect. Pellet retirement removes only RAM binding;
 // consumed tombstones remain to prevent replay/address reuse rewards.
 bool forgetPellet(const void* pellet,std::uint64_t handle);
 CorpseSnapshot snapshot()const;
 // Fresh ledger only: no in-session checkpoint rewind. Validator MUST resolve
 // generator/ordinal in the catalog and compare source/yield to audited profile.
 // Caller authenticates envelope. Failure preserves this ledger unchanged.
 bool restore(const CorpseSnapshot&,const Validator&,std::string&);
private:
 struct Binding {std::uint64_t handle;InstanceIdentity identity;};
 bool bind(const void*,const InstanceIdentity&,std::uint64_t&,std::string&);
 std::string mCatalog;
 std::map<InstanceIdentity,CorpseRecord> mRecords;
 std::map<const void*,Binding> mPellets;
 std::uint64_t mNextHandle=1;
};
}
