#pragma once
#include "pc_p2_fuefuki_follow.h"
#include "pc_p2_fuefuki_fsm.h"
#include <cmath>
#include <cstdint>

// Lane-owned hook/binding seam for pc_p2_fuefuki (#245). Engine-free host
// adapter contract in the Groink/BombSarai pattern: the host (or a fixture
// mock) supplies every engine fact through these callbacks; the binder
// drives P2FuefukiFsm and the squad-control interference policy. No actor,
// map, captain or P1 engine dependency; fixed 30 Hz source ticks, no wall
// clock. Item (f) of the slice — the FUEFUKIANIM motion bank — stays with
// the engine lane's converter/material work (#128); this seam only
// consumes host-supplied animation facts (animPlaying/keyEvent/
// motionFinished/turnComplete).
//
// Seam coverage (successor of the six root-owned request specs in
// P2_FUEFUKI_FSM.md):
//  (a) P2FuefukiEnumerateFn  — read-only squad enumeration + candidate
//      classification feeding the cast-tick scan (XZ, no height gate).
//  (b) P2FuefukiFollowStartFn / P2FuefukiFollowEndFn /
//      P2FuefukiPingCollectFn — claim->follow-action binding with
//      per-tick ping return; one controller per Pikmin (enforced by the
//      ownership table); NO captain-ownership write on claim.
//  (c) onCaptainWhistle — captain-whistle reclaim interception for
//      Panic-released followers only, performing the lane's single
//      ownership write through P2FuefukiOwnershipWriteFn. onCaptainSwitch
//      and onPartyCombine are explicit non-routes: always false, never
//      write.
//  (d) P2FuefukiKillFn — health/kill delivery. ownerDied is committed by
//      the FSM before any P2FuefukiFollowEndFn(PANIC) callback runs;
//      the kill command carries the Carry-carcass flag.
//  (e) P2FuefukiProbeFn — intrusion/arrival/water/position probes as
//      plain per-tick inputs.

// ---------------------------------------------------------------------------
// Host adapter interface (the host implements these; fixtures mock them)

// (e) Per-tick environment probe. The host fills every field and sets
// valid=true; valid=false or non-finite coordinates fail the whole tick
// without mutation.
struct P2FuefukiProbeResult {
    float x = 0.0f, z = 0.0f;     // beetle position (host-owned)
    float vx = 0.0f, vz = 0.0f;   // beetle velocity (source getVelocity; follow blend)
    bool intruder = false;        // Navi / non-owned non-stuck Pikmin inside mPrivateRadius
    bool arriveTarget = false;    // wall triangle or XZ dist^2 < 625 to the walk target
    bool water = false;           // mWaterBox present (ripple effects)
    bool valid = false;
};
typedef void (*P2FuefukiProbeFn)(void* context, P2FuefukiProbeResult& out);

// (a) Read-only squad enumeration for the cast-tick scan. The host lists
// Pikmin whose XZ distance to (x,z) is within radius (source sqrDistanceXZ,
// no height gate), classifies each candidate, and returns the count, or -1
// on failure (fails the whole tick). Counts beyond capacity are truncated.
struct P2FuefukiSquadEntry {
    std::uint32_t id = 0;
    bool living = false;       // isAlive
    bool callable = false;     // mCurrentState->callable()
    bool stuckToMouth = false; // isStickToMouth
    bool alreadyTeki = false;  // mBrain->mActionId == ACT_Teki (any owner)
};
typedef int (*P2FuefukiEnumerateFn)(void* context, float x, float z, float radius,
                                    P2FuefukiSquadEntry* out, int capacity);

// (b) Follow-action binding. followStart is called exactly once per
// accepted claim; admission already filtered the candidate, so the host
// must not reject post-admission — a false return is counted as a host
// contract error in P2FuefukiBindOut::followErrors and the policy remains
// authoritative for the claim. followEnd fires once per release with
// reason 0 = suspend (flying/bittered Success exit), 1 = panic (owner
// death). For reason 1 the ownership-table release is already committed
// when the callback runs (contract-critical ordering).
enum P2FuefukiFollowEndReason {
    P2FUEFUKI_END_SUSPEND = 0,
    P2FUEFUKI_END_PANIC   = 1,
};
typedef bool (*P2FuefukiFollowStartFn)(void* context, std::uint32_t pikmin);
typedef void (*P2FuefukiFollowEndFn)(void* context, std::uint32_t pikmin, int reason);

