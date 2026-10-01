// Careening Dirigibug (BombSarai, source 58) OWN campaign port (#244).
//
// In a campaign (bridge) session every actor whose seed slot maps to source
// 58 rides a P1 TEKI_Napkid vehicle (pc_p2_campaign_policy.h hostType), with
// the Napkid strategy suppressed (BTeki::doAI -> pc_p2_bombsarai_teki_suppress_ai).
// The engine-free source machine (pc_p2_bombsarai_own.cpp) decides; this
// module feeds it live host facts and applies its outputs to the real P1
// receivers:
//
//  * hover: EB_Untargetable <-> CF_IsFlying. While hovering the carrier is a
//    P1 flyer, so free Pikmin do not target it (P2 Untargetable) and only
//    thrown Pikmin latch on; Fall/Damage/early TakeOff clear it so the ground
//    squad attacks the grounded carrier.
//  * stuck census: live Piki whose stick object is this actor feed
//    mStuckPikminCount (rise factor, getNextStateOnHeight, Damage exit).
//  * payload: Supply births a Bomb (EnemyID 36) from the shared engine-free
//    bomb policy (pc_p2_bombsarai_bomb), held at the staged kamu_jnt1 joint;
//    Release/Fall throw it with the source velocities; onKill drops it. A
//    landed bomb arms, burns and detonates on its own clock (bombs outlive the
//    carrier), and the blast routes InteractBomb to Navi/Pikmin/Teki, with the
//    carrier itself only damaged while on the floor (bombCallBack).
//  * death: Dead KEYEVENT_END -> kill(): the held bomb drops, then the host
//    death funnel (die + dieSoon) births the ordinary LeaveCorpse pellet with
//    the host's retail carcass config. The seed source is bound with
//    pc_randomizer_p2_bind_source, so the ordinary Onion/Pod suck grants
//    onion:p2:58 for this token. Nothing is teleported or re-configured.
#include "pc_p2_bombsarai_teki.h"
#include "pc_p2_sfx.h"
#include "pc_p2_bombsarai_own.h"
#include "pc_p2_bombsarai_bomb.h"
#include "pc_p2_bombsarai_clock.h"
#include "pc_p2_bombsarai_map_trace.h"
#include "pc_p2_bombsarai_terrain.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_p2_animation.h"
#include "pc_p2_navi_select.h"
#include "pc_randomizer.h"
#include "Generator.h"
#include "Graphics.h"
#include "Interactions.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Pellet.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Shape.h"
#include "pc_p2_fb_smooth.h"
#include "pc_p2_pose_family.h"
#include "pc_p2_billboard_groups.h"
#include "pc_p2_bomb_visual.h"
#include <algorithm>
#include "Texture.h"
#include "gameflow.h"
#include "gl/pc_gfx.h"
#include "system.h"
#include "teki.h"
#include "UtEffect.h"
#include "KEffect.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <string>
#include <vector>

namespace {
constexpr unsigned kSource = 58;
constexpr int kHostType = 11; // TEKI_Napkid

struct Own {
    unsigned token = 0;
    p2bsown::Fsm fsm;
    P2BombSaraiSourceClock clock;
    P2BombSaraiBomb* held = nullptr;
    bool escaped = false;       // kill() ran (pcEscapeNow); corpse phase
    bool deadLogged = false;
    float lastHealth = 0.0f;
    float lastDamageCount = 0.0f;
    int pendingHits = 0;
    int totalHits = 0;
    int lastStuck = 0;
    int maxStuck = 0;
    float logTimer = 0.0f;
    float carcassTime = 0.0f;
    bool wasFlying = false;
    int supplies = 0, throws = 0, flicks = 0, falls = 0, takeoffs = 0;
    Pellet* corpse = nullptr;
    float corpseX = 0.0f, corpseZ = 0.0f;
    int corpseProbe = 0;
};
std::map<BTeki*, Own> sOwn;
std::map<BTeki*, int> sDrawLogged;

p2bsown::Params sParams;
p2bsown::BombParams sBombParams;
p2bsown::Bank sBank = p2bsown::defaultBank();
std::vector<Shape*> sPoses[p2bsown::AnimCount];   // parallel to sBank.clip[a].poses
std::vector<Shape*> sBombPoses[2];
bool sPosesLoaded = false;
// #972: lerp + 150 ms crossfade over the shared pose bank for the Dirigibug and
// its bomb (the nearest Shapes above stay the fallback; PIKMIN_P2_INTERPOLATION=0
// keeps them). Presentation only.
p2posefamily::Bank sPoseBank("BOMBSARAI"), sBombPoseBank("BOMBSARAI_BOMB");
p2posefamily::Actors sPoseVis, sBombVis;
std::size_t sDiskBytes = 0;
// #1027: balloon billboard vertex groups (p2-bombsarai-billboard.txt, staged
// from the extraction); empty = balloons keep their baked orientation.
std::vector<p2billboardgroups::Range> sBillboards;
bool sBillboardLogged = false;
// #1027: one shared Bomb countdown gauge (pc_p2_bomb_visual.h, the Volatile
// Dweevil's P2BombGauge) per bomb slot. P2 shows the Bomb enemy's ordinary life
// gauge, mHealth / mMaxHealth at fp27 above it, hidden while full.
constexpr int kBombGaugeSlots = 16;
P2BombGauge sBombGauge[kBombGaugeSlots];
bool sBombGaugeLogged = false;
// #1066: a burning bomb looks lit, with the same cues as the Volatile Dweevil's
// bomb (pc_p2_bomb_telegraph.h / pc_p2_bomb_visual.h): the flash/tick ramp
// (faster as the fuse empties), a red-hot tint and swell on each flash, a fuse
// spark and tick per flash, and below 4.0 fuse life P2's TBombrockLight
// (bomb.cpp:203-207) as a core glow on every flash. Every generator is
// tracked and force-killed at the blast (bombState.cpp:130 forceKill).
constexpr int kBombSparkEffect = 44;  // EFF_Piki_FireSparkles (pkf2.pcr), as the Volatile bomb
constexpr int kBombGlowEffect = 32;   // EFF_Bomb_Glow (bi_gro1.pcr), the P1 bomb-rock glow
struct BombFx {
    p2bombtelegraph::Pulse pulse;
    P2BombSparks sparks, glow;
    bool lit = false, light = false;
    std::uint64_t token = 0;
    unsigned baseline = 0;     // engine live generators when the fuse lit
    float sinceBlast = -1.0f;  // >= 0: seconds since this slot's blast (one late check)
};
BombFx sBombFx[kBombGaugeSlots];
bool bombBurning(const P2BombSaraiBomb* b) {
    return b && (b->phase() == P2BombSaraiBombPhase::ArmedLoop || b->phase() == P2BombSaraiBombPhase::Burning)
        && b->fuseMax() > 0.0f;
}
float bombRatio(const P2BombSaraiBomb* b) {
    const float r = b->fuseRemaining() / b->fuseMax();
    return r < 0.0f ? 0.0f : (r > 1.0f ? 1.0f : r);
}
void endBombFx(int s, const char* why) {
    BombFx& fx = sBombFx[s];
    if (!fx.lit) return;
    const int tracked = fx.sparks.count + fx.glow.count;
    fx.sparks.killAll();
    fx.glow.killAll();
    if (std::strcmp(why, "blast") == 0) fx.sinceBlast = 0.0f;
    std::printf("P2_BOMBSARAI_BOMB_FX_KILLED token=%llu slot=%d reason=%s pulses=%d light=%d killed=%d live_generators=%u baseline=%u\n",
                (unsigned long long)fx.token, s, why, fx.pulse.pulses, fx.light ? 1 : 0,
                tracked, pc_p2_bomb_live_generators(), fx.baseline);
    fx.pulse.reset();
    fx.lit = fx.light = false;
}
// A clip is bank-loadable when its staged files are numbered 0..N-1 (the
// extractor names poses by sample index; an old dead1 tree skipped some).
bool contiguousFiles(const std::vector<int>& files) {
    for (std::size_t k = 0; k < files.size(); ++k)
        if (files[k] != int(k)) return false;
    return true;
}

P2BombSaraiBombPool sPool(16);
P2BombSaraiBombConfig sBombConfig;
P2BombSaraiSourceClock sBombClock;
P2BombSaraiMapBinding* sMap = nullptr;
P2BombSaraiTerrainAdapter* sAdapter = nullptr;
int sBlastCount = 0;

// Blast owner when the carrier is gone (source mCarrier == nullptr branch).
class OwnBombOwner : public Creature {
public:
    OwnBombOwner() : Creature(nullptr) { mHealth = 1.0f; }
    void refresh(Graphics&) override {}
    void doKill() override {}
};
OwnBombOwner* sBombOwner = nullptr;

Own* find(const BTeki* t) {
    auto i = sOwn.find(const_cast<BTeki*>(t));
    return i == sOwn.end() ? nullptr : &i->second;
}

BTeki* carrierFor(std::uint64_t token) {
    for (auto& e : sOwn)
        if (e.second.token == token && !e.second.escaped && e.first->isAlive()) return e.first;
    return nullptr;
}
bool carrierAlive(void*, std::uint64_t token) { return carrierFor(token) != nullptr; }

// ------------------------------------------------------------------ assets
Shape* loadShape(const std::string& rel, Shape*& shared, std::size_t& total) {
    const std::string path = "assets/dataDir/courses/pikmin2room/" + rel;
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) return nullptr;
    const auto size = file.tellg();
    if (size <= 0 || size > 1024 * 1024 || total + std::size_t(size) > 24u * 1024 * 1024) return nullptr;
    total += std::size_t(size);
    file.seekg(0);
    std::vector<unsigned char> bytes(std::size_t(size), 0), resources;
    if (!file.read(reinterpret_cast<char*>(bytes.data()), size) || !p2animation::resources(bytes, resources)) return nullptr;
    Shape* shape = gameflow.loadShape(("courses/pikmin2room/" + rel).c_str(), true);
    if (!shape) return nullptr;
    if (!shared) {
        shared = shape;
        for (int t = 0; t < shape->mTexAttrCount; ++t)
            if (shape->mTexAttrList[t].mTexture) shape->mTexAttrList[t].mTexture->attach();
    } else {
        if (shape->mMaterialCount != shared->mMaterialCount || shape->mTexAttrCount != shared->mTexAttrCount
            || shape->mTevInfoCount != shared->mTevInfoCount) return nullptr;
        for (int j = 0; j < shape->mTotalMatpolyCount; ++j) {
            auto* poly = shape->mMatpolyList[j];
            if (!poly || !poly->mMaterial) continue;
            int material = -1;
            for (int m = 0; m < shape->mMaterialCount; ++m)
                if (poly->mMaterial == &shape->mMaterialList[m]) material = m;
            if (material < 0) return nullptr;
            poly->mMaterial = &shared->mMaterialList[material];
        }
        shape->mMaterialList = shared->mMaterialList;
        shape->mTexAttrList = shared->mTexAttrList;
        shape->mTevInfoList = shared->mTevInfoList;
    }
    return shape;
}

