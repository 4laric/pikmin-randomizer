// Family-owned ground-invertebrate source behavior for the batch-2 Chappy
// placement vehicle: Anode Beetle (ElecBug, EnemyID 28). Implements the source
// ElecBugState.cpp cycle (Wait/Turn/Move wander -> Charge -> Discharge -> Return)
// plus the Reverse flip from ElecBug.cpp::pressCallBack and the invulnerability
// that Reverse removes. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_ground_inverts_assets.py (GPVE01 rev 0).
//
// Port adaptations (recorded, not retail-faithful):
//   * The source two-beetle Charge/ChildCharge partner link is not implemented
//     on the P1 host; the beetle runs a singleton Charge -> Discharge cycle.
//   * Between-beetle Denki geometry is resolved as a single nearest non-Yellow
//     Pikmin within the discharge radius, shocked once per discharge. The P1
//     engine has no InteractDenki, so the electrical receiver uses InteractKill.
//   * View angle is a full hemisphere; charge/return durations are port values.
// No other lane's module is modified; every hook is a no-op for unregistered actors.
#include "pc_p2_elecbug.h"
#include "teki.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "GlobalGameOptions.h"
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
    ELEC_INVALID = -1,
    ELEC_DEAD = 0,
    ELEC_WAIT = 1,
    ELEC_TURN = 2,
    ELEC_MOVE = 3,
    ELEC_CHARGE = 4,
    ELEC_DISCHARGE = 5,
    ELEC_REVERSE = 8,
    ELEC_RETURN = 9,
};

const char* stateName(State s) {
    switch (s) {
    case ELEC_DEAD: return "dead";
    case ELEC_WAIT: return "wait";
    case ELEC_TURN: return "turn";
    case ELEC_MOVE: return "move";
    case ELEC_CHARGE: return "charge";
    case ELEC_DISCHARGE: return "discharge";
    case ELEC_REVERSE: return "reverse";
    case ELEC_RETURN: return "return";
    default: return "null";
    }
}

// Source enemyparm.txt values (ground_inverts manifest general/proper).
constexpr float LIFE = 500.0f;
constexpr float MOVE_SPEED = 30.0f;
constexpr float SIGHT = 200.0f;
constexpr float TERRITORY = 200.0f;
constexpr float HOME_RADIUS = 100.0f;
constexpr float FLIP_TIME = 5.0f;      // fp01
constexpr float WAIT_TIME = 1.5f;      // fp02
constexpr float DISCHARGE_TIME = 3.0f; // fp11
constexpr float CHARGE_TIME = 1.0f;    // port value
constexpr float RETURN_TIME = 0.5f;    // port value
constexpr float WANDER_TIME = 1.5f;    // port value
constexpr float ELEC_RADIUS = 70.0f;   // source sweep radius fp20/22 = 70
constexpr float TURN_RATE = 2.0f;

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
};

struct ElecBug {
    State state = ELEC_WAIT;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    bool shockedThisDischarge = false;
    bool flipped = false;
    bool deadLogged = false;
    std::string clip = "wait";
    float phase = 0.0f;
    float logTimer = 0.0f;
};

std::map<PelletView*, ElecBug> actors;
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
bool targetInSight(const Vector3f& pos) {
    if (naviMgr) {
        Navi* n = naviMgr->getNavi();
        if (n && n->isAlive() && distXZ(n->getPosition(), pos) < SIGHT) return true;
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (p && p->isAlive() && distXZ(p->getPosition(), pos) < SIGHT) return true;
        }
    }
    return false;
}
Piki* nearestNonYellow(const Vector3f& pos, float radius) {
    Piki* best = nullptr;
    float bestSq = radius * radius;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive() || p->mColor == Yellow) continue;
            const float d = distXZ(p->getPosition(), pos);
            if (d < radius && d * d < bestSq) { bestSq = d * d; best = p; }
        }
    }
    return best;
}
void enter(ElecBug& s, State state, const char* clip) {
    s.state = state;
    s.stateTime = 0.0f;
    if (clip) s.clip = clip;
}
void wander(BTeki* a, ElecBug& s) {
    a->setDirection(s.heading);
    const Vector3f drive(std::sin(s.heading) * MOVE_SPEED, 0.0f, std::cos(s.heading) * MOVE_SPEED);
    a->inputDrive(drive);
    a->mVelocity.set(drive);
}
void stop(BTeki* a) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
}
void setPhase(ElecBug& s) {
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

void pc_p2_elecbug_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}
void pc_p2_elecbug_forget(BTeki* actor) { actors.erase(static_cast<PelletView*>(actor)); }

float pc_p2_elecbug_param_f(const BTeki* actor, int idx, float fallback) {
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

bool pc_p2_elecbug_attacked(Teki* teki) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(teki));
    if (it == actors.end()) return false;
    if (it->second.state == ELEC_DEAD) return false;
    return !it->second.flipped; // invulnerable until flipped into Reverse
}

