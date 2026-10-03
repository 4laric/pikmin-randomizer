// Shared-base snagret source behavior for the batch-3 Chappy placement vehicle:
// Burrowing Snagret (SnakeCrow, EnemyID 34) and Pileated Snagret (SnakeWhole,
// EnemyID 70). Both species share the source `Game::SnakeJointMgr` spine over
// `bodyjnt3`-`bodyjnt8` (SnakeJointMgr.h:30,47; SnakeCrow.cpp:1471;
// SnakeWhole.cpp:1898) and register their own per-species FSM in
// SnakeCrowState.cpp / SnakeWholeState.cpp. This module implements the bounded
// shared FSM for BOTH:
//   Stay (burrow) -> Appear1/Appear2 (emerge) -> Wait/Turn/Move ->
//   Attack (bite: one directional bite capture) -> Eat (one swallow kill) ->
//   Struggle -> Disappear (dive flick) -> Stay, plus Dead.
// Source revision 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms and
// banked event frames from experimental/pikmin2_snagret_assets.py (GPVE01 rev
// 0, SPECIES/STATE_IDS/EXPECTED_EVENTS/DISC_PARMS). The attack stems are the
// disc spellings hit_near/hit/hit_far/hit_r/hit_l (SnakeCrow.h:232-236,
// SnakeWhole.h:230-234); the Eat clip is waitact1 and the dive clip is dive.
//
// Neither snagret is a `ChappyBase` and neither has a Pikmin 1 counterpart
// (docs/PIKMIN2_SNAGRET_ASSETS.md section 9): the P1 Chappy (TEKI_Chappy) is
// used only as a placement vehicle (expected native type) so the source FSM can
// run on the P1 engine.
//
// Port adaptations (recorded, not retail-faithful):
//   * The shared joint/neck segment chain (SnakeJointMgr bodyjnt3-bodyjnt8,
//     six driven joints) is a P2 model/skeleton feature that is not
//     representable on the P1 host; the module drives a flat translation-only
//     body and does not rebuild the spinal matrices or the joint callback.
//   * Bite (#886): the source five facing boxes of Obj::getAttackPiki /
//     getAttackNavi (SnakeCrow.cpp:348-450, SnakeWhole.cpp:404-510) and
//     the setAttackPosition floor heights are ported exactly in
//     pc_p2_captor_mouth.h. The attack starts only when a Pikmin or captain
//     is inside a box (animIdx 5 query, which also picks mAttackAnimIdx); at
//     the KEYEVENT_3 bite only that box is searched and the Pikmin is
//     InteractSwallow'd into the first free of the three kamujnt slots
//     (getSwallowSlot), physically stuck to the P1 host 'slot' part
//     (pc_p2_captor_host.h) so it cannot be whistled away. Eat (waitact1
//     KEYEVENT_2) swallows only Pikmin still held (white poison proper fp21).
//     With all three slots full the bite is refused (the source asserts on a
//     null slot). Port adaptation kept: the drawn stem is always the normal
//     `hit` clip, whatever box was chosen.
//   * Target detection is a full hemisphere (the source fp13 view-angle gate is
//     not applied to the P1 host), matching the Catfish/Armor ports.
//   * The source `appearNearByTarget` 120-unit reposition (SnakeCrow.cpp:297,
//     SnakeWhole.cpp:331) is not applied; the P1 host emerges in place. The
//     arena fixture stages each actor inside the source private radius.
//   * The falling Rock/Egg child spawner (DangoMushi only) and the SnakeCrow
//     White Flower Garden `mWFGHealth` (proper fp31) story override are N/A
//     here; the module always uses the retail general fp00 life.
//   * The P2 invulnerability/ModelHidden state flags, the burrow model hide and
//     the joint/rotate/wait/dead effects are P2-only and are not reproduced.
//   * Walk/leap uses the SnakeWhole source fp06=1000 leap clamped to a
//     P1-host speed; SnakeCrow is stationary (fp06=0) and never walks.
//   * View angle, turn rate, flick radius and shake values are P1-host values;
//     when the installed p2-snagret-bank.txt is absent the audited retail event
//     frames are used with 1 s fallback clip durations.
// No other lane's module is modified; every hook is a no-op for unregistered
// actors.
#include "pc_p2_snakejoint.h"
#include "pc_p2_original_actor.h"
#include "pc_p2_original_snagret_bank.h"
#include "pc_p2_original_snagret_death.h"
#include "pc_p2_original_drop_engine.h"
#include "pc_p2_original_bulblax_snagret_native.h"
#include "pc_p2_captor_host.h"
#include "MapMgr.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_randomizer.h"
#include "teki.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "pc_p2_navi_select.h"
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
    SNAKE_INVALID = -1,
    SNAKE_DEAD = 0,
    SNAKE_STAY = 1,
    SNAKE_APPEAR1 = 2,
    SNAKE_APPEAR2 = 3,
    SNAKE_DISAPPEAR = 4,
    SNAKE_WAIT = 5,
    SNAKE_WALK = 6,
    SNAKE_HOME = 7,
    SNAKE_ATTACK = 8,
    SNAKE_EAT = 9,
    SNAKE_STRUGGLE = 10,
};

const char* stateName(State s) {
    switch (s) {
    case SNAKE_DEAD: return "dead";
    case SNAKE_STAY: return "stay";
    case SNAKE_APPEAR1: return "appear1";
    case SNAKE_APPEAR2: return "appear2";
    case SNAKE_DISAPPEAR: return "disappear";
    case SNAKE_WAIT: return "wait";
    case SNAKE_WALK: return "walk";
    case SNAKE_HOME: return "home";
    case SNAKE_ATTACK: return "attack";
    case SNAKE_EAT: return "eat";
    case SNAKE_STRUGGLE: return "struggle";
    default: return "null";
    }
}

