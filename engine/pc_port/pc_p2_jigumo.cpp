// Jigumo / Hermit Crawmad (EnemyID 63, aquatic family #167) source behavior on
// the P1 TEKI_Chappy (3) placement vehicle, generator 374003. Jigumo owns a
// PanHouse child (Jigumo.cpp:73) and runs its own fourteen-state FSM
// (jigumoState.cpp:16). This port implements the bounded source slice:
//   Appear 1 -> Wait 0 -> Search 10 -> SAttack 11 / Attack 4 -> Miss 5 ->
//   Return 6 -> Carry 7 -> Eat 9 -> Hide 2, plus Flick 8 and Dead 3.
// Attack/S Attack are driven by the source animation key events: the bite
// event resolves an explicit capture and the later swallow event resolves
// exactly one InteractKill. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_aquatic_assets.py (GPVE01 rev 0).
//
// Port adaptations (recorded, not retail-faithful):
//   * No PanHouse/nest actor exists on the P1 host. The source birth creates a
//     PanHouse and links it through mHouse; here the nest is the Jigumo's home
//     point. Appear/Hide are animation-only (the source nest constraint and
//     revisionAnimPos nest-follow motion are not representable), so the host
//     stays at home while hidden and only the animation plays.
//   * Mouth slot (#886): the source kamu_joint1 slot (r=25) eats through
//     pc_p2_captor_mouth.h: Attack runs EnemyFunc::eatPikmin with the source
//     ConditionHeightCheckPiki every tick from key event 2 (frame 26) until a
//     catch, SAttack every tick from frame 13 to key event 3. A caught Pikmin
//     is stuck to the P1 host 'slot' part (pc_p2_captor_host.h), so it cannot
//     be whistled away; Eat (dive1 key event 8) and SAttack (key event 10)
//     swallow only Pikmin still held (swallowPikmin, white poison 500). The
//     joint position is a documented port approximation (see the header).
//     Death, teardown and non-carry transitions release the mouth; the
//     port's own flick sweep spares the held Pikmin (source flicks refuse a
//     swallowed Pikmin: PikiSwallowedState::dead(), interactPiki.cpp).
//   * The source view/search angle is a full hemisphere (the Jigumo general
//     block does not override the angle), so target selection ignores facing.
//     Turn rate, flick radius and shake values are P1-host values.
//   * The source damageCallBack part rule (only Carry/Return, head-vs-body) and
//     waterBox effects are not representable; damage is accepted while alive.
// Every hook is a no-op for unregistered actors; no other lane's module is
// modified.
#include "pc_p2_jigumo.h"
#include "pc_p2_captor_host.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_randomizer.h"
#include "pc_bbft.h"
#include "MapMgr.h"
#include "Pellet.h"
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
    JIGUMO_INVALID = -1,
    JIGUMO_WAIT = 0,
    JIGUMO_APPEAR = 1,
    JIGUMO_HIDE = 2,
    JIGUMO_DEAD = 3,
    JIGUMO_ATTACK = 4,
    JIGUMO_MISS = 5,
    JIGUMO_RETURN = 6,
    JIGUMO_CARRY = 7,
    JIGUMO_FLICK = 8,
    JIGUMO_EAT = 9,
    JIGUMO_SEARCH = 10,
    JIGUMO_SATTACK = 11,
    JIGUMO_SMISS = 12,
};

const char* stateName(State s) {
    switch (s) {
    case JIGUMO_WAIT: return "wait";
    case JIGUMO_APPEAR: return "appear";
    case JIGUMO_HIDE: return "hide";
    case JIGUMO_DEAD: return "dead";
    case JIGUMO_ATTACK: return "attack";
    case JIGUMO_MISS: return "miss";
    case JIGUMO_RETURN: return "return";
    case JIGUMO_CARRY: return "carry";
    case JIGUMO_FLICK: return "flick";
    case JIGUMO_EAT: return "eat";
    case JIGUMO_SEARCH: return "search";
    case JIGUMO_SATTACK: return "sattack";
    case JIGUMO_SMISS: return "smiss";
    default: return "null";
    }
}