void loadAssets() {
    sParams = p2bsown::Params{};
    {
        std::ifstream in("p2-bombsarai-parms.txt");
        std::string error;
        if (in && !p2bsown::parseEnemyParm(in, sParams, error)) {
            std::printf("P2_BOMBSARAI_OWN_PARMS_INVALID reason=%s fallback=retail_defaults\n", error.c_str());
            sParams = p2bsown::Params{};
        }
    }
    sBombParams = p2bsown::BombParams{};
    {
        std::ifstream in("p2-bombsarai-bomb-parms.txt");
        std::string error;
        if (in && !p2bsown::parseBombParm(in, sBombParams, error)) {
            std::printf("P2_BOMBSARAI_OWN_BOMB_PARMS_INVALID reason=%s fallback=retail_defaults\n", error.c_str());
            sBombParams = p2bsown::BombParams{};
        }
    }
    std::printf("P2_BOMBSARAI_OWN_PARMS source_id=58 retail=%d health=%.1f flight=%.1f transit=%.1f move=%.1f "
                "sight=%.1f territory=%.1f home=%.1f attack_range=%.1f attack_angle=%.1f attack_radius=%.1f "
                "flick=%.2f/%.2f struggle=%.2f bomb_retail=%d fuse=%.2f blast=%.1f navi_piki=%.1f teki=%.1f\n",
                sParams.retail ? 1 : 0, sParams.health, sParams.flightHeight, sParams.transitHeight,
                sParams.moveSpeed, sParams.sightRadius, sParams.territoryRadius, sParams.homeRadius,
                sParams.maxAttackRange, sParams.maxAttackAngle, sParams.attackRadius, sParams.freeFlick,
                sParams.ladenFlick, sParams.struggleTime, sBombParams.retail ? 1 : 0, sBombParams.fuseHealth,
                sBombParams.blastRadius, sBombParams.naviPikiDamage, sBombParams.tekiDamage);
    // Engine-free bomb policy config from the retail Bomb parms; gravity is
    // the shared aiConstants 560 u/s^2 at the 30 Hz source tick.
    sBombConfig = P2BombSaraiBombConfig{};
    sBombConfig.gravityPerTick = 560.0f / 30.0f;
    sBombConfig.fuseHealth = sBombParams.fuseHealth;
    sBombConfig.bombRadius = 15.0f;
    sBombConfig.blastRadius = sBombParams.blastRadius;
    sBombConfig.blastHalfHeight = sBombParams.blastHalfHeight;
    sBombConfig.tekiDamage = sBombParams.tekiDamage;
    sBombConfig.naviPikiDamage = sBombParams.naviPikiDamage;
    sBombConfig.ip02TriggerLimit = sBombParams.inductionLimit;
    sBombConfig.armLoopTicks = 8; // hit_loop.bca LOOP 0..7

    sBank = p2bsown::defaultBank();
    for (auto& v : sPoses) v.clear();
    for (auto& v : sBombPoses) v.clear();
    sPosesLoaded = false;
    {
        std::ifstream in("p2-bombsarai-own-bank.txt");
        std::string error;
        if (in && !p2bsown::parseBank(in, sBank, error)) {
            std::printf("P2_BOMBSARAI_OWN_BANK_INVALID reason=%s fallback=builtin_timing draw=host\n", error.c_str());
            sBank = p2bsown::defaultBank();
        }
    }
    int staged = 0;
    for (const auto& c : sBank.clip) staged += c.staged ? 1 : 0;
    for (int b = 0; b < sBank.bombClipCount; ++b)
        if (sBank.bombClip[b].name == "hit_loop") sBombConfig.armLoopTicks = sBank.bombClip[b].frames;
    Shape* shared = nullptr;
    std::size_t total = 0, poses = 0, bombPoses = 0;
    sPoseBank.reset();
    sBombPoseBank.reset();
    sPoseVis.clear();
    sBombVis.clear();
    sDiskBytes = 0;
    bool ok = staged > 0;
    // Preferred: compact pose-bank loader (every pose decoded, a few nearest
    // Shapes). A bank whose files are not numbered 0..N-1 keeps the legacy
    // one-Shape-per-pose load, without interpolation (reported).
    bool dense = ok;
    for (int a = 0; a < p2bsown::AnimCount; ++a) {
        std::vector<int> files;
        for (const auto& pose : sBank.clip[a].poses) files.push_back(pose.file);
        if (!contiguousFiles(files)) dense = false;
    }
    for (int b = 0; b < sBank.bombClipCount && b < 2; ++b)
        if (!contiguousFiles(sBank.bombClip[b].poseFiles)) dense = false;
    if (ok && !dense)
        std::printf("P2_BOMBSARAI_INTERPOLATION_DISABLED reason=noncontiguous_pose_files fallback=nearest\n");
    auto diskBytes = [](const std::string& stem, int count) {
        std::size_t bytes = 0;
        for (int k = 0; k < count; ++k) {
            std::ifstream f(p2poseload::stemPath(true, stem, k), std::ios::binary | std::ios::ate);
            if (f) bytes += std::size_t(f.tellg());
        }
        return bytes;
    };
    if (dense) {
        p2poseload::Shared famShared, bombShared;
        for (int a = 0; ok && a < p2bsown::AnimCount; ++a) {
            const auto& clip = sBank.clip[a];
            if (clip.poses.empty()) continue;
            std::vector<int> frames;
            for (const auto& pose : clip.poses) frames.push_back(pose.frame);
            const std::string stem = "bombsarai_BombSarai_" + clip.name;
            std::string error;
            if (!p2posefamily::loadFamilyClip(sPoseBank, clip.name, stem, int(frames.size()),
                                              p2fbsmooth::bankDuration(frames, clip.frames), frames, famShared, total,
                                              sPoses[a], error)) {
                std::printf("P2_BOMBSARAI_OWN_BANK_INVALID reason=%s clip=%s fallback=builtin_timing draw=host\n",
                            error.c_str(), clip.name.c_str());
                ok = false;
                break;
            }
            sDiskBytes += diskBytes(stem, int(frames.size()));
            poses += frames.size();
        }
        if (!ok) {
            for (auto& v : sPoses) v.clear();
            sPoseBank.reset();
        }
        sPosesLoaded = ok && poses > 0;
        if (sPosesLoaded) {
            for (int b = 0; b < sBank.bombClipCount && b < 2; ++b) {
                const auto& clip = sBank.bombClip[b];
                if (clip.poseFiles.empty()) continue;
                const std::string stem = "bombsarai_Bomb_" + clip.name;
                std::string error;
                if (!p2posefamily::loadFamilyClip(sBombPoseBank, clip.name, stem, int(clip.poseFrames.size()),
                                                  p2fbsmooth::bankDuration(clip.poseFrames, clip.frames),
                                                  clip.poseFrames, bombShared, total, sBombPoses[b], error)) {
                    sBombPoses[b].clear();
                    break;
                }
                sDiskBytes += diskBytes(stem, int(clip.poseFrames.size()));
                bombPoses += clip.poseFiles.size();
            }
        }
    }
    for (int a = 0; !dense && ok && a < p2bsown::AnimCount; ++a) {
        const auto& clip = sBank.clip[a];
        for (const auto& pose : clip.poses) {
            char rel[160];
            std::snprintf(rel, sizeof(rel), "bombsarai_BombSarai_%s_%02d.mod", clip.name.c_str(), pose.file);
            Shape* shape = loadShape(rel, shared, total);
            if (!shape) { ok = false; break; }
            sPoses[a].push_back(shape);
            ++poses;
        }
    }
    if (!dense && !ok) for (auto& v : sPoses) v.clear();
    if (!dense) sPosesLoaded = ok && poses > 0;
    if (!dense && sPosesLoaded) {
        Shape* bombShared = nullptr;
        for (int b = 0; b < sBank.bombClipCount && b < 2; ++b) {
            for (int file : sBank.bombClip[b].poseFiles) {
                char rel[160];
                std::snprintf(rel, sizeof(rel), "bombsarai_Bomb_%s_%02d.mod", sBank.bombClip[b].name.c_str(), file);
                Shape* shape = loadShape(rel, bombShared, total);
                if (!shape) { sBombPoses[b].clear(); break; }
                sBombPoses[b].push_back(shape);
                ++bombPoses;
            }
        }
    }
    sBillboards.clear();
    sBillboardLogged = false;
    {
        std::ifstream in("p2-bombsarai-billboard.txt");
        std::string error;
        if (in && !p2billboardgroups::parse(in, "P2_BOMBSARAI_BILLBOARD_1", sBillboards, error))
            std::printf("P2_BOMBSARAI_BILLBOARD_INVALID reason=%s fallback=baked_orientation\n", error.c_str());
    }
    std::printf("P2_BOMBSARAI_OWN_BANK staged_clips=%d poses=%zu bomb_poses=%zu bytes=%zu disk_bytes=%zu "
                "interpolation=%d bomb_interpolation=%d draw=%s arm_loop=%d\n",
                staged, sPosesLoaded ? poses : std::size_t(0), bombPoses, total, sDiskBytes,
                sPoseBank.ready() ? 1 : 0, sBombPoseBank.ready() ? 1 : 0,
                sPosesLoaded ? "p2_model" : "host", sBombConfig.armLoopTicks);
}

