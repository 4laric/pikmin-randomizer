#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
// Family-owned lane-22 elemental-dweevil source behavior for the batch-2 Chappy
// placement vehicle: Fiery Dweevil (FireOtakara, EnemyID 59) and its shared-base
// elemental siblings WaterOtakara (60), GasOtakara (61), ElecOtakara (62),
// plus Volatile Dweevil (BombOtakara, EnemyID 93, BombId).
// Implements the shared OtakaraBase normal FSM subset (Wait/Move/Turn/Flick/Dead,
// OtakaraBase.h:22-39 / OtakaraBaseState.cpp:14-34,71-136) on the P1 host, driven
// from p2-dweevil-actors.txt / p2-dweevil-bank.txt written by the dweevil arena.
// Source revision 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// docs/PIKMIN2_DWEEVIL_ASSETS.md (GPVE01 rev 0).
//
// Port adaptations (recorded, not retail-faithful):
//   * The shared Otakara Flick charge/discharge is resolved on the P1 host as a
//     bounded Flick clip: event type 2 (source `attack1` frame 12) flicks stuck
//     Pikmin, event type 3 (source `attack1` frame 35) discharges the species
//     element through the engine receivers. Fire/Bubble use the P1 InteractFire/
//     InteractBubble receivers; Gas/Denki use the lane-10 InteractGas/InteractDenki
//     receivers (see docs/PIKMIN2_RECEIVER_PATHS.md). Immunity is the receiver's
//     own lane-11 capability matrix (Red/Bulbmin fire, Blue/Bulbmin bubble,
//     White/Bulbmin gas, Yellow/Bulbmin electric).
//   * The item-carry (5..10) states are source-backed N/A: no treasure payload
//     is staged. BombOtakara (93) blast is OWN via this carrier FSM (inst3-misc):
//     Flick discharge event type 3 + damage/death edges route the source Bomb
//     blast (radius 90 fp22, teki 500 fp01, navi/piki 10 fp24, half-height 50
//     fp02, lane-20 pinned values) through the shared bombsarai blast primitive
//     on the live actor's own BTeki tick. The preview-only lane-20 sidecar
//     (pc_p2_bombotakara) remains a fixture driver only, not the bridge path.
//   * Wait/Move/Turn follow OtakaraBase isMovePositionSet/getTargetPosition
//     (OtakaraBase.cpp:361-444, OtakaraBaseState.cpp:165-334) via the engine-free
//     pc_p2_otakara_move.h (#884): elemental Dweevils (59-62) ESCAPE one moveSpeed
//     step away from the nearest Pikmin/Navi, clamped to the 200 home territory;
//     BombOtakara (93) keeps chasing its target (StateBombMove). Transitions commit
//     at the looped clip end (finishMotion -> KEYEVENT_END). No idle wander.
//   * The Flick starts through source EnemyFunc::isStartFlick (enemyAction.cpp:
//     1209-1244), evaluated after the move decision and committed at the clip end
//     like any other mNextState: the hit counter (mFlickTimer, +1 per addDamage)
//     counts InteractAttack receipts plus unattributed health drops, the stuck count
//     is the Pikmin whose getStickObject() is this actor, thresholds are retail
//     ip01-ip07, and Flick event 2 resets the counter (OtakaraBaseState.cpp:107).
//   * BombOtakara (93) chase runs the source stimulateBomb 1.5 s fuse (OtakaraBase.cpp:
//     699-707): 1.5 s of Move/Turn since the last Wait detonates the carried Bomb
//     (trigger=fuse). The port carrier outlives its payload (the source kills it,
//     OtakaraBaseState.cpp:761-764/816-819/880-883), so the chase also keeps the
//     pre-#884 territory rule: outside 200 from home the destination is home.
//   * View angle is a full circle (hit angle fp23=0 on the disc).
// No other lane's module is modified; every hook is a no-op for unregistered actors.
#include "pc_p2_otakara.h"
#include "pc_p2_otakara_fx.h"
#include "pc_p2_otakara_move.h"
#include "pc_p2_otakara_press_policy.h"
#include "pc_p2_dweevil_policy.h"
#include "pc_p2_bombsarai_blast.h"
#include "pc_p2_species.h"
#include "pc_p2_hazard_emitter.h"
#include "teki.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiState.h"
#include "PikiMgr.h"
#include "Pellet.h"
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
    OTA_INVALID = -1,
    OTA_DEAD = 0,
    OTA_FLICK = 1,
    OTA_WAIT = 2,
    OTA_MOVE = 3,
    OTA_TURN = 4,
};

const char* stateName(State s) {
    switch (s) {
    case OTA_DEAD: return "dead";
    case OTA_FLICK: return "flick";
    case OTA_WAIT: return "wait";
    case OTA_MOVE: return "move";
    case OTA_TURN: return "turn";
    default: return "null";
    }
}

// Source per-species general block (docs/PIKMIN2_DWEEVIL_ASSETS.md section 4).
inline float speciesLife(int species) {
    return species == p2dweevil::GasId ? 350.0f : 150.0f; // fp00
}
inline float speciesMoveSpeed(int species) {
    return species == p2dweevil::GasId ? 100.0f : 80.0f; // fp06
}
inline float speciesAttack(int species) {
    switch (species) { // fp24
    case p2dweevil::FireId: return 10.0f;
    case p2dweevil::ElecId: return 10.0f;
    default: return 0.0f; // Water/Gas/Bomb route through the elemental effect
    }
}
inline const char* colorName(unsigned color) {
    switch (color) {
    case Blue: return "blue";
    case Red: return "red";
    case Yellow: return "yellow";
    default: return "other";
    }
}

constexpr float SIGHT = 200.0f;       // fp12
constexpr float TERRITORY = 200.0f;   // fp09 home territory
constexpr float HIT_RANGE = 60.0f;    // fp22 attack hit range (disc)

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events; // source frame -> event type
};

