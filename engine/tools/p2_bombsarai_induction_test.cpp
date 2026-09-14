#include "pc_p2_bombsarai_bomb.h"

// This fixture performs state transitions inside assert() expressions (for
// example throwBomb()/update() side effects). Release builds pass -DNDEBUG, so
// assert() would be compiled out and the transitions would never run, leaving
// the induce() loop below unbounded. Force assertions on for the test unit.
#undef NDEBUG
#include <cassert>
#include <cstdio>

// Standalone fixture for the multi-carrier bomb-pool limit and the bomb-on-
// bomb ip02 induction slice of the BombSarai lane (#244). Engine-free: the
// pool, capture/throw and the induction counter are exercised directly.
// Source citations are to bomb.cpp / bombState.cpp at GPVE01 rev 0
// (632af937) via docs/PIKMIN2_BOMBSARAI_AUDIT.md ("Bomb supply, carry and
// throw", "Detonation") and the retail parm tables
// (docs/PIKMIN2_BOMBSARAI_RUNTIME_EVIDENCE.md: ip02 = 15 retail).

namespace {
using K = P2BombSaraiThrowKind;

P2BombSaraiBombConfig config(int ip02)
{
    P2BombSaraiBombConfig cfg;
    cfg.gravityPerTick = 18.666667f;  // retail (560 / 30)
    cfg.fuseHealth = 4.5f;            // retail bomb general fp00
    cfg.armLoopTicks = 30;            // retail hit_start.bca
    cfg.bombRadius = 15.0f;           // retail bomb/enemycoll.txt child
    cfg.blastRadius = 90.0f;          // retail fp22
    cfg.blastHalfHeight = 50.0f;      // retail fp02
    cfg.tekiDamage = 500.0f;          // retail fp01
    cfg.naviPikiDamage = 10.0f;       // retail fp24
    cfg.ip02TriggerLimit = ip02;
    return cfg;
}

// Floor-contacting trace: the bomb lands and arms on the first update
// (bomb.cpp:468-476 isAnimStart = escaped + floor triangle).
bool traceFloor(void*, const P2BombSaraiVec3& position, const P2BombSaraiVec3& velocity,
                float, float, P2BombSaraiTraceResult& result)
{
    result.position = position;
    result.velocity = velocity;
    result.floor = true;
    result.wall = false;
    result.groundY = 0.0f;
    result.hasGroundY = true;
    return true;
}

bool liveCarrier(void*, std::uint64_t)
{
    return true; // fixture carrier tokens are always considered live
}
}

