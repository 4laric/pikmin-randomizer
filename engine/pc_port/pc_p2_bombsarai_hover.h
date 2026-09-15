#pragma once

#include "pc_p2_bombsarai_bomb.h"
#include "pc_p2_bombsarai_terrain.h"

// Isolated BombSarai hover vertical-control policy, mirroring
// BombSarai::Obj::setHeightVelocity / addPitchRatio
// (src/plugProjectNishimuraU/BombSarai.cpp:202-224, :251-257 at revision
// 632af93787b9c95b63f0c13be32b161375ce3a96). Engine-free: terrain height
// comes from the lane terrain adapter (P2BombSaraiGetMinYFn); horizontal
// movement and the FSM remain host-owned.

struct P2BombSaraiHoverParms {
    float flightHeight = 90.0f;   // fp01 default (BombSarai.h:125)
    float pitchRate = 2.5f;       // fp10 default
    float pitchAmp = 20.0f;       // fp11 default
    float freeRiseFactor = 1.5f;  // fp21 default
    float ladenRiseFactor = 1.0f; // fp22 default
};

class P2BombSaraiHover {
public:
    static constexpr float kSourceDelta = 1.0f / 30.0f;
    static constexpr float kFastTakeOffRiseFactor = 6.0f; // BombSarai.cpp:205

    void reset(const P2BombSaraiHoverParms& parms);

    // One 30 Hz source update. Computes the source vertical velocity into
    // outVelocityY and the height above terrain (position.y - minY) into
    // outHeightAboveGround, matching setHeightVelocity's return. stuckPikmin
    // is clamped to [0, 5] exactly like the source (negative counts to 0,
    // above-5 to 5). A failed terrain sample or non-source delta returns
    // false and writes no output.
    bool update(bool fastTakeOff, int stuckPikmin, const P2BombSaraiVec3& position,
                float delta, P2BombSaraiGetMinYFn getMinY, void* getMinYContext,
                float& outVelocityY, float& outHeightAboveGround);

    float pitchRatio() const { return mPitchRatio; }

private:
    P2BombSaraiHoverParms mParms;
    float mPitchRatio = 0.0f; // BombSarai.cpp:45, wraps at TAU (:251-257)
};
