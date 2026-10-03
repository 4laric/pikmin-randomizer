// UmiMushi (Toady Bloyster, EnemyID 71) source behavior on the P1 TEKI_Chappy
// placement vehicle. UmiMushi ships a dedicated shared FSM (UmiMushiState.cpp,
// registered by FSM::init at umiMushiState.cpp:18) that both the ordinary
// Bloyster (71) and Blind Bloyster (101) use through one UmiMushi::Mgr. This
// port implements the observable ordinary-Bloyster states on the host:
//   Walk 1 (onInit start) -> Wait 0 -> Find 2 -> Search 3 -> Turn 4 ->
//   Flick 5 -> Attack 6 -> Eat 7, Dead 8, Lost 9.
// Attack is driven by the source animation key events: event 3 (attack1 frame
// 39) raises the tongue and eatPikmin captures, event 5 (frame 50) attacks
// Navis in the mouth slots, event 6 (frame 66) flicks nearby Pikmin/Navis; the
// Eat state swallows at the eat1 animation end. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_aquatic_assets.py (GPVE01 rev 0, UmiMushi DISC_PARMS).
//
// Port adaptations (recorded, not retail-faithful):
//   * Tongue (#886): the source seven-slot tongue (kamu_joint1..7, r=30,
//     Blind 25) eats through pc_p2_captor_mouth.h every tick from attack key
//     event 3 until key event 6 (EnemyFunc::eatPikmin, umiMushiState.cpp:
//     510-514); a caught Pikmin is stuck to the P1 host 'slot' part
//     (pc_p2_captor_host.h) so it cannot be whistled away. Eat swallows at
//     the eat1 end only Pikmin still held (swallowPikmin, white poison proper
//     fp11 = 200). The slot positions are a documented port approximation
//     (seven points on the facing axis out to fp22 = 170, halved for Blind).
//     Death and teardown release the tongue; the port's own flick sweeps
//     spare held Pikmin (a source flick refuses a swallowed Pikmin).
//   * No P2 water box (mWaterBox, Hamon sea height, dive/splash) is present on
//     the host; the source outMove/dry fallback and water presentation are
//     bounded gaps.
//   * The shared UmiMushi::Mgr base (100) exclusion remains a bounded gap.
//     Blind (101) is now ported on the same shared FSM: half scale, proper
//     fp12=800 health, Parms::mBlindTurnRateReduction 0.3 on turnFunc, no Navi
//     retargeting (isChangeNavi false) and the Walk move/wait frame cycle
//     (fp14/fp13, disc 200/200). The actors config marks it `UmiMushiBlind`.
//   * The mid-boss BGM phase staging, eye/weak joint callbacks and the
//     umimusi_model1.btk material animation are P2-only and not reproduced.
//   * Target selection uses the single active Navi; the two-player nearest-Navi
//     branch and the mouth-slot geometry test are port approximations. The
//     source view-angle gate is treated as a full hemisphere in target search.
//   * The walk weave (mWalkAngleSpeed, mRotateAngleDelta) and turn-to-target
//     clamp use the header proper values; Wait reuses srun1 as the source does.
// Every hook is a no-op for unregistered actors; no other lane's module is
// modified.
#include "pc_p2_umimushi.h"
#include "pc_p2_umimushi_policy.h"
#include "pc_p2_skewer.h"
#include "pc_p2_skewer_cam.h"
#include "pc_p2_captor_host.h"
#include "Collision.h"
#include "CreatureCollPart.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_randomizer.h"
#include "teki.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiState.h"
#include "gl/pc_gfx.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "pc_p2_navi_select.h"
#include "Generator.h"
#include "gameflow.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <vector>

extern Matrix4f invCamMat; // collInfo.cpp: camera inverse used by CollPart::getMatrix

namespace {
enum State {
    UMI_NULL = -1,
    UMI_WAIT = 0,
    UMI_WALK = 1,
    UMI_FIND = 2,
    UMI_SEARCH = 3,
    UMI_TURN = 4,
    UMI_FLICK = 5,
    UMI_ATTACK = 6,
    UMI_EAT = 7,
    UMI_DEAD = 8,
    UMI_LOST = 9,
};

const char* stateName(State s) {
    switch (s) {
    case UMI_WAIT: return "wait";
    case UMI_WALK: return "walk";
    case UMI_FIND: return "find";
    case UMI_SEARCH: return "search";
    case UMI_TURN: return "turn";
    case UMI_FLICK: return "flick";
    case UMI_ATTACK: return "attack";
    case UMI_EAT: return "eat";
    case UMI_DEAD: return "dead";
    case UMI_LOST: return "lost";
    default: return "null";
    }
}

// Source enemyparm.txt retail values (aquatic manifest, UmiMushi general and
// proper DISC_PARMS; header defaults where the disc omits a key).
constexpr float LIFE = 1500.0f;            // general fp00
constexpr float MOVE_SPEED = 15.0f;        // general fp06
constexpr float SEARCH_SPEED = 85.0f;      // proper fp04 search move speed
constexpr float TERRITORY = 300.0f;        // general fp09
constexpr float HOME_RADIUS = 30.0f;       // general fp10
constexpr float SIGHT = 700.0f;            // general fp12 sight radius
constexpr float SEARCH_DISTANCE = 200.0f;  // general fp14 default
constexpr float SEARCH_ANGLE = 2.0943951f; // general fp15 default 120 deg
constexpr float ATTACK_RANGE = 30.0f;      // general fp20 max attack range
constexpr float ATTACK_HIT = 170.0f;       // general fp22 attack hit radius
constexpr float ATTACK_HIT_ANGLE = 0.52359878f; // general fp23 retail 30 deg
constexpr float ATTACK_DAMAGE = 10.0f;     // general fp24
// Shake-off values are the retail general fp16..fp19 (p2umi::Shake*): chance 1.0, knockback 120,
// damage 1.0, range 90. isStartFlick is the source timer/stuck-tier test (p2umi::isStartFlick).
constexpr float TURN_START_ANGLE = 0.52359878f; // proper fp02 30 deg
constexpr float TURN_END_ANGLE = 0.17453293f;   // proper fp03 10 deg
constexpr float ROTATE_RATE = 0.05f;       // proper fp06
constexpr float ROTATE_MAX = 0.04363323f;  // proper fp07 2.5 deg
constexpr float GENERAL_TURN_RATE = 0.1f;  // general fp08 default
constexpr float GENERAL_MAX_TURN = 0.17453293f; // general fp28 default 10 deg
constexpr float WALK_ANGLE_SPEED = 10.0f;  // Parms mWalkAngleSpeed
constexpr float ROTATE_ANGLE_DELTA = 0.05f; // Parms mRotateAngleDelta
constexpr float WAIT_TIME = 0.25f;         // port value (source ip01 = 0)
// Blind (EnemyID_UmiMushiBlind, 101) shared-FSM parameter split from
// umiMushi.cpp: Obj::setParameters applies scale 0.5 and a 50.0 floor offset;
// onInit overwrites health with proper fp12 (disc 800); Parms::
// mBlindTurnRateReduction 0.3 scales turnFunc's rotate speed and max; the Walk
// state alternates fp14 move frames and fp13 wait frames (disc 200/200).
constexpr float BLIND_LIFE = 800.0f;       // proper fp12 mBlindHealth
constexpr float BLIND_SCALE = 0.5f;        // setParameters scale
constexpr float BLIND_TURN_RATE = 0.3f;    // Parms mBlindTurnRateReduction
constexpr float BLIND_WAIT_FRAMES = 200.0f; // proper fp13 mBlindWaitTime
constexpr float BLIND_MOVE_FRAMES = 200.0f; // proper fp14 mBlindMoveTime
constexpr float FRAME_RATE = 30.0f;        // source counter tick rate
constexpr float PI_F = 3.14159265f;
constexpr float TAU_F = 6.28318531f;

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events; // source frame -> event code
};

struct Umi {
    State state = UMI_WALK;
    State nextState = UMI_NULL;
    float stateTime = 0.0f;
    float heading = 0.0f;
    float prevHeading = 0.0f;
    float walkRotateAngle = 0.0f;
    Vector3f home;
    Vector3f goal;
    Navi* targetNavi = nullptr;
    p2captor::Held<Piki> held; // Pikmin on the tongue slots (validated against the host stick)
    bool tongueActive = false; // source StateAttack mIsTongueActive
    bool tongueHasPiki = false;
    bool mouthLogged = false;
    std::set<int> firedEvents;
    std::string clip = "run1";
    float phase = 0.0f;
    bool deadLogged = false;
    float logTimer = 0.0f;
    // Blind (101) shared-FSM split. sourceId is 71 or 101; blind actors use
    // half scale, fp12 health, a reduced turn rate and the Walk wait/move cycle.
    bool blind = false;
    int sourceId = 71;
    bool blindWaiting = false;
    float blindWaitTimer = 0.0f;
    float blindMoveTimer = 0.0f;
    bool escaped = false;
    float lastHealth = 0.0f;
    // #995: source mFlickTimer (addDamage flickSpeed 1.0 per accepted hit) and hit census.
    float flickTimer = 0.0f;
    int hitsStuck = 0, hitsPartless = 0, hitsRefused = 0;
    // #995: own collision tree (root/head/kuti/ketu/weak + 'slot' with seven 'kamN' children).
    struct Coll {
        CollInfo* own = nullptr;
        CollInfo* host = nullptr;
        CollPart* node[p2umitables::kNodeCount] = {};
        CollPart* slot = nullptr;
        CollPart* kam[p2umitables::kKamuCount] = {};
        bool released = false;
    } coll;
    float scale = 1.0f;
    int latchedLogged = -1;
    bool holdLogged = false;
    // TEST-ONLY evidence probe (PIKMIN_P2_UMIMUSHI_PROBE), never active in a normal run.
    float probeTime = 0.0f;
    bool probeBait = false;
    bool probeCaptain = false;
    int probeThrows = 0;
    float probeNextThrow = 0.0f;
    Piki* probeThrown[8] = {};
    float probeThrownAt[8] = {};
    bool probeLanded[8] = {};
    bool probeMid[8] = {};
};