// (b) Per-tick ping return: the host lists follower ids whose follow
// action executed this tick (source ActTeki exec -> timer-reset stimulus).
// Returns the count, or -1 on failure (fails the whole tick).
typedef int (*P2FuefukiPingCollectFn)(void* context, std::uint32_t* out, int capacity);

// (c) The lane's single captain-ownership write (source InteractFue
// receiver: clear action, piki->mNavi = whistling captain, LookAt). Fired
// only for an accepted Panic reclaim, exactly once per released follower.
typedef void (*P2FuefukiOwnershipWriteFn)(void* context, std::uint32_t pikmin, std::uint32_t naviId);

// (d) Kill delivery at dead-anim END. carcassCarryAnim requests the
// source startCarcassMotion -> FUEFUKIANIM_Carry carcass.
typedef void (*P2FuefukiKillFn)(void* context, bool carcassCarryAnim);

// (g) Follow locomotion (source PikiAI::ActTeki, aiTeki.cpp) — optional.
// When both followerSample and followDrive are present the binder drives the
// lane's P2FuefukiFollowController and emits one velocity command per held
// Pikmin per tick; the host applies it (P1 Piki::setSpeed / mTargetVelocity).
// Without them the binder keeps claim/release bookkeeping only (legacy).
typedef bool (*P2FuefukiFollowerSampleFn)(void* context, std::uint32_t pikmin, float& x, float& z);
typedef void (*P2FuefukiFollowDriveFn)(void* context, std::uint32_t pikmin, const P2FuefukiFollowMove& move);

struct P2FuefukiHost {
    void* context = nullptr;
    P2FuefukiProbeFn probe = nullptr;
    P2FuefukiEnumerateFn enumerate = nullptr;
    P2FuefukiFollowStartFn followStart = nullptr;
    P2FuefukiFollowEndFn followEnd = nullptr;
    P2FuefukiPingCollectFn pingCollect = nullptr;
    P2FuefukiOwnershipWriteFn ownershipWrite = nullptr;
    P2FuefukiKillFn kill = nullptr;
    P2FuefukiFollowerSampleFn followerSample = nullptr;
    P2FuefukiFollowDriveFn followDrive = nullptr;
    P2FuefukiRandFn randFloat = nullptr;
};

// ---------------------------------------------------------------------------
// Binder driver

struct P2FuefukiBindTick {
    float delta = 0.0f;          // fixed 1/30 source tick
    float health = 1.0f;
    int stuckPikmin = 0;
    bool animPlaying = false;
    int keyEvent = 0;            // 0 none, 2, 3, 4 = KEYEVENT_END
    bool motionFinished = false;
    bool turnComplete = false;
    bool pressed = false;
    bool bittered = false;
};

struct P2FuefukiBindOut {
    bool accepted = false;
    P2FuefukiFsmState state = P2FuefukiFsmState::Land;
    bool transited = false;
    float whistleRadius = 0.0f;
    int claimed = 0, endedSuspend = 0, endedPanic = 0;
    int followErrors = 0; // host followStart rejections (contract errors)
    int followMoves = 0, followStops = 0; // locomotion commands emitted this tick
    bool followActive = false;            // locomotion seam bound
    bool kill = false, carcassCarryAnim = false;
    P2FuefukiSuspendFallback suspendFallback = P2FUEFUKI_SUSPEND_FALLBACK_FREE;
    P2FuefukiFsmOut fsm;
};

