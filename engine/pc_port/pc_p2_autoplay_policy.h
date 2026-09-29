#pragma once

// TEST-ONLY headless autoplay bot policy (brief keys: bot-impl wf9, bot-v2 wf10, bot-v3 wf10).
//
// Engine-free state machine for the scripted player that drives the game
// through the NORMAL controller input path (synthesised pad state fed where
// the real pad is read: ControllerMgr::updateController honours
// pc_p2_input_script_override). The bot never teleports, never mode-forces,
// never mutates enemies/Pikmin: it only emits pad buttons + a desired world
// move direction, which the engine-linked driver
// (pc_port/pc_p2_autoplay.cpp) converts to a stick deflection through the
// live camera basis and publishes via pc_p2_input_script_set().
//
// Enabled only when PIKMIN_RANDOMIZER_AUTOPLAY is set (non-empty, != "0").
// The Brain also takes an explicit `enabled` sense: with enabled=false every
// update returns a neutral pad and stays IDLE, which is the
// inert-when-unset guarantee the native test pins (tools/p2_autoplay_test.cpp).
//
// bot-v7 (wf10) deltas, in brief priority order:
//   1. A grabbed lift below the corpse's declared minimum (carryWant,
//      PelletConfig p01; 0 = unknown) keeps seeding instead of escorting:
//      escorting a short lift parks the squad 100-250 u away with throws
//      suppressed, so the crew can never grow (v6b-1 Tank: 4 carriers for
//      231 s). SeedGrow (stand the squad ON the corpse, keep throwing
//      pad-only, never whistle) runs on the shortfall alone, even while the
//      corpse creeps (v7dev-1 Tank: a downhill slide reads moving=1 forever,
//      which locked out motion-gated growing): a real haul always carries at
//      least the minimum (doLift/pellet put-down physics), so motion with a
//      short crew is a slide or a dropped haul, both want more hands. A
//      stalled viable lift re-seeds the same way (bounded rethrows,
//      reason=stalled, latched past the minimum until motion resumes); a
//      crew that shrinks below the minimum re-seeds with reason=shrank.
//   2. AUTOPLAY_CARRY (driver) carries want=<min> + moving=<0/1> so the
//      shortfall is visible (brief format).
// bot-v6 (wf10) deltas, in brief priority order:
//   1. Power mode takes the squad in ONE step: the driver queues the whole
//      Onion through the normal exitPikis path once at start, and WithdrawSeek
//      waits (neutral pad, no menu) until field>=powerWantSquad (80). Normal
//      mode keeps the menu behaviour untouched.
//   2. Select verifies the target is still alive: a dead/absent target with no
//      latched damage is GIVEUP reason=target_gone (token/state as evidence);
//      a latched kill for the same token returns to Aftermath so v5 delivery
//      still finishes instead of dropping the engagement silently.
// bot-v5 (wf10) deltas, in brief priority order:
//   1. Aftermath never whistles (release B once the target is dead: holding
//      whistle gathers Pikmin at the navi 36-65 u from the corpse so no carry
//      ever initiates - v4b diagnosis). Instead it walks the squad ONTO the
//      corpse (contact ring, see piki.cpp/navi.cpp radii below), throws
//      Pikmin at it (thrown Pikmin attach on collision), then backs off so
//      the crew is free to grab it.
//   2. Carry is sensed live (TransportMode count / pellet carriers) with
//      RECENT corpse motion; the receipt window extends ONLY while carriers
//      > 0 AND the corpse is moving now (a stalled lift times out bounded
//      with carry_stalled, not an open-ended escort).
//   3. No grab after a bounded wait -> back off, then re-approach + re-throw
//      (bounded rethrows, pad-only); a grabbed-but-stalled lift (min carriers
//      not met) re-throws to grow the crew; giveup names the reason
//      (carry_no_grab, carry_stalled, corpse_despawned, corpse_out_of_reach,
//      receipt_timeout).
//   4. RESULT received=1 comes ONLY from the target's own per-token ledger
//      receipt (receiptSeen for this token); bystander CHECK Bestiary:Deliver
//      lines never score (harness keys received the same way).
//
// Carry/recruit ring (real radii, cited):
//   - Pellet attach is CONTACT-driven, not a fixed radius: FormationMode
//     Pikmin attach to a Pellet on collision with a free slot
//     (src/plugPikiKando/piki.cpp:2131-2143), gated by distCheck
//     (piki.cpp:2024-2027: C-stick held or mForcePikiDistCheck); thrown
//     (flying) Pikmin attach on collision with no distCheck needed
//     (src/plugPikiKando/pikiState.cpp:2258-2264, OBJTYPE_Pellet ->
//     TransportMode); the navi standing on a pellet 0.5 s forces one recruit
//     via mForcePikiDistCheck (Navi::letPikiWork,
//     src/plugPikiKando/navi.cpp:1853-1864 + 1820-1822).
//   - aftermathApproachRadius (60 u) is inside that contact scale (same ~50 u
//     navi-size + coll-radius contact the withdraw comment cites) with margin;
//     aftermathBackoffDist (200 u) steps back out of contact so the crew
//     settles onto the pellet. Whistle max radius is 100 u
//     (include/NaviMgr.h:27) - which is why aftermath must NOT whistle: it
//     would pin the squad at the navi instead of the corpse.
//
// bot-v3 (wf10) deltas, in brief priority order:
//   1. Approach follows the routeMgr waypoint graph leg by leg (driver
//      plans method=graph); STUCK lines carry the navi position + replan
//      count so logs prove whether the captain moves under stick input.
//   2. "Target out of reach after N replans" is GIVEUP reason=
//      target_unreachable, then Done idles near the Onion (enemies may come).
//   3. Driver never repeats an identical detour and tries alternates
//      (next-nearest start/goal waypoints, reversed legs); graph failure is
//      logged as AUTOPLAY_ROUTE_FAIL reason=<why>.
//
// bot-v2 (wf10) deltas, in brief priority order:
//   1. Onion receipt: Aftermath waits for the species' Onion receipt marker
//      (sensed as receiptSeen from the delivery ledger) or receiptTimeout;
//      RESULT carried=1 means a receipt line was seen, plus received=<0/1>.
//   2. Far targets: the driver plans over the routeMgr waypoint graph and
//      follows waypoint by waypoint (Brain honours waypointLeg + replan on
//      every STUCK window, not just the first).
//   3. Flyers: Sarai is only thrown at when low or holding a Pikmin (whistle
//      frees grabs); Kurage gets a longer attack window and rotating throws.
//   4. Full squad: the withdraw menu repeats until field>=wantSquad or the
//      Onion is empty (bounded by maxWithdrawCycles).
//   5. Kill claims: generic death latch (targetDead / health<=0 / !alive /
//      corpse) scores kills for every species, not just per-module markers.

#include <cmath>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