std::map<PelletView*, Umi> actors;
std::map<PelletView*, unsigned> corpses; // dead-actor delivery registry
std::map<std::string, Clip> clips;
bool ready = false;

float wrapPi(float a) {
    while (a > PI_F) a -= TAU_F;
    while (a < -PI_F) a += TAU_F;
    return a;
}
float degToRad(float d) { return d * PI_F / 180.0f; }
float distXZ(const Vector3f& a, const Vector3f& b) {
    const float dx = a.x - b.x, dz = a.z - b.z;
    return std::sqrt(dx * dx + dz * dz);
}
float clipDuration(const std::string& name) {
    auto it = clips.find(name);
    return it == clips.end() ? 1.0f : it->second.duration;
}
bool clipLoops(const std::string& name) {
    auto it = clips.find(name);
    return it != clips.end() && it->second.loop;
}

// Source isChangeNavi (umiMushi.cpp:849-853): getActiveNavi, or the nearest
// captain in two-player mode. Searches and area effects walk every captain.
Navi* activeNavi(const Vector3f& pos) {
    if (!naviMgr) return nullptr;
    Navi* n = pc_p2_source_active_navi(pos);
    return (n && n->isAlive()) ? n : nullptr;
}
Navi* nearestNavi(const Vector3f& pos) {
    if (!naviMgr) return nullptr;
    Navi* n = pc_p2_nearest_navi(pos);
    return (n && n->isAlive()) ? n : nullptr;
}
Piki* nearestPiki(const Vector3f& pos, float radius) {
    Piki* best = nullptr;
    float bestSq = radius * radius;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            // A Pikmin held on a tongue is neither a target nor a flick trigger (#886).
            if (!p || !p->isAlive() || p->isStickToMouth()) continue;
            const Vector3f q = p->getPosition();
            const float dx = q.x - pos.x, dz = q.z - pos.z;
            const float d = dx * dx + dz * dz;
            if (d < bestSq) { bestSq = d; best = p; }
        }
    }
    return best;
}
Piki* nearestPikiAngle(const Vector3f& pos, float heading, float radius, float angle) {
    Piki* best = nullptr;
    float bestSq = radius * radius;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive() || p->isStickToMouth()) continue;
            const Vector3f q = p->getPosition();
            const float dx = q.x - pos.x, dz = q.z - pos.z;
            const float d = dx * dx + dz * dz;
            if (d >= bestSq) continue;
            if (!p2umi::withinCone(p2captorhost::vec(pos), heading, p2captorhost::vec(q), radius, angle)) continue;
            bestSq = d; best = p;
        }
    }
    return best;
}
// Probe screenshot (PIKMIN_P2_PROXY_SHOT=<dir>, one BMP per key, taken 30 presented frames later).
void shot(const Umi& s, const char* what) {
    char key[64];
    std::snprintf(key, sizeof(key), "x|umi%s_%s", s.blind ? "blind" : "", what);
    pc_gfx_proxy_shot_notify_after(key, 4); // the moment of the event, not the default 30-frame delay
}

