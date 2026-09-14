// Family-owned flying-remainder source behavior for the batch-3 P1 Puffy
// Blowhog placement vehicle: Puffy Blowhog (Mar, EnemyID 29). Implements a
// bounded slice of source MarState.cpp: Wait (hover/WaitFly) -> Move (territory
// wander) -> Chase -> Attack (wind) -> Wait, plus Dead. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_flying_assets.py (GPVE01 revision 0, flying manifest).
//
// Source state IDs (Mar.h:20-35): Dead, Wait, Move, Chase, ChaseInside, Attack,
// Fall, Land, Ground, TakeOff, FlyFlick, GroundFlick.
//
// Port adaptations (recorded, not retail-faithful):
//   * The P1 engine has no InteractWind / InteractHanaChirashi. The source wind
//     attack (MarState.cpp:869, Mar.cpp::windTarget 1006) is resolved here as a
//     single InteractFlick blow/stagger on eligible Pikmin at the source attack
//     KEYEVENT_2 frame (attack bank event 50), not every frame. InteractWind's
//     rejection of invincible/Purple/KokeDamage/dead receivers is mapped to
//     isAlive() + the Piki mP2Purple flag; KokeDamage and the P2 invincible
//     state are not representable on the P1 host. Damage is fp24=0 (no HP loss).
//   * The source wind direction is a 3D vector; InteractFlick takes a scalar
//     heading, so the flattened wind heading and the source fp17 shake
//     knockback (200) are used as the P1 blow impulse. The cone geometry
//     (attack start, downward attack direction, fp22 radius, fp23 hit angle)
//     is reproduced from Mar.cpp::windTarget; fp23 is absent from the extracted
//     retail block, so the 45-degree half-angle is a documented port value.
//   * Fall/Land/Ground/TakeOff/FlyFlick/GroundFlick depend on the P2
//     stuck-Pikmin counter (mStuckPikminCount) and the P2 mouth/attach system,
//     which the P1 host does not simulate. They are bounded gaps: fly states
//     hold source flight height (fp01) with the fp05/fp06 vertical swing and
//     ground/shake states are not entered. Death always uses the fly death
//     clip (MARANIM_DeadFly = "dead").
//   * ChaseInside is folded into Chase/territory containment; the source
//     view-angle/FOV search is a documented port adaptation.
// No other lane's module is modified; every hook is a no-op for unregistered actors.
#include "pc_p2_mar.h"
#include "teki.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Generator.h"
#include "MapMgr.h"
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
    MAR_INVALID = -1,
    MAR_DEAD = 0,
    MAR_WAIT = 1,
    MAR_MOVE = 2,
    MAR_CHASE = 3,
    MAR_ATTACK = 5,
};

const char* stateName(State s) {
    switch (s) {
    case MAR_DEAD: return "dead";
    case MAR_WAIT: return "wait";
    case MAR_MOVE: return "move";
    case MAR_CHASE: return "chase";
    case MAR_ATTACK: return "attack";
    default: return "null";
    }
}

// Source enemyparm.txt retail values (flying manifest, Mar general/proper).
constexpr float LIFE = 3000.0f;             // fp00
constexpr float MOVE_SPEED = 120.0f;        // fp06
constexpr float TERRITORY = 400.0f;         // fp09 territory radius
constexpr float HOME_RADIUS = 100.0f;       // fp10 home radius
constexpr float SIGHT = 275.0f;             // fp12 sight radius
constexpr float SHAKE_KNOCKBACK = 200.0f;   // fp17 source shake knockback
constexpr float MAX_ATTACK_RANGE = 200.0f;  // fp20
constexpr float ATTACK_RADIUS = 300.0f;     // fp22 wind radius
constexpr float FLIGHT_HEIGHT = 80.0f;      // proper fp01
constexpr float RISE_FACTOR = 1.0f;         // proper fp02
constexpr float AIR_WAIT_TIME = 3.0f;       // proper fp03
constexpr float VERTICAL_SWING_SPEED = 2.5f; // proper fp05
constexpr float VERTICAL_SWING_WIDTH = 5.0f; // proper fp06
// Port values (not present in the extracted retail block):
constexpr float ATTACK_HIT_ANGLE = 0.785398f; // fp23 half-angle, 45 deg
constexpr float TURN_RATE = 2.0f;             // port turn rate
constexpr float MOVE_TIMEOUT = 7.5f;          // source StateMove::exec 7.5f
constexpr float MOVE_ARRIVE = 100.0f;         // source StateMove::exec 100.0f
constexpr float WIND_DOWN_TILT = -0.85f;      // Mar.cpp::updateEmit
constexpr int FALLBACK_ATTACK_FRAME = 50;     // attack bank event 50:2

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events;
};

