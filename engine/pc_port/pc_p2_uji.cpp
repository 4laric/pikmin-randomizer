#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
// Family-owned sheargrub source behavior for the campaign-identity Uji family:
// Female Sheargrub (UjiA, EnemyID 12), Male Sheargrub (UjiB, 13) and Shearwig
// (Tobi, 14) on the P1 KabekuiA/B/C placement vehicles (#871, inst-bugs).
// Implements the source Stay->Appear->Move->Attack1 cycle (UjiaState.cpp),
// plus Attack2->Eat for UjiB (UjibState.cpp: Attack2 bites/captures Pikmin,
// Eat carries) and the Fly loop for Tobi (TobiState.cpp: airborne reposition
// with the same attack chain). Driven from p2-uji-actors.txt /
// p2-uji-bank.txt written by experimental/pikmin2_uji_content.py in the exact
// batch-2 grammar (P2_UJI_ACTORS_1 / P2_UJI_BANK_1), with sampled pose meshes
// uji_<Species>_<clip>_%02d.mod loaded by the batch-2 uji family path.
// Source revision 632af93787b9c95b63f0c13be32b161375ce3a96; retail general
// parms from EnemyParmsBase (life 100, move 80, territory/sight 200) and UjiA
// proper fp01 bridge damage 25 (Ujia.h:118); species enemyparm.txt preserved
// by experimental/pikmin2_uji_assets.py.
//
// Port adaptations (recorded, not retail-faithful):
//   * View-angle detection is a full hemisphere (no fp13 view cone in the
//     general block); sight radius is the source fp12 default 200.
//   * Turn rate is fixed (~2 rad/s); source uses the fp turn class.
//   * Attack semantics (#886 defect 5, see pc_p2_uji_policy.h): UjiA never
//     harms a creature (its Attack1 is the bridge gnaw, and no P2 bridge
//     target exists on P1 maps). UjiB/Tobi enter Attack2 on a target inside
//     the source fp20/fp21 cone; its KEYEVENT_4 (frame 14) fires ONCE:
//     attackNavi(fp22, fp23, fp24) on every captain in the cone plus
//     eatPikmin through the kamujnt slot (pc_p2_captor_mouth.h, r=15, a
//     documented port approximation of the joint), physically sticking the
//     Pikmin to the P1 Kabekui host 'slot' part (pc_p2_captor_host.h, the
//     same InteractSwallow the P1 TAIAbiteForKabekui uses). Attack2 END goes
//     to Eat only with stuck Pikmin; Eat KEYEVENT_2 (frame 53) swallows only
//     Pikmin still held (poison proper default 300). Death and teardown
//     release the mouth. Tobi Fly keeps the host grounded drive (no
//     altitude physics).
//   * Appear/attack/dive/eat/fly durations are port values (source ends on
//     motion end). The general fp20-fp24 values are the EnemyParmsBase
//     header defaults (no retail Uji general block is extracted here).
// No other lane's module is modified; every hook is a no-op for unregistered
// actors.
#include "pc_p2_uji.h"
#include "pc_p2_uji_policy.h"
#include "pc_p2_captor_host.h"
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

using p2uji_policy::Fsm;
using p2uji_policy::In;
using p2uji_policy::Kind;
using p2uji_policy::Out;
using p2uji_policy::Parms;
using p2uji_policy::State;
using p2uji_policy::TOBI;
using p2uji_policy::UJIA;
using p2uji_policy::UJIB;
using p2uji_policy::UJI_ATTACK1;
using p2uji_policy::UJI_ATTACK2;
using p2uji_policy::UJI_DEAD;
using p2uji_policy::UJI_DIVE;
using p2uji_policy::UJI_EAT;
using p2uji_policy::UJI_FLY;
using p2uji_policy::UJI_GOHOME;
using p2uji_policy::UJI_MOVE;
using p2uji_policy::UJI_STAY;
using p2uji_policy::UJI_APPEAR;

const char* kindName(Kind k) {
    return k == UJIA ? "UjiA" : k == UJIB ? "UjiB" : "Tobi";
}

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events; // source frame -> key event type
};

struct Uji {
    Kind kind = UJIA;
    int sourceId = 12;
    Parms parms;
    Fsm fsm;
    float heading = 0.0f;
    Vector3f home;
    BTeki* self = nullptr;
    float lastHealth = 100.0f;
    bool deadLogged = false;
    bool hitLogged = false;
    p2captor::Held<Piki> held; // Pikmin in the kamujnt slot (validated against the host stick)
    bool mouthLogged = false;
    bool escaped = false;
    bool atariOn = false;
    bool gateInit = false;
    int hostMotion = -1;
    float tickAccum = 0.0f;
    std::string clip = "dive";
    float phase = 0.0f;
};

