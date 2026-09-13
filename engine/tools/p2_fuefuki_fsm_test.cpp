#include "pc_p2_fuefuki_fsm.h"
#include <cassert>
#include <cstdio>
#include <limits>

using S = P2FuefukiFsmState;
static constexpr float DT = 1.0f / 30.0f; // fixed 30 Hz source tick

static P2FuefukiFsmParms testParms()
{
    P2FuefukiFsmParms p;
    p.maxGroundTime = 2.0f;             // fp01, shortened for fixtures
    p.airborneTime = 0.2f;              // fp03
    p.minWhistleTime = 0.3f;            // fp11, leaves a patrol window
    p.maxWhistleTimeNoSquad = 0.4f;     // fp12
    p.maxWhistleTimeWithSquad = 1.0f;   // fp13
    p.struggleTime = 10.0f;             // fp21, kept above the 3.0 s stuck-empty exit
    p.jumpTime = 0.0f;                  // fp22
    p.attackRadius = 100.0f;
    p.castDuration = 1.2f;              // shortened; retail is hard-coded 3.0 s
    return p;
}

static P2FuefukiFsmInput baseIn()
{
    P2FuefukiFsmInput in;
    in.delta       = DT;
    in.health      = 100.0f;
    in.animPlaying = true;
    return in;
}

// Drive Land's KEYEVENT_2/3/END sequence into Wait.
static void finishLanding(P2FuefukiFsm& fsm)
{
    P2FuefukiFsmInput in = baseIn();
    in.keyEvent          = 2;
    P2FuefukiFsmOut out  = fsm.tick(in);
    assert(out.eventClear & P2FUEFUKI_EB_NoInterrupt);
    assert(out.eventSet & P2FUEFUKI_EB_Lifegauge);
    assert(out.downEffect);
    in.keyEvent = 3;
    fsm.tick(in);
    in.keyEvent = 4;
    out         = fsm.tick(in);
    assert(out.transited && out.state == S::Wait);
}

// Run ticks until the FSM requests a transition, then feed END.
static P2FuefukiFsmOut runUntilTransition(P2FuefukiFsm& fsm, P2FuefukiFsmInput in, int maxTicks)
{
    P2FuefukiFsmOut out;
    for (int i = 0; i < maxTicks; i++) {
        in.keyEvent = 0;
        out         = fsm.tick(in);
        if (out.transited) return out;
        if (out.requestFinishMotion) {
            in.keyEvent = 4;
            out         = fsm.tick(in);
            if (out.transited) return out;
        }
    }
    return out;
}