struct Mar {
    State state = MAR_WAIT;
    float stateTime = 0.0f;
    float heading = 0.0f;
    float pitchRatio = 0.0f;
    Vector3f home;
    Vector3f moveTarget;
    int attackFrame = FALLBACK_ATTACK_FRAME;
    bool blowFired = false;
    std::set<int> firedEvents;
    std::string clip = "move1";
    float phase = 0.0f;
    bool deadLogged = false;
    float logTimer = 0.0f;
};

std::map<PelletView*, Mar> actors;
std::map<std::string, Clip> clips;
bool ready = false;

float wrapPi(float a) {
    while (a > 3.14159265f) a -= TAU;
    while (a < -3.14159265f) a += TAU;
    return a;
}
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
float groundHeight(const Vector3f& pos) {
    return mapMgr ? mapMgr->getMinY(pos.x, pos.z, true) : pos.y;
}

Creature* nearestTarget(const Vector3f& pos) {
    Creature* best = nullptr;
    float bestSq = SIGHT * SIGHT;
    if (naviMgr) {
        Navi* n = naviMgr->getNavi();
        if (n && n->isAlive()) {
            const Vector3f p = n->getPosition();
            const float dx = p.x - pos.x, dz = p.z - pos.z;
            const float d = dx * dx + dz * dz;
            if (d < bestSq) { bestSq = d; best = n; }
        }
    }
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

void enter(Mar& s, State state, const char* clip) {
    s.state = state;
    s.stateTime = 0.0f;
    s.firedEvents.clear();
    s.blowFired = false;
    if (clip) s.clip = clip;
}

// Source Obj::setHeightVelocity (Mar.cpp:270): hold fp01 flight height above the
// floor with the fp05/fp06 vertical swing while at/above the swing threshold.
void setHeightVelocity(BTeki* a, Mar& s, float dt) {
    const Vector3f pos = a->getPosition();
    const float groundY = groundHeight(pos);
    float idealHeight = FLIGHT_HEIGHT;
    if (pos.y - groundY > idealHeight - VERTICAL_SWING_WIDTH) {
        s.pitchRatio += VERTICAL_SWING_SPEED * dt;
        if (s.pitchRatio > TAU) s.pitchRatio -= TAU;
        idealHeight += VERTICAL_SWING_WIDTH * std::sin(s.pitchRatio);
    }
    a->mVelocity.y = (groundY + idealHeight - pos.y) * RISE_FACTOR;
}

void stopFlying(BTeki* a, Mar& s, float dt) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
    setHeightVelocity(a, s, dt);
}

void turnAndFly(BTeki* a, Mar& s, const Vector3f& target, float dt) {
    const Vector3f pos = a->getPosition();
    const float desired = std::atan2(target.x - pos.x, target.z - pos.z);
    const float maxTurn = TURN_RATE * dt;
    float diff = wrapPi(desired - s.heading);
    if (diff > maxTurn) diff = maxTurn;
    if (diff < -maxTurn) diff = -maxTurn;
    s.heading = wrapPi(s.heading + diff);
    a->setDirection(s.heading);
    const Vector3f drive(std::sin(s.heading) * MOVE_SPEED, 0.0f,
                         std::cos(s.heading) * MOVE_SPEED);
    a->inputDrive(drive);
    a->mVelocity.x = drive.x;
    a->mVelocity.z = drive.z;
    setHeightVelocity(a, s, dt);
}

void setRandTarget(Mar& s) {
    const float outside = TERRITORY > HOME_RADIUS ? TERRITORY - HOME_RADIUS : 0.0f;
    const float radius = gsys->getRand(outside) + HOME_RADIUS;
    const float theta = gsys->getRand(TAU);
    s.moveTarget = Vector3f(s.home.x + radius * std::sin(theta), s.home.y,
                            s.home.z + radius * std::cos(theta));
}