struct Otakara {
    State state = OTA_WAIT;
    float stateTime = 0.0f;
    float timer = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    Vector3f target; // current isMovePositionSet destination (mMovePosition)
    State pending = OTA_INVALID; // source mNextState, committed at the clip end
    bool destClamped = false;
    bool threatValid = false;
    bool threatIsNavi = false;
    p2otakaramove::Vec2 threatPos{0.0f, 0.0f};
    float decisionLogTimer = 0.0f;
    // Source isStartFlick inputs: mFlickTimer (+1 per damage receipt, reset by
    // Flick event 2) and mStuckPikminCount (Pikmin stuck to this actor).
    float flickTimer = 0.0f;
    int stuckCount = 0;
    bool hitSinceDrop = false; // an InteractAttack already counted this drop
    bool flickTriggerLogged = false;
    bool flickEventFired = false; // Flick event 2 ran in this Flick state
    // BombOtakara (93) stimulateBomb fuse (mItemSearchDelayTimer), reset on Wait.
    float bombFuse = 0.0f;
    // P2_OTAKARA_FLEE_SUMMARY episode (Move/Turn stretch).
    bool fleeActive = false;
    bool fleeHasPrev = false;
    bool fleePrevClamped = false;
    float fleeDuration = 0.0f;
    float fleeSampleTimer = 0.0f;
    float fleeMaxHome = 0.0f;
    int fleeSamples = 0;
    int fleeAway = 0;
    int fleeToward = 0;
    int fleeBoundary = 0;
    p2otakaramove::Vec2 fleePrevPos{0.0f, 0.0f};
    p2otakaramove::Vec2 fleePrevThreat{0.0f, 0.0f};
    int species = p2dweevil::FireId;
    p2dweevil::Stimulus stimulus = p2dweevil::StimFire;
    float life = 150.0f;
    float attack = 10.0f;
    std::set<int> firedEvents;
    std::string clip = "wait1";
    float phase = 0.0f;
    float prevHealth = 0.0f;
    bool deadLogged = false;
    float logTimer = 0.0f;
    std::string lastInteraction = "unknown";
    std::string lastAttacker = "none";
    unsigned generator = 0;
    bool deathSeamLogged = false;
    bool bombDetonated = false;
    // P2_OTAKARA_PRESS once-per-press gate (pc_p2_otakara_press_policy.h).
    const void* lastPresser = nullptr;
    float sincePress = 1.0e6f;
    unsigned pressCount = 0;
};

std::map<PelletView*, Otakara> actors;
std::map<std::string, Clip> clips;
bool ready = false;

unsigned genOf(const BTeki* actor) { return actor && actor->mGenerator ? pc_p2_campaign_token(actor) : 0u; }

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

p2otakaramove::Vec2 v2(const Vector3f& v) { return p2otakaramove::Vec2{v.x, v.z}; }

// isMovePositionSet (OtakaraBase.cpp:361-389) for a creature target: select the
// threat with getNearestPikminOrNavi semantics (p2otakaramove::selectThreat), then
// store the escape (59-62) or chase (93) destination in s.target. No treasure is
// staged, so the treasure branch never applies at runtime. Also refreshes
// s.stuckCount (mStuckPikminCount) for isStartFlick. Returns hasTarget.
bool updateDestination(BTeki* actor, Otakara& s, const Vector3f& pos) {
    static std::vector<p2otakaramove::Candidate> cands;
    cands.clear();
    int stuck = 0;
    if (naviMgr) {
        Iterator it(naviMgr);
        CI_LOOP(it) {
            Navi* n = static_cast<Navi*>(*it);
            if (!n) continue;
            cands.push_back({v2(n->getPosition()), true, n->isAlive() != 0, false, false});
        }
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p) continue;
            const bool stuckToSelf = p->getStickObject() == static_cast<Creature*>(actor);
            if (stuckToSelf && p->isAlive()) ++stuck;
            cands.push_back({v2(p->getPosition()), false, p->isAlive() != 0, stuckToSelf, p->isStickToMouth() != 0});
        }
    }
    s.stuckCount = stuck;
    const int pick = p2otakaramove::selectThreat(cands.data(), int(cands.size()), v2(pos), SIGHT);
    s.threatValid = pick >= 0;
    s.destClamped = false;
    if (!s.threatValid) {
        s.target.set(pos);
        return false;
    }
    s.threatIsNavi = cands[pick].isNavi;
    s.threatPos = cands[pick].pos;
    const p2otakaramove::Mode mode =
        s.species == p2dweevil::BombId ? p2otakaramove::Mode::Pursue : p2otakaramove::Mode::Escape;
    const p2otakaramove::Vec2 dest =
        p2otakaramove::movePosition(mode, p2otakaramove::TargetKind::Creature, v2(pos), cands[pick].pos, v2(s.home),
                                    speciesMoveSpeed(s.species), TERRITORY, &s.destClamped);
    s.target.set(dest.x, pos.y, dest.z);
    return true;
}

bool facingDest(const Otakara& s, const Vector3f& pos) {
    return p2otakaramove::facingWithinGate(s.heading, v2(pos), v2(s.target));
}

State fromSt(p2otakaramove::St st) {
    switch (st) {
    case p2otakaramove::St::Dead: return OTA_DEAD;
    case p2otakaramove::St::Flick: return OTA_FLICK;
    case p2otakaramove::St::Wait: return OTA_WAIT;
    case p2otakaramove::St::Move: return OTA_MOVE;
    case p2otakaramove::St::Turn: return OTA_TURN;
    }
    return OTA_WAIT;
}
const char* clipFor(State s) {
    switch (s) {
    case OTA_DEAD: return "dead";
    case OTA_FLICK: return "attack1";
    case OTA_MOVE: return "move1";
    case OTA_TURN: return "pivot1";
    default: return "wait1";
    }
}
bool fleeing(State s) { return s == OTA_MOVE || s == OTA_TURN; }
const char* modeName(const Otakara& s) { return s.species == p2dweevil::BombId ? "pursue" : "escape"; }

