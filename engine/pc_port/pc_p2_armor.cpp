// Family-owned ground-invertebrate source behavior for the batch-2 Chappy
// placement vehicle: Cloaking Burrow-nit (Armor, EnemyID 15). Implements the
// source ArmorState.cpp combat FSM: Stay (buried) -> Appear -> Move/GoHome ->
// Attack2 -> Eat/Fail -> Dead, plus Flick. Bridge states (Attack1, MoveSide/
// Centre/Top) are source-backed N/A because the arena has no ItemBridge.
// Source revision 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_ground_inverts_assets.py (GPVE01 rev 0).
//
// Port adaptations (recorded, not retail-faithful):
//   * The P2 mouth-slot swallow is resolved on the P1 host as an explicit
//     capture within the source attack sweep radius at the attack2 source
//     damage event (frame 18), then a single InteractKill at the source eat
//     event (frame 60); flick fires on the flick source event (frame 39).
//     Timing is delivered by the authoritative sampled clock (#431), so the
//     effects fire exactly once across skipped frames, pause, interruption and
//     actor-address reuse. Exactly-once per bite.
//   * The source `damageCallBack` part-id rule (`dmg1`/bittered) is implemented
//     as a registered receiver (pc_p2_armor_receiver_rejects) hooked from
//     InteractAttack/InteractBomb::actTeki. The P1 host exposes the stuck-to
//     target's CollPart, but this visual-only Armor rides the P1 Chappy
//     collision and does not load the source model's `dmg1`. When `dmg1` is
//     absent the receiver designates one host collision part (the bounding
//     sphere) as a documented single-weakpoint-sphere approximation by part id
//     and logs `P2_ARMOR_RECEIVER_PART`; if none resolves, all non-bittered
//     damage is rejected. It never silently accepts all damage.
//   * `EB_Bittered` has no P1 host equivalent; pc_p2_armor_set_bittered is the
//     explicit host/fixture input for the bittered leg of the same rule.
//   * `doStartStoneState` flick is implemented, but the P1 host has no
//     petrification lifecycle. pc_p2_armor_update fires it on the rising edge
//     of TEKIOPT_Pressed (the host's flattened/incapacitated analogue) and the
//     port records `P2_ARMOR_STONE_NOTE host_lifecycle=absent port_analogue=pressed`.
//   * View angle is a full hemisphere (fp13 absent from the Armor general block);
//     turn rate and flick radius are documented port adaptations.
// No other lane's module is modified; every hook is a no-op for unregistered actors.
#include "pc_p2_armor.h"
#include "pc_p2_armor_events.h"
#include "pc_p2_armor_receiver_policy.h"
#include "teki.h"
#include "Interactions.h"
#include "Collision.h"
#include "ID32.h"
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
    ARMOR_INVALID = -1,
    ARMOR_DEAD = 0,
    ARMOR_STAY = 1,
    ARMOR_APPEAR = 2,
    ARMOR_DIVE = 3,
    ARMOR_MOVE = 4,
    ARMOR_GOHOME = 8,
    ARMOR_ATTACK2 = 10,
    ARMOR_EAT = 11,
    ARMOR_FLICK = 12,
    ARMOR_FAIL = 13,
};

const char* stateName(State s) {
    switch (s) {
    case ARMOR_DEAD: return "dead";
    case ARMOR_STAY: return "stay";
    case ARMOR_APPEAR: return "appear";
    case ARMOR_DIVE: return "dive";
    case ARMOR_MOVE: return "move";
    case ARMOR_GOHOME: return "gohome";
    case ARMOR_ATTACK2: return "attack2";
    case ARMOR_EAT: return "eat";
    case ARMOR_FLICK: return "flick";
    case ARMOR_FAIL: return "fail";
    default: return "null";
    }
}