int stuckToBody(BTeki* a) {
    // Source mStuckPikminCount tier input: Pikmin stuck to the body, not held in the mouth.
    return p2captorhost::pikiStickerCount(a) - p2captorhost::mouthStickerCount(a);
}
// Source EnemyFunc::isStartFlick(this, false): the flick timer (1.0 per accepted hit) against the
// shake-off tier of the stuck-Pikmin count (#995; the old rule was a 20-unit proximity test).
bool isStartFlick(BTeki* a, const Umi& s) {
    return p2umi::isStartFlick(s.flickTimer, stuckToBody(a));
}
void logHit(BTeki* a, const Umi& s, unsigned generator, const char* kind, const Vector3f& at, int slot) {
    const p2umi::Polar pl = p2umi::polar(p2captorhost::vec(a->getPosition()), s.heading, p2captorhost::vec(at));
    std::printf("P2_UMIMUSHI_HIT generator=%u source_id=%d kind=%s angle_deg=%.1f dist_xz=%.1f slot=%d\n",
                generator, s.sourceId, kind, double(pl.angleDeg), double(pl.distXZ), slot);
    std::fflush(stdout);
}
// Source StateFlick key 2 / StateAttack key 6: flickNearbyPikmin (3D < fp19, not stuck to this
// body, not in a mouth), flickStickPikmin (fp16 chance, angle facing + pi, every Pikmin stuck to
// this body) and flickNearbyNavi, all with fp17 knockback and fp18 damage; then mFlickTimer = 0.
int doFlick(BTeki* a, Umi& s, unsigned generator, int frame, const char* event, bool logEmpty) {
    const p2chappymouth::Vec3 apos = p2captorhost::vec(a->getPosition());
    std::vector<Piki*> nearby, stuck;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive() || p->isStickToMouth()) continue; // a mouth-held Pikmin is never flicked
            if (p->getStickObject() == a) stuck.push_back(p);
            else if (p2chappymouth::distance(p2captorhost::vec(p->getPosition()), apos) < p2umi::shakeRange(s.scale))
                nearby.push_back(p);
        }
    }
    int nearHit = 0, stuckHit = 0, naviHit = 0;
    for (Piki* p : nearby) {
        if (p->isAlive()
                && p->stimulate(InteractFlick(a, p2umi::ShakeKnockback, p2umi::ShakeDamage, FLICK_BACKWARDS_ANGLE))) {
            ++nearHit;
            logHit(a, s, generator, "flick_near", p->getPosition(), -1);
        }
    }
    const float stuckAngle = p2umi::flickStuckAngle(s.heading);
    for (Piki* p : stuck) {
        if (!p->isAlive() || p->getStickObject() != a || p->isStickToMouth()) continue;
        if (p->stimulate(InteractFlick(a, p2umi::ShakeKnockback, p2umi::ShakeDamage, stuckAngle))) {
            ++stuckHit;
            logHit(a, s, generator, "flick_stuck", p->getPosition(), -1);
        }
    }
    for (Navi* n : pc_p2_navis()) {
        if (!n->isAlive()) continue;
        if (p2chappymouth::distance(p2captorhost::vec(n->getPosition()), apos) >= p2umi::shakeRange(s.scale)) continue;
        if (n->stimulate(InteractFlick(a, p2umi::ShakeKnockback, p2umi::ShakeDamage, FLICK_BACKWARDS_ANGLE))) {
            ++naviHit;
            logHit(a, s, generator, "flick_navi", n->getPosition(), -1);
        }
    }
    const float before = s.flickTimer;
    s.flickTimer = 0.0f;
    if (logEmpty || nearHit + stuckHit + naviHit > 0) {
        std::printf("P2_UMIMUSHI_FLICK generator=%u frame=%d pikmin=%d near=%d stuck=%d navi=%d event=%s "
                    "flick_timer_before=%.2f\n", generator, frame, nearHit + stuckHit, nearHit, stuckHit,
                    naviHit, event, double(before));
        std::fflush(stdout);
    }
    return nearHit + stuckHit;
}
void stop(BTeki* a) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
}
float turnToTarget(BTeki* a, Umi& s, const Vector3f& target, float accel, float maxAngle) {
    const Vector3f pos = a->getPosition();
    const float desired = std::atan2(target.x - pos.x, target.z - pos.z);
    const float diff = wrapPi(desired - s.heading);
    float delta = diff * accel;
    if (delta > maxAngle) delta = maxAngle;
    if (delta < -maxAngle) delta = -maxAngle;
    s.heading = wrapPi(s.heading + delta);
    a->setDirection(s.heading);
    return std::fabs(wrapPi(desired - s.heading));
}
void walkFunc(BTeki* a, Umi& s) {
    s.walkRotateAngle += ROTATE_ANGLE_DELTA;
    if (s.walkRotateAngle > TAU_F) s.walkRotateAngle -= TAU_F;
    const float rotationDelta = WALK_ANGLE_SPEED * std::sin(s.walkRotateAngle);
    s.prevHeading = s.heading;
    turnToTarget(a, s, s.goal, GENERAL_TURN_RATE, GENERAL_MAX_TURN);
    s.heading = wrapPi(s.heading + degToRad(rotationDelta));
    a->setDirection(s.heading);
    const Vector3f drive(std::sin(s.heading) * MOVE_SPEED, 0.0f,
                         std::cos(s.heading) * MOVE_SPEED);
    a->inputDrive(drive);
    a->mVelocity.set(drive);
}
void searchMove(BTeki* a, Umi& s) {
    const Vector3f drive(std::sin(s.heading) * SEARCH_SPEED, 0.0f,
                         std::cos(s.heading) * SEARCH_SPEED);
    a->inputDrive(drive);
    a->mVelocity.set(drive);
}
bool isOutOfTerritory(const Umi& s, const Vector3f& pos, float scale) {
    return distXZ(s.home, pos) > TERRITORY * scale;
}
void setNextGoal(Umi& s) {
    const float angle = gsys->getRand(TAU_F);
    s.goal = Vector3f(s.home.x + TERRITORY * std::sin(angle), s.home.y,
                      s.home.z + TERRITORY * std::cos(angle));
}
bool canMove(BTeki* a, Umi& s) {
    if (isOutOfTerritory(s, a->getPosition(), 1.0f) && s.targetNavi) {
        if (distXZ(s.home, s.targetNavi->getPosition()) > TERRITORY) {
            stop(a);
            return false;
        }
    }
    return true;
}
void outMove(BTeki* a, Umi& s) {
    if (!s.targetNavi) { stop(a); return; }
    const Vector3f navi = s.targetNavi->getPosition();
    float dx = navi.x - s.home.x, dz = navi.z - s.home.z;
    const float len = std::sqrt(dx * dx + dz * dz);
    if (len < 1e-3f) { stop(a); return; }
    dx /= len; dz /= len;
    const Vector3f target(s.home.x + dx * TERRITORY * 1.5f, s.home.y,
                          s.home.z + dz * TERRITORY * 1.5f);
    turnToTarget(a, s, target, ROTATE_RATE, ROTATE_MAX);
    const Vector3f drive(dx * SEARCH_SPEED * 0.5f, 0.0f, dz * SEARCH_SPEED * 0.5f);
    a->inputDrive(drive);
    a->mVelocity.set(drive);
}
bool isChangeNavi(BTeki* a, Umi& s) {
    // Source umiMushi.cpp:843: Blind never retargets a Navi (returns false).
    if (s.blind) return false;
    const Vector3f pos = a->getPosition();
    Navi* navi = activeNavi(pos);
    if (!navi) return false;
    float dist = SEARCH_DISTANCE;
    if (s.targetNavi) dist *= 1.2f;
    dist *= dist;
    const Vector3f q = navi->getPosition();
    const float dx = q.x - pos.x, dz = q.z - pos.z;
    if (dx * dx + dz * dz < dist) {
        if (s.targetNavi != navi) {
            s.targetNavi = navi;
            s.goal = navi->getPosition();
            return true;
        }
        return false;
    }
    if (s.targetNavi) {
        s.targetNavi = nullptr;
        s.goal = s.home;
        return true;
    }
    return false;
}
bool isFindTarget(BTeki* a, Umi& s) {
    const Vector3f pos = a->getPosition();
    if (s.targetNavi && s.targetNavi->isAlive()) {
        if (distXZ(s.targetNavi->getPosition(), pos) < SEARCH_DISTANCE) {
            s.goal = s.targetNavi->getPosition();
            return true;
        }
    }
    Navi* navi = nearestNavi(pos); // source getNearestNavi (umiMushi.cpp:916)
    if (navi && distXZ(navi->getPosition(), pos) < SEARCH_DISTANCE) {
        s.goal = navi->getPosition();
        return true;
    }
    Piki* piki = nearestPikiAngle(pos, s.heading, SEARCH_DISTANCE, SEARCH_ANGLE);
    if (piki) {
        s.goal = piki->getPosition();
        return true;
    }
    return false;
}
bool isAttackStart(BTeki* a, Umi& s) {
    const Vector3f pos = a->getPosition();
    if (s.targetNavi && s.targetNavi->isAlive()) {
        const Vector3f q = s.targetNavi->getPosition();
        if (std::fabs(wrapPi(std::atan2(q.x - pos.x, q.z - pos.z) - s.heading))
                <= ATTACK_HIT_ANGLE
                && distXZ(q, pos) < ATTACK_HIT) {
            s.goal = q;
            return true;
        }
    }
    // Source umiMushi.cpp:1233: only a Pikmin inside the fp23 (30 deg) cone ahead and the fp22
    // radius starts the attack (#995: the old radius-only fallback started bites at Pikmin beside or
    // behind the body, where the tongue can never reach them).
    Piki* piki = nearestPikiAngle(pos, s.heading, ATTACK_HIT, ATTACK_HIT_ANGLE);
    if (piki) {
        s.goal = piki->getPosition();
        return true;
    }
    // Blind never stores targetNavi (isChangeNavi returns false), but the
    // source explicitly queries nearby captains here after the Pikmin path.
    // Attack key 5 still evaluates all live captains against the tongue slots;
    // this acquisition does not turn Blind into a captain-chasing Ranging.
    Navi* navi = p2umi::blindAttackNavi<Navi>(s.blind, pc_p2_navis(), p2captorhost::vec(pos),
        s.heading, ATTACK_HIT, ATTACK_HIT_ANGLE,
        [](Navi* n) { return n->isAlive() && n->isVisible() && !n->isStickToMouth(); },
        [](Navi* n) { return p2captorhost::vec(n->getPosition()); });
    if (navi) {
        s.goal = navi->getPosition();
        return true;
    }
    return false;
}
bool isNeedTurn(BTeki* a, Umi& s) {
    const Vector3f pos = a->getPosition();
    if (std::fabs(wrapPi(std::atan2(s.goal.x - pos.x, s.goal.z - pos.z) - s.heading))
            > TURN_START_ANGLE) {
        return true;
    }
    if (s.targetNavi) {
        const Vector3f q = s.targetNavi->getPosition();
        if (std::fabs(wrapPi(std::atan2(q.x - pos.x, q.z - pos.z) - s.heading))
                > TURN_START_ANGLE) {
            return true;
        }
    }
    return false;
}
float turnFunc(BTeki* a, Umi& s) {
    if (s.targetNavi) s.goal = s.targetNavi->getPosition();
    // Source umiMushi.cpp:820-825 scales both the search rotation rate and its
    // max by Parms::mBlindTurnRateReduction (0.3) for Blind.
    const float factor = s.blind ? BLIND_TURN_RATE : 1.0f;
    return turnToTarget(a, s, s.goal, ROTATE_RATE * factor, ROTATE_MAX * factor);
}

void enter(Umi& s, State state, const char* clip) {
    s.state = state;
    s.nextState = UMI_NULL;
    s.stateTime = 0.0f;
    s.firedEvents.clear();
    s.holdLogged = false;
    if (clip) s.clip = clip;
    // Source StateWalk::init resets both Blind pace counters and starts moving.
    if (state == UMI_WALK) {
        s.blindWaiting = false;
        s.blindWaitTimer = 0.0f;
        s.blindMoveTimer = 0.0f;
    }
}
const char* clipForState(State st) {
    switch (st) {
    case UMI_WAIT: return "srun1";
    case UMI_WALK: return "run1";
    case UMI_FIND: return "fsearch1";
    case UMI_SEARCH: return "srun1";
    case UMI_TURN: return "sturn1";
    case UMI_FLICK: return "flick1";
    case UMI_ATTACK: return "attack1";
    case UMI_EAT: return "eat1";
    case UMI_DEAD: return "dead1";
    case UMI_LOST: return "outview1";
    default: return "srun1";
    }
}
void setState(BTeki* a, Umi& s, State state, const char* clip) {
    enter(s, state, clip);
    const unsigned generator = a->mGenerator ? pc_p2_campaign_token(a) : 0u;
    std::printf("P2_UMIMUSHI_STATE generator=%u state=%s\n", generator, stateName(state));
    std::fflush(stdout);
}

