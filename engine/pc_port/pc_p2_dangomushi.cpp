// Family-owned snagret-family source behavior for the batch-3 Chappy placement
// vehicle: Segmented Crawbster (DangoMushi, EnemyID 94). Implements the source
// DangoMushiState.cpp segmented roller FSM: Stay -> Appear (fly) -> Wait ->
// Move -> Attack (ball roll) -> Turn (crash) -> Recover -> Flick (attack_2) ->
// Wait, plus Dead. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_snagret_assets.py (GPVE01 revision 0, DangoMushi
// DISC_PARMS). The source states, animation IDs and key-event streams are the
// audited disc values (DangoMushi.h:23-35, DangoMushi.h:210-222,
// EXPECTED_EVENTS['DangoMushi']).
//
// DangoMushi is a standalone `EnemyBase`/`EnemyBlendAnimatorBase` boss, not a
// snagret and not a `ChappyBase`; it shares this batch-3 host only as a
// placement vehicle (expected native type TEKI_Chappy) so the source FSM can
// run on the P1 engine.
//
// Port adaptations (recorded, not retail-faithful):
//   * The roll contact (source Obj::collisionCallback InteractPress while
//     mIsRolling) has no P1 collision-callback path here. It is resolved as a
//     single InteractFlick knockback+damage on the first Pikmin/Navi inside the
//     source fp22=100 hit radius after the roll starts, once per roll, instead
//     of every frame; the source InteractPress crush is not representable.
//   * The source only enters StateTurn from Obj::wallCallback (roll speed > 100
//     and >30 deg into a wall normal). The P1 host exposes no wall normal, so a
//     roll enters Turn when it leaves the source fp09=150 territory or after
//     the bounded roll timeout; the crash effects and the Turn LOOP_START
//     vulnerability window (DangoMushiState.cpp:530) are not reproduced.
//   * The Flick arm sweep (Obj::flickHandCollision) is resolved as one
//     InteractFlick per Flick state at the attack_2 KEYEVENT_2 arm-swing frame
//     (26), not per frame; the source Navi wither and Purple-crab rules are not
//     representable.
//   * The P2 invulnerability/ModelHidden state flags, the falling Rock/Egg
//     child spawner (DangoMushi.cpp:649-776) and the dangomushi.brk material
//     loop (DangoMushi.cpp:106-134) are P2-only and are not reproduced.
//   * Walk uses the source fp08=0.05 turn rate clamped to fp28=5 deg; the roll
//     uses proper fp02=0.03 / fp03=3 deg and fp01=200. Target search is a full
//     hemisphere (the source fp13 view-angle gate is not applied). When the
//     installed p2-snagret-bank.txt is absent the audited retail event frames
//     are used with 1 s fallback clip durations.
// No other lane's module is modified; every hook is a no-op for unregistered
// actors.
#include "pc_p2_dangomushi.h"
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
    DANGO_DEAD = 0,
    DANGO_STAY = 1,
    DANGO_APPEAR = 2,
    DANGO_WAIT = 3,
    DANGO_MOVE = 4,
    DANGO_ATTACK = 5,
    DANGO_TURN = 6,
    DANGO_RECOVER = 7,
    DANGO_FLICK = 8,
};

const char* stateName(State s) {
    switch (s) {
    case DANGO_DEAD: return "dead";
    case DANGO_STAY: return "stay";
    case DANGO_APPEAR: return "appear";
    case DANGO_WAIT: return "wait";
    case DANGO_MOVE: return "move";
    case DANGO_ATTACK: return "attack";
    case DANGO_TURN: return "turn";
    case DANGO_RECOVER: return "recover";
    case DANGO_FLICK: return "flick";
    default: return "null";
    }
}

