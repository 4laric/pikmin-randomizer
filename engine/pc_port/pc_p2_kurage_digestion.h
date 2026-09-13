#pragma once

#include <cmath>

// GPVE01 PikiSuikomiState::exec/execStomach, pikiState.cpp:2091/2196.
// Begins at stomach entry, not at suction admission. Movement, rendering and
// death accounting belong to the receiver. Source resets the shrink timer;
// excess time from the preceding phase must not carry into it.
class P2KurageDigestion {
public:
    enum class Phase { Inactive, Stomach, Shrinking, Terminal };
    enum class Event { None, ShrinkStarted, Released, Killed };

    bool begin(float seconds = 16.0f)
    {
        if (!std::isfinite(seconds) || seconds < 0.0f) return false;
        mPhase = Phase::Stomach;
        mRemaining = seconds;
        mScale = 1.0f;
        return true;
    }

    Event update(float delta, bool ownerAlive, bool ownerHasHealth,
                 bool bittered, bool stomachLinked)
    {
        if (!std::isfinite(delta) || delta < 0.0f
            || mPhase == Phase::Inactive || mPhase == Phase::Terminal)
            return Event::None;
        if (!ownerAlive) {
            mPhase = Phase::Terminal;
            mScale = 1.0f;
            return Event::Released;
        }
        if (!bittered && ownerHasHealth) mRemaining -= delta;
        if (mPhase == Phase::Shrinking) {
            // Retail computes this before the death test, including overshoot.
            mScale = mRemaining / 0.5f;
            if (mRemaining <= 0.0f) {
                mPhase = Phase::Terminal;
                return Event::Killed;
            }
        } else if (!stomachLinked) {
            mPhase = Phase::Terminal;
            return Event::Released;
        } else if (mRemaining <= 0.0f) {
            mPhase = Phase::Shrinking;
            mRemaining = 0.5f;
            return Event::ShrinkStarted;
        }
        return Event::None;
    }

    Phase phase() const { return mPhase; }
    float remaining() const { return mRemaining; }
    float scale() const { return mScale; }

private:
    Phase mPhase = Phase::Inactive;
    float mRemaining = 0.0f;
    float mScale = 1.0f;
};