namespace p2autoplay {

// Pad button bits. Must match include/Controller.h KeyboardButtons exactly;
// pc_port/pc_p2_autoplay.cpp static_asserts the equality so a drift breaks
// the build instead of silently mis-driving input.
enum PadButton {
    PadCStickLeft = 1 << 0,
    PadCStickRight = 1 << 1,
    PadCStickUp = 1 << 2,
    PadCStickDown = 1 << 3,
    PadDPadLeft = 1 << 8,
    PadDPadRight = 1 << 9,
    PadDPadUp = 1 << 10,
    PadDPadDown = 1 << 11,
    PadA = 1 << 12,
    PadB = 1 << 13,
    PadX = 1 << 14,
    PadY = 1 << 15,
    PadZ = 1 << 16,
    PadL = 1 << 17,
    PadR = 1 << 18,
    PadMainUp = 1 << 19,
    PadMainRight = 1 << 20,
    PadMainDown = 1 << 21,
    PadMainLeft = 1 << 22,
    PadStart = 1 << 24,
};

// Env gating. Unset/empty/"0" means production: the driver returns before
// touching any input state.
inline bool isEnabled()
{
    const char* v = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY");
    return v && v[0] && std::strcmp(v, "0") != 0;
}

// Optional target filter: PIKMIN_RANDOMIZER_AUTOPLAY_TARGET=<generator key or
// species name>. Empty means "nearest live P2-bound teki".
inline std::string targetFilter()
{
    const char* v = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_TARGET");
    return v ? std::string(v) : std::string();
}

// bot-v4 power mode (owner's idea; evidence, not a fair fight):
// PIKMIN_RANDOMIZER_AUTOPLAY_POWER, off by default, ONLY meaningful when the
// autoplay gate above is already on. Inert in normal play: with the autoplay
// gate closed this is always false, no matter what POWER is set to.
// A numeric POWER value (e.g. "10") configures the test-only damage
// multiplier; any other non-empty non-"0" value means "on" with x10.
inline bool isPowerEnabled()
{
    if (!isEnabled()) return false;
    const char* v = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER");
    return v && v[0] && std::strcmp(v, "0") != 0;
}

inline float powerDamageMult()
{
    if (!isPowerEnabled()) return 1.0f;
    const char* v = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER");
    if (v && v[0]) {
        char* end = nullptr;
        const double d = std::strtod(v, &end);
        if (end && end != v && *end == 0 && d > 0.0 && d < 1000000.0) return float(d);
    }
    return 10.0f;
}

enum class State {
    Idle = 0, // no input; waiting for enable + live captain
    WithdrawSeek, // walk to the stocked Onion
    WithdrawMenu, // Onion container UI: take Pikmin out, confirm
    Select, // (re)pick the current target
    Approach, // steer the stick toward the target (waypoint replan on stuck)
    Attack, // aim + throw (A); whistle (B) regroup when scattered
    Aftermath, // whistle back, let the corpse be carried
    Done, // no more targets: neutral input
};

inline const char* stateName(State s)
{
    switch (s) {
    case State::Idle: return "idle";
    case State::WithdrawSeek: return "withdraw_seek";
    case State::WithdrawMenu: return "withdraw_menu";
    case State::Select: return "select";
    case State::Approach: return "approach";
    case State::Attack: return "attack";
    case State::Aftermath: return "aftermath";
    case State::Done: return "done";
    }
    return "unknown";
}

// P2 source ids the bot knows by species name, for the TARGET filter and for
// per-species behaviour (Kogane never dies; flyers stay airborne).
// Values are the ENEMY_P2 source ids from the seed p2_layout bindings.
inline unsigned sourceForSpeciesName(const char* name)
{
    if (!name) return 0;
    struct Row {
        const char* name;
        unsigned source;
    };
    static const Row rows[] = {
        {"sokkuri", 79}, {"kogane", 9}, {"sarai", 23}, {"kurage", 57},
        {"miulin", 54}, {"bluekochappy", 44}, {"fireotakara", 59},
        {"waterotakara", 60}, {"gasotakara", 61}, {"elecotakara", 62},
    };
    // Case-insensitive compare, dash/space tolerant.
    char norm[64];
    size_t n = 0;
    for (const char* p = name; *p && n + 1 < sizeof(norm); ++p) {
        if (*p == ' ' || *p == '_' || *p == '-') continue;
        norm[n++] = char(*p >= 'A' && *p <= 'Z' ? *p + ('a' - 'A') : *p);
    }
    norm[n] = 0;
    for (const Row& row : rows) {
        if (std::strcmp(norm, row.name) == 0) return row.source;
    }
    return 0;
}

inline bool isKoganeLike(unsigned source) { return source == 9; }
inline bool isFlyer(unsigned source) { return source == 23 || source == 57 || source == 32 || source == 72; }

// #884 round 4: KingChappy (53) keeps the captain OUT of the source
// invisible range while attacking. Source searchTarget prefers a captain in
// the search cone and caps the Pikmin search at his distance
// (kingChappy.cpp:1131-1178); checkAttack refuses any target inside proper
// fp06 = 80 (kingChappy.cpp:1778-1822; port king::gateReason); checkFlick
// adds 0.1 per frame while a captain is within 3D fp06 (kingChappy.cpp:
// 2429-2470) and the flick tramples captains within 45 of the foot
// (kingChappyState.cpp:867-918, InteractPress 5 HP). A bot captain parked in
// contact (i1-53: tdist=18) therefore holds the King in a no-attack standoff
// while being stomped every flick. Only the King has this gate; every other
// family keeps the unchanged contact steer.
inline bool isKingStandoff(unsigned source) { return source == 53; }

// Numeric filter matches a generator key; otherwise a species name match.
inline bool matchTarget(unsigned token, unsigned source, const char* species, const std::string& filter)
{
    if (filter.empty()) return true;
    char* end = nullptr;
    const unsigned long asNum = std::strtoul(filter.c_str(), &end, 10);
    if (end && *end == 0 && filter[0] >= '0' && filter[0] <= '9') {
        if (unsigned(asNum) == token) return true;
        // A bare source id also matches (e.g. TARGET=79 for any Sokkuri).
        if (unsigned(asNum) == source) return true;
        return false;
    }
    if (species && sourceForSpeciesName(filter.c_str()) == source) return true;
    if (species) {
        // Direct name compare as a fallback.
        char a[64], b[64];
        size_t i = 0;
        for (const char* p = species; *p && i + 1 < sizeof(a); ++p) {
            if (*p == ' ' || *p == '_' || *p == '-') continue;
            a[i++] = char(*p >= 'A' && *p <= 'Z' ? *p + ('a' - 'A') : *p);
        }
        a[i] = 0;
        size_t j = 0;
        for (const char* p = filter.c_str(); *p && j + 1 < sizeof(b); ++p) {
            if (*p == ' ' || *p == '_' || *p == '-') continue;
            b[j++] = char(*p >= 'A' && *p <= 'Z' ? *p + ('a' - 'A') : *p);
        }
        b[j] = 0;
        if (std::strcmp(a, b) == 0) return true;
    }
    return false;
}

struct Config {
    float withdrawTimeout = 150.0f; // walk to Onion + work the container UI
    float menuOpenTimeout = 12.0f; // wait for the container UI after pressing A
    float menuHoldDuration = 8.0f; // hold stick-down to accumulate withdraw delta
    float menuConfirmDuration = 2.0f; // pulse A to confirm after the hold
    float approachTimeout = 150.0f; // steer to one target
    float attackTimeout = 240.0f; // throw at one target
    float aftermathTimeout = 60.0f; // whistle back + let the corpse be carried
    float receiptTimeout = 180.0f; // after a kill, wait for the Onion receipt marker or this timeout
    // bot-v5 aftermath delivery knobs (contact ring radii cited in the file
    // header: piki.cpp:2131-2143, pikiState.cpp:2258-2264, navi.cpp:1853-1864).
    float aftermathApproachRadius = 60.0f; // walk ONTO the corpse: inside contact scale
    float aftermathBackoffDist = 200.0f; // step back out of contact so the crew grabs it
    float carryGrabWait = 20.0f; // bounded wait for the first grab before backing off / re-seeding
    float aftermathSettleWait = 8.0f; // pause at backoff for grabs to settle before re-approach
    int aftermathRethrowMax = 5; // bounded re-approach + re-seed cycles when grabs fail or stall
    float carryStallWait = 25.0f; // grabbed but not moving for this long -> re-seed to add carriers
    float corpseStillWindow = 15.0f; // no corpse displacement for this long counts as stalled
    float corpseMoveMin = 15.0f; // corpse displacement that counts as "moving" (harness carried threshold)
    float corpseOutOfReach = 800.0f; // tdist past this at giveup names corpse_out_of_reach
    float koganeConfirm = 20.0f; // after Kogane damage, watch escapes then move on
    float kurageAttackMultiplier = 2.0f; // Kurage has high HP: longer attack window
    float saraiLowHeight = 120.0f; // Sarai thrown at only when within this height above ground (or grabbing)
    float throwRange = 260.0f; // XZ distance at which throws start
    float arriveRadius = 90.0f; // XZ distance considered "at" the Onion
    float throwHold = 0.12f; // A held per throw pulse
    float throwGap = 0.55f; // gap between throw pulses
    float whistleHold = 1.6f; // B held to regroup / call back
    float whistleCooldown = 3.0f; // bot-undamaged: gap after a whistle before re-latching (forces throw windows)
    float attackChaseDist = 500.0f; // bot-undamaged: target past this in attack re-enters approach (graph chase)
    float stuckWindow = 4.0f; // no-progress window before STUCK + replan
    float stuckMinProgress = 30.0f; // XZ units that count as progress
    int maxApproachReplans = 6; // consecutive STUCK windows before target_unreachable GIVEUP
    int wantSquad = 15; // withdrawn Pikmin before leaving the Onion
    int powerWantSquad = 80; // bot-v6: power-mode one-step squad readiness (field>=80, no menu)
    int maxWithdrawCycles = 6; // repeat the withdraw menu until field>=wantSquad or Onion empty
    int resupplyThreshold = 5; // Attack/Approach below this field count + Onion stock => disengage + withdraw
    // #884 round 4 KingChappy standoff (isKingStandoff). XZ distances; the
    // source gates are 3D, and 3D >= XZ, so XZ >= kingStandoffMin keeps the
    // captain outside fp06 (80) and the flick shake range (fp19 60) whatever
    // the height. kingStandoffMax stays under general fp20 (130, 3D attack
    // range) so the King can still target the captain and tongue the squad
    // standing with him (source attack path; eating needs a target outside
    // fp06). Hysteresis: back off below Min until Resume; close in above Max
    // until CloseStop; hold (look + throw) in between.
    bool kingStandoff = true;
    float kingStandoffMin = 95.0f;
    float kingStandoffResume = 110.0f;
    float kingStandoffMax = 125.0f;
    float kingStandoffCloseStop = 115.0f;
    float kingSidestepAfter = 3.0f; // backing off this long (wall/pinned) -> sidestep, swapping sides each window
    float kingCursorTol = 20.0f; // hold: cursor within this XZ of the King -> neutral stick (cursor stays put)
    // #884 round 5: tongue evade. The King's StateAttack attacks a captain
    // touching any kamu1..9 slot sphere (frames 40..94, radius 25; port
    // kingNaviContact, InteractAttack 5 HP, no knockback), and those slots
    // sweep local z 42..142 and x -79..58: the hold band (95..125, in the
    // +-30 degree attack cone) is inside the sweep. The bot therefore leaves
    // the sweep as soon as the King is in its attack state
    // (Senses::targetAttacking) and stays out until the attack ends.
    // kingEvadeClear must exceed the King profile's maxReach (XZ radius of
    // the farthest slot centre + slot radius = 166.7; checked in
    // p2_autoplay_test). From the band edge (125) that is 55 u, about 10
    // frames at a walk, well inside the 40-frame wind-up before the first
    // slot frame.
    bool kingEvade = true;
    float kingEvadeClear = 180.0f;
    float kingEvadeSideAfter = 0.5f; // still inside Clear after this long (pinned) -> away + 45 degrees sideways
    // Low-health guard: at or below kingLowHp (captain mHealth; Olimar has
    // 100, no field regen) the stance band moves out to [Clear, Clear+30]:
    // beyond fp20 (130) and the tongue reach, so the King never attacks the
    // captain; he keeps throwing from there. 0 disables.
    float kingLowHp = 35.0f;
    float lookStickScale = 0.24f; // 0.24*127 = 30 bytes: |stick| 0.41 (look band), no MSTICK bits (> 32)
};

// Power-mode effective withdraw targets (bot-v4, bot-v4b): up to ~100 Pikmin.
// The field cap binds the withdraw menu + exit queue + birth pool, so power
// mode lifts it to 100 as well (pc_randomizer_field_capacity); the Onion is
// stocked to ~100 by the driver (AUTOPLAY_POWER_STOCK). 15 menu cycles at the
// observed ~10/cycle UI accumulation rate reach 100 with headroom; the loop
// still exits early once field>=100 or the Onion is empty.
inline int effectiveWantSquad(const Config& cfg) { return isPowerEnabled() ? 100 : cfg.wantSquad; }
inline int effectiveMaxWithdrawCycles(const Config& cfg) { return isPowerEnabled() ? 15 : cfg.maxWithdrawCycles; }

// bot-v4b power-mode Onion stock: the day-start Onion only holds the 20
// starting Pikmin (gameSetup sets 20), so power mode tops the start-colour
// Onion up to ~100 through the normal born/stored bookkeeping (the field cap
// binds the menu/queue/pool too, so power mode lifts it to 100 as well).
// Pure function so the inert-when-unset rule is unit-testable: with power
// disabled the delta is always 0, no matter what the counts are. stored =
// Onion's stored count, field = live field Pikmin, already =
// GameStat::allPikis total, limit = piki pool limit.
inline int powerStockTarget() { return 100; }
inline int powerStockDelta(bool powerEnabled, int stored, int field, int already, int limit)
{
    if (!powerEnabled) return 0;
    int want = powerStockTarget() - (stored + field);
    if (want <= 0) return 0;
    const int room = limit - already;
    if (room <= 0) return 0;
    if (want > room) want = room;
    return want;
}

// bot-v5: corpse displacement past corpseMoveMin counts as "moving" (shared
// by the driver, which senses it live, and the Brain tests, which drive it).
inline bool corpseDisplaced(float dx, float dz)
{
    const float min = Config().corpseMoveMin;
    return dx * dx + dz * dz > min * min;
}

// Plain-data senses gathered by the engine-linked driver each tick.
struct Senses {
    bool enabled = false; // PIKMIN_RANDOMIZER_AUTOPLAY gate
    bool naviAlive = false; // controlled captain exists and is alive
    float dt = 0.016f; // logical tick length (seconds)
    // Geometry (world XZ). The Brain steers in world space; the driver
    // converts the move vector through the live camera into stick bytes.
    float naviX = 0.0f;
    float naviZ = 0.0f;
    bool hasOnion = false;
    float onionX = 0.0f;
    float onionZ = 0.0f;
    float wpX = 0.0f; // detour waypoint when waypointLeg is set
    float wpZ = 0.0f;
    // Onion / squad facts for the withdraw phase.
    int fieldPikmin = 0; // live field Pikmin
    int onionStored = 0; // Pikmin stored in the nearest stocked Onion
    float onionDist = 1.0e30f; // XZ distance to that Onion
    bool containerOpen = false; // Onion container UI is up
    // Current-target facts. targetToken==0 means "no target".
    unsigned targetToken = 0;
    unsigned targetSource = 0;
    float tgtX = 0.0f;
    float tgtZ = 0.0f;
    float targetDist = 1.0e30f; // XZ distance navi -> target
    bool targetAlive = false;
    float targetHealthFrac = 1.0f; // 1 == untouched
    bool targetDamagedLatch = false; // family-observed combat (e.g. Kogane flip)
    bool targetRevealed = true; // Sokkuri disguise dropped
    bool targetDead = false; // generic death: health<=0 / !alive / dead-state / corpse formed
    bool receiptSeen = false; // Onion receipt marker for this token observed (delivery ledger)
    float targetHeight = 0.0f; // Y above ground (flyers: Sarai/Kurage)
    bool targetGrabbing = false; // flyer holds a Pikmin (Sarai grab): whistle to free
    bool targetLow = false; // flyer low enough to hit (driver compares height to saraiLowHeight)
    bool transportSeen = false; // any live Pikmin in TransportMode
    // bot-v5 live carry senses (driver computes per-tick; Brain latches what
    // it needs). carryCount = TransportMode Pikmin near this corpse;
    // pelletCarriers = pellet mCarrierCounter near it; pelletExists = dead
    // body or corpse pellet still present. corpseMoving = the corpse is
    // moving NOW (displaced past corpseMoveMin AND displaced again within
    // corpseStillWindow - a lift that moved then stopped reads false, so the
    // window stops extending and the stall re-throw fires). corpseMoved =
    // displaced past corpseMoveMin at any point (motion history for reasons).
    int carryCount = 0;
    int pelletCarriers = 0;
    bool pelletExists = true;
    // bot-v7: the tracked corpse's declared carry minimum (PelletConfig p01
    // strength units, same scale as pelletCarriers). 0 = unknown (no dead
    // body or pellet resolved yet): the Brain falls back to the v5/v6 rule
    // (any carry escorts). When known, a grabbed-but-short lift keeps
    // seeding instead of escorting a stuck lift.
    int carryWant = 0;
    bool corpseMoving = false;
    bool corpseMoved = false;
    bool scattered = false; // squad scattered: whistle regroup
    bool squadDistress = false; // grabbed/thrown-off/burning Pikmin: whistle regroup (bot-v4)
    bool waypointLeg = false; // steer the detour waypoint, not the target
    // #884 round 4: live throw cursor (navi position + Navi::mCursorPosition,
    // world XZ). Only the King standoff hold reads it, to slide the cursor
    // onto the King instead of past it; without it the hold look-steers at
    // the King itself.
    bool cursorValid = false;
    float cursorX = 0.0f;
    float cursorZ = 0.0f;
    // #884 round 5: the target is in its attack state (KingChappy StateAttack,
    // read-only via pc_p2_chappy_probe; the King driver sets it for source 53
    // only), and the captain's live health (Navi::mHealth). Only the King
    // stance reads them.
    bool targetAttacking = false;
    bool naviHpValid = false;
    float naviHp = 0.0f;
};

// Pad output for one tick. moveX/moveZ is the desired world-space XZ move
// direction (driver converts through the live camera into stick bytes +
// MSTICK bits); (0,0) means "no movement". menuHold asks for the Onion
// container withdraw input (stick-down + MSTICK_DOWN) while the UI is open.
struct Command {
    unsigned buttons = 0;
    float moveX = 0.0f;
    float moveZ = 0.0f;
    bool menuHold = false;
    // #884 round 4: stick deflection scale for (moveX, moveZ). 1 = full
    // (walk). Config::lookStickScale puts the stick inside the P1 "look"
    // band (mNeutralStickThreshold 0.1 < |stick| <= mCursorMoveStickThreshold
    // 0.75, NaviMgr.h:72-73; |stick| = byte / 74, controller.cpp:78): the
    // captain stops (mTargetVelocity = 0), faces the cursor, and the cursor
    // slides along the stick at mCursorMoveSpeed (navi.cpp:2475-2489,
    // 2531-2538). Used only by the King standoff hold.
    float stickScale = 1.0f;
};

struct Result {
    unsigned token = 0;
    bool damaged = false;
    bool killed = false;
    bool carried = false;
    bool received = false; // Onion receipt marker observed (carried=1 implies received=1)
    float seconds = 0.0f;
    bool koganeLike = false;
};

class Brain {
public:
    explicit Brain(const Config& config = Config()) : cfg(config) { reset(); }

