// Empress Bulblax (Queen, enemy 30) OWN campaign binding (#256).
//
// A seeded campaign actor rides the P1 TEKI_Swallow vehicle (hostType 30 ->
// 4); its P1 strategy is fully suppressed (pc_p2_queen_teki_suppress_ai) and
// the engine-free source FSM in pc_p2_queen_own.h drives it from the live
// engine state:
//   * health is the engine BTeki::mHealth only; Pikmin hits arrive through the
//     BTeki::interact seam (pc_p2_queen_teki_attack), which is the source
//     Queen::damageCallBack: Pikmin only, x0.1 asleep, x0.2 flicking, and
//     every accepted hit is one addDamage(.., 1.0) for the flick counter.
//     Captain punches are refused (source: no damage from non-Piki).
//   * the stuck count is the real latch count (Piki::getStickObject()==host).
//   * flick/rolling press/larva birth/kill are executed on real creatures.
//   * death runs the host death funnel (die + dieSoon) at the Dead clip END,
//     leaving the host's LeaveCorpse carcass, which gets a private carcass
//     config (source carcass_config.txt: 15 pokos, carry 20-30) and is bound
//     to onion:p2:30 on the actor's own seed token.
// Larvae (Baby, enemy 31) are real P1 teki (the Queen's own vehicle type at
// larva scale) driven by the source Baby FSM, so Pikmin attack and kill them
// through the engine; they bite captains and persist after the Queen dies.
//
// The room-preview fixture path (p2-queen-teki.txt, non-bridge) still binds
// through the same OWN FSM; it is never used as admission evidence.
#include "pc_p2_queen_teki.h"
#include "pc_p2_queen_teki_policy.h"
#include "pc_p2_queen_own.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_p2_sfx.h"
#include "pc_p2_groink_clock.h"
#include "pc_p2_animation.h"
#include "pc_p2_pose_family.h"
#include "pc_p2_specular_layer.h"
#include "pc_p2_navi_select.h"
#include "pc_bbft.h"
#include "pc_randomizer.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include "pc_randomizer.h"
#include "pc_p2_campaign_actor.h"
#include "gl/pc_gfx.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Pellet.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Interactions.h"
#include "teki.h"
#include "Generator.h"
#include "system.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <set>
#include <SDL.h>
#include <string>
#include <vector>

