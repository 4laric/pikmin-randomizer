// #244 OWN: engine-free source-faithful BombSarai machine gates.
#include "pc_p2_bombsarai_own.h"

#include <cmath>
#include <cstdio>
#include <sstream>
#include <vector>

using namespace p2bsown;

static int sFail = 0;
#define CHECK(cond, msg)                                                          \
    do {                                                                          \
        if (!(cond)) {                                                            \
            std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, msg);             \
            ++sFail;                                                              \
        }                                                                         \
    } while (0)

namespace {
bool near(float a, float b, float eps = 1e-4f) { return std::fabs(a - b) <= eps; }

// Minimal host: integrates the machine's velocity like the P1 vehicle does
// (flyer: no gravity; grounded: 560 u/s^2 gravity with the floor at y = 0).
struct Host {
    Fsm fsm;
    Vec3 pos{0.0f, 0.0f, 0.0f};
    float vy = 0.0f;
    std::vector<Candidate> cands;
    int stuck = 0;
    float health = 1500.0f;
    bool carrying = false;
    TickOutput last;
    std::vector<State> seen;
    void step() {
        TickInput in;
        in.position = pos;
        in.groundY = 0.0f;
        in.health = health;
        in.stuckPikmin = stuck;
        in.carrying = carrying;
        in.candidates = cands.data();
        in.count = cands.size();
        last = fsm.tick(in);
        for (State s : last.entered) seen.push_back(s);
        if (last.supply) carrying = true;
        if (last.throwBomb) carrying = false;
        pos.x += last.velocity.x * kSourceDelta;
        pos.z += last.velocity.z * kSourceDelta;
        if (last.flying) {
            vy = last.velocity.y;
        } else {
            vy -= 560.0f * kSourceDelta;
        }
        pos.y += vy * kSourceDelta;
        if (pos.y < 0.0f) { pos.y = 0.0f; vy = 0.0f; }
    }
    bool saw(State s) const {
        for (State x : seen) if (x == s) return true;
        return false;
    }
};
} // namespace

