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
//   * Dweevil family fidelity pass (owner playtest 2026-09-30, "Dweevil fidelity" issue):
//       - Treasure pickup/carry/drop is implemented (states Take/ItemWait/ItemMove/ItemTurn/
//         ItemFlick/ItemDrop, pc_p2_otakara_item.h). The carried object is a real P1 pellet held
//         through the engine's own InteractSwallow mouth stick on a dedicated 'otak' part; it is a
//         labelled P1 stand-in for the P2 treasure. Damage while carrying goes to the treasure
//         (fp01 otakara life), never to the Dweevil.
//       - Collision is the retail two-sphere tree (root {none}{____} r15 + {body}{st__} r10 on
//         joint 11): the legs carry no part, so nothing sticks to or damages through them, and
//         InteractAttack::actTeki refuses the partless ground forms (pc_p2_otakara_part.h).
//       - The elemental attack has its charge visual at the body during the wind-up, a burst at
//         the Dweevil at the discharge event, the one-second attackTarget() window of
//         OtakaraBase::doUpdateCommon, and every effect generator is stopped (logged START/STOP
//         pairs) on discharge/window end/death/forget (pc_p2_otakara_attack.h).
//       - Move keeps the source horizontal fp06 on slopes (slope gain) and side-steps a stalled
//         Move instead of pushing into a slope (pc_p2_otakara_stall.h).
//     BombOtakara (93) blast is OWN via this carrier FSM (inst3-misc):
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
#include "pc_p2_otakara_fxplan.h"
#include "pc_p2_otakara_move.h"
#include "pc_p2_otakara_item.h"
#include "pc_p2_otakara_attack.h"
#include "pc_p2_otakara_part.h"
#include "pc_p2_otakara_stall.h"
#include "pc_p2_flyer_coll.h"
#include "pc_p2_otakara_press_policy.h"
#include "pc_p2_dweevil_policy.h"
#include "pc_p2_bombsarai_blast.h"
#include "pc_p2_bomb_telegraph.h"
#include "pc_p2_bomb_visual.h"
#include "pc_p2_species.h"
#include "pc_p2_sfx.h"
#include "pc_p2_hazard_emitter.h"
#include "teki.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiState.h"
#include "PikiMgr.h"
#include "Pellet.h"
#include "PelletState.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "EffectMgr.h"
#include "gl/pc_gfx.h"
#include "MapMgr.h"
#include "MapCode.h"
#include "Collision.h"
#include "CreatureCollPart.h"
#include "pc_p2_navi_select.h"
#include "Generator.h"
#include "gameflow.h"
#include "LifeGauge.h"
#include "ItemMgr.h"
#include "Shape.h"
#include "Graphics.h"
#include <cmath>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <vector>

extern Matrix4f invCamMat; // collInfo.cpp: camera inverse used by CollPart::getMatrix

namespace {
// Source StateID values (OtakaraBase.h:22-39).
enum State {
    OTA_INVALID = -1,
    OTA_DEAD = 0,
    OTA_FLICK = 1,
    OTA_WAIT = 2,
    OTA_MOVE = 3,
    OTA_TURN = 4,
    OTA_TAKE = 5,
    OTA_ITEMWAIT = 6,
    OTA_ITEMMOVE = 7,
    OTA_ITEMTURN = 8,
    OTA_ITEMFLICK = 9,
    OTA_ITEMDROP = 10,
};

const char* stateName(State s) {
    switch (s) {
    case OTA_DEAD: return "dead";
    case OTA_FLICK: return "flick";
    case OTA_WAIT: return "wait";
    case OTA_MOVE: return "move";
    case OTA_TURN: return "turn";
    case OTA_TAKE: return "take";
    case OTA_ITEMWAIT: return "itemwait";
    case OTA_ITEMMOVE: return "itemmove";
    case OTA_ITEMTURN: return "itemturn";
    case OTA_ITEMFLICK: return "itemflick";
    case OTA_ITEMDROP: return "itemdrop";
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
constexpr float HIT_RANGE = p2otakaraattack::kRadius; // fp22 attack hit range (disc), Flick radius

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events; // source frame -> event type
};

// One started particle generator of the attack visuals (pc_p2_otakara_fxplan.h).
struct FxGen {
    zen::particleGenerator* gen = nullptr;
    Vector3f pos;   // emit position (followed generators read this every frame)
    Vector3f off;   // offset from the followed anchor (a charge ring sits around the body)
    bool follow = false;
    int effect = -1;
};

struct FxSet {
    FxGen gens[p2otakarafx::kMaxGenerators];
    int count = 0;
    float age = 0.0f;
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
    // Carried Bomb telegraph (pc_p2_bomb_telegraph.h): the Bomb burns for its
    // own life (4.5 s) after it is forced, then blasts 10 frames later.
    p2bombtelegraph::Burn burn;
    const char* burnTrigger = "fuse";
    float heldHealth = 0.0f; // carrier takes no damage while its bomb burns
    P2BombSparks sparks;     // lit-fuse sparks, all killed at the blast
    unsigned liveBaseline = 0;
    float sinceBlast = -1.0f;
    bool cleanLogged = false;
    P2BombGauge gauge;       // the bomb's own countdown wheel (pc_p2_bomb_visual.h)
    int gaugeLogTick = 0;
    // P2_OTAKARA_PRESS once-per-press gate (pc_p2_otakara_press_policy.h).
    const void* lastPresser = nullptr;
    float sincePress = 1.0e6f;
    unsigned pressCount = 0;

    // ---- Dweevil family fidelity pass ----
    // Treasure (pc_p2_otakara_item.h): mTreasure / mTreasureHealth / mTargetCreature /
    // mItemSearchDelayTimer / mBodyHeightOffset.
    p2otakaraitem::Hold hold;
    Pellet* treasure = nullptr;
    Pellet* targetPellet = nullptr;
    bool treasureTarget = false;       // the current destination is a treasure
    float itemSearchTimer = p2otakaraitem::kSearchOpen;
    float bodyOffsetY = 0.0f;
    float pickRadius = 0.0f;
    float attackWaitTimer = 0.0f;
    float carryLog = 0.0f;
    unsigned destFrame = ~0u;          // updateTick of the last isMovePositionSet timer tick
    unsigned updateTick = 0;
    unsigned treasuresTaken = 0;
    unsigned treasuresDropped = 0;
    bool takeLogged = false;
    // Attack window + effects (pc_p2_otakara_attack.h, pc_p2_otakara_fxplan.h).
    float attackTimer = p2otakaraattack::kIdle;
    p2otakaraattack::Ledger fxLedger;
    FxSet chargeFx;
    FxSet dischargeFx;
    std::set<const void*> windowHit;   // targets already logged in this window
    int windowApplied = 0;
    int windowImmune = 0;
    unsigned windowFrames = 0;
    // Collision tree (pc_p2_otakara_part.h) through the #960 P2FlyerColl mechanism.
    P2FlyerColl coll;
    p2flyer::Sphere tree[3];
    bool collTried = false;
    float collRetry = 0.0f;
    unsigned collAttempts = 0;
    unsigned partAccepted = 0;
    unsigned partRefused = 0;
    // Stall detection / slope (pc_p2_otakara_stall.h).
    p2otakarastall::Tracker stall;
    Vector3f prevPos;
    bool prevPosValid = false;
    float moveCommanded = 0.0f;        // fp06 * gain of the last Move tick
    float traceTimer = 0.0f;
    float lastGain = 1.0f;
    // Dev-only staged treasure (PIKMIN_P2_DWEEVIL_STAGE_TREASURE): spawned once when a captain
    // first comes within range.
    bool stageDone = false;
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

// Membership test before any dereference of a remembered pellet (the pellet pool is recycled at
// scene teardown, so a stored pointer can dangle).
bool pelletLive(const Pellet* p) {
    if (!p || !pelletMgr) return false;
    Iterator it(pelletMgr);
    CI_LOOP(it) {
        if (static_cast<Pellet*>(*it) == p) return static_cast<Pellet*>(*it)->isAlive();
    }
    return false;
}

// Source isPickable()/mCaptureMatrix == nullptr for a P1 pellet: a live loose number pellet or
// carcass with nobody carrying it and no Pikmin on it. Ship parts (repair goals) and captains
// are never treasure (same exclusions as the Breadbug cargo snapshot, pc_p2_breadbug_teki.cpp),
// nor is a pellet another Dweevil already holds (mStuckMouthPart).
bool pelletTakeable(const Pellet* p) {
    if (!p || !p->isAlive() || !p->mConfig) return false;
    if (p->isUfoParts() || p->mConfig->mModelId.match('NAVI')) return false;
    if (p->mStuckMouthPart || p->mPikiCarrier || p->mCarrierCounter != 0 || p->mCarrierCount != 0) return false;
    const int st = const_cast<Pellet*>(p)->getState();
    if (st == PELSTATE_Goal || st == PELSTATE_Swallowed || st == PELSTATE_Dead || st == PELSTATE_Appear) return false;
    return const_cast<Pellet*>(p)->isFree();
}

// getNearestTreasure (OtakaraBase.cpp:395-417) over the live pellet pool.
Pellet* findTreasure(const Otakara& s, const Vector3f& pos) {
    if (!pelletMgr) return nullptr;
    static std::vector<p2otakaraitem::Pellet> info;
    static std::vector<Pellet*> who;
    info.clear();
    who.clear();
    Iterator it(pelletMgr);
    CI_LOOP(it) {
        Pellet* p = static_cast<Pellet*>(*it);
        if (!p) continue;
        p2otakaraitem::Pellet q;
        q.pos = v2(p->mSRT.t);
        q.y = p->mSRT.t.y;
        q.pickRadius = p->getBottomRadius();
        q.height = p->getCylinderHeight();
        q.alive = p->isAlive();
        q.captured = p->mStuckMouthPart != nullptr;
        q.pickable = pelletTakeable(p);
        info.push_back(q);
        who.push_back(p);
    }
    const int pick = p2otakaraitem::nearestTreasure(info.data(), int(info.size()), v2(pos), v2(s.home), SIGHT, TERRITORY);
    return pick >= 0 ? who[size_t(pick)] : nullptr;
}

// isMovePositionSet (OtakaraBase.cpp:361-389). `ignoreTreasures` is the item states' flag.
// A treasure (when the pickup delay allows a search) wins over any Pikmin/Navi and stores the
// pellet position; otherwise the creature half stores the escape (59-62) or chase (93)
// destination in s.target. Also refreshes s.stuckCount (mStuckPikminCount) for isStartFlick.
// Returns hasTarget.
bool updateDestination(BTeki* actor, Otakara& s, const Vector3f& pos, bool ignoreTreasures, float dt) {
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

    // Treasure half (species 93 never takes one: BombOtakara runs the Bomb states).
    s.targetPellet = nullptr;
    s.treasureTarget = false;
    if (s.species != p2dweevil::BombId) {
        float step = dt;
        if (s.destFrame == s.updateTick) step = 0.0f; // a second query in the same frame
        s.destFrame = s.updateTick;
        if (p2otakaraitem::searchOpen(s.itemSearchTimer, step, ignoreTreasures)) {
            if (Pellet* target = findTreasure(s, pos)) {
                s.targetPellet = target;
                s.treasureTarget = true;
                s.threatValid = true;
                s.threatIsNavi = false;
                s.destClamped = false;
                s.target.set(target->mSRT.t);
                if (!s.takeLogged) {
                    s.takeLogged = true;
                    std::printf("P2_OTAKARA_TREASURE_TARGET generator=%u source_id=%d pellet=%u x=%.1f y=%.1f z=%.1f "
                                "dist=%.1f pick_radius=%.1f state=%s\n",
                                s.generator, s.species, unsigned((unsigned long long)(size_t)target & 0xFFFFFFu),
                                target->mSRT.t.x, target->mSRT.t.y, target->mSRT.t.z, distXZ(pos, target->mSRT.t),
                                target->getBottomRadius(), stateName(s.state));
                    std::fflush(stdout);
                }
                return true;
            }
        }
    }

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
    case p2otakaramove::St::Take: return OTA_TAKE;
    case p2otakaramove::St::ItemWait: return OTA_ITEMWAIT;
    case p2otakaramove::St::ItemMove: return OTA_ITEMMOVE;
    case p2otakaramove::St::ItemTurn: return OTA_ITEMTURN;
    case p2otakaramove::St::ItemFlick: return OTA_ITEMFLICK;
    case p2otakaramove::St::ItemDrop: return OTA_ITEMDROP;
    }
    return OTA_WAIT;
}
p2otakaramove::St toSt(State s) {
    switch (s) {
    case OTA_DEAD: return p2otakaramove::St::Dead;
    case OTA_FLICK: return p2otakaramove::St::Flick;
    case OTA_MOVE: return p2otakaramove::St::Move;
    case OTA_TURN: return p2otakaramove::St::Turn;
    case OTA_TAKE: return p2otakaramove::St::Take;
    case OTA_ITEMWAIT: return p2otakaramove::St::ItemWait;
    case OTA_ITEMMOVE: return p2otakaramove::St::ItemMove;
    case OTA_ITEMTURN: return p2otakaramove::St::ItemTurn;
    case OTA_ITEMFLICK: return p2otakaramove::St::ItemFlick;
    case OTA_ITEMDROP: return p2otakaramove::St::ItemDrop;
    default: return p2otakaramove::St::Wait;
    }
}
// Bank clip per state (OtakaraBase.h AnimID; OtakaraBaseState.cpp startMotion calls).
const char* clipFor(State s) {
    switch (s) {
    case OTA_DEAD: return "dead";
    case OTA_FLICK: return "attack1";
    case OTA_MOVE: return "move1";
    case OTA_TURN: return "pivot1";
    case OTA_TAKE: return "takeitem";
    case OTA_ITEMWAIT: return "wait2";
    case OTA_ITEMMOVE: return "move2";
    case OTA_ITEMTURN: return "pivot2";
    case OTA_ITEMFLICK: return "attack2";
    case OTA_ITEMDROP: return "dropitem2";
    default: return "wait1";
    }
}
bool fleeing(State s) { return s == OTA_MOVE || s == OTA_TURN || s == OTA_ITEMMOVE || s == OTA_ITEMTURN; }
bool flickState(State s) { return s == OTA_FLICK || s == OTA_ITEMFLICK; }
bool carryingState(State s) { return p2otakaraitem::isItemState(toSt(s)); }
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
    // P1-approximation SFX (pc_p2_sfx_policy.h): the P1 bomb-rock burst, output-only.
    pc_p2_sfx(93, generator, p2sfx::Event::Burst, pos);
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
        // P2 Bomb blast: Pikmin are lethal (InteractBomb::actPiki, BlowStateArg mIsLethal=true,
        // interactPiki.cpp:304-326); captains take the attack damage (interactNavi.cpp:45-55).
        // The shared primitive's 10 is the captain value, so Pikmin get the P1 bomb damage (p77, 765).
        const bool isPiki = hit.kind == P2BombSaraiReceiverKind::Piki;
        const float dmg = isPiki && pikiMgr && pikiMgr->mPikiParms ? pikiMgr->mPikiParms->mPikiParms.mBombDamagePiki()
                                                                    : hit.damage;
        Creature* victim = actorsList[hit.receiverId];
        const float before = victim->mHealth;
        InteractBomb bomb(&sBlastOwner, dmg, nullptr);
        const bool accepted = victim->stimulate(bomb);
        std::printf("P2_BOMBOTAKARA_BLAST_HIT generator=%u kind=%s damage=%.1f health=%.1f->%.1f alive=%d accepted=%d\n",
                    generator, isPiki ? "piki" : "navi", dmg, before, victim->mHealth, int(victim->isAlive()),
                    int(accepted));
        if (isPiki) ++pikminHits;
    }
    std::printf("P2_BOMBOTAKARA_BLAST generator=%u payload=93 center=%.3f,%.3f,%.3f radius=%.1f receivers=%d "
                "hits=%d pikmin_hits=%d teki_damage=%.1f navi_piki_damage=%.1f shared_primitive=1 carrier_tick=1 "
                "trigger=%s\n",
                generator, pos.x, pos.y, pos.z, kBombBlastRadius, int(receivers.size()), routed,
                pikminHits, kBombTekiDamage, kBombNavPikiDamage, trigger);
    std::fflush(stdout);
}