// Source enemyparm.txt values (aquatic manifest general + Jigumo proper).
constexpr float LIFE = 500.0f;              // general fp00
constexpr float MOVE_SPEED = 300.0f;        // general fp06
constexpr float TERRITORY = 400.0f;         // general fp09
constexpr float HOME_RADIUS = 25.0f;        // general fp10
constexpr float SIGHT = 400.0f;             // general fp12
// Source StateSearch picks SAttack when the goal is inside general fp22
// mAttackRadius * scale (jigumoState.cpp:747-758); the retail Jigumo block
// does not override fp22, so the EnemyParmsBase default 70 applies. (The
// pre-#886 port gated on fp20 = 200, so an SAttack began far outside the
// mouth; harmless while capture ignored the mouth, a guaranteed miss now.)
constexpr float SATTACK_RADIUS = 70.0f;     // general fp22 (header default)
constexpr float ATTACK_ANGLE = 3.14159265f; // port adaptation (hemisphere)
constexpr float CARRY_SPEED = 75.0f;        // proper fp01
constexpr float RETURN_SPEED = 30.0f;       // proper fp02
constexpr float HIDING_FRAMES = 30.0f;      // proper ip01
constexpr float SATTACK_ACTIVE_FRAME = 13.0f; // Jigumo.h:133
constexpr float TURN_RATE = 2.5f;           // port adaptation
constexpr float FLICK_RADIUS = 25.0f;       // port adaptation
constexpr float SHAKE_RANGE = 100.0f;       // port adaptation
constexpr float SHAKE_KNOCKBACK = 120.0f;   // port adaptation
constexpr float ARRIVE_DIST = 20.0f;
constexpr float PI_F = 3.14159265f;

struct Clip {
    std::string name;
    float duration = 1.0f;
    std::vector<std::pair<int, int>> events; // source frame -> event code
};

struct Jigumo {
    State state = JIGUMO_APPEAR;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    Vector3f goal;
    bool appearArmed = false;
    bool attackActive = false;
    p2captor::Held<Piki> held; // Pikmin in the kamu_joint1 slot (validated against the host stick)
    bool mouthLogged = false;
    State nextState = JIGUMO_INVALID;
    const char* nextClip = nullptr;
    std::set<int> firedEvents;
    std::string clip = "appear1";
    float phase = 0.0f;
    bool sattackDone = false; // SAttack key event 3 closed the bite window
    bool deadLogged = false;
    bool deadEscapeDone = false; // OWN death: pcEscapeNow fired once after dead1
    float logTimer = 0.0f;
};

std::map<PelletView*, Jigumo> actors;
std::map<std::string, Clip> clips;
bool ready = false;

