// ADDITIVE-SCOPE GUARD (#678): standalone contract builds define
// P2_DAMAGUMO_BINDING_STANDALONE to compile only the engine-free
// profile/mesh/slot binding below. Production builds (macro undefined)
// compile the original file content that follows, byte-identical.
#ifndef P2_DAMAGUMO_BINDING_STANDALONE
// Family-owned snagret-family source behavior for the batch-3 Chappy placement
// vehicle: Segmented Crawbster (DangoMushi, EnemyID 94). Implements the source
// DangoMushiState.cpp segmented roller FSM: Stay -> Appear (fly) -> Wait ->
// Move -> Attack (ball roll) -> Turn (crash) -> Recover -> Flick (attack_2) ->
// Wait, plus Dead. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_snagret_assets.py (GPVE01 revision 0, DangoMushi
// DISC_PARMS). The source states, animation IDs and key-event streams are the
// audited disc values (DangoMushi.h:23-35, DangoMushi.h:210-222,
// EXPECTED_EVENTS['DangoMushi']).
//
// DangoMushi is a standalone `EnemyBase`/`EnemyBlendAnimatorBase` boss, not a
// snagret and not a `ChappyBase`; it shares this batch-3 host only as a
// placement vehicle (expected native type TEKI_Chappy) so the source FSM can
// run on the P1 engine.
//
// Boss loop (#897 fidelity pass; decisions in pc_p2_dangomushi_policy.h):
//   * Turn is entered ONLY from Obj::wallCallback (DangoMushi.cpp:260): the P1
//     BTeki::wallCallback(Plane&) hands the wall normal to
//     pc_p2_dangomushi_wall, which applies the source speed>100 and
//     dot(vel,n)<-0.5 crash test to the P2 roll velocity. The roll otherwise
//     lasts until the source 15 s timeout -> Wait. (The former territory-150
//     exit is gone.)
//   * Roll crush (Obj::collisionCallback): every frame while rolling, every
//     grounded Pikmin/Navi in body contact is pressed. P2 kills every pressed
//     Pikmin (PikiPressedState::exec -> kill after 1.5 s); the P1 receiver
//     only subtracts damage, so a Pikmin press carries lethal damage and the
//     P1 pressed state kills it at once. A Navi takes fp24. Only accepted
//     presses count toward roll_targets; P2_DANGOMUSHI_CRUSH_TALLY reports how
//     many crushed Pikmin are dead at the wall crash / roll stop. A 0.5 s
//     per-target cooldown only limits re-sends.
//   * The 15 s roll timeout calls finishMotion: the loop runs out to LOOP_END,
//     rolling stops and the uncurl tail plays to END before Wait.
//   * Health 0 during Turn plays the turn out (finishMotion, tail, END) before
//     Dead; every Turn exit runs StateTurn::cleanup flickStickPikmin(1,10,0).
//   * Turn clip (StateTurn::exec): turn.bca loops LOOP_START 32 .. LOOP_END 81
//     until FLIP_TIME 7.5 s, then plays the tail to END. LOOP_START opens the
//     stickable window (EB_Invulnerable clear), tail key 3 (108) closes it and
//     shakes the stickers (setBodyCollision(true)): Purple -> InteractFlick
//     (fp17/fp18), others -> wither (P1: blown flick + Leaf, the
//     InteractHanaChirashi outcome). Outside the window the bod parts are not
//     stickable in the source; P1 has no per-part stick switch on a teki, so a
//     Pikmin that latches outside the window is flicked off at once
//     (knockback 10, damage 0: the source StateTurn::cleanup flickStickPikmin).
//   * createCrashEnemy on EVERY Turn: 10 Rocks around the active captain plus
//     0/1 Egg at home by the captain's formation share. The Rocks/Egg are the
//     lane-20 P2RockHazard / P2Egg policies and are DRAWN
//     (pc_p2_dangomushi_draw_rain) with the P1 Iwagon boulder as the stand-in
//     mesh: no P2 Rock/Egg model is staged for the campaign.
//   * Flick (StateFlick): during the attack_2 KEYEVENT_2..3 windows the right
//     hand sweeps an arc in front of the body. Navi -> flick with fp24 damage
//     (P2 InteractWind::actNavi: flat 300 push; P1 InteractFlick knockback
//     300), Purple -> InteractFlick(fp17, fp18), other Pikmin -> wither, all
//     pushed away from the crab. Adaptation: the hand path is a sector (reach 170,
//     +-80 deg), not the hand_R joint tube, and the hand-hits-ground early
//     exit (flickHandCollision()) is not modelled.
//   * Carcass: the P2 retail carcass_config.txt DangoMushi row (min 20, max
//     30 carriers, 30 seeds) is applied to the corpse pellet through a private
//     PelletConfig, replacing the Swallow host carcass.
// Clip per state (#crawbster-idle): Stay and Wait show the looping wait clip,
// Appear plays fly once, never looped (the old fly loop made the crab fall in
// from above forever). Wait/Move run their clip out before the queued
// transit (finishMotion), Attack needs the fp21 15-degree cone (Move turns to
// it), and the roll timeout runs 3x/5x while against a wall.
// Remaining adaptations: Stay keeps the model visible (no
// ModelHidden; the source hides it until Appear); the dangomushi.brk material loop is not
// reproduced; walk uses fp08/fp28 and the roll fp01/fp02/fp03. When the
// installed p2-snagret-bank.txt is absent the audited retail event frames
// and 117-frame turn clip are used.
// No other lane's module is modified; every hook is a no-op for unregistered
// actors.
#include "pc_p2_dangomushi.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_randomizer.h"
#include "pc_p2_dangomushi_hazard.h"
#include "pc_p2_dangomushi_policy.h"
#include "pc_p2_sfx.h"
#include "pc_p2_egg_hazard.h"
#include "pc_p2_rock_hazard.h"
#include "pc_p2_rock_host.h"
#include "teki.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiState.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "pc_p2_navi_select.h"
#include "Generator.h"
#include "gameflow.h"
#include "GameStat.h"
#include "Creature.h"
#include "MapMgr.h"
#include "ItemMgr.h"
#include "Pellet.h"
#include "ObjType.h"
#include "Stickers.h"
#include "Plane.h"
#include "Graphics.h"
#include "Camera.h"
#include "Shape.h"
#include "GlobalGameOptions.h"
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace {
enum State {
    DANGO_DEAD = 0,
    DANGO_STAY = 1,
    DANGO_APPEAR = 2,
    DANGO_WAIT = 3,
    DANGO_MOVE = 4,
    DANGO_ATTACK = 5,
    DANGO_TURN = 6,
    DANGO_RECOVER = 7,
    DANGO_FLICK = 8,
};

const char* stateName(State s) {
    switch (s) {
    case DANGO_DEAD: return "dead";
    case DANGO_STAY: return "stay";
    case DANGO_APPEAR: return "appear";
    case DANGO_WAIT: return "wait";
    case DANGO_MOVE: return "move";
    case DANGO_ATTACK: return "attack";
    case DANGO_TURN: return "turn";
    case DANGO_RECOVER: return "recover";
    case DANGO_FLICK: return "flick";
    default: return "null";
    }
}

// Source enemyparm.txt retail values (snagret manifest, DangoMushi general).
constexpr float LIFE = 3000.0f;              // fp00
constexpr float MOVE_SPEED = 50.0f;          // fp06
constexpr float TERRITORY = 150.0f;          // fp09 territory radius
constexpr float HOME_RADIUS = 100.0f;        // fp10 home radius
constexpr float PRIVATE_RADIUS = 150.0f;     // fp11 Stay wake distance
constexpr float SIGHT = 500.0f;              // fp12 sight radius
constexpr float ATTACK_RANGE = 300.0f;       // fp20 max attack range
constexpr float ATTACK_ANGLE = 0.261799f;    // fp21 15 deg
constexpr float ATTACK_DAMAGE = 10.0f;       // fp24 attack power
constexpr float SHAKE_KNOCKBACK = 200.0f;    // fp17 shake knockback
constexpr float SHAKE_DAMAGE = 1.0f;         // fp18 shake damage
// Roll crush reach. Source: collisionCallback fires when a real collision part
// of the rolling body touches the target (enemycoll.txt: ball parts <= 35 radius
// around the body; the 200 root sphere is only the bounding volume). fp22=100 is
// the AI attack-hit range, not a contact radius. The ball sits 60 above the floor
// (Obj::resetMapCollisionSize(true): HeightOffsetFromFloor 60), so the rolling
// body is a ~60 radius ball; a target is hit when its own size overlaps it.
constexpr float ROLL_BALL_RADIUS = 60.0f;
constexpr float WALK_TURN_RATE = 0.05f;      // fp08 rotation speed rate
constexpr float WALK_MAX_TURN = 0.0872665f;  // fp28 5 deg
// Source proper-parm retail values (DangoMushi proper block).
constexpr float ROLL_SPEED = 200.0f;         // fp01 rolling movement speed
constexpr float ROLL_TURN_ACCEL = 0.03f;     // fp02 rolling rotation speed rate
constexpr float ROLL_TURN_SPEED = 0.0523599f; // fp03 rolling max turn 3 deg
constexpr float FLIP_TIME = 7.5f;            // fp10 (disc omits it; header default)
// Source state timers (DangoMushiState.cpp).
constexpr float WAIT_TIME = 3.0f;            // StateWait::exec 3.0f
constexpr float MOVE_TIMEOUT = 10.0f;        // StateMove::exec 10.0f
constexpr float ATTACK_TIMEOUT = 15.0f;      // StateAttack::exec 15.0f
constexpr float MOVE_ARRIVE = 25.0f;         // sqrt(625) Obj::isReachedTarget
// Source StateTurn::cleanup flickStickPikmin(1.0, 10.0, 0.0): used for a
// Pikmin that latches while the body is not stickable.
constexpr float UNSTICK_KNOCKBACK = 10.0f;
// Audited retail event frames (EXPECTED_EVENTS['DangoMushi']); used when the
// installed bank is absent.
constexpr int FALLBACK_ROLL_START = 23;      // attack 23:4 KEYEVENT_4
constexpr int FALLBACK_FLICK_START = 26;     // attack_2 26:2 KEYEVENT_2
// Rain host slot pool = the source generalEnemyMgr Rock reservation (30
// concurrent Rocks per Crawbster); a dead Rock returns its slot. Overflow is
// logged (P2_DANGOMUSHI_ROCK_OVERFLOW), never silent.
constexpr int kRainRockSlots = 30;

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events;
};

