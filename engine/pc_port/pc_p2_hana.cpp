// Family-owned ground-invertebrate source behavior for the batch-2 Chappy
// placement vehicle: Creeping Chrysanthemum (Hana, EnemyID 84). Implements the
// inherited ChappyBase FSM slice used by Hana: buried Sleep -> wake/emergence
// (type1) -> Walk/chase (move1) -> Attack (attack1) -> Eat -> Walk, plus Flick,
// GoHome and Dead. Source revision 632af93787b9c95b63f0c13be32b161375ce3a96;
// retail parms from experimental/pikmin2_ground_inverts_assets.py (GPVE01 rev 0).
//
// Port adaptations (recorded, not retail-faithful):
//   * The P2 three-slot mouth swallow (kamu1..3) is resolved on the P1 host as an
//     explicit capture of the nearest Pikmin inside the source attack sweep
//     radius at the attack1 bite event (frame 18), then a single InteractKill at
//     the source swallow event (frame 71). Timing is delivered by the
//     authoritative sampled clock (#431), so the effects fire exactly once
//     across skipped frames, pause, interruption and actor-address reuse.
//     A successfully consumed White Pikmin applies the fp02 poison (2500) at
//     that swallow frame.
//   * The buried gate is implemented as a read-only policy gate
//     (pc_p2_hana_buried / pc_p2_hana_rejects_attack) because the P1 Chappy host
//     has no EB_Invulnerable/EB_ModelHidden event flags and its TEKIOPT_Atari /
//     TEKIOPT_Invincible writes are gated on pc_render_is_authoritative(). While
//     buried (source Sleep) the gate reports non-targetable/no-atari and the
//     host attack path swallows incoming damage; the gate also toggles the host
//     options when authoritative. See pc_p2_hana_residual_policy.h.
//   * attackNavi captain damage fires at the source attack1 KEYEVENT_2 (retail
//     bite frame) with radius fp22=80, hit half-angle fp23=15 deg (header
//     default) and damage fp24=10.
//   * View angle is a full hemisphere; the attack sweep angle is the fp13=90
//     view-angle half-angle and turn rate/flick radius are port adaptations.
//   * The source isWakeup() uses the private radius (fp11=70); the wake test is
//     widened to the source sight radius (fp12=500) so staged fixture squads wake
//     the ambusher, per lane audit.
// No other lane's module is modified; every hook is a no-op for unregistered actors.
#include "pc_p2_hana.h"
#include "pc_p2_hana_events.h"
#include "pc_p2_hana_residual_policy.h"
#include "pc_p2_hana_sleep_policy.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_p2_white.h"
#include "gl/pc_gfx.h"
#include "pc_p2_sfx.h"
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
    HANA_INVALID = -1,
    HANA_DEAD = 0,
    HANA_SLEEP = 1,
    HANA_EMERGE = 2,
    HANA_WALK = 3,
    HANA_GOHOME = 4,
    HANA_ATTACK = 5,
    HANA_EAT = 6,
    HANA_FLICK = 7,
};

const char* stateName(State s) {
    switch (s) {
    case HANA_DEAD: return "dead";
    case HANA_SLEEP: return "sleep";
    case HANA_EMERGE: return "emerge";
    case HANA_WALK: return "walk";
    case HANA_GOHOME: return "gohome";
    case HANA_ATTACK: return "attack";
    case HANA_EAT: return "eat";
    case HANA_FLICK: return "flick";
    default: return "null";
    }
}

// Source enemyparm.txt values (ground_inverts manifest, Hana general/proper).
constexpr float LIFE = 2500.0f;
constexpr float MOVE_SPEED = 100.0f;
constexpr float SIGHT = 500.0f;
constexpr float TERRITORY = 300.0f;
constexpr float HOME_RADIUS = 15.0f;
constexpr float ATTACK_RANGE = 80.0f;       // fp22 attack hit radius
constexpr float ATTACK_ANGLE = 0.785398f;   // fp13 view angle 90 deg -> half-angle
constexpr float TURN_RATE = 2.5f;           // port adaptation
constexpr float FLICK_RADIUS = 25.0f;       // port adaptation
constexpr float SHAKE_RANGE = 100.0f;       // port adaptation
constexpr float SHAKE_KNOCKBACK = 120.0f;   // port adaptation