// Source enemyparm.txt retail values (snagret manifest, DangoMushi general).
constexpr float LIFE = 3000.0f;              // fp00
constexpr float MOVE_SPEED = 50.0f;          // fp06
constexpr float TERRITORY = 150.0f;          // fp09 territory radius
constexpr float HOME_RADIUS = 100.0f;        // fp10 home radius
constexpr float PRIVATE_RADIUS = 150.0f;     // fp11 Stay wake distance
constexpr float SIGHT = 500.0f;              // fp12 sight radius
constexpr float ATTACK_RANGE = 300.0f;       // fp20 max attack range
constexpr float ATTACK_ANGLE = 0.261799f;    // fp21 15 deg
constexpr float ATTACK_DAMAGE = 10.0f;       // fp24 attack power
constexpr float SHAKE_KNOCKBACK = 200.0f;    // fp17 shake knockback
constexpr float CONTACT_RADIUS = 100.0f;     // fp22 attack hit radius (roll body)
constexpr float WALK_TURN_RATE = 0.05f;      // fp08 rotation speed rate
constexpr float WALK_MAX_TURN = 0.0872665f;  // fp28 5 deg
// Source proper-parm retail values (DangoMushi proper block).
constexpr float ROLL_SPEED = 200.0f;         // fp01 rolling movement speed
constexpr float ROLL_TURN_ACCEL = 0.03f;     // fp02 rolling rotation speed rate
constexpr float ROLL_TURN_SPEED = 0.0523599f; // fp03 rolling max turn 3 deg
constexpr float FLIP_TIME = 7.5f;            // fp10 (disc omits it; header default)
// Source state timers (DangoMushiState.cpp).
constexpr float WAIT_TIME = 3.0f;            // StateWait::exec 3.0f
constexpr float MOVE_TIMEOUT = 10.0f;        // StateMove::exec 10.0f
constexpr float ATTACK_TIMEOUT = 15.0f;      // StateAttack::exec 15.0f
constexpr float MOVE_ARRIVE = 25.0f;         // sqrt(625) Obj::isReachedTarget
// Port arm-sweep radius: the source hand_R contact test needs the P2 model
// joints; a flat radius is the documented port value.
constexpr float FLICK_RADIUS = 150.0f;
// Audited retail event frames (EXPECTED_EVENTS['DangoMushi']); used when the
// installed bank is absent.
constexpr int FALLBACK_ROLL_START = 23;      // attack 23:4 KEYEVENT_4
constexpr int FALLBACK_FLICK_START = 26;     // attack_2 26:2 KEYEVENT_2

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events;
};

struct Dango {
    State state = DANGO_STAY;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    Vector3f moveTarget;
    bool rolling = false;
    bool rollHit = false;
    bool armSwinging = false;
    std::set<int> firedEvents;
    std::string clip = "fly";
    float phase = 0.0f;
    bool deadLogged = false;
    float logTimer = 0.0f;
};

std::map<PelletView*, Dango> actors;
std::map<std::string, Clip> clips;
int rollStartFrame = FALLBACK_ROLL_START;
int flickStartFrame = FALLBACK_FLICK_START;
bool ready = false;