    void reset()
    {
        state = State::Idle;
        stateTime = 0.0f;
        engageTime = 0.0f;
        pressPhase = 0.0f;
        pressOn = false;
        whistleTime = 0.0f;
        whistling = false;
        whistleCooldown = 0.0f;
        menuTaps = 0;
        menuHoldTime = 0.0f;
        menuConfirmed = false;
        stuckWindowStart = 0.0f;
        stuckWindowDist = 1.0e30f;
        wantReplan = false;
        progressBest = 1.0e30f;
        approachReplans = 0;
        initialHealthFrac = 1.0f;
        sawDamage = false;
        sawKill = false;
        sawCarry = false;
        sawReceipt = false;
        sawMove = false; // bot-v5: corpse displacement latched
        amPhase = AftermathSeed;
        amPhaseTime = 0.0f;
        amRethrows = 0;
        amTracked = false;
        amLastCX = 0.0f;
        amLastCZ = 0.0f;
        amStallTime = 0.0f;
        amGrow = false; // bot-v7: seeding a short crew instead of escorting
        amHadEnough = false; // bot-v7: the lift was viable (escorted)
        amLastCrew = 0; // bot-v7: high-water crew for SeedGrow progress
        amGrowStill = 0.0f; // bot-v7: time without crew growth in SeedGrow
        withdrawCycles = 0;
        throwSpin = 0.0f;
        kingBacking = false;
        kingClosing = false;
        kingBackTime = 0.0f;
        kingMode = -1;
        kingEvading = false;
        kingEvadeTime = 0.0f;
        kingLowHpMode = false;
        result = Result{};
        markers.clear();
        lastCommand = Command{};
        announced = false;
    }

    State current() const { return state; }
    Command command() const { return lastCommand; }
    bool replanWanted() const { return wantReplan; }
    void clearReplan() { wantReplan = false; }
    std::vector<std::string> takeMarkers()
    {
        std::vector<std::string> out;
        out.swap(markers);
        return out;
    }

