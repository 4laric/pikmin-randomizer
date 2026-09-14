#include "pc_p2_bombsarai_hover.h"

#include <cmath>

namespace {
constexpr float kTau = 6.2831853071795864769f;
bool finite(const P2BombSaraiVec3& value)
{
    return std::isfinite(value.x) && std::isfinite(value.y) && std::isfinite(value.z);
}
}

void P2BombSaraiHover::reset(const P2BombSaraiHoverParms& parms)
{
    mParms = parms;
    mPitchRatio = 0.0f;
}

bool P2BombSaraiHover::update(bool fastTakeOff, int stuckPikmin,
                              const P2BombSaraiVec3& position, float delta,
                              P2BombSaraiGetMinYFn getMinY, void* getMinYContext,
                              float& outVelocityY, float& outHeightAboveGround)
{
    if (!getMinY || !finite(position) || !std::isfinite(delta)
        || std::fabs(delta - kSourceDelta) > 0.000001f) {
        return false;
    }
    const float minY = getMinY(getMinYContext, position.x, position.z);
    if (!std::isfinite(minY)) {
        return false;
    }

    // Source rise factor: fast takeoff forces 6.0; otherwise linear blend of
    // the free/laden factors over the clamped stuck-Pikmin count
    // (BombSarai.cpp:205-212). Carrying Pikmin weighs the bug down.
    float riseFactor = kFastTakeOffRiseFactor;
    if (!fastTakeOff) {
        const int pikiCount = stuckPikmin < 0 ? 0 : (stuckPikmin > 5 ? 5 : stuckPikmin);
        const float pikiCountF = static_cast<float>(pikiCount);
        riseFactor = (5.0f - pikiCountF) / 5.0f * mParms.freeRiseFactor
                   + pikiCountF / 5.0f * mParms.ladenRiseFactor;
    }

    // Pitch oscillation engages only above flightHeight - pitchAmp
    // (BombSarai.cpp:214-219); the ratio advances by pitchRate per second and
    // wraps at TAU (addPitchRatio, :251-257).
    float newHeight = mParms.flightHeight;
    if (position.y - minY > newHeight - mParms.pitchAmp) {
        mPitchRatio += mParms.pitchRate * delta;
        if (mPitchRatio > kTau) {
            mPitchRatio -= kTau;
        }
        newHeight += mParms.pitchAmp * std::sin(mPitchRatio);
    }

    outVelocityY = riseFactor * ((minY + newHeight) - position.y);
    outHeightAboveGround = position.y - minY;
    return std::isfinite(outVelocityY);
}