int main() {
    Params p; // retail defaults
    // --- flick chance lerp (BombSarai.cpp:326-330) ---
    CHECK(near(Fsm::flickChance(p, 1), 0.2f), "1 stuck = fp31 0.2");
    CHECK(near(Fsm::flickChance(p, 2), 0.35f), "2 stuck = 0.35");
    CHECK(near(Fsm::flickChance(p, 3), 0.5f), "3 stuck = 0.5");
    CHECK(near(Fsm::flickChance(p, 5), 0.8f), "5 stuck = fp32 0.8");
    CHECK(near(Fsm::flickChance(p, 9), 0.8f), "clamped above 5");

    // --- retail parm parse ---
    {
        const char* text =
            "{\n{s003} 4 0.100000\n{_eof}\n{\n{fp00} 4 1500.0\n{fp14} 4 200.0\n{fp06} 4 60.0\n{fp28} 4 2.0\n"
            "{fp31} 4 0.0\n{_eof}\n{\n{fp01} 4 70.0\n{fp03} 4 50.0\n{fp31} 4 0.2\n{fp32} 4 0.8\n{fp40} 4 0.8\n{_eof}\n";
        std::istringstream in(text);
        Params q;
        q.flightHeight = 1.0f;
        std::string error;
        CHECK(parseEnemyParm(in, q, error), "parse retail parm");
        CHECK(q.retail && near(q.flightHeight, 70.0f) && near(q.freeFlick, 0.2f) && near(q.regenRate, 0.0f),
              "proper/general values");
        std::istringstream bad("{\n{fp01} 4 70.0\n{_eof}\n");
        Params r;
        CHECK(!parseEnemyParm(bad, r, error), "missing general fails closed");
    }
    // --- bank grammar ---
    {
        std::istringstream in("P2_BOMBSARAI_OWN_BANK_1 1\n"
                              "clip 12 wait1 60 2 10 0 49 1 2 0 0 1.0 -30.0 5.0 25 3 1.5 -31.0 5.0\n"
                              "bomb hit_loop 8 2 0 0 4 1\nEND\n");
        Bank b = defaultBank();
        std::string error;
        CHECK(parseBank(in, b, error), "parse bank");
        CHECK(b.staged && b.clip[AnimWait].poses.size() == 2 && b.clip[AnimWait].poses[1].file == 3
                  && near(b.clip[AnimWait].poses[1].kamu.y, -31.0f) && b.bombClipCount == 1,
              "bank contents");
        std::istringstream bad("P2_BOMBSARAI_OWN_BANK_1 1\nclip 12 wait1 60 0 0\n");
        Bank c = defaultBank();
        CHECK(!parseBank(bad, c, error), "missing END fails closed");
    }

    const Bank bank = defaultBank();
    // --- hover: spawn on the floor, rise to fp01 +- fp11, Untargetable ---
    {
        Host h;
        h.fsm.init(p, bank, h.pos, 0.0f, 7u);
        CHECK(h.fsm.state() == State::Wait && h.fsm.flying(), "starts in Wait, Untargetable");
        float minY = 1e9f, maxY = -1e9f;
        for (int i = 0; i < 300; ++i) {
            h.step();
            if (i > 120) { minY = std::fmin(minY, h.pos.y); maxY = std::fmax(maxY, h.pos.y); }
        }
        CHECK(h.last.flying, "hovering is flying");
        CHECK(minY > 70.0f - 20.0f - 5.0f && maxY < 70.0f + 20.0f + 5.0f, "hover band 70 +- 20");
        CHECK(h.saw(State::Move), "idle Wait times out into Move (3 s)");
    }
    // --- target in sight: Supply -> BombMove -> Release throws ---
    {
        Host h;
        h.pos = {0.0f, 70.0f, 0.0f};
        h.fsm.init(p, bank, h.pos, 0.0f, 11u);
        Candidate piki;
        piki.id = 1;
        piki.pikmin = true;
        piki.alive = piki.searchable = true;
        piki.pos = {0.0f, 0.0f, 40.0f}; // ahead, inside fp20 3D range 100 and fp21 45 deg
        h.cands.push_back(piki);
        bool supplied = false, threw = false;
        for (int i = 0; i < 600 && !threw; ++i) {
            h.step();
            supplied |= h.last.supply;
            threw |= h.last.throwBomb;
        }
        CHECK(supplied && h.saw(State::Supply), "Supply births the bomb");
        CHECK(h.saw(State::BombMove), "Supply END -> BombMove");
        CHECK(h.saw(State::Release) && threw, "Release KEYEVENT_2 throws");
        CHECK(near(h.last.throwVelocity.y, 100.0f), "release lob vy 100");
    }
    // --- latch: stuck Pikmin while hovering -> gate -> Fall/Flick; Fall
    // grounds, Damage struggles, TakeOff returns to hover ---
    {
        Host h;
        h.pos = {0.0f, 70.0f, 0.0f};
        h.fsm.init(p, bank, h.pos, 0.0f, 3u);
        for (int i = 0; i < 10; ++i) h.step();
        h.stuck = 1;
        h.step();
        CHECK(h.saw(State::Fall) || h.saw(State::Flick), "1 stuck resolves the height gate");
        CHECK(h.last.flickRolled && near(h.last.flickChance, 0.2f), "gate rolled fp31");
        int guard = 0;
        while (!h.saw(State::Fall) && guard++ < 400) { h.stuck = 1; h.step(); }
        CHECK(h.saw(State::Fall), "reaches Fall");
        guard = 0;
        while (!h.saw(State::Damage) && guard++ < 200) h.step();
        CHECK(h.saw(State::Damage) && !h.last.flying && h.pos.y < 1.0f, "Damage on the floor, targetable");
        h.health = 1400.0f; // above half: TakeOff1
        h.stuck = 0;
        guard = 0;
        while (!h.saw(State::TakeOff1) && guard++ < 200) h.step();
        CHECK(h.saw(State::TakeOff1), "struggle ends -> TakeOff1");
        guard = 0;
        bool grounded45 = true;
        while (h.fsm.state() == State::TakeOff1 && guard++ < 400) {
            h.step();
            if (h.fsm.state() == State::TakeOff1 && h.fsm.animator().frame() < 44.0f && h.last.flying)
                grounded45 = false;
        }
        CHECK(grounded45, "TakeOff1 targetable until frame 45");
        CHECK(h.saw(State::Move) && h.last.flying, "TakeOff END -> Move, hovering again");
    }
    // --- death: health 0 while hovering -> Fall -> Dead -> kill ---
    {
        Host h;
        h.pos = {0.0f, 70.0f, 0.0f};
        h.fsm.init(p, bank, h.pos, 0.0f, 5u);
        h.step();
        h.health = 0.0f;
        bool kill = false;
        for (int i = 0; i < 400 && !kill; ++i) {
            h.step();
            kill = h.last.killRequest;
        }
        CHECK(h.saw(State::Fall) && h.saw(State::Dead), "Fall -> Dead");
        CHECK(kill, "Dead KEYEVENT_END requests kill()");
    }
    // --- flick: forced by a 5-stack at a low seed eventually flicks ---
    {
        int flicks = 0;
        for (std::uint32_t seed = 1; seed < 40 && !flicks; ++seed) {
            Host h;
            h.pos = {0.0f, 70.0f, 0.0f};
            h.fsm.init(p, bank, h.pos, 0.0f, seed);
            Candidate s;
            s.id = 1; s.pikmin = true; s.alive = true; s.stuckToSelf = true;
            h.cands.push_back(s);
            h.stuck = 5;
            for (int i = 0; i < 60; ++i) {
                h.step();
                if (h.last.flick) { flicks += int(h.last.flickStick.size()); break; }
                if (h.fsm.state() == State::Fall) break;
            }
        }
        CHECK(flicks > 0, "Flick KEYEVENT_2 flicks stuck Pikmin");
    }
    if (sFail) {
        std::printf("p2_bombsarai_own_test: %d failure(s)\n", sFail);
        return 1;
    }
    std::printf("p2_bombsarai_own_test: all checks passed\n");
    return 0;
}