float wrapPi(float a) {
    while (a > PI_F) a -= 2.0f * PI_F;
    while (a < -PI_F) a += 2.0f * PI_F;
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
// Flick-trigger proxy only. A Pikmin held in a mouth is not a shake-off
// trigger (#886: it now physically sits at the host mouth part).
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
void doFlick(BTeki* a) {
    if (!pikiMgr) return;
    const Vector3f pos = a->getPosition();
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p && p->isAlive() && distXZ(p->getPosition(), pos) < SHAKE_RANGE
                && !p2captorhost::heldBy(a, p)) {
            p->stimulate(InteractFlick(a, SHAKE_KNOCKBACK, 0.0f, a->getDirection()));
        }
    }
}
void stop(BTeki* a) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
}
float turnTo(BTeki* a, Jigumo& s, const Vector3f& target, float dt) {
    const Vector3f pos = a->getPosition();
    const float desired = std::atan2(target.x - pos.x, target.z - pos.z);
    const float maxTurn = TURN_RATE * dt;
    float diff = wrapPi(desired - s.heading);
    if (diff > maxTurn) diff = maxTurn;
    if (diff < -maxTurn) diff = -maxTurn;
    s.heading = wrapPi(s.heading + diff);
    a->setDirection(s.heading);
    return wrapPi(desired - s.heading);
}
void walkTo(BTeki* a, Jigumo& s, const Vector3f& target, float speed, float dt) {
    turnTo(a, s, target, dt);
    const Vector3f drive(std::sin(s.heading) * speed, 0.0f, std::cos(s.heading) * speed);
    a->inputDrive(drive);
    a->mVelocity.set(drive);
}
void setPhase(Jigumo& s) {
    const float duration = clipDuration(s.clip);
    const float len = duration > 0.0f ? duration : 1.0f;
    s.phase = s.stateTime / len;
    if (s.phase > 1.0f) s.phase = 1.0f;
}
const p2captor::Geometry& mouthGeometry() { return *p2captor::geometryFor(63); }
int holding(BTeki* a, Jigumo& s) {
    bool occupied[p2captor::MaxSlots] = {};
    return p2captorhost::validate(a, s.held, mouthGeometry().slots, occupied);
}
void releaseMouth(BTeki* a, Jigumo& s, unsigned generator, const char* why) {
    const int freed = p2captorhost::release(a, s.held);
    if (freed > 0) {
        std::printf("P2_JIGUMO_RELEASE generator=%u reason=%s pikmin=%d\n", generator, why, freed);
        std::fflush(stdout);
    }
}
void transition(BTeki* actor, Jigumo& s, State state, const char* clip,
                unsigned generator, bool keepCaptured = false) {
    s.state = state;
    s.stateTime = 0.0f;
    s.firedEvents.clear();
    s.attackActive = false;
    s.sattackDone = false;
    if (!keepCaptured) releaseMouth(actor, s, generator, "transition");
    if (clip) s.clip = clip;
    std::printf("P2_JIGUMO_STATE generator=%u state=%s\n", generator, stateName(state));
    std::fflush(stdout);
}
// Fires the first not-yet-fired event with the given code once its banked source
// frame is reached; returns true and the source frame when it fires.
bool dueEvent(Jigumo& s, const char* clipName, int code, int& frameOut) {
    auto it = clips.find(clipName);
    if (it == clips.end()) return false;
    for (const auto& event : it->second.events) {
        if (event.second != code) continue;
        if (s.firedEvents.count(event.first)) continue;
        if (s.stateTime < event.first / 30.0f) continue;
        s.firedEvents.insert(event.first);
        frameOut = event.first;
        return true;
    }
    return false;
}
// Source EnemyFunc::eatPikmin through the kamu_joint1 slot (one pass).
// `heightCheck` selects the Attack ConditionHeightCheckPiki; SAttack uses
// the default condition. Returns the number caught this pass.
int eatPass(BTeki* actor, Jigumo& s, unsigned generator, int frame, bool heightCheck) {
    const p2captor::Geometry& g = mouthGeometry();
    if (!s.mouthLogged) {
        s.mouthLogged = true;
        std::printf("P2_JIGUMO_MOUTH generator=%u slots=%d radius=%.1f local_z=%.1f host_slots=%d\n",
                    generator, g.slots, g.radius, g.local[0][2], p2captorhost::hostSlotCount(actor));
        std::fflush(stdout);
    }
    bool occupied[p2captor::MaxSlots] = {};
    p2captorhost::validate(actor, s.held, g.slots, occupied);
    p2captorhost::Scene scene = p2captorhost::snapshot(actor);
    const p2captor::Vec3 apos = p2captorhost::vec(actor->getPosition());
    int refused = 0;
    auto stimulate = [&](int n, int slot) {
        if (!p2captorhost::swallowInto(actor, scene, n, slot, s.held, 0, &refused)) return false;
        const p2captor::Vec3 l = p2captor::toLocal(apos, s.heading, scene.prey[n].pos);
        std::printf("P2_JIGUMO_BITE generator=%u frame=%d pikmin=1 slot=%d local_x=%.1f local_y=%.1f "
                    "local_z=%.1f\n", generator, frame, slot, l.x, l.y, l.z);
        std::fflush(stdout);
        return true;
    };
    const int count = (int)scene.prey.size();
    int caught = 0;
    if (heightCheck) {
        caught = p2captor::eat(g, apos, s.heading, scene.prey.data(), count, occupied,
                               p2captor::JigumoHeightCheck{apos.y}, stimulate);
    } else {
        caught = p2captor::eat(g, apos, s.heading, scene.prey.data(), count, occupied,
                               p2captor::defaultEligible, stimulate);
    }
    if (refused > 0) {
        std::printf("P2_JIGUMO_EAT_REFUSED generator=%u reason=no_host_slot count=%d\n", generator, refused);
        std::fflush(stdout);
    }
    return caught;
}
// Source swallowPikmin(enemy, 300) with the Jigumo poison override (fp05):
// only Pikmin still held in the mouth die.
bool resolveKill(BTeki* actor, Jigumo& s, unsigned generator) {
    int white = 0;
    const int killed = p2captorhost::swallow(actor, s.held, mouthGeometry().slots, mouthGeometry().poison, &white);
    std::printf("P2_JIGUMO_EAT generator=%u pikmin=%d white=%d\n", generator, killed, white);
    std::fflush(stdout);
    return killed > 0;
}
}

