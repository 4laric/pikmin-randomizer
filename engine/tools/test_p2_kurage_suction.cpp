// Engine-free checks for the Jellyfloat suction polish (#960, owner playtest 2026-09-30):
// who the suction may take, where the stomach is in the drawn pose, and when the wind emits.
#include "pc_p2_kurage_fx.h"
#include "pc_p2_kurage_proom.h"
#include "pc_p2_kurage_suction_policy.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_kurage_suction_test: %s\n", what);
        std::fflush(stdout);
        std::_Exit(1);
    }
}

int main()
{
    using namespace p2kuragesuck;
    // The old gate (mayIstick) refused every Pikmin standing under the bell.
    require(pikiSuckable(true, false, kStateNormal, false), "standing Pikmin is suckable");
    require(pikiSuckable(true, false, kStatePush, false), "pushed Pikmin is suckable");
    require(pikiSuckable(true, false, kStateEmotion, false), "emoting Pikmin is suckable");
    require(!pikiSuckable(true, false, kStateFlying, true), "mid-throw Pikmin is never taken, even when mayIstick");
    require(!pikiSuckable(false, false, kStateNormal, true), "dead Pikmin is refused");
    require(!pikiSuckable(true, true, kStateNormal, true), "Pikmin already stuck is refused");
    require(!pikiSuckable(true, false, 6 /*Dying*/, false), "dying Pikmin is refused");
    require(!pikiSuckable(true, false, 12 /*Hanged*/, false), "Pikmin held by the captain is refused");
    require(pikiSuckable(true, false, 17 /*Fall*/, true), "a mayIstick Pikmin the old gate admitted stays admitted");

    // Hold ring: first on the part centre, the rest inside the sphere, all distinct.
    HoldOffset first = holdOffset(0, 15.0f);
    require(first.x == 0.0f && first.y == 0.0f && first.z == 0.0f, "first held Pikmin on the part centre");
    for (int i = 1; i < 10; ++i) {
        HoldOffset o = holdOffset(i, 15.0f);
        require(std::sqrt(o.x * o.x + o.z * o.z) < 15.0f, "ring stays inside the stomach sphere");
        for (int j = 0; j < i; ++j) {
            HoldOffset q = holdOffset(j, 15.0f);
            const float d = std::sqrt((o.x - q.x) * (o.x - q.x) + (o.z - q.z) * (o.z - q.z));
            require(d > 0.5f, "held Pikmin do not stack");
        }
    }

    // Stomach position in the drawn pose (retail Proom joint): inside the bell bounds of that pose.
    using p2kurage::Variant;
    struct Bounds { const char* pose; float lesserMin, lesserMax, greaterMin, greaterMax; };
    const Bounds bounds[] = {
        {"wait", -1.5f, 50.9f, -2.3f, 77.1f}, {"move1", -1.8f, 60.5f, -2.7f, 91.7f},
        {"attack", -2.8f, 22.0f, -4.3f, 33.3f}, {"type2", -1.8f, 60.5f, -2.7f, 91.7f},
    };
    for (const Bounds& b : bounds) {
        const p2kurageown::ProomOffset l = p2kurageown::proomOffset(Variant::Lesser, b.pose);
        const p2kurageown::ProomOffset g = p2kurageown::proomOffset(Variant::Greater, b.pose);
        require(l.y > b.lesserMin && l.y < b.lesserMax, "Lesser stomach inside the drawn bell");
        require(g.y > b.greaterMin && g.y < b.greaterMax, "Greater stomach inside the drawn bell");
        require(l.y > 0.0f && g.y > 0.0f, "stomach above the body origin (the old hold was 15-25 below it)");
    }
    require(p2kurageown::proomOffset(Variant::Lesser, "attack").y == 6.1f, "Lesser attack-pose Proom");
    require(p2kurageown::proomOffset(Variant::Greater, "wait").y == 17.0f, "Greater wait-pose Proom");
    require(p2kurageown::proomOffset(Variant::Lesser, nullptr).y == p2kurageown::proomOffset(Variant::Lesser, "move1").y,
            "unknown pose falls back to move1");
    require(p2kurageown::proomOffset(Variant::Greater, "nope").y == 41.4f, "unknown name falls back to move1 (Greater)");

    // Wind: emits only while the suction window is open, starts and ends once.
    p2kuragefx::State st;
    p2kuragefx::Command c = p2kuragefx::suctionTick(st, false, 1, 50, 2, -60);
    require(c.kind == p2kuragefx::Kind::None && !c.windowStart && !c.windowEnd, "no wind before the window");
    int emitted = 0, starts = 0, ends = 0;
    for (int i = 0; i < 30; ++i) {
        c = p2kuragefx::suctionTick(st, true, 1, 50, 2, -60);
        require(c.kind == p2kuragefx::Kind::Suction, "wind every tick of the window");
        require(c.x == 1 && c.z == 2 && c.y == -58.0f && c.topY == 50, "emitter on the ground under the body, jet to the bell");
        if (c.windowStart) ++starts;
        ++emitted;
    }
    require(starts == 1 && emitted == 30, "one window start");
    c = p2kuragefx::suctionTick(st, false, 1, 50, 2, -60);
    require(c.kind == p2kuragefx::Kind::None && c.windowEnd && c.emittedInWindow == 30, "window end reports the count");
    c = p2kuragefx::suctionTick(st, false, 1, 50, 2, -60);
    require(c.kind == p2kuragefx::Kind::None && !c.windowEnd, "no wind after the window");
    (void)ends;
    // Deterministic: same inputs, same commands.
    p2kuragefx::State a, b;
    for (int i = 0; i < 100; ++i) {
        const bool s = (i / 7) % 2 == 1;
        const p2kuragefx::Command x = p2kuragefx::suctionTick(a, s, float(i), 10, 3, 0);
        const p2kuragefx::Command y = p2kuragefx::suctionTick(b, s, float(i), 10, 3, 0);
        require(x.kind == y.kind && x.x == y.x && x.windowStart == y.windowStart && x.windowEnd == y.windowEnd, "deterministic");
    }
    std::printf("PASS p2_kurage_suction_test (%d checks)\n", gChecks);
    return 0;
}