class P2FuefukiBinding {
    static constexpr int BUFFER_CAPACITY = 128;
    P2FuefukiOwnershipTable ownedTable;
    P2FuefukiOwnershipTable* table = nullptr;
    P2FuefukiFsmParms parms;
    P2FuefukiFsm fsm;
    P2FuefukiFollowController followController;
    P2FuefukiHost host;
    bool bound = false;
    bool followBound = false;

public:
    // Bind a host adapter and parms. A null sharedTable uses the binder's
    // own ownership table; multiple beetles in one area MUST share one
    // table so single-controller exclusivity holds across instances. The
    // optional follow parms configure the ActTeki locomotion policy; the
    // locomotion seam is active only when the host supplies both
    // followerSample and followDrive.
    bool bind(const P2FuefukiHost& adapter, const P2FuefukiFsmParms& p, P2FuefukiOwnershipTable* sharedTable,
              const P2FuefukiFollowParms& fp = P2FuefukiFollowParms())
    {
        if (bound || !adapter.probe || !adapter.enumerate || !adapter.followStart || !adapter.followEnd
            || !adapter.pingCollect || !adapter.ownershipWrite || !adapter.kill)
            return false;
        host  = adapter;
        parms = p;
        fsm   = P2FuefukiFsm(p);
        table = sharedTable ? sharedTable : &ownedTable;
        followBound = adapter.followerSample && adapter.followDrive;
        followController.setParms(fp);
        bound = true;
        return true;
    }

    P2FuefukiBindOut spawn(std::uint64_t epoch)
    {
        P2FuefukiBindOut out;
        if (!bound) return out;
        followController.reset();
        P2FuefukiFsmOut s = fsm.spawn(*table, epoch);
        if (!s.accepted) return out;
        out.accepted = true;
        out.state    = s.state;
        out.transited = true;
        out.fsm      = s;
        return out;
    }

    P2FuefukiBindOut tick(const P2FuefukiBindTick& in)
    {
        P2FuefukiBindOut out;
        if (!bound || !std::isfinite(in.delta) || in.delta < 0.0f || !std::isfinite(in.health))
            return out;

        // (e) probes first; any failure rejects the tick before mutation.
        P2FuefukiProbeResult probe;
        host.probe(host.context, probe);
        if (!probe.valid || !std::isfinite(probe.x) || !std::isfinite(probe.z)) return out;

        // (b) ping return.
        std::uint32_t pingBuffer[BUFFER_CAPACITY];
        int pingCount = host.pingCollect(host.context, pingBuffer, BUFFER_CAPACITY);
        if (pingCount < 0) return out;

        // (a) cast-tick candidate scan. Source updateWhisle grows the ring
        // before scanning, so the query radius is this tick's post-growth
        // radius; outside Whisle no scan is performed.
        P2FuefukiSquadEntry entries[BUFFER_CAPACITY];
        int entryCount = 0;
        if (fsm.getState() == P2FuefukiFsmState::Whisle) {
            float modifier = fsm.squad().getRadiusModifier() + in.delta;
            if (modifier > 1.0f) modifier = 1.0f;
            float radius = modifier * parms.attackRadius;
            entryCount   = host.enumerate(host.context, probe.x, probe.z, radius, entries, BUFFER_CAPACITY);
            if (entryCount < 0) return out;
        }

        P2FuefukiFsmInput fin;
        fin.delta          = in.delta;
        fin.health         = in.health;
        fin.stuckPikmin    = in.stuckPikmin;
        fin.animPlaying    = in.animPlaying;
        fin.keyEvent       = in.keyEvent;
        fin.motionFinished = in.motionFinished;
        fin.turnComplete   = in.turnComplete;
        fin.arriveTarget   = probe.arriveTarget;
        fin.intruder       = probe.intruder;
        fin.pressed        = in.pressed;
        fin.bittered       = in.bittered;
        fin.water          = probe.water;
        for (int i = 0; i < entryCount; i++) {
            P2FuefukiCandidate cand;
            cand.id          = entries[i].id;
            cand.living      = entries[i].living;
            cand.callable    = entries[i].callable;
            cand.stuckToMouth = entries[i].stuckToMouth;
            cand.alreadyTeki = entries[i].alreadyTeki;
            fin.candidates.push_back(cand);
        }
        for (int i = 0; i < pingCount; i++) fin.followerPings.push_back(pingBuffer[i]);

        P2FuefukiFsmOut fout = fsm.tick(fin);
        if (!fout.accepted) return out;

        // (g) source updateFootmarks runs every beetle update, before the
        // follower actions it feeds; record the trail at this tick's anchor.
        followController.beetleTick(probe.x, probe.z, in.delta);

        // (b)/(d) dispatch. For panic releases the ownership-table release
        // was committed inside fsm.tick before these callbacks run.
        for (std::uint32_t id : fout.claimed) {
            if (!host.followStart(host.context, id)) out.followErrors++;
            followController.claim(id);
            out.claimed++;
        }
        for (std::uint32_t id : fout.releasedSuspend) {
            host.followEnd(host.context, id, P2FUEFUKI_END_SUSPEND);
            followController.release(id);
            out.endedSuspend++;
        }
        for (std::uint32_t id : fout.releasedPanic) {
            host.followEnd(host.context, id, P2FUEFUKI_END_PANIC);
            followController.release(id);
            out.endedPanic++;
        }
        if (fout.kill) {
            host.kill(host.context, fout.carcassCarryAnim);
            followController.releaseAll();
            out.kill             = true;
            out.carcassCarryAnim = fout.carcassCarryAnim;
        }

        // (g) drive each held follower along the trail (source ActTeki
        // exec -> test_0). The host applies the emitted velocity command.
        out.followActive = followBound;
        if (followBound) {
            for (int i = 0; i < followController.followerCount(); i++) {
                const std::uint32_t id = followController.followerAt(i);
                float px = 0.0f, pz = 0.0f;
                if (!host.followerSample(host.context, id, px, pz)) continue;
                P2FuefukiFollowMove move = followController.followerTick(
                    id, px, pz, probe.x, probe.z, probe.vx, probe.vz, in.delta, host.randFloat, host.context);
                if (!move.hasMove) continue;
                host.followDrive(host.context, id, move);
                if (move.stop)
                    out.followStops++;
                else
                    out.followMoves++;
            }
        }

        out.accepted      = true;
        out.state         = fout.state;
        out.transited     = fout.transited;
        out.whistleRadius = fout.whistleRadius;
        out.suspendFallback = fout.suspendFallback;
        out.fsm           = fout;
        return out;
    }

