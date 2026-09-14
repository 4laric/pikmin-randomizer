#pragma once

// Lane 31 (#443 / parent #175): engine-free combat rules for the Waterwraith
// (99 BlackMan) / Tyre (98) owned encounter. This header carries only the
// selection/acceptance rules; the engine-facing side effects (stimulating real
// Pikmin and routing damage into `p2_waterwraith_actor_apply_damage`) live in
// pc_p2_waterwraith_register.cpp. Keeping the rules here lets a warning-clean
// standalone fixture exercise them without engine objects.
//
// Source anchors (US GPVE01 rev 0, research rev 632af937):
//  - The riding roller is not damageable except while frozen; after the wraith
//    dismounts (EB_Invulnerable) the exposed body stays damageable
//    (tyreState.cpp:67-69, :152-153, blackMan.cpp:672-681). Only Purple hits
//    are accepted; this is enforced structurally by
//    `p2_waterwraith_actor_apply_damage`.
//  - Tyre general key fp24 attack damage is 10; the roll-over contact is the
//    P1 host's closest analogue to the source roller attack (the retained
//    source attack callback is out of scope, see the assets audit sec.0).
//  - Radii and the per-hit Purple damage are lane adaptations (the source
//    collision parts are not representable on this host); they are recorded as
//    approximations, not retail values.

namespace p2wwatk {

struct Target {
    float x = 0.0f;
    float z = 0.0f;
    bool purple = false;
    bool alive = false;
};

struct Rule {
    float stunRadius = 150.0f;    // Purple landing stun trigger (adaptation)
    float hitRadius = 120.0f;     // Purple direct-hit acceptance (adaptation)
    float crushRadius = 90.0f;    // roll-over contact (adaptation)
    float purpleHitDamage = 60.0f; // per accepted Purple hit (adaptation)
    float crushKnockback = 100.0f; // InteractFlick intensity (adaptation)
    float crushDamage = 10.0f;     // Tyre general fp24
};

enum ActionFlags : unsigned {
    ActionNone = 0u,
    ActionStun = 1u << 0,  // a Purple is in stun range while not damageable
    ActionHit = 1u << 1,   // >=1 Purple in hit range while damageable
    ActionCrush = 1u << 2, // >=1 non-Purple in crush range while rolling
};

struct Evaluation {
    unsigned actions = ActionNone;
    int purpleHits = 0;   // Purple targets in hit range (one accepted hit each)
    int crushTargets = 0; // non-Purple targets in crush range
};

inline bool inRange(float ax, float az, float bx, float bz, float radius)
{
    const float dx = ax - bx;
    const float dz = az - bz;
    return dx * dx + dz * dz <= radius * radius;
}

// Pure rules.
//  `attached`   : the single Tyre child is present and owned by the wraith.
//  `damageable` : the rig vulnerability gate is open (frozen riding, or after
//                 the wraith dismounted).
//  `rolling`    : the wraith is moving with the rollers (crush applies only
//                 then; a frozen roller is static and does not crush).
//
// A Purple target in stun range while the rig is closed sets ActionStun; the
// caller turns that into a roller quakeFreeze edge (once). While the rig is
// damageable, each Purple in hit range is one accepted hit. Non-Purple targets
// never stun or damage; they are only crushed while rolling.
inline Evaluation evaluate(const Rule& rule, float rollerX, float rollerZ, bool attached,
                           bool damageable, bool rolling, const Target* targets, int count)
{
    Evaluation result;
    if (!attached) {
        // Dismounted: the exposed body can still take Purple hits, but there is
        // no roller to stun or to crush with.
        for (int i = 0; i < count; ++i) {
            const Target& target = targets[i];
            if (!target.alive || !target.purple) {
                continue;
            }
            if (inRange(target.x, target.z, rollerX, rollerZ, rule.hitRadius)) {
                result.actions |= ActionHit;
                ++result.purpleHits;
            }
        }
        return result;
    }

    for (int i = 0; i < count; ++i) {
        const Target& target = targets[i];
        if (!target.alive) {
            continue;
        }
        if (target.purple) {
            if (damageable) {
                if (inRange(target.x, target.z, rollerX, rollerZ, rule.hitRadius)) {
                    result.actions |= ActionHit;
                    ++result.purpleHits;
                }
            } else if (inRange(target.x, target.z, rollerX, rollerZ, rule.stunRadius)) {
                result.actions |= ActionStun;
            }
        } else if (rolling && inRange(target.x, target.z, rollerX, rollerZ, rule.crushRadius)) {
            result.actions |= ActionCrush;
            ++result.crushTargets;
        }
    }
    return result;
}

} // namespace p2wwatk