// Source attackNavi / poison values (Hana disc, GPVE01 rev 0).
constexpr float POISON_DAMAGE = p2hanapolicy::WhitePoisonDamage; // proper fp02
constexpr float CAPTAIN_DAMAGE = 10.0f;     // general fp24 attack power
constexpr float ATTACK_HIT_ANGLE = 0.261799f; // general fp23 default 15 deg half-angle

struct Clip {
    std::string name;
    float duration = 1.0f;
    int frames = 0;            // source frame count (bank row)
    float loopBegin = -1.0f;   // LOOP_START event frame (key 0), -1 when absent
    float loopEnd = -1.0f;     // LOOP_END event frame (key 1), -1 when absent
    bool loop = false;
    p2sampled::Clip sampled;
};

struct Hana {
    State state = HANA_SLEEP;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    Piki* captured = nullptr;
    bool killed = false;
    bool hidden = true;
    p2hanaevents::Receiver events;
    std::string clip = "type1";
    float phase = 0.0f;
    bool deadLogged = false;
    bool escaped = false;  // host death funnel ran (pcEscapeNow): corpse pellet exists
    int sfxState = -1;     // last state a P1-approximation SFX was requested for
    bool buriedLogged = false;
    float logTimer = 0.0f;
    State prevState = HANA_WALK; // state before Flick (source mStateMachine->mPreviousID)
    p2hanapolicy::FlickReturn flickReturn;
    // Buried idle / emergence timeline over the type1 clip (pc_p2_hana_sleep_policy.h).
    p2hanasleep::Cursor sleep;
    bool campaign = false;     // wake radius: source private radius in a seed, sight radius in fixtures
    bool burstDone = false;    // emergence ground burst (type1 KEYEVENT_4) fired for this wake
    bool shotBuried = false, shotEmerge = false, shotCorpse = false;  // probe screenshots (PIKMIN_P2_PROXY_SHOT)
};

std::map<PelletView*, Hana> actors;
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