// ------------------------------------------------------------------ helpers
p2bsown::Vec3 kamuLocal(const Own& o) {
    // Staged kamu_jnt1 model-space translation at the nearest sampled pose of
    // the playing clip; clips without poses (supli1) use wait2's first pose.
    const int anim = o.fsm.animator().anim();
    if (anim >= 0 && anim < p2bsown::AnimCount) {
        if (const p2bsown::Pose* p = p2bsown::nearestPose(sBank.clip[anim], o.fsm.animator().frame())) return p->kamu;
    }
    if (const p2bsown::Pose* p = p2bsown::nearestPose(sBank.clip[p2bsown::AnimBombWait], 0.0f)) return p->kamu;
    return {0.0f, -20.0f, 10.0f};
}

P2BombSaraiVec3 jointWorld(BTeki* t, const Own& o) {
    const p2bsown::Vec3 k = kamuLocal(o);
    const float face = t->getDirection();
    const float s = std::sin(face), c = std::cos(face);
    const Vector3f p = t->getPosition();
    return {p.x + k.x * c + k.z * s, p.y + k.y, p.z - k.x * s + k.z * c};
}

int countStuck(BTeki* t, int& purple) {
    int stuck = 0;
    purple = 0;
    if (!pikiMgr) return 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive() || p->getStickObject() != t) continue;
        ++stuck;
        if (p->mP2Purple) ++purple;
    }
    return stuck;
}

int nearbyPikmin(BTeki* t) {
    // Live Piki within 60u of the grounded carrier that are not stuck to it.
    // Proximity only, not an attack-state count: the hits that actually move
    // health are the separate TEKIOPT_DamageCountable hits= field.
    if (!pikiMgr) return 0;
    const Vector3f me = t->getPosition();
    int n = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive() || p->getStickObject() == t) continue;
        const Vector3f q = p->getPosition();
        const float dx = q.x - me.x, dz = q.z - me.z;
        if (dx * dx + dz * dz < 60.0f * 60.0f && std::fabs(q.y - me.y) < 60.0f) ++n;
    }
    return n;
}

struct Snapshot {
    std::vector<p2bsown::Candidate> c;
    std::vector<Creature*> who;
};
void buildSnapshot(BTeki* self, Snapshot& snap) {
    snap.c.clear();
    snap.who.clear();
    auto add = [&](Creature* cr, p2bsown::Candidate cand) {
        const Vector3f p = cr->getPosition();
        cand.id = static_cast<std::uint64_t>(snap.who.size() + 1);
        cand.pos = {p.x, p.y, p.z};
        cand.alive = cr->isAlive();
        snap.c.push_back(cand);
        snap.who.push_back(cr);
    };
    for (Navi* n : pc_p2_navis()) {
        if (!n) continue;
        p2bsown::Candidate cand;
        cand.navi = true;
        add(n, cand);
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p) continue;
            p2bsown::Candidate cand;
            cand.pikmin = true;
            cand.stuckToSelf = p->getStickObject() == self;
            cand.stuckToMouth = p->isStickToMouth() != 0;
            cand.searchable = p->isAlive() && !p->isBuried() && !cand.stuckToMouth;
            add(p, cand);
        }
    }
}