namespace {
using namespace p2queenown;

// P1 vehicle sizing. The Swallow collision tree is scaled so Pikmin latch on
// a body of Queen size (source queen/enemycoll.txt: torso spheres 75-90, root
// 275); the P2 model itself is drawn at source scale 1 (the draw undoes the
// host scale). Larvae ride the same vehicle at larva scale (baby root 25).
constexpr float kQueenHostScale = 3.0f;
constexpr float kLarvaHostScale = 0.35f;
// Carry radius of the carcass pellet. 100 wedged in the Impact arena exit at
// (-391,712) with 31 carriers pulling (wave-3 a10, moving=0); the P2 Queen
// leaves no carcass in source, so this is an approximation sized to pass it.
constexpr float kQueenCorpseRadius = 50.0f;
// Source body extent along the Queen's facing axis (+Z = nose), in world
// units: the staged rest pose bulblax_Queen_wait1_00 bounds z = -224..245
// (the P2 model is drawn at source scale 1). The host has no nose/head/bod1/
// bod5 parts or body_end joint, so the flick part rule and the larva birth
// point are taken from this extent instead of the P1 host's centre sphere.
constexpr float kQueenBodyRear = -224.0f;
constexpr float kQueenBodyFront = 245.0f;
// P1 performance cap on live larvae (source Baby::Mgr pool 50, hysteresis
// max 50 / min 25). The cap scales the hysteresis to 10 / 5.
constexpr int kLarvaCap = 10;
// Standalone larva: no carcass (#1088). The source Baby leaves none (Baby.cpp:40
// disables EB_LeaveCarcass, BabyState.cpp:41/80 kill() at the clip end). The
// #1042 carryable-corpse accommodation is withdrawn by the owner ruling of
// 2026-10-01 ("get rid of the jellyfloat corpses and the larva corpses let's
// stay P2-accurate"); the randomizer check is earned at the kill
// (pc_p2_no_carcass). The radius is the larva's grab extent while it is alive.
constexpr float kLarvaCorpseRadius = 15.0f;
// Source carcass_config.txt Queen entry (pikmin2_bulblax_assets.CARCASS).
constexpr int kCarcassPokos = 15;
constexpr int kCarcassCarryMin = 20;
constexpr int kCarcassCarryMax = 30;

struct Binding {
    unsigned generator = 0;
    unsigned source = 0; // 30 in a campaign seed; 0 for the preview fixture
    Queen fsm;
    P2GroinkSourceClock clock;
    int hits = 0;          // accepted Pikmin hits since the last source tick
    int hitsTotal = 0;
    int refusedCaptain = 0;
    float lastHealth = 0.0f;
    float startHealth = 0.0f;
    Vector3f anchor;
    bool escaped = false;  // death funnel ran (die + dieSoon)
    bool corpse = false;   // carcass config applied
    bool deadLogged = false;
    float logTimer = 0.0f;
    int rollPresses = 0, rollPressPiki = 0, rollPressNavi = 0, rollPressLarva = 0;
    int flicks = 0, flickedPiki = 0;
    int births = 0, birthRefused = 0;
    int maxStuck = 0;
    // Approach position (actor frame: along, lateral) of each Pikmin last seen
    // near her and not stuck; decides which body part it latches on (exitPart).
    std::map<Piki*, p2queenown::Vec2> approach;
    // Flicked Pikmin and where they were, to log how far the knockback carried them.
    std::vector<std::pair<Piki*, Vector3f>> flung;
    float flungTimer = 0.0f;
};
std::map<BTeki*, Binding> s;

struct Larva {
    unsigned id = 0;
    unsigned queen = 0; // parent token (for logs; the larva outlives her)
    // Standalone larva (#1042): a seeded campaign slot bound to source id 31.
    // It owns its generator token, leaves a carryable corpse (see
    // kLarvaCarry*) and delivers the Onion receipt; Queen-born larvae keep
    // the source behaviour of no carcass.
    bool standalone = false;
    unsigned generator = 0;
    unsigned source = 0;
    bool corpse = false;   // carcass config applied
    Baby fsm;
    P2GroinkSourceClock clock;
    bool escaped = false;
    bool deadLogged = false;
    float lastHealth = 0.0f;
    int bites = 0;
    int hits = 0;
    Piki* mouth = nullptr; // Pikmin taken by eatPikmin at attack KEYEVENT_2 (mouth slot 0)
    int eaten = 0;
    int nearTicks = 0;
};
std::map<BTeki*, Larva> sLarvae;
unsigned sLarvaSerial = 0;

struct SpawnReq {
    unsigned queen = 0;
    int type = 0;
    Vector3f pos;
    float face = 0.0f;
    float vx = 0.0f, vz = 0.0f;
};
std::vector<SpawnReq> sSpawns;

Params sParams;
Bank sBank = defaultBank();
std::vector<Shape*> sPoses[AnimCount];
std::vector<Shape*> sBabyPoses[BabyAnimCount];
bool sPosesLoaded = false, sBabyPosesLoaded = false;
p2material::Bank sMaterial;
bool sMaterialEnabled = false;
float sMaterialFrame = 0.0f;
std::map<BTeki*, int> sDrawLogged;
// #972: dense (24/clip) poses are presented through the shared #895 pose path:
// bracket + lerp into a private Shape per actor, crossfade on clip change. The
// Queen and the larva are different meshes, so each has its own bank/tracks.
// Visual only: the FSM clocks and every gameplay input are untouched.
p2posefamily::Bank sQueenPoseBank("QUEEN"), sBabyPoseBank("QUEEN_LARVA");
p2posefamily::Actors sQueenVis, sBabyVis;
std::vector<PelletConfig*> sConfigs;

float groundY(float x, float z, float fallback) { return mapMgr ? mapMgr->getMinY(x, z, true) : fallback; }

// Staged bank + poses: bulblax_<Queen|Baby>_<clip>_<ii>.mod, one per staged
// pose frame (pikmin2_bulblax_assets pose naming), loaded through the shared
// compact pose loader (p2poseload::loadStem).
void loadBank(bool bridge) {
    sBank = defaultBank();
    sParams = Params{};
    for (auto& v : sPoses) v.clear();
    for (auto& v : sBabyPoses) v.clear();
    sPosesLoaded = sBabyPosesLoaded = false;
    std::ifstream in("p2-queen-bank.txt");
    std::string error;
    if (!in) {
        std::printf("P2_QUEEN_BANK staged=0 fallback=builtin_timing draw=host\n");
    } else if (!parseBank(in, sBank, sParams, error)) {
        std::printf("P2_QUEEN_BANK_INVALID reason=%s fallback=builtin_timing draw=host\n", error.c_str());
        sBank = defaultBank();
        sParams = Params{};
    }
    // Compact pose loader (#895/#972): a few full Shapes per clip (the nearest-pose
    // fallback and the material owner) plus decoded vectors for every pose, so a
    // dense 24-pose bank stays ~0.5 MiB resident per Queen clip.
    sQueenPoseBank.reset();
    sBabyPoseBank.reset();
    sQueenVis.clear();
    sBabyVis.clear();
    std::size_t total = 0, poses = 0;
    std::size_t minQueen = 0, maxQueen = 0, minBaby = 0, maxBaby = 0;
    p2poseload::Shared shared;
    bool ok = true;
    for (int a = 0; ok && a < AnimCount; ++a) {
        const Clip& c = sBank.clip[a];
        if (c.poses.empty()) continue;
        std::string why;
        if (!p2posefamily::loadFamilyClip(sQueenPoseBank, c.name, "bulblax_Queen_" + c.name, int(c.poses.size()),
                                          c.frames, c.poses, shared, total, sPoses[a], why)) {
            ok = false;
            std::printf("P2_QUEEN_POSE_MISSING clip=%s reason=%s\n", c.name.c_str(), why.c_str());
            break;
        }
        poses += c.poses.size();
        minQueen = minQueen ? std::min(minQueen, c.poses.size()) : c.poses.size();
        maxQueen = std::max(maxQueen, c.poses.size());
    }
    sPosesLoaded = ok && !sPoses[AnimWait].empty() && !sPoses[AnimDead].empty();
    if (!sPosesLoaded) for (auto& v : sPoses) v.clear();
    std::size_t babyPoses = 0;
    p2poseload::Shared babyShared;
    ok = true;
    for (int a = 0; ok && a < BabyAnimCount; ++a) {
        const Clip& c = sBank.baby[a];
        if (c.poses.empty()) continue;
        std::string why;
        if (!p2posefamily::loadFamilyClip(sBabyPoseBank, c.name, "bulblax_Baby_" + c.name, int(c.poses.size()),
                                          c.frames, c.poses, babyShared, total, sBabyPoses[a], why)) {
            ok = false;
            std::printf("P2_QUEEN_LARVA_POSE_MISSING clip=%s reason=%s\n", c.name.c_str(), why.c_str());
            break;
        }
        babyPoses += c.poses.size();
        minBaby = minBaby ? std::min(minBaby, c.poses.size()) : c.poses.size();
        maxBaby = std::max(maxBaby, c.poses.size());
    }
    sBabyPosesLoaded = ok && !sBabyPoses[BabyAnimMove].empty();
    if (!sBabyPosesLoaded) for (auto& v : sBabyPoses) v.clear();
    int staged = 0;
    for (const auto& c : sBank.clip) staged += c.staged ? 1 : 0;
    sMaterialEnabled = false;
    std::ifstream material("p2-queen-specular.txt");
    if (material && sPosesLoaded) {
        try {
            sMaterial = p2material::read(material);
            Shape* probe = sPoses[AnimWait].front();
            sMaterialEnabled = sMaterial.duration > 0 && sMaterial.tracks.size() == 1 && probe->mMaterialCount == 2
                && probe->mTexAttrCount >= 3 && probe->mMaterialList[1].mTextureInfo.mTextureDataCount == 1;
        } catch (...) {
            sMaterialEnabled = false;
        }
    }
    std::printf("P2_QUEEN_BANK staged_clips=%d retail_parms=%d poses=%zu baby_poses=%zu bytes=%zu draw=%s "
                "specular=%d bridge=%d health=%.1f rolling_time=%.2f birth_interval=%.2f territory=%.1f\n",
                staged, sParams.retail ? 1 : 0, sPosesLoaded ? poses : std::size_t(0),
                sBabyPosesLoaded ? babyPoses : std::size_t(0), total, sPosesLoaded ? "p2_model" : "host",
                sMaterialEnabled ? 1 : 0, bridge ? 1 : 0, sParams.health, sParams.rollingTime, sParams.birthInterval,
                sParams.territoryRadius);
    if (sPosesLoaded) {
        // #972: one line per setup naming the pose density and whether the draw
        // interpolates (PIKMIN_P2_INTERPOLATION=0 -> nearest pose, same bank).
        const p2motion::Tunables& tune = p2motion::tunables();
        const bool queenReady = sQueenPoseBank.ready(), larvaReady = sBabyPoseBank.ready();
        std::printf("P2_QUEEN_INTERPOLATION_READY interpolation=%d poses_per_clip=%zu..%zu larva_poses_per_clip=%zu..%zu "
                    "queen_vectors=%d larva_vectors=%d crossfade_ms=%d gameplay_clock=P1\n",
                    int(tune.lerp && queenReady), minQueen, maxQueen, minBaby, maxBaby, int(queenReady),
                    int(larvaReady), int(tune.crossfadeSeconds * 1000.f + .5f));
    }
    std::fflush(stdout);
}

int liveLarvae() {
    int n = 0;
    for (const auto& kv : sLarvae)
        if (!kv.second.escaped && kv.second.fsm.state() >= BabyBorn && kv.first->mHealth > 0.0f) ++n;
    return n;
}

void trackApproach(BTeki* t, Binding& b) {
    if (!pikiMgr) return;
    const float f = b.fsm.faceDir();
    const float fx = std::sin(f), fz = std::cos(f);
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p) continue;
        if (!p->isAlive()) { b.approach.erase(p); continue; }
        if (p->getStickObject() == t) continue; // latched: keep the recorded approach
        const Vector3f& pp = p->getPosition();
        const float dx = pp.x - t->mSRT.t.x, dz = pp.z - t->mSRT.t.z;
        if (dx * dx + dz * dz > 400.0f * 400.0f) { b.approach.erase(p); continue; }
        // Inside her footprint the host piles Pikmin round its centre at arbitrary bearings; only the approach from outside (>= 100) says which side they came from.
        if (dx * dx + dz * dz < 100.0f * 100.0f) continue;
        b.approach[p] = {dx * fx + dz * fz, dx * fz - dz * fx};
    }
}

int stuckCount(BTeki* t) {
    int n = 0;
    if (!pikiMgr) return 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p && p->isAlive() && p->getStickObject() == t) ++n;
    }
    return n;
}