struct Dango {
    State state = DANGO_STAY;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    Vector3f moveTarget;
    bool rolling = false;
    bool armSwinging = false;
    // #897 roll crush / wall crash / turn window / flick bookkeeping.
    float driveX = 0.0f, driveZ = 0.0f;     // P2 mRollingVelocity (XZ)
    p2dango::PressCrush crush{ROLL_BALL_RADIUS, 0.5f};
    std::set<Creature*> rollTargets;         // distinct targets whose press was accepted
    std::set<Piki*> rollCrushed;             // accepted Pikmin presses this roll
    float attackFinishAt = -1.0f;            // StateAttack finishMotion time (15 s timeout)
    bool dyingInTurn = false;                // StateTurn: health 0 -> finishMotion, then Dead
    float turnFlip = 7.5f;                   // finishMotion time for the turn clock
    p2dango::TurnClock turnClock;            // current turn.bca clock
    bool turnClosed = false;                 // key 3 reached this Turn
    bool rollDrawn = false;
    std::set<Creature*> flickHit;            // hand victims this Flick state
    int flickWindow = -1;
    float healthLogTimer = 0.0f;
    float lastLoggedHealth = -1.0f;
    bool carcassApplied = false;
    int rockDrawTurn = -1;
    std::string drawnClip;
    std::set<int> firedEvents;
    std::string clip = "wait";
    // StateWait/StateMove: finishMotion() queues nextState; the transit runs
    // when the current clip pass reaches KEYEVENT_END (finishAt, in state time).
    State nextState = DANGO_WAIT;
    float finishAt = -1.0f;
    float rollTimer = 0.0f;                  // StateAttack mStateTimer (advanced only by rollingMove)
    bool wallTouched = false;                // Obj::mWallTriangle seen this frame
    // StateStay (DangoMushiState.cpp:92-105): EB_ModelHidden. The P1 host hides
    // through the Mizinko/Hollec option set VISIBLE|ORGANIC|SHAPE_VISIBLE|SHADOW_VISIBLE|ATARI.
    bool hidden = false;
    int hiddenOpts = 0;                      // host option bits restored on Appear
    float shadowScale = 0.0f;                // Obj::mShadowScale; Appear when it reaches 1
    float stickLogTimer = 0.0f;
    float phase = 0.0f;
    bool deadLogged = false;
    bool escaped = false;
    float logTimer = 0.0f;
    // Lane-25 hazard policy (#376): Turn vulnerability window + Rock/Egg rain.
    P2DangoMushiHazardPolicy hazard;
    bool turnJustEntered = false;
    bool hazardWindowLogged = false;
    int hazardRocks = 0;
    // Applied vulnerability state: true only inside the Turn stickable window.
    // Outside it pc_p2_dangomushi_invulnerable rejects attack/bomb damage.
    bool stickable = false;
    bool attackRejectedLogged = false;
    // Lane-25 real rain host (#174/#376): the hazard policy's Rock/Egg decisions
    // realized as falling Rock hazards (lane-20 P2RockHazard) and a real Egg
    // (lane-20 P2Egg) whose break births real P1 pellets/nectar. The policies are
    // consumed unchanged; this state only hosts them.
    P2RockHazard rainRock[kRainRockSlots];
    bool rainRockUsed[kRainRockSlots] = {};
    float rainRockDeadTimer[kRainRockSlots] = {};
    float rainRockMaxLife[kRainRockSlots] = {};
    float rainRockAge[kRainRockSlots] = {};
    bool rainRockLifetimeExpired[kRainRockSlots] = {};
    P2RockHazardPhase rainRockPrev[kRainRockSlots] = {};
    std::set<std::uint64_t> rainContacts[kRainRockSlots];
    std::uint64_t rainRockSelf = 1;
    P2Egg rainEgg;
    bool rainEggActive = false;
    P2EggVec3 rainEggPos;
    p2rockhost::ScriptRng rainRng;
    double rainDebt = 0.0;
};

std::map<PelletView*, Dango> actors;
std::map<std::string, Clip> clips;
int rollStartFrame = FALLBACK_ROLL_START;
int flickStartFrame = FALLBACK_FLICK_START;
bool ready = false;