// ------------------------------------------------------------------ blasts
void applyBlast(const P2BombSaraiBlastEvent& e) {
    BTeki* carrier = e.carrierValid ? carrierFor(e.carrierToken) : nullptr;
    if (!sBombOwner) sBombOwner = new OwnBombOwner;
    Creature* owner = carrier ? static_cast<Creature*>(carrier) : static_cast<Creature*>(sBombOwner);
    auto inside = [&](const Vector3f& p) {
        const float dx = p.x - e.center.x, dy = p.y - e.center.y, dz = p.z - e.center.z;
        return dy >= -e.halfHeight && dy <= e.halfHeight && dx * dx + dz * dz <= e.radius * e.radius;
    };
    // Snapshot receivers first: a lethal InteractBomb removes Pikmin from pikiMgr.
    std::vector<Creature*> navis, pikis, tekis;
    for (Navi* n : pc_p2_navis()) if (n && n->isAlive() && inside(n->getPosition())) navis.push_back(n);
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (p && p->isAlive() && inside(p->getPosition())) pikis.push_back(p);
        }
    }
    int self = 0;
    if (tekiMgr) {
        Iterator it(tekiMgr);
        CI_LOOP(it) {
            BTeki* t = static_cast<BTeki*>(*it);
            if (!t || !t->isAlive() || !inside(t->getPosition())) continue;
            if (Own* o = find(t)) {
                // BombSarai::bombCallBack: only a carrier on the floor takes
                // the blast (addDamage), an airborne one is immune.
                if (!o->escaped && !t->isFlying() && t->mHealth > 0.0f) {
                    t->mStoredDamage += e.tekiDamage;
                    ++self;
                }
                continue;
            }
            tekis.push_back(t);
        }
    }
    // Detonation visual: the P1 bomb-rock explosion effect at the blast centre
    // (the source Bomb plays its own efx; this is the host equivalent).
    if (utEffectMgr) {
        Vector3f centre(e.center.x, e.center.y, e.center.z);
        EffectParm parm(centre);
        utEffectMgr->cast(KandoEffect::Bomb, parm);
    }
    // Receiver damage. P2 InteractBomb::actPiki (interactPiki.cpp:304-327)
    // sends every Pikmin in the blast into PIKISTATE_Blow with mIsLethal=true:
    // the Pikmin is blown back and dies. fp24 (naviPikiDamage, 10) is the
    // captain damage (InteractBomb::actNavi). The P1 host equivalent of a
    // lethal blow is its own bomb-rock Pikmin damage (PikiMgr p77
    // mBombDamagePiki, retail 765 > Pikmin health 100): InteractBomb::actPiki
    // subtracts it and flicks, and PikiFlickState kills the Pikmin on landing
    // (pikiState.cpp FLS_Landing, mHealth <= 0 -> PIKISTATE_Dead). Captains
    // keep fp24.
    const float pikiDamage = (pikiMgr && pikiMgr->mPikiParms)
                                 ? pikiMgr->mPikiParms->mPikiParms.mBombDamagePiki()
                                 : 765.0f;
    int naviHits = 0, pikiHits = 0, tekiHits = 0, pikiLethal = 0;
    // Per-hit evidence (#1027, same fields as P2_BOMBOTAKARA_BLAST_HIT): a lethal
    // Pikmin hit reads health <= 0 here and dies when its flick lands.
    auto logHit = [&](const char* kind, float damage, float before, float after, bool alive, bool accepted) {
        std::printf("P2_BOMBSARAI_BLAST_HIT token=%llu kind=%s damage=%.1f health=%.1f->%.1f alive=%d accepted=%d\n",
                    (unsigned long long)e.carrierToken, kind, damage, before, after, alive ? 1 : 0, accepted ? 1 : 0);
    };
    for (Creature* c : navis) {
        if (!c->isAlive()) continue;
        const float before = c->mHealth;
        const bool accepted = c->stimulate(InteractBomb(owner, e.naviPikiDamage, nullptr));
        naviHits += accepted ? 1 : 0;
        logHit("navi", e.naviPikiDamage, before, c->mHealth, c->isAlive(), accepted);
    }
    for (Creature* c : pikis) {
        if (!c->isAlive()) continue;
        const float before = c->mHealth;
        const bool accepted = c->stimulate(InteractBomb(owner, pikiDamage, nullptr));
        logHit("piki", pikiDamage, before, c->mHealth, c->isAlive(), accepted);
        if (!accepted) continue;
        ++pikiHits;
        if (static_cast<Piki*>(c)->mHealth <= 0.0f) ++pikiLethal;
    }
    for (Creature* c : tekis) if (c->isAlive() && c->stimulate(InteractBomb(owner, e.tekiDamage, nullptr))) ++tekiHits;
    ++sBlastCount;
    // P1 bomb-rock burst approximation (output-only, #946).
    pc_p2_sfx(58, unsigned(e.carrierToken), p2sfx::Event::Burst, Vector3f(e.center.x, e.center.y, e.center.z));
    std::printf("P2_BOMBSARAI_OWN_BLAST source_id=58 token=%llu carrier_valid=%d x=%.1f y=%.1f z=%.1f "
                "navi_hits=%d pikmin_hits=%d pikmin_lethal=%d piki_damage=%.1f navi_damage=%.1f teki_hits=%d "
                "self_hits=%d n=%d\n",
                (unsigned long long)e.carrierToken, carrier ? 1 : 0, e.center.x, e.center.y, e.center.z,
                naviHits, pikiHits, pikiLethal, pikiDamage, e.naviPikiDamage, tekiHits, self, sBlastCount);
    // Bomb-on-bomb induction (bomb.cpp:348-368, 426-440).
    for (int s = 0; s < sPool.slotCount(); ++s) {
        if (!sPool.slotLive(s)) continue;
        P2BombSaraiBomb* b = sPool.bombAt(s);
        const P2BombSaraiVec3& q = b->position();
        if (!inside(Vector3f(q.x, q.y, q.z))) continue;
        b->induce(carrierAlive, nullptr);
    }
}

void dropHeld(BTeki* t, Own& o, P2BombSaraiThrowKind kind, const char* why) {
    if (!o.held) return;
    if (o.held->phase() == P2BombSaraiBombPhase::Captured) {
        o.held->followJoint(jointWorld(t, o));
        o.held->throwBomb(kind, t->getDirection());
        ++o.throws;
        std::printf("P2_BOMBSARAI_OWN_THROW source_id=58 token=%u kind=%s reason=%s x=%.1f y=%.1f z=%.1f n=%d\n",
                    o.token, kind == P2BombSaraiThrowKind::Release ? "release" : kind == P2BombSaraiThrowKind::Fall ? "fall" : "death",
                    why, o.held->position().x, o.held->position().y, o.held->position().z, o.throws);
    }
    o.held = nullptr;
}

void logState(BTeki* t, const Own& o, p2bsown::State from, p2bsown::State to, int stuck) {
    const Vector3f p = t->getPosition();
    const float ground = mapMgr ? mapMgr->getMinY(p.x, p.z, true) : p.y;
    std::printf("P2_BOMBSARAI_OWN_STATE source_id=58 token=%u from=%s state=%s x=%.1f y=%.1f z=%.1f height=%.1f "
                "health=%.1f stuck=%d held=%d\n",
                o.token, p2bsown::stateName(from), p2bsown::stateName(to), p.x, p.y, p.z, p.y - ground, t->mHealth,
                stuck, o.held ? 1 : 0);
}