int main()
{
    // --- Multi-carrier pool limit ---
    // A capacity-2 pool (mChildNum = 2, enemyInfo.cpp:46) serves two carriers
    // concurrently but never more; each carrier holds at most one live bomb
    // (source !mHeldBomb guard, BombSarai.cpp:265). Exhaustion returns
    // nullptr with no partial state (:266-278).
    {
        const P2BombSaraiBombConfig cfg = config(0);
        P2BombSaraiBombPool pool(2);
        P2BombSaraiVec3 joint{ 10.0f, 70.0f, 0.0f };
        assert(pool.activeCount() == 0);
        P2BombSaraiBomb* a = pool.supply(9001, joint, cfg);
        assert(a && pool.activeCount() == 1);
        P2BombSaraiBomb* b = pool.supply(9002, joint, cfg);
        assert(b && pool.activeCount() == 2);
        // Duplicate live carrier: one bomb per token -> nullptr, no change.
        assert(pool.supply(9001, joint, cfg) == nullptr && pool.activeCount() == 2);
        // Third carrier: pool exhausted -> nullptr, no partial allocation.
        assert(pool.supply(9003, joint, cfg) == nullptr && pool.activeCount() == 2);
        // Throw A and detonate it (short fuse); the freed slot serves a new
        // carrier before B's slot.
        assert(a->throwBomb(K::Death, 0.0f)); // zero-velocity drop
        for (int i = 0; i < 2000 && a->phase() != P2BombSaraiBombPhase::Despawned; ++i) {
            a->update(P2BombSaraiBomb::kSourceDelta, traceFloor, nullptr, liveCarrier, nullptr);
            if (a->phase() == P2BombSaraiBombPhase::Despawned) break;
            // pump burn/detach by re-throwing is unnecessary: the drop with a
            // floor trace arms, then the fuse runs out on its own.
        }
        assert(a->phase() == P2BombSaraiBombPhase::Despawned);
        assert(a->hasBlast());
        assert(pool.activeCount() == 1); // B still live
        P2BombSaraiBomb* c = pool.supply(9003, joint, cfg);
        assert(c && c != b && pool.activeCount() == 2);
    }

    // --- ip02 induction countdown (retail 15) ---
    // An armed bomb detonates after exactly ip02 induce() calls; each call
    // before the last returns false and leaves the bomb armed (bomb.cpp:
    // 348-368, 426-440 trigger-limit countdown).
    {
        const int ip02 = 15; // retail
        P2BombSaraiBombPool pool(1);
        P2BombSaraiBomb* bomb = pool.supply(42, { 0.0f, 70.0f, 0.0f }, config(ip02));
        assert(bomb);
        assert(bomb->throwBomb(K::Death, 0.0f));
        assert(bomb->update(P2BombSaraiBomb::kSourceDelta, traceFloor, nullptr,
                            liveCarrier, nullptr));
        assert(bomb->phase() == P2BombSaraiBombPhase::ArmedLoop);
        assert(bomb->inductionCounter() == ip02);
        for (int i = 1; i < ip02; ++i) {
            assert(!bomb->induce(liveCarrier, nullptr));
            assert(bomb->inductionCounter() == ip02 - i);
            assert(bomb->phase() == P2BombSaraiBombPhase::ArmedLoop);
            assert(!bomb->hasBlast());
        }
        // The last induce() fires the induced detonation exactly once; the
        // counter lands spent at 0 and re-fires are rejected by the guard.
        assert(bomb->induce(liveCarrier, nullptr));
        assert(bomb->inductionCounter() == 0);
        assert(bomb->phase() == P2BombSaraiBombPhase::Despawned);
        assert(bomb->hasBlast());
        const P2BombSaraiBlastEvent& blast = bomb->lastBlast();
        assert(blast.carrierToken == 42 && blast.hasCarrier && blast.carrierValid);
        assert(blast.radius == 90.0f && blast.tekiDamage == 500.0f);
        // Fully spent: further induce() returns false, no second thread.
        assert(!bomb->induce(liveCarrier, nullptr));
        assert(bomb->hasBlast());
        bomb->clearBlast();
        assert(!bomb->hasBlast());
        assert(!bomb->induce(liveCarrier, nullptr));
        assert(!bomb->hasBlast());
    }

    // --- Induced blast records on the induced bomb; slot reusable afterwards.
    // The pool serves the freed slot to a fresh carrier (detonation kills the
    // slot, supply re-arms a fresh ip02 counter from the config).
    {
        const int ip02 = 15;
        P2BombSaraiBombPool pool(1);
        P2BombSaraiBomb* bomb = pool.supply(42, { 0.0f, 70.0f, 0.0f }, config(ip02));
        assert(bomb);
        assert(bomb->throwBomb(K::Death, 0.0f));
        assert(bomb->update(P2BombSaraiBomb::kSourceDelta, traceFloor, nullptr,
                            liveCarrier, nullptr));
        assert(bomb->phase() == P2BombSaraiBombPhase::ArmedLoop);
        assert(pool.activeCount() == 1);
        for (int guard = 0; guard < 1000 && !bomb->induce(liveCarrier, nullptr); ++guard) {}
        assert(bomb->phase() == P2BombSaraiBombPhase::Despawned);
        assert(pool.activeCount() == 0); // despawned slot no longer live
        P2BombSaraiBomb* fresh = pool.supply(77, { 5.0f, 70.0f, 0.0f }, config(ip02));
        assert(fresh);
        assert(fresh->inductionCounter() == ip02); // re-armed at capture
    }

    // --- Induction guard: only ArmedLoop/Burning bombs respond. ---
    {
        const int ip02 = 3;
        P2BombSaraiBomb bomb;
        bomb.reset(config(ip02));
        // Captured: constrained + invulnerable (bomb.cpp:23-44), no response.
        assert(bomb.capture(1, { 0.0f, 70.0f, 0.0f }));
        assert(!bomb.induce(liveCarrier, nullptr));
        assert(bomb.inductionCounter() == ip02);
        // InFlight (no floor triangle yet): no response.
        assert(bomb.throwBomb(K::Death, 0.0f));
        assert(!bomb.induce(liveCarrier, nullptr));
        assert(bomb.inductionCounter() == ip02);
        // ArmedLoop: one to go after two induce() calls.
        assert(bomb.update(P2BombSaraiBomb::kSourceDelta, traceFloor, nullptr,
                           liveCarrier, nullptr));
        assert(bomb.phase() == P2BombSaraiBombPhase::ArmedLoop);
        assert(!bomb.induce(liveCarrier, nullptr));
        assert(!bomb.induce(liveCarrier, nullptr));
        assert(bomb.inductionCounter() == 1);
        assert(bomb.induce(liveCarrier, nullptr));
        assert(bomb.phase() == P2BombSaraiBombPhase::Despawned);
    }

    // --- ip02 = 0 disables induction entirely (config default). ---
    {
        P2BombSaraiBombPool pool(1);
        P2BombSaraiBomb* bomb = pool.supply(5, { 0.0f, 70.0f, 0.0f }, config(0));
        assert(bomb);
        assert(bomb->throwBomb(K::Death, 0.0f));
        assert(bomb->update(P2BombSaraiBomb::kSourceDelta, traceFloor, nullptr,
                            liveCarrier, nullptr));
        assert(bomb->phase() == P2BombSaraiBombPhase::ArmedLoop);
        assert(bomb->inductionCounter() == 0);
        for (int i = 0; i < 10; ++i) {
            assert(!bomb->induce(liveCarrier, nullptr));
        }
        assert(bomb->phase() == P2BombSaraiBombPhase::ArmedLoop); // never fires
        assert(!bomb->hasBlast());
    }

    // --- Full bomb-on-bomb chain: A detonates on its own fuse, the fixture
    // host routes its blast to B (host-owned radius gate, our standalone
    // stand-in simply calls induce), and B's ip02 exhaustion fires the second
    // blast with B's carrier attribution (bomb.cpp:426-440).
    {
        const int ip02 = 2; // short chain so this stays readable
        P2BombSaraiBombPool pool(2);
        P2BombSaraiBomb* a = pool.supply(101, { 0.0f, 70.0f, 0.0f }, config(ip02));
        P2BombSaraiBomb* b = pool.supply(102, { 80.0f, 70.0f, 0.0f }, config(ip02));
        assert(a && b && pool.activeCount() == 2);
        // A falls at the origin and arms; then its fuse drains naturally.
        assert(a->throwBomb(K::Death, 0.0f));
        assert(a->update(P2BombSaraiBomb::kSourceDelta, traceFloor, nullptr,
                         liveCarrier, nullptr));
        assert(a->phase() == P2BombSaraiBombPhase::ArmedLoop);
        // B arms at 80 units away (within the 90-unit retail blast radius).
        assert(b->throwBomb(K::Death, 0.0f));
        assert(b->update(P2BombSaraiBomb::kSourceDelta, traceFloor, nullptr,
                         liveCarrier, nullptr));
        assert(b->phase() == P2BombSaraiBombPhase::ArmedLoop);
        // Pump A through the 30-tick arm loop and the fuse burn; it detonates
        // on its own timer (blast radius 90 reaches B at 80 units).
        for (int i = 0; i < 2000 && a->phase() != P2BombSaraiBombPhase::Despawned; ++i) {
            a->update(P2BombSaraiBomb::kSourceDelta, traceFloor, nullptr,
                      liveCarrier, nullptr);
        }
        assert(a->phase() == P2BombSaraiBombPhase::Despawned && a->hasBlast());
        assert(b->phase() == P2BombSaraiBombPhase::ArmedLoop); // untouched so far
        // Host routes A's blast to B: B is inside A's volume (the policy's
        // host owns the radius gate; the fixture just invokes the effect).
        const int bip02 = b->inductionCounter();
        for (int i = 1; i < bip02; ++i) {
            assert(!b->induce(liveCarrier, nullptr));
        }
        assert(b->induce(liveCarrier, nullptr));
        assert(b->phase() == P2BombSaraiBombPhase::Despawned);
        assert(b->hasBlast());
        assert(b->lastBlast().carrierToken == 102 && b->lastBlast().carrierValid);
        assert(pool.activeCount() == 0); // both slots spent
    }

    std::puts("PASS BOMBSARAI_INDUCTION");
    return 0;
}