std::map<PelletView*, Uji> actors;
// Per-species bank clips: kind -> (clip name -> Clip).
std::map<std::string, std::map<std::string, Clip>> bankClips;
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
unsigned genOf(const BTeki* actor) { return pc_p2_campaign_token(const_cast<BTeki*>(actor)); }
Uji* lookup(BTeki* actor) {
    auto it = actors.find(static_cast<PelletView*>(actor));
    return it == actors.end() ? nullptr : &it->second;
}
Clip* clipFor(Uji& s, const std::string& name) {
    auto kit = bankClips.find(kindName(s.kind));
    if (kit == bankClips.end()) return nullptr;
    auto it = kit->second.find(name);
    return it == kit->second.end() ? nullptr : &it->second;
}
float clipDuration(Uji& s, const std::string& name) {
    Clip* c = clipFor(s, name);
    return c ? c->duration : 1.0f;
}
bool clipLoops(Uji& s, const std::string& name) {
    Clip* c = clipFor(s, name);
    return c && c->loop;
}
bool targetInSight(const Vector3f& pos, float sight) {
    for (Navi* n : pc_p2_navis()) {
        if (n->isAlive() && distXZ(n->getPosition(), pos) < sight) return true;
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (p && p->isAlive() && distXZ(p->getPosition(), pos) < sight) return true;
        }
    }
    return false;
}
void enter(Uji& s, State state) {
    s.fsm.enter(state);
    s.clip = Fsm::clipFor(state, s.kind);
}
const char* stateName(State s);
// Source underground flags (UjiaState isAppearCheck/setBridgeSearch): while
// buried (Stay/Dive) the grub is model-hidden, untargetable and invulnerable.
// The suppressed Kabekui host never emerges on its own, so the P2 FSM drives
// the host collision/authority flags itself (hana pattern): buried =
// no-atari + Invincible, emerged = atari + vulnerable.
void applyBurrowGate(BTeki* a, Uji& s, unsigned generator) {
    const bool buried = (s.fsm.state == UJI_STAY || s.fsm.state == UJI_DIVE);
    const bool wantAtari = !buried;
    if (s.gateInit && wantAtari == s.atariOn) return;
    s.gateInit = true;
    s.atariOn = wantAtari;
    if (buried) {
        a->clearTekiOption(TEKIOPT_Atari);
        a->setTekiOption(TEKIOPT_Invincible);
        std::printf("P2_UJI_UNDERGROUND generator=%u source_id=%d event=enter no_atari=1 invulnerable=1\n",
                    generator, s.sourceId);
    } else {
        a->setTekiOption(TEKIOPT_Atari);
        a->clearTekiOption(TEKIOPT_Invincible);
        std::printf("P2_UJI_UNDERGROUND generator=%u source_id=%d event=exit no_atari=0 invulnerable=0\n",
                    generator, s.sourceId);
    }
    std::fflush(stdout);
}
// The suppressed Kabekui host never runs its own appear/move/attack motions,
// so its collision parts would stay frozen in the spawn (burrowed) pose while
// the P2 model fights above ground and Pikmin could never stick. Drive the
// (invisible - batch2 draws the P2 model instead) host animator from the P2
// FSM so the collparts ride along: emerge uses the host's own appear motion
// (WaitAct2, cf TAIkabekuiA.cpp:254), locomotion Move1, bites Attack.
void driveHostMotion(BTeki* a, Uji& s) {
    int want = -1;
    switch (s.fsm.state) {
    case UJI_APPEAR:
    case UJI_EAT:
        want = TekiMotion::WaitAct2;
        break;
    case UJI_MOVE:
    case UJI_GOHOME:
    case UJI_FLY:
        want = TekiMotion::Move1;
        break;
    case UJI_ATTACK1:
    case UJI_ATTACK2:
        want = TekiMotion::Attack;
        break;
    case UJI_DEAD:
        want = TekiMotion::Dead;
        break;
    default:
        return; // STAY/DIVE: keep the burrowed pose (no atari anyway)
    }
    if (want == s.hostMotion) return;
    s.hostMotion = want;
    a->startMotion(want);
}
// Nearest live Pikmin/Navi for the P2-owned bite and for turn-to-target.
Creature* nearestFoe(const Vector3f& pos, float range) {
    Creature* best = nullptr;
    float bestSq = range * range;
    if (naviMgr) {
        for (Navi* n : pc_p2_navis()) {
            if (!n->isAlive()) continue;
            const float dx = n->getPosition().x - pos.x, dz = n->getPosition().z - pos.z;
            const float d = dx * dx + dz * dz;
            if (d < bestSq) { bestSq = d; best = n; }
        }
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive() || p->isStickToMouth()) continue; // a held Pikmin is not a target
            const float dx = p->getPosition().x - pos.x, dz = p->getPosition().z - pos.z;
            const float d = dx * dx + dz * dz;
            if (d < bestSq) { bestSq = d; best = p; }
        }
    }
    return best;
}
// Source isTargetAttackable / getNearestPikminOrNavi(fp21, fp20): a live
// captain or searchable Pikmin inside the facing cone.
bool targetAttackable(const Vector3f& pos, const Uji& s) {
    const Parms& p = s.parms;
    for (Navi* n : pc_p2_navis()) {
        if (!n->isAlive()) continue;
        const Vector3f q = n->getPosition();
        if (p2uji_policy::inCone(q.x - pos.x, q.y - pos.y, q.z - pos.z, s.heading, p.attackRange, p.attackAngle))
            return true;
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* pk = static_cast<Piki*>(*it);
            if (!pk || !pk->isAlive() || pk->isStickToMouth()) continue;
            const Vector3f q = pk->getPosition();
            if (p2uji_policy::inCone(q.x - pos.x, q.y - pos.y, q.z - pos.z, s.heading, p.attackRange, p.attackAngle))
                return true;
        }
    }
    return false;
}
const p2captor::Geometry& mouthGeometry(const Uji& s) {
    return *p2captor::geometryFor(unsigned(s.sourceId));
}
// Source Attack2 KEYEVENT_4 (UjiB/Tobi only, once per Attack2): attackNavi
// on every captain in the fp22/fp23 cone, then eatPikmin through kamujnt.
void ujiStrike(BTeki* a, Uji& s, unsigned generator) {
    if (!p2uji_policy::attacksCreatures(s.kind)) return;
    const Vector3f pos = a->getPosition();
    int navis = 0;
    for (Navi* n : pc_p2_navis()) {
        if (!n->isAlive()) continue;
        const Vector3f q = n->getPosition();
        if (!p2uji_policy::inCone(q.x - pos.x, q.y - pos.y, q.z - pos.z, s.heading, s.parms.attackRadius,
                                  s.parms.hitAngle, true)) continue;
        if (n->stimulate(InteractAttack(a, nullptr, s.parms.attackDamage, false))) ++navis;
    }
    const p2captor::Geometry& g = mouthGeometry(s);
    if (!s.mouthLogged) {
        s.mouthLogged = true;
        std::printf("P2_UJI_MOUTH generator=%u source_id=%d slots=%d radius=%.1f local_z=%.1f host_slots=%d\n",
                    generator, s.sourceId, g.slots, g.radius, g.local[0][2], p2captorhost::hostSlotCount(a));
        std::fflush(stdout);
    }
    bool occupied[p2captor::MaxSlots] = {};
    p2captorhost::validate(a, s.held, g.slots, occupied);
    p2captorhost::Scene scene = p2captorhost::snapshot(a);
    const p2captor::Vec3 apos = p2captorhost::vec(pos);
    int refused = 0;
    const int eaten = p2captor::eat(g, apos, s.heading, scene.prey.data(), (int)scene.prey.size(), occupied,
                                    p2captor::defaultEligible, [&](int n, int slot) {
        return p2captorhost::swallowInto(a, scene, n, slot, s.held, 1, &refused);
    });
    std::printf("P2_UJI_ATTACK generator=%u source_id=%d frame=%d navi=%d eaten=%d refused_no_host=%d "
                "navi_damage=%.1f\n", generator, s.sourceId, s.parms.strikeFrame, navis, eaten, refused,
                s.parms.attackDamage);
    std::fflush(stdout);
}
// Source Eat KEYEVENT_2: swallowPikmin(proper poison) on Pikmin still held.
void ujiSwallow(BTeki* a, Uji& s, unsigned generator) {
    int white = 0;
    const int killed = p2captorhost::swallow(a, s.held, mouthGeometry(s).slots, s.parms.poisonDamage, &white);
    std::printf("P2_UJI_EAT generator=%u source_id=%d frame=%d pikmin=%d white=%d\n", generator, s.sourceId,
                s.parms.swallowFrame, killed, white);
    std::fflush(stdout);
}
void wander(BTeki* a, Uji& s, float speed) {
    a->setDirection(s.heading);
    const Vector3f drive(std::sin(s.heading) * speed, 0.0f, std::cos(s.heading) * speed);
    a->inputDrive(drive);
    a->mVelocity.set(drive);
}
void stop(BTeki* a) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
}
void setPhase(Uji& s, float dt) {
    const float duration = clipDuration(s, s.clip);
    const float len = duration > 0.0f ? duration : 1.0f;
    if (clipLoops(s, s.clip)) {
        s.phase += dt / len;
        s.phase -= std::floor(s.phase);
    } else {
        s.phase += dt / len;
        if (s.phase > 1.0f) s.phase = 1.0f;
    }
}
const char* stateName(State s) {
    switch (s) {
    case UJI_DEAD: return "dead";
    case UJI_STAY: return "stay";
    case UJI_APPEAR: return "appear";
    case UJI_DIVE: return "dive";
    case UJI_MOVE: return "move";
    case UJI_GOHOME: return "gohome";
    case UJI_ATTACK1: return "attack1";
    case UJI_ATTACK2: return "attack2";
    case UJI_EAT: return "eat";
    case UJI_FLY: return "fly";
    default: return "null";
    }
}

} // namespace

