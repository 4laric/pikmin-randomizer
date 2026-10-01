# Two-captain / squad-ownership / controller pin audit (#819; consumer #562)

Lane `two-captain-controller-pin`, issue #819 (OPEN, assigned 4laric;
parent #130). Downstream consumer: p2-challenge-ch-mat-crawler-p1 (#562
gen 10 rev 27; #129 resolved, gaps #130 two-captains and #131 White
Pikmin remain; verification 3ed0110d recorded prerequisite_resolved=true
for the staged boot). Recovery c794278c...d622. Read-only audit at native
pin a95040b6; no native/shared edits, no builds, no launches, no ADMIT.
All six gates UNTESTED. Captain safety #632: not applicable, no runtime
(read-only source audit); guard standard
`scripts/p2_fixture_captain_guard.h` sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
recorded for the consumers re-run.

## Verdict: paths half-exist; second-Navi construction is broken at three points

### FOUND: second-captain instantiation (owner: engine NaviMgr)

`native/src/plugPikiKando/naviMgr.cpp:65-70`
`Creature* NaviMgr::createObject()` does `new Navi(mNaviParms, mNaviID);
mNaviID++` (decl `include/NaviMgr.h:175`). Indexed instantiation supports
N navis. Owner of any spawn call: the engine system layer (no second call
exists - see ABSENT below).

### FOUND: second shape object never built (owner: engine NaviMgr construction)

`naviMgr.cpp:43-47`: the constructor builds only `mNaviShapeObject[0]`
(shape + anim mgr); index 1 of `mNaviShapeObject[2]` (`NaviMgr.h:193`)
stays uninitialized. `Navi::Navi(CreatureProp*, int)` (`navi.cpp:450`)
then reads `mNaviShapeObject[mNaviID]` (`:490`) and dereferences it
(`:492-493`). A naviID=1 construction reads garbage and crashes. This is
the first hard blocker for gap #130.

### FOUND: second-captain selection (owner: engine NaviMgr)

`naviMgr.cpp:93-102` `NaviMgr::getNavi(int idx)`: bounds-checked indexed
selection; the comment explicitly names leftover multiplayer
out-of-bounds requests. Decls `NaviMgr.h:178-179`. Sole indexed consumer
at this pin: `src/plugPikiNakata/pcamcamera.cpp:148` (`getNavi(1)` into
the camera array). Every other caller uses `getNavi()` (first object).

### FOUND: per-Navi controller binding (owner: engine Navi)

`navi.cpp:513`: `mKontroller = new Kontroller(naviID + 1)` inside the
ctor (member `Navi.h:159`, ctor decl `Navi.h:47`, id `Navi.h:248`).

### FOUND: per-pad routing (owner: engine Controller/ControllerMgr)

`controllerMgr.cpp:59-67` `updateController(Controller*)` routes
`sControllerPad[controller->mPlayerNum - 1]` (sticks, buttons, triggers,
DPAD, START) and calls `updateCont`. Driven per Controller via
`src/sysCommon/controller.cpp:70` and per Navi via `navi.cpp:1058`.
`Controller(int playerNum)` (`Controller.h:45`), `mPlayerNum`
(`Controller.h:77`, "1 => use controller port 0, etc"). Two pads are
routable end-to-end once two navis exist.

### FOUND: global keyDown is port-0-only (owner: engine ControllerMgr)

`controllerMgr.cpp:42-45` hardcodes `sControllerPad[0]`. Any gameplay
query through this path ignores player 2. Second hard blocker: must take
a player index (or route through the owning Navi) under #186 review.

### FOUND: squad-ownership split exists (owner: engine actors)

`Piki::mPlayerId` (`Piki.h:282`) vs `Navi::mNaviID` (`Navi.h:248`);
enforced at `aiFree.cpp:200` (contact ownership),
`aiTransport.cpp:1041` (`piki->mNavi->mNaviID`), `piki.cpp:837`, pluck
gating `navi.cpp:1219` (`mNaviID == piki->mPlayerId || mPlayerId == -1`),
whistle effects branching on id 0/1 (`naviState.cpp:1688,1845,1890`).
The split the second captain needs is already modeled.

### FOUND: versus explicitly never spawns a second navi

`include/FlowController.h:63`: "indicator of an (unimplemented) VS mode -
never TRUE because we never spawn a second navi." Explicit source
statement of the gap.

### ABSENT: second-Navi spawn owner

No callsite in the audited tree invokes `createObject` a second time;
nothing owns second-Navi spawning. Reason: versus unimplemented plus the
shape-object gap. This is the exact missing provider for #130.

## Downstream packet (consumer #562)

- Consumer: p2-challenge-ch-mat-crawler-p1 (#562, blocked gen 10 rev 27).
- Re-run check: consumer verification 3ed0110d (prerequisite_resolved=true
  on the staged boot) must be re-run after the #130 engine fix; expect the
  two-captain markers plus unchanged boot markers, exit 0, no CAPTAIN_DOWN.
- Engine fix ownership (not this lane): a bounded engine lane under #186
  shared-hook review owning (1) `mNaviShapeObject[1]` init in
  `NaviMgr::NaviMgr`, (2) a second-`createObject` spawn path, (3) player
  index for `ControllerMgr::keyDown`. Files:
  `native/src/plugPikiKando/naviMgr.cpp`,
  `native/src/sysDolphin/controllerMgr.cpp`
  (+ decls `native/include/NaviMgr.h`, `native/include/Controller.h`).
  Build membership to verify read-only at fix time (this pin: preview
  TU membership pattern per CMakeLists; the fix TU set above).
- #131 (White Pikmin) is out of scope here.

## Pins

- Native audit pin a95040b6 (blobs: NaviMgr.h `89e0d0772e167954215562feee4a718c2d089d4e`,
  naviMgr.cpp `4295c874cc6253ca3617e646ecac2d6359af9abe`, Controller.h `a6159320ddb9d1a3ca5c5632d9bb3a65f0804fbf`,
  controllerMgr.cpp `c2c01c3af3a5dee162fab59639ae99a2fc3f8172`).
- Root a5090371 (lane branch `codex/two-captain-controller-pin`).
- Tool + 12 tests green; this doc. No ADMIT.
