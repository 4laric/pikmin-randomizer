// OniKurage (Greater Spotted Jellyfloat, enemy ID 72) FSM face.
//
// Thin composition of the shared Jellyfloat bridge in pc_p2_kurage_fsm.h: the
// Greater Spotted Jellyfloat registers every Kurage state plus Drop
// (OniKurageState.cpp:21) and changes only the pitch numerics, the captain
// mouth route and the Drop falling state. Rather than fork the state machine,
// this header constructs the shared Fsm pinned to Variant::Greater so a
// standalone fixture can exercise the OniKurage state set while Kurage's
// default construction stays untouched.
//
// Source: native/pikmin2-research rev 632af93787b9c95b63f0c13be32b161375ce3a96
//   src/plugProjectNishimuraU/OniKurage.cpp / OniKurageState.cpp
//   include/Game/Entities/OniKurage.h
#ifndef PC_P2_ONIKURAGE_FSM_H
#define PC_P2_ONIKURAGE_FSM_H

#include "pc_p2_kurage_fsm.h"

namespace p2onikurage {

using Variant = p2kurage::Variant;
using State = p2kurage::State;
using Motion = p2kurage::Motion;
using KeyEvent = p2kurage::KeyEvent;
using Flags = p2kurage::Flags;
using In = p2kurage::In;
using Out = p2kurage::Out;
using Parms = p2kurage::Parms;

// The OniKurage-only state, surfaced for fixture readability.
constexpr State kDrop = State::Drop;

class Fsm {
public:
    explicit Fsm(Parms parms = Parms()) : mInner(parms, Variant::Greater) {}

    State state() const { return mInner.state(); }
    Motion motion() const { return mInner.motion(); }
    const Flags& flags() const { return mInner.flags(); }
    float fallTimer() const { return mInner.fallTimer(); }
    Variant variant() const { return mInner.variant(); }

    void spawn() { mInner.spawn(); }
    void forceState(State state) { mInner.forceState(state); }
    Out tick(const In& in) { return mInner.tick(in); }

private:
    p2kurage::Fsm mInner;
};

} // namespace p2onikurage

#endif