float wrapPi(float a) {
    while (a > PI) a -= TAU;
    while (a < -PI) a += TAU;
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
int eventFrame(const char* name, int type) {
    auto it = clips.find(name);
    if (it != clips.end()) {
        for (const auto& event : it->second.events)
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

void stop(BTeki* a) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
}

// Source Obj::turnByAngle: clamp(angleDist * turnSpeed, maxTurnAngle).
void turnAndMove(BTeki* a, Dango& s, const Vector3f& target,
                 float speed, float turnSpeed, float maxTurn, bool move = true) {
    const Vector3f pos = a->getPosition();
    const float desired = std::atan2(target.x - pos.x, target.z - pos.z);
    float delta = wrapPi(desired - s.heading) * turnSpeed;
    if (delta > maxTurn) delta = maxTurn;
    if (delta < -maxTurn) delta = -maxTurn;
    s.heading = wrapPi(s.heading + delta);
    a->setDirection(s.heading);
    if (!move) { // source: mTargetVelocity = 0 while the crab is not lined up yet
        s.driveX = s.driveZ = 0.0f;
        a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        a->mVelocity.x = 0.0f;
        a->mVelocity.z = 0.0f;
        return;
    }
    const Vector3f drive(std::sin(s.heading) * speed, 0.0f,
                         std::cos(s.heading) * speed);
    s.driveX = drive.x;
    s.driveZ = drive.z;
    a->inputDrive(drive);
    a->mVelocity.x = drive.x;
    a->mVelocity.z = drive.z;
}

// Source Obj::setRandTarget: a random point between the home and territory radii
// on the far side of the crab from home.
void setRandTarget(Dango& s) {
    const float outside = TERRITORY > HOME_RADIUS ? TERRITORY - HOME_RADIUS : 0.0f;
    const float radius = gsys->getRand(outside) + HOME_RADIUS;
    const float theta = gsys->getRand(TAU);
    s.moveTarget = Vector3f(s.home.x + radius * std::sin(theta), s.home.y,
                            s.home.z + radius * std::cos(theta));
}

bool canAttack(const Vector3f& pos, const Dango& s, Creature* target) {
    // Source isTargetAttackable(target, viewAngle, fp20 range, fp21 cone):
    // within 300 AND within 15 deg of the crab's facing. Move turns toward the
    // target until aligned, so the cone is reachable.
    const Vector3f t = target->getPosition();
    if (distXZ(t, pos) > ATTACK_RANGE) return false;
    return std::fabs(wrapPi(std::atan2(t.x - pos.x, t.z - pos.z) - s.heading)) <= ATTACK_ANGLE;
}

int hideMask() {
    return BTeki::TEKI_OPTION_VISIBLE | BTeki::TEKI_OPTION_ORGANIC | BTeki::TEKI_OPTION_SHAPE_VISIBLE
           | BTeki::TEKI_OPTION_SHADOW_VISIBLE | BTeki::TEKI_OPTION_ATARI;
}
// Switchable: PIKMIN_P2_DANGO_STAY_VISIBLE=1 keeps the crab on screen (wait clip)
// during Stay instead of hiding it until the drop-in.
bool stayHides() {
    static const bool hides = std::getenv("PIKMIN_P2_DANGO_STAY_VISIBLE") == nullptr;
    return hides;
}
void setHidden(BTeki* a, Dango& s, bool hide) {
    if (hide == s.hidden) return;
    if (hide) {
        s.hiddenOpts = 0;
        const int bits[] = {BTeki::TEKI_OPTION_VISIBLE, BTeki::TEKI_OPTION_ORGANIC,
                            BTeki::TEKI_OPTION_SHADOW_VISIBLE, BTeki::TEKI_OPTION_ATARI,
                            BTeki::TEKI_OPTION_SHAPE_VISIBLE};
        for (int bit : bits) if (a->getTekiOption(bit)) s.hiddenOpts |= bit;
        a->clearTekiOption(s.hiddenOpts);
    } else {
        a->setTekiOption(s.hiddenOpts);
    }
    s.hidden = hide;
}

void enter(Dango& s, State state, const char* clip) {
    s.state = state;
    s.stateTime = 0.0f;
    s.turnJustEntered = state == DANGO_TURN;
    s.firedEvents.clear();
    s.rolling = false;
    s.armSwinging = false;
    s.crush.reset();
    s.rollTargets.clear();
    s.rollCrushed.clear();
    s.attackFinishAt = -1.0f;
    s.dyingInTurn = false;
    s.turnFlip = FLIP_TIME;
    s.turnClock = p2dango::TurnClock();
    s.turnClosed = false;
    s.flickHit.clear();
    s.flickWindow = -1;
    s.finishAt = -1.0f;
    s.rollTimer = 0.0f;
    s.wallTouched = false;
    // Leave the body invulnerable on every transition; the Turn window reopens
    // it while stickable. attackRejectedLogged is per-window, not per-state.
    s.stickable = false;
    // Clip per state comes from the policy table (DangoMushiState.cpp anim ids);
    // the literal passed by the caller is only a fallback.
    const char* mapped = p2dango::stateClip(stateName(state));
    if (mapped) s.clip = mapped;
    else if (clip) s.clip = clip;
}
void setState(BTeki* a, Dango& s, State state, const char* clip) {
    enter(s, state, clip);
    // Bridge pack actors may carry a placeholder _70; the seed token is the
    // stable own-token for evidence. Fixes generator=0 STATE attribution.
    const unsigned generator = pc_p2_campaign_token(a) ? pc_p2_campaign_token(a)
        : (a->mGenerator ? a->mGenerator->_70 : 0u);
    std::printf("P2_DANGOMUSHI_STATE generator=%u state=%s clip=%s\n", generator,
                stateName(state), s.clip.c_str());
    std::printf("P2_DANGO_STATE generator=%u state=%s clip=%s loop=%d hidden=%d\n", generator,
                stateName(state), s.clip.c_str(), p2dango::clipLoops(s.clip.c_str()) ? 1 : 0,
                int(s.hidden));
    std::fflush(stdout);
    // P1 Cannon Beetle / boulder bank approximation (output-only, #946).
    switch (state) {
    case DANGO_TURN: pc_p2_sfx(94, generator, p2sfx::Event::Expose, a); break;
    case DANGO_FLICK: pc_p2_sfx(94, generator, p2sfx::Event::Flick, a); break;
    case DANGO_RECOVER: pc_p2_sfx(94, generator, p2sfx::Event::Attack, a); break;
    case DANGO_DEAD: pc_p2_sfx(94, generator, p2sfx::Event::Dead, a); break;
    default: break;
    }
}

// Source finishMotion() + KEYEVENT_END transit (StateWait/StateMove): the
// queued state starts only when the current clip pass ends, so the crab
// finishes its wait/walk cycle before rolling or walking again.
bool advanceFinish(BTeki* a, Dango& s, State next) {
    s.nextState = next;
    if (s.finishAt < 0.0f) {
        const float len = clipDuration(s.clip) > 0.0f ? clipDuration(s.clip) : 1.0f;
        s.finishAt = (std::floor(s.stateTime / len) + 1.0f) * len;
    }
    if (s.stateTime < s.finishAt) return false;
    const char* clip = next == DANGO_ATTACK ? "attack" : next == DANGO_MOVE ? "move" : "wait";
    if (next == DANGO_MOVE && s.state == DANGO_WAIT) setRandTarget(s);
    setState(a, s, next, clip);
    return true;
}

// Source Obj::rollingMove: steer toward the active Navi (else the nearest
// Pikmin/Navi) at the proper rolling speed.
void rollingMove(BTeki* a, Dango& s, const Vector3f& pos) {
    Creature* target = nullptr;
    if (naviMgr) {
        Navi* n = pc_p2_source_active_navi(pos); // source getActiveNavi (DangoMushi.cpp:414)
        if (n && n->isAlive()) target = n;
    }
    if (!target) target = nearestTarget(pos, SIGHT);
    if (target) {
        turnAndMove(a, s, target->getPosition(), ROLL_SPEED,
                    ROLL_TURN_ACCEL, ROLL_TURN_SPEED);
    } else {
        turnAndMove(a, s, Vector3f(pos.x + std::sin(s.heading) * 100.0f, pos.y,
                                   pos.z + std::cos(s.heading) * 100.0f),
                    ROLL_SPEED, ROLL_TURN_ACCEL, ROLL_TURN_SPEED);
    }
}

unsigned tokenOf(BTeki* a) {
    const unsigned campaignToken = pc_p2_campaign_token(a);
    return campaignToken ? campaignToken : (a->mGenerator ? a->mGenerator->_70 : 0u);
}

// Source Obj::collisionCallback while mIsRolling: InteractPress(fp24) to every
// grounded creature in body contact, every frame (policy: per-target cooldown).
// P2 InteractPress::actPiki (interactPiki.cpp:584) moves the Pikmin to
// PIKISTATE_Pressed, whose exec kill()s it after 1.5 s whatever its health
// (pikiState.cpp:1334). The P1 press receiver only subtracts the damage and
// kills a pressed Pikmin whose health is already <= 0, so a flower Pikmin
// would merely be stunned. The port therefore presses a Pikmin with lethal
// damage (p2dango::pressDamage): the P1 pressed state then kills it at once
// (adaptation: no 1.5 s flattened wait). A Navi keeps the source fp24 damage
// (InteractPress::actNavi, interactNavi.cpp:141).
void rollCrush(BTeki* a, Dango& s, const Vector3f& pos, unsigned generator) {
    auto consider = [&](Creature* c, const char* kind, bool piki) {
        if (!c || !c->isAlive()) return;
        const Vector3f q = c->getPosition();
        p2dango::PressCandidate cand;
        cand.token = static_cast<std::uint64_t>(reinterpret_cast<std::uintptr_t>(c));
        cand.dx = q.x - pos.x;
        cand.dz = q.z - pos.z;
        cand.grounded = c->mGroundTriangle != nullptr;
        cand.alive = true;
        cand.reach = c->getSize(); // the target's own collision size joins the ball radius
        if (!s.crush.shouldPress(cand, s.stateTime)) return;
        const float hitDist = std::sqrt(cand.dx * cand.dx + cand.dz * cand.dz);
        const float damage = p2dango::pressDamage(piki, c->mHealth);
        const bool took = c->stimulate(InteractPress(a, damage));
        // Only accepted presses count (a Pikmin already pressed, invincible
        // or airborne-state is rejected by the receiver).
        if (took) {
            s.rollTargets.insert(c);
            if (piki) s.rollCrushed.insert(static_cast<Piki*>(c));
        }
        std::printf("P2_DANGOMUSHI_PRESS generator=%u target=%s:%llx accepted=%d damage=%.1f "
                    "lethal=%d roll_targets=%zu dist=%.1f ball_radius=%.1f target_size=%.1f reach=%.1f\n", generator, kind,
                    static_cast<unsigned long long>(cand.token), int(took), damage,
                    int(piki && took), s.rollTargets.size(), hitDist, ROLL_BALL_RADIUS, cand.reach,
                    ROLL_BALL_RADIUS + cand.reach);
        std::fflush(stdout);
    };
    if (naviMgr) for (Navi* n : pc_p2_navis()) consider(n, "navi", false);
    if (pikiMgr) {
        std::vector<Piki*> pikis;
        Iterator it(pikiMgr);
        CI_LOOP(it) pikis.push_back(static_cast<Piki*>(*it));
        for (Piki* p : pikis) consider(p, "piki", true);
    }
}

// Runtime check that the crush is lethal: of the Pikmin whose press was
// accepted this roll, how many are dead (or dying) now.
void logCrushTally(Dango& s, unsigned generator, const char* when) {
    int dead = 0;
    for (Piki* p : s.rollCrushed) {
        const int st = p->getState();
        if (!p->isAlive() || st == PIKISTATE_Dead || st == PIKISTATE_Dying) ++dead;
    }
    std::printf("P2_DANGOMUSHI_CRUSH_TALLY generator=%u when=%s pressed_pikmin=%zu dead=%d "
                "roll_targets=%zu\n", generator, when, s.rollCrushed.size(), dead,
                s.rollTargets.size());
    std::fflush(stdout);
}

p2dango::TargetKind pikiKind(Piki* p) {
    return p->mP2Purple ? p2dango::TargetKind::PurplePikmin : p2dango::TargetKind::Pikmin;
}

// Apply a policy reaction; returns true when the receiver took it.
bool applyReaction(BTeki* a, Creature* target, const p2dango::ReactionOut& r, float angle) {
    switch (r.kind) {
    case p2dango::Reaction::Flick:
    case p2dango::Reaction::NaviFlick:
        return target->stimulate(InteractFlick(a, r.knockback, r.damage, angle));
    case p2dango::Reaction::Wither:
        // InteractHanaChirashi::actPiki: blown (BlowState, leaf chance 1.0).
        if (target->isAlive() && r.leaf) static_cast<Piki*>(target)->setFlower(Leaf);
        return target->stimulate(InteractFlick(a, r.knockback, r.damage, angle));
    default:
        return false;
    }
}

std::vector<Piki*> stuckPikis(BTeki* a) {
    std::vector<Piki*> out;
    Stickers stickers(a);
    Iterator it(&stickers);
    CI_LOOP(it) {
        Creature* stuck = *it;
        if (stuck && stuck->isPiki()) out.push_back(static_cast<Piki*>(stuck));
    }
    return out;
}

// Source Obj::setBodyCollision(true) at Turn key 3: shake every stuck Pikmin.
void shakeStickers(BTeki* a, Dango& s, unsigned generator) {
    const float angle = PI + s.heading;
    int purple = 0, wither = 0;
    const std::vector<Piki*> stuck = stuckPikis(a);
    if (a->mHealth > 0.0f) {
        for (Piki* p : stuck) {
            const p2dango::TargetKind kind = pikiKind(p);
            if (applyReaction(a, p, p2dango::shakeReaction(kind), angle)) {
                if (kind == p2dango::TargetKind::PurplePikmin) ++purple; else ++wither;
            }
        }
    }
    std::printf("P2_DANGOMUSHI_SHAKE generator=%u stuck=%zu count=%d purple=%d wither=%d "
                "frame=%.1f t=%.2f\n", generator, stuck.size(), purple + wither, purple, wither,
                s.turnClock.frame, s.stateTime);
    std::fflush(stdout);
}

// #stick diagnostics: the host CollInfo part tree and the Pikmin around the body
// while the Turn window is open. The host parts (P1 Swallow) are what Pikmin
// actually latch to; the drawn P2 crab is a baked-pose model.
void logPartTree(CollPart* part, const Vector3f& pos, unsigned generator, int depth) {
    if (!part || depth > 6) return;
    const u32 id = part->getID().mId;
    std::printf("P2_DANGOMUSHI_STICK_PART generator=%u id=%c%c%c%c depth=%d radius=%.1f "
                "dx=%.1f dy=%.1f dz=%.1f stickable=%d type=%d\n", generator,
                char(id >> 24), char(id >> 16), char(id >> 8), char(id), depth, part->mRadius,
                part->mCentre.x - pos.x, part->mCentre.y - pos.y, part->mCentre.z - pos.z,
                int(part->isStickable()), int(part->mPartType));
    const int n = part->getChildCount();
    for (int i = 0; i < n; ++i) logPartTree(part->getChildAt(i), pos, generator, depth + 1);
}

void logStickSurface(BTeki* a, const Vector3f& pos, unsigned generator, bool tree) {
    if (tree && a->mCollInfo) logPartTree(a->mCollInfo->getBoundingSphere(), pos, generator, 0);
    const std::vector<Piki*> stuck = stuckPikis(a);
    int near = 0;
    float nearest = 1e9f;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            const Vector3f q = p->getPosition();
            const float d = std::sqrt((q.x - pos.x) * (q.x - pos.x) + (q.z - pos.z) * (q.z - pos.z));
            if (d < 160.0f) ++near;
            if (d < nearest) nearest = d;
        }
    }
    std::printf("P2_DANGOMUSHI_STICK generator=%u stuck=%zu pikmin_within_160=%d nearest_pikmin=%.1f\n",
                generator, stuck.size(), near, nearest);
    for (Piki* p : stuck) {
        const Vector3f q = p->getPosition();
        std::printf("P2_DANGOMUSHI_STICK_PIKI generator=%u dx=%.1f dy=%.1f dz=%.1f\n", generator,
                    q.x - pos.x, q.y - pos.y, q.z - pos.z);
    }
    std::fflush(stdout);
}

// Outside the Turn window the source bod parts are not stickable: a Pikmin
// that latched anyway is flicked off at once (flickStickPikmin 10/0).
void unstickOutsideWindow(BTeki* a, Dango& s, unsigned generator) {
    const std::vector<Piki*> stuck = stuckPikis(a);
    if (stuck.empty()) return;
    int n = 0;
    for (Piki* p : stuck) {
        if (p->stimulate(InteractFlick(a, UNSTICK_KNOCKBACK, 0.0f, PI + s.heading))) ++n;
    }
    std::printf("P2_DANGOMUSHI_UNSTICK generator=%u state=%s stuck=%zu flicked=%d\n",
                generator, stateName(s.state), stuck.size(), n);
    std::fflush(stdout);
}

// Source StateTurn::cleanup (DangoMushiState.cpp:560): on every Turn exit
// (Recover or, after a death, Dead) flickStickPikmin(1.0, 10, 0).
void turnCleanup(BTeki* a, Dango& s, unsigned generator) {
    const std::vector<Piki*> stuck = stuckPikis(a);
    int n = 0;
    for (Piki* p : stuck)
        if (p->stimulate(InteractFlick(a, UNSTICK_KNOCKBACK, 0.0f, PI + s.heading))) ++n;
    std::printf("P2_DANGOMUSHI_TURN_CLEANUP generator=%u stuck=%zu flicked=%d dying=%d\n",
                generator, stuck.size(), n, int(s.dyingInTurn));
    std::fflush(stdout);
}

// Source StateFlick + Obj::flickHandCollision(Creature*): while the arm swings
// (attack_2 KEYEVENT_2..3) the right hand hits captains and Pikmin in front.
void flickSweep(BTeki* a, Dango& s, const Vector3f& pos, unsigned generator, int window) {
    int navis = 0, purple = 0, wither = 0;
    auto hit = [&](Creature* c, p2dango::TargetKind kind) {
        if (!c || !c->isAlive() || s.flickHit.count(c)) return;
        const Vector3f q = c->getPosition();
        const float dx = q.x - pos.x, dz = q.z - pos.z;
        if (!p2dango::inArmArc(dx, dz, s.heading)) return;
        s.flickHit.insert(c);
        // P1/P2 flick receivers push along -(sin a, cos a): `a` must point from
        // the victim to the crab (source JMAAtan2Radian(crab - target)).
        const float angle = p2dango::flickAngle(dx, dz);
        if (!applyReaction(a, c, p2dango::flickReaction(kind), angle)) return;
        if (kind == p2dango::TargetKind::Navi) ++navis;
        else if (kind == p2dango::TargetKind::PurplePikmin) ++purple;
        else ++wither;
    };
    if (naviMgr) for (Navi* n : pc_p2_navis()) hit(n, p2dango::TargetKind::Navi);
    if (pikiMgr) {
        std::vector<Piki*> pikis;
        Iterator it(pikiMgr);
        CI_LOOP(it) pikis.push_back(static_cast<Piki*>(*it));
        for (Piki* p : pikis) if (p) hit(p, pikiKind(p));
    }
    if (navis + purple + wither > 0) {
        std::printf("P2_DANGOMUSHI_FLICK generator=%u window=%d navi=%d purple=%d wither=%d "
                    "pikmin=%d frame=%.1f\n", generator, window, navis, purple, wither,
                    purple + wither, s.stateTime * 30.0f);
        std::fflush(stdout);
    }
}

