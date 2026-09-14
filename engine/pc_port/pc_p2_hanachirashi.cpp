// Family-owned flying-remainder source behavior for the batch-3 P1 Puffy
// Blowhog placement vehicle: Withering Blowhog (Hanachirashi, EnemyID 55).
// Implements a bounded slice of source HanachirashiState.cpp: Wait (hover/
// WaitFly) -> Move (territory wander) -> Chase -> Attack (withering wind) ->
// Laugh -> Wait, plus Dead. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_flying_assets.py (GPVE01 revision 0, flying manifest).
//
// Source state IDs (Hanachirashi.h:27-43): Dead, Wait, Move, Chase,
// ChaseInside, Attack, Fall, Land, Ground, TakeOff, FlyFlick, GroundFlick,
// Laugh.
//
// Port adaptations (recorded, not retail-faithful):
//   * The P1 engine has no InteractWind / InteractHanaChirashi. The source
//     withering wind (Hanachirashi.cpp::windTarget 752; StateAttack::exec 877)
//     is resolved here as a single InteractFlick blow/stagger on eligible
//     Pikmin at the source attack KEYEVENT_2 frame (attack bank event 50:2),
//     not every frame. The source windTarget runs each active frame with a
//     radius ramped by mWindScaleTimer; the single-frame port uses the full
//     fp22 attack radius. InteractHanaChirashi::actPiki rejects invincible/
//     Purple/KokeDamage/dead receivers; on the P1 host that maps to isAlive(),
//     with the P2 invincible and KokeDamage states not representable. A Purple
//     receiver in the cone strips a bud/flower to Leaf (mHappa = Leaf) and is
//     not blown, matching InteractHanaChirashi. Damage is fp24=0 (no HP loss).
//   * The source wind direction is a 3D vector with a vertical component
//     ((1-slide)*50 + slide*10); InteractFlick takes a scalar heading, so the
//     flattened wind heading and the source fp17 shake knockback (150) are used
//     as the P1 blow impulse. The cone geometry uses the source attack
//     direction normalize(sin, -0.85, cos), fp22 radius and the 45-degree
//     half-angle (fp23 is absent from the extracted retail block, so the
//     half-angle is a documented port value).
//   * A successful windTarget selects Laugh at the source attack END
//     (HanachirashiState.cpp:883/897); this port tracks any affected receiver
//     as the success bit.
//   * Fall/Land/Ground/TakeOff/FlyFlick/GroundFlick depend on the P2
//     stuck-Pikmin counter (mStuckPikminCount) and the P2 mouth/attach system,
//     which the P1 host does not simulate. They are bounded gaps: fly states
//     hold source flight height (fp01=70) with the fp05/fp06 vertical swing and
//     ground/shake states are not entered. Death always uses the fly death
//     clip (HANACHIANIM_DeadFly = "dead").
//   * ChaseInside is folded into Chase/territory containment; the source
//     view-angle/FOV search is a documented port adaptation.
// No other lane's module is modified; every hook is a no-op for unregistered actors.
#include "pc_p2_hanachirashi.h"
#include "teki.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Generator.h"
#include "MapMgr.h"
#include "GlobalGameOptions.h"
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
    HANA_INVALID = -1,
    HANA_DEAD = 0,
    HANA_WAIT = 1,
    HANA_MOVE = 2,
    HANA_CHASE = 3,
    HANA_ATTACK = 5,
    HANA_LAUGH = 12,
};

const char* stateName(State s) {
    switch (s) {
    case HANA_DEAD: return "dead";
    case HANA_WAIT: return "wait";
    case HANA_MOVE: return "move";
    case HANA_CHASE: return "chase";
    case HANA_ATTACK: return "attack";
    case HANA_LAUGH: return "laugh";
    default: return "null";
    }
}

