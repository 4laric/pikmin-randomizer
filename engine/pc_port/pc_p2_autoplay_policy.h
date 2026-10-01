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
#include <set>
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
// #901 TEST-ONLY: generator uids (comma list) of vanilla P1 teki the bot may
// fight (PIKMIN_RANDOMIZER_AUTOPLAY_P1_UID), for the held-part regression run.
constexpr unsigned kP1TargetSource = 0xFFFFu;
// A vanilla teki only spawns once the squad is near its generator (after the
// arena teleport), so the bot waits in Select while a P1 uid filter is set.
inline bool p1TargetWait()
{
    const char* v = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_P1_UID");
    return isEnabled() && v && v[0];
}
inline bool isP1TargetUid(unsigned uid)
{
    const char* v = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_P1_UID");
    if (!uid || !v || !v[0]) return false;
    while (*v) {
        char* end = nullptr;
        const unsigned long n = std::strtoul(v, &end, 10);
        if (end == v) break;
        if (unsigned(n) == uid) return true;
        v = *end ? end + 1 : end;
    }
    return false;
}

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

// #958 test tooling: PIKMIN_RANDOMIZER_AUTOPLAY_PURPLE=1 makes the power-mode
// squad Purple (through the ordinary pc_p2_make_purple, like the power-mode
// flowering above) so a bot run can press the Giant Breadbug (OoPanModoki
// pressCallBack accepts Purple presses only). Inert unless power mode is on
// and the session opted in to the Purple campaign banks.
inline bool isPurplePower()
{
    if (!isPowerEnabled()) return false;
    const char* v = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_PURPLE");
    return v && v[0] && std::strcmp(v, "0") != 0;
}

// #244 test tooling: PIKMIN_RANDOMIZER_AUTOPLAY_BOMBSARAI_HOLD=<seconds>
// overrides Config::bombsaraiHold (the "stand under the carrier" hold) so a
// run can throw while the carrier still holds its bomb. Inert unless the
// autoplay gate is on; a missing or unparsable value keeps the default.
inline float bombsaraiHoldSeconds(float fallback)
{
    if (!isEnabled()) return fallback;
    const char* v = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_BOMBSARAI_HOLD");
    if (v && v[0]) {
        char* end = nullptr;
        const double d = std::strtod(v, &end);
        if (end && end != v && *end == 0 && d >= 0.0 && d < 600.0) return float(d);
    }
    return fallback;
}

// #898 TEST-ONLY observation knob: PIKMIN_RANDOMIZER_AUTOPLAY_NO_DELIVER.
// After a kill the bot does NOT deliver the corpse: it holds the whistle for
// noDeliverWhistle seconds (calls the squad off the corpse) and reports, then
// Done walks back to the Onion and idles. Used to watch what the world does
// with an abandoned carcass (a Breadbug dragging it home) - pad input only,
// nothing is forced. Inert unless the autoplay gate is on.
inline bool noDeliverEnabled()
{
    if (!isEnabled()) return false;
    const char* v = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_NO_DELIVER");
    return v && v[0] && std::strcmp(v, "0") != 0;
}

// #901 TEST-ONLY: leave a dropped ship part on the ground (whistle the squad
// off it and stop) so a day-end carry-over of an uncarried held part can be
// observed. PIKMIN_RANDOMIZER_AUTOPLAY_NO_PART_CARRY=1.
inline bool noPartCarry()
{
    const char* v = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_NO_PART_CARRY");
    return v && v[0] == '1';
}

// #901 TEST-ONLY: move the captain and every free Pikmin to a fixed ground
// point once, after the squad is out, so an arena the bot cannot route to
// (bomb-wall or pit-rim gated) can still be fought. Format "x,z" in world
// units. Gated by the autoplay gate; inert in normal play.
// PIKMIN_RANDOMIZER_AUTOPLAY_TELEPORT=-460,3560
inline bool teleportTarget(float& x, float& z)
{
    if (!isEnabled()) return false;
    const char* v = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_TELEPORT");
    if (!v || !v[0]) return false;
    char* end = nullptr;
    const double a = std::strtod(v, &end);
    if (!end || end == v || *end != ',') return false;
    char* end2 = nullptr;
    const double b = std::strtod(end + 1, &end2);
    if (!end2 || end2 == end + 1 || *end2 != 0) return false;
    x = float(a);
    z = float(b);
    return true;
}

// TEST-ONLY lure path (#994, Fiery Bulblax water stall): the captain walks this
// waypoint list in order through the normal stick path, then stands still, so a
// chasing enemy can be led across ground or water. "x,z;x,z;..." in world units.
// Gated by the autoplay gate; inert in normal play.
// PIKMIN_RANDOMIZER_AUTOPLAY_LURE=-316,2022;-100,1500
inline std::vector<std::pair<float, float>> parseLure(const char* v)
{
    std::vector<std::pair<float, float>> out;
    if (!v) return out;
    while (*v) {
        char* e1 = nullptr;
        const double a = std::strtod(v, &e1);
        if (!e1 || e1 == v || *e1 != ',') return {};
        char* e2 = nullptr;
        const double b = std::strtod(e1 + 1, &e2);
        if (!e2 || e2 == e1 + 1) return {};
        out.emplace_back(float(a), float(b));
        if (*e2 == 0) break;
        if (*e2 != ';') return {};
        v = e2 + 1;
    }
    return out;
}