    void update(float dt, const Senses& in)
    {
        lastCommand = Command{};
        if (dt <= 0.0f || dt > 0.5f) dt = 0.016f;
        lastDt = dt;
        if (!in.enabled) {
            // Inert-when-unset: no input, no markers, forced IDLE.
            if (state != State::Idle) reset();
            return;
        }
        if (!in.naviAlive) {
            holdIdle();
            return;
        }
        stateTime += dt;
        switch (state) {
        case State::Idle: tickIdle(in); break;
        case State::WithdrawSeek: tickWithdrawSeek(dt, in); break;
        case State::WithdrawMenu: tickWithdrawMenu(dt, in); break;
        case State::Select: tickSelect(in); break;
        case State::Approach: tickApproach(dt, in); break;
        case State::Attack: tickAttack(dt, in); break;
        case State::Aftermath: tickAftermath(dt, in); break;
        case State::Done: tickDone(dt, in); break;
        }
    }

private:
    void emitState(const Senses& in)
    {
        char buf[256];
        std::snprintf(buf, sizeof(buf), "AUTOPLAY_STATE state=%s token=%u field=%d bot-driven",
                      stateName(state), in.targetToken, in.fieldPikmin);
        markers.emplace_back(buf);
    }
    void enter(State next, const Senses& in)
    {
        state = next;
        stateTime = 0.0f;
        pressPhase = 0.0f;
        pressOn = false;
        whistleTime = 0.0f;
        whistling = false;
        whistleCooldown = 0.0f;
        menuTaps = 0;
        menuHoldTime = 0.0f;
        menuConfirmed = false;
        stuckWindowStart = 0.0f;
        stuckWindowDist = 1.0e30f;
        wantReplan = false;
        progressBest = 1.0e30f;
        approachReplans = 0;
        kingBacking = false;
        kingClosing = false;
        kingBackTime = 0.0f;
        kingMode = -1;
        kingEvading = false;
        kingEvadeTime = 0.0f;
        kingLowHpMode = false;
        emitState(in);
    }
    void holdIdle() { lastCommand = Command{}; }

    void tickIdle(const Senses& in)
    {
        // First live tick with the gate set: announce and go withdraw.
        if (!announced) {
            announced = true;
            markers.emplace_back("AUTOPLAY_STATE state=idle gate=open bot-driven");
        }
        enter(State::WithdrawSeek, in);
    }

    void steer(float fromX, float fromZ, float toX, float toZ)
    {
        const float dx = toX - fromX, dz = toZ - fromZ;
        const float len = std::sqrt(dx * dx + dz * dz);
        if (len > 1.0f) {
            lastCommand.moveX = dx / len;
            lastCommand.moveZ = dz / len;
        }
    }

    // bot-v5: steer directly away from (x,z) (aftermath backoff).
    void steerAway(float fromX, float fromZ, float awayX, float awayZ)
    {
        const float dx = fromX - awayX, dz = fromZ - awayZ;
        const float len = std::sqrt(dx * dx + dz * dz);
        if (len > 1.0f) {
            lastCommand.moveX = dx / len;
            lastCommand.moveZ = dz / len;
        }
    }

    // bot-v7: stand the squad ON the corpse and throw Pikmin directly
    // onto it in a burst (normal input only: stick + A pulses, never
    // whistle). Shared by Seed (no grabs yet) and SeedGrow (short crew).
    void seedSteerThrow(const Senses& in)
    {
        if (in.waypointLeg) steer(in.naviX, in.naviZ, in.wpX, in.wpZ);
        else if (in.targetToken != 0) steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
        if (in.targetDist <= cfg.throwRange && in.targetToken != 0) pulseA(in, cfg.throwHold, cfg.throwGap);
    }

    void tickWithdrawSeek(float dt, const Senses& in)
    {
        // bot-v6 (power mode only): the squad arrives in ONE step through the
        // normal Onion exit queue (driver calls exitPikis for the whole Onion
        // once at start), never through the withdraw menu. Each menu cycle only
        // accumulates ~5-6 Pikmin of UI-local delta (bc4: 9-10 cycles to reach
        // 100), eating the run; the exit queue births ~100 in ~5 s of game
        // time. Wait here with a neutral pad until field>=powerWantSquad, then
        // Select. Normal mode keeps the menu behaviour below, untouched.
        if (isPowerEnabled()) {
            if (in.containerOpen) {
                // v3 guard preserved: never steer while the UI is up.
                enter(State::WithdrawMenu, in);
                return;
            }
            if (in.fieldPikmin >= cfg.powerWantSquad) {
                enter(State::Select, in);
                return;
            }
            if (in.onionStored <= 0 && in.fieldPikmin > 0) {
                // Queue drained with a short squad (or a unit-test sense with
                // no Onion): fight with the squad on the field.
                enter(State::Select, in);
                return;
            }
            if (stateTime >= cfg.withdrawTimeout) {
                giveUp(in, "withdraw_timeout");
                enter(State::Select, in);
            }
            return; // neutral pad: no A taps, no menu, the queue lands on its own
        }
        if (in.fieldPikmin >= effectiveWantSquad(cfg)) {
            enter(State::Select, in);
            return;
        }
        if (in.onionStored <= 0 && in.fieldPikmin > 0) {
            // Nothing stocked to take; fight with the squad on the field.
            enter(State::Select, in);
            return;
        }
        if (in.containerOpen) {
            // UI already open (A landed while closing distance): work it.
            enter(State::WithdrawMenu, in);
            return;
        }
        if (in.hasOnion) {
            // Keep closing until the real container trigger (navi size +
            // coll radius, ~50) fires: arriveRadius (90) only starts the A
            // taps, it must not stop the steering or the captain stalls at
            // 90 and never opens the UI (wf9-2 withdraw_timeout).
            if (in.waypointLeg) steer(in.naviX, in.naviZ, in.wpX, in.wpZ);
            else steer(in.naviX, in.naviZ, in.onionX, in.onionZ);
            if (in.onionDist <= cfg.arriveRadius) {
                // At the Onion: tap A to open the container UI.
                pulseA(in, 0.12f, 0.6f);
            }
            // Progress / stuck tracking so a wall between spawn and the
            // Onion logs AUTOPLAY_STUCK and asks the driver to replan via
            // the map waypoint graph (same contract as approach).
            if (stuckWindowDist >= 1.0e29f) {
                stuckWindowDist = in.onionDist;
                stuckWindowStart = 0.0f;
                progressBest = in.onionDist;
            }
            if (in.onionDist < progressBest) progressBest = in.onionDist;
            stuckWindowStart += dt;
            if (stuckWindowStart >= cfg.stuckWindow) {
                if (stuckWindowDist - progressBest < cfg.stuckMinProgress) {
                    char buf[256];
                    std::snprintf(buf, sizeof(buf),
                                  "AUTOPLAY_STUCK state=withdraw_seek onion_dist=%.0f navi=(%.0f,%.0f) bot-driven",
                                  in.onionDist, in.naviX, in.naviZ);
                    markers.emplace_back(buf);
                    wantReplan = true;
                }
                stuckWindowDist = progressBest;
                stuckWindowStart = 0.0f;
            }
        }
        if (stateTime >= cfg.withdrawTimeout) {
            giveUp(in, "withdraw_timeout");
            enter(State::Select, in);
        }
    }

    void tickWithdrawMenu(float dt, const Senses& in)
    {
        if (!in.containerOpen) {
            // UI closed after our A confirm: one withdraw cycle landed.
            if (menuConfirmed) {
                if (in.fieldPikmin >= effectiveWantSquad(cfg) || in.onionStored <= 0
                    || withdrawCycles + 1 >= effectiveMaxWithdrawCycles(cfg)) {
                    enter(State::Select, in);
                    return;
                }
                // Squad still short and the Onion still stocks: loop back for
                // another cycle (bot-v2 gap 4: repeat until 15 or empty).
                ++withdrawCycles;
                char buf[256];
                std::snprintf(buf, sizeof(buf),
                              "AUTOPLAY_WITHDRAW cycle=%d field=%d stored=%d bot-driven",
                              withdrawCycles, in.fieldPikmin, in.onionStored);
                markers.emplace_back(buf);
                enter(State::WithdrawSeek, in);
                return;
            }
            // UI did not open (or closed early): tap A to (re)open, then wait.
            pulseA(in, 0.12f, 0.8f);
            if (stateTime >= cfg.menuOpenTimeout) {
                giveUp(in, "withdraw_menu_timeout");
                enter(State::Select, in);
            }
            return;
        }
        if (in.fieldPikmin >= effectiveWantSquad(cfg) || in.onionStored <= 0) {
            // Already have a squad (e.g. re-entered): confirm and leave, but
            // NEVER while the container UI is still open (bot-v3: leaving
            // dirty strands the navi in NAVISTATE_Container, where the stick
            // drives the UI and mTargetVelocity stays 0, freezing approach).
            pulseA(in, 0.12f, 0.4f);
            menuHoldTime += dt;
            if (menuHoldTime > 1.2f) menuConfirmed = true;
            if (menuConfirmed && stateTime > 4.0f && !in.containerOpen) enter(State::Select, in);
            return;
        }
        // Need withdraw: the field count only rises AFTER the A confirm
        // (delta is UI-local until End), so a field-gated hold deadlocks
        // (wf9-3 withdraw_hold_timeout with field=0). Hold stick-down for
        // menuHoldDuration to accumulate delta, then pulse A to confirm.
        if (menuHoldTime < cfg.menuHoldDuration) {
            lastCommand.menuHold = true;
            menuHoldTime += dt;
            return;
        }
        pulseA(in, 0.12f, 0.4f);
        menuHoldTime += dt;
        if (menuHoldTime > cfg.menuHoldDuration + cfg.menuConfirmDuration) menuConfirmed = true;
        if (menuConfirmed) {
            // Keep pulsing until the UI closes (exitPikis runs on End).
            if (stateTime >= cfg.withdrawTimeout) {
                giveUp(in, "withdraw_hold_timeout");
                enter(State::Select, in);
            }
            return;
        }
        if (stateTime >= cfg.withdrawTimeout) {
            giveUp(in, "withdraw_hold_timeout");
            enter(State::Select, in);
        }
    }