const p2captor::Geometry& mouthGeometry(const Umi& s) {
    return *p2captor::geometryFor(s.blind ? 101u : 71u);
}
float phaseOf(const Umi& s) {
    const float duration = clipDuration(s.clip);
    const float len = duration > 0.0f ? duration : 1.0f;
    float phase = s.stateTime / len;
    if (clipLoops(s.clip)) phase -= std::floor(phase);
    else if (phase > 1.0f) phase = 1.0f;
    return phase;
}
// Source frame of the drawn clip: the same phase * (frames - 1) the pose draw uses.
float drawFrame(const Umi& s) {
    const int clip = p2umi::clipIndex(s.clip.c_str());
    const int frames = p2umi::clipFrames(clip);
    return frames > 1 ? phaseOf(s) * float(frames - 1) : 0.0f;
}
// World positions of the seven mouth slots (kamu_joint1..7, source initMouthSlots). attack1 and eat1
// carry every frame of the tongue; any other clip has no tongue table, so the slots rest on the mouth.
void slotPositions(BTeki* actor, const Umi& s, p2captor::Vec3* out) {
    const int clip = p2umi::clipIndex(s.clip.c_str());
    const float frame = drawFrame(s);
    const p2chappymouth::Vec3 apos = p2captorhost::vec(actor->getPosition());
    float mouth[3] = {0.0f, 0.0f, 0.0f};
    p2umi::nodeCentre(clip, frame, 2, mouth);
    for (int i = 0; i < p2umitables::kKamuCount; ++i) {
        float local[3] = {mouth[0], mouth[1], mouth[2]};
        p2umi::kamuCentre(clip, frame, i, local);
        out[i] = p2umi::toWorld(apos, s.heading, s.scale, local);
    }
}
// Source StateAttack key 5 (umiMushiState.cpp:521-539): every captain is tested against every
// mouth slot with `_length2` (the SQUARED separation) below the slot radius.
void attackNaviBySlots(BTeki* a, Umi& s, unsigned generator) {
    p2captor::Vec3 slots[p2umitables::kKamuCount];
    slotPositions(a, s, slots);
    const float radius = mouthGeometry(s).radius;
    for (Navi* n : pc_p2_navis()) {
        if (!n->isAlive()) continue;
        const p2chappymouth::Vec3 np = p2captorhost::vec(n->getPosition());
        for (int i = 0; i < p2umitables::kKamuCount; ++i) {
            if (!p2umi::naviHitBySlot(slots[i], np, radius)) continue;
            n->stimulate(InteractAttack(a, nullptr, ATTACK_DAMAGE, false));
            logHit(a, s, generator, "navi_bite", n->getPosition(), i);
        }
    }
}
// One source EnemyFunc::eatPikmin pass over the seven tongue slots.
int tongueEat(BTeki* actor, Umi& s, unsigned generator, int frame) {
    const p2captor::Geometry& g = mouthGeometry(s);
    p2captor::Vec3 slotPos[p2umitables::kKamuCount];
    slotPositions(actor, s, slotPos);
    if (!s.mouthLogged) {
        s.mouthLogged = true;
        std::printf("P2_UMIMUSHI_MOUTH generator=%u source_id=%d slots=%d radius=%.1f source=kamu_joint_tables "
                    "host_slots=%d\n", generator, s.sourceId, g.slots, g.radius, p2captorhost::hostSlotCount(actor));
        std::fflush(stdout);
    }
    bool occupied[p2captor::MaxSlots] = {};
    p2captorhost::validate(actor, s.held, g.slots, occupied);
    p2captorhost::Scene scene = p2captorhost::snapshot(actor);
    const p2captor::Vec3 apos = p2captorhost::vec(actor->getPosition());
    int refused = 0;
    const int caught = p2captor::eatAt(slotPos, g.slots, g.radius, scene.prey.data(), (int)scene.prey.size(),
                                       occupied, p2captor::defaultEligible, [&](int n, int slot) {
        if (!p2captorhost::swallowInto(actor, scene, n, slot, s.held, 0, &refused)) return false;
        const p2captor::Vec3 l = p2captor::toLocal(apos, s.heading, scene.prey[n].pos);
        const p2umi::Polar pl = p2umi::polar(apos, s.heading, scene.prey[n].pos);
        std::printf("P2_UMIMUSHI_BITE generator=%u frame=%d pikmin=1 slot=%d local_x=%.1f local_y=%.1f "
                    "local_z=%.1f angle_deg=%.1f dist_xz=%.1f slot_x=%.1f slot_y=%.1f slot_z=%.1f\n",
                    generator, frame, slot, l.x, l.y, l.z, double(pl.angleDeg), double(pl.distXZ),
                    double(slotPos[slot].x), double(slotPos[slot].y), double(slotPos[slot].z));
        std::fflush(stdout);
        shot(s, "bite");
        return true;
    });
    if (refused > 0) {
        std::printf("P2_UMIMUSHI_EAT_REFUSED generator=%u reason=no_host_slot count=%d\n", generator, refused);
        std::fflush(stdout);
    }
    return caught;
}
void releaseTongue(BTeki* actor, Umi& s, unsigned generator, const char* why) {
    const int freed = p2captorhost::release(actor, s.held);
    s.tongueActive = false;
    s.tongueHasPiki = false;
    if (freed > 0) {
        std::printf("P2_UMIMUSHI_RELEASE generator=%u reason=%s pikmin=%d\n", generator, why, freed);
        std::fflush(stdout);
    }
}

void fireAttackEvents(BTeki* actor, Umi& s, unsigned generator) {
    auto it = clips.find("attack1");
    if (it == clips.end()) return;
    const float frame = s.stateTime * 30.0f;
    // Source StateAttack::exec: eatPikmin runs first while the tongue is active.
    if (s.tongueActive && tongueEat(actor, s, generator, int(frame)) > 0) s.tongueHasPiki = true;
    for (const auto& event : it->second.events) {
        if (s.firedEvents.count(event.first)) continue;
        if (frame < event.first) continue;
        s.firedEvents.insert(event.first);
        if (event.second == 3) {
            s.tongueActive = true; // source KEYEVENT_3: the tongue starts eating
        } else if (event.second == 5) {
            attackNaviBySlots(actor, s, generator);
        } else if (event.second == 6) {
            s.tongueActive = false; // source KEYEVENT_6 closes the tongue
            doFlick(actor, s, generator, event.first, "attack", false);
        }
    }
}
void fireFlickEvents(BTeki* actor, Umi& s, unsigned generator) {
    auto it = clips.find("flick1");
    if (it == clips.end()) return;
    const float frame = s.stateTime * 30.0f;
    for (const auto& event : it->second.events) {
        if (s.firedEvents.count(event.first)) continue;
        if (frame < event.first) continue;
        s.firedEvents.insert(event.first);
        if (event.second == 2) doFlick(actor, s, generator, event.first, "flick", true);
    }
}

void setPhase(Umi& s) {
    s.phase = phaseOf(s);
}

