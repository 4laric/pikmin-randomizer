#include "pc_p2_groink_fx.h"

#ifdef P2_GROINK_FX_NO_ENGINE
// Engine-free build (p2_groink_fx_test): the command policy is tested alone.
void pc_p2_groink_fx_spawn(const P2GroinkFxCommand&) {}
#else
#include "EffectMgr.h"
#include "UtEffect.h"
#include "MapMgr.h"
#include "zen/particle.h"

#include <algorithm>
#include <cstdlib>

namespace {
constexpr float kGlowScale = 1.6f;
// Lifetimes in generator frames (30/s). Each effect is re-emitted every tick,
// so a few frames overlap into a continuous body without leaving sprites behind.
constexpr short kGlowLifetime = 5;
constexpr short kMarkerLifetime = 4;
constexpr short kTrailLifetime = 10;
constexpr short kTetherLifetime = 4;
constexpr float kShadowNear = 1.6f;   // ring scale with the shell on the ground
constexpr float kShadowRefHeight = 40.0f;
constexpr float kShadowMin = 0.5f;
constexpr float kTetherMinHeight = 12.0f;

// PIKMIN_P2_GROINK_FX_LEGACY=1 restores the first cut (long-lived, sparse
// glow/marker) for before/after leak comparisons. Diagnostic only.
bool legacyFx() {
    static const bool legacy = [] {
        const char* v = std::getenv("PIKMIN_P2_GROINK_FX_LEGACY");
        return v && v[0] == '1';
    }();
    return legacy;
}
void oneShot(int effect, const Vector3f& pos, const P2GroinkVec3* dir) {
    zen::particleGenerator* gen =
        effectMgr->create(static_cast<EffectMgr::effTypeTable>(effect), pos, nullptr, nullptr);
    if (gen && dir) {
        // TAIbeatle.cpp:573-585: emit along the nozzle axis, ground-up normal.
        gen->setEmitDir(Vector3f(dir->x, dir->y, dir->z));
        gen->setOrientedNormalVector(Vector3f(0.0f, 1.0f, 0.0f));
    }
}
} // namespace

void pc_p2_groink_fx_spawn(const P2GroinkFxCommand& c) {
    if (!effectMgr) return;
    const Vector3f pos(c.pos.x, c.pos.y, c.pos.z);
    switch (c.kind) {
    case P2GroinkFxKind::Shoot:
        oneShot(kP2GroinkFxShootHalo, pos, &c.dir);
        oneShot(kP2GroinkFxShootSpecks, pos, &c.dir);
        break;
    case P2GroinkFxKind::Trail: {
        zen::particleGenerator* gen = effectMgr->create(
            static_cast<EffectMgr::effTypeTable>(kP2GroinkFxTrail), pos, nullptr, nullptr);
        if (gen && !legacyFx()) gen->configureOneShotBurst(1.0f, kTrailLifetime);
        break;
    }
    case P2GroinkFxKind::Glow: {
        static int legacyCount = 0;
        if (legacyFx() && (legacyCount++ % 3) != 0) break;
        zen::particleGenerator* gen = effectMgr->create(
            static_cast<EffectMgr::effTypeTable>(kP2GroinkFxGlow), pos, nullptr, nullptr);
        if (gen) {
            gen->setScaleSize(kGlowScale);
            if (!legacyFx()) gen->configureOneShotBurst(1.0f, kGlowLifetime);
        }
        break;
    }
    case P2GroinkFxKind::Marker: {
        // Floor shadow directly beneath the shell, re-emitted every tick so it
        // travels with it, plus tether puffs on the vertical line between the
        // two. Skip while the map is unavailable. Detached one-shots only.
        if (!mapMgr || !mapMgr->mMapModel) break;
        static int legacyCount = 0;
        if (legacyFx() && (legacyCount++ % 6) != 0) break;
        const float floorY = mapMgr->getMinY(pos.x, pos.z, true) + 2.0f;
        const float height = std::max(0.0f, pos.y - floorY);
        zen::particleGenerator* gen = effectMgr->create(
            static_cast<EffectMgr::effTypeTable>(kP2GroinkFxMarker), Vector3f(pos.x, floorY, pos.z), nullptr,
            nullptr);
        if (legacyFx()) {
            if (gen) gen->configureOneShotBurst(1.0f, 24);
            break;
        }
        if (gen) {
            const float scale = std::max(kShadowMin, kShadowNear * kShadowRefHeight / (kShadowRefHeight + height));
            gen->setScaleSize(scale);
            gen->configureOneShotBurst(1.0f, kMarkerLifetime);
        }
        if (height >= kTetherMinHeight) {
            for (int i = 1; i <= 2; ++i) {
                zen::particleGenerator* t = effectMgr->create(
                    static_cast<EffectMgr::effTypeTable>(kP2GroinkFxTrail),
                    Vector3f(pos.x, floorY + height * float(i) / 3.0f, pos.z), nullptr, nullptr);
                if (t) {
                    t->setScaleSize(0.5f);
                    t->configureOneShotBurst(1.0f, kTetherLifetime);
                }
            }
        }
        break;
    }
    case P2GroinkFxKind::Hit:
        if (utEffectMgr) {
            EffectParm parm(pos);
            utEffectMgr->cast(KandoEffect::BombLight, parm);
        }
        break;
    case P2GroinkFxKind::WaterHit:
        oneShot(kP2GroinkFxWater, pos, nullptr);
        break;
    }
}
#endif
