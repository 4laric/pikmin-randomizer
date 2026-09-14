#include "pc_p2_bigtreasure.h"

// Release builds pass -DNDEBUG; force assertions (and their embedded
// side effects) on so this engine-free gate is not vacuous under ctest.
#undef NDEBUG
#include <cassert>
#include <cmath>
#include <cstdio>

// Isolated fixtures for the BigTreasure (Titan Dweevil) weapon ownership and
// teardown contract, issue #246. Source references use US GPVE01 rev 0 at
// research revision 632af937 (paths abbreviated BigTreasure.cpp = BTC,
// BigTreasureState.cpp = BTS, BigTreasureAttack.cpp = BTA).

namespace {

bool near(float actual, float expected, float epsilon = 0.0001f)
{
    return std::fabs(actual - expected) <= epsilon;
}

void attachAll(P2BigTreasureOwnership& owner)
{
    for (int i = 0; i < P2BTWEAPON_Count; i++) owner.attachWeapon(i);
    owner.attachLouie();
}

// Phase transition: pinch smoke and the normal/damaged parameter switch at
// weapon HP 3000 (BTC addTreasureDamage :864-887, isNormalAttack :1200-1203).
void testPhaseTransition()
{
    P2BigTreasureOwnership owner;
    attachAll(owner);
    assert(owner.isNormalAttack(P2BTWEAPON_Fire));

    bool pinch = owner.addWeaponDamage(P2BTWEAPON_Fire, 2500.0f, false);
    assert(!pinch && owner.isNormalAttack(P2BTWEAPON_Fire)); // 3500 > 3000

    pinch = owner.addWeaponDamage(P2BTWEAPON_Fire, 600.0f, false);
    assert(pinch);                                  // crossed 3000 downward
    assert(!owner.isNormalAttack(P2BTWEAPON_Fire)); // damaged parameter set
    assert(near(owner.weaponHealth(P2BTWEAPON_Fire), 2900.0f));

    // Other weapons stay in their normal set: escalation is per weapon.
    assert(owner.isNormalAttack(P2BTWEAPON_Elec));

    // Exactly at 3000: pinch smoke has not fired (no downward crossing), but
    // isNormalAttack is already false (strict > in BTC :1200-1203).
    P2BigTreasureOwnership edge;
    edge.attachWeapon(P2BTWEAPON_Gas);
    pinch = edge.addWeaponDamage(P2BTWEAPON_Gas, 3000.0f, false);
    assert(!pinch && !edge.isNormalAttack(P2BTWEAPON_Gas)); // 3000 exactly
    // Starting exactly at 3000 and dipping below does fire the pinch smoke
    // (BTC :879-881: starting >= 3000 && result < 3000).
    pinch = edge.addWeaponDamage(P2BTWEAPON_Gas, 1.0f, false);
    assert(pinch && !edge.isNormalAttack(P2BTWEAPON_Gas));
}

// Knock-off at weapon HP 0: endCapture + upward pop, slot cleared, body
// exposure only at zero weapons (BTC :788-818, :670-697).
void testKnockOffAndBodyExposure()
{
    P2BigTreasureOwnership owner;
    attachAll(owner);
    assert(!owner.isBodyExposed());

    // Damage routing: Pikmin hits on weapon parts route to weapon HP.
    bool pinch = false;
    assert(owner.damageCallBack(true, true, P2BTWEAPON_Water, 6000.0f, P2BT_ItemWalk,
                                false, &pinch)
           == P2BTDMG_Weapon);
    assert(pinch); // 6000 -> 0 crosses 3000

    P2BigTreasureDropEvent drops[P2BTWEAPON_Count];
    std::size_t dropped = owner.update(drops, P2BTWEAPON_Count);
    assert(dropped == 1 && drops[0].weapon == P2BTWEAPON_Water && !drops[0].isLouie);
    assert(near(drops[0].velocity.y, P2BigTreasureOwnership::kKnockOffPopY));
    assert(!owner.isWeaponAttached(P2BTWEAPON_Water));
    assert(owner.weaponCount() == 3 && !owner.isBodyExposed());

    // Body hits while any weapon remains are ignored (BTC :266-271).
    assert(owner.damageCallBack(true, true, -1, 100.0f, P2BT_Walk, false) == P2BTDMG_Ignored);

    // Knock off the remaining three.
    for (int w = 0; w < 3; w++) {
        assert(owner.damageCallBack(true, true, w, 6000.0f, P2BT_ItemWalk, false)
               == P2BTDMG_Weapon);
    }
    dropped = owner.update(drops, P2BTWEAPON_Count);
    assert(dropped == 3 && owner.isBodyExposed());

    // Now body damage routes to the boss.
    assert(owner.damageCallBack(true, true, -1, 100.0f, P2BT_Walk, false) == P2BTDMG_Body);

    // Louie survives the fight; only death releases it (BTC :912-920).
    assert(owner.louieAttached());
}

// Damage routing rules: Pikmin-only, coll part required, Land quartering,
// bitter 0.1x on weapons (BTC :248-275, :864-887).
void testDamageRules()
{
    P2BigTreasureOwnership owner;
    attachAll(owner);

    assert(owner.damageCallBack(false, true, P2BTWEAPON_Elec, 100.0f, P2BT_ItemWalk, false)
           == P2BTDMG_Ignored); // Navi/bomb source ignored
    assert(owner.damageCallBack(true, false, P2BTWEAPON_Elec, 100.0f, P2BT_ItemWalk, false)
           == P2BTDMG_Ignored); // no coll part
    assert(near(owner.weaponHealth(P2BTWEAPON_Elec), 6000.0f));

    // Land quarters damage before it reaches the weapon.
    assert(owner.damageCallBack(true, true, P2BTWEAPON_Elec, 100.0f, P2BT_Land, false)
           == P2BTDMG_Weapon);
    assert(near(owner.weaponHealth(P2BTWEAPON_Elec), 5975.0f));

    // Bittered weapon damage is further reduced to 0.1x.
    assert(owner.damageCallBack(true, true, P2BTWEAPON_Elec, 100.0f, P2BT_ItemWalk, true)
           == P2BTDMG_Weapon);
    assert(near(owner.weaponHealth(P2BTWEAPON_Elec), 5965.0f));

    // hipdropCallBack returns the negation (BTC :281-284; source gap 3).
    assert(!owner.hipdropCallBack(true, true, P2BTWEAPON_Elec, 100.0f, P2BT_ItemWalk, false));
    assert(owner.hipdropCallBack(false, true, P2BTWEAPON_Elec, 100.0f, P2BT_ItemWalk, false));
    assert(owner.hipdropCallBack(true, true, -1, 100.0f, P2BT_ItemWalk, false)); // body while armed
}

// Health-weighted next-weapon pick (BTC setTreasureAttack :984-1035).
void testWeaponPick()
{
    P2BigTreasureOwnership owner;
    attachAll(owner);

    // All full health: bands are 6000 each in elec/fire/gas/water order.
    assert(owner.pickWeapon(0.0f) == P2BTWEAPON_Elec);
    assert(owner.pickWeapon(5999.9f) == P2BTWEAPON_Elec);
    assert(owner.pickWeapon(6000.0f) == P2BTWEAPON_Fire);
    assert(owner.pickWeapon(11999.9f) == P2BTWEAPON_Fire);
    assert(owner.pickWeapon(18000.0f) == P2BTWEAPON_Water);
    assert(owner.pickWeapon(23999.9f) == P2BTWEAPON_Water);
    assert(owner.pickWeapon(24000.0f) == -1); // past total

    // Damaged weapons widen their band (12000 - hp): hurt elec to 3000.
    owner.addWeaponDamage(P2BTWEAPON_Elec, 3000.0f, false);
    assert(owner.pickWeapon(6000.0f) == P2BTWEAPON_Elec);  // elec band now 9000
    assert(owner.pickWeapon(8999.9f) == P2BTWEAPON_Elec);
    assert(owner.pickWeapon(9000.0f) == P2BTWEAPON_Fire);

    // No weapons: BIGATTACK_NULL.
    P2BigTreasureOwnership empty;
    assert(empty.pickWeapon(0.0f) == -1);
}

// Attack pacing limit 4 + 2 * liveWeapons, 3x accrual, 225-box gate
// (BTC isAttackLimitTime :356-403).
void testAttackPacing()
{
    P2BigTreasureAttackPacer pacer;
    pacer.reset(0.0f);
    const float dt = 1.0f / 30.0f;

    // 4 weapons: threshold 12 s. Below threshold, never allowed.
    for (int i = 0; i < 300; i++) { // 10 s
        assert(!pacer.tick(dt, 4, true, false));
    }
    // Cross 12 s with a target in the box.
    for (int i = 0; i < 70 && !pacer.tick(dt, 4, true, false); i++) {
    }
    assert(pacer.tick(dt, 4, true, false));
    // Over threshold but no target in the 225 box: denied.
    assert(!pacer.tick(dt, 4, false, false));

    // Fewer weapons lower the threshold: 1 weapon = 6 s.
    pacer.reset(0.0f);
    for (int i = 0; i < 190; i++) pacer.tick(dt, 1, true, false);
    assert(pacer.tick(dt, 1, true, false));

    // Unstuck outsider nearby triples accrual (source uses strict >).
    pacer.reset(0.0f);
    for (int i = 0; i < 61; i++) pacer.tick(dt, 1, true, true); // >6 s of 3x time
    assert(pacer.tick(dt, 1, true, true));
}

// Weapon removed mid-attack: FSM guards (BTS :375-377,497-505,573-581,642-650).
void testWeaponLossGuards()
{
    // Chosen weapon knocked off mid-charge: re-enter PreAttack to re-pick.
    assert(p2_bigtreasure_weapon_loss_guard(P2BT_PreAttack, true, false) == P2BT_PreAttack);
    assert(p2_bigtreasure_weapon_loss_guard(P2BT_Attack, true, false) == P2BT_PreAttack);
    assert(p2_bigtreasure_weapon_loss_guard(P2BT_PutItem, true, false) == P2BT_PreAttack);

    // Last weapon knocked off: DropItem from every attack-family state.
    assert(p2_bigtreasure_weapon_loss_guard(P2BT_PreAttack, false, false) == P2BT_DropItem);
    assert(p2_bigtreasure_weapon_loss_guard(P2BT_Attack, false, false) == P2BT_DropItem);
    assert(p2_bigtreasure_weapon_loss_guard(P2BT_PutItem, false, false) == P2BT_DropItem);
    assert(p2_bigtreasure_weapon_loss_guard(P2BT_ItemWait, false, false) == P2BT_DropItem);

    // No loss: states continue.
    assert(p2_bigtreasure_weapon_loss_guard(P2BT_Attack, true, true) == P2BT_Attack);
    assert(p2_bigtreasure_weapon_loss_guard(P2BT_ItemWait, true, false) == P2BT_ItemWait);

    // Unrelated states pass through (Walk handles loss via animation swap).
    assert(p2_bigtreasure_weapon_loss_guard(P2BT_Walk, false, false) == P2BT_Walk);
    assert(p2_bigtreasure_weapon_loss_guard(P2BT_ItemWalk, false, false) == P2BT_ItemWalk);
}

// Defeat with weapons remaining: lane teardown for source gap 1 releases
// every captured pellet; nothing may outlive the owner.
void testDefeatWithWeaponsRemaining()
{
    P2BigTreasureOwnership owner;
    attachAll(owner);
    owner.addWeaponDamage(P2BTWEAPON_Gas, 1500.0f, false); // mid-fight state

    P2BigTreasureDropEvent drops[P2BTWEAPON_Count + 1];
    std::size_t released = owner.defeat(drops, P2BTWEAPON_Count + 1);
    assert(released == 5);

    int weaponEvents = 0;
    bool louieEvent  = false;
    for (std::size_t i = 0; i < released; i++) {
        if (drops[i].isLouie) {
            louieEvent = true;
            assert(near(drops[i].velocity.y, P2BigTreasureOwnership::kLouiePopY));
        } else {
            weaponEvents++;
            assert(near(drops[i].velocity.y, P2BigTreasureOwnership::kKnockOffPopY));
        }
    }
    assert(weaponEvents == 4 && louieEvent);
    assert(!owner.hasAnyWeapon() && !owner.louieAttached());

    // Death path in source also releases Louie alone (BTC onKill :115-120).
    P2BigTreasureOwnership owner2;
    owner2.attachLouie();
    P2BigTreasureDropEvent drop;
    assert(owner2.releaseLouie(&drop) && drop.isLouie);
    assert(!owner2.releaseLouie(&drop));
}

// Pool exhaustion per element (BTA constructor :1043-1097): emission fails
// softly; capacities are source-fixed.
void testPoolExhaustion()
{
    P2BigTreasureAttackPools pools;
    assert(pools.capacity(P2BTWEAPON_Fire) == 8);
    assert(pools.capacity(P2BTWEAPON_Gas) == 200);
    assert(pools.capacity(P2BTWEAPON_Water) == 16);
    assert(pools.capacity(P2BTWEAPON_Elec) == 17);

    assert(pools.start(P2BTWEAPON_Fire));
    assert(!pools.start(P2BTWEAPON_Fire)); // already started: no-op
    for (int i = 0; i < 8; i++) assert(pools.emit(P2BTWEAPON_Fire));
    assert(!pools.emit(P2BTWEAPON_Fire)); // exhausted: silent skip
    assert(pools.inFlight(P2BTWEAPON_Fire) == 8);
    assert(pools.recycleOne(P2BTWEAPON_Fire));
    assert(pools.emit(P2BTWEAPON_Fire));

    for (int i = 0; i < 200; i++) assert(pools.emit(P2BTWEAPON_Gas));
    assert(!pools.emit(P2BTWEAPON_Gas));

    for (int i = 0; i < 16; i++) assert(pools.emit(P2BTWEAPON_Water));
    assert(!pools.emit(P2BTWEAPON_Water));

    for (int i = 0; i < 17; i++) assert(pools.emit(P2BTWEAPON_Elec));
    assert(!pools.emit(P2BTWEAPON_Elec));

    // Invalid element is inert.
    assert(!pools.emit(-1) && !pools.start(99) && pools.inFlight(-1) == 0);
}

// Elec chain invariant: 1 anchor + maxDischarge <= 17 (BTA :2712-2782).
void testElecInvariant()
{
    P2BigTreasureAttackPools pools;
    assert(pools.setElecMaxDischarge(16));
    assert(!pools.setElecMaxDischarge(17)); // would need 18 nodes
    assert(!pools.setElecMaxDischarge(-1));
}

// finishAttack semantics: elec recycled, water persists (source gap 2,
// preserved); defeat recycles water too (lane teardown).
void testFinishAndWaterPersistence()
{
    P2BigTreasureAttackPools pools;
    pools.start(P2BTWEAPON_Elec);
    pools.start(P2BTWEAPON_Water);
    for (int i = 0; i < 5; i++) pools.emit(P2BTWEAPON_Elec);
    for (int i = 0; i < 3; i++) pools.emit(P2BTWEAPON_Water);

    pools.finishAttack();
    assert(!pools.isStarted(P2BTWEAPON_Elec) && !pools.isStarted(P2BTWEAPON_Water));
    assert(pools.inFlight(P2BTWEAPON_Elec) == 0);  // finishElecAttack recycles
    assert(pools.inFlight(P2BTWEAPON_Water) == 3); // finishWaterAttack is empty

    // In-flight bubbles keep hitting until ground impact after state exit.
    assert(pools.recycleOne(P2BTWEAPON_Water));
    assert(pools.inFlight(P2BTWEAPON_Water) == 2);

    // Bitter + lost weapon force-finishes the whole attack (BTA :1167-1175).
    pools.start(P2BTWEAPON_Gas);
    pools.emit(P2BTWEAPON_Gas);
    pools.bitterWeaponLost(P2BTWEAPON_Gas);
    assert(!pools.isStarted(P2BTWEAPON_Gas));
    assert(pools.inFlight(P2BTWEAPON_Water) == 2); // water still persists

    // Defeat: lane teardown force-recycles everything.
    pools.defeat();
    assert(pools.inFlight(P2BTWEAPON_Water) == 0);
    assert(pools.inFlight(P2BTWEAPON_Gas) == 0);
}

// Multi-actor lifetime: five captured pellets plus pooled nodes all end with
// the owner; no shared writes (single owner drives every transition).
void testMultiActorLifetime()
{
    P2BigTreasureOwnership owner;
    P2BigTreasureAttackPools pools;
    attachAll(owner);

    pools.start(P2BTWEAPON_Elec);
    pools.setElecMaxDischarge(16);
    for (int i = 0; i < 17; i++) pools.emit(P2BTWEAPON_Elec);
    pools.start(P2BTWEAPON_Water);
    for (int i = 0; i < 4; i++) pools.emit(P2BTWEAPON_Water);

    P2BigTreasureDropEvent drops[P2BTWEAPON_Count + 1];
    const std::size_t released = owner.defeat(drops, P2BTWEAPON_Count + 1);
    pools.defeat();

    assert(released == 5);
    assert(!owner.hasAnyWeapon() && !owner.louieAttached());
    for (int i = 0; i < P2BTWEAPON_Count; i++) {
        assert(pools.inFlight(i) == 0 && !pools.isStarted(i));
    }
}

} // namespace

int main()
{
    testPhaseTransition();
    testKnockOffAndBodyExposure();
    testDamageRules();
    testWeaponPick();
    testAttackPacing();
    testWeaponLossGuards();
    testDefeatWithWeaponsRemaining();
    testPoolExhaustion();
    testElecInvariant();
    testFinishAndWaterPersistence();
    testMultiActorLifetime();
    std::puts("p2_bigtreasure_test: all fixtures passed");
    return 0;
}