// ---- Own collision tree (#995) -------------------------------------------------------------
// The P1 Chappy host's tree neither matches the drawn Bloyster nor the source parts. The bound
// Bloyster wears the retail umimushi/enemycoll.txt tree instead (root r180, head r80, kuti r40,
// ketu r25 and the stickable `weak` tail bulb r10 x Parms::mTailScale 1.4), posed through the
// current clip from the tables generated by scripts/p2_umimushi_tables.py, plus a 'slot' mouth part
// with seven 'kamN' children that follow kamu_joint1..7 for the swallow. Same host-swap pattern
// as the Emperor (pc_p2_chappy.cpp kingBuildColl). PIKMIN_P2_UMIMUSHI_OWN_COLL=0 keeps the host tree.
bool ownCollEnabled() {
    static const bool on = [] {
        const char* e = std::getenv("PIKMIN_P2_UMIMUSHI_OWN_COLL");
        return !(e && e[0] == '0');
    }();
    return on;
}
u32 fourcc(const char* id) {
    u32 v = 0;
    for (int i = 0; i < 4; ++i) v = (v << 8) | u32(static_cast<unsigned char>(id[i] ? id[i] : '_'));
    return v;
}
void buildColl(BTeki* actor, Umi& s, unsigned generator) {
    if (!ownCollEnabled() || s.coll.own || s.coll.released || !actor->mCollInfo) return;
    namespace T = p2umitables;
    std::vector<ObjCollInfo*> nodes;
    auto make = [&](const char* id, const char* code, float radius) {
        auto* n = new ObjCollInfo();
        n->mId.setID(fourcc(id));
        n->mCode.setID(fourcc(code));
        n->mRadius = radius;
        n->mCentrePosition.set(0.0f, 0.0f, 0.0f);
        n->mJointIndex = 0;
        nodes.push_back(n);
        return n;
    };
    for (int i = 0; i < T::kNodeCount; ++i) make(T::kNodes[i].id, T::kNodes[i].code, T::kNodes[i].radius * s.scale);
    for (int i = 1; i < T::kNodeCount; ++i) nodes[size_t(T::kNodes[i].parent)]->add(nodes[size_t(i)]);
    ObjCollInfo* slot = make("slot", "____", 1.0f);
    nodes[0]->add(slot);
    static const char* const kam[T::kKamuCount] = {"kam1", "kam2", "kam3", "kam4", "kam5", "kam6", "kam7"};
    for (int i = 0; i < T::kKamuCount; ++i) slot->add(make(kam[i], "____", s.blind ? p2umi::SlotRadiusBlind : p2umi::SlotRadius));
    Umi::Coll c;
    c.own = new CollInfo(int(nodes.size()) + 14);
    c.own->initInfoTree(nodes[0]);
    auto prepare = [](CollPart* part) {
        if (!part) return;
        part->mIsUpdateActive = false; // no parent shape: updateColl owns centre/radius
        part->mJointMatrix = Matrix4f::ident;
    };
    for (int i = 0; i < T::kNodeCount; ++i) {
        c.node[i] = c.own->getSphere(fourcc(T::kNodes[i].id));
        prepare(c.node[i]);
    }
    c.slot = c.own->getSphere(fourcc("slot"));
    prepare(c.slot);
    for (int i = 0; i < T::kKamuCount; ++i) {
        c.kam[i] = c.own->getSphere(fourcc(kam[i]));
        prepare(c.kam[i]);
    }
    c.host = actor->mCollInfo;
    actor->mCollInfo = c.own;
    // The host's model platforms would report contacts whose part this tree cannot resolve.
    actor->mPlatMgr.release();
    s.coll = c;
    std::printf("P2_UMIMUSHI_COLL_BIND generator=%u source_id=%d nodes=%zu stickable=%d root_radius=%.0f "
                "weak_radius=%.1f host_parts_replaced=1\n", generator, s.sourceId, nodes.size(),
                p2umi::stickableCount(), double(T::kNodes[0].radius * s.scale),
                double(T::kNodes[4].radius * s.scale * p2umi::TailScale));
    std::fflush(stdout);
}
// Poses every part at the actor position / heading for the current clip frame.
void updateColl(BTeki* actor, Umi& s) {
    if (!s.coll.own || s.coll.released) return;
    namespace T = p2umitables;
    Matrix4f yaw, camRot, camYaw;
    yaw.makeSRT(Vector3f(1.0f, 1.0f, 1.0f), Vector3f(0.0f, actor->getDirection(), 0.0f), Vector3f(0.0f, 0.0f, 0.0f));
    camRot.makeIdentity();
    for (int r = 0; r < 3; ++r)
        for (int c = 0; c < 3; ++c) camRot.mMtx[r][c] = invCamMat.mMtx[c][r];
    camRot.multiplyTo(yaw, camYaw);
    const int clip = p2umi::clipIndex(s.clip.c_str());
    const float frame = drawFrame(s);
    const p2chappymouth::Vec3 apos = p2captorhost::vec(actor->getPosition());
    float mouth[3] = {0.0f, 0.0f, 0.0f};
    for (int i = 0; i < T::kNodeCount; ++i) {
        CollPart* part = s.coll.node[i];
        if (!part) continue;
        float c[3] = {0.0f, 0.0f, 0.0f};
        p2umi::nodeCentre(clip, frame, i, c);
        if (i == 2) for (int k = 0; k < 3; ++k) mouth[k] = c[k];
        const p2chappymouth::Vec3 w = p2umi::toWorld(apos, actor->getDirection(), s.scale, c);
        part->mCentre.set(w.x, w.y, w.z);
        part->mRadius = T::kNodes[i].radius * s.scale * (i == 4 ? p2umi::TailScale : 1.0f);
        part->mJointMatrix = camYaw;
    }
    const p2chappymouth::Vec3 mw = p2umi::toWorld(apos, actor->getDirection(), s.scale, mouth);
    if (s.coll.slot) {
        s.coll.slot->mCentre.set(mw.x, mw.y, mw.z);
        s.coll.slot->mRadius = 1.0f;
        s.coll.slot->mJointMatrix = camYaw;
    }
    // World position of every slot first: a held Pikmin is laid along the local tangent of the tongue (#1020).
    float slotW[T::kKamuCount][3];
    for (int i = 0; i < T::kKamuCount; ++i) {
        float local[3] = {mouth[0], mouth[1], mouth[2]};
        p2umi::kamuCentre(clip, frame, i, local);
        const p2chappymouth::Vec3 w = p2umi::toWorld(apos, actor->getDirection(), s.scale, local);
        slotW[i][0] = w.x;
        slotW[i][1] = w.y;
        slotW[i][2] = w.z;
    }
    for (int i = 0; i < T::kKamuCount; ++i) {
        CollPart* part = s.coll.kam[i];
        if (!part) continue;
        float dir[3];
        p2skewer::tangent(slotW, T::kKamuCount, i, dir);
        float seated[3] = {slotW[i][0], slotW[i][1], slotW[i][2]};
        p2skewer::seat(seated, dir, s.scale);
        part->mCentre.set(seated[0], seated[1], seated[2]);
        part->mRadius = s.blind ? p2umi::SlotRadiusBlind : p2umi::SlotRadius;
        float rot[9];
        if (p2skewer::umiRotation(s.clip.c_str(), frame, i, rot))
            p2skewer::jointMatrixBasis(part->mJointMatrix, camRot, p2skewer::fromRotation(rot, actor->getDirection()));
        else
            p2skewer::jointMatrix(part->mJointMatrix, camRot, dir, actor->getDirection());
    }
}
// Gives the actor its host CollInfo back (the own tree is never freed: stuck Pikmin may still
// hold its CollPart pointers) and, for a death, seats the host carcass/centre on the body so the
// corpse pellet is born where the Bloyster died.
void restoreColl(BTeki* actor, Umi& s, bool dead) {
    if (!s.coll.own || s.coll.released) return;
    s.coll.released = true;
    if (!s.coll.host) return;
    if (actor->mCollInfo == s.coll.own) actor->mCollInfo = s.coll.host;
    const Vector3f p = actor->getPosition();
    if (dead && actor->mCollInfo) {
        if (CollPart* carcass = actor->mCollInfo->getSphere('carc')) carcass->mCentre.set(p.x, p.y, p.z);
        if (actor->mCollInfo->hasInfo()) {
            if (CollPart* bound = actor->mCollInfo->getBoundingSphere()) bound->mCentre.set(p.x, p.y, p.z);
            if (CollPart* cent = actor->mCollInfo->getSphere('cent')) cent->mCentre.set(p.x, p.y, p.z);
        }
    }
    s.coll.host = nullptr;
}
// ---- TEST-ONLY evidence probe (PIKMIN_P2_UMIMUSHI_PROBE=1) ---------------------------------------
// Headless runs have no player, so the skewer hold and the tail latch are exercised by moving Pikmin
// into the scene and throwing them through the REAL Navi::throwPiki + PikiFlyingState path:
//   * once, 2 s after bind: one bait Pikmin is placed 110 units straight ahead (inside the fp23 cone),
//     so the real attack, tongue capture, hold and swallow run;
//   * from 10 s: eight Pikmin are thrown (0.6 s apart) from 170 units behind the tail bulb, aimed at the
//     bulb XZ scaled by 0.9, 1.0 .. 1.6 (the descending arc crosses the raised bulb earlier than the
//     cursor point), so the real collision decides which ones latch.
// Nothing here changes a normal run; the env var is read once and unset by default.
BTeki* probeOwner = nullptr;
bool probeEnabled() {
    static const bool on = [] {
        const char* e = std::getenv("PIKMIN_P2_UMIMUSHI_PROBE");
        return e && *e && *e != '0';
    }();
    return on;
}
// While the eight probe throws are in the air the Bloyster is held still (no AI tick), so the bulb the
// Pikmin aim at is where the physics finds it. Before 9.5 s and after the window it runs normally.
bool probeFrozen(const BTeki* actor, const Umi& s) {
    return probeEnabled() && probeOwner == actor && s.probeTime >= 9.5f && s.probeTime < 18.0f;
}
Piki* probeFreePiki() {
    if (!pikiMgr) return nullptr;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive() || p->isStickTo() || p->isStickToMouth() || p->isBuried() || !p->isVisible()) continue;
        return p;
    }
    return nullptr;
}
void runProbe(BTeki* actor, Umi& s, unsigned generator, float dt) {
    if (!probeEnabled() || s.state == UMI_DEAD) return;
    if (!probeOwner) probeOwner = actor; // the probe drives exactly one Bloyster (the first to tick)
    if (probeOwner != actor) return;
    s.probeTime += dt;
    const Vector3f ap = actor->getPosition();
    if (s.probeTime >= 0.5f && !s.probeCaptain) {
        // Frame the scene: the camera follows the captain, who starts ~720 units away.
        if (Navi* navi = naviMgr ? naviMgr->getActiveNavi() : nullptr) {
            s.probeCaptain = true;
            // Stand the captain 300 units "behind" the Bloyster along the camera's own forward axis, so the
            // Bloyster is in front of the lens (the camera yaw follows the captain, not the other way round).
            float fx = 0.0f, fz = 1.0f;
            if (Camera* cam = navi->controlCamera()) {
                fx = -cam->mLookAtMtx.mMtx[2][0];
                fz = -cam->mLookAtMtx.mMtx[2][2];
                const float len = std::sqrt(fx * fx + fz * fz);
                if (len > 1.0e-4f) { fx /= len; fz /= len; }
            }
            const float cx = ap.x - fx * 300.0f, cz = ap.z - fz * 300.0f;
            const float cy = mapMgr ? mapMgr->getMinY(cx, cz, true) : ap.y;
            navi->mSRT.t = Vector3f(cx, cy, cz);
            navi->mFaceDirection = std::atan2(fx, fz);
            std::printf("P2_UMIMUSHI_PROBE kind=captain generator=%u x=%.1f y=%.1f z=%.1f\n", generator, double(cx),
                        double(cy), double(cz));
            std::fflush(stdout);
        }
    }
    if (!s.probeBait && s.probeTime >= 2.0f) {
        if (Piki* p = probeFreePiki()) {
            s.probeBait = true;
            p->mSRT.t = Vector3f(ap.x + std::sin(s.heading) * 110.0f, ap.y, ap.z + std::cos(s.heading) * 110.0f);
            p->mVelocity.set(0.0f, 0.0f, 0.0f);
            std::printf("P2_UMIMUSHI_PROBE kind=bait generator=%u x=%.1f y=%.1f z=%.1f\n", generator, double(p->mSRT.t.x),
                        double(p->mSRT.t.y), double(p->mSRT.t.z));
            std::fflush(stdout);
        }
    }
    for (int i = 0; i < s.probeThrows; ++i) {
        if (s.probeMid[i] || s.probeTime < s.probeThrownAt[i] + 0.5f || !s.probeThrown[i]) continue;
        s.probeMid[i] = true;
        Piki* t = s.probeThrown[i];
        std::printf("P2_UMIMUSHI_PROBE kind=flight n=%d pos=(%.1f,%.1f,%.1f) vel=(%.1f,%.1f,%.1f) state=%d\n", i,
                    double(t->mSRT.t.x), double(t->mSRT.t.y), double(t->mSRT.t.z), double(t->mVelocity.x),
                    double(t->mVelocity.y), double(t->mVelocity.z), int(t->getState()));
        std::fflush(stdout);
    }
    // Landing census: 1.8 s after each throw, where did the Pikmin end up relative to the bulb?
    for (int i = 0; i < s.probeThrows; ++i) {
        if (s.probeLanded[i] || s.probeTime < s.probeThrownAt[i] + 1.8f || !s.coll.node[4]) continue;
        s.probeLanded[i] = true;
        Piki* t = s.probeThrown[i];
        if (!t) continue;
        const CollPart* w = s.coll.node[4];
        const Vector3f q = t->mSRT.t;
        const float dx = q.x - w->mCentre.x, dy = q.y - w->mCentre.y, dz = q.z - w->mCentre.z;
        std::printf("P2_UMIMUSHI_PROBE kind=landing generator=%u n=%d dist_to_bulb=%.1f stuck_to_weak=%d stuck=%d alive=%d\n",
                    generator, i, double(std::sqrt(dx * dx + dy * dy + dz * dz)),
                    int(t->mStickPart == s.coll.node[4]), int(t->isStickTo()), int(t->isAlive()));
        std::fflush(stdout);
    }
    if (s.probeTime < 10.0f || s.probeThrows >= 8 || s.probeTime < s.probeNextThrow || !s.coll.node[4]) return;
    Navi* navi = naviMgr ? naviMgr->getActiveNavi() : nullptr;
    Piki* p = probeFreePiki();
    if (!navi || !p) return;
    const CollPart* weak = s.coll.node[4];
    const float bx = std::sin(s.heading), bz = std::cos(s.heading);
    const Vector3f bulb(weak->mCentre.x, weak->mCentre.y, weak->mCentre.z);
    const float lx = bulb.x - bx * 120.0f, lz = bulb.z - bz * 120.0f; // a captain 120 units behind the bulb, on the ground there
    const Vector3f launch(lx, mapMgr ? mapMgr->getMinY(lx, lz, true) : ap.y, lz);
    // Throw height of a quick tap (hold time 0) and the lock-on pin the game would use for it.
    const float quickHeight = C_NAVI_PARM(navi, mThrowMinHeight);
    const float lockK = p2umi::pinScale(bulb.y - ap.y, quickHeight, 550.0f, 0.5f);
    const float scan[8] = {1.0f, 1.1f, 1.2f, lockK, 1.3f, 1.35f, 1.4f, 1.5f};
    const float k = scan[s.probeThrows];
    const Vector3f aim(launch.x + (bulb.x - launch.x) * k, bulb.y, launch.z + (bulb.z - launch.z) * k);
    const Vector3f saved = navi->mSRT.t;
    navi->mSRT.t = launch;
    p->mFSM->transit(p, 14); // PIKISTATE_Flying, exactly as NaviThrowState key action 0
    navi->throwPiki(p, aim);
    navi->mSRT.t = saved;
    s.probeThrown[s.probeThrows] = p;
    s.probeThrownAt[s.probeThrows] = s.probeTime;
    std::printf("P2_UMIMUSHI_PROBE kind=throw generator=%u n=%d k=%.2f launch=(%.1f,%.1f,%.1f) bulb=(%.1f,%.1f,%.1f) "
                "aim=(%.1f,%.1f,%.1f)\n", generator, s.probeThrows, double(k), double(launch.x), double(launch.y),
                double(launch.z), double(bulb.x), double(bulb.y), double(bulb.z), double(aim.x), double(aim.y),
                double(aim.z));
    std::fflush(stdout);
    ++s.probeThrows;
    s.probeNextThrow = s.probeTime + 0.6f;
}
// Latched-Pikmin census (the tail bulb): logs when the number of Pikmin stuck to the body changes.
void logLatched(BTeki* actor, Umi& s, unsigned generator) {
    int weak = 0, other = 0;
    float nearest = -1.0f;
    for (Creature* c = actor->mStickListHead; c; c = c->mNextSticker) {
        if (!c->isPiki() || c->isStickToMouth()) continue;
        if (s.coll.node[4] && c->mStickPart == s.coll.node[4]) ++weak;
        else ++other;
        if (s.coll.node[4]) {
            const Vector3f q = c->mSRT.t;
            const float dx = q.x - s.coll.node[4]->mCentre.x, dy = q.y - s.coll.node[4]->mCentre.y,
                        dz = q.z - s.coll.node[4]->mCentre.z;
            const float d = std::sqrt(dx * dx + dy * dy + dz * dz);
            if (nearest < 0.0f || d < nearest) nearest = d;
        }
    }
    const int total = weak + other;
    if (weak >= 1) shot(s, "latch1");
    if (weak >= 3) shot(s, "latch3");
    if (total == s.latchedLogged) return;
    s.latchedLogged = total;
    std::printf("P2_UMIMUSHI_LATCH generator=%u source_id=%d stuck=%d on_weak=%d other=%d nearest_to_weak=%.1f "
                "weak_centre=(%.1f,%.1f,%.1f) weak_radius=%.1f flick_timer=%.2f health=%.1f\n", generator,
                s.sourceId, total, weak, other, double(nearest),
                s.coll.node[4] ? double(s.coll.node[4]->mCentre.x) : 0.0,
                s.coll.node[4] ? double(s.coll.node[4]->mCentre.y) : 0.0,
                s.coll.node[4] ? double(s.coll.node[4]->mCentre.z) : 0.0,
                s.coll.node[4] ? double(s.coll.node[4]->mRadius) : 0.0, double(s.flickTimer), double(actor->mHealth));
    std::fflush(stdout);
}
}