// P2_OTAKARA_MOVE_DECISION: on a transition into Move/Turn and at most 1 Hz in Move.
void logDecision(const Otakara& s, const Vector3f& pos) {
    const float threatDist = p2otakaramove::distXZ(v2(pos), s.threatPos);
    const int away = p2otakaramove::distXZ(v2(s.target), s.threatPos) > threatDist ? 1 : 0;
    std::printf("P2_OTAKARA_MOVE_DECISION generator=%u source_id=%d state=%s mode=%s threat=%s "
                "threat_dist=%.1f self=%.1f,%.1f threat=%.1f,%.1f dest=%.1f,%.1f dest_home_dist=%.1f "
                "territory=%.0f clamped=%d away=%d\n",
                s.generator, s.species, stateName(s.state), modeName(s), s.threatIsNavi ? "navi" : "piki",
                threatDist, pos.x, pos.z, s.threatPos.x, s.threatPos.z, s.target.x, s.target.z,
                distXZ(s.target, s.home), TERRITORY, int(s.destClamped), away);
    std::fflush(stdout);
}

// P2_OTAKARA_FLEE_SUMMARY: once per Move/Turn episode.
void endFlee(Otakara& s, const char* end) {
    if (!s.fleeActive) return;
    s.fleeActive = false;
    std::printf("P2_OTAKARA_FLEE_SUMMARY generator=%u source_id=%d mode=%s duration=%.2f samples=%d away=%d "
                "toward=%d boundary=%d max_home_dist=%.1f end=%s\n",
                s.generator, s.species, modeName(s), s.fleeDuration, s.fleeSamples, s.fleeAway, s.fleeToward,
                s.fleeBoundary, s.fleeMaxHome, end);
    std::fflush(stdout);
}

// Per-frame episode bookkeeping while in Move/Turn. A sample is taken each 1 s:
// boundary when the destination was clamped at either end, else away/toward by the
// sign of dot(pos_now - pos_prev, pos_prev - threat_prev); a displacement under one
// unit (turning in place) counts only toward samples.
void trackFlee(Otakara& s, const Vector3f& pos, float dt) {
    if (!s.fleeActive) return;
    s.fleeDuration += dt;
    const float homeDist = distXZ(pos, s.home);
    if (homeDist > s.fleeMaxHome) s.fleeMaxHome = homeDist;
    if (!s.fleeHasPrev) {
        if (!s.threatValid) return;
        s.fleeHasPrev = true;
        s.fleePrevPos = v2(pos);
        s.fleePrevThreat = s.threatPos;
        s.fleePrevClamped = s.destClamped;
        s.fleeSampleTimer = 0.0f;
        return;
    }
    s.fleeSampleTimer += dt;
    if (s.fleeSampleTimer < 1.0f) return;
    s.fleeSampleTimer = 0.0f;
    ++s.fleeSamples;
    const float dx = pos.x - s.fleePrevPos.x, dz = pos.z - s.fleePrevPos.z;
    const float ax = s.fleePrevPos.x - s.fleePrevThreat.x, az = s.fleePrevPos.z - s.fleePrevThreat.z;
    const float dot = dx * ax + dz * az;
    if (s.fleePrevClamped || s.destClamped) {
        ++s.fleeBoundary;
    } else if (dx * dx + dz * dz >= 1.0f) {
        if (dot > 0.0f) ++s.fleeAway;
        else ++s.fleeToward;
    }
    s.fleePrevPos = v2(pos);
    if (s.threatValid) s.fleePrevThreat = s.threatPos;
    s.fleePrevClamped = s.destClamped;
}

// The receiver decides immunity; this mirrors the receiver's own lane-11 matrix
// so the emitter can log the immune/rejected case distinctly and never deliver an
// interaction the receiver would swallow.
bool dweevilAccepts(const Piki* p, p2dweevil::Stimulus stim) {
    if (!p || !p->isAlive()) return false;
    const int species = pc_p2_species(p);
    switch (stim) {
    case p2dweevil::StimFire: return !p2_species_immune(species, P2HazardFire);
    case p2dweevil::StimBubble: return !p2_species_immune(species, P2HazardWater);
    case p2dweevil::StimGas: return p2_emitter_accepts(species, P2HazardGas, p->gasInvicible());
    case p2dweevil::StimDenki: return p2_emitter_accepts(species, P2HazardElectric, p->gasInvicible());
    default: return false;
    }
}

// Volatile Dweevil (93) OWN blast (inst3-misc): source BombOtakara carries a
// Bomb and detonates it on damage/earthquake/death (BombOtakara.cpp
// damageCallBack/earthquakeCallBack/bombCallBack -> forceBomb). Lane-20 pinned
// retail values: radius 90 fp22, teki 500 fp01, navi/piki 10 fp24,
// half-height 50 fp02. Routed through the shared bombsarai blast primitive on
// the live carrier's own BTeki tick (not the preview sidecar stepper).
class OtakaraBlastOwner : public Creature {
public:
    OtakaraBlastOwner() : Creature(nullptr) { mHealth = 1.0f; }
    void refresh(Graphics&) override {}
    void doKill() override {}
};
static OtakaraBlastOwner sBlastOwner;

constexpr float kBombBlastRadius = 90.0f;
constexpr float kBombBlastHalfHeight = 50.0f;
constexpr float kBombTekiDamage = 500.0f;
constexpr float kBombNavPikiDamage = 10.0f;