// Source enemyparm.txt values (ground_inverts manifest general).
constexpr float LIFE = 300.0f;
constexpr float MOVE_SPEED = 50.0f;
constexpr float SIGHT = 200.0f;
constexpr float TERRITORY = 400.0f;
constexpr float HOME_RADIUS = 30.0f;
constexpr float ATTACK_RANGE = 75.0f;
constexpr float ATTACK_ANGLE = 0.785398f; // fp attack hit angle ~45 deg
constexpr float TURN_RATE = 2.0f;         // port adaptation
constexpr float FLICK_RADIUS = 25.0f;     // port adaptation
constexpr float SHAKE_RANGE = 100.0f;
constexpr float SHAKE_KNOCKBACK = 120.0f;

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events;
    p2sampled::Clip sampled;
};

struct Armor {
    State state = ARMOR_STAY;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    Piki* captured = nullptr;
    p2armorevents::Receiver events;
    std::string clip = "appear";
    float phase = 0.0f;
    bool biteLogged = false;
    bool deadLogged = false;
    float logTimer = 0.0f;
    // Damage-receiver / stone-flick port state (see pc_p2_armor.h).
    bool bittered = false;
    bool stone = false;
    bool dmg1Present = false;
    bool weakpointActive = false;
    unsigned weakpointId = 0;
};

