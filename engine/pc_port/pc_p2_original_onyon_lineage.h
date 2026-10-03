#pragma once
#include "pc_p2_original_piki_origin.h"
#include <cstdint>
#include <array>
#include <map>
#include <string>
#include <variant>
#include <vector>

namespace p2originalonyon {
constexpr std::size_t memberLimit=65536, liveHeadLimit=100, liveBodyLimit=100;
struct Root {
 std::string sessionFingerprint,sourceSha,sourceKey;
 std::uint32_t sourceUid=0;
 std::uint8_t species=0;
 std::uint64_t incarnation=0;
 bool operator==(const Root&)const;
};
enum class CauseKind : std::uint8_t { Corpse=1, Number=2 };
enum class AncestryKind : std::uint8_t { None=0, TamagoMushi=68, ShijimiChou=77 };
struct SeedCause {
 CauseKind kind=CauseKind::Corpse;
 std::string catalogFingerprint;
 std::uint32_t sourceUid=0,sourceType=0,ordinal=0;
 std::uint64_t epoch=0,activation=0;
 // Resource producers retain the real parent sourceType separately from the
 // emitted 68/77 member kind. Direct numeric children use slot0/1; emitted
 // member children use slot0, emissionOrdinal0, member<10 or member<5.
 // Corpse causes have no numeric child/ancestry fields.
 std::uint32_t numericChildSlot=0;
 AncestryKind ancestry=AncestryKind::None;
 std::uint64_t emissionOrdinal=0;
 std::uint32_t member=0;
 bool operator==(const SeedCause&)const;
 bool operator<(const SeedCause&)const;
};
struct OnyonEmission {Root root;std::uint64_t memberSerial=0;SeedCause cause;std::uint32_t seedOrdinal=0;};
using MemberOrigin=std::variant<OriginalPikiBody,OnyonEmission>;
struct MemberBodyState {std::uint8_t species=0,maturity=0;bool wild=false,wasWild=false;};
enum class Location : std::uint8_t {Pending,Head,Body,Stored,Dead};
struct MemberRecord {
 std::uint64_t serial=0;
 std::string sessionFingerprint;
 MemberOrigin origin;
 MemberBodyState state;
 Location location=Location::Pending;
 // Stored stock is global(session,species). This is the last actual physical
 // receiver proof; it never replaces the immutable birth origin.
 Root receiverRoot;
 bool hasReceiver=false;
};
struct RewardPlan {Root root;SeedCause cause;std::uint32_t count=0;std::uint64_t firstSerial=0;};
enum class QueryResult {Missing,Present,Unavailable};
enum class StockResult {Empty,Present,Unavailable};
struct Report {
 std::string sessionFingerprint;
 std::vector<MemberRecord> members;
 std::uint64_t unknownStock[3]={0,0,0};
 std::size_t liveHeads=0,liveBodies=0;
};
// Single-threaded pure provenance state only. Native wrappers authenticate roots/causes,
// establish actual allocation/deposit facts, and enforce combined field limits.
// No native objects, RNG, stock counts, AP gates, SAVE authentication or codec.
// Null allocations and every bool refusal leave state and outputs unchanged.
class Lineage {
public:
 explicit Lineage(std::string sessionFingerprint);
 const std::string& sessionFingerprint()const noexcept{return mSession;}
 Lineage(const Lineage&)=delete;
 Lineage& operator=(const Lineage&)=delete;
 bool preflightReward(const Root&,const SeedCause&,std::uint32_t count,RewardPlan&,std::string&)const;
 bool commitReward(const RewardPlan&,std::string&);
 bool nextPending(const Root&,std::uint64_t& serial,std::string&)const;
 bool bindPendingHead(std::uint64_t serial,const Root&,const void* head,std::uint64_t& handle,std::string&);
 bool storePending(std::uint64_t serial,const Root&,std::string&);
 bool adoptAuthored(const std::string& currentSession,const OriginalPikiBody&,std::uint8_t maturity,const void* body,std::uint64_t& serial,std::uint64_t& handle,std::string&);
 bool headToBody(const void* head,std::uint64_t headHandle,const void* body,std::uint64_t& bodyHandle,std::string&);
 bool depositBody(const void* body,std::uint64_t handle,const Root& actualReceiver,std::string&);
 // Highest maturity, then oldest member serial (deliberate FIFO policy).
 StockResult peekStored(std::uint8_t species,MemberRecord&,std::string&)const;
 bool storedCounts(std::uint8_t,std::array<std::uint64_t,3>&)const noexcept;
 bool withdrawStored(std::uint64_t selectedSerial,const Root& actualReceiver,const void* successfullyBornBody,std::uint64_t& handle,std::string&);
 bool updateBody(const void*,std::uint64_t,const MemberBodyState&,std::string&);
 // Post-deposit/head-conversion/death cleanup is idempotent when no pointer
 // binding remains. A reused live pointer still requires its current handle.
 bool retireHead(const void*,std::uint64_t,std::string&);
 bool retireBody(const void*,std::uint64_t,std::string&);
 QueryResult queryHead(const void*,const std::string& currentSession,MemberRecord&,std::uint64_t& handle,std::string&)const;
 QueryResult queryBody(const void*,const std::string& currentSession,MemberRecord&,std::uint64_t& handle,std::string&)const;
 // Persistent label readers never copy records/strings or allocate; ownership
 // is still true when authenticated record queries report Unavailable.
 bool ownsBody(const void*)const noexcept;
 bool ownsHead(const void*)const noexcept;
 bool bodyHandle(const void*,std::uint64_t& out)const noexcept;
 // Actual teardown only, after party observers consume the living graph.
 // This is death/history retirement, never stock deposit or SAVE restoration.
 void retireSceneBodies() noexcept;
 bool markUnknownStock(std::uint8_t species,std::uint64_t count,std::string&);
 Report report()const;
 // Read-only early teardown guard. HEAD/pending graphs must remain intact
 // before provider disposal. BODY retirement follows the Party observer.
 bool preflightCourseFinish(std::string&)const;
 bool courseUnload(std::string&)const;
 // Explicit new campaign only. Refuses living graph or pending queue. Stored
 // members/dead history are reset only here, never on ordinary course unload.
 bool newSession(const std::string&,std::string&);
private:
 struct Binding {std::uint64_t serial=0,handle=0;};
 struct AuthoredKey {
  std::string catalog,key;std::uint32_t uid=0,attempt=0;std::uint64_t activation=0;
  bool operator<(const AuthoredKey&)const;
 };
 bool rootValid(const Root&)const;
 bool attach(std::uint64_t,const void*,bool,std::uint64_t&,std::string&);
 QueryResult query(const std::map<const void*,Binding>&,const void*,const std::string&,MemberRecord&,std::uint64_t&,std::string&)const;
 bool retire(std::map<const void*,Binding>&,const void*,std::uint64_t,std::string&);
 std::string mSession;
 std::map<std::uint64_t,MemberRecord> mMembers;
 std::map<SeedCause,std::uint32_t> mRewards;
 std::map<AuthoredKey,std::uint64_t> mAuthored;
 std::map<const void*,Binding> mHeads,mBodies;
 std::uint64_t mNextSerial=1,mNextHandle=1,mUnknown[3]={0,0,0};
};
}
