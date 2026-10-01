// Standalone, engine-free lifecycle tests for the Sarai (ID 23) captor lane.
//
// Coverage:
//   1. the shared escape window reused by the captor bridge: directional
//      D-pad edge accumulation and its transfer into the source animation
//      speed / escape roll, ending in detach (stick pointers + authority);
//   2. interruption: the forced-release detach clears the captain stick
//      pointers and revokes owner authority, and a wrong captain or stale owner
//      generation is refused;
//   3. teardown: release / owner-lost / scene-exit after a release are inert.
//
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_sarai_captor_lifecycle_test.cpp -o p2_sarai_captor_lifecycle_test.exe
#include "pc_p2_sarai_lifecycle.h"
#include "pc_p2_demon_drop_policy.h"
#include <cassert>
#include <cmath>
#include <cstdio>

using p2sarai::CaptureLifecycle;

namespace {
bool noPart(unsigned slot) { return slot != 0u && slot != 1u; }
}

int main()
{
    // --- 1. Escape window accumulation and transfer -------------------------
    {
        CaptureLifecycle lifecycle;
        assert(!lifecycle.occupied());
        assert(lifecycle.capture(7, 0xabcull, 0));
        assert(lifecycle.occupied() && lifecycle.authority(0xabcull));
        assert(lifecycle.captain() == 7u);
        assert(lifecycle.stickObject() == 0xabcull && lifecycle.stickPart() == 0u);

        // A detached captain cannot accumulate and must not consume the RNG.
        int draws = 0;
        auto fail = [&] { ++draws; return 0.99f; };
        for (int i = 0; i < 4; ++i) {
            const auto step = lifecycle.escapeTick(false, true, fail);
            assert(!step.escape && step.animationSpeed == 30.0f);
        }
        assert(draws == 0);

        // Five attached edges are below the source six-input window: no transfer.
        for (int i = 0; i < 5; ++i) {
            const auto step = lifecycle.escapeTick(true, true, fail);
            assert(!step.escape && step.animationSpeed == 30.0f);
        }
        assert(draws == 0);

        // The sixth edge opens the window: the count transfers into the
        // animation speed and the first RNG sample is drawn but fails.
        const auto sixth = lifecycle.escapeTick(true, true, fail);
        assert(draws == 1 && !sixth.escape);
        assert(std::fabs(sixth.animationSpeed - (6.0f / 22.0f * 60.0f + 60.0f)) < 1e-4f);
        assert(lifecycle.occupied()); // a failed roll must not detach

        // The source consumes a second sample only if the first passes; a
        // passing window escapes, detaches and clears the stick pointers.
        draws = 0;
        auto pass = [&] { ++draws; return 0.0f; };
        const auto escaped = lifecycle.escapeTick(false, false, pass);
        assert(escaped.escape && draws == 2);
        assert(!lifecycle.occupied() && !lifecycle.authority(0xabcull));
        assert(lifecycle.captain() == 0u && lifecycle.stickObject() == 0u && noPart(lifecycle.stickPart()));

        // A fresh capture starts a clean window (no carry-over count).
        assert(lifecycle.capture(8, 0xdefull, 1));
        draws = 0;
        for (int i = 0; i < 5; ++i) assert(!lifecycle.escapeTick(true, true, fail).escape);
        assert(draws == 0 && lifecycle.occupied());
    }

    // --- 1b. Capture admission bounds --------------------------------------
    {
        CaptureLifecycle lifecycle;
        assert(!lifecycle.capture(0, 1, 0));   // no captain identity
        assert(!lifecycle.capture(1, 0, 0));   // no owner generation
        assert(!lifecycle.capture(1, 1, 2));   // invalid mouth slot
        assert(!lifecycle.occupied());
        assert(lifecycle.capture(1, 1, 0));
        assert(!lifecycle.capture(2, 2, 1));   // one live binding only
        assert(lifecycle.captain() == 1u && lifecycle.authority(1u));
    }

    // --- 2. Interruption clears stick pointers and authority ---------------
    {
        CaptureLifecycle lifecycle;
        assert(!lifecycle.interrupt(1));       // nothing to interrupt
        assert(lifecycle.capture(11, 0x55ull, 1));
        assert(lifecycle.occupied() && lifecycle.authority(0x55ull));
        assert(lifecycle.stickObject() == 0x55ull && lifecycle.stickPart() == 1u);

        assert(!lifecycle.interrupt(12));      // a different captain is refused
        assert(lifecycle.occupied() && lifecycle.captain() == 11u);
        assert(lifecycle.interrupt(11));       // forced release detaches
        assert(!lifecycle.occupied() && !lifecycle.authority(0x55ull));
        assert(lifecycle.stickObject() == 0u && noPart(lifecycle.stickPart()));
        assert(!lifecycle.interrupt(11));      // second interrupt is inert

        // Owner loss is generation-qualified: a stale token is inert.
        assert(lifecycle.capture(11, 0x55ull, 0));
        assert(!lifecycle.ownerLost(0x54ull));
        assert(lifecycle.occupied() && lifecycle.authority(0x55ull));
        assert(lifecycle.ownerLost(0x55ull));
        assert(!lifecycle.occupied() && lifecycle.stickObject() == 0u && noPart(lifecycle.stickPart()));

        // A detached binding is observed but not double-detached.
        assert(!lifecycle.observeDetached());
        assert(lifecycle.capture(13, 0x56ull, 0));
        assert(lifecycle.observeDetached());
        assert(!lifecycle.occupied() && !lifecycle.observeDetached());
    }

    // --- 3. Teardown inert after release -----------------------------------
    {
        CaptureLifecycle lifecycle;
        assert(lifecycle.capture(21, 0x77ull, 0));
        assert(lifecycle.release(21));
        assert(!lifecycle.occupied() && !lifecycle.authority(0x77ull));
        assert(lifecycle.stickObject() == 0u && noPart(lifecycle.stickPart()));

        assert(!lifecycle.release(21));        // every teardown path is inert
        assert(!lifecycle.interrupt(21));
        assert(!lifecycle.ownerLost(0x77ull));
        assert(!lifecycle.sceneExit());
        assert(!lifecycle.observeDetached());

        // An inert lifecycle neither escapes nor draws the engine RNG.
        int draws = 0;
        auto random = [&] { ++draws; return 0.0f; };
        const auto step = lifecycle.escapeTick(true, true, random);
        assert(!step.escape && step.animationSpeed == 30.0f && draws == 0);

        // Scene exit is idempotent on a live binding too.
        assert(lifecycle.capture(22, 0x88ull, 1));
        assert(lifecycle.sceneExit());
        assert(!lifecycle.occupied());
        assert(!lifecycle.sceneExit());
    }

    // --- Interlock with the shared registered-drop policy ------------------
    {
        P2DemonDropPolicy drop;
        const auto begin = drop.begin(1, 10.0f, 200.0f);
        assert(begin.accepted && begin.startFall);
        assert(!drop.begin(2, 10.0f, 200.0f).accepted); // one live generation
        assert(drop.bounce(1).startKnockdown);
        const auto damage = drop.animationEnd(1, P2DemonDropPhase::Knockdown);
        assert(damage.deliverDamage && damage.damage == 10.0f);
        drop.cancel();
        assert(!drop.animationEnd(1, P2DemonDropPhase::Knockdown).deliverDamage);
        assert(!drop.bounce(1).accepted);
    }

    std::puts("p2_sarai_captor_lifecycle_test PASS");
    return 0;
}