    void tickSelect(const Senses& in)
    {
        if (in.containerOpen) {
            // bot-v3: the container UI must be closed before engaging; work
            // it instead of stranding the navi in NAVISTATE_Container.
            enter(State::WithdrawMenu, in);
            return;
        }
        if (in.targetToken == 0 || !in.targetAlive) {
            // bot-v6: verify the target is still alive before Select. A dead /
            // absent target used to fall through to Done silently, dropping the
            // engagement (bc4: kills with no RESULT after an aftermath ->
            // container bounce). Name it instead: a mid-engagement kill latched
            // for THIS token returns to Aftermath to finish v5 delivery;
            // anything else is GIVEUP reason=target_gone with the token/state
            // as evidence. token==0 (no targets at all) still idles silently.
            if (result.token != 0 && result.token == in.targetToken && (sawDamage || sawKill)) {
                enter(State::Aftermath, in);
                return;
            }
            if (in.targetToken != 0) giveUp(in, "target_gone");
            enter(State::Done, in);
            return;
        }
        // bot-v8 merge (#871): score-on-switch keeps ONE version (deliver's).
        // Both deliver (bc5 59/60/57: aftermath -> container -> new token with
        // no RESULT for the kill) and undamaged (bc5 44/54: WithdrawMenu bounce
        // picks the next live token, losing the first kill to 4 unreachable
        // RESULTs) implemented the same idea. Kept deliver's honest form:
        // finishTarget(false) so killed comes from sawKill only (55 false-kill
        // rule), kogane-likes excluded, return so the next tick engages the new
        // target. Same-token bounces still resume Aftermath above; only a true
        // token switch with latched combat scores here (no spurious RESULTs).
        if (result.token != 0 && in.targetToken != 0 && result.token != in.targetToken
            && (sawKill || sawDamage) && !result.koganeLike) {
            finishTarget(in, /*claimedKill*/ false);
            return;
        }
        engageTime = 0.0f;
        initialHealthFrac = in.targetHealthFrac;
        sawDamage = in.targetDamagedLatch;
        sawKill = in.targetDead;
        if (in.targetDead) sawDamage = true; // death implies damage
        sawCarry = false;
        sawReceipt = in.receiptSeen;
        sawMove = in.corpseMoving; // bot-v5: corpse-motion latch starts live
        if (in.corpseMoved) sawMove = true;
        amPhase = AftermathSeed;
        amPhaseTime = 0.0f;
        amRethrows = 0;
        amTracked = false;
        amLastCX = 0.0f;
        amLastCZ = 0.0f;
        amStallTime = 0.0f;
        amGrow = false;
        amHadEnough = false;
        amLastCrew = 0;
        amGrowStill = 0.0f;
        result = Result{};
        result.token = in.targetToken;
        result.koganeLike = isKoganeLike(in.targetSource);
        enter(State::Approach, in);
    }

    void tickApproach(float dt, const Senses& in)
    {
        if (in.containerOpen) {
            // bot-v3: stick drives the container UI, not the captain; close
            // it before steering or the navi never moves (bc2 freeze).
            enter(State::WithdrawMenu, in);
            return;
        }
        engageTime += dt;
        if (!in.targetAlive || in.targetDead) {
            // Died before we arrived (or despawned): score what we saw.
            // Generic death latch first so Otakara-style kills (no per-module
            // marker) still claim (bot-v2 gap 5).
            observeDeath(in);
            if (sawDamage || sawKill) {
                enter(State::Aftermath, in); // a corpse may still be carried
            } else {
                finishTarget(in, /*claimedKill*/ false);
            }
            return;
        }
        if (in.fieldPikmin < cfg.resupplyThreshold && in.hasOnion && in.onionStored > 0) {
            // bot-v4: squad eaten en route and the Onion still stocks:
            // disengage, walk back, withdraw more, then return.
            char buf[256];
            std::snprintf(buf, sizeof(buf),
                          "AUTOPLAY_RESUPPLY field=%d stored=%d token=%u state=approach bot-driven",
                          in.fieldPikmin, in.onionStored, in.targetToken);
            markers.emplace_back(buf);
            enter(State::WithdrawSeek, in);
            return;
        }
        observeDamage(in);
        observeDeath(in);
        observeReceipt(in);
        const float closeEnough = isFlyer(in.targetSource) ? cfg.throwRange : cfg.throwRange * 0.75f;
        const float need = in.targetRevealed ? closeEnough : 120.0f; // walk onto disguised Sokkuri
        if (in.targetDist <= need) {
            enter(State::Attack, in);
            return;
        }
        // Progress / stuck tracking on straight-line distance.
        if (stuckWindowDist >= 1.0e29f) {
            stuckWindowDist = in.targetDist;
            stuckWindowStart = 0.0f;
            progressBest = in.targetDist;
        }
        if (in.targetDist < progressBest) progressBest = in.targetDist;
        stuckWindowStart += dt;
        if (stuckWindowStart >= cfg.stuckWindow) {
            if (stuckWindowDist - progressBest < cfg.stuckMinProgress) {
                char buf[256];
                std::snprintf(buf, sizeof(buf),
                              "AUTOPLAY_STUCK state=approach token=%u dist=%.0f navi=(%.0f,%.0f) replan=%d bot-driven",
                              in.targetToken, in.targetDist, in.naviX, in.naviZ,
                              approachReplans + 1);
                markers.emplace_back(buf);
                wantReplan = true;
                ++approachReplans;
                stuckWindowDist = progressBest;
                stuckWindowStart = 0.0f;
                if (approachReplans >= cfg.maxApproachReplans) {
                    // Target out of reach after N replans: GIVEUP with a
                    // reason, then idle near the Onion (enemies may come).
                    giveUp(in, "target_unreachable");
                    finishTarget(in, /*killed*/ false);
                    return;
                }
            } else {
                // Real progress: the out-of-reach count restarts.
                approachReplans = 0;
                stuckWindowDist = progressBest;
                stuckWindowStart = 0.0f;
            }
        }
        // Driver fills moveX/moveZ toward the target or the detour waypoint.
        if (in.waypointLeg) steer(in.naviX, in.naviZ, in.wpX, in.wpZ);
        else steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
        if (stateTime >= cfg.approachTimeout) {
            giveUp(in, "approach_timeout");
            finishTarget(in, /*killed*/ false);
        }
    }

    void tickAttack(float dt, const Senses& in)
    {
        if (in.containerOpen) {
            enter(State::WithdrawMenu, in);
            return;
        }
        engageTime += dt;
        if (!in.targetAlive || in.targetDead) {
            observeDeath(in);
            enter(State::Aftermath, in); // whistle back, watch the corpse
            return;
        }
        if (in.fieldPikmin < cfg.resupplyThreshold && in.hasOnion && in.onionStored > 0) {
            // bot-v4: squad eaten mid-fight and the Onion still stocks:
            // disengage, walk back, withdraw more, then return.
            char buf[256];
            std::snprintf(buf, sizeof(buf),
                          "AUTOPLAY_RESUPPLY field=%d stored=%d token=%u state=attack bot-driven",
                          in.fieldPikmin, in.onionStored, in.targetToken);
            markers.emplace_back(buf);
            enter(State::WithdrawSeek, in);
            return;
        }
        observeDamage(in);
        observeDeath(in);
        observeReceipt(in);
        // Kogane never dies: damage observed -> confirm, then move on. Both
        // the engagement-time flag and the live senses must agree it is
        // Kogane-like, so a mid-fight source switch can never score a stale
        // token down the damage-and-move-on path (wf10-v2-1 Otakara lesson;
        // the driver additionally holds engagements mid-fight).
        if (result.koganeLike && isKoganeLike(in.targetSource) && sawDamage && stateTime >= cfg.koganeConfirm) {
            finishTarget(in, /*killed*/ false);
            return;
        }
        const bool sarai = in.targetSource == 23;
        const bool kurage = in.targetSource == 57 || in.targetSource == 72;
        const float limit = kurage ? cfg.attackTimeout * cfg.kurageAttackMultiplier : cfg.attackTimeout;
        // Whistle first, then re-throw (bot-v4: real players do this):
        // - Sarai holding a Pikmin (targetGrabbing): whistle frees the grab;
        // - grabbed/thrown-off/burning squad (squadDistress: mouth-stuck,
        //   swallowed, flick/flown/fall/wave/pressed, fired/panic/drown) or
        //   scattered squad: whistle them back.
        // NOTE: a plain stick onto the enemy (attack-latching) is NOT a grab:
        // whistling those recalls our own attackers and stalls damage (v4dev-1
        // Chappy: permanent whistle, hp stuck at 0.96), so targetGrabbing only
        // whistles for the Sarai capture case.
        const bool grabWhistle = sarai && in.targetGrabbing;
        // bot-v8 merge (#871): chase keeps ONE coherent flyer-aware version.
        // Both lanes implemented chase; neither alone passes both lanes'
        // tests (unkilled flyer-at-1000 expects steer-in-Attack, undamaged
        // ground-at-1302 expects re-Approach). Kept both mechanisms, split by
        // flight: flyers (32/72 Demon/OniKurage + 23/57) steer in Attack past
        // throwRange 260 u (unkilled: no whistle/throws while far, waypoint
        // aware, re-engages on resurface); ground/teleporters (38/41/16/77)
        // re-enter Approach past 500 u so the graph routes cross-map chases
        // (undamaged, hysteresis vs 195/260 u). Both keep the attack timeout.
        // Flyers first so Demon-at-1252 steers instead of graph-routing.
        if (isFlyer(in.targetSource) && in.targetDist > cfg.throwRange) {
            // bot-unkilled (wf11): Demon bc5 tdist 3->1252 stationary PadB;
            // OniKurage bc5 tdist 265 vs throwRange 260, regen outpaces DPS.
            if (in.waypointLeg) steer(in.naviX, in.naviZ, in.wpX, in.wpZ);
            else steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
            if (stateTime >= limit) {
                giveUp(in, "attack_timeout");
                finishTarget(in, /*killed*/ false);
            }
            return;
        }
        // bot-undamaged: fled/teleporting ground targets re-enter approach;
        // straight-line attack steer cannot cross the map.
        if (in.targetDist > cfg.attackChaseDist) {
            enter(State::Approach, in);
            return;
        }
        if (whistleCooldown > 0.0f) whistleCooldown -= dt;
        if ((in.scattered || in.squadDistress || grabWhistle) && !whistling && whistleCooldown <= 0.0f) {
            whistling = true;
            whistleTime = 0.0f;
        }
        if (whistling) {
            whistleTime += dt;
            lastCommand.buttons = PadB; // hold whistle to regroup / free grabs
            // bot-v8 merge (#871): whistle timeout keeps ONE version
            // (undamaged's). Both lanes fixed the same whistle-starves-timeout
            // flaw (undamaged bc5 800 s stalls on 16/30/38/40/42/73/95/96;
            // unkilled control Chappy field=4 scat=1 800 s lock). Kept
            // undamaged's bound + cooldown (forces throw windows) with the
            // kurage-aware limit both lanes used (unkilled limit == wlimit).
            {
                const float wlimit = kurage ? cfg.attackTimeout * cfg.kurageAttackMultiplier : cfg.attackTimeout;
                if (stateTime >= wlimit) {
                    giveUp(in, "attack_timeout");
                    finishTarget(in, /*killed*/ false);
                    return;
                }
            }
            if (whistleTime >= cfg.whistleHold || (!in.scattered && !in.squadDistress && !grabWhistle)) {
                whistling = false;
                whistleCooldown = cfg.whistleCooldown; // force a throw window before re-latching
            }
            return;
        }
        if (sarai && !in.targetLow && !in.targetGrabbing) {
            // Flyer high and holding nothing: stay near it with the squad
            // following (steer under it), save Pikmin until it swoops low.
            steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
            if (stateTime >= cfg.attackTimeout) {
                giveUp(in, "attack_timeout");
                finishTarget(in, /*killed*/ false);
            }
            return;
        }
        if (cfg.kingStandoff && isKingStandoff(in.targetSource)) {
            tickKingStandoff(dt, in, limit);
            return;
        }
        // Kurage: body is on the ground (visual float only) so throw at the
        // body position; high HP means a longer window, and throws rotate to
        // spread Pikmin around the bell.
        float aimX = in.tgtX, aimZ = in.tgtZ;
        float gap = cfg.throwGap;
        if (kurage) {
            throwSpin += dt * 1.5f;
            const float dx = in.tgtX - in.naviX, dz = in.tgtZ - in.naviZ;
            const float len = std::sqrt(dx * dx + dz * dz);
            if (len > 1.0f) {
                const float wob = std::sin(throwSpin) * 40.0f;
                aimX += (-dz / len) * wob;
                aimZ += (dx / len) * wob;
            }
            gap = cfg.throwGap * (1.0f + 0.4f * std::sin(throwSpin * 0.7f));
        }
        // Keep the stick toward the target so the cursor aims at it, and
        // pulse A to throw. Flyers are thrown at from range as the game allows.
        steer(in.naviX, in.naviZ, aimX, aimZ);
        pulseA(in, cfg.throwHold, gap);
        if (stateTime >= limit) {
            giveUp(in, "attack_timeout");
            finishTarget(in, /*killed*/ false);
        }
    }