inline std::vector<std::pair<float, float>> lurePath()
{
    if (!isEnabled()) return {};
    return parseLure(std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_LURE"));
}

// #901 TEST-ONLY: tap A while no captain exists (day-end movie, result screens)
// so a run reaches the next day. PIKMIN_RANDOMIZER_AUTOPLAY_NEXT_DAY=1.
inline bool nextDayTap()
{
    if (!isEnabled()) return false;
    const char* v = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_NEXT_DAY");
    return v && v[0] == '1';
}

// #901 TEST-ONLY: move the squad beside a dropped ship part whose crew stays
// short (it fell where the squad cannot walk). PIKMIN_RANDOMIZER_AUTOPLAY_TELEPORT_TO_PART=1.
inline bool teleportToPart()
{
    if (!isEnabled()) return false;
    const char* v = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_TELEPORT_TO_PART");
    return v && v[0] == '1';
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
// #244: 58 BombSarai hovers at fp01 and is engaged by throwing Pikmin onto it.
inline bool isFlyer(unsigned source) { return source == 23 || source == 57 || source == 58 || source == 32 || source == 72; }
// #898: the Breadbug (38) takes no attack damage (source damageCallBack is
// bitter-only): only a thrown Pikmin landing on it while falling hurts it
// (press). The bot leads its throws onto the walking body and keeps a
// longer attack window; it is still pad input only.
inline bool isPressOnly(unsigned source) { return source == 38 || source == 40; }
// #898 aftermath: the Breadbug corpse is small. Walking onto it (the generic
// seed) shoves it ahead of the captain (pellet collision, navi at ~20 u) and
// the walking cursor sits ~78 u ahead, so thrown Pikmin fly over it and land
// past it (v2c: carriers=0 for 60 s, cursor 78 u beyond the corpse). For
// these corpses the bot stands off, slides the cursor onto the corpse with
// the P1 look band (the captain stands still) and throws only when the
// cursor is on it. Pad input only, like every other bot stance.
inline bool aimsCorpseWithCursor(unsigned source) { return source == 38 || source == 40; }

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

// #245 Antenna Beetle (Fuefuki) stance. The beetle's whistle claims every
// Pikmin inside attackRadius (fp22 = 130, FuefukiState.cpp updateWhisle), so
// a captain in contact loses his whole squad each cast (d4: 76 held at
// death) and never throws. A player fights it from range: stand outside the
// cast ring and lob Pikmin onto its back, which is also the only way to
// reach the source pressCallBack (a thrown Pikmin landing while mCanStruggle
// flips it into Struggle, Fuefuki.cpp:163-168). The stance reuses the King
// back/close/hold machinery with its own band (Config::fuefuki*); the King's
// tongue evade and low-health band do not apply. Pad input only.
inline bool isFuefukiStandoff(unsigned source) { return source == 41; }
// #897 bot roll evade: Segmented Crawbster (DangoMushi, 94). The body is
// invulnerable except inside the Turn stickable window (EB_Invulnerable,
// DangoMushiState.cpp:530), its StateAttack ball roll presses every grounded
// Pikmin it touches (PikiPressedState: lethal), and it only wakes from Stay
// inside fp11 (150). A squad thrown at the ball outside the window therefore
// only feeds the next roll (r5/r6: 93/93 and 77/77 pressed Pikmin died). The
// roller stance wakes it, then holds a standoff with no throws, dodges the
// roll sideways with the squad whistled tight, and throws everything only
// while the Turn window is open. Only 94 has this stance.
inline bool isRollerStance(unsigned source) { return source == 94; }

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
    // OniKurage (72) has 4500 HP against the Kurage 2500 (retail fp00): scale its window.
    float greaterKurageAttackMultiplier = 1.8f;
    float pressOnlyAttackMultiplier = 5.0f; // #898 press-only targets: one press per landed throw
    float pressLeadSeconds = 0.6f; // #898 aim ahead of a walking press-only target
    float corpseAimNear = 40.0f; // #898 cursor-aim corpses: closer than this -> step back (never shove it)
    float corpseAimFar = 70.0f; // #898 cursor-aim corpses: farther than this -> walk in (no throws)
    float corpseCursorTol = 12.0f; // #898 cursor-aim corpses: throw only with the cursor this close
    float corpseAimWhistleCooldown = 10.0f; // #898 cursor-aim corpses: throw window after a regroup whistle
    bool noDeliver = false; // #898 TEST-ONLY: abandon corpses (also env NO_DELIVER)
    float noDeliverWhistle = 3.0f; // #898 whistle hold before abandoning a corpse
    // #246: the Titan Dweevil (73) soaks 4 x 6000 weapon HP before its 5000
    // body HP is exposed, and only a Pikmin stuck on a weapon's own part
    // damages it; the bot keeps throwing for a longer window (bot assistance).
    float titanAttackMultiplier = 6.0f;
    // Wave-3 lane 53: the Emperor Bulblax (53) is a 1300 HP multi-cycle boss whose source
    // damageCallBack only counts stuck attackers, so the bot keeps fighting for a longer
    // window than a single throw burst (bot assistance, like the Titan).
    float kingAttackMultiplier = 5.0f;
    // #246: a Titan lets go of every stuck Pikmin at Dead (deathProcedure
    // setAlive(false)) ~11 s before its corpse forms, so the aftermath can
    // start with an empty squad and nobody to seed-throw. A player whistles
    // the strays: bounded episodes, only while the squad is empty.
    int titanAftermathWhistles = 3;
    float titanAftermathWhistleHold = 1.5f;
    float titanRegroupWalk = 12.0f; // #246: max walk to the stray centroid per regroup episode
    float titanSeedRingMin = 60.0f;  // #246: Titan corpse seeding standoff ring (cursor ~95 u ahead)
    float titanSeedRingMax = 140.0f;
    float saraiLowHeight = 120.0f; // Sarai thrown at only when within this height above ground (or grabbing)
    float throwRange = 260.0f; // XZ distance at which throws start
    float arriveRadius = 90.0f; // XZ distance considered "at" the Onion
    float throwHold = 0.12f; // A held per throw pulse
    float throwGap = 0.55f; // gap between throw pulses
    float empressWalkMax = 45.0f; // #256: bound on one regroup walk to the idle strays
    float whistleHold = 1.6f; // B held to regroup / call back
    int pressRegroupBelow = 10;  // #958 press-only target: whistle when the party is below this ...
    int pressRegroupStrays = 10; // ... and at least this many idle strays lie about
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
    // #244 BombSarai 58: on each fresh engagement the squad first stands under
    // the carrier (no throws) for this long, the way a player waits out the
    // bomb drop; the carrier's own source Release decides whether it drops.
    float bombsaraiHold = 6.0f;
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
    // #245 Fuefuki stance band (XZ). d5 showed a band outside the cast ring
    // (150-195) never lands a throw: the cursor trails the backing stick and
    // P1 throws land at the cursor, so no thrown Pikmin ever reached the
    // beetle (presses=0). The stance now holds a throwing band inside the
    // ring while the beetle is not casting and leaves the ring
    // (fuefukiEvadeClear) for the whole whistle cast (Senses::targetAttacking,
    // source StateWhisle; the ring grows to fp22 = 130 over 1 s, so the
    // captain at <= 95 walks out ahead of it).
    bool fuefukiStandoff = true;
    float fuefukiStandoffMin = 55.0f;
    float fuefukiStandoffResume = 65.0f;
    float fuefukiStandoffMax = 95.0f;
    float fuefukiStandoffCloseStop = 85.0f;
    float fuefukiEvadeClear = 165.0f;
    // #245 owner-death Panic reclaim (Aftermath, Fuefuki targets only): the
    // beetle's followers go into an astonish Panic when it dies
    // (FuefukiState.cpp StateDead -> releasing the whistle hold). A player
    // whistles them back before carrying; the bot does the same when a
    // panicking Pikmin is inside panicReclaimRadius (under the 100 u whistle
    // max radius, NaviMgr.h:27), for whistleHold, at most panicReclaimMax
    // times per engagement, with whistleCooldown between.
    bool panicReclaim = true;
    float panicReclaimRadius = 90.0f;
    int panicReclaimMax = 4;
    float lookStickScale = 0.24f; // 0.24*127 = 30 bytes: |stick| 0.41 (look band), no MSTICK bits (> 32)
    // #897 roller stance (isRollerStance). The standoff band sits around the
    // source fp20 attack range (300) so the Crawbster keeps coming and rolls;
    // the dodge starts while the ball is within rollerEvadeRange.
    bool rollerStance = true;
    float rollerStandMin = 180.0f; // ar8: a 280..400 band sat outside fp20 (300) and the Crawbster never rolled
    float rollerStandMax = 270.0f;
    float rollerWakeDist = 110.0f; // walk inside fp11 (150) to wake it from Stay
    float rollerEvadeRange = 650.0f;
    float rollerThrowGap = 0.10f; // Turn window: throw as fast as the pad allows (ar7: ~2/s left 13-15 hits per window)
    float rollerThrowHold = 0.08f;
    float rollerAttackTimeout = 900.0f; // a multi-cycle boss fight, not one throw burst
    float rollerChaseDist = 1100.0f; // the ball rolls away far; only a real loss re-approaches
    // Tier gate: the Impact arena sits on an upper tier (y=20) above the box
    // corridor (y=-30). XZ-close across the ledge is not "in range" (ar6: the
    // bot stood 400 below the ledge for minutes while the Crawbster could not
    // reach it). Past this |dy| the roller keeps approaching over the route.
    float rollerTierDy = 40.0f;
    float rollerSeedStand = 130.0f; // corpse seeding: stop here and aim the cursor onto the corpse
    float rollerHomeLeash = 200.0f; // back-off blends toward home past this XZ distance from it
    // #897 power-mode resupply: the power squad is the whole stocked Onion,
    // so after a crush the Onion is empty and the v4 resupply (needs stock)
    // never fired (r5 field=1, r6 no resupply). Below this field count power
    // mode walks back to the Onion, the driver restocks it through the same
    // power stock path and exits it again (AUTOPLAY_POWER_RESTOCK), then the
    // Brain re-selects. 0 disables.
    int powerResupplyField = 25;
    int powerRestockMax = 12;
    // #897 push obstacles: a P1 HinderRock (the Impact Site cardboard box)
    // blocks the only walk to the impact_goolix arena (ar1: 6 STUCK at the
    // box -> target_unreachable). When the driver reports an unfinished box
    // in front of the approach, close to obstaclePushDist and throw at it;
    // thrown Pikmin push it (HinderRock::workable). Stuck windows do not count
    // while pushing; obstaclePushMax bounds one approach stint.
    float obstaclePushDist = 150.0f;
    float obstaclePushGap = 0.35f;
    float obstaclePushMax = 120.0f;
    float obstacleRegroupEvery = 6.0f; // after a push: whistle pulse period while scattered
    // #901 part gather: stand in this XZ ring around a dropped ship part and
    // swarm (C-stick) the party onto it; formed Pikmin that touch a pellet
    // with a free slot start carrying it (piki.cpp collisionCallback
    // OBJTYPE_Pellet, distCheck true while the C-stick is held).
    float partRingMin = 80.0f;
    float partRingMax = 160.0f;
    float partWhistleCooldown = 5.0f; // gap between gather whistles
    float partFreeFar = 120.0f; // free-Pikmin centroid this far from the part: whistle there (carriers safe)
    // #901 route obstacles: after a STUCK window next to an unfinished gate /
    // bridge / hinder rock, stand off it, swarm and throw the squad onto it
    // (formed Pikmin that touch a gate break it, piki.cpp collisionCallback
    // isSluice; thrown Pikmin landing on a bridge or rock work it,
    // pikiState.cpp flying collide), bounded by obstacleTimeout.
    float obstacleRingMin = 70.0f;
    float obstacleRingMax = 150.0f;
    float obstacleTimeout = 150.0f;
    float obstacleHardTimeout = 420.0f; // hard (23) gates: far more health per stage
    // #901 ranged attack: an approach that goes STUCK this close to a ground
    // target (a ledge or pit rim between them) throws from where it stands,
    // sliding the cursor onto the target in the look band (cursor reach is
    // mCursorMaxRadius 300, NaviMgr.h p46), instead of routing away.
    float rangedAttackDist = 290.0f;
 // 0.24*127 = 30 bytes: |stick| 0.41 (look band), no MSTICK bits (> 32)
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
    bool trackingPart = false; // #901: the tracked pellet is a dropped ship part
    // #901 part gather (TEST-ONLY, read only while trackingPart): the
    // captain's party (FormationMode Pikmin following him), idle FreeMode
    // Pikmin near the part and their XZ centroid, and a latch that the part
    // this engagement tracked has left the field (delivered to the ship).
    int partyCount = 0;
    int freeCount = 0;
    float freeX = 0.0f;
    float freeZ = 0.0f;
    bool partGone = false;
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
    int squadPikmin = 0; // #246: live Pikmin following the captain (FormationMode)
    // #246: idle field Pikmin (FreeMode, not carrying, not in distress) and
    // their centroid, so a Titan aftermath can walk to them before whistling.
    int strayPikmin = 0;
    // #256: "lost" Pikmin = idle strays or Formation followers left 350-1000 u
    // behind (a14: 33 followers + 36 strays sat at the arena ledge foot); the
    // nearest one, and how many Pikmin are within 350 u. The whistle reaches
    // only 100 u (NaviMgr p01).
    int lostPikmin = 0;
    int nearPikmin = 0;
    float strayNearX = 0.0f;
    float strayNearZ = 0.0f;
    float strayNearDist = 1.0e30f;
    float strayX = 0.0f;
    float strayZ = 0.0f;
    int onionStored = 0; // Pikmin stored in the nearest stocked Onion
    float onionDist = 1.0e30f; // XZ distance to that Onion
    bool containerOpen = false; // Onion container UI is up
    // Current-target facts. targetToken==0 means "no target".
    unsigned targetToken = 0;
    unsigned targetSource = 0;
    float tgtX = 0.0f;
    float tgtZ = 0.0f;
    // #246 bot assistance: a throw aim point other than the actor centre
    // (the Titan's nearest captured weapon, the only stickable part).
    bool aimValid = false;
    float aimX = 0.0f;
    float aimZ = 0.0f;
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
    // #246/#899: the driver is walking the squad into an unfinished P1
    // HinderRock (pushable box) on the approach route. Pikmin push it by the
    // normal formation collision (piki.cpp PushstoneMode); the captain stands
    // still meanwhile, so these windows are not "stuck" and do not age the
    // approach timeout. The driver caps the total obstacle time.
    bool obstacleWork = false;
    // #901: XZ length still to walk along the planned route (captain -> active
    // leg -> remaining legs -> target); 0 = no route. Approach measures
    // progress on it while a route is active, so a detour that first leads
    // away from the target is not called STUCK and thrown away.
    float pathRemaining = 0.0f;
    // #901 route obstacles (TEST-ONLY bot): the nearest unfinished P1 work
    // obstacle near the captain (gate, bridge, hinder rock, climbing stalk;
    // kind 1/2/3/4, 0 = none) and the Pikmin working one now
    // (BreakWall/Bridge/Pushstone/Rope).
    int obstacleKind = 0;
    float obstacleX = 0.0f;
    float obstacleZ = 0.0f;
    int workCount = 0;
    // Diagnostics for the log: the obstacle's object type (22 soft gate,
    // 23 hard gate, bridge/rock = their WorkObject kind), build stage and
    // health. Bomb gates (24/25) are never reported: punching cannot open them.
    int obstacleType = 0;
    // #901: a movie (e.g. the first-gate-down demo), a UI overlay or a global
    // pause holds the sim. The Brain then taps A (the P1 skip / dismiss
    // input) and freezes its own clocks instead of calling the world STUCK.
    bool movieActive = false;
    bool overlayActive = false;
    int obstacleStage = 0;
    int obstacleStages = 0;
    float obstacleHealth = 0.0f;
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
    // #245: Pikmin in PIKISTATE_Panic (any cause) and the XZ distance from
    // the captain to the nearest one (1e30 when none). Only the Fuefuki
    // Aftermath panic reclaim reads them.
    int panicCount = 0;
    float panicNearest = 1.0e30f;
    // #897 roller stance senses (read-only DangoMushi probe; the driver sets
    // them for source 94 only). Dormant = still in Stay (hidden).
    bool targetDormant = false;
    // #897 the roller's home (where it was first seen, in Stay): the arena
    // floor. Evade/back-off lean toward it so the captain does not walk off
    // the arena tier (ar7: an evade dropped him off the Impact ledge).
    bool homeValid = false;
    float homeX = 0.0f;
    float homeZ = 0.0f;
    bool targetDyValid = false; // #897 target height minus captain height is known
    float targetDy = 0.0f;
    bool targetRolling = false;
    bool targetVulnerable = false;
    float targetVelX = 0.0f;
    float targetVelZ = 0.0f;
    // #897 power resupply: restocks the driver has already spent this run.
    int powerRestocks = 0;
    // #897 push obstacle: nearest unfinished HinderRock in front of the
    // approach (driver: within its scan range and ahead of the current leg).
    bool pushValid = false;
    float pushX = 0.0f;
    float pushZ = 0.0f;
    float pushDist = 1.0e30f;
    bool pushMoving = false;
    // Throw aim: a point just outside the face toward the captain (a throw
    // at the centre lands ON the box and those Pikmin never push; ar2).
    float pushAimX = 0.0f;
    float pushAimZ = 0.0f;
    // #256 Empress Bulblax: she is charging (Flick) or rolling (read-only
    // via pc_p2_queen_teki_probe). A player recalls the squad and steps off
    // the roll line along her body axis; dodgeX/Z is that safe point.
    bool queenDanger = false;
    float dodgeX = 0.0f;
    float dodgeZ = 0.0f;
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
    // #901: world-space XZ C-stick (swarm) direction; (0,0) = C-stick idle.
    // The driver converts it through the camera basis like moveX/moveZ.
    float swarmX = 0.0f;
    float swarmZ = 0.0f;
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
        aimWhistleLeft = 0.0f;
        aimWhistleCooldown = 0.0f;
        menuTaps = 0;
        menuHoldTime = 0.0f;
        menuConfirmed = false;
        stuckWindowStart = 0.0f;
        stuckWindowDist = 1.0e30f;
        wantReplan = false;
        progressBest = 1.0e30f;
        approachReplans = 0;
        approachOnRoute = false;
        obsWork = false;
        obsTime = 0.0f;
        obsLogTime = 0.0f;
        obsGiveups = 0;
        rangedAttack = false;
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
        amWhistles = 0;
        amWhistleTime = 0.0f;
        amRegroupWalk = 0.0f;
        pgWhistle = 0.0f;
        pgCooldown = 0.0f;
        pgLogTime = 0.0f;
        pgSawPart = false;
        pgCrewBest = 0;
        pgStall = 0.0f;
        withdrawCycles = 0;
        throwSpin = 0.0f;
        leadValid = false;
        leadVX = leadVZ = 0.0f;
        kingBacking = false;
        kingClosing = false;
        kingBackTime = 0.0f;
        kingMode = -1;
        kingEvading = false;
        kingEvadeTime = 0.0f;
        kingLowHpMode = false;
        amPanicWhistles = 0;
        amPanicWhistle = false;
        amPanicTime = 0.0f;
        amPanicCooldown = 0.0f;
        rollerMode = -1;
        rollerWhistleTime = 0.0f;
        powerResupplying = false;
        powerAtOnion = false;
        pushTime = 0.0f;
        pushing = false;
        pushedThisStint = false;
        regroupClock = 0.0f;
        legKnown = false;
        tierReplanAsked = false;
        result = Result{};
        markers.clear();
        lastCommand = Command{};
        announced = false;
    }

    State current() const { return state; }
    Command command() const { return lastCommand; }
    bool replanWanted() const { return wantReplan; }
    // #897: the Brain is back at the Onion for a power-mode resupply and wants
    // the driver to restock + exit it (driver: once per visit, bounded).
    bool wantsPowerRestock() const { return state == State::WithdrawSeek && powerResupplying && powerAtOnion; }
    void clearReplan() { wantReplan = false; }
    // #256: the Empress regroup asks the driver to route (waypoint graph) to
    // the nearest idle stray; a straight steer hits the arena ledge.
    bool strayRouteWanted() const { return wantStrayRoute; }
    float strayRouteGoalX() const { return strayRouteX; }
    float strayRouteGoalZ() const { return strayRouteZ; }
    void clearStrayRoute() { wantStrayRoute = false; }
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
        if ((in.movieActive || in.overlayActive) && !in.containerOpen && state != State::Idle
            && state != State::WithdrawMenu) {
            uiWaitTime += dt;
            uiLogTime -= dt;
            if (uiLogTime <= 0.0f) {
                uiLogTime = 5.0f;
                char buf[160];
                std::snprintf(buf, sizeof(buf), "AUTOPLAY_UI_WAIT movie=%d overlay=%d seconds=%.0f state=%s bot-driven",
                              in.movieActive ? 1 : 0, in.overlayActive ? 1 : 0, uiWaitTime, stateName(state));
                markers.emplace_back(buf);
            }
            pulseA(in, cfg.throwHold, 1.0f);
            return;
        }
        uiWaitTime = 0.0f;
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
        aimWhistleLeft = 0.0f;
        aimWhistleCooldown = 0.0f;
        menuTaps = 0;
        menuHoldTime = 0.0f;
        menuConfirmed = false;
        stuckWindowStart = 0.0f;
        stuckWindowDist = 1.0e30f;
        wantReplan = false;
        progressBest = 1.0e30f;
        approachReplans = 0;
        approachOnRoute = false;
        obsWork = false;
        obsTime = 0.0f;
        obsLogTime = 0.0f;
        obsGiveups = 0;
        rangedAttack = false;
        kingBacking = false;
        kingClosing = false;
        kingBackTime = 0.0f;
        kingMode = -1;
        kingEvading = false;
        kingEvadeTime = 0.0f;
        kingLowHpMode = false;
        rollerMode = -1;
        rollerWhistleTime = 0.0f;
        powerAtOnion = false;
        pushTime = 0.0f;
        pushing = false;
        regroupClock = 0.0f;
        legKnown = false;
        tierReplanAsked = false;
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
        // #256: the Empress dies against the arena's far wall (a13/a15: carcass
        // 617 u away over a ledge, the captain pushed at the wall for minutes,
        // carry_no_grab). A straight steer cannot reach it, so ask the driver
        // for a waypoint route every 15 s and follow its legs while far.
        if (in.targetSource == 30 && in.targetToken != 0 && in.targetDist > 250.0f) {
            seedRouteCooldown -= in.dt > 0.0f && in.dt <= 0.5f ? in.dt : 0.016f;
            if (!in.waypointLeg && seedRouteCooldown <= 0.0f) {
                wantReplan = true;
                seedRouteCooldown = 15.0f;
            }
            if (in.waypointLeg) steer(in.naviX, in.naviZ, in.wpX, in.wpZ);
            else steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
            return;
        }
        if (!in.waypointLeg && in.targetToken != 0 && in.cursorValid && aimsCorpseWithCursor(in.targetSource)) {
            cursorAimThrow(in);
            return;
        }
        // #246 a8-a11: standing ON the Titan corpse put the throw cursor
        // (~95 u ahead of the captain) past it, so thrown Pikmin landed idle
        // and the crew never grew past 1-2 of 10. For the Titan, hold a
        // standoff ring and slide the cursor onto the corpse in the P1 look
        // band (the King standoff's aim), then throw.
        // #256: the Empress carcass (radius 50, a12: 5 carriers of 20 from standing
        // on it) gets the same standoff ring.
        if ((in.targetSource == 73 || in.targetSource == 30) && in.targetToken != 0 && !in.waypointLeg
            && in.cursorValid) {
            if (in.targetDist < cfg.titanSeedRingMin) {
                steerAway(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
            } else if (in.targetDist > cfg.titanSeedRingMax) {
                steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
            } else {
                kingLookAndThrow(in);
            }
            return;
        }
        // #897 big corpse (Crawbster): walking onto it pins the captain at its
        // centre with the cursor ~100 past the far edge, so throws land off
        // the corpse (ar9: 11/20 carriers, carry_stalled). Inside
        // rollerSeedStand stop, and slide the cursor onto the corpse with the
        // look-band stick, then throw.
        if (cfg.rollerStance && isRollerStance(in.targetSource) && in.targetToken != 0
            && in.targetDist <= cfg.rollerSeedStand && in.cursorValid) {
            const float ex = in.tgtX - in.cursorX, ez = in.tgtZ - in.cursorZ;
            const float el = std::sqrt(ex * ex + ez * ez);
            if (el > cfg.kingCursorTol) {
                lastCommand.moveX = ex / el;
                lastCommand.moveZ = ez / el;
                lastCommand.stickScale = cfg.lookStickScale;
            }
            if (el <= cfg.kingCursorTol * 2.0f) pulseA(in, cfg.throwHold, cfg.throwGap);
            return;
        }
        if (in.waypointLeg) steer(in.naviX, in.naviZ, in.wpX, in.wpZ);
        else if (in.targetToken != 0) steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
        if (in.targetDist <= cfg.throwRange && in.targetToken != 0) pulseA(in, cfg.throwHold, cfg.throwGap);
    }

    // #898: stand off the corpse, slide the cursor onto it, throw on it.
    void cursorAimThrow(const Senses& in)
    {
        const float d = in.targetDist;
        // Regroup: throws need Pikmin at the captain. After the presses the
        // squad is spread over the kill site (y1: 53 on the field, fewer than
        // 5 near the captain, 2 carriers for 100 s, no throw ever landed).
        // This path only runs while the crew is short (Seed / SeedGrow), so a
        // stuck partial crew loses nothing to the whistle. Whistle for
        // whistleHold, then a throw window of corpseAimWhistleCooldown.
        if (aimWhistleCooldown > 0.0f) aimWhistleCooldown -= lastDt;
        if (aimWhistleLeft <= 0.0f && in.scattered && aimWhistleCooldown <= 0.0f && d <= cfg.throwRange) {
            aimWhistleLeft = cfg.whistleHold;
            char buf[128];
            std::snprintf(buf, sizeof(buf), "AUTOPLAY_AIM_REGROUP token=%u tdist=%.0f bot-driven", in.targetToken, d);
            markers.emplace_back(buf);
        }
        if (aimWhistleLeft > 0.0f) {
            aimWhistleLeft -= lastDt;
            if (aimWhistleLeft <= 0.0f) aimWhistleCooldown = cfg.corpseAimWhistleCooldown;
            lastCommand.buttons = PadB;
            pressOn = false;
            pressPhase = 0.0f;
            return;
        }
        if (d > cfg.corpseAimFar) {
            steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
            pressOn = false; // no throws while walking: the cursor trails the stick
            pressPhase = 0.0f;
            return;
        }
        if (d < cfg.corpseAimNear) {
            steerAway(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
            pressOn = false;
            pressPhase = 0.0f;
            return;
        }
        const float dx = in.tgtX - in.cursorX, dz = in.tgtZ - in.cursorZ;
        const float len = std::sqrt(dx * dx + dz * dz);
        if (len > cfg.corpseCursorTol && len > 1.0f) {
            lastCommand.moveX = dx / len;
            lastCommand.moveZ = dz / len;
            lastCommand.stickScale = cfg.lookStickScale;
            // Keep holding a Pikmin already in hand; release only on target.
            if (pressOn) lastCommand.buttons |= PadA;
            return;
        }
        pulseA(in, cfg.throwHold, cfg.throwGap);
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
            if (powerResupplying) {
                tickPowerResupply(dt, in);
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
        if (in.targetToken == 0 && result.token == 0 && p2autoplay::p1TargetWait() && stateTime < 60.0f) {
            return; // #901: the vanilla holder has not spawned yet
        }
        if (in.targetToken == 0 || !in.targetAlive) {
            // bot-v6: verify the target is still alive before Select. A dead /
            // absent target used to fall through to Done silently, dropping the
            // engagement (bc4: kills with no RESULT after an aftermath ->
            // container bounce). Name it instead: a mid-engagement kill latched
            // for THIS token returns to Aftermath to finish v5 delivery;
            // anything else is GIVEUP reason=target_gone with the token/state
            // as evidence. token==0 (no targets at all) still idles silently.
            if (!resultReported && result.token != 0 && result.token == in.targetToken && (sawDamage || sawKill)) {
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
        // #898: a RESULT already reported for result.token must not be
        // re-reported on every Select tick (multi-target sweep loop).
        if (!resultReported && result.token != 0 && in.targetToken != 0 && result.token != in.targetToken
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
        amPanicWhistles = 0;
        amPanicWhistle = false;
        amPanicTime = 0.0f;
        amPanicCooldown = 0.0f;
        amWhistles = 0;
        amWhistleTime = 0.0f;
        amRegroupWalk = 0.0f;
        result = Result{};
        resultReported = false;
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
        if (wantPowerResupply(in, "approach")) return;
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
        const bool otherTier = rollerOtherTier(in);
        if (otherTier && !tierReplanAsked && !in.waypointLeg) {
            // Straight at it only hits the ledge: ask for a route now.
            tierReplanAsked = true;
            wantReplan = true;
            char buf[200];
            std::snprintf(buf, sizeof(buf), "AUTOPLAY_TIER token=%u dy=%.0f dist=%.0f replan=1 bot-driven",
                          in.targetToken, in.targetDy, in.targetDist);
            markers.emplace_back(buf);
        }
        if (in.targetDist <= need && !otherTier) {
            enter(State::Attack, in);
            return;
        }
        if (in.obstacleWork) {
            // Pushing a HinderRock: steer into it, no stuck window, no
            // approach-timeout ageing (the driver bounds the push time).
            stateTime -= dt;
            stuckWindowDist = 1.0e30f;
            stuckWindowStart = 0.0f;
            steer(in.naviX, in.naviZ, in.wpX, in.wpZ);
            return;
        }
        if (tickObstaclePush(dt, in)) return;
        if (tickObstacle(dt, in)) return;
        // Progress / stuck tracking on straight-line distance, or on the
        // remaining route length while a route is active (#901: a
        // straight-line window threw away every long detour into a far arena).
        // #897: with a detour leg but no route length, progress is measured
        // to that leg (a real route may first lead AWAY from the target: the
        // Impact Site ramp from the box corridor east to the upper tier), and
        // reaching a new leg is progress in itself.
        const bool onRoute = in.waypointLeg && in.pathRemaining > 0.0f;
        float metric = onRoute ? in.pathRemaining : in.targetDist;
        if (onRoute != approachOnRoute) {
            approachOnRoute = onRoute;
            stuckWindowDist = 1.0e30f; // re-anchor on the new metric
        }
        if (in.waypointLeg && !onRoute) {
            const float lx = in.wpX - in.naviX, lz = in.wpZ - in.naviZ;
            metric = std::sqrt(lx * lx + lz * lz);
            if (!legKnown || std::fabs(in.wpX - legX) > 1.0f || std::fabs(in.wpZ - legZ) > 1.0f) {
                if (legKnown) approachReplans = 0;
                legKnown = true;
                legX = in.wpX;
                legZ = in.wpZ;
                stuckWindowDist = 1.0e30f;
            }
        } else if (legKnown) {
            legKnown = false;
            stuckWindowDist = 1.0e30f;
        }
        if (stuckWindowDist >= 1.0e29f) {
            stuckWindowDist = metric;
            stuckWindowStart = 0.0f;
            progressBest = metric;
        }
        if (metric < progressBest) progressBest = metric;
        stuckWindowStart += dt;
        if (stuckWindowStart >= cfg.stuckWindow) {
            if (stuckWindowDist - progressBest < cfg.stuckMinProgress) {
                char buf[256];
                std::snprintf(buf, sizeof(buf),
                              "AUTOPLAY_STUCK state=approach token=%u dist=%.0f navi=(%.0f,%.0f) replan=%d bot-driven",
                              in.targetToken, in.targetDist, in.naviX, in.naviZ,
                              approachReplans + 1);
                markers.emplace_back(buf);
                // #901: replan once first (the route may climb to the
                // target's own floor level); throw from range only when that
                // replan also stalls here.
                if (in.targetDist <= cfg.rangedAttackDist && !isFlyer(in.targetSource) && approachReplans >= 1) {
                    char rbuf[160];
                    std::snprintf(rbuf, sizeof(rbuf), "AUTOPLAY_RANGED token=%u dist=%.0f bot-driven",
                                  in.targetToken, in.targetDist);
                    markers.emplace_back(rbuf);
                    enter(State::Attack, in);
                    rangedAttack = true;
                    return;
                }
                wantReplan = true;
                ++approachReplans;
                stuckWindowDist = 1.0e30f; // the replan changes the route: re-anchor
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

    // #901 route obstacle work (TEST-ONLY). Returns true while it owns the
    // pad this tick. Starts only after a STUCK window with an unfinished
    // obstacle near the captain; ends when no unfinished obstacle is near any
    // more, or after obstacleTimeout (then the normal replan / unreachable
    // rules resume).
    bool tickObstacle(float dt, const Senses& in)
    {
        if (!obsWork) {
            if (in.obstacleKind == 0 || approachReplans < 1 || obsGiveups >= 2) return false;
            obsWork = true;
            obsTime = 0.0f;
            obsLogTime = 0.0f;
            char buf[200];
            std::snprintf(buf, sizeof(buf),
                          "AUTOPLAY_OBSTACLE start kind=%d at=(%.0f,%.0f) token=%u bot-driven",
                          in.obstacleKind, in.obstacleX, in.obstacleZ, in.targetToken);
            markers.emplace_back(buf);
        }
        if (in.obstacleKind == 0) {
            obsWork = false;
            char buf[160];
            std::snprintf(buf, sizeof(buf), "AUTOPLAY_OBSTACLE done seconds=%.0f token=%u bot-driven",
                          obsTime, in.targetToken);
            markers.emplace_back(buf);
            approachReplans = 0;
            stuckWindowDist = 1.0e30f;
            stuckWindowStart = 0.0f;
            wantReplan = true; // the way is open: route again
            return false;
        }
        obsTime += dt;
        stateTime -= dt; // obstacle work does not spend the approach budget
        const float limit = in.obstacleType == 23 ? cfg.obstacleHardTimeout : cfg.obstacleTimeout;
        if (obsTime >= limit) {
            obsWork = false;
            ++obsGiveups;
            char buf[160];
            std::snprintf(buf, sizeof(buf), "AUTOPLAY_OBSTACLE timeout kind=%d work=%d token=%u bot-driven",
                          in.obstacleKind, in.workCount, in.targetToken);
            markers.emplace_back(buf);
            return false;
        }
        obsLogTime -= dt;
        if (obsLogTime <= 0.0f) {
            obsLogTime = 5.0f;
            char buf[200];
            std::snprintf(buf, sizeof(buf),
                          "AUTOPLAY_OBSTACLE work kind=%d type=%d stage=%d/%d health=%.0f work=%d at=(%.0f,%.0f) seconds=%.0f bot-driven",
                          in.obstacleKind, in.obstacleType, in.obstacleStage, in.obstacleStages, in.obstacleHealth,
                          in.workCount, in.obstacleX, in.obstacleZ, obsTime);
            markers.emplace_back(buf);
        }
        const float dx = in.obstacleX - in.naviX, dz = in.obstacleZ - in.naviZ;
        const float d = std::sqrt(dx * dx + dz * dz);
        if (d > cfg.obstacleRingMax) {
            steer(in.naviX, in.naviZ, in.obstacleX, in.obstacleZ);
        } else if (d < cfg.obstacleRingMin) {
            steerAway(in.naviX, in.naviZ, in.obstacleX, in.obstacleZ);
        } else {
            // Look band: the captain stops and the cursor slides onto it.
            steer(in.naviX, in.naviZ, in.obstacleX, in.obstacleZ);
            lastCommand.stickScale = cfg.lookStickScale;
            pulseA(in, cfg.throwHold, cfg.throwGap);
        }
        if (d > 1.0f) {
            lastCommand.swarmX = dx / d;
            lastCommand.swarmZ = dz / d;
        }
        stuckWindowDist = 1.0e30f;
        stuckWindowStart = 0.0f;
        return true;
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
        if (wantPowerResupply(in, "attack")) return;
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
        // #256 Empress Bulblax roll dodge (pad-only player tactic): while she
        // charges or rolls, hold the whistle and walk to the safe point off
        // her roll line; resume throwing once she is back in a held state.
        if (in.queenDanger) {
            if (!queenDodging) {
                queenDodging = true;
                char buf[200];
                std::snprintf(buf, sizeof(buf), "AUTOPLAY_QUEEN_DODGE start=1 token=%u dodge=(%.0f,%.0f) bot-driven",
                              in.targetToken, in.dodgeX, in.dodgeZ);
                markers.emplace_back(buf);
            }
            lastCommand.buttons = PadB;
            steer(in.naviX, in.naviZ, in.dodgeX, in.dodgeZ);
            return;
        }
        if (queenDodging) {
            queenDodging = false;
            char buf[160];
            std::snprintf(buf, sizeof(buf), "AUTOPLAY_QUEEN_DODGE start=0 token=%u bot-driven", in.targetToken);
            markers.emplace_back(buf);
        }
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
        const bool pressOnly = isPressOnly(in.targetSource);
        // #256: the Empress (5000 HP boss) shares the Titan's long attack window.
        const bool titan = in.targetSource == 73 || in.targetSource == 30;
        const bool kingBoss = in.targetSource == 53;
        const bool roller = cfg.rollerStance && isRollerStance(in.targetSource);
        const float limit = roller ? cfg.rollerAttackTimeout
            : kurage ? cfg.attackTimeout * cfg.kurageAttackMultiplier * (in.targetSource == 72 ? cfg.greaterKurageAttackMultiplier : 1.0f)
            : titan ? cfg.attackTimeout * cfg.titanAttackMultiplier
            : kingBoss ? cfg.attackTimeout * cfg.kingAttackMultiplier
            : pressOnly ? cfg.attackTimeout * cfg.pressOnlyAttackMultiplier : cfg.attackTimeout;
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
        if (in.targetDist > (roller ? cfg.rollerChaseDist : cfg.attackChaseDist)) {
            enter(State::Approach, in);
            return;
        }
        if (roller && rollerOtherTier(in) && !in.targetVulnerable) {
            char buf[200];
            std::snprintf(buf, sizeof(buf), "AUTOPLAY_TIER token=%u dy=%.0f dist=%.0f state=attack bot-driven",
                          in.targetToken, in.targetDy, in.targetDist);
            markers.emplace_back(buf);
            enter(State::Approach, in);
            return;
        }
        if (roller) {
            tickRollerStance(dt, in, limit);
            return;
        }
        if (whistleCooldown > 0.0f) whistleCooldown -= dt;
        // #958: a press-only target (Breadbug 38, Giant 40) is only hurt by thrown
        // Pikmin, and a thrown Pikmin lands idle beside it instead of returning to
        // the party. Once the party is nearly used up while idle strays lie about,
        // whistle them back (the scattered sense stays false because the strays
        // are close to the captain), otherwise A only punches and the fight stalls
        // after about one throw per Pikmin (bot runs r6/r8, arena Giant).
        const bool pressRegroup = pressOnly && in.squadPikmin < cfg.pressRegroupBelow
            && in.strayPikmin >= cfg.pressRegroupStrays;
        if ((in.scattered || in.squadDistress || grabWhistle || pressRegroup) && !whistling && whistleCooldown <= 0.0f) {
            whistling = true;
            whistleTime = 0.0f;
            empressWalk = 0.0f;
            if (in.targetSource == 30) {
                char wbuf[200];
                std::snprintf(wbuf, sizeof(wbuf),
                              "AUTOPLAY_WHISTLE start token=%u strays=%d near=%.0f navi=(%.0f,%.0f) bot-driven",
                              in.targetToken, in.lostPikmin, in.strayNearDist, in.naviX, in.naviZ);
                markers.emplace_back(wbuf);
            }
        }
        if (whistling) {
            whistleTime += dt;
            lastCommand.buttons = PadB; // hold whistle to regroup / free grabs
            // #256 Empress: her flick and roll drop the squad into idle
            // FreeMode strays around the arena (a4/a5: ~50 strays 350-600 u
            // away on both sides of her roll line, so their centroid sits at
            // her body; the whistle reaches 100 u). Walk to the nearest stray
            // while whistling and keep the hold running until it is in reach.
            bool empressRegroup = false;
            if (in.targetSource == 30) {
                if (strayRouteCooldown > 0.0f) strayRouteCooldown -= dt;
                if (in.lostPikmin >= 5 && in.strayNearDist > 90.0f && in.strayNearDist < 1.0e29f
                    && empressWalk < cfg.empressWalkMax) {
                    empressWalk += dt;
                    if (!in.waypointLeg && strayRouteCooldown <= 0.0f) {
                        wantStrayRoute = true;
                        strayRouteX = in.strayNearX;
                        strayRouteZ = in.strayNearZ;
                        strayRouteCooldown = 20.0f;
                    }
                    if (in.waypointLeg) steer(in.naviX, in.naviZ, in.wpX, in.wpZ);
                    else steer(in.naviX, in.naviZ, in.strayNearX, in.strayNearZ);
                    empressRegroup = true;
                }
            }
            // bot-v8 merge (#871): whistle timeout keeps ONE version
            // (undamaged's). Both lanes fixed the same whistle-starves-timeout
            // flaw (undamaged bc5 800 s stalls on 16/30/38/40/42/73/95/96;
            // unkilled control Chappy field=4 scat=1 800 s lock). Kept
            // undamaged's bound + cooldown (forces throw windows) with the
            // kurage-aware limit both lanes used (unkilled limit == wlimit).
            {
                const float wlimit = kurage ? cfg.attackTimeout * cfg.kurageAttackMultiplier * (in.targetSource == 72 ? cfg.greaterKurageAttackMultiplier : 1.0f)
                                   : titan  ? cfg.attackTimeout * cfg.titanAttackMultiplier
                                   : kingBoss ? cfg.attackTimeout * cfg.kingAttackMultiplier
                                   : pressOnly ? cfg.attackTimeout * cfg.pressOnlyAttackMultiplier : cfg.attackTimeout;
                if (stateTime >= wlimit) {
                    giveUp(in, "attack_timeout");
                    finishTarget(in, /*killed*/ false);
                    return;
                }
            }
            if ((whistleTime >= cfg.whistleHold && !empressRegroup)
                || (!in.scattered && !in.squadDistress && !grabWhistle && !pressRegroup)) {
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
        if (in.targetSource == 58 && stateTime < bombsaraiHoldSeconds(cfg.bombsaraiHold)) {
            steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
            return;
        }
        if ((cfg.kingStandoff && isKingStandoff(in.targetSource))
            || (cfg.fuefukiStandoff && isFuefukiStandoff(in.targetSource))) {
            tickKingStandoff(dt, in, limit);
            return;
        }
        // Kurage: body is on the ground (visual float only) so throw at the
        // body position; high HP means a longer window, and throws rotate to
        // spread Pikmin around the bell.
        float aimX = in.aimValid ? in.aimX : in.tgtX, aimZ = in.aimValid ? in.aimZ : in.tgtZ;
        float gap = cfg.throwGap;
        if (pressOnly) {
            // Lead the throw by the target's observed ground velocity.
            if (leadValid && dt > 0.0f) {
                const float vx = (in.tgtX - leadX) / dt, vz = (in.tgtZ - leadZ) / dt;
                leadVX += (vx - leadVX) * 0.2f;
                leadVZ += (vz - leadVZ) * 0.2f;
            }
            leadX = in.tgtX;
            leadZ = in.tgtZ;
            leadValid = true;
            aimX += leadVX * cfg.pressLeadSeconds;
            aimZ += leadVZ * cfg.pressLeadSeconds;
        }
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
        if (rangedAttack && in.targetDist <= cfg.rangedAttackDist + 60.0f) {
            // #901: the captain cannot close in: stand, slide the cursor onto
            // the target and throw over whatever is between.
            kingLookAndThrow(in);
        } else {
            // Keep the stick toward the target so the cursor aims at it, and
            // pulse A to throw. Flyers are thrown at from range as the game allows.
            steer(in.naviX, in.naviZ, aimX, aimZ);
            pulseA(in, cfg.throwHold, gap);
        }
        if (stateTime >= limit) {
            giveUp(in, "attack_timeout");
            finishTarget(in, /*killed*/ false);
        }
    }

    // #901: a dropped ship part is a heavy carry the squad is seeded onto a
    // few Pikmin at a time, so it gets more bounded re-seed cycles.
    int rethrowMax(const Senses& in) const
    {
        return in.trackingPart ? cfg.aftermathRethrowMax * 4 : cfg.aftermathRethrowMax;
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
        if (in.trackingPart && noPartCarry()) {
            // #901 TEST-ONLY: hold the whistle a few seconds so every Pikmin
            // near the part rejoins the party, then stop engaging; the part
            // stays where it dropped.
            if (amPhaseTime < 4.0f) {
                lastCommand.buttons = PadB;
                return;
            }
            char buf[160];
            std::snprintf(buf, sizeof(buf), "AUTOPLAY_PART_LEFT token=%u seconds=%.0f bot-driven", in.targetToken,
                          stateTime);
            markers.emplace_back(buf);
            finishTarget(in, /*killed*/ sawKill);
            return;
        }
        if ((!in.targetAlive || in.targetDead) && !sawDamage && !sawKill && !sawCarry && !sawReceipt) {
            // Target gone with no combat observed: nothing to wait for.
            finishTarget(in, /*claimedKill*/ false);
            return;
        }
        if (sawKill && !sawReceipt && (cfg.noDeliver || noDeliverEnabled())) {
            // #898 TEST-ONLY: abandon the corpse (whistle the squad off it).
            if (stateTime < cfg.noDeliverWhistle) {
                lastCommand.buttons = PadB;
                return;
            }
            char buf[160];
            std::snprintf(buf, sizeof(buf), "AUTOPLAY_NO_DELIVER token=%u corpse_left=1 bot-driven", in.targetToken);
            markers.emplace_back(buf);
            finishTarget(in, /*killed*/ true);
            return;
        }
        // bot-v5: NEVER whistle here (no PadB). Holding whistle gathers
        // Pikmin at the navi 36-65 u from the corpse so no carry ever
        // initiates (v4b diagnosis). Deliver with stick + throws only.
        const bool carryActive = in.transportSeen || in.carryCount > 0 || in.pelletCarriers > 0;
        // #245 owner-death Panic reclaim (Fuefuki only; see Config). The one
        // exception to "never whistle here": a short, bounded whistle while a
        // panicking follower of the dead beetle is in range, so the squad it
        // stole can crew the carry. Carry sensing and seeding resume after.
        if (amPanicCooldown > 0.0f) amPanicCooldown -= dt;
        if (cfg.panicReclaim && isFuefukiStandoff(in.targetSource) && !sawReceipt) {
            if (!amPanicWhistle && in.panicCount > 0 && in.panicNearest <= cfg.panicReclaimRadius
                && amPanicWhistles < cfg.panicReclaimMax && amPanicCooldown <= 0.0f) {
                amPanicWhistle = true;
                amPanicTime = 0.0f;
                ++amPanicWhistles;
                char buf[256];
                std::snprintf(buf, sizeof(buf),
                              "AUTOPLAY_PANIC_RECLAIM token=%u panic=%d nearest=%.0f whistle=%d/%d bot-driven",
                              in.targetToken, in.panicCount, in.panicNearest, amPanicWhistles, cfg.panicReclaimMax);
                markers.emplace_back(buf);
            }
            if (amPanicWhistle) {
                amPanicTime += dt;
                lastCommand.buttons = PadB;
                if (amPanicTime >= cfg.whistleHold) {
                    amPanicWhistle = false;
                    amPanicCooldown = cfg.whistleCooldown;
                }
                return;
            }
        }
        // #246 exception to the no-whistle rule (see titanAftermathWhistles):
        // Titan only, strays on the field, bounded episodes. It fires when the
        // squad is empty, or when squad plus crew cannot reach the corpse's
        // carry minimum while idle strays could (a8/a9: 7 in the squad, 40
        // idle strays scattered by the fight, crew stuck at 1 of 10). The
        // captain first walks to the strays' centroid (at most
        // titanRegroupWalk seconds), then holds the whistle there.
        const int amCrew = in.pelletCarriers > 0 ? in.pelletCarriers : in.carryCount;
        const bool amShort = in.squadPikmin == 0
            || (in.carryWant > 0 && in.squadPikmin + amCrew < in.carryWant && in.strayPikmin > 0)
            || (in.targetSource == 30 && in.lostPikmin >= 10 && in.nearPikmin < 20);
        // #256: the Empress joins the Titan's regroup (her flick and roll leave
        // ~50 idle strays, a11: 12 carriers of 20), walking to the NEAREST stray
        // over the waypoint graph because the strays ring the arena.
        const bool amEmpress = in.targetSource == 30;
        if ((in.targetSource == 73 || amEmpress)
            && (amWhistleTime > 0.0f || amRegroupWalk > 0.0f
                || (amShort && in.fieldPikmin > in.pelletCarriers
                    && amWhistles < cfg.titanAftermathWhistles))) {
            if (amWhistleTime <= 0.0f && (amEmpress ? in.lostPikmin : in.strayPikmin) > 0
                && amRegroupWalk < (amEmpress ? cfg.empressWalkMax : cfg.titanRegroupWalk)) {
                const bool nearest = amEmpress && in.strayNearDist < 1.0e29f;
                const float gx = nearest ? in.strayNearX : in.strayX;
                const float gz = nearest ? in.strayNearZ : in.strayZ;
                const float sx = gx - in.naviX, sz = gz - in.naviZ;
                if (sx * sx + sz * sz > (amEmpress ? 90.0f * 90.0f : 60.0f * 60.0f)) {
                    amRegroupWalk += dt;
                    if (amEmpress) {
                        if (strayRouteCooldown > 0.0f) strayRouteCooldown -= dt;
                        if (!in.waypointLeg && strayRouteCooldown <= 0.0f) {
                            wantStrayRoute = true;
                            strayRouteX = gx;
                            strayRouteZ = gz;
                            strayRouteCooldown = 20.0f;
                        }
                    }
                    if (amEmpress && in.waypointLeg) steer(in.naviX, in.naviZ, in.wpX, in.wpZ);
                    else steer(in.naviX, in.naviZ, gx, gz);
                    return;
                }
            }
            if (amWhistleTime <= 0.0f) ++amWhistles;
            amWhistleTime += dt;
            lastCommand.buttons = PadB;
            if (amWhistleTime >= cfg.titanAftermathWhistleHold) {
                amWhistleTime = 0.0f;
                amRegroupWalk = 0.0f;
            }
            return;
        }
        if (in.trackingPart) pgSawPart = true;
        if (pgSawPart && in.partGone) {
            // #901: the tracked ship part left the field (sucked into the
            // ship: UfoItem::finishSuck -> pc_bbft_check). The CHECK line in
            // the log is the evidence; the bot just scores and moves on.
            char buf[160];
            std::snprintf(buf, sizeof(buf), "AUTOPLAY_PART_GONE token=%u seconds=%.0f bot-driven",
                          in.targetToken, stateTime);
            markers.emplace_back(buf);
            finishTarget(in, /*killed*/ false);
            return;
        }
        if (in.trackingPart && tickPartGather(dt, in)) {
            // #901: a short ship-part crew is gathered by whistle + swarm, not
            // by the corpse throw/re-seed cycle (throws overshoot a big part:
            // r4 crew 12/20 after three re-seeds). Same window as a corpse.
            const float waitBase = ((sawKill || sawDamage) ? cfg.receiptTimeout : cfg.aftermathTimeout)
            * (in.targetSource == 30 ? 2.0f : 1.0f); // #256: regroup walk + route + carry
            if (stateTime >= waitBase * 2.0f) {
                giveUpAftermath(in, "part_short_crew");
                finishTarget(in, /*killed*/ false);
            }
            return;
        }
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
                    if (amRethrows >= rethrowMax(in)) {
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
                    if (amRethrows >= rethrowMax(in)) {
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
                    if (amRethrows >= rethrowMax(in)) {
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
                if (amRethrows >= rethrowMax(in)) {
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
                    if (amRethrows >= rethrowMax(in)) {
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
        const float waitBase = ((sawKill || sawDamage) ? cfg.receiptTimeout : cfg.aftermathTimeout)
            * (in.targetSource == 30 ? 2.0f : 1.0f); // #256: regroup walk + route + carry
        // bot-v5: extend ONLY while carriers > 0 AND the corpse is moving
        // (live, not latched). A latched-but-stalled lift times out bounded.
        const float wait = (carryActive && in.corpseMoving) ? cfg.receiptTimeout * 2.0f : waitBase;
        if (stateTime >= wait) {
            giveUpAftermath(in, aftermathGiveupReason(in));
            // bot-deliver (#871): killed from sawKill, not claimed (55 fix).
            finishTarget(in, /*killed*/ false);
        }
    }

    // #901 part gather (TEST-ONLY bot). Returns false once the crew meets the
    // part's declared minimum, so the normal escort follows the haul to the
    // ship. Pad-only: stick + B (gather whistle) + C-stick (swarm).
    bool tickPartGather(float dt, const Senses& in)
    {
        const int crew = in.pelletCarriers > 0 ? in.pelletCarriers : in.carryCount;
        if (in.carryWant > 0 && crew >= in.carryWant) {
            pgWhistle = 0.0f;
            return false;
        }
        if (pgCooldown > 0.0f) pgCooldown -= dt;
        if (crew > pgCrewBest) {
            pgCrewBest = crew;
            pgStall = 0.0f;
        } else {
            pgStall += dt;
        }
        const int need = in.carryWant > 0 ? in.carryWant - crew : 10;
        const float fdx = in.freeX - in.tgtX, fdz = in.freeZ - in.tgtZ;
        const bool freeFar = fdx * fdx + fdz * fdz > cfg.partFreeFar * cfg.partFreeFar;
        pgLogTime -= dt;
        if (pgLogTime <= 0.0f) {
            pgLogTime = 5.0f;
            char buf[200];
            std::snprintf(buf, sizeof(buf),
                          "AUTOPLAY_PART_GATHER crew=%d want=%d party=%d free=%d free_far=%d tdist=%.0f bot-driven",
                          crew, in.carryWant, in.partyCount, in.freeCount, freeFar ? 1 : 0, in.targetDist);
            markers.emplace_back(buf);
        }
        if (pgWhistle <= 0.0f && pgCooldown <= 0.0f && in.partyCount < need && in.freeCount >= 3
            && (freeFar || crew * 2 < in.carryWant || in.carryWant <= 0)) {
            // Idle Pikmin are not in the party: call them. Whistling over the
            // part also calls its crew, so that happens only while the crew is
            // under half the minimum (they rejoin the swarm right away).
            pgWhistle = cfg.whistleHold;
            pgCooldown = cfg.partWhistleCooldown + cfg.whistleHold;
        }
        if (pgWhistle > 0.0f) {
            pgWhistle -= dt;
            // Walk the cursor (ahead of the captain) over the idle Pikmin.
            steer(in.naviX, in.naviZ, in.freeX, in.freeZ);
            lastCommand.buttons |= PadB;
            return true;
        }
        // Swarm: hold the ring around the part and push the party into it. A crew
        // that stopped growing (the swarm did not reach the part from the ring)
        // walks the captain in close so the party touches the pellet.
        if (pgStall > 8.0f) {
            if (in.targetDist > 45.0f) steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
        } else if (in.waypointLeg && in.targetDist > cfg.partRingMax) {
            steer(in.naviX, in.naviZ, in.wpX, in.wpZ);
        } else if (in.targetDist > cfg.partRingMax) {
            steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
        } else if (in.targetDist < cfg.partRingMin) {
            steerAway(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
        }
        if (in.targetDist < 2.5f * cfg.partRingMax) {
            const float dx = in.tgtX - in.naviX, dz = in.tgtZ - in.naviZ;
            const float len = std::sqrt(dx * dx + dz * dz);
            if (len > 1.0f) {
                lastCommand.swarmX = dx / len;
                lastCommand.swarmZ = dz / len;
            }
        }
        return true;
    }

    void tickDone(float dt, const Senses& in)
    {
        if (in.containerOpen) {
            enter(State::WithdrawMenu, in);
            return;
        }
        // #898: a matching target that was not listed when Done was entered
        // (a Snagret still underground, a late spawn) re-engages. A token the
        // bot already scored or gave up on never does, so this cannot loop.
        if (in.targetToken != 0 && in.targetAlive && !settledTokens.count(in.targetToken)) {
            enter(State::Select, in);
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
        if (in.targetToken) settledTokens.insert(in.targetToken);
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
        resultReported = true;
        if (result.token) settledTokens.insert(result.token);
        // The combat latches belong to the finished token. Left set, the next
        // Select saw "token switch with latched combat scores" against a second
        // live target of the same species and re-emitted this RESULT every
        // tick (#897 Groink 78 re-run: 3,700 duplicate RESULT lines).
        sawDamage = false;
        sawKill = false;
        sawReceipt = false;
        // The driver advances to the next target (or Done when none remain).
        enter(State::Select, in);
    }

    bool rollerOtherTier(const Senses& in) const
    {
        return cfg.rollerStance && isRollerStance(in.targetSource) && in.targetDyValid
            && std::fabs(in.targetDy) > cfg.rollerTierDy;
    }

    // #897 push obstacle (Approach only). Returns true while it owns the pad.
    bool tickObstaclePush(float dt, const Senses& in)
    {
        const bool want = in.pushValid && pushTime < cfg.obstaclePushMax;
        if (!want) {
            if (pushing) {
                pushing = false;
                char buf[200];
                std::snprintf(buf, sizeof(buf), "AUTOPLAY_OBSTACLE phase=%s push_s=%.0f field=%d bot-driven",
                              in.pushValid ? "budget" : "cleared", pushTime, in.fieldPikmin);
                markers.emplace_back(buf);
                stuckWindowDist = 1.0e30f; // fresh progress window after the push
                approachReplans = 0;
            }
            if (pushedThisStint && in.scattered) {
                // Pushers stay at the box: short whistle pulses on the way.
                regroupClock += dt;
                if (std::fmod(regroupClock, cfg.obstacleRegroupEvery) < 1.0f) {
                    if (in.waypointLeg) steer(in.naviX, in.naviZ, in.wpX, in.wpZ);
                    else steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
                    lastCommand.buttons = PadB;
                    return true;
                }
            }
            return false;
        }
        if (!pushing) {
            pushing = true;
            pushedThisStint = true;
            char buf[200];
            std::snprintf(buf, sizeof(buf),
                          "AUTOPLAY_OBSTACLE phase=push at=(%.0f,%.0f) aim=(%.0f,%.0f) dist=%.0f field=%d bot-driven",
                          in.pushX, in.pushZ, in.pushAimX, in.pushAimZ, in.pushDist,
                          in.fieldPikmin);
            markers.emplace_back(buf);
        }
        pushTime += dt;
        stuckWindowStart = 0.0f; // pushing is progress, not a stuck window
        steer(in.naviX, in.naviZ, in.pushX, in.pushZ);
        if (in.pushDist <= cfg.obstaclePushDist) {
            // In range: look-band stick (the captain stops and faces the
            // cursor, which slides along the stick) moving the cursor onto the
            // near-face aim point; throw once it is there.
            lastCommand.moveX = 0.0f;
            lastCommand.moveZ = 0.0f;
            float cx = in.cursorX, cz = in.cursorZ;
            if (!in.cursorValid) {
                cx = in.pushAimX;
                cz = in.pushAimZ;
            }
            const float ex = in.pushAimX - cx, ez = in.pushAimZ - cz;
            const float el = std::sqrt(ex * ex + ez * ez);
            if (el > cfg.kingCursorTol) {
                lastCommand.moveX = ex / el;
                lastCommand.moveZ = ez / el;
                lastCommand.stickScale = cfg.lookStickScale;
            }
            if (el <= cfg.kingCursorTol * 2.0f) pulseA(in, cfg.throwHold, cfg.obstaclePushGap);
        }
        return true;
    }

    // #897 power-mode resupply trigger (Approach/Attack). Returns true when
    // it switched state.
    bool wantPowerResupply(const Senses& in, const char* from)
    {
        if (!isPowerEnabled() || cfg.powerResupplyField <= 0 || !in.hasOnion) return false;
        if (in.fieldPikmin >= cfg.powerResupplyField) return false;
        if (in.onionStored <= 0 && in.powerRestocks >= cfg.powerRestockMax) return false;
        if (in.targetVulnerable) return false; // finish the open Turn window first
        char buf[256];
        std::snprintf(buf, sizeof(buf),
                      "AUTOPLAY_RESUPPLY field=%d stored=%d token=%u state=%s power=1 restocks=%d bot-driven",
                      in.fieldPikmin, in.onionStored, in.targetToken, from, in.powerRestocks);
        markers.emplace_back(buf);
        powerResupplying = true;
        enter(State::WithdrawSeek, in);
        return true;
    }

    // #897 power resupply leg: walk back to the Onion (waypoint aware), stand
    // at it while the driver restocks + exits the squad, whistle the new
    // Pikmin in, then re-select once the field is back to powerWantSquad.
    void tickPowerResupply(float dt, const Senses& in)
    {
        if (!in.hasOnion) {
            powerResupplying = false;
            enter(State::Select, in);
            return;
        }
        const float at = cfg.arriveRadius * 2.0f;
        if (!powerAtOnion && in.onionDist <= at) powerAtOnion = true;
        if (!powerAtOnion) {
            if (in.waypointLeg) steer(in.naviX, in.naviZ, in.wpX, in.wpZ);
            else steer(in.naviX, in.naviZ, in.onionX, in.onionZ);
        } else {
            // Short whistle pulses gather the exiting Pikmin into the party.
            pressPhase += dt;
            if (std::fmod(pressPhase, 2.0f) < 0.6f) lastCommand.buttons = PadB;
        }
        if (powerAtOnion && in.fieldPikmin >= cfg.powerWantSquad) {
            powerResupplying = false;
            enter(State::Select, in);
            return;
        }
        if (powerAtOnion && in.onionStored <= 0 && in.powerRestocks >= cfg.powerRestockMax
            && in.fieldPikmin > 0 && stateTime > 20.0f) {
            powerResupplying = false; // restock budget spent: fight with what is out
            enter(State::Select, in);
            return;
        }
        // Stuck walking back: same replan contract as the normal path.
        if (!powerAtOnion) {
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
        if (stateTime >= cfg.withdrawTimeout * 2.0f) {
            giveUp(in, "resupply_timeout");
            powerResupplying = false;
            enter(State::Select, in);
        }
    }

    // #897 roller stance (see isRollerStance). Modes:
    //   wake   - still in Stay: walk inside fp11 so it drops in;
    //   punish - Turn stickable window open: close in and throw fast;
    //   evade  - ball rolling within rollerEvadeRange: whistle held (squad
    //            tight on the captain) and walk off the roll line, on the
    //            captain's side of it, with a little distance added;
    //   stand  - otherwise: hold [rollerStandMin, rollerStandMax] with no
    //            throws (the body rejects damage), whistle pulses to regroup.
    enum RollerMode { RollerWake = 0, RollerPunish, RollerEvade, RollerStand };
    static const char* rollerModeName(int m)
    {
        switch (m) {
        case RollerWake: return "wake";
        case RollerPunish: return "punish";
        case RollerEvade: return "evade";
        case RollerStand: return "stand";
        }
        return "none";
    }
    void tickRollerStance(float dt, const Senses& in, float limit)
    {
        if (stateTime >= limit) {
            giveUp(in, "attack_timeout");
            finishTarget(in, /*killed*/ false);
            return;
        }
        int mode = RollerStand;
        if (in.targetVulnerable) mode = RollerPunish;
        else if (in.targetRolling && in.targetDist < cfg.rollerEvadeRange) mode = RollerEvade;
        else if (in.targetDormant) mode = RollerWake;
        if (mode != rollerMode) {
            rollerMode = mode;
            char buf[256];
            std::snprintf(buf, sizeof(buf),
                          "AUTOPLAY_ROLLER mode=%s token=%u dist=%.0f field=%d hp=%.3f bot-driven",
                          rollerModeName(mode), in.targetToken, in.targetDist, in.fieldPikmin,
                          in.targetHealthFrac);
            markers.emplace_back(buf);
            rollerWhistleTime = 0.0f;
            punishClock = 0.0f;
            punishThrows = 0;
        }
        switch (mode) {
        case RollerPunish: {
            steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
            const bool wasOn = pressOn;
            if (in.targetDist <= cfg.throwRange) pulseA(in, cfg.rollerThrowHold, cfg.rollerThrowGap);
            if (pressOn && !wasOn) ++punishThrows;
            punishClock += dt;
            if (punishClock >= 1.0f) {
                punishClock = 0.0f;
                char buf[200];
                std::snprintf(buf, sizeof(buf),
                              "AUTOPLAY_ROLLER_PUNISH dist=%.0f field=%d presses=%d hp=%.3f bot-driven",
                              in.targetDist, in.fieldPikmin, punishThrows, in.targetHealthFrac);
                markers.emplace_back(buf);
            }
            return;
        }
        case RollerWake:
            if (in.targetDist > cfg.rollerWakeDist) steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
            return;
        case RollerEvade: {
            float vx = in.targetVelX, vz = in.targetVelZ;
            float vlen = std::sqrt(vx * vx + vz * vz);
            const float ax = in.naviX - in.tgtX, az = in.naviZ - in.tgtZ;
            if (vlen < 1.0f) {
                // No drive velocity yet: assume it rolls straight at us.
                vx = ax;
                vz = az;
                vlen = std::sqrt(vx * vx + vz * vz);
            }
            if (vlen < 1.0f) {
                vx = 1.0f;
                vz = 0.0f;
                vlen = 1.0f;
            }
            vx /= vlen;
            vz /= vlen;
            float px = -vz, pz = vx;
            if (ax * px + az * pz < 0.0f) {
                px = -px;
                pz = -pz;
            }
            // Off the roll line either way works; take the side toward the
            // arena floor (home) when the captain is not already between
            // the ball and that side by a wide margin.
            if (in.homeValid) {
                const float hx = in.homeX - in.naviX, hz = in.homeZ - in.naviZ;
                const float lateral = std::fabs(ax * px + az * pz);
                if (hx * px + hz * pz < 0.0f && lateral < 120.0f) {
                    px = -px;
                    pz = -pz;
                }
            }
            // Ahead of the ball: sideways plus a little away; behind it (it
            // is rolling off): just sideways.
            const float ahead = ax * vx + az * vz;
            const float away = ahead > 0.0f ? 0.35f : 0.0f;
            float mx = px + vx * away, mz = pz + vz * away;
            const float ml = std::sqrt(mx * mx + mz * mz);
            if (ml > 1.0e-3f) {
                mx /= ml;
                mz /= ml;
            }
            lastCommand.moveX = mx;
            lastCommand.moveZ = mz;
            lastCommand.buttons = PadB;
            return;
        }
        default:
            break;
        }
        if (in.targetDist < cfg.rollerStandMin) {
            steerAway(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
            // Back off along the arena floor: blend toward home once the
            // captain is more than rollerHomeLeash from it.
            if (in.homeValid) {
                const float hx = in.homeX - in.naviX, hz = in.homeZ - in.naviZ;
                const float hl = std::sqrt(hx * hx + hz * hz);
                if (hl > cfg.rollerHomeLeash) {
                    float mx = lastCommand.moveX + hx / hl, mz = lastCommand.moveZ + hz / hl;
                    const float ml = std::sqrt(mx * mx + mz * mz);
                    if (ml > 1.0e-3f) {
                        lastCommand.moveX = mx / ml;
                        lastCommand.moveZ = mz / ml;
                    }
                }
            }
        } else if (in.targetDist > cfg.rollerStandMax) {
            steer(in.naviX, in.naviZ, in.tgtX, in.tgtZ);
        }
        rollerWhistleTime += dt;
        if ((in.scattered || in.squadDistress) && std::fmod(rollerWhistleTime, 2.5f) < cfg.whistleHold * 0.5f)
            lastCommand.buttons = PadB;
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
        const bool fue = isFuefukiStandoff(in.targetSource);
        const bool lowHp = !fue && cfg.kingLowHp > 0.0f && in.naviHpValid && in.naviHp <= cfg.kingLowHp;
        const float bandMin = fue ? cfg.fuefukiStandoffMin : lowHp ? cfg.kingEvadeClear : cfg.kingStandoffMin;
        const float bandResume = fue ? cfg.fuefukiStandoffResume
                                 : lowHp ? cfg.kingEvadeClear + 15.0f : cfg.kingStandoffResume;
        const float bandMax = fue ? cfg.fuefukiStandoffMax : lowHp ? cfg.kingEvadeClear + 30.0f : cfg.kingStandoffMax;
        const float bandCloseStop = fue ? cfg.fuefukiStandoffCloseStop
                                    : lowHp ? cfg.kingEvadeClear + 20.0f : cfg.kingStandoffCloseStop;
        const bool attacking = fue ? in.targetAttacking : cfg.kingEvade && in.targetAttacking;
        const float evadeClear = fue ? cfg.fuefukiEvadeClear : cfg.kingEvadeClear;
        if (attacking && !kingEvading) kingEvadeTime = 0.0f;
        kingEvading = attacking;
        int mode;
        if (kingEvading) {
            mode = KingEvade;
            // The band hysteresis restarts after the attack.
            kingBacking = false;
            kingClosing = false;
            kingBackTime = 0.0f;
            if (d < evadeClear) {
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
                          "%s mode=%s token=%u dist=%.0f back_time=%.1f king_attack=%d "
                          "navi_hp=%.0f low_hp=%d bot-driven",
                          fue ? "AUTOPLAY_FUEFUKI_STANDOFF" : "AUTOPLAY_KING_STANDOFF", kingModeName(mode), in.targetToken, d, kingBacking ? kingBackTime : 0.0f,
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
    float aimWhistleLeft = 0.0f; // #898 cursor-aim regroup whistle remaining
    float aimWhistleCooldown = 0.0f; // #898 throw window after a regroup whistle
    int menuTaps = 0;
    float menuHoldTime = 0.0f;
    bool menuConfirmed = false;
    float stuckWindowStart = 0.0f;
    float stuckWindowDist = 1.0e30f;
    bool wantReplan = false;
    float progressBest = 1.0e30f;
    bool trackingLeg = false; // approach stuck window follows a detour leg (#246/#899)
    float trackLegX = 0.0f, trackLegZ = 0.0f;
    int approachReplans = 0; // consecutive STUCK windows in this Approach stint (bot-v3)
    bool approachOnRoute = false; // #901: approach progress metric is the route length
    bool obsWork = false; // #901: working a route obstacle in Approach
    float uiWaitTime = 0.0f; // #901: time the sim has been held by a movie / overlay
    bool rangedAttack = false; // #901: Attack entered from a STUCK approach near the target
    float uiLogTime = 0.0f;
    float obsTime = 0.0f; // #901: time spent on the current obstacle episode
    float obsLogTime = 0.0f;
    int obsGiveups = 0; // #901: obstacle episodes that timed out this Approach stint
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
    int amWhistles = 0;         // #246 Titan aftermath regroup episodes used
    float amWhistleTime = 0.0f; // #246 current regroup whistle hold
    float amRegroupWalk = 0.0f; // #246 time spent walking to the strays this episode
    float pgWhistle = 0.0f; // #901: remaining gather-whistle hold
    float pgCooldown = 0.0f; // #901: time until the next gather whistle may start
    float pgLogTime = 0.0f; // #901: AUTOPLAY_PART_GATHER rate limit
    bool pgSawPart = false; // #901: this aftermath tracked a dropped ship part
    int pgCrewBest = 0; // #901: best crew seen; a crew that stops growing closes the ring
    float pgStall = 0.0f;
    float initialHealthFrac = 1.0f;
    bool sawDamage = false;
    bool sawKill = false; // generic death latched (any species)
    bool sawCarry = false;
    bool sawMove = false; // bot-v5: corpse displacement latched (extension needs live move too)
    bool sawReceipt = false; // Onion receipt latched (authoritative for carried)
    int withdrawCycles = 0; // withdraw-menu repeat count this run
    float throwSpin = 0.0f; // Kurage throw rotation phase
    bool leadValid = false; // #898 press-only lead estimate
    bool resultReported = false; // #898 RESULT emitted for result.token
    std::set<unsigned> settledTokens; // #898 tokens already scored or given up (Done never re-engages them)
    float leadX = 0.0f, leadZ = 0.0f, leadVX = 0.0f, leadVZ = 0.0f;
    bool kingBacking = false; // #884 round 4: King standoff backing off (hysteresis)
    bool kingClosing = false; // #884 round 4: King standoff closing in (hysteresis)
    float kingBackTime = 0.0f; // continuous backing time (sidestep after kingSidestepAfter)
    int kingMode = -1; // last AUTOPLAY_KING_STANDOFF mode (-1 = none this stint)
    bool queenDodging = false; // #256: stepping off the Empress Bulblax roll line
    bool wantStrayRoute = false; // #256: driver should route to strayRouteX/Z
    float strayRouteX = 0.0f;
    float strayRouteZ = 0.0f;
    float strayRouteCooldown = 0.0f;
    float seedRouteCooldown = 0.0f; // #256
    float empressWalk = 0.0f; // seconds walked to strays in this whistle episode
    bool kingEvading = false; // #884 round 5: leaving the tongue sweep for the current King attack
    float kingEvadeTime = 0.0f; // time spent evading inside kingEvadeClear (sidestep after kingEvadeSideAfter)
    bool kingLowHpMode = false; // last stance used the low-health band (marker field)
    int amPanicWhistles = 0; // #245: panic reclaim whistles used this engagement
    bool amPanicWhistle = false; // #245: holding a panic reclaim whistle
    float amPanicTime = 0.0f;
    float amPanicCooldown = 0.0f;
    int rollerMode = -1; // #897 last AUTOPLAY_ROLLER mode (-1 = none this stint)
    float rollerWhistleTime = 0.0f; // #897 stand-mode whistle pulse clock
    float punishClock = 0.0f; // #897 punish diagnostics clock
    int punishThrows = 0; // #897 A presses this punish stint
    bool powerResupplying = false; // #897 power resupply leg in progress (survives enter())
    bool powerAtOnion = false; // #897 reached the Onion on this resupply visit
    float pushTime = 0.0f; // #897 time spent pushing obstacles this approach stint
    bool pushing = false; // #897 obstacle push active
    bool pushedThisStint = false; // #897 pushed a box since the last reset (regroup pulses)
    float regroupClock = 0.0f; // #897 post-push whistle pulse clock
    bool tierReplanAsked = false; // #897 one immediate replan per approach when the target is on another tier
    bool legKnown = false; // #897 approach progress is measured to this detour leg
    float legX = 0.0f;
    float legZ = 0.0f;
    bool announced = false;
    Result result;
    Command lastCommand;
    std::vector<std::string> markers;
};

} // namespace p2autoplay