int turnClipFrames() {
    auto it = clips.find("turn");
    return it == clips.end() ? p2dango::kTurnClipFrames
                             : int(std::lround(it->second.duration * 30.0f));
}

void setPhase(Dango& s) {
    // Looped source clocks (turn 32..81 until FLIP_TIME, roll 50..100).
    if (s.state == DANGO_TURN || (s.state == DANGO_ATTACK && (s.rolling || s.attackFinishAt >= 0.0f))) {
        const float frames = clips.count(s.clip) ? clipDuration(s.clip) * 30.0f : 0.0f;
        if (frames > 1.0f) {
            const float frame = s.state == DANGO_TURN ? s.turnClock.frame
                : p2dango::attackClock(s.stateTime, s.attackFinishAt, int(std::lround(frames))).frame;
            s.phase = frame / (frames - 1.0f);
            if (s.phase > 1.0f) s.phase = 1.0f;
            if (s.phase < 0.0f) s.phase = 0.0f;
            return;
        }
    }
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

// ---------------------------------------------------------------------------
// Lane-25 real rain host (#174/#376): consume the lane-20 Rock/Egg policies and
// realize the Crawbster's hazard decisions as real children. The policies are
// not forked: P2RockHazard falls under the source velocity and emits real
// InteractPress/InteractAttack; P2Egg breaks into real P1 pellets/nectar. Rock
// fall/scale values are the documented fixture host parms already used by
// tools/p2_rock_hazard_test.cpp (mSearchDistance/Height/Angle stand-ins); they
// are host inputs, never source constants. Egg drop chances are the disc proper
// parms fp01-fp05 (0.5/0.35/0.05/0.05/0.05) with general fp00=50.
// ---------------------------------------------------------------------------
constexpr float kRainDelta = P2RockHazard::kSourceDelta;
constexpr float kRainOnFloorTolerance = 40.0f;
constexpr float kRainContactPad = 12.0f;
constexpr float kRainEggContactRadius = 25.0f;
constexpr float kRainSpawnHeight = 300.0f;

P2RockHazardConfig rainRockConfig() {
    P2RockHazardConfig config;
    config.fallSpeed = 500.0f;      // fixture host parm (mSearchDistance)
    config.fallOffset = 100.0f;     // fixture host parm (mSearchHeight)
    config.scaleUpRate = 5.0f;      // fixture host parm (mSearchAngle)
    config.sightRadius = 350.0f;    // general mSightRadius fixture
    config.attackDamage = 10.0f;    // general mAttackDamage fixture
    config.collisionRadius = 40.0f; // host fall trace radius
    config.health = 100.0f;         // general mHealth fixture
    return config;
}

P2EggConfig rainEggConfig() {
    P2EggConfig config;
    config.singleNectarChance = 0.5f;  // disc fp01
    config.doubleNectarChance = 0.35f; // disc fp02
    config.mititesChance = 0.05f;      // disc fp03
    config.spicyChance = 0.05f;        // disc fp04
    config.bitterChance = 0.05f;       // disc fp05
    config.forcedDropType = 0;
    config.checkHasSpray = true;
    config.health = 50.0f;             // general fp00
    return config;
}

// Static-map sphere trace for the rain Rocks: reuse the shared lane-20 Rock host
// binding (p2rockhost::RockMapBinding / detectRock / ScriptRng) rather than a
// local fork of pc_p2_projectiles.cpp's RockMapBinding / rockDetection / rng.
p2rockhost::RockMapBinding gRainBinding;

bool rainOnFloor(const Creature& creature) {
    if (!mapMgr) return false;
    const Vector3f& position = creature.mSRT.t;
    if (!std::isfinite(position.x) || !std::isfinite(position.z)) return false;
    const float ground = mapMgr->getMinY(position.x, position.z, true);
    return std::isfinite(ground) && std::fabs(position.y - ground) <= kRainOnFloorTolerance;
}

std::uint64_t rainToken(const Creature* creature) {
    return static_cast<std::uint64_t>(reinterpret_cast<std::uintptr_t>(creature));
}

void spawnRainRocks(Dango& s, BTeki* actor, const Vector3f& center, float angle,
                    int count, float lifetime, unsigned generator) {
    const P2RockHazardConfig config = rainRockConfig();
    int spawned = 0;
    for (int i = 0; i < count; ++i) {
        int slot = -1;
        for (int k = 0; k < kRainRockSlots; ++k) {
            if (!s.rainRockUsed[k]
                || s.rainRock[k].phase() == P2RockHazardPhase::Killed) {
                slot = k;
                break;
            }
        }
        if (slot < 0) {
            // Source mgr->birth returns null when the 30-Rock pool is full.
            std::printf("P2_DANGOMUSHI_ROCK_OVERFLOW generator=%u requested=%d spawned=%d "
                        "slots=%d\n", generator, count, spawned, kRainRockSlots);
            std::fflush(stdout);
            break;
        }
        float ox = 0.0f, oz = 0.0f;
        P2DangoMushiHazardPolicy::rockOffset(i, count, angle, &ox, &oz);
        P2RockHazardInit init;
        init.position = { center.x + ox, center.y + kRainSpawnHeight, center.z + oz };
        init.dropGroupNone = false; // DropWait -> immediate Fall
        init.timedAppear = false;
        init.initialTimer = 0.0f;
        init.sourceToken = actor
            ? static_cast<std::uint64_t>(reinterpret_cast<std::uintptr_t>(actor)) : 0;
        init.selfToken = s.rainRockSelf++;
        s.rainRock[slot].reset(config);
        if (!s.rainRock[slot].onInit(init)) continue;
        s.rainRockUsed[slot] = true;
        s.rainRockDeadTimer[slot] = 0.0f;
        s.rainRockMaxLife[slot] = lifetime;
        s.rainRockAge[slot] = 0.0f;
        s.rainRockLifetimeExpired[slot] = false;
        s.rainRockPrev[slot] = s.rainRock[slot].phase();
        s.rainContacts[slot].clear();
        ++spawned;
    }
    std::printf("P2_DANGOMUSHI_ROCK_BIRTH generator=%u requested=%d real=%d lifetime=%.1f\n",
                generator, count, spawned, lifetime);
    std::fflush(stdout);
}

void spawnRainEgg(Dango& s, const Vector3f& home, unsigned generator) {
    // Only one Egg can be live per Crawbster; a second request while the first
    // has not broken must not reset() it (that would discard its pending drop).
    if (s.rainEggActive) return;
    s.rainEgg.reset(rainEggConfig());
    s.rainEggPos = { home.x, home.y, home.z };
    if (!s.rainEgg.birth(true)) { // drop-group: a Navi/Piki touch breaks it
        std::printf("P2_DANGOMUSHI_EGG_BIRTH generator=%u real=0\n", generator);
        std::fflush(stdout);
        return;
    }
    s.rainEggActive = true;
    std::printf("P2_DANGOMUSHI_EGG_BIRTH generator=%u real=1 x=%.1f y=%.1f z=%.1f health=%.1f\n",
                generator, home.x, home.y, home.z, rainEggConfig().health);
    std::fflush(stdout);
}

void applyRainRockContact(Dango& s, int slot, P2RockHazardContactKind kind,
                          Creature* target, BTeki* owner, unsigned generator) {
    const std::uint64_t token = rainToken(target);
    const P2RockHazardContactResult result =
        s.rainRock[slot].contact(kind, rainOnFloor(*target), false, token);
    // Do not dedupe a contact ignored by the source 1 s atari grace, or it would
    // be skipped forever for this rock once the grace expires.
    if (result.ignored) return;
    if (!s.rainContacts[slot].insert(token).second) return;
    if (result.strikeEmitted) {
        if (result.strike.kind == P2RockHazardStrikeKind::Press) {
            target->stimulate(InteractPress(owner, result.strike.damage));
        } else {
            target->stimulate(InteractAttack(owner, nullptr, result.strike.damage, false));
        }
        std::printf("P2_DANGOMUSHI_ROCK_STRIKE generator=%u kind=%s damage=%.1f target=%llu\n",
                    generator,
                    result.strike.kind == P2RockHazardStrikeKind::Press ? "Press" : "Attack",
                    result.strike.damage, static_cast<unsigned long long>(token));
        std::fflush(stdout);
    }
}

void birthRainEggDrop(Dango& s, unsigned generator) {
    const P2EggDrop& drop = s.rainEgg.drop();
    const Vector3f base(s.rainEggPos.x, s.rainEggPos.y + drop.positionOffsetY, s.rainEggPos.z);
    for (int i = 0; i < drop.itemCount && i < 2; ++i) {
        const P2EggItem& item = drop.items[i];
        P2EggSpawnKind kind = item.kind;
        bool fallback = false;
        if (kind == P2EggSpawnKind::MititeGroup && drop.mititeFallbackToNectar) {
            kind = P2EggSpawnKind::Nectar; // P1 has no Mitite manager
            fallback = true;
        }
        bool birthed = false;
        const char* born = "none";
        if (kind == P2EggSpawnKind::PelletOne || kind == P2EggSpawnKind::PelletFive) {
            if (pelletMgr) {
                Pellet* pellet = pelletMgr->newNumberPellet(
                    item.pelletColor,
                    kind == P2EggSpawnKind::PelletFive ? NUMPEL_FivePellet : NUMPEL_OnePellet);
                if (pellet) {
                    pellet->init(base);
                    pellet->mVelocity.set(item.velocity.x, item.velocity.y, item.velocity.z);
                    pellet->startAI(0);
                    birthed = true;
                    born = "pellet";
                }
            }
        } else if (kind == P2EggSpawnKind::Nectar) {
            if (itemMgr) {
                Creature* nectar = itemMgr->birth(OBJTYPE_Water);
                if (nectar) {
                    nectar->init(base);
                    nectar->startAI(0);
                    birthed = true;
                    born = "nectar";
                }
            }
        } else {
            born = "unsupported";
        }
        std::printf("P2_DANGOMUSHI_EGG_ITEM generator=%u index=%d kind=%d real=%d fallback=%d "
                    "item=%s\n", generator, i, int(item.kind), int(birthed), int(fallback), born);
    }
    std::fflush(stdout);
}

void tickRain(Dango& s, BTeki* actor, const Vector3f& pos, float dt) {
    s.rainDebt += dt;
    int ticks = static_cast<int>(s.rainDebt / kRainDelta);
    if (ticks > 6) ticks = 6;
    s.rainDebt -= ticks * static_cast<double>(kRainDelta);
    if (ticks <= 0) return;
    const unsigned campaignToken = pc_p2_campaign_token(actor);
    const unsigned generator = campaignToken ? campaignToken
        : (actor->mGenerator ? actor->mGenerator->_70 : 0u);
    const P2RockHazardConfig config = rainRockConfig();
    const float radiusSq = (config.collisionRadius + kRainContactPad)
        * (config.collisionRadius + kRainContactPad);

    for (int tick = 0; tick < ticks; ++tick) {
        for (int k = 0; k < kRainRockSlots; ++k) {
            if (!s.rainRockUsed[k]) continue;
            P2RockHazard& rock = s.rainRock[k];
            if (rock.phase() == P2RockHazardPhase::Killed) {
                s.rainRockUsed[k] = false;
                s.rainContacts[k].clear();
                continue;
            }
            if (!rock.isAlive()) {
                if (rock.phase() == P2RockHazardPhase::Dead) {
                    s.rainRockDeadTimer[k] += kRainDelta;
                    if (s.rainRockDeadTimer[k] >= 0.5f && rock.finishDeath()) {
                        std::printf("P2_DANGOMUSHI_ROCK_DESTROY generator=%u slot=%d "
                                    "reason=%s\n", generator, k,
                                    s.rainRockLifetimeExpired[k] ? "lifetime"
                                        : (rock.health() <= 0.0f ? "health" : "floor"));
                        std::fflush(stdout);
                    }
                }
                continue;
            }
            // Source birthArg.mExistenceLength 30 s: a rock that never traces a
            // floor still dies and releases its pool slot after its lifetime.
            s.rainRockAge[k] += kRainDelta;
            if (s.rainRockMaxLife[k] > 0.0f && s.rainRockAge[k] >= s.rainRockMaxLife[k]) {
                rock.forceDeath();
                s.rainRockLifetimeExpired[k] = true;
                if (rock.phase() != s.rainRockPrev[k]) {
                    std::printf("P2_DANGOMUSHI_ROCK_PHASE generator=%u slot=%d phase=%d\n",
                                generator, k, int(rock.phase()));
                    std::fflush(stdout);
                    s.rainRockPrev[k] = rock.phase();
                }
                continue;
            }
            const P2RockHazardVec3 before = rock.position();
            rock.update(kRainDelta, p2rockhost::detectRock(before, config.sightRadius),
                        p2rockhost::RockMapBinding::trace, &gRainBinding);
            if (rock.phase() != s.rainRockPrev[k]) {
                std::printf("P2_DANGOMUSHI_ROCK_PHASE generator=%u slot=%d phase=%d\n",
                            generator, k, int(rock.phase()));
                std::fflush(stdout);
                s.rainRockPrev[k] = rock.phase();
            }
            const P2RockHazardVec3 rp = rock.position();
            auto consider = [&](Creature* creature, P2RockHazardContactKind kind) {
                if (!creature || !creature->isAlive()) return;
                const Vector3f& q = creature->mSRT.t;
                const float dx = q.x - rp.x, dy = q.y - rp.y, dz = q.z - rp.z;
                if (dx * dx + dy * dy + dz * dz > radiusSq) return;
                applyRainRockContact(s, k, kind, creature, actor, generator);
            };
            for (Navi* navi : pc_p2_navis()) consider(navi, P2RockHazardContactKind::NaviPiki);
            if (pikiMgr) {
                Iterator pikiIt(pikiMgr);
                CI_LOOP(pikiIt) {
                    consider(static_cast<Piki*>(*pikiIt), P2RockHazardContactKind::NaviPiki);
                }
            }
            if (tekiMgr) {
                Iterator tekiIt(tekiMgr);
                CI_LOOP(tekiIt) {
                    consider(static_cast<Teki*>(*tekiIt), P2RockHazardContactKind::Teki);
                }
            }
        }

        if (s.rainEggActive) {
            bool touched = false;
            auto near = [&](const Creature* creature) {
                const Vector3f& p = creature->mSRT.t;
                const float dx = p.x - s.rainEggPos.x, dy = p.y - s.rainEggPos.y;
                const float dz = p.z - s.rainEggPos.z;
                return dx * dx + dy * dy + dz * dz
                    <= kRainEggContactRadius * kRainEggContactRadius;
            };
            for (Navi* navi : pc_p2_navis())
                if (navi->isAlive() && near(navi)) { touched = true; break; }
            if (!touched && pikiMgr) {
                Iterator it(pikiMgr);
                CI_LOOP(it) {
                    Piki* piki = static_cast<Piki*>(*it);
                    if (piki && piki->isAlive() && near(piki)) { touched = true; break; }
                }
            }
            if (touched && s.rainEgg.contact(false, false)) {
                std::printf("P2_DANGOMUSHI_EGG_CONTACT generator=%u health=0\n", generator);
                std::fflush(stdout);
            }
            if (s.rainEgg.health() <= 0.0f
                && s.rainEgg.update(p2rockhost::rngFloat, &s.rainRng, p2rockhost::rngInt, &s.rainRng)) {
                birthRainEggDrop(s, generator);
                s.rainEggActive = false;
            }
        }
    }
}
}

