#pragma once
// Watery Blowhog breath stream: visual-only layout (owner playtest 2026-09-30,
// "no visible stream of water coming out of its nose"). Engine-free so the
// emission layout is unit-tested (tools/p2_tank_stream_test.cpp).
//
// What P2 draws (native/pikmin2-research): Wtank owns efx::TWtankEffect
// (Wtank.cpp:44-112): TTankWat, four synced JPA emitters PID_TankWat_1..4 that
// chase the hoppe joint matrix, created at the breath key event and faded when
// the breath ends, with TParticleCallBack_TankFire limiting particle travel to
// mMaxDistance (= the live breath range, Wtank.cpp:131-132) and TTankWatHit
// splashes where particles land; TTankWatYodare drools at the mouth after the
// attack (startYodare, TankState.cpp:911). P1 has none of those assets, so the
// port layers P1 water particles along the same emitter ray and range.
//
// This header only places points; it never reads or writes simulation state.
#include "pc_p2_attack_fx.h"

namespace p2tankstream {
constexpr int   POINTS_PER_TICK = 6;    // droplets along the live range each tick
constexpr int   MAX_POINTS      = POINTS_PER_TICK + 2; // + muzzle burst + tip splash
constexpr short DROP_LIFETIME   = 7;    // generator frames (30/s): overlap into a body
constexpr short MUZZLE_LIFETIME = 8;
constexpr float MIN_RANGE       = p2attackfx::MIN_RANGE; // below this the stream has not left the nose
constexpr int   MAX_LIVE_GENERATORS = p2attackfx::MAX_LIVE_GENERATORS;

enum class Kind { Muzzle, Drop, Tip };
struct Point { Kind kind; float x, y, z; float scale; };

// Thin adapter over the shared layout (pc_p2_attack_fx.h, Element::Water): the
// Watery Blowhog stream is the water preset of the shared attack-effect
// helpers, so the layout constants live in one place. Emitter origin (ox,oy,oz),
// unit XZ direction (dx,dz), live range from p2tankbreath::advance.
inline int layout(float ox, float oy, float oz, float dx, float dz, float range, unsigned tick, Point* out) {
    p2attackfx::Point pts[p2attackfx::MAX_STREAM_POINTS];
    const int n = p2attackfx::layoutStream(p2attackfx::Element::Water, ox, oy, oz, dx, dz, range, tick, 1.0f, pts);
    for (int i = 0; i < n; ++i) {
        const p2attackfx::Kind k = pts[i].kind;
        out[i] = {k == p2attackfx::Kind::Muzzle ? Kind::Muzzle : k == p2attackfx::Kind::Tip ? Kind::Tip : Kind::Drop,
                  pts[i].x, pts[i].y, pts[i].z, pts[i].scale};
    }
    return n;
}
} // namespace p2tankstream
