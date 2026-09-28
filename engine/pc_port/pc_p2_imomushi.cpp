// Family-owned ground-invertebrate source behavior for the batch-2 Chappy
// placement vehicle: Ravenous Whiskerpillar (Imomushi, EnemyID 65). Implements
// the source ImomushiState.cpp FSM slice Stay -> Appear -> Move -> GoHome ->
// Dive -> Stay, plus Fall -> Dead on death. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_ground_inverts_assets.py (GPVE01 rev 0): general
// fp00 life 200, fp06 speed 40, fp09 territory 500, fp10 home 30, fp12 sight
// 500; proper fp01 climb speed 2.0, fp02 seed speed 0.3, fp11 eat time 10.0.
//
// Plant-eating is source-backed N/A: StateStay/StateAppear/StateFallMove only
// advance when Obj::getRandFruitsPlant() returns a fruit-bearing ItemPlant
// (Imomushi.cpp:723), and StateClimb/StateAttack (moveStickTube/moveStickSphere/
// eatTsuyukusa) require a plant CollPart. The batch-2 ground arena stages no
// fruit-bearing plants, so Wait/Climb/Attack are not implemented and are not
// faked. Imomushi has no Pikmin attack (source attack is plant eating); there is
// no player-damage receiver, so attack/delivery are N/A.
//
// Port adaptations (recorded, not retail-faithful):
//   * Wake condition: source StateStay wakes only after 6s when NO Pikmin is
//     within the private radius AND a fruit plant is in territory
//     (ImomushiState.cpp:184-193). With no staged fruit, sight of a Pikmin/Navi
//     within fp12=500 stands in for "a plant is available", making the
//     Appear/Move/GoHome/Dive cycle observable in an unattended run.
//   * Move target: source StateMove walks to the fruit plant (fp06=40); with no
//     plant the nearest Pikmin/Navi is the walk target for a bounded interval,
//     then GoHome. Imomushi never damages the target.
//   * FallMove/FallDive are entered from Climb/Attack on death and from
//     dropCallBack (Imomushi.cpp:567). Climb/Attack are N/A, so death routes
//     Move/GoHome through FallDive before Dead so both banked fall/dead clips
//     are exercised.
//   * Turn rate is a fixed adaptation (~pi rad/s); source uses
//     mTurnSpeed/mMaxTurnAngle.
// No other lane's module is modified; every hook is a no-op for unregistered actors.
#include "pc_p2_imomushi.h"
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
    IMOMUSHI_DEAD = 0,
    IMOMUSHI_FALL = 2,
    IMOMUSHI_STAY = 4,
    IMOMUSHI_APPEAR = 5,
    IMOMUSHI_DIVE = 6,
    IMOMUSHI_MOVE = 7,
    IMOMUSHI_GOHOME = 8,
};

const char* stateName(State s) {
    switch (s) {
    case IMOMUSHI_DEAD: return "dead";
    case IMOMUSHI_FALL: return "fall";
    case IMOMUSHI_STAY: return "stay";
    case IMOMUSHI_APPEAR: return "appear";
    case IMOMUSHI_DIVE: return "dive";
    case IMOMUSHI_MOVE: return "move";
    case IMOMUSHI_GOHOME: return "gohome";
    default: return "null";
    }
}

// Source enemyparm.txt values (ground_inverts manifest general/proper).
constexpr float LIFE = 200.0f;
constexpr float MOVE_SPEED = 40.0f;  // fp06
constexpr float SIGHT = 500.0f;      // fp12
constexpr float TERRITORY = 500.0f;  // fp09
constexpr float HOME_RADIUS = 30.0f; // fp10
constexpr float MOVE_TIME = 5.0f;    // port bound (no plant target to reach)
constexpr float TURN_RATE = 3.14159265f; // port adaptation

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
};

struct Imomushi {
    State state = IMOMUSHI_STAY;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    bool hiddenLogged = false;
    bool deadLogged = false;
    std::string clip = "set";
    float phase = 0.0f;
    float logTimer = 0.0f;
};

std::map<PelletView*, Imomushi> actors;
std::map<std::string, Clip> clips;
bool ready = false;

float wrapPi(float a) {
    while (a > 3.14159265f) a -= 6.28318531f;
    while (a < -3.14159265f) a += 6.28318531f;
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
void enter(Imomushi& s, State state, const char* clip) {
    s.state = state;
    s.stateTime = 0.0f;
    if (clip) s.clip = clip;
}
void stop(BTeki* a) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
}
void walkTo(BTeki* a, Imomushi& s, const Vector3f& target, float dt) {
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
    a->mVelocity.set(drive);
}
void setPhase(Imomushi& s) {
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
}

void pc_p2_imomushi_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}
void pc_p2_imomushi_forget(BTeki* actor) { actors.erase(static_cast<PelletView*>(actor)); }