// Source enemyparm.txt retail values (snagret manifest general + proper). The
// general fp00/fp06/fp09/fp10/fp11/fp12/fp24 values are DISC_PARMS['general'],
// the proper fp01/fp11/fp12 are DISC_PARMS['proper']; fp28=10 deg is the retail
// general max turn shared by both species.
struct SpeciesParms {
    const char* name;
    int sourceId;
    float life;             // general fp00
    float moveSpeed;        // general fp06
    float territory;        // general fp09
    float homeRadius;       // general fp10
    float privateRadius;    // general fp11 (Stay wake distance)
    float sight;            // general fp12
    float turnRate;         // general fp08
    float maxTurn;          // general fp28 (10 deg)
    float waitTime;         // proper fp11
    float undergroundTime;  // proper fp12
    float fastAppearChance; // proper fp01
};
constexpr float DEG10 = 0.174532925f;
const SpeciesParms SNAKE_CROW = {
    "SnakeCrow", 34, 1500.0f, 0.0f, 80.0f, 100.0f, 100.0f, 150.0f,
    0.1f, DEG10, 2.5f, 2.5f, 0.6f};
const SpeciesParms SNAKE_WHOLE = {
    "SnakeWhole", 70, 5000.0f, 1000.0f, 380.0f, 100.0f, 100.0f, 400.0f,
    0.1f, DEG10, 0.5f, 2.5f, 0.6f};

// Attack start and bite use the source getAttackPiki/getAttackNavi facing
// boxes (pc_p2_captor_mouth.h SnakeZones), which replaced the pre-#886
// 220-unit omnidirectional ATTACK_RANGE.
// Port walk/leap clamp: the source SnakeWhole fp06=1000 leap is a 22-frame
// jump (SnakeWhole.cpp:263) not representable on the flat P1 host.
constexpr float LEAP_SPEED = 220.0f;
constexpr float WALK_TIMEOUT = 4.0f;
constexpr float STRUGGLE_TIME = 1.5f; // source StateStruggle::exec
// Port flick/flicker values: the source flick is a latched-Pikmin sweep at the
// dive KEYEVENT_2 (SnakeCrowState.cpp:400, SnakeWholeState.cpp:438).
constexpr float FLICK_RADIUS = 25.0f;
constexpr float SHAKE_RANGE = 200.0f;   // general fp17
constexpr float SHAKE_KNOCKBACK = 120.0f;
// Audited retail event fallbacks (EXPECTED_EVENTS): hit 34:3 (bite), waitact1
// 42:2 (swallow), dive 12:2 (flick).
constexpr int BITE_FALLBACK = 34;
constexpr int SWALLOW_FALLBACK = 42;
constexpr int FLICK_FALLBACK = 12;

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events;
};

struct Snake {
    const SpeciesParms* parms = &SNAKE_CROW;
    State state = SNAKE_STAY;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    Vector3f burrowPos;        // where a SnakeCrow is pinned; moves with each appearNearByTarget
    bool hidden = false;       // source EB_ModelHidden, set only while buried (Stay)
    bool wokeOnce = false;
    Vector3f moveTarget;
    p2captor::Held<Piki> held; // Pikmin in the kamujnt1..3 slots (validated against the host stick)
    int attackZone = p2captor::SnakeAnyZone; // source mAttackAnimIdx
    bool mouthLogged = false;
    bool biteFired = false;
    bool swallowFired = false;
    bool flickFired = false;
    std::string clip = "appear1";
    float phase = 0.0f;
    unsigned rng = 1;
    bool deadLogged = false;
    bool original = false;
    p2original::bulblax_snagret::DeathItems deathItems;
    bool escaped = false;
    float logTimer = 0.0f;
    // Slice-2 vulnerability gate: EB_Invulnerable only while buried (Stay).
    bool rejectLogged = false;  // first rejected attack per buried period
    bool acceptLogged = false;  // first admitted attack per emerged period
};

std::map<PelletView*, Snake> actors;
std::map<PelletView*, unsigned> corpses; // dead-actor delivery registry
std::map<std::string, std::map<std::string, Clip>> clipBank; // species -> clip
bool ready = false;
bool originalBank = false;
unsigned identityToken(const BTeki* actor) {
 const unsigned original=pc_p2_original_actor_token(static_cast<const Creature*>(actor));
 return original?original:(actor->mGenerator?pc_p2_campaign_token(actor):0u);
}

float wrapPi(float a) {
    while (a > PI) a -= TAU;
    while (a < -PI) a += TAU;
    return a;
}
float distXZ(const Vector3f& a, const Vector3f& b) {
    const float dx = a.x - b.x, dz = a.z - b.z;
    return std::sqrt(dx * dx + dz * dz);
}
unsigned nextRand(Snake& s) {
    s.rng = s.rng * 1664525u + 1013904223u;
    return s.rng >> 8;
}
float rand01(Snake& s) { return float(nextRand(s) & 0xffff) / 65535.0f; }

Clip* findClip(const std::string& species, const std::string& name) {
    auto speciesIt = clipBank.find(species);
    if (speciesIt == clipBank.end()) return nullptr;
    auto clipIt = speciesIt->second.find(name);
    return clipIt == speciesIt->second.end() ? nullptr : &clipIt->second;
}
float clipDuration(const std::string& species, const std::string& name) {
    Clip* clip = findClip(species, name);
    return clip ? clip->duration : 1.0f;
}
bool clipLoops(const std::string& species, const std::string& name) {
    Clip* clip = findClip(species, name);
    return clip && clip->loop;
}
int eventFrame(const std::string& species, const std::string& name, int type) {
    Clip* clip = findClip(species, name);
    if (clip) {
        for (const auto& event : clip->events)
            if (event.second == type) return event.first;
    }
    return -1;
}

