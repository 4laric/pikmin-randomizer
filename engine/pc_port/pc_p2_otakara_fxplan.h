#pragma once
// Engine-free emitter layout for the Dweevil elemental attack visuals (59-62).
//
// P2 draws two things per attack (Fire|Water|Gas|ElecOtakara.cpp):
//   charge    efx::TOtaCharge{fire,wat,gas,elec}: follows the center joint during the wind-up
//             (setupEffect -> setMtxptr(center joint), startChargeEffect -> create,
//              finishChargeEffect -> fade at Flick event 3)
//   discharge efx::TOta{Fire,Wat,Gas,Elec}: a burst at mPosition at Flick event 3
// P2's JPA2 particles do not exist in the P1 zen system, so each one is mapped onto the closest
// P1 EffectMgr::effTypeTable emitters (include/EffectMgr.h). The mapping is a stand-in (labelled
// in the P2_OTAKARA_FX_START log); the timing, placement and lifecycle are the source's.
//
//   59 Fire   charge    EFF_Piki_Fire (43 pkf.pcr) + EFF_Piki_FireSparkles (44 pkf2.pcr): the
//                       burning-Pikmin flame pair, on the body
//             discharge EFF_Hiba_Fire (227 z_hiba.pcr, the flame-thrower column TAIhibaA drives)
//                       in a ring of 5 at radius 35 + EFF_Bomb_FireBang (34 bi_hiba1.pcr) at the
//                       centre
//   60 Water  charge    EFF_Piki_Bubble (36 pk_slime.pcr) + EFF_P_Bubbles (15 p_shibuki.pcr), scaled
//                       2x, on the body (the Mizu geyser set was tried and is near-invisible)
//             discharge EFF_Piki_Bubble in a ring of 5 at radius 35 (3x) + EFF_P_Bubbles 3x at the
//                       centre
//   61 Gas    charge    EFF_Kinoko_ChargeSpores (150 n_k_cg.pcr): the Puffstool charge spores
//             discharge EFF_Kinoko_AttackSpores (154) + EFF_Kinoko_AttackCloud (152) at the
//                       centre, EFF_Kinoko_PostAttackCloud (153) in a ring of 4 at radius 35
//   62 Elec   charge    EFF_Rocket_Biri (268 rkt_biri.pcr, "biri" = electric shock) +
//                       EFF_Rocket_Sparkles1 (325 pt_kira1.pcr) on the body
//             discharge EFF_Spider_SmallSparks (190 dg_hib2.pcr, sparks) in a ring of 5 at radius
//                       35 + EFF_Rocket_Biri (268) at the centre
//
// Every emitter is one P1 particle generator owned by the actor's ledger and stopped through
// EffectMgr::kill (pc_p2_otakara_attack.h Ledger); none is fire-and-forget.
namespace p2otakarafx {

struct Emit {
    int effect;   // EffectMgr::effTypeTable id
    int copies;   // 1 = at the anchor; >1 = ring of `copies` around it
    float radius; // ring radius
    float y;      // height above the anchor
    float scale;  // zen::particleGenerator::setScaleSize multiplier (1 = the effect's own size)
};

constexpr int kMaxEmits = 4;
constexpr int kMaxGenerators = 8; // per kind per actor (copies summed)

struct Plan {
    Emit emit[kMaxEmits];
    int count;
};

inline int generators(const Plan& p) {
    int n = 0;
    for (int i = 0; i < p.count; ++i) n += p.emit[i].copies;
    return n;
}

// Anchor: the body joint (follows the body every tick).
inline Plan charge(int species) {
    switch (species) {
    case 59: return {{{43, 3, 10.0f, 4.0f, 2.5f}, {44, 1, 0.0f, 0.0f, 2.5f}}, 2};
    case 60: return {{{36, 1, 0.0f, 0.0f, 2.0f}, {15, 1, 0.0f, 0.0f, 2.0f}}, 2};
    case 61: return {{{150, 1, 0.0f, 0.0f, 1.0f}}, 1};
    case 62: return {{{268, 1, 0.0f, 0.0f, 2.5f}, {325, 1, 0.0f, 0.0f, 3.0f}, {190, 3, 10.0f, 0.0f, 2.0f}}, 3};
    default: return {{}, 0};
    }
}

// Anchor: the Dweevil's position (mPosition at the discharge event), fixed for the window.
inline Plan discharge(int species) {
    switch (species) {
    case 59: return {{{227, 5, 35.0f, 0.0f, 1.0f}, {34, 1, 0.0f, 8.0f, 1.0f}}, 2};
    case 60: return {{{36, 5, 35.0f, 6.0f, 3.0f}, {15, 1, 0.0f, 8.0f, 3.0f}}, 2};
    case 61: return {{{154, 1, 0.0f, 8.0f, 1.0f}, {152, 1, 0.0f, 8.0f, 1.0f}, {153, 4, 35.0f, 8.0f, 1.0f}}, 3};
    case 62: return {{{190, 5, 35.0f, 6.0f, 1.5f}, {268, 1, 0.0f, 8.0f, 2.5f}, {189, 1, 0.0f, 8.0f, 2.0f}}, 3};
    default: return {{}, 0};
    }
}

inline const char* effectName(int id) {
    switch (id) {
    case 15: return "EFF_P_Bubbles";
    case 34: return "EFF_Bomb_FireBang";
    case 36: return "EFF_Piki_Bubble";
    case 189: return "EFF_Spider_DeadBombSparks";
    case 43: return "EFF_Piki_Fire";
    case 44: return "EFF_Piki_FireSparkles";
    case 150: return "EFF_Kinoko_ChargeSpores";
    case 152: return "EFF_Kinoko_AttackCloud";
    case 153: return "EFF_Kinoko_PostAttackCloud";
    case 154: return "EFF_Kinoko_AttackSpores";
    case 190: return "EFF_Spider_SmallSparks";
    case 193: return "EFF_Mizu_IdleBubbles";
    case 194: return "EFF_Mizu_IdleMist";
    case 195: return "EFF_Mizu_JetStream";
    case 227: return "EFF_Hiba_Fire";
    case 268: return "EFF_Rocket_Biri";
    case 325: return "EFF_Rocket_Sparkles1";
    default: return "EFF_UNKNOWN";
    }
}

} // namespace p2otakarafx
