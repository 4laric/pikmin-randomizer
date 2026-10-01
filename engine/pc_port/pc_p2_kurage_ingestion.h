#pragma once

#include "pc_p2_kurage_digestion.h"

// GPVE01 rev 0 PikiSuikomiState lifecycle (pikiState.cpp:2071-2244), extracted
// as a dependency-free controller.  The host owns engine movement, attachment
// and scale application; this owns the source phase ordering and gates:
//
//   init()      (2071) stores the owner/stomach references, clears move velocity
//                      and ends any previous stick.
//   exec()      (2091) when the owner is no longer alive, restores the base
//                      scale and re-enters Walk.
//   execMouth() (2113) closes on the mouth point (stomach collpart for Kurage)
//                      within 10 units, captures the stomach and starts the
//                      mKurageKillTime countdown (PikiParms P016, 16.0 s).
//   execStomach()(2196) decrements only while the enemy is not EB_Bittered and
//                      health is positive; expiry starts a separate 0.5 s shrink
//                      before death.  Outside the shrink phase, loss of the
//                      target collision object releases to Blow recovery.
//   cleanup()   (2240) ends the stomach capture and restores movement velocity.
//
// `P2KurageDigestion` remains the stomach timer/shrink policy; this composes it
// and adds the admission, mouth and cleanup accounting the bounded host needs.
class P2KurageIngestion {
public:
    enum class Phase { Inactive, Mouth, Stomach, Shrinking, Terminal };
    enum class Event {
        None,
        Captured,
        ShrinkStarted,
        Released,  // stomach/link loss while the owner is still alive (Blow)
        Ejected,   // owner no longer alive: restore scale and return to Walk
        Killed,
    };

    // PikiParms.h:114 'P016' mKurageKillTime default.
    static constexpr float kKurageKillTime = 16.0f;
    static constexpr float kShrinkTime = 0.5f;

    // InteractSuikomi_Test::actPiki (interactPiki.cpp:423): rejects invincible
    // Pikmin.  Kurage::suckPikmin (Kurage.cpp:511) additionally excludes a
    // Pikmin already stuck to this owner; mayStick maps Piki::mayIstick().
    bool admit(bool invincible, bool alreadyAttached, bool mayStick)
    {
        if (mPhase != Phase::Inactive || invincible || alreadyAttached || !mayStick) return false;
        mPhase = Phase::Mouth;
        return true;
    }

    // execMouth (pikiState.cpp:2130): when the mouth closes within 10 units the
    // Pikmin captures the stomach and mKurageKillTime starts.  Seconds are
    // parameterized so fixture hosts can shorten the countdown deterministically.
    bool capture(float seconds = kKurageKillTime)
    {
        if (mPhase != Phase::Mouth || !mDigestion.begin(seconds)) return false;
        mPhase = Phase::Stomach;
        return true;
    }

    // exec()/execStomach() (pikiState.cpp:2091/2196).  `linked` is the live
    // stomach/target collision reference.  Returns at most one event per tick.
    Event update(float delta, bool ownerAlive, bool ownerHasHealth, bool bittered, bool linked)
    {
        if (mPhase == Phase::Inactive || mPhase == Phase::Terminal) return Event::None;
        if (mPhase == Phase::Mouth) {
            if (!ownerAlive) { finish(); return Event::Ejected; }
            return Event::None;
        }
        const P2KurageDigestion::Event event =
            mDigestion.update(delta, ownerAlive, ownerHasHealth, bittered, linked);
        switch (mDigestion.phase()) {
        case P2KurageDigestion::Phase::Stomach: mPhase = Phase::Stomach; break;
        case P2KurageDigestion::Phase::Shrinking: mPhase = Phase::Shrinking; break;
        case P2KurageDigestion::Phase::Terminal: finish(); break;
        default: break;
        }
        switch (event) {
        case P2KurageDigestion::Event::ShrinkStarted: return Event::ShrinkStarted;
        case P2KurageDigestion::Event::Killed: return Event::Killed;
        case P2KurageDigestion::Event::Released:
            return ownerAlive ? Event::Released : Event::Ejected;
        default: return Event::None;
        }
    }

    // cleanup() (pikiState.cpp:2240): endStomachCapture + setMoveVelocity(true).
    // Returns true exactly once, while a live capture/attachment was owned, so
    // the host knows to restore the stored capture scale before detaching.
    bool cleanup() { return finish(); }

    Phase phase() const { return mPhase; }
    bool active() const { return mPhase != Phase::Inactive && mPhase != Phase::Terminal; }
    float remaining() const { return mDigestion.remaining(); }
    float scale() const { return mDigestion.scale(); }

private:
    bool finish()
    {
        if (mPhase == Phase::Inactive || mPhase == Phase::Terminal) return false;
        mPhase = Phase::Terminal;
        return true;
    }

    P2KurageDigestion mDigestion;
    Phase mPhase = Phase::Inactive;
};