Creature* nearestTarget(const Vector3f& pos, float radius) {
    Creature* best = nullptr;
    float bestSq = radius * radius;
    if (naviMgr) {
        for (Navi* n : pc_p2_navis()) {
            if (!n->isAlive()) continue;
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
// Flick-trigger proxy only; a Pikmin held in a mouth is not a trigger (#886).
Piki* nearestPiki(const Vector3f& pos, float radius) {
    Piki* best = nullptr;
    float bestSq = radius * radius;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive() || p->isStickToMouth()) continue;
            const Vector3f q = p->getPosition();
            const float dx = q.x - pos.x, dz = q.z - pos.z;
            const float d = dx * dx + dz * dz;
            if (d < bestSq) { bestSq = d; best = p; }
        }
    }
    return best;
}
bool shouldFlick(BTeki* a) {
    return nearestPiki(a->getPosition(), FLICK_RADIUS) != nullptr;
}

void stop(BTeki* a) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
}

// Source SnakeCrow::Obj::onInit calls hardConstraintOn(): a Burrowing Snagret
// is never displaced by collision. The P1 Chappy host has no hard constraint,
// so creature-vs-creature separation let a captain walking into it shove the
// burrow hundreds of units (#920: the bot drove it ~1000 units off its slot,
// out of its own swarm's reach, and the corpse landed where it could not be
// grabbed). Pin a living SnakeCrow to its burrow; SnakeWhole walks, and the
// corpse must stay free so it can be carried.
void holdBurrow(BTeki* a, const Snake& s) {
    if (s.parms->sourceId != 34 || s.state == SNAKE_DEAD) return;
    const Vector3f pos = a->getPosition();
    a->mVelocity.x = a->mVelocity.z = 0.0f;
    a->mVolatileVelocity.x = a->mVolatileVelocity.z = 0.0f;
    if (pos.x != s.burrowPos.x || pos.z != s.burrowPos.z) a->resetPosition(Vector3f(s.burrowPos.x, pos.y, s.burrowPos.z));
}

// Source StateStay::init/cleanup (SnakeCrowState.cpp:110-127, SnakeWholeState.cpp:113-130):
// buried = EB_ModelHidden + setAtari(false) + life gauge hidden + appear1 held at
// frame 0; StateStay::cleanup restores them. The P1 Chappy host otherwise kept
// drawing the appear1 end pose, so the snagret stood fully out of the ground.
void applyBurrowVisibility(BTeki* a, Snake& s, unsigned generator) {
    const bool buried = s.state == SNAKE_STAY;
    if (buried == s.hidden) return;
    s.hidden = buried;
    constexpr int kOpts = TEKIOPT_Atari | TEKIOPT_ShadowVisible | TEKIOPT_LifeGaugeVisible;
    Teki* teki = static_cast<Teki*>(a);
    if (buried) teki->clearTekiOption(kOpts);
    else teki->setTekiOption(kOpts);
    std::printf("P2_SNAKEJOINT_BURIED generator=%u buried=%d model_hidden=%d atari=%d\n", generator,
                int(buried), int(buried), int(teki->isAtari()));
    std::fflush(stdout);
}

constexpr float APPEAR_OFFSET = 120.0f; // source appearNearByTarget ring radius

// Source Obj::appearNearByTarget (SnakeWhole.cpp:331-373, SnakeCrow.cpp:297): the
// snagret surfaces 120 units from the target it woke for, inside its territory of
// home, else on the home-to-target bearing +/- 90 degrees.
void appearNearByTarget(BTeki* a, Snake& s, const Vector3f& target) {
    float face = rand01(s) * TAU;
    Vector3f np(target.x - std::sin(face) * APPEAR_OFFSET, 0.0f, target.z - std::cos(face) * APPEAR_OFFSET);
    const float t2 = s.parms->territory * s.parms->territory;
    auto sqrXZ = [](const Vector3f& p, const Vector3f& q) {
        const float dx = p.x - q.x, dz = p.z - q.z;
        return dx * dx + dz * dz;
    };
    if (sqrXZ(s.home, np) > t2) {
        face = std::atan2(target.x - s.home.x, target.z - s.home.z) + (rand01(s) * PI - PI * 0.5f);
        np = Vector3f(target.x - std::sin(face) * APPEAR_OFFSET, 0.0f,
                      target.z - std::cos(face) * APPEAR_OFFSET);
    }
    np.y = mapMgr ? mapMgr->getMinY(np.x, np.z, true) : a->getPosition().y;
    a->resetPosition(np);
    s.burrowPos = np;
    s.heading = std::atan2(target.x - np.x, target.z - np.z);
    a->setDirection(s.heading);
}

// Source StateStay::exec target query: a live, unheld Pikmin (then a captain) inside
// the territory radius of home. Anything only inside 400 just keeps the boss BGM.
Creature* buriedWakeTarget(const Snake& s) {
    const float t2 = s.parms->territory * s.parms->territory;
    auto sqr3 = [&](const Vector3f& p) {
        const float dx = p.x - s.home.x, dy = p.y - s.home.y, dz = p.z - s.home.z;
        return dx * dx + dy * dy + dz * dz;
    };
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive() || p->isStickToMouth()) continue;
            if (sqr3(p->getPosition()) < t2) return p;
        }
    }
    if (naviMgr) {
        for (Navi* n : pc_p2_navis()) {
            if (n->isAlive() && sqr3(n->getPosition()) < t2) return n;
        }
    }
    return nullptr;
}

