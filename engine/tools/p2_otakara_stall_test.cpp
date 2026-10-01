// p2_otakara_stall_test (Dweevil family fidelity): source horizontal speed on slopes and the
// stalled-Move side-step (pc_p2_otakara_stall.h), engine-free.
//
// Owner playtest 2026-09-30: "too slow" and "trouble pathfinding, stuck on a slope". Source:
// EnemyFunc::walkToTarget -> EnemyBase::setTargetSpeed sets the HORIZONTAL target velocity to
// exactly fp06 (EnemyBase.h:419-427); the P1 host projects the drive onto the ground plane and
// re-normalises it (creature.cpp moveVelocity), so the horizontal part shrinks with the slope.
// The pre-fix behaviour is modelled by `p1Horizontal(..., gain = 1)`.
//
// Negative controls:
//   * -DP2_OTAKARA_STALL_TEST_LEGACY commands the raw fp06 (gain 1) and never side-steps, so the
//     test fails.
//   * Passing a source root as argv[1] that holds the pre-fix pc_p2_otakara.cpp makes the wiring
//     checks fail.
//
// NOTE: checks use an always-evaluated CHECK macro, never bare assert().
#include "pc_p2_otakara_stall.h"

#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

#ifndef P2_OTAKARA_STALL_SOURCE_ROOT
#define P2_OTAKARA_STALL_SOURCE_ROOT "."
#endif

using namespace p2otakarastall;

static int failures = 0;