namespace { void loadCarcassRow(); }

void pc_p2_dangomushi_reset() {
    actors.clear();
    clips.clear();
    rollStartFrame = FALLBACK_ROLL_START;
    flickStartFrame = FALLBACK_FLICK_START;
    ready = false;
}
void pc_p2_dangomushi_forget(BTeki* actor) {
    // Lane 06 single-use binding: drop the ordinary-delivery source so a
    // recycled actor address can never inherit it. Idempotent with the
    // central pc_p2_forget_teki seam.
    pc_randomizer_p2_forget_source(static_cast<PelletView*>(actor));
    actors.erase(static_cast<PelletView*>(actor));
}

float pc_p2_dangomushi_param_f(const BTeki* actor, int idx, float fallback) {
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

bool pc_p2_dangomushi_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    // Draw evidence: one line per clip change of the drawn P2 model.
    if (it->second.drawnClip != it->second.clip) {
        it->second.drawnClip = it->second.clip;
        std::printf("P2_DANGOMUSHI_CLIP_DRAW generator=%u clip=%s phase=%.2f state=%s\n",
                    tokenOf(const_cast<BTeki*>(actor)), name, phase, stateName(it->second.state));
        std::fflush(stdout);
    }
    return true;
}
bool pc_p2_dangomushi_probe(const BTeki* actor, const char** state, bool* rolling, bool* stickable,
                            float* driveX, float* driveZ) {
    if (!ready || !actor) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    const Dango& s = it->second;
    if (state) *state = stateName(s.state);
    if (rolling) *rolling = s.rolling;
    if (stickable) *stickable = s.stickable;
    if (driveX) *driveX = s.driveX;
    if (driveZ) *driveZ = s.driveZ;
    return true;
}
bool pc_p2_dangomushi_suppress_ai(const BTeki* actor) {
    return ready && actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor))) != 0;
}

bool pc_p2_dangomushi_invulnerable(const BTeki* actor) {
    if (!ready || !actor) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    Dango& s = it->second;
    const unsigned campaignToken = pc_p2_campaign_token(const_cast<BTeki*>(actor));
    const unsigned generator = campaignToken ? campaignToken
        : (actor->mGenerator ? actor->mGenerator->_70 : 0u);
    if (!P2DangoMushiHazardPolicy::attackRejected(s.stickable)) {
        // Inside the Turn stickable window: EB_Invulnerable is clear and the
        // attack is admitted (return false so the normal damage path runs).
        std::printf("P2_DANGOMUSHI_DAMAGE_ACCEPTED generator=%u stickable=1 state=%s\n",
                    generator, stateName(s.state));
        std::fflush(stdout);
        return false;
    }
    // Outside the window the source body is invulnerable. Report the first
    // rejection per window so the fixture can observe an applied (not merely
    // decided) window without spamming every attack frame.
    if (!s.attackRejectedLogged) {
        s.attackRejectedLogged = true;
        std::printf("P2_DANGOMUSHI_DAMAGE_REJECTED generator=%u stickable=0 invulnerable=1 "
                    "state=%s\n", generator, stateName(s.state));
        std::fflush(stdout);
    }
    return true;
}

void pc_p2_dangomushi_setup() {
    pc_p2_dangomushi_reset();
    gRainBinding.reset(mapMgr);
    if (!tekiMgr) return;
    loadCarcassRow();

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
                    std::string species, name, events, marker, status, value;
                    long long frames = 0;
                    int poses = 0;
                    if (!(bank >> species >> name >> frames >> events >> marker >> poses)) break;
                    if (!(bank >> value)) break;
                    if (value != "status") status = value;
                    else if (!(bank >> status)) break;
                    if (species == "DangoMushi") {
                        Clip clip;
                        clip.name = name;
                        clip.duration = frames > 0 ? float(frames) / 30.0f : 1.0f;
                        clip.loop = p2dango::clipLoops(name.c_str());
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
    }
    const int roll = eventFrame("attack", 4);
    const int flick = eventFrame("attack_2", 2);
    if (roll >= 0) rollStartFrame = roll;
    if (flick >= 0) flickStartFrame = flick;

    std::ifstream in("p2-snagret-actors.txt");
    if (!in) return;
    std::string header;
    int count = 0;
    if (!(in >> header >> count) || header != "P2_SNAGRET_ACTORS_1" || count < 1) return;
    std::map<unsigned, std::string> wanted;
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        std::string species;
        if (!(in >> generator >> species)) return;
        if (species == "DangoMushi") wanted[unsigned(generator)] = species;
    }
    // inst-bugs lane (#871): in bridge campaigns the seed owns the binding,
    // so the filed ids are placeholders replaced from pc_p2_campaign_ids(94)
    // (mirrors pc_p2_sokkuri_setup). Actors match by campaign token: scene
    // members may carry no mGenerator, exactly like the batch-2 bind.
    const bool bridge = pc_randomizer_p2_bridge();
    if (bridge) {
        wanted.clear();
        for (unsigned id : pc_p2_campaign_ids(94)) wanted[id] = "DangoMushi";
    }
    if (wanted.empty()) return;

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
        // Campaign vehicle is TEKI_Swallow (proxy row host_teki 4); the arena
        // path keeps whatever the sidecar staged on (historically Chappy).
        const int wantType = bridge ? TEKI_Swallow : TEKI_Chappy;
        if (actor->mTekiType != wantType) {
            std::printf("P2_DANGOMUSHI_ERROR native_type generator=%u\n", key);
            if (pc_p2_setup_skip(bridge, "DangoMushi", "actor_type_mismatch")) return;
            std::abort();
        }
        Dango& s = actors[static_cast<PelletView*>(actor)];
        s.hazard.reset(P2DangoMushiHazardParms{});
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        s.moveTarget = s.home;
        actor->mHealth = LIFE;
        enter(s, DANGO_STAY, "wait");
        if (stayHides()) setHidden(actor, s, true);
        // Ordinary-delivery bridge (lane 06 contract): bind source 94 so
        // GoalItem::suckMe grants onion:p2:94 exactly once. Single-use.
        pc_randomizer_p2_bind_source(static_cast<PelletView*>(actor), 94, key);
        std::printf("P2_DANGOMUSHI_DELIVERY_BIND generator=%u source_id=94\n", key);
        std::printf("P2_DANGOMUSHI_BIND generator=%u source_id=94 visual_only=0\n", key);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=DangoMushi native_family=Swallow generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=interactpress_roll\n",
                    key, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        std::printf("P2_DANGOMUSHI_STATE generator=%u state=stay clip=%s\n", key,
                    s.clip.c_str());
        std::printf("P2_DANGO_STATE generator=%u state=stay clip=%s loop=%d hidden=%d\n", key,
                    s.clip.c_str(), p2dango::clipLoops(s.clip.c_str()) ? 1 : 0, int(s.hidden));
        std::fflush(stdout);
        found.insert(key);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_DANGOMUSHI_ERROR missing_actor wanted=%zu found=%zu\n",
                    wanted.size(), found.size());
        if (pc_p2_setup_skip(bridge, "DangoMushi", "actor_roster_incomplete")) return;
        std::abort();
    }
    ready = true;
}