// Source Obj::turnToTarget: proportional turn clamped to the source max turn.
void turnAndMove(BTeki* a, Snake& s, const Vector3f& target, float speed) {
    const Vector3f pos = a->getPosition();
    const float desired = std::atan2(target.x - pos.x, target.z - pos.z);
    float delta = wrapPi(desired - s.heading) * s.parms->turnRate;
    if (delta > s.parms->maxTurn) delta = s.parms->maxTurn;
    if (delta < -s.parms->maxTurn) delta = -s.parms->maxTurn;
    s.heading = wrapPi(s.heading + delta);
    a->setDirection(s.heading);
    if (speed <= 0.0f) { stop(a); return; }
    const Vector3f drive(std::sin(s.heading) * speed, 0.0f,
                         std::cos(s.heading) * speed);
    a->inputDrive(drive);
    a->mVelocity.x = drive.x;
    a->mVelocity.z = drive.z;
}

void doFlick(BTeki* a, unsigned generator) {
    if (!pikiMgr) return;
    const Vector3f pos = a->getPosition();
    int hit = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive() || distXZ(p->getPosition(), pos) >= SHAKE_RANGE) continue;
        if (p2captorhost::heldBy(a, p)) continue; // a swallowed Pikmin is never flicked
        const float angle = std::atan2(p->getPosition().x - pos.x,
                                       p->getPosition().z - pos.z);
        p->stimulate(InteractFlick(a, SHAKE_KNOCKBACK, 0.0f, angle));
        ++hit;
    }
    if (hit > 0) {
        std::printf("P2_SNAKEJOINT_FLICK generator=%u pikmin=%d\n", generator, hit);
        std::fflush(stdout);
    }
}

void enter(Snake& s, State state, const char* clip) {
    s.state = state;
    s.stateTime = 0.0f;
    if (clip) s.clip = clip;
    s.biteFired = false;
    s.swallowFired = false;
    s.flickFired = false;
}
void setState(BTeki* a, Snake& s, State state, const char* clip) {
    const unsigned generator = a->mGenerator ? a->mGenerator->_70 : 0u;
    // Only Attack -> Eat carries the mouth; every other transition (and
    // death) frees it without harm.
    if (state != SNAKE_EAT) {
        const int freed = p2captorhost::release(a, s.held);
        if (freed > 0) {
            std::printf("P2_SNAKEJOINT_RELEASE generator=%u reason=%s pikmin=%d\n", generator,
                        state == SNAKE_DEAD ? "death" : "transition", freed);
            std::fflush(stdout);
        }
    }
    enter(s, state, clip);
    std::printf("P2_SNAKEJOINT_STATE generator=%u state=%s\n", generator, stateName(state));
    std::fflush(stdout);
    applyBurrowVisibility(a, s, generator);
}

const p2captor::Geometry& mouthGeometry(const Snake& s) {
    return *p2captor::geometryFor(unsigned(s.parms->sourceId));
}
// mAttackPositions[i].y: the floor under each setAttackPosition point.
void attackFloors(BTeki* a, const Snake& s, float* floorY) {
    const p2captor::SnakeZones& z = p2captor::snakeZonesFor(unsigned(s.parms->sourceId));
    const p2captor::Vec3 apos = p2captorhost::vec(a->getPosition());
    for (int i = 0; i < 5; ++i) {
        const p2captor::Vec3 q = p2captor::snakeAttackPosition(z, i, apos, s.heading);
        float y = mapMgr ? mapMgr->getMinY(q.x, q.z, true) : apos.y;
        if (!std::isfinite(y)) y = apos.y;
        floorY[i] = y;
    }
}
// Source getAttackPiki(animIdx) || getAttackNavi(animIdx): true when a
// Pikmin (manager order) or captain is inside the facing box(es); sets
// s.attackZone (mAttackAnimIdx) to that box.
bool findAttack(BTeki* a, Snake& s, int animIdx) {
    const p2captor::SnakeZones& z = p2captor::snakeZonesFor(unsigned(s.parms->sourceId));
    float floorY[5];
    attackFloors(a, s, floorY);
    const p2captor::Vec3 apos = p2captorhost::vec(a->getPosition());
    p2captorhost::Scene scene = p2captorhost::snapshot(a);
    int zone = -1;
    if (p2captor::snakeAttackPiki(z, animIdx, apos, s.heading, floorY, scene.prey.data(), (int)scene.prey.size(),
                                  &zone) >= 0) {
        s.attackZone = zone;
        return true;
    }
    for (Navi* n : pc_p2_navis()) {
        if (!n->isAlive()) continue;
        zone = p2captor::snakeZoneOf(z, animIdx, apos, s.heading, floorY, p2captorhost::vec(n->getPosition()));
        if (zone >= 0) {
            std::printf("P2_SNAKEJOINT_ATTACK_TRIGGER target=navi zone=%d\n", zone);
            s.attackZone = zone;
            return true;
        }
    }
    return false;
}
// Source StateAttack KEYEVENT_3: getAttackPiki(mAttackAnimIdx), then
// InteractSwallow into getSwallowSlot(). Returns true when a Pikmin is held.
bool biteZone(BTeki* a, Snake& s, unsigned generator, int frame) {
    const p2captor::Geometry& g = mouthGeometry(s);
    const p2captor::SnakeZones& z = p2captor::snakeZonesFor(unsigned(s.parms->sourceId));
    if (!s.mouthLogged) {
        s.mouthLogged = true;
        std::printf("P2_SNAKEJOINT_MOUTH generator=%u source_id=%d slots=%d rule=facing_boxes host_slots=%d\n",
                    generator, s.parms->sourceId, g.slots, p2captorhost::hostSlotCount(a));
        std::fflush(stdout);
    }
    float floorY[5];
    attackFloors(a, s, floorY);
    const p2captor::Vec3 apos = p2captorhost::vec(a->getPosition());
    p2captorhost::Scene scene = p2captorhost::snapshot(a);
    int zone = -1;
    const int n = p2captor::snakeAttackPiki(z, s.attackZone, apos, s.heading, floorY, scene.prey.data(),
                                            (int)scene.prey.size(), &zone);
    if (n < 0) return false;
    bool occupied[p2captor::MaxSlots] = {};
    p2captorhost::validate(a, s.held, g.slots, occupied);
    const int slot = p2captor::firstFreeSlot(occupied, g.slots);
    int refused = 0;
    if (slot < 0 || !p2captorhost::swallowInto(a, scene, n, slot, s.held, 0, &refused)) {
        std::printf("P2_SNAKEJOINT_EAT_REFUSED generator=%u reason=%s zone=%d\n", generator,
                    slot < 0 ? "slots_full" : (refused ? "no_host_slot" : "receiver"), zone);
        std::fflush(stdout);
        return false;
    }
    const p2captor::Vec3 l = p2captor::toLocal(apos, s.heading, scene.prey[n].pos);
    std::printf("P2_SNAKEJOINT_BITE generator=%u frame=%d pikmin=1 zone=%d slot=%d local_x=%.1f local_y=%.1f "
                "local_z=%.1f\n", generator, frame, zone, slot, l.x, l.y, l.z);
    std::fflush(stdout);
    return true;
}
int holding(BTeki* a, Snake& s) {
    bool occupied[p2captor::MaxSlots] = {};
    return p2captorhost::validate(a, s.held, mouthGeometry(s).slots, occupied);
}

