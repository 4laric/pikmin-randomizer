// TEST-ONLY autoplay bot policy test (bot-impl wf9, bot-v2/v3/v4 wf10, bot-v5 wf10). Engine-free.
//
// Pins the engine-free Brain in pc_port/pc_p2_autoplay_policy.h:
//   * inert-when-unset: with the PIKMIN_RANDOMIZER_AUTOPLAY gate closed the
//     Brain stays IDLE, emits a neutral pad and records no markers, no
//     matter how adversarial the senses are;
//   * the withdraw -> select -> approach -> attack -> aftermath -> result
//     flow, timeouts with AUTOPLAY_GIVEUP, stuck detection with replan,
//     Kogane damage-and-move-on, kill+carry scoring, and target matching;
//   * bot-v2: Onion receipt wait (carried=1 means a receipt line,
//     received=<0/1>), generic death latch for every species, withdraw-menu
//     repeat until 15-or-empty, Sarai low-or-grabbing throws + whistle,
//     Kurage extended attack with rotating throws, replan on every STUCK.
//   * bot-v3: STUCK lines carry navi=(x,z) (+replan=N in approach);
//     target_unreachable GIVEUP after maxApproachReplans consecutive STUCK
//     windows (count resets on real progress); Done idles near the Onion.
//
//   * bot-v5: aftermath never whistles (release B), walks onto the corpse
//     (contact ring) + throws to seed grabs, backs off, re-throws bounded
//     times; a grabbed-but-stalled lift re-throws to grow the crew; receipt
//     window extends only while carriers>0 AND the corpse moves now;
//     giveups name the broken link; received=1 only from the token's
//     own ledger receipt.
//   * bot-v6: power WithdrawSeek waits pad-neutral (no menu) until field>=80;
//     Select names a dead/absent target (target_gone) and a latched kill for
//     the same token resumes Aftermath instead of dropping to Done.
//   * bot-v7: a grabbed lift below the corpse's declared minimum (carryWant)
//     that is not moving keeps seeding (SeedGrow: onto the corpse + throws,
//     never whistle) instead of escorting a stuck lift; a shrinking crew
//     re-seeds (reason=shrank); proxy campaign actors bind their lane-06
//     delivery source (harness proves the receipt).
//   * #884 round 4: KingChappy (53) attack stance keeps the captain outside
//     the source invisible range (back / side / close / hold with a look-band
//     stick), other families keep the contact steer; a coupled simulation
//     against the engine-free King model (pc_p2_chappy_mouth.h) shows the
//     parked-at-18 standoff (no attack, repeated flicks and tramples) without
//     the stance and an open attack gate with no flick or trample with it.
// Exit 0 only if every check passes; any failure prints FAIL and exits 1.
#include "pc_p2_autoplay_policy.h"
#include "pc_p2_chappy_mouth.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {

int failures = 0;

#define CHECK(cond, name) do { \
    if (cond) { std::printf("PASS %s\n", name); } \
    else { std::printf("FAIL %s\n", name); ++failures; } \
} while (0)

void setEnv(const char* name, const char* value)
{
#ifdef _WIN32
    if (!value) {
        _putenv_s(name, "");
    } else {
        _putenv_s(name, value);
    }
#else
    if (!value) {
        unsetenv(name);
    } else {
        setenv(name, value, 1);
    }
#endif
}

p2autoplay::Senses liveSenses()
{
    p2autoplay::Senses s;
    s.enabled = true;
    s.naviAlive = true;
    s.dt = 0.05f;
    return s;
}

bool hasMarker(const std::vector<std::string>& markers, const char* substr)
{
    for (const std::string& m : markers) {
        if (m.find(substr) != std::string::npos) return true;
    }
    return false;
}

void testGate()
{
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", nullptr);
    CHECK(!p2autoplay::isEnabled(), "gate/unset_is_disabled");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", "");
    CHECK(!p2autoplay::isEnabled(), "gate/empty_is_disabled");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", "0");
    CHECK(!p2autoplay::isEnabled(), "gate/zero_is_disabled");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", "1");
    CHECK(p2autoplay::isEnabled(), "gate/one_is_enabled");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_TARGET", "Sokkuri");
    CHECK(p2autoplay::targetFilter() == "Sokkuri", "gate/target_filter_read");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_TARGET", nullptr);
    CHECK(p2autoplay::targetFilter().empty(), "gate/target_filter_empty");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", nullptr);
}

void testInertWhenUnset()
{
    // Adversarial senses with the gate closed: must stay neutral and silent.
    p2autoplay::Brain brain;
    p2autoplay::Senses s = liveSenses();
    s.enabled = false;
    s.fieldPikmin = 20;
    s.hasOnion = true;
    s.onionDist = 10.0f;
    s.targetToken = 1234;
    s.targetAlive = true;
    s.targetDist = 50.0f;
    s.targetHealthFrac = 0.2f;
    s.transportSeen = true;
    s.scattered = true;
    s.targetDead = true;
    s.receiptSeen = true;
    s.targetGrabbing = true;
    s.targetLow = true;
    for (int i = 0; i < 600; ++i) brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Idle, "inert/stays_idle");
    const p2autoplay::Command cmd = brain.command();
    CHECK(cmd.buttons == 0 && cmd.moveX == 0.0f && cmd.moveZ == 0.0f && !cmd.menuHold,
          "inert/pad_neutral");
    CHECK(brain.takeMarkers().empty(), "inert/no_markers");
    CHECK(!brain.replanWanted(), "inert/no_replan");

    // Opening the gate lets the same senses drive the machine.
    s.enabled = true;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::WithdrawSeek, "inert/gate_opens_to_withdraw");
    CHECK(hasMarker(brain.takeMarkers(), "AUTOPLAY_STATE"), "inert/state_marker_when_open");
}

void testWithdrawFlow()
{
    p2autoplay::Config cfg;
    cfg.wantSquad = 15;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    brain.update(0.05f, s); // idle -> withdraw_seek
    CHECK(brain.current() == p2autoplay::State::WithdrawSeek, "withdraw/enters_seek");

    // Far from the Onion: steers toward it in world space.
    s.hasOnion = true;
    s.naviX = 0.0f;
    s.naviZ = 0.0f;
    s.onionX = 400.0f;
    s.onionZ = 0.0f;
    s.onionDist = 400.0f;
    s.onionStored = 20;
    brain.update(0.05f, s);
    const p2autoplay::Command cmd = brain.command();
    CHECK(cmd.moveX > 0.9f && std::fabs(cmd.moveZ) < 0.01f, "withdraw/steers_to_onion");

    // At the Onion with the UI open: holds the withdraw input.
    s.onionDist = 10.0f;
    s.containerOpen = true;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::WithdrawMenu, "withdraw/enters_menu");
    brain.update(0.05f, s);
    CHECK(brain.command().menuHold, "withdraw/menu_hold");

    // Squad filled: confirms and leaves for target select.
    s.fieldPikmin = 20;
    for (int i = 0; i < 30 && brain.current() == p2autoplay::State::WithdrawMenu; ++i) {
        brain.update(0.05f, s);
    }
    s.containerOpen = false; // UI closed after the A confirm
    for (int i = 0; i < 10 && brain.current() == p2autoplay::State::WithdrawMenu; ++i) {
        brain.update(0.05f, s);
    }
    CHECK(brain.current() == p2autoplay::State::Select, "withdraw/leaves_when_filled");
}

void testWithdrawKeepsClosing()
{
    // Regression for wf9-2 withdraw_timeout: arriving within arriveRadius
    // (90) must not stop the steering -- the real container trigger is
    // ~50, so stopping at 90 stalls forever. Close distance still steers
    // while tapping A, honours waypoint detours, and logs STUCK + replan.
    p2autoplay::Config cfg;
    cfg.wantSquad = 15;
    cfg.stuckWindow = 0.2f;
    cfg.stuckMinProgress = 30.0f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    brain.update(0.05f, s); // idle -> withdraw_seek
    s.hasOnion = true;
    s.naviX = 0.0f;
    s.naviZ = 0.0f;
    s.onionX = 50.0f;
    s.onionZ = 0.0f;
    s.onionDist = 50.0f;
    s.onionStored = 20;
    s.containerOpen = false;
    brain.update(0.05f, s);
    const p2autoplay::Command close = brain.command();
    CHECK(close.moveX > 0.9f, "withdraw-close/keeps_steering_inside_arrive");
    int aOn = 0;
    for (int i = 0; i < 40; ++i) {
        brain.update(0.05f, s);
        if (brain.command().buttons & unsigned(p2autoplay::PadA)) ++aOn;
    }
    CHECK(aOn > 0, "withdraw-close/pulses_A_while_closing");
    CHECK(brain.current() == p2autoplay::State::WithdrawSeek, "withdraw-close/stays_until_open");

    // Waypoint detour overrides the straight line to the Onion.
    s.waypointLeg = true;
    s.wpX = 0.0f;
    s.wpZ = 400.0f;
    brain.update(0.05f, s);
    const p2autoplay::Command det = brain.command();
    CHECK(det.moveZ > 0.9f && std::fabs(det.moveX) < 0.2f, "withdraw-close/waypoint_detour");
    s.waypointLeg = false;

    // No progress: STUCK + replan wanted (driver routes via waypoints).
    std::vector<std::string> markers;
    for (int i = 0; i < 30; ++i) {
        brain.update(0.05f, s);
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(markers, "AUTOPLAY_STUCK state=withdraw_seek"), "withdraw-close/stuck_marker");
    CHECK(brain.replanWanted(), "withdraw-close/replan_wanted");
}

void testWithdrawMenuHoldThenConfirm()
{
    // Regression for wf9-3 withdraw_hold_timeout: field stays 0 while the
    // container UI is open (delta is UI-local until A confirms), so a
    // field-gated hold deadlocks. The menu must hold stick-down for
    // menuHoldDuration, then pulse A to confirm even with field=0.
    p2autoplay::Config cfg;
    cfg.wantSquad = 15;
    cfg.menuHoldDuration = 1.0f;
    cfg.menuConfirmDuration = 1.0f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    brain.update(0.05f, s); // idle -> withdraw_seek
    s.hasOnion = true;
    s.onionDist = 10.0f;
    s.onionStored = 20;
    s.fieldPikmin = 0;
    s.containerOpen = true;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::WithdrawMenu, "withdraw-menu/enters");
    // Hold phase: menuHold, no A yet.
    brain.update(0.05f, s);
    CHECK(brain.command().menuHold, "withdraw-menu/holds_first");
    // After the hold duration: A pulses to confirm despite field=0.
    for (int i = 0; i < 30; ++i) brain.update(0.05f, s);
    int aOn = 0;
    for (int i = 0; i < 40; ++i) {
        brain.update(0.05f, s);
        if (brain.command().buttons & unsigned(p2autoplay::PadA)) ++aOn;
    }
    CHECK(aOn > 0, "withdraw-menu/confirms_after_hold");
    // UI closes after the confirm with field still 0 and the Onion stocked:
    // bot-v2 repeats the withdraw menu (another cycle) instead of leaving
    // empty-handed for target select.
    s.containerOpen = false;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::WithdrawSeek, "withdraw-menu/loops_for_another_cycle");
    CHECK(hasMarker(brain.takeMarkers(), "AUTOPLAY_WITHDRAW cycle=1"), "withdraw-menu/cycle_logged");
}

void testCombatFlow()
{
    p2autoplay::Config cfg;
    cfg.throwHold = 0.1f;
    cfg.throwGap = 0.2f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s); // idle -> withdraw_seek
    brain.update(0.05f, s); // withdraw_seek -> select (squad ready)
    CHECK(brain.current() == p2autoplay::State::Select, "combat/reaches_select");

    // Acquire a Sokkuri target.
    s.targetToken = 5465461;
    s.targetSource = 79;
    s.targetAlive = true;
    s.tgtX = 1000.0f;
    s.tgtZ = 0.0f;
    s.targetDist = 1000.0f;
    s.targetHealthFrac = 1.0f;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Approach, "combat/approach");
    // Still disguised: keeps closing past throw range.
    s.targetRevealed = false;
    s.targetDist = 200.0f;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Approach, "combat/closes_on_disguise");
    s.targetRevealed = true;
    s.targetDist = 100.0f;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Attack, "combat/attacks_in_range");

    // Throw pulses: A toggles over time while closing the aim.
    int aOn = 0;
    for (int i = 0; i < 60; ++i) {
        brain.update(0.05f, s);
        if (brain.command().buttons & unsigned(p2autoplay::PadA)) ++aOn;
    }
    CHECK(aOn > 0 && aOn < 60, "combat/throw_pulses");
    // Aims at the target: move vector points at it.
    const p2autoplay::Command aim = brain.command();
    CHECK(aim.moveX != 0.0f || aim.moveZ != 0.0f, "combat/aims_while_throwing");

    // Scattered squad: whistle regroup takes over throwing.
    s.scattered = true;
    brain.update(0.05f, s);
    CHECK(brain.command().buttons & unsigned(p2autoplay::PadB), "combat/whistle_regroup");
    s.scattered = false;

    // Combat damage observed, then the kill: aftermath watches the corpse.
    s.targetHealthFrac = 0.6f;
    brain.update(0.05f, s);
    s.targetAlive = false;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Aftermath, "combat/aftermath_after_kill");
    s.transportSeen = true;
    s.receiptSeen = true; // Onion receipt lands while the corpse is carried
    std::vector<std::string> markers;
    for (int i = 0; i < 200 && brain.current() == p2autoplay::State::Aftermath; ++i) {
        brain.update(0.05f, s);
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(markers, "AUTOPLAY_RESULT target=5465461 damaged=1 killed=1 carried=1"),
          "combat/result_kill_carry");
    CHECK(hasMarker(markers, "received=1"), "combat/result_received");
    CHECK(hasMarker(markers, "bot-driven"), "combat/result_labelled_bot_driven");
}

void testKoganeMovesOn()
{
    p2autoplay::Config cfg;
    cfg.koganeConfirm = 1.0f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 983680291;
    s.targetSource = 9;
    s.targetAlive = true;
    s.targetDist = 100.0f;
    s.targetHealthFrac = 1.0f; // Kogane never loses health
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    CHECK(brain.current() == p2autoplay::State::Attack, "kogane/attacks");
    // A flip (family-observed combat) then the confirm window: moves on with
    // damage counted and no kill/carry claim.
    s.targetDamagedLatch = true;
    std::vector<std::string> markers;
    for (int i = 0; i < 200 && brain.current() != p2autoplay::State::Select; ++i) {
        brain.update(0.05f, s);
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(markers, "AUTOPLAY_RESULT target=983680291 damaged=1 killed=0 carried=0"),
          "kogane/result_damage_no_kill");
}

void testTimeoutsAndStuck()
{
    p2autoplay::Config cfg;
    cfg.approachTimeout = 1.0f;
    cfg.stuckWindow = 0.2f;
    cfg.stuckMinProgress = 30.0f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 111;
    s.targetSource = 23; // Sarai flyer
    s.targetAlive = true;
    s.targetDist = 2000.0f;
    s.tgtX = 2000.0f;
    s.tgtZ = 0.0f;
    brain.update(0.05f, s); // -> approach
    std::vector<std::string> markers;
    for (int i = 0; i < 100; ++i) {
        brain.update(0.05f, s); // no progress: stuck then timeout
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(markers, "AUTOPLAY_STUCK"), "stuck/marker_logged");
    CHECK(hasMarker(markers, "AUTOPLAY_GIVEUP reason=approach_timeout"), "timeout/giveup_logged");
    CHECK(hasMarker(markers, "AUTOPLAY_RESULT target=111 damaged=0 killed=0 carried=0"),
          "timeout/result_no_claims");
}