void pc_p2_umimushi_reset() {
    for (auto& e : actors) {
        BTeki* actor = static_cast<BTeki*>(e.first);
        if (actor && e.second.coll.own && !e.second.coll.released && e.second.coll.host
                && actor->mCollInfo == e.second.coll.own)
            actor->mCollInfo = e.second.coll.host; // stage boundary: hand every Bloyster its host tree back
    }
    actors.clear();
    corpses.clear();
    clips.clear();
    ready = false;
}

void pc_p2_umimushi_forget_piki(Piki* piki) {
    for (auto& entry : actors) entry.second.held.forget(piki);
}

void pc_p2_umimushi_forget(BTeki* actor) {
    pc_randomizer_p2_forget_source(static_cast<PelletView*>(actor));
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it != actors.end()) {
        p2captorhost::release(actor, it->second.held); // teardown frees the tongue
        restoreColl(actor, it->second, false);
    }
    actors.erase(static_cast<PelletView*>(actor));
    corpses.erase(static_cast<PelletView*>(actor));
}

bool pc_p2_umimushi_suppress_ai(const BTeki* actor) {
    return ready && actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor))) != 0;
}

float pc_p2_umimushi_param_f(const BTeki* actor, int idx, float fallback) {
    if (!ready) return fallback;
    auto found = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (found == actors.end()) return fallback;
    if (idx == TPF_Life) return found->second.blind ? BLIND_LIFE : LIFE;
    if (idx == TPF_LifeRecoverRate) return 0.0f;
    switch (idx) {
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

bool pc_p2_umimushi_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

void pc_p2_umimushi_setup() {
    pc_p2_umimushi_reset();
    if (!tekiMgr) return;

    // Clip durations and source key-event frames from the validated aquatic bank.
    std::ifstream bank("p2-aquatic-bank.txt");
    if (bank) {
        std::string token;
        if (bank >> token && token == "P2_AQUATIC_BANK_1") {
            while (bank >> token) {
                if (token == "species") {
                    std::string species, identity;
                    bank >> species >> identity;
                } else if (token == "clip") {
                    std::string species, name, frames, events, marker, poses, status;
                    bank >> species >> name >> frames >> events >> marker >> poses >> status;
                    if (species == "UmiMushi") {
                        Clip clip;
                        clip.name = name;
                        const double sourceFrames = std::atof(frames.c_str());
                        clip.duration = sourceFrames > 0.0 ? float(sourceFrames) / 30.0f : 1.0f;
                        clip.loop = (name == "run1" || name == "srun1" || name == "sturn1");
                        if (events != "-") {
                            size_t start = 0;
                            while (start < events.size()) {
                                const size_t comma = events.find(',', start);
                                const std::string pair = events.substr(start, comma - start);
                                const size_t colon = pair.find(':');
                                if (colon != std::string::npos) {
                                    clip.events.emplace_back(std::atoi(pair.substr(0, colon).c_str()),
                                                             std::atoi(pair.substr(colon + 1).c_str()));
                                }
                                if (comma == std::string::npos) break;
                                start = comma + 1;
                            }
                        }
                        clips[name] = clip;
                    }
                } else if (token == "frames") {
                    // P2_BANK_FRAMES_1 trailer (#895): per-pose source frames,
                    // consumed by the batch draw paths; skip its list token here.
                    std::string framesList;
                    bank >> framesList;
                } else {
                    break;
                }
            }
        }
    }

    std::ifstream in("p2-aquatic-actors.txt");
    if (!in && !pc_randomizer_p2_bridge()) return;
    std::string header;
    int count = 0;
    // Same shared UmiMushi::Mgr FSM, two source IDs: ordinary (71) and Blind
    // (101). The actors config marks Blind with the `UmiMushiBlind` species;
    // the Blind bank reuses the converted UmiMushi clips (visual stand-in).
    std::map<unsigned, bool> wanted; // generator -> blind
    if (in && (in >> header >> count) && header == "P2_AQUATIC_ACTORS_1" && count >= 1) {
        for (int i = 0; i < count; ++i) {
            unsigned long long generator = 0;
            std::string species;
            if (!(in >> generator >> species)) return;
            if (species == "UmiMushi") wanted[unsigned(generator)] = false;
            else if (species == "UmiMushiBlind") wanted[unsigned(generator)] = true;
        }
    }
    if (pc_randomizer_p2_bridge()) {
        wanted.clear();
        for (unsigned id : pc_p2_campaign_ids(71)) wanted[id] = false;
        for (unsigned id : pc_p2_campaign_ids(101)) wanted[id] = true;
    }
    if (wanted.empty()) return;

    std::set<unsigned> found;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor || !actor->mGenerator) continue;
        const unsigned token = pc_p2_campaign_token(actor);
        auto match = wanted.find(token);
        if (match == wanted.end()) continue;
        if (actor->mTekiType != TEKI_Chappy) {
            std::printf("P2_UMIMUSHI_ERROR native_type generator=%u\n", token);
            std::fflush(stdout);
            if (pc_p2_setup_skip(pc_randomizer_p2_bridge(), "UmiMushi", "actor_type_mismatch")) return;
        }
        Umi& s = actors[static_cast<PelletView*>(actor)];
        s.blind = match->second;
        s.sourceId = s.blind ? 101 : 71;
        s.home = actor->getPosition();
        s.goal = s.home;
        s.heading = actor->getDirection();
        actor->mHealth = s.blind ? BLIND_LIFE : LIFE;
        actor->mMaxHealth = actor->mHealth;
        s.lastHealth = actor->mHealth;
        // Source setParameters applies scale 0.5 to Blind; the P1 host draws the
        // actor from mSRT.s (batch-3 onCamMtx), so the visual is genuinely half.
        if (s.blind) actor->mSRT.s.set(BLIND_SCALE, BLIND_SCALE, BLIND_SCALE);
        s.scale = s.blind ? BLIND_SCALE : 1.0f;
        // Lane 06 ordinary delivery: bind the campaign source so the corpse
        // mints onion:p2:<id> via GoalItem::suckMe.
        pc_randomizer_p2_bind_source(static_cast<PelletView*>(actor),
                                     unsigned(s.blind ? 101 : 71), token);
        std::printf("P2_UMIMUSHI_DELIVERY_BIND generator=%u source_id=%d\n",
                    token, s.sourceId);
        enter(s, UMI_WALK, "run1");
        std::printf("P2_UMIMUSHI_BIND generator=%u source_id=%d visual_only=0 blind=%d\n",
                    token, s.sourceId, s.blind ? 1 : 0);
        if (s.blind) {
            std::printf("P2_UMIMUSHI_BLIND generator=%u scale=%.3f health=%.1f "
                        "turn_rate=%.2f wait_frames=%.0f move_frames=%.0f\n",
                        token, BLIND_SCALE, BLIND_LIFE, BLIND_TURN_RATE,
                        BLIND_WAIT_FRAMES, BLIND_MOVE_FRAMES);
        }
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=%s native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=animation_event water=absent\n",
                    s.blind ? "UmiMushiBlind" : "UmiMushi",
                    token, pos.x, pos.y, pos.z, actor->mHealth,
                    actor->mMaxHealth);
        std::printf("P2_UMIMUSHI_STATE generator=%u state=walk\n", token);
        std::fflush(stdout);
        found.insert(token);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_UMIMUSHI_ERROR missing_actor wanted=%zu found=%zu\n",
                    wanted.size(), found.size());
        std::fflush(stdout);
        if (pc_p2_setup_skip(pc_randomizer_p2_bridge(), "UmiMushi", "actor_roster_incomplete")) return;
    }
    ready = true;
}

