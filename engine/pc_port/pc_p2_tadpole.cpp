// Family-owned aquatic source behavior for the batch-3 placeable host: Tadpole
// (Wogpole, EnemyID 27). Implements the source TadpoleState.cpp six-state FSM
// (Dead 0, Wait 1, Move 2, Amaze 3, Escape 4, Leap 5), the Wait/Move Navi
// targeting and getTargetPosition flee vector (Tadpole.cpp:110), the random
// territory wander (Tadpole.cpp:122) and the dry-land Leap hop
// (createLeapEffect, Tadpole.cpp:168). Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_aquatic_assets.py (GPVE01 rev 0).
//
// ATTACKS / RECEIVERS ARE SOURCE-BACKED N/A: Tadpole's retail general block has
// fp24=0 (zero attack); it is harmless to Pikmin. The source StateAmaze calls
// flickNearbyPikmin with the inherited shake parms, but that is a non-damaging
// panic shake, and this port raises no InteractAttack/InteractFlick at all.
//
// Port adaptations (recorded, not retail-faithful):
//   * The P1 host has no water box. The source gate "Wait/Move/Escape -> Leap
//     when mWaterBox is absent" (TadpoleState.cpp:101,165,264) is deferred to the
//     end of each source state's animation/timer so Wait and Move stay observable
//     in the dry private arena; the leap remains the source dry fallback.
//   * Target detection accepts the nearest Navi or Pikmin (source Wait/Move use
//     getNearestNavi only); view angle is treated as a full hemisphere.
//   * Turn rate is a fixed ~pi rad/s and the vertical hop is a HOP_HEIGHT sine
//     impulse over one leap clip; both are P1-host approximations.
// No other lane's module is modified; every hook is a no-op for unregistered
// actors.
#include "pc_p2_tadpole.h"
#include "teki.h"
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
    TADPOLE_INVALID = -1,
    TADPOLE_DEAD = 0,
    TADPOLE_WAIT = 1,
    TADPOLE_MOVE = 2,
    TADPOLE_AMAZE = 3,
    TADPOLE_ESCAPE = 4,
    TADPOLE_LEAP = 5,
};

const char* stateName(State s) {
    switch (s) {
    case TADPOLE_DEAD: return "dead";
    case TADPOLE_WAIT: return "wait";
    case TADPOLE_MOVE: return "move";
    case TADPOLE_AMAZE: return "amaze";
    case TADPOLE_ESCAPE: return "escape";
    case TADPOLE_LEAP: return "leap";
    default: return "null";
    }
}

// Source values: DiscParms general block (GPVE01 rev 0) + EnemyParmsBase header
// defaults for the fields the Tadpole general block does not override.
constexpr float LIFE = 200.0f;            // general fp00
constexpr float MOVE_SPEED = 180.0f;      // general fp06
constexpr float TERRITORY = 200.0f;       // general fp09
constexpr float HOME_RADIUS = 50.0f;      // general fp10
constexpr float SIGHT = 200.0f;           // general fp12
constexpr float PITTER_SPEED = 20.0f;     // proper fp01
constexpr float WAIT_TIME = 3.0f;         // StateWait/StateMove mStateTimer > 3.0
constexpr float MOVE_TIME = 3.0f;
constexpr float REACH_SQ = 100.0f;        // sqrDistanceXZ < 100 in source
constexpr float ESCAPE_TIME = 1.0f;       // port bound (move1 clip length used when known)
constexpr float TURN_RATE = 3.14159265f;  // port adaptation
constexpr float HOP_HEIGHT = 16.0f;       // port adaptation
constexpr float HOP_TIME = 0.6f;          // port adaptation
constexpr float PI_F = 3.14159265f;

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events; // source frame -> event code
};

struct Tadpole {
    State state = TADPOLE_WAIT;
    float stateTime = 0.0f;
    float heading = 0.0f;
    float hopGroundY = 0.0f;
    Vector3f home;
    Vector3f targetPosition;
    bool targetValid = false;
    unsigned rng = 1;
    std::set<int> firedEvents;
    std::string clip = "wait1";
    float phase = 0.0f;
    bool deadLogged = false;
    float logTimer = 0.0f;
};

std::map<PelletView*, Tadpole> actors;
std::map<std::string, Clip> clips;
bool ready = false;

unsigned nextRand(Tadpole& s) {
    s.rng = s.rng * 1664525u + 1013904223u;
    return s.rng >> 8;
}
float rand01(Tadpole& s) { return float(nextRand(s) & 0xffff) / 65535.0f; }
float randRange(Tadpole& s, float lo, float hi) { return lo + (hi - lo) * rand01(s); }