void testTargetMatching()
{
    CHECK(p2autoplay::matchTarget(5465461, 79, "Sokkuri", ""), "match/empty_filter");
    CHECK(p2autoplay::matchTarget(5465461, 79, "Sokkuri", "5465461"), "match/generator_key");
    CHECK(p2autoplay::matchTarget(5465461, 79, "Sokkuri", "79"), "match/source_id");
    CHECK(p2autoplay::matchTarget(5465461, 79, "Sokkuri", "Sokkuri"), "match/species_name");
    CHECK(p2autoplay::matchTarget(5465461, 79, "Sokkuri", "sokkuri"), "match/name_case");
    CHECK(!p2autoplay::matchTarget(5465461, 79, "Sokkuri", "Sarai"), "match/wrong_species");
    CHECK(p2autoplay::matchTarget(2175753366u, 23, "Sarai", "23"), "match/sarai_source");
    CHECK(p2autoplay::matchTarget(983680291, 9, "Kogane", "Kogane"), "match/kogane_name");
    CHECK(p2autoplay::matchTarget(1787125272, 57, "Kurage", "1787125272"), "match/kurage_key");
    CHECK(p2autoplay::sourceForSpeciesName("Sokkuri") == 79, "match/sokkuri_id");
    CHECK(p2autoplay::sourceForSpeciesName("Kogane") == 9, "match/kogane_id");
    CHECK(p2autoplay::sourceForSpeciesName("Sarai") == 23, "match/sarai_id");
    CHECK(p2autoplay::sourceForSpeciesName("Kurage") == 57, "match/kurage_id");
}

void testReceiptWait()
{
    // bot-v2 gap 1: Aftermath waits for the Onion receipt marker or a
    // timeout. carried=1 must mean a receipt line; received=<0/1> is scored.
    p2autoplay::Config cfg;
    cfg.receiptTimeout = 1.0f;
    cfg.aftermathTimeout = 60.0f;
    cfg.whistleHold = 0.2f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 777001;
    s.targetSource = 79;
    s.targetAlive = true;
    s.targetDist = 100.0f;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    // Kill without a receipt yet: stays in Aftermath, no RESULT.
    s.targetHealthFrac = 0.5f;
    brain.update(0.05f, s);
    s.targetAlive = false;
    s.transportSeen = true;
    s.receiptSeen = false;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Aftermath, "receipt/waits_after_kill");
    for (int i = 0; i < 6; ++i) brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Aftermath, "receipt/keeps_waiting_without_receipt");
    CHECK(!hasMarker(brain.takeMarkers(), "AUTOPLAY_RESULT"), "receipt/no_early_result");
    // Timeout with no receipt: kill claimed, carry/receipt refused. The lift
    // was seen (transport) but the corpse never moved: bot-v5 names the stall
    // (carry_stalled) instead of the generic receipt_timeout.
    std::vector<std::string> markers;
    for (int i = 0; i < 60 && brain.current() == p2autoplay::State::Aftermath; ++i) {
        brain.update(0.05f, s);
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(markers, "AUTOPLAY_GIVEUP reason=carry_stalled"), "receipt/stall_logged");
    CHECK(hasMarker(markers, "AUTOPLAY_RESULT target=777001 damaged=1 killed=1 carried=0"),
          "receipt/timeout_no_carry_claim");
    CHECK(hasMarker(markers, "received=0"), "receipt/timeout_received_zero");

    // Second kill where the receipt lands mid-wait: prompt carried=1.
    p2autoplay::Brain brain2(cfg);
    brain2.update(0.05f, s); // idle -> withdraw_seek (field=20 still set)
    p2autoplay::Senses s2 = s;
    s2.targetAlive = true;
    s2.targetHealthFrac = 1.0f;
    s2.transportSeen = false;
    s2.receiptSeen = false;
    brain2.update(0.05f, s2); // -> select
    brain2.update(0.05f, s2); // -> approach
    brain2.update(0.05f, s2); // -> attack
    s2.targetHealthFrac = 0.4f;
    brain2.update(0.05f, s2);
    s2.targetAlive = false;
    s2.transportSeen = true;
    brain2.update(0.05f, s2);
    CHECK(brain2.current() == p2autoplay::State::Aftermath, "receipt/waits_second_kill");
    for (int i = 0; i < 4; ++i) brain2.update(0.05f, s2); // whistle window
    s2.receiptSeen = true;
    markers.clear();
    for (int i = 0; i < 40 && brain2.current() == p2autoplay::State::Aftermath; ++i) {
        brain2.update(0.05f, s2);
        const std::vector<std::string> got = brain2.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(markers, "AUTOPLAY_RESULT target=777001 damaged=1 killed=1 carried=1"),
          "receipt/receipt_scores_carry");
    CHECK(hasMarker(markers, "received=1"), "receipt/receipt_scores_received");
}

void testGenericDeath()
{
    // bot-v2 gap 5: Otakara-style kill with no health-frac drop and no
    // per-module marker still claims damaged+killed via the generic latch.
    p2autoplay::Config cfg;
    cfg.receiptTimeout = 60.0f;
    cfg.whistleHold = 0.2f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 3921089765u;
    s.targetSource = 59; // FireOtakara
    s.targetAlive = true;
    s.targetDist = 100.0f;
    s.targetHealthFrac = 1.0f; // no P2_OTAKARA_DAMAGE line, no frac drop
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    CHECK(brain.current() == p2autoplay::State::Attack, "generic-death/attacks");
    // Host death seam (mDeadState): generic latch, health frac untouched.
    s.targetDead = true;
    s.targetAlive = false;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Aftermath, "generic-death/aftermath");
    s.transportSeen = true;
    s.receiptSeen = true;
    std::vector<std::string> markers;
    for (int i = 0; i < 60 && brain.current() == p2autoplay::State::Aftermath; ++i) {
        brain.update(0.05f, s);
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(markers, "AUTOPLAY_RESULT target=3921089765 damaged=1 killed=1 carried=1"),
          "generic-death/result_claims_kill");
}

void testWithdrawRepeat()
{
    // bot-v2 gap 4: a 5-Pikmin first cycle loops back for another cycle
    // while the Onion still stocks; a full squad leaves for select.
    p2autoplay::Config cfg;
    cfg.wantSquad = 15;
    cfg.menuHoldDuration = 0.5f;
    cfg.menuConfirmDuration = 0.5f;
    cfg.maxWithdrawCycles = 5;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    brain.update(0.05f, s); // idle -> withdraw_seek
    s.hasOnion = true;
    s.onionDist = 10.0f;
    s.onionStored = 20;
    s.fieldPikmin = 0;
    s.containerOpen = true;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::WithdrawMenu, "withdraw-repeat/enters");
    for (int i = 0; i < 40 && brain.current() == p2autoplay::State::WithdrawMenu; ++i) {
        brain.update(0.05f, s);
        if (brain.takeMarkers().empty()) continue;
    }
    // First cycle lands only 5 Pikmin: loops back to seek, logs the cycle.
    s.containerOpen = false;
    s.fieldPikmin = 5;
    s.onionStored = 15;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::WithdrawSeek, "withdraw-repeat/loops_back_when_short");
    CHECK(hasMarker(brain.takeMarkers(), "AUTOPLAY_WITHDRAW cycle=1"), "withdraw-repeat/cycle_logged");
    // Second cycle: back at the Onion, UI reopens, fills to 15, leaves.
    s.onionDist = 10.0f;
    brain.update(0.05f, s);
    s.containerOpen = true;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::WithdrawMenu, "withdraw-repeat/reenters");
    for (int i = 0; i < 40; ++i) brain.update(0.05f, s);
    s.containerOpen = false;
    s.fieldPikmin = 15;
    s.onionStored = 5;
    for (int i = 0; i < 10 && brain.current() == p2autoplay::State::WithdrawMenu; ++i) {
        brain.update(0.05f, s);
    }
    CHECK(brain.current() == p2autoplay::State::Select, "withdraw-repeat/leaves_when_full");
    // Empty Onion with a short squad still leaves (nothing left to take).
    p2autoplay::Brain brain2(cfg);
    brain2.update(0.05f, s);
    p2autoplay::Senses s2 = liveSenses();
    s2.hasOnion = true;
    s2.onionDist = 10.0f;
    s2.onionStored = 0;
    s2.fieldPikmin = 5;
    brain2.update(0.05f, s2);
    CHECK(brain2.current() == p2autoplay::State::Select, "withdraw-repeat/leaves_when_empty");
}

void testSaraiFlyer()
{
    // bot-v2 gap 3 (Sarai 23): high + holding nothing -> follow, no throws;
    // grabbing -> whistle; low -> throws.
    p2autoplay::Config cfg;
    cfg.throwHold = 0.1f;
    cfg.throwGap = 0.2f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 2175753366u;
    s.targetSource = 23;
    s.targetAlive = true;
    s.naviX = 0.0f;
    s.naviZ = 0.0f;
    s.tgtX = 200.0f;
    s.tgtZ = 0.0f;
    s.targetDist = 200.0f;
    s.targetLow = false;
    s.targetGrabbing = false;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack (flyer range)
    CHECK(brain.current() == p2autoplay::State::Attack, "sarai/attacks_in_range");
    int aOn = 0;
    for (int i = 0; i < 30; ++i) {
        brain.update(0.05f, s);
        if (brain.command().buttons & unsigned(p2autoplay::PadA)) ++aOn;
    }
    CHECK(aOn == 0, "sarai/holds_throws_while_high");
    CHECK(brain.command().moveX > 0.5f, "sarai/stays_near_while_high");
    // Grab: whistle takes over.
    s.targetGrabbing = true;
    brain.update(0.05f, s);
    CHECK(brain.command().buttons & unsigned(p2autoplay::PadB), "sarai/whistle_frees_grab");
    s.targetGrabbing = false;
    s.targetLow = true; // swooped low: throws resume
    aOn = 0;
    for (int i = 0; i < 40; ++i) {
        brain.update(0.05f, s);
        if (brain.command().buttons & unsigned(p2autoplay::PadA)) ++aOn;
    }
    CHECK(aOn > 0, "sarai/throws_when_low");
}

void testKurageLongAttack()
{
    // bot-v2 gap 3 (Kurage 57): high HP -> attack window is multiplied, and
    // throws rotate (aim varies) instead of a fixed pulse.
    p2autoplay::Config cfg;
    cfg.attackTimeout = 1.0f;
    cfg.kurageAttackMultiplier = 3.0f;
    cfg.throwHold = 0.1f;
    cfg.throwGap = 0.2f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 1787125272u;
    s.targetSource = 57;
    s.targetAlive = true;
    s.targetDist = 100.0f;
    s.naviX = 0.0f;
    s.naviZ = 0.0f;
    s.tgtX = 100.0f;
    s.tgtZ = 0.0f;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    for (int i = 0; i < 30; ++i) brain.update(0.05f, s); // 1.5s > base 1.0s
    CHECK(brain.current() == p2autoplay::State::Attack, "kurage/outlasts_base_timeout");
    int aOn = 0;
    float firstZ = 0.0f, lastZ = 0.0f;
    for (int i = 0; i < 20; ++i) { // total 2.5s < 3.0s extended window
        brain.update(0.05f, s);
        const p2autoplay::Command cmd = brain.command();
        if (cmd.buttons & unsigned(p2autoplay::PadA)) ++aOn;
        if (i == 0) firstZ = cmd.moveZ;
        lastZ = cmd.moveZ;
    }
    CHECK(aOn > 0, "kurage/keeps_throwing");
    CHECK(firstZ != lastZ, "kurage/rotates_throws");
    // Control: a non-Kurage target times out at the base window (the Brain
    // re-engages the same live target afterwards, so pin the timeout markers
    // rather than the transient Select state).
    p2autoplay::Brain plain(cfg);
    plain.update(0.05f, s);
    plain.update(0.05f, s);
    p2autoplay::Senses s2 = s;
    s2.targetToken = 999001;
    s2.targetSource = 44;
    plain.update(0.05f, s2);
    plain.update(0.05f, s2);
    std::vector<std::string> plainMarkers;
    for (int i = 0; i < 40; ++i) {
        plain.update(0.05f, s2);
        const std::vector<std::string> got = plain.takeMarkers();
        plainMarkers.insert(plainMarkers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(plainMarkers, "AUTOPLAY_GIVEUP reason=attack_timeout"),
          "kurage/control_times_out_at_base");
    CHECK(hasMarker(plainMarkers, "AUTOPLAY_RESULT target=999001 damaged=0 killed=0 carried=0"),
          "kurage/control_no_claims");
}

void testKoganePathNeedsEngagement()
{
    // wf10-v2-1 Otakara lesson: a mid-fight source switch onto Kogane must
    // not score the stale (non-Kogane) engagement down the damage-and-move-on
    // path. The Kogane path needs BOTH the engagement-time flag and live senses.
    p2autoplay::Config cfg;
    cfg.koganeConfirm = 0.5f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 3921089765u;
    s.targetSource = 59; // engaged as FireOtakara (not Kogane-like)
    s.targetAlive = true;
    s.targetDist = 100.0f;
    s.targetHealthFrac = 0.8f; // damage observed
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    CHECK(brain.current() == p2autoplay::State::Attack, "kogane-guard/attacks");
    // Mid-fight source switch to Kogane with damage: must NOT move on.
    s.targetSource = 9;
    s.targetDamagedLatch = true;
    for (int i = 0; i < 30; ++i) brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Attack, "kogane-guard/no_move_on_for_stale_token");
    CHECK(!hasMarker(brain.takeMarkers(), "AUTOPLAY_RESULT"), "kogane-guard/no_stale_result");
}

void testReplanRepeats()
{    // bot-v2 gap 2: every STUCK window replans (far targets get repeated
    // graph replans, not just one detour).
    p2autoplay::Config cfg;
    cfg.approachTimeout = 30.0f;
    cfg.stuckWindow = 0.2f;
    cfg.stuckMinProgress = 30.0f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 3886812794u;
    s.targetSource = 9;
    s.targetAlive = true;
    s.targetDist = 1290.0f;
    s.tgtX = 1290.0f;
    s.tgtZ = 0.0f;
    brain.update(0.05f, s); // -> approach
    int stuck = 0, replans = 0;
    for (int i = 0; i < 12; ++i) {
        brain.update(0.05f, s);
        for (const std::string& m : brain.takeMarkers()) {
            if (m.find("AUTOPLAY_STUCK") != std::string::npos) ++stuck;
        }
        if (brain.replanWanted()) {
            ++replans;
            brain.clearReplan(); // driver replans
        }
    }
    CHECK(stuck >= 2, "replan/repeats_on_stuck");
    CHECK(replans >= 2, "replan/replan_every_window");
}

void testStuckCarriesNaviPos()
{
    // bot-v3: STUCK lines prove whether the captain moves under stick input.
    p2autoplay::Config cfg;
    cfg.approachTimeout = 30.0f;
    cfg.stuckWindow = 0.2f;
    cfg.stuckMinProgress = 30.0f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 424242u;
    s.targetSource = 44;
    s.targetAlive = true;
    s.targetDist = 1000.0f;
    s.naviX = -200.0f;
    s.naviZ = 70.0f;
    s.tgtX = 800.0f;
    s.tgtZ = 0.0f;
    brain.update(0.05f, s); // -> approach
    std::vector<std::string> markers;
    for (int i = 0; i < 12; ++i) {
        brain.update(0.05f, s);
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
        if (brain.replanWanted()) brain.clearReplan();
    }
    CHECK(hasMarker(markers, "AUTOPLAY_STUCK state=approach"), "stuckpos/approach_marker");
    CHECK(hasMarker(markers, "navi=(-200,70)"), "stuckpos/approach_navi_pos");
    CHECK(hasMarker(markers, "replan="), "stuckpos/approach_replan_count");
}

