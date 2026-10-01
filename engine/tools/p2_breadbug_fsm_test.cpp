// Engine-free regressions for the Breadbug (PanModoki 38) source FSM port
// (pc_port/pc_p2_breadbug_fsm.*). Each block names the source lines it pins.
#include "pc_p2_breadbug_fsm.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <sstream>
#include <vector>

using namespace p2breadbugfsm;

namespace {
int failures = 0;
void check(bool ok, const char* what) {
    if (!ok) { std::fprintf(stderr, "FAIL %s\n", what); ++failures; }
}
bool near(float a, float b, float eps = 1e-3f) { return std::fabs(a - b) <= eps; }

// Retail GPVE01 panmodoki/enemyparm.txt values (creature, general, proper
// blocks; comments stripped). The proper block also carries fp00/fp14, so a
// general-block detector keyed on fp00+fp14 alone (the Groink rule) would
// read the proper block as a second general block.
const char* kRetailParm =
    "{\n{s000} 4 0.5\n{s001} 4 0.5\n{s002} 4 0.25\n{s003} 4 0.1\n{s004} 4 0.3\n{_eof}\n}\n"
    "{\n{fp00} 4 1100.0\n{fp27} 4 45.0\n{fp31} 4 0.0\n{fp30} 4 30.0\n{fp01} 4 20.0\n{fp33} 4 20.0\n"
    "{fp34} 4 20.0\n{fp32} 4 20.0\n{fp02} 4 0.5\n{fp03} 4 0.5\n{fp04} 4 0.35\n{fp05} 4 0.1\n"
    "{fp06} 4 60.0\n{fp08} 4 0.1\n{fp28} 4 3.0\n{fp09} 4 200.0\n{fp10} 4 15.0\n{fp11} 4 70.0\n"
    "{fp12} 4 300.0\n{fp25} 4 50.0\n{fp13} 4 90.0\n{fp14} 4 500.0\n{fp26} 4 50.0\n{fp15} 4 120.0\n"
    "{fp17} 4 200.0\n{fp18} 4 1.0\n{fp19} 4 30.0\n{fp16} 4 1.0\n{fp20} 4 80.0\n{fp21} 4 50.0\n"
    "{fp22} 4 80.0\n{fp23} 4 50.0\n{fp24} 4 10.0\n{fp29} 4 15.0\n{fp35} 4 1.0\n{fp36} 4 50.0\n"
    "{fp37} 4 0.0\n{fp38} 4 0.0\n{ip01} 4 0\n{ip02} 4 1\n{ip03} 4 12\n{ip04} 4 10\n{ip05} 4 17\n"
    "{ip06} 4 20\n{ip07} 4 22\n{_eof}\n}\n"
    "{\n{fp00} 4 1.0\n{fp16} 4 2.0\n{fp02} 4 0.2\n{fp05} 4 5.0\n{fp03} 4 35.0\n{fp04} 4 1000.0\n"
    "{fp06} 4 200.0\n{fp14} 4 0.0\n{fp15} 4 150.0\n{ip01} 4 11\n{_eof}\n}\n";

// Retail GPVE01 oopanmodoki/enemyparm.txt (Giant Breadbug, source 40), comments
// stripped. Same block layout as PanModoki; different values (#958).
const char* kGiantParm =
    "{\n{s000} 4 0.5\n{s001} 4 0.5\n{s002} 4 0.25\n{s003} 4 0.1\n{s004} 4 0.3\n{_eof}\n}\n"
    "{\n{fp00} 4 2000.0\n{fp27} 4 45.0\n{fp31} 4 0.0\n{fp30} 4 30.0\n{fp01} 4 40.0\n{fp33} 4 60.0\n"
    "{fp34} 4 20.0\n{fp32} 4 50.0\n{fp02} 4 0.5\n{fp03} 4 0.5\n{fp04} 4 0.35\n{fp05} 4 0.1\n"
    "{fp06} 4 85.0\n{fp08} 4 0.1\n{fp28} 4 2.0\n{fp09} 4 200.0\n{fp10} 4 30.0\n{fp11} 4 70.0\n"
    "{fp12} 4 300.0\n{fp25} 4 50.0\n{fp13} 4 90.0\n{fp14} 4 300.0\n{fp26} 4 50.0\n{fp15} 4 120.0\n"
    "{fp17} 4 200.0\n{fp18} 4 1.0\n{fp19} 4 30.0\n{fp16} 4 1.0\n{fp20} 4 80.0\n{fp21} 4 50.0\n"
    "{fp22} 4 80.0\n{fp23} 4 50.0\n{fp24} 4 10.0\n{fp29} 4 15.0\n{fp35} 4 1.0\n{fp36} 4 50.0\n"
    "{fp37} 4 0.0\n{fp38} 4 0.0\n{ip01} 4 6\n{ip02} 4 5\n{ip03} 4 12\n{ip04} 4 10\n{ip05} 4 17\n"
    "{ip06} 4 20\n{ip07} 4 22\n{_eof}\n}\n"
    "{\n{fp00} 4 2.0\n{fp16} 4 1.0\n{fp02} 4 0.2\n{fp05} 4 5.0\n{fp03} 4 45.0\n{fp04} 4 1000.0\n"
    "{fp06} 4 100.0\n{fp14} 4 0.0\n{fp15} 4 150.0\n{ip01} 4 1\n{_eof}\n}\n";

Params giantRetail() {
    Params p;
    applyVariant(p, true);
    std::istringstream in(kGiantParm);
    std::string error;
    if (!parseEnemyParm(in, p, error)) std::fprintf(stderr, "giant parse: %s\n", error.c_str());
    return p;
}

Params retail() {
    Params p;
    std::istringstream in(kRetailParm);
    std::string error;
    if (!parseEnemyParm(in, p, error)) std::fprintf(stderr, "parse: %s\n", error.c_str());
    return p;
}

// Straight corridor of waypoints along +Z, bidirectional links.
struct LineRoute : Route {
    std::vector<WayPointInfo> points;
    LineRoute(int n, float spacing) {
        for (int i = 0; i < n; ++i) {
            WayPointInfo w;
            w.index = i;
            w.pos = {0.0f, 0.0f, float(i) * spacing};
            if (i > 0) w.links[w.linkCount++] = i - 1;
            if (i + 1 < n) w.links[w.linkCount++] = i + 1;
            points.push_back(w);
        }
    }
    int nearest(const Vec3& p) const override {
        int best = -1; float bd = 1e30f;
        for (const auto& w : points) {
            const float dx = w.pos.x - p.x, dz = w.pos.z - p.z, d = dx * dx + dz * dz;
            if (d < bd) { bd = d; best = w.index; }
        }
        return best;
    }
    bool get(int i, WayPointInfo& out) const override {
        if (i < 0 || i >= int(points.size())) return false;
        out = points[size_t(i)];
        return true;
    }
    bool noPath = false;  // #898: a carry graph with no path home
    bool path(int from, int to, std::vector<int>& out) const override {
        out.clear();
        if (noPath) return false;
        const int step = from <= to ? 1 : -1;
        for (int i = from;; i += step) { out.push_back(i); if (i == to) break; }
        return true;
    }
};

// Minimal host: integrates the returned velocity when free; a stuck
// Breadbug rides its cargo at a fixed offset; the cargo moves with the
// winning pull (or the Pikmin crew's velocity when they win).
struct Host {
    Fsm fsm;
    LineRoute route{8, 200.0f};
    Vec3 pos;
    std::vector<PelletInfo> pellets;
    std::uint64_t held = 0;
    Vec3 offset;
    int presses = 0;
    bool bounce = false, suck = false;
    float external = 0.0f;
    Vec3 crewVel{0.0f, 0.0f, -40.0f};  // Pikmin haul toward -Z
    std::vector<State> seen;
    TickOutput last;
    bool consumed = false, killed = false;
    bool frozen = false;  // #898: cargo wedged against the map (never moves)