// ---------------------------------------------------------------------------
// Attack visuals and the attack window (pc_p2_otakara_attack.h / _fxplan.h)
// ---------------------------------------------------------------------------
using p2otakaraattack::Kind;
using p2otakaraattack::Reason;


// Dev-only effect lab (env PIKMIN_P2_DWEEVIL_FXLAB="id,id,..."): the first time a captain comes within
// 360 of a registered Dweevil, every listed EffectMgr id is started in a grid in front of that captain
// (row-major, 4 per row, 45 apart, 140 ahead), held 3 s, then finished, with a frame-dump burst. One
// frame shows every candidate stand-in side by side; the log lists the id of each grid cell.
struct FxLab {
    bool done = false;
    bool running = false;
    float age = 0.0f;
    std::vector<zen::particleGenerator*> gens;
    std::vector<Vector3f> pos;
};
FxLab sLab;

std::vector<float>& labScales() {
    static std::vector<float> scales;
    return scales;
}

const std::vector<int>& labIds() {
    static std::vector<int> ids;
    static bool parsed = false;
    if (!parsed) {
        parsed = true;
        if (const char* v = std::getenv("PIKMIN_P2_DWEEVIL_FXLAB")) {
            std::string text(v);
            size_t at = 0;
            while (at < text.size()) {
                const size_t comma = text.find(',', at);
                const std::string tok = text.substr(at, comma == std::string::npos ? std::string::npos : comma - at);
                if (!tok.empty()) {
                    ids.push_back(std::atoi(tok.c_str()));
                    const size_t colon = tok.find(':');
                    labScales().push_back(colon == std::string::npos ? 1.0f : float(std::atof(tok.c_str() + colon + 1)));
                }
                if (comma == std::string::npos) break;
                at = comma + 1;
            }
        }
    }
    return ids;
}

void labTick(Otakara& s, float dt) {
    const std::vector<int>& ids = labIds();
    if (ids.empty() || !effectMgr || sLab.done) return;
    if (!sLab.running) {
        Navi* cap = nullptr;
        for (Navi* n : pc_p2_navis()) {
            if (n && n->isAlive() && distXZ(n->getPosition(), s.home) < 360.0f) { cap = n; break; }
        }
        if (!cap) return;
        sLab.running = true;
        sLab.age = 0.0f;
        const Vector3f cp = cap->getPosition();
        // Camera basis in world space: invCamMat maps view -> world, so its third column is the
        // view +z (backwards), its first column the view +x (right).
        float fx = -invCamMat.mMtx[0][2], fz = -invCamMat.mMtx[2][2];
        float rx = invCamMat.mMtx[0][0], rz = invCamMat.mMtx[2][0];
        const float fl = std::sqrt(fx * fx + fz * fz), rl = std::sqrt(rx * rx + rz * rz);
        if (fl > 1.0e-4f) { fx /= fl; fz /= fl; } else { fx = std::sin(cap->mFaceDirection); fz = std::cos(cap->mFaceDirection); }
        if (rl > 1.0e-4f) { rx /= rl; rz /= rl; } else { rx = fz; rz = -fx; }
        sLab.pos.resize(ids.size());
        sLab.gens.assign(ids.size(), nullptr);
        for (size_t i = 0; i < ids.size(); ++i) {
            const int row = int(i) / 4, col = int(i) % 4;
            const float lateral = (float(col) - 1.5f) * 45.0f;
            const float ahead = 110.0f + float(row) * 40.0f;
            sLab.pos[i].set(cp.x + fx * ahead + rx * lateral, cp.y + 2.0f, cp.z + fz * ahead + rz * lateral);
            sLab.gens[i] = effectMgr->create(static_cast<EffectMgr::effTypeTable>(ids[i]), sLab.pos[i], nullptr, nullptr);
            if (sLab.gens[i]) {
                sLab.gens[i]->setEmitDir(Vector3f(0.0f, 1.0f, 0.0f));
                const float sc = i < labScales().size() ? labScales()[i] : 1.0f;
                if (sc != 1.0f) sLab.gens[i]->setScaleSize(sLab.gens[i]->getScaleSize() * sc);
            }
            std::printf("P2_OTAKARA_FXLAB cell=%zu row=%d col=%d effect=%d created=%d x=%.0f z=%.0f\n", i, row, col, ids[i],
                        sLab.gens[i] ? 1 : 0, sLab.pos[i].x, sLab.pos[i].z);
        }
        std::fflush(stdout);
        pc_gfx_frame_dump_burst(60);
        return;
    }
    sLab.age += dt;
    if (sLab.age > 3.0f) {
        for (auto* g : sLab.gens) if (g) effectMgr->kill(g, false);
        sLab.gens.clear();
        sLab.running = false;
        sLab.done = true;
    }
}

