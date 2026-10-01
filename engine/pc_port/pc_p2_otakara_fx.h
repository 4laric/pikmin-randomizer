#pragma once

// Visible Otakara discharge attacks (#170, rd-p2-otakara-fx).
//
// The elemental Otakara discharge (pc_p2_otakara.cpp doDischarge) applies its
// element through the engine receivers but spawns no particle, so the attack
// is invisible. This module maps each discharge species to the closest
// existing P1 hazard visual (a real EffectMgr::effTypeTable id, see
// include/EffectMgr.h) and spawns it at the discharge position:
//
//   source 59 FireOtakara -> EFF_Hiba_Fire (227, z_hiba.pcr): the P1 fire
//       geyser flame, src/plugPikiYamashita/TAIhibaA.cpp:144.
//   source 60 WaterOtakara -> EFF_P_Bubbles (15, p_shibuki.pcr): the engine
//       bubble/water hit visual (KandoEffect::Bubbles),
//       src/plugPikiKando/uteffect.cpp:116.
//   source 61 GasOtakara -> EFF_Kinoko_AttackSpores (154, k_bafuh1.pcr): the
//       Puffstool attack spore burst, the closest P1 analogue of a poison-gas
//       discharge, src/plugPikiNakata/taikinoko.cpp:478.
//   source 62 ElecOtakara -> EFF_Rocket_Biri (268, rkt_biri.pcr): the P1
//       electric-spark trouble visual ("biri" = electric shock),
//       src/plugPikiKando/ufoItem.cpp:200-201.
//
// Lifetime contract: each discharge spawns a finite one-shot particle whose
// authored emission window is the visual duration; no generator handle is
// retained, so there is nothing outstanding to stop on actor death or scene
// end (scene teardown stays owned by the engine's own EffectMgr::killAll).
// The per-species slot below is bookkeeping only: it records the latest
// discharge per species for the P2_OTAKARA_FX log and lets a repeat discharge
// finish a still-alive visual before replacing it, mirroring the hazard
// precedent (TAIhibaA finish-before-replace).
//
// Engine-free by construction (plain data + printf only) so the mapping and
// the slot lifecycle stay unit-testable; the real EffectMgr::create call
// lives in pc_p2_otakara_fx.cpp, which compiles engine-free under
// P2_OTAKARA_FX_NO_ENGINE for the p2_otakara_fx_test target.

// P1 EffectMgr::effTypeTable ids (include/EffectMgr.h) per Otakara source id.
// Unknown species (including BombOtakara 93, which delegates to the lane-20
// Bomb payload and has no self-contained discharge) map to -1: no visual.
inline int pc_p2_otakara_fx_effect_for_species(int species) {
    switch (species) {
    case 59: return 227; // EFF_Hiba_Fire
    case 60: return 15;  // EFF_P_Bubbles
    case 61: return 154; // EFF_Kinoko_AttackSpores
    case 62: return 268; // EFF_Rocket_Biri
    default: return -1;
    }
}

inline const char* pc_p2_otakara_fx_effect_name(int effect) {
    switch (effect) {
    case 227: return "EFF_Hiba_Fire";
    case 15: return "EFF_P_Bubbles";
    case 154: return "EFF_Kinoko_AttackSpores";
    case 268: return "EFF_Rocket_Biri";
    default: return "EFF_UNKNOWN";
    }
}

// Number of tracked discharge slots: exactly one per elemental species.
#define P2_OTAKARA_FX_SLOTS 4
// Visual tail (seconds) covering the Flick clip remainder after the frame-35
// discharge event; port adaptation, not a retail value.
#define P2_OTAKARA_FX_TTL 0.6f

struct P2OtakaraFxSlot {
    bool used;
    int species;
    int effect;
    float x;
    float y;
    float z;
    float ttl;
    void* handle;
};

struct P2OtakaraFxState {
    P2OtakaraFxSlot slots[P2_OTAKARA_FX_SLOTS];
};

inline P2OtakaraFxState& pc_p2_otakara_fx_state() {
    static P2OtakaraFxState state = {};
    return state;
}

inline int pc_p2_otakara_fx_slot_index(int species) {
    return (species >= 59 && species <= 62) ? species - 59 : -1;
}

inline void pc_p2_otakara_fx_reset() {
    P2OtakaraFxState& st = pc_p2_otakara_fx_state();
    for (int i = 0; i < P2_OTAKARA_FX_SLOTS; ++i) {
        st.slots[i].used = false;
        st.slots[i].species = 0;
        st.slots[i].effect = -1;
        st.slots[i].x = st.slots[i].y = st.slots[i].z = 0.0f;
        st.slots[i].ttl = 0.0f;
        st.slots[i].handle = nullptr;
    }
}

inline int pc_p2_otakara_fx_active_count() {
    P2OtakaraFxState& st = pc_p2_otakara_fx_state();
    int n = 0;
    for (int i = 0; i < P2_OTAKARA_FX_SLOTS; ++i) {
        if (st.slots[i].used) ++n;
    }
    return n;
}

// Discharge entry: maps the species, spawns the P1 effect at (x, y, z),
// records the slot and logs P2_OTAKARA_FX once per discharge. Defined in
// pc_p2_otakara_fx.cpp (needs the engine spawn seam); returns the P1 effect
// id, or -1 when the species has no visual.
int pc_p2_otakara_fx_on_discharge(int species, float x, float y, float z);

// Engine spawn seam (defined in pc_p2_otakara_fx.cpp): real
// effectMgr->create in game builds, null in P2_OTAKARA_FX_NO_ENGINE builds.
void* pc_p2_otakara_fx_engine_spawn(int effect, float x, float y, float z);
// Engine kill seam: gracefully finishes a still-alive visual (particle
// finish(), mirroring TAIhibaA), or a no-op in NO_ENGINE builds.
void pc_p2_otakara_fx_engine_kill(void* handle);

// Advances visual tails; finishing expired handles. Engine-free.
inline void pc_p2_otakara_fx_update(float dt) {
    if (dt <= 0.0f) return;
    P2OtakaraFxState& st = pc_p2_otakara_fx_state();
    for (int i = 0; i < P2_OTAKARA_FX_SLOTS; ++i) {
        if (!st.slots[i].used) continue;
        st.slots[i].ttl -= dt;
        if (st.slots[i].ttl <= 0.0f) {
            pc_p2_otakara_fx_engine_kill(st.slots[i].handle);
            st.slots[i].used = false;
            st.slots[i].handle = nullptr;
        }
    }
}

// Death/scene-end cleanup: finishes every outstanding visual and clears the
// ledger. One-shot spawns self-terminate, so this is normally a no-op ledger
// reset; it exists so a future tick hookup has a defined teardown entry.
inline void pc_p2_otakara_fx_clear() {
    P2OtakaraFxState& st = pc_p2_otakara_fx_state();
    for (int i = 0; i < P2_OTAKARA_FX_SLOTS; ++i) {
        if (!st.slots[i].used) continue;
        pc_p2_otakara_fx_engine_kill(st.slots[i].handle);
        st.slots[i].used = false;
        st.slots[i].handle = nullptr;
    }
}
