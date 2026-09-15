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
//   * The source manager-owned group birth (tamagoMushiMgr.cpp::createGroup:77/
//     122, 10 surface / 30 cave from TAMAGOMUSHI_GROUP_COUNT) has TWO port paths:
//     - the pre-staged approximation (no p2-tamago-host.txt): the arena stages a
//       bounded cluster of TamagoMushi generators and setup links the smallest as
//       leader; no brand-new P1 Teki actors are born.
//     - the manager-driven birth mode (p2-tamago-host.txt present): a single host
//       births its group once on Appear via pc_p2_tamago_birth_group, which uses
//       BTeki::generateTeki to create the real leader-follower Teki actors inside
//       the scene (no spawn velocity; source birth offsets approximated by a
//       bounded 45-unit distribution).
//   * Leader teardown is not established by the source (audit note); an
//     orphaned follower promotes itself to its own leader instead of holding a
//     dangling swarm pointer.
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
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <utility>
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
// Bounded swarm leash; source general territory radius fp09=120. A follower
// inside this radius runs the ground cycle, outside it drives at the leader.
constexpr float FOLLOW_RADIUS = 60.0f;
// Source group counts from generalEnemyMgr.cpp:436-443 (surface 10 / cave 30).
constexpr int SOURCE_GROUP_SURFACE = 10;
constexpr int SOURCE_GROUP_CAVE = 30;

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
    bool isLeader = true;
    unsigned generator = 0;
    unsigned leaderGenerator = 0;
    BTeki* leaderActor = nullptr;
    // Manager-driven birth (#165): host births its group exactly once on Appear.
    bool madeFellow = false;
    bool isGroupHost = false;
};

std::map<PelletView*, Tamago> actors;
std::map<std::string, Clip> clips;
bool ready = false;
// Birth-mode group state: when p2-tamago-host.txt is present, the host births its
// own group via pc_p2_tamago_birth_group (manager-driven), once.
bool birthMode = false;
unsigned hostGenerator = 0;
int hostGroupCount = 0;
// Deferred sibling kills: pc_p2_tamago_forget's group branch runs inside the
// TekiMgr update loop (natural host death -> doKill -> forget), so it queues the
// born followers here and pc_p2_tamago_tick() drains them once per frame outside
// that loop (gameCoreSection.cpp, after tekiMgr->update()).
std::vector<BTeki*> pendingKills;

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
            std::printf("P2_TAMAGO_ASTONISH generator=%u pikmin=1\n", s.generator);
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
    std::printf("P2_TAMAGO_HONEY generator=%u source_id=68\n", s.generator);
    std::fflush(stdout);
}
}

void pc_p2_tamago_reset() {
    actors.clear();
    clips.clear();
    pendingKills.clear();
    ready = false;
}
void pc_p2_tamago_forget(BTeki* actor) {
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    const bool wasLeader = it->second.isLeader;
    const unsigned gone = it->second.generator;
    const bool wasGroupHost = it->second.isGroupHost;
    // Whole-group cleanup on host forget: the manager-birth host owns its group,
    // so forgetting the host erases the whole group and despawns every born
    // follower. The born-actor kills are QUEUED and drained by pc_p2_tamago_tick()
    // once per frame, outside the TekiMgr update loop this hook runs inside on a
    // natural host death (BTeki::doKill -> pc_p2_forget_teki).
    if (wasGroupHost) {
        std::vector<BTeki*> children;
        for (auto& entry : actors) {
            if (entry.first != static_cast<PelletView*>(actor)
                    && entry.second.leaderActor == actor) {
                children.push_back(static_cast<BTeki*>(entry.first));
            }
        }
        int queued = 0;
        for (BTeki* child : children) {
            actors.erase(static_cast<PelletView*>(child));
            if (child->isAlive()) {
                pendingKills.push_back(child);
                ++queued;
            }
        }
        actors.erase(static_cast<PelletView*>(actor));
        std::printf("P2_TAMAGO_GROUP_FORGET host=%u group=%d remaining=%zu queued=%d source_id=68\n",
                    gone, int(children.size()) + 1, actors.size(), queued);
        std::fflush(stdout);
        return;
    }
    actors.erase(it);
    if (!wasLeader) return;
    // Bounded leader teardown for the pre-staged group path: source leader reuse/
    // teardown is not established, so an orphaned follower promotes itself rather
    // than keeping a dangling swarm pointer.
    for (auto& entry : actors) {
        if (entry.second.leaderActor != actor) continue;
        entry.second.leaderActor = nullptr;
        entry.second.isLeader = true;
        entry.second.leaderGenerator = entry.second.generator;
        std::printf("P2_TAMAGO_PROMOTE generator=%u leader_gone=%u source_id=68\n",
                    entry.second.generator, gone);
    }
    std::fflush(stdout);
}

