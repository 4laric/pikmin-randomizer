#pragma once
// Natural captor front end for the Swooping Snitchbug (Sarai, enemy ID 23).
//
// Independent transcription of Sarai.cpp getAttackableTarget() and the capped
// turn/approach shape already proven by the shared P2DemonCaptor (Demon ID 32
// inherits Sarai). This controller consumes the Sarai source geometry from
// pc_p2_sarai_policy.h directly (viewHalfAngle()'s PI * DEG2RAD * mViewAngle
// expression, territory and sight gates, floor/stick/alive filters) instead of
// the Demon gate so the Sarai lane drives its own source facts.
//
// It never touches captain stick state, animation clocks, capture delivery,
// carry, escape, drop or teardown; those stay with the host and the shared
// pc_demon_capture bridge. Dependency-free so acquisition/approach ordering can
// be unit tested without a rendered scene.
#include "pc_p2_sarai_policy.h"
#include <cmath>
#include <cstddef>

struct P2SaraiCaptain {
    bool alive = true;
    bool stickToMouth = false;   // already carried by any mouth
    bool stickerIsSelf = false;  // mouth-stuck to this Sarai
    bool floorTriangle = true;   // standing on a floor triangle
    float angleRad = 0;          // getAngDist(candidate) relative to facing
    float sqrDistXZ = 0;         // squared XZ distance to the Sarai
};

class P2SaraiCaptor {
public:
    struct Input {
        float faceDirection = 0;
        float homeDistanceSquaredXZ = 0;
        float territoryRadius = 0;
        float viewAngleDegrees = 0;  // mViewAngle
        float sightRadius = 0;
        float moveSpeed = 0;
        float turnSpeed = 0;
        float maxTurnAngleDegrees = 0;
        float attackRange = 0;
        float delta = 0;
        const P2SaraiCaptain* captains = nullptr;
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

    void reset() { mTimer = 0.0f; }
    float targetTimer() const { return mTimer; }

    Output step(const Input& in) {
        Output out;
        if (!std::isfinite(in.delta) || in.delta <= 0.0f || in.delta > 0.25f) return out;
        if (!std::isfinite(in.faceDirection) || !std::isfinite(in.moveSpeed)
            || !std::isfinite(in.turnSpeed) || !std::isfinite(in.maxTurnAngleDegrees)
            || !std::isfinite(in.attackRange) || in.attackRange < 0.0f
            || in.moveSpeed < 0.0f || in.turnSpeed < 0.0f || in.maxTurnAngleDegrees < 0.0f) return out;
        if (!std::isfinite(in.homeDistanceSquaredXZ) || !std::isfinite(in.territoryRadius)
            || !std::isfinite(in.viewAngleDegrees) || !std::isfinite(in.sightRadius)
            || in.territoryRadius < 0.0f || in.sightRadius < 0.0f
            || in.homeDistanceSquaredXZ < 0.0f || in.count > 64 || (in.count && !in.captains)) return out;

        out.valid = true;
        if (!in.active) return out;
        mTimer += in.delta;  // Source increments per query, not per rendered frame.
        if (!(mTimer > 3.0f)) return out;
        if (!(in.homeDistanceSquaredXZ < in.territoryRadius * in.territoryRadius)) return out;

        const p2sarai::TargetQuery query{in.homeDistanceSquaredXZ, in.territoryRadius,
                                          in.viewAngleDegrees, in.sightRadius};
        for (std::size_t i = 0; i < in.count; ++i) {
            const P2SaraiCaptain& c = in.captains[i];
            if (!std::isfinite(c.angleRad) || !std::isfinite(c.sqrDistXZ)
                || c.sqrDistXZ < 0.0f || std::fabs(c.angleRad) > 2.0f * p2sarai::kPi) return out;
            p2sarai::TargetCandidate candidate;
            candidate.alive = c.alive;
            candidate.isPikmin = true;
            candidate.stickToMouth = c.stickToMouth;
            candidate.stickerIsSelf = c.stickerIsSelf;
            candidate.floorTriangle = c.floorTriangle;
            candidate.angleRad = c.angleRad;
            candidate.sqrDistXZ = c.sqrDistXZ;
            if (p2sarai::targetable(query, candidate)) { out.targetFound = true; out.targetIndex = i; break; }
        }
        if (!out.targetFound) return out;

        const P2SaraiCaptain& c = in.captains[out.targetIndex];
        const float cap = in.maxTurnAngleDegrees * p2sarai::kDeg2Rad;
        const float turn = std::min(std::fabs(c.angleRad) * in.turnSpeed, cap);
        out.faceDirection = in.faceDirection + (c.angleRad < 0.0f ? -turn : turn);
        if (!std::isfinite(out.faceDirection)) out.faceDirection = in.faceDirection;

        // Stop once the captain is inside grab range so the host can run the
        // source Attack window against a stable mouth position.
        if (c.sqrDistXZ <= in.attackRange * in.attackRange) {
            out.beginAttack = true;
            return out;
        }
        out.velocityX = std::sin(out.faceDirection) * in.moveSpeed;
        out.velocityZ = std::cos(out.faceDirection) * in.moveSpeed;
        return out;
    }

private:
    float mTimer = 0.0f;
};
