// Sarai23 campaign targeting/reacquisition regression test (#834).
//
// Engine-free proof over the REAL shipped headers: pc_p2_sarai_policy.h
// (retail target geometry), pc_p2_sarai_capture.h (mouth admission +
// nearest-first selection + FallMeck receivers), pc_p2_sarai_fsm.h (bounded
// Wait/Move/Attack/CatchFly/FallMeck reacquisition), the REAL
// pc_p2_sarai_capture_bridge.cpp against stub engine headers (BEFORE pc_port,
// same technique as p2_sarai_campaign_test), and pc_randomizer_p2_roster.h
// (source-23 delivery binding unchanged). No engine is booted, no
// health/state is written, no Transport is assigned, no captain exists here.
//
// What regressed (#834 evidence campaign-g4-01 .../native.log): eight
// campaign Sarai shared one room-wide capture territory, scanned ONLY the
// captain (retail getAttackableTarget scans pikiMgr Pikmin and never
// captains), and re-acquired instantly after every drop (no FallMeck
// attackable-timer gap) until captain-down at tick 5139 with zero
// throws/damage. The production fix lives in pc_p2_sarai_host.{h,cpp}
// (Pikmin-first scan, captain fallback only for zero-Pikmin rooms,
// post-drop cooldown) and pc_p2_sarai_manager.cpp (retail-scale campaign
// geometry). This test pins the contracts that fix relies on:
//
//   1. Retail eligibility: territory / view-half-angle / sight gates plus
//      alive/Pikmin/not-mouth-stuck/not-self-stuck filters; a captain-shaped
//      candidate (isPikmin=false) is never targetable.
//   2. Nearest-first mouth selection spreads multiple Sarai across the squad.
//   3. Bounded reacquisition at FSM level: lost target -> Move, Attack miss ->
//      Move, empty CatchFly -> Move, FallMeck END -> Move; catch attempts only
//      inside 16 < frame <= 30.
//   4. Drop/flick receivers: FallMeck damage default 10, release velocity -200,
//      escape flick harmless, dead captives detached without damage.
//   5. Teardown (owner_lost / scene_exit / forget) strands nothing.
//   6. Source-23 delivery binding unchanged: roster bindable(23), not 0.
//
// Optional log mode: p2_sarai_campaign_behavior_test <native.log> verifies a
// campaign-behavior run: READY + DELIVERY_BIND present, GEOMETRY campaign
// marker with the retail-scale values (territory=200 view=90 sight=200),
// ZERO captain P2_SARAI_CAPTURE markers, no P2_FIXTURE_CAPTAIN_DOWN, no
// injected markers, and host P2_SARAI_CARRY census lines (carriage +
// cooldown fields).
// Pikmin capture/drop counts are reported, never required: a bounded run may
// legitimately end before contact.
//
// Exit 0 only if every check passes; any failure prints FAIL and exits 1.
#include "Piki.h"
#include "Collision.h"
#include "pc_p2_sarai_capture.h"
#include "pc_p2_sarai_capture_bridge.h"
#include "pc_p2_sarai_fsm.h"
#include "pc_p2_sarai_policy.h"
#include "pc_randomizer_p2_roster.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>

namespace {

int failures = 0;

#define CHECK(cond, name) do { \
    if (cond) { std::printf("PASS %s\n", name); } \
    else { std::printf("FAIL %s\n", name); ++failures; } \
} while (0)

using namespace p2sarai;

TargetQuery query(float homeSq, float territory, float viewDeg, float sight)
{
    TargetQuery q;
    q.sqrDistToHome = homeSq;
    q.territoryRadius = territory;
    q.viewAngleDeg = viewDeg;
    q.sightRadius = sight;
    return q;
}

TargetCandidate candidate(float angleRad, float sqrDistXZ)
{
    TargetCandidate c;
    c.alive = true;
    c.isPikmin = true;
    c.stickToMouth = false;
    c.stickerIsSelf = false;
    c.floorTriangle = true;
    c.angleRad = angleRad;
    c.sqrDistXZ = sqrDistXZ;
    return c;
}

int countToken(const std::string& text, const std::string& token)
{
    int n = 0;
    for (size_t at = 0; (at = text.find(token, at)) != std::string::npos; ++at) ++n;
    return n;
}