// Test-only frame capture (needs PIKMIN_FRAME_DUMP too): PIKMIN_P2_DWEEVIL_SHOT=1 asks the
// renderer for a burst of frames at the first two attacks / takes / drops of the session, so the
// visuals can be inspected from a headless run.
void shotRequest(Otakara& s, const char* what, unsigned frames) {
    static int enabled = -1;
    static unsigned taken = 0;
    if (enabled < 0) {
        const char* v = std::getenv("PIKMIN_P2_DWEEVIL_SHOT");
        enabled = (v && *v && std::string(v) != "0") ? 1 : 0;
    }
    if (enabled != 1 || taken >= 24) return;
    ++taken;
    pc_gfx_frame_dump_burst(frames);
    std::printf("P2_OTAKARA_SHOT generator=%u source_id=%d what=%s frames=%u n=%u\n", s.generator, s.species, what, frames, taken);
    std::fflush(stdout);
}

FxSet& fxSet(Otakara& s, Kind k) { return k == Kind::Charge ? s.chargeFx : s.dischargeFx; }

bool directionalEffect(int effect) { return effect == 227 || effect == 195; }

// Starts every generator of `plan` around `anchor`. A ring is laid out from `yaw`.
void fxSpawnPlan(FxSet& set, const p2otakarafx::Plan& plan, const Vector3f& anchor, bool follow, float yaw) {
    set.count = 0;
    set.age = 0.0f;
    if (!effectMgr) return;
    for (int i = 0; i < plan.count; ++i) {
        const p2otakarafx::Emit& e = plan.emit[i];
        for (int c = 0; c < e.copies && set.count < p2otakarafx::kMaxGenerators; ++c) {
            FxGen& g = set.gens[set.count];
            float ox = 0.0f, oz = 0.0f;
            if (e.copies > 1) {
                const float ang = yaw + 6.2831853f * float(c) / float(e.copies);
                ox = std::sin(ang) * e.radius;
                oz = std::cos(ang) * e.radius;
            }
            g.pos.set(anchor.x + ox, anchor.y + e.y, anchor.z + oz);
            g.off.set(ox, e.y, oz);
            g.follow = follow;
            g.effect = e.effect;
            g.gen = effectMgr->create(static_cast<EffectMgr::effTypeTable>(e.effect), g.pos, nullptr, nullptr);
            if (!g.gen) continue;
            if (directionalEffect(e.effect)) g.gen->setEmitDir(Vector3f(0.0f, 1.0f, 0.0f));
            if (e.scale != 1.0f) g.gen->setScaleSize(g.gen->getScaleSize() * e.scale);
            if (follow) g.gen->setEmitPosPtr(&g.pos);
            ++set.count;
        }
    }
}

void fxKillSet(FxSet& set, bool force) {
    for (int i = 0; i < set.count; ++i) {
        if (set.gens[i].gen && effectMgr) effectMgr->kill(set.gens[i].gen, force);
        set.gens[i].gen = nullptr;
    }
    set.count = 0;
}

void fxStart(Otakara& s, Kind k, const Vector3f& anchor, float yaw) {
    const p2otakarafx::Plan plan = k == Kind::Charge ? p2otakarafx::charge(s.species) : p2otakarafx::discharge(s.species);
    if (plan.count == 0) return;
    if (!s.fxLedger.start(k)) return;
    FxSet& set = fxSet(s, k);
    fxSpawnPlan(set, plan, anchor, k == Kind::Charge, yaw);
    char names[160];
    names[0] = '\0';
    for (int i = 0; i < plan.count; ++i) {
        std::snprintf(names + std::strlen(names), sizeof(names) - std::strlen(names), "%s%s*%d", i ? "," : "",
                      p2otakarafx::effectName(plan.emit[i].effect), plan.emit[i].copies);
    }
    std::printf("P2_OTAKARA_FX_START generator=%u source_id=%d kind=%s generators=%d/%d effects=%s x=%.1f y=%.1f z=%.1f "
                "stand_in=p1_particles n=%u\n",
                s.generator, s.species, p2otakaraattack::kindName(k), set.count, p2otakarafx::generators(plan), names,
                anchor.x, anchor.y, anchor.z, s.fxLedger.starts[int(k)]);
    std::fflush(stdout);
}

// force = engine scene/teardown stop (forceFinish); otherwise the emitters are finished and the
// live particles fade out.
void fxStop(Otakara& s, Kind k, Reason why, bool force) {
    if (!s.fxLedger.stop(k)) return;
    FxSet& set = fxSet(s, k);
    const int n = set.count;
    fxKillSet(set, force);
    std::printf("P2_OTAKARA_FX_STOP generator=%u source_id=%d kind=%s reason=%s generators=%d force=%d n=%u outstanding=%d\n",
                s.generator, s.species, p2otakaraattack::kindName(k), p2otakaraattack::reasonName(why), n, int(force),
                s.fxLedger.stops[int(k)], int(s.fxLedger.anyOn()));
    std::fflush(stdout);
}

void fxStopAll(Otakara& s, Reason why, bool force) {
    fxStop(s, Kind::Charge, why, force);
    fxStop(s, Kind::Discharge, why, force);
}

// The followed charge emitters chase the body joint every tick (setupEffect -> setMtxptr).
void fxFollow(Otakara& s, const Vector3f& bodyPos) {
    for (int i = 0; i < s.chargeFx.count; ++i) {
        if (s.chargeFx.gens[i].follow) {
            FxGen& g = s.chargeFx.gens[i];
            g.pos.set(bodyPos.x + g.off.x, bodyPos.y + g.off.y, bodyPos.z + g.off.z);
        }
    }
}

// interactCreature (Fire|Water|Gas|ElecOtakara.cpp:41-48 and ElecOtakara.cpp:41-60).
bool dischargeInteract(BTeki* a, const Otakara& s, Creature* c, bool isPiki) {
    const Vector3f pos = a->getPosition();
    switch (s.stimulus) {
    case p2dweevil::StimFire: return c->stimulate(InteractFire(a, s.attack));
    case p2dweevil::StimBubble: return c->stimulate(InteractBubble(a, s.attack));
    case p2dweevil::StimGas: return c->stimulate(InteractGas(a, s.attack));
    case p2dweevil::StimDenki: {
        // ElecOtakara::interactCreature: horizontal direction scaled by fp14 (300), and for a
        // Pikmin the vertical part is fp26 (50).
        Vector3f dir(c->getPosition().x - pos.x, 0.0f, c->getPosition().z - pos.z);
        const float len = std::sqrt(dir.x * dir.x + dir.z * dir.z);
        if (len > 0.0f) { dir.x /= len; dir.z /= len; }
        dir.x *= 300.0f;
        dir.z *= 300.0f;
        if (isPiki) dir.y = 50.0f;
        return c->stimulate(InteractDenki(a, s.attack, &dir));
    }
    default: return false;
    }
}

// OtakaraBase::Obj::attackTarget (OtakaraBase.cpp:580-610), one frame of the window.
void attackFrame(BTeki* a, Otakara& s) {
    const Vector3f pos = a->getPosition();
    ++s.windowFrames;
    auto visit = [&](Creature* c, bool isPiki) {
        if (!c || !c->isAlive()) return;
        const Vector3f tp = c->getPosition();
        if (!p2otakaraattack::inReach(tp.x - pos.x, tp.z - pos.z, tp.y - pos.y)) return;
        const bool first = s.windowHit.insert(c).second;
        if (isPiki) {
            Piki* p = static_cast<Piki*>(c);
            if (!dweevilAccepts(p, s.stimulus)) {
                if (first) {
                    ++s.windowImmune;
                    std::printf("P2_OTAKARA_DISCHARGE_IMMUNE generator=%u source_id=%d pikmin=%d colour=%s stimulus=%s\n",
                                s.generator, s.species, pc_p2_species(p), colorName(p->mColor),
                                p2dweevil::stimulusName(s.stimulus));
                    std::fflush(stdout);
                }
                return;
            }
        }
        const bool accepted = dischargeInteract(a, s, c, isPiki);
        if (!first) return;
        ++s.windowApplied;
        if (isPiki) {
            Piki* p = static_cast<Piki*>(c);
            std::printf("P2_OTAKARA_DISCHARGE_HIT generator=%u source_id=%d pikmin=%d colour=%s stimulus=%s accepted=%d "
                        "target_state=%d(%s) window_frame=%u\n",
                        s.generator, s.species, pc_p2_species(p), colorName(p->mColor),
                        p2dweevil::stimulusName(s.stimulus), int(accepted), p->getState(),
                        p->getState() == PIKISTATE_DenkiDying ? "DenkiDying"
                        : p->getState() == PIKISTATE_Fired ? "Fired"
                        : p->getState() == PIKISTATE_Panic ? "Panic" : "other",
                        s.windowFrames);
        } else {
            std::printf("P2_OTAKARA_DISCHARGE_NAVI generator=%u source_id=%d stimulus=%s accepted=%d window_frame=%u\n",
                        s.generator, s.species, p2dweevil::stimulusName(s.stimulus), int(accepted), s.windowFrames);
        }
        std::fflush(stdout);
    };
    for (Navi* n : pc_p2_navis()) visit(static_cast<Creature*>(n), false);
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) { visit(static_cast<Creature*>(static_cast<Piki*>(*it)), true); }
    }
}