// Queen::flickPikmin(angle). The P1 host has no nose/head/bod1/bod5 part ids, so
// each stuck Pikmin is given the source body sphere nearest its position
// (p2queenown::nearestPart, sphere centres from the model's joints):
// nose/head/bod1 -> flick at `angle`; bod5 -> flick at PI + angle; bod2/bod3/bod4
// -> shake off with 0 knockback, backward. The P2 InteractFlick::actPiki
// receiver ignores the damage argument, so none is passed to the P1 receiver
// (which would subtract it from Pikmin health); the source value is logged.
int flickStuck(BTeki* t, Binding& b, bool face) {
    if (!pikiMgr) return 0;
    const float f = b.fsm.faceDir();
    const float fx = std::sin(f), fz = std::cos(f);
    const float angle = face ? f : FLICK_BACKWARDS_ANGLE;
    int flicked = 0, front = 0, rear = 0, none = 0;
    std::vector<Piki*> stuck; // snapshot: the flick detaches them from the live list
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p && p->isAlive() && p->getStickObject() == t) stuck.push_back(p);
    }
    for (Piki* p : stuck) {
        const Vector3f& pp = p->getPosition();
        const float dx = pp.x - t->mSRT.t.x, dz = pp.z - t->mSRT.t.z;
        const float along = dx * fx + dz * fz;
        const float lateral = dx * fz - dz * fx;
        const float height = pp.y - t->mSRT.t.y;
        const auto known = b.approach.find(p);
        const int part = known != b.approach.end() ? p2queenown::exitPart(known->second.x, known->second.z)
                                                   : p2queenown::nearestPart(along, lateral, height);
        const int kind = p2queenown::flickKind(part);
        const float knock = kind == p2queenown::FlickNone ? 0.0f : b.fsm.params().shakeKnockback;
        const float dir = kind == p2queenown::FlickRear && face ? kPi + angle
                          : kind == p2queenown::FlickNone ? FLICK_BACKWARDS_ANGLE : angle;
        const bool ok = p->stimulate(InteractFlick(t, knock, 0.0f, dir));
        if (kind == p2queenown::FlickFront) ++front;
        else if (kind == p2queenown::FlickRear) ++rear;
        else ++none;
        if (ok) {
            ++flicked;
            b.flung.emplace_back(p, pp);
            b.flungTimer = 0.6f;
        }
        std::printf("P2_QUEEN_FLICK_PIKI generator=%u part=%s from=%s along=%.1f lateral=%.1f height=%.1f knockback=%.0f "
                    "dir_deg=%.0f accepted=%d detached=%d\n",
                    b.generator, p2queenown::partName(part), known != b.approach.end() ? "approach" : "position", along,
                    lateral, height, knock,
                    dir < -10.0f ? -1.0f : dir * 180.0f / kPi, ok ? 1 : 0, p->getStickObject() == t ? 0 : 1);
    }
    if (face || flicked) {
        b.flickedPiki += flicked;
        std::printf("P2_QUEEN_FLICK generator=%u source_id=%u mode=%s stuck=%zu flicked=%d front=%d rear=%d none=%d "
                    "knockback=%.0f source_damage=%.1f part_rule=body_spheres\n",
                    b.generator, b.source, face ? "key2_face" : "rolling_backward", stuck.size(), flicked, front, rear,
                    none, b.fsm.params().shakeKnockback, b.fsm.params().shakeDamage);
    }
    return flicked;
}

// Queen::rollingAttack: every live creature within 250 of the Queen with
// |dy| < 50, |lateral| < attackHitAngle (25 units) and |forward| <
// attackRadius (150) receives InteractPress(attackDamage). Larvae run the
// source Baby::pressCallBack.
void rollPress(BTeki* t, Binding& b) {
    const Vector3f q = t->getPosition();
    const float f = b.fsm.faceDir();
    const float fx = std::sin(f), fz = std::cos(f);
    const float bx = -fz, bz = fx;
    const Params& P = b.fsm.params();
    auto inBox = [&](const Vector3f& p) {
        const float dx = p.x - q.x, dy = p.y - q.y, dz = p.z - q.z;
        if (dx * dx + dy * dy + dz * dz > 250.0f * 250.0f) return false;
        if (std::fabs(dy) >= 50.0f) return false;
        if (std::fabs(bx * dx + bz * dz) >= P.attackHitAngle) return false;
        return std::fabs(fx * dx + fz * dz) < P.attackRadius;
    };
    // `damage` is the value actually passed to InteractPress (larvae take the
    // source Baby::pressCallBack instead, logged as their press state).
    auto log = [&](const char* kind, Creature* c, bool accepted, float damage) {
        const Vector3f& p = c->getPosition();
        std::printf("P2_QUEEN_ROLL_PRESS generator=%u source_id=%u target=%s accepted=%d damage=%.1f x=%.1f z=%.1f\n",
                    b.generator, b.source, kind, accepted ? 1 : 0, damage, p.x, p.z);
    };
    for (Navi* n : pc_p2_navis()) {
        if (!n || !n->isAlive() || !inBox(n->getPosition())) continue;
        const bool ok = n->stimulate(InteractPress(t, P.attackDamage));
        if (ok) { ++b.rollPresses; ++b.rollPressNavi; }
        log("navi", n, ok, P.attackDamage);
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive() || !inBox(p->getPosition())) continue;
            // P2 InteractPress::actPiki -> PikiPressedState always crushes the
            // Pikmin (interactPiki.cpp:584-604); the P1 pressed state only
            // kills at health <= 0, so the press carries the Pikmin's health.
            const float crush = p->mHealth > P.attackDamage ? p->mHealth : P.attackDamage;
            const bool ok = p->stimulate(InteractPress(t, crush));
            if (ok) { ++b.rollPresses; ++b.rollPressPiki; }
            log("piki", p, ok, crush);
        }
    }
    if (tekiMgr) {
        Iterator it(tekiMgr);
        CI_LOOP(it) {
            BTeki* o = static_cast<BTeki*>(*it);
            if (!o || o == t || !o->isAlive() || !inBox(o->getPosition())) continue;
            auto l = sLarvae.find(o);
            if (l != sLarvae.end()) {
                BabyOutput out;
                const bool ok = !l->second.escaped && l->second.fsm.press(out);
                if (ok) {
                    ++b.rollPresses;
                    ++b.rollPressLarva;
                    o->mHealth = 0.0f; // StatePress::init sets mHealth = 0 (source)
                    std::printf("P2_QUEEN_LARVA_STATE id=%u queen=%u state=Press cause=roll\n", l->second.id,
                                l->second.queen);
                }
                log("larva", o, ok, 0.0f);
                continue;
            }
            if (s.count(o)) continue;
            const bool ok = o->stimulate(InteractPress(t, P.attackDamage));
            log("teki", o, ok, P.attackDamage);
        }
    }
}

void logState(Binding& b, int from, int to, BTeki* t, int stuck) {
    const Vector3f p = t->getPosition();
    std::printf("P2_QUEEN_STATE generator=%u source_id=%u from=%s state=%s x=%.1f z=%.1f health=%.1f stuck=%d "
                "flick_timer=%.1f larvae=%d hits_total=%d\n",
                b.generator, b.source, stateName(from), stateName(to), p.x, p.z, t->mHealth, stuck,
                b.fsm.flickTimer(), liveLarvae(), b.hitsTotal);
}

void queueBirth(BTeki* t, Binding& b) {
    // createBabyChappy: position = body_end joint (the Queen's tail; the P1
    // host has no joint -> the tail end of the source body extent,
    // kQueenBodyRear), face = PI + faceDir, velocity = searchDistance *
    // (sin, cos)(face).
    if (liveLarvae() + int(sSpawns.size()) >= kLarvaCap) {
        ++b.birthRefused;
        std::printf("P2_QUEEN_BIRTH_CAPPED generator=%u source_id=%u live=%d cap=%d\n", b.generator, b.source,
                    liveLarvae(), kLarvaCap);
        return;
    }
    const float f = b.fsm.faceDir();
    const float back = -kQueenBodyRear;
    SpawnReq r;
    r.queen = b.generator;
    r.type = t->mTekiType;
    r.pos.set(t->mSRT.t.x - std::sin(f) * back, t->mSRT.t.y, t->mSRT.t.z - std::cos(f) * back);
    r.face = f + kPi;
    r.vx = b.fsm.params().searchDistance * std::sin(r.face);
    r.vz = b.fsm.params().searchDistance * std::cos(r.face);
    sSpawns.push_back(r);
    ++b.births;
}

void applyOutput(BTeki* t, Binding& b, const TickOutput& o, int& shown, int stuck) {
    for (int e : o.entered) {
        logState(b, shown, e, t, stuck);
        shown = e;
        if (e == Dead && !b.deadLogged) {
            b.deadLogged = true;
            std::printf("P2_QUEEN_DEAD generator=%u source_id=%u health=%.1f start_health=%.1f hits_total=%d "
                        "roll_presses=%d piki=%d navi=%d larva=%d flicked=%d births=%d max_stuck=%d refused_captain=%d\n",
                        b.generator, b.source, t->mHealth, b.startHealth, b.hitsTotal, b.rollPresses,
                        b.rollPressPiki, b.rollPressNavi, b.rollPressLarva, b.flickedPiki, b.births, b.maxStuck,
                        b.refusedCaptain);
        }
    }
    if (o.flickFace) { ++b.flicks; flickStuck(t, b, true); pc_p2_sfx(30, b.generator, p2sfx::Event::Flick, t->getPosition()); }
    if (o.flickBackward) flickStuck(t, b, false);
    if (o.rollStart) pc_p2_sfx(30, b.generator, p2sfx::Event::Roll, t->getPosition());
    if (o.rollStart)
        std::printf("P2_QUEEN_ROLL_START generator=%u source_id=%u anim=%s ignore_atari=navi,teki\n", b.generator,
                    b.source, animName(b.fsm.animator().anim()));
    if (o.rollingAttack) rollPress(t, b);
    if (o.crash) pc_p2_sfx(30, b.generator, p2sfx::Event::Crash, t->getPosition());
    if (o.crash)
        std::printf("P2_QUEEN_CRASH generator=%u source_id=%u dot=%.1f territory=%.1f margin=50\n", b.generator,
                    b.source, o.rollDot, b.fsm.params().territoryRadius);
    if (o.blockedTurn || o.blockedEnd) {
        if (o.blockedTurn) pc_p2_sfx(30, b.generator, p2sfx::Event::Crash, t->getPosition());
        std::printf("P2_QUEEN_ROLL_BLOCKED generator=%u source_id=%u action=%s dot=%.1f x=%.1f z=%.1f "
                    "port_constraint=p1_map_collision_no_progress\n",
                    b.generator, b.source, o.blockedTurn ? "turn" : "end_wait", o.rollDot, t->mSRT.t.x, t->mSRT.t.z);
    }
    if (o.birth) queueBirth(t, b);
    if (o.deadKey)
        std::printf("P2_QUEEN_DEAD_KEY generator=%u source_id=%u frame=%.0f\n", b.generator, b.source,
                    b.fsm.animator().frame());
}

