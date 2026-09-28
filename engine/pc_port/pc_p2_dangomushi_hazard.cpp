#include "pc_p2_dangomushi_hazard.h"

#include <cmath>

namespace {
constexpr float kRockRingRadius = 100.0f;
constexpr float kTwoPi = 6.283185307179586f;
}

void P2DangoMushiHazardPolicy::reset(const P2DangoMushiHazardParms& parms)
{
    mParms = parms;
    mRocksRemaining = parms.rockBudget;
    mEggsRemaining = parms.eggBudget;
    mInTurn = false;
    mRocksThisTurn = false;
    mEggThisTurn = false;
    mWindowActive = false;
}

void P2DangoMushiHazardPolicy::update(const P2DangoMushiHazardInput& input,
                                      P2DangoMushiHazardOutput& output)
{
    output = P2DangoMushiHazardOutput();

    if (input.turnExited) {
        mInTurn = false;
        mRocksThisTurn = false;
        mEggThisTurn = false;
        mWindowActive = false;
    }
    if (input.turnEntered) {
        mInTurn = true;
        mRocksThisTurn = false;
        mEggThisTurn = false;
        mWindowActive = false;
    }

    if (mInTurn) {
        if (!mRocksThisTurn) {
            const int count = mParms.rocksPerTurn < mRocksRemaining
                ? mParms.rocksPerTurn : mRocksRemaining;
            if (count > 0) {
                output.rocksToSpawn = count;
                output.rockLifetime = mParms.rockLifetime;
                mRocksRemaining -= count;
            }
            mRocksThisTurn = true;

            mEggThisTurn = true;
            if (mEggsRemaining > 0 && input.eggRoll < input.activeCaptainGroupShare) {
                output.eggRequested = true;
                mEggsRemaining -= 1;
            }
        }

        // Source: stickable only between the animation loop-start key and key 3.
        mWindowActive = input.turnFrame >= float(mParms.turnLoopStartFrame)
            && input.turnFrame < float(mParms.turnKey3Frame);
        output.stickable = mWindowActive;
        output.invulnerable = !mWindowActive;
    } else {
        output.stickable = false;
        output.invulnerable = true;
    }

    output.rocksRemaining = mRocksRemaining;
    output.eggsRemaining = mEggsRemaining;
}

void P2DangoMushiHazardPolicy::rockOffset(int index, int count, float angle,
                                          float* x, float* z)
{
    if (!x || !z) return;
    if (count <= 0 || index < 0 || index >= count) {
        *x = 0.0f;
        *z = 0.0f;
        return;
    }
    const float theta = angle + kTwoPi * float(index) / float(count);
    *x = std::cos(theta) * kRockRingRadius;
    *z = std::sin(theta) * kRockRingRadius;
}
