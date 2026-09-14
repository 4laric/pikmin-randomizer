#pragma once

#include "pc_p2_bombsarai_bomb.h"

// Isolated blast receiver routing policy for the BombSarai lane, mirroring
// the source detonation volume and attribution rules
// (src/plugProjectMorimuraU/bombState.cpp:140-198 at revision
// 632af93787b9c95b63f0c13be32b161375ce3a96) plus the dirigibug's own
// bomb-immunity callback (src/plugProjectNishimuraU/BombSarai.cpp:127-135).
//
// The host enumerates candidate receivers (cell-iterator equivalent) and
// owns the actual InteractBomb stimulation; this policy only classifies and
// attributes. The source volume is a CellIterator sphere plus an explicit
// vertical gate; the policy applies an exact 3D sphere test, which is at
// least as strict as the source's cell granularity — documented as a
// host-visible approximation, not Pikmin 2 collision parity.

enum class P2BombSaraiReceiverKind { Teki, Navi, Piki };

struct P2BombSaraiReceiver {
    std::uint64_t id = 0;
    P2BombSaraiVec3 position;
    P2BombSaraiReceiverKind kind = P2BombSaraiReceiverKind::Teki;
    bool alive = true;
    // Receiver-side bomb callback contract: a Careening Dirigibug takes
    // explosion damage only while grounded (mFloorTriangle, bombCallBack).
    // Set airborneBombImmune for receivers with that callback (the carrier
    // and any other dirigibug); grounded selects the source's floor branch.
    bool airborneBombImmune = false;
    bool grounded = true;
};

struct P2BombSaraiRoutedHit {
    std::uint64_t receiverId = 0;
    P2BombSaraiReceiverKind kind = P2BombSaraiReceiverKind::Teki;
    float damage = 0.0f;
    // Teki hits carry the source's zero direction (no knockback);
    // Navi/Pikmin hits carry the source separation knockback:
    // normalizeXZ(receiver - center) * weight with y = weight
    // (bombState.cpp:174-186), weight 100 Navi / 200 Pikmin.
    P2BombSaraiVec3 knockback;
    // Attribution: Teki hits are always attributed to the bomb itself
    // (source passes the bomb as attacker, :163). Navi/Pikmin hits carry the
    // carrier token only when the blast recorded a confirmed-live carrier;
    // otherwise attributeToSelf mirrors the source mCarrier==nullptr
    // fallback (:167-172) and the stale-mCarrier policy decision.
    std::uint64_t attackerToken = 0;
    bool attributeToSelf = true;
};

// Routes one recorded blast against a candidate list. Returns the number of
// hits written (up to outCapacity), or -1 on invalid input. The bomb itself
// is never a candidate — the host must not list it (source excludes
// creature == enemy, :156).
int p2_bombsarai_route_blast(const P2BombSaraiBlastEvent& blast,
                             const P2BombSaraiReceiver* receivers, int receiverCount,
                             P2BombSaraiRoutedHit* out, int outCapacity);