void testUnreachableGiveup()
{
    // bot-v3: N consecutive no-progress STUCK windows in one Approach stint
    // is GIVEUP reason=target_unreachable (then RESULT, no kill claims).
    // Progress resets the count.
    p2autoplay::Config cfg;
    cfg.approachTimeout = 60.0f;
    cfg.stuckWindow = 0.2f;
    cfg.stuckMinProgress = 30.0f;
    cfg.maxApproachReplans = 3;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 515001u;
    s.targetSource = 44;
    s.targetAlive = true;
    s.targetDist = 1000.0f;
    s.tgtX = 1000.0f;
    s.tgtZ = 0.0f;
    brain.update(0.05f, s); // -> approach
    std::vector<std::string> markers;
    for (int i = 0; i < 40; ++i) {
        brain.update(0.05f, s);
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
        if (brain.replanWanted()) brain.clearReplan();
    }
    CHECK(hasMarker(markers, "AUTOPLAY_GIVEUP reason=target_unreachable"),
          "unreachable/giveup_logged");
    CHECK(hasMarker(markers, "AUTOPLAY_RESULT target=515001 damaged=0 killed=0 carried=0"),
          "unreachable/result_no_claims");

    // Progress resets the out-of-reach count: two STUCK, then a big close,
    // then two more STUCK must NOT give up (count restarted).
    p2autoplay::Brain brain2(cfg);
    brain2.update(0.05f, s);
    brain2.update(0.05f, s);
    p2autoplay::Senses s2 = s;
    s2.targetDist = 1000.0f;
    brain2.update(0.05f, s2); // -> approach
    for (int i = 0; i < 8; ++i) { // ~2 STUCK windows, no progress
        brain2.update(0.05f, s2);
        if (brain2.replanWanted()) brain2.clearReplan();
    }
    brain2.takeMarkers();
    s2.targetDist = 500.0f; // real progress: well past stuckMinProgress
    for (int i = 0; i < 4; ++i) { // one window carrying the progress: resets the count
        brain2.update(0.05f, s2);
        if (brain2.replanWanted()) brain2.clearReplan();
    }
    brain2.takeMarkers();
    std::vector<std::string> m2;
    for (int i = 0; i < 8; ++i) { // two more STUCK after progress: count restarts (2 < 3)
        brain2.update(0.05f, s2);
        const std::vector<std::string> got = brain2.takeMarkers();
        m2.insert(m2.end(), got.begin(), got.end());
        if (brain2.replanWanted()) brain2.clearReplan();
    }
    CHECK(!hasMarker(m2, "target_unreachable"), "unreachable/progress_resets_count");
}

void testContainerGuards()
{
    // bot-v3 root-cause fix: leaving the withdraw menu (or engaging) while
    // the Onion container UI is open strands the navi in NAVISTATE_Container
    // (stick drives the UI, velocity stays 0: bc2 38x identical detour).
    // Select/Approach/Attack/Aftermath/Done with containerOpen bounce back
    // to WithdrawMenu; the menu never leaves while open.
    p2autoplay::Config cfg;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s); // idle -> withdraw_seek
    brain.update(0.05f, s); // -> select
    CHECK(brain.current() == p2autoplay::State::Select, "containerguard/reaches_select");
    // Select with the UI open: back to the menu, never to approach.
    s.containerOpen = true;
    s.targetToken = 616001u;
    s.targetSource = 44;
    s.targetAlive = true;
    s.targetDist = 500.0f;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::WithdrawMenu, "containerguard/select_bounces_to_menu");
    // Full squad but the UI still open: the menu must NOT leave dirty (old
    // code entered Select after 4s); it keeps confirming until close.
    for (int i = 0; i < 100; ++i) brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::WithdrawMenu, "containerguard/menu_waits_for_close");
    // Close the UI with a full squad: menu confirms, then leaves for select.
    s.containerOpen = false;
    s.onionStored = 0;
    for (int i = 0; i < 20 && brain.current() == p2autoplay::State::WithdrawMenu; ++i) {
        brain.update(0.05f, s);
    }
    CHECK(brain.current() == p2autoplay::State::Select, "containerguard/menu_leaves_when_closed");
    // Approach with the UI open: back to the menu (no steering freeze).
    brain.update(0.05f, s); // -> approach (closed, target live)
    CHECK(brain.current() == p2autoplay::State::Approach, "containerguard/enters_approach");
    s.containerOpen = true;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::WithdrawMenu, "containerguard/approach_bounces_to_menu");
    // Done with the UI open: back to the menu as well.
    p2autoplay::Brain brain2(cfg);
    brain2.update(0.05f, s);
    p2autoplay::Senses s2 = liveSenses();
    s2.fieldPikmin = 20;
    s2.containerOpen = false;
    brain2.update(0.05f, s2);
    s2.targetToken = 0;
    s2.targetAlive = false;
    brain2.update(0.05f, s2);
    CHECK(brain2.current() == p2autoplay::State::Done, "containerguard/enters_done");
    s2.containerOpen = true;
    brain2.update(0.05f, s2);
    CHECK(brain2.current() == p2autoplay::State::WithdrawMenu, "containerguard/done_bounces_to_menu");
}

void testDoneIdlesNearOnion()
{
    // bot-v3: Done (no targets left) steers back toward the Onion instead of
    // standing still; close to the Onion it goes neutral.
    p2autoplay::Config cfg;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s); // idle -> withdraw_seek
    brain.update(0.05f, s); // withdraw_seek -> select (squad ready)
    CHECK(brain.current() == p2autoplay::State::Select, "done-idle/reaches_select");
    s.targetToken = 0; // no targets left
    s.targetAlive = false;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Done, "done-idle/enters_done");
    s.hasOnion = true;
    s.naviX = 0.0f;
    s.naviZ = 0.0f;
    s.onionX = 400.0f;
    s.onionZ = 0.0f;
    s.onionDist = 400.0f;
    brain.update(0.05f, s);
    const p2autoplay::Command far = brain.command();
    CHECK(far.moveX > 0.9f && std::fabs(far.moveZ) < 0.01f, "done-idle/steers_to_onion");
    s.onionDist = 10.0f;
    s.onionX = 10.0f;
    brain.update(0.05f, s);
    const p2autoplay::Command near = brain.command();
    CHECK(near.moveX == 0.0f && near.moveZ == 0.0f, "done-idle/neutral_when_close");
}

void testPowerGate()
{
    // bot-v4: PIKMIN_RANDOMIZER_AUTOPLAY_POWER is off by default and ONLY
    // meaningful when the autoplay gate is already on (inert in normal play).
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", nullptr);
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", nullptr);
    CHECK(!p2autoplay::isPowerEnabled(), "power/off_by_default");
    CHECK(p2autoplay::powerDamageMult() == 1.0f, "power/mult_one_when_off");
    // Inert in normal play: POWER set but the autoplay gate closed.
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", "10");
    CHECK(!p2autoplay::isPowerEnabled(), "power/inert_when_gate_closed");
    CHECK(p2autoplay::powerDamageMult() == 1.0f, "power/mult_one_when_gate_closed");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", "0");
    CHECK(!p2autoplay::isPowerEnabled(), "power/inert_when_gate_zero");
    // Gate open, POWER unset: still off.
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", "1");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", nullptr);
    CHECK(!p2autoplay::isPowerEnabled(), "power/off_when_unset");
    // Gate open + POWER on: numeric value configures the multiplier, any
    // other non-empty non-"0" value means on with the default x10.
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", "1");
    CHECK(p2autoplay::isPowerEnabled(), "power/on_with_gate");
    CHECK(p2autoplay::powerDamageMult() == 1.0f, "power/numeric_one_is_x1");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", "on");
    CHECK(p2autoplay::powerDamageMult() == 10.0f, "power/default_x10");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", "7.5");
    CHECK(p2autoplay::isPowerEnabled(), "power/on_with_number");
    CHECK(std::fabs(p2autoplay::powerDamageMult() - 7.5f) < 0.001f, "power/numeric_configures_mult");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", "0");
    CHECK(!p2autoplay::isPowerEnabled(), "power/zero_is_off");
    // Effective squad: ~100 in power mode, cfg.wantSquad otherwise.
    p2autoplay::Config cfg;
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", "10");
    CHECK(p2autoplay::effectiveWantSquad(cfg) == 100, "power/want_100");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", nullptr);
    CHECK(p2autoplay::effectiveWantSquad(cfg) == cfg.wantSquad, "power/want_normal_when_off");

    // bot-v4b Onion stock delta: pure function, inert when power is off.
    CHECK(p2autoplay::powerStockTarget() == 100, "power/stock_target_100");
    // Inert when either gate is unset: delta is 0 no matter the counts.
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", nullptr);
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", "10");
    CHECK(p2autoplay::powerStockDelta(p2autoplay::isPowerEnabled(), 20, 0, 20, 100) == 0,
          "power/stock_inert_when_gate_closed");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", "1");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", nullptr);
    CHECK(p2autoplay::powerStockDelta(p2autoplay::isPowerEnabled(), 20, 0, 20, 100) == 0,
          "power/stock_inert_when_power_unset");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", "0");
    CHECK(p2autoplay::powerStockDelta(p2autoplay::isPowerEnabled(), 20, 0, 20, 100) == 0,
          "power/stock_inert_when_power_zero");
    // Enabled: fresh boot (stored 20, field 0) tops up 80 to reach 100.
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", "10");
    CHECK(p2autoplay::powerStockDelta(p2autoplay::isPowerEnabled(), 20, 0, 20, 100) == 80,
          "power/stock_80_from_boot");
    // Mid-run (stored 0, field 20 already withdrawn) still tops to 100 total.
    CHECK(p2autoplay::powerStockDelta(p2autoplay::isPowerEnabled(), 0, 20, 20, 100) == 80,
          "power/stock_80_mid_run");
    // Already full: no top-up. At the pool limit: no top-up.
    CHECK(p2autoplay::powerStockDelta(p2autoplay::isPowerEnabled(), 100, 0, 100, 100) == 0,
          "power/stock_none_when_full");
    CHECK(p2autoplay::powerStockDelta(p2autoplay::isPowerEnabled(), 20, 0, 100, 100) == 0,
          "power/stock_none_at_limit");
    // Capped by pool room, never overfills past the limit.
    CHECK(p2autoplay::powerStockDelta(p2autoplay::isPowerEnabled(), 20, 0, 90, 100) == 10,
          "power/stock_capped_by_limit");

    // RESULT tagging: power=1 on every result of a power run, absent otherwise.
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", "10");
    {
        p2autoplay::Brain brain(cfg);
        p2autoplay::Senses s = liveSenses();
        s.fieldPikmin = 20;
        brain.update(0.05f, s);
        brain.update(0.05f, s); // -> select
        s.targetToken = 610001;
        s.targetSource = 79;
        s.targetAlive = true;
        s.targetDist = 100.0f;
        brain.update(0.05f, s); // -> approach
        brain.update(0.05f, s); // -> attack
        s.targetHealthFrac = 0.5f;
        brain.update(0.05f, s);
        s.targetAlive = false;
        s.transportSeen = true;
        brain.update(0.05f, s); // -> aftermath
        s.receiptSeen = true;
        std::vector<std::string> markers;
        for (int i = 0; i < 60 && brain.current() == p2autoplay::State::Aftermath; ++i) {
            brain.update(0.05f, s);
            const std::vector<std::string> got = brain.takeMarkers();
            markers.insert(markers.end(), got.begin(), got.end());
        }
        CHECK(hasMarker(markers, "power=1"), "power/result_tagged");
    }
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", nullptr);
    {
        p2autoplay::Brain brain(cfg);
        p2autoplay::Senses s = liveSenses();
        s.fieldPikmin = 20;
        brain.update(0.05f, s);
        brain.update(0.05f, s); // -> select
        s.targetToken = 610002;
        s.targetSource = 79;
        s.targetAlive = true;
        s.targetDist = 100.0f;
        brain.update(0.05f, s); // -> approach
        brain.update(0.05f, s); // -> attack
        s.targetHealthFrac = 0.5f;
        brain.update(0.05f, s);
        s.targetAlive = false;
        s.transportSeen = true;
        brain.update(0.05f, s); // -> aftermath
        s.receiptSeen = true;
        std::vector<std::string> markers;
        for (int i = 0; i < 60 && brain.current() == p2autoplay::State::Aftermath; ++i) {
            brain.update(0.05f, s);
            const std::vector<std::string> got = brain.takeMarkers();
            markers.insert(markers.end(), got.begin(), got.end());
        }
        CHECK(hasMarker(markers, "AUTOPLAY_RESULT target=610002"), "power/control_result_logged");
        CHECK(!hasMarker(markers, "power=1"), "power/control_result_untagged");
    }
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", nullptr);
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", nullptr);
}

void testRegroupDistress()
{
    // bot-v4 regroup rule: distress (grabbed/thrown-off/burning) or a
    // scattered squad whistles first, then re-throws once the squad is back.
    // A plain attack-latch (targetGrabbing on a ground enemy) must NOT
    // whistle: those Pikmin are dealing damage, and recalling them stalls the
    // fight (v4dev-1 Chappy regression: permanent whistle, hp stuck at 0.96).
    p2autoplay::Config cfg;
    cfg.throwHold = 0.1f;
    cfg.throwGap = 0.2f;
    cfg.whistleHold = 0.2f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 620001;
    s.targetSource = 44; // ground enemy
    s.targetAlive = true;
    s.targetDist = 100.0f;
    s.targetHealthFrac = 1.0f;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    CHECK(brain.current() == p2autoplay::State::Attack, "regroup/attacks");
    // Distress (thrown-off/burning): whistle takes over throwing.
    s.squadDistress = true;
    brain.update(0.05f, s);
    CHECK(brain.command().buttons & unsigned(p2autoplay::PadB), "regroup/distress_whistles");
    // Attack-latch on a ground enemy is not a grab: no whistle, throws continue.
    s.squadDistress = false;
    s.targetGrabbing = true;
    for (int i = 0; i < 10; ++i) brain.update(0.05f, s);
    CHECK(!(brain.command().buttons & unsigned(p2autoplay::PadB)), "regroup/latch_does_not_whistle");
    int aOn = 0;
    for (int i = 0; i < 40; ++i) {
        brain.update(0.05f, s);
        if (brain.command().buttons & unsigned(p2autoplay::PadA)) ++aOn;
    }
    CHECK(aOn > 0, "regroup/keeps_throwing_while_latched");
    // Sarai capture (flyer grab): whistle frees the grabbed Pikmin.
    p2autoplay::Brain brain2(cfg);
    brain2.update(0.05f, s);
    p2autoplay::Senses s2 = liveSenses();
    s2.fieldPikmin = 20;
    brain2.update(0.05f, s2);
    s2.targetToken = 620002;
    s2.targetSource = 23; // Sarai
    s2.targetAlive = true;
    s2.targetDist = 200.0f;
    s2.targetLow = true;
    s2.targetGrabbing = true;
    brain2.update(0.05f, s2); // -> approach
    brain2.update(0.05f, s2); // -> attack
    brain2.update(0.05f, s2); // whistle answers the grab
    CHECK(brain2.command().buttons & unsigned(p2autoplay::PadB), "regroup/sarai_grab_whistles");
    // Squad back: whistle releases and throws resume.
    s.squadDistress = false;
    s.targetGrabbing = false;
    for (int i = 0; i < 10; ++i) brain.update(0.05f, s);
    aOn = 0;
    for (int i = 0; i < 40; ++i) {
        brain.update(0.05f, s);
        if (brain.command().buttons & unsigned(p2autoplay::PadA)) ++aOn;
    }
    CHECK(aOn > 0, "regroup/rethrows_after_regroup");
}

void testResupply()
{
    // bot-v4 resupply rule: field below threshold + Onion stock => disengage
    // to WithdrawSeek with AUTOPLAY_RESUPPLY; no detour when the Onion is
    // empty or the squad is healthy.
    p2autoplay::Config cfg;
    cfg.resupplyThreshold = 5;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 630001;
    s.targetSource = 44;
    s.targetAlive = true;
    s.targetDist = 100.0f;
    s.targetHealthFrac = 1.0f;
    s.hasOnion = true;
    s.onionStored = 10;
    s.onionDist = 500.0f;
    s.onionX = -500.0f;
    s.onionZ = 0.0f;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    CHECK(brain.current() == p2autoplay::State::Attack, "resupply/attacks");
    s.fieldPikmin = 2; // squad eaten, Onion still stocks
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::WithdrawSeek, "resupply/disengages_to_withdraw");
    CHECK(hasMarker(brain.takeMarkers(), "AUTOPLAY_RESUPPLY"), "resupply/marker_logged");
    // Back at the Onion with a fresh squad: the machine can re-engage.
    s.fieldPikmin = 15;
    s.onionDist = 10.0f;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Select
              || brain.current() == p2autoplay::State::WithdrawSeek,
          "resupply/withdraws_then_selects");
    // Control: empty Onion never disengages (nothing to withdraw).
    p2autoplay::Brain brain2(cfg);
    brain2.update(0.05f, s);
    p2autoplay::Senses s2 = liveSenses();
    s2.fieldPikmin = 20;
    brain2.update(0.05f, s2);
    s2.targetToken = 630002;
    s2.targetSource = 44;
    s2.targetAlive = true;
    s2.targetDist = 100.0f;
    s2.hasOnion = true;
    s2.onionStored = 0;
    brain2.update(0.05f, s2);
    brain2.update(0.05f, s2);
    s2.fieldPikmin = 2;
    brain2.update(0.05f, s2);
    CHECK(brain2.current() == p2autoplay::State::Attack, "resupply/no_detour_when_empty");
    CHECK(!hasMarker(brain2.takeMarkers(), "AUTOPLAY_RESUPPLY"), "resupply/no_marker_when_empty");
}

