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
//   * The P2 seven-slot tongue (kamu_joint1..7, radius 30) is not representable
//     on the P1 host. The swallow is resolved as an explicit nearest-Pikmin
//     capture inside the source fp22=170 attack hit radius at the banked attack
//     bite event (attack1 frame 39, event 3), then exactly one InteractKill at
//     the banked Eat swallow (eat1 animation end). Exactly-once per bite;
//     mirrors the Catfish/Armor port.
//   * No P2 water box (mWaterBox, Hamon sea height, dive/splash) is present on
//     the host; the source outMove/dry fallback and water presentation are
//     bounded gaps.
//   * The shared UmiMushi::Mgr base (100) exclusion and Blind (101)
//     half-scale / fp12=800 health / reduced turn-rate parameter split are
//     bounded gaps; this port runs the ordinary (71) parameters only.
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
#include "teki.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
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
constexpr float ATTACK_HIT_ANGLE = 0.26179939f; // general fp23 default 15 deg
constexpr float ATTACK_DAMAGE = 10.0f;     // general fp24
constexpr float SHAKE_KNOCKBACK = 300.0f;  // general fp17 default
constexpr float SHAKE_DAMAGE = 0.0f;       // general fp18 default
constexpr float SHAKE_RANGE = 20.0f;       // port latch radius for isStartFlick (fp19 default 120 is too broad on the P1 host, where it would pre-empt every bite)
constexpr float TURN_START_ANGLE = 0.52359878f; // proper fp02 30 deg
constexpr float TURN_END_ANGLE = 0.17453293f;   // proper fp03 10 deg
constexpr float ROTATE_RATE = 0.05f;       // proper fp06
constexpr float ROTATE_MAX = 0.04363323f;  // proper fp07 2.5 deg
constexpr float GENERAL_TURN_RATE = 0.1f;  // general fp08 default
constexpr float GENERAL_MAX_TURN = 0.17453293f; // general fp28 default 10 deg
constexpr float WALK_ANGLE_SPEED = 10.0f;  // Parms mWalkAngleSpeed
constexpr float ROTATE_ANGLE_DELTA = 0.05f; // Parms mRotateAngleDelta
constexpr float WAIT_TIME = 0.25f;         // port value (source ip01 = 0)
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
    Piki* captured = nullptr;
    bool tongueHasPiki = false;
    std::set<int> firedEvents;
    std::string clip = "run1";
    float phase = 0.0f;
    bool deadLogged = false;
    float logTimer = 0.0f;
};

std::map<PelletView*, Umi> actors;
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