void pc_p2_umimushi_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Umi& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = actor->mGenerator ? pc_p2_campaign_token(actor) : 0u;
    // The P1 TAI reaction path is suppressed for registered bloysters
    // (pc_p2_umimushi_suppress_ai), so the source FSM applies pending damage
    // itself. Mirrors pc_p2_frog_update.
    if (actor->mStoredDamage > 0.0f) actor->makeDamaged();
    // Natural-combat observability: incremental still-positive decrease is
    // real attack damage. Mirrors P2_FROG_DAMAGE.
    if (actor->mHealth < s.lastHealth && actor->mHealth > 0.0f) {
        std::printf("P2_UMIMUSHI_DAMAGE generator=%u source_id=%d health=%.1f\n",
                    generator, s.sourceId, actor->mHealth);
        std::fflush(stdout);
    }
    s.lastHealth = actor->mHealth;

    if (actor->mHealth <= 0.0f && s.state != UMI_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_UMIMUSHI_DEAD generator=%u source_id=%d health=0\n",
                        generator, s.sourceId);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        // Keep the generator for Pod receipt after the engine tears down
        // the host into a carriable pellet.
        if (generator) corpses[static_cast<PelletView*>(actor)] = generator;
        releaseTongue(actor, s, generator, "death");
        setState(actor, s, UMI_DEAD, "dead1");
        restoreColl(actor, s, true);
    }

    s.stateTime += dt;
    if (probeFrozen(actor, s)) stop(actor);
    else switch (s.state) {
    case UMI_WALK: {
        if (distXZ(pos, s.goal) < 50.0f) {
            if (isOutOfTerritory(s, pos, 1.0f) || !isFindTarget(actor, s)) setNextGoal(s);
        }
        // Source StateWalk::exec (umiMushiState.cpp:146-173) bifurcates: Blind
        // alternates configured move (fp14) and wait (fp13) frame windows while
        // the ordinary Bloyster walks continuously.
        if (s.blind) {
            if (s.blindWaiting) {
                stop(actor);
                s.blindWaitTimer += dt;
                if (s.blindWaitTimer >= BLIND_WAIT_FRAMES / FRAME_RATE) {
                    s.blindWaitTimer = 0.0f;
                    s.blindMoveTimer = 0.0f;
                    s.blindWaiting = false;
                    std::printf("P2_UMIMUSHI_BLIND_MOVE generator=%u\n", generator);
                    std::fflush(stdout);
                }
            } else {
                s.blindMoveTimer += dt;
                walkFunc(actor, s);
                if (s.blindMoveTimer >= BLIND_MOVE_FRAMES / FRAME_RATE) {
                    s.blindMoveTimer = 0.0f;
                    s.blindWaitTimer = 0.0f;
                    s.blindWaiting = true;
                    std::printf("P2_UMIMUSHI_BLIND_WAIT generator=%u\n", generator);
                    std::fflush(stdout);
                }
            }
        } else {
            walkFunc(actor, s);
        }
        if (isStartFlick(actor, s)) {
            setState(actor, s, UMI_FLICK, "flick1");
            s.nextState = UMI_WALK;
        } else if (isAttackStart(actor, s)) {
            releaseTongue(actor, s, generator, "attack_start");
            setState(actor, s, UMI_ATTACK, "attack1");
        } else if (isChangeNavi(actor, s)) {
            setState(actor, s, UMI_FIND, "fsearch1");
        }
        break;
    }
    case UMI_WAIT:
        stop(actor);
        if (s.stateTime < WAIT_TIME) break;
        if (isStartFlick(actor, s)) {
            setState(actor, s, UMI_FLICK, "flick1");
            s.nextState = UMI_SEARCH;
        } else if (isChangeNavi(actor, s)) {
            setState(actor, s, UMI_FIND, "fsearch1");
        } else if (isAttackStart(actor, s)) {
            releaseTongue(actor, s, generator, "attack_start");
            setState(actor, s, UMI_ATTACK, "attack1");
        } else if (s.targetNavi) {
            if (isNeedTurn(actor, s)) setState(actor, s, UMI_TURN, "sturn1");
            else setState(actor, s, UMI_SEARCH, "srun1");
        } else {
            setState(actor, s, UMI_WALK, "run1");
        }
        break;
    case UMI_FIND:
        stop(actor);
        if (!s.targetNavi) {
            setState(actor, s, UMI_LOST, "outview1");
            break;
        }
        if (s.stateTime >= clipDuration(s.clip)) {
            if (isNeedTurn(actor, s)) setState(actor, s, UMI_TURN, "sturn1");
            else if (isAttackStart(actor, s)) setState(actor, s, UMI_ATTACK, "attack1");
            else setState(actor, s, UMI_SEARCH, "srun1");
        }
        break;
    case UMI_SEARCH:
        if (s.targetNavi) turnFunc(actor, s);
        if (canMove(actor, s)) searchMove(actor, s);
        else outMove(actor, s);
        if (isStartFlick(actor, s)) {
            setState(actor, s, UMI_FLICK, "flick1");
            s.nextState = UMI_SEARCH;
        } else if (isChangeNavi(actor, s)) {
            setState(actor, s, UMI_FIND, "fsearch1");
        } else if (isAttackStart(actor, s)) {
            releaseTongue(actor, s, generator, "attack_start");
            setState(actor, s, UMI_ATTACK, "attack1");
        } else if (isNeedTurn(actor, s)) {
            setState(actor, s, UMI_TURN, "sturn1");
        }
        break;
    case UMI_TURN: {
        stop(actor);
        const float residual = turnFunc(actor, s);
        if (isStartFlick(actor, s)) {
            setState(actor, s, UMI_FLICK, "flick1");
            s.nextState = UMI_TURN;
        } else if (isChangeNavi(actor, s)) {
            setState(actor, s, UMI_FIND, "fsearch1");
        } else if (residual < TURN_END_ANGLE) {
            if (isAttackStart(actor, s)) {
                releaseTongue(actor, s, generator, "attack_start");
                setState(actor, s, UMI_ATTACK, "attack1");
            } else {
                setState(actor, s, UMI_SEARCH, "srun1");
            }
        }
        break;
    }
    case UMI_FLICK:
        stop(actor);
        fireFlickEvents(actor, s, generator);
        if (s.stateTime >= clipDuration("flick1")) {
            const State next = (s.nextState == UMI_NULL) ? UMI_SEARCH : s.nextState;
            if (isChangeNavi(actor, s)) setState(actor, s, UMI_FIND, "fsearch1");
            else setState(actor, s, next, clipForState(next));
        }
        break;
    case UMI_ATTACK:
        stop(actor);
        fireAttackEvents(actor, s, generator);
        if (s.stateTime >= clipDuration("attack1")) {
            s.tongueActive = false;
            if (s.tongueHasPiki) {
                setState(actor, s, UMI_EAT, "eat1");
            } else {
                setState(actor, s, UMI_WAIT, "srun1");
            }
        }
        break;
    case UMI_EAT:
        stop(actor);
        if (s.stateTime >= 0.4f && p2captorhost::mouthStickerCount(actor) > 0) {
            if (!s.holdLogged) {
                s.holdLogged = true; // held-on-tongue census, once per Eat state
                std::printf("P2_UMIMUSHI_HOLD generator=%u source_id=%d held=%d frame=%.1f clip=%s\n", generator,
                            s.sourceId, p2captorhost::mouthStickerCount(actor), double(drawFrame(s)), s.clip.c_str());
                std::fflush(stdout);
            }
            shot(s, "held");
        }
        if (s.stateTime >= clipDuration("eat1")) {
            // Source StateEat END: swallowPikmin on the Pikmin still held.
            int white = 0;
            const int killed = p2captorhost::swallow(actor, s.held, mouthGeometry(s).slots,
                                                     mouthGeometry(s).poison, &white);
            std::printf("P2_UMIMUSHI_EAT generator=%u pikmin=%d white=%d\n", generator, killed, white);
            std::fflush(stdout);
            releaseTongue(actor, s, generator, "eat_end");
            setState(actor, s, UMI_WAIT, "srun1");
            shot(s, "swallowed");
        }
        break;
    case UMI_LOST:
        stop(actor);
        if (s.stateTime >= clipDuration("outview1")) {
            s.goal = s.home;
            setState(actor, s, UMI_WALK, "run1");
        }
        break;
    case UMI_DEAD:
        stop(actor);
        // dieSoon() only runs inside the P1 doAI block, which is suppressed
        // for registered bloysters; pcEscapeNow() finalizes the corpse outside
        // doAI, fired exactly once when the dead clip completes. Mirrors frog.
        if (!s.escaped && s.stateTime >= clipDuration("dead1")) {
            s.escaped = true;
            actor->pcEscapeNow();
        }
        break;
    default:
        break;
    }
    setPhase(s);
    buildColl(actor, s, generator);
    updateColl(actor, s);
    pc_p2_skewer_cam_follow(actor, actor->getDirection(), s.blind ? "umiblind" : "umi");
    runProbe(actor, s, generator, dt);
    logLatched(actor, s, generator);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        const Vector3f now = actor->getPosition();
        std::printf("P2_UMIMUSHI_POS generator=%u state=%s clip=%s phase=%.2f "
                    "x=%.2f y=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase,
                    now.x, now.y, now.z);
        std::fflush(stdout);
    }
}

