// p2_otakara_attack_test (Dweevil family fidelity): the elemental attack window and the effect
// start/stop lifecycle (pc_p2_otakara_attack.h, pc_p2_otakara_fxplan.h), engine-free.
//
// Owner playtest 2026-09-30: "visual indicator for the attack itself, not just for how it
// affects the pikmin" and "check for lingering visual effects after its attack is done".
// Pre-fix (pc_p2_otakara_fx.h): a one-shot particle per discharge at the feet, never stopped
// (pc_p2_otakara_fx_update/clear/reset had no caller), no charge visual at the body, and a
// single-frame discharge instead of the one-second attackTarget() window. The pre-fix lifecycle
// is modelled by `LegacyDriver` (start at the discharge, never stop).
//
// Negative controls:
//   * -DP2_OTAKARA_ATTACK_TEST_LEGACY drives the pre-fix lifecycle, so the test fails.
//   * Passing a source root as argv[1] that holds the pre-fix pc_p2_otakara.cpp makes the wiring
//     checks fail.
//
// NOTE: checks use an always-evaluated CHECK macro, never bare assert().
#include "pc_p2_otakara_attack.h"
#include "pc_p2_otakara_fxplan.h"

#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

#ifndef P2_OTAKARA_ATTACK_SOURCE_ROOT
#define P2_OTAKARA_ATTACK_SOURCE_ROOT "."
#endif

using namespace p2otakaraattack;

static int failures = 0;

