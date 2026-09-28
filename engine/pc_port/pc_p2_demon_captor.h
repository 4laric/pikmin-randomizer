#pragma once
#include "pc_p2_demon_capture.h"
#include <cmath>
#include <cstddef>

// Natural captor front end for the Bumbling Snitchbug (Demon ID 32), inherited
// from Sarai ID 23. It transcribes only the source target-acquisition and
// approach decisions so an ordinary host can find a live captain, turn toward
// it under the source turn cap and request the Attack window once it is inside
// grab range.
//
// This controller never touches a captain: stick/attachment, capture delivery,
// animation clocks, carry, escape, drop and teardown stay with pc_demon_capture,
// the registered drop/escape states and P2DemonHost. Keeping it dependency-free
// lets the acquisition/approach/admission ordering be unit-tested without a
// rendered scene.
class P2DemonCaptor {
public:
    struct Input {
        float faceDirection = 0;
        float homeDistanceSquaredXZ = 0;
        float territoryRadius = 0;
        float viewAngleDegrees = 0;
        float sightRadius = 0;
        float moveSpeed = 0;
        float turnSpeed = 0;
        float maxTurnAngleDegrees = 0;
        float attackRange = 0;
        float delta = 0;
        const P2DemonCaptain* captains = nullptr;
        std::size_t count = 0;
        bool active = true;
    };
    struct Output {
        bool valid = false;
        bool targetFound = false;
        std::size_t targetIndex = 0;
        float faceDirection = 0;
        float velocityX = 0;
        float velocityZ = 0;
        bool beginAttack = false;
    };

    void reset() { gate_.reset(); }
    float targetTimer() const { return gate_.timer(); }

    Output step(const Input& in) {
        Output out;
        if (!std::isfinite(in.delta) || in.delta <= 0.0f || in.delta > 0.25f) return out;
        if (!std::isfinite(in.faceDirection) || !std::isfinite(in.moveSpeed) ||
            !std::isfinite(in.turnSpeed) || !std::isfinite(in.maxTurnAngleDegrees) ||
            !std::isfinite(in.attackRange) || in.attackRange < 0.0f ||
            in.moveSpeed < 0.0f || in.turnSpeed < 0.0f || in.maxTurnAngleDegrees < 0.0f) return out;

        P2DemonTargetInput gate{in.homeDistanceSquaredXZ, in.territoryRadius,
            in.viewAngleDegrees, in.sightRadius};
        const P2DemonSelection selection = gate_.step(in.delta, gate, in.captains, in.count, in.active);
        out.valid = selection.valid;
        if (!selection.valid) return out;
        if (!selection.found) return out;

        out.targetFound = true;
        out.targetIndex = selection.index;
        const P2DemonCaptain& c = in.captains[selection.index];
        const float angle = c.angleRadians;
        const float cap = in.maxTurnAngleDegrees * 3.14159265358979323846f / 180.0f;
        const float turn = std::min(std::fabs(angle) * in.turnSpeed, cap);
        out.faceDirection = in.faceDirection + (angle < 0.0f ? -turn : turn);
        if (!std::isfinite(out.faceDirection)) { out.faceDirection = in.faceDirection; }

        // Stop once the captain is inside grab range so the host can run the
        // source Attack window against a stable mouth position.
        if (c.distanceSquaredXZ <= in.attackRange * in.attackRange) {
            out.beginAttack = true;
            return out;
        }
        out.velocityX = std::sin(out.faceDirection) * in.moveSpeed;
        out.velocityZ = std::cos(out.faceDirection) * in.moveSpeed;
        return out;
    }

private:
    P2DemonTargetGate gate_;
};