PelletConfig* carcassConfig(PelletConfig* source, int carryMin = kCarcassCarryMin, int carryMax = kCarcassCarryMax) {
    PelletConfig* result = new PelletConfig;
#define COPY_VALUE(name) result->name.mValue = source->name.mValue
    COPY_VALUE(mPelletName);
    COPY_VALUE(mPelletType);
    COPY_VALUE(mPelletColor);
    COPY_VALUE(mUseDynamicMotion);
    COPY_VALUE(_A0);
    COPY_VALUE(_B0);
    COPY_VALUE(_C0);
    COPY_VALUE(mMatchingOnyonSeeds);
    COPY_VALUE(mNonMatchingOnyonSeeds);
    COPY_VALUE(mPelletScale);
    COPY_VALUE(mCarryInfoHeight);
    COPY_VALUE(mAnimSoundID);
    COPY_VALUE(mBounceSoundID);
#undef COPY_VALUE
    result->mModelId = source->mModelId;
    result->mPelletId = source->mPelletId;
    result->mUnusedId = source->mUnusedId;
    result->mRepairAnimJointIndex = source->mRepairAnimJointIndex;
    result->mCarryMinPikis.mValue = carryMin;
    result->mCarryMaxPikis.mValue = carryMax;
    sConfigs.push_back(result);
    return result;
}

void becomeCarcass(BTeki* t, Binding& b) {
    if (b.corpse || !t->mPellet) return;
    b.corpse = true;
    Pellet* pellet = t->mPellet;
    if (pellet->mConfig) pellet->mConfig = carcassConfig(pellet->mConfig);
    const Vector3f& p = pellet->mSRT.t;
    std::printf("P2_QUEEN_CARCASS generator=%u source_id=%u pokos=%d carry_min=%d carry_max=%d x=%.1f z=%.1f "
                "seeds_match=%d seeds_other=%d draw=%s\n",
                b.generator, b.source, kCarcassPokos, pellet->mConfig ? pellet->mConfig->mCarryMinPikis.mValue : -1,
                pellet->mConfig ? pellet->mConfig->mCarryMaxPikis.mValue : -1, p.x, p.z,
                pellet->mConfig ? pellet->mConfig->mMatchingOnyonSeeds.mValue : -1,
                pellet->mConfig ? pellet->mConfig->mNonMatchingOnyonSeeds.mValue : -1,
                sParams.carcassCarryDegenerate ? "dead_pose_fallback" : (sPoses[AnimCarry].empty() ? "dead_last" : "carry"));
    std::fflush(stdout);
}

void ownTick(BTeki* t, Binding& b, float dt) {
    // The damage seam already applied the source coefficient; drain it the
    // way the suppressed strategy would (makeDamaged), the only health write.
    if (t->mStoredDamage > 0.0f) t->makeDamaged();
    if (t->mHealth < b.lastHealth && t->mHealth > 0.0f) pc_p2_sfx(30, b.generator, p2sfx::Event::Damage, t->getPosition());
    if (t->mHealth < b.lastHealth)
        std::printf("P2_QUEEN_DAMAGE generator=%u source_id=%u health=%.1f prior=%.1f state=%s hits=%d stuck=%d\n",
                    b.generator, b.source, t->mHealth, b.lastHealth, stateName(b.fsm.state()), b.hits,
                    stuckCount(t));
    b.lastHealth = t->mHealth;
    trackApproach(t, b);
    if (b.flungTimer > 0.0f && (b.flungTimer -= dt) <= 0.0f) {
        for (const auto& f : b.flung) {
            const Vector3f& now = f.first->getPosition();
            std::printf("P2_QUEEN_FLICK_LAND generator=%u moved_xz=%.1f alive=%d still_stuck=%d\n", b.generator,
                        std::sqrt((now.x - f.second.x) * (now.x - f.second.x) + (now.z - f.second.z) * (now.z - f.second.z)),
                        f.first->isAlive() ? 1 : 0, f.first->getStickObject() == t ? 1 : 0);
        }
        b.flung.clear();
    }
    const int ticks = b.clock.step(double(dt), true);
    if (ticks <= 0) return;
    const int stuck = stuckCount(t);
    if (stuck > b.maxStuck) b.maxStuck = stuck;
    int shown = b.fsm.state();
    TickOutput last;
    bool kill = false;
    Navi* captain = pc_p2_source_active_navi(t->getPosition());
    for (int k = 0; k < ticks && !kill; ++k) {
        TickInput in;
        in.health = t->mHealth;
        in.hits = k == 0 ? b.hits : 0;
        in.stuck = stuck;
        in.larvae = liveLarvae();
        in.pos = {t->mSRT.t.x, t->mSRT.t.z};
        if (captain) {
            in.captain = true;
            in.captainPos = {captain->getPosition().x, captain->getPosition().z};
        }
        last = b.fsm.tick(in);
        applyOutput(t, b, last, shown, stuck);
        kill = last.kill;
        // A constrained state holds position (hardConstraintOn); a rolling
        // pass moves by the target velocity, integrated here per source tick
        // (the suppressed P1 strategy does not integrate the vehicle).
        if (!last.constrained) {
            t->mSRT.t.x += last.velocity.x * kSourceDelta;
            t->mSRT.t.z += last.velocity.z * kSourceDelta;
            b.anchor = t->mSRT.t;
        }
    }
    b.hits = 0;
    t->mSRT.t.x = b.anchor.x;
    t->mSRT.t.z = b.anchor.z;
    t->mSRT.t.y = groundY(b.anchor.x, b.anchor.z, t->mSRT.t.y);
    t->mVelocity.set(0.0f, 0.0f, 0.0f);
    t->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    t->setDirection(b.fsm.faceDir());
    t->mSRT.s.set(kQueenHostScale, kQueenHostScale, kQueenHostScale);
    if (t->mHealth > 0.0f) t->updateLifeGauge();
    b.logTimer += dt;
    if (b.logTimer >= 1.0f) {
        b.logTimer = 0.0f;
        std::printf("P2_QUEEN_POS generator=%u source_id=%u state=%s anim=%s frame=%.0f x=%.1f z=%.1f home=%.1f,%.1f "
                    "health=%.1f stuck=%d flick_timer=%.1f birth_timer=%.2f room=%d larvae=%d rolling=%d\n",
                    b.generator, b.source, stateName(b.fsm.state()), animName(b.fsm.animator().anim()),
                    b.fsm.animator().frame(), t->mSRT.t.x, t->mSRT.t.z, b.fsm.home().x, b.fsm.home().z, t->mHealth,
                    stuck, b.fsm.flickTimer(), b.fsm.birthTimer(), b.fsm.room() ? 1 : 0, liveLarvae(),
                    b.fsm.rolling() ? 1 : 0);
    }
    std::fflush(stdout);
    if (kill && !b.escaped) {
        // Dead KEYEVENT_END -> kill(): the host death funnel (die + dieSoon)
        // births the LeaveCorpse carcass pellet. dieSoon only runs inside the
        // suppressed doAI, hence pcEscapeNow (Groink/long-legs pattern).
        b.escaped = true;
        std::printf("P2_QUEEN_ESCAPE generator=%u source_id=%u native=host_escape_now\n", b.generator, b.source);
        std::fflush(stdout);
        t->pcEscapeNow();
        becomeCarcass(t, b);
    }
}