unsigned long pc_p2_tamago_count() { return (unsigned long)actors.size(); }
bool pc_p2_tamago_registered(BTeki* actor) {
    return actors.count(static_cast<PelletView*>(actor)) != 0;
}

void pc_p2_tamago_tick() {
    // Once-per-frame drain of queued born-follower kills (see pendingKills). Runs
    // outside the TekiMgr update loop so sibling despawns never re-enter the host's
    // own update() death funnel. `killed` records how many born Teki actually went
    // through the death funnel here, so the runtime can prove the group was
    // despawned (not merely erased from this module's actor map) before _Exit(0).
    int killed = 0;
    for (BTeki* child : pendingKills) {
        if (child && child->isAlive()) {
            child->kill(false);
            ++killed;
        }
    }
    if (!pendingKills.empty()) {
        std::printf("P2_TAMAGO_GROUP_DRAIN killed=%d source_id=68\n", killed);
        std::fflush(stdout);
    }
    pendingKills.clear();
}

void pc_p2_tamago_birth_group(BTeki* host, int count) {
    if (!ready || !host || count < 1) return;
    auto hostIt = actors.find(static_cast<PelletView*>(host));
    if (hostIt == actors.end()) return;
    Tamago& hostState = hostIt->second;
    if (hostState.madeFellow) return;  // exactly-once (source mHasMadeFellow)
    hostState.madeFellow = true;
    hostState.isGroupHost = true;
    const unsigned hostGen = hostState.generator;
    const Vector3f hostPos = host->getPosition();
    const int follow = count - 1;
    int born = 0;
    // Source createGroup follower placement: birthRadius*(45*sin/cos) around the
    // leader (tamagoMushiMgr.cpp:152-178), leaders self-own.
    for (int i = 0; i < follow; ++i) {
        // generateTeki births a fresh Chappy-vehicle Teki with its personality
        // inherited from the host but NO spawn position/launch velocity (spawnTeki
        // would apply SpawnVelocity*Strength and fling the child out of the arena).
        Teki* child = host->generateTeki(TEKI_Chappy);
        if (!child) continue;  // null birth tolerated (source skips, count short)
        // Bounded deterministic birth radius in [0.2, 1.0] (source
        // createGroup birthRadius 0.8*randFloat()+0.2), 45-unit distribution.
        const float radius = 0.2f + 0.8f * (float(unsigned(i * 2654435761u) & 0xffffu) / 65535.0f);
        const float face = 6.28318531f * float(i) / float(count);
        const Vector3f offset(45.0f * radius * std::sin(face), 0.0f,
                              45.0f * radius * std::cos(face));
        Vector3f pos = hostPos + offset;
        child->inputPosition(pos);
        child->startAI(0);
        const unsigned gen = hostGen + 1u + unsigned(i);
        Tamago& s = actors[static_cast<PelletView*>(child)];
        s.generator = gen;
        s.home = pos;
        s.heading = 0.0f;
        child->mHealth = LIFE;
        s.isLeader = false;
        s.leaderGenerator = hostGen;
        s.leaderActor = host;
        enter(s, TAMAGO_APPEAR, "set");
        std::printf("P2_TAMAGO_GROUP leader=%u follower=%u source_id=68\n", hostGen, gen);
        // born=1 flags the synthetic (manager-birth) id, distinct from a staged id.
        std::printf("P2_TAMAGO_BIND generator=%u source_id=68 visual_only=0 born=1\n", gen);
        ++born;
    }
    std::printf("P2_TAMAGO_BIRTH host=%u leader=%u follow=%d count=%d source=manager\n",
                hostGen, hostGen, born, count);
    std::printf("P2_TAMAGO_BIRTH_ONCE host=%u born=%d\n", hostGen, born);
    std::fflush(stdout);
}

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

    // Manager-driven birth mode: a single staged host births its own group on
    // Appear (source createFellow / tamagoMushiMgr::createGroup), exactly once.
    hostGenerator = 0;
    hostGroupCount = 0;
    birthMode = false;
    std::ifstream hostFile("p2-tamago-host.txt");
    if (hostFile) {
        std::string hdr;
        unsigned long long hg = 0;
        int hc = 0;
        if (hostFile >> hdr >> hg >> hc && hdr == "P2_TAMAGO_HOST_1" && hc >= 1 && hc <= 100) {
            birthMode = true;
            hostGenerator = unsigned(hg);
            hostGroupCount = hc;
        }
    }
    if (birthMode) {
        BTeki* hostActor = nullptr;
        Iterator hit(tekiMgr);
        CI_LOOP(hit) {
            Teki* actor = static_cast<Teki*>(*hit);
            if (actor && actor->mGenerator && actor->mGenerator->_70 == hostGenerator) {
                hostActor = actor;
                break;
            }
        }
        if (!hostActor) {
            std::printf("P2_TAMAGO_ERROR missing_host host=%u\n", hostGenerator);
            std::abort();
        }
        Tamago& s = actors[static_cast<PelletView*>(hostActor)];
        s.generator = hostGenerator;
        s.home = hostActor->getPosition();
        s.heading = hostActor->getDirection();
        hostActor->mHealth = LIFE;
        s.isLeader = true;
        s.isGroupHost = true;
        s.madeFellow = false;
        s.leaderGenerator = hostGenerator;
        s.leaderActor = hostActor;
        enter(s, TAMAGO_APPEAR, "set");
        std::printf("P2_TAMAGO_HOST_BIND host=%u egg=1 source_id=68\n", hostGenerator);
        std::printf("P2_TAMAGO_LEADER generator=%u followers=0 surface_count=%d cave_count=%d "
                    "source_group=createGroup\n",
                    hostGenerator, SOURCE_GROUP_SURFACE, SOURCE_GROUP_CAVE);
        std::printf("P2_TAMAGO_BIND generator=%u source_id=68 visual_only=0\n", hostGenerator);
        const Vector3f pos = hostActor->getPosition();
        std::printf("P2_ENEMY_READY species=TamagoMushi native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented astonish=native_P1_approx honey=native\n",
                    hostGenerator, pos.x, pos.y, pos.z, hostActor->mHealth, LIFE);
        ready = true;
        return;
    }

    // Collect the staged cluster first so the leader can be chosen
    // deterministically (smallest generator) before any state is assigned.
    std::vector<std::pair<BTeki*, unsigned>> matched;
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
        if (!found.insert(actor->mGenerator->_70).second) continue;
        matched.emplace_back(actor, actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_TAMAGO_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::abort();
    }
    if (matched.empty()) return;
    std::sort(matched.begin(), matched.end(),
              [](const std::pair<BTeki*, unsigned>& a, const std::pair<BTeki*, unsigned>& b) {
                  return a.second < b.second;
              });
    BTeki* leaderActor = matched.front().first;
    const unsigned leaderGenerator = matched.front().second;
    const Vector3f leaderHome = leaderActor->getPosition();
    std::printf("P2_TAMAGO_LEADER generator=%u followers=%zu surface_count=%d cave_count=%d "
                "source_group=createGroup\n",
                leaderGenerator, matched.size() - 1, SOURCE_GROUP_SURFACE, SOURCE_GROUP_CAVE);

    for (const auto& entry : matched) {
        BTeki* actor = entry.first;
        const unsigned generator = entry.second;
        Tamago& s = actors[static_cast<PelletView*>(actor)];
        s.generator = generator;
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        actor->mHealth = LIFE;
        s.isLeader = (generator == leaderGenerator);
        s.leaderGenerator = leaderGenerator;
        s.leaderActor = leaderActor;
        if (s.isLeader) {
            enter(s, TAMAGO_WALK, "move");
        } else {
            // Followers emerge near the leader and keep their wandering bounded
            // to the leader's home territory.
            s.home = leaderHome;
            enter(s, TAMAGO_APPEAR, "set");
            std::printf("P2_TAMAGO_GROUP leader=%u follower=%u source_id=68\n",
                        leaderGenerator, generator);
        }
        std::printf("P2_TAMAGO_BIND generator=%u source_id=68 visual_only=0\n", generator);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=TamagoMushi native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented astonish=native_P1_approx honey=native\n",
                    generator, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
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
    const unsigned generator = s.generator;

    // Manager-driven birth trigger: the host births its group exactly once on its
    // first Appear (source createFellow, guarded by mHasMadeFellow).
    if (birthMode && s.isGroupHost && s.state == TAMAGO_APPEAR && !s.madeFellow) {
        pc_p2_tamago_birth_group(actor, hostGroupCount);
    }

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

    const bool follower = !s.isLeader && s.leaderActor && s.leaderActor != actor;
    const float leaderDistance = follower ? distXZ(pos, s.leaderActor->getPosition()) : 0.0f;

    s.stateTime += dt;
    if (follower && s.state != TAMAGO_DEAD && leaderDistance > FOLLOW_RADIUS) {
        // Bounded swarm leash: outside the follow radius the follower overrides
        // the ground cycle and drives straight at the live leader.
        if (s.state != TAMAGO_WALK) enter(s, TAMAGO_WALK, "move");
        const Vector3f leaderPos = s.leaderActor->getPosition();
        s.heading = wrapPi(std::atan2(leaderPos.x - pos.x, leaderPos.z - pos.z));
        wander(actor, s);
    } else {
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
    }
    setPhase(s);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        std::printf("P2_TAMAGO_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z);
        if (follower) {
            std::printf("P2_TAMAGO_FOLLOW generator=%u leader=%u distance=%.2f state=%s "
                        "x=%.2f z=%.2f\n",
                        generator, s.leaderGenerator, leaderDistance, stateName(s.state),
                        pos.x, pos.z);
        }
        std::fflush(stdout);
    }
}