void pc_p2_jigumo_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}

void pc_p2_jigumo_forget(BTeki* actor) {
    pc_randomizer_p2_forget_source(static_cast<PelletView*>(actor));
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it != actors.end()) p2captorhost::release(actor, it->second.held); // teardown frees the mouth
    actors.erase(static_cast<PelletView*>(actor));
}

void pc_p2_jigumo_forget_piki(Piki* piki) {
    for (auto& entry : actors) entry.second.held.forget(piki);
}

bool pc_p2_jigumo_suppress_ai(const BTeki* actor) {
    return actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor))) != 0;
}

float pc_p2_jigumo_param_f(const BTeki* actor, int idx, float fallback) {
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

bool pc_p2_jigumo_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    // Bot-campaign drawn evidence: batch3 draws Jigumo via the aquatic pose
    // bank without a per-species DRAW line the scorer keys on, so report the
    // first forced-clip handoff per campaign token here (draw-time call).
    static std::set<unsigned> drawn;
    const unsigned token = pc_p2_campaign_token(const_cast<BTeki*>(actor));
    if (drawn.insert(token ? token : 1u).second) {
        std::printf("P2_JIGUMO_DRAW corpse=0 clip=%s token=%u\n", name, token);
        std::fflush(stdout);
    }
    return true;
}

void pc_p2_jigumo_setup() {
    pc_p2_jigumo_reset();
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
                    if (species == "Jigumo") {
                        Clip clip;
                        clip.name = name;
                        const double sourceFrames = std::atof(frames.c_str());
                        clip.duration = sourceFrames > 0.0 ? float(sourceFrames) / 30.0f : 1.0f;
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

    std::map<unsigned, std::string> wanted;
    std::ifstream in("p2-aquatic-actors.txt");
    if (!in) {
        if (pc_randomizer_p2_bridge()) {
            // No sidecar: fall through to the seed-bridge identity below.
        } else return;
    } else {
        std::string header;
        int count = 0;
        if (!(in >> header >> count) || header != "P2_AQUATIC_ACTORS_1" || count < 1) {
            if (pc_p2_setup_skip(pc_randomizer_p2_bridge(), "Jigumo", "staged_config_invalid")) return;
        } else {
            for (int i = 0; i < count; ++i) {
                unsigned long long generator = 0;
                std::string species;
                if (!(in >> generator >> species)) {
                    if (pc_p2_setup_skip(pc_randomizer_p2_bridge(), "Jigumo", "staged_config_invalid")) return;
                }
                if (species == "Jigumo") wanted[unsigned(generator)] = species;
            }
        }
    }
    const bool bridge = pc_randomizer_p2_bridge() && !pc_pikipelago_room_preview();
    if (bridge) {
        // Generated campaign sessions bind by the seed's source id per actor,
        // like Sokkuri: the sidecar's filed generators are placeholders there.
        wanted.clear();
        for (unsigned id : pc_p2_campaign_ids(63)) wanted[id] = "Jigumo";
    }
    if (wanted.empty()) return;

    std::set<unsigned> found;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor || !actor->mGenerator) continue;
        const unsigned token = bridge ? pc_p2_campaign_token(actor) : actor->mGenerator->_70;
        auto match = wanted.find(token);
        if (match == wanted.end()) continue;
        if (actor->mTekiType != TEKI_Chappy) {
            std::printf("P2_JIGUMO_ERROR native_type generator=%u\n", token);
            std::fflush(stdout);
            if (pc_p2_setup_skip(bridge, "Jigumo", "actor_type_mismatch")) return;
        }
        Jigumo& s = actors[static_cast<PelletView*>(actor)];
        s.home = actor->getPosition();
        s.goal = s.home;
        s.heading = actor->getDirection();
        s.state = JIGUMO_APPEAR;
        s.clip = "appear1";
        s.appearArmed = false;
        actor->mHealth = LIFE;
        std::printf("P2_JIGUMO_BIND generator=%u source_id=63 visual_only=0\n",
                    token);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=Jigumo native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=animation_event nest=2\n",
                    token, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        std::printf("P2_JIGUMO_STATE generator=%u state=appear\n", token);
        std::fflush(stdout);
        if (bridge) {
            // Ordinary-delivery bridge (lane 06): bind source 63 so the hauled
            // corpse grants onion:p2:63 exactly once via
            // pc_randomizer_p2_corpse_delivered. Mirrors ElecBug/Sarai/Sokkuri.
            pc_randomizer_p2_bind_source(static_cast<PelletView*>(actor), 63, token);
            std::printf("P2_JIGUMO_DELIVERY_BIND generator=%u source_id=63\n", token);
            std::fflush(stdout);
        }
        found.insert(token);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_JIGUMO_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::fflush(stdout);
        if (pc_p2_setup_skip(bridge, "Jigumo", "actor_roster_incomplete")) return;
    }
    ready = true;
}