float wrapPi(float a) {
    while (a > PI_F) a -= 2.0f * PI_F;
    while (a < -PI_F) a += 2.0f * PI_F;
    return a;
}
float distXZsq(const Vector3f& a, const Vector3f& b) {
    const float dx = a.x - b.x, dz = a.z - b.z;
    return dx * dx + dz * dz;
}
float distXZ(const Vector3f& a, const Vector3f& b) { return std::sqrt(distXZsq(a, b)); }

float clipDuration(const std::string& name) {
    auto it = clips.find(name);
    return it == clips.end() ? 1.0f : it->second.duration;
}
bool clipLoops(const std::string& name) {
    auto it = clips.find(name);
    return it != clips.end() && it->second.loop;
}

void enter(Tadpole& s, State state, const char* clip) {
    s.state = state;
    s.stateTime = 0.0f;
    s.firedEvents.clear();
    if (clip) s.clip = clip;
}

// Enumerate the nearest live Navi or Pikmin inside the source sight radius.
bool nearestTargetPos(const Vector3f& pos, Vector3f& out) {
    bool found = false;
    float bestSq = SIGHT * SIGHT;
    if (naviMgr) {
        Navi* n = naviMgr->getNavi();
        if (n && n->isAlive()) {
            const Vector3f p = n->getPosition();
            const float d = distXZsq(p, pos);
            if (d < bestSq) { bestSq = d; out = p; found = true; }
        }
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            const Vector3f q = p->getPosition();
            const float d = distXZsq(q, pos);
            if (d < bestSq) { bestSq = d; out = q; found = true; }
        }
    }
    return found;
}

// Source Obj::setRandTarget (Tadpole.cpp:122): a random point in the
// [home, territory] annulus around home, biased away from the home vector.
void setRandTarget(Tadpole& s, const Vector3f& pos, bool check) {
    const float p1 = check ? 0.0f : (TERRITORY - HOME_RADIUS);
    const float radius = randRange(s, 0.0f, p1) + HOME_RADIUS;
    float angle = std::atan2(pos.x - s.home.x, pos.z - s.home.z);
    angle = randRange(s, 0.0f, PI_F) + angle + PI_F * 0.5f;
    s.targetPosition.x = radius * std::sin(angle) + s.home.x;
    s.targetPosition.y = s.home.y;
    s.targetPosition.z = radius * std::cos(angle) + s.home.z;
    s.targetValid = true;
}

// Source Obj::getTargetPosition (Tadpole.cpp:142): one move-speed step directly
// away from the target, clamped to the territory radius around home.
Vector3f getTargetPosition(const Tadpole& s, const Vector3f& pos, const Vector3f& target) {
    Vector3f sep = pos - target;
    sep.y = 0.0f;
    const float len = std::sqrt(sep.x * sep.x + sep.z * sep.z);
    if (len > 0.0001f) { sep.x /= len; sep.z /= len; }
    else { sep.x = 0.0f; sep.z = 0.0f; }
    sep.x = sep.x * MOVE_SPEED + pos.x;
    sep.z = sep.z * MOVE_SPEED + pos.z;
    sep.y = pos.y;
    if (distXZsq(sep, s.home) > TERRITORY * TERRITORY) {
        Vector3f dir = sep - s.home;
        dir.y = 0.0f;
        const float d = std::sqrt(dir.x * dir.x + dir.z * dir.z);
        if (d > 0.0001f) { dir.x /= d; dir.z /= d; }
        sep.x = s.home.x + dir.x * TERRITORY;
        sep.z = s.home.z + dir.z * TERRITORY;
    }
    return sep;
}

void stop(BTeki* a) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.y = 0.0f;
    a->mVelocity.z = 0.0f;
}

void walkToTarget(BTeki* a, Tadpole& s, const Vector3f& target, float speed, float dt) {
    const Vector3f pos = a->getPosition();
    const float desired = std::atan2(target.x - pos.x, target.z - pos.z);
    const float maxTurn = TURN_RATE * dt;
    float diff = wrapPi(desired - s.heading);
    if (diff > maxTurn) diff = maxTurn;
    if (diff < -maxTurn) diff = -maxTurn;
    s.heading = wrapPi(s.heading + diff);
    a->setDirection(s.heading);
    const Vector3f drive(std::sin(s.heading) * speed, 0.0f, std::cos(s.heading) * speed);
    a->inputDrive(drive);
    a->mVelocity.x = drive.x;
    a->mVelocity.z = drive.z;
}

