#pragma once

#include "pc_p2_bigtreasure.h"
#include "pc_p2_bigtreasure_motion.h"
#include "pc_p2_retail_player.h"

#include <cstddef>

// Lane-owned animation keyframe source for the BigTreasure FSM host (#246).
//
// The 12-state policy owns no clip lengths: it advances on host keyframe
// pulses (animEnd / keyEvent2 / keyEvent100). This module is that source. It
// maps each policy phase to the source animation (BigTreasure.h AnimID and the
// State*.cpp init selections), plays that clip through the vendored retail
// event player over the lane's P2_RETAIL_EVENTS_1 motion table, and translates
// the dispatched events back into the policy's pulses.
//
// Engine-free: it owns its own P2BigTreasureMotionBank + player and never
// touches the shared visual bank, so it can run in the ordinary update
// alongside a visual-only player without cross-talk.

struct P2BigTreasureAnimPulses {
    bool animEnd = false;
    bool keyEvent2 = false;
    bool keyEvent100 = false;
};

// Writes the source clip name for a policy phase into `out` (NUL terminated)
// and returns false when no clip is mapped or the buffer is too small.
// PreAttack/Attack/PutItem are weapon-suffixed (elec/fire/gas/water -> e/f/g/w;
// fire uses its forward variant here; the source picks a fire direction from
// the target angle, which is host work).
bool p2_bigtreasure_anim_clip(P2BigTreasurePhase phase, int chosenWeapon,
                              char* out, std::size_t capacity);

// Maps retail-dispatched event types to FSM keyframe pulses: 1000 (implicit
// completion) and 1 (authored loop marker, treated as the host cycle end) ->
// animEnd; authored KEYEVENT_2 -> keyEvent2; KEYEVENT_100 -> keyEvent100.
// Other authored types are host-side effects the policy ignores.
void p2_bigtreasure_anim_translate(const int* types, int count,
                                   P2BigTreasureAnimPulses& out);

class P2BigTreasureAnimClock {
public:
    // Loads the motion table; a missing/invalid table leaves the clock
    // inactive (tick produces no pulses) rather than failing the host.
    bool load(const char* eventsPath);
    void reset();
    bool ready() const { return mBank.loaded; }

    // Advances the mapped clip by one 30 Hz source tick and reports this
    // tick's pulses. Starts the phase clip on a phase/weapon change (no events
    // are produced on the start tick).
    void tick(P2BigTreasurePhase phase, int chosenWeapon, P2BigTreasureAnimPulses& out);

    const char* activeClip() const { return mActiveName[0] ? mActiveName : nullptr; }

private:
    P2BigTreasureMotionBank mBank;
    p2retail::Player mPlayer;
    char mActiveName[40] = {};
};
