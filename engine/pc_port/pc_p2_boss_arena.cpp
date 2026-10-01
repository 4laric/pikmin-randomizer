#include "pc_p2_boss_arena.h"

#include "pc_p2_boss_arena_policy.h"
#include "pc_p2_campaign_policy.h"
#include "pc_p2_generated_placement.h"
#include "pc_held_part.h"
#include "pc_p2_kabuto_host.h"
#include "pc_p2_placement_probe.h"
#include "pc_randomizer.h"

#include "Generator.h"
#include "MapCode.h"
#include "MapMgr.h"
#include "TekiPersonality.h"
#include "teki.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {

unsigned boundSource(Generator* generator, unsigned* uidOut)
{
    if (!generator || !pc_randomizer_p2_bridge()) return 0;
    const unsigned uid = pc_randomizer_generator_id(generator);
    if (uidOut) *uidOut = uid;
    return uid ? pc_randomizer_p2_source_for_id(uid) : 0;
}

bool finite(float x, float y, float z)
{
    return std::isfinite(x) && std::isfinite(y) && std::isfinite(z)
        && std::fabs(x) <= 100000.0f && std::fabs(z) <= 100000.0f;
}

} // namespace

void pc_p2_boss_arena_rekey(Generator* generator)
{
    if (!generator || !pc_randomizer_p2_bridge()) return;
    const unsigned uid = pc_randomizer_generator_id(generator);
    const unsigned primary = p2bossarena::aliasPrimary(uid);
    if (primary && pc_randomizer_p2_source_for_id(primary)) {
        pc_randomizer_set_generator_id(generator, primary);
        std::printf("P2_BOSS_ARENA_ALIAS generator=%u primary=%u\n", uid, primary);
        std::fflush(stdout);
    }
}

int pc_p2_boss_arena_host(Generator* generator)
{
    const unsigned source = boundSource(generator, nullptr);
    if (!source) return -1;
    const int host = p2bossarena::hostFor(source, p2campaign::hostType);
    return (host >= TEKI_START && host < TEKI_TypeCount) ? host : -1;
}

void pc_p2_reserve_source_extras(Generator* generator)
{
    const unsigned source = boundSource(generator, nullptr);
    if (source == 94 && tekiMgr && !tekiMgr->mUsingType[TEKI_Iwagon]) {
        // Without this the rain Rocks/Egg are simulated but never drawn on a
        // stage whose own generators hold no Iwagon (the impact_goolix arena).
        tekiMgr->mUsingType[TEKI_Iwagon] = true;
        std::printf("P2_DANGOMUSHI_RAIN_MESH_RESERVED generator=%u type=%d\n",
                    pc_randomizer_generator_id(generator), int(TEKI_Iwagon));
        std::fflush(stdout);
    }
}

bool pc_p2_boss_arena_suppressed(Generator* generator)
{
    if (!generator || !pc_randomizer_p2_bridge()) return false;
    const unsigned primary = p2bossarena::suppressPrimary(pc_randomizer_generator_id(generator));
    return primary && pc_randomizer_p2_source_for_id(primary) != 0;
}

void pc_p2_boss_arena_probe(float x, float y, float z, unsigned uid, const char* kind, int type)
{
    if (!mapMgr || !finite(x, y, z)) return;
    // 16 rays in 25-unit steps out to 500 (the #256 boss-slot rule extended to
    // measure the arena, not just pass 250): a ray stops at missing ground,
    // water, a height step over 20 between samples, or ground more than 60
    // from the arena floor. `clear` is the smallest reach (a flat dry disc),
    // `median` the typical reach (arena size).
    const float centre = mapMgr->getMinY(x, z, true);
    float reach[16];
    int water = 0, offmap = 0, walls = 0;
    const bool centreWater = [&] {
        CollTriInfo* tri = mapMgr->getCurrTri(x, z, true);
        return tri && MapCode::getAttribute(tri) == ATTR_Water;
    }();
    for (int ray = 0; ray < 16; ++ray) {
        const float a = float(ray) * 6.2831853f / 16.0f;
        float prev = centre;
        reach[ray] = 0.0f;
        for (float r = 25.0f; r <= 500.0f; r += 25.0f) {
            const float px = x + std::sin(a) * r, pz = z + std::cos(a) * r;
            CollTriInfo* tri = mapMgr->getCurrTri(px, pz, true);
            if (!tri) { ++offmap; break; }
            if (MapCode::getAttribute(tri) == ATTR_Water) { ++water; break; }
            const float h = mapMgr->getMinY(px, pz, true);
            if (std::fabs(h - prev) > 20.0f || std::fabs(h - centre) > 60.0f) { ++walls; break; }
            prev = h;
            reach[ray] = r;
        }
    }
    float sorted[16];
    std::memcpy(sorted, reach, sizeof(sorted));
    std::sort(sorted, sorted + 16);
    char rays[16 * 5 + 1] = {};
    int used = 0;
    for (int ray = 0; ray < 16 && used < int(sizeof(rays)) - 5; ++ray)
        used += std::snprintf(rays + used, sizeof(rays) - used, ray ? ",%d" : "%d", int(reach[ray]));
    std::printf("P2_BOSS_ARENA_PROBE uid=%u kind=%s type=%d clear=%.0f median=%.0f max=%.0f water_rays=%d "
                "offmap_rays=%d wall_rays=%d centre_water=%d x=%.1f y=%.1f z=%.1f rays=%s\n",
                uid, kind ? kind : "?", type, double(sorted[0]), double((sorted[7] + sorted[8]) * 0.5f),
                double(sorted[15]), water, offmap, walls, centreWater ? 1 : 0, double(x), double(centre),
                double(z), rays);
    std::fflush(stdout);
}