// Baby::StateMove target: EnemyFunc::getNearestPikminOrNavi(viewAngle,
// sightRadius) -- nearest searchable Pikmin or live captain in the view cone.
BabyTarget babyTarget(BTeki* t, const Larva& l) {
    BabyTarget best;
    best.dist = sParams.babySightRadius;
    const Vector3f me = t->getPosition();
    const float half = sParams.babyViewAngle * 0.5f * kPi / 180.0f;
    auto consider = [&](Creature* c, bool navi) {
        const Vector3f& p = c->getPosition();
        const float dx = p.x - me.x, dz = p.z - me.z;
        const float d = std::sqrt(dx * dx + dz * dz);
        if (d >= best.dist) return;
        if (std::fabs(p2queenown::angDist(std::atan2(dx, dz), l.fsm.faceDir())) > half) return;
        best.valid = true;
        best.navi = navi;
        best.pos = {p.x, p.z};
        best.dist = d;
    };
    for (Navi* n : pc_p2_navis())
        if (n && n->isAlive()) consider(n, true);
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (p && p->isAlive() && !p->isBuried() && !p->isStickToMouth()) consider(p, false);
        }
    }
    return best;
}

// EnemyFunc::eatPikmin for the larva's single mouth slot (radius 20 at the
// "kamu" joint, approximated 15 ahead of the root: p2queenown::babyMouthReaches).
// Default condition: a Pikmin not already stuck to this larva and not already
// in a mouth. The first Pikmin in reach fills the slot (getMax() == 1).
void larvaEat(BTeki* t, Larva& l) {
    l.mouth = nullptr;
    if (!pikiMgr) return;
    const Vector3f me = t->getPosition();
    const p2queenown::Vec2 pos{me.x, me.z};
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive() || p->getStickObject() == t || p->isStickToMouth()) continue;
        const Vector3f& pp = p->getPosition();
        if (!p2queenown::babyMouthReaches(pos, l.fsm.faceDir(), {pp.x, pp.z}, pp.y - me.y)) continue;
        l.mouth = p;
        std::printf("P2_QUEEN_LARVA_EAT id=%u queen=%u piki_x=%.1f piki_z=%.1f larva_x=%.1f larva_z=%.1f slot_radius=%.0f\n",
                    l.id, l.queen, pp.x, pp.z, me.x, me.z, p2queenown::kBabyMouthRadius);
        return;
    }
    std::printf("P2_QUEEN_LARVA_EAT_NONE id=%u queen=%u larva_x=%.1f larva_z=%.1f\n", l.id, l.queen, me.x, me.z);
}

// Baby StateAttack KEYEVENT_3: swallowPikmin -> InteractKill on what the mouth
// holds. The held Pikmin is a snapshot taken at KEYEVENT_2 (like the Emperor
// eat fix); it is killed wherever it now is, if still alive.
void larvaSwallow(BTeki* t, Larva& l) {
    Piki* p = l.mouth;
    l.mouth = nullptr;
    if (!p) return;
    const bool killed = p->isAlive() && p->stimulate(InteractKill(t, 0));
    if (killed) ++l.eaten;
    std::printf("P2_QUEEN_LARVA_SWALLOW id=%u queen=%u killed=%d total_eaten=%d\n", l.id, l.queen, killed ? 1 : 0, l.eaten);
}

void larvaTick(BTeki* t, Larva& l, float dt) {
    if (t->mStoredDamage > 0.0f) t->makeDamaged();
    if (t->mHealth < l.lastHealth)
        std::printf("P2_QUEEN_LARVA_DAMAGE id=%u queen=%u health=%.1f prior=%.1f hits=%d\n", l.id, l.queen,
                    t->mHealth, l.lastHealth, l.hits);
    l.lastHealth = t->mHealth;
    const int ticks = l.clock.step(double(dt), true);
    bool kill = false;
    for (int k = 0; k < ticks && !kill; ++k) {
        BabyInput in;
        in.health = t->mHealth;
        in.landed = true; // gravity-suppressed vehicle held on the ground below
        in.pos = {t->mSRT.t.x, t->mSRT.t.z};
        in.target = babyTarget(t, l);
        const BabyOutput o = l.fsm.tick(in);
        if (in.target.valid && in.target.navi && in.target.dist < 80.0f && (l.nearTicks++ % 15) == 0)
            std::printf("P2_QUEEN_LARVA_NEAR id=%u queen=%u state=%s captain_dist=%.1f angle_deg=%.1f\n", l.id, l.queen,
                        babyStateName(l.fsm.state()), in.target.dist,
                        p2queenown::angDist(std::atan2(in.target.pos.x - in.pos.x, in.target.pos.z - in.pos.z),
                                            l.fsm.faceDir()) * 180.0f / kPi);
        for (int e : o.entered) {
            std::printf("P2_QUEEN_LARVA_STATE id=%u queen=%u state=%s health=%.1f x=%.1f z=%.1f\n", l.id, l.queen,
                        babyStateName(e), t->mHealth, t->mSRT.t.x, t->mSRT.t.z);
            if ((e == BabyDead || e == BabyPress) && !l.deadLogged) {
                l.deadLogged = true;
                std::printf("P2_QUEEN_LARVA_DEAD id=%u queen=%u cause=%s hits=%d no_corpse=%d\n", l.id, l.queen,
                            e == BabyPress ? "press" : "attack", l.hits, l.standalone ? 0 : 1);
            }
        }
        if (o.attackKey) {
            // Baby StateAttack KEYEVENT_2: attackNavi(attackRadius, hitAngle,
            // attackDamage), then eatPikmin, then AttackFail if the slot is empty.
            const Vector3f me = t->getPosition();
            for (Navi* n : pc_p2_navis()) {
                if (!n || !n->isAlive()) continue;
                const Vector3f& p = n->getPosition();
                const float dx = p.x - me.x, dz = p.z - me.z;
                const float d = std::sqrt(dx * dx + dz * dz);
                if (d > sParams.babyAttackRadius) continue;
                if (std::fabs(p2queenown::angDist(std::atan2(dx, dz), l.fsm.faceDir())) > sParams.babyAttackHitAngle * kPi / 180.0f)
                    continue;
                const float before = n->mHealth;
                const bool ok = n->stimulate(InteractAttack(t, nullptr, sParams.babyAttackDamage, false));
                ++l.bites;
                std::printf("P2_QUEEN_LARVA_BITE id=%u queen=%u accepted=%d damage=%.1f captain_before=%.1f "
                            "captain_after=%.1f\n",
                            l.id, l.queen, ok ? 1 : 0, sParams.babyAttackDamage, before, n->mHealth);
            }
            larvaEat(t, l);
            if (!l.mouth) l.fsm.attackFailed();
        }
        if (o.swallowKey) larvaSwallow(t, l);
        t->mSRT.t.x += o.velocity.x * kSourceDelta;
        t->mSRT.t.z += o.velocity.z * kSourceDelta;
        t->setDirection(o.faceDir);
        kill = o.kill;
    }
    t->mSRT.t.y = groundY(t->mSRT.t.x, t->mSRT.t.z, t->mSRT.t.y);
    t->mVelocity.set(0.0f, 0.0f, 0.0f);
    t->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    t->mSRT.s.set(kLarvaHostScale, kLarvaHostScale, kLarvaHostScale);
    std::fflush(stdout);
    if (kill && !l.escaped && l.standalone) {
        // Standalone larva (#1042): StateDead/StatePress KEYEVENT_END -> kill()
        // (BabyState.cpp:41/80). The source leaves nothing (Baby.cpp:40), and
        // so does the port since #1088: run the host death funnel (die +
        // dieSoon, pcEscapeNow, the Queen pattern); the vehicle corpse is
        // suppressed (pc_p2_no_carcass_corpse_type) and the randomizer check is
        // earned at the kill (pc_p2_no_carcass_forget).
        l.escaped = true;
        std::printf("P2_LARVA_ESCAPE generator=%u source_id=%u id=%u native=host_escape_now carcass=none\n", l.generator,
                    l.source, l.id);
        std::fflush(stdout);
        t->pcEscapeNow();
        return;
    }
    if (kill && !l.escaped) {
        // StateDead/StatePress KEYEVENT_END -> kill(). No carcass (TPI
        // CorpseType override) and no P1 enemy-defeat report: arm the death
        // state and run the host teardown directly (dieSoon -> kill).
        l.escaped = true;
        std::printf("P2_QUEEN_LARVA_KILL id=%u queen=%u\n", l.id, l.queen);
        std::fflush(stdout);
        t->pcTeardownSilently();
    }
}