void testAftermathEscortExtension()
{
    // bot-v4: a carry en route doubles the receipt window instead of timing
    // out while the corpse is still being carried (bc3 receipt_timeout).
    // bot-v5: the extension needs carriers > 0 AND the corpse moving (live);
    // a latched-but-stalled lift times out bounded with carry_stalled.
    p2autoplay::Config cfg;
    cfg.receiptTimeout = 1.0f;
    cfg.aftermathTimeout = 60.0f;
    cfg.whistleHold = 0.2f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 640001;
    s.targetSource = 79;
    s.targetAlive = true;
    s.targetDist = 100.0f;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    s.targetHealthFrac = 0.5f;
    brain.update(0.05f, s);
    s.targetAlive = false;
    s.transportSeen = true; // corpse en route, no receipt yet
    s.corpseMoving = true; // ... and the corpse is actually moving
    s.receiptSeen = false;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Aftermath, "escort/waits_after_kill");
    for (int i = 0; i < 30; ++i) brain.update(0.05f, s); // 1.5s > base 1.0s window
    CHECK(brain.current() == p2autoplay::State::Aftermath, "escort/outlasts_base_window_while_carrying");
    CHECK(!hasMarker(brain.takeMarkers(), "AUTOPLAY_RESULT"), "escort/no_early_result_while_carrying");

    // Control: carriers but no motion -> no extension, bounded stall giveup.
    p2autoplay::Brain stalled(cfg);
    stalled.update(0.05f, s);
    p2autoplay::Senses s2 = liveSenses();
    s2.fieldPikmin = 20;
    stalled.update(0.05f, s2); // -> select
    s2.targetToken = 640002;
    s2.targetSource = 79;
    s2.targetAlive = true;
    s2.targetDist = 100.0f;
    stalled.update(0.05f, s2); // -> approach
    stalled.update(0.05f, s2); // -> attack
    s2.targetHealthFrac = 0.5f;
    stalled.update(0.05f, s2);
    s2.targetAlive = false;
    s2.transportSeen = true; // lift seen...
    s2.corpseMoving = false; // ... but the corpse never moves
    s2.receiptSeen = false;
    stalled.update(0.05f, s2);
    std::vector<std::string> stalledMarkers;
    for (int i = 0; i < 60 && stalled.current() == p2autoplay::State::Aftermath; ++i) {
        stalled.update(0.05f, s2);
        const std::vector<std::string> got = stalled.takeMarkers();
        stalledMarkers.insert(stalledMarkers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(stalledMarkers, "AUTOPLAY_GIVEUP reason=carry_stalled"),
          "escort/stall_no_extension");
    CHECK(hasMarker(stalledMarkers, "AUTOPLAY_RESULT target=640002 damaged=1 killed=1 carried=0"),
          "escort/stall_no_carry_claim");
}

void testAftermathNoWhistle()
{
    // bot-v5 (v4b diagnosis): aftermath HOLDS whistle (B) while standing
    // 36-65 u from the corpse, so Pikmin gather at the navi and no carry
    // ever initiates. Aftermath must never whistle, even scattered / in
    // distress / grabbing: it releases B and delivers with stick + throws.
    p2autoplay::Config cfg;
    cfg.throwHold = 0.1f;
    cfg.throwGap = 0.2f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 650001;
    s.targetSource = 2;
    s.targetAlive = true;
    s.targetDist = 100.0f;
    s.naviX = 0.0f;
    s.naviZ = 0.0f;
    s.tgtX = 100.0f;
    s.tgtZ = 0.0f;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    s.targetHealthFrac = 0.5f;
    brain.update(0.05f, s);
    s.targetAlive = false;
    s.targetDist = 50.0f; // corpse 50 u out
    s.tgtX = 50.0f;
    s.scattered = true; // worst case: scattered + distress + grab
    s.squadDistress = true;
    s.targetGrabbing = true;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Aftermath, "nowhistle/aftermath");
    bool whistled = false, steered = false;
    for (int i = 0; i < 60; ++i) {
        brain.update(0.05f, s);
        const p2autoplay::Command cmd = brain.command();
        if (cmd.buttons & unsigned(p2autoplay::PadB)) whistled = true;
        if (cmd.moveX > 0.5f) steered = true; // walks ONTO the corpse, not idle
        if (brain.current() != p2autoplay::State::Aftermath) break;
    }
    CHECK(!whistled, "nowhistle/releases_B_despite_scatter");
    CHECK(steered, "nowhistle/closes_onto_corpse");
}

void testAftermathSeedBackoffRethrow()
{
    // bot-v5 delivery loop: seed (onto the corpse + throws), bounded wait,
    // back off out of contact, re-approach + re-throw bounded times, then a
    // named giveup (carry_no_grab) - all pad-only.
    p2autoplay::Config cfg;
    cfg.throwHold = 0.1f;
    cfg.throwGap = 0.2f;
    cfg.receiptTimeout = 60.0f;
    cfg.aftermathTimeout = 60.0f;
    cfg.carryGrabWait = 0.5f;
    cfg.aftermathSettleWait = 0.5f;
    cfg.aftermathRethrowMax = 2;
    cfg.aftermathApproachRadius = 60.0f;
    cfg.aftermathBackoffDist = 200.0f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 650002;
    s.targetSource = 27;
    s.targetAlive = true;
    s.targetDist = 300.0f;
    s.naviX = 0.0f;
    s.naviZ = 0.0f;
    s.tgtX = 300.0f;
    s.tgtZ = 0.0f;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    s.targetHealthFrac = 0.5f;
    brain.update(0.05f, s);
    s.targetAlive = false; // kill: corpse 300 u out, nobody grabs it
    s.transportSeen = false;
    s.carryCount = 0;
    s.pelletCarriers = 0;
    s.corpseMoving = false;
    s.receiptSeen = false;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Aftermath, "seed/aftermath");
    // Far: steers onto the corpse and throws once in range.
    brain.update(0.05f, s);
    CHECK(brain.command().moveX > 0.5f, "seed/steers_onto_corpse");
    s.targetDist = 50.0f; // closed into the contact ring
    s.tgtX = 50.0f;
    int aOn = 0;
    for (int i = 0; i < 12; ++i) {
        brain.update(0.05f, s);
        if (brain.command().buttons & unsigned(p2autoplay::PadA)) ++aOn;
    }
    CHECK(aOn > 0, "seed/throws_at_corpse");
    // Bounded wait on the corpse with no grab: backs off (steers AWAY).
    bool backed = false;
    for (int i = 0; i < 20 && !backed; ++i) {
        brain.update(0.05f, s);
        if (brain.command().moveX < -0.5f) backed = true;
    }
    CHECK(backed, "seed/backs_off_when_no_grab");
    // Settle out of contact (or settle wait): re-approach + re-throw logged.
    std::vector<std::string> markers;
    s.targetDist = 200.0f; // reached backoff distance
    for (int i = 0; i < 5; ++i) {
        brain.update(0.05f, s);
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(markers, "AUTOPLAY_RETHROW token=650002 attempt=1"), "seed/rethrow_logged");
    // Window expiry far from the corpse with no grab: named giveup, kill
    // kept, no carry claim. (Seed never reaches the contact ring at
    // tdist=200, so the bounded window, not a phase cap, ends it.)
    for (int i = 0; i < 1400 && brain.current() == p2autoplay::State::Aftermath; ++i) {
        brain.update(0.05f, s);
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(markers, "AUTOPLAY_GIVEUP reason=carry_no_grab"), "seed/giveup_names_no_grab");
    CHECK(hasMarker(markers, "AUTOPLAY_RESULT target=650002 damaged=1 killed=1 carried=0"),
          "seed/result_no_carry_claim");
    int rethrows = 0;
    for (const std::string& m : markers) {
        if (m.find("AUTOPLAY_RETHROW") != std::string::npos) ++rethrows;
    }
    CHECK(rethrows <= 2, "seed/rethrows_bounded");
}

void testAftermathEscortNoThrows()
{
    // bot-v5 escort: while the carry is active the bot follows the corpse
    // (steers when far) and stops throwing so the crew keeps hauling.
    p2autoplay::Config cfg;
    cfg.receiptTimeout = 60.0f;
    cfg.throwHold = 0.1f;
    cfg.throwGap = 0.2f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 650003;
    s.targetSource = 79;
    s.targetAlive = true;
    s.targetDist = 100.0f;
    s.naviX = 0.0f;
    s.naviZ = 0.0f;
    s.tgtX = 500.0f;
    s.tgtZ = 0.0f;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    s.targetHealthFrac = 0.5f;
    brain.update(0.05f, s);
    s.targetAlive = false;
    s.transportSeen = true;
    s.carryCount = 6;
    s.corpseMoving = true;
    s.receiptSeen = false;
    s.targetDist = 500.0f;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Aftermath, "escort2/aftermath");
    int aOn = 0;
    bool followed = false;
    for (int i = 0; i < 20; ++i) {
        brain.update(0.05f, s);
        const p2autoplay::Command cmd = brain.command();
        if (cmd.buttons & unsigned(p2autoplay::PadA)) ++aOn;
        if (cmd.buttons & unsigned(p2autoplay::PadB)) aOn += 1000; // whistle forbidden too
        if (cmd.moveX > 0.5f) followed = true;
    }
    CHECK(aOn == 0, "escort2/no_throws_no_whistle_while_hauling");
    CHECK(followed, "escort2/follows_corpse");
    CHECK(brain.current() == p2autoplay::State::Aftermath, "escort2/keeps_escorting");
}

void testAftermathGiveupReasons()
{    // bot-v5: the giveup names the broken link (despawned / no grab /
    // stalled / out of reach / slow receipt).
    p2autoplay::Config cfg;
    cfg.receiptTimeout = 0.5f;
    cfg.aftermathTimeout = 60.0f;
    cfg.carryGrabWait = 100.0f; // stay seeding: reach the window, not a phase cap
    cfg.aftermathRethrowMax = 100;
    cfg.corpseOutOfReach = 800.0f;
    const auto runKill = [&](unsigned token, p2autoplay::Senses s, float corpseDist) {
        p2autoplay::Brain* brain = new p2autoplay::Brain(cfg);
        brain->update(0.05f, s);
        brain->update(0.05f, s); // -> select
        s.targetToken = token;
        s.targetSource = 2;
        s.targetAlive = true;
        s.targetDist = 100.0f;
        brain->update(0.05f, s); // -> approach
        brain->update(0.05f, s); // -> attack
        s.targetHealthFrac = 0.5f;
        brain->update(0.05f, s);
        s.targetAlive = false;
        s.targetDist = corpseDist; // aftermath sees the corpse at this distance
        s.receiptSeen = false;
        brain->update(0.05f, s); // -> aftermath
        std::vector<std::string> markers;
        for (int i = 0; i < 120 && brain->current() == p2autoplay::State::Aftermath; ++i) {
            brain->update(0.05f, s);
            const std::vector<std::string> got = brain->takeMarkers();
            markers.insert(markers.end(), got.begin(), got.end());
        }
        delete brain;
        return markers;
    };
    // Corpse gone entirely (no body, no pellet, no carry): despawned.
    p2autoplay::Senses d = liveSenses();
    d.fieldPikmin = 20;
    d.pelletExists = false;
    d.transportSeen = false;
    d.carryCount = 0;
    d.targetDist = 100.0f;
    CHECK(hasMarker(runKill(651001, d, 100.0f), "reason=corpse_despawned"), "reasons/despawned");
    // Present corpse, nobody grabs, far away: out of reach.
    p2autoplay::Senses f = liveSenses();
    f.fieldPikmin = 20;
    f.pelletExists = true;
    f.transportSeen = false;
    f.carryCount = 0;
    f.targetDist = 900.0f;
    CHECK(hasMarker(runKill(651002, f, 900.0f), "reason=corpse_out_of_reach"), "reasons/out_of_reach");
    // Present corpse, moving haul, receipt just slow: receipt_timeout kept.
    p2autoplay::Senses r = liveSenses();
    r.fieldPikmin = 20;
    r.pelletExists = true;
    r.transportSeen = true;
    r.carryCount = 4;
    r.corpseMoving = true;
    r.targetDist = 100.0f;
    p2autoplay::Config cfg2 = cfg;
    cfg2.receiptTimeout = 0.5f; // base 0.5, extended 1.0: loop 120 ticks (6 s) covers it
    p2autoplay::Brain brainR(cfg2);
    brainR.update(0.05f, r);
    brainR.update(0.05f, r);
    p2autoplay::Senses r2 = r;
    r2.targetToken = 651003;
    r2.targetSource = 2;
    r2.targetAlive = true;
    brainR.update(0.05f, r2);
    brainR.update(0.05f, r2);
    r2.targetHealthFrac = 0.5f;
    brainR.update(0.05f, r2);
    r2.targetAlive = false;
    brainR.update(0.05f, r2);
    std::vector<std::string> mr;
    for (int i = 0; i < 120 && brainR.current() == p2autoplay::State::Aftermath; ++i) {
        brainR.update(0.05f, r2);
        const std::vector<std::string> got = brainR.takeMarkers();
        mr.insert(mr.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(mr, "reason=receipt_timeout"), "reasons/slow_receipt");
}

void testReceiptPerTokenOnly()
{
    // bot-v5: RESULT received=1 comes ONLY from this token's own ledger
    // receipt (receiptSeen). A kill + visible carry with NO receipt scores
    // carried=0 received=0: bystander CHECK Bestiary:Deliver lines (which the
    // harness used to count) must never flip the bot's verdict.
    p2autoplay::Config cfg;
    cfg.receiptTimeout = 0.5f;
    cfg.whistleHold = 0.2f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 652001;
    s.targetSource = 30; // Queen: v4b saw a bystander Spotty-Bulborb deliver CHECK here
    s.targetAlive = true;
    s.targetDist = 100.0f;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    s.targetHealthFrac = 0.4f;
    brain.update(0.05f, s);
    s.targetAlive = false;
    s.transportSeen = true; // crew on it...
    s.receiptSeen = false; // ... but no ledger line for THIS token
    brain.update(0.05f, s);
    std::vector<std::string> markers;
    for (int i = 0; i < 120 && brain.current() == p2autoplay::State::Aftermath; ++i) {
        brain.update(0.05f, s);
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(markers, "AUTOPLAY_RESULT target=652001 damaged=1 killed=1 carried=0"),
          "pertoken/carry_refused_without_ledger");
    CHECK(hasMarker(markers, "received=0"), "pertoken/received_refused_without_ledger");
    CHECK(!hasMarker(markers, "received=1"), "pertoken/no_bystander_receipt");
}

void testAftermathStallRethrow()
{
    // bot-v5 (v5dev-1 Chappy/Kurage lesson) as grown by bot-v7: a
    // grabbed-but-stalled lift below the corpse's declared minimum keeps
    // seeding (SeedGrow) to grow the crew instead of escorting it forever.
    // Recent motion gates the window: moved-then-stopped names carry_stalled,
    // not receipt_timeout. No-progress grow episodes burn the bounded
    // rethrow budget, then the stall is named.
    p2autoplay::Config cfg;
    cfg.throwHold = 0.1f;
    cfg.throwGap = 0.2f;
    cfg.receiptTimeout = 60.0f;
    cfg.aftermathTimeout = 60.0f;
    cfg.carryStallWait = 0.5f;
    cfg.aftermathRethrowMax = 2;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 653001;
    s.targetSource = 2; // Chappy-weight corpse, light crew
    s.targetAlive = true;
    s.targetDist = 100.0f;
    s.naviX = 0.0f;
    s.naviZ = 0.0f;
    s.tgtX = 100.0f;
    s.tgtZ = 0.0f;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    s.targetHealthFrac = 0.5f;
    brain.update(0.05f, s);
    s.targetAlive = false; // kill: 2 carriers grab but cannot lift a 10-weight corpse
    s.transportSeen = true;
    s.carryCount = 2;
    s.pelletCarriers = 2;
    s.carryWant = 10;
    s.corpseMoving = true; // hauling at first...
    s.corpseMoved = true;
    s.receiptSeen = false;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Aftermath, "stall/aftermath");
    // A short crew grows even while the corpse moves (v7dev-1 Tank: a slide
    // reads moving=1; motion with a short crew is never a real lift, so the
    // shortfall alone seeds). Advance the fix each tick so the stall watch
    // would see motion, like the driver's live pellet tracking.
    for (int i = 0; i < 10; ++i) {
        s.tgtX += 10.0f;
        brain.update(0.05f, s);
        CHECK(brain.command().moveX > 0.5f, "stall/grows_while_moving_when_short");
    }
    CHECK(brain.current() == p2autoplay::State::Aftermath, "stall/keeps_growing_while_short");
    // ... then the lift stalls (moved-ever, not moving now): freeze the fix.
    s.corpseMoving = false;
    std::vector<std::string> markers;
    // Re-seeding throws again (pad-only) instead of idling the escort:
    // sample throws across the regression + first grow episode (later the
    // bounded episodes name the stall and finish, after which a static
    // test sense bounces Select/Aftermath without new throws).
    int aOn = 0;
    for (int i = 0; i < 20; ++i) {
        brain.update(0.05f, s);
        if (brain.command().buttons & unsigned(p2autoplay::PadA)) ++aOn;
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(markers, "AUTOPLAY_RETHROW token=653001 attempt=1"), "stall/rethrow_logged");
    CHECK(hasMarker(markers, "reason=stalled"), "stall/reason_names_stall");
    CHECK(aOn > 0, "stall/rethrows_to_grow_crew");
    // Still stalled past the bounded budget: carry_stalled, kill kept.
    for (int i = 0; i < 200 && brain.current() == p2autoplay::State::Aftermath; ++i) {
        brain.update(0.05f, s);
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(markers, "AUTOPLAY_GIVEUP reason=carry_stalled"), "stall/giveup_names_stall");
    CHECK(hasMarker(markers, "AUTOPLAY_RESULT target=653001 damaged=1 killed=1 carried=0"),
          "stall/result_no_carry_claim");
}