Navi* activeNavi() {
    if (!naviMgr) return nullptr;
    Navi* n = naviMgr->getNavi();
    return (n && n->isAlive()) ? n : nullptr;
}
Piki* nearestPiki(const Vector3f& pos, float radius) {
    Piki* best = nullptr;
    float bestSq = radius * radius;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
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
            if (!p || !p->isAlive()) continue;
            const Vector3f q = p->getPosition();
            const float dx = q.x - pos.x, dz = q.z - pos.z;
            const float d = dx * dx + dz * dz;
            if (d >= bestSq) continue;
            if (std::fabs(wrapPi(std::atan2(dx, dz) - heading)) > angle) continue;
            bestSq = d; best = p;
        }
    }
    return best;
}
bool isStartFlick(const Vector3f& pos) {
    if (nearestPiki(pos, SHAKE_RANGE)) return true;
    Navi* n = activeNavi();
    return n && distXZ(n->getPosition(), pos) < SHAKE_RANGE;
}
int flickNearby(BTeki* a) {
    const Vector3f pos = a->getPosition();
    int hit = 0;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            const Vector3f q = p->getPosition();
            if (distXZ(q, pos) >= SHAKE_RANGE) continue;
            const float angle = std::atan2(q.x - pos.x, q.z - pos.z);
            p->stimulate(InteractFlick(a, SHAKE_KNOCKBACK, SHAKE_DAMAGE, angle));
            ++hit;
        }
    }
    Navi* n = activeNavi();
    if (n && distXZ(n->getPosition(), pos) < SHAKE_RANGE) {
        const Vector3f q = n->getPosition();
        const float angle = std::atan2(q.x - pos.x, q.z - pos.z);
        n->stimulate(InteractFlick(a, SHAKE_KNOCKBACK, SHAKE_DAMAGE, angle));
        ++hit;
    }
    return hit;
}
void attackNearbyNavi(BTeki* a) {
    Navi* n = activeNavi();
    if (!n) return;
    if (distXZ(n->getPosition(), a->getPosition()) < ATTACK_HIT) {
        n->stimulate(InteractAttack(a, nullptr, ATTACK_DAMAGE, false));
    }
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
    Navi* navi = activeNavi();
    if (!navi) return false;
    const Vector3f pos = a->getPosition();
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
    Navi* navi = activeNavi();
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
    Piki* piki = nearestPikiAngle(pos, s.heading, ATTACK_HIT, ATTACK_HIT_ANGLE);
    // Port adaptation: the source also gates the bite on the fp23=15 deg cone.
    // The P1 host has no tongue geometry, so a Pikmin anywhere inside the source
    // fp22=170 hit radius starts the attack (the tongue then captures it).
    if (!piki) piki = nearestPiki(pos, ATTACK_HIT);
    if (piki) {
        s.goal = piki->getPosition();
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
    return turnToTarget(a, s, s.goal, ROTATE_RATE, ROTATE_MAX);
}

void enter(Umi& s, State state, const char* clip) {
    s.state = state;
    s.nextState = UMI_NULL;
    s.stateTime = 0.0f;
    s.firedEvents.clear();
    if (clip) s.clip = clip;
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
    const unsigned generator = a->mGenerator ? a->mGenerator->_70 : 0u;
    std::printf("P2_UMIMUSHI_STATE generator=%u state=%s\n", generator, stateName(state));
    std::fflush(stdout);
}

void fireAttackEvents(BTeki* actor, Umi& s, unsigned generator) {
    auto it = clips.find("attack1");
    if (it == clips.end()) return;
    const Vector3f pos = actor->getPosition();
    const float frame = s.stateTime * 30.0f;
    for (const auto& event : it->second.events) {
        if (s.firedEvents.count(event.first)) continue;
        if (frame < event.first) continue;
        s.firedEvents.insert(event.first);
        if (event.second == 3) {
            Piki* piki = nearestPikiAngle(pos, s.heading, ATTACK_HIT, ATTACK_HIT_ANGLE);
            if (!piki) piki = nearestPiki(pos, ATTACK_HIT);
            if (piki) {
                s.captured = piki;
                s.tongueHasPiki = true;
                std::printf("P2_UMIMUSHI_BITE generator=%u frame=%d pikmin=1\n",
                            generator, event.first);
                std::fflush(stdout);
            }
        } else if (event.second == 5) {
            attackNearbyNavi(actor);
        } else if (event.second == 6) {
            const int hit = flickNearby(actor);
            if (hit > 0) {
                std::printf("P2_UMIMUSHI_FLICK generator=%u frame=%d pikmin=%d\n",
                            generator, event.first, hit);
                std::fflush(stdout);
            }
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
        if (event.second == 2) {
            const int hit = flickNearby(actor);
            std::printf("P2_UMIMUSHI_FLICK generator=%u frame=%d pikmin=%d\n",
                        generator, event.first, hit);
            std::fflush(stdout);
        }
    }
}

void setPhase(Umi& s) {
    const float duration = clipDuration(s.clip);
    const float len = duration > 0.0f ? duration : 1.0f;
    if (clipLoops(s.clip)) {
        s.phase = s.stateTime / len;
        s.phase -= std::floor(s.phase);
    } else {
        s.phase = s.stateTime / len;
        if (s.phase > 1.0f) s.phase = 1.0f;
    }
}
}

void pc_p2_umimushi_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}

void pc_p2_umimushi_forget(BTeki* actor) {
    actors.erase(static_cast<PelletView*>(actor));
}

