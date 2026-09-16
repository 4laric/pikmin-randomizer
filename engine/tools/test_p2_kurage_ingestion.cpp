#include "../pc_port/pc_p2_kurage_ingestion.h"
#include <cassert>
#include <cstdio>
#include <limits>

int main()
{
    using I = P2KurageIngestion;
    using E = I::Event;
    using P = I::Phase;

    static_assert(I::kKurageKillTime == 16.0f, "PikiParms P016");
    static_assert(I::kShrinkTime == 0.5f, "source shrink window");

    // InteractSuikomi_Test::actPiki admission: invincible, already attached and
    // non-stickable candidates are rejected; one admission per lifecycle.
    {
        I g;
        assert(!g.admit(true, false, true));
        assert(!g.admit(false, true, true));
        assert(!g.admit(false, false, false));
        assert(g.admit(false, false, true));
        assert(g.phase() == P::Mouth && g.active());
        assert(!g.admit(false, false, true));
        I h;
        assert(!h.capture()); // mouth arrival requires admission
    }

    // execMouth: capture starts the P016 countdown from the mouth reference.
    {
        I g;
        assert(g.admit(false, false, true));
        assert(g.capture());
        assert(g.phase() == P::Stomach && g.remaining() == 16.0f && g.active());
        assert(!g.capture());
        assert(g.cleanup());
        assert(g.phase() == P::Terminal && !g.active());
        assert(!g.cleanup());
    }

    // exec() owner death in the mouth phase restores the base scale and returns
    // to Walk without ever entering the stomach.
    {
        I g;
        assert(g.admit(false, false, true));
        assert(g.update(1.0f, true, true, false, true) == E::None);
        assert(g.update(0.25f, false, true, false, true) == E::Ejected);
        assert(g.phase() == P::Terminal && !g.active());
        assert(g.update(1.0f, true, true, false, true) == E::None);
        assert(!g.cleanup());
        I h;
        assert(h.admit(false, false, true));
        assert(!h.admit(false, false, true)); // no double admission from Mouth
    }

    // execStomach: 16 s countdown, separate 0.5 s shrink, exact scale, then kill.
    {
        I g;
        assert(g.admit(false, false, true));
        assert(g.capture());
        for (int i = 0; i < 63; ++i) assert(g.update(0.25f, true, true, false, true) == E::None);
        assert(g.update(0.25f, true, true, false, true) == E::ShrinkStarted);
        assert(g.phase() == P::Shrinking && g.remaining() == 0.5f && g.scale() == 1.0f);
        assert(g.update(0.25f, true, true, false, true) == E::None && g.scale() == 0.5f);
        assert(g.update(0.25f, true, true, false, true) == E::Killed);
        assert(g.phase() == P::Terminal);
        assert(g.update(1.0f, true, true, false, true) == E::None);
        assert(!g.cleanup()); // the kill path already terminated the lifecycle
    }

    // Bitter pause and zero-health pause never decrement, in both phases.
    {
        I g;
        assert(g.admit(false, false, true));
        assert(g.capture());
        assert(g.update(50.0f, true, true, true, true) == E::None && g.remaining() == 16.0f);
        assert(g.update(50.0f, true, false, false, true) == E::None && g.remaining() == 16.0f);
        assert(g.update(16.0f, true, true, false, true) == E::ShrinkStarted);
        assert(g.update(0.25f, true, true, false, true) == E::None && g.scale() == 0.5f);
        assert(g.update(20.0f, true, true, true, true) == E::None && g.scale() == 0.5f);
        assert(g.update(20.0f, true, false, false, true) == E::None && g.scale() == 0.5f);
        assert(g.update(0.25f, true, true, false, true) == E::Killed);
    }

    // execStomach owner-death gate: health <= 0 pauses but stays captured; the
    // owner becoming not alive ejects and restores scale.
    {
        I g;
        assert(g.admit(false, false, true));
        assert(g.capture());
        assert(g.update(1.0f, true, false, false, true) == E::None);
        assert(g.phase() == P::Stomach && g.active());
        assert(g.update(0.25f, false, false, false, true) == E::Ejected);
        assert(g.phase() == P::Terminal && !g.active());
    }

    // Link loss outside the shrink phase releases to Blow recovery.
    {
        I g;
        assert(g.admit(false, false, true));
        assert(g.capture());
        assert(g.update(0.25f, true, true, false, false) == E::Released);
        assert(g.phase() == P::Terminal && !g.active());
    }

    // cleanup() reports a live capture exactly once; invalid ticks are ignored.
    {
        I g;
        assert(g.admit(false, false, true));
        assert(g.capture());
        const float nan = std::numeric_limits<float>::quiet_NaN();
        assert(g.update(nan, true, true, false, true) == E::None);
        assert(g.update(-1.0f, true, true, false, true) == E::None);
        assert(g.remaining() == 16.0f && g.phase() == P::Stomach);
        assert(g.cleanup() && !g.cleanup());
        I h;
        assert(h.admit(false, false, true) && h.capture(1.0f));
        assert(h.update(1.0f, true, true, false, true) == E::ShrinkStarted);
        assert(h.remaining() == 0.5f); // countdown overshoot is discarded
    }

    std::puts("PASS Kurage ingestion: admission gates, mouth/stomach capture, 16s timer, "
              "bitter/health pauses, 0.5s shrink, owner-death eject, link-loss release, cleanup");
}
