#pragma once
#include <cstdint>
class Piki;
class Creature;
class CollPart;

// Narrow Sarai (Swooping Snitchbug, ID 23) Pikmin mouth-capture engine bridge.
// The private P2SaraiHost owns two live mouth CollParts (rkamujnt/lkamujnt) but
// is not a registered P1 teki, so captured Pikmin stick directly to those
// parts via Creature::startStickMouth. This bridge tracks, per Piki*, which
// host/mouth/slot currently carries it, so carry, drop (FallMeck) and escape
// (Flick) are exactly-once and address-reuse safe. Mirrors pc_demon_bridge.*
// for the Demon captain, extended to two Pikmin slots.
//
// Ownership is a host-owned generation token, not a pointer. The host must
// invalidate it (owner_lost / scene_exit) before its mouth parts are disposed.
bool pc_p2_sarai_piki_capture(Piki* piki, Creature* owner, CollPart* mouth,
                              std::uint64_t ownerToken, unsigned slot);
bool pc_p2_sarai_piki_bound(const Piki* piki);
bool pc_p2_sarai_piki_owned_by(const Piki* piki, Creature* owner);
// Returns the bound mouth slot, or -1 when this Pikmin is not mouth-captured.
int pc_p2_sarai_piki_slot(const Piki* piki);
// Grounded release: detach without damage (usually Fall descent / teardown).
bool pc_p2_sarai_piki_release(Piki* piki);
// fallMeckGround(): InteractFallMeck (damage) + downward setVelocity(-speed)
// for every Pikmin mouth-captured by `owner`. Returns the number released.
unsigned pc_p2_sarai_drop_owned(Creature* owner, float damage, float downSpeed);
// flickStickTarget(): InteractFlick(knockback, 0) for every Pikmin
// mouth-captured by `owner` (escape, no damage). Returns the number detached.
unsigned pc_p2_sarai_flick_owned(Creature* owner);
unsigned pc_p2_sarai_carried_count(Creature* owner);
// Before manager/heap invalidation, while creature links are live.
void pc_p2_sarai_owner_lost(std::uint64_t ownerToken);
void pc_p2_sarai_scene_exit();
void pc_p2_sarai_forget();