namespace {
// P2 retail carcass_config.txt row "DangoMushi" (GPVE01 rev 0,
// user/Abe/Pellet/us/carcass_config.txt: min 20, max 30, pikicountmin/max 30).
// The root extractor stages the row as p2-dangomushi-carcass.txt; these are
// the audited fallbacks when the sidecar is absent.
struct CarcassRow { int min = 20, max = 30, seeds = 30; const char* source = "fallback"; };
CarcassRow gCarcass;

void loadCarcassRow() {
    gCarcass = CarcassRow();
    std::ifstream in("p2-dangomushi-carcass.txt");
    std::string header;
    int mn = 0, mx = 0, seeds = 0;
    if (in && (in >> header >> mn >> mx >> seeds) && header == "P2_DANGOMUSHI_CARCASS_1"
            && mn > 0 && mx >= mn && mx <= 100 && seeds > 0 && seeds <= 100) {
        gCarcass.min = mn;
        gCarcass.max = mx;
        gCarcass.seeds = seeds;
        gCarcass.source = "staged";
    }
    std::printf("P2_DANGOMUSHI_CARCASS_ROW source=%s min=%d max=%d seeds=%d\n", gCarcass.source,
                gCarcass.min, gCarcass.max, gCarcass.seeds);
    std::fflush(stdout);
}

// Fresh Parameters chain; never copy the intrusive CoreNode links (same
// private-config pattern as pc_p2_cave_items.cpp / pc_p2_preview.cpp). One
// private config per host config for the process lifetime (Pellet::initPellet
// resets mConfig on reuse, so the host's own config is never mutated).
PelletConfig* carcassConfig(PelletConfig* source) {
    static std::map<PelletConfig*, PelletConfig*> cache;
    auto hit = cache.find(source);
    if (hit != cache.end()) {
        hit->second->mCarryMinPikis.mValue = gCarcass.min;
        hit->second->mCarryMaxPikis.mValue = gCarcass.max;
        hit->second->mMatchingOnyonSeeds.mValue = gCarcass.seeds;
        hit->second->mNonMatchingOnyonSeeds.mValue = gCarcass.seeds;
        return hit->second;
    }
    PelletConfig* result = new PelletConfig;
#define COPY_VALUE(name) result->name.mValue = source->name.mValue
    COPY_VALUE(mPelletName);
    COPY_VALUE(mPelletType);
    COPY_VALUE(mPelletColor);
    COPY_VALUE(mUseDynamicMotion);
    COPY_VALUE(_A0);
    COPY_VALUE(_B0);
    COPY_VALUE(_C0);
    COPY_VALUE(mPelletScale);
    COPY_VALUE(mCarryInfoHeight);
    COPY_VALUE(mAnimSoundID);
    COPY_VALUE(mBounceSoundID);
#undef COPY_VALUE
    result->mModelId = source->mModelId;
    result->mPelletId = source->mPelletId;
    result->mUnusedId = source->mUnusedId;
    result->mRepairAnimJointIndex = source->mRepairAnimJointIndex;
    result->mCarryMinPikis.mValue = gCarcass.min;
    result->mCarryMaxPikis.mValue = gCarcass.max;
    result->mMatchingOnyonSeeds.mValue = gCarcass.seeds;
    result->mNonMatchingOnyonSeeds.mValue = gCarcass.seeds;
    cache.emplace(source, result);
    return result;
}

// Called in the same update tick as pcEscapeNow(): becomePellet creates the
// corpse pellet there, so no Pikmin AI tick can attach carriers while the
// host config is still installed.
void applyCarcass(BTeki* actor, Dango& s, unsigned generator) {
    if (s.carcassApplied) return;
    Pellet* pellet = actor->mPellet;
    if (!pellet || !pellet->mConfig) return;
    s.carcassApplied = true;
    PelletConfig* host = pellet->mConfig;
    const int hostMin = host->mCarryMinPikis();
    const int hostMax = host->mCarryMaxPikis();
    const int hostSeeds = host->mMatchingOnyonSeeds();
    const int carriers = int(pellet->mCarrierCount);
    pellet->mConfig = carcassConfig(host);
    std::printf("P2_DANGOMUSHI_CARCASS generator=%u source=carcass_config.txt:DangoMushi:%s "
                "min=%d max=%d seeds=%d host_min=%d host_max=%d host_seeds=%d "
                "carriers_at_swap=%d\n", generator, gCarcass.source, gCarcass.min, gCarcass.max,
                gCarcass.seeds, hostMin, hostMax, hostSeeds, carriers);
    std::fflush(stdout);
}
} // namespace

void pc_p2_dangomushi_wall(BTeki* actor, const Plane& plane) {
    if (!ready || !actor) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Dango& s = it->second;
    if (s.state != DANGO_ATTACK || !s.rolling) return;
    s.wallTouched = true;
    const Vector3f& n = plane.mNormal;
    if (!p2dango::wallCrash(true, s.driveX, 0.0f, s.driveZ, n.x, n.y, n.z)) return;
    const unsigned generator = tokenOf(actor);
    const float speed = std::sqrt(s.driveX * s.driveX + s.driveZ * s.driveZ);
    const float dot = speed > 0.0f ? (s.driveX * n.x + s.driveZ * n.z) / speed : 0.0f;
    const Vector3f pos = actor->getPosition();
    std::printf("P2_DANGOMUSHI_WALL_CRASH generator=%u speed=%.1f dot=%.3f nx=%.3f ny=%.3f "
                "nz=%.3f t=%.2f roll_targets=%zu x=%.1f z=%.1f\n", generator, speed, dot, n.x, n.y,
                n.z, s.stateTime, s.rollTargets.size(), pos.x, pos.z);
    std::fflush(stdout);
    logCrushTally(s, generator, "wall_crash");
    pc_p2_sfx(94, generator, p2sfx::Event::Crash, actor);
    // mFsm->transit(this, DANGOMUSHI_Turn) straight from the wall callback.
    stop(actor);
    setState(actor, s, DANGO_TURN, "turn");
}

float pc_p2_dangomushi_cull_radius(Creature* creature) {
    if (!ready || !creature || creature->mObjType != OBJTYPE_Pellet) return 0.0f;
    Pellet* pellet = static_cast<Pellet*>(creature);
    if (!pellet->mPelletView) return 0.0f;
    auto it = actors.find(pellet->mPelletView);
    if (it == actors.end() || !it->second.escaped) return 0.0f;
    // P2 culls the DangoMushi by its LOD radius (enemyparm fp32 = 250,
    // user/Abe/... DangoMushi EnemyParmsBase), which covers the 200-unit
    // enemycoll root sphere; keep the corpse on screen as long as that is.
    return 250.0f;
}

void pc_p2_dangomushi_draw_rain(Graphics& gfx) {
    if (!ready || actors.empty() || !gfx.mCamera || !tekiMgr) return;
    // #897 carry diagnosis: the P1 DualCreature::refresh frustum test that
    // gates the corpse pellet's draw, evaluated here once a second.
    static unsigned cullFrame = 0;
    if (++cullFrame % 60u == 0u) {
        for (auto& entry : actors) {
            if (!entry.second.escaped) continue;
            Pellet* pellet = static_cast<BTeki*>(entry.first)->mPellet;
            if (!pellet) continue;
            const Vector3f& p = pellet->mSRT.t;
            const float radius = pellet->getBoundingSphereRadius();
            Camera& cam = *gfx.mCamera;
            int worst = -1;
            float worstD = 1e9f;
            for (int i = 0; i < cam.mActivePlaneCount; ++i) {
                const Plane& pl = cam.mPlanePointers[i]->mPlane;
                const float d = p.x * pl.mNormal.x + p.y * pl.mNormal.y + p.z * pl.mNormal.z - pl.mOffset;
                if (d < worstD) { worstD = d; worst = i; }
            }
            std::printf("P2_DANGOMUSHI_CORPSE_CULL visible=%d radius=%.1f planes=%d worst=%d d=%.1f "
                        "px=%.1f py=%.1f pz=%.1f\n", int(cam.isPointVisible(p, 2.0f * radius)), radius,
                        cam.mActivePlaneCount, worst, worstD, p.x, p.y, p.z);
        }
    }
    bool any = false;
    for (auto& entry : actors) {
        const Dango& s = entry.second;
        if (s.rainEggActive) any = true;
        for (int k = 0; k < kRainRockSlots && !any; ++k)
            if (s.rainRockUsed[k] && s.rainRock[k].isAlive()) any = true;
        if (any) break;
    }
    if (!any) return;
    TekiShapeObject* so = tekiMgr->getTekiShapeObject(TEKI_Iwagon);
    Shape* shape = so ? so->mShape : nullptr;
    if (!shape) return;
    AnimData* const sharedAnim = so->mAnimContext.mData;
    AnimData* const shapeAnim = shape->mCurrentAnimation ? shape->mCurrentAnimation->mData : nullptr;
    AnimData* const drawAnim = sharedAnim ? sharedAnim : shapeAnim;
    if (!drawAnim) return;
    const float savedFrame = so->mAnimContext.mCurrentFrame;
    so->mAnimContext.mData = drawAnim;
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov,
                       gfx.mCamera->mAspectRatio, gfx.mCamera->mNear, gfx.mCamera->mFar, 1.f);
    gfx.useMaterial(nullptr);
    gfx.setDepth(true);
    // Scale from the stand-in mesh's own extent (bind-pose vertices), not an
    // assumed radius: the P2 Rock outer collision radius is 40
    // (rock/enemycoll.txt), the Egg ~25.
    static float meshRadius = -1.0f;
    if (meshRadius < 0.0f) {
        float lo[3] = {1e9f, 1e9f, 1e9f}, hi[3] = {-1e9f, -1e9f, -1e9f};
        for (int i = 0; i < shape->mVertexCount; ++i) {
            const Vector3f& v = shape->mVertexList[i];
            const float c[3] = {v.x, v.y, v.z};
            for (int k = 0; k < 3; ++k) { if (c[k] < lo[k]) lo[k] = c[k]; if (c[k] > hi[k]) hi[k] = c[k]; }
        }
        float r = 0.0f;
        for (int k = 0; k < 3; ++k) if ((hi[k] - lo[k]) * 0.5f > r) r = (hi[k] - lo[k]) * 0.5f;
        meshRadius = r > 1.0f ? r : 24.0f;
        std::printf("P2_DANGOMUSHI_ROCK_MESH iwagon_radius=%.1f rock_radius=40.0 scale=%.3f\n",
                    meshRadius, 40.0f / meshRadius);
        std::fflush(stdout);
    }
    auto drawAt = [&](float x, float y, float z, float k) {
        Matrix4f world, view;
        world.makeSRT(Vector3f(k, k, k), Vector3f(0.0f, 0.0f, 0.0f), Vector3f(x, y, z));
        gfx.mCamera->mLookAtMtx.multiplyTo(world, view);
        float frame = 0.0f; // pinned: the shared Iwagon animator is not advanced
        shape->updateAnim(gfx, view, &frame, nullptr);
        shape->drawshape(gfx, *gfx.mCamera, nullptr);
    };
    for (auto& entry : actors) {
        Dango& s = entry.second;
        int rocks = 0;
        for (int k = 0; k < kRainRockSlots; ++k) {
            if (!s.rainRockUsed[k]) continue;
            const P2RockHazard& rock = s.rainRock[k];
            if (!rock.isAlive() || rock.modelHidden()) continue;
            const P2RockHazardVec3 p = rock.position();
            drawAt(p.x, p.y, p.z, (40.0f / meshRadius) * rock.scale());
            ++rocks;
        }
        if (s.rainEggActive)
            drawAt(s.rainEggPos.x, s.rainEggPos.y + 20.0f, s.rainEggPos.z, 25.0f / meshRadius);
        const int turn = s.hazard.turns();
        if (rocks > 0 && s.rockDrawTurn != turn) {
            s.rockDrawTurn = turn;
            std::printf("P2_DANGOMUSHI_ROCK_DRAW generator=%u turn=%d rocks=%d egg=%d "
                        "model=iwagon_standin\n", tokenOf(static_cast<BTeki*>(entry.first)), turn,
                        rocks, int(s.rainEggActive));
            std::fflush(stdout);
        }
    }
    so->mAnimContext.mData = sharedAnim;
    so->mAnimContext.mCurrentFrame = savedFrame;
}