void applyBombBlast(BTeki* a, Otakara& s, const char* trigger) {
    const Vector3f pos = a->getPosition();
    const unsigned generator = genOf(a);
    P2BombSaraiBlastEvent event;
    event.center = P2BombSaraiVec3{pos.x, pos.y, pos.z};
    event.radius = kBombBlastRadius;
    event.halfHeight = kBombBlastHalfHeight;
    event.tekiDamage = kBombTekiDamage;
    event.naviPikiDamage = kBombNavPikiDamage;
    event.hasCarrier = false;
    event.carrierValid = false;
    std::vector<P2BombSaraiReceiver> receivers;
    std::vector<Creature*> actorsList;
    auto addReceiver = [&](Creature* creature, P2BombSaraiReceiverKind kind) {
        if (!creature || !creature->isAlive()) return;
        const Vector3f& p = creature->getPosition();
        P2BombSaraiReceiver r;
        r.id = receivers.size();
        r.position = P2BombSaraiVec3{p.x, p.y, p.z};
        r.kind = kind;
        r.alive = true;
        r.grounded = true;
        receivers.push_back(r);
        actorsList.push_back(creature);
    };
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) { addReceiver(static_cast<Creature*>(static_cast<Piki*>(*it)), P2BombSaraiReceiverKind::Piki); }
    }
    for (Navi* navi : pc_p2_navis()) {
        addReceiver(static_cast<Creature*>(navi), P2BombSaraiReceiverKind::Navi);
    }
    if (receivers.empty()) {
        std::printf("P2_BOMBOTAKARA_BLAST generator=%u payload=93 center=%.3f,%.3f,%.3f radius=%.1f "
                    "receivers=0 hits=0 pikmin_hits=0 trigger=%s shared_primitive=1 carrier_tick=1\n",
                    generator, pos.x, pos.y, pos.z, kBombBlastRadius, trigger);
        std::fflush(stdout);
        return;
    }
    std::vector<P2BombSaraiRoutedHit> hits(receivers.size());
    const int routed = p2_bombsarai_route_blast(event, receivers.data(), int(receivers.size()), hits.data(),
                                                int(hits.size()));
    if (routed < 0) {
        std::printf("P2_BOMBOTAKARA_BLAST_BLOCKED generator=%u trigger=%s reason=invalid_blast\n",
                    generator, trigger);
        return;
    }
    int pikminHits = 0;
    sBlastOwner.mSRT.t.set(pos.x, pos.y, pos.z);
    for (int i = 0; i < routed; ++i) {
        const P2BombSaraiRoutedHit& hit = hits[i];
        if (hit.receiverId >= actorsList.size() || !actorsList[hit.receiverId]) continue;
        InteractBomb bomb(&sBlastOwner, hit.damage, nullptr);
        actorsList[hit.receiverId]->stimulate(bomb);
        if (hit.kind == P2BombSaraiReceiverKind::Piki) ++pikminHits;
    }
    std::printf("P2_BOMBOTAKARA_BLAST generator=%u payload=93 center=%.3f,%.3f,%.3f radius=%.1f receivers=%d "
                "hits=%d pikmin_hits=%d teki_damage=%.1f navi_piki_damage=%.1f shared_primitive=1 carrier_tick=1 "
                "trigger=%s\n",
                generator, pos.x, pos.y, pos.z, kBombBlastRadius, int(receivers.size()), routed,
                pikminHits, kBombTekiDamage, kBombNavPikiDamage, trigger);
    std::fflush(stdout);
}

void doDischarge(BTeki* a, Otakara& s) {
    if (s.stimulus == p2dweevil::StimNone) {
        // BombOtakara (93) OWN: Flick discharge event detonates the carried
        // Bomb on this actor's own tick (source BombOtakara damage->forceBomb
        // path, decided here by the P2 carrier FSM, not delegated).
        if (!s.bombDetonated) {
            s.bombDetonated = true;
            applyBombBlast(a, s, "flick");
        } else {
            std::printf("P2_BOMBOTAKARA_DETONATE_SUPPRESSED generator=%u payload=93 trigger=flick detonated=0 "
                        "already_detonated=1\n", genOf(a));
            std::fflush(stdout);
        }
        std::printf("P2_OTAKARA_DISCHARGE generator=%u source_id=%d stimulus=bomb trigger=flick carrier_tick=1\n",
                    genOf(a), s.species);
        std::fflush(stdout);
        return;
    }
    if (!pikiMgr) return;
    const Vector3f pos = a->getPosition();
    const unsigned generator = genOf(a);
    int applied = 0, immune = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        if (distXZ(p->getPosition(), pos) >= HIT_RANGE) continue;
        const int species = pc_p2_species(p);
        if (!dweevilAccepts(p, s.stimulus)) {
            ++immune;
            std::printf("P2_OTAKARA_DISCHARGE_IMMUNE generator=%u source_id=%d pikmin=%d colour=%s "
                        "stimulus=%s\n",
                        generator, s.species, species, colorName(p->mColor),
                        p2dweevil::stimulusName(s.stimulus));
            continue;
        }
        bool accepted = false;
        switch (s.stimulus) {
        case p2dweevil::StimFire:
            accepted = p->stimulate(InteractFire(a, s.attack));
            break;
        case p2dweevil::StimBubble:
            accepted = p->stimulate(InteractBubble(a, s.attack));
            break;
        case p2dweevil::StimGas:
            accepted = p->stimulate(InteractGas(a, s.attack));
            break;
        case p2dweevil::StimDenki: {
            Vector3f dir(p->getPosition().x - pos.x, 0.0f, p->getPosition().z - pos.z);
            accepted = p->stimulate(InteractDenki(a, s.attack, &dir));
            break;
        }
        default:
            break;
        }
        ++applied;
        std::printf("P2_OTAKARA_DISCHARGE_HIT generator=%u source_id=%d pikmin=%d colour=%s "
                    "stimulus=%s accepted=%d target_state=%d(%s)\n",
                    generator, s.species, species, colorName(p->mColor),
                    p2dweevil::stimulusName(s.stimulus), int(accepted), p->getState(),
                    p->getState() == PIKISTATE_DenkiDying ? "DenkiDying"
                    : p->getState() == PIKISTATE_Fired ? "Fired"
                    : p->getState() == PIKISTATE_Panic ? "Panic" : "other");
        std::fflush(stdout);
    }
    std::printf("P2_OTAKARA_DISCHARGE generator=%u source_id=%d stimulus=%s applied=%d immune=%d\n",
                generator, s.species, p2dweevil::stimulusName(s.stimulus), applied, immune);
    pc_p2_otakara_fx_on_discharge(s.species, pos.x, pos.y, pos.z);
    std::fflush(stdout);
}

void doFlick(BTeki* a) {
    if (!pikiMgr) return;
    const Vector3f pos = a->getPosition();
    int flicked = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p && p->isAlive() && distXZ(p->getPosition(), pos) < HIT_RANGE) {
            if (p->stimulate(InteractFlick(a, 120.0f, 0.0f, a->getDirection()))) ++flicked;
        }
    }
    if (flicked) std::printf("P2_OTAKARA_FLICK generator=%u flicked=%d\n", genOf(a), flicked);
}