Creature* pc_p2_boss_arena_birth(BirthInfo& info, const GenObjectBoss& boss)
{
    unsigned uid = 0;
    const unsigned source = boundSource(info.mGenerator, &uid);
    if (!source) return nullptr;
    const int host = p2bossarena::hostFor(source, p2campaign::hostType);
    if (!tekiMgr || host < TEKI_START || host >= TEKI_TypeCount || !tekiMgr->hasType(host)) {
        std::printf("P2_BOSS_ARENA_BIRTH source_id=%u target=%u p1_boss=%d host=%d ok=0 reason=host-type-not-loaded\n",
                    source, uid, boss.mBossID, host);
        std::fflush(stdout);
        return nullptr;
    }
    Teki* teki = tekiMgr->newTeki(host);
    if (!teki) {
        std::printf("P2_BOSS_ARENA_BIRTH source_id=%u target=%u p1_boss=%d host=%d ok=0 reason=teki-pool-full\n",
                    source, uid, boss.mBossID, host);
        std::fflush(stdout);
        return nullptr;
    }
    // Same personality hand-off as GenObjectTeki::birth. The P1 boss's number
    // pellet reward carries over, and so does its held ship part (#901): the
    // part goes in the personality mID exactly like a P1 part-holder teki,
    // resolved from the generator's pellet config like BossMgr::setBossParam.
    // BTeki::startAI then registers it (or clears it when it already exists)
    // and the BTeki death funnels drop it once.
    static TekiPersonality* personality = nullptr;
    if (!personality) personality = new TekiPersonality();
    personality->reset();
    const unsigned heldPart = pc_held_part_for_pellet_config(boss.mPelletConfigIdx);
    if (heldPart) {
        personality->mID.setID(heldPart);
        pc_held_part_log_assign(heldPart, source, uid, boss.mBossID, "arena");
    }
    personality->mPosition.set(info.mPosition);
    personality->mNestPosition.set(info.mScale);
    personality->mFaceDirection = info.mRotation.y;
    if (boss.mItemCount > 0) {
        personality->mPelletKind  = boss.mItemIndex;
        personality->mPelletColor = (boss.mItemColour >= 0 && boss.mItemColour <= 2) ? boss.mItemColour : -1;
        personality->setI(TekiPersonality::INT_PelletMinCount, boss.mItemCount);
        personality->setI(TekiPersonality::INT_PelletMaxCount, boss.mItemCount);
        personality->setF(TekiPersonality::FLT_PelletAppearChance, 1.0f);
    }
    teki->mPersonality->input(*personality);
    pc_held_part_birth_uid(uid); // the newborn has no mGenerator yet
    teki->reset();
    teki->startAI(0);
    pc_held_part_birth_uid(0);
    teki->mSRT.r = info.mRotation;
    if (info.mGenerator->doAdjustFaceDir()) teki->setCreatureFlag(CF_AdjustFaceDirOnSpawn);
    teki->mRebirthDay = info.mGenerator->getRebirthDay();

    std::printf("P2_BOSS_ARENA_BIRTH source_id=%u target=%u p1_boss=%d host=%d ok=1 x=%.1f y=%.1f z=%.1f\n",
                source, uid, boss.mBossID, host, double(info.mPosition.x), double(info.mPosition.y),
                double(info.mPosition.z));
    std::printf("P2_SEED_RESOLVE source_id=%u target=%u original_type=-1 p1_boss=%d x=%.1f z=%.1f\n",
                source, uid, boss.mBossID, double(info.mPosition.x), double(info.mPosition.z));
    std::fflush(stdout);
    // Same claim path as a bound teki generator (genteki.cpp birth).
    pc_p2_generated_placement_bind(static_cast<BTeki*>(teki), source, uid, uid);
    pc_p2_kabuto_bind_dynamic(teki, uid, source);
    pc_p2_placement_probe_birth(info.mPosition.x, info.mPosition.y, info.mPosition.z,
                                info.mGenerator->_70, uid, host);
    pc_p2_boss_arena_probe(info.mPosition.x, info.mPosition.y, info.mPosition.z, uid, "p2boss", int(source));
    return teki;
}
