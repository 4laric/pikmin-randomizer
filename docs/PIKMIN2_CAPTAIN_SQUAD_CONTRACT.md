# P2 captain / captive / squad ownership contract (lane 12, #130)

Lane 12 of [PIKMIN2_IMPLEMENTATION_FANOUT.md](PIKMIN2_IMPLEMENTATION_FANOUT.md),
parent [#109](https://github.com/4laric/pikmin-randomizer/issues/109), child
[#130](https://github.com/4laric/pikmin-randomizer/issues/130). Implementation
owner: Codex through the shared `4laric` account; executing session: opencode
(`opencode-go/deepseek-v4.1-flash`), recorded separately per AGENTS.md.

Native candidate (contract): branch `opencode/p2-lanes-1012` @ `8219bf17`,
base `f9e139d8` (`codex/pikmin2-room-preview`). Header-only contract, no engine
behavior changed, no shared checkout touched. Patch bundle:
`native-candidates/lanes-1012/`.

Native candidate (slot-0 engine adapter): branch `opencode/p2-sub-captains` @
`fd40992c`, base `5a0cb4ee`. Patch bundle: `native-candidates/p2-sub-captains/`.
Single-captain binding only; see "Single-captain audit" and "Two-captain
blocker" below.

Native candidate (second-captain scaffolding): branch `opencode/p2-sub2-captains`
@ `8352ef91`, base `4f7485d5`. Patch bundle:
`native-candidates/p2-sub2-captains/0001-*.patch`. Adds the additive engine
primitives, slot-1 binding and a strictly opt-in creation path that is inert
while the live gate is closed; see "Second-captain scaffolding slice" below.

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

`native/pc_port/pc_p2_captain.h` + `pc_p2_captain.cpp` (the engine-facing host
adapter, added this slice):

- `P2CaptainHostOps` is the engine-free callback seam (captain handle, health
  get/set, Piki actor id, `Piki::mNavi` owner slot get/set, squad enumeration).
  `pc_p2_captain.cpp` implements it against the live P1 `naviMgr`/`pikiMgr`;
  the standalone test binds doubles.
- `P2CaptainAdapter` owns the ownership table and policy, `setup()` configures
  present captains and adopts the live squad, and captain capture / captor-held
  actor operations mirror `Piki::mNavi` back into the engine. Plus
  `syncOwnership`, `health`/`setHealth`/`refresh`, `switchActive`,
  `captureCaptain`/`releaseCaptain`, `captureActor`/`releaseActor`/
  `dropAllCaptured`, `reload`, `teardown`.
- `namespace pc_p2_captain` exposes opt-in glue used by future captor families:
  `setup_from_navi_mgr`, `health`, `set_health`, `capture_captain`,
  `release_captain`, `switch_active`, `reload`, `adopt_squad`, `capture_actor`,
  `release_actor`, `drop_captured`, `teardown`. Nothing runs unless called.

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
# policy contract (unchanged, engine-double)
g++ -std=c++17 -Wall -Wextra -I pc_port tools/test_p2_captain_policy.cpp -o test_p2_captain_policy.exe
PASS P2_CAPTAIN_POLICY

# engine-facing adapter (engine-double host; not a live Navi runtime)
g++ -std=c++17 -Wall -Wextra -Werror -I pc_port tools/test_p2_captain_adapter.cpp -o test_p2_captain_adapter.exe
PASS P2_CAPTAIN_ADAPTER

# second-captain roster helpers (engine-free selection logic; not a live Navi)
g++ -std=c++17 -Wall -Wextra -Werror -I pc_port tools/test_p2_captain_roster.cpp -o test_p2_captain_roster.exe
PASS P2_CAPTAIN_ROSTER

# private engine build (native base 5a0cb4ee + fd40992c)
cmake -S output/native-sub-captains -B output/native-sub-captains-build -G Ninja \
  -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ -DCMAKE_BUILD_TYPE=Release -DPIKMIN_NATIVE_JAUDIO=ON
cmake --build output/native-sub-captains-build --target pikmin_pc -j 4
ninja -C output/native-sub-captains-build -n pikmin_pc   # ninja: no work to do.
```

- Policy contract: native commit `14e8fb92`; executable SHA-256
  `DCDAAE668FC8DDFB951C6FAB83CB65E9BCB9E1D13F5D2FFEA98B9BCACED57A25`.
- Adapter + engine build: native commit `fd40992c` (base `5a0cb4ee`),
  `output/native-sub-captains-build/bin/nectar.exe` SHA-256
  `9DED5D4E0390B3FAF87608F7FB7C3B1C05FA69D4441936A3EBCE392F8998F976`,
  `ninja -n` reports no work to do. The adapter test and the policy test are
  engine-double/contract tests; neither claims a live `Navi` runtime.
- Second-captain scaffolding: native commit `8352ef91` (base `4f7485d5`),
  private build `output/native-sub2-captains-build/bin/nectar.exe` SHA-256
  `E17047522D52A7876F2D18D051ACD7BB8DA41C7D193C8208F9559BDA20B784FF`,
  `ninja -C output/native-sub2-captains-build -n pikmin_pc` reports no work to
  do. Root gate
  `pytest tests/test_pikmin2_captain_adapter.py tests/test_pikmin2_lanes_1012_policies.py -q`
  -> **10 passed** (includes `PASS P2_CAPTAIN_ROSTER`). All are
  compile/engine-double/contract tests; none claims a live two-captain runtime.

## Single-captain audit (what a second captain would require)

The port is a Pikmin-1 engine with one captain. Anchors:

| Assumption | Anchor | Consequence |
|---|---|---|
| No second-captain index | `include/Navi.h` has no `mNaviIndex`; only `int mNaviID` at `Navi.h:248` (`_92C`), assigned by `NaviMgr::createObject()` (`naviMgr.cpp:65-69`) from the spawn counter `NaviMgr::mNaviID` (`NaviMgr.h:195`). | No `GET_OTHER_NAVI`; slot mapping is by spawn order only. |
| One Navi object | `NaviMgr::getNavi()` returns the first object (`naviMgr.cpp:83-88`); `getNavi(int)` exists (`naviMgr.cpp:93-102`) and is used with `0`/`1` only by latent P1 2-player naming (`piki.cpp:2928,2984`). Every gameplay consumer calls the no-arg `getNavi()`. | The engine only ever creates/updates one Navi for the campaign. |
| No manager knockout API | `NaviMgr.h:169-197` has no `getActiveNavi`/`getAliveOrima`/`getDeadOrima`/`informOrimaDead`, no `mDeadNavis`/`mNaviDeadFlags[2]`. `NaviMgr` is a plain `MonoObjectMgr`. | Active/knockout state must be tracked outside the manager (the policy does). |
| Health is inherited | `Navi` has no own health member; it uses `Creature::mHealth` (`Creature.h:388`, `_58`). `Navi::Navi` seeds it from `NaviProp::Parms::mHealth` (`navi.cpp:497`, `NaviMgr.h:143`); damage paths subtract from `navi->mHealth` (`navi.cpp:2757,2780,2802`); knockout is `NAVISTATE_Dead` via `finishDamage`/`NaviDeadState` (`navi.cpp:428-445`, `naviState.cpp:3188-3190`). | A second captain needs separate health storage; `NaviMgr::mNaviParms` is shared. |
| One shape slot | `NaviMgr::mNaviShapeObject[2]` exists (`NaviMgr.h:193`) but only `[0]` is created (`naviMgr.cpp:43-47`) and `Navi::mNaviShapeObject = naviMgr->mNaviShapeObject[mNaviID]` (`navi.cpp:490`). | A second captain would index `[1]` and needs `mNaviID == 1` from `createObject()`. |
| Squad ownership is per-Piki | `Piki::mNavi` (`Piki.h:318`, `_504`); set in `Piki::init` (`piki.cpp:2404`), read for id/name (`piki.cpp:837`, `2928`). Generator spawns Pikmin with `naviMgr->getNavi()` (`generator.cpp:1193,1197,1199`). | Ownership can already be remapped; the adapter mirrors `mNavi` through the ownership table. |
| Game-over is global | `GAMEEND_NaviDown` (`FlowController.h:25`); `GameStat::orimaDead` (`gameStat.cpp:22`, `NaviDeadState::init`, `naviState.cpp:3190`). `gameCoreSection.cpp` reads `mNavi->mHealth` for game over (`:2092-2094`). | Real 2-captain needs per-captain dead flags and a survivor check before game over. |

To add a real second captain the engine needs, at minimum:
`NaviMgr::getNavi(1)` creation with `mNaviID`/`mNaviShapeObject[1]`; a
`Navi::mNaviIndex`/`GET_OTHER_NAVI` equivalent; per-captain active/dead tracking
(`getActiveNavi`/`getAliveOrima`/`getDeadOrima`, dead flags); a survivor-gated
`GAMEEND_NaviDown`; and control routing (`Kontroller`, camera, whistle) per
active captain. Until then this lane is **slot 0 only**, and the adapter refuses
`switchActive(1)` / `captureCaptain(0, …)` exactly as the contract requires.

## Second-captain scaffolding slice (slot-1 binding + opt-in path)

Native `8352ef91` (base `4f7485d5`) adds the minimum engine surface a second
captain needs, all additive and default-off:

- `Navi::getNaviIndex()` / `Navi::getOtherNaviIndex()` (`include/Navi.h`) are the
  `GET_OTHER_NAVI` equivalent over the existing spawn index `mNaviID`.
- `NaviMgr::getOtherNavi`, `getActiveNavi`, `getAliveOrima`, `getDeadOrima`,
  `setActiveNavi`, `informOrimaDead`, `isNaviDead`, `hasSecondNavi`,
  `getNaviCount`, `resetCaptainRoster` (`include/NaviMgr.h`,
  `src/plugPikiKando/naviMgr.cpp`) delegate active/dead selection to an
  engine-free `P2CaptainRoster` (`pc_port/pc_p2_captain_roster.h`). With one
  Navi every query resolves to slot 0, so the single-captain path is unchanged.
- `pc_p2_second_captain.cpp` implements the opt-in route keyed on
  `PIKMIN_P2_SECOND_CAPTAIN` (`navi_capacity`, `prepare_second_captain_assets`,
  `birth_second_captain`). `NaviMgr::ensureSecondNaviShapeObject()` builds
  `mNaviShapeObject[1]` from a fresh uncached `pikis/nv3Model.mod`.
- `pc_p2_captain.cpp` now maps slot N to `naviMgr->getNavi(N)` and routes the
  adapter's `switchActive`/`captureCaptain`/`damageCaptain` into
  `NaviMgr::setActiveNavi`/`informOrimaDead` via optional `notifyActive` /
  `notifyKnockout` host callbacks (`pc_p2_captain.h`). Slot 1 binds only when a
  second Navi is actually present; otherwise the adapter refuses as before.
- `GameCoreSection` consults `pc_p2_captain::navi_capacity()` before
  `NaviMgr::create` (`gameCoreSection.cpp:1494`).

**The live spawn is deliberately gated shut.** `second_captain_live_allowed()`
returns false, so `navi_capacity()` is 1 even with the env var set: no second
Navi is constructed, no asset is prepared, and single-captain play is
byte-identical. Porting the missing systems first is the next slice.

## Remaining work for real two-captain play (`file:line`)

1. **Per-captain follow/whistle AI and split squad.** `Navi::callPikis` /
   `letPikiWork` / `reviseController` and the `CPlate` party
   (`navi.cpp:612`, `navi.cpp:175-251`) assume one captain; squad assignment
   uses `naviMgr->getNavi()` (`generator.cpp:1193,1197,1199`). Each Piki already
   stores `Piki::mNavi` (`Piki.h:318`), so the follow-up is to route
   `getActiveNavi()`/captain-aware follow targets instead of the first Navi.
2. **Split camera.** Startup binds one camera to the first Navi
   (`gameCoreSection.cpp:1214 cameraMgr->startCamera(naviMgr->getNavi())`;
   `pcamcameramanager.cpp:163 naviMgr->getNavi(0)`), and `Navi::mNaviCamera`
   is copied from the first captain (`genNavi.cpp:68`, `navi.cpp:160`). Needs a
   per-captain camera or an active-captain camera switch.
3. **Controls / Kontroller.** `Navi::Navi` builds `new Kontroller(naviID + 1)`
   (`navi.cpp:513`) and only captain 0's controller is started
   (`gameCoreSection.cpp:1277 naviMgr->getNavi(0)->startKontroller()`). P2
   second-pad / split control mapping is not ported.
4. **Whistle/cursor and HUD.** Cursor and whistle state live on each `Navi`
   (`Navi::mCursorPosition`, `mWhistle*`, `navi.cpp`); HUD reads
   `naviMgr->getNavi(0)` (`drawGameInfo.cpp:195,282,317`) and the player-state
   model uses `naviMgr->mNaviShapeObject[0]` (`playerState.cpp:821`). Needs
   active-captain routing.
5. **Survivor-gated game over.** `NaviDeadState::init` sets the global
   `GameStat::orimaDead` (`naviState.cpp:3190`), `gameCoreSection.cpp:2092`
   keys off `mNavi->mHealth`, and `newPikiGame.cpp:2779` sets
   `GAMEEND_NaviDown`. Must become "game over only when every present captain
   is down", using `NaviMgr::getAliveOrima()` / `isNaviDead()`.
6. **Knockout integration.** Replace direct `NaviState` transitions to
   `NAVISTATE_Dead` (`navi.cpp:434`, `naviState.cpp:1511,2852`) with a call that
   also invokes `NaviMgr::informOrimaDead` and `P2CaptainPolicy::damage` so
   policy and engine stay in sync. `P2CaptainAdapter::damageCaptain` is the
   seam.
7. **Death/corpse, drop and reward** remain family/test-owned as before.

Until all of the above exist, the gate in `second_captain_live_allowed()`
stays closed and this lane still does **not** claim live two-captain gameplay.

## Limits and next slices

- Live binding is slot 0 only by default. `pc_p2_captain.cpp` maps slot N to
  `naviMgr->getNavi(N)`, but no second Navi is created unless the closed live
  gate is opened. There is no live two-captain runtime and this slice does not
  claim one.
- The adapter's actor ids come from a pointer-keyed registry in
  `pc_p2_captain.cpp`. A freed-then-reused `Piki*` within one scene can inherit
  an id; captor families must release a captive before its actor is destroyed
  (same lifetime rule as the source captor FSMs). `teardown()` clears it.
- No caller wires `pc_p2_captain.cpp` yet; it is additive and inert until
  `pc_p2_captain` functions are invoked from a captor family.
- Held bombs and task ownership are represented only through the generic
  ownership table; dedicated held-item semantics remain to be audited.
- Two-player mode and President substitution are modeled as `present` slots but
  have no runtime acceptance.

Consumers (29/30/16) can implement against this interface now; a fake adapter
alone is not end-to-end acceptance.
