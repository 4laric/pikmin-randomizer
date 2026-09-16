#pragma once

#include "pc_p2_bigtreasure.h"

// Lane-owned elemental damage receiver decision for the BigTreasure (Titan
// Dweevil, enemy ID 73) ordinary encounter, issue #246. Engine-free: it maps a
// confirmed elemental hit to the source stimulus, damage and (for elec) zap
// direction. The shared P2 Pikmin receivers (lane 10/11: InteractFire /
// InteractGas / InteractBubble / InteractDenki in interactBattle.cpp / navi.cpp)
// own the state mutation; this module names the exact stimulus so the engine
// host (pc_p2_hardlanes.cpp and the runtime fixture) can construct it.
//
// Source anchors (US GPVE01 rev 0, BigTreasureAttack.cpp at research revision
// 632af93787b9c95b63f0c13be32b161375ce3a96):
//   fire  : InteractFire  (attackDamage)                        :118
//   gas   : InteractGas   (attackDamage)                        :220
//   water : InteractBubble(0.0)                                 :315
//   elec  : InteractDenki (attackDamage, zapDir)                :470
// attackDamage is CG_GENERALPARMS(mOwner).mAttackDamage (include/Game/
// EnemyParmsBase.h 'fp24' "attack power", header default 10.0f, range 0..1000).

enum class P2BigTreasureReceiverStimulus {
    None = 0,
    Fire,
    Gas,
    Water,
    Elec,
};

const char* p2_bigtreasure_receiver_stimulus_name(P2BigTreasureReceiverStimulus stimulus);

// Boss elemental attack power used when the host has not yet wired the disc
// general-parameter table (EnemyParmsBase.h 'fp24' header default).
inline constexpr float kBigTreasureDefaultAttackDamage = 10.0f;

// One resolved elemental hit against a target position.
struct P2BigTreasureReceiverHit {
    P2BigTreasureReceiverStimulus stimulus = P2BigTreasureReceiverStimulus::None;
    float damage = 0.0f;            // attackDamage passthrough; 0 for water
    P2BigTreasureVec3 direction{};  // elec zap direction (|xz|=150, y=150); zero otherwise
};

// Resolves the source stimulus for the running element `weapon` against a hit
// `target`, from the boss base `origin`, with the boss elemental `attackDamage`.
// Elec direction is the source zap shape: horizontal (target - origin)
// normalised and scaled to the source 150 magnitude, raised to y = 150. The
// port receivers do not consume the direction (both actPiki and actNavi ignore
// it), so it is recorded for source parity rather than used for movement.
P2BigTreasureReceiverHit p2_bigtreasure_receiver_resolve(
    int weapon, const P2BigTreasureVec3& origin, float attackDamage,
    const P2BigTreasureVec3& target);
