#pragma once
#include <cstdint>
#include <string>
#include <vector>
class Piki;
struct OriginalPikiOrigin {
 std::string sourceKey;
 // Synthetic external catalog UID, distinct from retail/runtime UID0.
 // No native Generator is fabricated for a source GenPiki body.
 std::uint32_t recordUid=0,attempt=0;
 std::uint64_t activation=0;
 std::string catalogFingerprint;
};
// uid is originalSourceCatalogUid(sourceKey), not the retail Piki UID.
struct OriginalPikiSource {std::string sourceKey;std::uint32_t uid=0,count=0;std::uint8_t species=0;};
// Full immutable Piki catalog, including currently inactive calendar members.
// Install only before births/after old scene associations have been forgotten.
bool pc_p2_original_piki_origin_install(const std::string& fingerprint,const std::vector<OriginalPikiSource>&,std::string& error);
// Called ONLY after a successful original source birth, never ordinary P1 birth.
bool pc_p2_original_piki_origin_associate_birth(Piki*,const OriginalPikiOrigin&);
bool pc_p2_original_piki_origin_query(const Piki*,OriginalPikiOrigin& out);
bool pc_p2_original_piki_origin_restore_saved(Piki*,const OriginalPikiOrigin&);
void pc_p2_original_piki_origin_forget(Piki*);
// After scene consumers retire their provenance and before the actor heap is
// released. Clear live pointers only; keep catalog and consumed member history.
void pc_p2_original_piki_origin_scene_exit() noexcept;
// Cave owns the authenticated selected-checkpoint/transaction proof. This is
// false outside committed teardown or scoped physical party restoration. An
// older selected SAVE is permitted: current-scene death is not global permadeath.
bool pc_p2_cave_campaign_survivor_permit(const std::string& sourceKey,std::uint32_t recordUid,std::uint32_t attempt,std::uint64_t activation,const std::string& catalogFingerprint,std::uint64_t* generation,std::uint8_t sha[32]);

// Successful canonical association notifies the party consumer transactionally.
bool pc_p2_cave_campaign_party_associate_birth(Piki*,const char*,std::uint32_t,std::uint32_t,std::uint64_t,const char*);

// Original-source logical body flags are independent of P1 FreeMode/AP access.
// Source setZikatu(true) sets both bits; recruitment clears only wild.
struct OriginalPikiBodyState {
 std::uint8_t species=0;
 bool wild=false,wasWild=false;
};
struct OriginalPikiBody {
 OriginalPikiOrigin origin;
 OriginalPikiBodyState state;
};
bool pc_p2_original_piki_body_associate_birth(Piki*,const OriginalPikiBody&);
// Unlabelled P1 / legacy origin-only associations return false unchanged.
bool pc_p2_original_piki_body_query(const Piki*,OriginalPikiBody& out);
bool pc_p2_original_piki_body_restore_saved(Piki*,const OriginalPikiBody&);
// Call only after actual accepted RGB source recruitment, never on an attempt.
bool pc_p2_original_piki_body_recruited(Piki*);
// Cave-owned authenticated selected living body, not a tuple-only ticket. All
// outputs unchanged on refusal; checkpoint proof matches the selected body.
bool pc_p2_cave_campaign_survivor_body(const std::string& sourceKey,
 std::uint32_t recordUid,std::uint32_t attempt,std::uint64_t activation,
 const std::string& catalogFingerprint,OriginalPikiBodyState& state,
 std::uint64_t* generation,std::uint8_t sha[32]);

// Read-only source admission before a physical birth; exact member/species,
// fresh flags and no current live association. No native allocation or RNG.
bool pc_p2_original_piki_body_birth_admit(const OriginalPikiBody&);
bool pc_p2_original_piki_body_wild(const Piki*) noexcept;

// Exact-body RGB bind scope for an authenticated selected Cave survivor. It
// neither resets Piki::init/FSM nor consumes RNG nor unlocks an AP color globally.
class PcOriginalPikiSavedColorScope {
public:
 explicit PcOriginalPikiSavedColorScope(Piki*);
 ~PcOriginalPikiSavedColorScope();
 PcOriginalPikiSavedColorScope(const PcOriginalPikiSavedColorScope&)=delete;
 PcOriginalPikiSavedColorScope& operator=(const PcOriginalPikiSavedColorScope&)=delete;
 bool valid() const noexcept{return mActive;}
private:
 Piki* mBody=nullptr;
 OriginalPikiBody mSelected;
 std::uint64_t mGeneration=0;
 std::uint8_t mSha[32]={};
 bool mActive=false;
 friend bool pc_p2_original_piki_saved_color_held(const Piki*,int) noexcept;
};
bool pc_p2_original_piki_saved_color_held(const Piki*,int baseColor) noexcept;
// Reapply only the existing source body's canonical base color (e.g. ending
// mushroom tint). Caller additionally requires color==native current mColor.
bool pc_p2_original_piki_body_color_access(const Piki*,int baseColor) noexcept;

// Bootstrap-only read view of the successfully installed immutable catalog.
const std::string& pc_p2_original_piki_catalog_fingerprint() noexcept;

// Durable ancestry is body.origin (literal successful attempt index, not a
// shared generator UID or positional guess). Native lifetime is a monotonic
// actual association incarnation, process-local and retired before pool reuse.
// A fresh process resolves saved durable ancestry to its new native handles.
struct OriginalPikiBodyHandle {OriginalPikiBody body;std::uint64_t nativeLifetime=0;};
bool pc_p2_original_piki_body_handle(const Piki*,OriginalPikiBodyHandle&);
bool pc_p2_original_piki_body_current(const Piki*,std::uint64_t)noexcept;