std::map<PelletView*, Armor> actors;
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
std::string fourCCString(unsigned id) {
    char buf[5];
    buf[0] = char((id >> 24) & 0xffu);
    buf[1] = char((id >> 16) & 0xffu);
    buf[2] = char((id >> 8) & 0xffu);
    buf[3] = char(id & 0xffu);
    buf[4] = '\0';
    for (int i = 0; i < 4; ++i) {
        if (buf[i] < 32 || buf[i] > 126) buf[i] = '?';
    }
    return std::string(buf);
}
// Resolve the damage-receiver weakpoint from the host collision and log it.
// The source `dmg1` part wins when the host actually loaded it; otherwise the
// first collision part (bounding sphere) is the documented port approximation.
void resolveReceiverPart(Creature* actor, Armor& s) {
    s.dmg1Present = false;
    s.weakpointActive = false;
    s.weakpointId = 0;
    CollPart* dmg1 = nullptr;
    CollPart* bound = nullptr;
    if (actor->mCollInfo) {
        dmg1 = actor->mCollInfo->getSphere(p2armorreceiver::DamagePartID);
        bound = actor->mCollInfo->getBoundingSphere();
    }
    if (dmg1) {
        s.dmg1Present = true;
        s.weakpointActive = true;
        s.weakpointId = dmg1->getID().mId;
    } else if (bound) {
        s.weakpointActive = true;
        s.weakpointId = bound->getID().mId;
    }
    const char* mode = s.dmg1Present ? "source_dmg1"
        : (s.weakpointActive ? "port_bounding_sphere" : "reject_all");
    std::printf("P2_ARMOR_RECEIVER_PART generator=%u dmg1=%s weakpoint=%s mode=%s\n",
                actor->mGenerator ? actor->mGenerator->_70 : 0u,
                s.dmg1Present ? "present" : "absent",
                s.weakpointActive ? fourCCString(s.weakpointId).c_str() : "none", mode);
    // The P1 host has no petrification lifecycle; record the wired analogue.
    std::printf("P2_ARMOR_STONE_NOTE generator=%u host_lifecycle=absent port_analogue=pressed\n",
                actor->mGenerator ? actor->mGenerator->_70 : 0u);
    std::fflush(stdout);
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
void doFlick(BTeki* a, Armor& s) {
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
void enter(Armor& s, State state, const char* clip) {
    s.state = state;
    s.stateTime = 0.0f;
    s.biteLogged = false;
    if (clip) s.clip = clip;
    auto it = clips.find(s.clip);
    if (it != clips.end()) {
        s.events.start(it->second.sampled, it->second.name);
    } else {
        s.events.cancel();
    }
}
void walkTo(BTeki* a, Armor& s, const Vector3f& target, float dt) {
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

void setPhase(Armor& s) {
    if (s.state == ARMOR_STAY) { s.phase = 0.0f; return; }
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

void pc_p2_armor_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}
void pc_p2_armor_forget_piki(Piki* piki) {
    for (auto& entry : actors) if (entry.second.captured == piki) entry.second.captured = nullptr;
}

void pc_p2_armor_forget(BTeki* actor) { actors.erase(static_cast<PelletView*>(actor)); }

unsigned long pc_p2_armor_count() { return (unsigned long)actors.size(); }
bool pc_p2_armor_registered(BTeki* actor) { return actors.count(static_cast<PelletView*>(actor)) != 0; }
bool pc_p2_armor_receiver_rejects(Teki* teki, const InteractAttack* attack) {
    if (!ready || !teki) return false;
    auto it = actors.find(static_cast<PelletView*>(teki));
    if (it == actors.end()) return false;
    const Armor& s = it->second;

    p2armorreceiver::Inputs in;
    in.bittered = s.bittered;
    in.has_part = attack && attack->mCollPart;
    in.part_id = in.has_part ? attack->mCollPart->getID().mId : 0u;
    // The port weakpoint substitutes for the missing source `dmg1` part; the
    // exact source rule already covers `dmg1` when present.
    in.weakpoint_active = s.weakpointActive && !s.dmg1Present;
    in.weakpoint_id = s.weakpointId;

    const p2armorreceiver::Decision decision = p2armorreceiver::decide(in);
    const bool reject = decision == p2armorreceiver::Decision::Reject;
    std::printf("P2_ARMOR_RECEIVER generator=%u decision=%s reason=%s part=%s bittered=%d "
                "weakpoint=%s\n",
                teki->mGenerator ? teki->mGenerator->_70 : 0u, reject ? "reject" : "accept",
                p2armorreceiver::decisionName(decision),
                in.has_part ? fourCCString(in.part_id).c_str() : "none", int(in.bittered),
                s.weakpointActive ? fourCCString(s.weakpointId).c_str() : "none");
    std::fflush(stdout);
    return reject;
}

void pc_p2_armor_set_bittered(BTeki* actor, bool value) {
    if (!ready || !actor) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    it->second.bittered = value;
    std::printf("P2_ARMOR_BITTERED generator=%u value=%d\n",
                actor->mGenerator ? actor->mGenerator->_70 : 0u, int(value));
    std::fflush(stdout);
}

void pc_p2_armor_start_stone(BTeki* actor) {
    if (!ready || !actor) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Armor& s = it->second;
    if (s.stone) return;
    s.stone = true;

    // Source Obj::doStartStoneState iterates Stickers(this); InteractFlick's
    // actCommon detaches the sticker, so snapshot the list before flicking.
    std::vector<Creature*> mouths;
    for (Creature* c = actor->mStickListHead; c; c = c->mNextSticker) {
        if (c->isStickToMouth()) mouths.push_back(c);
    }
    int flicked = 0;
    for (Creature* c : mouths) {
        if (c->isAlive()
                && c->stimulate(InteractFlick(actor, 0.0f, 0.0f, FLICK_BACKWARDS_ANGLE))) {
            ++flicked;
        }
    }
    // The port mouth-slot capture is the P1 stand-in for the source mouth slot.
    if (s.captured && s.captured->isAlive()) {
        if (s.captured->stimulate(InteractFlick(actor, 0.0f, 0.0f, FLICK_BACKWARDS_ANGLE))) {
            ++flicked;
        }
        s.captured = nullptr;
    }
    std::printf("P2_ARMOR_STONE generator=%u event=enter stuck=%zu flicked=%d\n",
                actor->mGenerator ? actor->mGenerator->_70 : 0u, mouths.size(), flicked);
    std::fflush(stdout);
}

void pc_p2_armor_finish_stone(BTeki* actor) {
    if (!ready || !actor) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Armor& s = it->second;
    if (!s.stone) return;
    s.stone = false;
    // Preserve consumed sampled events across the pressed-state exit; replaying
    // them would duplicate bite/eat effects. Clip transitions reset the clock.
    std::printf("P2_ARMOR_STONE generator=%u event=exit\n",
                actor->mGenerator ? actor->mGenerator->_70 : 0u);
    std::fflush(stdout);
}

float pc_p2_armor_param_f(const BTeki* actor, int idx, float fallback) {
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

bool pc_p2_armor_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

void pc_p2_armor_setup() {
    pc_p2_armor_reset();
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
                    if (species == "Armor") {
                        Clip clip;
                        clip.name = name;
                        clip.duration = frames > 0 ? float(frames) / 30.0f : 1.0f;
                        clip.loop = (name == "move");
                        p2armorevents::Row row;
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
                                    clip.events.emplace_back(eventFrame, std::atoi(key.c_str()));
                                    row.events.push_back(p2sampled::Event{eventFrame, key});
                                }
                                if (comma == std::string::npos) break;
                                start = comma + 1;
                            }
                        }
                        clip.sampled = p2armorevents::makeClip(row);
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
        if (species == "Armor") wanted[unsigned(generator)] = species;
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
            std::printf("P2_ARMOR_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::abort();
        }
        Armor& s = actors[static_cast<PelletView*>(actor)];
        s = Armor();  // reject stale clock/capture state on actor-address reuse
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        actor->mHealth = LIFE;
        resolveReceiverPart(actor, s);
        enter(s, ARMOR_STAY, "appear");
        std::printf("P2_ARMOR_BIND generator=%u source_id=15 visual_only=0\n", actor->mGenerator->_70);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=Armor native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=animation_event\n",
                    actor->mGenerator->_70, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_ARMOR_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::abort();
    }
    ready = true;
}

void pc_p2_armor_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Armor& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    // Port stone analogue: the P1 host has no petrified lifecycle, so the
    // source doStartStoneState flick fires on the rising edge of the host
    // TEKIOPT_Pressed state (see pc_p2_armor.h / P2_ARMOR_RECEIVER.md).
    const bool pressed = actor->getTekiOption(TEKIOPT_Pressed);
    if (pressed && !s.stone) {
        pc_p2_armor_start_stone(actor);
    } else if (!pressed && s.stone) {
        pc_p2_armor_finish_stone(actor);
    }
    const Vector3f pos = actor->getPosition();
    const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;

    if (actor->mHealth <= 0.0f && s.state != ARMOR_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_ARMOR_DEAD generator=%u source_id=15 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        enter(s, ARMOR_DEAD, "dead");
    }

    s.stateTime += dt;
    switch (s.state) {
    case ARMOR_STAY:
        stop(actor);
        s.clip = "appear";
        if (nearestTarget(pos)) {
            std::printf("P2_ARMOR_STATE generator=%u state=appear\n", generator);
            enter(s, ARMOR_APPEAR, "appear");
        }
        break;
    case ARMOR_APPEAR:
        stop(actor);
        if (s.stateTime >= clipDuration("appear")) {
            std::printf("P2_ARMOR_STATE generator=%u state=move\n", generator);
            enter(s, ARMOR_MOVE, "move");
        }
        break;
    case ARMOR_MOVE:
    case ARMOR_GOHOME: {
        Creature* target = nearestTarget(pos);
        if (s.state == ARMOR_MOVE && target) {
            const float angle = std::fabs(wrapPi(std::atan2(target->getPosition().x - pos.x,
                                                           target->getPosition().z - pos.z) - s.heading));
            if (distXZ(target->getPosition(), pos) < ATTACK_RANGE && angle < ATTACK_ANGLE) {
                std::printf("P2_ARMOR_STATE generator=%u state=attack2\n", generator);
                enter(s, ARMOR_ATTACK2, "attack2");
                break;
            }
            walkTo(actor, s, target->getPosition(), dt);
        } else if (s.state == ARMOR_GOHOME || !target) {
            walkTo(actor, s, s.home, dt);
        }
        if (distXZ(pos, s.home) > TERRITORY && s.state != ARMOR_GOHOME) {
            std::printf("P2_ARMOR_STATE generator=%u state=gohome\n", generator);
            enter(s, ARMOR_GOHOME, "move");
            break;
        }
        if (s.state == ARMOR_GOHOME && distXZ(pos, s.home) < HOME_RADIUS) {
            std::printf("P2_ARMOR_STATE generator=%u state=dive\n", generator);
            enter(s, ARMOR_DIVE, "dive");
            break;
        }
        if (shouldFlick(actor)) {
            std::printf("P2_ARMOR_STATE generator=%u state=flick\n", generator);
            enter(s, ARMOR_FLICK, "flick");
        }
        break;
    }
    case ARMOR_ATTACK2: {
        stop(actor);
        for (const p2armorevents::Dispatched& event : s.events.advance(dt)) {
            if (event.action == p2armorevents::Action::Bite && !s.captured) {
                Piki* piki = nearestPiki(pos, ATTACK_RANGE);
                if (piki) {
                    s.captured = piki;
                    std::printf("P2_ARMOR_BITE generator=%u frame=%d pikmin=1\n",
                                generator, event.frame);
                    std::fflush(stdout);
                }
            }
        }
        if (s.stateTime >= clipDuration("attack2")) {
            if (s.captured && s.captured->isAlive()) {
                std::printf("P2_ARMOR_STATE generator=%u state=eat\n", generator);
                enter(s, ARMOR_EAT, "eat");
            } else {
                std::printf("P2_ARMOR_STATE generator=%u state=fail\n", generator);
                enter(s, ARMOR_FAIL, "attack_fail");
            }
        }
        break;
    }
    case ARMOR_EAT: {
        stop(actor);
        for (const p2armorevents::Dispatched& event : s.events.advance(dt)) {
            if (event.action == p2armorevents::Action::Eat) {
                if (s.captured && s.captured->isAlive()) {
                    s.captured->stimulate(InteractKill(actor, 0));
                    std::printf("P2_ARMOR_EAT generator=%u pikmin=1\n", generator);
                    std::fflush(stdout);
                }
                s.captured = nullptr;
            }
        }
        if (s.stateTime >= clipDuration("eat")) {
            s.captured = nullptr;
            std::printf("P2_ARMOR_STATE generator=%u state=move\n", generator);
            enter(s, ARMOR_MOVE, "move");
        }
        break;
    }
    case ARMOR_FLICK: {
        stop(actor);
        for (const p2armorevents::Dispatched& event : s.events.advance(dt)) {
            if (event.action == p2armorevents::Action::Flick) {
                doFlick(actor, s);
                std::printf("P2_ARMOR_FLICK generator=%u frame=%d\n", generator, event.frame);
                std::fflush(stdout);
            }
        }
        if (s.stateTime >= clipDuration("flick")) {
            std::printf("P2_ARMOR_STATE generator=%u state=move\n", generator);
            enter(s, ARMOR_MOVE, "move");
        }
        break;
    }
    case ARMOR_FAIL:
        stop(actor);
        if (s.stateTime >= clipDuration("attack_fail")) {
            std::printf("P2_ARMOR_STATE generator=%u state=move\n", generator);
            enter(s, ARMOR_MOVE, "move");
        }
        break;
    case ARMOR_DIVE:
        stop(actor);
        if (s.stateTime >= clipDuration("dive")) {
            std::printf("P2_ARMOR_STATE generator=%u state=stay\n", generator);
            enter(s, ARMOR_STAY, "appear");
        }
        break;
    case ARMOR_DEAD:
        stop(actor);
        // Host death handoff: the P1 strategy reacts to mHealth<=0 inside
        // BTeki::doAI(), calls die() there and then dieSoon()->becomePellet() in
        // the same doAI() pass. Calling BTeki::die() from this update-phase hook
        // would set mDeadState before the next doAI() and permanently block
        // dieSoon(), leaving a dead-but-present actor with no corpse. The module
        // only drives the source dead clip and lets the host complete
        // teardown/corpse.
        break;
    default:
        break;
    }
    setPhase(s);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        std::printf("P2_ARMOR_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z);
        std::fflush(stdout);
    }
}