void pc_p2_uji_reset() {
    actors.clear();
    bankClips.clear();
    ready = false;
}
unsigned long pc_p2_uji_count() { return (unsigned long)actors.size(); }
bool pc_p2_uji_registered(BTeki* actor) { return actors.count(static_cast<PelletView*>(actor)) != 0; }
bool pc_p2_uji_suppress_ai(const BTeki* actor) {
    return ready && actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor))) != 0;
}
void pc_p2_uji_forget(BTeki* actor) {
    // Lane 06 single-use binding: drop the ordinary-delivery source so a
    // recycled actor address can never inherit it and credit the P1 proxy
    // as an onion:p2 grant. The central pc_p2_forget_teki seam also clears
    // it; this is idempotent.
    pc_randomizer_p2_forget_source(static_cast<PelletView*>(actor));
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it != actors.end()) p2captorhost::release(actor, it->second.held); // teardown frees the mouth
    actors.erase(static_cast<PelletView*>(actor));
}
void pc_p2_uji_forget_piki(Piki* piki) {
    for (auto& entry : actors) entry.second.held.forget(piki);
}

float pc_p2_uji_param_f(const BTeki* actor, int idx, float fallback) {
    if (!ready || !actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor)))) return fallback;
    if (idx == TPF_Life) {
        auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
        return it->second.parms.life;
    }
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