// Source enemyparm.txt retail values (flying manifest, Hanachirashi block).
constexpr float LIFE = 1800.0f;              // general fp00
constexpr float MOVE_SPEED = 100.0f;         // general fp06
constexpr float TERRITORY = 250.0f;          // general fp09 territory radius
constexpr float HOME_RADIUS = 100.0f;        // general fp10 home radius
constexpr float SIGHT = 275.0f;              // general fp12 sight radius
constexpr float SHAKE_KNOCKBACK = 150.0f;    // general fp17 source shake knockback
constexpr float MAX_ATTACK_RANGE = 200.0f;   // general fp20
constexpr float ATTACK_RADIUS = 300.0f;      // general fp22 wind radius
constexpr float FLIGHT_HEIGHT = 70.0f;       // proper fp01
constexpr float RISE_FACTOR = 1.0f;          // proper fp02
constexpr float AIR_WAIT_TIME = 3.0f;        // proper fp03
constexpr float VERTICAL_SWING_SPEED = 2.5f; // proper fp05
constexpr float VERTICAL_SWING_WIDTH = 5.0f; // proper fp06
// Port values (not present in the extracted retail block):
constexpr float ATTACK_HIT_ANGLE = 0.785398f; // fp23 half-angle, 45 deg
constexpr float TURN_RATE = 2.0f;             // port turn rate
constexpr float MOVE_TIMEOUT = 7.5f;          // source StateMove::exec 7.5f
constexpr float MOVE_ARRIVE = 100.0f;         // source StateMove::exec 100.0f
constexpr float WIND_DOWN_TILT = -0.85f;      // Hanachirashi.cpp::updateEmit
constexpr int FALLBACK_ATTACK_FRAME = 50;     // attack bank event 50:2

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events;
};

struct Hana {
    State state = HANA_WAIT;
    float stateTime = 0.0f;
    float heading = 0.0f;
    float pitchRatio = 0.0f;
    Vector3f home;
    Vector3f moveTarget;
    int attackFrame = FALLBACK_ATTACK_FRAME;
    bool blowFired = false;
    bool windHit = false;
    std::set<int> firedEvents;
    std::string clip = "move1";
    float phase = 0.0f;
    bool deadLogged = false;
    float logTimer = 0.0f;
};

std::map<PelletView*, Hana> actors;
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

void enter(Hana& s, State state, const char* clip) {
    s.state = state;
    s.stateTime = 0.0f;
    s.firedEvents.clear();
    s.blowFired = false;
    s.windHit = false;
    if (clip) s.clip = clip;
}

// Source Obj::setHeightVelocity (Hanachirashi.cpp:271): hold fp01 flight height
// above the floor with the fp05/fp06 vertical swing while at/above the swing
// threshold.
void setHeightVelocity(BTeki* a, Hana& s, float dt) {
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

void stopFlying(BTeki* a, Hana& s, float dt) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
    setHeightVelocity(a, s, dt);
}