// Campaign-behavior log check (see file header for the contract).
int checkBehaviorLog(const char* logPath)
{
    std::ifstream in(logPath);
    if (!in) {
        std::printf("FAIL log-open path=%s\n", logPath);
        return 1;
    }
    const std::string text((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());

    static const char* const kInjected[] = {
        "P2_SARAI_INJECT", "P2_LIFECYCLE_INJECT", "injected_health", "mHealth=",
        "InteractAttack", "not_natural_combat=1",
    };
    for (const char* token : kInjected) {
        if (text.find(token) != std::string::npos) {
            std::printf("FAIL log-injected token=%s\n", token);
            return 1;
        }
    }
    if (text.find("P2_SARAI_READY source_id=23") == std::string::npos) {
        std::printf("FAIL log-missing-ready\n");
        return 1;
    }
    if (text.find("P2_SARAI_DELIVERY_BIND generator=") == std::string::npos) {
        std::printf("FAIL log-missing-delivery-bind\n");
        return 1;
    }
    // Retail-scale campaign geometry must be the bound one (#834: the
    // room-wide 1000/360/1200 accommodation caused the eight-Sarai overlap).
    if (text.find("P2_SARAI_GEOMETRY mode=campaign territory=200 view=90 sight=200") == std::string::npos) {
        std::printf("FAIL log-missing-campaign-geometry\n");
        return 1;
    }
    // The defect signature: any captain capture re-opens #834.
    const int captainCaptures = countToken(text, "P2_SARAI_CAPTURE source_id=23");
    if (captainCaptures != 0) {
        std::printf("FAIL log-captain-capture count=%d\n", captainCaptures);
        return 1;
    }
    if (text.find("P2_FIXTURE_CAPTAIN_DOWN") != std::string::npos) {
        std::printf("FAIL log-captain-down\n");
        return 1;
    }
    if (text.find("P2_SARAI_CARRY ") == std::string::npos) {
        std::printf("FAIL log-missing-carriage-census\n");
        return 1;
    }
    const int pikminCaptures = countToken(text, "P2_SARAI_PIKMIN_CAPTURE ");
    const int pikminDrops = countToken(text, "P2_SARAI_PIKMIN_DROP ");
    std::printf("PASS P2_SARAI_CAMPAIGN_BEHAVIOR_LOG geometry=campaign captain_captures=0 pikmin_captures=%d pikmin_drops=%d\n",
                pikminCaptures, pikminDrops);
    return 0;
}

Fsm freshFsm()
{
    Fsm fsm;
    fsm.spawn(0.1f);
    return fsm;
}

In tickIn()
{
    In in;
    in.deltaTime = 1.0f / 30.0f;
    in.health = 100.0f;
    in.bodyStuckCount = 0;
    in.mouthCarried = 0;
    in.purpleLatched = false;
    in.mapY = 0.0f;
    in.positionY = 100.0f;
    in.targetPresent = false;
    in.hasTargetCreature = false;
    in.targetFrame = 0.0f;
    in.distToPatrolTargetXZ = 1.0e9f;
    in.keyEvent = KeyEvent::None;
    in.motionFinished = false;
    in.randomUnit = 0.5f;
    return in;
}

} // namespace