void spawnLarvae() {
    if (sSpawns.empty()) return;
    std::vector<SpawnReq> pending;
    pending.swap(sSpawns);
    for (const SpawnReq& r : pending) {
        if (!tekiMgr || !tekiMgr->hasType(r.type)) {
            std::printf("P2_QUEEN_LARVA_SPAWN_FAIL queen=%u reason=type_unloaded type=%d\n", r.queen, r.type);
            continue;
        }
        Teki* teki = tekiMgr->newTeki(r.type);
        if (!teki) {
            std::printf("P2_QUEEN_LARVA_SPAWN_FAIL queen=%u reason=pool_full\n", r.queen);
            continue;
        }
        BTeki* bt = static_cast<BTeki*>(teki);
        Larva l;
        l.id = ++sLarvaSerial;
        l.queen = r.queen;
        l.fsm.init(sParams, sBank, r.face, {r.vx, r.vz});
        auto placed = sLarvae.emplace(bt, l);
        TekiPersonality pers;
        pers.mPosition = r.pos;
        pers.mPosition.y = groundY(r.pos.x, r.pos.z, r.pos.y);
        pers.mNestPosition = pers.mPosition;
        pers.mFaceDirection = r.face;
        pers.setF(TekiPersonality::FLT_TerritoryRange, 0.0f);
        teki->mPersonality->input(pers);
        teki->reset();
        teki->startAI(0);
        teki->mSRT.r.set(0.0f, r.face, 0.0f);
        teki->setDirection(r.face);
        teki->mSRT.s.set(kLarvaHostScale, kLarvaHostScale, kLarvaHostScale);
        placed.first->second.lastHealth = teki->mHealth;
        std::printf("P2_QUEEN_LARVA id=%u queen=%u x=%.1f y=%.1f z=%.1f face=%.3f launch=%.1f health=%.1f live=%d "
                    "cap=%d host_type=%d\n",
                    l.id, r.queen, pers.mPosition.x, pers.mPosition.y, pers.mPosition.z, r.face,
                    std::sqrt(r.vx * r.vx + r.vz * r.vz), teki->mHealth, liveLarvae(), kLarvaCap, r.type);
    }
    std::fflush(stdout);
}

// Standalone Bulborb Larva (Baby, 31): a seeded slot rides the Swallow vehicle
// at larva scale and runs the same source Baby FSM as the Queen-born larvae
// (Baby.cpp onInit starts in Born; StateMove has no idle wander outside the
// Piklopedia, Baby.cpp:262-279).
bool bindLarva(BTeki* t, unsigned token, unsigned source) {
    // #1088: no carcass, so the vehicle's corpse type no longer matters (the
    // check is earned at the kill, pc_p2_no_carcass).
    if (s.count(t)) return false;
    Larva l;
    l.id = ++sLarvaSerial;
    l.standalone = true;
    l.generator = token;
    l.source = source;
    l.fsm.init(sParams, sBank, t->getDirection(), {0.0f, 0.0f});
    auto placed = sLarvae.emplace(t, l).first;
    t->mSRT.s.set(kLarvaHostScale, kLarvaHostScale, kLarvaHostScale);
    t->mHealth = sParams.babyHealth;
    placed->second.lastHealth = t->mHealth;
    t->setTekiOption(TEKIOPT_DamageCountable);
    t->setPersonalityF(TekiPersonality::FLT_PelletAppearChance, 0.0f);
    std::printf("P2_LARVA_OWN_BIND generator=%u source_id=%u id=%u host_type=%d health=%.1f retail_parms=%d draw=%s "
                "host_scale=%.2f state=%s\n",
                token, source, l.id, t->mTekiType, t->mHealth, sParams.retail ? 1 : 0,
                sBabyPosesLoaded ? "p2_baby" : "host", kLarvaHostScale, babyStateName(placed->second.fsm.state()));
    pc_randomizer_p2_bind_source(static_cast<PelletView*>(t), source, token);
    std::printf("P2_LARVA_DELIVERY_BIND generator=%u source_id=%u\n", token, source);
    std::fflush(stdout);
    return true;
}

bool bindActor(BTeki* t, unsigned token, unsigned source) {
    if (t->getParameterI(TPI_CorpseType) != TEKICORPSE_LeaveCorpse) {
        std::printf("P2_QUEEN_UNBOUND generator=%u reason=no_corpse type=%d\n", token, t->mTekiType);
        return false;
    }
    Binding bind;
    bind.generator = token;
    bind.source = source;
    auto placed = s.emplace(t, bind);
    Binding& b = placed.first->second;
    Params P = sParams;
    // Larva pool cap (P1 performance): hysteresis scaled to the cap.
    P.maxBirths = kLarvaCap;
    P.minBirths = kLarvaCap / 2;
    const Vector3f pos = t->getPosition();
    // The full (story) variant only: larvae on, no easy first roll. The Hole
    // of Beasts variant (no larvae, fp11 health, easy roll) exists in the FSM
    // init flags, but nothing in the campaign selects it.
    b.fsm.init(P, sBank, true, false, {pos.x, pos.z}, t->getDirection(), (token * 2654435761u) | 1u);
    t->mSRT.s.set(kQueenHostScale, kQueenHostScale, kQueenHostScale);
    t->mHealth = P.health;
    b.lastHealth = b.startHealth = t->mHealth;
    b.anchor = pos;
    t->setTekiOption(TEKIOPT_DamageCountable);
    t->setPersonalityF(TekiPersonality::FLT_PelletAppearChance, 0.0f);
    std::printf("P2_QUEEN_OWN_BIND generator=%u source_id=%u host_type=%d health=%.1f retail_parms=%d draw=%s "
                "host_scale=%.2f centre=%.1f state=%s larva_cap=%d hysteresis=%d/%d variant=full\n",
                token, source, t->mTekiType, t->mHealth, sParams.retail ? 1 : 0, sPosesLoaded ? "p2_model" : "host",
                kQueenHostScale, t->getCentreSize(), stateName(b.fsm.state()), kLarvaCap, P.maxBirths, P.minBirths);
    if (source) {
        pc_randomizer_p2_bind_source(static_cast<PelletView*>(t), source, token);
        std::printf("P2_QUEEN_DELIVERY_BIND generator=%u source_id=%u\n", token, source);
    }
    std::fflush(stdout);
    return true;
}
} // namespace

void pc_p2_queen_teki_reset() {
    const int before = int(s.size() + sLarvae.size());
    s.clear();
    sLarvae.clear();
    sSpawns.clear();
    sDrawLogged.clear();
    sQueenVis.clear();
    sBabyVis.clear();
    sQueenPoseBank.reset();
    sBabyPoseBank.reset();
    for (auto& v : sPoses) v.clear();
    for (auto& v : sBabyPoses) v.clear();
    sPosesLoaded = sBabyPosesLoaded = false;
    sMaterialEnabled = false;
    if (before > 0) {
        std::printf("P2_QUEEN_TEKI_RESET bound_before=%d\n", before);
        std::fflush(stdout);
    }
}

void pc_p2_queen_teki_forget(BTeki* t) {
    if (!t) return;
    auto q = s.find(t);
    if (q != s.end()) {
        std::printf("P2_QUEEN_TEKI_FORGET generator=%u source_id=%u larvae_alive=%d\n", q->second.generator,
                    q->second.source, liveLarvae());
        s.erase(q);
    }
    auto l = sLarvae.find(t);
    if (l != sLarvae.end()) {
        std::printf("P2_QUEEN_LARVA_FORGET id=%u queen=%u\n", l->second.id, l->second.queen);
        sLarvae.erase(l);
    }
    sDrawLogged.erase(t);
    sQueenVis.forget(t);
    sBabyVis.forget(t);
    std::fflush(stdout);
}

bool pc_p2_queen_teki_is_bound(const BTeki* t) {
    return t && (s.count(const_cast<BTeki*>(t)) || sLarvae.count(const_cast<BTeki*>(t)));
}

