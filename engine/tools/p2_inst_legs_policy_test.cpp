// inst-legs lane engine-free policy gate (#871): 56 Damagumo, 63 Jigumo, 69 BigFoot.
//
// Covers the campaign-policy half of the per-species done rule (host via
// campaign policy, bindable roster) plus the Long Legs source-FSM half for the
// two long-legs identities (Damagumo/BigFoot share pc_p2_long_legs_fsm; Jigumo
// runs the aquatic FSM in pc_p2_jigumo.cpp, proven by its arena + campaign
// runs). Engine-free: no engine types, no retail assets, no environment.
#include "pc_p2_campaign_policy.h"
#include "pc_p2_long_legs_fsm.h"
#include <cassert>
#include <cstdio>
#include <initializer_list>

int main() {
    // Campaign hosts: all three ride Chappy (3) in the identity path.
    for (int original = 0; original < 34; ++original) {
        assert(p2campaign::hostType(56, original, false) == 3);
        assert(p2campaign::hostType(63, original, false) == 3);
        assert(p2campaign::hostType(69, original, false) == 3);
        assert(p2campaign::hostType(56, original, true) == original);
        assert(p2campaign::hostType(63, original, true) == original);
        assert(p2campaign::hostType(69, original, true) == original);
    }
    assert(p2campaign::hasStaticHost(56));
    assert(p2campaign::hasStaticHost(63));
    assert(p2campaign::hasStaticHost(69));

    // Long Legs FSM: Damagumo wakes Stay->Land on a nearby target, fires feet
    // at landing key 2, then reaches Wait; BigFoot shares the cycle with its
    // fixed 5 s wait. One tick per state edge at the source 30 Hz delta.
    for (P2LongLegsSpecies species :
         {P2LongLegsSpecies::Damagumo, P2LongLegsSpecies::BigFoot}) {
        P2LongLegsFsm fsm;
        P2LongLegsFsmParms parms = p2LongLegsParmsFor(species);
        fsm.reset(parms);
        assert(fsm.state() == P2LongLegsState::Stay);
        P2LongLegsFsmInput in;
        P2LongLegsFsmOutput out;
        in.wakeTargetNearby = true;
        fsm.update(in, out);
        assert(fsm.state() == P2LongLegsState::Land);
        // Drive to key 2: landing fires feet and flips damageable.
        in = P2LongLegsFsmInput();
        in.health = parms.maxHealth;
        in.landingKey2 = true;
        in.ikMoveRatio = 2.0f;
        in.footDescendingOrPlanting = true;
        fsm.update(in, out);
        assert(out.footCrush || out.feetFired || fsm.state() == P2LongLegsState::Land);
        // Force the landing end: must leave Land for Wait/Walk/Shot/Dead.
        in = P2LongLegsFsmInput();
        in.health = parms.maxHealth;
        in.animEnd = true;
        for (int i = 0; i < 4 && fsm.state() == P2LongLegsState::Land; ++i)
            fsm.update(in, out);
        assert(fsm.state() != P2LongLegsState::Land);
        // Death is terminal with the source child/treasure intent.
        in = P2LongLegsFsmInput();
        in.health = 0.0f;
        in.killed = true;
        fsm.update(in, out);
        assert(fsm.state() == P2LongLegsState::Dead);
    }
    // Round-2 retail parms + intents: Damagumo 1300 HP / 25 ShijimiChou,
    // BigFoot 10000 HP / fixed 5 s wait / 10 s walk + 5 s post-flick / 30
    // Mitites; neither gunless species shoots (Houdai Shot branch unused).
    {
        const P2LongLegsFsmParms d = p2LongLegsParmsFor(P2LongLegsSpecies::Damagumo);
        assert(d.maxHealth == 1300.0f && d.deathChildren == 25 && !d.hasShotGun);
        assert(d.waitMinSeconds == 1.75f && d.waitMaxSeconds == 3.5f);
        const P2LongLegsFsmParms b = p2LongLegsParmsFor(P2LongLegsSpecies::BigFoot);
        assert(b.maxHealth == 10000.0f && b.deathChildren == 30 && !b.hasShotGun);
        assert(b.waitMinSeconds == 5.0f && b.waitMaxSeconds == 5.0f);
        assert(b.walkMinSeconds == 10.0f && b.walkPostFlickSeconds == 5.0f);
        P2LongLegsFsm fsm;
        P2LongLegsFsmInput in;
        P2LongLegsFsmOutput out;
        fsm.reset(d);
        in.killed = true;
        fsm.update(in, out);
        assert(out.birthChildren == 25 && !out.dropTreasure);
        fsm.reset(b);
        in = P2LongLegsFsmInput();
        in.killed = true;
        fsm.update(in, out);
        assert(out.birthChildren == 30 && !out.dropTreasure);
    }
    std::printf("PASS INST_LEGS_POLICY species=56,63,69\n");
    return 0;
}
