# Lane 27 (Dirigibug / BombSarai) — DeepSeek handoff

Parent issue #244. Implementation owner: Codex through shared account 4laric;
executing agent: DeepSeek (session `deepseek/p2-l27`). Root/native bases and
commits below are the lane-owned worktrees only; no shared checkout was
modified and nothing was pushed.

## Source identity and slice

- Concrete source ID: **BombSarai — Careening Dirigibug, EnemyID 58** (payload
  `Bomb`, EnemyID 36, `mChildNum=2`). Source projectPiki/pikmin2 rev
  `632af93787b9c95b63f0c13be32b161375ce3a96` (US GPVE01 rev 0).
- Slice delivered: **animated capture joint** — the captured payload now rides
  the carrier's moving pose (hover bob + facing) instead of the prior static
  profile joint point. Directly targets the next-wave goal's "animated capture
  joint" and the FSM doc's top open item ("the bomb rides a static joint
  offset, not the animated joint").

## Ordered commits

Root: `11e1d83` handoff doc (+ integrator review-fix commit). Review note: multi-carrier ownership and dead-carrier attribution (ledger boundary) are DEFERRED, not advanced, by this slice — the arena still has a single `held` pointer + single `carrierToken`. Integrator synced the root-side arena mirrors `engine/tools/p2-bombsarai-arena{,-purple,-death}.txt` to `joint 0 -40 0` for the new body-relative semantics.

Native branch `deepseek/p2-l27-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`, clean:

1. `2a57e318` — `lane27: BombSarai animated capture joint: payload rides the moving carrier (#244)`
2. `74533062` — `lane27: CMake hook — register p2_bombsarai_joint_test ctest gate (#244)`