float wrapPi(float a) {
    while (a > PI) a -= TAU;
    while (a < -PI) a += TAU;
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
int eventFrame(const char* name, int type) {
    auto it = clips.find(name);
    if (it != clips.end()) {
        for (const auto& event : it->second.events)
            if (event.second == type) return event.first;
    }
    return -1;
}

Creature* nearestTarget(const Vector3f& pos, float radius) {
    Creature* best = nullptr;
    float bestSq = radius * radius;
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

void stop(BTeki* a) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
}

// Source Obj::turnByAngle: clamp(angleDist * turnSpeed, maxTurnAngle).
void turnAndMove(BTeki* a, Dango& s, const Vector3f& target,
                 float speed, float turnSpeed, float maxTurn) {
    const Vector3f pos = a->getPosition();
    const float desired = std::atan2(target.x - pos.x, target.z - pos.z);
    float delta = wrapPi(desired - s.heading) * turnSpeed;
    if (delta > maxTurn) delta = maxTurn;
    if (delta < -maxTurn) delta = -maxTurn;
    s.heading = wrapPi(s.heading + delta);
    a->setDirection(s.heading);
    const Vector3f drive(std::sin(s.heading) * speed, 0.0f,
                         std::cos(s.heading) * speed);
    a->inputDrive(drive);
    a->mVelocity.x = drive.x;
    a->mVelocity.z = drive.z;
}

// Source Obj::setRandTarget: a random point between the home and territory radii
// on the far side of the crab from home.
void setRandTarget(Dango& s) {
    const float outside = TERRITORY > HOME_RADIUS ? TERRITORY - HOME_RADIUS : 0.0f;
    const float radius = gsys->getRand(outside) + HOME_RADIUS;
    const float theta = gsys->getRand(TAU);
    s.moveTarget = Vector3f(s.home.x + radius * std::sin(theta), s.home.y,
                            s.home.z + radius * std::cos(theta));
}

bool canAttack(const Vector3f& pos, const Dango& s, Creature* target) {
    // Port adaptation: the source attackable check also gates on a narrow
    // fp21=15 deg cone, but the P1 host has no wall-route roll and wandering
    // rarely aligns the cone. Activation uses the source fp20=300 range only;
    // the roll then steers toward the target via rollingMove.
    (void)s;
    const Vector3f t = target->getPosition();
    return distXZ(t, pos) <= ATTACK_RANGE;
}

void enter(Dango& s, State state, const char* clip) {
    s.state = state;
    s.stateTime = 0.0f;
    s.firedEvents.clear();
    s.rolling = false;
    s.rollHit = false;
    s.armSwinging = false;
    if (clip) s.clip = clip;
}
void setState(BTeki* a, Dango& s, State state, const char* clip) {
    enter(s, state, clip);
    const unsigned generator = a->mGenerator ? a->mGenerator->_70 : 0u;
    std::printf("P2_DANGOMUSHI_STATE generator=%u state=%s\n", generator, stateName(state));
    std::fflush(stdout);
}

// Source Obj::rollingMove: steer toward the active Navi (else the nearest
// Pikmin/Navi) at the proper rolling speed.
void rollingMove(BTeki* a, Dango& s, const Vector3f& pos) {
    Creature* target = nullptr;
    if (naviMgr) {
        Navi* n = naviMgr->getNavi();
        if (n && n->isAlive()) target = n;
    }
    if (!target) target = nearestTarget(pos, SIGHT);
    if (target) {
        turnAndMove(a, s, target->getPosition(), ROLL_SPEED,
                    ROLL_TURN_ACCEL, ROLL_TURN_SPEED);
    } else {
        turnAndMove(a, s, Vector3f(pos.x + std::sin(s.heading) * 100.0f, pos.y,
                                   pos.z + std::cos(s.heading) * 100.0f),
                    ROLL_SPEED, ROLL_TURN_ACCEL, ROLL_TURN_SPEED);
    }
}

// Resolve the single roll contact: the first Pikmin/Navi inside fp22 after the
// roll starts, at most once per roll.
void rollContact(BTeki* a, Dango& s, const Vector3f& pos, unsigned generator) {
    if (s.rollHit) return;
    Creature* target = nearestTarget(pos, CONTACT_RADIUS);
    if (!target) return;
    s.rollHit = true;
    const Vector3f q = target->getPosition();
    const float angle = std::atan2(q.x - pos.x, q.z - pos.z);
    target->stimulate(InteractFlick(a, SHAKE_KNOCKBACK, ATTACK_DAMAGE, angle));
    std::printf("P2_DANGOMUSHI_HIT generator=%u pikmin=1\n", generator);
    std::fflush(stdout);
}

// Resolve the single attack_2 arm sweep at the source KEYEVENT_2 frame.
void flickSweep(BTeki* a, const Vector3f& pos, unsigned generator) {
    if (!pikiMgr) return;
    int hit = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        const Vector3f q = p->getPosition();
        if (distXZ(q, pos) >= FLICK_RADIUS) continue;
        const float angle = std::atan2(q.x - pos.x, q.z - pos.z);
        p->stimulate(InteractFlick(a, SHAKE_KNOCKBACK, 0.0f, angle));
        ++hit;
    }
    if (hit > 0) {
        std::printf("P2_DANGOMUSHI_FLICK generator=%u pikmin=%d\n", generator, hit);
        std::fflush(stdout);
    }
}

