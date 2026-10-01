// p2_otakara_item_test (Dweevil family fidelity): treasure pickup / carry / drop decisions of
// OtakaraBase (OtakaraBase.cpp:361-574, OtakaraBaseState.cpp:349-740), engine-free.
//
// Owner playtest 2026-09-30: "never saw it pick up a treasure". The port had no item states; the
// pre-fix behaviour is modelled by `legacy*` below (a Dweevil that never searches for, takes or
// carries anything and whose damage always reaches its own life).
//
// Negative controls:
//   * -DP2_OTAKARA_ITEM_TEST_LEGACY swaps the policy for the pre-fix behaviour, so the test fails.
//   * Passing a source root as argv[1] that holds the pre-fix pc_p2_otakara.cpp makes the wiring
//     checks fail.
//
// NOTE: checks use an always-evaluated CHECK macro, never bare assert().
#include "pc_p2_otakara_item.h"

#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#ifndef P2_OTAKARA_ITEM_SOURCE_ROOT
#define P2_OTAKARA_ITEM_SOURCE_ROOT "."
#endif

using namespace p2otakaraitem;
using p2otakaramove::Vec2;

static int failures = 0;

#define CHECK(cond)                                                                       \
    do {                                                                                  \
        if (!(cond)) {                                                                    \
            std::printf("P2_OTAKARA_ITEM_TEST_FAIL line=%d check=%s\n", __LINE__, #cond); \
            ++failures;                                                                   \
        }                                                                                 \
    } while (0)

namespace {

#ifdef P2_OTAKARA_ITEM_TEST_LEGACY
// Pre-fix: no treasure state exists, nothing is searched, damage always hurts the Dweevil.
bool uSearchOpen(float& timer, float dt, bool) { timer += dt; return false; }
int uNearest(const Pellet*, int, Vec2, Vec2, float, float) { return -1; }
DamageRoute uDamage(Hold&, float) { return {false, true}; }
St uDecide(const In& in) {
    In legacy = in;
    legacy.takeNow = false;
    return decide(legacy);
}
#else
bool uSearchOpen(float& timer, float dt, bool ignoring) { return searchOpen(timer, dt, ignoring); }
int uNearest(const Pellet* p, int n, Vec2 self, Vec2 home, float sight, float territory) {
    return nearestTreasure(p, n, self, home, sight, territory);
}
DamageRoute uDamage(Hold& h, float damage) { return damageTreasure(h, damage); }
St uDecide(const In& in) { return decide(in); }
#endif

Pellet pel(float x, float z, float pick = 10.0f) {
    Pellet p;
    p.pos = Vec2{x, z};
    p.y = 0.0f;
    p.pickRadius = pick;
    p.height = 20.0f;
    p.alive = true;
    p.captured = false;
    p.pickable = true;
    return p;
}

void checkConstants() {
    CHECK(kCatchDelay == 2.5f);      // fp21
    CHECK(kNormalAttack == 1.0f);    // fp10
    CHECK(kOtakaraAttack == 1.25f);  // fp11
    CHECK(kSearchOpen > kCatchDelay); // OtakaraBase.cpp:59
    CHECK(otakaraLife(59) == 80.0f);
    CHECK(otakaraLife(60) == 80.0f);
    CHECK(otakaraLife(62) == 80.0f);
    CHECK(otakaraLife(93) == 80.0f);
    CHECK(otakaraLife(61) == 100.0f); // Munge retail fp01
    CHECK(takeRadius(10.0f) == 50.0f);
    CHECK(takeRadius(30.0f) == 50.0f);
    CHECK(takeRadius(40.0f) == 60.0f);
    CHECK(isTake(49.9f, 10.0f));
    CHECK(!isTake(50.0f, 10.0f)); // strict <
    CHECK(isTake(59.9f, 40.0f));
    CHECK(!isTake(60.0f, 40.0f));
}

void checkSearch() {
    // The timer starts open (12800): the first isMovePositionSet(false) may search.
    float timer = kSearchOpen;
    CHECK(uSearchOpen(timer, 0.033f, false));
    // The item states never search (isMovePositionSet(true)) and only advance the timer.
    float t2 = 0.0f;
    CHECK(!uSearchOpen(t2, 0.5f, true));
    CHECK(t2 == 0.5f);
    // After StateItemDrop::cleanup the delay restarts: closed until the timer passes 2.5 s.
    float cool = 0.0f;
    int frames = 0;
    while (!uSearchOpen(cool, 1.0f / 30.0f, false) && frames < 1000) ++frames;
    CHECK(frames >= 75 && frames <= 85); // ~2.5 s at 30 Hz
    // A search attempt does not advance the timer (only the non-searching branch does).
    float held = 3.0f;
    CHECK(uSearchOpen(held, 0.1f, false));
    CHECK(held == 3.0f);
}

void checkNearest() {
    const Vec2 home{0.0f, 0.0f};
    const Vec2 self{0.0f, 0.0f};
    std::vector<Pellet> v;
    v.push_back(pel(150.0f, 0.0f));  // 0: inside sight and territory
    v.push_back(pel(90.0f, 0.0f));   // 1: nearer
    v.push_back(pel(250.0f, 0.0f));  // 2: beyond sight and territory
    int pick = uNearest(v.data(), int(v.size()), self, home, 200.0f, 200.0f);
#ifndef P2_OTAKARA_ITEM_TEST_LEGACY
    CHECK(pick == 1);
    // Unpickable / captured / dead pellets are skipped.
    v[1].captured = true;
    CHECK(uNearest(v.data(), int(v.size()), self, home, 200.0f, 200.0f) == 0);
    v[0].pickable = false;
    CHECK(uNearest(v.data(), int(v.size()), self, home, 200.0f, 200.0f) == -1);
    v[0].pickable = true;
    v[0].alive = false;
    CHECK(uNearest(v.data(), int(v.size()), self, home, 200.0f, 200.0f) == -1);
    // Territory is about HOME, sight about the Dweevil: a pellet 150 from the Dweevil but 230
    // from home is ignored.
    std::vector<Pellet> w;
    w.push_back(pel(230.0f, 0.0f));
    CHECK(uNearest(w.data(), 1, Vec2{80.0f, 0.0f}, home, 200.0f, 200.0f) == -1);
    // Strict <: exactly sight away is not found.
    std::vector<Pellet> e;
    e.push_back(pel(200.0f, 0.0f));
    CHECK(uNearest(e.data(), 1, self, Vec2{100.0f, 0.0f}, 200.0f, 200.0f) == -1);
#else
    CHECK(pick == 1); // legacy never finds one: this check must fail
#endif
}

void checkDamage() {
    Hold h;
    // Empty-handed: addDamage reaches the Dweevil.
    DamageRoute r = uDamage(h, 10.0f);
    CHECK(!r.toTreasure);
    CHECK(r.addDamage);
    // Carrying: the treasure takes it and the Dweevil's own life is untouched.
    grab(h, 80.0f);
    r = uDamage(h, 15.0f);
    CHECK(r.toTreasure);
    CHECK(!r.addDamage);
    CHECK(h.health == 65.0f);
    CHECK(!isDrop(h));
    for (int i = 0; i < 4; ++i) uDamage(h, 15.0f);
    CHECK(h.health == 5.0f);
    uDamage(h, 15.0f);
    CHECK(h.health == 0.0f); // clamped at 0
    CHECK(isDrop(h));
    release(h);
    CHECK(!h.holding);
    CHECK(isDrop(h)); // nothing held: isDropTreasure is true
    // Hipdrop / earthquake while carrying take the full otakara life (OtakaraBase.cpp:203-231).
    Hold c;
    grab(c, 80.0f);
    CHECK(hipdropDamage(c, 50.0f, 80.0f) == 80.0f);
    Hold e;
    CHECK(hipdropDamage(e, 50.0f, 80.0f) == 50.0f);
}

void checkDecide() {
    const auto in = [](St cur, bool target, bool facing, bool take, bool flick, bool drop) {
        return In{cur, target, facing, take, flick, drop, false};
    };
#ifndef P2_OTAKARA_ITEM_TEST_LEGACY
    // Wait -> Move / Take / Turn / stay.
    CHECK(uDecide(in(St::Wait, true, true, false, false, false)) == St::Move);
    CHECK(uDecide(in(St::Wait, true, true, true, false, false)) == St::Take);
    CHECK(uDecide(in(St::Wait, true, false, true, false, false)) == St::Turn); // take needs the facing gate
    CHECK(uDecide(in(St::Wait, false, false, false, false, false)) == St::Wait);
    // Move -> Take on reach, Turn when not facing, Wait without a target.
    CHECK(uDecide(in(St::Move, true, true, true, false, false)) == St::Take);
    CHECK(uDecide(in(St::Move, true, false, false, false, false)) == St::Turn);
    CHECK(uDecide(in(St::Move, false, false, false, false, false)) == St::Wait);
    // Turn -> Move once facing, Take if already in reach.
    CHECK(uDecide(in(St::Turn, true, true, false, false, false)) == St::Move);
    CHECK(uDecide(in(St::Turn, true, true, true, false, false)) == St::Take);
    // Flick overrides the move decision, Dead overrides Flick.
    CHECK(uDecide(in(St::Move, true, true, false, true, false)) == St::Flick);
    const In dead{St::Move, true, true, false, true, false, true};
    CHECK(uDecide(dead) == St::Dead);
    // Item states flee like the plain ones and never Take.
    CHECK(uDecide(in(St::ItemWait, true, true, true, false, false)) == St::ItemMove);
    CHECK(uDecide(in(St::ItemWait, true, false, false, false, false)) == St::ItemTurn);
    CHECK(uDecide(in(St::ItemMove, false, false, false, false, false)) == St::ItemWait);
    CHECK(uDecide(in(St::ItemTurn, true, true, false, false, false)) == St::ItemMove);
    // Flick then drop: a depleted treasure wins over everything.
    CHECK(uDecide(in(St::ItemMove, true, true, false, true, false)) == St::ItemFlick);
    CHECK(uDecide(in(St::ItemMove, true, true, false, true, true)) == St::ItemDrop);
    CHECK(uDecide(in(St::ItemWait, false, false, false, false, true)) == St::ItemDrop);
    // Clip-end transitions.
    CHECK(afterTake(true, false, false) == St::ItemMove);
    CHECK(afterTake(true, true, false) == St::ItemDrop);
    CHECK(afterTake(true, false, true) == St::ItemFlick);
    CHECK(afterTake(false, false, false) == St::ItemDrop); // take failed
    CHECK(afterItemFlick(true, true, true) == St::ItemDrop);
    CHECK(afterItemFlick(false, true, true) == St::ItemMove);
    CHECK(afterItemFlick(false, true, false) == St::ItemTurn);
    CHECK(afterItemFlick(false, false, false) == St::ItemWait);
    CHECK(afterItemDrop(true, false, false, false) == St::Dead);
    CHECK(afterItemDrop(false, true, false, false) == St::Flick);
    CHECK(afterItemDrop(false, false, true, true) == St::Move);
    CHECK(afterItemDrop(false, false, true, false) == St::Turn);
    CHECK(afterItemDrop(false, false, false, false) == St::Wait);
    CHECK(attackTimerDone(false, 1.01f) && !attackTimerDone(false, 0.99f));
    CHECK(attackTimerDone(true, 1.26f) && !attackTimerDone(true, 1.2f));
#else
    CHECK(uDecide(in(St::Wait, true, true, true, false, false)) == St::Take); // legacy never takes
#endif
}

// A scripted pickup-carry-drop run over the decisions above: a Dweevil next to one pellet.
void checkScenario() {
    Hold hold;
    float timer = kSearchOpen;
    St st = St::Wait;
    int takes = 0, drops = 0;
    bool pelletFree = true;
    float t = 0.0f;
    const float dt = 1.0f / 30.0f;
    for (int i = 0; i < 1200; ++i, t += dt) {
        const bool item = isItemState(st);
        const bool search = uSearchOpen(timer, dt, item);
        const bool haveTreasure = search && pelletFree && !hold.holding;
        In in{st, haveTreasure, true, haveTreasure, false, item && isDrop(hold), false};
        const St next = uDecide(in);
        if (st == St::Wait && next == St::Take) {
            // Take: event 2 grabs, the clip end (30 frames) decides the carry state.
            grab(hold, otakaraLife(59));
            pelletFree = false;
            ++takes;
            st = afterTake(true, isDrop(hold), false);
        } else if (st == St::ItemMove) {
            // Captain hits the carried treasure: 15 damage every second.
            if (i % 30 == 0) uDamage(hold, 15.0f);
            if (isDrop(hold)) st = St::ItemDrop;
        } else if (st == St::ItemDrop) {
            release(hold);
            pelletFree = true;
            ++drops;
            timer = 0.0f; // StateItemDrop::cleanup
            st = St::Wait;
        } else if (st == St::Wait && next != St::Wait) {
            st = next;
        } else if (st == St::Move && next == St::Take) {
            grab(hold, otakaraLife(59));
            pelletFree = false;
            ++takes;
            st = afterTake(true, isDrop(hold), false);
        }
        if (takes >= 2 && drops >= 1) break;
    }
#ifndef P2_OTAKARA_ITEM_TEST_LEGACY
    CHECK(takes >= 2); // picks up, drops, and (after the 2.5 s delay) picks up again
    CHECK(drops >= 1);
#else
    CHECK(takes >= 2); // legacy: never
#endif
}

std::string readFile(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return std::string();
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

void checkWiring(const std::string& root) {
    const std::string glue = readFile(root + "/pc_port/pc_p2_otakara.cpp");
    CHECK(!glue.empty());
    // The item states are driven by the policy and the takeitem/dropitem2 clip events.
    CHECK(glue.find("p2otakaraitem::decide(") != std::string::npos);
    CHECK(glue.find("p2otakaraitem::afterTake(") != std::string::npos);
    CHECK(glue.find("p2otakaraitem::afterItemFlick(") != std::string::npos);
    CHECK(glue.find("p2otakaraitem::afterItemDrop(") != std::string::npos);
    CHECK(glue.find("takeTreasure(a, s, pos); // StateTake::exec event 2") != std::string::npos);
    CHECK(glue.find("dropTreasure(a, s, true, \"itemdrop\")") != std::string::npos);
    // The carried object is held through the engine's own mouth stick and cannot be carried away.
    CHECK(glue.find("InteractSwallow(a, mouth, 0)") != std::string::npos);
    CHECK(glue.find("mSlotFlags[i] = -1") != std::string::npos);
    // Death and forget put it back on the ground.
    CHECK(glue.find("dropTreasure(actor, s, true, \"death\")") != std::string::npos);
    CHECK(glue.find("dropTreasure(actor, s, false, \"forget\")") != std::string::npos);
    // StateItemDrop::cleanup restarts the pickup delay.
    CHECK(glue.find("s.itemSearchTimer = 0.0f;") != std::string::npos);
    // Ship parts are never treasure.
    CHECK(glue.find("isUfoParts()") != std::string::npos);
    // The dev staging is env-gated.
    CHECK(glue.find("PIKMIN_P2_DWEEVIL_STAGE_TREASURE") != std::string::npos);
}

} // namespace

int main(int argc, char** argv) {
    checkConstants();
    checkSearch();
    checkNearest();
    checkDamage();
    checkDecide();
    checkScenario();
    checkWiring(argc > 1 ? std::string(argv[1]) : std::string(P2_OTAKARA_ITEM_SOURCE_ROOT));
    if (failures) {
        std::printf("FAIL p2_otakara_item_test failures=%d\n", failures);
        return 1;
    }
    std::printf("PASS p2_otakara_item_test\n");
    return 0;
}
