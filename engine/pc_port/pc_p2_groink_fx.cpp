#include "pc_p2_groink_fx.h"

#ifdef P2_GROINK_FX_NO_ENGINE
// Engine-free build (p2_groink_fx_test): the command policy is tested alone.
void pc_p2_groink_fx_spawn(const P2GroinkFxCommand&) {}
#else
#include "EffectMgr.h"
#include "UtEffect.h"

namespace {
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
    case P2GroinkFxKind::Trail:
        oneShot(kP2GroinkFxTrail, pos, nullptr);
        break;
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
