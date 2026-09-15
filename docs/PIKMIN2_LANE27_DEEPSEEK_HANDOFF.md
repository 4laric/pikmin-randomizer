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

| Gate | Status | Evidence / label |
|---|---|---|
| 1 Exact identity and spawn | source-backed N/A (unchanged) | Still the pinned opt-in profile (`P2_BOMBSARAI_ARENA_1`); no ordinary spawn binding. |
| 2 Autonomous movement and animation | PARTIAL (unit only) | Animated capture joint now follows the carrier hover bob + yaw (new `followJoint` + `P2BombSaraiJoint`); carrier horizontal `walkToTarget` still pinned/blocked. |
| 3 Attacks and receivers | UNTESTED (unchanged) | Blast still routes to instrumented receivers, not live creatures (lane 10 boundary). |
| 4 Death and corpse | source-backed N/A (unchanged) | Existing FSM death/corpse decision paths preserved, not re-exercised this slice. |
| 5 Actual transport and reward | source-backed N/A | Out of this slice's scope; no transport/reward seam touched. |
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

| Gate | Status | Evidence / label |
|---|---|---|
| 1 Exact identity and spawn | source-backed N/A | Still the pinned opt-in profile; no ordinary BombSarai actor registered. |
| 2 Autonomous movement and animation | PASS (joint-follow observed) | `P2_BOMBSARAI_JOINT_FOLLOW` in all three scenarios on the hover-moving carrier. |
| 3 Attacks and receivers | PARTIAL | Blast routes to instrumented profile receivers (teki 500/navi+piki 10); live creatures still lane 10. |
| 4 Death and corpse | PARTIAL | Death scenario executes zero-velocity drop + dead-carrier attribution; no live corpse/transport. |
| 5 Actual transport and reward | source-backed N/A | Out of slice scope. |
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