void testAftermathGrowKeepsSeeding()
{
    // bot-v7 (v6b-1 Tank lesson): a grabbed lift below the declared minimum
    // that is not moving is NOT escorted (escort would park 100-250 u off
    // with throws suppressed, freezing the crew). It keeps seeding: onto
    // the corpse + throws, never whistle. Once the crew reaches the minimum
    // the escort takes over and throws stop.
    p2autoplay::Config cfg;
    cfg.throwHold = 0.1f;
    cfg.throwGap = 0.2f;
    cfg.receiptTimeout = 60.0f;
    cfg.aftermathTimeout = 60.0f;
    cfg.carryGrabWait = 100.0f; // stay seeding: phases never cap this test
    cfg.aftermathSettleWait = 100.0f;
    cfg.aftermathRethrowMax = 5;
    cfg.carryStallWait = 100.0f; // no stall episodes: the crew below keeps growing
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 80;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 654001;
    s.targetSource = 24; // Tank-weight corpse
    s.targetAlive = true;
    s.targetDist = 100.0f;
    s.naviX = 0.0f;
    s.naviZ = 0.0f;
    s.tgtX = 150.0f;
    s.tgtZ = 0.0f;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    s.targetHealthFrac = 0.5f;
    brain.update(0.05f, s);
    s.targetAlive = false; // kill: 4 carriers on a 12-weight corpse, stalled
    s.transportSeen = true;
    s.carryCount = 4;
    s.pelletCarriers = 4;
    s.carryWant = 12;
    s.corpseMoving = false;
    s.corpseMoved = false;
    s.receiptSeen = false;
    s.targetDist = 150.0f; // escort would hold here (inside 100-250): neutral
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Aftermath, "grow/aftermath");
    int aOn = 0, steered = 0, whistled = 0;
    for (int i = 0; i < 40; ++i) {
        brain.update(0.05f, s);
        const p2autoplay::Command cmd = brain.command();
        if (cmd.buttons & unsigned(p2autoplay::PadA)) ++aOn;
        if (cmd.buttons & unsigned(p2autoplay::PadB)) ++whistled;
        if (cmd.moveX > 0.5f) ++steered;
        if (brain.current() != p2autoplay::State::Aftermath) break;
    }
    CHECK(brain.current() == p2autoplay::State::Aftermath, "grow/keeps_seeding_while_short");
    CHECK(steered == 40, "grow/closes_onto_corpse_not_escort_hold");
    CHECK(aOn > 0, "grow/throws_onto_corpse");
    CHECK(whistled == 0, "grow/never_whistles");
    CHECK(!hasMarker(brain.takeMarkers(), "AUTOPLAY_RETHROW"), "grow/no_rethrow_for_first_shortfall");
    // Crew reaches the minimum: escort takes over (hold: neutral inside the
    // band, no throws).
    s.carryCount = 12;
    s.pelletCarriers = 12;
    int idle = 0;
    aOn = 0;
    for (int i = 0; i < 10; ++i) {
        brain.update(0.05f, s);
        const p2autoplay::Command cmd = brain.command();
        if (cmd.buttons & unsigned(p2autoplay::PadA)) ++aOn;
        if (cmd.moveX == 0.0f && cmd.moveZ == 0.0f) ++idle;
    }
    CHECK(aOn == 0, "grow/escort_stops_throws_when_enough");
    CHECK(idle == 10, "grow/escort_holds_when_enough");
}

void testAftermathReseedOnShrink()
{
    // bot-v7: a viable lift (escorted) whose crew shrinks below the minimum
    // re-seeds with reason=shrank instead of escorting the shortfall; the
    // episodes stay bounded and name carry_stalled past budget.
    p2autoplay::Config cfg;
    cfg.throwHold = 0.1f;
    cfg.throwGap = 0.2f;
    cfg.receiptTimeout = 60.0f;
    cfg.aftermathTimeout = 60.0f;
    cfg.carryStallWait = 0.5f;
    cfg.aftermathRethrowMax = 2;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 80;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 654002;
    s.targetSource = 2;
    s.targetAlive = true;
    s.targetDist = 100.0f;
    s.naviX = 0.0f;
    s.naviZ = 0.0f;
    s.tgtX = 100.0f;
    s.tgtZ = 0.0f;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    s.targetHealthFrac = 0.5f;
    brain.update(0.05f, s);
    s.targetAlive = false;
    s.transportSeen = true;
    s.carryCount = 10;
    s.pelletCarriers = 10;
    s.carryWant = 10; // full crew: escorts
    s.corpseMoving = false;
    s.corpseMoved = false;
    s.receiptSeen = false;
    s.targetDist = 150.0f;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Aftermath, "shrink/aftermath");
    for (int i = 0; i < 5; ++i) brain.update(0.05f, s); // escorting, viable
    CHECK(brain.command().moveX == 0.0f, "shrink/escort_holds_while_viable");
    // Crew shrinks below the minimum while stalled: re-seed (shrank), back
    // onto the corpse with throws.
    s.carryCount = 6;
    s.pelletCarriers = 6;
    std::vector<std::string> markers;
    for (int i = 0; i < 5; ++i) {
        brain.update(0.05f, s);
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(markers, "AUTOPLAY_RETHROW token=654002 attempt=1"), "shrink/rethrow_logged");
    CHECK(hasMarker(markers, "reason=shrank"), "shrink/reason_names_shrink");
    CHECK(brain.command().moveX > 0.5f, "shrink/reseeds_onto_corpse");
    // Shortfall never recovers: bounded episodes, then carry_stalled with the
    // kill kept and no carry claim.
    for (int i = 0; i < 200 && brain.current() == p2autoplay::State::Aftermath; ++i) {
        brain.update(0.05f, s);
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    int rethrows = 0;
    for (const std::string& m : markers) {
        if (m.find("AUTOPLAY_RETHROW") != std::string::npos) ++rethrows;
    }
    CHECK(rethrows <= 2, "shrink/rethrows_bounded");
    CHECK(hasMarker(markers, "AUTOPLAY_GIVEUP reason=carry_stalled"), "shrink/giveup_names_stall");
    CHECK(hasMarker(markers, "AUTOPLAY_RESULT target=654002 damaged=1 killed=1 carried=0"),
          "shrink/result_no_carry_claim");
}

void testAftermathUnknownWantEscorts()
{
    // bot-v7 compat: with no declared minimum (carryWant=0, e.g. the corpse
    // is not resolved yet) any live carry escorts exactly as v5/v6 did -
    // follow without throws - instead of seeding blindly.
    p2autoplay::Config cfg;
    cfg.throwHold = 0.1f;
    cfg.throwGap = 0.2f;
    cfg.receiptTimeout = 60.0f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 654003;
    s.targetSource = 79;
    s.targetAlive = true;
    s.targetDist = 100.0f;
    s.naviX = 0.0f;
    s.naviZ = 0.0f;
    s.tgtX = 500.0f;
    s.tgtZ = 0.0f;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    s.targetHealthFrac = 0.5f;
    brain.update(0.05f, s);
    s.targetAlive = false;
    s.transportSeen = true;
    s.carryCount = 2; // short crew, but no declared minimum...
    s.carryWant = 0;
    s.corpseMoving = false;
    s.receiptSeen = false;
    s.targetDist = 500.0f;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Aftermath, "unknown/aftermath");
    int aOn = 0;
    bool followed = false;
    for (int i = 0; i < 20; ++i) {
        brain.update(0.05f, s);
        const p2autoplay::Command cmd = brain.command();
        if (cmd.buttons & unsigned(p2autoplay::PadA)) ++aOn;
        if (cmd.moveX > 0.5f) followed = true;
    }
    CHECK(aOn == 0, "unknown/escort_no_throws_without_want");
    CHECK(followed, "unknown/escort_follows_without_want");
}

void testPowerFastSquad()
{
    // bot-v6: power mode takes the squad in ONE step (driver queues the whole
    // Onion through exitPikis). WithdrawSeek waits with a neutral pad - no A
    // taps, no menu hold, no WithdrawMenu cycles - until field>=80, then
    // Select. Normal mode keeps the menu behaviour (control below).
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", "1");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", "10");
    {
        p2autoplay::Config cfg;
        p2autoplay::Brain brain(cfg);
        p2autoplay::Senses s = liveSenses();
        brain.update(0.05f, s); // idle -> withdraw_seek
        CHECK(brain.current() == p2autoplay::State::WithdrawSeek, "powersquad/enters_seek");
        s.hasOnion = true;
        s.naviX = 0.0f;
        s.naviZ = 0.0f;
        s.onionX = 174.0f;
        s.onionZ = 0.0f;
        s.onionDist = 174.0f;
        s.onionStored = 100;
        s.fieldPikmin = 0;
        s.containerOpen = false;
        // The exit queue lands over seconds: short squads wait, pad-neutral.
        bool touchedMenu = false;
        for (int i = 0; i < 40; ++i) {
            brain.update(0.05f, s);
            if (brain.current() == p2autoplay::State::WithdrawMenu) touchedMenu = true;
            const p2autoplay::Command cmd = brain.command();
            if ((cmd.buttons & unsigned(p2autoplay::PadA)) || cmd.menuHold) touchedMenu = true;
            for (const std::string& m : brain.takeMarkers()) {
                if (m.find("withdraw_menu") != std::string::npos) touchedMenu = true;
            }
        }
        CHECK(brain.current() == p2autoplay::State::WithdrawSeek, "powersquad/waits_while_short");
        CHECK(!touchedMenu, "powersquad/no_menu_while_waiting");
        s.fieldPikmin = 50; // queue still dispensing: still waits
        brain.update(0.05f, s);
        CHECK(brain.current() == p2autoplay::State::WithdrawSeek, "powersquad/waits_at_half");
        s.fieldPikmin = 85; // one-step squad ready: straight to select
        brain.update(0.05f, s);
        CHECK(brain.current() == p2autoplay::State::Select, "powersquad/selects_at_80");
        CHECK(!hasMarker(brain.takeMarkers(), "AUTOPLAY_WITHDRAW cycle="), "powersquad/no_withdraw_cycles");
    }
    // Control: normal mode still works the menu (UI open -> WithdrawMenu).
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", nullptr);
    {
        p2autoplay::Config cfg;
        p2autoplay::Brain brain(cfg);
        p2autoplay::Senses s = liveSenses();
        brain.update(0.05f, s);
        s.hasOnion = true;
        s.onionDist = 10.0f;
        s.onionStored = 20;
        s.fieldPikmin = 0;
        s.containerOpen = true;
        brain.update(0.05f, s);
        CHECK(brain.current() == p2autoplay::State::WithdrawMenu, "powersquad/control_menu_when_off");
    }
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", nullptr);
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", nullptr);
}

void testSelectTargetGone()
{
    // bot-v6: Select verifies the target is still alive. A dead/absent target
    // with no latched damage is GIVEUP reason=target_gone (token/state as
    // evidence), not a silent Done. A latched kill for the SAME token (e.g.
    // an aftermath -> container bounce) returns to Aftermath so v5 delivery
    // still finishes instead of dropping the engagement.
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", "1");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", nullptr);
    p2autoplay::Config cfg;
    // Fresh select, target already dead, never damaged: named giveup + Done.
    {
        p2autoplay::Brain brain(cfg);
        p2autoplay::Senses s = liveSenses();
        s.fieldPikmin = 20;
        brain.update(0.05f, s);
        brain.update(0.05f, s); // -> select
        s.targetToken = 660001;
        s.targetSource = 24; // Tank
        s.targetAlive = false; // dead/absent before we ever engaged
        s.targetHealthFrac = 0.0f;
        std::vector<std::string> markers;
        brain.update(0.05f, s);
        for (const std::string& m : brain.takeMarkers()) markers.push_back(m);
        CHECK(brain.current() == p2autoplay::State::Done, "targetgone/done_when_dead");
        CHECK(hasMarker(markers, "AUTOPLAY_GIVEUP reason=target_gone"), "targetgone/giveup_logged");
        CHECK(hasMarker(markers, "token=660001"), "targetgone/token_evidence");
        CHECK(hasMarker(markers, "state=select"), "targetgone/state_evidence");
    }
    // No targets at all (token 0): still idles silently, no spurious giveup.
    {
        p2autoplay::Brain brain(cfg);
        p2autoplay::Senses s = liveSenses();
        s.fieldPikmin = 20;
        brain.update(0.05f, s);
        brain.update(0.05f, s); // -> select
        s.targetToken = 0;
        s.targetAlive = false;
        brain.update(0.05f, s);
        CHECK(brain.current() == p2autoplay::State::Done, "targetgone/done_when_empty");
        CHECK(!hasMarker(brain.takeMarkers(), "target_gone"), "targetgone/no_giveup_when_empty");
    }
    // Bounce: kill latched for this token, aftermath -> container UI ->
    // menu -> select with the target dead: back to Aftermath, no giveup.
    {
        p2autoplay::Brain brain(cfg);
        p2autoplay::Senses s = liveSenses();
        s.fieldPikmin = 20;
        brain.update(0.05f, s);
        brain.update(0.05f, s); // -> select
        s.targetToken = 660002;
        s.targetSource = 27; // Tadpole
        s.targetAlive = true;
        s.targetDist = 100.0f;
        s.targetHealthFrac = 1.0f;
        brain.update(0.05f, s); // -> approach
        brain.update(0.05f, s); // -> attack
        s.targetHealthFrac = 0.5f;
        brain.update(0.05f, s);
        s.targetAlive = false; // kill
        s.transportSeen = false;
        s.receiptSeen = false;
        brain.update(0.05f, s);
        CHECK(brain.current() == p2autoplay::State::Aftermath, "targetgone/aftermath_after_kill");
        s.containerOpen = true; // stepped on the Onion mid-delivery: UI bounce
        brain.update(0.05f, s);
        CHECK(brain.current() == p2autoplay::State::WithdrawMenu, "targetgone/bounces_to_menu");
        // Work the UI like the container guard does: the full-squad confirm
        // needs menuHoldTime>1.2 s and stateTime>4 s while open...
        for (int i = 0; i < 100 && brain.current() == p2autoplay::State::WithdrawMenu; ++i) {
            brain.update(0.05f, s);
        }
        s.containerOpen = false; // ... then the UI closes and the menu leaves.
        s.onionStored = 0;
        for (int i = 0; i < 10 && brain.current() == p2autoplay::State::WithdrawMenu; ++i) {
            brain.update(0.05f, s);
        }
        CHECK(brain.current() == p2autoplay::State::Select, "targetgone/menu_returns_to_select");
        // ... select sees the same dead token with the kill latched ...
        std::vector<std::string> markers;
        for (int i = 0; i < 5; ++i) {
            brain.update(0.05f, s);
            for (const std::string& m : brain.takeMarkers()) markers.push_back(m);
            if (brain.current() != p2autoplay::State::Select) break;
        }
        CHECK(brain.current() == p2autoplay::State::Aftermath, "targetgone/latched_kill_resumes_aftermath");
        CHECK(!hasMarker(markers, "target_gone"), "targetgone/no_giveup_for_latched_kill");
    }
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", nullptr);
}

