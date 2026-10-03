#pragma once
#include "pc_p2_original_catalog.h"
#include "pc_p2_original_checkpoint_graph.h"
#include <memory>
#include <map>
#include <set>
class Pom;class Piki;class PikiHeadItem;
namespace p2budorigin {
struct Creation;
// Floor owner supplies the actual selected source6 incarnation. This is NOT a
// GenPiki record, and the native Pom UID is not replaced by a generated hash.
struct FloorIdentity {
 std::string campaign,session,cave,visit,sourceSha,catalogSha,layoutSha,instance;
 unsigned floor=0,row=0,ordinal=0;
 std::uint64_t epoch=0,activation=0;
 bool operator==(const FloorIdentity&)const;
};
struct Identity {
 FloorIdentity floor;
 p2original::InstanceIdentity bud;
 unsigned emission=0;
 bool operator==(const Identity&)const;
 bool operator<(const Identity&)const;
};
// Donor references come from the actual body/party authority while it is alive.
// logical contains that authority's canonical durable key, never an address.
enum class DonorKind:unsigned { GenPiki=1,BudConversion=2,Party=3 };
struct Donor {DonorKind kind=DonorKind::Party;std::string campaign,logical;unsigned species=0;bool operator<(const Donor&)const;};
struct Record {Identity identity;Donor donor;unsigned species=0;bool refunded=false;};
enum class Lifecycle:unsigned { Head=1,Body=2,Retired=3 };
struct Entry {Record record;Lifecycle lifecycle=Lifecycle::Head;};
struct Snapshot {std::string campaign,session;std::vector<Entry> emissions;};
struct HeadBinding {Identity identity;PikiHeadItem* head=nullptr;};
struct BodyBinding {Identity identity;Piki* body=nullptr;};
bool valid(const FloorIdentity&) noexcept;
bool valid(const Identity&) noexcept;
bool valid(const Donor&) noexcept;
bool encode(const Record&,std::string&,std::string&);
bool decode(const std::string&,Record&,std::string&);
bool encodeSnapshot(const Snapshot&,std::string&,std::string&);
bool decodeSnapshot(const std::string&,Snapshot&,std::string&);
// Owner implementation MUST call actual SelectedFloorAuthority::expectedBirth,
// recheck native selected family/card/session on every call, and verify the live
// actual Pom source6 registry/token. There is no accepting default. Caller owns
// this authority until sceneExit, and no authority pointer enters saved bytes.
class Authority:public p2originalcheckpoint::ProofSource {
public:
 // Fresh/RAM native creation is separate from selected saved-card proof.
 // Defaults refuse so old/cold-only implementations cannot silently authorize.
 virtual bool creation(Creation&,std::string&)const{return false;}
 virtual const Creation* liveCreation()const noexcept{return nullptr;}
 virtual bool carried(const Snapshot&,const std::vector<BodyBinding>&,std::string&)const{return false;}
 virtual bool receive(const Snapshot&,const std::vector<BodyBinding>&,std::string&)const{return false;}
 virtual bool context(std::string& campaign,std::string& session,std::string&)const=0;
 virtual bool bud(const Pom*,unsigned token,const p2original::InstanceIdentity&,
                  FloorIdentity&,std::string&)const=0;
 virtual bool donor(const Piki*,Donor&,std::string&)const=0;
 // Recheck the actual selected floor/body family record for each live lookup.
 // The parent bud may have died; its successful output is still a distinct body.
 virtual bool record(const Record&,std::string&)const=0;
 // Nonallocating native owner check of the same selected full-card proof and
 // current owned floor/scene serial. No provider-created attestation accepted.
 virtual bool stillCurrent(const p2originalcheckpoint::Proof&)const noexcept=0;
 // Actual native reader must compare the complete selected family bytes and
 // generation/full SHA; ledger metadata alone never authorizes a restore.
 virtual bool saved(const Snapshot&,const p2originalcheckpoint::Proof&,std::string&)const=0;
};
class Registry;
class Carry {
 struct Impl;std::unique_ptr<Impl> impl;friend class Registry;
public:
 Carry();~Carry();Carry(Carry&&)noexcept;Carry&operator=(Carry&&)noexcept;
 Carry(const Carry&)=delete;Carry&operator=(const Carry&)=delete;
 bool ready()const noexcept;
};
// Allocate all provenance bookkeeping BEFORE native donor consumption. Pending
// output is reversible; it commits neither donor tombstone nor output identity.
class PendingEmission {
 struct Impl;std::unique_ptr<Impl> impl;friend class Registry;
public:
 PendingEmission();~PendingEmission();
 PendingEmission(PendingEmission&&)noexcept;PendingEmission&operator=(PendingEmission&&)noexcept;
 PendingEmission(const PendingEmission&)=delete;PendingEmission&operator=(const PendingEmission&)=delete;
 bool ready()const noexcept;
 unsigned ordinal()const noexcept;
};
class Registry {
 friend class PendingEmission;
 friend class Carry;
 struct State;std::shared_ptr<State> state;
public:
 Registry();~Registry();Registry(const Registry&)=delete;Registry&operator=(const Registry&)=delete;
 bool bind(const Authority&,const p2originalcheckpoint::Proof&,std::string&);
 bool bindLive(const Authority&,std::string&);
 // Actual committed RAM transition only. Owner must confirm the COMPLETE live
 // converted census/dispositions; bodies omitted from carried must actually
 // retire, not merely unload into another saved floor graph. Such retained
 // floors require their separate full graph owner, not this party-only path.
 bool detachCarry(const std::vector<BodyBinding>&,Carry&,std::string&);
 // Empty destination registry, actual new native owner/serial and complete
 // carried mapping. No emission/pluck/source activation or cold-card proof.
 bool receiveCarry(const Authority&,Carry&,const std::vector<BodyBinding>&,std::string&);
 bool prepare(const Pom*,unsigned token,const p2original::InstanceIdentity&,const Piki* donor,
              unsigned species,bool refunded,PendingEmission&,std::string&);
 // Only the producer calls this AFTER successful real head init and actual
 // donor consumption. Same-colour refund still adopts a real emitted head.
 bool adopt(PendingEmission&&,PikiHeadItem*,unsigned actualOrdinal,unsigned actualSpecies,bool actualRefund,const char*& reason)noexcept;
 bool head(const PikiHeadItem*,Record&)const;
 bool body(const Piki*,Record&)const;
 bool admitted(const Record&,std::string&)const;
 bool prepareTransfer(PikiHeadItem*,unsigned actualSpecies,PendingEmission&,std::string&);
 bool adoptBody(PendingEmission&&,Piki*,const char*& reason)noexcept;
 void forget(const PikiHeadItem*)noexcept;void forget(const Piki*)noexcept;
 void sceneExit()noexcept;
 // Exact selected native checkpoint proof, no ordinary emission/activation.
 bool snapshot(Snapshot&,std::string&)const;
 // AFTER real native SAVE succeeds, adopt only its selected proof and exact
 // unchanged family bytes. Failed SAVE/new graph/older rollback cannot use this.
 bool adoptSelected(const Authority&,const Snapshot&,const p2originalcheckpoint::Proof&,std::string&);
 // Restore only into an EMPTY provisional registry. ALL saved head/body
 // bindings and terminal histories are required before one atomic publication.
 bool restore(const Authority&,const Snapshot&,const p2originalcheckpoint::Proof&,
              const std::vector<HeadBinding>&,const std::vector<BodyBinding>&,std::string&);
 void swap(Registry&)noexcept;
};
Registry& registry();
}
