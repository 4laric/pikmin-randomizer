#pragma once

#include "pc_p2_bigtreasure.h"
#include "pc_p2_hazard_reaction.h"

// Lane 10 + 32: BigTreasure (Titan Dweevil, enemy ID 73) elemental attack ->
// Pikmin receiver contract (#170/#408, #246). The four Titan weapons deliver the
// four P2 elemental stimuli; this names the stimulus and provides the shared
// emitter-side decision. It consults the same lane-11 `p2_species_immune` matrix
// the Pikmin receiver reads (pc_p2_hazard_reaction.h), so an emitter and its
// receiver cannot disagree about immunity.
//
//   Fire   (Flare Cannon)     -> InteractFire   (source P1 receiver; reject Red/Bulbmin)
//   Water  (Monster Pump)     -> InteractBubble (source P1 receiver; reject Blue/Bulbmin)
//   Elec   (Shock Therapist)  -> InteractDenki  (lane-10 receiver; reject Yellow/Bulbmin)
//   Gas    (Comedy Bomb)      -> InteractGas     (lane-10 receiver; reject White/Bulbmin)
//
// Source basis (native/pikmin2-research, US GPVE01 revision 0,
// src/plugProjectKandoU/interactPiki.cpp):
//   InteractFire::actPiki   :445, reject Red/Bulbmin
//   InteractBubble::actPiki :503, reject Blue/Bulbmin
//   InteractDenki::actPiki  :334, reject Yellow/Bulbmin -> PIKISTATE_DenkiDying
//   InteractGas::actPiki    :531, gas gate + reject White/Bulbmin -> PIKISTATE_Panic
//
// Header-only and engine-free so tools/test_p2_elemental_attack.cpp can pin the
// decision table without linking the engine, following pc_p2_hazard_reaction.h.

enum P2ElementalAttack {
    P2ElementalAttackFire = 0,
    P2ElementalAttackWater = 1,
    P2ElementalAttackElectric = 2,
    P2ElementalAttackGas = 3,
    P2ElementalAttackCount = 4,
};

// BigTreasure weapon -> the element it emits. Uses the source enum so a weapon
// reordering cannot silently mis-map; returns -1 for an invalid weapon.
inline int p2_elemental_attack_for_weapon(int weapon) {
    switch (weapon) {
    case P2BTWEAPON_Elec: return P2ElementalAttackElectric;
    case P2BTWEAPON_Fire: return P2ElementalAttackFire;
    case P2BTWEAPON_Gas: return P2ElementalAttackGas;
    case P2BTWEAPON_Water: return P2ElementalAttackWater;
    default: return -1;
    }
}

// Element -> lane-11 hazard id (pc_p2_species_policy.h). -1 for an invalid id.
inline int p2_elemental_attack_hazard(int element) {
    switch (element) {
    case P2ElementalAttackFire: return P2HazardFire;
    case P2ElementalAttackWater: return P2HazardWater;
    case P2ElementalAttackElectric: return P2HazardElectric;
    case P2ElementalAttackGas: return P2HazardGas;
    default: return -1;
    }
}

// True when the Pikmin receiver will accept the delivered element. False for an
// immune species, and for the gas element while `gasInvincible` (the source
// Piki::gasInvicible gate). Mirrors each receiver's `actPiki` rejection exactly.
inline bool p2_elemental_attack_accepts(int element, int species, bool gasInvincible) {
    const int hazard = p2_elemental_attack_hazard(element);
    if (hazard < 0) {
        return false;
    }
    if (element == P2ElementalAttackGas && gasInvincible) {
        return false;
    }
    return !p2_species_immune(species, hazard);
}