// Live tick for an OWN-bound carrier. Returns true once the host teardown ran.
bool ownTick(BTeki* t, Own& o, float dt) {
    // The suppressed Napkid strategy normally applies stored damage; drain it
    // here so Pikmin hits reach mHealth (TEKIOPT_DamageCountable counts hits).
    const float before = t->mHealth;
    if (t->mStoredDamage > 0.0f) t->makeDamaged();
    if (t->mDamageCount < o.lastDamageCount) o.lastDamageCount = t->mDamageCount;
    const int hits = int(t->mDamageCount - o.lastDamageCount);
    o.lastDamageCount = t->mDamageCount;
    o.pendingHits += hits;
    o.totalHits += hits;
    int purple = 0;
    const int stuck = countStuck(t, purple);
    if (stuck != o.lastStuck) {
        std::printf("P2_BOMBSARAI_OWN_LATCH source_id=58 token=%u stuck=%d prior=%d flying=%d state=%s health=%.1f\n",
                    o.token, stuck, o.lastStuck, t->isFlying() ? 1 : 0, p2bsown::stateName(o.fsm.state()), t->mHealth);
        o.lastStuck = stuck;
        if (stuck > o.maxStuck) o.maxStuck = stuck;
    }
    if (t->mHealth < before || (t->mHealth < o.lastHealth && t->mHealth >= 0.0f)) {
        if (t->mHealth > 0.0f) pc_p2_sfx(58, o.token, p2sfx::Event::Damage, t);
        std::printf("P2_BOMBSARAI_OWN_DAMAGE source_id=58 token=%u health=%.1f prior=%.1f hits=%d stuck=%d "
                    "nearby_pikmin=%d flying=%d state=%s\n",
                    o.token, t->mHealth, o.lastHealth, o.pendingHits, stuck, t->isFlying() ? 0 : nearbyPikmin(t),
                    t->isFlying() ? 1 : 0, p2bsown::stateName(o.fsm.state()));
        o.pendingHits = 0;
    }
    o.lastHealth = t->mHealth;

    const int ticks = o.clock.step(double(dt), true);
    if (ticks <= 0) return false;
    Snapshot snap;
    buildSnapshot(t, snap);
    p2bsown::TickOutput last;
    bool kill = false;
    for (int k = 0; k < ticks && !kill; ++k) {
        p2bsown::TickInput in;
        const Vector3f pos = t->getPosition();
        in.position = {pos.x, pos.y, pos.z};
        in.groundY = mapMgr ? mapMgr->getMinY(pos.x, pos.z, true) : pos.y;
        in.health = t->mHealth;
        in.stuckPikmin = stuck;
        in.stuckPurple = purple;
        in.carrying = o.held && o.held->phase() == P2BombSaraiBombPhase::Captured;
        in.inCave = false; // P1 campaign areas are overworld courses
        in.candidates = snap.c.data();
        in.count = snap.c.size();
        const p2bsown::State shown = o.fsm.state();
        last = o.fsm.tick(in);
        if (!last.valid) break;
        p2bsown::State from = shown;
        for (p2bsown::State e : last.entered) {
            logState(t, o, from, e, stuck);
            // P1 Sarai/bomb bank approximation (output-only, #946).
            switch (e) {
            case p2bsown::State::Release: pc_p2_sfx(58, o.token, p2sfx::Event::Attack, t); break;
            case p2bsown::State::Flick:
            case p2bsown::State::BombFlick: pc_p2_sfx(58, o.token, p2sfx::Event::Flick, t); break;
            case p2bsown::State::Damage: pc_p2_sfx(58, o.token, p2sfx::Event::Damage, t); break;
            case p2bsown::State::Dead:
                pc_p2_sfx_stop(58, p2sfx::Event::Hover, t);
                pc_p2_sfx(58, o.token, p2sfx::Event::Dead, t);
                break;
            case p2bsown::State::Fall: pc_p2_sfx(58, o.token, p2sfx::Event::Land, t); break;
            default: break;
            }
            if (e == p2bsown::State::Fall) ++o.falls;
            if (e == p2bsown::State::TakeOff1 || e == p2bsown::State::TakeOff2) ++o.takeoffs;
            if (e == p2bsown::State::Dead && !o.deadLogged) {
                o.deadLogged = true;
                std::printf("P2_BOMBSARAI_OWN_DEAD source_id=58 token=%u health=%.1f hits=%d max_stuck=%d\n",
                            o.token, t->mHealth, o.totalHits, o.maxStuck);
            }
            from = e;
        }
        if (last.flickRolled) {
            std::printf("P2_BOMBSARAI_OWN_GATE source_id=58 token=%u stuck=%d chance=%.3f roll=%.3f result=%s\n",
                        o.token, stuck, last.flickChance, last.flickRoll,
                        last.entered.empty() ? "none" : p2bsown::stateName(last.entered.back()));
        }
        if (last.supply) {
            if (!o.held) {
                o.held = sPool.supply(o.token, jointWorld(t, o), sBombConfig);
                if (o.held) ++o.supplies;
            }
            std::printf("P2_BOMBSARAI_OWN_SUPPLY source_id=58 token=%u bomb=%d n=%d\n", o.token, o.held ? 1 : 0,
                        o.supplies);
        }
        if (last.throwBomb && o.held) {
            dropHeld(t, o, last.throwKind == 1 ? P2BombSaraiThrowKind::Fall : P2BombSaraiThrowKind::Release,
                     last.throwKind == 1 ? "fall_key2" : "release_key2");
        }
        if (last.flick) {
            int flicked = 0;
            for (auto id : last.flickStick) {
                Creature* c = id >= 1 && id <= snap.who.size() ? snap.who[std::size_t(id - 1)] : nullptr;
                if (c && c->isAlive() && c->getStickObject() == t && !c->isStickToMouth()
                    && c->stimulate(InteractFlick(t, last.flickKnockback, last.flickDamage, last.flickAngle))) ++flicked;
            }
            ++o.flicks;
            std::printf("P2_BOMBSARAI_OWN_FLICK source_id=58 token=%u stick=%d/%zu stuck=%d n=%d\n", o.token,
                        flicked, last.flickStick.size(), stuck, o.flicks);
        }
        kill = last.killRequest;
    }
    if (last.valid) {
        // Facing and horizontal motion are the machine's (walkToTarget +
        // doSimulation*); vertical motion is setHeightVelocity while
        // Untargetable (a P1 flyer: no gravity in moveNew), else host gravity.
        t->setDirection(last.faceDir);
        if (last.flying) {
            if (!t->isFlying()) t->startFlying();
            if (o.fsm.state() != p2bsown::State::Dead) pc_p2_sfx(58, o.token, p2sfx::Event::Hover, t);
        } else if (t->isFlying()) {
            t->finishFlying();
            pc_p2_sfx_stop(58, p2sfx::Event::Hover, t);
        }
        const Vector3f drive(last.velocity.x, last.flying ? last.velocity.y : 0.0f, last.velocity.z);
        t->inputDrive(drive);
        t->mVelocity.x = drive.x;
        t->mVelocity.z = drive.z;
        if (last.flying) t->mVelocity.y = drive.y;
        if (last.flying != o.wasFlying) {
            std::printf("P2_BOMBSARAI_OWN_FLYING source_id=58 token=%u flying=%d state=%s\n", o.token,
                        last.flying ? 1 : 0, p2bsown::stateName(o.fsm.state()));
            o.wasFlying = last.flying;
        }
    }
    // Carried bomb rides the animated kamu_jnt1.
    if (o.held && o.held->phase() == P2BombSaraiBombPhase::Captured) o.held->followJoint(jointWorld(t, o));
    if (t->mHealth > 0.0f) t->updateLifeGauge();
    o.logTimer += dt;
    if (o.logTimer >= 1.0f) {
        o.logTimer = 0.0f;
        const Vector3f p = t->getPosition();
        const float ground = mapMgr ? mapMgr->getMinY(p.x, p.z, true) : p.y;
        std::printf("P2_BOMBSARAI_OWN_POS source_id=58 token=%u state=%s anim=%s frame=%.0f x=%.1f y=%.1f z=%.1f "
                    "height=%.1f flying=%d health=%.1f stuck=%d held=%d carry_timer=%.2f target=%.1f,%.1f "
                    "home=%.1f,%.1f hits=%d\n",
                    o.token, p2bsown::stateName(o.fsm.state()),
                    p2bsown::animDefaultName(o.fsm.animator().anim()), o.fsm.animator().frame(), p.x, p.y, p.z,
                    p.y - ground, t->isFlying() ? 1 : 0, t->mHealth, stuck, o.held ? 1 : 0, o.fsm.carryTimer(),
                    o.fsm.target().x, o.fsm.target().z, o.fsm.home().x, o.fsm.home().z, o.totalHits);
    }
    std::fflush(stdout);
    if (kill && !o.escaped) {
        // Dead KEYEVENT_END -> kill(): onKill drops the held bomb with zero
        // velocity, then the host death funnel (die + dieSoon) births the
        // ordinary LeaveCorpse pellet. dieSoon only runs inside the suppressed
        // doAI, hence pcEscapeNow (groink/long-legs pattern).
        dropHeld(t, o, P2BombSaraiThrowKind::Death, "on_kill");
        o.escaped = true;
        if (t->isFlying()) t->finishFlying();
        t->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        t->mVelocity.x = t->mVelocity.z = 0.0f;
        o.corpseX = t->getPosition().x;
        o.corpseZ = t->getPosition().z;
        std::printf("P2_BOMBSARAI_OWN_KILL source_id=58 token=%u health=%.1f corpse_type=%d native=host_escape_now\n",
                    o.token, t->mHealth, t->getParameterI(TPI_CorpseType));
        std::fflush(stdout);
        t->pcEscapeNow();
        return true;
    }
    return false;
}