void testUndamagedAttack()
{
    // bot-undamaged (bc5): permanent whistle (800 s B, zero throws on
    // 16/30/38/40/42/73/95/96) must be bounded, and fled targets must be
    // chased via approach (graph) instead of whistling in place.
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", "1");
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER", nullptr);
    // 1. Persistent distress still times out (RESULT emitted, not a stall).
    {
        p2autoplay::Config cfg;
        cfg.attackTimeout = 1.0f;
        cfg.whistleHold = 0.2f;
        cfg.whistleCooldown = 0.3f;
        cfg.throwHold = 0.1f;
        cfg.throwGap = 0.2f;
        p2autoplay::Brain brain(cfg);
        p2autoplay::Senses s = liveSenses();
        s.fieldPikmin = 20;
        brain.update(0.05f, s);
        brain.update(0.05f, s); // -> select
        s.targetToken = 670001;
        s.targetSource = 42; // BlueChappy (ground)
        s.targetAlive = true;
        s.targetDist = 50.0f;
        s.targetHealthFrac = 1.0f;
        brain.update(0.05f, s); // -> approach
        brain.update(0.05f, s); // -> attack
        CHECK(brain.current() == p2autoplay::State::Attack, "undamaged/attacks");
        s.squadDistress = true; // flick/flown every tick (bc5 whistle latch)
        std::vector<std::string> markers;
        for (int i = 0; i < 40; ++i) { // 2 s > 1 s timeout
            brain.update(0.05f, s);
            for (const std::string& m : brain.takeMarkers()) markers.push_back(m);
        }
        CHECK(hasMarker(markers, "AUTOPLAY_GIVEUP reason=attack_timeout"),
              "undamaged/whistle_still_times_out");
        CHECK(hasMarker(markers, "AUTOPLAY_RESULT target=670001"),
              "undamaged/whistle_timeout_scores_result");
    }
    // 2. Persistent distress gets throw windows (cooldown forces PadA).
    {
        p2autoplay::Config cfg;
        cfg.attackTimeout = 30.0f;
        cfg.whistleHold = 0.2f;
        cfg.whistleCooldown = 0.3f;
        cfg.throwHold = 0.1f;
        cfg.throwGap = 0.2f;
        p2autoplay::Brain brain(cfg);
        p2autoplay::Senses s = liveSenses();
        s.fieldPikmin = 20;
        brain.update(0.05f, s);
        brain.update(0.05f, s);
        s.targetToken = 670002;
        s.targetSource = 16; // Qurione
        s.targetAlive = true;
        s.targetDist = 47.0f;
        s.targetHealthFrac = 1.0f;
        brain.update(0.05f, s);
        brain.update(0.05f, s);
        s.scattered = true; // bc5 scat=1 latch
        int bOn = 0, aOn = 0;
        for (int i = 0; i < 60; ++i) {
            brain.update(0.05f, s);
            if (brain.command().buttons & unsigned(p2autoplay::PadB)) ++bOn;
            if (brain.command().buttons & unsigned(p2autoplay::PadA)) ++aOn;
            if (brain.current() != p2autoplay::State::Attack) break;
        }
        CHECK(bOn > 0, "undamaged/whistles_first");
        CHECK(aOn > 0, "undamaged/cooldown_forces_throws");
    }
    // 3. Far target in attack re-enters approach (chase fled/teleport).
    {
        p2autoplay::Config cfg;
        cfg.attackChaseDist = 500.0f;
        p2autoplay::Brain brain(cfg);
        p2autoplay::Senses s = liveSenses();
        s.fieldPikmin = 20;
        brain.update(0.05f, s);
        brain.update(0.05f, s);
        s.targetToken = 670003;
        s.targetSource = 38; // PanModoki (flees to nest)
        s.targetAlive = true;
        s.targetDist = 100.0f;
        s.targetHealthFrac = 1.0f;
        brain.update(0.05f, s); // -> approach
        brain.update(0.05f, s); // -> attack
        CHECK(brain.current() == p2autoplay::State::Attack, "undamaged/chase_starts_attack");
        s.targetDist = 1302.0f; // bc5 PanModoki end state
        brain.update(0.05f, s);
        CHECK(brain.current() == p2autoplay::State::Approach, "undamaged/far_reenters_approach");
    }
    // 4. Token switch with a latched kill scores the old kill first (bc5
    // 44/54: aftermath -> menu -> select picks the next token; the first
    // kill must emit RESULT damaged=1/killed=1 instead of being dropped).
    {
        p2autoplay::Config cfg;
        p2autoplay::Brain brain(cfg);
        p2autoplay::Senses s = liveSenses();
        s.fieldPikmin = 20;
        brain.update(0.05f, s);
        brain.update(0.05f, s); // -> select
        s.targetToken = 670004;
        s.targetSource = 44;
        s.targetAlive = true;
        s.targetDist = 100.0f;
        s.targetHealthFrac = 1.0f;
        brain.update(0.05f, s); // -> approach
        brain.update(0.05f, s); // -> attack
        s.targetHealthFrac = 0.5f;
        brain.update(0.05f, s);
        s.targetAlive = false; // kill
        brain.update(0.05f, s);
        CHECK(brain.current() == p2autoplay::State::Aftermath, "undamaged/switch_aftermath");
        // Driver switches to the next live token across a menu bounce.
        s.targetToken = 670005;
        s.targetSource = 44;
        s.targetAlive = true;
        s.targetDist = 900.0f;
        s.targetHealthFrac = 1.0f;
        s.targetDamagedLatch = false;
        s.targetDead = false;
        brain.update(0.05f, s); // select sees the new token? No: still aftermath.
        // Force the switch path: aftermath -> menu -> select -> new token.
        s.containerOpen = true;
        brain.update(0.05f, s);
        CHECK(brain.current() == p2autoplay::State::WithdrawMenu, "undamaged/switch_bounces_menu");
        for (int i = 0; i < 120 && brain.current() == p2autoplay::State::WithdrawMenu; ++i)
            brain.update(0.05f, s);
        s.containerOpen = false;
        s.onionStored = 0;
        for (int i = 0; i < 10 && brain.current() == p2autoplay::State::WithdrawMenu; ++i)
            brain.update(0.05f, s);
        // May go to Select (then score old kill on engaging the new token).
        std::vector<std::string> markers;
        for (int i = 0; i < 10; ++i) {
            brain.update(0.05f, s);
            for (const std::string& m : brain.takeMarkers()) markers.push_back(m);
            if (hasMarker(markers, "AUTOPLAY_RESULT target=670004")) break;
        }
        CHECK(hasMarker(markers, "AUTOPLAY_RESULT target=670004"), "undamaged/switch_scores_old_kill");
        CHECK(hasMarker(markers, "damaged=1"), "undamaged/switch_scores_damage");
    }
    setEnv("PIKMIN_RANDOMIZER_AUTOPLAY", nullptr);
}

void testUnkilledKoganeScope()
{
    // bot-unkilled (wf11): only source 9 is never-dies by design (finite
    // flip/escape, no health damage). Wealthy (10) and Fart (11) are plain
    // Chappy-host proxies that CAN die, so they must score kills.
    CHECK(p2autoplay::isKoganeLike(9), "unkilled/kogane9_like");
    CHECK(!p2autoplay::isKoganeLike(10), "unkilled/wealthy10_not_like");
    CHECK(!p2autoplay::isKoganeLike(11), "unkilled/fart11_not_like");
    CHECK(!p2autoplay::isKoganeLike(2), "unkilled/chappy2_not_like");
    // 10 kills and delivers: killed=1 carried=1 received=1.
    p2autoplay::Config cfg;
    cfg.receiptTimeout = 60.0f;
    cfg.aftermathTimeout = 60.0f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 80;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 1945764764u;
    s.targetSource = 10;
    s.targetAlive = true;
    s.targetDist = 100.0f;
    s.targetHealthFrac = 1.0f;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    s.targetHealthFrac = 0.5f;
    brain.update(0.05f, s);
    s.targetAlive = false;
    s.targetDead = true;
    s.transportSeen = true;
    s.carryCount = 3;
    s.receiptSeen = true;
    brain.update(0.05f, s); // -> aftermath
    CHECK(brain.current() == p2autoplay::State::Aftermath, "unkilled/wealthy_aftermath");
    std::vector<std::string> markers;
    for (int i = 0; i < 10 && brain.current() == p2autoplay::State::Aftermath; ++i) {
        brain.update(0.05f, s);
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(markers, "AUTOPLAY_RESULT target=1945764764 damaged=1 killed=1 carried=1"),
        "unkilled/wealthy_kill_scores");
}

void testUnkilledFlyers()
{
    // bot-unkilled (wf11): Demon (32) and OniKurage (72) are airborne and
    // must use the flyer approach range (throwRange, not 0.75x).
    CHECK(p2autoplay::isFlyer(23), "unkilled/sarai_flyer");
    CHECK(p2autoplay::isFlyer(57), "unkilled/kurage_flyer");
    CHECK(p2autoplay::isFlyer(32), "unkilled/demon_flyer");
    CHECK(p2autoplay::isFlyer(72), "unkilled/onikurage_flyer");
    CHECK(!p2autoplay::isFlyer(2), "unkilled/chappy_not_flyer");
}

void testUnkilledChaseWhenFar()
{
    // bot-unkilled (wf11): Attack at tdist > throwRange steers toward the
    // target with no whistle and no wasted throws, even when scattered or in
    // distress (Demon bc5: stationary PadB at 1200 u; OniKurage: throws from
    // 265 u while regen outpaces DPS).
    p2autoplay::Config cfg;
    cfg.throwRange = 260.0f;
    cfg.attackTimeout = 60.0f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 100;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 1945764764u;
    s.targetSource = 32;
    s.targetAlive = true;
    s.naviX = 0.0f;
    s.naviZ = 0.0f;
    s.tgtX = 1000.0f;
    s.tgtZ = 0.0f;
    s.targetDist = 1000.0f;
    s.scattered = true;
    s.squadDistress = true;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack (flyer range 260, but already attack?)
    // Force attack: within old 0.75x range would have entered; drive to attack.
    s.targetDist = 200.0f;
    brain.update(0.05f, s);
    CHECK(brain.current() == p2autoplay::State::Attack, "unkilled-chase/attacks");
    // Now flee far: must chase, not whistle/throw.
    s.targetDist = 1000.0f;
    s.tgtX = 1000.0f;
    brain.update(0.05f, s);
    const p2autoplay::Command cmd = brain.command();
    CHECK(!(cmd.buttons & unsigned(p2autoplay::PadB)), "unkilled-chase/no_whistle_when_far");
    CHECK(!(cmd.buttons & unsigned(p2autoplay::PadA)), "unkilled-chase/no_throw_when_far");
    CHECK(cmd.moveX > 0.5f, "unkilled-chase/steers_when_far");
    CHECK(brain.current() == p2autoplay::State::Attack, "unkilled-chase/stays_in_attack");
}

void testUnkilledOniKurageWindow()
{
    // bot-unkilled (wf11): OniKurage (72, 2000 HP + 1%/s regen) gets the
    // Kurage extended attack window and rotating throws.
    p2autoplay::Config cfg;
    cfg.attackTimeout = 1.0f;
    cfg.kurageAttackMultiplier = 3.0f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 100;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 1945764764u;
    s.targetSource = 72;
    s.targetAlive = true;
    s.targetDist = 100.0f;
    s.naviX = 0.0f;
    s.naviZ = 0.0f;
    s.tgtX = 100.0f;
    s.tgtZ = 0.0f;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    for (int i = 0; i < 30; ++i) brain.update(0.05f, s); // 1.5s > base 1.0s
    CHECK(brain.current() == p2autoplay::State::Attack, "unkilled-kurage/outlasts_base_timeout");
}

void testUnkilledWhistleTimeout()
{
    // bot-unkilled (wf11): permanent scatter/distress must not whistle past
    // the attack window with no RESULT (control Chappy unkilled-1 lock).
    p2autoplay::Config cfg;
    cfg.attackTimeout = 1.0f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 4;
    brain.update(0.05f, s);
    brain.update(0.05f, s); // -> select
    s.targetToken = 1945764764u;
    s.targetSource = 2;
    s.targetAlive = true;
    s.targetDist = 61.0f;
    s.naviX = 0.0f;
    s.naviZ = 0.0f;
    s.tgtX = 61.0f;
    s.tgtZ = 0.0f;
    s.scattered = true;
    s.squadDistress = true;
    brain.update(0.05f, s); // -> approach
    brain.update(0.05f, s); // -> attack
    std::vector<std::string> markers;
    for (int i = 0; i < 60; ++i) {
        brain.update(0.05f, s);
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(markers, "AUTOPLAY_GIVEUP reason=attack_timeout"), "unkilled-whistle/times_out");
    CHECK(hasMarker(markers, "AUTOPLAY_RESULT target=1945764764"), "unkilled-whistle/results");
}

} // namespace

// #884 round 4 helpers: drive a fresh Brain into Attack on a KingChappy.
p2autoplay::Senses kingSenses(unsigned source, float dist)
{
    p2autoplay::Senses s = liveSenses();
    s.fieldPikmin = 20;
    s.targetToken = 530053;
    s.targetSource = source;
    s.targetAlive = true;
    s.targetHealthFrac = 1.0f;
    s.tgtX = 0.0f;
    s.tgtZ = 0.0f;
    s.naviX = 0.0f;
    s.naviZ = dist;
    s.targetDist = dist;
    return s;
}

bool enterAttack(p2autoplay::Brain& brain, p2autoplay::Senses s)
{
    p2autoplay::Senses pre = liveSenses();
    pre.fieldPikmin = 20;
    brain.update(0.05f, pre); // idle -> withdraw_seek
    brain.update(0.05f, pre); // withdraw_seek -> select
    s.targetDist = 150.0f; // select -> approach -> attack (<= 195); the caller's copy keeps its distance
    s.naviZ = 150.0f;
    brain.update(0.05f, s);
    brain.update(0.05f, s);
    brain.takeMarkers();
    return brain.current() == p2autoplay::State::Attack;
}