Creature* nearestTarget(const Vector3f& pos, float radius = SIGHT) {
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
Piki* nearestPiki(const Vector3f& pos, float radius) {
    Piki* best = nullptr;
    float bestSq = radius * radius;
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
// Source EnemyFunc::isStartFlick (enemyAction.cpp:1209) keys on Pikmin stuck to
// the body (mStuckPikminCount vs the ShakeOffSticking tiers and mFlickTimer vs
// ShakeOffBlowA-D; the port keeps only the stuck-count >= 3 test, a port
// simplification that omits the tiered mFlickTimer gate: it does not follow the
// source tiers), not on a nearby swarm:
// proximity flicks made Hana flick back-to-back and never settle (wave 3
// mechanics probe: drifted 1200 units from home while flicking). Same rule as
// pc_p2_chappy.cpp FLICK_STUCK_MIN.
constexpr int FLICK_STUCK_MIN = 3;
bool shouldFlick(BTeki* a) {
    int stuck = 0;
    for (Creature* c = a->mStickListHead; c; c = c->mNextSticker) {
        if (c->isPiki() && c->isAlive()) ++stuck;
    }
    return stuck >= FLICK_STUCK_MIN;
}
void doFlick(BTeki* a, Hana& s) {
    if (!pikiMgr) return;
    const Vector3f pos = a->getPosition();
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p && p->isAlive() && distXZ(p->getPosition(), pos) < SHAKE_RANGE) {
            p->stimulate(InteractFlick(a, SHAKE_KNOCKBACK, 0.0f, a->getDirection()));
        }
    }
    (void)s;
}
// Source EnemyFunc::attackNavi (enemyAction.cpp:1179): damage every Navi inside
// the attack hit radius (fp22) and hit half-angle (fp23) at the attack event
// frame. Fired once per attack1 bite (KEYEVENT_2); `frame` is the source event
// frame delivered by the sampled clock, not the accumulated wall time.
void doAttackNavi(BTeki* a, const Hana& s, unsigned generator, int frame) {
    if (!naviMgr) return;
    const Vector3f pos = a->getPosition();
    int attacked = 0;
    for (int i = 0; i < naviMgr->getSize(); ++i) {
        Navi* n = naviMgr->getNavi(i);
        if (!n || !n->isAlive()) continue;
        const Vector3f np = n->getPosition();
        if (distXZ(np, pos) >= ATTACK_RANGE) continue;
        const float angle = std::fabs(wrapPi(std::atan2(np.x - pos.x, np.z - pos.z) - s.heading));
        if (angle >= ATTACK_HIT_ANGLE) continue;
        n->stimulate(InteractAttack(a, nullptr, CAPTAIN_DAMAGE, false));
        ++attacked;
    }
    std::printf("P2_HANA_ATTACK_NAVI generator=%u frame=%d navi=%d damage=%.1f\n",
                generator, frame, attacked, CAPTAIN_DAMAGE);
    std::fflush(stdout);
}
// Read-only policy gate for the buried window. Registered Hana actors in the
// buried Sleep state are non-targetable/no-atari and damage is swallowed. The
// host TEKIOPT_Atari/TEKIOPT_Invincible writes are authoritative-only (see
// pc_p2_hana_residual_policy.h); the query hooks used by the attack path are not.
void applyUndergroundGate(BTeki* a, Hana& s, unsigned generator) {
    p2hanapolicy::UndergroundInputs in;
    in.registered = true;
    in.buried = (s.state == HANA_SLEEP);
    const bool buried = p2hanapolicy::noAtari(p2hanapolicy::undergroundGate(in));
    if (buried == s.buriedLogged) return;
    s.buriedLogged = buried;
    if (buried) {
        a->clearTekiOption(TEKIOPT_Atari);
        a->setTekiOption(TEKIOPT_Invincible);
        std::printf("P2_HANA_UNDERGROUND generator=%u event=enter no_atari=1 invulnerable=1\n",
                    generator);
    } else {
        a->setTekiOption(TEKIOPT_Atari);
        a->clearTekiOption(TEKIOPT_Invincible);
        std::printf("P2_HANA_UNDERGROUND generator=%u event=exit no_atari=0 invulnerable=0\n",
                    generator);
    }
    std::fflush(stdout);
}
void enter(Hana& s, State state, const char* clip) {
    // Source mPreviousID: remember the state Flick is entered from (Walk or
    // GoHome) before it is overwritten; read back at the Flick end.
    if (state == HANA_FLICK) {
        s.prevState = s.state;
        s.flickReturn.noteEnter(static_cast<int>(s.state));
    }
    s.state = state;
    s.stateTime = 0.0f;
    if (state == HANA_ATTACK) {
        s.captured = nullptr;
        s.killed = false;
    }
    if (clip) s.clip = clip;
    if (state == HANA_SLEEP) {
        // Buried Sleep: type1 from StateSleep::init (mDoSkipSleepStart = frame 70 inside the
        // LOOP_START..LOOP_END bump). A GoHome re-entry calls startDive() after this.
        auto t1 = clips.find("type1");
        if (t1 != clips.end() && t1->second.frames > 1)
            s.sleep.configure(float(t1->second.frames), t1->second.loopBegin, t1->second.loopEnd);
        s.sleep.startSpawn();
        s.burstDone = false;
    }
    // Start the sampled clock for the entered clip, or cancel it when the clip
    // has no authored gameplay events. A start() bumps the clock generation,
    // discarding the previous clip's outstanding events.
    auto it = clips.find(s.clip);
    if (it != clips.end()) {
        s.events.start(it->second.sampled, it->second.name);
    } else {
        s.events.cancel();
    }
}
void walkTo(BTeki* a, Hana& s, const Vector3f& target, float dt) {
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
void stop(BTeki* a) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
}

void setPhase(Hana& s) {
    // Buried idle and emergence walk the type1 timeline (loop region underground, then the
    // 60 fps finish-motion rise); pose 0 is the standing body and must not be held.
    if (s.state == HANA_SLEEP || s.state == HANA_EMERGE) { s.phase = s.sleep.phase01(); return; }
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

void pc_p2_hana_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}
void pc_p2_hana_forget(BTeki* actor) { actors.erase(static_cast<PelletView*>(actor)); }