void setPhase(Tadpole& s) {
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

// Animation key-event evidence. Tadpole has no damage events; the only effect
// hook is the source createLeapEffect at the Amaze/Leap/Dead key events.
void fireEvents(BTeki* a, Tadpole& s) {
    auto it = clips.find(s.clip);
    if (it == clips.end()) return;
    const unsigned generator = a->mGenerator ? a->mGenerator->_70 : 0u;
    for (const auto& event : it->second.events) {
        if (s.firedEvents.count(event.first)) continue;
        if (s.stateTime < event.first / 30.0f) continue;
        s.firedEvents.insert(event.first);
        if (event.second == 2 || event.second == 3) {
            if (s.state == TADPOLE_LEAP || s.state == TADPOLE_AMAZE) {
                std::printf("P2_TADPOLE_LEAP generator=%u state=%s frame=%d\n",
                            generator, stateName(s.state), event.first);
            } else if (s.state == TADPOLE_DEAD) {
                std::printf("P2_TADPOLE_DEAD_EFFECT generator=%u frame=%d\n",
                            generator, event.first);
            }
        }
    }
}
}

void pc_p2_tadpole_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}

void pc_p2_tadpole_forget(BTeki* actor) {
    actors.erase(static_cast<PelletView*>(actor));
}

float pc_p2_tadpole_param_f(const BTeki* actor, int idx, float fallback) {
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
        return 0.0f; // harmless: zero attack/receiver surface
    default:
        return fallback;
    }
}

bool pc_p2_tadpole_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