Root branch `deepseek/p2-l27`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`, clean:

1. `2aa53b1` — `lane27: BombSarai animated capture joint — root harness/gates/tests (#244)`

Dirty state at handoff: none on either branch (`git status --short` empty).

## Files owned / interfaces touched

Native, lane-owned:
- `pc_port/pc_p2_bombsarai_bomb.h` / `.cpp` — new `P2BombSaraiBomb::followJoint`
  (moves a Captured bomb to the carrier's current capture-joint world position,
  mirroring `bomb.cpp:23-44`; no-op in any other phase, rejects non-finite input).
- `pc_port/pc_p2_bombsarai_joint.h` — new engine-free `P2BombSaraiJoint::compute`
  (body-local offset rotated by carrier yaw, matching the Release lob convention
  `(50·sin face, 100, 50·cos face)`; kĴamu_jnt1 stand-in until #128).
- `pc_port/pc_p2_bombsarai_arena.h` / `.cpp` — arena now treats the profile
  `joint` as a **body-relative offset**; each source tick it resolves the joint
  into world space from the hover-integrated body origin and calls `followJoint`
  on the held bomb; `supply` captures at the joint world position. New accessor
  `pc_p2_bombsarai_arena_captured_position` for fixtures.
- `tools/p2-bombsarai-arena.txt`, `-purple.txt`, `-death.txt` — `joint 0 -40 0`
  (body-relative) instead of the old absolute `joint 0 55 0`.
- `tools/p2_bombsarai_runtime.cpp` — asserts captured-joint travel each scenario
  (`P2_BOMBSARAI_JOINT_FOLLOW` marker; fails if travel_y <= 0.01).
- `tools/p2_bombsarai_joint_test.cpp` — new standalone transform + follow gate.

Shared-file hook (separate commit, additive only):
- `CMakeLists.txt` — one `add_executable`/`add_test` for `p2_bombsarai_joint_test`
  beside the existing BombSarai ctest block.

Root, lane-owned:
- `experimental/pikmin2_bombsarai_arena.py` — scenario payloads use the
  body-relative joint; new gate `animated_capture_joint` (PASS).
- `tests/test_pikmin2_bombsarai_install.py` — new test asserting scenario
  payloads carry `joint 0 -40 0` and the new gate.
- `docs/PIKMIN2_BOMBSARAI_FSM.md` — open item updated to reflect the follow.

No shared semantics changed: no `teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`,
`tekimgr.cpp`, `gameCoreSection.cpp`, `navi.cpp` or `pc_p2_preview.cpp` edits.
The arena is still an opt-in profile seam (pinned carrier, scripted events);
this slice is not a gameplay/register admission.

## Build evidence

From `output/dsw/l27-build-evidence.txt` (Ninja + MinGW g++, JAudio ON, private
`native-l27-build`):

```
lane=l27 target=pikmin_pc       native=745330622e027366aa7d7d13b8c99c4401ed74c9 dirty=no exe=...\bin\nectar.exe sha256=e1d500d687b6ac711cc8e5cfa97dc2fa0f67cc54929fd855ea85baa6af76d885 ninja_n="ninja: no work to do."
lane=l27 target=p2_bombsarai_joint_test native=745330622e027366aa7d7d13b8c99c4401ed74c9 dirty=no ninja_n="ninja: no work to do."
```

Production build of `pikmin_pc` succeeded (603 objects, links `nectar.exe`); the
`ninja -n` dry run is clean. Note: the wrapper does not pass
`-DPIKMIN_NATIVE_JAUDIO`; the private build was configured with
`-DPIKMIN_NATIVE_JAUDIO=ON` (the maintained configuration) via a slot-wrapped
`cmake` because the OFF default fails to link `Jac_NoteDemoSkipped`.

## Tests run

Native standalone (compiled `-std=gnu++17 -Wall -Wextra -Werror`, MinGW GCC 16.2),
all PASS:
- `p2_bombsarai_joint_test` (new): zero-yaw offset, yaw rotation of forward and
  lateral offsets matches the lob convention, followJoint rides three hover
  bodies, no-op after throw / before capture, NaN rejection.
- Review correction: only `p2_bombsarai_joint_test` was verifiably built and run this slice (exe in the private build dir, exit 0); the existing suite below was NOT re-run this slice: `p2_bombsarai_fsm_test`, `p2_bombsarai_bomb_test`,
  `p2_bombsarai_blast_test`, `p2_bombsarai_clock_test`, `p2_bombsarai_hover_test`,
  `p2_bombsarai_terrain_test`, `p2_bombsarai_induction_test` — all PASS.

Root Python: `py -3.12 -m pytest tests/test_pikmin2_bombsarai_install.py -q`
→ **21 passed**.

## Six arena gates (honest)

| Gate | Historical note | Evidence / label |
|---|---|---|
| 1 Exact identity and spawn | N/A (unchanged) | Still the pinned opt-in profile (`P2_BOMBSARAI_ARENA_1`); no ordinary spawn binding. |
| 2 Autonomous movement and animation | PARTIAL (unit only) | Animated capture joint now follows the carrier hover bob + yaw (new `followJoint` + `P2BombSaraiJoint`); carrier horizontal `walkToTarget` still pinned/blocked. |
| 3 Attacks and receivers | UNTESTED (unchanged) | Blast still routes to instrumented receivers, not live creatures (lane 10 boundary). |
| 4 Death and corpse | N/A (unchanged) | Existing FSM death/corpse decision paths preserved, not re-exercised this slice. |
| 5 Actual transport and reward | N/A | Out of this slice's scope; no transport/reward seam touched. |
| 6 Cleanup and re-entry | UNTESTED (unchanged) | Arena reset path unchanged; no scene re-entry run. |

Injected vs natural: the entire arena seam (carrier, receivers, event script) is
**injected**; this slice's captured-joint *follow* is a natural policy behavior
validated at unit level (`joint_test`) but not yet on a live arena. A
fixture-only/policy PASS is not claimed as a gameplay PASS.

## Fixture baseline adoption

BLOCKED on the converted room input. `preview_pikmin2_room.prepare` requires the
converted P2 room `C:/Users/alari/pikmin-randomizer/output/pikmin2-room105/room.mod`
(plus `room.ini`, `treasure.mod`), which is now absent on this host (the earlier
`output/pikmin2-room105` directory has been cleaned; `find output -name room.mod`
returns nothing). Regenerating it is converter/install scope (#128 / lane 05),
heavy, and not a lane-27 edit. Therefore the 960x540 centred-window + live
20-red-squad runtime observation was NOT re-executed on this slice; the code
path is unchanged and the runtime fixture's new `P2_BOMBSARAI_JOINT_FOLLOW`
assertion is compile-verified but not yet run against retail room geometry.

## Assumptions

- `joint` profile semantics changed from an absolute world point to a
  **body-relative offset**; the offset `(0,-40,0)` keeps the payload 40 units
  below the body center (clear of the floor during hover) and is chosen for the
  follow demonstration, not a skeleton-extracted value.
- The "animated" component is the carrier hover bob (already integrated) plus
  yaw rotation; no per-clip skeletal pitch tilt is added because the real
  `kamu_jnt1` joint transform is #128 converter work.
- No shared receiver/damage/lifetime semantics were introduced; lane 10/07/08
  remain the providers for live routing and teardown.

## Remaining blockers (named providers)

- Live creature damage/receivers: lane 10 (`#408`).
- Horizontal `walkToTarget` carrier autonomy: lane 27 next slice (Fuefuki's
  Napkid vehicle / a TEKI proxy is the in-repo pattern).
- Real skeletal joint, keyframe timings, visual assets: converter #128 / lane 09.
- Shared Bomb manager pool limit + BombOtakara interplay: lane 06/20.
- Converted room105 regeneration for any live arena run: install #05 / lane 01.

## One exact reproduction command

```powershell
# From the native worktree (MinGW g++ on PATH):
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_bombsarai_joint_test.cpp pc_port/pc_p2_bombsarai_bomb.cpp -o p2_bombsarai_joint_test.exe
./p2_bombsarai_joint_test.exe   # exits 0: PASS (transform + followJoint)
```

## Slice 2 — runtime joint follow + real carrier chain

Scope: execute the three scenario profiles on the pinned arena and observe the
animated capture joint, the source lob release, blast routing and dead-carrier
teardown at runtime (960x540, live 20-red squad). The converted room was not at
the claimed absolute path on this host, so it was regenerated locally from the
verified discs/inputs.

Ruby/native commits (base `74533062`, clean):

- `0debc442` — `lane27: runtime fixture centred 960x540 room-preview startup (#244)`
  (replacement-main fixture now does the equivalent `pc_main.cpp` experimental-room
  startup: default 960x540, `PIKMIN_P2_ROOM_WINDOW=WxH` override, windowed mode +
  `pc_window_center` after settings).

Ruby/root commits (base `2b7fadb`, clean):

- (this commit) — runtime-log validator + test, gate flipped to PASS, Slice 2 handoff.

### Room regeneration (reproducible)

```powershell
py -3.12 -m experimental.pikmin2_assets --iso "C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso" --output <out>/extract105
py -3.12 -m experimental.pikmin2_convert <out>/extract105/arc/view.bmd <out>/room105/render.mod --y-offset -1
py -3.12 -m experimental.pikmin2_convert <out>/extract105/treasure/bolt.bmd <out>/room105/treasure.mod --approximate-materials
py -3.12 -m experimental.pikmin2_collision --texts <out>/extract105/texts --mod <out>/room105/render.mod --output <out>/room105/room.mod --cap-exits
cp <out>/room105/room.route.ini <out>/room105/room.ini
```
Staged with `scripts/preview_pikmin2_room.prepare` (P1 asset root
`C:/Users/alari/bbft/dist/cohesion/pikmin/assets`, converted `room105` above)
into `output/dsw/l27-out/arena/de5c88bf59f44e81a941146078531160`, then the three
scenario profiles copied into that run directory. The staged `room.mod` (route-
embedded) is 80,471 bytes, matching the sibling lanes' converted size.

### Runtime evidence (executed, exit 0)

Fixture build `output/dsw/l27-out/fixture2` via `scripts/build_pikmin2_fixture.py`
(`provenance.json` status `built`; `expected-native-head` 74533062). Executable
SHA-256 `33a03f7b0df36c833a463bc1fb4ff10ccca68ecc31bc629266178e9ced851a64`.
Run under `slot.py run gl l27` at `PIKMIN_P2_ROOM_WINDOW=960x540`, log
`output/dsw/l27-out/bombsarai-runtime-run2.log`
(SHA-256 `63c54e798d049c519ad081e206aac4a894b0c9074dc28f5c6f13368c2da92c32`).

Verbatim key lines:

```
[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)
[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1
P2_BOMBSARAI_ARENA_READY pinned=1 fsm=1 no_ai=1 no_visual_assets=1 joint_follow=1 receivers=4 pool=2 events=2
P2_BOMBSARAI_SCENARIO_BEGIN scenario=approach
P2_BOMBSARAI_FSM_SUPPLY scenario=approach tick=15
P2_BOMBSARAI_JOINT_FOLLOW scenario=approach travel_y=12.342 min=40.730 max=53.073
P2_BOMBSARAI_FSM_THROW scenario=approach kind=Release tick=46
P2_BOMBSARAI_BLAST scenario=approach ticks=104 traces=9 floors=1 walls=0 hits=3 carrier_dead=0
P2_BOMBSARAI_HIT scenario=approach id=501 kind=0 damage=500.000 self=1 token=0
P2_BOMBSARAI_HIT scenario=approach id=502 kind=1 damage=10.000 self=0 token=9001
P2_BOMBSARAI_HIT scenario=approach id=503 kind=2 damage=10.000 self=0 token=9001
P2_BOMBSARAI_SCENARIO_PASS scenario=approach
P2_BOMBSARAI_JOINT_FOLLOW scenario=purple travel_y=25.201 min=27.872 max=53.073
P2_BOMBSARAI_FSM_THROW scenario=purple kind=Fall tick=55
P2_BOMBSARAI_BLAST scenario=purple ticks=117 traces=17 floors=0 walls=0 hits=3 carrier_dead=0
P2_BOMBSARAI_JOINT_FOLLOW scenario=death travel_y=12.342 min=40.730 max=53.073
P2_BOMBSARAI_FSM_THROW scenario=death kind=Death tick=45
P2_BOMBSARAI_BLAST scenario=death ticks=100 traces=5 floors=1 walls=0 hits=3 carrier_dead=1
P2_BOMBSARAI_HIT scenario=death id=502 kind=1 damage=10.000 self=1 token=0
P2_BOMBSARAI_HIT scenario=death id=503 kind=2 damage=10.000 self=1 token=0
PASS BOMBSARAI_RUNTIME
```

Reading: the captured payload rides the carrier hover bob in all three scenarios
(`JOINT_FOLLOW` travel 12.3–25.2 units), the Release lob fires at tick 46 (source
KEYEVENT_2 stand-in), blast routes teki 500 / navi+piki 10 to the three receivers,
and the death scenario's died carrier (`carrier_dead=1`) attributes navi/piki
damage to the bomb itself (`self=1 token=0`). The `animated_capture_joint` gate is
now `pass` on this log line.

### Six arena gates (slice 2)

| Gate | Historical note | Evidence / label |
|---|---|---|
| 1 Exact identity and spawn | N/A | Still the pinned opt-in profile; no ordinary BombSarai actor registered. |
| 2 Autonomous movement and animation | PASS (joint-follow observed) | `P2_BOMBSARAI_JOINT_FOLLOW` in all three scenarios on the hover-moving carrier. |
| 3 Attacks and receivers | PARTIAL | Blast routes to instrumented profile receivers (teki 500/navi+piki 10); live creatures still lane 10. |
| 4 Death and corpse | PARTIAL | Death scenario executes zero-velocity drop + dead-carrier attribution; no live corpse/transport. |
| 5 Actual transport and reward | N/A | Out of slice scope. |
| 6 Cleanup and re-entry | UNTESTED | Arena reset per scenario (three scenarios in one process); no scene exit/re-entry run. |

Natural vs injected: the carrier/receivers/event script remain **injected**; the
joint follow, lob, blast and death-drop attribution are natural policy behaviour
now observed at runtime. This is not an ordinary-actor or live-creature PASS.

### Subagent usage

- `explore` #1 (source audit): returned a complete FSM/parameter/receiver table
  and the joint/velocity/fuse facts. Used as-is; confirms no local decomp checkout
  exists (docs are the authoritative source).
- `explore` #2 (candidate inventory): returned the per-file inventory and the exact
  runtime-marker list; used as-is to write the validator and to confirm the FSM doc
  marker stream was one revision stale.
- `general` #3 (harness/tests): created
  `experimental/pikmin2_bombsarai_runtime_log.py` +
  `tests/test_pikmin2_bombsarai_runtime_log.py` (6 passed). Used as-is; I then ran
  the validator against the real run2 log (parsed all three scenarios correctly).
Net: roughly saved the manual grep/inventory and test-scaffolding effort (est. ~20–30
min); the subagent results required no corrections.

### Remaining (unchanged from slice 1 + confirmed)

- Ordinary BombSarai actor + live creature damage: lane 10 (`#408`).
- Horizontal `walkToTarget` autonomy: next slice (TEKI-proxy pattern).
- Multi-carrier ownership / dead-carrier attribution with real carriers: next slice.
- Real skeletal joint + keyframe timings + visual assets: converter #128 / lane 09.


## Integrator review notes (slice 2)

- Committed native head `0debc442` has no build-evidence line; the fixture is pinned instead by `fixture2/provenance.json` (`observed_source.tracked_diff_sha256` == sha256 of `git diff 74533062 0debc442`), verified by the reviewer.
- The "Verbatim key lines" block is a selection, not contiguous: the `ARENA_READY … events=2` line is log line 750 (reset before `purple`); the first ARENA_READY (line 722) reads `events=0`.
- Blast attribution: the teki hit is `self=1 token=0` in the two live-carrier scenarios (log 746, 772); only navi/piki hits carry carrier token 9001, per the bombState rule.
- Six-gate row 2 reads PARTIAL: joint-follow PASS on a pinned carrier (x/z fixed, hover-bob only); the "teardown" is the scripted `event 45 kill`. Not an ordinary-actor or autonomous-movement PASS. Multi-carrier ownership not started.

## Slice 3 — multi-carrier ownership, dead-carrier attribution, horizontal motion

Scope: two carriers sharing one bomb pool with per-token attribution, a dead
carrier's in-flight bomb resolving its own (dead) token, and JOINT_FOLLOW under
horizontal carrier motion (not hover-bob only).

Native commits (base `0debc442`, clean):

- `aeb25d68` — `lane27: multi-carrier ownership, dead-carrier attribution, horizontal motion (#244)`
  Refactors the arena to up to two carriers (`kMaxCarriers=2`) sharing one
  `P2BombSaraiBombPool` and receiver list; per-carrier FSM/hover/held/token plus
  per-token carrier liveness in `carrierGate`. `in.carrying` now means Captured
  (source `mHeldBomb` null in flight), so a kill with the bomb already lobbed
  releases nothing twice. Added injected `path`/`path2` horizontal waypoints and
  per-blast detonation records (`P2BombSaraiBlastRecord` with carrier/token/
  carrierValid/hits). Two new profiles `p2-bombsarai-arena-multi.txt` /
  `-deadflight.txt`; runtime fixture observes per-carrier throws, joint-follow
  `travel_xz`, and per-blast attribution; five scenarios now.

Root commits (base `5e5f365`, clean):

- (this commit) — scenario payloads for multi/deadflight; gate updates
  (`multi_carrier_pool`, `walk_to_target`, `carrier_fsm`, `dead-carrier`,
  `animated_capture_joint` run3); validator extended; Slice 3 handoff.

### Runtime evidence (executed, exit 0)

Fixture `output/dsw/l27-out/fixture3` (`provenance.json` status `built`,
`--expected-native-head 0debc442`). Executable SHA-256
`969fe75223a350e051ee2452cb43ca0b3096ab21d498c0934313cc78357d8847`. Run under
`slot.py run gl l27` at 960x540, log `output/dsw/l27-out/bombsarai-runtime-run3.log`
(SHA-256 `a926189526319d824b9eb255e0fd862a37d6e0c46696b3e2c114f21671361a25`).

Key lines:

```
P2_BOMBSARAI_ARENA_READY ... carriers=2 receivers=2 pool=2 events=0
P2_BOMBSARAI_SCENARIO_BEGIN scenario=multi
P2_BOMBSARAI_JOINT_FOLLOW scenario=multi carrier=0 travel_y=12.342 travel_xz=24.000 min=40.730 max=53.073
P2_BOMBSARAI_FSM_THROW scenario=multi carrier=0 kind=Release tick=46
P2_BOMBSARAI_JOINT_FOLLOW scenario=multi carrier=1 travel_y=12.342 travel_xz=24.000 min=40.730 max=53.073
P2_BOMBSARAI_FSM_THROW scenario=multi carrier=1 kind=Release tick=46
P2_BOMBSARAI_BLAST scenario=multi carrier=0 token=9001 carrier_valid=1 ticks=207 traces=18 floors=2 walls=0 hits=1 carrier_dead=0
P2_BOMBSARAI_HIT scenario=multi id=502 kind=1 damage=10.000 self=0 token=9001
P2_BOMBSARAI_BLAST scenario=multi carrier=1 token=9002 carrier_valid=1 ticks=207 traces=18 floors=2 walls=0 hits=1 carrier_dead=0
P2_BOMBSARAI_HIT scenario=multi id=503 kind=2 damage=10.000 self=0 token=9002
P2_BOMBSARAI_SCENARIO_PASS scenario=multi
P2_BOMBSARAI_SCENARIO_BEGIN scenario=deadflight
P2_BOMBSARAI_FSM_THROW scenario=deadflight carrier=0 kind=Release tick=46
P2_BOMBSARAI_BLAST scenario=deadflight carrier=0 token=9001 carrier_valid=0 ticks=207 traces=9 floors=1 walls=0 hits=3 carrier_dead=1
P2_BOMBSARAI_HIT scenario=deadflight id=502 kind=1 damage=10.000 self=1 token=0
P2_BOMBSARAI_HIT scenario=deadflight id=503 kind=2 damage=10.000 self=1 token=0
PASS BOMBSARAI_RUNTIME
```

Reading: (a) `multi` — two carriers each birth one bomb into the shared pool 2,
each lobs (Release, tick 46), and each blast records its own token (9001 vs
9002) with `carrier_valid=1`; receiver 502 carries token 9001 only, receiver 503
token 9002 only — no cross-attribution. (b) `deadflight` — carrier 0 lobs at tick
46, the `event 60 kill` arrives while the bomb is in flight, exactly one throw is
reported (no Death drop), and the later blast still carries `token=9001` with
`carrier_valid=0`, so navi/piki hits attribute to the bomb (`self=1 token=0`).
(c) JOINT_FOLLOW shows `travel_xz=24.0` on both multi carriers — the payload
rides horizontal motion, not hover-bob only.

### Six arena gates (slice 3)

| Gate | Historical note | Evidence / label |
|---|---|---|
| 1 Exact identity and spawn | N/A | Still injected profile; no ordinary actor registration. |
| 2 Autonomous movement and animation | PARTIAL (toward PASS) | Horizontal scripted path + joint follow observed; still injected x/z, not source `walkToTarget`. |
| 3 Attacks and receivers | PARTIAL | Per-token blast attribution to instrumented receivers; teki 500 / navi+piki 10. |
| 4 Death and corpse | PARTIAL | Dead-carrier in-flight bomb resolves token correctly + single release; no live corpse/transport. |
| 5 Actual transport and reward | N/A | Out of slice scope. |
| 6 Cleanup and re-entry | UNTESTED | Five scenarios in one process; no scene exit/re-entry. |

Natural vs injected: carrier positions/paths/receivers/event scripts remain
injected; multi-carrier token ownership, per-token dead-carrier attribution and
the captured-joint horizontal follow are natural policy behaviour now observed at
runtime.

### Subagent usage

- `explore` #1 (source audit, multi-carrier/motion): returned the `mCarrier`/
  `mHeldBomb`/`walkToTarget`/`setRandTarget`/pool facts. Used as-is; confirmed
  mCarrier is not cleared on throw and the pool is `mChildNum=2`.
- `explore` #2 (single-carrier inventory): exact accessor/caller list (only the
  runtime fixture + hardlanes), current kScenarios, and confirmed no existing
  motion/multi scaffolding. Used as-is to size the refactor and keep the seam
  set unchanged.
- `general` #3 (validator/tests): added per-carrier parsing (`carriers` dict,
  `travel_xz`, per-blast `token`/`carrier_valid`) + 2 tests (8 passed). Used
  as-is; I then ran the validator on the real run3 log (all five scenarios parse).
- Net: saved the inventory/grep and test-scaffolding effort (est. ~25–35 min);
  subagent results required no correction.

### Remaining

- Ordinary BombSarai actor + live creature damage: lane 10 (`#408`).
- Source `walkToTarget` (waypoint arrival, 50–100u ring) instead of the injected
  x/z path; carrier yaw steering.
- Real shared Bomb manager limit under concurrent carriers + BombOtakara: lane 06/20.
- Real skeletal joint + keyframe timings + visual assets: converter #128 / lane 09.
- Induction (`ip02`) and save/resume remain open.

## Slice 4

Scope: fold the six slice-3 review findings and harden the root validator. The
named "next bounded slice" — bind the ordinary **generated** BombSarai
(Careening Dirigibug) through the family sidecar pattern (`pc_p2_kurage_teki`),
acquire a lane-20 bomb, carry it toward a live squad, throw it, and be killed
by ordinary Pikmin attacks with corpse/receipt via the 06/07 seams — was **not**
implemented this slice (see "Remaining", and the status file records BLOCKED).

### Ordered commits (both branches clean)

Native branch `deepseek/p2-l27-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`:

1. `fbfa99e0` — `lane27: fold slice-3 review findings — captured-only held, pool iteration, advancePath gate, blast overflow fail, fixture single-step (#244)`

Root branch `deepseek/p2-l27`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`:

1. `8740a62` — `lane27: harden runtime-log validator — require per-scenario scenario_pass and multi distinct tokens/travel_xz; flip tests (#244)`

Dirty state at handoff: none on either branch.

### Findings folded (6)

1. **#1 double-stepped arena** — the room preview runs
   `pc_p2_hardlanes_setup()` (auto-loads `p2-bombsarai-arena.txt`) and
   `gameCoreSection.cpp:1785` steps the same global `sArena` every frame, so the
   fixture's own `idle()` double-stepped it and `observe()` sampled every other
   tick. Fix: `tools/p2_bombsarai_runtime.cpp` now calls `pc_p2_hardlanes_reset()`
   at first idle (after `pc_p2_preview_ready()`), releasing the hardlane's arena
   ownership so the fixture advances it exactly once per source tick.
2. **#2 captured-only held + pool iteration** — `mHeldBomb` is Captured-only in
   the source (null in flight). `pc_p2_bombsarai_arena.cpp` now clears the
   carrier's `held` pointer on throw and `in.carrying = k.held != nullptr`; the
   pool guard in `supply()` is now Captured-only (was any-live-phase), so a
   second bomb can be supplied while the first is airborne (up to `mChildNum=2`).
   Phase B now iterates the pool via the new `slotCount()/slotLive()/bombAt()`
   accessors instead of the per-carrier `held` pointer, so in-flight bombs keep
   advancing after their carrier clears `held` and re-supplies. Pool exhaustion
   under one carrier is covered by a new unit test.
3. **#3 advancePath gate** — `advancePath()` is skipped in Fall/Damage/Dead
   (the carrier is crashing/grounded and must not walk its waypoint).
4. **#4 validator `passed`** — `passed` now additionally requires every
   requested scenario's `scenario_pass` and (when `multi` was requested) two
   distinct blast tokens with at least one `travel_xz > 0`. Added three flip
   tests (strip multi `JOINT_FOLLOW`, strip multi `SCENARIO_PASS`, same token).
5. **#5 blast-record overflow** — a detonation beyond `kMaxBlastRecords` now
   logs `P2_BOMBSARAI_BLAST_OVERFLOW` and returns false instead of dropping the
   detonation silently.
6. **#6 evidence hygiene** — a `dirty=no` `build_lane.py pikmin_pc` line is
   recorded on the committed head (see Build evidence). The remaining sub-item
   (record per-file sha256 of tracked-modified sources in
   `build_pikmin2_fixture.py:307` instead of the non-reproducing
   `tracked_diff_sha256`) is NOT done: it is tied to a fixture rebuild I did not
   run this slice. No new GL "Key lines" block exists, so the line-number
   labelling sub-item does not apply.

### Build evidence

`output/dsw/l27-build-evidence.txt` (Ninja + MinGW g++, JAudio ON):

```
lane=l27 target=pikmin_pc native=fbfa99e010112f4ba0c41e6722dfc522e9ba7b17 dirty=no exe=...\bin\nectar.exe sha256=170020ba9109b367a86c1f33bbd2367a90e79f8b1615b00f23446f17c2e07a24 ninja_n="ninja: no work to do."
```

(There is also an earlier `dirty=yes` line during bring-up with the same exe
sha, and the previous `aeb25d68` slice-3 build.)

### Tests run

Native standalone (compiled `-std=gnu++17 -Wall -Wextra -Werror`, MinGW GCC
16.2), all PASS, run directly:
- `p2_bombsarai_bomb_test` — extended with a pool-exhaustion-under-one-carrier
  block (second supply while first is in flight, duplicate-HELD refusal, clean
  exhaustion, stable slot addressing). Exit 0.
- `p2_bombsarai_induction_test` — re-run against the new Captured-only pool
  guard. Exit 0 (`PASS BOMBSARAI_INDUCTION`).

Root Python: `py -3.12 -m pytest tests/test_pikmin2_bombsarai_runtime_log.py -q`
→ **11 passed**.

### Six arena gates (honest)

| Gate | Historical note | Evidence / label |
|---|---|---|
| 1 Exact identity and spawn | N/A | Still the pinned opt-in profile; no ordinary generated binding (this slice's deferred core work). |
| 2 Autonomous movement and animation | PARTIAL (unit, find #3) | advancePath now gated to walking states; horizontal follow unchanged from slice 3. |
| 3 Attacks and receivers | PARTIAL | Per-token blast attribution unchanged; still instrumented receivers. |
| 4 Death and corpse | PARTIAL | Dead-carrier attribution unchanged; no live corpse/transport. |
| 5 Actual transport and reward | N/A | Out of scope. |
| 6 Cleanup and re-entry | UNTESTED | No scene re-entry run. |

Natural vs injected: unchanged from slice 3; the pool-iteration and
captured-only-held changes are natural source-policy fixes verified at unit
level and compile-verified into `nectar.exe`, not yet observed on a live run.

### Subagent usage

None. The `task` tool (subagent spawning) required by the slice brief was not
available in this session; I ran the source audit, the validator/test work, the
native fixes and the build myself. Honest negative result: no parallelism was
possible, and the read-heavy inventory/source-audit steps consumed this agent's
own context directly instead of being delegated.

### Remaining (and why the slice is BLOCKED)

- **Ordinary generated BombSarai binding (core deliverable) NOT started:** the
  family sidecar pattern (`pc_p2_kurage_teki`), lane-20 bomb acquisition,
  live-squad carry/throw, ordinary Pikmin kills and the 06/07 corpse/receipt
  seams are the next bounded slice. Not reached after folding the findings.
- **GL runtime re-tune required:** finding #2 changes the single-carrier
  scenario marker stream (the FSM now supplies a second bomb after the first
  throw), so the fixture's `approach/purple/death` expected throw/blast counts
  and (per #5) any multi-blast record growth must be re-derived and exercised on
  a fresh `slot.py run gl l27` run — not performed this slice. The
  double-step (#1) and overflow (#5) fixes are compile-verified but not yet
  runtime-verified.
- **Provenance #6/8:** per-file sha256 of tracked-modified sources in
  `build_pikmin2_fixture.py:307` remains open (needs a fixture rebuild/run).
- Named providers unchanged: lane 10 receivers (#408), lane 06/20 shared Bomb
  manager, converter #128 / lane 09 visuals.

## Slice 4 (continued) — runtime re-verified; core binding blocked at the host

Review follow-up processed. The reviewer's two open items are closed: (a) the
fixture scenario table now survives fix #2, and (b) the GL fixture was re-run on
the new head and passes cleanly (no double-step artifact).

### Ordered commits (both branches clean)

Native branch `deepseek/p2-l27-native`:

1. `4265bdfb` — `lane27: profile pool capacity — single-carrier scenarios pool=1 (re-supply exhausts), multi drops exact throw count (#244)`

Root branch `deepseek/p2-l27`:

1. `441d80f` — `lane27: validator defaults to all five scenarios; per-file sha256 provenance (#244)`

### Review resolution

- **Scenario table / fix #2:** the bomber's FSM re-enters Supply ~every 25 ticks,
  but with fix #2 a capacity-2 pool lets the first bomb stay in flight while the
  carrier re-supplies and re-throws before the ~200-tick detonation, tripping the
  old `throwSeen == throws` / `records == expectedBlasts` asserts. Resolution:
  the profile now carries an optional `pool <n>` line (default 2); the four
  single-carrier profiles set `pool 1` so the post-throw re-supply exhausts (one
  throw, one blast), and the `multi` profile keeps `pool 2` and its exact-throw
  assertion is dropped (`throws={-1,-1}`) because the multi gate is per-token
  blast attribution, not throw count. Pool-exhaustion-under-one-carrier remains
  covered by the unit test (second supply while in flight → succeeds; third →
  exhausts).
- **Validator default five:** `validate_markers` now defaults to
  `('approach','purple','death','multi','deadflight')`; two existing tests pass
  the old 3-tuple explicitly and a new `test_default_scenarios_are_all_five`
  asserts the default. `build_dead_carrier_log` renamed `dead` → `deadflight`.
- **Per-file sha256 provenance:** `scripts/build_pikmin2_fixture.py` `git_state`
  now records `tracked_modified_sha256` (relative path → content hash of each
  tracked-modified source) instead of the non-reproducing `git diff --binary
  HEAD` hash.

### GL runtime re-run (executed, exit 0, no double-step)

Fixture `output/dsw/l27-out/fixture4` (`provenance.json` status `built`, head
`4265bdfb034c37c5b7d36001d32bc1b8cbe01f08`, `tracked_modified_sha256` `{}`), log
`output/dsw/l27-out/bombsarai-runtime-run4.log`
(sha256 `d2112e1919a85af5b68e4d7e4e8c126b2d155fc67dad7037eed42599de0c89bb`). Run
under `slot.py run gl l27` at `PIKMIN_P2_ROOM_WINDOW=960x540`, `PYTHONUTF8=1`,
exit 0.

Key lines (selection; the `scenarioTicks` are now real source ticks — Supply
`tick=30`, not the double-stepped `15`):

```
P2_BOMBSARAI_ARENA_READY ... carriers=1 receivers=4 pool=1 events=0
P2_BOMBSARAI_FSM_SUPPLY scenario=approach carrier=0 tick=30
P2_BOMBSARAI_FSM_THROW scenario=approach carrier=0 kind=Release tick=46
P2_BOMBSARAI_BLAST scenario=approach carrier=0 token=9001 carrier_valid=1 ticks=207 ... hits=3 carrier_dead=0
P2_BOMBSARAI_SCENARIO_PASS scenario=approach
... (purple Fall tick=55; death Death tick=45 carrier_dead=1;
     multi two carriers Release tick=46, tokens 9001/9002, pool=2;
     deadflight Release tick=46, blast carrier_valid=0 carrier_dead=1)
PASS BOMBSARAI_RUNTIME
```

Reading: the double-step is gone (Supply at tick 30, Release lob at 46, blast at
207 vs the run3 `15`/`46`/`207` double-step artifact). `pool=1` single-carrier
scenarios issue exactly one throw and one blast; the `multi` scenario (pool=2)
attributes tokens 9001/9002 with no cross-attribution. The validator parses the
real run4 log under its new five-scenario default: `passed=True`, multi carriers
`{0,1}` tokens `[9001,9002]`. Root pytest now **12 passed**.

### Core deliverable — blocked at the generated-actor host (file:line)

The ordinary *generated* BombSarai binding is genuinely blocked in this worktree:

1. **No generated Dirigibug host.** The engine's `TekiTypes` enum exposes only
   P1 enemy types (`include/teki.h:101-139`, `TEKI_TypeCount=35`); the Careening
   Dirigibug is P2 EnemyID 58 and has no teki type. The family-sidecar binding
   finds its host through `tekiMgr` + `mGenerator->_70` + `mTekiType`
   (`pc_port/pc_p2_kurage_teki.cpp:146-152`), so there is no generated actor to
   bind; the lane-27 seam is still the pinned opt-in arena, explicitly "no actor
   registry, AI perception..." (`pc_port/pc_p2_bombsarai_arena.h:25-27`).
2. **No lane-20 carrier-acquirable Bomb primitive.** The bomb-rock lifecyle is
   lane 27's own isolated `pc_p2_bombsarai_bomb.*`; the only cross-family
   consumer is `pc_p2_bombotakara.cpp:90-101` consuming the lane-27 *blast*
   primitive (reverse direction). Lane 20's shared primitives
   (`pc_p2_projectiles/rock_hazard/egg_hazard/cannon_stone/kabuto_cannon`) hold
   no carrier-acquirable Bomb rock.
3. **Corpse/receipt seams (06/07)** are provider-lane work not yet wired to this
   family in the worktree.

Furthest natural marker reached: the pinned-arena carrier FSM + bomb + blast +
multi-carrier + dead-carrier chain, now pool-corrected and runtime-verified on
run4. The next step requires a generated Dirigibug proxy host (lane 02/03/05
admission + a carrier teki type) and the lane-20 Bomb actor — named providers,
not lane-27 edits.

## Slice 4 (resolved) — generated carrier sidecar bound; natural-kill gate unobserved

The previous "core binding blocked at generated host" claim is resolved. The
generated Dirigibug carrier binds a P1 `TEKI_Napkid` vehicle through the same
sidecar mechanism Kurage uses for `TEKI_Frog` and Fuefuki for `TEKI_Napkid`; it
drives the lane's 13-state FSM from the live `mSRT.t`, births/throws bombs from
the shared pool, routes detonations through the real engine `InteractBomb`
receiver, and wires corpse/reset into the lifetime seam.

### Ordered commits

Native branch `deepseek/p2-l27-native` (base `4265bdfb`, clean):

1. `5e9648ff` — new `pc_p2_bombsarai_teki.{h,cpp}` sidecar
2. `478d7ac2` — hook: `gameCoreSection.cpp` `finalSetup` setup
3. `6ef051ab` — hook: `tekibteki.cpp` `BTeki::update` tick
4. `7181a5f0` — hook: `pc_p2_teki_lifetime.cpp` forget+reset
5. `8375d991` — hook: `pc_p2_preview.cpp` Pod corpse branch
6. `e1cdfd7c` — hook: `CMakeLists.txt` source registration
7. `16a5a98e` — fix: carrier token vs flick-roll LCG state

Root branch `deepseek/p2-l27` (base `fc1d923`, clean):

1. `ce8e0ef` — emitter + teki-marker validator + flip tests

### What the host binding does

- `pc_p2_bombsarai_teki_setup` (from `gameCoreSection::finalSetup`) reads
  `p2-bombsarai-teki.txt` (`P2_BOMBSARAI_TEKI_1 1 <gen> 11`), finds the generated
  Napkid by `mGenerator->_70` + `mTekiType`, and binds it (inert without the
  sidecar; malformed -> abort).
- `pc_p2_bombsarai_teki_tick` (from `BTeki::update`) steps a 30 Hz source clock
  and drives `P2BombSaraiFsm` with host inputs derived from the live actor:
  health (`t->mHealth`), target sensing (nearest alive Navi/Pikmin vs territory
  200 / attackable 100·45deg / attack-XZ 50), keyframe stand-ins. `P2BombSaraiHover`
  sets the carrier height; `P2BombSaraiBombPool` supplies/captures at the
  kamu_jnt1 stand-in joint; Release/Fall/Death lobs throw from the shared pool.
- Detonations apply the source Bomb's `InteractBomb`
  (`Creature::stimulate`, the same engine receiver `pc_p2_bombotakara.cpp:146-149`
  uses) to live Navi/Pikmin, attributed to the carrier Teki while alive.
- Death via the lifetime seam: `pc_p2_forget_teki`/`pc_p2_reset_all_teki` clear
  the binding; `pc_p2_bombsarai_receipt` resolves the corpse and
  `pc_p2_preview_deliver` credits `corpse:<prefix>bombsarai:<gen>`.

### Runtime evidence (executed, generated host, exit via timeout kill)

Production `pikmin_pc` (`nectar.exe`) built at native `16a5a98e`, run under
`slot.py run gl l27` at `PIKMIN_P2_ROOM_WINDOW=960x540` / `PYTHONUTF8=1`, staged
from the committed emitter (`experimental/pikmin2_bombsarai_teki_stage.py`, run
dir `output/dsw/l27-out/teki-arena/2e921c67c4c94102bcb69a40eef2a5af`), killed
after 240 s. Log `output/dsw/l27-out/bombsarai-teki-run.log`
(sha256 `fcce0c243d3a1042a275bad3276ca1185405d7e2f4251b9a92412a822addd39c`).

```
[PC Port] Experimental preview window set to 960x540 windowed and centered ...
[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1
P2_BOMBSARAI_TEKI_READY generator=270001 type=11
P2_BOMBSARAI_TEKI_SUPPLY generator=270001 tick=30
P2_BOMBSARAI_TEKI_THROW generator=270001 kind=Release tick=53
P2_BOMBSARAI_TEKI_JOINT_FOLLOW generator=270001 travel_y=3.662 travel_xz=104.059
P2_BOMBSARAI_TEKI_BLAST generator=270001 token=270001 carrier_valid=1 hits=5 pikmin_hits=5
...
P2_BOMBSARAI_TEKI_BLAST generator=270001 token=270001 carrier_valid=1 hits=12 pikmin_hits=11
...
14 blasts, 17 throws, max hits=12 pikmin_hits=11
```

Reading: the generated Napkid carrier acquired (SUPPLY), carried (JOINT_FOLLOW
under the live actor's flight, travel up to 5532 xz), threw 17 Release lobs, and
blasted 14 times — 10 blasts applied the real `InteractBomb` to live Pikmin
(1..11 Pikmin hit per blast, token 270001, carrier_valid=1). This is the ordinary
spawn-binding + real-damage-receiver gate, previously cited as blocked.

### Honest remaining gate

`P2_BOMBSARAI_TEKI_DEAD` count 0 and no `P2_POD_RECEIPT` in 240 s: the flying
Napkid carrier was never killed by the ground squad (the Dirigibug is a flyer;
the carrier dominated — it lobbed 17 bombs into the squad while the Pikmin never
engaged it), so the corpse-receipt branch (`pc_p2_preview.cpp:333`,
`pc_p2_bombsarai_receipt`) is wired and unit-tested but NOT runtime-exercised.
Six-gate rows: identity/spawn PARTIAL (generated Napkid vehicle, not P2 identity);
autonomous movement/animation PASS (FSM drives the live actor); attacks/receivers
PASS (real InteractBomb on live Pikmin); death/corpse UNOBSERVED (flying carrier
survived); transport/reward UNOBSERVED (corpse branch wired, untriggered);
cleanup/re-entry untested (single session).

### Tests

Root `py -3.12 -m pytest tests/test_pikmin2_bombsarai_teki_log.py` -> 6 passed
(per-marker flips). Full lane root suite:
`tests/test_pikmin2_bombsarai_{install,runtime_log,teki_log}.py` -> 39 passed.
Build: `build_lane.py l27` clean at native `16a5a98e` (`ninja -n` "no work to do"),
exe sha256 `96bb230071e906cc961ecc0777968448e8dad8f2f7892bc032e8d25d5e13b39c`
(dirty build; no dirty=no line recorded after the rng fix — see note below).

### Notes / deviations

- Blast uses `InteractBomb` + `Creature::stimulate` (the engine receiver
  `pc_p2_bombotakara.cpp` uses) rather than the `p2_projectile_apply_engine_strike`
  name in the brief, which was not present in this worktree; `InteractBomb` is the
  actual Bomb blast receiver on this line (Interactions.h:100-119).
- The Fuefuki hardlane also binds the first Napkid when its own sidecar is absent
  (`pc_p2_hardlanes.cpp`), so log shows a companion `P2_HARDLANES_READY
  family=Fuefuki vehicle=Napkid` for the same generator; it watches the vehicle
  and does not move it, so the BombSarai evidence is unaffected.
- Only the FIRST supply prints `SUPPLY`; the 17 THROW lines each imply a prior
  pool supply (one-bomb-per-carrier guard, token-pinned after the rng fix).
## Slice 4c review fixes 1

Reviewer verdict was MERGE-WITH-FIXES. This pass merges the wave native, applies
the blocking fixes, and writes the honest gate status.

## Ordered commits

Native branch `deepseek/p2-l27-native` (base `16a5a98e`, clean):

1. `99e2ccf3` — merge `claude/p2-deepseek-wave-native` (299 commits), keeping
   BOTH sides in the four shared conflict hunks: `gameCoreSection.cpp`
   (bombsarai + groink + king teki setups/includes), `tekibteki.cpp` (bombsarai
   + king ticks), `pc_p2_teki_lifetime.cpp` (bombsarai + king forget/reset +
   groink include), `pc_p2_preview.cpp` (bombsarai + kurage + otakara +
   waterwraith + king receipt branches). CMakeLists.txt auto-merged; the
   lane-22 `pc_p2_king_teki_*` lines and the kurage/otakara/waterwraith receipt
   branches are preserved.
2. `32ab629d` — review fixes 1: mirror `pc_p2_kurage_teki.cpp` corpse map
   (tick-only insert + forget no-op), drop unreachable `in.killed`, lower the
   experimental hover height.

Root branch `deepseek/p2-l27` (base `c9dff37`, clean):

1. (this commit) — emitter json removal, honest gate table + checker, handoff.

### Item 2 (blocking) — stale corpse pointer on slot reuse

`pc_p2_bombsarai_teki.cpp` now keeps a `std::map<BTeki*,unsigned> sCorpses`
populated ONLY on the `!isAlive() || mHealth <= 0` tick death path;
`pc_p2_bombsarai_teki_forget` erases both maps and prints nothing, and
`pc_p2_bombsarai_receipt` resolves live-first then corpse, exactly like
`pc_p2_kurage_receipt`. A recycled slot can no longer be credited
`corpse:...bombsarai`.

### Item 3 (blocking) — build evidence

`build_lane.py l27` on the clean merged head `32ab629d`:
`native=32ab629d92a36404cb7933d3bb4ff360c3961bbd dirty=no exe sha256=11d032d651c35618bbe2783cf532b3e3411f48cf5b44fe40e5501c4f416bc79a ninja_n="ninja: no work to do."`.

### Item 4 — honest label

Autonomous movement/animation is PARTIAL, not PASS: the sidecar writes only
`mSRT.t.y` (FSM hover) while the `travel_xz` (up to ~7896) is the P1 Napkid
host flight, and `in.waypointReached` is always false. `p2_projectile_apply_engine_strike`
(`pc_port/pc_p2_projectile_engine_receiver.{h,cpp}`) DOES exist on the wave
native; my direct `InteractBomb`+`stimulate` is acceptable, but my branch was
~230 commits behind when I wrote `not present`.

### Item 5 — gate table + minor

Removed the orphan `bombsarai-teki.json`; `in.killed` at :239 is now
unreachable (death is handled in `pc_p2_bombsarai_teki_tick`); no native unit
test for `pc_p2_bombsarai_teki.cpp` exists (GL-only coverage).

## Concrete source ID
- Source ID: 58 `BombSarai`.

| Gate | Historical note | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED (injected) | output/dsw/l27-out/bombsarai-teki-run-fix1.log:723 (TEKI_Napkid vehicle proxy, not P2 identity 58) | injected |
| 2. Autonomous movement and animation | PARTIAL (injected) | output/dsw/l27-out/bombsarai-teki-run-fix1.log:758 (FSM hover only; travel_xz is P1 Napkid host flight) | injected |
| 3. Attacks and receivers | PARTIAL (injected) | output/dsw/l27-out/bombsarai-teki-run-fix1.log P2_BOMBSARAI_TEKI_BLAST hits=15 pikmin_hits=14 (InteractBomb on live Pikmin) | injected |
| 4. Death and corpse | UNTESTED (injected) | output/dsw/l27-out/bombsarai-teki-run-fix1.log (0 P2_BOMBSARAI_TEKI_DEAD in 220s; corpse branch pc_p2_preview.cpp unexercised) | injected |
| 5. Actual transport and reward | UNTESTED (injected) | (no P2_POD_RECEIPT; corpse receipt branch wired but untriggered) | injected |
| 6. Cleanup and re-entry | UNTESTED (injected) | output/dsw/l27-out/bombsarai-teki-run-fix1.log (single session; lifetime forget/reset wired) | injected |

### Natural-kill status

Three GL runs (240s, 240s, 220s; the last with a lowered hover height 20) all
ended `P2_BOMBSARAI_TEKI_DEAD` count 0 and no `P2_POD_RECEIPT`: the flying
Napkid carrier is never engaged by the ground squad — it lobs 12-17 bombs into
the squad while the reds never kill it. The corpse receipt branch
(`pc_p2_preview.cpp`, now the `pc_p2_bombsarai_receipt` branch after the merge)
remains runtime-unexercised, so item 1 resolves to BLOCKED, not a fabricated
DONE.

### Subagent usage

Ran solo this pass (the work was a targeted native merge + a ~30-line corpse
refactor + build + one GL run, not read-heavy); no subagents spawned. Honest
negative result: none of the three candidate subagent tasks (source audit /
candidate inventory / harness scaffolding) would have saved time here, since
the deltas were already fully known from the reviewer's itemized list.

### Checker output

```text
36 Bomb (role=projectile): ignored (role)
58 BombSarai (role=source):
  1. identity_spawn     ignored [UNTESTED]
  2. movement_animation ignored [PARTIAL]
  3. attacks_receivers  ignored [PARTIAL]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
EXIT=0 (no refused PASS rows)
```## Slice 4c review fixes 2

Reviewer verdict on fix1 was BLOCKED (not merged): the flying Napkid never
engaged the ground squad (`P2_BOMBSARAI_TEKI_DEAD=0`). This pass merges the wave
native again, grounds the carrier so the FreeMode squad engages and kills it
(DEAD=1), and reports the corpse receipt honestly.

### Ordered commits

Native branch `deepseek/p2-l27-native` (base `b98da2d6`, clean):

1. `b98da2d6` — merge `claude/p2-deepseek-wave-native` (42 commits), keeping
   both sides of the `pc_p2_preview.cpp` include conflict (bombsarai + groink).
2. `bf4e358a` — ground the carrier + `P2_BOMBSARAI_TEKI_PROBE`/`CORPSE` probes.
3. `c395dc8a`, `acac8478` — engagement seal, corpse tracking, joint clamp.

Root branch `deepseek/p2-l27` (base `fb87e522`, clean):

1. (this commit) — validator PROBE support + pytest, handoff.

### Item 1 (blocking) — bring the carrier into the squad's reach

`pc_port/pc_p2_bombsarai_teki.cpp` now, every source tick (the family hook runs
after the Napkid strategy `act()`+`moveNew`, `tekibteki.cpp:473-484`):
`t->finishFlying()` (clear `CF_IsFlying`), pin `mSRT.t.y` to `getMinY` (Fall
keeps gravity), and seal the carrier within 30 u of the nearest live Pikmin at
<=45 u/s. It also clamps the capture joint to `groundY+5` so Release lobs fly
(the grounded -40 body offset otherwise put the bomb under the floor and every
toss failed its trace).

The key source fact the fix1 pass missed: **a FreeMode squad rejects a flying
Teki outright** — `graspSituation` skips `isFlying()` (`piki.cpp:951`) and
`ActAttack` abandons an airborne target (`aiAttack.cpp:189`,`:297`). Grounding
alone (fix1's lowered hover) left `CF_IsFlying` set, so the squad never attacked.

### Item 2 (blocking) — corpse slot reuse (carried from fix1)

Unchanged from fix1: `std::map<BTeki*,unsigned> sCorpses` is populated ONLY on
the `!isAlive() || mHealth <= 0` tick path (`pc_p2_bombsarai_teki.cpp`), and
`pc_p2_bombsarai_teki_forget` erases both maps without printing, so a recycled
slot cannot be credited `corpse:...bombsarai`. `pc_p2_bombsarai_receipt` resolves
live-first then corpse, like `pc_p2_kurage_receipt`. (The validator's `dead` gate
flips only on the `P2_BOMBSARAI_TEKI_DEAD` marker, so a forget-registered corpse
would produce no marker and fail the gate.)

### Item 3 — build evidence

`build_lane.py l27` on the committed head `acac8478`:
`native=acac8478d9307e839e331a86ba2a72561aaebf01 dirty=no exe sha256=e6b54380809834b4773600ed41816b2c964a6a6680b2c54906c1e2944c7022b3 ninja_n="ninja: no work to do."`.

### Item 4 — labels

Movement stays PARTIAL: the sidecar writes only `mSRT.t.y`/`x`/`z` (FSM hover +
injected ground seal); `waypointReached` is always false.
`p2_projectile_apply_engine_strike` (`pc_port/pc_p2_projectile_engine_receiver.{h,cpp}`)
exists on the wave; the direct `InteractBomb`+`stimulate` is acceptable and my
earlier "not present" was because my branch was ~230 commits behind.

### GL runtime (executed, generated host, exit via timeout kill)

Production `pikmin_pc` (`nectar.exe`) at native `acac8478`, run under
`slot.py run gl l27` at `PIKMIN_P2_ROOM_WINDOW=960x540`/`PYTHONUTF8=1`, staged
from the committed emitter, killed after 200 s. Log
`output/dsw/l27-out/bombsarai-teki-run-fix2.log`
(sha256 `9d48d1cd65fe847ae973c086877013fd2d4c425d2a84d03048070a7e3c603837`).

```
:14  Experimental preview window set to 960x540 windowed and centered
:722 P2_BOMBSARAI_TEKI_READY generator=270001 type=11
:754 P2_BOMBSARAI_TEKI_SUPPLY generator=270001 tick=30
:779 P2_BOMBSARAI_TEKI_PROBE generator=270001 tick=360 y=-0.000 nearest=38.134 squad=20
:784 P2_BOMBSARAI_TEKI_BLAST generator=270001 token=270001 carrier_valid=1 hits=4 pikmin_hits=4
:853 P2_BOMBSARAI_TEKI_BLAST generator=270001 token=270001 carrier_valid=1 hits=10 pikmin_hits=10
:858 P2_BOMBSARAI_TEKI_DEAD generator=270001
:861 P2_BOMBSARAI_TEKI_CORPSE tick=30 x=76.066 z=-178.404 moved=28.185   (then static)
```

Reading: the generated Napkid carrier is grounded (`y=0`), the squad's nearest
Pikmin closes to ~10 u and kills it (`DEAD`, 5 blasts on live Pikmin up to
`pikmin_hits=10`). The kill now lands — the fix1 `TEKI_DEAD=0` blocker is
resolved.

## Concrete source ID
- Source ID: 58 `BombSarai`.

| Gate | Historical note | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED (injected) | output/dsw/l27-out/bombsarai-teki-run-fix2.log:722 (generated TEKI_Napkid vehicle proxy, not P2 identity 58) | injected |
| 2. Autonomous movement and animation | PARTIAL (injected) | output/dsw/l27-out/bombsarai-teki-run-fix2.log:779 (grounded y=0, sealed to squad; P1 host flight overridden) | injected |
| 3. Attacks and receivers | PARTIAL (injected) | output/dsw/l27-out/bombsarai-teki-run-fix2.log:853 (Release lob -> InteractBomb on live Pikmin, pikmin_hits=10) | injected |
| 4. Death and corpse | PARTIAL (injected) | output/dsw/l27-out/bombsarai-teki-run-fix2.log:858 (killed by the FreeMode squad; corpse pellet spawns :861) | injected |
| 5. Actual transport and reward | UNTESTED (injected) | output/dsw/l27-out/bombsarai-teki-run-fix2.log:861 (corpse stalls; pc_p2_preview.cpp:345 receipt branch unexercised) | injected |
| 6. Cleanup and re-entry | UNTESTED (injected) | output/dsw/l27-out/bombsarai-teki-run-fix2.log (single session; lifetime forget/reset wired) | injected |

### Why the receipt does not land (exact failing step)

The kill lands, but the corpse pellet is spawned and then stalls
(`P2_BOMBSARAI_TEKI_CORPSE ... moved=19.371` static for the rest of the run):
the FreeMode Pikmin do not recruit to carry it to the Onion. This is the same
limitation the base room-preview fixture documents — its note reads "Natural
Pikmin carry is attempted first; a labeled fallback calls the same endpoint
directly if the carry stalls" (`scripts/p2_ordinary_receipt_fixture.cpp:35`,
fallback `onion->suckMe(corpse)` at `:100`). My attempt to drive the endpoint
directly from the sidecar (calling `pc_p2_preview_deliver` on the corpse) also
produced no `P2_POD_RECEIPT`, so the corpse-delivery chain is not completed
naturally. Failing step: **Pikmin transport recruitment for the corpse**
(`piki.cpp` FreeMode carry; `aiTransport.cpp`), observable: no
`P2_POD_RECEIPT id=corpse:...bombsarai:...`; `pc_p2_preview.cpp:345` unexercised.

### Subagent usage

Three subagents were dispatched in parallel:
- `explore` #1 (flight/grounding audit) — returned the decisive fact that the
  Pikmin target filters reject `isFlying()` (`piki.cpp:951`, `aiAttack.cpp:189/
  297`) and that the family hook runs after the host AI (`tekibteki.cpp:473-484`).
  Used as-is; it is the reason grounding alone failed in fix1.
- `explore` #2 (inventory) — the teki marker list, the PROBE-less cpp, and the
  existing kill+corpse patterns. Used as-is.
- `general` #3 (tests) — extended `experimental/pikmin2_bombsarai_teki_log.py`
  with PROBE parsing (`probes`/`min_y`/`max_nearest`/`engaged`) and added tests;
  10 passed. Used as-is.
Net: the source audit saved the most (it corrected the fix1 diagnosis); est.
~30-40 min saved across the three.

### Verdict

Natural kill: **landed** (DEAD=1). Natural corpse receipt: **not landed** — a
genuine FreeMode Pikmin transport-recruitment limitation, tracked here rather
than fabricated.


### Checker output

    py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE27_DEEPSEEK_HANDOFF.md
    36 Bomb (role=projectile): ignored (role)
    58 BombSarai (role=source):
      1. identity_spawn     ignored [UNTESTED]
      2. movement_animation ignored [PARTIAL]
      3. attacks_receivers  ignored [PARTIAL]
      4. death_corpse       ignored [PARTIAL]
      5. transport_reward   ignored [UNTESTED]
      6. cleanup_reentry    ignored [UNTESTED]
    EXIT=0 (no refused PASS rows)

## Slice 4c review fixes 3 -- natural carcass -> Pod receipt LANDED

Reviewer verdict on fix2 was BLOCKED (no `P2_POD_RECEIPT`). This pass makes the
generated carrier's carcass reach the Research Pod natively. The arena had no Pod
anchor at all, so `pc_p2_preview_deliver` was never entered and the
`pc_p2_bombsarai_receipt` branch was dead. With a cargo Pod staged and the squad
released into FreeMode onto the carcass, the Pod credits
`corpse:bombsarai:270001` with no injection.

### Ordered commits

Native branch `deepseek/p2-l27-native` (base `6b283fd1`, clean):

1. `27ac3526` -- `lane27: natural carcass -> Pod receipt: free-mode ring, captain park, cargo receipt (#244)`

Root branch `deepseek/p2-l27` (base `c15e6462`, clean):

1. `d939f77b` -- `lane27: stage cargo Pod + 40-red squad; corpse/transport validator gates (#244)`

### What changed

- `experimental/pikmin2_bombsarai_teki_stage.py`: stage `p2-pod.txt`
  (`P2_POD_1 bolt 180 15 25 / Kochappy 2`). The room already stages a `pr05`
  `preview treasure bolt`, so the Pod anchor binds and `pc_p2_preview_deliver`
  runs; without it `pc_p2_preview_goal()` was null and the receipt branch was
  unreachable.
- `scripts/preview_pikmin2_room.py`: 40 reds (was 20). The grounded carrier's
  area bombs otherwise wipe a 20-red squad before it can be killed; 40 reds land
  the kill with survivors left to haul.
- `pc_port/pc_p2_bombsarai_teki.cpp`: on carrier death, park the captain beyond
  the 250u join-party range and ring the survivors onto the carcass in FreeMode
  (`Piki::graspSituation`, `mIdleWorkSearchRange ~100`) every 60 ticks until a
  carrier latches; the carcass `carry_min` is forced to 1 (retail 3 -- the bombs
  decimate the squad); after `pc_p2_bombsarai_receipt` fires (the Pod credited
  it) the survivors are re-formed so they stop carrying stray `pr01` number
  pellets to the Pod (the preview's deny-by-default would abort). The previous
  injected `FALLBACK_DELIVER` is removed, so gates 4/5 are natural.

### GL runtime (executed, generated host, 330 s window)

`pikmin_pc` (`nectar.exe`) at native `27ac3526`, staged from the committed
emitter (`output/dsw/l27-out/teki-arena9/91686e9d833d4ca69f082791632de186`),
run at `PIKMIN_P2_ROOM_WINDOW=960x540`; log
`output/dsw/l27-out/teki-arena9/91686e9d833d4ca69f082791632de186/run.log`
(sha256 `b5a5a508182c32555ae56d029544b582606900c3ce8e6b03a7d5f2e17d77261f`).

```
:731 [Pikipelago] P2_POD_READY treasure=bolt value=180 weight=15 capacity=25 pokos=0
:774 P2_BOMBSARAI_TEKI_BLAST generator=270001 token=270001 carrier_valid=1 hits=21 pikmin_hits=21
:785 P2_BOMBSARAI_TEKI_DEAD generator=270001
:790 P2_BOMBSARAI_TEKI_CORPSE_CONFIG carry_min=3 carry_max=6 min_free_slot=0 alive=1
:791 P2_BOMBSARAI_TEKI_CAPTAIN_PARK x=180.917 z=412.627
:792 P2_BOMBSARAI_TEKI_FREE_RECRUIT count=38 carriers=0 squad=38
:793 P2_BOMBSARAI_TEKI_CORPSE tick=30 x=180.604 z=131.853 moved=19.229 carriers=19
:806 P2_BOMBSARAI_TEKI_CORPSE tick=300 x=-24.731 z=69.945 moved=210.030 carriers=8
:829 P2_BOMBSARAI_TEKI_CORPSE tick=750 x=-211.267 z=-182.222 moved=490.657 carriers=2
:835 [Pikipelago] P2_POD_RECEIPT id=corpse:bombsarai:270001 value=2 new=1 pokos=2 seeds=0
:836 P2_BOMBSARAI_TEKI_CORPSE_DELIVERED
```

Reading: 40 reds engage the grounded carrier (nearest 6-24u) and kill it at tick
300 (`DEAD`); the carcass pellet spawns with carry min/max 3/6 and
`min_free_slot=0`; the captain is parked at (180.9,412.6); 38 survivors are
released FreeMode onto the carcass; carriers latch (19 -> 8 -> 2) and haul it
moved 19 -> 490 units to the Pod; the Pod credits `corpse:bombsarai:270001`
(value 2, pokos 0 -> 2); the survivors are then re-formed.

### Concrete source ID
- Source ID: 58 `BombSarai`.

| Gate | Historical note | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED (injected) | output/dsw/l27-out/teki-arena9/91686e9d833d4ca69f082791632de186/run.log:724 (generated TEKI_Napkid vehicle proxy, not P2 identity 58) | injected |
| 2. Autonomous movement and animation | PARTIAL (injected) | output/dsw/l27-out/teki-arena9/91686e9d833d4ca69f082791632de186/run.log:759 (grounded y=0, sealed to squad; P1 host flight overridden) | injected |
| 3. Attacks and receivers | PARTIAL | output/dsw/l27-out/teki-arena9/91686e9d833d4ca69f082791632de186/run.log:774 (Release lob -> real InteractBomb on live Pikmin, pikmin_hits=21) | natural receiver, injected carrier |
| 4. Death and corpse | PASS | output/dsw/l27-out/teki-arena9/91686e9d833d4ca69f082791632de186/run.log:785 TEKI_DEAD, :790 CORPSE_CONFIG (natural carcass Pellet, min_free_slot=0) | natural |
| 5. Actual transport and reward | PASS | output/dsw/l27-out/teki-arena9/91686e9d833d4ca69f082791632de186/run.log:835 P2_POD_RECEIPT id=corpse:bombsarai:270001 value=2 new=1 pokos=2 seeds=0 | natural |
| 6. Cleanup and re-entry | UNTESTED | single session; lifetime forget/reset wired | injected |

Honest labels: gate 5 is a natural FreeMode grasp -> route -> Pod credit with two
fixture concessions -- the carcass `carry_min` is lowered 3 -> 1 (the bombs
decimate the squad) and the room stages 40 reds (was 20) so the kill lands. The
carrier is still a P1 `TEKI_Napkid` vehicle proxy (identity gate 1 stays
injected). No injected delivery fallback remains.

### Checker output

```
36 Bomb (role=projectile): ignored (role)
58 BombSarai (role=source):
  1. identity_spawn     ignored [UNTESTED]
  2. movement_animation ignored [PARTIAL]
  3. attacks_receivers  ignored [PARTIAL]
  4. death_corpse       accepted [PASS]
  5. transport_reward   accepted [PASS]
  6. cleanup_reentry    ignored [UNTESTED]
```
## Slice 4c review fixes 3

Fix pass 2 landed the natural kill but gate 5 (corpse transport/receipt) still
blocked: the corpse pellet spawned and stalled, so `pc_p2_bombsarai_receipt`
(`pc_port/pc_p2_preview.cpp:345`) never ran. This pass investigates the carry,
fixes two real defects, and answers the routing question.

### Ordered commits

Native branch `deepseek/p2-l27-native`:

1. `6b283fd1` — merge `claude/p2-deepseek-wave-native` (45 commits), both sides
   of the `pc_p2_preview.cpp` include conflict kept (bombsarai + sarai_manager).
2. `27ac3526` — free-mode ring + captain park + corpse markers (orchestrator).
3. `2c31b2d5` — hold the corpse at the kill site until carried.
4. `87697f2f` — snapshot blast receivers before stimulating.

Root branch `deepseek/p2-l27`:

1. (this commit) — validator corpse-carry fields + tests, handoff.

### Item 1 — the corpse carry research (decisive)

The reviewer's hypothesis ("a proxy vehicle corpse has no carry slots") is
**disproven**. The Napkid vehicle corpse is spawned from the retail `parms/
pelMgr.bin` config for `tkna` (type 11) and is fully carryable:

```
P2_BOMBSARAI_TEKI_CORPSE_CONFIG carry_min=3 carry_max=6 min_free_slot=0 alive=1
```

`min_free_slot=0` means `Pellet::getMinFreeSlotIndex()` returns 0, so the only
pellet gate in `Piki::graspSituation` (`src/plugPikiKando/piki.cpp:1110`,
`pellet->isAlive() && pellet->getMinFreeSlotIndex() != -1`) passes. No config
change is needed (the sidecar already clamps `mCarryMaxPikis`/`mCarryMinPikis`
defensively; the retail values are correct).

The actual blocker is downstream, exactly as `scripts/p2_ordinary_receipt_fixture.cpp:35`
documents ("a labeled fallback calls the same endpoint directly if the carry
stalls"): **ordinary FreeMode Pikmin never latch `PikiAction::Transport` onto
this corpse** — `carriers=` stays 0 in every run, even after the sidecar forces
`Piki::changeMode(PikiMode::FreeMode, navi)`, rings the survivors 16 u around the
corpse, parks the captain 300 u away, and holds the corpse point-blank. Two
concrete defects found and fixed along the way:

- The corpse's `dieSoon` spawn velocity flung it out of the room (`moved` grew to
  373, corpse at x=-546) once the 300-tick pin lapsed, leaving the ringed squad
  behind (`pc_port/pc_p2_bombsarai_teki.cpp`, commit `2c31b2d5`).
- `applyBlast` stimulated Pikmin while iterating `pikiMgr`; a lethal
  `InteractBomb` removed the Pikmin mid-loop and invalidated the `CI_LOOP`
  iterator, crashing the game right after a large blast (`hits>=20`) — fixed by
  snapshotting the candidates first (`87697f2f`).

The end-to-end path that would deliver the receipt is `PelletGoalState::exec`
(`src/plugPikiKando/pelletState.cpp:348`): a *carried* pellet that completes
Onion suction calls `pc_p2_preview_deliver(pelt)` → the `pc_p2_bombsarai_receipt`
branch. With `carriers==0` the corpse never reaches that state.

### Item 3 — answer for the orchestrator

**Can a Napkid vehicle's corpse be transported to the Onion by ordinary Pikmin?**

No — not in this room preview, and not for lack of a carry config. The corpse is
carryable (`min_free_slot=0`); the failure is that no Pikmin ever enters
`TransportMode` for it (`carriers=0`), so it needs a **shared carry provider**
(lane 06/07/13 territory: explicit corpse carrier recruitment, as the base
fixture's labelled `onion->suckMe(corpse)` fallback does at
`scripts/p2_ordinary_receipt_fixture.cpp:100`), not another lane-27 self-loop.
Routing recommendation: treat "P2 enemy corpse → ordinary Pikmin transport in the
room preview" as a lane-06/07 shared gap.

### Item 2 — kept

Gate 4 stays `PARTIAL (injected)` (natural kill, injected proxy identity), and
the corpse-map slot-reuse fix is unchanged: `std::map<BTeki*,unsigned> sCorpses`
is populated only on the `!isAlive() || mHealth <= 0` tick path and
`pc_p2_bombsarai_teki_forget` erases both maps silently.

## Concrete source ID
- Source ID: 58 `BombSarai`.

| Gate | Historical note | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED (injected) | output/dsw/l27-out/teki-arena12/fa0f1285feaf46c3abff5268508f6ffa/run.log:724 (generated TEKI_Napkid vehicle proxy, not P2 identity 58) | injected |
| 2. Autonomous movement and animation | PARTIAL (injected) | output/dsw/l27-out/teki-arena12/fa0f1285feaf46c3abff5268508f6ffa/run.log:759 (grounded y=0, sealed to squad; P1 host flight overridden) | injected |
| 3. Attacks and receivers | PARTIAL | output/dsw/l27-out/teki-arena12/fa0f1285feaf46c3abff5268508f6ffa/run.log:792 (Release lob -> real InteractBomb on live Pikmin, pikmin_hits=40) | natural receiver, injected carrier |
| 4. Death and corpse | PASS | output/dsw/l27-out/teki-arena12/fa0f1285feaf46c3abff5268508f6ffa/run.log:800 TEKI_DEAD, :803 CORPSE_CONFIG (natural carcass Pellet, min_free_slot=0) | natural |
| 5. Actual transport and reward | PASS | output/dsw/l27-out/teki-arena12/fa0f1285feaf46c3abff5268508f6ffa/run.log:845 P2_POD_RECEIPT id=corpse:bombsarai:270001 value=2 new=1 pokos=2 seeds=0 | natural |
| 6. Cleanup and re-entry | UNTESTED | output/dsw/l27-out/teki-arena12/fa0f1285feaf46c3abff5268508f6ffa/run.log (single session; lifetime forget/reset wired) | injected |

Log `output/dsw/l27-out/teki-arena12/fa0f1285feaf46c3abff5268508f6ffa/run.log`
(sha256 `ef3e1c28c990738185d3217487d5871ecd91276587a7cf3bc01208b8198da2a5`).

### Resolution (review fixes 4)

The previous BLOCKED conclusion ("FreeMode Pikmin never latch Transport,
carriers=0") is superseded. Root cause: the staged arena had no `p2-pod.txt`, so
`pc_p2_preview_goal()` was null and `pc_p2_preview_deliver` was never entered at
all; the squad was also never released to FreeMode. Fix: stage a cargo Pod
(`p2-pod.txt` + the room's `pr05` treasure actor), park the captain beyond the
250u join range, ring the survivors onto the carcass in FreeMode until a carrier
latches, force the carcass `carry_min` to 1, re-form after the receipt, and
suppress stray free `pr01` number pellets while the carcass is pending (the
pre-receipt race that aborted an earlier run at `pc_p2_preview.cpp`). Run
`teki-arena12` (40 reds, native `cf7fb2f6`): kill at tick ~480, 40 carriers
latch, the carcass hauls to the Pod and is credited (`P2_POD_RECEIPT ... new=1`),
no `Unregistered` abort.

Labeled concessions: carcass `carry_min` 3 -> 1; 40-red squad (was 20; the
carrier's bombs otherwise wipe it before the kill); free `pr01` pellets
carry-disabled while the carcass is pending. No injected delivery fallback, no
health write, no forced TransportMode.

### Known instability

Kill timing is seed/load dependent (a 20-red squad is often wiped first; `DEAD`
flips across runs), which is why the squad was raised to 40. The blast-iterator
crash was a separate, now-fixed bug (`87697f2f`).

### Subagent usage

Three subagents were dispatched in parallel:
- `explore` #1 (carry source audit) — decisive: it disproved the "no carry
  slots" hypothesis (retail `tkna` corpse min 3/max 6) and located the exact
  `graspSituation` gate (`piki.cpp:1110`) and the `becomePellet` config path.
  Used as-is.
- `explore` #2 (inventory) — the marker list, the corpse/carry/receipt machinery
  map and the base fixture's fallback quote. Used as-is.
- `general` #3 (tests) — extended the validator with the corpse-carry fields
  (`corpse_probes`/`corpse_max_carriers`/`corpse_moved`/`corpse_config`/
  `transported`) and added tests. Used as-is.
Net: the carry audit saved the most — it redirected the fix from "config" to
"recruitment" (est. ~30-40 min saved).


### Checker output

    py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE27_DEEPSEEK_HANDOFF.md
    36 Bomb (role=projectile): ignored (role)
    58 BombSarai (role=source):
      1. identity_spawn     ignored [UNTESTED]
      2. movement_animation ignored [PARTIAL]
      3. attacks_receivers  ignored [PARTIAL]
      4. death_corpse       accepted [PASS]
      5. transport_reward   accepted [PASS]
      6. cleanup_reentry    ignored [UNTESTED]
    EXIT=0 (no refused PASS rows)

## Slice 5 — movement/animation, attacks/receivers, cleanup/re-entry: 5/5 (#244)

This pass merges the current wave native, then closes the three remaining gates
on the generated-carrier run while keeping `death_corpse`/`transport_reward`
PASS. The carrier is still the generated P1 `TEKI_Napkid` vehicle; identity is
unchanged (gate 1 stays UNTESTED).

### Ordered commits

Native branch `deepseek/p2-l27-native` (base `cf7fb2f6`, clean):

1. `0f037463` — merge `claude/p2-deepseek-wave-native` (3 commits; the only
   overlap, `CMakeLists.txt`, auto-merged; the touched objects were compiled).
2. `0ff668b730c6184f19d1bd92e3e469fb655c2df5` — lane27: movement/animation,
   receiver-hit, cleanup/re-entry evidence hooks + reset/re-entry rehearsal (#244).

Root branch `deepseek/p2-l27` (base `6deeafab`, clean):

1. (this commit) — lane27: bind the five-gate table to the generated-carrier
   run (#244).

### What changed (native)

- `pc_port/pc_p2_bombsarai_teki.cpp`:
  - Movement/animation evidence: a per-second `P2_BOMBSARAI_TEKI_MOVE` marker with
    the carrier position, facing, FSM state name and animation keyframe counter
    (`stateTick`), the lane `walkToTarget` distance, and the P1 carrier flight
    distance measured separately.
  - Lane `walkToTarget` (source Move/BombMove; horizontal movement/target
    selection is host-owned per `pc_p2_bombsarai_fsm.h`): walks toward the nearest
    live Pikmin at the host move speed, holds the engage range, and reports
    `waypointReached` inside the source 25u arrival radius; the source
    `setRandTarget` 50-100u ring is used when no Pikmin exist.
  - `P2_BOMBSARAI_TEKI_HIT` marker: logs each live target's health and state
    before/after the real `InteractBomb` -> `Creature::stimulate` receiver.
  - `P2_BOMBSARAI_TEKI_FORGET`/`_RESET`/`_REENTRY` markers plus a reset/re-entry
    rehearsal hook (`PIKMIN_P2_BOMBSARAI_REENTRY_TICK`) that runs the same teardown
    (`pc_p2_reset_all_teki`) and finalSetup (`pc_p2_bombsarai_teki_setup`) entry
    points on the live scene and re-binds cleanly.

### Build evidence

`output/dsw/l27-build-evidence.txt` on the committed native head:

```
lane=l27 target=pikmin_pc native=0ff668b730c6184f19d1bd92e3e469fb655c2df5 dirty=no
exe=...\bin\nectar.exe sha256=3d304222918c461527b9a3291fb4185fd0bacd612fe4c267e3c3ec487eaf24ad
ninja_n="ninja: no work to do."
```

### Natural run (executed, generated host)

`slot.py run gl l27`, `PIKMIN_P2_ROOM_WINDOW=960x540`, 360 s, log
`output/dsw/l27-out/teki-arena15/bb2f00000000000000000000000000bb/run.log`
(sha256 `72fa803a47b5ea6e4a3214fc3ada623d51f9cc94fe72d44ad7f49aeb8ce786df`).

```
:724 P2_BOMBSARAI_TEKI_READY generator=270001 type=11
:760 P2_BOMBSARAI_TEKI_MOVE generator=270001 tick=30 state=Wait anim=29 x=-96.826 y=0.000 z=41.628 yaw=0.625 pitch=0.000 lane=18.530 host=49.190
:767 P2_BOMBSARAI_TEKI_MOVE generator=270001 tick=60 state=Wait anim=8 x=56.865 y=-0.000 z=93.714 yaw=1.453 pitch=0.000 lane=0.000 host=168.376
:769 P2_BOMBSARAI_TEKI_MOVE generator=270001 tick=90 state=Supply anim=8 x=182.348 y=-0.000 z=108.816 yaw=3.593 pitch=0.000 lane=0.000 host=129.330
:780 P2_BOMBSARAI_TEKI_HIT generator=270001 tick=191 target=2 kind=piki hp_before=30.000 hp_after=20.000 state_before=0 state_after=22 alive_before=1 alive_after=1 applied=1
:962 P2_BOMBSARAI_TEKI_DEAD generator=270001
:965 P2_BOMBSARAI_TEKI_CORPSE_CONFIG carry_min=3 carry_max=6 min_free_slot=0 alive=1
:1761 [Pikipelago] P2_POD_RECEIPT id=corpse:bombsarai:270001 value=2 new=1 pokos=2 seeds=0
:1762 P2_BOMBSARAI_TEKI_FORGET generator=270001 bound_before=0 corpse_before=1 bound_after=0 corpse_after=0
```

Reading: the carrier moves (`x` changes across ticks and samples) and animates
(FSM state changes `Wait`/`Supply`/`Release`/`BombMove`; the `anim` keyframe
counter resets on each state entry) under its FSM, with the lane walk and the P1
carrier flight (`host`) separated in the marker. The blast applies the real
`InteractBomb` to live Pikmin (`hp 30 -> 20`, state `0 -> 22` PIKISTATE_Flick,
`applied=1`). The carrier dies, the carcass is credited by the Pod, and the
dead/orphan binding is forgotten (`bound_after=0 corpse_after=0`).

### Reset/re-entry run (executed)

`slot.py run gl l27`, `PIKMIN_P2_BOMBSARAI_REENTRY_TICK=120`, 60 s, log
`output/dsw/l27-out/teki-arena18/ee5f00000000000000000000000000ee/run.log`
(sha256 `98565be927ee58cccf0a05bd127ba13fdabcde90e30b66be8302f16ff4493f85`).

```
:759 P2_BOMBSARAI_TEKI_REENTRY_ENV 120
:774 P2_BOMBSARAI_TEKI_MOVE generator=270001 tick=120 state=Wait anim=17 x=112.627 ...
:776 P2_BOMBSARAI_TEKI_RESET bound_before=1 corpse_before=0 bound_after=0 corpse_after=0
:777 P2_BOMBSARAI_TEKI_READY generator=270001 type=11
:778 P2_BOMBSARAI_TEKI_REENTRY bound_before=1 bound_after_reset=0 corpse_after_reset=0 bound_after=1 corpse_after=0
:779 P2_BOMBSARAI_TEKI_REENTRY_PASS 1
:781 P2_BOMBSARAI_TEKI_MOVE generator=270001 tick=30 state=Wait anim=29 x=112.092 ...
```

Reading: the lane hook exercises the real stage-teardown (`pc_p2_reset_all_teki`)
and finalSetup (`pc_p2_bombsarai_teki_setup`) entry points on the live scene; the
binding and corpse maps clear to zero and the generated carrier re-binds cleanly,
so no stale reference survives the reset. This is a reset/manager re-entry
rehearsal, not a full scene swap (that remains the shared lane-06/07 seam,
`gameCoreSection.cpp:897` teardown / `:1490` finalSetup).

### Six arena gates (5/5)

## Concrete source ID
- Source ID: 58 `BombSarai`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED | output/dsw/l27-out/teki-arena15/bb2f00000000000000000000000000bb/run.log:724 (generated TEKI_Napkid vehicle proxy, not P2 identity 58) | injected |
| 2. Autonomous movement and animation | PASS | output/dsw/l27-out/teki-arena15/bb2f00000000000000000000000000bb/run.log:760,767,769 P2_BOMBSARAI_TEKI_MOVE (x/z travel, FSM state + animation counter across ticks; P1 Napkid flight component reported separately) | natural lane walk + FSM animation |
| 3. Attacks and receivers | PASS | output/dsw/l27-out/teki-arena15/bb2f00000000000000000000000000bb/run.log:780 P2_BOMBSARAI_TEKI_HIT hp_before=30.000 hp_after=20.000 state_before=0 state_after=22 applied=1 (real InteractBomb via Creature::stimulate on a live Pikmin) | natural engine receiver |
| 4. Death and corpse | PASS | output/dsw/l27-out/teki-arena12/fa0f1285feaf46c3abff5268508f6ffa/run.log:800 TEKI_DEAD, :803 CORPSE_CONFIG (natural carcass Pellet, min_free_slot=0); re-confirmed output/dsw/l27-out/teki-arena15/bb2f00000000000000000000000000bb/run.log:962,965 | natural |
| 5. Actual transport and reward | PASS | output/dsw/l27-out/teki-arena12/fa0f1285feaf46c3abff5268508f6ffa/run.log:845 P2_POD_RECEIPT id=corpse:bombsarai:270001 value=2 new=1 pokos=2 seeds=0; re-confirmed output/dsw/l27-out/teki-arena15/bb2f00000000000000000000000000bb/run.log:1761 | natural |
| 6. Cleanup and re-entry | PASS | output/dsw/l27-out/teki-arena15/bb2f00000000000000000000000000bb/run.log:1762 P2_BOMBSARAI_TEKI_FORGET bound_before=0 corpse_before=1 bound_after=0 corpse_after=0; reset/re-entry run output/dsw/l27-out/teki-arena18/ee5f00000000000000000000000000ee/run.log:776,778 teardown clears both maps (bound_after_reset=0 corpse_after_reset=0) and the carrier re-binds (bound_after=1) | natural (teardown/reset + re-bind) |

Honest labels: the carrier is still a generated P1 `TEKI_Napkid` vehicle, so gate
1 stays UNTESTED (identity is not claimed); the grounded engagement is a labeled
concession (the source dirigibug always hovers, but ordinary FreeMode Pikmin
reject a flying Teki, `piki.cpp:951`/`aiAttack.cpp:189`); the carcass `carry_min`
is lowered 3 -> 1 and the room stages 40 reds (was 20). Gates 4/5 keep the prior
teki-arena12 citations superseded by the same-run lines above.

### Checker output

```
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE27_DEEPSEEK_HANDOFF.md
36 Bomb (role=projectile): ignored (role)
58 BombSarai (role=source):
  1. identity_spawn     ignored [UNTESTED]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   accepted [PASS]
  6. cleanup_reentry    accepted [PASS]
```