void corpseProbe(BTeki* t, Own& o) {
    // Read-only carcass evidence: the host pellet's own retail carry config
    // and the natural carriers. Nothing here moves, mutates or recruits.
    if (!o.corpse) {
        o.corpse = t->mPellet;
        if (o.corpse && o.corpse->mConfig) {
            // P2 retail carcass entry for BombSarai (disc user/Abe/Pellet/us/
            // carcass_config.txt, sha256 a76c4763...de9de0): min 3, max 6,
            // money 4. The host pellet is only read and compared, never mutated.
            constexpr int kP2CarcassMin = 3, kP2CarcassMax = 6;
            const int mn = o.corpse->mConfig->mCarryMinPikis.mValue;
            const int mx = o.corpse->mConfig->mCarryMaxPikis.mValue;
            std::printf("P2_BOMBSARAI_OWN_CORPSE_CONFIG source_id=58 token=%u carry_min=%d carry_max=%d "
                        "config=retail_host mutated=0 p2_carcass_min=%d p2_carcass_max=%d p2_match=%d\n",
                        o.token, mn, mx, kP2CarcassMin, kP2CarcassMax,
                        (mn == kP2CarcassMin && mx == kP2CarcassMax) ? 1 : 0);
        }
    }
    if (!o.corpse || !o.corpse->isAlive()) return;
    if (++o.corpseProbe % 60 == 0) {
        const Vector3f& cp = o.corpse->mSRT.t;
        const float dx = cp.x - o.corpseX, dz = cp.z - o.corpseZ;
        std::printf("P2_BOMBSARAI_OWN_CORPSE source_id=58 token=%u x=%.1f z=%.1f moved=%.1f carriers=%d\n", o.token,
                    cp.x, cp.z, std::sqrt(dx * dx + dz * dz), o.corpse->mCarrierCounter);
        std::fflush(stdout);
    }
}
} // namespace

// ---------------------------------------------------------------- public
bool pc_p2_bombsarai_own_setup() {
    if (!pc_randomizer_p2_bridge() || !tekiMgr) return false;
    loadAssets();
    if (!sMap) sMap = new P2BombSaraiMapBinding;
    if (!sAdapter) sAdapter = new P2BombSaraiTerrainAdapter;
    sMap->reset(mapMgr);
    sAdapter->reset(P2BombSaraiMapBinding::traceMove, sMap, P2BombSaraiMapBinding::getMinY, sMap);
    sPool = P2BombSaraiBombPool(16);
    sBombClock.reset();
    int bound = 0;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        auto* t = static_cast<Teki*>(*it);
        if (!t || !t->mGenerator) continue;
        BTeki* b = static_cast<BTeki*>(t);
        if (pc_p2_campaign_source(b) != kSource) continue;
        const unsigned token = pc_p2_campaign_token(b);
        if (t->mTekiType != kHostType) {
            std::printf("P2_BOMBSARAI_OWN_UNBOUND token=%u type=%d reason=host_type_mismatch\n", token, t->mTekiType);
            std::fflush(stdout);
            if (pc_p2_setup_skip(true, "BombSarai", "actor_type_mismatch")) continue;
        }
        Own& o = sOwn[b];
        o = Own{};
        o.token = token;
        const Vector3f pos = t->getPosition();
        o.fsm.init(sParams, sBank, {pos.x, pos.y, pos.z}, t->getDirection(), (token * 2654435761u) | 1u);
        t->mHealth = sParams.health;
        o.lastHealth = t->mHealth;
        t->setTekiOption(TEKIOPT_DamageCountable);
        o.lastDamageCount = t->mDamageCount;
        // Ordinary-delivery bridge: GoalItem::suckMe grants onion:p2:58 for
        // this token exactly once when the carcass reaches the Onion/Pod.
        pc_randomizer_p2_bind_source(static_cast<PelletView*>(b), kSource, token);
        ++bound;
        std::printf("P2_BOMBSARAI_OWN_BIND source_id=58 token=%u host_type=%d health=%.1f retail_parms=%d "
                    "bank_clips=%d draw=%s suppress_ai=1 corpse_type=%d state=%s\n",
                    token, t->mTekiType, t->mHealth, sParams.retail ? 1 : 0,
                    [] { int n = 0; for (const auto& c : sBank.clip) n += c.staged ? 1 : 0; return n; }(),
                    sPosesLoaded ? "p2_model" : "host", t->getParameterI(TPI_CorpseType),
                    p2bsown::stateName(o.fsm.state()));
        std::printf("P2_BOMBSARAI_OWN_DELIVERY_BIND source_id=58 token=%u\n", token);
    }
    std::printf("P2_BOMBSARAI_OWN_SETUP bound=%d\n", bound);
    std::fflush(stdout);
    return true;
}

bool pc_p2_bombsarai_own_tick(BTeki* t) {
    auto i = sOwn.find(t);
    if (i == sOwn.end()) return false;
    Own& o = i->second;
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    if (o.escaped) {
        o.carcassTime += dt > 0.0f && dt < 0.5f ? dt : 0.0f;
        corpseProbe(t, o);
        return true;
    }
    if (t->mDeadState == 1) {
        // Something outside the machine called die(); dieSoon only runs in
        // the suppressed doAI, so finish the teardown (groink pattern).
        dropHeld(t, o, P2BombSaraiThrowKind::Death, "host_die_external");
        o.escaped = true;
        std::printf("P2_BOMBSARAI_OWN_KILL source_id=58 token=%u health=%.1f native=host_die_external\n", o.token,
                    t->mHealth);
        std::fflush(stdout);
        t->pcEscapeNow();
        return true;
    }
    if (t->mDeadState != 0) return true;
    if (!(dt > 0.0f && dt < 0.5f)) return true;
    ownTick(t, o, dt);
    return true;
}

void pc_p2_bombsarai_own_forget(BTeki* t) {
    auto i = sOwn.find(t);
    if (i == sOwn.end()) return;
    // A carried bomb is released, never left captured on a dead slot.
    if (i->second.held && i->second.held->phase() == P2BombSaraiBombPhase::Captured)
        i->second.held->throwBomb(P2BombSaraiThrowKind::Death, 0.0f);
    std::printf("P2_BOMBSARAI_OWN_FORGET source_id=58 token=%u escaped=%d remaining=%d\n", i->second.token,
                i->second.escaped ? 1 : 0, int(sOwn.size()) - 1);
    std::fflush(stdout);
    sOwn.erase(i);
    sDrawLogged.erase(t);
    sPoseVis.forget(t);
}

void pc_p2_bombsarai_own_reset() {
    const int before = int(sOwn.size());
    sOwn.clear();
    sDrawLogged.clear();
    sPoseVis.clear();
    sBombVis.clear();
    sPoseBank.reset();
    sBombPoseBank.reset();
    for (auto& gauge : sBombGauge) gauge = P2BombGauge();
    for (int s = 0; s < kBombGaugeSlots; ++s) endBombFx(s, "reset");
    sPool = P2BombSaraiBombPool(16);
    for (auto& v : sPoses) v.clear();
    for (auto& v : sBombPoses) v.clear();
    sPosesLoaded = false;
    sBlastCount = 0;
    if (before) {
        std::printf("P2_BOMBSARAI_OWN_RESET bound_before=%d\n", before);
        std::fflush(stdout);
    }
}

