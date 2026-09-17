#pragma once

#include <cstddef>
#include <cstdint>

// Real Pom actor-birth provider for Candypop buds 3-8 (issue #448).
// Lane shard-enemies-1-pom-actor-provider.
//
// Adjudicated facts (read-only, see docs/PIKMIN2_POM_ACTOR_PROVIDER.md):
//   * Generator records name a colored id 3..8 (`EFlag_CanBeSpawned`,
//     no `UseOwnID`); the manager resolves to parent `EnemyID_Pom`
//     (`enemyInfo.h:204`).
//   * The base `Pom` (82) itself is not spawnable ("crashes"); it must
//     be REFUSED fail-closed, never invented into a spawnable base.
//   * The port has no Pom manager/teki reference, so this provider owns
//     the birth RECORD lifecycle behind a seam (mirroring the accepted
//     #577 Bomb payload provider shape). The lane-23 Chappy proxy vehicle
//     (pc_p2_pom.cpp) is untouched; real in-game birth is deferred to a
//     follow-on and needs a shared-owner engine change (teki birth path).
//
// Engine-free boundary: this header and its .cpp compile with -Ipc_port
// only (cstdint/cstddef/cstdio). This module never enumerates creatures,
// never touches a manager, and prints nothing: markers are FORMATTED into
// caller buffers for the host to log, so no fake log evidence is possible
// from here. Nothing here claims gate-1 runtime closure.

// Colored Candypop-bud source ids; the base Pom id is never spawnable.
static const std::uint32_t P2_POM_SOURCE_FIRST = 3;
static const std::uint32_t P2_POM_SOURCE_LAST = 8;
static const std::uint32_t P2_POM_BASE_ID = 82;
static const std::uint32_t P2_POM_PARENT_ID = 82;

// Record bound to one generator: colored source resolved via the
// parent-id rule. A record never names the base as spawnable.
struct P2PomActorRecord {
    std::uint32_t generator = 0;
    std::uint32_t source_id = 0;
    std::uint32_t parent_id = P2_POM_PARENT_ID;
};

// Generational handle. generation==0 is never issued and always invalid,
// so slot reuse can never resurrect a stale handle.
struct P2PomActorHandle {
    std::uint32_t slot = 0;
    std::uint32_t generation = 0;
};

bool p2_pom_actor_handle_valid(P2PomActorHandle handle);
bool p2_pom_actor_source_colored(std::uint32_t source_id);
bool p2_pom_actor_is_base(std::uint32_t source_id);

// Fail-closed resolution: true with parent_id=82 only for colored ids
// 3..8. Base 82 and every other id resolve false (never invent a base).
bool p2_pom_actor_resolve(std::uint32_t generator, std::uint32_t source_id,
                          P2PomActorRecord* out);

enum class P2PomActorPhase { Free, Bound, Born };

// Single-use binding with recycle-safe generations. Birth is RECORDED,
// never executed: the real engine-actor birth plugs into the
// P2PomActorBirthSeam (host manager births through its own manager and
// hands this pool the generator token plus the resolved record).
static const std::uint32_t P2_POM_ACTOR_POOL = 8;

struct P2PomActorSlot {
    P2PomActorPhase phase = P2PomActorPhase::Free;
    std::uint32_t generation = 0;
    P2PomActorRecord record = P2PomActorRecord();
};

struct P2PomActorPool {
    P2PomActorSlot slots[P2_POM_ACTOR_POOL];
};

void p2_pom_actor_pool_init(P2PomActorPool* pool);
// Binds one record to a free slot; single-use: a second bind of the same
// generator while bound fails. Returns an invalid handle on failure.
P2PomActorHandle p2_pom_actor_bind(P2PomActorPool* pool,
                                   const P2PomActorRecord* record);
// Records the deferred-birth marker for a bound handle; exactly-once:
// a second birth on the same binding fails.
bool p2_pom_actor_record_birth(P2PomActorPool* pool, P2PomActorHandle handle);
// Releases a binding; the slot generation advances so stale handles stay
// invalid (recycle-safe).
bool p2_pom_actor_release(P2PomActorPool* pool, P2PomActorHandle handle);

// Marker grammar (reuses the adjudication names):
//   P2_POM_ACTOR_BIRTH generator=<g> source_id=<3..8> parent_id=82
//   P2_POM_BASE_REJECTED generator=<g> source_id=82
// Returns the formatted length excluding NUL, or -1 when truncated.
int p2_pom_actor_format_birth(char* out, std::size_t capacity,
                              const P2PomActorRecord* record,
                              P2PomActorHandle handle);
int p2_pom_actor_format_base_refusal(char* out, std::size_t capacity,
                                     std::uint32_t generator);
