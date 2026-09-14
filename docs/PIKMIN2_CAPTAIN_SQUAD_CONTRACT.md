# P2 captain / captive / squad ownership contract (lane 12, #130)

Lane 12 of [PIKMIN2_IMPLEMENTATION_FANOUT.md](PIKMIN2_IMPLEMENTATION_FANOUT.md),
parent [#109](https://github.com/4laric/pikmin-randomizer/issues/109), child
[#130](https://github.com/4laric/pikmin-randomizer/issues/130). Implementation
owner: Codex through the shared `4laric` account; executing session: opencode
(`opencode-go/deepseek-v4.1-flash`), recorded separately per AGENTS.md.

Native candidate: branch `opencode/p2-lanes-1012` @ `8219bf17`, base
`f9e139d8` (`codex/pikmin2-room-preview`). Header-only contract, no engine
behavior changed, no shared checkout touched. Patch bundle:
`native-candidates/lanes-1012/`.

## Why this slice first

Captor and squad consumers are blocked on a stable captain/captive boundary:

- Greater Jellyfloat (#243, lane 29) ingests a captain.
- Bumbling Snitchbug / Demon (#215–#242, lane 30) capture and drop squad
  members.
- Ranging Bloyster (#174, lane 16) depends on which captain is present.

No `pc_p2_captain` / `pc_p2_squad` module existed. The only prior captain write
was a family-local hook in the Fuefuki interference policy. This contract
centralizes the two-captain identity, health/knockout, held-actor ownership and
capture/release boundary so those families do not each invent one.

## Source basis

`native/pikmin2-research` (US GPVE01 revision 0):

| Concern | Anchor |
|---|---|
| two captains | `include/Game/Navi.h:40` `GET_OTHER_NAVI(navi) == 1 - mNaviIndex` |
| per-captain health | `include/Game/Navi.h:275` `mHealth`; `gamePlayData.h:487` `mNaviLifeMax[2]` |
| manager selection/knockout | `NaviMgr::getActiveNavi/getAliveOrima/getDeadOrima/informOrimaDead`, `mDeadNavis`, `mNaviDeadFlags[2]` (`Navi.h:322–350`) |
| squad ownership | `include/Game/Piki.h:291` `Piki::mNavi` |
| capture by Greater Jellyfloat | `OniKurage.cpp:56–57,597–681` `mSuckedNavis[2]`, `suckNavi()`, `isFinishNaviSuck()`, `escapeCheckNavi()` |
| Lesser Jellyfloat knockback | `Kurage.cpp`/`KurageState.cpp:675` `flickNearbyNavi()` |

## Interface

`native/pc_port/pc_p2_captain_policy.h` (header-only, no engine includes):

- `P2CaptainOwnershipTable` — shared scene domain `actor id -> captain`. One
  holder per actor; `transferAll(from,to)` moves a squad without dropping it.
- `P2CaptainPolicy` — per-scene controller:
  - `configure(captain, healthMax, present)` (Olimar / Louie or President)
  - `switchActive(target)` — source `getActiveNavi` switch
  - `claim` / `abandon` — Pikmin or carried actor ownership
  - `damage(captain, amount)` — knockout releases that captain's actors and
    hands control to the survivor
  - `capture(captain, captorEpoch)` / `releaseCaptured(captain, captorEpoch)`
  - `revive(captain, health)`, `reload()`, `cancel()`
  - captor-held actors: `captureActor(captorEpoch, actor)`,
    `releaseActor(captorEpoch, actor, toCaptain)`,
    `dropAllCaptured(captorEpoch)`, `isCaptive`, `captiveCount`

Captor families own their FSM and their `mSuckedNavis` / grab mapping; they call
`capture`/`releaseCaptured` for a captain and `captureActor`/`releaseActor` for
a Pikmin or carried item, always with a nonzero captor epoch. A stale epoch
(previous occupant of a recycled slot) can never release another captor's
capture.

## Invariants (enforced by the policy test)

1. Exactly one Active captain whenever any present captain is controllable.
2. An owned actor has at most one captain.
3. Switch, capture, knockout and scene reload never lose or duplicate an owned
   actor: it is either still owned by exactly one captain or explicitly
   freed.
4. Capture is epoch-qualified; stale captors are rejected.
5. A capture that would leave the player with zero control is refused.
6. A Pikmin/carried actor is either captain-owned or captor-held, never both.
   Captor death frees held actors (whistle-reclaimable, not deleted) and a
   reload restores them to their previous captain, so nothing is lost.

## Evidence

```text
g++ -std=c++17 -Wall -Wextra -I pc_port tools/test_p2_captain_policy.cpp -o test_p2_captain_policy.exe
PASS P2_CAPTAIN_POLICY
```

Native commit `14e8fb92`; executable SHA-256
`DCDAAE668FC8DDFB951C6FAB83CB65E9BCB9E1D13F5D2FFEA98B9BCACED57A25`.
This is a policy/contract test (engine-double), not a live `Navi` runtime run.

## Limits and next slices

- Not yet wired to the live `Navi` / `NaviMgr` objects; the host adapter that
  maps `mNaviIndex`, `mHealth` and `Piki::mNavi` onto this policy is the next
  lane-12 slice and requires a private native build plus an arena run.
- Held bombs and task ownership are represented only through the generic
  ownership table; dedicated held-item semantics remain to be audited.
- Two-player mode and President substitution are modeled as `present` slots but
  have no runtime acceptance yet.

Consumers (29/30/16) can implement against this interface now; a fake adapter
alone is not end-to-end acceptance.
