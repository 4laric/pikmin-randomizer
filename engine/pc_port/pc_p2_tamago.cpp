// Family-owned ground-invertebrate source behavior for the batch-2 Chappy
// placement vehicle: Mitite (TamagoMushi, EnemyID 68). Implements the source
// tamagoMushiState.cpp cycle (Walk/Turn/Appear/Hide/Wait/Dead), the
// collisionCallback Astonish receiver (tamagoMushi.cpp:239) and the genItem
// honey reward (tamagoMushi.cpp:326). Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_ground_inverts_assets.py (GPVE01 rev 0).
//
// Port adaptations (recorded, not retail-faithful):
//   * The P1 engine has no InteractAstonish; contact with a Pikmin is resolved
//     as an InteractFlick knockback (the closest P1 panic/scatter receiver),
//     applied once per contact.
//   * The source manager-owned group birth (createGroup, 10 surface / 30 cave) is
//     not implemented; the staged actor runs the singleton FSM.
//   * Honey uses the P1 OBJTYPE_Water (nectar) resolution of ItemHoney HONEY_Y;
//     the host corpse is suppressed so the reward is exactly-once.
// No other lane's module is modified; every hook is a no-op for unregistered actors.
#include "pc_p2_tamago.h"
#include "teki.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Generator.h"
#include "ItemMgr.h"
#include "ObjType.h"
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
    TAMAGO_INVALID = -1,
    TAMAGO_WALK = 0,
    TAMAGO_TURN = 1,
    TAMAGO_APPEAR = 2,
    TAMAGO_HIDE = 3,
    TAMAGO_DEAD = 4,
    TAMAGO_WAIT = 5,
};

const char* stateName(State s) {
    switch (s) {
    case TAMAGO_WALK: return "walk";
    case TAMAGO_TURN: return "turn";
    case TAMAGO_APPEAR: return "appear";
    case TAMAGO_HIDE: return "hide";
    case TAMAGO_DEAD: return "dead";
    case TAMAGO_WAIT: return "wait";
    default: return "null";
    }
}

// Source enemyparm.txt / header values (TamagoMushi Parms).
constexpr float LIFE = 50.0f;
constexpr float MOVE_SPEED = 100.0f;
constexpr float SIGHT = 150.0f;
constexpr float TERRITORY = 120.0f;
constexpr float HOME_RADIUS = 30.0f;
constexpr float APPEAR_RANGE = 80.0f; // fp02
constexpr float HONEY_RATE = 1.0f;    // fp03
constexpr float ASTONISH_RADIUS = 18.0f; // source collision root r18
constexpr float FLICK_KNOCKBACK = 120.0f;
constexpr float WALK_TIME = 1.3f;   // ip01/ip02 midpoint
constexpr float APPEAR_TIME = 0.5f; // port value
constexpr float HIDE_TIME = 0.5f;   // port value
constexpr float WAIT_TIME = 1.0f;   // ip03/ip04 midpoint
constexpr float TURN_TIME = 0.4f;   // port value

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
};

struct Tamago {
    State state = TAMAGO_WALK;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    std::set<Piki*> inContact;
    bool honeyDropped = false;
    bool deadLogged = false;
    std::string clip = "move";
    float phase = 0.0f;
    float logTimer = 0.0f;
};

std::map<PelletView*, Tamago> actors;
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
void enter(Tamago& s, State state, const char* clip) {
    s.state = state;
    s.stateTime = 0.0f;
    if (clip) s.clip = clip;
}
void wander(BTeki* a, Tamago& s) {
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
void setPhase(Tamago& s) {
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
// Astonish receiver: InteractFlick on each Pikmin entering the collision radius,
// once per contact (source collisionCallback excludes an Appear-state hit).
void astonishContacts(BTeki* a, Tamago& s) {
    std::set<Piki*> inside;
    if (pikiMgr) {
        const Vector3f pos = a->getPosition();
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            if (distXZ(p->getPosition(), pos) > ASTONISH_RADIUS) continue;
            inside.insert(p);
            if (s.inContact.count(p)) continue;
            p->stimulate(InteractFlick(a, FLICK_KNOCKBACK, 0.0f, a->getDirection()));
            std::printf("P2_TAMAGO_ASTONISH generator=%u pikmin=1\n",
                        a->mGenerator ? a->mGenerator->_70 : 0u);
            std::fflush(stdout);
        }
    }
    s.inContact.swap(inside);
}
void dropHoney(BTeki* a, Tamago& s) {
    if (s.honeyDropped) return;
    s.honeyDropped = true;
    if (!(HONEY_RATE > 0.0f) || !itemMgr) return;
    const Vector3f pos = a->getPosition();
    Creature* drop = itemMgr->birth(OBJTYPE_Water);
    if (!drop) return;
    drop->init(pos);
    drop->startAI(0);
    std::printf("P2_TAMAGO_HONEY generator=%u source_id=68\n",
                a->mGenerator ? a->mGenerator->_70 : 0u);
    std::fflush(stdout);
}
}

