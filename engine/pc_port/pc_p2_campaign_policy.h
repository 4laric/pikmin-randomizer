#pragma once

// Native host types for the admitted campaign modules. This only chooses the
// engine vehicle; family setup still must bind its source behavior and assets.
// Never infer admission or a legal placement from this table.
namespace p2campaign {
inline int hostType(unsigned source, int original, bool protectedSpawn) {
    if (protectedSpawn) return original;
    switch (source) {
    case 9: case 44: case 59: case 60: case 61: case 62: case 79:
        return 3; // TEKI_Chappy (3; 4 is TEKI_Swallow): typed beetle/dwarf/dweevil/Skitter Leaf hosts
    // inst-chappy (#871): Chappy-family vehicles preserve the proven proxy
    // hosts (include/teki.h). The lane is complete: Chappy (2),
    // FireChappy (33), YellowChappy (43) and KingChappy (53) ride
    // TEKI_Swallow (4, P1 Spotty Bulborb), KumaChappy (35) rides
    // TEKI_Swallob (32, P1 Spotty Bulbear), LeafChappy (67) rides
    // TEKI_Chappy (3, P1 Dwarf Bulborb), KumaKochappy (76) rides
    // TEKI_Chappb (31, P1 Dwarf Bulbear).
    case 2: case 33: case 43: case 53:
        return 4; // TEKI_Swallow: Red/Fiery/Hairy/Emperor Bulborb adults
    case 35:
        return 32; // TEKI_Swallob: Spotty Bulbear
    case 67:
        return 3; // TEKI_Chappy: Bulbmin
    case 76:
        return 31; // TEKI_Chappb: Dwarf Bulbear
    // #948 (#951 U26): Orange Bulborb (42) binds only a TEKI_Chappy vehicle
    // (pc_p2_bluechappy.cpp bindActor); the Kabuto variants (95 Rkabuto,
    // 96 Fkabuto) bind only TEKI_Beatle (pc_p2_enemy.cpp
    // pc_p2_kabuto_bind_dynamic). Without a row they rode whatever the slot
    // P1 original was and refused on every other slot.
    case 42: return 3; // TEKI_Chappy: BlueChappy adult host
    case 95: case 96: return 17; // TEKI_Beatle: Kabuto variant hosts
    // Sarai binds whatever type its anchor carries (pc_p2_sarai_manager.cpp:109,119),
    // so 3 here is the placement vehicle, not a requirement. "Kochappy" is the P2 name
    // for the Dwarf Bulborb; the P1 enum for it is TEKI_Chappy, and there is no
    // TEKI_Kochappy in include/teki.h.
    case 23: return 3; // TEKI_Chappy: Sarai ordinary-host path
    // #215: Demon (Bumbling Snitchbug) is a Sarai::Obj subclass and rides the
    // same Sarai host/anchor vehicle with its species profile.
    case 32: return 3; // TEKI_Chappy: Demon profile of the Sarai host
    case 28: case 68: return 3; // TEKI_Chappy: ElecBug/TamagoMushi ground hosts
    case 94: return 4; // TEKI_Swallow: DangoMushi snagret host
    case 12: return 18; // TEKI_KabekuiA: UjiA Female Sheargrub host
    case 13: return 19; // TEKI_KabekuiB: UjiB Male Sheargrub host
    case 14: return 20; // TEKI_KabekuiC: Tobi Shearwig host
    case 54: return 24; // TEKI_Miurin: Mamuta
    case 57: case 72: case 78: return 0; // TEKI_Frog: Jellyfloat (Kurage/OniKurage)/Groink sidecar hosts
    // #244 OWN: Careening Dirigibug rides the P1 flying vehicle TEKI_Napkid
    // (11); pc_p2_bombsarai_own_setup binds only this host type.
    case 58: return 11; // TEKI_Napkid: BombSarai OWN campaign host
    case 17: return 0; // TEKI_Frog: Yellow Wollywog (inst-frogs #871)
    case 18: return 33; // TEKI_Frow: Wollywog (inst-frogs #871)
    case 24: return 15; // TEKI_Tank: Fiery Blowhog (inst2-frogs #871)
    case 25: return 15; // TEKI_Tank: Watery Blowhog (inst2-frogs #871)
    case 15: return 3; // TEKI_Chappy: Cloaking Burrow-nit (inst2-frogs #871)
    case 75: return 17; // TEKI_Beatle: Armored Cannon Beetle Larva (inst2-frogs #871)
    // inst-legs lane (#871): Damagumo (56, Beady Long Legs) + BigFoot (69,
    // Raging Long Legs) ride the Chappy placement vehicle the pc_p2_long_legs
    // host expects (setup fails otherwise); Jigumo (63, Hermit Crawmad) rides
    // Chappy like the pc_p2_jigumo aquatic host. Proxy rows used Swallow (4)
    // for 56/69; the identity path standardizes on Chappy (3).
    case 56: case 63: case 69: return 3; // TEKI_Chappy: legs-lane identity hosts
    // inst-worms lane (#871): snagret pair (34/70), Imomushi (65) and bloyster
    // pair (71/101) all run on the P1 Chappy placement vehicle, matching the
    // native modules' TEKI_Chappy expectation (pc_p2_snakejoint.cpp,
    // pc_p2_imomushi.cpp, pc_p2_umimushi.cpp).
    case 34: case 70: case 65: case 71: case 101: return 3; // TEKI_Chappy
    case 26: return 30; // TEKI_Namazu: Catfish (Water Dumple) aquatic host
    case 27: return 25; // TEKI_Otama: Tadpole (Wogpole) aquatic host
    case 84: return 3; // TEKI_Chappy: Hana (Creeping Chrysanthemum)
    case 93: return 3; // TEKI_Chappy: BombOtakara (Volatile Dweevil)
    // #245 OWN: Antenna Beetle (Fuefuki) rides a suppressed Chappy ground
    // vehicle with a LeaveCorpse carcass (pc_p2_fuefuki_teki_setup asserts
    // TEKI_Chappy); never the Napkid flyer the proxy tier used.
    case 41: return 3; // TEKI_Chappy: Fuefuki
    case 66: return 4; // TEKI_Swallow: Houdai (Man-at-Legs) proxy vehicle
    case 97: return 0; // TEKI_Frog: FminiHoudai (Gatling Groink pedestal) proxy vehicle
    // #898: Breadbug (PanModoki 38) rides the P1 Breadbug host TEKI_Collec (8)
    // as a placement vehicle only; pc_p2_breadbug_teki runs the source FSM.
    case 38: return 8; // TEKI_Collec: Breadbug OWN vehicle
    // #958: Giant Breadbug (OoPanModoki 40) runs the same OWN driver on the same vehicle.
    case 40: return 8; // TEKI_Collec: Giant Breadbug OWN vehicle
    // #246 OWN: BigTreasure (Titan Dweevil) rides the TEKI_Swallow placement
    // vehicle driven by pc_p2_bigtreasure_teki (source-order core).
    case 73: return 4; // TEKI_Swallow: BigTreasure campaign actor
    case 30: return 4; // TEKI_Swallow: Empress Bulblax OWN vehicle (#256, pc_p2_queen_teki)
    // #1042: the standalone Bulborb Larva (Baby) rides the same vehicle at larva scale
    // (the Queen-born larvae already do); pc_p2_queen_teki binds it.
    case 31: return 4; // TEKI_Swallow: Bulborb Larva OWN vehicle
    default: return original;
    }
}
inline bool hasStaticHost(unsigned source) {
    return hostType(source, -1, false) == hostType(source, -2, false);
}
}