float pc_p2_umimushi_param_f(const BTeki* actor, int idx, float fallback) {
    if (!ready || !actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor)))) return fallback;
    if (idx == TPF_Life) return LIFE;
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
                } else {
                    break;
                }
            }
        }
    }

    std::ifstream in("p2-aquatic-actors.txt");
    if (!in) return;
    std::string header;
    int count = 0;
    if (!(in >> header >> count) || header != "P2_AQUATIC_ACTORS_1" || count < 1) return;
    std::map<unsigned, std::string> wanted;
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        std::string species;
        if (!(in >> generator >> species)) return;
        if (species == "UmiMushi") wanted[unsigned(generator)] = species;
    }
    if (wanted.empty()) return;

    std::set<unsigned> found;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor || !actor->mGenerator) continue;
        auto match = wanted.find(actor->mGenerator->_70);
        if (match == wanted.end()) continue;
        if (actor->mTekiType != TEKI_Chappy) {
            std::printf("P2_UMIMUSHI_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::fflush(stdout);
            std::abort();
        }
        Umi& s = actors[static_cast<PelletView*>(actor)];
        s.home = actor->getPosition();
        s.goal = s.home;
        s.heading = actor->getDirection();
        actor->mHealth = LIFE;
        enter(s, UMI_WALK, "run1");
        std::printf("P2_UMIMUSHI_BIND generator=%u source_id=71 visual_only=0\n",
                    actor->mGenerator->_70);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=UmiMushi native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=animation_event water=absent\n",
                    actor->mGenerator->_70, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        std::printf("P2_UMIMUSHI_STATE generator=%u state=walk\n", actor->mGenerator->_70);
        std::fflush(stdout);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_UMIMUSHI_ERROR missing_actor wanted=%zu found=%zu\n",
                    wanted.size(), found.size());
        std::fflush(stdout);
        std::abort();
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
    const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;

    if (actor->mHealth <= 0.0f && s.state != UMI_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_UMIMUSHI_DEAD generator=%u source_id=71 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        setState(actor, s, UMI_DEAD, "dead1");
    }

    s.stateTime += dt;
    switch (s.state) {
    case UMI_WALK: {
        if (distXZ(pos, s.goal) < 50.0f) {
            if (isOutOfTerritory(s, pos, 1.0f) || !isFindTarget(actor, s)) setNextGoal(s);
        }
        walkFunc(actor, s);
        if (isStartFlick(pos)) {
            setState(actor, s, UMI_FLICK, "flick1");
            s.nextState = UMI_WALK;
        } else if (isAttackStart(actor, s)) {
            s.captured = nullptr;
            s.tongueHasPiki = false;
            setState(actor, s, UMI_ATTACK, "attack1");
        } else if (isChangeNavi(actor, s)) {
            setState(actor, s, UMI_FIND, "fsearch1");
        }
        break;
    }
    case UMI_WAIT:
        stop(actor);
        if (s.stateTime < WAIT_TIME) break;
        if (isStartFlick(pos)) {
            setState(actor, s, UMI_FLICK, "flick1");
            s.nextState = UMI_SEARCH;
        } else if (isChangeNavi(actor, s)) {
            setState(actor, s, UMI_FIND, "fsearch1");
        } else if (isAttackStart(actor, s)) {
            s.captured = nullptr;
            s.tongueHasPiki = false;
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
        if (isStartFlick(pos)) {
            setState(actor, s, UMI_FLICK, "flick1");
            s.nextState = UMI_SEARCH;
        } else if (isChangeNavi(actor, s)) {
            setState(actor, s, UMI_FIND, "fsearch1");
        } else if (isAttackStart(actor, s)) {
            s.captured = nullptr;
            s.tongueHasPiki = false;
            setState(actor, s, UMI_ATTACK, "attack1");
        } else if (isNeedTurn(actor, s)) {
            setState(actor, s, UMI_TURN, "sturn1");
        }
        break;
    case UMI_TURN: {
        stop(actor);
        const float residual = turnFunc(actor, s);
        if (isStartFlick(pos)) {
            setState(actor, s, UMI_FLICK, "flick1");
            s.nextState = UMI_TURN;
        } else if (isChangeNavi(actor, s)) {
            setState(actor, s, UMI_FIND, "fsearch1");
        } else if (residual < TURN_END_ANGLE) {
            if (isAttackStart(actor, s)) {
                s.captured = nullptr;
                s.tongueHasPiki = false;
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
            if (s.tongueHasPiki && s.captured) {
                setState(actor, s, UMI_EAT, "eat1");
            } else {
                setState(actor, s, UMI_WAIT, "srun1");
            }
        }
        break;
    case UMI_EAT:
        stop(actor);
        if (s.stateTime >= clipDuration("eat1")) {
            if (s.captured && s.captured->isAlive()) {
                s.captured->stimulate(InteractKill(actor, 0));
                std::printf("P2_UMIMUSHI_EAT generator=%u pikmin=1\n", generator);
                std::fflush(stdout);
            }
            s.captured = nullptr;
            s.tongueHasPiki = false;
            setState(actor, s, UMI_WAIT, "srun1");
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
        if (s.stateTime >= clipDuration("dead1")) actor->die();
        break;
    default:
        break;
    }
    setPhase(s);
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