void pc_p2_dangomushi_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Dango& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = tokenOf(actor);

    // The P1 TAI damage reaction lives in the suppressed host strategy, so
    // the P2 FSM drains queued Pikmin damage itself (frog pattern). The Turn
    // stickable-window gate (pc_p2_dangomushi_invulnerable) still swallows
    // attack/bomb interactions outside the window; this applies admitted damage.
    s.healthLogTimer -= dt;
    if (actor->mStoredDamage > 0.0f) {
        const float before = actor->mHealth;
        actor->makeDamaged();
        if (actor->mHealth < before && actor->mHealth > 0.0f)
            pc_p2_sfx(94, generator, p2sfx::Event::Damage, actor);
        if (actor->mHealth != before && (s.healthLogTimer <= 0.0f || actor->mHealth <= 0.0f)) {
            s.healthLogTimer = 0.5f;
            std::printf("P2_DANGOMUSHI_HEALTH generator=%u health=%.1f before=%.1f state=%s "
                        "stickable=%d\n", generator, actor->mHealth,
                        s.lastLoggedHealth >= 0.0f ? s.lastLoggedHealth : before,
                        stateName(s.state), int(s.stickable));
            std::fflush(stdout);
            s.lastLoggedHealth = actor->mHealth;
        }
    }

    // StateTurn::exec (DangoMushiState.cpp:510): health 0 only sets
    // mNextState=Dead and finishMotion(); the turn tail plays out and END
    // transits (handled in DANGO_TURN). Every other state transits at once.
    if (actor->mHealth <= 0.0f && s.state != DANGO_DEAD && s.state != DANGO_TURN) {
        if (!s.deadLogged) {
            std::printf("P2_DANGOMUSHI_DEAD generator=%u source_id=94 health=0 from=%s\n",
                        generator, stateName(s.state));
            std::fflush(stdout);
            s.deadLogged = true;
        }
        setState(actor, s, DANGO_DEAD, "dead");
    }

    s.stateTime += dt;
    switch (s.state) {
    case DANGO_STAY:
        stop(actor);
        // Source StateStay::exec (DangoMushiState.cpp:111-142): once a captain or
        // Pikmin is inside the private radius the ground shadow starts growing
        // (mShadowScale += 0.6 dt, Obj::addShadowScale); it keeps growing whether or
        // not the target stays, and at 1.0 (1.67 s) the crab transits to Appear.
        if (s.shadowScale <= 0.0f && nearestTarget(pos, PRIVATE_RADIUS)) {
            s.shadowScale = 0.0001f;
            std::printf("P2_DANGO_STAY_WAKE generator=%u radius=%.0f hidden=%d\n", generator,
                        PRIVATE_RADIUS, int(s.hidden));
            std::fflush(stdout);
        }
        if (s.shadowScale > 0.0f) {
            s.shadowScale += 0.6f * dt;
            if (s.shadowScale >= 1.0f) {
                s.shadowScale = 1.0f;
                setHidden(actor, s, false); // StateAppear::init disableEvent(EB_ModelHidden)
                setState(actor, s, DANGO_APPEAR, "fly");
            }
        }
        break;
    case DANGO_APPEAR:
        stop(actor);
        if (s.stateTime >= clipDuration("fly")) {
            Creature* target = nearestTarget(pos, SIGHT);
            if (target && canAttack(pos, s, target)) {
                setState(actor, s, DANGO_ATTACK, "attack");
            } else if (target) {
                setRandTarget(s);
                setState(actor, s, DANGO_MOVE, "move");
            } else {
                setState(actor, s, DANGO_WAIT, "wait");
            }
        }
        break;
    case DANGO_WAIT: {
        stop(actor);
        // StateWait::exec: pick Attack/Move, finishMotion(); the wait clip plays
        // out to END before the transit (DangoMushiState.cpp:250-284).
        Creature* target = nearestTarget(pos, SIGHT);
        if (target) {
            advanceFinish(actor, s, canAttack(pos, s, target) ? DANGO_ATTACK : DANGO_MOVE);
        } else if (s.stateTime > WAIT_TIME) {
            advanceFinish(actor, s, DANGO_MOVE);
        }
        break;
    }
    case DANGO_MOVE: {
        // StateMove::exec (DangoMushiState.cpp:311-372).
        Creature* target = nearestTarget(pos, SIGHT);
        if (target) {
            if (canAttack(pos, s, target)) {
                advanceFinish(actor, s, DANGO_ATTACK);
            } else {
                // Turn toward the target; walk only once within the fp21 cone.
                const Vector3f tp = target->getPosition();
                const bool lined = std::fabs(wrapPi(std::atan2(tp.x - pos.x, tp.z - pos.z)
                                                    - s.heading)) <= ATTACK_ANGLE;
                turnAndMove(actor, s, tp, MOVE_SPEED, WALK_TURN_RATE, WALK_MAX_TURN, lined);
            }
        } else if (distXZ(pos, s.moveTarget) < MOVE_ARRIVE || s.stateTime > MOVE_TIMEOUT) {
            advanceFinish(actor, s, DANGO_WAIT);
        } else {
            const bool lined = std::fabs(wrapPi(std::atan2(s.moveTarget.x - pos.x,
                                                           s.moveTarget.z - pos.z) - s.heading))
                               <= 30.0f * PI / 180.0f;
            turnAndMove(actor, s, s.moveTarget, MOVE_SPEED, WALK_TURN_RATE, WALK_MAX_TURN, lined);
        }
        if (s.finishAt >= 0.0f) stop(actor); // isFinishMotion -> velocity 0
        break;
    }
    case DANGO_ATTACK: {
        const float frame = s.stateTime * 30.0f;
        const p2dango::AttackClock clock = p2dango::attackClock(
            s.stateTime, s.attackFinishAt, clips.count("attack")
                ? int(std::lround(clipDuration("attack") * 30.0f)) : p2dango::kAttackClipFrames);
        if (!s.rolling && !clock.tail && frame >= float(rollStartFrame)) {
            s.rolling = true;
            s.crush.reset();
            s.rollTargets.clear();
            s.rollCrushed.clear();
            std::printf("P2_DANGOMUSHI_ROLL generator=%u frame=%.1f x=%.1f z=%.1f\n",
                        generator, float(rollStartFrame), pos.x, pos.z);
            std::fflush(stdout);
            pc_p2_sfx(94, generator, p2sfx::Event::Roll, actor);
        }
        if (s.rolling && clock.tail) {
            // KEYEVENT_LOOP_END after finishMotion: mIsRolling/mIsBall clear.
            s.rolling = false;
            logCrushTally(s, generator, "roll_end");
            std::printf("P2_DANGOMUSHI_ROLL_STOP generator=%u frame=%.1f t=%.2f\n", generator,
                        clock.frame, s.stateTime);
            std::fflush(stdout);
        }
        if (s.rolling) {
            rollingMove(actor, s, pos);
            // Source rollingMove advances mStateTimer 1x, or 3x/5x (slow) while
            // the body is against a wall (DangoMushi.cpp:428-437).
            {
                const float spd = std::sqrt(actor->mVelocity.x * actor->mVelocity.x
                                            + actor->mVelocity.z * actor->mVelocity.z);
                s.rollTimer += dt * (s.wallTouched ? (spd < 100.0f ? 5.0f : 3.0f) : 1.0f);
                s.wallTouched = false;
            }
            rollCrush(actor, s, pos, generator);
            // Turn only comes from pc_p2_dangomushi_wall (Obj::wallCallback).
            if (s.attackFinishAt < 0.0f
                    && p2dango::rollExit(s.rollTimer, false, distXZ(pos, s.home))
                    == p2dango::RollExit::Wait) {
                // StateAttack::exec 15 s: finishMotion, the loop runs out.
                s.attackFinishAt = s.stateTime;
                std::printf("P2_DANGOMUSHI_ROLL_END generator=%u reason=timeout t=%.2f "
                            "roll_targets=%zu\n", generator, s.stateTime, s.rollTargets.size());
                std::fflush(stdout);
            }
        } else {
            stop(actor);
        }
        if (clock.finished) setState(actor, s, DANGO_WAIT, "wait");
        break;
    }
    case DANGO_TURN: {
        stop(actor);
        if (actor->mHealth <= 0.0f && !s.dyingInTurn) {
            // mNextState = Dead; finishMotion(): the running loop pass ends
            // at LOOP_END and the tail plays to END.
            s.dyingInTurn = true;
            if (s.stateTime < s.turnFlip) s.turnFlip = s.stateTime;
            std::printf("P2_DANGOMUSHI_TURN_DYING generator=%u t=%.2f frame=%.1f\n", generator,
                        s.stateTime, s.turnClock.frame);
            std::fflush(stdout);
        }
        s.turnClock = p2dango::turnClock(s.stateTime, s.turnFlip, turnClipFrames());
        // Lane-25 hazard policy fed the LOOPED turn frame (after key 3 the
        // tail frame is >= 108, so the window stays closed); createCrashEnemy
        // fires on the Turn entry tick.
        const float share = GameStat::allPikis > 0
            ? float(GameStat::formationPikis) / float(GameStat::allPikis) : 0.0f;
        P2DangoMushiHazardInput hz;
        hz.turnEntered = s.turnJustEntered;
        hz.turnFrame = s.turnClock.frame;
        hz.activeCaptainGroupShare = share;
        hz.eggRoll = gsys->getRand(1.0f);
        P2DangoMushiHazardOutput hzo;
        s.hazard.update(hz, hzo);
        if (hzo.stickable && !s.stickable) {
            s.attackRejectedLogged = false;
        }
        s.stickable = hzo.stickable;
        if (hzo.rocksToSpawn > 0) {
            std::printf("P2_DANGOMUSHI_HAZARD generator=%u turn=%d rocks=%d lifetime=%.1f egg=%d\n",
                        generator, hzo.turnIndex, hzo.rocksToSpawn, hzo.rockLifetime,
                        int(hzo.eggRequested));
            std::fflush(stdout);
            // Source getFallPosition(Rock): the active captain.
            Vector3f rainCentre = pos;
            if (naviMgr) {
                Navi* active = pc_p2_source_active_navi(pos); // DangoMushi.cpp:763
                if (active && active->isAlive()) rainCentre = active->getPosition();
            }
            spawnRainRocks(s, actor, rainCentre, gsys->getRand(PI), hzo.rocksToSpawn,
                           hzo.rockLifetime, generator);
        }
        if (hzo.eggRequested) {
            spawnRainEgg(s, s.home, generator);
        }
        if (hzo.stickable != s.hazardWindowLogged) {
            s.hazardWindowLogged = hzo.stickable;
            std::printf("P2_DANGOMUSHI_TURN_WINDOW generator=%u frame=%.1f t=%.2f stickable=%d "
                        "invulnerable=%d looping=%d tail=%d\n", generator, s.turnClock.frame,
                        s.stateTime, int(hzo.stickable), int(hzo.invulnerable),
                        int(s.turnClock.looping), int(s.turnClock.tail));
            std::fflush(stdout);
        }
        if (s.stickable) {
            const bool first = s.stickLogTimer <= 0.0f;
            s.stickLogTimer += dt;
            if (first || s.stickLogTimer >= 1.0f) {
                if (!first) s.stickLogTimer = 0.0001f;
                logStickSurface(actor, pos, generator, first);
            }
        } else {
            s.stickLogTimer = 0.0f;
        }
        s.turnJustEntered = false;
        if (!s.turnClosed && s.turnClock.closed) {
            // Key 3: EB_Invulnerable re-armed + setBodyCollision(true).
            s.turnClosed = true;
            shakeStickers(actor, s, generator);
        }
        if (!s.stickable) unstickOutsideWindow(actor, s, generator);
        if (s.turnClock.finished) {
            P2DangoMushiHazardInput exitInput;
            exitInput.turnExited = true;
            P2DangoMushiHazardOutput exitOutput;
            s.hazard.update(exitInput, exitOutput);
            s.stickable = exitOutput.stickable; // false: body is invulnerable again
            turnCleanup(actor, s, generator);
            if (s.dyingInTurn) {
                if (!s.deadLogged) {
                    std::printf("P2_DANGOMUSHI_DEAD generator=%u source_id=94 health=0 from=turn "
                                "tail_played=1\n", generator);
                    std::fflush(stdout);
                    s.deadLogged = true;
                }
                setState(actor, s, DANGO_DEAD, "dead");
            } else {
                setState(actor, s, DANGO_RECOVER, "recover");
            }
        }
        break;
    }
    case DANGO_RECOVER:
        stop(actor);
        if (s.stateTime >= clipDuration("recover")) {
            // Source StateRecover::exec KEYEVENT_END flips the facing direction.
            s.heading = wrapPi(s.heading + PI);
            actor->setDirection(s.heading);
            setState(actor, s, DANGO_FLICK, "attack_2");
        }
        break;
    case DANGO_FLICK: {
        stop(actor);
        const float frame = s.stateTime * 30.0f;
        const bool swinging = p2dango::armWindow(frame);
        if (swinging && !s.armSwinging) {
            ++s.flickWindow;
            s.flickHit.clear(); // each KEYEVENT_2 swing can hit again
        }
        s.armSwinging = swinging;
        if (s.armSwinging) flickSweep(actor, s, pos, generator, s.flickWindow);
        if (s.stateTime >= clipDuration("attack_2")) {
            setState(actor, s, DANGO_WAIT, "wait");
        }
        break;
    }
    case DANGO_DEAD:
        stop(actor);
        // dieSoon() only runs inside the suppressed host doAI; finalize the
        // corpse outside doAI once the dead clip completes (frog pattern).
        if (!s.escaped && s.stateTime >= clipDuration("dead")) {
            s.escaped = true;
            actor->pcEscapeNow();
        }
        if (s.escaped) applyCarcass(actor, s, generator);
        break;
    default:
        break;
    }
    if (s.state != DANGO_TURN && s.state != DANGO_DEAD) unstickOutsideWindow(actor, s, generator);
    if (s.state == DANGO_MOVE || (s.state == DANGO_ATTACK && !s.rolling))
        pc_p2_sfx_stride(94, generator, actor, 30.0f);
    setPhase(s);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        // After the carcass swap the teki stays at its death spot; the corpse
        // is the pellet, drawn through BTeki::viewDraw at the pellet's own
        // matrix. Log the pellet too so a carry can be checked against it.
        Pellet* corpsePellet = s.escaped ? actor->mPellet : nullptr;
        std::printf("P2_DANGOMUSHI_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f "
                    "health=%.1f corpse_pellet=%d px=%.2f py=%.2f pz=%.2f carriers=%d vis=%d pstate=%d pick=%.1f\n", generator,
                    stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z, actor->mHealth,
                    int(corpsePellet != nullptr), corpsePellet ? corpsePellet->mSRT.t.x : 0.0f,
                    corpsePellet ? corpsePellet->mSRT.t.y : 0.0f,
                    corpsePellet ? corpsePellet->mSRT.t.z : 0.0f,
                    corpsePellet ? int(corpsePellet->mCarrierCount) : 0,
                    corpsePellet ? int(corpsePellet->aiCullable()) : 0,
                    corpsePellet ? corpsePellet->getState() : -1,
                    corpsePellet ? corpsePellet->getPickOffset() : 0.0f);
        std::fflush(stdout);
    }
    // Step any live Rock/Egg children the hazard decisions created.
    tickRain(s, actor, pos, dt);
}

