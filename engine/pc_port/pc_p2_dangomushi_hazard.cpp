#include "pc_p2_dangomushi_hazard.h"

#include <cmath>

namespace {
constexpr float kPi = 3.141592653589793f;
constexpr float kTwoPi = 6.283185307179586f;
}

void P2DangoMushiHazardPolicy::reset(const P2DangoMushiHazardParms& parms)
{
    mParms = parms;
    mTurns = 0;
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
        ++mTurns;
        mInTurn = true;
        mRocksThisTurn = false;
        mEggThisTurn = false;
        mWindowActive = false;
    }

    if (mInTurn) {
        if (!mRocksThisTurn) {
            // createCrashEnemy on every Turn entry: no lifetime budget.
            if (mParms.rocksPerTurn > 0) {
                output.rocksToSpawn = mParms.rocksPerTurn;
                output.rockLifetime = mParms.rockLifetime;
            }
            mRocksThisTurn = true;

            // getFallEggNum: randWeightFloat(1) < groupSize / activePikmin.
            mEggThisTurn = true;
            if (input.eggRoll < input.activeCaptainGroupShare) {
                output.eggRequested = true;
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

    output.turnIndex = mTurns;
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
    float theta = 0.0f;
    float dist = 7.5f;                       // randWeightFloat(15) midpoint
    if (index == 0) {
        theta = 0.0f;
    } else if (index < 4) {
        theta = (2.0f * kPi / 3.0f) * float(index) + (angle + 0.5f);
        dist = 77.5f;                        // 70 + randWeightFloat(15)
    } else if (index < 10) {
        theta = (kPi / 3.0f) * float(index) + (angle + 0.5f + 0.25f);
        dist = 147.5f;                       // 140 + randWeightFloat(15)
    } else {
        theta = (kPi / 6.0f) * float(index) + (angle + 0.25f + 0.05f);
        dist = 227.5f;                       // unused past 10 in retail
    }
    if (theta > kTwoPi) theta -= kTwoPi;
    *x = std::sin(theta) * dist;
    *z = std::cos(theta) * dist;
}