void enter(Otakara& s, State state, const char* clip, float timer = 0.0f) {
    if (fleeing(s.state) && !fleeing(state)) {
        endFlee(s, state == OTA_FLICK ? "flick" : state == OTA_DEAD ? "dead" : "wait");
    }
    if (fleeing(state) && !s.fleeActive) {
        s.fleeActive = true;
        s.fleeHasPrev = false;
        s.fleePrevClamped = false;
        s.fleeDuration = 0.0f;
        s.fleeSampleTimer = 0.0f;
        s.fleeMaxHome = 0.0f;
        s.fleeSamples = s.fleeAway = s.fleeToward = s.fleeBoundary = 0;
    }
    s.pending = OTA_INVALID;
    s.decisionLogTimer = 0.0f;
    s.flickTriggerLogged = false;
    s.flickEventFired = false;
    if (state == OTA_WAIT) s.bombFuse = 0.0f; // StateBombWait::init (OtakaraBaseState.cpp:748)
    s.state = state;
    s.stateTime = 0.0f;
    s.timer = timer;
    s.firedEvents.clear();
    if (clip) s.clip = clip;
}

// Commit the pending source mNextState when the looped clip reaches its end
// (finishMotion -> KEYEVENT_END, OtakaraBaseState.cpp:196-198/266-268).
void commitPending(BTeki* a, Otakara& s, const Vector3f& pos, float prevStateTime) {
    if (s.pending == OTA_INVALID || s.pending == s.state) return;
    if (!p2otakaramove::clipEndCrossed(prevStateTime, s.stateTime, clipDuration(s.clip))) return;
    const State next = s.pending;
    std::printf("P2_OTAKARA_STATE generator=%u state=%s\n", genOf(a), stateName(next));
    enter(s, next, clipFor(next));
    if (fleeing(next)) logDecision(s, pos);
}

// EnemyFunc::isStartFlick(ota, false) (enemyAction.cpp:1209-1244) on the port
// counters; logs P2_OTAKARA_FLICK_TRIGGER once per state when it first holds.
bool flickRequested(Otakara& s, unsigned generator) {
    if (!p2otakaramove::isStartFlick(s.flickTimer, s.stuckCount)) return false;
    if (!s.flickTriggerLogged) {
        s.flickTriggerLogged = true;
        std::printf("P2_OTAKARA_FLICK_TRIGGER generator=%u source_id=%d state=%s hits=%.0f stuck=%d\n", generator,
                    s.species, stateName(s.state), s.flickTimer, s.stuckCount);
        std::fflush(stdout);
    }
    return true;
}

// Obj::stimulateBomb (OtakaraBase.cpp:699-707) for BombOtakara (93) while chasing
// (StateBombMove/StateBombTurn call it every frame, OtakaraBaseState.cpp:821/885).
void bombFuseTick(BTeki* a, Otakara& s, float dt) {
    if (s.species != p2dweevil::BombId || s.bombDetonated) return;
    if (!p2otakaramove::bombFuseStep(s.bombFuse, dt)) return;
    s.bombDetonated = true;
    std::printf("P2_BOMBOTAKARA_FUSE generator=%u payload=93 chase=%.2f\n", genOf(a), s.bombFuse);
    std::fflush(stdout);
    applyBombBlast(a, s, "fuse");
}

void fireEvents(BTeki* a, Otakara& s) {
    auto it = clips.find(s.clip);
    if (it == clips.end()) return;
    for (const auto& event : it->second.events) {
        if (s.firedEvents.count(event.first)) continue;
        if (s.stateTime < event.first / 30.0f) continue;
        s.firedEvents.insert(event.first);
        if (s.state == OTA_FLICK && event.second == 2) {
            doFlick(a);
            s.flickTimer = 0.0f; // OtakaraBaseState.cpp:107
            s.flickEventFired = true;
        } else if (s.state == OTA_FLICK && event.second == 3) {
            doDischarge(a, s);
        }
    }
}

void setPhase(Otakara& s) {
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
} // namespace

void pc_p2_otakara_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}

void pc_p2_otakara_forget(BTeki* actor) {
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    const unsigned generator = it->second.generator;
    endFlee(it->second, "forget");
    actors.erase(it);
    // lane-07 seam (pc_p2_forget_teki in BTeki::doKill / slot reuse): report the
    // registration actually dropping (count after the erase). This marker is
    // computed from the live map; the fixture's P2_OTAKARA_SEAM_OBSERVED is the
    // authoritative zero-registration probe.
    const unsigned long after = (unsigned long)actors.size();
    std::printf("P2_OTAKARA_FORGET generator=%u registered=1 count=%lu\n", generator, after);
    std::fflush(stdout);
}

void pc_p2_otakara_died(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end() || it->second.deathSeamLogged) return;
    it->second.deathSeamLogged = true;
    // Host death seam (BTeki::die, mDeadState transition), distinct from the
    // module's P2_OTAKARA_MODULE_DEAD observation on mHealth<=0.
    std::printf("P2_OTAKARA_DEAD generator=%u source_id=%d mDeadState=1\n",
                it->second.generator, it->second.species);
    std::fflush(stdout);
}

bool pc_p2_otakara_receipt(PelletView* view, unsigned& generator) {
    if (!view || !ready) return false;
    auto it = actors.find(view);
    if (it == actors.end()) return false;
    generator = it->second.generator;
    return true;
}

void pc_p2_otakara_attack(BTeki* actor, Creature* owner, const char* interaction) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Otakara& s = it->second;
    // Source damageCallBack -> damageTreasure -> addDamage(damage, 1.0f)
    // (OtakaraBase.cpp:190-195, 563-574): each damage receipt adds 1 to mFlickTimer.
    s.flickTimer += 1.0f;
    s.hitSinceDrop = true;
    s.lastInteraction = interaction && *interaction ? interaction : "InteractAttack";
    if (owner && owner->isPiki()) {
        s.lastAttacker = colorName(static_cast<Piki*>(owner)->mColor);
    } else if (owner) {
        s.lastAttacker = "creature";
    } else {
        s.lastAttacker = "none";
    }
}

