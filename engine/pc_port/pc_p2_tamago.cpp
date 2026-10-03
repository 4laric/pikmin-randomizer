// Family-owned ground-invertebrate source behavior for the batch-2 Chappy
// placement vehicle: Mitite (TamagoMushi, EnemyID 68). Implements the source
// tamagoMushiState.cpp cycle (Walk/Turn/Appear/Hide/Wait/Dead), the
// collisionCallback Astonish receiver (tamagoMushi.cpp:239) and the genItem
// honey reward (tamagoMushi.cpp:326). Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_ground_inverts_assets.py (GPVE01 rev 0).
//
// Campaign (per-placement) mode, issue #992 -- source behaviour:
//   * Every placement is its own leader. It starts hidden in StateAppear (no atari,
//     invulnerable, appear clip held at frame 0) until a Pikmin or captain comes
//     within the retail appearance range fp02 = 120 (Obj::isFound). The leader then
//     births nine fellows (Mgr::createGroup, count 10, ground offsets), every member
//     waits a random 20..90 ticks and emerges; at the appear clip's KEYEVENT_2 the
//     leader astonishes every Pikmin within 150 (Obj::appearPanic).
//   * Any Pikmin touching a surfaced Mitite is astonished (collisionCallback), via
//     the real PikiPanicState astonish (pc_p2_astonish). Nothing damages a Pikmin.
//   * Walk/Turn cycle with the retail ip01/ip02 tick windows, then after
//     0.8..1.0 x 180 ticks the member dives (StateHide); fellows are killed there as
//     in the source, the bound leader recycles to hidden so its check stays reachable.
//   * Fellows carry no delivery source: one placement is one check, not ten.
// Port adaptations (recorded, not retail-faithful):
//   * Legacy arena fixtures (no campaign bridge) keep the InteractFlick approximation
//     of the contact receiver, applied once per contact.
//   * Walk ends into Turn (source KEYEVENT_END) before Hide; Hide recycles to
//     Appear as a bounded port approximation (source Hide despawns the actor,
//     which would end the campaign encounter before any kill).
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
#include "pc_p2_tamago_policy.h"
#include "pc_p2_astonish.h"
#include "pc_p2_navi_select.h"
#include "pc_p2_batch2.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_randomizer.h"
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
    bool escaped = false;
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
    // Campaign per-placement source FSM (#992).
    bool sourceMode = false;
    bool ballFall = false;
    bool bigFootDrop = false;
    bool born = false;
    int member = 0;
    bool hidden = true;
    bool gate = false;
    bool found = false;
    bool emerging = false;
    bool panicFired = false;
    bool cleanupDone = false;
    float appearDelay = 0.0f;
    float appearTimer = 0.0f;
    float walkMax = 0.0f;
    float activeTicks = 0.0f;
    float activeMax = 0.0f;
    float turnFactor = 1.0f;
    float speedFactor = 1.0f;
    float moveOffset = 0.0f;
    Vector3f goal;
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
float rnd01() { return gsys ? gsys->getRand(1.0f) : 0.5f; }
// Source Stay/Appear: invulnerable, no atari while hidden (mirrors pc_p2_hana).
void applyGate(BTeki* a, Tamago& s) {
    const bool under = s.hidden;
    if (under == s.gate) return;
    s.gate = under;
    if (under) {
        a->clearTekiOption(TEKIOPT_Atari);
        a->setTekiOption(TEKIOPT_Invincible);
    } else {
        a->setTekiOption(TEKIOPT_Atari);
        a->clearTekiOption(TEKIOPT_Invincible);
    }
}
// Obj::isFound inputs: nearest live Pikmin / captain inside the appearance range.
bool foundNear(const Vector3f& pos) {
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            const Vector3f q = p->getPosition();
            if (p2tamagopolicy::withinAppearRange(distXZ(q, pos))) return true;
        }
    }
    if (naviMgr) {
        for (Navi* n : pc_p2_navis()) {
            if (!n->isAlive()) continue;
            if (p2tamagopolicy::withinAppearRange(distXZ(n->getPosition(), pos))) return true;
        }
    }
    return false;
}
void beginSourceAppear(BTeki* a, Tamago& s) {
    enter(s, TAMAGO_APPEAR, "set");
    s.hidden = true;
    s.found = false;
    s.emerging = false;
    s.panicFired = false;
    s.appearTimer = 0.0f;
    s.appearDelay = p2tamagopolicy::appearDelaySeconds(rnd01());
    s.activeTicks = 0.0f;
    s.activeMax = p2tamagopolicy::activeMaxTicks(rnd01());
    s.phase = 0.0f;
    stop(a);
}
void pickGoal(BTeki* a, Tamago& s) {
    const float r = p2tamagopolicy::Territory * (0.5f * rnd01() + 0.5f);
    const float ang = 6.28318531f * rnd01();
    s.goal = s.home;
    s.goal.x += r * std::sin(ang);
    s.goal.z += r * std::cos(ang);
    (void)a;
}
// Obj::appearPanic: only the leader; every Pikmin within the panic radius.
int appearPanic(BTeki* a, Tamago& s) {
    if (s.born) return 0;
    const Vector3f pos = a->getPosition();
    int hit = 0, seen = 0;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            if (distXZ(p->getPosition(), pos) >= p2tamagopolicy::PanicRadius) continue;
            ++seen;
            if (pc_p2_astonish_request(p, a, s.generator, "mitite_appear")) ++hit;
        }
    }
    std::printf("P2_TAMAGO_APPEAR_PANIC generator=%u radius=%.0f pikmin_in_radius=%d astonished=%d\n",
                s.generator, p2tamagopolicy::PanicRadius, seen, hit);
    std::fflush(stdout);
    return hit;
}
// collisionCallback: a Pikmin touching a surfaced Mitite is astonished.
void astonishContactsSource(BTeki* a, Tamago& s) {
    if (s.hidden || s.state == TAMAGO_APPEAR || s.state == TAMAGO_DEAD || !pikiMgr) return;
    const Vector3f pos = a->getPosition();
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        if (distXZ(p->getPosition(), pos) > p2tamagopolicy::ContactRadius) continue;
        if (pc_p2_astonish_request(p, a, s.generator, "mitite_contact")) {
            std::printf("P2_TAMAGO_ASTONISH generator=%u member=%d pikmin=1 source=contact harm=none\n",
                        s.generator, s.member);
            std::fflush(stdout);
        }
    }
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
    pc_p2_astonish_reset();
    actors.clear();
    clips.clear();
    pendingKills.clear();
    ready = false;
}
void pc_p2_tamago_forget(BTeki* actor) {
    // Lane 06 single-use binding: drop the ordinary-delivery source so a
    // recycled actor address can never inherit it. Idempotent with the
    // central pc_p2_forget_teki seam.
    pc_randomizer_p2_forget_source(static_cast<PelletView*>(actor));
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
bool pc_p2_tamago_suppress_ai(const BTeki* actor) {
    return ready && actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor))) != 0;
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