// Closes the one-second window: stops the discharge emitters and logs the summary line the
// root-side evidence parsers read (P2_OTAKARA_DISCHARGE generator=.. source_id=.. stimulus=..).
void closeWindow(Otakara& s, Reason why) {
    if (s.windowFrames == 0 && !s.fxLedger.on[int(Kind::Discharge)]) return;
    std::printf("P2_OTAKARA_DISCHARGE generator=%u source_id=%d stimulus=%s applied=%d immune=%d frames=%u reason=%s\n",
                s.generator, s.species, p2dweevil::stimulusName(s.stimulus), s.windowApplied, s.windowImmune,
                s.windowFrames, p2otakaraattack::reasonName(why));
    std::fflush(stdout);
    fxStop(s, Kind::Discharge, why, false);
    s.windowFrames = 0;
    s.windowHit.clear();
    s.windowApplied = s.windowImmune = 0;
}

// Flick event 3 (OtakaraBaseState.cpp:109-114 / 640-646): finishChargeEffect, createDisChargeEffect,
// mAttackActiveTimer = 0.
// World position of the carried Bomb: the Dweevil's local back offset rotated
// by its heading (the source carries the Bomb on the `otakara` joint,
// OtakaraBase.cpp:665).
Vector3f bombWorldPos(BTeki* a) {
    const Vector3f pos = a->getPosition();
    const float d = a->getDirection();
    const p2bombtelegraph::Offset o = p2bombtelegraph::kBackOffset;
    return Vector3f(pos.x + o.x * std::cos(d) + o.z * std::sin(d), pos.y + o.y,
                    pos.z - o.x * std::sin(d) + o.z * std::cos(d));
}

// Source forceBomb: the carried Bomb enters its burn state. The blast itself
// now comes when the burn ends (bombBurnTick), not at the trigger.
void igniteBomb(BTeki* a, Otakara& s, const char* trigger, float carrierHealth) {
    if (s.species != p2dweevil::BombId || s.bombDetonated || s.burn.burning) return;
    s.burn.ignite();
    s.burnTrigger = trigger;
    s.heldHealth = carrierHealth;
    s.liveBaseline = pc_p2_bomb_live_generators();
    std::printf("P2_BOMBOTAKARA_FUSE_START generator=%u payload=93 trigger=%s life=%.2f blast_in=%.3f "
                "source=bombState.cpp:97-122\n",
                genOf(a), trigger, p2bombtelegraph::kBombLife, p2bombtelegraph::kTotalSeconds);
    std::fflush(stdout);
    shotRequest(s, "bomb_fuse", 540); // test-only frame burst (PIKMIN_P2_DWEEVIL_SHOT + PIKMIN_FRAME_DUMP)
}

// One burn frame: drain (addDamage(dt,1)), flash pulse -> spark + tick, the
// TBombrockLight threshold, and the blast 10 frames after the gauge empties.
void bombBurnTick(BTeki* a, Otakara& s, float dt) {
    if (s.species != p2dweevil::BombId || !s.burn.burning) return;
    const unsigned generator = genOf(a);
    const p2bombtelegraph::Step step = s.burn.step(dt);
    s.sparks.update(dt, 0.35f);
    const Vector3f wp = bombWorldPos(a);
    if (step.pulse) {
        s.sparks.spawn(44, wp.x, wp.y + 4.0f, wp.z); // EFF_Piki_FireSparkles (pkf2.pcr), force-killed after 0.35 s
        pc_p2_sfx(93, generator, p2sfx::Event::Fuse, a);
        std::printf("P2_BOMBOTAKARA_FUSE_TICK generator=%u payload=93 n=%d t=%.2f ratio=%.3f period=%.3f\n",
                    generator, s.burn.pulses, s.burn.elapsed(), s.burn.ratio(),
                    p2bombtelegraph::flashPeriod(s.burn.ratio()));
    }
    if (step.lightOn) {
        std::printf("P2_BOMBOTAKARA_LIGHT generator=%u payload=93 health=%.2f threshold=%.1f source=bomb.cpp:203\n",
                    generator, s.burn.health, p2bombtelegraph::kLightBelowHealth);
    }
    if (++s.gaugeLogTick % 15 == 0) {
        std::printf("P2_BOMBOTAKARA_GAUGE generator=%u payload=93 health=%.2f max=%.1f ratio=%.3f flash=%d "
                    "period=%.3f\n",
                    generator, s.burn.health, p2bombtelegraph::kBombLife, s.burn.ratio(), int(s.burn.flashOn()),
                    p2bombtelegraph::flashPeriod(s.burn.ratio()));
    }
    std::fflush(stdout);
    if (step.detonate) {
        s.bombDetonated = true;
        std::printf("P2_BOMBOTAKARA_FUSE_END generator=%u payload=93 trigger=%s ratio=0.000 t=%.2f pulses=%d\n",
                    generator, s.burnTrigger, s.burn.elapsed(), s.burn.pulses);
        std::fflush(stdout);
        s.sparks.killAll();
        s.sinceBlast = 0.0f;
        std::printf("P2_BOMBOTAKARA_FX_KILLED generator=%u live_generators=%u baseline=%u\n", generator,
                    pc_p2_bomb_live_generators(), s.liveBaseline);
        applyBombBlast(a, s, s.burnTrigger);
    }
}

void doDischarge(BTeki* a, Otakara& s) {
    if (s.stimulus == p2dweevil::StimNone) {
        // BombOtakara (93) OWN: Flick discharge event detonates the carried
        // Bomb on this actor's own tick (source BombOtakara damage->forceBomb
        // path, decided here by the P2 carrier FSM, not delegated).
        if (!s.bombDetonated && !s.burn.burning) {
            igniteBomb(a, s, "flick", a->mHealth);
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
    const Vector3f pos = a->getPosition();
    if (s.fxLedger.on[int(Kind::Discharge)]) closeWindow(s, Reason::Abort); // a new discharge replaces an open window
    fxStop(s, Kind::Charge, Reason::Discharge, false);
    p2otakaraattack::windowOpen(s.attackTimer);
    s.windowHit.clear();
    s.windowApplied = s.windowImmune = 0;
    s.windowFrames = 0;
    fxStart(s, Kind::Discharge, pos, a->getDirection());
    std::printf("P2_OTAKARA_DISCHARGE_START generator=%u source_id=%d stimulus=%s window=%.1f radius=%.0f height=%.0f/%.0f\n",
                s.generator, s.species, p2dweevil::stimulusName(s.stimulus), p2otakaraattack::kWindow,
                p2otakaraattack::kRadius, p2otakaraattack::kHeightUp, p2otakaraattack::kHeightDown);
    std::fflush(stdout);
}

// Flick event 2 (flickStickPikmin, enemyAction.cpp:780-800): only Pikmin stuck to this Dweevil.
void doFlick(BTeki* a) {
    if (!pikiMgr) return;
    int flicked = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p && p->isAlive() && p->getStickObject() == static_cast<Creature*>(a)) {
            if (p->stimulate(InteractFlick(a, 120.0f, 0.0f, a->getDirection()))) ++flicked;
        }
    }
    if (flicked) std::printf("P2_OTAKARA_FLICK generator=%u flicked=%d\n", genOf(a), flicked);
}

// ---------------------------------------------------------------------------
// Collision tree (pc_p2_otakara_part.h) and treasure carry (pc_p2_otakara_item.h)
// ---------------------------------------------------------------------------
constexpr int kTreeRoot = 0, kTreeBody = 1, kTreeMouth = 2;

// The retail tree plus the port's mouth anchor 'otak' (a non-stickable, non-damageable point at
// the body joint that the carried pellet is stuck to, like the Chappy 'slot' mouth parts).
void initTree(Otakara& s) {
    const p2flyer::Sphere* base = p2otakarapart::spheres();
    s.tree[kTreeRoot] = base[0];
    s.tree[kTreeBody] = base[1];
    s.tree[kTreeBody].parent = 0;
    s.tree[kTreeMouth] = {"otak", "____", 1.0f, {0.0f, 0.0f, 0.0f}, 0};
    if (s.species == p2dweevil::BombId) {
        // initBombOtakara (OtakaraBase.cpp:659-675): body r15, base r25, both raised 10.
        s.tree[kTreeRoot].radius = 25.0f;
        s.tree[kTreeRoot].offset.y = 10.0f;
        s.tree[kTreeBody].radius = 15.0f;
        s.tree[kTreeBody].offset.y = 10.0f;
    }
}

// resetTreasure / takeTreasure part sizes (OtakaraBase.cpp:450-470, 493-524).
void sizeTreeForHold(Otakara& s) {
    if (s.species == p2dweevil::BombId) return;
    if (s.hold.holding) {
        s.tree[kTreeBody].radius = s.pickRadius;
        s.tree[kTreeBody].offset.y = s.bodyOffsetY;
        s.tree[kTreeRoot].radius = 10.0f + s.pickRadius;
        s.tree[kTreeRoot].offset.y = s.bodyOffsetY;
    } else {
        s.tree[kTreeBody].radius = 10.0f;
        s.tree[kTreeBody].offset.y = 0.0f;
        s.tree[kTreeRoot].radius = 15.0f;
        s.tree[kTreeRoot].offset.y = 0.0f;
    }
}

void bindTree(BTeki* a, Otakara& s) {
    if (s.coll.bound()) return;
    s.collTried = true;
    initTree(s);
    const bool ok = s.coll.bind(a, s.tree, 3);
    std::printf("P2_OTAKARA_COLL generator=%u source_id=%d bound=%d spheres=3 root=none/____/r%.0f body=body/st__/r%.0f "
                "stick_bottom=%.1f legs=none\n",
                s.generator, s.species, int(ok), s.tree[kTreeRoot].radius, s.tree[kTreeBody].radius,
                p2otakarapart::stickBottom(p2otakarapart::bodyHeight("wait1", 0.0f)));
    std::fflush(stdout);
}

float bodyJointHeight(const Otakara& s) {
    if (s.species == p2dweevil::BombId) return 0.0f; // offset y 10 already in the tree
    return p2otakarapart::bodyHeight(s.clip.c_str(), s.phase);
}

