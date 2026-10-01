// #892 Gatling Groink shell burst policy (pc_p2_groink_burst.h, pc_p2_groink_volley.*).
// Source: MiniHoudaiShotGunMgr::emitShotGun (MiniHoudaiShotGun.cpp:1345-1384) runs
// `for (int i = 0; i < 3; i++)` inside one call, so a burst is three shells in the same
// source tick with +-0.1 per-axis direction jitter; nothing is staggered.
#include "pc_p2_groink_burst.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>

namespace {
void check(bool ok, const char* what) {
    if (!ok) { std::fprintf(stderr, "FAIL %s\n", what); std::exit(1); }
}
const P2GroinkMuzzle muzzle{{1, 0, 0}, {0, 1, 0}, {0, 0, 1}, {0, 40, 0}};
constexpr float kSpeed = 400.0f;
using Samples = std::array<P2GroinkVec3, 3>;
}

int main() {
    namespace B = p2groinkburst;
    // Constants pin the source loop and the retail key.
    check(B::kShots == 3 && B::kIntervalTicks == 0 && B::kSpread == 0.1f, "source burst constants");
    check(B::kEmitKeyFrame == 25 && B::kEmitKeyType == 4 && B::kMuzzleAhead == 25.0f, "emit key and muzzle offset");
    check(P2GroinkVolley::kVolleySize == std::size_t(B::kShots), "volley size == source loop count");

    // Same tick: all three shells are live and positioned the moment emit() returns.
    P2GroinkVolley pool;
    const Samples spread{{{0.0f, 0.5f, 1.0f}, {0.5f, 0.5f, 0.5f}, {1.0f, 0.0f, 0.5f}}};
    const auto e = pool.emit(muzzle, kSpeed, spread);
    check(e.valid && e.count == 3 && pool.activeCount() == 3, "one emit spawns three live shells");
    for (std::size_t i = 0; i < 3; ++i) {
        const P2GroinkShell sh = pool.shell(e.slots[i]);
        check(sh.active, "every shell is active before the next source tick");
        check(sh.position.x == 25.0f && sh.position.y == 40.0f, "shared muzzle origin 25 ahead of kuti");
        const float speed = std::sqrt(sh.velocity.x * sh.velocity.x + sh.velocity.y * sh.velocity.y + sh.velocity.z * sh.velocity.z);
        check(std::fabs(speed - kSpeed) < 0.01f, "each shell leaves at mShellSpeed");
    }
    const auto s = B::summarize(pool, e);
    check(s.shots == 3 && s.intervalTicks == 0 && s.sameTick, "summary: 3 shots, interval 0, same tick");
    check(s.primaryFirst && pool.shell(e.slots[0]).primary && !pool.shell(e.slots[1]).primary && !pool.shell(e.slots[2]).primary,
          "only the first shell is primary (camera/rumble)");
    check(s.maxSpreadDeg > 1.0f && s.maxSpreadDeg < 25.0f, "spread comes from the +-0.1 jitter");

    // Extreme jitter stays inside the source +-0.1 per axis: worst pair < 2 * atan(0.1 * sqrt(3)) ~ 19.7 deg.
    const Samples extremeA{{{0, 0, 0}, {1, 1, 1}, {0, 1, 0}}};
    P2GroinkVolley wide;
    const auto ew = wide.emit(muzzle, kSpeed, extremeA);
    const auto sw = B::summarize(wide, ew);
    check(sw.maxSpreadDeg < 19.8f, "spread never exceeds the source jitter bound");

    // Mid-range jitter (all 0.5) means no jitter: the three shells overlap exactly.
    const Samples none{{{0.5f, 0.5f, 0.5f}, {0.5f, 0.5f, 0.5f}, {0.5f, 0.5f, 0.5f}}};
    P2GroinkVolley tight;
    const auto et = tight.emit(muzzle, kSpeed, none);
    check(B::summarize(tight, et).maxSpreadDeg < 1e-3f, "zero jitter collapses the burst to one line");

    // Invalid random input rejects the whole burst and leaves the pool untouched.
    const Samples bad{{{0.5f, 0.5f, 0.5f}, {2.0f, 0.5f, 0.5f}, {0.5f, 0.5f, 0.5f}}};
    P2GroinkVolley reject;
    const auto er = reject.emit(muzzle, kSpeed, bad);
    check(!er.valid && reject.activeCount() == 0 && B::summarize(reject, er).shots == 0, "invalid sample rejects the burst");

    // Pool of six: two full bursts, then the source `if (!node) continue` skips every node.
    P2GroinkVolley full;
    check(B::expectedShots(6) == 3, "six free nodes -> three shells");
    check(full.emit(muzzle, kSpeed, spread).count == 3, "first burst");
    check(full.emit(muzzle, kSpeed, spread).count == 3 && full.activeCount() == 6, "second burst while the first is in flight");
    check(B::expectedShots(0) == 0, "no free node -> no shells");
    const auto ef = full.emit(muzzle, kSpeed, spread);
    check(ef.valid && ef.count == 0 && full.activeCount() == 6, "full pool skips every node");
    check(B::summarize(full, ef).shots == 0, "summary of a full-pool burst is empty");
    check(B::expectedShots(1) == 1 && B::expectedShots(2) == 2, "a partly free pool fires the nodes it has");

    std::puts("p2_groink_burst_test PASS");
    return 0;
}