void pc_p2_tamago_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}
void pc_p2_tamago_forget(BTeki* actor) { actors.erase(static_cast<PelletView*>(actor)); }

float pc_p2_tamago_param_f(const BTeki* actor, int idx, float fallback) {
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

int pc_p2_tamago_corpse_type(const BTeki* actor, int fallback) {
    if (!ready || !actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor)))) return fallback;
    return TEKICORPSE_NoCorpse; // honey reward instead of a corpse
}

bool pc_p2_tamago_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

void pc_p2_tamago_setup() {
    pc_p2_tamago_reset();
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
                    if (species == "TamagoMushi") {
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
        if (species == "TamagoMushi") wanted[unsigned(generator)] = species;
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
            std::printf("P2_TAMAGO_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::abort();
        }
        Tamago& s = actors[static_cast<PelletView*>(actor)];
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        actor->mHealth = LIFE;
        enter(s, TAMAGO_WALK, "move");
        std::printf("P2_TAMAGO_BIND generator=%u source_id=68 visual_only=0\n",
                    actor->mGenerator->_70);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=TamagoMushi native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented astonish=native_P1_approx honey=native\n",
                    actor->mGenerator->_70, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_TAMAGO_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::abort();
    }
    ready = true;
}

void pc_p2_tamago_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Tamago& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;

    if (actor->mHealth <= 0.0f && s.state != TAMAGO_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_TAMAGO_DEAD generator=%u source_id=68 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        dropHoney(actor, s);
        enter(s, TAMAGO_DEAD, "dead");
    }

    if (s.state != TAMAGO_DEAD) astonishContacts(actor, s);

    s.stateTime += dt;
    switch (s.state) {
    case TAMAGO_WALK:
        if (distXZ(pos, s.home) > TERRITORY) {
            s.heading = wrapPi(std::atan2(s.home.x - pos.x, s.home.z - pos.z));
        } else {
            s.heading = wrapPi(s.heading + 0.5f * dt);
        }
        wander(actor, s);
        if (s.stateTime > WALK_TIME) {
            std::printf("P2_TAMAGO_STATE generator=%u state=hide\n", generator);
            enter(s, TAMAGO_HIDE, "dive");
        }
        break;
    case TAMAGO_HIDE:
        stop(actor);
        if (s.stateTime > HIDE_TIME) {
            std::printf("P2_TAMAGO_STATE generator=%u state=appear\n", generator);
            enter(s, TAMAGO_APPEAR, "set");
        }
        break;
    case TAMAGO_APPEAR:
        stop(actor);
        if (s.stateTime > APPEAR_TIME) {
            std::printf("P2_TAMAGO_STATE generator=%u state=wait\n", generator);
            enter(s, TAMAGO_WAIT, "wait");
        }
        break;
    case TAMAGO_WAIT:
        stop(actor);
        if (s.stateTime > WAIT_TIME) {
            std::printf("P2_TAMAGO_STATE generator=%u state=walk\n", generator);
            enter(s, TAMAGO_WALK, "move");
        }
        break;
    case TAMAGO_TURN:
        stop(actor);
        if (s.stateTime > TURN_TIME) enter(s, TAMAGO_WALK, "move");
        break;
    case TAMAGO_DEAD:
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
        std::printf("P2_TAMAGO_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z);
        std::fflush(stdout);
    }
}
