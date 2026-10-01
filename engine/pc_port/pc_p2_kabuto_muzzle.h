#pragma once

#include "pc_p2_attachments.h"
#include "pc_p2_kabuto_cannon.h"

#include <cstdint>

// Isolated per-species Kabuto/Rkabuto/Fkabuto moving-muzzle provider (lane 20,
// #169 / #424 / #425). It connects the shared animated-attachment bank
// (`pc_p2_attachments.h`) to the committed Cannon Beetle fire FSM
// (`pc_p2_kabuto_cannon.h`): the FSM decides *when* to fire and owns the Stone
// birth semantics; this module resolves the species' attack clip and mouth
// joint, samples the joint world position at the source KEYEVENT_2 frame, and
// consumes the pending FireStone into a `P2KabutoStoneBirth`.
//
// The source birth (Kabuto.cpp:268-290) places the Stone at the world mouth
// joint + (0, 25, 0) and aims it along the enemy's facing, not the joint axis.
// So the muzzle supplies only the moving mouth position; `faceDir` stays the
// host actor's facing and is passed through to `P2KabutoCannon::takeBirth`.
// This replaces the static configured mouth point used by the private host seam
// (`pc_p2_projectiles.cpp` `kabutoMouthJoint`).
//
// Source (US GPVE01 rev 0) `enemyanimmgr.txt`: the surfaced `attack` clip fires
// at frame 50 (KEYEVENT_2); buried Fkabuto uses `K_attack` at frame 55. The
// packed retail `anim.szs` stores the buried clips lowercased (`k_attack.bca`),
// so clip resolution falls back to a case-insensitive match. The mouth joint is
// the source `kuti` joint; the exact bank joint name is confirmed by the family
// from the extracted BMD, and an unresolved clip/joint fails closed.
//
// This file has no engine, creature, map, sound or effect dependency and adds
// no shared hooks. It consumes the same immutable bank as a bound
// `p2attach::Instance`; clip/joint indices are bank-local, so the muzzle and the
// instance must be bound to the same bank.

struct P2KabutoMouthClip {
    const char* clip = "";  // source clip name (enemyanimmgr.txt)
    const char* joint = ""; // source mouth joint name
    int fireFrame = 0;      // KEYEVENT_2 frame inside that clip
};

// Source-authoritative descriptor for one species. Kabuto and Rkabuto share the
// surfaced `attack` clip; Fkabuto uses the buried `K_attack` clip.
const P2KabutoMouthClip& p2_kabuto_mouth_clip(P2KabutoSpecies species);

// Cached resolution of a descriptor against a bound bank. Indices are bank-local.
struct P2KabutoMouthBinding {
    int clip = -1;
    int joint = -1;
    int fireFrame = 0;
    bool valid() const { return clip >= 0 && joint >= 0 && fireFrame >= 0; }
};

// Resolve the species descriptor against `bank`: exact clip/joint name first,
// then a case-insensitive match (the shipped buried clips are lowercased). The
// fire frame must be a valid frame of the resolved clip. Fails closed (returns
// false and leaves `out` invalid) on any missing name or out-of-range frame.
bool p2_kabuto_mouth_resolve(const p2attach::Bank& bank, P2KabutoSpecies species,
                             P2KabutoMouthBinding& out);

class P2KabutoMuzzle {
public:
    // Resolve and cache the species descriptor against `bank`. The attachment
    // Instance used with this muzzle must be bound to the same bank.
    bool bind(const p2attach::Bank& bank, P2KabutoSpecies species);

    bool valid() const { return mBinding.valid(); }
    const P2KabutoMouthBinding& binding() const { return mBinding; }

    // Sample the bound bank at the fire frame and report the mouth joint's world
    // position. `owner` is the actor-to-world transform; `tick` must be
    // non-decreasing per the shared attachment contract. Returns false and
    // writes nothing on an unresolved binding or a rejected sample.
    bool sampleMouth(p2attach::Instance& instance, p2attach::Token token,
                     const p2attach::Affine& owner, std::uint64_t tick,
                     p2attach::Vec& out) const;

    // `sampleMouth` then `P2KabutoCannon::takeBirth`. Requires that the FSM has a
    // pending FireStone; returns false without mutating the muzzle otherwise.
    bool takeBirth(P2KabutoCannon& cannon, p2attach::Instance& instance,
                   p2attach::Token token, const p2attach::Affine& owner,
                   std::uint64_t tick, float faceDir, P2KabutoStoneBirth& out) const;

private:
    P2KabutoMouthBinding mBinding;
};