void pc_p2_tadpole_setup() {
    pc_p2_tadpole_reset();
    if (!tekiMgr) return;

    // Clip durations and source key-event frames from the validated aquatic bank.
    std::ifstream bank("p2-aquatic-bank.txt");
    if (bank) {
        std::string token;
        if (bank >> token && token == "P2_AQUATIC_BANK_1") {
            while (bank >> token) {
                if (token == "species") {
                    std::string species, id;
                    bank >> species >> id;
                } else if (token == "clip") {
                    std::string species, name, frames, events, marker, poses, status;
                    bank >> species >> name >> frames >> events >> marker >> poses >> status;
                    if (species == "Tadpole") {
                        Clip clip;
                        clip.name = name;
                        const double sourceFrames = std::atof(frames.c_str());
                        clip.duration = sourceFrames > 0.0 ? float(sourceFrames) / 30.0f : 1.0f;
                        clip.loop = (name == "wait1" || name == "move1" || name == "piti1");
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
        if (species == "Tadpole") wanted[unsigned(generator)] = species;
    }
    if (wanted.empty()) return;

    std::set<unsigned> found;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor || !actor->mGenerator) continue;
        auto match = wanted.find(actor->mGenerator->_70);
        if (match == wanted.end()) continue;
        if (actor->mTekiType != TEKI_Otama) {
            std::printf("P2_TADPOLE_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::fflush(stdout);
            std::abort();
        }
        Tadpole& s = actors[static_cast<PelletView*>(actor)];
        s.rng = (actor->mGenerator->_70 * 2654435761u) | 1u;
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        s.hopGroundY = s.home.y;
        s.targetPosition = s.home;
        actor->mHealth = LIFE;
        enter(s, TADPOLE_WAIT, "wait1");
        std::printf("P2_TADPOLE_BIND generator=%u source_id=27 visual_only=0\n",
                    actor->mGenerator->_70);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=Tadpole native_family=Otama generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented water=absent attack=none\n",
                    actor->mGenerator->_70, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        std::fflush(stdout);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_TADPOLE_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::fflush(stdout);
        std::abort();
    }
    ready = true;
}

void pc_p2_tadpole_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Tadpole& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;

    if (actor->mHealth <= 0.0f && s.state != TADPOLE_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_TADPOLE_DEAD generator=%u source_id=27 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        enter(s, TADPOLE_DEAD, "dead");
    }

    Vector3f target;
    const bool targetNear = s.state != TADPOLE_DEAD && nearestTargetPos(pos, target);

    s.stateTime += dt;
    switch (s.state) {
    case TADPOLE_WAIT:
        stop(actor);
        if (targetNear) {
            s.targetPosition = getTargetPosition(s, pos, target);
            s.targetValid = true;
            std::printf("P2_TADPOLE_STATE generator=%u state=amaze\n", generator);
            enter(s, TADPOLE_AMAZE, "waitact1");
        } else if (s.stateTime >= WAIT_TIME || s.stateTime >= clipDuration("wait1")) {
            setRandTarget(s, pos, false);
            std::printf("P2_TADPOLE_STATE generator=%u state=move\n", generator);
            enter(s, TADPOLE_MOVE, "move1");
        }
        break;
    case TADPOLE_MOVE: {
        if (!s.targetValid) setRandTarget(s, pos, false);
        walkToTarget(actor, s, s.targetPosition, MOVE_SPEED, dt);
        if (targetNear) {
            s.targetPosition = getTargetPosition(s, pos, target);
            std::printf("P2_TADPOLE_STATE generator=%u state=amaze\n", generator);
            enter(s, TADPOLE_AMAZE, "waitact1");
        } else if (distXZsq(pos, s.targetPosition) < REACH_SQ
                || s.stateTime >= MOVE_TIME || s.stateTime >= clipDuration("move1")) {
            stop(actor);
            s.hopGroundY = actor->getPosition().y;
            std::printf("P2_TADPOLE_STATE generator=%u state=leap\n", generator);
            enter(s, TADPOLE_LEAP, "piti1");
        }
        break;
    }
    case TADPOLE_AMAZE:
        stop(actor);
        if (s.stateTime >= clipDuration("waitact1")) {
            std::printf("P2_TADPOLE_STATE generator=%u state=escape\n", generator);
            enter(s, TADPOLE_ESCAPE, "move1");
        }
        break;
    case TADPOLE_ESCAPE:
        if (targetNear) {
            s.targetPosition = getTargetPosition(s, pos, target);
            walkToTarget(actor, s, s.targetPosition, MOVE_SPEED, dt);
        } else {
            walkToTarget(actor, s, s.home, MOVE_SPEED, dt);
        }
        if (s.stateTime >= clipDuration("move1") || s.stateTime >= ESCAPE_TIME) {
            stop(actor);
            s.hopGroundY = actor->getPosition().y;
            std::printf("P2_TADPOLE_STATE generator=%u state=leap\n", generator);
            enter(s, TADPOLE_LEAP, "piti1");
        }
        break;
    case TADPOLE_LEAP: {
        // Source dry fallback: pitter-patter toward the random territory target
        // with the proper fp01 speed while the vertical hop arc plays.
        if (!s.targetValid) setRandTarget(s, pos, true);
        if (targetNear) {
            s.targetPosition = getTargetPosition(s, pos, target);
        }
        const float desired = std::atan2(s.targetPosition.x - pos.x, s.targetPosition.z - pos.z);
        s.heading = wrapPi(desired);
        actor->setDirection(s.heading);
        const Vector3f drive(std::sin(s.heading) * PITTER_SPEED, 0.0f,
                             std::cos(s.heading) * PITTER_SPEED);
        actor->inputDrive(drive);
        actor->mVelocity.x = drive.x;
        actor->mVelocity.z = drive.z;
        actor->mVelocity.y = 0.0f;
        const float dur = clipDuration("piti1") > HOP_TIME ? clipDuration("piti1") : HOP_TIME;
        float u = s.stateTime / dur;
        if (u > 1.0f) u = 1.0f;
        actor->getPosition().y = s.hopGroundY + HOP_HEIGHT * std::sin(PI_F * u);
        if (s.stateTime >= dur) {
            actor->getPosition().y = s.hopGroundY;
            if (targetNear) {
                s.targetPosition = getTargetPosition(s, pos, target);
                s.targetValid = true;
                std::printf("P2_TADPOLE_STATE generator=%u state=amaze\n", generator);
                enter(s, TADPOLE_AMAZE, "waitact1");
            } else {
                std::printf("P2_TADPOLE_STATE generator=%u state=wait\n", generator);
                enter(s, TADPOLE_WAIT, "wait1");
            }
        }
        break;
    }
    case TADPOLE_DEAD:
        stop(actor);
        if (s.stateTime >= clipDuration("dead")) actor->die();
        break;
    default:
        break;
    }
    setPhase(s);
    fireEvents(actor, s);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        const Vector3f now = actor->getPosition();
        std::printf("P2_TADPOLE_POS generator=%u state=%s clip=%s phase=%.2f "
                    "x=%.2f y=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase,
                    now.x, now.y, now.z);
        std::fflush(stdout);
    }
}