bool pc_p2_elecbug_pressed(BTeki* teki, Creature*) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(teki));
    if (it == actors.end()) return false;
    ElecBug& s = it->second;
    if (s.state == ELEC_DEAD || s.state == ELEC_REVERSE) return true;
    s.flipped = true;
    enter(s, ELEC_REVERSE, "recover");
    std::printf("P2_ELECBUG_FLIP generator=%u source_id=28\n",
                teki->mGenerator ? teki->mGenerator->_70 : 0u);
    std::fflush(stdout);
    return true;
}

bool pc_p2_elecbug_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

void pc_p2_elecbug_setup() {
    pc_p2_elecbug_reset();
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
                    if (species == "ElecBug") {
                        Clip clip;
                        clip.name = name;
                        clip.duration = frames > 0 ? float(frames) / 30.0f : 1.0f;
                        clip.loop = (name == "move" || name == "wait");
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
        if (species == "ElecBug") wanted[unsigned(generator)] = species;
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
            std::printf("P2_ELECBUG_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::abort();
        }
        ElecBug& s = actors[static_cast<PelletView*>(actor)];
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        actor->mHealth = LIFE;
        enter(s, ELEC_WAIT, "wait");
        std::printf("P2_ELECBUG_BIND generator=%u source_id=28 visual_only=0\n",
                    actor->mGenerator->_70);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=ElecBug native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=discharge_receiver\n",
                    actor->mGenerator->_70, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_ELECBUG_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::abort();
    }
    ready = true;
}

void pc_p2_elecbug_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    ElecBug& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;

    if (actor->mHealth <= 0.0f && s.state != ELEC_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_ELECBUG_DEAD generator=%u source_id=28 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        enter(s, ELEC_DEAD, "dead");
    }

    s.stateTime += dt;
    switch (s.state) {
    case ELEC_WAIT:
        stop(actor);
        if (targetInSight(pos)) {
            std::printf("P2_ELECBUG_STATE generator=%u state=charge\n", generator);
            enter(s, ELEC_CHARGE, "charge");
        } else if (s.stateTime > WAIT_TIME) {
            std::printf("P2_ELECBUG_STATE generator=%u state=move\n", generator);
            enter(s, ELEC_MOVE, "move");
        }
        break;
    case ELEC_TURN:
        stop(actor);
        if (s.stateTime > RETURN_TIME) {
            std::printf("P2_ELECBUG_STATE generator=%u state=move\n", generator);
            enter(s, ELEC_MOVE, "move");
        }
        break;
    case ELEC_MOVE:
        if (targetInSight(pos)) {
            std::printf("P2_ELECBUG_STATE generator=%u state=charge\n", generator);
            enter(s, ELEC_CHARGE, "charge");
            break;
        }
        s.heading = wrapPi(s.heading + 0.4f * dt);
        wander(actor, s);
        if (s.stateTime > WANDER_TIME) {
            std::printf("P2_ELECBUG_STATE generator=%u state=wait\n", generator);
            enter(s, ELEC_WAIT, "wait");
        }
        break;
    case ELEC_CHARGE:
        stop(actor);
        if (s.stateTime >= CHARGE_TIME) {
            s.shockedThisDischarge = false;
            std::printf("P2_ELECBUG_STATE generator=%u state=discharge\n", generator);
            std::printf("P2_ELECBUG_DISCHARGE generator=%u source_id=28 duration=%.3f\n",
                        generator, DISCHARGE_TIME);
            std::fflush(stdout);
            enter(s, ELEC_DISCHARGE, "discharge");
        }
        break;
    case ELEC_DISCHARGE: {
        stop(actor);
        if (!s.shockedThisDischarge) {
            Piki* piki = nearestNonYellow(pos, ELEC_RADIUS);
            if (piki) {
                s.shockedThisDischarge = true;
                piki->stimulate(InteractKill(actor, 0));
                std::printf("P2_ELECBUG_SHOCK generator=%u pikmin=1\n", generator);
                std::fflush(stdout);
            }
        }
        if (s.stateTime >= DISCHARGE_TIME) {
            std::printf("P2_ELECBUG_STATE generator=%u state=return\n", generator);
            enter(s, ELEC_RETURN, "recover");
        }
        break;
    }
    case ELEC_RETURN:
        stop(actor);
        if (s.stateTime >= RETURN_TIME) {
            std::printf("P2_ELECBUG_STATE generator=%u state=wait\n", generator);
            enter(s, ELEC_WAIT, "wait");
        }
        break;
    case ELEC_REVERSE:
        stop(actor);
        if (s.stateTime >= FLIP_TIME) {
            s.flipped = false;
            std::printf("P2_ELECBUG_RECOVER generator=%u source_id=28\n", generator);
            std::fflush(stdout);
            enter(s, ELEC_RETURN, "recover");
        }
        break;
    case ELEC_DEAD:
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
        std::printf("P2_ELECBUG_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z);
        std::fflush(stdout);
    }
}