// Source Mar.cpp::windTarget (1006), mapped onto the P1 host:
//   * attack start = the actor position (the P1 Puffy Blowhog has no exposed
//     mouth joint equivalent to Mar's efx matrix translation);
//   * attack direction = normalize(sin(heading), -0.85, cos(heading));
//   * the cone test, slide factor and horizontal wind strength are source;
//   * the knockback impulse is the source fp17 shake knockback because the P1
//     InteractFlick receiver takes a scalar intensity, not a wind vector.
// Eligible receivers: living non-Purple Pikmin (source InteractWind::actPiki
// rejects invincible/Purple/KokeDamage/dead; KokeDamage and the P2 invincible
// state have no P1 equivalent).
void blowWind(BTeki* a, Mar& s) {
    if (!pikiMgr) return;
    const Vector3f start = a->getPosition();
    const float sn = std::sin(s.heading), cs = std::cos(s.heading);
    const float dlen = std::sqrt(sn * sn + WIND_DOWN_TILT * WIND_DOWN_TILT + cs * cs);
    const float dx = sn / dlen, dy = WIND_DOWN_TILT / dlen, dz = cs / dlen;
    const float nlen = std::sqrt(dz * dz + dx * dx);
    if (nlen <= 0.0f) return;
    const float nx = -dz / nlen, nz = dx / nlen;
    // cross = attackNormal x attackDirection, normalised.
    float cx = -nz * dy;
    float cy = nz * dx - nx * dz;
    float cz = nx * dy;
    const float clen = std::sqrt(cx * cx + cy * cy + cz * cz);
    if (clen <= 0.0f) return;
    cx /= clen; cy /= clen; cz /= clen;
    const float slope = std::tan(ATTACK_HIT_ANGLE);
    int hit = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive() || p->mP2Purple) continue;
        const Vector3f q = p->getPosition();
        const float sx = q.x - start.x, sy = q.y - start.y, sz = q.z - start.z;
        const float dot = dx * sx + dy * sy + dz * sz;
        if (dot <= 0.0f || dot >= ATTACK_RADIUS) continue;
        const float coneRadius = dot * slope;
        const float dotsX = nx * sx + nz * sz;
        const float dotsY = cx * sx + cy * sy + cz * sz;
        const float dotsSq = dotsX * dotsX + dotsY * dotsY;
        if (dotsSq >= coneRadius * coneRadius) continue;
        const float slide = std::sqrt(dotsSq) / coneRadius;
        const float strength = (1.0f - slide) * 15.0f + slide * 1.5f;
        const float wx = strength * (dx * dotsY + nx * dotsX);
        const float wz = strength * (dz * dotsY + nz * dotsX);
        const float angle = std::atan2(wx, wz);
        p->stimulate(InteractFlick(a, SHAKE_KNOCKBACK, 0.0f, angle));
        ++hit;
    }
    const unsigned generator = a->mGenerator ? a->mGenerator->_70 : 0u;
    if (hit > 0) {
        std::printf("P2_MAR_BLOW generator=%u pikmin=%d\n", generator, hit);
        std::fflush(stdout);
    }
}

void setPhase(Mar& s) {
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

void pc_p2_mar_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}
void pc_p2_mar_forget(BTeki* actor) { actors.erase(static_cast<PelletView*>(actor)); }

