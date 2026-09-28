#include "pc_p2_otakara_fx.h"

#include <cstdio>

#ifdef P2_OTAKARA_FX_NO_ENGINE
// ---------------------------------------------------------------------------
// Engine-free build (p2_otakara_fx_test): no engine headers, null seams so
// the mapping and slot lifecycle stay unit-testable without linking the game.
// ---------------------------------------------------------------------------
void* pc_p2_otakara_fx_engine_spawn(int, float, float, float) { return nullptr; }
void pc_p2_otakara_fx_engine_kill(void*) {}
#else
// ---------------------------------------------------------------------------
// Game build: spawn the closest existing P1 hazard effect through the same
// EffectMgr::create API the P1 hazards use (cf. TAIhibaA EFF_Hiba_Fire,
// uteffect KandoEffect::Bubbles, taikinoko attack spores, ufoItem Biri).
// ---------------------------------------------------------------------------
#include "EffectMgr.h"

void* pc_p2_otakara_fx_engine_spawn(int effect, float x, float y, float z) {
    if (!effectMgr || effect < 0) return nullptr;
    Vector3f pos(x, y, z);
    zen::particleGenerator* gen =
        effectMgr->create(static_cast<EffectMgr::effTypeTable>(effect), pos, nullptr, nullptr);
    return static_cast<void*>(gen);
}

void pc_p2_otakara_fx_engine_kill(void* handle) {
    if (!handle) return;
    // Graceful stop (lets the flame/spark die out) mirroring the HibaA
    // finish-before-replace precedent (TAIhibaA.cpp finish() on attack end).
    static_cast<zen::particleGenerator*>(handle)->finish();
}
#endif

int pc_p2_otakara_fx_on_discharge(int species, float x, float y, float z) {
    const int effect = pc_p2_otakara_fx_effect_for_species(species);
    if (effect < 0) return -1;
    const int slot = pc_p2_otakara_fx_slot_index(species);
    if (slot < 0) return -1;
    P2OtakaraFxState& st = pc_p2_otakara_fx_state();
    // Refresh: finish a still-alive visual from the previous discharge before
    // replacing it, so rapid re-discharges never stack generators.
    if (st.slots[slot].used) pc_p2_otakara_fx_engine_kill(st.slots[slot].handle);
    void* handle = pc_p2_otakara_fx_engine_spawn(effect, x, y, z);
    st.slots[slot].used = true;
    st.slots[slot].species = species;
    st.slots[slot].effect = effect;
    st.slots[slot].x = x;
    st.slots[slot].y = y;
    st.slots[slot].z = z;
    st.slots[slot].ttl = P2_OTAKARA_FX_TTL;
    st.slots[slot].handle = handle;
    std::printf("P2_OTAKARA_FX species=%d effect=%d\n", species, effect);
    std::fflush(stdout);
    return effect;
}