#define CHECK(cond)                                                                        \
    do {                                                                                   \
        if (!(cond)) {                                                                     \
            std::printf("P2_OTAKARA_STALL_TEST_FAIL line=%d check=%s\n", __LINE__, #cond); \
            ++failures;                                                                    \
        }                                                                                  \
    } while (0)

namespace {

constexpr float kDeg = 0.0174532925f;

// P1 Creature::moveVelocity on level steady state: vel = drive - (drive.n) n, renormalised to
// |drive|; returns its horizontal length.
float p1Horizontal(float nx, float ny, float nz, float dx, float dz, float driveLen) {
    const float dn = dx * nx + dz * nz; // drive = (dx, 0, dz) * driveLen
    float vx = dx - dn * nx, vy = -dn * ny, vz = dz - dn * nz;
    const float len = std::sqrt(vx * vx + vy * vy + vz * vz);
    if (len <= 0.0f) return 0.0f;
    vx = vx / len * driveLen;
    vz = vz / len * driveLen;
    return std::sqrt(vx * vx + vz * vz);
}

float commandedGain(float nx, float ny, float nz, float dx, float dz) {
#ifdef P2_OTAKARA_STALL_TEST_LEGACY
    (void)nx; (void)ny; (void)nz; (void)dx; (void)dz;
    return 1.0f;
#else
    return slopeGain(nx, ny, nz, dx, dz);
#endif
}

void checkSlopeGain() {
    const float speed = 80.0f; // fp06 (Fire/Water/Elec)
    // Level ground: no change.
    CHECK(std::fabs(commandedGain(0, 1, 0, 1, 0) - 1.0f) < 1.0e-4f);
    // A 40 degree slope tilted along x, walking straight up/down it.
    const float a = 40.0f * kDeg;
    const float nx = std::sin(a), ny = std::cos(a);
    const float h = p1Horizontal(nx, ny, 0.0f, 1.0f, 0.0f, speed * commandedGain(nx, ny, 0.0f, 1.0f, 0.0f));
    CHECK(std::fabs(h - speed) < 0.5f); // source: horizontal speed is fp06 whatever the slope
    // Across the slope nothing is lost and nothing is added.
    const float hAcross = p1Horizontal(nx, ny, 0.0f, 0.0f, 1.0f, speed * commandedGain(nx, ny, 0.0f, 0.0f, 1.0f));
    CHECK(std::fabs(hAcross - speed) < 0.5f);
    // The owner's number: at ~50 degrees the un-compensated P1 host walks at 80*cos(50) = 51 u/s
    // (the owner's Anode log averaged 44 u/s against 80 commanded; 73 u/s on the flat test slot).
    const float b = 50.0f * kDeg;
    const float raw = p1Horizontal(std::sin(b), std::cos(b), 0.0f, 1.0f, 0.0f, speed);
    CHECK(raw < 55.0f && raw > 48.0f);
    const float fixed = p1Horizontal(std::sin(b), std::cos(b), 0.0f, 1.0f, 0.0f,
                                     speed * commandedGain(std::sin(b), std::cos(b), 0.0f, 1.0f, 0.0f));
    CHECK(std::fabs(fixed - speed) < 0.5f);
    // Munge (fp06 100) follows the same rule.
    const float hm = p1Horizontal(nx, ny, 0.0f, 1.0f, 0.0f, 100.0f * commandedGain(nx, ny, 0.0f, 1.0f, 0.0f));
    CHECK(std::fabs(hm - 100.0f) < 0.6f);
#ifndef P2_OTAKARA_STALL_TEST_LEGACY
    // Never more than 1.8x: a very steep face is not driven harder and harder.
    const float c = 75.0f * kDeg;
    CHECK(slopeGain(std::sin(c), std::cos(c), 0.0f, 1.0f, 0.0f) <= kMaxGain + 1.0e-5f);
    // Random directions and slopes up to 50 degrees: the compensated horizontal speed is fp06.
    unsigned seed = 7u;
    auto rnd = [&seed]() { seed = seed * 1664525u + 1013904223u; return float((seed >> 8) & 0xffff) / 65535.0f; };
    for (int i = 0; i < 500; ++i) {
        const float tilt = rnd() * 50.0f * kDeg;
        const float dir = rnd() * 6.2831853f;
        const float nnx = std::sin(tilt) * std::cos(dir), nnz = std::sin(tilt) * std::sin(dir), nny = std::cos(tilt);
        const float hd = rnd() * 6.2831853f;
        const float dx = std::sin(hd), dz = std::cos(hd);
        const float got = p1Horizontal(nnx, nny, nnz, dx, dz, speed * slopeGain(nnx, nny, nnz, dx, dz));
        CHECK(std::fabs(got - speed) < 0.8f);
    }
#endif
}

void checkTracker() {
    Tracker t;
    // Walking normally: 0.6 s at 80 u/s is never a stall.
    for (int i = 0; i < 40; ++i) CHECK(!t.sample(1.0f / 30.0f, 80.0f / 30.0f, 80.0f / 30.0f));
    // Pinned against a slope: less than 35% of the commanded distance over 0.6 s.
    bool stalled = false;
    for (int i = 0; i < 40 && !stalled; ++i) stalled = t.sample(1.0f / 30.0f, 0.2f, 80.0f / 30.0f);
#ifdef P2_OTAKARA_STALL_TEST_LEGACY
    CHECK(stalled); // legacy has no detector: this check must fail
#else
    CHECK(stalled);
    CHECK(t.stalls == 1);
#endif
    // Standing still commands nothing: not a stall.
    Tracker s;
    for (int i = 0; i < 60; ++i) CHECK(!s.sample(1.0f / 30.0f, 0.0f, 0.0f));
    // Hold ticks down and expires.
    Tracker h;
    h.hold = kHold;
    CHECK(h.holding());
    for (int i = 0; i < 60; ++i) h.tickHold(1.0f / 30.0f);
    CHECK(!h.holding());
    h.reset();
    CHECK(!h.holding());
}

void checkWalkable() {
    Probe here{true, 0.0f, 1.0f, 0};
    Probe ok1{true, 5.0f, 0.95f, 0}, ok2{true, 10.0f, 0.95f, 0};
    CHECK(walkable(here, ok1, ok2));
    CHECK(!walkable(here, Probe{}, ok2));                          // no ground under the near probe
    CHECK(!walkable(here, ok1, Probe{true, 10.0f, 0.5f, 0}));      // normal.y below the ground threshold
    CHECK(!walkable(here, Probe{true, 5.0f, 0.95f, 2}, ok2));      // slip-coded triangle
    CHECK(!walkable(here, ok1, Probe{true, 120.0f, 0.95f, 0}));    // a cliff/step: rise > 1.3 * run
    CHECK(walkable(here, Probe{true, 40.0f, 0.7f, 0}, Probe{true, 80.0f, 0.7f, 0})); // 50 degree ramp is fine
}

void checkSideStep() {
    // pickSide returns the first walkable offset in the alternating order.
    bool ok[6] = {false, false, true, true, true, true};
    const int pos = pickSide(ok, true);
    CHECK(pos == 2 && sideOffsetDeg(pos) == 90);
    const int neg = pickSide(ok, false);
    CHECK(neg == 3 && sideOffsetDeg(neg) == -90);
    bool none[6] = {false, false, false, false, false, false};
    CHECK(pickSide(none, true) == -1);
    bool first[6] = {true, true, true, true, true, true};
    CHECK(sideOffsetDeg(pickSide(first, true)) == 45);
    CHECK(sideOffsetDeg(pickSide(first, false)) == -45);
    // A slope-blocked escape: the ground straight ahead and +/-45 is unwalkable, 90 is open; the
    // side-step heading is perpendicular to the blocked one.
    bool blocked[6] = {false, false, true, true, true, true};
    const int pick = pickSide(blocked, true);
    const float heading = 0.0f + float(sideOffsetDeg(pick)) * kDeg;
    CHECK(std::fabs(std::fabs(heading) - 90.0f * kDeg) < 1.0e-4f);
}

std::string readFile(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return std::string();
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

std::string functionBody(const std::string& text, const std::string& signature) {
    const size_t at = text.find(signature);
    if (at == std::string::npos) return std::string();
    size_t end = text.find("\n}", at);
    if (end == std::string::npos) end = text.size();
    return text.substr(at, end - at);
}

void checkWiring(const std::string& root) {
    const std::string glue = readFile(root + "/pc_port/pc_p2_otakara.cpp");
    CHECK(!glue.empty());
    const std::string walk = functionBody(glue, "void walkStep(BTeki* a, Otakara& s");
    CHECK(!walk.empty());
    CHECK(walk.find("p2otakarastall::slopeGain(") != std::string::npos);
    CHECK(walk.find("s.stall.sample(") != std::string::npos);
    CHECK(walk.find("onStall(") != std::string::npos);
    const std::string stall = functionBody(glue, "void onStall(BTeki* a, Otakara& s");
    CHECK(stall.find("P2_OTAKARA_STALL") != std::string::npos);
    CHECK(stall.find("pickSide(") != std::string::npos);
    // No teleport: the side-step only changes the heading handed to the drive.
    CHECK(stall.find("mSRT.t") == std::string::npos);
    CHECK(walk.find("mSRT.t") == std::string::npos);
    // Move and Take both walk through it.
    CHECK(glue.find("walkStep(actor, s, pos, dt)") != std::string::npos);
}

} // namespace

int main(int argc, char** argv) {
    checkSlopeGain();
    checkTracker();
    checkWalkable();
    checkSideStep();
    checkWiring(argc > 1 ? std::string(argv[1]) : std::string(P2_OTAKARA_STALL_SOURCE_ROOT));
    if (failures) {
        std::printf("FAIL p2_otakara_stall_test failures=%d\n", failures);
        return 1;
    }
    std::printf("PASS p2_otakara_stall_test\n");
    return 0;
}
