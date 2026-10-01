#include "pc_p2_kurage_fx.h"

#include "EffectMgr.h"
#include "zen/particle.h"


namespace {
// Lifetimes are generator frames (30/s). One burst per 30 Hz source tick, so a
// few frames of overlap read as a continuous upward stream while suction runs
// and nothing is left behind when it stops. One-shots self-terminate, so no
// generator handle is retained (a stored handle outlives its generator in the
// P1 pool, see pc_p2_groink_fx.cpp).
constexpr float kJetScale = 1.0f;
constexpr short kJetLife = 12;
constexpr float kJetCount = 1.0f;
constexpr short kDustLife = 10;
} // namespace

void pc_p2_kurage_fx_emit(const p2kuragefx::Command& c)
{
    if (c.kind != p2kuragefx::Kind::Suction || !effectMgr) return;
    const Vector3f ground(c.x, c.y, c.z);
    zen::particleGenerator* jet = effectMgr->create(EffectMgr::EFF_Mar_WindJet, ground, nullptr, nullptr);
    if (jet) {
        // TAImar.cpp:206-210: emit along the nozzle axis, ground-up normal. The
        // nozzle here points straight up into the bell.
        jet->setEmitPos(ground);
        jet->setEmitDir(Vector3f(0.0f, 1.0f, 0.0f));
        jet->setOrientedNormalVector(Vector3f(0.0f, 1.0f, 0.0f));
        jet->setScaleSize(kJetScale);
        jet->configureOneShotBurst(kJetCount, kJetLife);
    }
    {
        zen::particleGenerator* dust = effectMgr->create(EffectMgr::EFF_Mar_WindDust, ground, nullptr, nullptr);
        if (dust) {
            dust->setOrientedNormalVector(Vector3f(0.0f, 1.0f, 0.0f));
            dust->configureOneShotBurst(1.0f, kDustLife);
        }
    }
}