bool pc_p2_bombsarai_teki_suppress_ai(const BTeki* t) {
    const Own* o = find(t);
    return o && !o->escaped;
}

float pc_p2_bombsarai_teki_param_f(const BTeki* t, int idx, float fallback) {
    const Own* o = find(t);
    if (!o || o->escaped) return fallback;
    if (idx == TPF_Life) return o->fsm.params().health;
    if (idx == TPF_LifeRecoverRate) return o->fsm.params().regenRate;
    return fallback;
}

void pc_p2_bombsarai_teki_update_bombs() {
    if (!sAdapter || sPool.activeCount() == 0) {
        sBombClock.reset();
        for (int s = 0; s < sPool.slotCount(); ++s) sBombVis.forget(sPool.bombAt(s));
        for (int s = 0; s < kBombGaugeSlots; ++s) endBombFx(s, "no_bombs");
        return;
    }
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    for (int s = 0; s < sPool.slotCount(); ++s) {
        if (sPool.slotLive(s)) sBombVis.advance(sPool.bombAt(s), p2fbsmooth::fadeStep(dt));
        else sBombVis.forget(sPool.bombAt(s));
    }
    // #1066 lit-bomb cues, one presentation frame at a time.
    for (int s = 0; s < sPool.slotCount() && s < kBombGaugeSlots; ++s) {
        const P2BombSaraiBomb* b = sPool.slotLive(s) ? sPool.bombAt(s) : nullptr;
        BombFx& fx = sBombFx[s];
        if (fx.sinceBlast >= 0.0f && (fx.sinceBlast += p2fbsmooth::fadeStep(dt)) >= 1.0f) {
            // One second on: only the engine's own blast effect may still be fading.
            std::printf("P2_BOMBSARAI_BOMB_FX_AFTER token=%llu slot=%d tracked=%d live_generators=%u baseline=%u\n",
                        (unsigned long long)fx.token, s, fx.sparks.count + fx.glow.count,
                        pc_p2_bomb_live_generators(), fx.baseline);
            fx.sinceBlast = -1.0f;
        }
        if (!bombBurning(b)) {
            endBombFx(s, "not_burning");
            continue;
        }
        const P2BombSaraiVec3& p = b->position();
        if (!fx.lit) {
            fx.lit = true;
            fx.token = b->carrierToken();
            fx.baseline = pc_p2_bomb_live_generators();
            std::printf("P2_BOMBSARAI_BOMB_LIT token=%llu slot=%d fuse=%.2f/%.2f\n", (unsigned long long)fx.token, s,
                        b->fuseRemaining(), b->fuseMax());
        }
        const float ratio = bombRatio(b);
        fx.sparks.update(p2fbsmooth::fadeStep(dt), 0.35f);
        fx.glow.update(p2fbsmooth::fadeStep(dt), 0.35f);
        if (!fx.light && b->fuseRemaining() < p2bombtelegraph::kLightBelowHealth) {
            fx.light = true;
            std::printf("P2_BOMBSARAI_BOMB_LIGHT token=%llu slot=%d fuse=%.2f threshold=%.1f source=bomb.cpp:203\n",
                        (unsigned long long)fx.token, s, b->fuseRemaining(), p2bombtelegraph::kLightBelowHealth);
        }
        if (fx.pulse.step(p2fbsmooth::fadeStep(dt), ratio)) {
            fx.sparks.spawn(kBombSparkEffect, p.x, p.y + 8.0f, p.z);
            if (fx.light) fx.glow.spawn(kBombGlowEffect, p.x, p.y + 4.0f, p.z);
            pc_p2_sfx(58, unsigned(fx.token), p2sfx::Event::Fuse, Vector3f(p.x, p.y, p.z));
            std::printf("P2_BOMBSARAI_BOMB_TICK token=%llu slot=%d n=%d ratio=%.3f period=%.3f light=%d\n",
                        (unsigned long long)fx.token, s, fx.pulse.pulses, ratio, p2bombtelegraph::flashPeriod(ratio),
                        fx.light ? 1 : 0);
        }
    }
    const int ticks = sBombClock.step(double(dt), true);
    for (int k = 0; k < ticks; ++k) {
        for (int s = 0; s < sPool.slotCount(); ++s) {
            if (!sPool.slotLive(s)) continue;
            P2BombSaraiBomb* b = sPool.bombAt(s);
            const P2BombSaraiBombPhase before = b->phase();
            b->update(P2BombSaraiBomb::kSourceDelta, P2BombSaraiTerrainAdapter::trace, sAdapter, carrierAlive, nullptr);
            if (before == P2BombSaraiBombPhase::InFlight && b->phase() == P2BombSaraiBombPhase::ArmedLoop) {
                std::printf("P2_BOMBSARAI_OWN_BOMB_LANDED source_id=58 token=%llu x=%.1f y=%.1f z=%.1f\n",
                            (unsigned long long)b->carrierToken(), b->position().x, b->position().y, b->position().z);
            }
            if (b->hasBlast()) {
                const P2BombSaraiBlastEvent e = b->lastBlast();
                b->clearBlast();
                if (s < kBombGaugeSlots) endBombFx(s, "blast");  // nothing outlives the blast
                applyBlast(e);
            }
        }
    }
    std::fflush(stdout);
}

namespace {
void drawShapeAt(Graphics& gfx, Shape* shape, const Vector3f& pos, float yaw, float scale = 1.0f, bool lit = false,
                 bool flashOn = false, float ratio = 1.0f) {
    Matrix4f world, view;
    world.makeSRT(Vector3f(scale, scale, scale), Vector3f(0.0f, yaw, 0.0f), pos);
    gfx.mCamera->mLookAtMtx.multiplyTo(world, view);
    // #1066: the shared lit-fuse tint (pc_p2_bomb_visual.h), restored after the draw.
    pc_p2_bomb_draw_tinted(gfx, *shape, view, lit, flashOn, ratio);
}
bool sBombDrawLogged = false;
}

void pc_p2_bombsarai_teki_draw_bombs(Graphics& gfx) {
    if (!gfx.mCamera || sPool.activeCount() == 0) return;
    const bool haveIdle = !sBombPoses[0].empty();
    const bool haveLoop = !sBombPoses[1].empty();
    if (!haveIdle && !haveLoop) return;
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov, gfx.mCamera->mAspectRatio,
                       gfx.mCamera->mNear, gfx.mCamera->mFar, 1.0f);
    gfx.useMaterial(nullptr);
    gfx.setDepth(true);
    static int pulse = 0;
    ++pulse;
    int drawn = 0;
    pc_gfx_specular_family_scope(1);
    for (int s = 0; s < sPool.slotCount(); ++s) {
        if (!sPool.slotLive(s)) continue;
        const P2BombSaraiBomb* b = sPool.bombAt(s);
        const bool armed = b->phase() == P2BombSaraiBombPhase::ArmedLoop || b->phase() == P2BombSaraiBombPhase::Burning;
        Shape* shape = nullptr;
        if (armed && haveLoop) shape = sBombPoses[1][std::size_t(pulse / 4) % sBombPoses[1].size()];
        else if (haveIdle) shape = sBombPoses[0][0];
        else shape = sBombPoses[1][0];
        {
            // #972: hit_start frame 0 while carried/falling, hit_loop at a continuous
            // frame once armed; the private Shape lerps and crossfades the change.
            const bool loop = armed && haveLoop;
            const int use = loop ? 1 : (haveIdle ? 0 : 1);
            if (use < sBank.bombClipCount) {
                const int loopFrames = std::max(1, sBank.bombClip[use].frames);
                if (Shape* smooth = sBombVis.draw(b, sBombPoseBank, sBank.bombClip[use].name,
                                                  loop ? p2fbsmooth::bombLoopFrame(pulse, loopFrames) : 0.0f,
                                                  unsigned(b->carrierToken())))
                    shape = smooth;
            }
        }
        const P2BombSaraiVec3& p = b->position();
        const bool lit = s < kBombGaugeSlots && sBombFx[s].lit && bombBurning(b);
        const bool flashOn = lit && sBombFx[s].pulse.on();
        drawShapeAt(gfx, shape, Vector3f(p.x, p.y, p.z), 0.0f, flashOn ? p2bombtelegraph::kFlashSwell : 1.0f, lit,
                    flashOn, lit ? bombRatio(b) : 1.0f);
        ++drawn;
    }
    pc_gfx_specular_family_scope(0);
    if (drawn && !sBombDrawLogged) {
        sBombDrawLogged = true;
        std::printf("P2_BOMBSARAI_OWN_BOMB_DRAW model=p2_bomb bombs=%d\n", drawn);
        std::fflush(stdout);
    }
}