bool pc_p2_hana_buried(const BTeki* actor) {
    if (!ready || !actor) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    p2hanapolicy::UndergroundInputs in;
    in.registered = true;
    in.buried = (it->second.state == HANA_SLEEP);
    return p2hanapolicy::noAtari(p2hanapolicy::undergroundGate(in));
}

bool pc_p2_hana_rejects_attack(Teki* teki) {
    if (!ready || !teki) return false;
    auto it = actors.find(static_cast<PelletView*>(static_cast<BTeki*>(teki)));
    if (it == actors.end()) return false;
    p2hanapolicy::UndergroundInputs in;
    in.registered = true;
    in.buried = (it->second.state == HANA_SLEEP);
    const bool blocked = p2hanapolicy::blocksDamage(p2hanapolicy::undergroundGate(in));
    if (blocked) {
        std::printf("P2_HANA_UNDERGROUND_BLOCK generator=%u source_id=84 buried=1\n",
                    teki->mGenerator ? pc_p2_campaign_token(teki) : 0u);
        std::fflush(stdout);
    }
    return blocked;
}

float pc_p2_hana_param_f(const BTeki* actor, int idx, float fallback) {
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

bool pc_p2_hana_suppress_ai(const BTeki* actor) {
    return ready && actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor))) != 0;
}

bool pc_p2_hana_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

void pc_p2_hana_setup() {
    pc_p2_hana_reset();
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
                    if (species == "Hana") {
                        Clip clip;
                        clip.name = name;
                        clip.duration = frames > 0 ? float(frames) / 30.0f : 1.0f;
                        clip.frames = frames > 0 ? int(frames) : 0;
                        clip.loop = (name == "move1" || name == "wait2");
                        p2hanaevents::Row row;
                        row.name = name;
                        row.sourceFrames = frames > 0 ? int(frames) : 0;
                        row.poseCount = poses;
                        row.loop = clip.loop;
                        if (events != "-") {
                            size_t start = 0;
                            while (start < events.size()) {
                                const size_t comma = events.find(',', start);
                                const std::string pair = events.substr(start, comma - start);
                                const size_t colon = pair.find(':');
                                if (colon != std::string::npos) {
                                    const int eventFrame = std::atoi(pair.substr(0, colon).c_str());
                                    const std::string key = pair.substr(colon + 1);
                                    row.events.push_back(p2sampled::Event{eventFrame, key});
                                    if (name == "type1" && key == "0") clip.loopBegin = float(eventFrame);
                                    if (name == "type1" && key == "1") clip.loopEnd = float(eventFrame);
                                }
                                if (comma == std::string::npos) break;
                                start = comma + 1;
                            }
                        }
                        clip.sampled = p2hanaevents::makeClip(row);
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
        if (species == "Hana") wanted[unsigned(generator)] = species;
    }
    if (pc_randomizer_p2_bridge()) {
        wanted.clear();
        for (unsigned id : pc_p2_campaign_ids(84)) wanted[id] = "Hana";
    }
    if (wanted.empty()) return;

    std::set<unsigned> found;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor || !actor->mGenerator) continue;
        auto match = wanted.find(pc_p2_campaign_token(actor));
        if (match == wanted.end()) continue;
        if (actor->mTekiType != TEKI_Chappy) {
            std::printf("P2_HANA_ERROR native_type generator=%u\n", pc_p2_campaign_token(actor));
            std::fflush(stdout);
            if (pc_p2_setup_skip(pc_randomizer_p2_bridge(), "Hana", "actor_type_mismatch")) return;
            std::abort();
        }
        Hana& s = actors[static_cast<PelletView*>(actor)];
        s = Hana();  // reject stale clock/capture state on actor-address reuse
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        s.campaign = pc_randomizer_p2_bridge();
        actor->mHealth = LIFE;
        // Bite/swallow/flick timing comes from the authored attack1/flick events
        // via the sampled clock; no per-state frame fields to extract.
        enter(s, HANA_SLEEP, "type1");
        // Ordinary-delivery bridge (lane 06 contract, mirrors Catfish 26):
        // bind source 84 to this live actor so GoalItem::suckMe can grant
        // onion:p2:84 exactly once. Single-use: consumed on delivery and
        // cleared on forget/recycle.
        pc_randomizer_p2_bind_source(static_cast<PelletView*>(actor), 84,
                                     pc_p2_campaign_token(actor));
        std::printf("P2_HANA_DELIVERY_BIND generator=%u source_id=84\n",
                    pc_p2_campaign_token(actor));
        std::printf("P2_HANA_BIND generator=%u source_id=84 visual_only=0\n",
                    pc_p2_campaign_token(actor));
        std::printf("P2_HANA_STATE generator=%u state=sleep\n", pc_p2_campaign_token(actor));
        std::printf("P2_HANA_SLEEP generator=%u entry=spawn frame=%.1f loop=%.0f..%.0f wake_radius=%.0f buried_pose=%d\n",
                    pc_p2_campaign_token(actor), double(s.sleep.frame()), double(s.sleep.loopBegin()),
                    double(s.sleep.loopEnd()), double(p2hanasleep::wakeRadius(s.campaign)),
                    s.sleep.buriedPose() ? 1 : 0);
        std::fflush(stdout);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=Hana native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=animation_event\n",
                    pc_p2_campaign_token(actor), pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        found.insert(pc_p2_campaign_token(actor));
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_HANA_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::fflush(stdout);
        if (pc_p2_setup_skip(pc_randomizer_p2_bridge(), "Hana", "actor_roster_incomplete")) return;
        std::abort();
    }
    ready = true;
}