bool pc_p2_uji_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

const char* pc_p2_uji_state_name(const BTeki* actor) {
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return nullptr;
    return stateName(it->second.fsm.state);
}

void pc_p2_uji_setup() {
    pc_p2_uji_reset();
    {
        int live = 0;
        if (tekiMgr) {
            Iterator it(tekiMgr);
            CI_LOOP(it) {
                Teki* a = static_cast<Teki*>(*it);
                if (a) ++live;
            }
        }
        std::printf("P2_UJI_SETUP_ENTER teki=%d bridge=%d\n",
                    live, pc_randomizer_p2_bridge() ? 1 : 0);
        std::fflush(stdout);
    }
    if (!tekiMgr) return;

    std::ifstream bank("p2-uji-bank.txt");
    if (bank) {
        std::string token;
        if (bank >> token && token == "P2_UJI_BANK_1") {
            while (bank >> token) {
                if (token == "species") {
                    std::string species, id;
                    bank >> species >> id;
                    bankClips[species]; // ensure per-species bucket
                } else if (token == "clip") {
                    std::string species, name, events, marker, status;
                    long long frames = 0;
                    int poses = 0;
                    bank >> species >> name >> frames >> events >> marker >> poses >> status;
                    if (bankClips.count(species)) {
                        Clip clip;
                        clip.name = name;
                        clip.duration = frames > 0 ? float(frames) / 30.0f : 1.0f;
                        clip.loop = (name == "move" || name == "fly");
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
                        bankClips[species][name] = clip;
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

    std::ifstream in("p2-uji-actors.txt");
    if (!in) return;
    std::string header;
    int count = 0;
    if (!(in >> header >> count) || header != "P2_UJI_ACTORS_1" || count < 1) return;
    std::map<unsigned, std::string> wanted;
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        std::string species;
        if (!(in >> generator >> species)) return;
        if (species == "UjiA" || species == "UjiB" || species == "Tobi")
            wanted[unsigned(generator)] = species;
    }
    if (pc_randomizer_p2_bridge()) {
        wanted.clear();
        for (unsigned id : pc_p2_campaign_ids(12)) wanted[id] = "UjiA";
        for (unsigned id : pc_p2_campaign_ids(13)) wanted[id] = "UjiB";
        for (unsigned id : pc_p2_campaign_ids(14)) wanted[id] = "Tobi";
    }
    std::printf("P2_UJI_SETUP_WANTED wanted=%zu\n", wanted.size());
    std::fflush(stdout);
    if (wanted.empty()) return;

    std::set<unsigned> found;
    const bool bridge = pc_randomizer_p2_bridge();
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor) continue;
        // Bridge campaigns match by campaign token (pack-spawned members
        // share one token and may carry no mGenerator, exactly like the
        // batch-2 bind); outside bridge, match the filed generator id.
        const unsigned token = pc_p2_campaign_token(actor);
        const unsigned key =
            bridge ? token : (actor->mGenerator ? actor->mGenerator->_70 : 0u);
        if (!bridge && key == 0u) continue;
        auto match = wanted.find(key);
        if (match == wanted.end()) continue;
        const std::string& species = match->second;
        const Kind kind = species == "UjiA" ? UJIA : species == "UjiB" ? UJIB : TOBI;
        const int wantType = p2uji_policy::hostTypeFor(kind);
        if (actor->mTekiType != wantType) {
            std::printf("P2_UJI_ERROR native_type generator=%u species=%s\n", token, species.c_str());
            if (pc_p2_setup_skip(pc_randomizer_p2_bridge(), species.c_str(), "actor_type_mismatch")) return;
        }
        Uji& s = actors[static_cast<PelletView*>(actor)];
        s.kind = kind;
        s.sourceId = p2uji_policy::sourceIdFor(kind);
        s.parms = p2uji_policy::parmsFor(kind);
        // Retail key-event frames from the installed bank when present.
        if (Clip* c = clipFor(s, "attack2")) {
            for (const auto& e : c->events) if (e.second == 4) s.parms.strikeFrame = e.first;
        }
        if (Clip* c = clipFor(s, "eat")) {
            for (const auto& e : c->events) if (e.second == 2) s.parms.swallowFrame = e.first;
        }
        s.self = actor;
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        s.lastHealth = s.parms.life;
        actor->mHealth = s.parms.life;
        s.fsm.reset();
        s.clip = "dive";
        s.phase = 0.0f;
        applyBurrowGate(actor, s, token);
        // Ordinary-delivery bridge (lane 06 contract): bind the source so
        // GoalItem::suckMe grants onion:p2:<id> exactly once through
        // pc_randomizer_p2_corpse_delivered. Single-use: consumed on
        // delivery and cleared on forget/recycle.
        pc_randomizer_p2_bind_source(static_cast<PelletView*>(actor), (unsigned)s.sourceId, token);
        std::printf("P2_UJI_DELIVERY_BIND generator=%u source_id=%d\n", token, s.sourceId);
        std::printf("P2_UJI_BIND generator=%u source_id=%d visual_only=0\n", token, s.sourceId);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=%s native_family=Kabekui generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=bridge_bite\n",
                    species.c_str(), token, pos.x, pos.y, pos.z, actor->mHealth, s.parms.life);
        found.insert(token);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_UJI_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        if (pc_p2_setup_skip(pc_randomizer_p2_bridge(), "Uji", "actor_roster_incomplete")) return;
    }
    ready = true;
}

void pc_p2_uji_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Uji& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = genOf(actor);

    // The P1 TAI damage reaction lives in the suppressed host strategy, so
    // the P2 FSM drains queued Pikmin damage itself (frog pattern).
    if (actor->mStoredDamage > 0.0f) actor->makeDamaged();

    if (actor->mHealth < s.lastHealth && actor->mHealth > 0.0f && !s.hitLogged) {
        std::printf("P2_UJI_HIT generator=%u source_id=%d health=%.1f\n",
                    generator, s.sourceId, actor->mHealth);
        std::fflush(stdout);
        s.hitLogged = true;
    }
    s.lastHealth = actor->mHealth;

    if (actor->mHealth <= 0.0f && s.fsm.state != UJI_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_UJI_DEAD generator=%u source_id=%d health=0\n", generator, s.sourceId);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        const int freed = p2captorhost::release(actor, s.held);
        if (freed > 0) {
            std::printf("P2_UJI_RELEASE generator=%u reason=death pikmin=%d\n", generator, freed);
            std::fflush(stdout);
        }
        enter(s, UJI_DEAD);
        applyBurrowGate(actor, s, generator);
        setPhase(s, dt);
        return;
    }
    if (s.fsm.state == UJI_DEAD) {
        // dieSoon() only runs inside the suppressed host doAI; finalize the
        // corpse outside doAI once the dead clip completes (frog pattern).
        s.fsm.stateTime += dt;
        if (!s.escaped && s.fsm.stateTime >= clipDuration(s, "dead")) {
            s.escaped = true;
            actor->pcEscapeNow();
        }
        setPhase(s, dt);
        return;
    }

    In in;
    in.health = actor->mHealth;
    in.targetInSight = targetInSight(pos, s.parms.sight);
    in.targetAttackable = targetAttackable(pos, s);
    in.stuckPikmin = p2captorhost::pikiStickerCount(actor) > 0;
    in.farFromHome = distXZ(pos, s.home) > s.parms.territory;
    Out out;
    // Fixed-step policy tick (30 Hz retail clock): accumulate real dt into
    // 30 Hz quanta so behavior is frame-rate independent.
    s.tickAccum += dt;
    bool moved = false;
    while (s.tickAccum >= 1.0f / 30.0f) {
        s.tickAccum -= 1.0f / 30.0f;
        const State before = s.fsm.state;
        const bool changed = s.fsm.tick(in, s.parms, s.kind, out);
        if (out.strike) {
            ujiStrike(actor, s, generator);
            in.stuckPikmin = p2captorhost::pikiStickerCount(actor) > 0;
        }
        if (out.swallow) ujiSwallow(actor, s, generator);
        if (changed && s.fsm.state != UJI_EAT) {
            // Only Attack2 -> Eat carries the mouth.
            const int freed = p2captorhost::release(actor, s.held);
            if (freed > 0) {
                std::printf("P2_UJI_RELEASE generator=%u reason=transition pikmin=%d\n", generator, freed);
                std::fflush(stdout);
            }
        }
        if (changed && s.fsm.state != before) {
            s.clip = Fsm::clipFor(s.fsm.state, s.kind);
            s.phase = 0.0f;
            std::printf("P2_UJI_STATE generator=%u state=%s\n", generator, stateName(s.fsm.state));
            std::fflush(stdout);
            moved = true;
        }
    }
    (void)moved;
    applyBurrowGate(actor, s, generator);
    driveHostMotion(actor, s);

    // Drive the P1 vehicle per state. Source Move wanders toward the target
    // (turnToTarget); the fixed heading drift is kept only with no target in
    // sight. Attack windows stop and deal the OWN P2 bite (ujiStrike).
    switch (s.fsm.state) {
    case UJI_MOVE:
    case UJI_GOHOME:
    case UJI_FLY: {
        if (s.fsm.state == UJI_GOHOME) {
            const float dx = s.home.x - pos.x, dz = s.home.z - pos.z;
            if (dx * dx + dz * dz > 1e-6f) s.heading = std::atan2(dx, dz);
        } else if (Creature* foe = nearestFoe(pos, s.parms.sight)) {
            // Source turnToTarget at ~2 rad/s toward the prey.
            const Vector3f fp = foe->getPosition();
            const float desired = std::atan2(fp.x - pos.x, fp.z - pos.z);
            const float maxTurn = 2.0f * dt;
            float diff = wrapPi(desired - s.heading);
            if (diff > maxTurn) diff = maxTurn;
            if (diff < -maxTurn) diff = -maxTurn;
            s.heading = wrapPi(s.heading + diff);
        } else {
            s.heading = wrapPi(s.heading + 0.6f * dt);
        }
        wander(actor, s, s.parms.moveSpeed);
        break;
    }
    case UJI_ATTACK1:
    case UJI_ATTACK2:
        stop(actor); // the one Attack2 strike fires from the FSM key event above
        break;
    case UJI_EAT:
        stop(actor);
        break;
    default:
        stop(actor);
        break;
    }
    setPhase(s, dt);
}