namespace {
const char* presserName(Creature* presser) {
    if (!presser) return "none";
    if (presser->isPiki()) return colorName(static_cast<Piki*>(presser)->mColor);
    if (presser->mObjType == OBJTYPE_Navi) return "navi";
    if (presser->mObjType == OBJTYPE_Teki) return "teki";
    return "creature";
}

// Shared body of the two host squash intercepts. The source decision
// (pc_p2_otakara_press_policy.h) consumes the press with no damage, no
// addDamage/mFlickTimer tick and no BombOtakara forceBomb; the presser Pikmin
// keeps its own P1 flying-collision path (pikiState.cpp:2205-2240: startStick +
// PikiAction::Attack), matching the P2 latch (pikiState.cpp:2335-2342).
bool interceptPress(BTeki* actor, Creature* presser, p2otakarapress::Path path) {
    if (!ready || !actor) return false;
    auto it = actors.find(static_cast<PelletView*>(actor));
    const bool registered = it != actors.end();
    const p2otakarapress::Decision d = p2otakarapress::decide(registered, path);
    if (!d.consume) return false;
    Otakara& s = it->second;
    if (p2otakarapress::shouldLog(s.lastPresser, s.sincePress, presser)) {
        ++s.pressCount;
        std::printf("P2_OTAKARA_PRESS generator=%u source_id=%d path=%s presser=%s outcome=%s "
                    "damage=%.1f counts_as_hit=%d bomb=%d health=%.1f state=%s press=%u\n",
                    genOf(actor), s.species, p2otakarapress::pathName(path), presserName(presser),
                    d.outcome, d.damage, d.countsAsHit ? 1 : 0, d.detonatesBomb ? 1 : 0,
                    actor->mHealth, stateName(s.state), s.pressCount);
        std::fflush(stdout);
    }
    s.lastPresser = presser;
    s.sincePress = 0.0f;
    return true;
}
} // namespace

bool pc_p2_otakara_pressed(BTeki* actor, Creature* presser) {
    return interceptPress(actor, presser, p2otakarapress::Path::HostPress);
}

bool pc_p2_otakara_smashed(BTeki* actor, Creature* presser) {
    return interceptPress(actor, presser, p2otakarapress::Path::ThrownLanding);
}

unsigned long pc_p2_otakara_count() { return (unsigned long)actors.size(); }
bool pc_p2_otakara_registered(BTeki* actor) {
    return actors.count(static_cast<PelletView*>(actor)) != 0;
}

float pc_p2_otakara_param_f(const BTeki* actor, int idx, float fallback) {
    if (!ready || !actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor)))) return fallback;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (idx == TPF_Life) return it->second.life;
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

bool pc_p2_otakara_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

static int speciesFromName(const std::string& name) {
    if (name == "FireOtakara") return p2dweevil::FireId;
    if (name == "WaterOtakara") return p2dweevil::WaterId;
    if (name == "GasOtakara") return p2dweevil::GasId;
    if (name == "ElecOtakara") return p2dweevil::ElecId;
    if (name == "BombOtakara") return p2dweevil::BombId;
    return -1; // unknown species left to the other paths
}

static int speciesFromSource(unsigned source) {
    switch (source) {
    case 59: return p2dweevil::FireId;
    case 60: return p2dweevil::WaterId;
    case 61: return p2dweevil::GasId;
    case 62: return p2dweevil::ElecId;
    case 93: return p2dweevil::BombId;
    default: return -1;
    }
}