void turnAndFly(BTeki* a, Hana& s, const Vector3f& target, float dt) {
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

void setRandTarget(Hana& s) {
    const float outside = TERRITORY > HOME_RADIUS ? TERRITORY - HOME_RADIUS : 0.0f;
    const float radius = gsys->getRand(outside) + HOME_RADIUS;
    const float theta = gsys->getRand(TAU);
    s.moveTarget = Vector3f(s.home.x + radius * std::sin(theta), s.home.y,
                            s.home.z + radius * std::cos(theta));
}

// Source Hanachirashi.cpp::windTarget (752), mapped onto the P1 host:
//   * attack start = the actor position (the P1 Puffy Blowhog has no exposed
//     mouth joint equivalent to Hanachirashi's mEfxPosition/"hana3" joint);
//   * attack direction = normalize(sin(heading), -0.85, cos(heading));
//   * the cone test, slide factor and horizontal wind strength are source;
//   * the knockback impulse is the source fp17 shake knockback because the P1
//     InteractFlick receiver takes a scalar intensity, not a wind vector.
// Receiver boundary (source InteractHanaChirashi::actPiki, interactPiki.cpp:278):
// living receivers; a Purple bud/flower in the cone strips to Leaf and is not
// blown; other eligible Pikmin are blown (staggered). KokeDamage and the P2
// invincible state have no P1 equivalent.
bool blowWind(BTeki* a, Hana& s) {
    if (!pikiMgr) return false;
    const Vector3f start = a->getPosition();
    const float sn = std::sin(s.heading), cs = std::cos(s.heading);
    const float dlen = std::sqrt(sn * sn + WIND_DOWN_TILT * WIND_DOWN_TILT + cs * cs);
    const float dx = sn / dlen, dy = WIND_DOWN_TILT / dlen, dz = cs / dlen;
    const float nlen = std::sqrt(dz * dz + dx * dx);
    if (nlen <= 0.0f) return false;
    const float nx = -dz / nlen, nz = dx / nlen;
    // cross = attackNormal x attackDirection, normalised.
    float cx = -nz * dy;
    float cy = nz * dx - nx * dz;
    float cz = nx * dy;
    const float clen = std::sqrt(cx * cx + cy * cy + cz * cz);
    if (clen <= 0.0f) return false;
    cx /= clen; cy /= clen; cz /= clen;
    const float slope = std::tan(ATTACK_HIT_ANGLE);
    int blown = 0;
    int stripped = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        const Vector3f q = p->getPosition();
        const float sx = q.x - start.x, sy = q.y - start.y, sz = q.z - start.z;
        const float dot = dx * sx + dy * sy + dz * sz;
        if (dot <= 0.0f || dot >= ATTACK_RADIUS) continue;
        const float coneRadius = dot * slope;
        const float dotsX = nx * sx + nz * sz;
        const float dotsY = cx * sx + cy * sy + cz * sz;
        const float dotsSq = dotsX * dotsX + dotsY * dotsY;
        if (dotsSq >= coneRadius * coneRadius) continue;
        if (p->mP2Purple) {
            if (p->mHappa >= Bud) { p->mHappa = Leaf; ++stripped; }
            continue;
        }
        const float slide = std::sqrt(dotsSq) / coneRadius;
        const float strength = (1.0f - slide) * 5.0f + slide;
        const float wx = strength * (dx * dotsY + nx * dotsX);
        const float wz = strength * (dz * dotsY + nz * dotsX);
        const float angle = std::atan2(wx, wz);
        p->stimulate(InteractFlick(a, SHAKE_KNOCKBACK, 0.0f, angle));
        ++blown;
    }
    const int affected = blown + stripped;
    const unsigned generator = a->mGenerator ? a->mGenerator->_70 : 0u;
    if (affected > 0) {
        std::printf("P2_HANACHIRASHI_BLOW generator=%u pikmin=%d\n", generator, affected);
        std::fflush(stdout);
    }
    s.windHit = affected > 0;
    return s.windHit;
}

void setPhase(Hana& s) {
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

void pc_p2_hanachirashi_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}
void pc_p2_hanachirashi_forget(BTeki* actor) { actors.erase(static_cast<PelletView*>(actor)); }

float pc_p2_hanachirashi_param_f(const BTeki* actor, int idx, float fallback) {
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

bool pc_p2_hanachirashi_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

void pc_p2_hanachirashi_setup() {
    pc_p2_hanachirashi_reset();
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
                    if (species == "Hanachirashi") {
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
        if (species == "Hanachirashi") wanted[unsigned(generator)] = species;
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
            std::printf("P2_HANACHIRASHI_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::abort();
        }
        Hana& s = actors[static_cast<PelletView*>(actor)];
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
        enter(s, HANA_WAIT, "move1");
        std::printf("P2_HANACHIRASHI_BIND generator=%u source_id=55 visual_only=0\n",
                    actor->mGenerator->_70);
        std::printf("P2_HANACHIRASHI_STATE generator=%u state=wait\n", actor->mGenerator->_70);
        std::fflush(stdout);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=Hanachirashi native_family=Mar generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=interactflick_wither\n",
                    actor->mGenerator->_70, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_HANACHIRASHI_ERROR missing_actor wanted=%zu found=%zu\n",
                    wanted.size(), found.size());
        std::abort();
    }
    ready = true;
}