int main()
{
    // --- full spawn -> patrol -> cast -> suspend -> re-claim cycle ---
    {
        P2FuefukiOwnershipTable table;
        table.invalidateDomain();
        P2FuefukiFsm fsm(testParms());
        P2FuefukiFsmOut out = fsm.spawn(table, 1);
        assert(out.accepted && out.state == S::Land && out.transited);
        assert(out.teleportToTarget);
        assert(out.eventSet & P2FUEFUKI_EB_NoInterrupt);
        finishLanding(fsm);
        assert(fsm.getState() == S::Wait);

        // patrol: Wait -> Turn -> Walk -> (arrive, no squad) -> Wait
        P2FuefukiFsmInput in = baseIn();
        out                  = runUntilTransition(fsm, in, 10);
        assert(out.transited && out.state == S::Turn);
        in.turnComplete = true;
        out             = runUntilTransition(fsm, in, 10);
        assert(out.transited && out.state == S::Walk);
        in.turnComplete = false;
        in.arriveTarget = true;
        out             = runUntilTransition(fsm, in, 10);
        assert(out.transited && out.state == S::Wait); // no squad -> Wait
        in.arriveTarget = false;

        // whistle cadence fp12 (no squad): patrol continues until the cast
        for (int guard = 0; guard < 12 && !(out.transited && out.state == S::Whisle); guard++)
            out = runUntilTransition(fsm, in, 60);
        assert(out.transited && out.state == S::Whisle);
        assert(fsm.getState() == S::Whisle);

        // cast: ring grows over 1 s; candidate admitted through interference
        P2FuefukiFsmInput cast = baseIn();
        P2FuefukiCandidate cand;
        cand.id = 10; cand.living = cand.callable = true;
        cast.candidates.push_back(cand);
        cast.followerPings = { 10 };
        float maxRadius = 0.0f;
        bool claimed    = false;
        for (int i = 0; i < 40; i++) {
            out = fsm.tick(cast);
            if (!out.claimed.empty()) claimed = true;
            if (out.whistleRadius > maxRadius) maxRadius = out.whistleRadius;
            cast.candidates.clear(); // already-owned followers are skipped by the host scan
        }
        assert(claimed && fsm.squad().holds(10));
        assert(maxRadius == 100.0f); // modifier clamped at 1.0 * attackRadius
        assert(out.squadActive);     // follower ping keeps the squad alive

        // cast ends after 3.0 s fixed; squad present -> Turn; claims persist
        cast.candidates.clear();
        out = runUntilTransition(fsm, cast, 40);
        assert(out.transited && out.state == S::Turn);
        assert(out.stopWhistleEffect && out.whistleEcho);
        assert(fsm.squad().holds(10)); // finishWhisle keeps ACT_Teki claims
        assert(fsm.squad().getPhase() == P2FuefukiPhase::Idle);

        // jump-away via appear timer (fp01 = 0.5 s of ground time)
        cast.followerPings = { 10 };
        out                = runUntilTransition(fsm, cast, 40);
        assert(out.transited && out.state == S::Jump);

        // Jump: KEYEVENT_3 escape burst, END -> Stay -> suspend release
        P2FuefukiFsmInput jin = baseIn();
        jin.keyEvent          = 3;
        out                   = fsm.tick(jin);
        assert(out.escapeVelocity && out.flickNavi && out.flickPikmin && out.flickStuck);
        assert(out.eventSet & P2FUEFUKI_EB_Untargetable);
        jin.keyEvent = 4;
        out          = fsm.tick(jin);
        assert(out.transited && out.state == S::Stay);
        assert(out.releasedSuspend.size() == 1 && out.releasedSuspend[0] == 10);
        assert(!fsm.squad().holds(10));
        assert(!fsm.squad().reclaimPanic(10).accepted); // suspend is not Panic

        // Stay airborne fp03 -> Land again; re-cast and re-claim the Pikmin
        out = runUntilTransition(fsm, baseIn(), 20);
        assert(out.transited && out.state == S::Land && out.teleportToTarget);
        finishLanding(fsm);
        P2FuefukiFsmInput pin = baseIn();
        for (int guard = 0; guard < 12 && !(out.transited && out.state == S::Whisle); guard++)
            out = runUntilTransition(fsm, pin, 90); // patrol until re-cast
        assert(out.transited && out.state == S::Whisle);
        P2FuefukiFsmInput recast = baseIn();
        recast.candidates.push_back(cand);
        out = fsm.tick(recast);
        assert(!out.claimed.empty() && out.claimed[0] == 10); // re-claimed
        assert(fsm.squad().holds(10));
    }

    // --- jump-away by intrusion, gated by squad presence ---
    {
        P2FuefukiOwnershipTable table;
        table.invalidateDomain();
        P2FuefukiFsm fsm(testParms());
        fsm.spawn(table, 1);
        finishLanding(fsm);
        P2FuefukiFsmInput in = baseIn();
        in.intruder          = true; // Navi inside mPrivateRadius, no squad
        P2FuefukiFsmOut out  = runUntilTransition(fsm, in, 5);
        assert(out.transited && out.state == S::Jump);

        // with an active squad the same intrusion does not trigger Jump
        P2FuefukiFsmParms calm = testParms();
        calm.maxGroundTime    = 100.0f; // isolate intrusion from the fp01 cap
        P2FuefukiFsm fast(calm);
        P2FuefukiOwnershipTable table2;
        table2.invalidateDomain();
        fast.spawn(table2, 1);
        finishLanding(fast);
        P2FuefukiFsmInput win = baseIn();
        P2FuefukiFsmOut wout;
        for (int guard = 0; guard < 12 && !(wout.transited && wout.state == S::Whisle); guard++)
            wout = runUntilTransition(fast, win, 60); // patrol -> Whisle (fp12)
        assert(wout.state == S::Whisle);
        P2FuefukiCandidate cand;
        cand.id = 20; cand.living = cand.callable = true;
        win.candidates.push_back(cand);
        fast.tick(win); // claim 20
        assert(fast.squad().holds(20));
        // keep squad pinged, intruder present: no jump-away
        P2FuefukiFsmInput guard = baseIn();
        guard.intruder          = true;
        guard.followerPings     = { 20 };
        bool jumped             = false;
        for (int i = 0; i < 100; i++) {
            wout = fast.tick(guard);
            if (wout.transited && wout.state == S::Jump) jumped = true;
            if (wout.requestFinishMotion) { // let non-Jump transitions proceed
                guard.keyEvent = 4;
                fast.tick(guard);
                guard.keyEvent = 0;
            }
        }
        assert(!jumped);
    }

    // --- whistle cadence: fp12 without squad, fp13 with squad, fp12 when stuck ---
    {
        // no-squad cadence (fp12): ticks from landing until the first cast
        auto ticksToWhistle = []() {
            P2FuefukiOwnershipTable table;
            table.invalidateDomain();
            P2FuefukiFsmParms p = testParms();
            p.maxGroundTime     = 100.0f; // keep jump-away out of the measurement
            P2FuefukiFsm fsm(p);
            fsm.spawn(table, 1);
            P2FuefukiFsmInput land = baseIn();
            land.keyEvent          = 2;
            fsm.tick(land);
            land.keyEvent = 3;
            fsm.tick(land);
            land.keyEvent = 4;
            fsm.tick(land);
            P2FuefukiFsmInput in = baseIn();
            int ticks              = 0;
            for (; ticks < 200; ticks++) {
                P2FuefukiFsmOut out = fsm.tick(in);
                if (fsm.getState() == S::Whisle) break;
                if (out.requestFinishMotion) {
                    in.keyEvent = 4;
                    fsm.tick(in);
                    in.keyEvent = 0;
                    if (fsm.getState() == S::Whisle) break;
                }
            }
            return ticks;
        };
        // squad case needs a held follower; drive it through one real cast
        auto ticksToWhistleWithSquad = [](bool stuck) {
            P2FuefukiOwnershipTable table;
            table.invalidateDomain();
            P2FuefukiFsmParms p = testParms();
            p.maxGroundTime     = 100.0f;
            P2FuefukiFsm fsm(p);
            fsm.spawn(table, 1);
            P2FuefukiFsmInput land = baseIn();
            land.keyEvent          = 2;
            fsm.tick(land);
            land.keyEvent = 3;
            fsm.tick(land);
            land.keyEvent = 4;
            fsm.tick(land);
            // first cast (fp12, no squad): claim follower 50
            P2FuefukiFsmInput in = baseIn();
            for (int i = 0; i < 200 && fsm.getState() != S::Whisle; i++) {
                P2FuefukiFsmOut out = fsm.tick(in);
                if (out.requestFinishMotion) {
                    in.keyEvent = 4;
                    fsm.tick(in);
                    in.keyEvent = 0;
                }
            }
            assert(fsm.getState() == S::Whisle);
            P2FuefukiCandidate cand;
            cand.id = 50; cand.living = cand.callable = true;
            in.candidates.push_back(cand);
            fsm.tick(in);
            assert(fsm.squad().holds(50));
            in.candidates.clear();
            // end the cast, then measure ticks until the next cast
            int ticks = 0;
            bool leftCast = false;
            in.followerPings = { 50 };
            in.stuckPikmin   = stuck ? 1 : 0;
            P2FuefukiFsmOut out;
            for (; ticks < 300; ticks++) {
                out = fsm.tick(in);
                if (leftCast && fsm.getState() == S::Whisle) break;
                if (fsm.getState() != S::Whisle) leftCast = true;
                if (out.requestFinishMotion) {
                    in.keyEvent = 4;
                    fsm.tick(in);
                    in.keyEvent = 0;
                    if (leftCast && fsm.getState() == S::Whisle) break;
                    if (fsm.getState() != S::Whisle) leftCast = true;
                }
            }
            assert(leftCast && fsm.getState() == S::Whisle);
            return ticks;
        };
        int noSquad    = ticksToWhistle();
        int squad      = ticksToWhistleWithSquad(false);
        int squadStuck = ticksToWhistleWithSquad(true);
        // fp13 (1.0 s) vs fp12 (0.4 s) at 30 Hz: squad cadence is longer,
        // stuck attackers pull it back to the no-squad interval.
        assert(squad > noSquad);
        assert(squadStuck < squad);
    }

    // --- struggle: entry, exits to Jump and Dead, bittered rejection ---
    {
        P2FuefukiOwnershipTable table;
        table.invalidateDomain();
        P2FuefukiFsm fsm(testParms());
        fsm.spawn(table, 1);
        finishLanding(fsm); // Land KEYEVENT_3 armed canStruggle
        P2FuefukiFsmInput in = baseIn();
        in.pressed           = true;
        in.stuckPikmin       = 2;
        P2FuefukiFsmOut out  = fsm.tick(in);
        assert(out.transited && out.state == S::Struggle);
        // struggle ends when attackers leave after 3 s -> Jump
        in.pressed     = false;
        in.stuckPikmin = 0;
        int ticks      = 0;
        for (; ticks < 200; ticks++) {
            out = fsm.tick(in);
            if (out.requestFinishMotion) break;
        }
        assert(ticks > 85); // ~3 s at 30 Hz
        in.keyEvent = 4;
        out         = fsm.tick(in);
        assert(out.transited && out.state == S::Jump);

        // bittered press does not struggle
        P2FuefukiFsm fsm2(testParms());
        P2FuefukiOwnershipTable t2;
        t2.invalidateDomain();
        fsm2.spawn(t2, 2);
        finishLanding(fsm2);
        P2FuefukiFsmInput bin = baseIn();
        bin.pressed           = true;
        bin.bittered          = true;
        out                   = fsm2.tick(bin);
        assert(out.state != S::Struggle);

        // struggle with fatal damage exits to Dead at END
        P2FuefukiFsm fsm3(testParms());
        P2FuefukiOwnershipTable t3;
        t3.invalidateDomain();
        fsm3.spawn(t3, 3);
        finishLanding(fsm3);
        P2FuefukiFsmInput din = baseIn();
        din.pressed           = true;
        din.stuckPikmin       = 1;
        fsm3.tick(din);
        assert(fsm3.getState() == S::Struggle);
        din.pressed = false;
        din.health  = 0.0f;
        out         = fsm3.tick(din);
        assert(out.requestFinishMotion);
        din.keyEvent = 4;
        out          = fsm3.tick(din);
        assert(out.transited && out.state == S::Dead);
    }

    // --- death routing from every state that checks health ---
    {
        auto driveTo = [](S target, P2FuefukiFsm& fsm) {
            P2FuefukiFsmInput in = baseIn();
            P2FuefukiFsmOut out;
            for (int i = 0; i < 400 && fsm.getState() != target; i++) {
                in.turnComplete = (fsm.getState() == S::Turn);
                out             = fsm.tick(in);
                if (out.requestFinishMotion) {
                    in.keyEvent = 4;
                    fsm.tick(in);
                    in.keyEvent = 0;
                }
            }
            assert(fsm.getState() == target);
        };
        const S deathStates[] = { S::Wait, S::Turn, S::Walk, S::Whisle };
        for (S target : deathStates) {
            P2FuefukiOwnershipTable table;
            table.invalidateDomain();
            P2FuefukiFsmParms p = testParms();
            p.maxGroundTime     = 100.0f; // isolate from jump-away
            P2FuefukiFsm fsm(p);
            fsm.spawn(table, 1);
            finishLanding(fsm);
            driveTo(target, fsm);
            P2FuefukiFsmInput in = baseIn();
            in.health            = 0.0f;
            P2FuefukiFsmOut out  = fsm.tick(in);
            if (out.requestFinishMotion) {
                in.keyEvent = 4;
                out         = fsm.tick(in);
            }
            assert(out.transited && out.state == S::Dead);
            // dead-anim END kills; carcass uses the Carry anim
            P2FuefukiFsmInput din = baseIn();
            din.health            = 0.0f;
            din.keyEvent          = 4;
            out                   = fsm.tick(din);
            assert(out.kill && out.carcassCarryAnim);
        }
        // Jump struggle window: health <= 0 routes directly to Dead
        {
            P2FuefukiOwnershipTable table;
            table.invalidateDomain();
            P2FuefukiFsm fsm(testParms());
            fsm.spawn(table, 1);
            finishLanding(fsm);
            P2FuefukiFsmInput in = baseIn();
            in.intruder          = true;
            P2FuefukiFsmOut out  = runUntilTransition(fsm, in, 5);
            assert(out.state == S::Jump);
            in.intruder = false;
            in.health   = 0.0f;
            out         = fsm.tick(in); // canStruggle window
            assert(out.transited && out.state == S::Dead);
        }
        // death while casting releases followers through the Panic path
        {
            P2FuefukiOwnershipTable table;
            table.invalidateDomain();
            P2FuefukiFsm fsm(testParms());
            fsm.spawn(table, 1);
            finishLanding(fsm);
            driveTo(S::Whisle, fsm);
            P2FuefukiFsmInput in = baseIn();
            P2FuefukiCandidate cand;
            cand.id = 77; cand.living = cand.callable = true;
            in.candidates.push_back(cand);
            fsm.tick(in);
            assert(fsm.squad().holds(77));
            in.candidates.clear();
            in.health           = 0.0f;
            P2FuefukiFsmOut out = fsm.tick(in);
            assert(out.requestFinishMotion);
            in.keyEvent = 4;
            out         = fsm.tick(in);
            assert(out.state == S::Dead);
            assert(out.releasedPanic.size() == 1 && out.releasedPanic[0] == 77);
            assert(fsm.squad().reclaimPanic(77).accepted); // captain whistle reclaims
        }
        // Land and Stay have no health check in source: no death routing
        {
            P2FuefukiOwnershipTable table;
            table.invalidateDomain();
            P2FuefukiFsm fsm(testParms());
            fsm.spawn(table, 1);
            assert(fsm.getState() == S::Land);
            P2FuefukiFsmInput in = baseIn();
            in.health            = 0.0f;
            in.keyEvent          = 4; // Land END with no pending next -> Wait
            P2FuefukiFsmOut out  = fsm.tick(in);
            assert(out.state != S::Dead);
        }
    }

    // --- malformed deltas rejected without mutation ---
    {
        P2FuefukiOwnershipTable table;
        table.invalidateDomain();
        P2FuefukiFsm fsm(testParms());
        fsm.spawn(table, 1);
        P2FuefukiFsmInput in = baseIn();
        in.delta             = -DT;
        assert(!fsm.tick(in).accepted);
        in.delta = std::numeric_limits<float>::quiet_NaN();
        assert(!fsm.tick(in).accepted);
        in.delta = std::numeric_limits<float>::infinity();
        assert(!fsm.tick(in).accepted);
        in.health = std::numeric_limits<float>::quiet_NaN();
        in.delta  = DT;
        assert(!fsm.tick(in).accepted);
        assert(fsm.getState() == S::Land); // unchanged
        assert(fsm.tick(baseIn()).accepted);
    }

    puts("p2_fuefuki_fsm_test PASS");
}