    PelletInfo* cargo() {
        for (auto& p : pellets) if (p.id == held) return &p;
        return nullptr;
    }
    TickOutput step() {
        TickInput in;
        in.position = pos;
        in.presses = presses;
        in.bounced = bounce;
        in.suckFinished = suck;
        in.externalDamage = external;
        in.held = held;
        in.pellets = pellets.data();
        in.count = pellets.size();
        in.route = &route;
        presses = 0; bounce = suck = false; external = 0.0f;
        last = fsm.tick(in);
        for (State s : last.entered) seen.push_back(s);
        if (last.stickTo) {
            held = last.stickTo;
            PelletInfo* c = cargo();
            offset = {pos.x - c->pos.x, 0.0f, pos.z - c->pos.z};
        }
        if (last.release) held = 0;
        if (last.consumeCargo) consumed = true;
        if (last.killRequest) killed = true;
        if (PelletInfo* c = cargo()) {
            Vec3 v = last.pulled ? last.pullVelocity : (c->pikiStrength > 0.0f ? crewVel : Vec3());
            if (last.holdCargo) v = last.homeNudge, v.x *= 30.0f, v.z *= 30.0f;
            if (frozen) v = Vec3();
            c->velocity = v;
            c->pos.x += v.x * kSourceDelta;
            c->pos.z += v.z * kSourceDelta;
            pos = {c->pos.x + offset.x, pos.y, c->pos.z + offset.z};
        } else {
            pos.x += last.velocity.x * kSourceDelta;
            pos.z += last.velocity.z * kSourceDelta;
        }
        return last;
    }
    bool ran(State s) const {
        for (State x : seen) if (x == s) return true;
        return false;
    }
    int until(State s, int limit) {
        for (int i = 0; i < limit; ++i) { step(); if (fsm.state() == s) return i; }
        return -1;
    }
};

PelletInfo pellet(std::uint64_t id, float x, float z, int mn, int mx) {
    PelletInfo p;
    p.id = id;
    p.pos = {x, 0.0f, z};
    p.bottomY = 0.0f;
    p.radius = 15.0f;
    p.carryMin = mn;
    p.carryMax = mx;
    return p;
}

void testParms() {
    const Params p = retail();
    check(p.retail, "retail parms parse");
    check(near(p.health, 1100.0f), "fp00 life 1100 from the general block, not the proper fp00");
    check(near(p.moveSpeed, 60.0f) && near(p.turnSpeed, 0.1f) && near(p.maxTurnAngle, 3.0f), "general move/turn");
    check(near(p.searchDistance, 500.0f) && near(p.searchAngle, 120.0f) && near(p.homeRadius, 15.0f), "general search/home");
    check(near(p.accel, 0.1f), "s003 accel");
    check(near(p.pressDamage, 200.0f) && near(p.suckDamage, 1000.0f), "proper fp06 press / fp04 container damage");
    check(near(p.carrySpeed, 35.0f) && near(p.walkAnimSpeed, 2.0f), "proper fp03/fp16");
    check(near(p.waitTime, 0.0f) && near(p.hideTime, 150.0f) && p.maxCarryWeight == 11, "proper fp14/fp15/ip01");
    // Fail closed.
    Params q;
    std::string error;
    std::istringstream bad("{\n{fp00} 4 -5\n{fp27} 4 1\n{_eof}\n}\n");
    check(!parseEnemyParm(bad, q, error) && !q.retail, "nonphysical life refused");
    std::istringstream none("{\n{s003} 4 0.1\n{_eof}\n}\n");
    check(!parseEnemyParm(none, q, error), "missing general block refused");
}

void testBank() {
    const Bank b = defaultBank();
    check(b.clip[AnimWalk].frames == 54 && b.clip[AnimBack].frames == 49 && b.clip[AnimDead].frames == 99,
          "retail clip durations");
    std::istringstream in("P2_BREADBUG_BANK_1 1\nclip 2 move2 49 2 10 0 39 1 3 0 24 48\nEND\n");
    Bank staged = defaultBank();
    std::string error;
    check(parseBank(in, staged, error) && staged.clip[AnimBack].staged && staged.clip[AnimBack].poses.size() == 3,
          "bank parses and stages move2 poses");
    std::istringstream bad("P2_BREADBUG_BANK_1 1\nclip 9 x 49 0 0\nEND\n");
    check(!parseBank(bad, staged, error), "anim id 9 refused");
}

void testContestRules() {
    // pelletCarry.cpp: challenger must be STRICTLY stronger.
    PelletCarry c;
    check(c.pull(PcsBreadbug, Vec3(), 1.5f) && c.state == PcsBreadbug, "idle pellet taken");
    check(!c.pull(PcsCarry, Vec3(), 1.0f) && c.state == PcsBreadbug, "1 Pikmin cannot out-pull 1.5");
    check(c.pull(PcsCarry, Vec3(), 2.0f) && c.state == PcsCarry && near(c.timer, 0.5f), "2 Pikmin take it, 0.5 s freeze");
    check(!c.pullable(PcsBreadbug, 1.5f), "breadbug no longer pullable");
    c.giveup(PcsBreadbug);
    check(c.state == PcsCarry, "giveup by the non-owner is a no-op");
    c.giveup(PcsCarry);
    check(c.state == PcsIdle, "owner giveup idles it");
    // A tie never changes hands (carryAmt > mCarryStrength).
    PelletCarry tie;
    tie.pull(PcsBreadbug, Vec3(), 2.0f);
    check(!tie.pull(PcsCarry, Vec3(), 2.0f) && tie.state == PcsBreadbug, "2 vs 2: the holder keeps it");
    check(!tie.pullable(PcsCarry, 2.0f), "tie is not pullable");
}

// Appear -> Walk -> Stick -> Back: the natural cargo grab.
void testGrab(Host& h) {
    h.pos = {0.0f, 0.0f, 0.0f};
    h.fsm.init(retail(), defaultBank(), h.pos, 0.0f, 12345u, &h.route);
    check(h.fsm.state() == State::Appear && near(h.fsm.health(), 1100.0f), "starts in Appear at full health");
    // Appear (type2, 69 frames at 30) ends after ~69 updates, then Walk.
    check(h.until(State::Walk, 80) >= 60, "Appear END -> Walk");
    h.pellets.push_back(pellet(7, 0.0f, 180.0f, 1, 2));  // ahead, inside fp14 and fp15
    const int t = h.until(State::Back, 400);
    check(t >= 0, "Walk finds the pellet, Stick, then Back");
    check(h.ran(State::Stick), "Stick visited on the way");
    check(h.held == 7, "host stuck the Breadbug to the pellet");
    check(near(h.fsm.carryStrength(), 1.5f), "contest strength (min+max)/2");
}

void testAttackImmune() {
    // damageCallBack (panModoki.cpp:450-456): not bittered -> no damage. The
    // FSM has no attack input: a long run with no press/suck/bomb keeps
    // health exactly at fp00 whatever the host saw.
    Host h;
    testGrab(h);
    const float before = h.fsm.health();
    check(!h.fsm.damageCallBack(10.0f), "damageCallBack refuses ordinary attacks");
    for (int i = 0; i < 300; ++i) h.step();
    check(near(h.fsm.health(), before), "health constant without press/suck/bomb");
}

void testContestAndPress() {
    Host h;
    testGrab(h);
    // One Pikmin grabs on: 1 < 1.5, the Breadbug keeps backing.
    h.cargo()->pikiStrength = 1.0f;
    for (int i = 0; i < 5; ++i) h.step();
    check(h.fsm.state() == State::Back && h.last.canBack, "1 carrier loses the tug");
    // Two Pikmin: 2 > 1.5 -> Pulled.
    h.cargo()->pikiStrength = 2.0f;
    check(h.until(State::Pulled, 5) >= 0, "2 carriers win: Back -> Pulled");
    // Back down to one: the Breadbug out-pulls again -> Back.
    h.cargo()->pikiStrength = 1.0f;
    check(h.until(State::Back, 10) >= 0, "carriers drop: Pulled -> Back");
    // A thrown Pikmin landing on it while falling: press -> Damage, fp06.
    const float before = h.fsm.health();
    h.presses = 1;
    h.step();
    check(h.fsm.state() == State::Damage, "press in Back -> Damage");
    check(h.last.damageKind == DamageKind::Press && near(h.last.hpBefore, before)
              && near(h.last.hpAfter, before - 200.0f), "press damage is proper fp06 (200)");
    check(h.held == 0, "Damage releases the cargo (giveup + endStick)");
    // Presses during Damage are ignored (pressCallBack state list).
    h.presses = 1;
    h.step();
    check(h.last.pressRejected && near(h.fsm.health(), before - 200.0f), "press ignored while in Damage");
    check(h.until(State::Wait, 80) >= 0, "Damage END with health > 0 -> Wait");
}

void testDeath() {
    Host h;
    testGrab(h);
    int presses = 0;
    for (int guard = 0; guard < 4000 && h.fsm.state() != State::Dead; ++guard) {
        const State s = h.fsm.state();
        if (s == State::Walk || s == State::Wait || s == State::Back || s == State::Pulled || s == State::Stick) {
            h.presses = 1;
            ++presses;
        }
        h.step();
    }
    check(h.fsm.state() == State::Dead, "presses kill it through Damage -> Dead");
    check(presses == 6, "1100 health takes six 200-damage presses");
    check(h.until(State::Null, 120) < 0 && h.killed, "Dead END requests kill()");
}

void testSuck() {
    Host h;
    testGrab(h);
    h.cargo()->pikiStrength = 3.0f;
    check(h.until(State::Pulled, 5) >= 0, "crew wins");
    h.cargo()->inGoal = true;
    for (int i = 0; i < 3; ++i) h.step();
    check(h.fsm.state() == State::Pulled, "no Back while the cargo is in the Onion goal");
    const float before = h.fsm.health();
    h.suck = true;
    h.step();
    check(h.fsm.state() == State::Sucked && h.held == 0, "InteractSuckFinish -> Sucked, released");
    for (int i = 0; i < 10; ++i) h.step();
    check(h.fsm.state() == State::Sucked && near(h.fsm.health(), before), "Sucked waits for the landing");
    h.bounce = true;
    h.step();
    check(h.fsm.state() == State::Damage && h.last.damageKind == DamageKind::Suck
              && near(h.fsm.health(), before - 1000.0f), "landing -> Damage with fp04 (1000)");
    h.presses = 1;  // mutant guard: a later press must not reuse the suck damage
    h.step();
    check(near(h.fsm.health(), before - 1000.0f), "no extra damage while in Damage");
}

void testHide() {
    Host h;
    testGrab(h);
    // Damage it once so the Hide refill is observable.
    h.external = 100.0f;
    h.step();
    check(h.last.damageKind == DamageKind::External && near(h.fsm.health(), 1000.0f), "bomb addDamage applies");
    // No carriers: the Breadbug drags the cargo home (0,0,0 is its home).
    const int t = h.until(State::CarryEnd, 3000);
    check(t >= 0, "Back reaches home -> CarryEnd");
    check(h.until(State::Hide, 400) >= 0, "CarryEnd at home -> Hide");
    check(h.until(State::Appear, 400) >= 0, "Hide -> Appear after fp15");
    check(h.consumed, "Hide END consumes the cargo (endCarry)");
    check(near(h.fsm.health(), 1100.0f), "Hide END refills health to fp00");
}

void testBackWatchdog() {
    // #898 port watchdog: a haul wedged against the map (the cargo never
    // moves) skips route nodes, then releases the cargo instead of standing
    // in Back forever.
    Host h;
    testGrab(h);
    h.frozen = true;
    bool skipped = false, released = false;
    for (int i = 0; i < 60 * (kBackStuckRelease + 2) && !released; ++i) {
        h.step();
        skipped = skipped || h.last.backStuckSkip;
        released = released || h.last.backStuckRelease;
    }
    check(skipped, "wedged Back skips to the next route node");
    check(released && h.fsm.state() == State::Wait && h.held == 0, "still wedged: cargo released, Back -> Wait");
    // A haul that keeps moving never trips the watchdog.
    Host m;
    testGrab(m);
    bool trip = false;
    for (int i = 0; i < 600 && m.fsm.state() == State::Back; ++i) {
        m.step();
        trip = trip || m.last.backStuckSkip || m.last.backStuckRelease;
    }
    check(!trip, "a moving haul never trips the watchdog");
}

void testNoRouteHaulsHome() {
    // #898 port fallback: with no route-graph path home the Breadbug hauls
    // straight at the nest instead of standing in Back with the cargo.
    Host h;
    h.route.noPath = true;
    testGrab(h);
    check(!h.fsm.pathfinding(), "no route path home");
    check(h.until(State::CarryEnd, 3000) >= 0, "no-path haul still reaches home -> CarryEnd");
    check(h.until(State::Appear, 800) >= 0 && h.consumed, "then Hide consumes and Appear");
}

void testLivingAndConsumePolicy() {
    check(!isLivingThing(false, true), "unbittered live Breadbug is not a living thing (no Pikmin/captain target)");
    check(isLivingThing(true, true), "bittered live Breadbug is a living thing");
    check(!isLivingThing(true, false), "dead is never a living thing");
    check(consumeOutcome(true) == ConsumeOutcome::SpareCarcass,
          "a carcass is spared at the nest (its delivery check is never forfeited)");
    check(consumeOutcome(false) == ConsumeOutcome::Destroy, "a pellet is eaten (retail endCarry)");
}
// Giant Breadbug (OoPanModoki 40, #958): the variant differences from the decomp.
void testGiantVariant() {
    const Params g = giantRetail();
    check(g.retail && g.giant, "giant retail parms parse with the giant flag kept");
    check(near(g.health, 2000.0f) && near(g.moveSpeed, 85.0f) && near(g.maxTurnAngle, 2.0f), "giant general fp00/fp06/fp28");
    check(near(g.searchDistance, 300.0f) && near(g.homeRadius, 30.0f), "giant general search/home");
    check(near(g.pressDamage, 100.0f) && near(g.suckDamage, 1000.0f), "giant proper fp06 press 100 / fp04 container 1000");
    check(near(g.carrySpeed, 45.0f) && near(g.walkAnimSpeed, 1.0f) && near(g.nestScale, 2.0f), "giant proper fp03/fp16/fp00");
    check(near(g.hideTime, 150.0f) && g.maxCarryWeight == 1, "giant proper fp15/ip01");
    check(near(g.carrySizeDiff, kGiantCarrySizeDiff) && near(kGiantCarrySizeDiff, 40.0f), "OoPanModoki mCarrySizeDiff 40");
    check(near(g.waypointSlack, 150.0f), "OoPanModoki walkFunc slack 150");
    Params small = retail();
    check(!small.giant && near(small.carrySizeDiff, 20.0f) && near(small.waypointSlack, 100.0f), "PanModoki defaults untouched");
    Params applied;
    applyVariant(applied, false);
    check(!applied.giant && near(applied.carrySizeDiff, 20.0f), "applyVariant(false) is the Breadbug");

    // canTarget: PanModoki takes strictly lighter cargo (ip01 11 > min), the
    // Giant takes at-or-above (ip01 1 <= min): a min-10 pellet is a Breadbug
    // target and a Giant target, a min-11 pellet only the Giant's.
    auto grabs = [](const Params& params, int carryMin) {
        Host h;
        h.pos = {0.0f, 0.0f, 0.0f};
        h.fsm.init(params, defaultBank(), h.pos, 0.0f, 12345u, &h.route);
        h.until(State::Walk, 80);
        h.pellets.push_back(pellet(7, 0.0f, 180.0f, carryMin, carryMin + 1));
        return h.until(State::Back, 400) >= 0 && h.held == 7;
    };
    check(grabs(retail(), 10), "Breadbug grabs a min-10 pellet (11 > 10)");
    check(!grabs(retail(), 11), "Breadbug refuses a min-11 pellet (11 > 11 is false)");
    check(grabs(giantRetail(), 1), "Giant grabs a min-1 pellet (1 <= 1)");
    check(grabs(giantRetail(), 11), "Giant grabs a min-11 pellet (1 <= 11)");
    // Same table, opposite rule: the Giant with the small Breadbug's ip01 (11)
    // refuses a min-10 pellet, the Breadbug with the Giant's ip01 (1) refuses min 1.
    Params giantBig = giantRetail();
    giantBig.maxCarryWeight = 11;
    check(!grabs(giantBig, 10), "Giant with limit 11 refuses a min-10 pellet (11 <= 10 is false)");
    Params smallOne = retail();
    smallOne.maxCarryWeight = 1;
    check(!grabs(smallOne, 1), "Breadbug with limit 1 refuses a min-1 pellet (1 > 1 is false)");

    // Health, press and container damage come from the giant parms.
    Host h;
    h.pos = {0.0f, 0.0f, 0.0f};
    h.fsm.init(giantRetail(), defaultBank(), h.pos, 0.0f, 12345u, &h.route);
    check(near(h.fsm.health(), 2000.0f), "giant starts at fp00 2000");
    h.until(State::Walk, 80);
    h.presses = 1;
    h.step();
    check(h.fsm.state() == State::Damage && h.last.damageKind == DamageKind::Press
              && near(h.last.hpBefore, 2000.0f) && near(h.last.hpAfter, 1900.0f), "giant press damage is 100");
}
} // namespace

int main() {
    testParms();
    testBank();
    testContestRules();
    testAttackImmune();
    testContestAndPress();
    testDeath();
    testSuck();
    testHide();
    testLivingAndConsumePolicy();
    testBackWatchdog();
    testNoRouteHaulsHome();
    testGiantVariant();
    if (failures) {
        std::fprintf(stderr, "%d failure(s)\n", failures);
        return 1;
    }
    std::puts("p2_breadbug_fsm_test OK");
    return 0;
}