void testKingStandoffPolicy()
{
    const p2autoplay::Config def;
    // Look band: <= 32 bytes (no MSTICK bits), |stick| = bytes / 74 inside
    // (mNeutralStickThreshold 0.1, mCursorMoveStickThreshold 0.75].
    const int lookBytes = int(def.lookStickScale * 127.0f);
    CHECK(lookBytes <= 32 && lookBytes / 74.0f > 0.1f && lookBytes / 74.0f <= 0.75f, "king/look_band_bytes");
    // Standoff band sits outside fp06 (80) and fp19 (60), inside fp20 (130).
    namespace K = p2chappymouth::king;
    CHECK(def.kingStandoffMin > K::InvisibleRange && def.kingStandoffMin > K::ShakeRange
              && def.kingStandoffMax < K::AttackRange && def.kingStandoffResume > def.kingStandoffMin
              && def.kingStandoffCloseStop < def.kingStandoffMax
              && def.kingStandoffCloseStop >= def.kingStandoffResume,
          "king/band_outside_fp06_inside_fp20");
    CHECK(p2autoplay::isKingStandoff(53) && !p2autoplay::isKingStandoff(2) && !p2autoplay::isKingStandoff(35)
              && !p2autoplay::isKingStandoff(76) && !p2autoplay::isKingStandoff(44),
          "king/only_source_53");

    p2autoplay::Config cfg;
    cfg.throwHold = 0.1f;
    cfg.throwGap = 0.2f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = kingSenses(53, 18.0f);
    CHECK(enterAttack(brain, s), "king/enters_attack");

    // Parked at 18 in front (i1-53): walk straight away, never throw.
    std::vector<std::string> markers;
    int aOn = 0;
    bool away = true, full = true;
    for (int i = 0; i < 20; ++i) {
        brain.update(0.05f, s);
        const p2autoplay::Command c = brain.command();
        if (c.buttons & unsigned(p2autoplay::PadA)) ++aOn;
        if (!(c.moveZ > 0.99f)) away = false; // navi at +z of the King: away = +z
        if (c.stickScale != 1.0f) full = false;
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(away && full, "king/backs_straight_away_inside_min");
    CHECK(aOn == 0, "king/no_throws_while_backing");
    CHECK(hasMarker(markers, "AUTOPLAY_KING_STANDOFF mode=back token=530053 dist=18"), "king/back_marker");

    // Still inside Resume (100): keeps backing (hysteresis).
    s.naviZ = s.targetDist = 100.0f;
    brain.update(0.05f, s);
    CHECK(brain.command().moveZ > 0.99f && !(brain.command().buttons & unsigned(p2autoplay::PadA)),
          "king/hysteresis_keeps_backing_below_resume");

    // In the band with the cursor behind the captain: look-band stick that
    // slides the cursor toward the King, throws pulse, captain stands.
    s.naviZ = s.targetDist = 112.0f;
    s.cursorValid = true;
    s.cursorX = 0.0f;
    s.cursorZ = 300.0f; // trailing behind after the back-off
    markers.clear();
    aOn = 0;
    bool look = true;
    for (int i = 0; i < 40; ++i) {
        brain.update(0.05f, s);
        const p2autoplay::Command c = brain.command();
        if (c.buttons & unsigned(p2autoplay::PadA)) ++aOn;
        if (!(c.stickScale == cfg.lookStickScale && c.moveZ < -0.99f)) look = false;
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(look, "king/hold_look_stick_moves_cursor_to_king");
    CHECK(aOn > 0 && aOn < 40, "king/hold_throw_pulses");
    CHECK(hasMarker(markers, "AUTOPLAY_KING_STANDOFF mode=hold"), "king/hold_marker");

    // Cursor on the King: neutral stick (cursor stays), throws continue.
    s.cursorZ = 8.0f;
    aOn = 0;
    bool neutral = true;
    for (int i = 0; i < 40; ++i) {
        brain.update(0.05f, s);
        const p2autoplay::Command c = brain.command();
        if (c.buttons & unsigned(p2autoplay::PadA)) ++aOn;
        if (c.moveX != 0.0f || c.moveZ != 0.0f) neutral = false;
    }
    CHECK(neutral && aOn > 0, "king/hold_neutral_when_cursor_on_king");

    // Without a cursor sense: look-steer at the King itself.
    s.cursorValid = false;
    brain.update(0.05f, s);
    CHECK(brain.command().stickScale == cfg.lookStickScale && brain.command().moveZ < -0.99f,
          "king/hold_without_cursor_looks_at_king");

    // Beyond Max: close in with a full stick and throw; stop closing at CloseStop.
    s.naviZ = s.targetDist = 160.0f;
    markers.clear();
    aOn = 0;
    bool in = true;
    for (int i = 0; i < 40; ++i) {
        brain.update(0.05f, s);
        const p2autoplay::Command c = brain.command();
        if (c.buttons & unsigned(p2autoplay::PadA)) ++aOn;
        if (!(c.stickScale == 1.0f && c.moveZ < -0.99f)) in = false;
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(in && aOn > 0, "king/close_full_stick_and_throw");
    CHECK(hasMarker(markers, "AUTOPLAY_KING_STANDOFF mode=close"), "king/close_marker");
    s.naviZ = s.targetDist = 120.0f; // between CloseStop and Max: still closing
    brain.update(0.05f, s);
    CHECK(brain.command().stickScale == 1.0f, "king/close_hysteresis");
    s.naviZ = s.targetDist = 114.0f;
    brain.update(0.05f, s);
    CHECK(brain.command().stickScale == cfg.lookStickScale, "king/close_stops_at_closestop");

    // Pinned (distance never grows): sidestep after kingSidestepAfter, side
    // swapping every window, still no throws.
    s.naviZ = s.targetDist = 30.0f;
    markers.clear();
    float sideX1 = 0.0f, sideX2 = 0.0f;
    aOn = 0;
    const int perWindow = int(cfg.kingSidestepAfter / 0.05f);
    for (int i = 0; i < perWindow * 3; ++i) {
        brain.update(0.05f, s);
        const p2autoplay::Command c = brain.command();
        if (c.buttons & unsigned(p2autoplay::PadA)) ++aOn;
        if (i == perWindow + 5) sideX1 = c.moveX;
        if (i == 2 * perWindow + 5) sideX2 = c.moveX;
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(hasMarker(markers, "AUTOPLAY_KING_STANDOFF mode=side"), "king/side_marker_when_pinned");
    CHECK(std::fabs(sideX1) > 0.5f && std::fabs(sideX2) > 0.5f && sideX1 * sideX2 < 0.0f,
          "king/side_swaps_each_window");
    CHECK(aOn == 0, "king/no_throws_while_sidestepping");

    // Other Chappy families at 18 keep the unchanged contact steer.
    const unsigned others[] = {2u, 35u, 76u, 44u};
    for (unsigned src : others) {
        p2autoplay::Brain b(cfg);
        p2autoplay::Senses o = kingSenses(src, 18.0f);
        enterAttack(b, o);
        std::vector<std::string> om;
        bool toward = true;
        for (int i = 0; i < 10; ++i) {
            b.update(0.05f, o);
            const p2autoplay::Command c = b.command();
            if (!(c.moveZ < -0.99f && c.stickScale == 1.0f)) toward = false;
            const std::vector<std::string> got = b.takeMarkers();
            om.insert(om.end(), got.begin(), got.end());
        }
        char name[96];
        std::snprintf(name, sizeof(name), "king/source_%u_keeps_contact_steer", src);
        CHECK(toward && !hasMarker(om, "AUTOPLAY_KING_STANDOFF"), name);
    }
}

// Coupled 30 fps simulation: the Brain drives a captain (walk 160 u/s at a
// full stick, stands in the look band, cursor slides at 200 u/s up to 300,
// body contact keeps him >= 18 from the King's centre) against the
// engine-free King model: searchTarget, walkTick pursuit at MoveSpeed,
// checkFlick (captain term, no hits), walkStateStep, a Flick pause of the
// flick.bca length (70 frames) with the frame-35 trample test, Turn by
// turnTick. Starts at the i1-53 geometry: captain parked 18 in front.
struct KingSimResult {
    int attackFrame = -1;
    int flicks = 0;
    int presses = 0;
    int naviNearFrames = 0;
    float distAtAttack = 0.0f;
};

KingSimResult runKingSim(bool standoff, int frameLimit)
{
    namespace K = p2chappymouth::king;
    p2autoplay::Config cfg;
    cfg.kingStandoff = standoff;
    cfg.attackTimeout = 1.0e6f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = kingSenses(53, 18.0f);
    enterAttack(brain, s);

    const float dt = 1.0f / 30.0f;
    p2chappymouth::Vec3 king{0.0f, 0.0f, 0.0f};
    float heading = 0.0f; // facing +z, toward the captain
    K::Walker walker;
    K::initWalker(walker, king);
    p2chappymouth::Vec3 navi{0.0f, 0.0f, 18.0f};
    float curX = 0.0f, curZ = -150.0f; // cursor ahead of a captain who walked in along -z
    float flickTimer = 0.0f;
    int kingState = 0; // 0 walk, 1 turn, 2 flick
    int flickFrame = 0;
    KingSimResult r;
    for (int f = 0; f < frameLimit; ++f) {
        // --- captain (Brain) ---
        s.naviX = navi.x;
        s.naviZ = navi.z;
        s.tgtX = king.x;
        s.tgtZ = king.z;
        s.targetDist = std::sqrt(K::sqrXZ(navi, king));
        s.cursorValid = true;
        s.cursorX = navi.x + curX;
        s.cursorZ = navi.z + curZ;
        brain.update(dt, s);
        const p2autoplay::Command c = brain.command();
        if (c.moveX != 0.0f || c.moveZ != 0.0f) {
            const float mag = c.stickScale * 127.0f / 74.0f;
            curX += c.moveX * 200.0f * dt;
            curZ += c.moveZ * 200.0f * dt;
            const float cl = std::sqrt(curX * curX + curZ * curZ);
            if (cl > 300.0f) {
                curX *= 300.0f / cl;
                curZ *= 300.0f / cl;
            }
            if (mag > 0.75f) { // walking; the look band stands still
                navi.x += c.moveX * 160.0f * dt;
                navi.z += c.moveZ * 160.0f * dt;
            }
        }
        // --- King ---
        const float nd = std::sqrt(K::sqrXZ(navi, king));
        if (nd < 18.0f) { // body contact
            const float k = nd > 0.01f ? 18.0f / nd : 1.0f;
            navi.x = king.x + (navi.x - king.x) * k;
            navi.z = king.z + (navi.z - king.z) * k;
        }
        if (K::naviInInvisibleRange(king, navi)) ++r.naviNearFrames;
        if (kingState == 2) {
            ++flickFrame;
            if (flickFrame == K::FlickEventFrame) {
                if (K::tramples(K::footPosition(king, heading), navi)) ++r.presses;
                flickTimer = 0.0f;
            }
            if (flickFrame >= 70) kingState = 0;
            continue;
        }
        const bool canSearch = K::canSearch(walker, king);
        const int pick = canSearch ? K::selectTarget(king, heading, &navi, nullptr, 0) : -1;
        const p2chappymouth::Vec3* target = pick == -2 ? &navi : nullptr;
        K::tickDelay(walker, 1.0f);
        if (kingState == 1) {
            const bool done = K::turnTick(heading, king, target ? *target : walker.goal, target != nullptr, 1.0f);
            const bool flick = K::checkFlick(flickTimer, K::naviInInvisibleRange(king, navi) ? 1 : 0, 0, 1.0f);
            const K::WalkNext next = K::turnStateStep(done, flick, false);
            if (next == K::NextFlick) {
                kingState = 2;
                flickFrame = 0;
                ++r.flicks;
            } else if (next == K::NextWalk) {
                kingState = 0;
            }
            continue;
        }
        K::WalkInputs in;
        in.walker = K::walkTick(walker, king, heading, target, 1.0f, 0.5f, 0.5f);
        in.hasTarget = target != nullptr;
        in.flickStart = in.walker != K::WalkTurn
            && K::checkFlick(flickTimer, K::naviInInvisibleRange(king, navi) ? 1 : 0, 0, 1.0f);
        in.inRange = target && !walker.targetDropped && K::attackGate(king, heading, *target);
        const K::WalkNext next = K::walkStateStep(in);
        if (next == K::NextAttack) {
            r.attackFrame = f;
            r.distAtAttack = std::sqrt(K::sqrXZ(navi, king));
            break;
        }
        if (next == K::NextFlick) {
            kingState = 2;
            flickFrame = 0;
            ++r.flicks;
            continue;
        }
        if (next == K::NextTurn) {
            kingState = 1;
            continue;
        }
        king.x += std::sin(heading) * K::MoveSpeed * dt;
        king.z += std::cos(heading) * K::MoveSpeed * dt;
    }
    return r;
}

void testKingStandoffOpensGate()
{
    // Without the stance: the i1-53 standoff. The captain stays at contact,
    // the gate never opens, and the King flicks and tramples him repeatedly.
    const KingSimResult old = runKingSim(false, 60 * 30);
    std::printf("INFO king_sim standoff=0 attack_frame=%d flicks=%d presses=%d navi_near_frames=%d\n",
                old.attackFrame, old.flicks, old.presses, old.naviNearFrames);
    CHECK(old.attackFrame < 0 && old.flicks >= 5 && old.presses >= 5,
          "king_sim/contact_steer_reproduces_standoff");

    // With the stance: the captain backs out of fp06 before the captain term
    // can start a flick, the King's checkAttack passes on him, no trample.
    const KingSimResult now = runKingSim(true, 60 * 30);
    std::printf("INFO king_sim standoff=1 attack_frame=%d flicks=%d presses=%d navi_near_frames=%d dist=%.1f\n",
                now.attackFrame, now.flicks, now.presses, now.naviNearFrames, now.distAtAttack);
    CHECK(now.attackFrame >= 0 && now.attackFrame < 5 * 30, "king_sim/stance_opens_attack_gate");
    CHECK(now.flicks == 0 && now.presses == 0, "king_sim/stance_no_flick_no_trample");
    CHECK(now.distAtAttack > p2chappymouth::king::InvisibleRange
              && now.distAtAttack < p2chappymouth::king::AttackRange,
          "king_sim/attack_on_captain_in_band");
    CHECK(now.naviNearFrames < 60, "king_sim/leaves_fp06_quickly");
}


// #884 round 5: the tongue evade and the low-health guard (policy level).
void testKingEvadePolicy()
{
    namespace K = p2chappymouth::king;
    const p2autoplay::Config def;
    const p2chappymouth::Profile* prof = p2chappymouth::profileForSource(53);
    const float reach = prof ? p2chappymouth::maxReach(*prof) : 1.0e9f;
    std::printf("INFO king_evade reach=%.1f clear=%.1f\n", reach, def.kingEvadeClear);
    // XZ outside the farthest slot centre + slot radius cannot touch any
    // slot sphere at any height (3D >= XZ).
    CHECK(prof && def.kingEvadeClear > reach && def.kingEvadeClear > K::AttackRange, "king_evade/clear_beyond_reach");
    // From the band edge the walk out (160 u/s, conservative vs p04 170)
    // finishes before the first slot frame (40 of attack.bca at 30 fps).
    CHECK(prof && (def.kingEvadeClear - def.kingStandoffMax) / 160.0f * 30.0f < float(prof->firstFrame) * 0.5f,
          "king_evade/walk_out_before_first_slot_frame");

    p2autoplay::Config cfg;
    cfg.throwHold = 0.1f;
    cfg.throwGap = 0.2f;
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = kingSenses(53, 113.0f);
    s.cursorValid = true;
    s.cursorX = 0.0f;
    s.cursorZ = 0.0f; // cursor already on the King: hold is neutral
    s.naviHpValid = true;
    s.naviHp = 100.0f;
    CHECK(enterAttack(brain, s), "king_evade/enters_attack");
    for (int i = 0; i < 10; ++i) brain.update(0.05f, s);
    brain.takeMarkers();
    CHECK(brain.command().moveX == 0.0f && brain.command().moveZ == 0.0f, "king_evade/holds_in_band_before_attack");

    // The King commits to an attack: walk straight out at a full stick, no
    // throws, one evade marker carrying king_attack=1.
    s.targetAttacking = true;
    std::vector<std::string> markers;
    int aOn = 0;
    bool out = true;
    for (int i = 0; i < 8; ++i) {
        brain.update(0.05f, s);
        const p2autoplay::Command c = brain.command();
        if (c.buttons & unsigned(p2autoplay::PadA)) ++aOn;
        if (!(c.moveZ > 0.99f && c.stickScale == 1.0f)) out = false;
        const std::vector<std::string> got = brain.takeMarkers();
        markers.insert(markers.end(), got.begin(), got.end());
    }
    CHECK(out, "king_evade/walks_out_of_the_sweep");
    CHECK(aOn == 0, "king_evade/no_throws_while_walking_out");
    CHECK(hasMarker(markers, "AUTOPLAY_KING_STANDOFF mode=evade token=530053 dist=113")
              && hasMarker(markers, "king_attack=1 navi_hp=100 low_hp=0"),
          "king_evade/evade_marker");

    // Pinned inside Clear past kingEvadeSideAfter: away + 45 degrees.
    for (int i = 0; i < int(cfg.kingEvadeSideAfter / 0.05f) + 2; ++i) brain.update(0.05f, s);
    CHECK(std::fabs(brain.command().moveX) > 0.5f && brain.command().moveZ > 0.5f, "king_evade/pinned_sidesteps");

    // Outside Clear while the attack lasts: stand (look band) and throw; do
    // NOT walk back in (the band's close mode would).
    s.naviZ = s.targetDist = def.kingEvadeClear + 5.0f;
    s.cursorZ = s.naviZ; // cursor at the captain: look-steer it toward the King
    aOn = 0;
    bool stands = true;
    for (int i = 0; i < 40; ++i) {
        brain.update(0.05f, s);
        const p2autoplay::Command c = brain.command();
        if (c.buttons & unsigned(p2autoplay::PadA)) ++aOn;
        if (c.stickScale != cfg.lookStickScale) stands = false;
    }
    CHECK(stands && aOn > 0, "king_evade/outside_clear_stands_and_throws");

    // Attack over: the band takes over again (close in from Clear+5).
    s.targetAttacking = false;
    markers.clear();
    brain.update(0.05f, s);
    markers = brain.takeMarkers();
    CHECK(brain.command().stickScale == 1.0f && brain.command().moveZ < -0.99f
              && hasMarker(markers, "AUTOPLAY_KING_STANDOFF mode=close"),
          "king_evade/attack_over_closes_in");

    // The evade overrides back/side too (attack sensed while backing).
    s.naviZ = s.targetDist = 90.0f;
    brain.update(0.05f, s); // back
    s.targetAttacking = true;
    brain.update(0.05f, s);
    markers = brain.takeMarkers();
    CHECK(hasMarker(markers, "mode=evade") && brain.command().moveZ > 0.99f, "king_evade/overrides_back");
    s.targetAttacking = false;

    // Low-health guard: at or below kingLowHp the band is [Clear, Clear+30].
    p2autoplay::Brain low(cfg);
    p2autoplay::Senses l = kingSenses(53, 150.0f);
    l.naviHpValid = true;
    l.naviHp = cfg.kingLowHp;
    l.cursorValid = true;
    l.cursorX = 0.0f;
    l.cursorZ = 0.0f;
    enterAttack(low, l);
    low.update(0.05f, l);
    markers = low.takeMarkers();
    CHECK(low.command().moveZ > 0.99f && hasMarker(markers, "mode=back") && hasMarker(markers, "low_hp=1"),
          "king_evade/low_hp_backs_out_of_fp20");
    l.naviZ = l.targetDist = cfg.kingEvadeClear + 20.0f;
    for (int i = 0; i < 5; ++i) low.update(0.05f, l);
    CHECK(low.command().moveX == 0.0f && low.command().moveZ == 0.0f, "king_evade/low_hp_holds_outside_clear");
    l.naviHp = 100.0f; // healthy again (e.g. a new sortie): the normal band
    l.naviZ = l.targetDist = 150.0f;
    low.update(0.05f, l);
    markers = low.takeMarkers();
    CHECK(low.command().moveZ < -0.99f && hasMarker(markers, "mode=close") && hasMarker(markers, "low_hp=0"),
          "king_evade/healthy_band_closes_at_150");

    // Other Chappy families: the attack sense changes nothing (contact steer).
    const unsigned others[] = {2u, 35u, 76u, 44u};
    for (unsigned src : others) {
        p2autoplay::Brain b(cfg);
        p2autoplay::Senses o = kingSenses(src, 113.0f);
        o.targetAttacking = true;
        o.naviHpValid = true;
        o.naviHp = 10.0f;
        enterAttack(b, o);
        bool toward = true;
        std::vector<std::string> om;
        for (int i = 0; i < 10; ++i) {
            b.update(0.05f, o);
            if (!(b.command().moveZ < -0.99f && b.command().stickScale == 1.0f)) toward = false;
            const std::vector<std::string> got = b.takeMarkers();
            om.insert(om.end(), got.begin(), got.end());
        }
        char name[96];
        std::snprintf(name, sizeof(name), "king_evade/source_%u_ignores_attack_sense", src);
        CHECK(toward && !hasMarker(om, "AUTOPLAY_KING_STANDOFF"), name);
    }
}

// #884 round 5: the coupled simulation continued through repeated attacks.
// Same captain and King model as runKingSim, plus: StateAttack (attack.bca,
// 95 frames, the King stopped) with the per-frame kamu1..9 slot-sphere test
// against the captain (port kingNaviContact; one bite per attack counted,
// 5 HP, attackDamage of the King row), the flick trample (InteractPress 5 HP)
// and optional hits from Pikmin stuck to the King feeding FlickPerHit. The
// Brain senses the King's attack state and the captain's health. Captain HP
// starts at `hp` (Olimar 100, no regen).
struct KingLongResult {
    int attacks = 0;
    int bitten = 0;
    int presses = 0;
    int flicks = 0;
    int evades = 0;
    float hp = 0.0f;
    float minDist = 1.0e9f;
};

KingLongResult runKingLongSim(bool evade, int seconds, float hp, float hitsPerSecond)
{
    namespace K = p2chappymouth::king;
    const p2chappymouth::Profile* prof = p2chappymouth::profileForSource(53);
    p2autoplay::Config cfg;
    cfg.attackTimeout = 1.0e6f;
    cfg.kingEvade = evade;
    if (!evade) cfg.kingLowHp = 0.0f; // the eeb71a4d4 stance
    p2autoplay::Brain brain(cfg);
    p2autoplay::Senses s = kingSenses(53, 18.0f);
    enterAttack(brain, s);
    const float dt = 1.0f / 30.0f;
    p2chappymouth::Vec3 king{0.0f, 0.0f, 0.0f};
    float heading = 0.0f;
    K::Walker walker;
    K::initWalker(walker, king);
    p2chappymouth::Vec3 navi{0.0f, 0.0f, 18.0f};
    float curX = 0.0f, curZ = -150.0f;
    float flickTimer = 0.0f;
    int kingState = 0; // 0 walk, 1 turn, 2 flick, 3 attack
    int stateFrame = 0;
    bool bitThisAttack = false;
    float hitAcc = 0.0f;
    KingLongResult r;
    r.hp = hp;
    for (int f = 0; f < seconds * 30; ++f) {
        s.naviX = navi.x;
        s.naviZ = navi.z;
        s.tgtX = king.x;
        s.tgtZ = king.z;
        s.targetDist = std::sqrt(K::sqrXZ(navi, king));
        s.cursorValid = true;
        s.cursorX = navi.x + curX;
        s.cursorZ = navi.z + curZ;
        s.targetAttacking = kingState == 3;
        s.naviHpValid = true;
        s.naviHp = r.hp;
        brain.update(dt, s);
        const p2autoplay::Command c = brain.command();
        for (const std::string& m : brain.takeMarkers()) {
            if (m.find("mode=evade") != std::string::npos) ++r.evades;
        }
        if (c.moveX != 0.0f || c.moveZ != 0.0f) {
            const float mag = c.stickScale * 127.0f / 74.0f;
            curX += c.moveX * 200.0f * dt;
            curZ += c.moveZ * 200.0f * dt;
            const float cl = std::sqrt(curX * curX + curZ * curZ);
            if (cl > 300.0f) {
                curX *= 300.0f / cl;
                curZ *= 300.0f / cl;
            }
            if (mag > 0.75f) {
                navi.x += c.moveX * 160.0f * dt;
                navi.z += c.moveZ * 160.0f * dt;
            }
        }
        const float nd = std::sqrt(K::sqrXZ(navi, king));
        if (nd < 18.0f) {
            const float k = nd > 0.01f ? 18.0f / nd : 1.0f;
            navi.x = king.x + (navi.x - king.x) * k;
            navi.z = king.z + (navi.z - king.z) * k;
        }
        if (f > 60) r.minDist = std::min(r.minDist, nd);
        // Hits from latched Pikmin (addDamage flickSpeed, every state).
        hitAcc += hitsPerSecond * dt;
        while (hitAcc >= 1.0f) {
            hitAcc -= 1.0f;
            flickTimer += K::FlickPerHit;
        }
        if (kingState == 2) {
            ++stateFrame;
            if (stateFrame == K::FlickEventFrame) {
                if (K::tramples(K::footPosition(king, heading), navi)) {
                    ++r.presses;
                    r.hp -= 5.0f;
                }
                flickTimer = 0.0f;
            }
            if (stateFrame >= 70) kingState = 0;
            continue;
        }
        if (kingState == 3) {
            ++stateFrame;
            if (prof && stateFrame >= prof->firstFrame && stateFrame <= prof->lastFrame) {
                for (int i = 0; i < prof->slots; ++i) {
                    const p2chappymouth::Vec3 sw = p2chappymouth::slotWorld(*prof, stateFrame, i, king, heading);
                    if (p2chappymouth::distance(sw, navi) < p2chappymouth::effectiveRadius(*prof)) {
                        if (!bitThisAttack) r.hp -= 5.0f;
                        bitThisAttack = true;
                    }
                }
            }
            if (stateFrame >= 95) {
                ++r.attacks;
                if (bitThisAttack) ++r.bitten;
                kingState = 0;
            }
            continue;
        }
        const bool canSearch = K::canSearch(walker, king);
        const int pick = canSearch ? K::selectTarget(king, heading, &navi, nullptr, 0) : -1;
        const p2chappymouth::Vec3* target = pick == -2 ? &navi : nullptr;
        K::tickDelay(walker, 1.0f);
        if (kingState == 1) {
            const bool done = K::turnTick(heading, king, target ? *target : walker.goal, target != nullptr, 1.0f);
            const bool flick = K::checkFlick(flickTimer, K::naviInInvisibleRange(king, navi) ? 1 : 0, 0, 1.0f);
            const K::WalkNext next = K::turnStateStep(done, flick, false);
            if (next == K::NextFlick) {
                kingState = 2;
                stateFrame = 0;
                ++r.flicks;
            } else if (next == K::NextWalk) {
                kingState = 0;
            }
            continue;
        }
        K::WalkInputs in;
        in.walker = K::walkTick(walker, king, heading, target, 1.0f, 0.5f, 0.5f);
        in.hasTarget = target != nullptr;
        in.flickStart = in.walker != K::WalkTurn
            && K::checkFlick(flickTimer, K::naviInInvisibleRange(king, navi) ? 1 : 0, 0, 1.0f);
        in.inRange = target && !walker.targetDropped && K::attackGate(king, heading, *target);
        const K::WalkNext next = K::walkStateStep(in);
        if (next == K::NextAttack) {
            kingState = 3;
            stateFrame = 0;
            bitThisAttack = false;
            continue;
        }
        if (next == K::NextFlick) {
            kingState = 2;
            stateFrame = 0;
            ++r.flicks;
            continue;
        }
        if (next == K::NextTurn) {
            kingState = 1;
            continue;
        }
        king.x += std::sin(heading) * K::MoveSpeed * dt;
        king.z += std::cos(heading) * K::MoveSpeed * dt;
    }
    return r;
}

void testKingEvadeLongSim()
{
    const int secs = 75; // the i1-53 fight length (AUTOPLAY_RESULT seconds=75)
    // The eeb71a4d4 stance (no evade): bitten on every attack.
    const KingLongResult old = runKingLongSim(false, secs, 100.0f, 0.0f);
    std::printf("INFO king_long evade=0 attacks=%d bitten=%d presses=%d flicks=%d hp=%.0f min_dist=%.0f\n",
                old.attacks, old.bitten, old.presses, old.flicks, old.hp, old.minDist);
    CHECK(old.attacks >= 10 && old.bitten >= old.attacks - 1, "king_long/hold_without_evade_is_bitten");

    const float rates[] = {0.0f, 0.5f, 1.0f};
    for (float hps : rates) {
        const KingLongResult now = runKingLongSim(true, secs, 100.0f, hps);
        std::printf("INFO king_long evade=1 hits_per_s=%.1f attacks=%d bitten=%d presses=%d flicks=%d evades=%d "
                    "hp=%.0f min_dist=%.0f\n",
                    hps, now.attacks, now.bitten, now.presses, now.flicks, now.evades, now.hp, now.minDist);
        char name[96];
        std::snprintf(name, sizeof(name), "king_long/evade_hits_%.1f_no_captain_damage", hps);
        // Bound: <= 5 HP of captain damage per minute (one bite); the model
        // predicts 0.
        CHECK(now.bitten == 0 && now.presses == 0 && now.hp >= 100.0f - 5.0f * secs / 60.0f, name);
        std::snprintf(name, sizeof(name), "king_long/evade_hits_%.1f_king_keeps_attacking", hps);
        CHECK(now.attacks >= 10 && now.evades >= now.attacks, name);
    }

    // Low health: the captain stays out of fp20 and the tongue; no damage.
    const KingLongResult low = runKingLongSim(true, secs, 30.0f, 0.0f);
    std::printf("INFO king_long low_hp=30 attacks=%d bitten=%d presses=%d flicks=%d hp=%.0f min_dist=%.0f\n",
                low.attacks, low.bitten, low.presses, low.flicks, low.hp, low.minDist);
    CHECK(low.bitten == 0 && low.presses == 0 && low.hp >= 30.0f, "king_long/low_hp_no_damage");
}

int main()
{
    testGate();
    testInertWhenUnset();
    testWithdrawFlow();
    testWithdrawKeepsClosing();
    testWithdrawMenuHoldThenConfirm();
    testCombatFlow();
    testKoganeMovesOn();
    testTimeoutsAndStuck();
    testTargetMatching();
    testKoganePathNeedsEngagement();
    testReceiptWait();
    testGenericDeath();
    testWithdrawRepeat();
    testSaraiFlyer();
    testKurageLongAttack();
    testReplanRepeats();
    testStuckCarriesNaviPos();
    testUnreachableGiveup();
    testContainerGuards();
    testDoneIdlesNearOnion();
    testPowerGate();
    testRegroupDistress();
    testResupply();
    testAftermathEscortExtension();
    testAftermathNoWhistle();
    testAftermathSeedBackoffRethrow();
    testAftermathEscortNoThrows();
    testAftermathGiveupReasons();
    testReceiptPerTokenOnly();
    testAftermathStallRethrow();
    testAftermathGrowKeepsSeeding();
    testAftermathReseedOnShrink();
    testAftermathUnknownWantEscorts();
    testPowerFastSquad();
    testSelectTargetGone();
    testUndamagedAttack();
    testUnkilledKoganeScope();
    testUnkilledFlyers();
    testUnkilledChaseWhenFar();
    testUnkilledOniKurageWindow();
    testUnkilledWhistleTimeout();
    testKingStandoffPolicy();
    testKingStandoffOpensGate();
    testKingEvadePolicy();
    testKingEvadeLongSim();
    if (failures == 0) {
        std::printf("PASS p2_autoplay\n");
        return 0;
    }
    std::printf("FAIL p2_autoplay failures=%d\n", failures);
    return 1;
}