void pc_p2_hana_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Hana& s = it->second;
    float dt = gsys->getFrameTime();
    if (dt <= 0.0f) return;
    // Clamp a pathological single-frame hitch (e.g. a debugger pause) so one
    // tick cannot cause a giant simulation step, but still advance the sampled
    // clock by the clamped delta instead of dropping the whole update: dropping
    // it would discard crossed animation events and break exactly-once timing.
    if (dt > 0.5f) dt = 0.5f;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = actor->mGenerator ? pc_p2_campaign_token(actor) : 0u;

    // Host-AI suppression drain (rev6-misc5 Finding 1): the P1 TAI reaction
    // path (TaiDamagingAction) normally applies stored damage through
    // makeDamaged(), but BTeki::doAI is suppressed for registered actors, so
    // the source FSM applies pending damage itself. Mirrors
    // pc_p2_frog_suppress_ai (pc_p2_frog.cpp).
    if (actor->mStoredDamage > 0.0f) {
        actor->makeDamaged();
        if (actor->mHealth > 0.0f) {
            std::printf("P2_HANA_DAMAGE generator=%u source_id=84 health=%.1f\n", generator, actor->mHealth);
            std::fflush(stdout);
            pc_p2_sfx(84, generator, p2sfx::Event::Damage, actor);
        }
    }

    if (actor->mHealth <= 0.0f && s.state != HANA_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_HANA_DEAD generator=%u source_id=84 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        enter(s, HANA_DEAD, "dead");
    }

    s.stateTime += dt;
    // P1-approximation SFX (pc_p2_sfx_policy.h). Output-only: no sim state.
    if (s.sfxState != int(s.state)) {
        s.sfxState = int(s.state);
        if (s.state == HANA_ATTACK) pc_p2_sfx(84, generator, p2sfx::Event::Attack, actor);
        else if (s.state == HANA_FLICK) pc_p2_sfx(84, generator, p2sfx::Event::Flick, actor);
        else if (s.state == HANA_DEAD) pc_p2_sfx(84, generator, p2sfx::Event::Dead, actor);
    }
    if (s.state == HANA_WALK || s.state == HANA_GOHOME) pc_p2_sfx_stride(84, generator, actor, 45.0f);
    switch (s.state) {
    case HANA_SLEEP: {
        stop(actor);
        s.hidden = true;
        s.clip = "type1"; // buried bump: loop region of the type1 clip
        s.sleep.advance(dt);
        // Source isWakeup(): Navi or Pikmin inside the private radius (fp11). Fixture squads
        // keep the sight radius (see pc_p2_hana_sleep_policy.h).
        const float wakeR = p2hanasleep::wakeRadius(s.campaign);
        // Probe screenshot (env-gated, no effect otherwise): a squad close enough to be on screen
        // while the plant is still buried.
        if (!s.shotBuried && s.sleep.buriedPose() && nearestTarget(pos, 130.0f)) {
            s.shotBuried = true;
            pc_gfx_proxy_shot_notify_after("x|Hana_buried", 2);
        }
        Creature* waker = nearestTarget(pos, wakeR);
        if (waker) {
            std::printf("P2_HANA_WAKE generator=%u frame=%.1f radius=%.0f distance=%.1f buried_pose=%d\n", generator,
                        double(s.sleep.frame()), double(wakeR), double(distXZ(waker->getPosition(), pos)),
                        s.sleep.buriedPose() ? 1 : 0);
            std::printf("P2_HANA_STATE generator=%u state=emerge\n", generator);
            if (!s.shotEmerge) {
                s.shotEmerge = true;
                pc_gfx_proxy_shot_notify_after("x|Hana_emerging", 25);
            }
            const p2hanasleep::Cursor keep = s.sleep;
            enter(s, HANA_EMERGE, "type1");
            s.sleep = keep;  // the wake continues the sleep clip from the current frame
            s.sleep.wake();
        }
        break;
    }
    case HANA_EMERGE: {
        stop(actor);
        s.hidden = false;
        const float before = s.sleep.frame();
        const bool finished = s.sleep.advance(dt);
        // type1 KEYEVENT_4 (createSmokeEffect): the ground burst flicks nearby Pikmin.
        if (!s.burstDone && p2hanasleep::Cursor::crossed(before, s.sleep.frame(), 120.0f)) {
            s.burstDone = true;
            std::printf("P2_HANA_EMERGE_BURST generator=%u frame=120\n", generator);
            doFlick(actor, s);
        }
        if (finished) {
            std::printf("P2_HANA_STATE generator=%u state=walk\n", generator);
            enter(s, HANA_WALK, "move1");
        }
        break;
    }
    case HANA_WALK:
    case HANA_GOHOME: {
        s.hidden = false;
        Creature* target = nearestTarget(pos);
        if (s.state == HANA_WALK && target) {
            const float angle = std::fabs(wrapPi(std::atan2(target->getPosition().x - pos.x,
                                                           target->getPosition().z - pos.z) - s.heading));
            if (distXZ(target->getPosition(), pos) < ATTACK_RANGE && angle < ATTACK_ANGLE) {
                std::printf("P2_HANA_STATE generator=%u state=attack\n", generator);
                enter(s, HANA_ATTACK, "attack1");
                break;
            }
            walkTo(actor, s, target->getPosition(), dt);
        } else if (s.state == HANA_GOHOME || !target) {
            walkTo(actor, s, s.home, dt);
        }
        if (distXZ(pos, s.home) > TERRITORY && s.state != HANA_GOHOME) {
            std::printf("P2_HANA_STATE generator=%u state=gohome\n", generator);
            enter(s, HANA_GOHOME, "move1");
            break;
        }
        if (s.state == HANA_GOHOME && distXZ(pos, s.home) < HOME_RADIUS) {
            std::printf("P2_HANA_STATE generator=%u state=sleep\n", generator);
            enter(s, HANA_SLEEP, "type1");
            s.sleep.startDive();  // GoHome re-entry: no skip-start, the body sinks first
            break;
        }
        if (shouldFlick(actor)) {
            std::printf("P2_HANA_STATE generator=%u state=flick\n", generator);
            enter(s, HANA_FLICK, "flick");
        }
        break;
    }
    case HANA_ATTACK: {
        stop(actor);
        // Source StateAttack::exec KEYEVENT_2/KEYEVENT_3 (bite capture +
        // attackNavi, then swallow + White poison) are delivered by the sampled
        // clock exactly once per crossing, in source frame order.
        for (const p2hanaevents::Dispatched& event : s.events.advance(dt)) {
            if (event.action == p2hanaevents::Action::Bite && !s.captured) {
                doAttackNavi(actor, s, generator, event.frame);
                Piki* piki = nearestPiki(pos, ATTACK_RANGE);
                if (piki) {
                    s.captured = piki;
                    std::printf("P2_HANA_BITE generator=%u frame=%d pikmin=1\n", generator, event.frame);
                    std::fflush(stdout);
                }
            } else if (event.action == p2hanaevents::Action::Swallow && s.captured && !s.killed) {
                s.killed = true;
                Piki* piki = s.captured;
                s.captured = nullptr;
                const bool isWhite = pc_p2_is_white(piki);
                const bool killedNow = piki->isAlive() && piki->stimulate(InteractKill(actor, 0));
                p2hanapolicy::PoisonInputs poison;
                poison.killSucceeded = killedNow;
                poison.isWhite = isWhite;
                if (p2hanapolicy::appliesWhitePoison(poison)) {
                    actor->mHealth -= p2hanapolicy::poisonDamage(poison);
                    std::printf("P2_HANA_POISON generator=%u pikmin=1 damage=%.1f health=%.1f\n",
                                generator, p2hanapolicy::poisonDamage(poison), actor->mHealth);
                    std::fflush(stdout);
                }
                std::printf("P2_HANA_EAT generator=%u pikmin=1\n", generator);
                std::fflush(stdout);
            }
        }
        if (s.stateTime >= clipDuration("attack1")) {
            if (s.killed) {
                std::printf("P2_HANA_STATE generator=%u state=eat\n", generator);
                enter(s, HANA_EAT, "waitact1");
            } else {
                std::printf("P2_HANA_STATE generator=%u state=walk\n", generator);
                enter(s, HANA_WALK, "move1");
            }
        }
        break;
    }
    case HANA_EAT:
        stop(actor);
        if (s.stateTime >= clipDuration("waitact1")) {
            std::printf("P2_HANA_STATE generator=%u state=walk\n", generator);
            enter(s, HANA_WALK, "move1");
        }
        break;
    case HANA_FLICK: {
        stop(actor);
        for (const p2hanaevents::Dispatched& event : s.events.advance(dt)) {
            if (event.action == p2hanaevents::Action::Flick) {
                doFlick(actor, s);
                std::printf("P2_HANA_FLICK generator=%u frame=%d\n", generator, event.frame);
                std::fflush(stdout);
            }
        }
        if (s.stateTime >= clipDuration("flick")) {
            // Source StateFlick::exec KEYEVENT_END (chappyState.cpp:2206-2207):
            // transit(enemy, mPreviousID), i.e. back to the state Flick was
            // entered from (Walk or GoHome here); the territory check then runs
            // as in any Walk frame.
            const State back = static_cast<State>(s.flickReturn.returnState(HANA_WALK, HANA_GOHOME));
            std::printf("P2_HANA_STATE generator=%u state=%s\n", generator, stateName(back));
            enter(s, back, "move1");
        }
        break;
    }
    case HANA_DEAD:
        stop(actor);
        // The host doAI that normally calls die()+dieSoon() is suppressed, so
        // die() alone (mDeadState=1, no corpse pellet) left nothing to carry
        // (wave 3 mechanics probe: killed=1 carried=0). pcEscapeNow() is the
        // full funnel (Armor/Groink/Breadbug pattern).
        if (!s.escaped && s.stateTime >= clipDuration("dead")) {
            s.escaped = true;
            if (!s.shotCorpse) {
                s.shotCorpse = true;
                pc_gfx_proxy_shot_notify_after("x|Hana_corpse", 20);
            }
            actor->pcEscapeNow();
        }
        break;
    default:
        break;
    }
    applyUndergroundGate(actor, s, generator);
    setPhase(s);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        std::printf("P2_HANA_POS generator=%u state=%s clip=%s phase=%.2f frame=%.1f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase,
                    (s.state == HANA_SLEEP || s.state == HANA_EMERGE) ? double(s.sleep.frame()) : double(s.phase * 30.0f * clipDuration(s.clip)),
                    pos.x, pos.z);
        std::fflush(stdout);
    }
}