void setPhase(Snake& s) {
    const float duration = clipDuration(s.parms->name, s.clip);
    const float len = duration > 0.0f ? duration : 1.0f;
    if (clipLoops(s.parms->name, s.clip)) {
        s.phase = s.stateTime / len;
        s.phase -= std::floor(s.phase);
    } else {
        s.phase = s.stateTime / len;
        if (s.phase > 1.0f) s.phase = 1.0f;
    }
}

// Post-attack/post-eat continuation shared by both species. SnakeWhole adds the
// Walk/Home return loop (SnakeWholeState.cpp:777-814); SnakeCrow returns to Wait.
void attackFollowUp(BTeki* a, Snake& s, const Vector3f& pos) {
    if (s.parms->sourceId == 70) {
        Creature* target = nearestTarget(pos, s.parms->sight);
        if (distXZ(pos, s.home) > s.parms->territory) {
            setState(a, s, SNAKE_HOME, "run1");
        } else if (target) {
            setState(a, s, SNAKE_WALK, "run1");
        } else {
            setState(a, s, SNAKE_WAIT, "wait1");
        }
    } else {
        setState(a, s, SNAKE_WAIT, "wait1");
    }
}
}

void pc_p2_snakejoint_reset() {
    for(const auto& entry:actors)if(entry.second.original){
        std::fprintf(stderr,"P2_ORIGINAL_SNAKECROW reset with live physical actor\n");
        std::abort();
    }
    originalBank = false;
    actors.clear();
    corpses.clear();
    clipBank.clear();
    ready = false;
}
void pc_p2_snakejoint_forget(BTeki* actor) {
    pc_p2_original_bulblax_snagret_forget(actor);
    // Slice-2 cleanup observability: the centralized forget seam is the P1
    // analogue of scene exit/death teardown; log the release so the fixture can
    // prove the dead snagret is removed without a stale reference.
    // Lane 06 single-use binding: drop the ordinary-delivery source so a
    // recycled actor address can never inherit the source. Idempotent.
    pc_randomizer_p2_forget_source(static_cast<PelletView*>(actor));
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it != actors.end()) {
        p2captorhost::release(actor, it->second.held); // teardown frees the mouth
        std::printf("P2_SNAKEJOINT_FORGET generator=%u source_id=%d\n",
                    identityToken(actor),
                    it->second.parms->sourceId);
        std::fflush(stdout);
    }
    actors.erase(static_cast<PelletView*>(actor));
    corpses.erase(static_cast<PelletView*>(actor));
}

void pc_p2_snakejoint_forget_piki(Piki* piki) {
    for (auto& entry : actors) entry.second.held.forget(piki);
}

bool pc_p2_snakejoint_suppress_ai(const BTeki* actor) {
    return ready && actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor))) != 0;
}

float pc_p2_snakejoint_param_f(const BTeki* actor, int idx, float fallback) {    if (!ready) return fallback;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return fallback;
    if (idx == TPF_Life) return it->second.parms->life;
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

bool pc_p2_snakejoint_model_hidden(const BTeki* actor) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    return it != actors.end() && it->second.hidden;
}

bool pc_p2_snakejoint_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

bool pc_p2_snakejoint_invulnerable(const BTeki* actor) {
    if (!ready || !actor)
        return pc_p2_snakejoint_attack_rejected(false, false);
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end())
        return pc_p2_snakejoint_attack_rejected(false, false);
    Snake& s = it->second;
    const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;
    const bool buriedStay = (s.state == SNAKE_STAY);
    if (!pc_p2_snakejoint_attack_rejected(true, buriedStay)) {
        // Emerged: EB_Invulnerable cleared (StateStay::cleanup); admit damage.
        if (!s.acceptLogged) {
            s.acceptLogged = true;
            std::printf("P2_SNAKEJOINT_DAMAGE_ACCEPTED generator=%u state=%s\n",
                        generator, stateName(s.state));
            std::fflush(stdout);
        }
        s.rejectLogged = false;
        return false;
    }
    // Buried (Stay): report the first rejection per buried period and swallow.
    if (!s.rejectLogged) {
        s.rejectLogged = true;
        std::printf("P2_SNAKEJOINT_DAMAGE_REJECTED generator=%u state=%s\n",
                    generator, stateName(s.state));
        std::fflush(stdout);
    }
    s.acceptLogged = false;
    return true;
}