#define CHECK(cond)                                                                         \
    do {                                                                                    \
        if (!(cond)) {                                                                      \
            std::printf("P2_OTAKARA_ATTACK_TEST_FAIL line=%d check=%s\n", __LINE__, #cond); \
            ++failures;                                                                     \
        }                                                                                   \
    } while (0)

namespace {

// The glue's lifecycle in policy terms: charge at Flick entry, stop charge + open the window +
// start discharge at event 3, close the window after one second, stop everything on death/forget.
struct Driver {
    Ledger fx;
    float timer = kIdle;
    int charged = 0;   // generators alive for the charge visual
    int burst = 0;     // generators alive for the discharge visual
    int frames = 0;    // attack frames applied
    int plannedCharge = 2;
    int plannedBurst = 7;

    void flickEntry() {
#ifndef P2_OTAKARA_ATTACK_TEST_LEGACY
        if (fx.start(Kind::Charge)) charged = plannedCharge;
#endif
    }
    void dischargeEvent() {
#ifdef P2_OTAKARA_ATTACK_TEST_LEGACY
        // Pre-fix: one fire-and-forget generator per discharge, single application.
        burst += 1;
        frames += 1;
#else
        if (fx.stop(Kind::Charge)) charged = 0;
        windowOpen(timer);
        if (fx.start(Kind::Discharge)) burst = plannedBurst;
#endif
    }
    void tick(float dt) {
#ifndef P2_OTAKARA_ATTACK_TEST_LEGACY
        if (windowStep(timer, dt)) ++frames;
        if (fx.on[int(Kind::Discharge)] && !windowActive(timer)) {
            fx.stop(Kind::Discharge);
            burst = 0;
        }
#else
        (void)dt;
#endif
    }
    void flickAbort() {
#ifndef P2_OTAKARA_ATTACK_TEST_LEGACY
        if (fx.stop(Kind::Charge)) charged = 0;
#endif
    }
    void dead() {
#ifndef P2_OTAKARA_ATTACK_TEST_LEGACY
        if (fx.stop(Kind::Discharge)) burst = 0;
        if (fx.stop(Kind::Charge)) charged = 0;
        timer = kIdle;
#endif
    }
    bool clean() const {
#ifndef P2_OTAKARA_ATTACK_TEST_LEGACY
        return fx.balanced() && charged == 0 && burst == 0;
#else
        return burst == 0; // legacy leaves the generator running
#endif
    }
};

void checkWindow() {
    float timer = kIdle;
    CHECK(!windowStep(timer, 1.0f / 30.0f)); // idle: attackTarget never runs
    windowOpen(timer);
    int frames = 0;
    while (windowStep(timer, 1.0f / 30.0f) && frames < 100) ++frames;
    CHECK(frames >= 30 && frames <= 31); // one second of frames, not one frame
    CHECK(!windowActive(timer));
    // It runs in any state: the window continues after the Flick clip (50 frames) ends. The
    // discharge event is frame 35; the window covers frames 35..65.
    const float flickEnd = 50.0f / 30.0f;
    const float eventAt = 35.0f / 30.0f;
    CHECK(eventAt + kWindow > flickEnd);
    CHECK(eventAt + kWindow - flickEnd > 0.4f);
}

void checkReach() {
    CHECK(inReach(0.0f, 0.0f, 0.0f));
    CHECK(inReach(59.0f, 0.0f, 0.0f));
    CHECK(!inReach(60.0f, 0.0f, 0.0f)); // strict < fp22
    CHECK(!inReach(43.0f, 43.0f, 0.0f)); // 60.8 diagonal
    CHECK(inReach(0.0f, 0.0f, 24.9f));
    CHECK(!inReach(0.0f, 0.0f, 25.0f));   // below the +25 ceiling
    CHECK(inReach(0.0f, 0.0f, -24.9f));
    CHECK(!inReach(0.0f, 0.0f, -25.0f));
}

void checkLedger() {
    Ledger l;
    CHECK(l.start(Kind::Charge));
    CHECK(!l.start(Kind::Charge));   // a second start spawns nothing
    CHECK(l.anyOn());
    CHECK(l.stop(Kind::Charge));
    CHECK(!l.stop(Kind::Charge));    // a second stop kills nothing
    CHECK(l.balanced());
    CHECK(l.starts[0] == 1 && l.stops[0] == 1);
    CHECK(l.start(Kind::Discharge));
    CHECK(!l.balanced());
    CHECK(l.stop(Kind::Discharge));
    CHECK(l.balanced());
    CHECK(std::string(kindName(Kind::Charge)) == "charge");
    CHECK(std::string(reasonName(Reason::WindowEnd)) == "window_end");
    CHECK(onDischargeEvent().charge && !onDischargeEvent().discharge);
    CHECK(!onWindowEnd().charge && onWindowEnd().discharge);
    CHECK(onDead().charge && onDead().discharge);
    CHECK(onForget().charge && onForget().discharge);
}

void checkPlans() {
    for (int species : {59, 60, 61, 62}) {
        const p2otakarafx::Plan c = p2otakarafx::charge(species);
        const p2otakarafx::Plan d = p2otakarafx::discharge(species);
        CHECK(c.count >= 1);
        CHECK(d.count >= 1);
        CHECK(p2otakarafx::generators(c) >= 1 && p2otakarafx::generators(c) <= p2otakarafx::kMaxGenerators);
        CHECK(p2otakarafx::generators(d) >= 1 && p2otakarafx::generators(d) <= p2otakarafx::kMaxGenerators);
        for (int i = 0; i < c.count; ++i) {
            CHECK(std::string(p2otakarafx::effectName(c.emit[i].effect)) != "EFF_UNKNOWN");
            CHECK(c.emit[i].copies >= 1 && c.emit[i].scale >= 1.0f); // followed by the body; rings keep their offsets
        }
        for (int i = 0; i < d.count; ++i) CHECK(std::string(p2otakarafx::effectName(d.emit[i].effect)) != "EFF_UNKNOWN");
    }
    // The four elements do not share one discharge visual.
    CHECK(p2otakarafx::discharge(59).emit[0].effect != p2otakarafx::discharge(60).emit[0].effect);
    CHECK(p2otakarafx::discharge(61).emit[0].effect != p2otakarafx::discharge(62).emit[0].effect);
    // BombOtakara (93) delegates its blast to the Bomb payload: no elemental visual.
    CHECK(p2otakarafx::charge(93).count == 0);
    CHECK(p2otakarafx::discharge(93).count == 0);
}

void checkLifecycle() {
    const float dt = 1.0f / 30.0f;
    // Normal attack: entry, discharge at frame 35, window ends, clip ends.
    {
        Driver d;
        d.flickEntry();
        for (int f = 0; f < 35; ++f) d.tick(dt);
        CHECK(d.charged == 2);
        d.dischargeEvent();
        CHECK(d.charged == 0);
        for (int f = 0; f < 80; ++f) d.tick(dt);
        CHECK(d.clean());
        CHECK(d.frames >= 30);
    }
    // Died mid-window.
    {
        Driver d;
        d.flickEntry();
        d.dischargeEvent();
        for (int f = 0; f < 10; ++f) d.tick(dt);
        d.dead();
        CHECK(d.clean());
    }
    // Died during the wind-up.
    {
        Driver d;
        d.flickEntry();
        for (int f = 0; f < 12; ++f) d.tick(dt);
        d.dead();
        CHECK(d.clean());
    }
    // Flick left without its discharge event.
    {
        Driver d;
        d.flickEntry();
        d.flickAbort();
        CHECK(d.clean());
    }
    // Fuzz: random sequences of attacks, aborts and deaths always end clean, and every start has
    // exactly one stop.
    unsigned seed = 12345u;
    auto rnd = [&seed]() { seed = seed * 1664525u + 1013904223u; return (seed >> 16) & 0xffff; };
    for (int run = 0; run < 400; ++run) {
        Driver d;
        for (int step = 0; step < 40; ++step) {
            switch (rnd() % 6) {
            case 0: d.flickEntry(); break;
            case 1: d.dischargeEvent(); break;
            case 2: for (int k = 0; k < int(rnd() % 50); ++k) d.tick(dt); break;
            case 3: d.flickAbort(); break;
            default: break;
            }
        }
        d.dead();
        for (int k = 0; k < 40; ++k) d.tick(dt);
        CHECK(d.clean());
    }
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
    // The one-shot, never-stopped fx module is no longer the attack visual.
    CHECK(glue.find("pc_p2_otakara_fx_on_discharge(") == std::string::npos);
    // Charge starts at Flick entry (enter), stops at event 3; the window runs in any state.
    const std::string enterFn = functionBody(glue, "void enter(BTeki* a, Otakara& s, State state");
    CHECK(enterFn.find("fxStart(s, Kind::Charge") != std::string::npos);
    CHECK(enterFn.find("Reason::Abort") != std::string::npos);
    const std::string dis = functionBody(glue, "void doDischarge(BTeki* a, Otakara& s)");
    CHECK(dis.find("fxStop(s, Kind::Charge, Reason::Discharge") != std::string::npos);
    CHECK(dis.find("fxStart(s, Kind::Discharge") != std::string::npos);
    CHECK(dis.find("windowOpen(s.attackTimer)") != std::string::npos);
    CHECK(glue.find("windowStep(s.attackTimer, dt)") != std::string::npos);
    CHECK(glue.find("closeWindow(s, Reason::WindowEnd)") != std::string::npos);
    // Death and forget stop everything.
    CHECK(glue.find("fxStopAll(s, Reason::Dead, false)") != std::string::npos);
    CHECK(glue.find("fxStopAll(s, Reason::Forget, true)") != std::string::npos);
    // The paired log lines exist.
    CHECK(glue.find("P2_OTAKARA_FX_START") != std::string::npos);
    CHECK(glue.find("P2_OTAKARA_FX_STOP") != std::string::npos);
    // The followed charge emitters chase the body.
    CHECK(glue.find("fxFollow(s, bodyWorld(actor, s))") != std::string::npos);
}

} // namespace

int main(int argc, char** argv) {
    checkWindow();
    checkReach();
    checkLedger();
    checkPlans();
    checkLifecycle();
    checkWiring(argc > 1 ? std::string(argv[1]) : std::string(P2_OTAKARA_ATTACK_SOURCE_ROOT));
    if (failures) {
        std::printf("FAIL p2_otakara_attack_test failures=%d\n", failures);
        return 1;
    }
    std::printf("PASS p2_otakara_attack_test\n");
    return 0;
}