// Source Obj::damageCallBack (umiMushi.cpp:467-492) through p2umi::damageAccept, evaluated on the
// InteractAttack fields (mOwner, mCollPart) before the P1 host sees the hit. A refused hit takes no
// damage and adds no flickSpeed; a partless low hit is scaled by proper fp01 (retail 0.03). Returns
// < 0 for every actor that is not a live registered Bloyster (host path unchanged).
float pc_p2_umimushi_damage_rate(BTeki* actor, Creature* owner, CollPart* part) {
    if (!ready || !actor) return -1.0f;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return -1.0f;
    Umi& s = it->second;
    if (s.state == UMI_DEAD || actor->mHealth <= 0.0f) return -1.0f; // dead: host corpse path
    p2umi::DamageAttacker a;
    a.present = owner != nullptr;
    a.hasCollPart = p2umi::sourceHasCollPart(part != nullptr, owner && owner->mObjType == OBJTYPE_Navi);
    if (owner) {
        a.alive = owner->isAlive();
        a.stuck = owner->isStickTo();
        a.pos = p2captorhost::vec(owner->getPosition());
    }
    const p2umi::DamageAccept d = p2umi::damageAccept(p2captorhost::vec(actor->getPosition()), a);
    const int count = d == p2umi::DamageStuck ? ++s.hitsStuck : d == p2umi::DamagePartless ? ++s.hitsPartless : ++s.hitsRefused;
    if (count <= 3 || count % 20 == 0) {
        const unsigned generator = actor->mGenerator ? pc_p2_campaign_token(actor) : 0u;
        const p2umi::Polar pl = owner ? p2umi::polar(p2captorhost::vec(actor->getPosition()), s.heading, a.pos)
                                      : p2umi::Polar{0.0f, 0.0f};
        char partId[5] = {'-', 0, 0, 0, 0};
        if (part && part->mCollInfo) {
            const char* raw = part->mCollInfo->mId.mStringID; // packed little-endian: 'weak' prints as "kaew"
            for (int i = 0; i < 4; ++i) partId[i] = raw[3 - i];
        }
        std::printf("P2_UMIMUSHI_RECV generator=%u source_id=%d result=%s part=%s navi=%d stuck=%d angle_deg=%.1f "
                    "dist_xz=%.1f n=%d rate=%.3f\n", generator, s.sourceId,
                    d == p2umi::DamageStuck ? "stuck" : d == p2umi::DamagePartless ? "partless" : "refused", partId,
                    int(owner && owner->mObjType == OBJTYPE_Navi), int(a.stuck), double(pl.angleDeg),
                    double(pl.distXZ), count, double(p2umi::damageRate(d)));
        std::fflush(stdout);
    }
    return p2umi::damageRate(d);
}

// Source EnemyBase::addDamage flickSpeed (1.0) for every hit damageCallBack accepts. No-op for every
// other actor.
void pc_p2_umimushi_attacked(BTeki* actor, bool accepted) {
    if (!ready || !actor || !accepted) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end() || it->second.state == UMI_DEAD) return;
    it->second.flickTimer += p2umi::FlickPerHit;
}

bool pc_p2_umimushi_lock_aim(Creature* target, float naviX, float naviZ, float throwHeight, float gravity,
                             float halfTime, float& offsetX, float& offsetZ) {
    if (!ready || !target || !target->isTeki()) return false;
    auto it = actors.find(static_cast<PelletView*>(static_cast<BTeki*>(target)));
    if (it == actors.end()) return false;
    const Umi& s = it->second;
    const CollPart* weak = s.coll.node[4];
    if (s.state == UMI_DEAD || !weak || s.coll.released) return false;
    const float feet = static_cast<BTeki*>(target)->getPosition().y;
    const float k = p2umi::pinScale(weak->mCentre.y - feet, throwHeight, gravity, halfTime);
    offsetX = (weak->mCentre.x - naviX) * k;
    offsetZ = (weak->mCentre.z - naviZ) * k;
    return true;
}

bool pc_p2_umimushi_receipt(PelletView* view, unsigned& generator) {
    if (!view) return false;
    auto i = actors.find(view);
    if (i != actors.end()) {
        // Live lookup needs the bound token, not the retail _70.
        BTeki* t = static_cast<BTeki*>(view);
        generator = (t && t->mGenerator) ? pc_p2_campaign_token(t) : 0u;
        if (!generator) return false;
        return true;
    }
    auto c = corpses.find(view);
    if (c == corpses.end()) return false;
    generator = c->second;
    return true;
}

int pc_p2_umimushi_bound_count() {
    return int(actors.size() + corpses.size());
}