// Source Obj::createFellow -> Mgr::createGroup(leader, count, false): births
// count-1 fellows around the leader. Unbound (one placement is one check), each
// hidden in StateAppear until the leader is found.
static int birthFellowsSource(BTeki* host, Tamago& hs, int count) {
    int born = 0;
    const Vector3f hostPos = host->getPosition();
    const int follow = p2tamagopolicy::fellowCount(count);
    for (int i = 0; i < follow; ++i) {
        Teki* child = host->generateTeki(TEKI_Chappy);
        if (!child) break;
        const p2tamagopolicy::Offset o = p2tamagopolicy::fellowOffset(i, count, rnd01());
        Vector3f pos = hostPos;
        pos.x += o.x;
        pos.z += o.z;
        child->inputPosition(pos);
        child->startAI(0);
        child->setDirection(o.faceDir);
        child->mHealth = LIFE;
        Tamago& s = actors[static_cast<PelletView*>(child)];
        s = Tamago();
        s.sourceMode = true;
        s.born = true;
        s.member = i + 1;
        s.generator = hs.generator;
        s.leaderGenerator = hs.generator;
        s.leaderActor = host;
        s.isLeader = false;
        s.home = pos;
        s.heading = o.faceDir;
        s.speedFactor = 0.7f + 0.3f * rnd01();
        s.turnFactor = 0.7f + 0.3f * rnd01();
        beginSourceAppear(child, s);
        // The leader is already found when fellows are born, so they start the
        // random emerge delay at once (source isFound defers to the leader).
        s.found = true;
        pc_p2_batch2_adopt(child, host);
        ++born;
    }
    return born;
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
        pc_randomizer_p2_bind_source(static_cast<PelletView*>(child), 68, gen);
        std::printf("P2_TAMAGO_DELIVERY_BIND generator=%u source_id=68 born=1\n", gen);
        std::printf("P2_TAMAGO_BIND generator=%u source_id=68 visual_only=0 born=1\n", gen);
        ++born;
    }
    std::printf("P2_TAMAGO_BIRTH host=%u leader=%u follow=%d count=%d source=manager\n",
                hostGen, hostGen, born, count);
    std::printf("P2_TAMAGO_BIRTH_ONCE host=%u born=%d\n", hostGen, born);
    std::fflush(stdout);
}