// A held pellet is drawn by Pellet::doRender from mStuckMouthPart->getJointMatrix() as its VIEW-space
// model matrix (pelletMgr.cpp:1392-1400). A real joint part carries the joint's view-space
// translation in mJointMatrix; P2FlyerColl::follow keeps only the rotation (its parts are found by
// centre), which would draw the pellet at the camera origin. Seat the mouth part's translation too
// (its getMatrix() overrides the translation with the world centre, so nothing else reads it).
void seatMouthView(Otakara& s) {
    CollPart* m = s.coll.part(kTreeMouth);
    if (!m) return;
    Matrix4f look;
    invCamMat.inverse(&look);
    Vector3f v(m->mCentre);
    v.multMatrix(look);
    m->mJointMatrix.setTranslation(v);
}

void followTree(BTeki* a, Otakara& s, const Vector3f& pos) {
    if (!s.coll.bound() || s.coll.released()) return;
    sizeTreeForHold(s);
    s.coll.follow(a, p2flyer::Vec3{pos.x, pos.y, pos.z}, a->getDirection(),
                  p2flyer::Vec3{0.0f, bodyJointHeight(s), 0.0f}, 1.0f);
    if (s.hold.holding) seatMouthView(s);
}

// World position of the body joint (charge emitters and the carried pellet follow it).
Vector3f bodyWorld(const BTeki* a, const Otakara& s) {
    const Vector3f p = const_cast<BTeki*>(a)->getPosition();
    return Vector3f(p.x, p.y + bodyJointHeight(s), p.z);
}

// takeTreasure (OtakaraBase.cpp:493-524). Returns true when the pellet is now held.
bool takeTreasure(BTeki* a, Otakara& s, const Vector3f& pos) {
    Pellet* p = s.targetPellet;
    if (!p || !pelletLive(p) || !pelletTakeable(p) || s.hold.holding) return false;
    const Vector3f pp = p->mSRT.t;
    const float dx = pp.x - pos.x, dy = pp.y - pos.y, dz = pp.z - pos.z;
    const float dist = std::sqrt(dx * dx + dy * dy + dz * dz);
    if (!p2otakaraitem::isTake(dist, p->getBottomRadius())) return false;
    CollPart* mouth = s.coll.part(kTreeMouth);
    if (!mouth) {
        std::printf("P2_OTAKARA_TREASURE_BLOCKED generator=%u source_id=%d reason=no_mouth_part\n", s.generator, s.species);
        std::fflush(stdout);
        return false;
    }
    s.pickRadius = p->getBottomRadius();
    s.bodyOffsetY = 0.5f * p->getCylinderHeight();
    p2otakaraitem::grab(s.hold, p2otakaraitem::otakaraLife(s.species));
    s.treasure = p;
    sizeTreeForHold(s);
    s.coll.follow(a, p2flyer::Vec3{pos.x, pos.y, pos.z}, a->getDirection(), p2flyer::Vec3{0.0f, bodyJointHeight(s), 0.0f}, 1.0f);
    // Engine mouth stick: the pellet follows the 'otak' part; every carry slot is marked taken so
    // no Pikmin can start carrying it (getMinFreeSlotIndex() == -1).
    seatMouthView(s);
    p->stimulate(InteractSwallow(a, mouth, 0));
    for (int i = 0; i < 4; ++i) p->mSlotFlags[i] = -1;
    p->mVelocity.set(0.0f, 0.0f, 0.0f);
    ++s.treasuresTaken;
    shotRequest(s, "take", 45);
    std::printf("P2_OTAKARA_TREASURE_TAKE generator=%u source_id=%d pellet=%u treasure_health=%.1f pick_radius=%.1f "
                "body_offset=%.1f dist=%.1f stand_in=p1_number_pellet taken=%u\n",
                s.generator, s.species, unsigned((unsigned long long)(size_t)p & 0xFFFFFFu), s.hold.health, s.pickRadius,
                s.bodyOffsetY, dist, s.treasuresTaken);
    std::fflush(stdout);
    return true;
}

// Keeps the held pellet on the mouth part (and still), so a culled frame cannot leave it behind.
void pinTreasure(BTeki* a, Otakara& s) {
    if (!s.hold.holding) return;
    if (!pelletLive(s.treasure)) {
        std::printf("P2_OTAKARA_TREASURE_LOST generator=%u source_id=%d reason=pellet_gone\n", s.generator, s.species);
        std::fflush(stdout);
        s.treasure = nullptr;
        p2otakaraitem::release(s.hold);
        sizeTreeForHold(s);
        return;
    }
    if (CollPart* mouth = s.coll.part(kTreeMouth)) {
        s.treasure->mSRT.t = mouth->mCentre;
        s.treasure->mVelocity.set(0.0f, 0.0f, 0.0f);
    }
    (void)a;
}

// fallTreasure(check) (OtakaraBase.cpp:530-548). `pop` = the (0,100,0) knock-up of fallTreasure(true).
void dropTreasure(BTeki* a, Otakara& s, bool pop, const char* reason) {
    if (!s.hold.holding) return;
    Pellet* p = s.treasure;
    const Vector3f body = bodyWorld(a, s);
    if (pelletLive(p)) {
        p->endStickMouth();
        p->mStuckMouthPart = nullptr;
        for (int i = 0; i < 4; ++i) p->mSlotFlags[i] = 0;
        p->mSRT.t = body;
        p->mVelocity.set(0.0f, pop ? p2otakaraitem::kDropPopVelocityY : 0.0f, 0.0f);
    }
    ++s.treasuresDropped;
    shotRequest(s, "drop", 45);
    std::printf("P2_OTAKARA_TREASURE_DROP generator=%u source_id=%d pellet=%u reason=%s pop=%d treasure_health=%.1f dropped=%u "
                "x=%.1f y=%.1f z=%.1f\n",
                s.generator, s.species, unsigned((unsigned long long)(size_t)p & 0xFFFFFFu), reason, int(pop), s.hold.health,
                s.treasuresDropped, body.x, body.y, body.z);
    std::fflush(stdout);
    s.treasure = nullptr;
    p2otakaraitem::release(s.hold);
    sizeTreeForHold(s);
}

// Dev-only staged treasure (env PIKMIN_P2_DWEEVIL_STAGE_TREASURE=1): the smoke packages have no
// P1 pellet near the Dweevil, so the first time a captain comes within 360 of its home one
// labelled P1 number pellet (yellow 5) is placed 90 from the Dweevil toward that captain. Never
// active without the env var; owner play of a normal seed is untouched.
bool stageTreasureEnabled() {
    static int cached = -1;
    if (cached < 0) {
        const char* v = std::getenv("PIKMIN_P2_DWEEVIL_STAGE_TREASURE");
        cached = (v && *v && std::string(v) != "0") ? 1 : 0;
    }
    return cached == 1;
}

void stageTreasure(BTeki* a, Otakara& s, const Vector3f& pos) {
    if (s.stageDone || s.species == p2dweevil::BombId || !stageTreasureEnabled() || !pelletMgr || !naviMgr) return;
    Navi* nearestNavi = nullptr;
    float best = 360.0f;
    for (Navi* n : pc_p2_navis()) {
        if (!n || !n->isAlive()) continue;
        const float d = distXZ(n->getPosition(), s.home);
        if (d < best) { best = d; nearestNavi = n; }
    }
    if (!nearestNavi) return;
    s.stageDone = true;
    Pellet* p = pelletMgr->newNumberPellet(PELCOLOR_Yellow, NUMPEL_FivePellet);
    if (!p) {
        std::printf("P2_OTAKARA_STAGE_TREASURE generator=%u source_id=%d spawned=0 reason=no_pellet\n", s.generator, s.species);
        std::fflush(stdout);
        return;
    }
    float dx = nearestNavi->getPosition().x - pos.x, dz = nearestNavi->getPosition().z - pos.z;
    const float len = std::sqrt(dx * dx + dz * dz);
    if (len > 0.0f) { dx /= len; dz /= len; }
    Vector3f at(pos.x + dx * 90.0f, pos.y + 10.0f, pos.z + dz * 90.0f);
    p->init(at);
    p->startAI(0);
    std::printf("P2_OTAKARA_STAGE_TREASURE generator=%u source_id=%d spawned=1 pellet=%u x=%.1f y=%.1f z=%.1f captain_dist=%.1f "
                "dev_only=1 stand_in=p1_number_pellet\n",
                s.generator, s.species, unsigned((unsigned long long)(size_t)p & 0xFFFFFFu), at.x, at.y, at.z, best);
    std::fflush(stdout);
    (void)a;
}

// ---------------------------------------------------------------------------
// Walking: source horizontal speed on slopes, stall detection and side-step
// (pc_p2_otakara_stall.h)
// ---------------------------------------------------------------------------
p2otakarastall::Probe probeAt(float x, float z) {
    p2otakarastall::Probe p;
    if (!mapMgr) return p;
    CollTriInfo* tri = mapMgr->getCurrTri(x, z, false);
    if (!tri) return p;
    p.valid = true;
    p.y = mapMgr->getMinY(x, z, false);
    p.normalY = tri->mTriangle.mNormal.y;
    p.slip = MapCode::getSlipCode(tri);
    return p;
}

// Walkable ground along `heading` from `pos` (two probe points) staying inside the territory.
bool headingWalkable(const Otakara& s, const Vector3f& pos, float heading) {
    const float sx = std::sin(heading), sz = std::cos(heading);
    const p2otakarastall::Probe here = probeAt(pos.x, pos.z);
    const p2otakarastall::Probe near1 = probeAt(pos.x + sx * p2otakarastall::kProbeNear, pos.z + sz * p2otakarastall::kProbeNear);
    const p2otakarastall::Probe far1 = probeAt(pos.x + sx * p2otakarastall::kProbeFar, pos.z + sz * p2otakarastall::kProbeFar);
    if (!p2otakarastall::walkable(here, near1, far1)) return false;
    const float fx = pos.x + sx * p2otakarastall::kProbeFar, fz = pos.z + sz * p2otakarastall::kProbeFar;
    return distXZ(Vector3f(fx, 0.0f, fz), Vector3f(s.home.x, 0.0f, s.home.z)) <= TERRITORY + 20.0f;
}