static void loadBank() {
    if (!clips.empty()) return;
    // Shared OtakaraBase clip bank (one bank aliased across the dweevil species).
    std::ifstream bank("p2-dweevil-bank.txt");
    if (!bank) return;
    std::string token;
    if (!(bank >> token) || token != "P2_DWEEVIL_BANK_1") return;
    while (bank >> token) {
        if (token == "species") {
            std::string species, id;
            bank >> species >> id;
        } else if (token == "clip") {
            std::string species, name, events, marker, status;
            long long frames = 0;
            int poses = 0;
            bank >> species >> name >> frames >> events >> marker >> poses >> status;
            if (clips.count(name) == 0) {
                Clip clip;
                clip.name = name;
                clip.duration = frames > 0 ? float(frames) / 30.0f : 1.0f;
                clip.loop = (name == "wait1" || name == "move1" || name == "pivot1"
                             || name == "wait2" || name == "move2" || name == "pivot2"
                             || name == "carry");
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

static bool registerActor(BTeki* actor, int species, unsigned generator) {
    if (!actor || species < 0) return false;
    Otakara& s = actors[static_cast<PelletView*>(actor)];
    s = Otakara();
    s.species = species;
    s.stimulus = p2dweevil::stimulusFor(s.species);
    s.life = speciesLife(s.species);
    s.attack = speciesAttack(s.species);
    s.generator = generator;
    s.home = actor->getPosition();
    s.target = s.home;
    s.heading = actor->getDirection();
    actor->mHealth = s.life;
    s.prevHealth = s.life;
    enter(s, OTA_WAIT, "wait1");
    std::printf("P2_OTAKARA_BIND generator=%u source_id=%d stimulus=%s visual_only=0\n",
                generator, s.species, p2dweevil::stimulusName(s.stimulus));
    // bot-deliver (#871): lane-06 ordinary-delivery source bind so
    // GoalItem::suckMe grants onion:p2:<59-62> instead of the P1 bestiary
    // CHECK. Mirrors Sokkuri/ElecBug/Sarai and proxy batch2. Single-use:
    // consumed on delivery, cleared on forget/recycle. Species id equals
    // source id for 59-62 (p2dweevil::FireId etc).
    pc_randomizer_p2_bind_source(static_cast<PelletView*>(actor), (unsigned)s.species, generator);
    std::printf("P2_OTAKARA_DELIVERY_BIND generator=%u source_id=%d\n", generator, s.species);
    std::fflush(stdout);
    const Vector3f pos = actor->getPosition();
    std::printf("P2_ENEMY_READY species=%s native_family=Chappy generator=%u "
                "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                "source_FSM=implemented attack=%s\n",
                p2dweevil::speciesName(s.species), generator, pos.x, pos.y,
                pos.z, actor->mHealth, s.life,
                s.stimulus == p2dweevil::StimNone ? "payload_delegated" : "elemental_discharge");
    return true;
}

void pc_p2_otakara_setup() {
    pc_p2_otakara_reset();
    if (!tekiMgr) return;
    loadBank();

    std::map<unsigned, int> wanted;
    std::ifstream in("p2-dweevil-actors.txt");
    if (!in) return;
    std::string header;
    int count = 0;
    if (!(in >> header >> count) || header != "P2_DWEEVIL_ACTORS_1" || count < 1) return;
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        std::string species;
        if (!(in >> generator >> species)) return;
        const int sid = speciesFromName(species);
        if (sid >= 0) wanted[unsigned(generator)] = sid;
    }
    if (pc_randomizer_p2_bridge()) {
        wanted.clear();
        for (unsigned source=59; source<=62; ++source)
            for (unsigned id : pc_p2_campaign_ids(source)) wanted[id] = speciesFromSource(source);
        for (unsigned id : pc_p2_campaign_ids(93)) wanted[id] = speciesFromSource(93);
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
            std::printf("P2_OTAKARA_ERROR native_type generator=%u\n", pc_p2_campaign_token(actor));
            if (pc_p2_setup_skip(pc_randomizer_p2_bridge(), "Otakara", "actor_type_mismatch")) return;
        }
        registerActor(actor, match->second, pc_p2_campaign_token(actor));
        if (match->second == p2dweevil::BombId) {
            // Ordinary-delivery bridge for the Volatile Dweevil carrier
            // (lane 06 contract, mirrors Catfish 26): bind source 93 so
            // GoalItem::suckMe can grant onion:p2:93 exactly once. The
            // element itself stays delegated to the carried Bomb payload.
            pc_randomizer_p2_bind_source(static_cast<PelletView*>(actor), 93,
                                         pc_p2_campaign_token(actor));
            std::printf("P2_BOMBOTAKARA_DELIVERY_BIND generator=%u source_id=93\n",
                        pc_p2_campaign_token(actor));
            std::fflush(stdout);
        }
        found.insert(pc_p2_campaign_token(actor));
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_OTAKARA_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        if (pc_p2_setup_skip(pc_randomizer_p2_bridge(), "Otakara", "actor_roster_incomplete")) return;
    }
    ready = true;
}

bool pc_p2_otakara_bind_dynamic(BTeki* actor, unsigned generatorId, unsigned sourceId) {
    const int species = speciesFromSource(sourceId);
    // wf7 dweevil-impl (#871): reject a zero generator id. At birth time the
    // newborn BTeki has no mGenerator yet, so the caller's token reads 0; the
    // caller must pass the seed uid instead. Accepting 0 here created a bogus
    // generator=0 registration later overwritten by setup (double-claim
    // window, one actor briefly animated under two identities).
    if (!actor || !generatorId || species < 0 || actors.count(static_cast<PelletView*>(actor))) return false;
    loadBank();
    if (!registerActor(actor, species, generatorId)) return false;
    ready = true;
    std::printf("P2_OTAKARA_BIND_DYNAMIC source_id=%u generator=%u\n", sourceId, generatorId);
    std::fflush(stdout);
    return true;
}

void pc_p2_otakara_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    // Headless staged death hook (wf7 dweevil-impl, #871): env-gated,
    // clearly labelled STAGED. With PIKMIN_P2_DWEEVIL_STAGED_DEATH=1 the first
    // updated dweevil is killed after ~300 updates, so headless can prove the
    // corpse holds clip=dead. Off by default; no effect on owner play.
    // wf7-d-1 showed mHealth=0 alone never reaches BTeki::die() headless (no
    // combat, so the P1 Chappy TAI never picks its dying branch): the module
    // went state=dead clip=dead but no P2_OTAKARA_DEAD (mDeadState) line and
    // no corpse draw ever appeared. So the hook also enters the host's own
    // natural death funnel via die() (the same call the TAI makes), letting
    // dieSoon()->becomePellet() form the real carriable corpse.
    // wf7-d-2 showed die() alone still strands the host at mDeadState=1
    // headless (the dormant actor's doAI tail never runs dieSoon()), so the
    // staged step uses the public pcEscapeNow() lane helper (#219: die() plus
    // the dieSoon() a dormant doAI would run), forming the real pellet corpse
    // through the unchanged natural funnel.
    {
        static bool stagedArmed = false;
        static bool stagedChecked = false;
        static bool stagedDone = false;
        static unsigned long stagedTicks = 0;
        if (!stagedChecked) {
            stagedChecked = true;
            const char* env = std::getenv("PIKMIN_P2_DWEEVIL_STAGED_DEATH");
            stagedArmed = (env && std::string(env) == "1");
        }
        if (stagedArmed && !stagedDone) {
            ++stagedTicks;
            if (stagedTicks == 300) {
                stagedDone = true;
                actor->mHealth = 0.0f;
                actor->pcEscapeNow();
                std::printf("P2_DWEEVIL_STAGED_DEATH staged=1 generator=%u source_id=%d health=0 corpse=%d\n",
                            it->second.generator, it->second.species, int(actor->mPellet != nullptr));
                std::fflush(stdout);
            }
        }
    }
    Otakara& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    s.sincePress += dt;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = genOf(actor);

    // Damage receipt observation (queue-then-apply, docs/PIKMIN2_RECEIVER_PATHS.md):
    // the host TAI applies mStoredDamage inside makeDamaged; this logs the drop
    // independent of the injected fixture trigger, so natural pre-injection combat
    // is observable as a positive delta.
    if (s.prevHealth - actor->mHealth > 0.5f) {
        std::printf("P2_OTAKARA_HIT generator=%u source_id=%d health=%.1f->%.1f delta=%.1f "
                    "interaction=%s attacker=%s\n",
                    generator, s.species, s.prevHealth, actor->mHealth,
                    s.prevHealth - actor->mHealth, s.lastInteraction.c_str(), s.lastAttacker.c_str());
        std::fflush(stdout);
        // A drop with no InteractAttack receipt behind it (bomb, fire, ...) still
        // went through a source damage callback -> addDamage: count it once.
        if (!s.hitSinceDrop) s.flickTimer += 1.0f;
        s.hitSinceDrop = false;
        // Attribution is per drop: clear it so a later non-Attack drop is not mislabelled.
        s.lastInteraction = "unknown";
        s.lastAttacker = "none";
        // Source BombOtakara damage->forceBomb path (BombOtakara.cpp
        // damageCallBack/hipdropCallBack/bombCallBack): any damage detonates
        // the carried Bomb on this actor's own tick. P2-decided attack.
        if (s.species == p2dweevil::BombId && !s.bombDetonated) {
            s.bombDetonated = true;
            applyBombBlast(actor, s, "damage");
        }
    }
    s.prevHealth = actor->mHealth;

    if (actor->mHealth <= 0.0f && s.state != OTA_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_OTAKARA_MODULE_DEAD generator=%u source_id=%d health=0\n", generator, s.species);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        // Source death detonates the carried Bomb (damageCallBack path).
        if (s.species == p2dweevil::BombId && !s.bombDetonated) {
            s.bombDetonated = true;
            applyBombBlast(actor, s, "death");
        }
        enter(s, OTA_DEAD, "dead");
    }

    const float prevStateTime = s.stateTime;
    s.stateTime += dt;
    switch (s.state) {
    case OTA_WAIT: {
        // Source StateWait::exec (OtakaraBaseState.cpp:165-199): no idle transition;
        // the move decision, then isStartFlick, commit at the wait1 clip end.
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        actor->mVelocity.x = 0.0f;
        actor->mVelocity.z = 0.0f;
        s.clip = "wait1";
        const bool hasTarget = updateDestination(actor, s, pos);
        const bool flick = flickRequested(s, generator);
        const State next = fromSt(p2otakaramove::decide(
            {p2otakaramove::St::Wait, hasTarget, hasTarget && facingDest(s, pos), flick, false}));
        if (next != OTA_WAIT) s.pending = next;
        commitPending(actor, s, pos, prevStateTime);
        break;
    }
    case OTA_MOVE: {
        // Source StateMove::exec (OtakaraBaseState.cpp:225-269): recompute the
        // destination every frame; walkToTarget while within THIRD_PI, else stop.
        // A pending Flick zeroes the velocity (mTargetVelocity = 0, :252-256).
        bombFuseTick(actor, s, dt);
        const bool hasTarget = updateDestination(actor, s, pos);
        const bool facing = hasTarget && facingDest(s, pos);
        const bool flick = flickRequested(s, generator);
        if (facing && !flick) {
            s.heading = p2otakaramove::turnStep(s.heading, v2(pos), v2(s.target), dt);
            actor->setDirection(s.heading);
            const Vector3f drive(std::sin(s.heading) * speciesMoveSpeed(s.species), 0.0f,
                                 std::cos(s.heading) * speciesMoveSpeed(s.species));
            actor->inputDrive(drive);
            actor->mVelocity.set(drive);
        } else {
            actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
            actor->mVelocity.x = 0.0f;
            actor->mVelocity.z = 0.0f;
        }
        const State next =
            fromSt(p2otakaramove::decide({p2otakaramove::St::Move, hasTarget, facing, flick, false}));
        if (next != OTA_MOVE) s.pending = next;
        trackFlee(s, pos, dt);
        s.decisionLogTimer += dt;
        if (hasTarget && s.decisionLogTimer >= 1.0f) {
            s.decisionLogTimer = 0.0f;
            logDecision(s, pos);
        }
        commitPending(actor, s, pos, prevStateTime);
        break;
    }
    case OTA_TURN: {
        // Source StateTurn::exec (OtakaraBaseState.cpp:297-334): turnToTarget toward
        // the destination; Move once the pre-turn angle is within THIRD_PI.
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        actor->mVelocity.x = 0.0f;
        actor->mVelocity.z = 0.0f;
        bombFuseTick(actor, s, dt);
        const bool hasTarget = updateDestination(actor, s, pos);
        const bool facing = hasTarget && facingDest(s, pos);
        if (hasTarget) {
            s.heading = p2otakaramove::turnStep(s.heading, v2(pos), v2(s.target), dt);
            actor->setDirection(s.heading);
        }
        const bool flick = flickRequested(s, generator);
        const State next =
            fromSt(p2otakaramove::decide({p2otakaramove::St::Turn, hasTarget, facing, flick, false}));
        if (next != OTA_TURN) s.pending = next;
        trackFlee(s, pos, dt);
        commitPending(actor, s, pos, prevStateTime);
        break;
    }
    case OTA_FLICK:
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        actor->mVelocity.x = 0.0f;
        actor->mVelocity.z = 0.0f;
        if (s.stateTime >= clipDuration("attack1")) {
            // Port guard: a bank whose attack1 lacks event 2 must not re-trigger the
            // Flick forever, so the counter still resets once per Flick.
            if (!s.flickEventFired) s.flickTimer = 0.0f;
            // Source StateFlick KEYEVENT_END (OtakaraBaseState.cpp:115-133): straight
            // back to Move/Turn while a threat exists, else Wait.
            const bool hasTarget = updateDestination(actor, s, pos);
            const State next = fromSt(p2otakaramove::afterFlick(actor->mHealth <= 0.0f, hasTarget,
                                                                hasTarget && facingDest(s, pos)));
            std::printf("P2_OTAKARA_STATE generator=%u state=%s\n", generator, stateName(next));
            enter(s, next, clipFor(next));
            if (fleeing(next)) logDecision(s, pos);
        }
        break;
    case OTA_DEAD:
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        actor->mVelocity.x = 0.0f;
        actor->mVelocity.z = 0.0f;
        // Host death handoff: the P1 strategy reacts to mHealth<=0 inside
        // BTeki::doAI(), calls die() and then dieSoon()->becomePellet() in the
        // same pass. The module only drives the source dead clip and lets the
        // host complete teardown/corpse (same contract as pc_p2_sokkuri/armor).
        break;
    default:
        break;
    }
    setPhase(s);
    fireEvents(actor, s);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        std::printf("P2_OTAKARA_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z);
        std::fflush(stdout);
    }
}