// #1027: the bomb's own life gauge, drawn in the 2D pass (GameCoreSection::draw1D).
// P2 shows the Bomb enemy's ordinary life gauge (EnemyBase::doGetLifeGaugeParam:
// mHealth / mMaxHealth at mPosition.y + fp27) and hides it while the ratio is 1
// (LifeGaugeMgr::update), so it appears once the fuse starts draining after the
// bomb lands (ArmedLoop) and stays through the burn.
void pc_p2_bombsarai_teki_draw_bomb_gauges(Graphics& gfx) {
    if (!gfx.mCamera) return;
    int drawn = 0;
    for (int s = 0; s < sPool.slotCount() && s < kBombGaugeSlots; ++s) {
        const P2BombSaraiBomb* b = sPool.slotLive(s) ? sPool.bombAt(s) : nullptr;
        const bool burning = b && (b->phase() == P2BombSaraiBombPhase::ArmedLoop
                                   || b->phase() == P2BombSaraiBombPhase::Burning);
        if (!burning || !(b->fuseMax() > 0.0f) || !(b->fuseRemaining() < b->fuseMax())) {
            sBombGauge[s] = P2BombGauge();
            continue;
        }
        const P2BombSaraiVec3& p = b->position();
        sBombGauge[s].draw(gfx, Vector3f(p.x, p.y, p.z), std::max(0.0f, b->fuseRemaining()), b->fuseMax());
        ++drawn;
        if (!sBombGaugeLogged) {
            sBombGaugeLogged = true;
            std::printf("P2_BOMBSARAI_BOMB_GAUGE token=%llu ratio=%.3f fuse=%.2f/%.2f gauge=P2BombGauge\n",
                        (unsigned long long)b->carrierToken(), b->fuseRemaining() / b->fuseMax(),
                        b->fuseRemaining(), b->fuseMax());
            std::fflush(stdout);
        }
    }
    (void)drawn;
}

bool pc_p2_bombsarai_teki_draw(BTeki* t, Graphics& gfx, const Matrix4f& view, bool corpse) {
    auto i = sOwn.find(t);
    if (i == sOwn.end() || !sPosesLoaded || !gfx.mCamera) return false;
    Own& o = i->second;
    const bool dead = corpse || o.escaped || t->mDeadState != 0;
    int anim = o.fsm.animator().anim();
    float frame = o.fsm.animator().frame();
    if (dead && o.escaped) {
        // startCarcassMotion: type5 loops LOOP_START 10 .. LOOP_END 29.
        anim = p2bsown::AnimCarry;
        frame = 10.0f + std::fmod(o.carcassTime * 30.0f, 19.0f);
    }
    if (anim < 0 || anim >= p2bsown::AnimCount || sPoses[anim].empty()) {
        // supli1 has no convertible pose (zero joint scale): hold wait2.
        anim = !sPoses[p2bsown::AnimBombWait].empty() ? int(p2bsown::AnimBombWait) : int(p2bsown::AnimWait);
        frame = 0.0f;
        if (sPoses[anim].empty()) return false;
    }
    const auto& poses = sBank.clip[anim].poses;
    std::size_t best = 0;
    for (std::size_t k = 1; k < poses.size() && k < sPoses[anim].size(); ++k)
        if (std::fabs(float(poses[k].frame) - frame) < std::fabs(float(poses[best].frame) - frame)) best = k;
    Shape* shape = sPoses[anim][best];
    {
        // #972: lerped pose via the per-actor private Shape (150 ms crossfade on clip
        // change). The carried corpse loops carry (type5) between its source loop
        // markers; a death clip stops on its last visible pose (Actors::draw).
        const float sourceFrame = dead && o.escaped ? p2fbsmooth::carryLoopFrame(o.carcassTime, 10, 29) : frame;
        if (Shape* smooth = sPoseVis.draw(t, sPoseBank, sBank.clip[anim].name, std::max(0.0f, sourceFrame), o.token)) {
            shape = smooth;
            // #1027: the balloons are J3D billboards; turn them to the camera on this
            // actor's private geometry (the shared nearest-pose Shapes stay baked).
            if (!sBillboards.empty()) {
                static_assert(sizeof(Vector3f) == 3 * sizeof(float), "packed Vector3f");
                float rot[3][3];
                for (int r = 0; r < 3; ++r)
                    for (int c = 0; c < 3; ++c) rot[r][c] = view.mMtx[r][c];
                const bool turned = p2billboardgroups::faceCamera(
                    sBillboards, rot, reinterpret_cast<float*>(shape->mVertexList), shape->mVertexCount,
                    reinterpret_cast<float*>(shape->mNormalList), shape->mNormalCount);
                if (!sBillboardLogged) {
                    sBillboardLogged = true;
                    std::printf("P2_BOMBSARAI_BILLBOARD_READY token=%u groups=%zu applied=%d vertices=%d normals=%d\n",
                                o.token, sBillboards.size(), turned ? 1 : 0, shape->mVertexCount, shape->mNormalCount);
                }
            }
        }
    }
    shape->updateAnim(gfx, view, nullptr, t);
    pc_gfx_specular_family_scope(1);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    pc_gfx_specular_family_scope(0);
    int& logged = sDrawLogged[t];
    const int bit = dead ? 2 : 1;
    if (!(logged & bit)) {
        logged |= bit;
        std::printf("P2_BOMBSARAI_OWN_DRAW source_id=58 token=%u corpse=%d clip=%s pose=%zu model=p2_bombsarai\n",
                    o.token, dead ? 1 : 0, sBank.clip[anim].name.c_str(), best);
        std::fflush(stdout);
    }
    if (std::getenv("PIKMIN_FRAME_DUMP")) {
        // Eye-check aid (frame-dump runs only): where this actor sits on screen, so a
        // dumped frame can be cropped around it.
        static std::map<const BTeki*, int> countdown;
        if (++countdown[t] >= 15) {
            countdown[t] = 0;
            // A carried corpse is the pellet; the escaped host drifts away.
            Vector3f sp = dead && t->mPellet ? t->mPellet->getPosition() : t->getPosition();
            const float depth = gfx.mCamera->projectWorldPoint(gfx, sp);
            if (depth > 0.0f && gfx.mScreenWidth > 0 && gfx.mScreenHeight > 0)
                // view_yaw: the actor's model +Z (its front) in view space, 0 = facing the
                // camera, +-180 = seen from behind, +-90 = side on.
                std::printf("P2_BOMBSARAI_SCREEN source_id=58 token=%u u=%.3f v=%.3f depth=%.0f clip=%s frame=%.0f corpse=%d "
                            "view_yaw=%.0f\n",
                            o.token, sp.x / float(gfx.mScreenWidth), sp.y / float(gfx.mScreenHeight), depth,
                            sBank.clip[anim].name.c_str(), frame, dead ? 1 : 0,
                            std::atan2(view.mMtx[0][2], view.mMtx[2][2]) * 57.29578f);
        }
    }
    return true;
}

bool pc_p2_bombsarai_own_is_bound(const BTeki* t) { return find(t) != nullptr; }