bool pc_p2_tamago_prepare_bigfoot() {
    // BigFoot's Chappy vehicle already loads the child manager's host resources.
    // P2 enemyInfo declares TamagoMushi as its dependency, even with no source68
    // placements. Bank preload must not manufacture a generator or AP check.
    const bool available = pc_p2_batch2_prepare_tamago();
    std::printf("P2_BIGFOOT_MITITE_RESOURCE ready=%d\n", int(available));
    if (available) ready = true;
    return available;
}

int pc_p2_tamago_birth_bigfoot(BTeki* boss, unsigned generator, const Vector3f& position) {
    if (!boss || !ready || !pc_p2_batch2_prepare_tamago()) return 0;
    BTeki* leader = nullptr;
    const int born = p2tamagopolicy::bigFootGroup([&](int member) {
        Teki* child = boss->generateTeki(TEKI_Chappy);
        if (!child) return false;
        Vector3f pos = position;
        const auto offset = p2tamagopolicy::bigFootOffset(member, rnd01(), rnd01());
        pos.x += offset.x;
        pos.z += offset.z;
        const float yaw = offset.faceDir;
        const float vy = p2tamagopolicy::bigFootFallSpeed(member, rnd01());
        child->inputPosition(pos);
        child->startAI(0);
        child->resetCreatureFlag(CF_IsOnGround); // pooled/reset contact is not a fall impact
        child->setDirection(yaw);
        child->mHealth = LIFE;
        child->mVelocity.set(0.0f, vy, 0.0f);
        if (!leader) leader = child;
        Tamago& s = actors[static_cast<PelletView*>(child)];
        s = Tamago();
        s.sourceMode = s.born = s.madeFellow = s.ballFall = true;
        s.bigFootDrop = true;
        s.hidden = false; // source setTypeBall: visible falling Wait, no atari
        s.generator = s.leaderGenerator = generator;
        s.member = member;
        s.home = pos;
        s.heading = yaw;
        s.leaderActor = leader;
        s.isLeader = child == leader;
        s.speedFactor = 0.7f + 0.3f * rnd01();
        s.turnFactor = 0.7f + 0.3f * rnd01();
        s.activeMax = p2tamagopolicy::activeMaxTicks(rnd01());
        enter(s, TAMAGO_WAIT, "wait");
        child->clearTekiOption(TEKIOPT_Atari);
        child->setTekiOption(TEKIOPT_Invincible);
        pc_p2_batch2_bind_tamago(child);
        // Deliberately no campaign/source binding: children are drops, not slots.
        std::printf("P2_BIGFOOT_MITITE_BORN generator=%u member=%d x=%.1f y=%.1f z=%.1f vy=%.1f bound=0\n",
                    generator, member, pos.x, pos.y, pos.z, vy);
        return true;
    });
    std::printf("P2_BIGFOOT_MITITE_GROUP generator=%u count=%d requested=30\n", generator, born);
    std::fflush(stdout);
    return born;
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
    // inst-bugs lane (#871): a killed Mitite leaves its natural carriable
    // corpse (the campaign kill->carry->Onion loop needs a real pellet for
    // the onion:p2:68 receipt) alongside the exactly-once honey drop
    // (dropHoney). Previously NoCorpse here made every identity corpse
    // uncarriable (carry_no_grab, carriers=0): the dead Teki slid without
    // ever pelletizing because dieSoon saw NoCorpse.
    return fallback;
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
    // inst-bugs lane (#871): in bridge campaigns the seed owns the binding,
    // so the filed ids are placeholders replaced from pc_p2_campaign_ids(68)
    // (mirrors pc_p2_sokkuri_setup).
    const bool bridge = pc_randomizer_p2_bridge();
    if (bridge) {
        wanted.clear();
        for (unsigned id : pc_p2_campaign_ids(68)) wanted[id] = "TamagoMushi";
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
            if (!actor) continue;
            const unsigned key =
                bridge ? pc_p2_campaign_token(actor)
                       : (actor->mGenerator ? actor->mGenerator->_70 : 0u);
            if (key == hostGenerator) {
                hostActor = actor;
                break;
            }
        }
        if (!hostActor) {
            std::printf("P2_TAMAGO_ERROR missing_host host=%u\n", hostGenerator);
            if (pc_p2_setup_skip(bridge, "TamagoMushi", "actor_roster_incomplete")) return;
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
        // Ordinary-delivery bridge (lane 06 contract): bind source 68 so
        // GoalItem::suckMe grants onion:p2:68 exactly once. Single-use.
        pc_randomizer_p2_bind_source(static_cast<PelletView*>(hostActor), 68, hostGenerator);
        std::printf("P2_TAMAGO_DELIVERY_BIND generator=%u source_id=68\n", hostGenerator);
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
        if (!actor) continue;
        const unsigned key =
            bridge ? pc_p2_campaign_token(actor)
                   : (actor->mGenerator ? actor->mGenerator->_70 : 0u);
        if (!bridge && key == 0u) continue;
        auto match = wanted.find(key);
        if (match == wanted.end()) continue;
        if (actor->mTekiType != TEKI_Chappy) {
            std::printf("P2_TAMAGO_ERROR native_type generator=%u\n", key);
            if (pc_p2_setup_skip(bridge, "TamagoMushi", "actor_type_mismatch")) return;
            std::abort();
        }
        // Swarm members share one campaign token: bind every live member
        // (each corpse needs its own delivery source) while counting the
        // token once toward the roster check.
        found.insert(key);
        matched.emplace_back(actor, key);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_TAMAGO_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        if (pc_p2_setup_skip(bridge, "TamagoMushi", "actor_roster_incomplete")) return;
        std::abort();
    }
    if (matched.empty()) return;
    std::sort(matched.begin(), matched.end(),
              [](const std::pair<BTeki*, unsigned>& a, const std::pair<BTeki*, unsigned>& b) {
                  return a.second < b.second;
              });
    if (bridge) {
        // Campaign (#992): every placement is its own leader; staged members that
        // share one campaign token join the first member of that token as fellows.
        std::map<unsigned, BTeki*> leaders;
        for (const auto& entry : matched) {
            BTeki* actor = entry.first;
            const unsigned generator = entry.second;
            Tamago& s = actors[static_cast<PelletView*>(actor)];
            s = Tamago();
            s.sourceMode = true;
            s.generator = generator;
            s.home = actor->getPosition();
            s.heading = actor->getDirection();
            s.speedFactor = 0.7f + 0.3f * rnd01();
            s.turnFactor = 0.7f + 0.3f * rnd01();
            actor->mHealth = LIFE;
            auto lead = leaders.find(generator);
            if (lead == leaders.end()) {
                leaders[generator] = actor;
                s.isLeader = true;
                s.leaderGenerator = generator;
                s.leaderActor = actor;
            } else {
                s.isLeader = false;
                s.born = true;
                s.member = 1;
                s.leaderGenerator = generator;
                s.leaderActor = lead->second;
            }
            beginSourceAppear(actor, s);
            pc_randomizer_p2_bind_source(static_cast<PelletView*>(actor), 68, generator);
            std::printf("P2_TAMAGO_DELIVERY_BIND generator=%u source_id=68\n", generator);
            std::printf("P2_TAMAGO_BIND generator=%u source_id=68 visual_only=0\n", generator);
            const Vector3f pos = actor->getPosition();
            std::printf("P2_TAMAGO_SOURCE_READY generator=%u leader=%d hidden=1 appear_range=%.0f "
                        "group=%d pikmin_harm=none scare=astonish\n",
                        generator, int(s.isLeader), p2tamagopolicy::AppearRange, p2tamagopolicy::GroupCount);
            std::printf("P2_ENEMY_READY species=TamagoMushi native_family=Chappy generator=%u "
                        "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                        "source_FSM=implemented astonish=native_PikiPanic group=10 honey=native\n",
                        generator, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        }
        ready = true;
        return;
    }
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
        pc_randomizer_p2_bind_source(static_cast<PelletView*>(actor), 68, generator);
        std::printf("P2_TAMAGO_DELIVERY_BIND generator=%u source_id=68\n", generator);
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

    // The P1 TAI damage reaction lives in the suppressed host strategy, so
    // the P2 FSM drains queued Pikmin damage itself (frog pattern).
    if (actor->mStoredDamage > 0.0f) actor->makeDamaged();

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

    if (s.sourceMode) {
        if (s.ballFall && s.state != TAMAGO_DEAD) {
            // P2 StateWait ends on bounceCallback. The P1 collision flag is set
            // by the real terrain trace; do not freeze vertical falling velocity.
            s.stateTime += dt;
            s.phase = std::fmod(s.stateTime / clipDuration("wait"), 1.0f);
            if (s.stateTime > dt && actor->isCreatureFlag(CF_IsOnGround)) {
                s.ballFall = false;
                s.hidden = false;
                actor->setTekiOption(TEKIOPT_Atari);
                actor->clearTekiOption(TEKIOPT_Invincible);
                // Source bounceCallback: rise10, horizontal80, vertical35..50.
                Vector3f bounced = actor->getPosition();
                bounced.y += 10.0f;
                actor->inputPosition(bounced);
                actor->resetCreatureFlag(CF_IsOnGround);
                actor->mVelocity.set(std::sin(s.heading) * 80.0f,
                                     50.0f * (0.7f + 0.3f * rnd01()), std::cos(s.heading) * 80.0f);
                appearPanic(actor, s);
                s.walkMax = p2tamagopolicy::walkSeconds(rnd01());
                pickGoal(actor, s);
                enter(s, TAMAGO_WALK, "move");
                std::printf("P2_BIGFOOT_MITITE_LAND generator=%u member=%d\n", generator, s.member);
            }
            return;
        }
        if (s.state != TAMAGO_DEAD) astonishContactsSource(actor, s);
        s.stateTime += dt;
        switch (s.state) {
        case TAMAGO_APPEAR: {
            stop(actor);
            if (!s.found) {
                bool f;
                if (s.born && s.leaderActor && s.leaderActor != actor) {
                    auto lit = actors.find(static_cast<PelletView*>(s.leaderActor));
                    f = lit != actors.end() && lit->second.found;
                } else {
                    f = foundNear(pos);
                }
                if (f) {
                    s.found = true;
                    if (!s.born) {
                        std::printf("P2_TAMAGO_FOUND generator=%u range=%.0f x=%.1f z=%.1f\n", generator,
                                    p2tamagopolicy::AppearRange, pos.x, pos.z);
                        if (!s.madeFellow && !birthMode) {
                            s.madeFellow = true;
                            int alive = 0;
                            for (auto& e : actors)
                                if (e.second.born && e.second.leaderActor == actor && e.first != static_cast<PelletView*>(actor)) ++alive;
                            const int born = alive > 0 ? 0 : birthFellowsSource(actor, s, p2tamagopolicy::GroupCount);
                            s.isGroupHost = false;
                            std::printf("P2_TAMAGO_GROUP_BIRTH host=%u count=%d fellows=%d born=%d source=createFellow\n",
                                        generator, p2tamagopolicy::GroupCount, p2tamagopolicy::fellowCount(p2tamagopolicy::GroupCount), born);
                        }
                    }
                }
                s.phase = 0.0f;
                break;
            }
            s.appearTimer += dt;
            if (!s.emerging) {
                if (s.appearTimer > s.appearDelay) {
                    s.emerging = true;
                    s.stateTime = 0.0f;
                    std::printf("P2_TAMAGO_EMERGE generator=%u member=%d delay=%.2f\n", generator, s.member, s.appearDelay);
                } else {
                    s.phase = 0.0f;
                    break;
                }
            }
            if (!s.panicFired && s.stateTime >= p2tamagopolicy::AppearEventSeconds) {
                s.panicFired = true;
                s.hidden = false;
                appearPanic(actor, s);
            }
            if (s.stateTime >= clipDuration("set")) {
                std::printf("P2_TAMAGO_STATE generator=%u member=%d state=walk\n", generator, s.member);
                s.activeTicks = 0.0f;
                s.walkMax = p2tamagopolicy::walkSeconds(rnd01());
                pickGoal(actor, s);
                enter(s, TAMAGO_WALK, "move");
            }
            break;
        }
        case TAMAGO_WALK: {
            // Source: walk along the wander heading, speed = speedFactor * fp06.
            const float want = std::atan2(s.goal.x - pos.x, s.goal.z - pos.z);
            const float turn = s.turnFactor * 3.14159265f * dt;
            float diff = wrapPi(want - s.heading);
            if (diff > turn) diff = turn;
            if (diff < -turn) diff = -turn;
            s.moveOffset += 0.3f;
            s.heading = wrapPi(s.heading + diff + 0.15f * std::sin(s.moveOffset) * dt);
            actor->setDirection(s.heading);
            const float speed = s.speedFactor * p2tamagopolicy::MoveSpeed;
            const Vector3f drive(std::sin(s.heading) * speed, 0.0f, std::cos(s.heading) * speed);
            actor->inputDrive(drive);
            // Keep the source bounce's vertical arc through normal terrain physics.
            const float vy = s.bigFootDrop && !actor->isCreatureFlag(CF_IsOnGround) ? actor->mVelocity.y : 0.0f;
            actor->mVelocity.set(drive.x, vy, drive.z);
            s.activeTicks += dt / p2tamagopolicy::TickSeconds;
            if (distXZ(pos, s.goal) < 10.0f || s.stateTime > s.walkMax) {
                std::printf("P2_TAMAGO_STATE generator=%u member=%d state=turn\n", generator, s.member);
                pickGoal(actor, s);
                enter(s, TAMAGO_TURN, "wait");
            }
            break;
        }
        case TAMAGO_TURN: {
            stop(actor);
            const float want = std::atan2(s.goal.x - pos.x, s.goal.z - pos.z);
            const float turn = s.turnFactor * 3.14159265f * dt * 2.0f;
            float diff = wrapPi(want - s.heading);
            const bool done = std::fabs(diff) < 0.1f;
            if (diff > turn) diff = turn;
            if (diff < -turn) diff = -turn;
            s.heading = wrapPi(s.heading + diff);
            actor->setDirection(s.heading);
            s.activeTicks += dt / p2tamagopolicy::TickSeconds;
            if (done || s.stateTime > 1.5f) {
                s.walkMax = p2tamagopolicy::walkSeconds(rnd01());
                enter(s, TAMAGO_WALK, "move");
            }
            break;
        }
        case TAMAGO_HIDE:
            stop(actor);
            if (s.stateTime >= clipDuration("dive")) {
                if (s.born) {
                    s.hidden = true;
                    applyGate(actor, s);
                    if (!s.cleanupDone) {
                        std::printf("P2_TAMAGO_HIDE_KILL generator=%u member=%d source=StateHide\n", generator, s.member);
                        std::fflush(stdout);
                        s.cleanupDone = true;
                        pendingKills.push_back(actor); // drained by pc_p2_tamago_tick
                    }
                    break;
                }
                std::printf("P2_TAMAGO_HIDE_RECYCLE generator=%u bound_leader=1\n", generator);
                s.madeFellow = false;
                beginSourceAppear(actor, s);
            }
            break;
        case TAMAGO_DEAD:
            stop(actor);
            s.hidden = false;
            if (!s.escaped && s.stateTime >= clipDuration("dead")) {
                s.escaped = true;
                actor->pcEscapeNow();
            }
            break;
        default:
            break;
        }
        if ((s.state == TAMAGO_WALK || s.state == TAMAGO_TURN) &&
            p2tamagopolicy::shouldHide(s.activeTicks, s.activeMax)) {
            std::printf("P2_TAMAGO_STATE generator=%u member=%d state=hide active_ticks=%.0f\n", generator, s.member, s.activeTicks);
            enter(s, TAMAGO_HIDE, "dive");
        }
        applyGate(actor, s);
        setPhase(s);
        if (s.state == TAMAGO_APPEAR && !s.emerging) s.phase = 0.0f;
        s.logTimer += dt;
        if (s.logTimer >= 1.0f) {
            s.logTimer = 0.0f;
            std::printf("P2_TAMAGO_POS generator=%u member=%d state=%s clip=%s phase=%.2f x=%.2f z=%.2f hidden=%d\n",
                        generator, s.member, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z, int(s.hidden));
            std::fflush(stdout);
        }
        return;
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
                // Source Walk ends on KEYEVENT_END into Turn; the port Turn
                // reorients briefly before hiding (was dead code).
                std::printf("P2_TAMAGO_STATE generator=%u state=turn\n", generator);
                enter(s, TAMAGO_TURN, "move");
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
            if (s.stateTime > TURN_TIME) {
                std::printf("P2_TAMAGO_STATE generator=%u state=hide\n", generator);
                enter(s, TAMAGO_HIDE, "dive");
            }
            break;
        case TAMAGO_DEAD:
            // dieSoon() only runs inside the suppressed host doAI; finalize
            // the carriable corpse outside doAI once the dead clip completes
            // (frog pattern). Honey already dropped exactly-once at entry.
            stop(actor);
            if (!s.escaped && s.stateTime >= clipDuration("dead")) {
                s.escaped = true;
                actor->pcEscapeNow();
            }
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
