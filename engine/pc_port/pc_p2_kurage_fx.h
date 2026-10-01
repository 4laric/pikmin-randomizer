// Jellyfloat suction wind (owner playtest 2026-09-30, #960: "the suction attack
// lacks any kind of wind animation").
//
// Source: Kurage::startSuckEffect/updateSuckEffect/finishSuckEffect
// (Kurage.cpp:603-625) run efx::TNewkurageSui at the point on the ground under
// the body (position = body position minus its altitude) from the attack clip's
// KEYEVENT_2 (suck start) to its KEYEVENT_1 (suck end). P1 has no P2 particle
// assets, so the closest P1 effect is used, as the owner suggested: the
// Blowhog (Mar) wind jet (EFF_Mar_WindJet, TAImar.cpp:206) aimed straight up
// from the ground into the bell, plus its ground dust.
//
// Visual only: nothing here reads or writes simulation state. The host feeds
// the 30 Hz source tick and the commands are a pure function of it.
#pragma once

#include <cstdint>

namespace p2kuragefx {

enum class Kind : std::uint8_t { None, Suction };

struct Command {
    Kind kind = Kind::None;
    float x = 0.0f, y = 0.0f, z = 0.0f; // emitter on the ground under the body
    float topY = 0.0f;                  // where the jet ends (the bell underside)
    bool windowStart = false;           // first command of a suction window
    bool windowEnd = false;             // the window closed this tick (kind is None)
    int emittedInWindow = 0;            // valid when windowEnd
};

struct State {
    bool sucking = false;
    int emitted = 0;
};

// One call per 30 Hz source tick. `isSucking` is the FSM's suction window flag
// (Attack between KEYEVENT_2 and KEYEVENT_1). Emits only while it is set.
inline Command suctionTick(State& st, bool isSucking, float bodyX, float bodyY, float bodyZ, float groundY)
{
    Command c;
    if (isSucking) {
        c.kind = Kind::Suction;
        c.x = bodyX;
        c.z = bodyZ;
        c.y = groundY + 2.0f;
        c.topY = bodyY;
        c.windowStart = !st.sucking;
        st.sucking = true;
        ++st.emitted;
        return c;
    }
    if (st.sucking) {
        c.windowEnd = true;
        c.emittedInWindow = st.emitted;
    }
    st.sucking = false;
    st.emitted = 0;
    return c;
}

} // namespace p2kuragefx

// Engine side (pc_p2_kurage_fx.cpp). Safe to call with no effect manager.
void pc_p2_kurage_fx_emit(const p2kuragefx::Command& command);