bool pc_p2_queen_teki_cull_bounds(const BTeki* t, float* radius) {
    if (!t || !radius) return false;
    BTeki* key = const_cast<BTeki*>(t);
    const bool larva = sLarvae.count(key) != 0;
    if (!larva && !s.count(key)) return false;
    *radius = p2queenown::cullRadius(larva);
    static std::set<const BTeki*> logged;
    if (logged.insert(t).second) {
        std::printf("P2_QUEEN_CULL kind=%s cull_radius=%.0f host_radius=%.1f\n", larva ? "larva" : "queen", *radius,
                    key->getBoundingSphereRadius());
        std::fflush(stdout);
    }
    return true;
}

void pc_p2_queen_teki_setup() {
    pc_p2_queen_teki_reset();
    if (!tekiMgr) return;
    const bool bridge = pc_randomizer_p2_bridge();
    if (bridge) {
        const std::set<unsigned> wanted = pc_p2_campaign_ids(30);
        const std::set<unsigned> wantedLarva = pc_p2_campaign_ids(31);
        if (wanted.empty() && wantedLarva.empty()) return;
        loadBank(true);
        int bound = 0, boundLarva = 0;
        Iterator it(tekiMgr);
        CI_LOOP(it) {
            BTeki* t = static_cast<BTeki*>(*it);
            if (!t || !t->mGenerator) continue;
            const unsigned source = pc_p2_campaign_source(t);
            if (source != 30 && source != 31) continue;
            const unsigned token = pc_p2_campaign_token(t);
            if (s.count(t) || sLarvae.count(t)) continue;
            if (source == 30 && bindActor(t, token, 30)) ++bound;
            if (source == 31 && bindLarva(t, token, 31)) ++boundLarva;
        }
        if (!wanted.empty() && !bound) pc_p2_setup_skip(true, "Queen", "no_bindable_actor");
        if (!wantedLarva.empty() && !boundLarva) pc_p2_setup_skip(true, "Baby", "no_bindable_actor");
        return;
    }
    // Room-preview fixture path (never admission evidence).
    if (!pc_pikipelago_room_preview()) return;
    std::ifstream in("p2-queen-teki.txt");
    if (!in) return;
    p2queenteki::Binding cfg{};
    if (!p2queenteki::read(in, cfg)) {
        pc_p2_setup_skip(false, "Queen", "staged_config_invalid");
        return;
    }
    loadBank(false);
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        BTeki* t = static_cast<BTeki*>(*it);
        if (!t || !t->mGenerator || pc_p2_campaign_token(t) != cfg.generator) continue;
        if (t->mTekiType != cfg.type || !s.empty()) {
            pc_p2_setup_skip(false, "Queen", "actor_type_mismatch");
            return;
        }
        bindActor(t, cfg.generator, 0);
    }
}

void pc_p2_queen_teki_frame() { spawnLarvae(); }

void pc_p2_queen_teki_tick(BTeki* t) {
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    auto l = sLarvae.find(t);
    if (l != sLarvae.end()) {
        Larva& lv = l->second;
        if (lv.standalone && lv.escaped) return;
        if (lv.standalone && !lv.escaped && t->mDeadState != 0) {
            // Something outside the FSM called die() (a host hazard): finish
            // the teardown here (no carcass, #1088; the kill earns the check).
            lv.escaped = true;
            std::printf("P2_LARVA_ESCAPE generator=%u source_id=%u id=%u native=host_die_external carcass=none\n",
                        lv.generator, lv.source, lv.id);
            std::fflush(stdout);
            t->pcEscapeNow();
            return;
        }
        if (lv.escaped || t->mDeadState != 0) return;
        if (!(dt > 0.0f && dt < 0.5f)) return;
        larvaTick(t, lv, dt); // may run the host teardown; never touch l after it
        return;
    }
    auto i = s.find(t);
    if (i == s.end()) return;
    Binding& b = i->second;
    if (b.escaped) { becomeCarcass(t, b); return; }
    if (t->mDeadState == 0) {
        if (!(dt > 0.0f && dt < 0.5f)) return;
        ownTick(t, b, dt);
        return;
    }
    // Something outside the FSM called die() (e.g. a host hazard): finish the
    // teardown here or the corpse would never pelletize.
    b.escaped = true;
    std::printf("P2_QUEEN_ESCAPE generator=%u source_id=%u native=host_die_external\n", b.generator, b.source);
    std::fflush(stdout);
    t->pcEscapeNow();
    becomeCarcass(t, b);
}

bool pc_p2_queen_teki_suppress_ai(const BTeki* t) {
    BTeki* key = const_cast<BTeki*>(t);
    auto i = s.find(key);
    if (i != s.end()) return !i->second.escaped;
    auto l = sLarvae.find(key);
    return l != sLarvae.end() && !l->second.escaped;
}

int pc_p2_queen_teki_attack(BTeki* t, Creature* owner, float damage) {
    BTeki* key = t;
    auto i = s.find(key);
    if (i != s.end()) {
        Binding& b = i->second;
        if (b.escaped) return -1;
        // Queen::damageCallBack: only Pikmin hits count (captains, other
        // enemies and part-less hits do nothing).
        // A bomb-rock blast (InteractBomb -> Attack, owner = the bomb) takes
        // the EnemyBase::bombCallBack path in the source: full damage.
        if (owner && owner->mObjType == OBJTYPE_Bomb) {
            t->mStoredDamage += damage;
            ++b.hits;
            ++b.hitsTotal;
            std::printf("P2_QUEEN_BOMB generator=%u source_id=%u damage=%.1f\n", b.generator, b.source, damage);
            return 1;
        }
        if (!owner || !owner->isPiki()) {
            ++b.refusedCaptain;
            if (b.refusedCaptain <= 3 || b.refusedCaptain % 50 == 0)
                std::printf("P2_QUEEN_HIT_REFUSED generator=%u source_id=%u owner=%s count=%d\n", b.generator,
                            b.source, owner && owner->mObjType == OBJTYPE_Navi ? "navi" : "other", b.refusedCaptain);
            return 0;
        }
        const float factor = damageFactor(b.fsm.state());
        t->mStoredDamage += damage * factor;
        t->mDamageCount += 1.0f;
        ++b.hits;
        ++b.hitsTotal;
        return 1;
    }
    auto l = sLarvae.find(key);
    if (l != sLarvae.end()) {
        if (l->second.escaped) return -1;
        // Baby uses the EnemyBase default damageCallBack: every attack counts.
        t->mStoredDamage += damage;
        ++l->second.hits;
        return 1;
    }
    return -1;
}

bool pc_p2_queen_teki_ignore_atari(BTeki* t, Creature* target) {
    auto i = s.find(t);
    if (i == s.end() || !target || i->second.escaped) return false;
    // Queen::ignoreAtari: while rolling, captains and enemies pass through.
    return i->second.fsm.rolling() && (target->mObjType == OBJTYPE_Navi || target->mObjType == OBJTYPE_Teki);
}

int pc_p2_queen_teki_corpse_type(BTeki* t, int fallback) {
    // Every larva leaves nothing (source Baby.cpp:40). Queen-born larvae here;
    // a standalone (seeded, bound) larva also through pc_p2_no_carcass (#1088).
    return sLarvae.count(t) ? int(TEKICORPSE_NoCorpse) : fallback;
}

float pc_p2_queen_teki_corpse_radius(BTeki* t, float fallback) {
    // Pellet::getSize multiplies this by the view scale (the vehicle scale).
    if (s.count(t)) return kQueenCorpseRadius / kQueenHostScale;
    auto l = sLarvae.find(t);
    if (l != sLarvae.end() && l->second.standalone) return kLarvaCorpseRadius / kLarvaHostScale;
    return fallback;
}

// The live draw matrix carries the vehicle scale (mSRT.s) and the carcass
// pellet matrix carries the pellet's own; both are camera * world, and the
// camera part is a pure rotation, so the world scale is the column length.
// Normalise it away: the P2 model is drawn at source scale 1.
static void sourceScale(const Matrix4f& matrix, Matrix4f& view) {
    Vector3f c0, c1, c2;
    matrix.getColumn(0, c0);
    matrix.getColumn(1, c1);
    matrix.getColumn(2, c2);
    const float sx = c0.length(), sy = c1.length(), sz = c2.length();
    Matrix4f unscale;
    unscale.makeSRT(Vector3f(sx > 1e-6f ? 1.0f / sx : 1.0f, sy > 1e-6f ? 1.0f / sy : 1.0f, sz > 1e-6f ? 1.0f / sz : 1.0f),
                    Vector3f(0.0f, 0.0f, 0.0f), Vector3f(0.0f, 0.0f, 0.0f));
    const_cast<Matrix4f&>(matrix).multiplyTo(unscale, view);
}