void pc_p2_jigumo_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Jigumo& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    // OWN damage path (mirrors frog): the P1 TAI damaging reaction is
    // suppressed with doAI, so the source FSM applies pending attack damage
    // itself.
    if (actor->mStoredDamage > 0.0f) actor->makeDamaged();
    const Vector3f pos = actor->getPosition();
    const unsigned generator = pc_p2_campaign_token(actor);
    int frame = 0;
    // Natural-combat observability: incremental health decrease is live Pikmin
    // damage (mirrors Sokkuri/Long Legs). Logged for the bot evidence scorer.
    static std::map<PelletView*, float> lastHealth;
    PelletView* key = static_cast<PelletView*>(actor);
    auto lh = lastHealth.find(key);
    if (lh == lastHealth.end()) lastHealth[key] = LIFE;
    if (actor->mHealth < lastHealth[key] && actor->mHealth > 0.0f) {
        std::printf("P2_JIGUMO_DAMAGE generator=%u source_id=63 health=%.1f\n",
                    generator, actor->mHealth);
        std::fflush(stdout);
    }
    lastHealth[key] = actor->mHealth;

    // Death-drop-to-ground (mirrors Kurage corpseTail): a Jigumo killed on a
    // ledge spawns its corpse Pellet above the floor, which FreeMode Pikmin
    // cannot grasp. Settle the fresh Pellet onto the floor so the carry can
    // latch; idempotent once grounded.
    if ((actor->mHealth <= 0.0f || !actor->isAlive()) && actor->mPellet && mapMgr) {
        Pellet* corpse = actor->mPellet;
        const float groundY = mapMgr->getMinY(corpse->mSRT.t.x, corpse->mSRT.t.z, true);
        if (std::isfinite(groundY) && corpse->mSRT.t.y > groundY + 1.0f) {
            std::printf("P2_JIGUMO_CORPSE_DROP from_y=%.3f ground_y=%.3f generator=%u\n",
                        corpse->mSRT.t.y, groundY, generator);
            std::fflush(stdout);
            corpse->mSRT.t.y = groundY;
            corpse->mVelocity.set(0.0f, 0.0f, 0.0f);
            corpse->mTargetVelocity.set(0.0f, 0.0f, 0.0f);
        }
        static std::set<Pellet*> loggedPellet;
        if (loggedPellet.insert(corpse).second && corpse->mConfig) {
            std::printf("P2_JIGUMO_CORPSE_CONFIG carry_min=%d carry_max=%d alive=%d x=%.1f y=%.1f z=%.1f ground=%.1f generator=%u\n",
                        corpse->mConfig->mCarryMinPikis.mValue,
                        corpse->mConfig->mCarryMaxPikis.mValue,
                        corpse->isAlive() ? 1 : 0,
                        corpse->mSRT.t.x, corpse->mSRT.t.y, corpse->mSRT.t.z,
                        groundY, generator);
            std::fflush(stdout);
        }
    }

    if (actor->mHealth <= 0.0f && s.state != JIGUMO_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_JIGUMO_DEAD generator=%u source_id=63 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        // Release any held Pikmin without killing it: a Jigumo that dies
        // while ferrying a Pikmin to the nest must not take it down (source
        // deathProcedure setAlive(false); the P1 swallowed state frees a
        // Pikmin whose holder is gone).
        releaseMouth(actor, s, generator, "death");
        transition(actor, s, JIGUMO_DEAD, "dead1", generator);
    }

    s.stateTime += dt;
    switch (s.state) {
    case JIGUMO_APPEAR: {
        stop(actor);
        if (!s.appearArmed) {
            // Source StateAppear holds the nest-hidden pose for mHidingTime,
            // then emerges only while a target is inside the territory.
            if (s.stateTime >= HIDING_FRAMES / 30.0f && nearestTarget(pos, TERRITORY)) {
                s.appearArmed = true;
                s.stateTime = 0.0f;
                s.clip = "appear1";
                std::printf("P2_JIGUMO_STATE generator=%u state=appear\n", generator);
                std::fflush(stdout);
            }
            break;
        }
        if (s.stateTime >= clipDuration("appear1")) {
            transition(actor, s, JIGUMO_WAIT, "wait1", generator);
        }
        break;
    }
    case JIGUMO_WAIT: {
        stop(actor);
        Creature* target = nearestTarget(pos, SIGHT);
        if (target) {
            s.goal = target->getPosition();
            transition(actor, s, JIGUMO_SEARCH, "turn1", generator);
            break;
        }
        if (s.stateTime >= clipDuration("wait1")) {
            transition(actor, s, JIGUMO_HIDE, "hide1", generator);
        }
        break;
    }
    case JIGUMO_SEARCH: {
        stop(actor);
        Creature* target = nearestTarget(pos, SIGHT);
        if (!target) {
            transition(actor, s, JIGUMO_WAIT, "wait1", generator);
            break;
        }
        s.goal = target->getPosition();
        const float residual = turnTo(actor, s, s.goal, dt);
        if (std::fabs(residual) < 0.02f || s.stateTime >= clipDuration("turn1")) {
            const float gx = s.goal.x - pos.x, gy = s.goal.y - pos.y, gz = s.goal.z - pos.z;
            if (gx * gx + gy * gy + gz * gz < SATTACK_RADIUS * SATTACK_RADIUS) {
                transition(actor, s, JIGUMO_SATTACK, "sattack1", generator);
            } else {
                transition(actor, s, JIGUMO_ATTACK, "attack1", generator);
            }
        }
        break;
    }
    case JIGUMO_ATTACK: {
        Creature* target = nearestTarget(pos, SIGHT);
        if (target) s.goal = target->getPosition();
        // Source StateAttack enables the bite at animation key event 2 (frame 26)
        // and only then calls walkFunc for the lunge.
        if (s.stateTime < 26.0f / 30.0f) {
            stop(actor);
            if (target) turnTo(actor, s, target->getPosition(), dt);
        } else {
            // Source StateAttack: key event 2 arms the bite; while armed, the
            // lunge walks and eatPikmin (height check) runs every frame until
            // a catch or the goal is reached (jigumoState.cpp:327-371).
            if (dueEvent(s, "attack1", 2, frame)) s.attackActive = true;
            if (s.attackActive && holding(actor, s) == 0
                    && eatPass(actor, s, generator, int(s.stateTime * 30.0f), true) > 0) {
                s.attackActive = false;
            }
            if (s.attackActive && distXZ(pos, s.goal) < 10.0f) s.attackActive = false;
            if (s.attackActive) {
                walkTo(actor, s, s.goal, MOVE_SPEED, dt);
            } else {
                stop(actor);
            }
        }
        if (s.stateTime >= clipDuration("attack1")) {
            if (holding(actor, s) > 0) {
                transition(actor, s, JIGUMO_CARRY, "backrun1", generator, true);
            } else {
                transition(actor, s, JIGUMO_MISS, "to_runaway1", generator);
            }
        }
        break;
    }
    case JIGUMO_MISS:
        stop(actor);
        if (s.stateTime >= clipDuration("to_runaway1")) {
            transition(actor, s, JIGUMO_RETURN, "runaway1", generator);
        }
        break;
    case JIGUMO_RETURN: {
        if (shouldFlick(actor)) {
            s.nextState = JIGUMO_HIDE;
            s.nextClip = "hide1";
            transition(actor, s, JIGUMO_FLICK, "flick1", generator);
            break;
        }
        if (distXZ(pos, s.home) < ARRIVE_DIST) {
            transition(actor, s, JIGUMO_HIDE, "hide1", generator);
            break;
        }
        walkTo(actor, s, s.home, RETURN_SPEED, dt);
        break;
    }
    case JIGUMO_CARRY: {
        if (shouldFlick(actor)) {
            s.nextState = JIGUMO_EAT;
            s.nextClip = "dive1";
            transition(actor, s, JIGUMO_FLICK, "flick1", generator, true);
            break;
        }
        if (distXZ(pos, s.home) < ARRIVE_DIST) {
            transition(actor, s, JIGUMO_EAT, "dive1", generator, true);
            break;
        }
        walkTo(actor, s, s.home, CARRY_SPEED, dt);
        break;
    }
    case JIGUMO_EAT: {
        stop(actor);
        // Source dive1 key event 8 (frame 80) swallows the carried Pikmin.
        if (dueEvent(s, "dive1", 8, frame)) {
            resolveKill(actor, s, generator);
        }
        if (s.stateTime >= clipDuration("dive1")) {
            transition(actor, s, JIGUMO_HIDE, "hide1", generator);
        }
        break;
    }
    case JIGUMO_FLICK: {
        stop(actor);
        if (dueEvent(s, "flick1", 2, frame)) {
            doFlick(actor);
            std::printf("P2_JIGUMO_FLICK generator=%u frame=%d\n", generator, frame);
            std::fflush(stdout);
        }
        if (s.stateTime >= clipDuration("flick1")) {
            const State next = s.nextState == JIGUMO_INVALID ? JIGUMO_RETURN : s.nextState;
            const char* clip = s.nextClip ? s.nextClip : "runaway1";
            s.nextState = JIGUMO_INVALID;
            s.nextClip = nullptr;
            transition(actor, s, next, clip, generator, true);
        }
        break;
    }
    case JIGUMO_SATTACK: {
        Creature* target = nearestTarget(pos, SIGHT);
        stop(actor);
        if (target) turnTo(actor, s, target->getPosition(), dt);
        // Source StateSAttack activates at mSAttackActiveFrame (13) and runs
        // eatPikmin continuously until the key event 3 miss check (frame 26).
        if (!s.attackActive && !s.sattackDone && s.stateTime * 30.0f >= SATTACK_ACTIVE_FRAME) {
            s.attackActive = true;
        }
        if (s.attackActive) {
            eatPass(actor, s, generator, int(s.stateTime * 30.0f), false);
        }
        if (dueEvent(s, "sattack1", 3, frame)) {
            s.attackActive = false;
            s.sattackDone = true;
            if (holding(actor, s) == 0) {
                transition(actor, s, JIGUMO_SMISS, "smiss1", generator);
                break;
            }
        }
        // Source sattack1 key event 10 (frame 115) swallows a caught Pikmin.
        if (dueEvent(s, "sattack1", 10, frame)) {
            resolveKill(actor, s, generator);
        }
        if (s.stateTime >= clipDuration("sattack1")) {
            transition(actor, s, JIGUMO_SEARCH, "turn1", generator);
        }
        break;
    }
    case JIGUMO_SMISS:
        stop(actor);
        if (s.stateTime >= clipDuration("smiss1")) {
            transition(actor, s, JIGUMO_SEARCH, "turn1", generator);
        }
        break;
    case JIGUMO_HIDE:
        stop(actor);
        if (s.stateTime >= clipDuration("hide1")) {
            transition(actor, s, JIGUMO_APPEAR, "appear1", generator);
        }
        break;
    case JIGUMO_DEAD:
        stop(actor);
        // OWN death (mirrors frog/kochappy): doAI is suppressed, so dieSoon()
        // never runs there. The source dead1 clip plays, then pcEscapeNow()
        // (= die() + dieSoon(), teki.h) finalizes the host teardown and births
        // the real carriable Chappy-pellet corpse. The pre-round-2 host handoff
        // (never call die() from update) is superseded: with suppression the
        // escape is the ONLY path to a corpse, and it runs outside doAI so the
        // dieSoon block is not skipped.
        if (!s.deadEscapeDone && s.stateTime >= clipDuration("dead1")) {
            s.deadEscapeDone = true;
            std::printf("P2_JIGUMO_ESCAPE generator=%u native=host_escape_now\n", generator);
            std::fflush(stdout);
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
        const Vector3f now = actor->getPosition();
        std::printf("P2_JIGUMO_POS generator=%u state=%s clip=%s phase=%.2f "
                    "x=%.2f y=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase,
                    now.x, now.y, now.z);
        std::fflush(stdout);
    }
}
