// Unit test for the engine-free Empress Bulblax FSM (pc_p2_queen_own.h, #256).
// Necessary, never admission evidence.
#include "pc_p2_queen_own.h"
#include <cassert>
#include <cstdio>
#include <sstream>

using namespace p2queenown;

static int runUntil(Queen& q, TickInput in, int state, int maxTicks, std::vector<int>* entered = nullptr,
                    TickOutput* sawFlags = nullptr) {
    for (int i = 0; i < maxTicks; ++i) {
        TickOutput o = q.tick(in);
        if (entered) entered->insert(entered->end(), o.entered.begin(), o.entered.end());
        if (sawFlags) {
            sawFlags->flickFace |= o.flickFace;
            sawFlags->rollingAttack |= o.rollingAttack;
            sawFlags->birth |= o.birth;
            sawFlags->crash |= o.crash;
            sawFlags->kill |= o.kill;
        }
        if (o.velocity.x != 0.0f || o.velocity.z != 0.0f) {
            in.pos.x += o.velocity.x * kSourceDelta;
            in.pos.z += o.velocity.z * kSourceDelta;
        }
        in.hits = 0;
        if (q.state() == state) return i;
    }
    return -1;
}

int main() {
    Params p;
    Bank bank = defaultBank();
    // isStartFlick thresholds (enemyAction.cpp): stuck < 5 needs > 30 blows.
    assert(!isStartFlick(30.0f, 0, p));
    assert(isStartFlick(31.0f, 0, p));
    assert(!isStartFlick(35.0f, 5, p) && isStartFlick(36.0f, 5, p));
    assert(!isStartFlick(50.0f, 20, p) && isStartFlick(51.0f, 20, p));
    assert(damageFactor(Sleep) == 0.1f && damageFactor(Flick) == 0.2f && damageFactor(Wait) == 1.0f);

    // Entry: Wait with larvae, Sleep without (Queen::onInit).
    Queen q;
    q.init(p, bank, true, false, {0, 0}, 0.0f, 7u);
    assert(q.state() == Wait);
    Queen s;
    s.init(p, bank, false, false, {0, 0}, 0.0f, 7u);
    assert(s.state() == Sleep);

    // Larva due after the birth interval -> Born, KEYEVENT_2 births one.
    TickInput in;
    in.health = 5000.0f;
    TickOutput flags;
    assert(runUntil(q, in, Born, 200, nullptr, &flags) >= 0);
    assert(runUntil(q, in, Wait, 200, nullptr, &flags) >= 0);
    assert(flags.birth);

    // A Pikmin hit raises the hit counter -> Damage while Pikmin are stuck.
    in.hits = 1;
    in.stuck = 3;
    in.larvae = 30; // above min: no birth pressure
    Queen d;
    d.init(p, bank, false, false, {0, 0}, 0.0f, 9u); // Sleep entry
    assert(runUntil(d, in, Damage, 400) >= 0);
    // Blows past the threshold -> Flick -> key 2 flick -> Rolling.
    in.hits = 40;
    std::vector<int> entered;
    TickOutput f2;
    assert(runUntil(d, in, Rolling, 400, &entered, &f2) >= 0);
    assert(f2.flickFace);
    // Rolling passes: press every frame while rolling, crash at the
    // territory edge, then a timed pass ends back in Wait.
    in.stuck = 0;
    TickOutput f3;
    assert(runUntil(d, in, Wait, 3000, &entered, &f3) >= 0);
    assert(f3.rollingAttack);
    // Port constraint: a roll the host cannot advance (P1 map collision holds
    // the Queen against a wall) must still terminate. Host position frozen.
    for (bool left : {false, true}) {
        Queen r;
        r.init(p, bank, false, left, {0, 0}, 0.0f, 11u);
        TickInput bi2;
        bi2.health = 5000.0f;
        bi2.hits = 40;
        bi2.pos = {100.0f, 0.0f}; // dot +-100: outside the home band, inside the territory
        int turns = 0, ends = 0, rollStarts = 0;
        bool sawRolling = false, reachedWait = false;
        for (int i = 0; i < 6000 && !reachedWait; ++i) {
            TickOutput o = r.tick(bi2); // pos never changes: fully blocked
            bi2.hits = 0;
            turns += o.blockedTurn;
            ends += o.blockedEnd;
            rollStarts += o.rollStart;
            if (r.state() == Rolling) sawRolling = true;
            else if (sawRolling && r.state() == Wait) reachedWait = true;
        }
        assert(sawRolling && reachedWait);
        assert(ends == 1 && rollStarts >= 1);
        assert(turns <= 3); // bounded: turns only until rollingTime elapses
    }
    // An unblocked roll never trips the guard.
    {
        Queen r;
        r.init(p, bank, false, false, {0, 0}, 0.0f, 13u);
        TickInput ri;
        ri.health = 5000.0f;
        ri.hits = 40;
        bool sawRolling = false, reachedWait = false, guard = false;
        for (int i = 0; i < 6000 && !reachedWait; ++i) {
            TickOutput o = r.tick(ri);
            ri.hits = 0;
            guard |= o.blockedTurn || o.blockedEnd;
            ri.pos.x += o.velocity.x * kSourceDelta;
            ri.pos.z += o.velocity.z * kSourceDelta;
            if (r.state() == Rolling) sawRolling = true;
            else if (sawRolling && r.state() == Wait) reachedWait = true;
        }
        assert(reachedWait && !guard);
    }
    // Death -> Dead -> KEYEVENT_END kill.
    in.health = 0.0f;
    TickOutput f4;
    assert(runUntil(d, in, Dead, 400, nullptr, &f4) >= 0);
    for (int i = 0; i < 200 && !f4.kill; ++i) f4.kill |= d.tick(in).kill;
    assert(f4.kill);

    // Bank grammar round trip.
    std::istringstream text("P2_QUEEN_BANK_1\nparm health 3300\nclip queen wait1 30 2 0 0 29 1 2 0 15\nend\n");
    Bank b2 = defaultBank();
    Params p2;
    std::string error;
    assert(parseBank(text, b2, p2, error));
    assert(p2.health == 3300.0f && p2.retail && b2.clip[AnimWait].poses.size() == 2);
    std::istringstream bad("P2_QUEEN_BANK_1\nclip queen nope 30 0 0\nend\n");
    assert(!parseBank(bad, b2, p2, error));

    // Baby: Born -> Move -> Attack near a target; press kills past Born.
    Baby baby;
    baby.init(p, bank, 0.0f, {0.0f, 50.0f});
    BabyInput bi;
    bi.health = 5.0f;
    bi.target.valid = true;
    bi.target.pos = {0.0f, 10.0f};
    bi.target.dist = 10.0f;
    bool attacked = false;
    for (int i = 0; i < 300 && !attacked; ++i) attacked = baby.tick(bi).attackKey;
    assert(attacked);
    // KEYEVENT_3 (frame 30) fires after KEYEVENT_2 unless the host reports an empty mouth.
    {
        Baby b2b;
        b2b.init(p, bank, 0.0f, {0.0f, 50.0f});
        bool k2 = false, k3 = false;
        for (int i = 0; i < 600 && !k3; ++i) {
            const BabyOutput t2 = b2b.tick(bi);
            k2 = k2 || t2.attackKey;
            k3 = k3 || t2.swallowKey;
        }
        assert(k2 && k3);
        Baby b3;
        b3.init(p, bank, 0.0f, {0.0f, 50.0f});
        bool missed = false, swallowed = false;
        int after = 0;
        for (int i = 0; i < 600 && after < 40; ++i) {
            const BabyOutput t3 = b3.tick(bi);
            if (missed) ++after;
            if (t3.attackKey && !missed) { b3.attackFailed(); missed = true; }
            swallowed = swallowed || t3.swallowKey;
        }
        assert(missed && !swallowed);
    }
    // Approach bearing -> part (footprint circles, height ignored).
    assert(exitPart(1.0f, 0.0f) == PartNose);   // straight at the nose
    assert(exitPart(-1.0f, 0.0f) == PartBod5);  // straight at the tail
    assert(exitPart(0.0f, 1.0f) == PartBod3);   // from the side
    assert(exitPart(0.0f, -1.0f) == PartBod3);
    assert(exitPart(0.7f, 0.7f) == PartBod1 || exitPart(0.7f, 0.7f) == PartBod2);
    // Flick part rule (Queen::flickPikmin): only nose/head/bod1 and bod5 get knockback.
    assert(nearestPart(235.0f, 0.0f, 90.0f) == PartNose && flickKind(PartNose) == FlickFront);
    assert(nearestPart(205.0f, 0.0f, 90.0f) == PartHead);
    assert(nearestPart(160.0f, 40.0f, 87.0f) == PartBod1 && flickKind(PartBod1) == FlickFront);
    assert(flickKind(nearestPart(90.0f, 60.0f, 87.0f)) == FlickNone);   // bod2
    assert(flickKind(nearestPart(0.0f, 50.0f, 87.0f)) == FlickNone);    // bod3
    assert(flickKind(nearestPart(-95.0f, 50.0f, 87.0f)) == FlickNone);  // bod4
    assert(nearestPart(-200.0f, 40.0f, 87.0f) == PartBod5 && flickKind(PartBod5) == FlickRear);
    // Cull spheres cover the staged pose-bank extents (Queen 385, Baby 36 from the origin).
    assert(cullRadius(false) > 385.0f && cullRadius(true) > 36.0f);
    // Mouth slot: radius 20 around a point 15 ahead of the root.
    assert(babyMouthReaches({0.0f, 0.0f}, 0.0f, {0.0f, 30.0f}, 0.0f));
    assert(!babyMouthReaches({0.0f, 0.0f}, 0.0f, {0.0f, -10.0f}, 0.0f));
    assert(!babyMouthReaches({0.0f, 0.0f}, 0.0f, {0.0f, 40.0f}, 0.0f));
    BabyOutput po;
    assert(baby.press(po) && baby.state() == BabyPress);
    std::puts("p2_queen_own_test OK");
    return 0;
}