namespace {
void loadBank() {
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
                    std::string species, name, frames, events, marker, value, status;
                    int poses = 0;
                    if (!(bank >> species >> name >> frames >> events >> marker >> poses)) break;
                    if (!(bank >> value)) break;
                    if (value != "status") status = value;
                    else if (!(bank >> status)) break;
                    Clip clip;
                    clip.name = name;
                    const double sourceFrames = std::atof(frames.c_str());
                    clip.duration = sourceFrames > 0.0 ? float(sourceFrames) / 30.0f : 1.0f;
                    clip.loop = (name == "wait1" || name == "run1");
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
                    clipBank[species][name] = clip;
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

}
}

void pc_p2_snakejoint_setup() {
    if(originalBank || pc_p2_original_bulblax_snagret_admitted())return;
    pc_p2_snakejoint_reset();
    if (!tekiMgr) return;

    loadBank();

    std::ifstream in("p2-snagret-actors.txt");
    if (!in && !pc_randomizer_p2_bridge()) return;
    std::string header;
    int count = 0;
    std::map<unsigned, const SpeciesParms*> wanted;
    if (in && (in >> header >> count) && header == "P2_SNAGRET_ACTORS_1" && count >= 1) {
        for (int i = 0; i < count; ++i) {
            unsigned long long generator = 0;
            std::string species;
            if (!(in >> generator >> species)) return;
            if (species == "SnakeCrow") wanted[unsigned(generator)] = &SNAKE_CROW;
            else if (species == "SnakeWhole") wanted[unsigned(generator)] = &SNAKE_WHOLE;
        }
    }
    if (pc_randomizer_p2_bridge()) {
        wanted.clear();
        for (unsigned id : pc_p2_campaign_ids(34)) wanted[id] = &SNAKE_CROW;
        for (unsigned id : pc_p2_campaign_ids(70)) wanted[id] = &SNAKE_WHOLE;
    }
    if (wanted.empty()) return;

    std::set<unsigned> found;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor || !actor->mGenerator) continue;
        const unsigned token = pc_p2_campaign_token(actor);
        auto match = wanted.find(token);
        if (match == wanted.end()) continue;
        if (actor->mTekiType != TEKI_Chappy) {
            std::printf("P2_SNAKEJOINT_ERROR native_type generator=%u\n", token);
            std::fflush(stdout);
            if (pc_p2_setup_skip(pc_randomizer_p2_bridge(), "SnakeJoint", "actor_type_mismatch")) return;
        }
        Snake& s = actors[static_cast<PelletView*>(actor)];
        s.parms = match->second;
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        s.moveTarget = s.home;
        s.rng = (token * 2654435761u) | 1u;
        actor->mHealth = s.parms->life;
        // Lane 06 ordinary delivery: bind the campaign source so the corpse
        // mints onion:p2:<id> via GoalItem::suckMe.
        pc_randomizer_p2_bind_source(static_cast<PelletView*>(actor),
                                     unsigned(s.parms->sourceId), token);
        std::printf("P2_SNAKEJOINT_DELIVERY_BIND generator=%u source_id=%d\n",
                    token, s.parms->sourceId);
        enter(s, SNAKE_STAY, "appear1");
        s.burrowPos = s.home;
        applyBurrowVisibility(actor, s, token);
        std::printf("P2_SNAKEJOINT_BIND generator=%u species=%s source_id=%d visual_only=0\n",
                    token, s.parms->name, s.parms->sourceId);
        // Slice-2 joint-fidelity measurement: the source rig drives six spinal
        // joints (bodyjnt3-bodyjnt8, SnakeJointMgr.cpp:47) feeding the head; the
        // P1 Chappy host drives a single flat translation-only body, so the drawn
        // pose comes from the per-species clip override, not the spinal matrices.
        std::printf("P2_SNAKEJOINT_JOINTS generator=%u species=%s source_joints=6 "
                    "host_joints=1 pose=clip_override\n",
                    token, s.parms->name);
        std::fflush(stdout);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=%s native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=animation_event\n",
                    s.parms->name, token, pos.x, pos.y, pos.z,
                    actor->mHealth, s.parms->life);
        std::printf("P2_SNAKEJOINT_STATE generator=%u state=stay\n", token);
        std::fflush(stdout);
        found.insert(token);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_SNAKEJOINT_ERROR missing_actor wanted=%zu found=%zu\n",
                    wanted.size(), found.size());
        std::fflush(stdout);
        if (pc_p2_setup_skip(pc_randomizer_p2_bridge(), "SnakeJoint", "actor_roster_incomplete")) return;
    }
    ready = true;
}