int main(int argc, char** argv)
{
    // --- 1. Retail target eligibility (Sarai.cpp getAttackableTarget) ------
    {
        // Inside territory (home 100 < 200), centered, close: eligible.
        CHECK(targetable(query(100.0f * 100.0f, 200.0f, 90.0f, 200.0f), candidate(0.0f, 50.0f * 50.0f)),
            "retail-centered-pikmin-targetable");
        // Territory gate: at/over the radius nothing is scanned.
        CHECK(!targetable(query(200.0f * 200.0f, 200.0f, 90.0f, 200.0f), candidate(0.0f, 10.0f)),
            "retail-territory-edge-refused");
        CHECK(!targetable(query(500.0f * 500.0f, 200.0f, 90.0f, 200.0f), candidate(0.0f, 10.0f)),
            "retail-outside-territory-refused");
        // Sight gate.
        CHECK(!targetable(query(0.0f, 200.0f, 90.0f, 200.0f), candidate(0.0f, 200.0f * 200.0f)),
            "retail-outside-sight-refused");
        // View half-angle gate (narrow view so the gate discriminates:
        // half = PI * DEG2RAD * 10 ~= 0.548 rad).
        CHECK(targetable(query(0.0f, 200.0f, 10.0f, 200.0f), candidate(0.4f, 50.0f * 50.0f)),
            "retail-inside-view-admitted");
        CHECK(!targetable(query(0.0f, 200.0f, 10.0f, 200.0f), candidate(0.7f, 50.0f * 50.0f)),
            "retail-outside-view-refused");
        CHECK(!targetable(query(0.0f, 200.0f, 10.0f, 200.0f), candidate(-0.7f, 50.0f * 50.0f)),
            "retail-outside-view-negative-refused");
        // Candidate filters.
        TargetCandidate dead = candidate(0.0f, 10.0f);
        dead.alive = false;
        CHECK(!targetable(query(0.0f, 200.0f, 90.0f, 200.0f), dead), "retail-dead-refused");
        TargetCandidate mouth = candidate(0.0f, 10.0f);
        mouth.stickToMouth = true;
        CHECK(!targetable(query(0.0f, 200.0f, 90.0f, 200.0f), mouth), "retail-mouth-stuck-refused");
        TargetCandidate self = candidate(0.0f, 10.0f);
        self.stickerIsSelf = true;
        CHECK(!targetable(query(0.0f, 200.0f, 90.0f, 200.0f), self), "retail-self-stuck-refused");
        // Captain safety at policy level: a non-Pikmin candidate (the
        // captain) is never targetable, however close and centered.
        TargetCandidate captain = candidate(0.0f, 1.0f);
        captain.isPikmin = false;
        CHECK(!targetable(query(0.0f, 200.0f, 90.0f, 200.0f), captain), "retail-captain-never-targetable");
    }

    // --- 2. Nearest-first mouth selection (multiple Sarai spread) ----------
    {
        MouthCandidate cands[3];
        cands[0].withinMouthRadius = true;   // far but eligible
        cands[1].withinMouthRadius = true;   // nearest eligible
        cands[2].withinMouthRadius = false;  // nearest overall, out of mouth radius
        const float dists[3] = {100.0f, 25.0f, 1.0f};
        int chosen[2] = {-1, -1};
        CHECK(selectMouthCaptures(cands, 3, dists, chosen) == 2, "select-two-slots");
        CHECK(chosen[0] == 1 && chosen[1] == 0, "select-nearest-first-skips-ineligible");
        // A mouth-stuck Pikmin is skipped so two Sarai cannot hold one.
        MouthCandidate held[2];
        held[0].stuckToMouth = true;
        const float dists2[2] = {1.0f, 100.0f};
        int chosen2[2] = {-1, -1};
        CHECK(selectMouthCaptures(held, 2, dists2, chosen2) == 1 && chosen2[0] == 1,
            "select-skips-mouth-held");
        CHECK(selectMouthCaptures(nullptr, 0, nullptr, nullptr) == 0, "select-fail-closed");
    }

    // --- 3. Bounded reacquisition (FSM level) ------------------------------
    {
        // Lost target aborts Attack back to Move (no stickiness).
        Fsm fsm = freshFsm();
        fsm.forceState(State::Attack, 0.1f);
        In in = tickIn();
        in.hasTargetCreature = false;
        CHECK(fsm.tick(in).state == State::Move, "fsm-attack-lost-target-moves");
        // Attack END with no catch returns to Move (miss -> rescan).
        Fsm miss = freshFsm();
        miss.forceState(State::Attack, 0.1f);
        In missIn = tickIn();
        missIn.hasTargetCreature = true;
        missIn.targetFrame = 40.0f;
        missIn.mouthCarried = 0;
        missIn.motionFinished = true;
        CHECK(miss.tick(missIn).state == State::Move, "fsm-attack-miss-moves");
        // Attack END with a catch reaches CatchFly (success path intact).
        Fsm hit = freshFsm();
        hit.forceState(State::Attack, 0.1f);
        In hitIn = tickIn();
        hitIn.hasTargetCreature = true;
        hitIn.targetFrame = 40.0f;
        hitIn.mouthCarried = 1;
        hitIn.motionFinished = true;
        CHECK(hit.tick(hitIn).state == State::CatchFly, "fsm-attack-hit-catchfly");
        // Empty CatchFly returns to Move (lost captive -> rescan).
        Fsm empty = freshFsm();
        empty.forceState(State::CatchFly, 0.1f);
        In emptyIn = tickIn();
        emptyIn.mouthCarried = 0;
        CHECK(empty.tick(emptyIn).state == State::Move, "fsm-empty-catchfly-moves");
        // FallMeck END returns to Move (post-drop -> rescan, host cooldown
        // on top in production code).
        Fsm drop = freshFsm();
        drop.forceState(State::FallMeck, 0.1f);
        In dropIn = tickIn();
        dropIn.keyEvent = KeyEvent::Key3;
        Out dropOut = drop.tick(dropIn);
        CHECK(dropOut.drop, "fsm-fallmeck-key3-drops");
        dropIn.keyEvent = KeyEvent::None;
        dropIn.motionFinished = true;
        CHECK(drop.tick(dropIn).state == State::Move, "fsm-fallmeck-end-moves");
        // Catch window only past frame 16 and at most 30.
        Fsm win = freshFsm();
        win.forceState(State::Attack, 0.1f);
        In winIn = tickIn();
        winIn.hasTargetCreature = true;
        winIn.targetFrame = 16.0f;
        CHECK(!win.tick(winIn).attemptCatch, "fsm-catch-closed-at-16");
        winIn.targetFrame = 20.0f;
        CHECK(win.tick(winIn).attemptCatch, "fsm-catch-open-past-16");
        winIn.targetFrame = 31.0f;
        CHECK(!win.tick(winIn).attemptCatch, "fsm-catch-closed-past-30");
        // Dead/Fall/Damage entry flicks (mouth release on the way down: the
        // flag fires on the transition tick into Fall, not steady-state).
        Fsm dying = freshFsm();
        dying.forceState(State::TakeOff, 0.1f);
        In dyingIn = tickIn();
        dyingIn.health = 0.0f;
        dyingIn.motionFinished = true;
        Out dyingOut = dying.tick(dyingIn);
        CHECK(dyingOut.state == State::Fall && dyingOut.flickAttackers, "fsm-fall-entry-flicks");
    }

    // --- 4. Drop/flick receivers (capture.h constants the host calls) ------
    {
        CHECK(fallMeckDamage(10.0f) == 10.0f, "receiver-fallmeck-damage");
        CHECK(fallMeckReleaseVelocity(200.0f) == -200.0f, "receiver-fallmeck-velocity");
        CHECK(kFlickDamage == 0.0f, "receiver-flick-harmless");
        CHECK(kMouthSlots == 2 && kMouthRadius == 15.0f, "receiver-two-mouths-radius-15");
        MouthCandidate ok;
        CHECK(captureEligible(ok), "receiver-eligible-admitted");
        MouthCandidate stuck;
        stuck.stuckToMouth = true;
        CHECK(!captureEligible(stuck), "receiver-mouth-held-refused");
    }

    // --- 5. Bridge teardown (real bridge, stub engine) ---------------------
    {
        Creature host;
        CollPart mouthA, mouthB;
        mouthA.mPartType = PART_BoundSphere;
        mouthA.mRadius = kMouthRadius;
        mouthB.mPartType = PART_BoundSphere;
        mouthB.mRadius = kMouthRadius;
        const std::uint64_t token = 424242u;
        pc_p2_sarai_forget();
        Piki piki;
        CHECK(pc_p2_sarai_piki_capture(&piki, &host, &mouthA, token, 0), "bridge-capture");
        pc_p2_sarai_owner_lost(token ^ 0x1u);
        CHECK(pc_p2_sarai_piki_bound(&piki), "bridge-stale-token-keeps");
        pc_p2_sarai_owner_lost(token);
        CHECK(!pc_p2_sarai_piki_bound(&piki) && pc_p2_sarai_carried_count(&host) == 0,
            "bridge-owner-lost-revokes");
        CHECK(pc_p2_sarai_piki_capture(&piki, &host, &mouthB, token, 1), "bridge-recapture");
        pc_p2_sarai_scene_exit();
        CHECK(pc_p2_sarai_carried_count(&host) == 0, "bridge-scene-exit-clears");
        CHECK(pc_p2_sarai_piki_capture(&piki, &host, &mouthA, token, 0), "bridge-rentry-capture");
        pc_p2_sarai_forget();
        CHECK(!pc_p2_sarai_piki_bound(&piki), "bridge-forget-clears");
    }

    // --- 6. Source-23 delivery binding unchanged ---------------------------
    {
        CHECK(randomizerP2IsBindable(23), "roster-23-bindable");
        CHECK(!randomizerP2IsBindable(0), "roster-0-unbindable");
    }

    if (argc > 1) {
        if (checkBehaviorLog(argv[1]) != 0) ++failures;
    }

    if (failures == 0) std::printf("PASS P2_SARAI_CAMPAIGN_BEHAVIOR eligibility selection reacquire receivers teardown roster\n");
    else std::printf("P2_SARAI_CAMPAIGN_BEHAVIOR pass=0 failures=%d\n", failures);
    return failures == 0 ? 0 : 1;
}