void onStall(BTeki* a, Otakara& s, const Vector3f& pos, float ratio) {
    bool ok[6];
    for (int i = 0; i < 6; ++i) {
        const float h = s.heading + float(p2otakarastall::sideOffsetDeg(i)) * 0.0174532925f;
        ok[i] = headingWalkable(s, pos, h);
    }
    const int pick = p2otakarastall::pickSide(ok, s.stall.lastSide < 0);
    const p2otakarastall::Probe here = probeAt(pos.x, pos.z);
    const float gn = a->mGroundTriangle ? a->mGroundTriangle->mTriangle.mNormal.y : -1.0f;
    const int gslip = a->mGroundTriangle ? MapCode::getSlipCode(a->mGroundTriangle) : -1;
    if (pick >= 0) {
        const int off = p2otakarastall::sideOffsetDeg(pick);
        s.stall.holdHeading = s.heading + float(off) * 0.0174532925f;
        s.stall.hold = p2otakarastall::kHold;
        s.stall.lastSide = off > 0 ? 1 : -1;
        ++s.stall.sidesteps;
        std::printf("P2_OTAKARA_STALL generator=%u source_id=%d state=%s x=%.1f z=%.1f heading_deg=%.0f ratio=%.2f "
                    "normal_y=%.2f slip=%d probe_normal_y=%.2f action=sidestep offset_deg=%d hold=%.1f stalls=%u sidesteps=%u\n",
                    s.generator, s.species, stateName(s.state), pos.x, pos.z, s.heading * 57.2957795f, ratio, gn, gslip,
                    here.normalY, off, p2otakarastall::kHold, s.stall.stalls, s.stall.sidesteps);
    } else {
        ++s.stall.noRoute;
        std::printf("P2_OTAKARA_STALL generator=%u source_id=%d state=%s x=%.1f z=%.1f heading_deg=%.0f ratio=%.2f "
                    "normal_y=%.2f slip=%d probe_normal_y=%.2f action=none reason=no_walkable_side stalls=%u no_route=%u\n",
                    s.generator, s.species, stateName(s.state), pos.x, pos.z, s.heading * 57.2957795f, ratio, gn, gslip,
                    here.normalY, s.stall.stalls, s.stall.noRoute);
    }
    std::fflush(stdout);
}

// EnemyFunc::walkToTarget(ota, movePos, fp06, fp08, fp28) (enemyAction.cpp:2102-2107): turn toward
// the destination, then set the target speed along the facing. `dest` is the destination in
// force (s.target, or the side-step heading while one is held).
void walkStep(BTeki* a, Otakara& s, const Vector3f& pos, float dt) {
    p2otakaramove::Vec2 dest = v2(s.target);
    if (s.stall.holding()) {
        dest = p2otakaramove::Vec2{pos.x + std::sin(s.stall.holdHeading) * 100.0f, pos.z + std::cos(s.stall.holdHeading) * 100.0f};
        s.stall.tickHold(dt);
    }
    s.heading = p2otakaramove::turnStep(s.heading, v2(pos), dest, dt);
    a->setDirection(s.heading);
    const float speed = speciesMoveSpeed(s.species);
    const float dx = std::sin(s.heading), dz = std::cos(s.heading);
    float gain = 1.0f;
    if (a->mGroundTriangle) {
        const Vector3f& n = a->mGroundTriangle->mTriangle.mNormal;
        gain = p2otakarastall::slopeGain(n.x, n.y, n.z, dx, dz);
    }
    s.lastGain = gain;
    s.moveCommanded = speed;
    const Vector3f drive(dx * speed * gain, 0.0f, dz * speed * gain);
    a->inputDrive(drive);
    a->mVelocity.set(drive);
    if (s.prevPosValid) {
        const float moved = distXZ(pos, s.prevPos);
        if (s.stall.sample(dt, moved, speed * dt)) onStall(a, s, pos, moved / (speed * dt));
    }
}

void stopStep(BTeki* a) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
}