void pc_p2_snakejoint_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Snake& s = it->second;
    const SpeciesParms& parms = *s.parms;
    // The P1 TAI reaction path is suppressed for registered snagrets
    // (pc_p2_snakejoint_suppress_ai), so the source FSM applies pending
    // damage itself. Mirrors pc_p2_frog_update.
    if (actor->mStoredDamage > 0.0f) actor->makeDamaged();
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    holdBurrow(actor, s);
    const Vector3f pos = actor->getPosition();
    const unsigned generator = identityToken(actor);

    if (actor->mHealth <= 0.0f && s.state != SNAKE_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_SNAKEJOINT_DEAD generator=%u source_id=%d health=0\n",
                        generator, parms.sourceId);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        // Keep the generator for Pod receipt after the engine tears down
        // the host into a carriable pellet.
        if (generator && !s.original) corpses[static_cast<PelletView*>(actor)] = generator;
        setState(actor, s, SNAKE_DEAD, "dead");
    }

    const float previousStateTime=s.stateTime;
    s.stateTime += dt;
    switch (s.state) {
    case SNAKE_STAY: {
        stop(actor);
        // Source StateStay: after the proper fp12 underground time, wake when a
        // target is inside the territory (else the 400-unit near radius).
        if (s.stateTime > parms.undergroundTime) {
            Creature* target = buriedWakeTarget(s);
            if (target) {
                const Vector3f tp = target->getPosition();
                appearNearByTarget(actor, s, tp);
                std::printf("P2_SNAKEJOINT_WAKE generator=%u source_id=%d buried_seconds=%.2f "
                            "target_dist_home=%.1f territory=%.0f emerge_x=%.1f emerge_z=%.1f\n",
                            generator, parms.sourceId, s.stateTime, distXZ(tp, s.home),
                            parms.territory, s.burrowPos.x, s.burrowPos.z);
                std::fflush(stdout);
                if (rand01(s) < parms.fastAppearChance) {
                    setState(actor, s, SNAKE_APPEAR1, "appear1");
                } else {
                    setState(actor, s, SNAKE_APPEAR2, "appear2");
                }
            }
        }
        break;
    }
    case SNAKE_APPEAR1:
    case SNAKE_APPEAR2: {
        stop(actor);
        const char* clip = s.state == SNAKE_APPEAR1 ? "appear1" : "appear2";
        if (s.stateTime >= clipDuration(parms.name, clip)) {
            Creature* target = nearestTarget(pos, parms.sight);
            if (findAttack(actor, s, p2captor::SnakeAnyZone)) {
                setState(actor, s, SNAKE_ATTACK, "hit");
            } else if (parms.sourceId == 70 && target) {
                setState(actor, s, SNAKE_WALK, "run1");
            } else {
                setState(actor, s, SNAKE_WAIT, "wait1");
            }
        }
        break;
    }
    case SNAKE_WAIT: {
        stop(actor);
        Creature* target = nearestTarget(pos, parms.sight);
        if (target) turnAndMove(actor, s, target->getPosition(), 0.0f);
        if (shouldFlick(actor)) {
            setState(actor, s, SNAKE_DISAPPEAR, "dive");
            break;
        }
        if (findAttack(actor, s, p2captor::SnakeAnyZone)) {
            setState(actor, s, SNAKE_ATTACK, "hit");
            break;
        }
        if (parms.sourceId == 70) {
            if (distXZ(pos, s.home) > parms.territory) {
                setState(actor, s, SNAKE_HOME, "run1");
                break;
            }
            if (target) {
                setState(actor, s, SNAKE_WALK, "run1");
                break;
            }
        }
        // Source StateWait: waitTime (proper fp11) then disappear.
        if (s.stateTime > parms.waitTime) {
            setState(actor, s, SNAKE_DISAPPEAR, "dive");
        }
        break;
    }
    case SNAKE_WALK: {
        Creature* target = nearestTarget(pos, parms.sight);
        if (findAttack(actor, s, p2captor::SnakeAnyZone)) {
            setState(actor, s, SNAKE_ATTACK, "hit");
            break;
        }
        if (distXZ(pos, s.home) > parms.territory) {
            setState(actor, s, SNAKE_HOME, "run1");
            break;
        }
        if (target) turnAndMove(actor, s, target->getPosition(), LEAP_SPEED);
        else setState(actor, s, SNAKE_WAIT, "wait1");
        if (s.stateTime > WALK_TIMEOUT) setState(actor, s, SNAKE_HOME, "run1");
        break;
    }
    case SNAKE_HOME: {
        if (distXZ(pos, s.home) < parms.homeRadius) {
            setState(actor, s, SNAKE_WAIT, "wait1");
            break;
        }
        turnAndMove(actor, s, s.home, LEAP_SPEED);
        if (s.stateTime > WALK_TIMEOUT) setState(actor, s, SNAKE_WAIT, "wait1");
        break;
    }
    case SNAKE_ATTACK: {
        stop(actor);
        // Exactly-once capture inside the source bite sweep at the banked
        // KEYEVENT_3 bite frame of the normal `hit` stem.
        int bite = eventFrame(parms.name, s.clip, 3);
        if (bite < 0) bite = BITE_FALLBACK;
        const float frame = s.stateTime * 30.0f;
        if (!s.biteFired && frame >= float(bite)) {
            s.biteFired = true;
            biteZone(actor, s, generator, bite);
        }
        if (s.stateTime >= clipDuration(parms.name, s.clip)) {
            if (holding(actor, s) > 0) { // source isSwallowPikmin
                setState(actor, s, SNAKE_EAT, "waitact1");
            } else {
                attackFollowUp(actor, s, pos);
            }
        }
        break;
    }
    case SNAKE_EAT: {
        stop(actor);
        // Exactly-once swallow at the banked waitact1 KEYEVENT_2 event.
        int swallow = eventFrame(parms.name, "waitact1", 2);
        if (swallow < 0) swallow = SWALLOW_FALLBACK;
        if (!s.swallowFired && s.stateTime * 30.0f >= float(swallow)) {
            s.swallowFired = true;
            int white = 0;
            const int killed = p2captorhost::swallow(actor, s.held, mouthGeometry(s).slots,
                                                     mouthGeometry(s).poison, &white);
            std::printf("P2_SNAKEJOINT_EAT generator=%u pikmin=%d white=%d\n", generator, killed, white);
            std::fflush(stdout);
        }
        if (s.stateTime >= clipDuration(parms.name, "waitact1")) {
            attackFollowUp(actor, s, pos);
        }
        break;
    }
    case SNAKE_STRUGGLE:
        stop(actor);
        if (s.stateTime > STRUGGLE_TIME) {
            if (findAttack(actor, s, p2captor::SnakeAnyZone)) {
                setState(actor, s, SNAKE_ATTACK, "hit");
            } else {
                setState(actor, s, SNAKE_WAIT, "wait1");
            }
        }
        break;
    case SNAKE_DISAPPEAR: {
        stop(actor);
        int flick = eventFrame(parms.name, "dive", 2);
        if (flick < 0) flick = FLICK_FALLBACK;
        if (!s.flickFired && s.stateTime * 30.0f >= float(flick)) {
            s.flickFired = true;
            doFlick(actor, generator);
        }
        if (s.stateTime >= clipDuration(parms.name, "dive")) {
            setState(actor, s, SNAKE_STAY, "appear1");
        }
        break;
    }
    case SNAKE_DEAD:
        stop(actor);
        // Retail StateDead KEYEVENT_3 (frame131) throws source items before
        // END kills. Never route original drops through an AP/P1 personality.
        if(s.deathItems.advance(s.original,previousStateTime,s.stateTime)){
            if(!pc_p2_original_spawn_items(actor)){
                std::fputs("P2_ORIGINAL_SNAKECROW death event lost original registry\n",stderr);
                std::abort();
            }
            std::printf("P2_ORIGINAL_SNAKECROW_DROP generator=%u frame=131 before_end=1\n",generator);
            std::fflush(stdout);
        }
        // dieSoon() only runs inside the P1 doAI block, which is suppressed
        // for registered snagrets; pcEscapeNow() finalizes the corpse outside
        // doAI, fired exactly once when the dead clip completes. Mirrors frog.
        if (!s.escaped && s.stateTime >= clipDuration(parms.name, "dead")) {
            s.escaped = true;
            actor->pcEscapeNow();
        }
        break;
    default:
        break;
    }
    setPhase(s);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        std::printf("P2_SNAKEJOINT_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f "
                    "stickers=%d mouth=%d health=%.1f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z,
                    p2captorhost::pikiStickerCount(actor), p2captorhost::mouthStickerCount(actor),
                    actor->mHealth);
        std::fflush(stdout);
    }
}

