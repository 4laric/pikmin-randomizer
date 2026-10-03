// Lane 48 (#486, cave wave #468): engine-facing real Candypop bud actor.
//
// Instantiates one actor per seeded ``kind=="bud"`` node in the live lane-44
// cave layout, then runs the ordinary throw/convert path: an airborne Pikmin
// inside the source slot radius (p2pom::SlotRadius, lane 23) is consumed and the
// bud births a real PikiHeadItem of the bud's colour, which is completed through
// the ordinary pluck (PikiHeadItem::interactBikkuri). No staged recolour or forced
// species write: the resulting live Pikmin gives the squad its colour key.
#pragma once

#include "Vector.h"
class Pom;

// Explicit WFG body profile suppresses legacy file-presence recognition even
// before final setup. Species queries authorize only this validated scene.
bool pc_p2_cave_bud_body_profile();
int pc_p2_cave_bud_body_species(const Pom*);
int pc_p2_cave_bud_body_remaining(const Pom*);
// Call only after an output was allocated and its input consumed.
void pc_p2_cave_bud_body_output(const Pom*, bool sameSpecies);
// Native Pom death only: retire an exhausted, empty body before manager reuse.
void pc_p2_cave_bud_body_retire(Pom*);

// True when at least one seeded bud actor was instantiated this run.
bool pc_p2_cave_bud_active();

// Number of seeded bud actors (0 when inactive).
int pc_p2_cave_bud_count();

void pc_p2_cave_bud_setup();
void pc_p2_cave_bud_shutdown();
void pc_p2_cave_bud_tick();

// Completed ordinary conversions (a live Pikmin was born from a bud).
int pc_p2_cave_bud_conversions();

// World position of the first actor of a colour ("yellow"/"blue"/...).
bool pc_p2_cave_bud_position(const char* colour, Vector3f& out);

// Conversion output still waiting for item-manager capacity.
bool pc_p2_cave_bud_pending();

// Snapshot conversion budgets at the same floor boundary as the squad.
bool pc_p2_cave_bud_save(const char* path);

// #1281 original source6 is per-body, never an opt-in to the WFG scene profile.
#include <string>
namespace p2original { struct InstanceIdentity; }
// All lookups prove active BossMgr membership before dereferencing Pom.
// Bind requires the exact originalActors() source6 identity/token already installed.
bool pc_p2_original_pom_preflight(std::string& error);
bool pc_p2_original_pom_bind(Pom*, const p2original::InstanceIdentity&, unsigned token, std::string& error);
bool pc_p2_original_pom_start(Pom*, std::string& error);
// Release is idempotent for an unbound body; safe during partial birth unwind.
// It revokes core authority only, never kills or releases a manager root.
bool pc_p2_original_pom_release(Pom*, std::string& error);
bool pc_p2_original_pom_pose(const Pom*, unsigned& motion, float& sourceFrame);
// Core dispatch: distinguishes owned-but-unready from unrelated P1/WFG bodies.
bool pc_p2_original_pom_managed(const Pom*);
bool pc_p2_original_pom_ready(const Pom*);
int pc_p2_original_pom_remaining(const Pom*); // -1 if not a ready source6 body
class Piki;
class PikiHeadItem;
class CollPart;
// Leaf supplies the actual source slot mouth; the core performs native swallow.
// Reservation is committed only on successful stimulation, once per donor.
bool pc_p2_original_pom_intake(Pom*, Piki*, CollPart* mouth);
class Creature;
void pc_p2_original_pom_touch(Pom*, Creature* collider);
bool pc_p2_original_pom_press(Pom*, Creature* donor, CollPart* hit);
bool pc_p2_original_pom_take_touch(Pom*);
bool pc_p2_original_pom_reserved(const Pom*, const Piki*);
int pc_p2_original_pom_pending(const Pom*);
// Called after actual successful head birth/initialization and donor consumption.
// Snapshot is read-only: it must not tombstone or commit an output. It may run
// again after capacity failure. Receipt format and durable identity belong to
// the body/floor owner, not this core. No donor pointer escapes the output event.
using PcOriginalPomDonorSnapshot = bool (*)(const Pom*, const p2original::InstanceIdentity&,
    unsigned token, const Piki* liveDonor, std::string& receipt, void* context);
using PcOriginalPomHeadCallback = void (*)(const Pom*, const p2original::InstanceIdentity&,
    unsigned token, unsigned outputOrdinal, PikiHeadItem*, bool refunded,
    const std::string& donorReceipt, void* context);
bool pc_p2_original_pom_set_head_callback(Pom*, PcOriginalPomDonorSnapshot, PcOriginalPomHeadCallback, void* context);
bool pc_p2_original_pom_snapshot(const Pom*, Piki*, std::string& donorReceipt);
void pc_p2_original_pom_output(const Pom*, const Piki* consumed, PikiHeadItem*, bool sameSpecies, const std::string& donorReceipt);
// Existing PomAi supplies motion changes, consumes actual source keys once,
// and retains its native transitions/conversion path. No rendering-driven ticks.
void pc_p2_original_pom_motion(Pom*, unsigned motion);
struct PcOriginalPomEvents { bool action=false, finished=false; };
PcOriginalPomEvents pc_p2_original_pom_advance(Pom*, float seconds);