float pc_p2_mar_param_f(const BTeki* actor, int idx, float fallback) {
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

bool pc_p2_mar_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

void pc_p2_mar_setup() {
    pc_p2_mar_reset();
    if (!tekiMgr) return;

    std::ifstream bank("p2-flying-bank.txt");
    if (bank) {
        std::string token;
        if (bank >> token && token == "P2_FLYING_BANK_1") {
            while (bank >> token) {
                if (token == "species") {
                    std::string species, identity;
                    bank >> species >> identity;
                    // Flying install writes `clips <count>`; tolerate the
                    // legacy numeric enemy-id row as well.
                    if (identity == "clips") {
                        int clipCount = 0;
                        bank >> clipCount;
                    }
                } else if (token == "clip") {
                    std::string species, name, events, marker, status, value;
                    long long frames = 0;
                    int poses = 0;
                    if (!(bank >> species >> name >> frames >> events >> marker >> poses)) break;
                    // Flying install writes a literal `status` token before the
                    // value; the legacy bank wrote the value directly.
                    if (!(bank >> value)) break;
                    if (value != "status") status = value;
                    else if (!(bank >> status)) break;
                    if (species == "Mar") {
                        Clip clip;
                        clip.name = name;
                        clip.duration = frames > 0 ? float(frames) / 30.0f : 1.0f;
                        clip.loop = (name == "move1" || name == "wait2");
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

    std::ifstream in("p2-flying-actors.txt");
    if (!in) return;
    std::string header;
    int count = 0;
    if (!(in >> header >> count) || header != "P2_FLYING_ACTORS_1" || count < 1) return;
    std::map<unsigned, std::string> wanted;
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        std::string species;
        if (!(in >> generator >> species)) return;
        if (species == "Mar") wanted[unsigned(generator)] = species;
    }
    if (wanted.empty()) return;

    std::set<unsigned> found;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor || !actor->mGenerator) continue;
        auto match = wanted.find(actor->mGenerator->_70);
        if (match == wanted.end()) continue;
        if (actor->mTekiType != TEKI_Mar) {
            std::printf("P2_MAR_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::abort();
        }
        Mar& s = actors[static_cast<PelletView*>(actor)];
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        s.moveTarget = s.home;
        actor->mHealth = LIFE;
        auto attack = clips.find("attack");
        if (attack != clips.end()) {
            for (const auto& event : attack->second.events) {
                if (event.second == 2) { s.attackFrame = event.first; break; }
            }
        }
        enter(s, MAR_WAIT, "move1");
        std::printf("P2_MAR_BIND generator=%u source_id=29 visual_only=0\n",
                    actor->mGenerator->_70);
        std::printf("P2_MAR_STATE generator=%u state=wait\n", actor->mGenerator->_70);
        std::fflush(stdout);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=Mar native_family=Mar generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=interactflick_wind\n",
                    actor->mGenerator->_70, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_MAR_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::abort();
    }
    ready = true;
}

void pc_p2_mar_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Mar& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;

    if (actor->mHealth <= 0.0f && s.state != MAR_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_MAR_DEAD generator=%u source_id=29 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        enter(s, MAR_DEAD, "dead");
    }

    s.stateTime += dt;
    switch (s.state) {
    case MAR_WAIT: {
        stopFlying(actor, s, dt);
        Creature* target = nearestTarget(pos);
        if (target) {
            std::printf("P2_MAR_STATE generator=%u state=chase\n", generator);
            enter(s, MAR_CHASE, "move1");
            break;
        }
        if (s.stateTime > AIR_WAIT_TIME) {
            setRandTarget(s);
            std::printf("P2_MAR_STATE generator=%u state=move\n", generator);
            enter(s, MAR_MOVE, "move1");
        }
        break;
    }
    case MAR_MOVE: {
        Creature* target = nearestTarget(pos);
        if (target) {
            std::printf("P2_MAR_STATE generator=%u state=chase\n", generator);
            enter(s, MAR_CHASE, "move1");
            break;
        }
        if (distXZ(pos, s.moveTarget) < MOVE_ARRIVE || s.stateTime > MOVE_TIMEOUT
                || distXZ(pos, s.home) > TERRITORY) {
            std::printf("P2_MAR_STATE generator=%u state=wait\n", generator);
            enter(s, MAR_WAIT, "move1");
            break;
        }
        turnAndFly(actor, s, s.moveTarget, dt);
        break;
    }
    case MAR_CHASE: {
        Creature* target = nearestTarget(pos);
        if (!target) {
            std::printf("P2_MAR_STATE generator=%u state=wait\n", generator);
            enter(s, MAR_WAIT, "move1");
            break;
        }
        const Vector3f targetPos = target->getPosition();
        const float angle = std::fabs(wrapPi(std::atan2(targetPos.x - pos.x,
                                                       targetPos.z - pos.z) - s.heading));
        if (distXZ(targetPos, pos) < MAX_ATTACK_RANGE && angle < ATTACK_HIT_ANGLE) {
            std::printf("P2_MAR_STATE generator=%u state=attack\n", generator);
            enter(s, MAR_ATTACK, "attack");
            break;
        }
        if (distXZ(pos, s.home) > TERRITORY) {
            std::printf("P2_MAR_STATE generator=%u state=wait\n", generator);
            enter(s, MAR_WAIT, "move1");
            break;
        }
        turnAndFly(actor, s, targetPos, dt);
        break;
    }
    case MAR_ATTACK: {
        stopFlying(actor, s, dt);
        const float frame = s.stateTime * 30.0f;
        if (!s.blowFired && frame >= float(s.attackFrame)) {
            s.blowFired = true;
            blowWind(actor, s);
        }
        if (s.stateTime >= clipDuration("attack")) {
            std::printf("P2_MAR_STATE generator=%u state=wait\n", generator);
            enter(s, MAR_WAIT, "move1");
        }
        break;
    }
    case MAR_DEAD:
        stopFlying(actor, s, dt);
        if (s.stateTime >= clipDuration("dead")) actor->die();
        break;
    default:
        break;
    }
    setPhase(s);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        std::printf("P2_MAR_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z);
        std::fflush(stdout);
    }
}