void setPhase(Dango& s) {
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

void pc_p2_dangomushi_reset() {
    actors.clear();
    clips.clear();
    rollStartFrame = FALLBACK_ROLL_START;
    flickStartFrame = FALLBACK_FLICK_START;
    ready = false;
}
void pc_p2_dangomushi_forget(BTeki* actor) { actors.erase(static_cast<PelletView*>(actor)); }

float pc_p2_dangomushi_param_f(const BTeki* actor, int idx, float fallback) {
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

bool pc_p2_dangomushi_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

void pc_p2_dangomushi_setup() {
    pc_p2_dangomushi_reset();
    if (!tekiMgr) return;

    std::ifstream bank("p2-snagret-bank.txt");
    if (bank) {
        std::string token;
        if (bank >> token && token == "P2_SNAGRET_BANK_1") {
            while (bank >> token) {
                if (token == "species") {
                    std::string species, identity;
                    bank >> species >> identity;
                    // Snagret install writes the numeric enemy id; tolerate the
                    // `clips <count>` row as well.
                    if (identity == "clips") {
                        int clipCount = 0;
                        bank >> clipCount;
                    }
                } else if (token == "clip") {
                    std::string species, name, events, marker, status, value;
                    long long frames = 0;
                    int poses = 0;
                    if (!(bank >> species >> name >> frames >> events >> marker >> poses)) break;
                    if (!(bank >> value)) break;
                    if (value != "status") status = value;
                    else if (!(bank >> status)) break;
                    if (species == "DangoMushi") {
                        Clip clip;
                        clip.name = name;
                        clip.duration = frames > 0 ? float(frames) / 30.0f : 1.0f;
                        clip.loop = (name == "fly" || name == "wait" || name == "move");
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
    const int roll = eventFrame("attack", 4);
    const int flick = eventFrame("attack_2", 2);
    if (roll >= 0) rollStartFrame = roll;
    if (flick >= 0) flickStartFrame = flick;

    std::ifstream in("p2-snagret-actors.txt");
    if (!in) return;
    std::string header;
    int count = 0;
    if (!(in >> header >> count) || header != "P2_SNAGRET_ACTORS_1" || count < 1) return;
    std::map<unsigned, std::string> wanted;
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        std::string species;
        if (!(in >> generator >> species)) return;
        if (species == "DangoMushi") wanted[unsigned(generator)] = species;
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
            std::printf("P2_DANGOMUSHI_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::abort();
        }
        Dango& s = actors[static_cast<PelletView*>(actor)];
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        s.moveTarget = s.home;
        actor->mHealth = LIFE;
        enter(s, DANGO_STAY, "fly");
        std::printf("P2_DANGOMUSHI_BIND generator=%u source_id=94 visual_only=0\n",
                    actor->mGenerator->_70);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=DangoMushi native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=interactflick_roll\n",
                    actor->mGenerator->_70, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        std::printf("P2_DANGOMUSHI_STATE generator=%u state=stay\n", actor->mGenerator->_70);
        std::fflush(stdout);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_DANGOMUSHI_ERROR missing_actor wanted=%zu found=%zu\n",
                    wanted.size(), found.size());
        std::abort();
    }
    ready = true;
}

void pc_p2_dangomushi_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Dango& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;

    if (actor->mHealth <= 0.0f && s.state != DANGO_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_DANGOMUSHI_DEAD generator=%u source_id=94 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        setState(actor, s, DANGO_DEAD, "dead");
    }

    s.stateTime += dt;
    switch (s.state) {
    case DANGO_STAY:
        stop(actor);
        // Source StateStay: wake when a target enters the source private radius.
        if (nearestTarget(pos, PRIVATE_RADIUS)) {
            setState(actor, s, DANGO_APPEAR, "fly");
        }
        break;
    case DANGO_APPEAR:
        stop(actor);
        if (s.stateTime >= clipDuration("fly")) {
            Creature* target = nearestTarget(pos, SIGHT);
            if (target) {
                setRandTarget(s);
                setState(actor, s, DANGO_MOVE, "move");
            } else {
                setState(actor, s, DANGO_WAIT, "wait");
            }
        }
        break;
    case DANGO_WAIT: {
        stop(actor);
        Creature* target = nearestTarget(pos, SIGHT);
        if (target) {
            if (canAttack(pos, s, target)) {
                setState(actor, s, DANGO_ATTACK, "attack");
            } else {
                setRandTarget(s);
                setState(actor, s, DANGO_MOVE, "move");
            }
        } else if (s.stateTime > WAIT_TIME) {
            setRandTarget(s);
            setState(actor, s, DANGO_MOVE, "move");
        }
        break;
    }
    case DANGO_MOVE: {
        Creature* target = nearestTarget(pos, SIGHT);
        if (target) {
            if (canAttack(pos, s, target)) {
                setState(actor, s, DANGO_ATTACK, "attack");
                break;
            }
            turnAndMove(actor, s, target->getPosition(), MOVE_SPEED,
                        WALK_TURN_RATE, WALK_MAX_TURN);
        } else if (distXZ(pos, s.moveTarget) < MOVE_ARRIVE || s.stateTime > MOVE_TIMEOUT) {
            setState(actor, s, DANGO_WAIT, "wait");
        } else {
            turnAndMove(actor, s, s.moveTarget, MOVE_SPEED, WALK_TURN_RATE, WALK_MAX_TURN);
        }
        break;
    }
    case DANGO_ATTACK: {
        const float frame = s.stateTime * 30.0f;
        if (!s.rolling && frame >= float(rollStartFrame)) {
            s.rolling = true;
            s.rollHit = false;
            std::printf("P2_DANGOMUSHI_ROLL generator=%u frame=%.1f\n",
                        generator, float(rollStartFrame));
            std::fflush(stdout);
        }
        if (s.rolling) {
            rollingMove(actor, s, pos);
            rollContact(actor, s, pos, generator);
            if (distXZ(pos, s.home) > TERRITORY) {
                setState(actor, s, DANGO_TURN, "turn");
            } else if (s.stateTime > ATTACK_TIMEOUT) {
                setState(actor, s, DANGO_WAIT, "wait");
            }
        } else {
            stop(actor);
        }
        break;
    }
    case DANGO_TURN:
        stop(actor);
        if (s.stateTime >= FLIP_TIME || s.stateTime >= clipDuration("turn")) {
            setState(actor, s, DANGO_RECOVER, "recover");
        }
        break;
    case DANGO_RECOVER:
        stop(actor);
        if (s.stateTime >= clipDuration("recover")) {
            // Source StateRecover::exec KEYEVENT_END flips the facing direction.
            s.heading = wrapPi(s.heading + PI);
            actor->setDirection(s.heading);
            setState(actor, s, DANGO_FLICK, "attack_2");
        }
        break;
    case DANGO_FLICK: {
        stop(actor);
        const float frame = s.stateTime * 30.0f;
        if (!s.armSwinging && frame >= float(flickStartFrame)) {
            s.armSwinging = true;
            flickSweep(actor, pos, generator);
        }
        if (s.stateTime >= clipDuration("attack_2")) {
            setState(actor, s, DANGO_WAIT, "wait");
        }
        break;
    }
    case DANGO_DEAD:
        stop(actor);
        if (s.stateTime >= clipDuration("dead")) actor->die();
        break;
    default:
        break;
    }
    setPhase(s);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        std::printf("P2_DANGOMUSHI_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z);
        std::fflush(stdout);
    }
}