    void tickAftermath(float dt, const Senses& in)
    {
        if (in.containerOpen) {
            enter(State::WithdrawMenu, in);
            return;
        }
        engageTime += dt;
        amPhaseTime += dt;
        if (in.transportSeen || in.carryCount > 0 || in.pelletCarriers > 0) sawCarry = true;
        if (in.corpseMoving || in.corpseMoved) sawMove = true;
        observeDeath(in);
        observeReceipt(in);
        if ((!in.targetAlive || in.targetDead) && !sawDamage && !sawKill && !sawCarry && !sawReceipt) {
            // Target gone with no combat observed: nothing to wait for.
            finishTarget(in, /*claimedKill*/ false);
            return;
        }
        // bot-v5: NEVER whistle here (no PadB). Holding whistle gathers
        // Pikmin at the navi 36-65 u from the corpse so no carry ever
        // initiates (v4b diagnosis). Deliver with stick + throws only.
        const bool carryActive = in.transportSeen || in.carryCount > 0 || in.pelletCarriers > 0;
        if (sawReceipt) {
            // Onion receipt landed: score it promptly. received=1 comes ONLY
            // from this token's own ledger line; bystander CHECK
            // Bestiary:Deliver lines never score (driver + harness key by token).
            finishTarget(in, /*killed*/ true);
            return;
        }
        if (carryActive) {
            // bot-v7: crew strength vs the corpse's declared minimum
            // (carryWant, PelletConfig p01; 0 = unknown). A short lift keeps
            // seeding (SeedGrow below) instead of escorting: escorting parks
            // the squad 100-250 u away with throws suppressed, so the crew
            // can never grow (v6b-1 Tank: 4 carriers for 231 s while the
            // squad stood 105 u off; v7dev-1 Tank: a downhill slide reads
            // moving=1 forever, so the shortfall alone must trigger the
            // grow - motion with a short crew is a slide or a dropped haul,
            // never a real lift, because doLift and the pellet put-down
            // (pelletMgr.cpp:1259-1262) both gate on the minimum). A moving
            // haul, a sufficient crew, or an unknown minimum escorts exactly
            // as v5/v6 did.
            const int crew = in.pelletCarriers > 0 ? in.pelletCarriers : in.carryCount;
            // A resumed haul ends a latched stall episode: the lift is
            // viable again, so the escort takes over (or the shortfall rule
            // below re-seeds on its own terms).
            if (in.corpseMoving) amGrow = false;
            const bool seedGrow = in.carryWant > 0 && (crew < in.carryWant || amGrow);
            if (!seedGrow) {
                if (amPhase != AftermathEscort) {
                    amPhase = AftermathEscort;
                    amPhaseTime = 0.0f;
                    // Fresh escort episode (new grabs, or motion resumed
                    // after a grow): re-arm the stall watch on this fix so a
                    // later stop is timed from the resume, not from stale
                    // history.
                    amTracked = false;
                    amStallTime = 0.0f;
                }
                amGrow = false;
                amHadEnough = true;
                // bot-v5 stall watch: grabbed but not moving. Track the
                // corpse fix each tick; a bounded still time re-seeds
                // (SeedGrow) to grow the crew instead of escorting a stuck
                // lift.
                if (!amTracked) {
                    amTracked = true;
                    amLastCX = in.tgtX;
                    amLastCZ = in.tgtZ;
                    amStallTime = 0.0f;
                } else {
                    const float sx = in.tgtX - amLastCX, sz = in.tgtZ - amLastCZ;
                    if (sx * sx + sz * sz > 25.0f) { // 5 u jitter margin
                        amLastCX = in.tgtX;
                        amLastCZ = in.tgtZ;
                        amStallTime = 0.0f;
                    } else {
                        amStallTime += dt;
                    }
                }
                if (amStallTime >= cfg.carryStallWait) {
                    if (amRethrows >= cfg.aftermathRethrowMax) {
                        giveUpAftermath(in, "carry_stalled");
                        // bot-deliver (#871): never claim a kill without a death
                        // latch (bc5 55 Hanachirashi: aftermath timeout with no
                        // corpse scored killed=1). killed comes from sawKill.
                        finishTarget(in, /*killed*/ false);
                        return;
                    }
                    ++amRethrows;
                    amGrow = true;
                    amHadEnough = false;
                    amStallTime = 0.0f;
                    amLastCrew = crew;
                    amGrowStill = 0.0f;
                    logRethrow(in, "stalled");
                }
                // Escort the haul toward the Onion: follow the corpse (the
                // driver tracks the pellet into tgtX/Z) without whistling or
                // throwing so the crew keeps hauling. Hold close, not on top.
                if (in.waypointLeg) {
                    steer(in.naviX, in.naviZ, in.wpX, in.wpZ);
                } else if (in.targetToken != 0) {
                    const float dx = in.tgtX - in.naviX, dz = in.tgtZ - in.naviZ;
                    const float d2 = dx * dx + dz * dz;
                    if (d2 > 250.0f * 250.0f) steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
                    else if (d2 < 100.0f * 100.0f) steerAway(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
                }
            } else {
                // bot-v7 SeedGrow: stand the squad ON the corpse and keep
                // throwing Pikmin directly onto it (pad-only: stick + A,
                // never whistle) until the crew reaches the minimum (Escort
                // takes over), the carry is lost, or the window ends. A crew
                // that shrank below a once-viable lift re-seeds here with
                // reason=shrank; a stall episode re-seeds with reason=stalled.
                if (amHadEnough) {
                    // Regression: this lift escorted before (sufficient crew
                    // or motion) and fell short again.
                    if (amRethrows >= cfg.aftermathRethrowMax) {
                        giveUpAftermath(in, "carry_stalled");
                        // bot-deliver (#871): killed from sawKill, not claimed.
                        finishTarget(in, /*killed*/ false);
                        return;
                    }
                    ++amRethrows;
                    amHadEnough = false;
                    amLastCrew = crew;
                    amGrowStill = 0.0f;
                    logRethrow(in, sawMove ? "stalled" : "shrank");
                }
                // NOTE: amGrow is NOT latched here. A plain shortfall grows
                // purely on crew < want, so reaching the minimum returns to
                // Escort on its own. Only the Escort stall trigger latches
                // amGrow (a viable-but-stuck lift keeps growing past the
                // minimum until motion resumes); motion, a full loss, or the
                // window clears it.
                amPhase = AftermathSeed;
                amPhaseTime = 0.0f;
                // Progress: crew growth restarts the still clock; a grow
                // that adds nobody for a full stall wait burns one rethrow
                // episode (bounded), so a capped-out lift (all pellet slots
                // taken below the minimum) names carry_stalled instead of
                // sitting out the window silently.
                if (crew > amLastCrew) {
                    amLastCrew = crew;
                    amGrowStill = 0.0f;
                } else {
                    amGrowStill += dt;
                }
                if (amGrowStill >= cfg.carryStallWait) {
                    if (amRethrows >= cfg.aftermathRethrowMax) {
                        giveUpAftermath(in, "carry_stalled");
                        // bot-deliver (#871): killed from sawKill, not claimed.
                        finishTarget(in, /*killed*/ false);
                        return;
                    }
                    ++amRethrows;
                    amGrowStill = 0.0f;
                    logRethrow(in, "stalled");
                }
                seedSteerThrow(in);
            }
        } else {
            // No live carry: seed grabs. Walk ONTO the corpse (contact ring)
            // and throw Pikmin at it (thrown Pikmin attach on collision,
            // pikiState.cpp:2258-2264), then back off so the crew grabs it.
            // A full loss ends any grow episode: the next grabs start fresh.
            // Losing an escort OR a grow reseeds (bounded, reason=lost).
            const bool wasHeld = (amPhase == AftermathEscort) || amGrow;
            amGrow = false;
            amHadEnough = false;
            if (wasHeld) {
                // Carry lost en route: re-seed while rethrows remain.
                if (amRethrows >= cfg.aftermathRethrowMax) {
                    giveUpAftermath(in, "carry_stalled");
                    // bot-deliver (#871): killed from sawKill, not claimed.
                    finishTarget(in, /*killed*/ false);
                    return;
                }
                ++amRethrows;
                amPhase = AftermathSeed;
                amPhaseTime = 0.0f;
                amGrow = false;
                amHadEnough = false;
                logRethrow(in, "lost");
            }
            if (amPhase == AftermathBackoff) {
                if (in.targetToken != 0) steerAway(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
                if (in.targetDist >= cfg.aftermathBackoffDist || amPhaseTime >= cfg.aftermathSettleWait) {
                    // Settled out of contact: re-approach + re-throw if allowed.
                    if (amRethrows >= cfg.aftermathRethrowMax) {
                        giveUpAftermath(in, "carry_no_grab");
                        // bot-deliver (#871): killed from sawKill, not claimed.
                        finishTarget(in, /*killed*/ false);
                        return;
                    }
                    ++amRethrows;
                    amPhase = AftermathSeed;
                    amPhaseTime = 0.0f;
                    logRethrow(in, "no_grab");
                }
            } else {
                // Seed: close onto the corpse, throwing once in range.
                seedSteerThrow(in);
                if (amPhaseTime >= cfg.carryGrabWait && in.targetDist <= cfg.aftermathApproachRadius) {
                    // On the corpse with no grab after a bounded wait: back off.
                    amPhase = AftermathBackoff;
                    amPhaseTime = 0.0f;
                }
            }
        }
        const float waitBase = (sawKill || sawDamage) ? cfg.receiptTimeout : cfg.aftermathTimeout;
        // bot-v5: extend ONLY while carriers > 0 AND the corpse is moving
        // (live, not latched). A latched-but-stalled lift times out bounded.
        const float wait = (carryActive && in.corpseMoving) ? cfg.receiptTimeout * 2.0f : waitBase;
        if (stateTime >= wait) {
            giveUpAftermath(in, aftermathGiveupReason(in));
            // bot-deliver (#871): killed from sawKill, not claimed (55 fix).
            finishTarget(in, /*killed*/ false);
        }
    }

    void tickDone(float dt, const Senses& in)
    {
        if (in.containerOpen) {
            enter(State::WithdrawMenu, in);
            return;
        }
        // No more targets: idle near the Onion (bot-v3: enemies may walk to
        // the squad, which is how bc1/bc2 scored its only kills). Pad-only,
        // still gated by update(); neutral when there is no Onion to hold.
        if (in.waypointLeg) {
            steer(in.naviX, in.naviZ, in.wpX, in.wpZ);
        } else if (in.hasOnion && in.onionDist > cfg.arriveRadius) {
            steer(in.naviX, in.naviZ, in.onionX, in.onionZ);
        }
        if (stuckWindowDist >= 1.0e29f) {
            stuckWindowDist = in.onionDist;
            stuckWindowStart = 0.0f;
            progressBest = in.onionDist;
        }
        if (in.onionDist < progressBest) progressBest = in.onionDist;
        stuckWindowStart += dt;
        if (stuckWindowStart >= cfg.stuckWindow) {
            if (in.hasOnion && stuckWindowDist - progressBest < cfg.stuckMinProgress
                && in.onionDist > cfg.arriveRadius) {
                char buf[256];
                std::snprintf(buf, sizeof(buf),
                              "AUTOPLAY_STUCK state=done onion_dist=%.0f navi=(%.0f,%.0f) bot-driven",
                              in.onionDist, in.naviX, in.naviZ);
                markers.emplace_back(buf);
                wantReplan = true;
            }
            stuckWindowDist = progressBest;
            stuckWindowStart = 0.0f;
        }
    }

    void observeDamage(const Senses& in)
    {
        if (in.targetHealthFrac < initialHealthFrac - 0.001f) sawDamage = true;
        if (in.targetDamagedLatch) sawDamage = true;
    }

    void observeDeath(const Senses& in)
    {
        // Generic death for every species (bot-v2 gap 5): engine death
        // signals, not per-module markers. Death implies damage.
        if (in.targetDead) {
            sawKill = true;
            sawDamage = true;
        }
        if (!in.targetAlive && (sawDamage || in.targetHealthFrac <= 0.001f)) {
            sawKill = true;
            if (in.targetHealthFrac <= 0.001f) sawDamage = true;
        }
    }

    void observeReceipt(const Senses& in)
    {
        if (in.receiptSeen) sawReceipt = true;
    }

    void giveUp(const Senses& in, const char* reason)
    {
        char buf[256];
        std::snprintf(buf, sizeof(buf), "AUTOPLAY_GIVEUP reason=%s token=%u state=%s bot-driven",
                      reason, in.targetToken, stateName(state));
        markers.emplace_back(buf);
    }

    // bot-v5: aftermath giveup names WHY the delivery failed so the evidence
    // says which link broke (no grab / stalled lift / despawned / too far /
    // escorted but slow). Carriers + tdist ride along for the matrix.
    const char* aftermathGiveupReason(const Senses& in)
    {
        if (!in.pelletExists && !sawCarry) return "corpse_despawned";
        if (!sawCarry) {
            if (in.targetDist > cfg.corpseOutOfReach) return "corpse_out_of_reach";
            return "carry_no_grab";
        }
        // Grabbed but not moving NOW: never lifted, or moved then stopped
        // (min carriers not met - the crew holds a corpse it cannot lift).
        if (!in.corpseMoving) return "carry_stalled";
        if (in.targetDist > cfg.corpseOutOfReach) return "corpse_out_of_reach";
        return "receipt_timeout";
    }

    void giveUpAftermath(const Senses& in, const char* reason)
    {
        char buf[256];
        std::snprintf(buf, sizeof(buf),
                      "AUTOPLAY_GIVEUP reason=%s token=%u state=aftermath carriers=%d tdist=%.0f bot-driven",
                      reason, in.targetToken, in.carryCount, in.targetDist);
        markers.emplace_back(buf);
    }

    void logRethrow(const Senses& in, const char* why)
    {
        char buf[256];
        std::snprintf(buf, sizeof(buf), "AUTOPLAY_RETHROW token=%u attempt=%d tdist=%.0f reason=%s bot-driven",
                      in.targetToken, amRethrows, in.targetDist, why);
        markers.emplace_back(buf);
    }

    void finishTarget(const Senses& in, bool claimedKill)
    {
        result.damaged = sawDamage || sawKill;
        result.killed = (claimedKill || sawKill) && result.damaged && !result.koganeLike;
        if (result.koganeLike) {
            // Kogane never dies; damage is the outcome.
            result.killed = false;
            result.carried = false;
            result.received = false;
        } else {
            // carried=1 means an Onion receipt line was seen (bot-v2 gap 1).
            result.received = sawReceipt;
            result.carried = sawReceipt;
        }
        result.seconds = engageTime;
        char buf[256];
        if (isPowerEnabled()) {
            std::snprintf(buf, sizeof(buf),
                          "AUTOPLAY_RESULT target=%u damaged=%d killed=%d carried=%d received=%d seconds=%.0f power=1 bot-driven",
                          result.token, int(result.damaged), int(result.killed),
                          int(result.carried), int(result.received), result.seconds);
        } else {
            std::snprintf(buf, sizeof(buf),
                          "AUTOPLAY_RESULT target=%u damaged=%d killed=%d carried=%d received=%d seconds=%.0f bot-driven",
                          result.token, int(result.damaged), int(result.killed),
                          int(result.carried), int(result.received), result.seconds);
        }
        markers.emplace_back(buf);
        // The driver advances to the next target (or Done when none remain).
        enter(State::Select, in);
    }

    // #884 round 4: KingChappy attack stance (see isKingStandoff). Modes:
    //   back  - inside kingStandoffMin: walk straight away, no throws (the
    //           cursor trails behind a walking captain, so throws would miss);
    //   side  - backing for kingSidestepAfter without reaching Resume
    //           (pinned on a wall or the body): walk away + sideways at 45
    //           degrees, the side swapping every window, no throws;
    //   close - beyond kingStandoffMax: walk in and throw (the normal attack);
    //   hold  - in the band: look-band stick sliding the cursor onto the King
    //           (neutral once it is there), throw pulses; the captain stands.
    // #884 round 5 adds:
    //   evade - the King is in its attack state (Senses::targetAttacking):
    //           inside kingEvadeClear walk straight away (45 degrees sideways
    //           after kingEvadeSideAfter), no throws; once outside, stand and
    //           look/throw as in hold. It overrides every other mode until the
    //           attack ends, so the tongue slots (reach 166.7) never find the
    //           captain; the next approach re-enters through close/hold.
    //   Low-health guard: at or below kingLowHp the band is [Clear, Clear+30]
    //           instead of [Min, Max] (outside fp20 and the tongue reach).
    // AUTOPLAY_KING_STANDOFF marks each mode change.
    enum KingMode { KingBack = 0, KingSide, KingClose, KingHold, KingEvade };
    static const char* kingModeName(int m)
    {
        switch (m) {
        case KingBack: return "back";
        case KingSide: return "side";
        case KingClose: return "close";
        case KingHold: return "hold";
        case KingEvade: return "evade";
        }
        return "?";
    }

    // Unit XZ direction from the King to the captain (+x when on top of it).
    static void awayFrom(const Senses& in, float& ax, float& az)
    {
        ax = in.naviX - in.tgtX;
        az = in.naviZ - in.tgtZ;
        const float len = std::sqrt(ax * ax + az * az);
        if (len > 1.0f) {
            ax /= len;
            az /= len;
        } else {
            ax = 1.0f; // on top of the King: any direction out
            az = 0.0f;
        }
    }

    // Away + perpendicular (45 degrees); sign picks the side.
    void steerAwaySide(float ax, float az, float sign)
    {
        const float sx = ax - sign * az, sz = az + sign * ax;
        const float sl = std::sqrt(sx * sx + sz * sz);
        lastCommand.moveX = sx / sl;
        lastCommand.moveZ = sz / sl;
    }

    // Stand in the look band sliding the cursor onto the King, throw pulses.
    void kingLookAndThrow(const Senses& in)
    {
        const float fx = in.cursorValid ? in.cursorX : in.naviX;
        const float fz = in.cursorValid ? in.cursorZ : in.naviZ;
        const float dx = in.tgtX - fx, dz = in.tgtZ - fz;
        const float len = std::sqrt(dx * dx + dz * dz);
        if ((!in.cursorValid || len > cfg.kingCursorTol) && len > 1.0f) {
            lastCommand.moveX = dx / len;
            lastCommand.moveZ = dz / len;
            lastCommand.stickScale = cfg.lookStickScale;
        }
        pulseA(in, cfg.throwHold, cfg.throwGap);
    }

    void tickKingStandoff(float dt, const Senses& in, float limit)
    {
        const float d = in.targetDist;
        const bool lowHp = cfg.kingLowHp > 0.0f && in.naviHpValid && in.naviHp <= cfg.kingLowHp;
        const float bandMin = lowHp ? cfg.kingEvadeClear : cfg.kingStandoffMin;
        const float bandResume = lowHp ? cfg.kingEvadeClear + 15.0f : cfg.kingStandoffResume;
        const float bandMax = lowHp ? cfg.kingEvadeClear + 30.0f : cfg.kingStandoffMax;
        const float bandCloseStop = lowHp ? cfg.kingEvadeClear + 20.0f : cfg.kingStandoffCloseStop;
        const bool attacking = cfg.kingEvade && in.targetAttacking;
        if (attacking && !kingEvading) kingEvadeTime = 0.0f;
        kingEvading = attacking;
        int mode;
        if (kingEvading) {
            mode = KingEvade;
            // The band hysteresis restarts after the attack.
            kingBacking = false;
            kingClosing = false;
            kingBackTime = 0.0f;
            if (d < cfg.kingEvadeClear) {
                kingEvadeTime += dt;
                float ax, az;
                awayFrom(in, ax, az);
                if (kingEvadeTime < cfg.kingEvadeSideAfter) {
                    lastCommand.moveX = ax;
                    lastCommand.moveZ = az;
                } else {
                    steerAwaySide(ax, az, 1.0f);
                }
                pressOn = false; // no throws while walking out of the sweep
                pressPhase = 0.0f;
            } else {
                kingLookAndThrow(in);
            }
        } else {
            if (d < bandMin) {
                if (!kingBacking) kingBackTime = 0.0f;
                kingBacking = true;
                kingClosing = false;
            } else if (kingBacking && d >= bandResume) {
                kingBacking = false;
            }
            if (!kingBacking) {
                if (d > bandMax) kingClosing = true;
                else if (d <= bandCloseStop) kingClosing = false;
            }
            if (kingBacking) {
                kingBackTime += dt;
                float ax, az;
                awayFrom(in, ax, az);
                if (kingBackTime < cfg.kingSidestepAfter) {
                    mode = KingBack;
                    lastCommand.moveX = ax;
                    lastCommand.moveZ = az;
                } else {
                    mode = KingSide;
                    const int window = int((kingBackTime - cfg.kingSidestepAfter) / cfg.kingSidestepAfter);
                    steerAwaySide(ax, az, (window % 2 == 0) ? 1.0f : -1.0f);
                }
                pressOn = false; // no throws while walking away
                pressPhase = 0.0f;
            } else if (kingClosing) {
                mode = KingClose;
                steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
                pulseA(in, cfg.throwHold, cfg.throwGap);
            } else {
                mode = KingHold;
                kingLookAndThrow(in);
            }
        }
        if (mode != kingMode || lowHp != kingLowHpMode) {
            kingMode = mode;
            kingLowHpMode = lowHp;
            char buf[256];
            std::snprintf(buf, sizeof(buf),
                          "AUTOPLAY_KING_STANDOFF mode=%s token=%u dist=%.0f back_time=%.1f king_attack=%d "
                          "navi_hp=%.0f low_hp=%d bot-driven",
                          kingModeName(mode), in.targetToken, d, kingBacking ? kingBackTime : 0.0f,
                          in.targetAttacking ? 1 : 0, in.naviHpValid ? in.naviHp : -1.0f, lowHp ? 1 : 0);
            markers.emplace_back(buf);
        }
        if (stateTime >= limit) {
            giveUp(in, "attack_timeout");
            finishTarget(in, /*killed*/ false);
        }
    }

    // A-press pulse train: hold A for holdSecs, release for gapSecs.
    void pulseA(const Senses& in, float holdSecs, float gapSecs)
    {
        (void)in;
        pressPhase += lastDt;
        if (!pressOn && pressPhase >= gapSecs) {
            pressOn = true;
            pressPhase = 0.0f;
        } else if (pressOn && pressPhase >= holdSecs) {
            pressOn = false;
            pressPhase = 0.0f;
        }
        if (pressOn) lastCommand.buttons |= PadA;
    }

public:
    // Set by update() before the tick handlers run (pulseA needs dt).
    float lastDt = 0.016f;

private:
    Config cfg;
    State state = State::Idle;
    float stateTime = 0.0f;
    float engageTime = 0.0f;
    float pressPhase = 0.0f;
    bool pressOn = false;
    float whistleTime = 0.0f;
    bool whistling = false;
    float whistleCooldown = 0.0f;
    int menuTaps = 0;
    float menuHoldTime = 0.0f;
    bool menuConfirmed = false;
    float stuckWindowStart = 0.0f;
    float stuckWindowDist = 1.0e30f;
    bool wantReplan = false;
    float progressBest = 1.0e30f;
    int approachReplans = 0; // consecutive STUCK windows in this Approach stint (bot-v3)
    // bot-v5 aftermath delivery phases (pad-only; never whistles).
    enum AftermathPhase {
        AftermathSeed = 0, // walk onto the corpse + throw to seed grabs
        AftermathBackoff = 1, // step back out of contact so the crew grabs it
        AftermathEscort = 2, // carry active: follow the haul, no throws
    };
    AftermathPhase amPhase = AftermathSeed;
    float amPhaseTime = 0.0f;
    int amRethrows = 0; // bounded re-approach + re-throw cycles used
    bool amTracked = false; // bot-v5 stall watch has a corpse fix
    float amLastCX = 0.0f;
    float amLastCZ = 0.0f;
    float amStallTime = 0.0f; // still time while a carry is active
    bool amGrow = false; // bot-v7: SeedGrow latches a stall/shortfall episode
    bool amHadEnough = false; // bot-v7: the lift escorted (viable) before shrinking
    int amLastCrew = 0; // bot-v7: high-water crew for SeedGrow progress
    float amGrowStill = 0.0f; // bot-v7: time without crew growth in SeedGrow
    float initialHealthFrac = 1.0f;
    bool sawDamage = false;
    bool sawKill = false; // generic death latched (any species)
    bool sawCarry = false;
    bool sawMove = false; // bot-v5: corpse displacement latched (extension needs live move too)
    bool sawReceipt = false; // Onion receipt latched (authoritative for carried)
    int withdrawCycles = 0; // withdraw-menu repeat count this run
    float throwSpin = 0.0f; // Kurage throw rotation phase
    bool kingBacking = false; // #884 round 4: King standoff backing off (hysteresis)
    bool kingClosing = false; // #884 round 4: King standoff closing in (hysteresis)
    float kingBackTime = 0.0f; // continuous backing time (sidestep after kingSidestepAfter)
    int kingMode = -1; // last AUTOPLAY_KING_STANDOFF mode (-1 = none this stint)
    bool kingEvading = false; // #884 round 5: leaving the tongue sweep for the current King attack
    float kingEvadeTime = 0.0f; // time spent evading inside kingEvadeClear (sidestep after kingEvadeSideAfter)
    bool kingLowHpMode = false; // last stance used the low-health band (marker field)
    bool announced = false;
    Result result;
    Command lastCommand;
    std::vector<std::string> markers;
};

} // namespace p2autoplay
