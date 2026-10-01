#include "../pc_port/pc_p2_kurage_digestion.h"
#include <cassert>
#include <cstdio>
#include <limits>

int main()
{
    using D = P2KurageDigestion;
    using E = D::Event;
    D d;
    auto tick = [&](float dt, bool alive = true, bool health = true,
                    bool bitter = false, bool linked = true) {
        return d.update(dt, alive, health, bitter, linked);
    };
    assert(tick(1.0f) == E::None);
    assert(d.begin());
    // Exact binary fractions avoid accidental float threshold drift.
    for (int i = 0; i < 63; ++i) assert(tick(0.25f) == E::None);
    assert(tick(0.25f) == E::ShrinkStarted);
    assert(d.remaining() == 0.5f && d.scale() == 1.0f);
    assert(tick(20.0f, true, true, true) == E::None);
    assert(tick(20.0f, true, false) == E::None);
    assert(d.remaining() == 0.5f);
    assert(tick(0.25f) == E::None && d.scale() == 0.5f);
    assert(tick(0.25f) == E::Killed);
    assert(tick(1.0f) == E::None);

    assert(d.begin(1.0f));
    assert(tick(100.0f) == E::ShrinkStarted);
    assert(d.remaining() == 0.5f); // no overshoot carry
    assert(tick(0.125f) == E::None && d.scale() == 0.75f);
    assert(tick(0.0f, false) == E::Released && d.scale() == 1.0f);
    assert(tick(1.0f) == E::None);

    assert(d.begin(1.0f));
    assert(tick(1.0f, true, true, false, false) == E::Released);
    assert(d.begin(0.0f));
    assert(tick(0.0f) == E::ShrinkStarted);
    // Source checks link loss only before entering its terminal shrink phase.
    assert(tick(0.25f, true, true, false, false) == E::None);
    assert(tick(0.25f, true, true, false, false) == E::Killed);

    assert(d.begin());
    assert(tick(50.0f, true, true, true) == E::None);
    assert(tick(50.0f, true, false) == E::None);
    assert(d.remaining() == 16.0f);
    const float nan = std::numeric_limits<float>::quiet_NaN();
    assert(!d.begin(nan) && !d.begin(-1.0f));
    assert(tick(nan) == E::None && tick(-1.0f) == E::None);
    assert(d.remaining() == 16.0f && d.phase() == D::Phase::Stomach);
    std::puts("PASS Kurage digestion: phase timing, pauses, overshoot, release precedence, terminal idempotence");
}