float pc_p2_imomushi_param_f(const BTeki* actor, int idx, float fallback) {
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

bool pc_p2_imomushi_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

void pc_p2_imomushi_setup() {
    pc_p2_imomushi_reset();
    if (!tekiMgr) return;

    std::ifstream bank("p2-ground-bank.txt");
    if (bank) {
        std::string token;
        if (bank >> token && token == "P2_GROUND_BANK_1") {
            while (bank >> token) {
                if (token == "species") {
                    std::string species, id;
                    bank >> species >> id;
                } else if (token == "clip") {
                    std::string species, name, events, marker, status;
                    long long frames = 0;
                    int poses = 0;
                    bank >> species >> name >> frames >> events >> marker >> poses >> status;
                    if (species == "Imomushi") {
                        Clip clip;
                        clip.name = name;
                        clip.duration = frames > 0 ? float(frames) / 30.0f : 1.0f;
                        clip.loop = (name == "move1");
                        clips[name] = clip;
                    }
                } else {
                    break;
                }
            }
        }
    }

    std::ifstream in("p2-ground-actors.txt");
    if (!in) return;
    std::string header;
    int count = 0;
    if (!(in >> header >> count) || header != "P2_GROUND_ACTORS_1" || count < 1) return;
    std::map<unsigned, std::string> wanted;
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        std::string species;
        if (!(in >> generator >> species)) return;
        if (species == "Imomushi") wanted[unsigned(generator)] = species;
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
            std::printf("P2_IMOMUSHI_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::abort();
        }
        Imomushi& s = actors[static_cast<PelletView*>(actor)];
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        actor->mHealth = LIFE;
        enter(s, IMOMUSHI_STAY, "set");
        std::printf("P2_IMOMUSHI_BIND generator=%u source_id=65 visual_only=0\n",
                    actor->mGenerator->_70);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=Imomushi native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented plant_eat=source_backed_NA\n",
                    actor->mGenerator->_70, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_IMOMUSHI_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::abort();
    }
    ready = true;
}

void pc_p2_imomushi_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Imomushi& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;

    if (actor->mHealth <= 0.0f && s.state != IMOMUSHI_DEAD && s.state != IMOMUSHI_FALL) {
        if (!s.deadLogged) {
            std::printf("P2_IMOMUSHI_DEAD generator=%u source_id=65 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        std::printf("P2_IMOMUSHI_STATE generator=%u state=fall\n", generator);
        enter(s, IMOMUSHI_FALL, "fall2");
    }

    s.stateTime += dt;
    switch (s.state) {
    case IMOMUSHI_STAY:
        stop(actor);
        s.clip = "set";
        if (!s.hiddenLogged) {
            s.hiddenLogged = true;
            std::printf("P2_IMOMUSHI_HIDDEN generator=%u hidden=1\n", generator);
        }
        if (nearestTarget(pos)) {
            std::printf("P2_IMOMUSHI_STATE generator=%u state=appear\n", generator);
            enter(s, IMOMUSHI_APPEAR, "set");
        }
        break;
    case IMOMUSHI_APPEAR:
        stop(actor);
        if (s.stateTime >= clipDuration("set")) {
            std::printf("P2_IMOMUSHI_STATE generator=%u state=move\n", generator);
            enter(s, IMOMUSHI_MOVE, "move1");
        }
        break;
    case IMOMUSHI_MOVE: {
        Creature* target = nearestTarget(pos);
        if (target) walkTo(actor, s, target->getPosition(), dt);
        else stop(actor);
        if (distXZ(pos, s.home) > TERRITORY || s.stateTime > MOVE_TIME) {
            std::printf("P2_IMOMUSHI_STATE generator=%u state=gohome\n", generator);
            enter(s, IMOMUSHI_GOHOME, "move1");
        }
        break;
    }
    case IMOMUSHI_GOHOME:
        walkTo(actor, s, s.home, dt);
        if (distXZ(pos, s.home) < HOME_RADIUS) {
            std::printf("P2_IMOMUSHI_STATE generator=%u state=dive\n", generator);
            enter(s, IMOMUSHI_DIVE, "dive");
        }
        break;
    case IMOMUSHI_DIVE:
        stop(actor);
        if (s.stateTime >= clipDuration("dive")) {
            std::printf("P2_IMOMUSHI_STATE generator=%u state=stay\n", generator);
            enter(s, IMOMUSHI_STAY, "set");
        }
        break;
    case IMOMUSHI_FALL:
        stop(actor);
        if (s.stateTime >= clipDuration("fall2")) {
            std::printf("P2_IMOMUSHI_STATE generator=%u state=dead\n", generator);
            enter(s, IMOMUSHI_DEAD, "dead");
        }
        break;
    case IMOMUSHI_DEAD:
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
        std::printf("P2_IMOMUSHI_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z);
        std::fflush(stdout);
    }
}