    // (c) Captain-whistle reclaim interception: only a Panic-released
    // follower is reclaimed, exactly once, via the lane's single write.
    bool onCaptainWhistle(std::uint32_t pikmin, std::uint32_t naviId)
    {
        if (!bound) return false;
        if (!fsm.squad().reclaimPanic(pikmin).accepted) return false;
        host.ownershipWrite(host.context, pikmin, naviId);
        return true;
    }

    // (c) Explicit non-routes: captain switch and party combine never
    // touch beetle-held or Panic-released Pikmin (source interactPiki
    // ACT_Teki branch gates on PIKISTATE_Panic; combine touches Formation
    // actions only). Always false; never perform an ownership write.
    bool onCaptainSwitch(std::uint32_t pikmin) const
    {
        (void)pikmin;
        return false;
    }
    bool onPartyCombine(std::uint32_t pikmin) const
    {
        (void)pikmin;
        return false;
    }

    // (d) Force the owner-death release path directly. The host's forget/doKill
    // seam calls this when the engine death funnel reaches the actor before the
    // regular tick can consume health<=0 -> Dead. Mirrors tick()'s release
    // dispatch: enterOwnerDeath() commits the Panic release inside the FSM, then
    // followEnd(PANIC) fires for each released follower. Idempotent after a
    // normal Dead transit (no claim survives, no duplicate callback).
    P2FuefukiBindOut killVehicle()
    {
        P2FuefukiBindOut out;
        if (!bound) return out;
        P2FuefukiFsmOut fout = fsm.enterOwnerDeath();
        if (!fout.accepted) return out;
        for (std::uint32_t id : fout.releasedPanic) {
            host.followEnd(host.context, id, P2FUEFUKI_END_PANIC);
            followController.release(id);
            out.endedPanic++;
        }
        out.accepted  = true;
        out.state     = fout.state;
        out.transited = fout.transited;
        out.fsm       = fout;
        return out;
    }

    P2FuefukiFsm& getFsm() { return fsm; }
    P2FuefukiFollowController& follow() { return followController; }
    const P2FuefukiFollowController& follow() const { return followController; }
};