bool pc_p2_queen_teki_draw(BTeki* t, Graphics& gfx, const Matrix4f& matrix, bool corpse) {
    if (!gfx.mCamera) return false;
    auto l = sLarvae.find(t);
    if (l != sLarvae.end()) {
        if (!sBabyPosesLoaded) return false;
        int anim = l->second.fsm.animator().anim();
        if (anim < 0 || anim >= BabyAnimCount || sBabyPoses[anim].empty()) anim = BabyAnimMove;
        const auto& poses = sBank.baby[anim].poses;
        const float frame = l->second.fsm.animator().frame();
        std::size_t best = 0;
        for (std::size_t k = 1; k < poses.size() && k < sBabyPoses[anim].size(); ++k)
            if (std::fabs(float(poses[k]) - frame) < std::fabs(float(poses[best]) - frame)) best = k;
        Matrix4f view;
        sourceScale(matrix, view);
        Shape* shape = sBabyPoses[anim][best];
        {   // #972: lerp + crossfade into a private Shape; nearest pose stays the fallback.
            const auto& clip = sBank.baby[anim];
            const float duration = float(clip.frames > 1 ? clip.frames : 2);
            const float drawFrame = std::isfinite(frame) ? std::max(0.0f, std::min(duration - 1.0f, frame)) : 0.0f;
            if (Shape* smooth = sBabyVis.draw(t, sBabyPoseBank, clip.name, drawFrame, l->second.id)) shape = smooth;
        }
        shape->updateAnim(gfx, view, nullptr, t);
        shape->drawshape(gfx, *gfx.mCamera, nullptr);
        int& logged = sDrawLogged[t];
        if (!logged) {
            logged = 1;
            std::printf("P2_QUEEN_LARVA_DRAW id=%u clip=%s pose=%zu model=p2_baby\n", l->second.id,
                        sBank.baby[anim].name.c_str(), best);
        }
        return true;
    }
    auto i = s.find(t);
    if (i == s.end() || !sPosesLoaded) return false;
    Binding& b = i->second;
    const bool dead = corpse || b.escaped || t->mDeadState != 0;
    int anim = b.fsm.animator().anim();
    float frame = b.fsm.animator().frame();
    bool last = false;
    if (dead && sParams.carcassCarryDegenerate && sParams.carcassDeadPose >= 0
        && sParams.carcassDeadPose < int(sPoses[AnimDead].size())) {
        // Staged carry poses collapse (see pikmin2_queen_stage.carcass_pose_rows).
        anim = AnimDead;
        frame = float(sBank.clip[AnimDead].poses[std::size_t(sParams.carcassDeadPose)]);
    } else if (dead) {
        if (!sPoses[AnimCarry].empty()) {
            anim = AnimCarry;
            // Carry clip loops 10..29 while the carcass is hauled.
            frame = 10.0f + std::fmod(float(SDL_GetTicks()) * 0.03f, 19.0f);
        } else {
            anim = AnimDead;
            last = true;
        }
    }
    if (anim < 0 || anim >= AnimCount || sPoses[anim].empty()) {
        anim = AnimWait;
        frame = 0.0f;
    }
    const auto& poses = sBank.clip[anim].poses;
    std::size_t best = last ? sPoses[anim].size() - 1 : 0;
    if (!last)
        for (std::size_t k = 1; k < poses.size() && k < sPoses[anim].size(); ++k)
            if (std::fabs(float(poses[k]) - frame) < std::fabs(float(poses[best]) - frame)) best = k;
    Matrix4f view;
    sourceScale(matrix, view);
    Shape* shape = sPoses[anim][best];
    // #972: lerp + crossfade into a private Shape; nearest pose stays the fallback.
    // The fixed carcass pose (degenerate carry) is a deliberate single pose: no blend.
    if (!(dead && sParams.carcassCarryDegenerate && sParams.carcassDeadPose >= 0)) {
        const auto& clip = sBank.clip[anim];
        const float duration = float(clip.frames > 1 ? clip.frames : 2);
        const float drawFrame = last ? duration - 1.0f
                                     : (std::isfinite(frame) ? std::max(0.0f, std::min(duration - 1.0f, frame)) : 0.0f);
        if (Shape* smooth = sQueenVis.draw(t, sQueenPoseBank, clip.name, drawFrame, b.generator)) shape = smooth;
    }
    shape->updateAnim(gfx, view, nullptr, t);
    bool drawn = false;
    if (sMaterialEnabled && !dead) {
        if (!gameflow.mPauseAll) sMaterialFrame = std::fmod(sMaterialFrame + 1.0f, float(sMaterial.duration));
        p2material::Sample sample;
        drawn = p2material::sample(sMaterial, 0, sMaterialFrame, sample) && p2material::drawSpecular(*shape, gfx, 1, 1, sample);
    }
    if (!drawn) {
        pc_gfx_specular_family_scope(1);
        shape->drawshape(gfx, *gfx.mCamera, nullptr);
        pc_gfx_specular_family_scope(0);
    }
    int& logged = sDrawLogged[t];
    const int bit = dead ? 2 : 1;
    if (!(logged & bit)) {
        logged |= bit;
        std::printf("P2_QUEEN_DRAW generator=%u source_id=%u corpse=%d clip=%s pose=%zu model=p2_queen specular=%d\n",
                    b.generator, b.source, dead ? 1 : 0, sBank.clip[anim].name.c_str(), best,
                    sMaterialEnabled && !dead ? 1 : 0);
        std::fflush(stdout);
    }
    return true;
}

bool pc_p2_queen_teki_probe(const BTeki* t, int* state, float* faceDir, float* homeX, float* homeZ) {
    auto i = s.find(const_cast<BTeki*>(t));
    if (i == s.end() || i->second.escaped) return false;
    if (state) *state = i->second.fsm.state();
    if (faceDir) *faceDir = i->second.fsm.faceDir();
    if (homeX) *homeX = i->second.fsm.home().x;
    if (homeZ) *homeZ = i->second.fsm.home().z;
    return true;
}

bool pc_p2_queen_teki_dead_key_seen() {
    for (const auto& kv : s)
        if (kv.second.deadLogged) return true;
    return false;
}
unsigned long pc_p2_queen_teki_behavior_tick() { return 0; }
int pc_p2_queen_teki_attached_count(const BTeki* t) {
    return s.count(const_cast<BTeki*>(t)) ? stuckCount(const_cast<BTeki*>(t)) : -1;
}

float pc_p2_queen_teki_param_f(const BTeki* actor, int idx, float fallback) {
    BTeki* key = const_cast<BTeki*>(actor);
    const bool queen = s.count(key) != 0;
    const bool larva = !queen && sLarvae.count(key) != 0;
    if (!queen && !larva) return fallback;
    switch (idx) {
    case TPF_Life:
        return queen ? s.find(key)->second.fsm.params().health : sParams.babyHealth;
    case TPF_Scale:
        return queen ? kQueenHostScale : kLarvaHostScale;
    case TPF_LifeRecoverRate:
    case TPF_VisibleRange:
    case TPF_VisibleAngle:
    case TPF_AttackableRange:
    case TPF_AttackableAngle:
    case TPF_AttackRange:
    case TPF_AttackHitRange:
    case TPF_AttackPower:
    case TPF_DangerTerritoryRange:
    case TPF_SafetyTerritoryRange:
        return 0.0f;
    default:
        return fallback;
    }
}

bool pc_p2_queen_teki_receipt(PelletView* view, unsigned& generator) {
    if (!view) return false;
    auto i = s.find(static_cast<BTeki*>(view));
    if (i == s.end()) return false;
    generator = i->second.generator;
    return true;
}

const char* pc_p2_queen_teki_name(PelletView* view) {
    if (!view) return nullptr;
    return s.count(static_cast<BTeki*>(view)) ? "Empress Bulblax" : nullptr;
}
