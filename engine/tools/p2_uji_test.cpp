// Engine-free fixtures for pc_p2_uji_policy.h (UjiA 12 / UjiB 13 / Tobi 14).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_uji_test.cpp -o p2_uji_test.exe
//
// #886 defect 5: the attack-semantics block runs the real Fsm and, on the
// same input, a verbatim transcription of the pre-#886 port attack rule
// (legacyStrikes) and requires the legacy rule to break the source contract
// (UjiA harms creatures; UjiB/Tobi strike twice per attack and eat nothing).
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <initializer_list>
#include <string>
#include "pc_p2_uji_policy.h"

using namespace p2uji_policy;

static int gChecks = 0;
static void require(bool ok, const char* what) {
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_uji_test: %s\n", what);
        std::fflush(stdout);
        std::_Exit(1);
    }
}

static In sighted() {
    In in;
    in.health = 100.0f;
    in.targetInSight = true;
    return in;
}

// Result of driving one attack from Move with a target that stays attackable.
struct AttackRun {
    int strikes = 0;      // creature-harming events (source: Attack2 KEYEVENT_4)
    int swallows = 0;     // Eat KEYEVENT_2
    int attackStates = 0; // Attack1/Attack2 entries
    bool reachedEat = false;
    bool back = false;    // back in Move afterwards
};

static AttackRun runAttack(Kind k, bool pikminStuckAfterStrike) {
    Fsm fsm;
    Out out;
    Parms p = parmsFor(k);
    fsm.state = UJI_MOVE;
    In in = sighted();
    in.targetAttackable = true;
    AttackRun r;
    State last = fsm.state;
    for (int i = 0; i < 400; ++i) {
        fsm.tick(in, p, k, out);
        if (out.strike) {
            ++r.strikes;
            in.stuckPikmin = pikminStuckAfterStrike; // the eat just caught one
        }
        if (out.swallow) {
            ++r.swallows;
            in.stuckPikmin = false;
        }
        if (fsm.state != last && (fsm.state == UJI_ATTACK1 || fsm.state == UJI_ATTACK2)) ++r.attackStates;
        if (fsm.state == UJI_EAT) r.reachedEat = true;
        if (last != UJI_MOVE && fsm.state == UJI_MOVE) {
            r.back = true;
            break;
        }
        last = fsm.state;
    }
    return r;
}

// Pre-#886 port rule, transcribed: Move -> Attack1 on a target in range;
// UjiA Attack1 -> Move, others Attack1 -> Attack2 -> Eat; pc_p2_uji.cpp
// ujiStrike ran once per ATTACK1/ATTACK2 entry (attackHit reset on each
// state change) and sent InteractAttack(bridgeDamage) to the nearest foe;
// Eat only stopped the actor.
struct LegacyRun {
    int strikes = 0;
    float damage = 0.0f;
    int eats = 0;
};
static LegacyRun legacyStrikes(Kind k) {
    LegacyRun r;
    const Parms p = parmsFor(UJIA); // old code used the shared 25 for everyone
    r.strikes = (k == UJIA) ? 1 : 2;
    r.damage = p.bridgeDamage * float(r.strikes);
    r.eats = 0;
    return r;
}

static void testAttackSemantics() {
    // UjiA: no creature attack at all (source Attack1 = breakTargetBridge).
    {
        const AttackRun r = runAttack(UJIA, true);
        require(r.strikes == 0 && r.attackStates == 0, "UjiA never attacks a creature");
        require(!attacksCreatures(UJIA), "UjiA has no creature attack");
        const LegacyRun old = legacyStrikes(UJIA);
        require(old.strikes > 0 && old.damage > 0.0f, "legacy UjiA hit a creature (old behaviour fails)");
    }
    // UjiB / Tobi: Move -> Attack2, one strike, Eat only with a catch, one swallow.
    for (Kind k : {UJIB, TOBI}) {
        const AttackRun r = runAttack(k, true);
        require(r.attackStates == 1, "one Attack2 per attack (no Attack1 chain)");
        require(r.strikes == 1, "UjiB/Tobi strike exactly once per attack");
        require(r.reachedEat && r.swallows == 1, "caught Pikmin: Eat swallows once");
        require(r.back, "attack cycle returns to Move");
        const LegacyRun old = legacyStrikes(k);
        require(old.strikes == 2 && old.eats == 0, "legacy struck twice and never ate (old behaviour fails)");
        const AttackRun miss = runAttack(k, false);
        require(miss.strikes == 1 && !miss.reachedEat && miss.swallows == 0, "miss: Attack2 END goes to Move");
    }
    // The strike fires at the retail attack2 KEYEVENT_4 frame, the swallow at eat KEYEVENT_2.
    {
        Fsm fsm;
        Out out;
        Parms p = parmsFor(UJIB);
        require(p.strikeFrame == 14 && p.swallowFrame == 53, "retail key-event frames");
        fsm.enter(UJI_ATTACK2);
        In in = sighted();
        in.targetAttackable = true;
        int strikeTick = -1;
        for (int i = 1; i <= 30 && strikeTick < 0; ++i) {
            fsm.tick(in, p, UJIB, out);
            if (out.strike) strikeTick = i;
        }
        require(strikeTick == 14, "strike on source frame 14");
    }
    // Source attack cone (fp20 70, fp21 15 deg) and attackNavi cone (strict).
    {
        const Parms p = parmsFor(UJIB);
        require(inCone(0.0f, 0.0f, 50.0f, 0.0f, p.attackRange, p.attackAngle), "front target attackable");
        require(!inCone(0.0f, 0.0f, -20.0f, 0.0f, p.attackRange, p.attackAngle), "rear target not attackable");
        require(!inCone(30.0f, 0.0f, 30.0f, 0.0f, p.attackRange, p.attackAngle), "45 deg off-axis not attackable");
        require(!inCone(0.0f, 0.0f, 70.0f, 0.0f, p.attackRange, p.attackAngle), "range is strict");
        require(!inCone(0.0f, 60.0f, 45.0f, 0.0f, p.attackRange, p.attackAngle), "range is 3D");
        const float edge = 15.0f * 3.14159265f / 180.0f;
        const float ex = 40.0f * std::sin(edge), ez = 40.0f * std::cos(edge);
        require(!inCone(ex * 1.0001f, 0.0f, ez * 0.9999f, 0.0f, p.attackRadius, p.hitAngle, true),
                "attackNavi angle is strict");
    }
}