bool pc_p2_snakejoint_receipt(PelletView* view, unsigned& generator) {
    if (!view) return false;
    auto i = actors.find(view);
    if (i != actors.end()) {
        if(i->second.original)return false;
        // Live lookup needs the bound token, not the retail _70.
        BTeki* t = static_cast<BTeki*>(view);
        generator = t ? identityToken(t) : 0u;
        if (!generator) return false;
        return true;
    }
    auto c = corpses.find(view);
    if (c == corpses.end()) return false;
    generator = c->second;
    return true;
}

int pc_p2_snakejoint_bound_count() {
    return int(actors.size() + corpses.size());
}

// Original bank admission requires complete authored clips and event timing.
// It never reads an AP roster and never manufactures fallback timings.
bool pc_p2_snakejoint_original_resources(std::string& error) {
 if(!actors.empty()||!corpses.empty()){error="original Snagret resources with live family actors";return false;}
 if(ready&&!originalBank){error="original Snagret cannot reuse AP resource owner";return false;}
 if(!originalBank){
  std::ifstream bank("p2-snagret-bank.txt");
  if(!p2original::bulblax_snagret::validateSnagretBank(bank,error))return false;
  clipBank.clear();loadBank();
 }
 const char* required[]={"dead","appear1","appear2","wait1","hit","waitact1","dive","waitact2","type5","hit_near","hit_far","hit_r","hit_l"};
 for(const char* name:required){auto* clip=findClip("SnakeCrow",name);
  if(!clip||clip->duration<=0||clip->events.empty()){error=std::string("original SnakeCrow authored clip unavailable: ")+name;return false;}}
 for(const auto& requiredEvent:std::vector<std::pair<const char*,std::pair<int,int>>>{{"hit",{34,3}},{"waitact1",{42,2}},{"dive",{12,2}}}) {
  const auto* clip=findClip("SnakeCrow",requiredEvent.first);
  bool found=false;for(const auto& event:clip->events)if(event==requiredEvent.second)found=true;
  if(!found){error="original SnakeCrow required retail animation event unavailable";return false;}
 }
 originalBank=true;ready=true;error.clear();return true;
}
bool pc_p2_snakejoint_bind_original(BTeki* actor,unsigned token,std::string& error) {
 unsigned source=0,bound=0;
 if(!actor||!originalBank||actor->mTekiType!=TEKI_Chappy
  ||!p2original::originalActors().query(static_cast<Creature*>(actor),source,bound)
  ||source!=34||bound!=token||!token||actors.count(static_cast<PelletView*>(actor))) {error="original SnakeCrow physical/registry identity mismatch";return false;}
 Snake state;state.original=true;state.parms=&SNAKE_CROW;
 state.home=actor->getPosition();state.heading=actor->getDirection();state.moveTarget=state.home;
 state.rng=(token*2654435761u)|1u;state.burrowPos=state.home;
 enter(state,SNAKE_STAY,"appear1");actor->mHealth=actor->mMaxHealth=SNAKE_CROW.life;
 auto inserted=actors.emplace(static_cast<PelletView*>(actor),std::move(state));
 applyBurrowVisibility(actor,inserted.first->second,token);
 error.clear();return true;
}
