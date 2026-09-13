# Fuefuki squad-control interference policy (#245)

Successor of the #245 source audit. pc_p2_fuefuki_interference_policy.h
expresses commands for the source InteractFueFuki -> ACT_Teki -> release
paths without touching captain state, Pikmin FSMs or shared hooks. Source
revision and exact receiver details remain in P2_FUEFUKI_AUDIT.md
(projectPiki/pikmin2 632af93787b9c95b63f0c13be32b161375ce3a96, US GPVE01
rev 0, read-only under native/pikmin2-research).

Ownership analogue: the Demon captain-ownership lane (#226/#231/#236/#237,
native/tools/P2_DEMON_FORCED_DROP.md, P2_DEMON_DROP_POLICY.md). Where Sarai
holds creatures in mouth slots, Fuefuki borrows Pikmin through the AI-action
slot keyed on a raw owner pointer; the #237 generation/admission discipline
is applied here as owner epochs plus a shared ownership table.

## Host contract

- Exclusive single-controller registration. One shared
  P2FuefukiOwnershipTable is the callback domain mapping pikmin -> owner
  epoch. A Pikmin is claimable by exactly one live owner; tryClaim fails
  for any current holder. The beetle never writes captain ownership
  (piki->mNavi); squad borrowing lives entirely in the action slot.
- Epochs. Bind a strictly increasing, nonzero owner epoch per callback
  domain. Invalidate the entire domain (invalidateDomain) before any
  manager-slot or owner-pointer reuse — source ActTeki holds a raw
  EnemyBase* and checks isAlive() only, so slot reuse without invalidation
  is a stale-owner hazard. Epochs never wrap or reuse; a rejected command
  makes no mutation.
- Admission-before-mutation (source interactPiki.cpp InteractFueFuki::actPiki,
  34-49). admit requires an active cast and all four source gates: living
  Pikmin, callable current state, not stuck to a mouth, not already
  ACT_Teki-owned by anyone. The source's per-frame radius scan
  (updateWhisle) becomes: host iterates candidates inside
  radiusModifier * retail mAttackRadius each cast tick and feeds admit.
- Cast lifecycle. beginCast resets the ring; tickCast grows the modifier
  once per simulation update, clamped at 1.0 after one second, matching
  the source. Paused calls must be omitted or pass zero delta. The cast
  ends via suspend, ownerDied or cancel; the policy does not model the
  source's fixed 3.0-second state duration — that belongs to the future
  beetle FSM bridge, not the ownership policy.
- Squad-timer cadence decision. Source mSquadTimer is set to 5.0 by each
  follower ping (InteractFuefukiTimerReset, Fuefuki.cpp:18-26) and
  decremented by 1 per doUpdate frame regardless of deltaTime
  (Fuefuki.cpp:103-105). Chosen host cadence: an integer count of fixed
  simulation ticks — ping sets 5, tickSquad decrements exactly once per
  tick, never scaled by deltaTime. At retail 60 fps the window is ~83 ms;
  because every live follower pings once per exec tick, ping and decrement
  rates match and squadActive() stays true while any follower is active.
  A variable-rate host must keep a fixed-step accumulator, not multiply
  the timer by deltaTime. squadActive() selects the source's squad-cadence
  branch (Turn instead of Wait after Walk/Whisle; fp13 whistle interval).
- Release paths are distinct and must not be merged:
  - ownerDied (source ActTeki owner-death branch, aiTeki.cpp:65-81):
    releases all claims and commits them to the Panic-released set BEFORE
    the host runs any Pikmin state callback; followers transit to Panic.
    The epoch stays bound so reclaimPanic keeps working, but the dead
    owner cannot cast, admit or ping again; host must cancel() before
    reuse.
  - suspend (owner flying or bittered, aiTeki.cpp:83-94): releases all
    claims as the source's ACTEXEC_Success/emote exit. It is NOT a Panic
    release — no reclaim, no captain-ownership write; the Pikmin's stored
    mNavi decides rejoining (brain fallback untraced, see audit).
  - reclaimPanic (source InteractFue::actPiki ACT_Teki branch,
    interactPiki.cpp:172-206): accepted only for a follower in the
    Panic-released set, exactly once. On acceptance the host performs the
    source's ownership write: clear current action, piki->mNavi =
    whistling captain, transit LookAt. This is the only captain-ownership
    mutation in the lane; either captain may whistle-reclaim.
  - A live beetle's followers ignore all captain whistles: reclaimPanic
    rejects anything not in the Panic-released set.
- Captain switch and party combine are always no-ops on beetle-held and on
  Panic-released Pikmin (source: captain-swap whistle and actNavi
  party-combine touch Formation actions only; ACT_Teki is callable only in
  Panic via reclaim). The policy returns rejected commands with no
  mutation for both.
- cancel synchronously before owner teardown, manager-slot reuse,
  movie/scene exits or external state interruption. It releases this
  owner's claims and clears its Panic records WITHOUT emitting any Pikmin
  state command; death and suspension releases must go through
  ownerDied/suspend first. No claim may survive cancellation.
- Two-beetle claim ordering decision. Source ACT_Teki admission rejects
  any existing Teki follower, but simultaneous first-contact in one frame
  is untraced. Contract: the host serializes admit calls within one
  simulation tick in a fixed owner ordering (manager index); the shared
  table makes the first claim win and rejects the second, so ordering is
  deterministic and both beetles can never hold the same Pikmin.

Validation checks, epoch-qualified stale-command rejection, finite-value
checks on cast deltas and pikmin-id 0 rejection are host safety
constraints, not claims that these fields exist in the P2 decomp.

## Fixtures and evidence

tools/p2_fuefuki_interference_policy_test.cpp covers: attract -> control
with every admission gate, ring growth/clamp and paused/malformed deltas;
ping/squad-timer refresh, per-tick expiry at 5 ticks and non-follower ping
rejection; beetle defeat mid-effect with exactly-once Panic reclaim by
captain whistle and dead-owner cast/admit rejection; captain switch and
party combine as no-ops while held and after release; suspension exit
(flying/bittered) as non-Panic release with re-claim after return;
two-beetle simultaneous claim (first in fixed ordering wins, cross-owner
release isolation); stale-owner/manager-slot-reuse (cancel leaves no
phantom claims, new epoch binds, stale commands rejected); epoch zero and
pikmin id 0 rejection. Build and run:

    g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_interference_policy_test.cpp -o ../fuefuki-interference-policy-test.exe
    ../fuefuki-interference-policy-test.exe   # prints PASS

Result: PASS (MinGW64 g++, -Wall -Wextra -Werror clean) on the #245
commit. No live captain, Pikmin FSM, native hook integration, whistle
ring geometry, animation fidelity or gameplay acceptance follows from
these fixtures. Root retains shared integration.

## Remaining open items

- The 3.0-second cast state, Whisle/Jump/Dead FSM branches and the
  InteractFue ownership write belong to the future pc_p2_fuefuki FSM
  bridge and P1 squad hook requests (root-owned); this policy only
  arbitrates ownership.
- Brain fallback after suspend (Formation rejoin vs Free) is untraced in
  source; fixtures assert only the release set, not the destination state.
- Retail parm values (mAttackRadius whistle base, fp12/fp13) and the
  callable-state enumeration remain converter/audit dependencies (#128,
  #113, #131).
- Persistence of claims across day/cave transitions is undefined; cancel
  on teardown is the safe default until the lifecycle contract is agreed.