int main() {
    // Identity: source ids, hosts, parms.
    require(sourceIdFor(UJIA) == 12, "UjiA source 12");
    require(sourceIdFor(UJIB) == 13, "UjiB source 13");
    require(sourceIdFor(TOBI) == 14, "Tobi source 14");
    require(hostTypeFor(UJIA) == 18, "UjiA host KabekuiA");
    require(hostTypeFor(UJIB) == 19, "UjiB host KabekuiB");
    require(hostTypeFor(TOBI) == 20, "Tobi host KabekuiC");
    require(parmsFor(UJIA).life == 100.0f, "UjiA retail life 100");
    require(parmsFor(UJIA).bridgeDamage == 25.0f, "UjiA retail fp01 25");

    // Stay -> Appear on sight (all kinds).
    for (int k = 0; k < 3; ++k) {
        Fsm fsm;
        Out out;
        Parms p = parmsFor((Kind)k);
        require(fsm.state == UJI_STAY, "spawn buried");
        require(fsm.tick(sighted(), p, (Kind)k, out), "sight reveals");
        require(fsm.state == UJI_APPEAR, "stay->appear");
        // Appear -> Move after appearTime (30 ticks).
        In idle;
        idle.health = 100.0f;
        for (int i = 0; i < 30; ++i) fsm.tick(idle, p, (Kind)k, out);
        require(fsm.state == UJI_MOVE, "appear completes to move");
    }

    // #886 defect 5: attack semantics against the source (and the old rule).
    testAttackSemantics();

    // Tobi flies after flyTime without a target, then lands.
    {
        Fsm fsm;
        Out out;
        Parms p = parmsFor(TOBI);
        fsm.state = UJI_MOVE;
        In idle;
        idle.health = 100.0f;
        for (int i = 0; i < 130; ++i) fsm.tick(idle, p, TOBI, out);
        require(fsm.state == UJI_FLY, "Tobi takes off");
        require(Fsm::clipFor(UJI_FLY, TOBI) != nullptr, "fly clip names");
        // Source StateFly ends only at its clip end: an attackable target
        // does not interrupt the flight.
        In seen = idle;
        seen.targetAttackable = true;
        fsm.tick(seen, p, TOBI, out);
        require(fsm.state == UJI_FLY, "Tobi flight is not interrupted by a target");
        for (int i = 0; i < 130; ++i) fsm.tick(idle, p, TOBI, out);
        require(fsm.state == UJI_MOVE, "Tobi lands");
    }

    // GoHome/Dive/Stay when far from home.
    {
        Fsm fsm;
        Out out;
        Parms p = parmsFor(UJIA);
        fsm.state = UJI_MOVE;
        In in = sighted();
        in.farFromHome = true;
        fsm.tick(in, p, UJIA, out);
        require(fsm.state == UJI_GOHOME, "far move goes home");
        for (int i = 0; i < 130; ++i) fsm.tick(in, p, UJIA, out);
        require(fsm.state == UJI_DIVE, "gohome times out to dive");
        in.targetInSight = false; // no target: dive reburies and stays buried
        for (int i = 0; i < 40; ++i) fsm.tick(in, p, UJIA, out);
        require(fsm.state == UJI_STAY, "dive reburies");
    }

    // Death from any state mints the dead clip.
    {
        Fsm fsm;
        Out out;
        Parms p = parmsFor(UJIB);
        fsm.state = UJI_ATTACK2;
        In in;
        in.health = 0.0f;
        require(fsm.tick(in, p, UJIB, out), "death changes motion");
        require(fsm.state == UJI_DEAD, "health 0 kills");
        require(out.downEffect, "death drops effect flag");
    }

    // OWN round-2 guards: per-species toughness/speed, OWN bite damage, clips.
    require(parmsFor(UJIB).life == 120.0f, "UjiB tougher than female");
    require(parmsFor(TOBI).life == 150.0f, "Tobi toughest");
    require(parmsFor(TOBI).moveSpeed == 120.0f, "Tobi fly speed");
    // Bridge power is the InteractBreakBridge parameter only (per species).
    require(parmsFor(UJIB).bridgeDamage == 50.0f, "UjiB proper fp02 bridge power");
    require(parmsFor(TOBI).bridgeDamage == 75.0f, "Tobi proper fp12 bridge power");
    require(std::string(Fsm::clipFor(UJI_ATTACK2, UJIB)) == "attack2", "attack2 clip");
    require(std::string(Fsm::clipFor(UJI_EAT, UJIB)) == "eat", "eat clip");
    require(std::string(Fsm::clipFor(UJI_FLY, TOBI)) == "fly", "tobi fly clip");
    require(std::string(Fsm::clipFor(UJI_FLY, UJIA)) == "move", "non-tobi fly falls back");
    require(std::string(Fsm::clipFor(UJI_DEAD, TOBI)) == "dead", "dead clip all kinds");

    std::printf("PASS p2_uji_test checks=%d\n", gChecks);
    return 0;
}