#else
// pc_p2_dangomushi.cpp -- DangoMushi profile/mesh/slot binding, slot 312004 (#678).
//
// Binds the #670-derived Damagumo/Demon profile+mesh for arena slot 312004
// under the #638 staging contract (installer accepts Damagumo ONLY from an
// explicit demon-lane 56 profile/mesh, hash-gated, never aliased).
//
// Source facts (verified #670 record; read-only refs, nothing reimplemented):
//   profile f9ec5030..., mesh 8fc0ac7f..., slot-312004 61019a39...,
//   15 joints, 4 textures, BCA rows landing/wait/flick/dead.
// Full artifact hashes are caller-supplied here: the emitted #670 artifact
// files are not present on disk in this workspace, so this TU takes expected
// hashes as explicit parameters and gates on exact match (fail-closed). The
// recorded prefixes above are cross-checks, not substitutes.
//
// Engine-free core (stdlib only): compiles standalone for contract review and
// links into the guarded fixture. Not wired into CMakeLists.txt by this lane
// (shared registration stays serialized); never linked into production here.

#include <cstdint>
#include <cstdio>
#include <cstring>

namespace p2_dangomushi {

constexpr int kSlotId = 312004;
constexpr int kEnemyId = 56;
constexpr int kJointCount = 15;
constexpr int kTextureCount = 4;
constexpr const char* kRecordedProfilePrefix = "f9ec5030";
constexpr const char* kRecordedMeshPrefix = "8fc0ac7f";
constexpr const char* kRecordedSlotPrefix = "61019a39";
constexpr const char* kProfileName = "damagumo-family.json";
constexpr const char* kMeshPath = "Demon/enemy.bmd";
constexpr const char* kSlotName = "damagumo-slot-312004.json";
constexpr const char* kRequiredClips[] = {"landing", "wait", "flick", "dead"};
constexpr int kRequiredClipCount =
    static_cast<int>(sizeof(kRequiredClips) / sizeof(kRequiredClips[0]));

namespace {

bool is_hex64(const char* value) {
    if (!value) {
        return false;
    }
    if (std::strlen(value) != 64) {
        return false;
    }
    for (const char* p = value; *p; ++p) {
        const char c = *p;
        const bool hex = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') ||
                         (c >= 'A' && c <= 'F');
        if (!hex) {
            return false;
        }
    }
    return true;
}

bool starts_with(const char* value, const char* prefix) {
    if (!value || !prefix) {
        return false;
    }
    return std::strncmp(value, prefix, std::strlen(prefix)) == 0;
}

bool has_clip(const char** clips, int count, const char* want) {
    if (!clips || !want) {
        return false;
    }
    for (int i = 0; i < count; ++i) {
        if (clips[i] && std::strcmp(clips[i], want) == 0) {
            return true;
        }
    }
    return false;
}

}  // namespace

struct ExpectedHashes {
    char profile[65];
    char mesh[65];
    char slot[65];
};

struct SlotBinding {
    int slot;
    int enemy;
    const char* profile_name;
    const char* mesh_path;
    const char* slot_name;
    bool hash_gated;
};

// Fail-closed structural check against the verified #670 record. Returns
// null on success or a static reason string.
const char* check_structure(int joints, int textures, const char** clips,
                            int clip_count) {
    if (joints != kJointCount) {
        return "joint count mismatch";
    }
    if (textures != kTextureCount) {
        return "texture count mismatch";
    }
    for (int i = 0; i < kRequiredClipCount; ++i) {
        if (!has_clip(clips, clip_count, kRequiredClips[i])) {
            return "required clip absent";
        }
    }
    return nullptr;
}

// Exact-match hash gate over caller-supplied expected hashes. All three must
// be well-formed 64-hex and equal the observed values; recorded #670 prefixes
// are cross-checked but never substitute for the full comparison.
const char* check_hashes(const char* profile_sha, const char* mesh_sha,
                         const char* slot_sha, const ExpectedHashes* exp) {
    if (!exp) {
        return "missing expected hashes";
    }
    if (!is_hex64(exp->profile) || !is_hex64(exp->mesh) || !is_hex64(exp->slot)) {
        return "malformed expected hash";
    }
    if (!profile_sha || std::strcmp(profile_sha, exp->profile) != 0) {
        return "profile hash mismatch";
    }
    if (!mesh_sha || std::strcmp(mesh_sha, exp->mesh) != 0) {
        return "mesh hash mismatch";
    }
    if (!slot_sha || std::strcmp(slot_sha, exp->slot) != 0) {
        return "slot hash mismatch";
    }
    if (!starts_with(exp->profile, kRecordedProfilePrefix) ||
        !starts_with(exp->mesh, kRecordedMeshPrefix) ||
        !starts_with(exp->slot, kRecordedSlotPrefix)) {
        return "expected hash outside recorded #670 prefix";
    }
    return nullptr;
}

// Slot binding record consumed by the #638 staging contract: demon-lane 56
// profile+mesh bound to arena actor slot 312004, hash-gated, never aliased.
SlotBinding bind_slot(const ExpectedHashes* exp) {
    SlotBinding out;
    out.slot = kSlotId;
    out.enemy = kEnemyId;
    out.profile_name = kProfileName;
    out.mesh_path = kMeshPath;
    out.slot_name = kSlotName;
    out.hash_gated = (exp != nullptr);
    return out;
}

}  // namespace p2_dangomushi

#endif  // P2_DAMAGUMO_BINDING_STANDALONE
