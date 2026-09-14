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
//     radius during the attack1 bite window, then a single InteractKill at the
//     source swallow event frame. Exactly-once per bite. A successfully consumed
//     White Pikmin applies the fp02 poison (2500) to Hana at that swallow frame.
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
#include "pc_p2_hana_residual_policy.h"
#include "pc_p2_white.h"
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

// Audit fallbacks for the attack1 bite/swallow events (Hana bank 18:2, 71:3).
constexpr int FALLBACK_BITE_FRAME = 18;
constexpr int FALLBACK_SWALLOW_FRAME = 71;
constexpr int FALLBACK_FLICK_FRAME = 50;

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events;
};

struct Hana {
    State state = HANA_SLEEP;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    Piki* captured = nullptr;
    bool killed = false;
    bool hidden = true;
    int biteFrame = FALLBACK_BITE_FRAME;
    int swallowFrame = FALLBACK_SWALLOW_FRAME;
    int flickFrame = FALLBACK_FLICK_FRAME;
    std::set<int> firedEvents;
    std::string clip = "type1";
    float phase = 0.0f;
    bool deadLogged = false;
    bool buriedLogged = false;
    float logTimer = 0.0f;
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
bool shouldFlick(BTeki* a) {
    const Vector3f pos = a->getPosition();
    return nearestPiki(pos, FLICK_RADIUS) != nullptr;
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
// frame. Fired once per attack1 bite (KEYEVENT_2).
void doAttackNavi(BTeki* a, const Hana& s, unsigned generator) {
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
    std::printf("P2_HANA_ATTACK_NAVI generator=%u frame=%.1f navi=%d damage=%.1f\n",
                generator, s.stateTime * 30.0f, attacked, CAPTAIN_DAMAGE);
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
    s.state = state;
    s.stateTime = 0.0f;
    s.firedEvents.clear();
    if (state == HANA_ATTACK) {
        s.captured = nullptr;
        s.killed = false;
    }
    if (clip) s.clip = clip;
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
float motionFrame(const Hana& s) { return s.stateTime * 30.0f; }

void setPhase(Hana& s) {
    if (s.state == HANA_SLEEP) { s.phase = 0.0f; return; }
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
                    teki->mGenerator ? teki->mGenerator->_70 : 0u);
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
    if (wanted.empty()) return;

    std::set<unsigned> found;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor || !actor->mGenerator) continue;
        auto match = wanted.find(actor->mGenerator->_70);
        if (match == wanted.end()) continue;
        if (actor->mTekiType != TEKI_Chappy) {
            std::printf("P2_HANA_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::abort();
        }
        Hana& s = actors[static_cast<PelletView*>(actor)];
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        actor->mHealth = LIFE;
        // Bite/swallow/flick frames come from the validated disc bank, not hardcoded.
        auto attack = clips.find("attack1");
        if (attack != clips.end()) {
            for (const auto& event : attack->second.events) {
                if (event.second == 2 && s.biteFrame == FALLBACK_BITE_FRAME) s.biteFrame = event.first;
                if (event.second == 3 && s.swallowFrame == FALLBACK_SWALLOW_FRAME) s.swallowFrame = event.first;
            }
        }
        auto flick = clips.find("flick");
        if (flick != clips.end() && !flick->second.events.empty()) {
            s.flickFrame = flick->second.events.front().first;
        }
        enter(s, HANA_SLEEP, "type1");
        std::printf("P2_HANA_BIND generator=%u source_id=84 visual_only=0\n",
                    actor->mGenerator->_70);
        std::printf("P2_HANA_STATE generator=%u state=sleep\n", actor->mGenerator->_70);
        std::fflush(stdout);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=Hana native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=animation_event\n",
                    actor->mGenerator->_70, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_HANA_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::abort();
    }
    ready = true;
}

void pc_p2_hana_update(BTeki* actor) {
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
            std::printf("P2_HANA_DEAD generator=%u source_id=84 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        enter(s, HANA_DEAD, "dead");
    }

    s.stateTime += dt;
    switch (s.state) {
    case HANA_SLEEP:
        stop(actor);
        s.hidden = true;
        s.clip = "type1"; // buried pose; phase forced to frame 0
        if (nearestTarget(pos)) {
            std::printf("P2_HANA_STATE generator=%u state=emerge\n", generator);
            enter(s, HANA_EMERGE, "type1");
        }
        break;
    case HANA_EMERGE:
        stop(actor);
        s.hidden = false;
        if (s.stateTime >= clipDuration("type1")) {
            std::printf("P2_HANA_STATE generator=%u state=walk\n", generator);
            enter(s, HANA_WALK, "move1");
        }
        break;
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
        const float frame = motionFrame(s);
        // Source StateAttack::exec KEYEVENT_2: attackNavi + eatAttackPikmin.
        if (!s.firedEvents.count(s.biteFrame) && frame >= float(s.biteFrame)) {
            s.firedEvents.insert(s.biteFrame);
            doAttackNavi(actor, s, generator);
            Piki* piki = nearestPiki(pos, ATTACK_RANGE);
            if (piki) {
                s.captured = piki;
                std::printf("P2_HANA_BITE generator=%u frame=%.1f pikmin=1\n", generator, frame);
                std::fflush(stdout);
            }
        }
        // Source StateAttack::exec KEYEVENT_3: swallowPikmin(poisonDamage).
        if (s.captured && !s.killed && frame >= float(s.swallowFrame)) {
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
        if (!s.firedEvents.count(s.flickFrame) && s.stateTime >= s.flickFrame / 30.0f) {
            s.firedEvents.insert(s.flickFrame);
            doFlick(actor, s);
            std::printf("P2_HANA_FLICK generator=%u frame=%d\n", generator, s.flickFrame);
            std::fflush(stdout);
        }
        if (s.stateTime >= clipDuration("flick")) {
            std::printf("P2_HANA_STATE generator=%u state=walk\n", generator);
            enter(s, HANA_WALK, "move1");
        }
        break;
    }
    case HANA_DEAD:
        stop(actor);
        if (s.stateTime >= clipDuration("dead")) actor->die();
        break;
    default:
        break;
    }
    applyUndergroundGate(actor, s, generator);
    setPhase(s);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        std::printf("P2_HANA_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z);
        std::fflush(stdout);
    }
}
