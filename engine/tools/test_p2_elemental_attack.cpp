#include "pc_p2_elemental_attack.h"
#include <cassert>
#include <cstdio>

// Lane 10 + 32 emitter/receiver decision test (#170/#408, #246). The four
// BigTreasure weapons deliver the four P2 elemental stimuli to live Pikmin
// through the real source receivers; this pins the shared decision table so an
// emitter cannot deliver an element the receiver would reject, and vice versa.
//
// Source basis (native/pikmin2-research, US GPVE01 revision 0,
// src/plugProjectKandoU/interactPiki.cpp):
//   InteractFire::actPiki   :445  reject Red/Bulbmin
//   InteractBubble::actPiki :503  reject Blue/Bulbmin
//   InteractDenki::actPiki  :334  reject Yellow/Bulbmin
//   InteractGas::actPiki    :531  reject White/Bulbmin (+ Piki::gasInvicible)
int main() {
    // Weapon -> element mapping uses the source BigTreasure weapon enum.
    assert(p2_elemental_attack_for_weapon(P2BTWEAPON_Elec) == P2ElementalAttackElectric);
    assert(p2_elemental_attack_for_weapon(P2BTWEAPON_Fire) == P2ElementalAttackFire);
    assert(p2_elemental_attack_for_weapon(P2BTWEAPON_Gas) == P2ElementalAttackGas);
    assert(p2_elemental_attack_for_weapon(P2BTWEAPON_Water) == P2ElementalAttackWater);
    assert(p2_elemental_attack_for_weapon(-1) == -1);
    assert(p2_elemental_attack_for_weapon(P2BTWEAPON_Count) == -1);

    // Element -> lane-11 hazard id.
    assert(p2_elemental_attack_hazard(P2ElementalAttackFire) == P2HazardFire);
    assert(p2_elemental_attack_hazard(P2ElementalAttackWater) == P2HazardWater);
    assert(p2_elemental_attack_hazard(P2ElementalAttackElectric) == P2HazardElectric);
    assert(p2_elemental_attack_hazard(P2ElementalAttackGas) == P2HazardGas);
    assert(p2_elemental_attack_hazard(-1) == -1);
    assert(p2_elemental_attack_hazard(P2ElementalAttackCount) == -1);

    // Fire: only Red and Bulbmin are immune; every other species is affected.
    assert(!p2_elemental_attack_accepts(P2ElementalAttackFire, P2SpeciesRed, false));
    assert(!p2_elemental_attack_accepts(P2ElementalAttackFire, P2SpeciesBulbmin, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackFire, P2SpeciesBlue, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackFire, P2SpeciesYellow, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackFire, P2SpeciesPurple, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackFire, P2SpeciesWhite, false));

    // Water: only Blue and Bulbmin are immune.
    assert(!p2_elemental_attack_accepts(P2ElementalAttackWater, P2SpeciesBlue, false));
    assert(!p2_elemental_attack_accepts(P2ElementalAttackWater, P2SpeciesBulbmin, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackWater, P2SpeciesRed, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackWater, P2SpeciesYellow, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackWater, P2SpeciesPurple, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackWater, P2SpeciesWhite, false));

    // Electric: only Yellow and Bulbmin are immune; the rest take the lethal
    // DenkiDying path.
    assert(!p2_elemental_attack_accepts(P2ElementalAttackElectric, P2SpeciesYellow, false));
    assert(!p2_elemental_attack_accepts(P2ElementalAttackElectric, P2SpeciesBulbmin, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackElectric, P2SpeciesRed, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackElectric, P2SpeciesBlue, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackElectric, P2SpeciesPurple, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackElectric, P2SpeciesWhite, false));

    // Gas: only White and Bulbmin are immune; every other species panics.
    assert(!p2_elemental_attack_accepts(P2ElementalAttackGas, P2SpeciesWhite, false));
    assert(!p2_elemental_attack_accepts(P2ElementalAttackGas, P2SpeciesBulbmin, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackGas, P2SpeciesRed, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackGas, P2SpeciesBlue, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackGas, P2SpeciesYellow, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackGas, P2SpeciesPurple, false));

    // The gas-invincibility gate suppresses only the gas element (source
    // Piki::gasInvicible) and never touches the other three.
    assert(!p2_elemental_attack_accepts(P2ElementalAttackGas, P2SpeciesRed, true));
    assert(!p2_elemental_attack_accepts(P2ElementalAttackGas, P2SpeciesPurple, true));
    assert(!p2_elemental_attack_accepts(P2ElementalAttackFire, P2SpeciesRed, true)); // Red is still fire-immune
    assert(p2_elemental_attack_accepts(P2ElementalAttackFire, P2SpeciesBlue, true));
    assert(p2_elemental_attack_accepts(P2ElementalAttackElectric, P2SpeciesRed, true));
    assert(p2_elemental_attack_accepts(P2ElementalAttackWater, P2SpeciesRed, true));

    // An unknown species is not immune, so it follows the affected path; an
    // invalid element never accepts.
    assert(p2_elemental_attack_accepts(P2ElementalAttackFire, 99, false));
    assert(p2_elemental_attack_accepts(P2ElementalAttackElectric, 99, false));
    assert(!p2_elemental_attack_accepts(-1, P2SpeciesRed, false));
    assert(!p2_elemental_attack_accepts(P2ElementalAttackCount, P2SpeciesRed, false));

    std::puts("PASS P2_ELEMENTAL_ATTACK");
    return 0;
}