void pc_p2_hanachirashi_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Hana& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;

    if (actor->mHealth <= 0.0f && s.state != HANA_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_HANACHIRASHI_DEAD generator=%u source_id=55 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        enter(s, HANA_DEAD, "dead");
    }

    s.stateTime += dt;
    switch (s.state) {
    case HANA_WAIT: {
        stopFlying(actor, s, dt);
        Creature* target = nearestTarget(pos);
        if (target) {
            std::printf("P2_HANACHIRASHI_STATE generator=%u state=chase\n", generator);
            enter(s, HANA_CHASE, "move1");
            break;
        }
        if (s.stateTime > AIR_WAIT_TIME) {
            setRandTarget(s);
            std::printf("P2_HANACHIRASHI_STATE generator=%u state=move\n", generator);
            enter(s, HANA_MOVE, "move1");
        }
        break;
    }
    case HANA_MOVE: {
        Creature* target = nearestTarget(pos);
        if (target) {
            std::printf("P2_HANACHIRASHI_STATE generator=%u state=chase\n", generator);
            enter(s, HANA_CHASE, "move1");
            break;
        }
        if (distXZ(pos, s.moveTarget) < MOVE_ARRIVE || s.stateTime > MOVE_TIMEOUT
                || distXZ(pos, s.home) > TERRITORY) {
            std::printf("P2_HANACHIRASHI_STATE generator=%u state=wait\n", generator);
            enter(s, HANA_WAIT, "move1");
            break;
        }
        turnAndFly(actor, s, s.moveTarget, dt);
        break;
    }
    case HANA_CHASE: {
        Creature* target = nearestTarget(pos);
        if (!target) {
            std::printf("P2_HANACHIRASHI_STATE generator=%u state=wait\n", generator);
            enter(s, HANA_WAIT, "move1");
            break;
        }
        const Vector3f targetPos = target->getPosition();
        const float angle = std::fabs(wrapPi(std::atan2(targetPos.x - pos.x,
                                                       targetPos.z - pos.z) - s.heading));
        if (distXZ(targetPos, pos) < MAX_ATTACK_RANGE && angle < ATTACK_HIT_ANGLE) {
            std::printf("P2_HANACHIRASHI_STATE generator=%u state=attack\n", generator);
            enter(s, HANA_ATTACK, "attack");
            break;
        }
        if (distXZ(pos, s.home) > TERRITORY) {
            std::printf("P2_HANACHIRASHI_STATE generator=%u state=wait\n", generator);
            enter(s, HANA_WAIT, "move1");
            break;
        }
        turnAndFly(actor, s, targetPos, dt);
        break;
    }
    case HANA_ATTACK: {
        stopFlying(actor, s, dt);
        const float frame = s.stateTime * 30.0f;
        if (!s.blowFired && frame >= float(s.attackFrame)) {
            s.blowFired = true;
            blowWind(actor, s);
        }
        if (s.stateTime >= clipDuration("attack")) {
            if (s.windHit) {
                std::printf("P2_HANACHIRASHI_STATE generator=%u state=laugh\n", generator);
                enter(s, HANA_LAUGH, "laugh");
            } else {
                std::printf("P2_HANACHIRASHI_STATE generator=%u state=wait\n", generator);
                enter(s, HANA_WAIT, "move1");
            }
        }
        break;
    }
    case HANA_LAUGH: {
        stopFlying(actor, s, dt);
        if (s.stateTime >= clipDuration("laugh")) {
            Creature* target = nearestTarget(pos);
            if (target && distXZ(target->getPosition(), pos) < MAX_ATTACK_RANGE) {
                std::printf("P2_HANACHIRASHI_STATE generator=%u state=attack\n", generator);
                enter(s, HANA_ATTACK, "attack");
            } else {
                std::printf("P2_HANACHIRASHI_STATE generator=%u state=wait\n", generator);
                enter(s, HANA_WAIT, "move1");
            }
        }
        break;
    }
    case HANA_DEAD:
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
        std::printf("P2_HANACHIRASHI_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z);
        std::fflush(stdout);
    }
}