// ---------------------------------------------------------------------------
// State entry / commit
// ---------------------------------------------------------------------------
void enter(BTeki* a, Otakara& s, State state, const char* clip, float timer = 0.0f) {
    if (fleeing(s.state) && !fleeing(state)) {
        endFlee(s, flickState(state) ? "flick" : state == OTA_DEAD ? "dead" : state == OTA_TAKE ? "take" : "wait");
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
    // A Flick left without its discharge event must not leave the charge emitters running.
    if (flickState(s.state) && !flickState(state) && s.fxLedger.on[int(Kind::Charge)]) {
        fxStop(s, Kind::Charge, Reason::Abort, false);
    }
    // StateItemDrop::cleanup (OtakaraBaseState.cpp:733-739): the pickup delay restarts.
    if (s.state == OTA_ITEMDROP && state != OTA_ITEMDROP) s.itemSearchTimer = 0.0f;
    if (state != OTA_MOVE && state != OTA_ITEMMOVE && state != OTA_TAKE) s.stall.reset();
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
    s.phase = 0.0f;
    if (flickState(state)) {
        s.attackWaitTimer = 0.0f;
        fxStart(s, Kind::Charge, bodyWorld(a, s), a->getDirection());
        shotRequest(s, "attack", 105);
    }
}

// Commit the pending source mNextState when the looped clip reaches its end
// (finishMotion -> KEYEVENT_END, OtakaraBaseState.cpp:196-198/266-268).
void commitPending(BTeki* a, Otakara& s, const Vector3f& pos, float prevStateTime) {
    if (s.pending == OTA_INVALID || s.pending == s.state) return;
    if (!p2otakaramove::clipEndCrossed(prevStateTime, s.stateTime, clipDuration(s.clip))) return;
    const State next = s.pending;
    std::printf("P2_OTAKARA_STATE generator=%u state=%s\n", genOf(a), stateName(next));
    enter(a, s, next, clipFor(next));
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
    if (s.species != p2dweevil::BombId || s.bombDetonated || s.burn.burning) return;
    if (!p2otakaramove::bombFuseStep(s.bombFuse, dt)) return;
    std::printf("P2_BOMBOTAKARA_FUSE generator=%u payload=93 chase=%.2f\n", genOf(a), s.bombFuse);
    std::fflush(stdout);
    igniteBomb(a, s, "fuse", a->mHealth);
}

void fireEvents(BTeki* a, Otakara& s, const Vector3f& pos) {
    auto it = clips.find(s.clip);
    if (it == clips.end()) return;
    for (const auto& event : it->second.events) {
        if (s.firedEvents.count(event.first)) continue;
        if (s.stateTime < event.first / 30.0f) continue;
        s.firedEvents.insert(event.first);
        if (flickState(s.state) && event.second == 2) {
            doFlick(a);
            s.flickTimer = 0.0f; // OtakaraBaseState.cpp:107
            s.flickEventFired = true;
        } else if (flickState(s.state) && event.second == 3) {
            doDischarge(a, s);
        } else if (s.state == OTA_TAKE && event.second == 2) {
            takeTreasure(a, s, pos); // StateTake::exec event 2 (OtakaraBaseState.cpp:365-366)
        } else if (s.state == OTA_ITEMDROP && event.second == 2) {
            dropTreasure(a, s, true, "itemdrop"); // StateItemDrop::exec event 2 (:698-699)
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

// isTakeTreasure (OtakaraBase.cpp:472-489) for the current treasure destination.
bool takeNow(const Otakara& s, const Vector3f& pos) {
    if (!s.treasureTarget || !s.targetPellet) return false;
    const Vector3f pp = s.targetPellet->mSRT.t;
    const float dx = pp.x - pos.x, dy = pp.y - pos.y, dz = pp.z - pos.z;
    return p2otakaraitem::isTake(std::sqrt(dx * dx + dy * dy + dz * dz), s.targetPellet->getBottomRadius());
}
} // namespace

void pc_p2_otakara_reset() {
    // Scene (re)start: the engine's own EffectMgr::killAll has stopped every generator, so
    // the ledgers only record that the scene teardown owned the stop. No pellet, collision or
    // effect pointer of the old scene is dereferenced here.
    for (auto& kv : actors) {
        Otakara& s = kv.second;
        if (!s.fxLedger.anyOn()) continue;
        for (int k = 0; k < 2; ++k) {
            if (s.fxLedger.on[k]) {
                s.fxLedger.stop(Kind(k));
                std::printf("P2_OTAKARA_FX_STOP generator=%u source_id=%d kind=%s reason=teardown generators=%d force=0 "
                            "n=%u outstanding=0 owner=engine_killall\n",
                            s.generator, s.species, p2otakaraattack::kindName(Kind(k)), (k == 0 ? s.chargeFx : s.dischargeFx).count,
                            s.fxLedger.stops[k]);
            }
        }
    }
    actors.clear();
    clips.clear();
    ready = false;
}

void pc_p2_otakara_forget(BTeki* actor) {
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    const unsigned generator = it->second.generator;
    Otakara& s = it->second;
    // Teardown of everything this actor owns: the held treasure goes back to the ground, every
    // generator is force-stopped, and the host's own CollInfo is put back (pooled actors).
    dropTreasure(actor, s, false, "forget");
    closeWindow(s, Reason::Forget);
    fxStopAll(s, Reason::Forget, true);
    s.coll.detach(actor);
    endFlee(s, "forget");
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


// ---------------------------------------------------------------------------
// Receiver hooks
// ---------------------------------------------------------------------------
namespace {
const char* ownerName(Creature* owner) {
    if (!owner) return "none";
    if (owner->isPiki()) return colorName(static_cast<Piki*>(owner)->mColor);
    if (owner->mObjType == OBJTYPE_Navi) return "navi";
    if (owner->mObjType == OBJTYPE_Teki) return "teki";
    return "creature";
}
} // namespace

// Source OtakaraBase::Obj::damageCallBack (OtakaraBase.cpp:190-197): `if (collpart) damageTreasure`,
// else false. A latched Pikmin attack carries its stick part (aiAttack.cpp:740/762); the ground
// punches (aiAttack.cpp:688/707, Navi::punch) carry none and are refused. BombOtakara (93)
// overrides damageCallBack without a part test (BombOtakara.cpp), so it keeps the partless path.
int pc_p2_otakara_attack_part(BTeki* actor, Creature* owner, CollPart* part, float damage) {
    if (!ready || !actor) return -1;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return -1;
    Otakara& s = it->second;
    if (s.species == p2dweevil::BombId) return -1;
    const bool fromFighter = owner && (owner->isPiki() || owner->mObjType == OBJTYPE_Navi);
    if (!fromFighter) return -1;
    const p2otakarapart::Verdict v = p2otakarapart::verdict(part != nullptr);
    if (v.accept) ++s.partAccepted;
    else ++s.partRefused;
    const unsigned n = v.accept ? s.partAccepted : s.partRefused;
    if (n <= 4 || n % 25 == 0) {
        // ID32::mStringID holds the four characters in register order (byte-reversed on this
        // host); print them as written in enemycoll.txt.
        char idBuf[5] = {'n', 'o', 'n', 'e', 0};
        if (part && part->mCollInfo) {
            const char* raw = part->mCollInfo->mId.mStringID;
            for (int i = 0; i < 4; ++i) idBuf[i] = raw[3 - i];
        }
        const char* id = idBuf;
        std::printf("P2_OTAKARA_PART generator=%u source_id=%d owner=%s part=%s form=%s verdict=%s damage=%.1f "
                    "accepted=%u refused=%u health=%.1f state=%s\n",
                    s.generator, s.species, ownerName(owner), id,
                    p2otakarapart::formOf(part != nullptr) == p2otakarapart::Form::LatchedAttack ? "latched" : "ground_punch",
                    v.reason, damage, s.partAccepted, s.partRefused, actor->mHealth, stateName(s.state));
        std::fflush(stdout);
    }
    return v.accept ? 1 : 0;
}

// damageTreasure while carrying (OtakaraBase.cpp:563-574): the hit reduces the treasure's health,
// not the Dweevil's, and adds no flick count.
bool pc_p2_otakara_divert(BTeki* actor, Creature* owner, float damage) {
    if (!ready || !actor) return false;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return false;
    Otakara& s = it->second;
    if (!s.hold.holding) return false;
    const float before = s.hold.health;
    p2otakaraitem::damageTreasure(s.hold, damage);
    std::printf("P2_OTAKARA_TREASURE_HIT generator=%u source_id=%d attacker=%s damage=%.1f treasure_health=%.1f->%.1f "
                "dweevil_health=%.1f state=%s\n",
                s.generator, s.species, ownerName(owner), damage, before, s.hold.health, actor->mHealth, stateName(s.state));
    std::fflush(stdout);
    return true;
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

static bool registerActor(BTeki* actor, int species, unsigned generator) {
    if (!actor || species < 0) return false;
    // A second registration of the same actor (the dynamic bind at birth, then the setup pass)
    // must first give back what the first one took: the host CollInfo the own tree replaced, a
    // held treasure and any running generator. Otherwise the new registration would treat the
    // first own tree as the "vehicle" tree and the real one would be lost.
    auto existing = actors.find(static_cast<PelletView*>(actor));
    if (existing != actors.end()) {
        Otakara& old = existing->second;
        dropTreasure(actor, old, false, "rebind");
        closeWindow(old, Reason::Forget);
        fxStopAll(old, Reason::Forget, true);
        old.coll.detach(actor);
    }
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
    initTree(s);
    enter(actor, s, OTA_WAIT, "wait1");
    bindTree(actor, s);
    if (s.coll.bound()) s.collAttempts = 99;
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
    ++s.updateTick;
    s.sincePress += dt;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = genOf(actor);

    // Collision tree: retry a failed bind a few times (the host tree may not exist on the first tick).
    if (!s.coll.bound() && !s.coll.released() && s.collAttempts < 5) {
        s.collRetry -= dt;
        if (s.collRetry <= 0.0f) {
            ++s.collAttempts;
            bindTree(actor, s);
            s.collRetry = 1.0f;
        }
    }
    stageTreasure(actor, s, pos);
    labTick(s, dt);

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
        if (s.species == p2dweevil::BombId && !s.bombDetonated && !s.burn.burning) {
            igniteBomb(actor, s, "damage", s.prevHealth);
        }
    }
    // The carrier's damage callbacks route to the Bomb, not to the carrier
    // (BombOtakara.cpp:42-55), so a burning bomb holds the carrier's health
    // until the bomb itself goes off (payload-dead rule below).
    if (s.species == p2dweevil::BombId && s.burn.burning && !s.bombDetonated && actor->mHealth < s.heldHealth
            && actor->mHealth > 0.0f) {
        actor->mHealth = s.heldHealth;
    }
    bombBurnTick(actor, s, dt);
    if (s.sinceBlast >= 0.0f && !s.cleanLogged) {
        s.sinceBlast += dt;
        if (s.sinceBlast >= 1.0f) {
            s.cleanLogged = true;
            std::printf("P2_BOMBOTAKARA_FX_CLEAN generator=%u since_blast=%.2f live_generators=%u baseline=%u\n",
                        genOf(actor), s.sinceBlast, pc_p2_bomb_live_generators(), s.liveBaseline);
            std::fflush(stdout);
        }
    }
    // Source Otakara::doUpdateCommon (OtakaraBase.cpp:93-108) for BombOtakara:
    // once the carried Bomb is no longer alive (mTargetCreature dead, or null)
    // the Dweevil sets mTargetCreature = nullptr and mHealth = 0, i.e. it dies
    // with its payload. The port has no separate Bomb creature; a detonated
    // bomb (fuse, damage, flick or death) is the "Bomb no longer alive" case.
    if (s.species == p2dweevil::BombId && s.bombDetonated && actor->mHealth > 0.0f) {
        std::printf("P2_BOMBOTAKARA_PAYLOAD_DEAD generator=%u health=%.1f->0 (source OtakaraBase.cpp:93-108)\n",
                    generator, actor->mHealth);
        std::fflush(stdout);
        actor->mHealth = 0.0f;
    }
    s.prevHealth = actor->mHealth;

    if (actor->mHealth <= 0.0f && s.state != OTA_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_OTAKARA_MODULE_DEAD generator=%u source_id=%d health=0 part_accepted=%u part_refused=%u "
                        "treasures_taken=%u treasures_dropped=%u stalls=%u sidesteps=%u fx_starts=%u/%u fx_stops=%u/%u\n",
                        generator, s.species, s.partAccepted, s.partRefused, s.treasuresTaken, s.treasuresDropped,
                        s.stall.stalls, s.stall.sidesteps, s.fxLedger.starts[0], s.fxLedger.starts[1], s.fxLedger.stops[0],
                        s.fxLedger.stops[1]);
            std::fflush(stdout);
            s.deadLogged = true;
            if (s.species == p2dweevil::BombId) pc_p2_sfx(93, generator, p2sfx::Event::Dead, actor);
        }
        // Source death detonates the carried Bomb (damageCallBack path).
        if (s.species == p2dweevil::BombId && !s.bombDetonated) {
            s.bombDetonated = true;
            s.burn.burning = false;
            s.burn.detonated = true;
            s.sparks.killAll();
            applyBombBlast(actor, s, "death");
        }
        // OtakaraBase::onKill (OtakaraBase.cpp:65-69): fallTreasure(true) + finishChargeEffect. The
        // attack window and its emitters end with the Dweevil.
        dropTreasure(actor, s, true, "death");
        if (s.windowFrames > 0 || s.fxLedger.on[int(Kind::Discharge)]) closeWindow(s, Reason::Dead);
        fxStopAll(s, Reason::Dead, false);
        s.attackTimer = p2otakaraattack::kIdle;
        // The vehicle tree goes back before the host forms the corpse (P2FlyerColl::release).
        s.coll.release(actor, p2flyer::Vec3{pos.x, pos.y + 5.0f, pos.z});
        enter(actor, s, OTA_DEAD, "dead");
    }

    // Obj::doUpdateCommon (OtakaraBase.cpp:85-92): the attack window runs in any state.
    if (s.state != OTA_DEAD) {
        if (p2otakaraattack::windowStep(s.attackTimer, dt)) attackFrame(actor, s);
        if ((s.windowFrames > 0 || s.fxLedger.on[int(Kind::Discharge)]) && !p2otakaraattack::windowActive(s.attackTimer)) {
            closeWindow(s, Reason::WindowEnd);
        }
    }

    const float prevStateTime = s.stateTime;
    s.stateTime += dt;
    using p2otakaramove::St;
    const bool carrying = s.hold.holding;
    switch (s.state) {
    case OTA_WAIT:
    case OTA_MOVE:
    case OTA_TURN:
    case OTA_ITEMWAIT:
    case OTA_ITEMMOVE:
    case OTA_ITEMTURN: {
        // Source StateWait/Move/Turn (OtakaraBaseState.cpp:165-334) and the Item* twins
        // (:415-594): the destination decision (treasure for the plain states, flee for all),
        // isStartFlick / isDropTreasure, commit at the looped clip end.
        const bool itemState = carryingState(s.state);
        if (s.state == OTA_MOVE || s.state == OTA_TURN) bombFuseTick(actor, s, dt);
        const bool hasTarget = updateDestination(actor, s, pos, itemState, dt);
        const bool sideStep = s.stall.holding() && (s.state == OTA_MOVE || s.state == OTA_ITEMMOVE);
        const bool facing = hasTarget && (sideStep || facingDest(s, pos));
        const bool flick = flickRequested(s, generator);
        const bool drop = itemState && p2otakaraitem::isDrop(s.hold);
        const State next = fromSt(p2otakaraitem::decide(
            {toSt(s.state), hasTarget, facing, hasTarget && takeNow(s, pos), flick, drop, false}));
        if (s.state == OTA_WAIT || s.state == OTA_ITEMWAIT) {
            stopStep(actor);
            s.clip = s.state == OTA_WAIT ? "wait1" : "wait2";
        } else if (s.state == OTA_TURN || s.state == OTA_ITEMTURN) {
            stopStep(actor);
            if (hasTarget) {
                s.heading = p2otakaramove::turnStep(s.heading, v2(pos), v2(s.target), dt);
                actor->setDirection(s.heading);
            }
        } else {
            // Move: walk along the facing while within THIRD_PI; a pending Flick/Take/Turn zeroes the drive.
            if (facing && next == s.state) walkStep(actor, s, pos, dt);
            else stopStep(actor);
        }
        if (next != s.state) s.pending = next;
        if (s.state == OTA_MOVE || s.state == OTA_TURN || s.state == OTA_ITEMMOVE || s.state == OTA_ITEMTURN) {
            trackFlee(s, pos, dt);
            if (s.state == OTA_MOVE || s.state == OTA_ITEMMOVE) {
                s.decisionLogTimer += dt;
                if (hasTarget && s.decisionLogTimer >= 1.0f) {
                    s.decisionLogTimer = 0.0f;
                    logDecision(s, pos);
                }
            }
        }
        commitPending(actor, s, pos, prevStateTime);
        break;
    }
    case OTA_TAKE:
        // Source StateTake::exec (OtakaraBaseState.cpp:362-391): keep walking at the stored
        // destination while the takeitem clip plays; event 2 takes the treasure (fireEvents);
        // the clip end decides the carry states.
        walkStep(actor, s, pos, dt);
        if (s.stateTime >= clipDuration("takeitem")) {
            const bool flick = flickRequested(s, generator);
            const State next = fromSt(p2otakaraitem::afterTake(s.hold.holding, p2otakaraitem::isDrop(s.hold), flick));
            std::printf("P2_OTAKARA_STATE generator=%u state=%s holding=%d\n", generator, stateName(next), int(s.hold.holding));
            enter(actor, s, next, clipFor(next));
        }
        break;
    case OTA_FLICK:
    case OTA_ITEMFLICK:
        stopStep(actor);
        s.attackWaitTimer += dt;
        if (s.stateTime >= clipDuration(s.clip)) {
            // Port guard: a bank whose attack clip lacks event 2 must not re-trigger the
            // Flick forever, so the counter still resets once per Flick.
            if (!s.flickEventFired) s.flickTimer = 0.0f;
            const bool item = s.state == OTA_ITEMFLICK;
            // Source StateFlick KEYEVENT_END (OtakaraBaseState.cpp:115-133): straight
            // back to Move/Turn while a threat exists, else Wait. StateItemFlick (:646-665)
            // drops first and ignores treasures.
            const bool hasTarget = updateDestination(actor, s, pos, item, 0.0f);
            const bool facing = hasTarget && facingDest(s, pos);
            const State next = item ? fromSt(p2otakaraitem::afterItemFlick(p2otakaraitem::isDrop(s.hold), hasTarget, facing))
                                    : fromSt(p2otakaramove::afterFlick(actor->mHealth <= 0.0f, hasTarget, facing));
            std::printf("P2_OTAKARA_STATE generator=%u state=%s\n", generator, stateName(next));
            enter(actor, s, next, clipFor(next));
            if (fleeing(next)) logDecision(s, pos);
        }
        break;
    case OTA_ITEMDROP:
        stopStep(actor);
        if (s.stateTime >= clipDuration("dropitem2")) {
            // StateItemDrop KEYEVENT_END (OtakaraBaseState.cpp:703-729).
            const bool flick = flickRequested(s, generator);
            const bool hasTarget = updateDestination(actor, s, pos, false, 0.0f);
            const bool facing = hasTarget && facingDest(s, pos);
            const State next = fromSt(p2otakaraitem::afterItemDrop(actor->mHealth <= 0.0f, flick, hasTarget, facing));
            std::printf("P2_OTAKARA_STATE generator=%u state=%s\n", generator, stateName(next));
            enter(actor, s, next, clipFor(next));
            if (fleeing(next)) logDecision(s, pos);
        }
        break;
    case OTA_DEAD:
        stopStep(actor);
        // Host death handoff: the P1 strategy reacts to mHealth<=0 inside
        // BTeki::doAI(), calls die() and then dieSoon()->becomePellet() in the
        // same pass. The module only drives the source dead clip and lets the
        // host complete teardown/corpse (same contract as pc_p2_sokkuri/armor).
        break;
    default:
        break;
    }
    (void)carrying;
    setPhase(s);
    if (s.state != OTA_DEAD) {
        followTree(actor, s, pos);
        pinTreasure(actor, s);
        if (s.hold.holding && s.treasure) {
            s.carryLog += dt;
            if (s.carryLog >= 1.0f) {
                s.carryLog = 0.0f;
                const Vector3f pp = s.treasure->mSRT.t;
                std::printf("P2_OTAKARA_CARRY generator=%u source_id=%d state=%s pellet=%u pellet_at=%.1f,%.1f,%.1f dweevil_at=%.1f,%.1f,%.1f "
                            "pellet_above_feet=%.1f stuck_to_mouth=%d free_slot=%d treasure_health=%.1f dweevil_health=%.1f\n",
                            s.generator, s.species, stateName(s.state), unsigned((unsigned long long)(size_t)s.treasure & 0xFFFFFFu),
                            pp.x, pp.y, pp.z, pos.x, pos.y, pos.z, pp.y - pos.y, int(s.treasure->isStickToMouth()),
                            s.treasure->getMinFreeSlotIndex(), s.hold.health, actor->mHealth);
                std::fflush(stdout);
            }
        }
        if (s.fxLedger.on[int(Kind::Charge)]) fxFollow(s, bodyWorld(actor, s));
    }
    fireEvents(actor, s, pos);

    // Trace (1 Hz while walking): commanded vs measured horizontal speed and the ground under it.
    if (s.moveCommanded > 0.0f && (s.state == OTA_MOVE || s.state == OTA_ITEMMOVE || s.state == OTA_TAKE)) {
        s.traceTimer += dt;
        if (s.traceTimer >= 1.0f) {
            const float moved = s.prevPosValid ? distXZ(pos, s.prevPos) : 0.0f;
            const float gn = actor->mGroundTriangle ? actor->mGroundTriangle->mTriangle.mNormal.y : -1.0f;
            const int gslip = actor->mGroundTriangle ? MapCode::getSlipCode(actor->mGroundTriangle) : -1;
            std::printf("P2_OTAKARA_MOVE_TRACE generator=%u source_id=%d state=%s commanded=%.1f gain=%.2f "
                        "horizontal_cmd=%.1f vel=%.1f,%.1f,%.1f tick_speed=%.1f normal_y=%.2f slip=%d home_dist=%.1f "
                        "stuck=%d stalls=%u sidesteps=%u\n",
                        generator, s.species, stateName(s.state), s.moveCommanded, s.lastGain, s.moveCommanded * s.lastGain,
                        actor->mVelocity.x, actor->mVelocity.y, actor->mVelocity.z, moved / dt, gn, gslip,
                        distXZ(pos, s.home), s.stuckCount, s.stall.stalls, s.stall.sidesteps);
            std::fflush(stdout);
            s.traceTimer = 0.0f;
        }
    } else {
        s.traceTimer = 0.0f;
        s.moveCommanded = 0.0f;
    }
    s.prevPos = pos;
    s.prevPosValid = true;
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        std::printf("P2_OTAKARA_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z);
        std::fflush(stdout);
    }
}

// ---------------------------------------------------------------------------
// Volatile Dweevil carried-Bomb visuals (pc_p2_bomb_telegraph.h). Output-only:
// nothing here touches sim state.
// ---------------------------------------------------------------------------

// Draw the P1 bomb-rock shape (objects/bomb/bomb.mod, ItemMgr::mItemShapes[2])
// on the Dweevil's back, in the actor's own draw matrix. While the fuse burns
// the bomb materials flash (dim / hot), faster as the gauge empties.
void pc_p2_otakara_draw_bomb(BTeki* actor, Graphics& gfx, const Matrix4f& matrix) {
    if (!ready || !actor || !gfx.mCamera) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Otakara& s = it->second;
    if (s.species != p2dweevil::BombId || s.bombDetonated || actor->mHealth <= 0.0f) return;
    Matrix4f local, view;
    const p2bombtelegraph::Offset o = p2bombtelegraph::kBackOffset;
    const float k = p2bombtelegraph::kBombScale * (s.burn.flashOn() ? p2bombtelegraph::kFlashSwell : 1.0f);
    local.makeSRT(Vector3f(k, k, k), Vector3f(0.0f, 0.0f, 0.0f), Vector3f(o.x, o.y, o.z));
    matrix.multiplyTo(local, view);

    // Shared shape draw (pc_p2_bomb_visual.h): tints the bomb materials while the fuse burns.
    pc_p2_bomb_draw_shape(gfx, view, s.burn.burning, s.burn.flashOn(), s.burn.ratio());
    static std::set<unsigned> logged;
    if (logged.insert(genOf(actor)).second) {
        std::printf("P2_BOMBOTAKARA_BOMB_DRAW generator=%u model=objects/bomb/bomb.mod offset=%.1f,%.1f,%.1f "
                    "scale=%.2f\n",
                    genOf(actor), o.x, o.y, o.z, k);
        std::fflush(stdout);
    }
}

// The bomb's own countdown gauge: the P1 life-gauge wheel, drained from full
// to empty over the burn (EnemyBase::getLifeGaugeParam ratio = mHealth /
// mMaxHealth, bombItem.cpp:167-178 for the P1 wheel style).
bool pc_p2_otakara_bomb_gauge(BTeki* actor, Graphics& gfx) {
    if (!ready || !actor || !gfx.mCamera) return false;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return false;
    Otakara& s = it->second;
    if (s.species != p2dweevil::BombId) return false;
    // The Dweevil never takes damage itself (BombOtakara.cpp:42-55 routes it to the Bomb), so
    // it shows no life gauge of its own: only the bomb's countdown wheel.
    if (!s.burn.burning || s.bombDetonated) return true;
    s.gauge.draw(gfx, bombWorldPos(actor), s.burn.health, p2bombtelegraph::kBombLife);
    return true;
}
