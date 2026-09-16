# Pikmin 2 Waterwraith/Tyre dependent-roller policy (lane 31)

Lane 31 of [the P2 implementation fan-out](PIKMIN2_IMPLEMENTATION_FANOUT.md)
(dispatch #435, coordination #186). Child issue
[#443](https://github.com/4laric/pikmin-randomizer/issues/443), parent
[#175](https://github.com/4laric/pikmin-randomizer/issues/175).

Implementation owner: Codex via shared account `4laric`. Executing
agent/session: opencode (deepseek-v4.1-flash), started 2026-09-13.

This is the first bounded native slice for the lane. It adds a lane-owned,
engine-free policy for the BlackMan (99) / Tyre (98) dependent-roller
relationship and the roller vulnerability gate. It builds on the completed
[source/asset contract](PIKMIN2_WATERWRAITH_ASSETS.md), the batch-2
install/arena glue (<code>experimental/pikmin2_waterwraith_{install,arena}.py</code>)
and the converted assets (16/16 clips). Locomotion, route pathfinding and the
real actor wiring remain open.

## New native files

Branch `opencode/p2-lane31-waterwraith` (local; native origin never pushed),
base `086ed858c2693d9259679177e0eca00a80f57fbf`, head
`baa3c4dbd4c43145edb16e2471ad14be42467d70`:

- `pc_port/pc_p2_waterwraith.h/.cpp` — `P2WaterwraithRig`.
- `tools/p2_waterwraith_test.cpp` — standalone engine-free fixture.

The patch bundle is published at
`native-candidates/waterwraith-roller/` (`waterwraith-roller-full.patch`,
`patches/0001-…`, `provenance.json`).

## Policy contract

Encoded source facts (US GPVE01 rev 0, research rev `632af937`):

- **Single owned child.** `birth()` creates exactly one roller, owned by the
  wraith (`blackMan.cpp:159-167`); a second birth is refused. `dismount()`
  releases ownership and sets EB_Invulnerable.
- **Phases.** Tyre starts in `land` (`tyre.cpp:79`); first floor contact flicks
  and enters `freeze` (`landFloorContact`, `tyreState.cpp:105-115`);
  `moveRestart` -> `move` (`Tyre.cpp:565-572`); a quake while moving -> `freeze`
  (`quakeFreeze`, `tyre.cpp:347-353`).
- **Collision.** The six `tyr1..tyr6` spheres are stickable only while frozen
  (`collisionSticky()`), matching `collisionStOn/Off`.
- **Vulnerability / death gate.** The roller is only damageable while frozen or
  after dismount; death requires health <= 0 **and** the dismounted
  EB_Invulnerable flag (`tyreState.cpp:67-69, :152-153`). `beginDead()` plays
  the `tyre_getoff` path; `finishDead()` removes the child on the end key.
- **Roll.** Angle accumulates by planar distance / 44π scaled by proper fp01
  (`blackMan.cpp:988-995`, `tyreState.cpp:51-65`); a frozen roller is static and
  does not roll.
- **Ride regen.** The wraith regenerates 5 HP/frame while riding
  (`blackMan.cpp:843-848`); `rideRegen()` reports the delta.
- **Shadow.** Ramps from 0.01 to 1 after the fall begins
  (`tyre.cpp:721-727`, `TyreShadow.cpp:217-257`).

All randomness and movement are host-supplied; the policy is deterministic and
engine-free. General parameters are retained: Tyre life 1800, attack damage 10,
retail fp01 rotation speed 25.0.

## Fixture evidence (standalone, real module)

MinGW64 GCC 16.2.0, `-std=gnu++17 -Wall -Wextra -Werror`, warning-clean.
Executable SHA-256 `6f8482ad11b2fe1bb9450ef0fb2f800369ba3ac9200b5b914a6cc340dbe3726b`.

```
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_waterwraith_test.cpp \
    pc_port/pc_p2_waterwraith.cpp -o output/p2_waterwraith_test.exe
```

`PASS WATERWRAITH_POLICY` (exit 0), eight groups: birth/lifetime, state
transitions, collision stickiness, vulnerability gate (riding Land ignored;
freeze applies damage; zero HP without dismount does not kill), dismount + death
sequence, roll angle (44π distance with fp01=1 -> 1 rad; frozen push ignored),
ride regen, and shadow ramp/clamp.

## Fresh arena staging (mandatory baseline adoption)

The converted lane assets were located on this host at
`output/p2-lane-verify/waterwraith/` (BlackMan + Tyre, 16/16 clips + per-pose
`.mod`, manifest policy `P2_WATERWRAITH_1`). A fresh private arena was staged
with the current overlay using the existing batch-2 arena CLI:

```
py -3.12 -m experimental.pikmin2_waterwraith_arena \
    --assets C:/Users/alari/pikmin-local/game/assets \
    --imported C:/Users/alari/pikmin-randomizer/output/p2-lane-verify/waterwraith \
    --output C:/Users/alari/pikmin-randomizer/output/lane31-waterwraith-arena-01
```

Run directory `output/lane31-waterwraith-arena-01/9d9af4131b6e4973a93dbd75127a1304`:

- BlackMan `352001` at `(-60,30,1850)`, Tyre `352002` at `(60,30,1850)`,
  P1 Chappy control `352003` at `(240,30,1500)`; `enemy_count=2`.
- The mandatory starting-squad overlay is present: the staged
  `assets/dataDir/stages/chal0/default.gen` carries **20 `fixture starting
  squad` `ikip` records** (27 generators total), SHA-256
  `534381d41dfca21c4c3e62cb653f182d423b761831fc5200a101249a4c326cff`.
- `arena.json` SHA-256 `20f36bb7fe2d8d4d73a93c0458ad0e989d33943dea98225224dbcd0291a756e9`;
  imported manifest SHA-256 `8bf85791db25c8f09ff67265abf3a6b16221d85abbacb309bbd23e4d0f562b7d`.

This is Python staging only; no source actor is registered, so it does not
claim gameplay. The batch-2 `experimental/pikmin2_batch2_core.py prepare()`
default-installer argument bug (three-arg call to the four-parameter `install`)
blocked the arena CLI; it was fixed here identically to the known batch-4 fix
(`opencode/p2-batch4-root` @ `f59a076`, flagged for lane 01) so the family
CLIs work.

## Visual stage preview (root-side)

`experimental/pikmin2_waterwraith_stage.py` stages the converted sampled poses
for a future native visual consumer, mirroring
`experimental/pikmin2_bigtreasure_stage.py`:

```
py -3.12 -m experimental.pikmin2_waterwraith_stage \
    --imported C:/Users/alari/pikmin-randomizer/output/p2-lane-verify/waterwraith \
    --output C:/Users/alari/pikmin-randomizer/output/lane31-waterwraith-visual-stage-01
```

Real run: **16 clips / 30 poses** (BlackMan 14, Tyre 2). Profile
`p2-waterwraith-visual.txt` (`P2_WATERWRAITH_VISUAL_1`) SHA-256
`7c3b803cfd6097410704a8bcdece55c3f6a5ded2ad996181b6a0008d0740ceac` (680 bytes,
30 `.mod` files copied); `stage.json` SHA-256
`114da8e025e2493862b8e3781756513952b8d39dbf1b27a28b887707fa9c8fda`.
`tests/test_pikmin2_waterwraith_stage.py` -> **8 passed** (policy/format/hash/
subset/budget/output-refusal checks).

The profile grammar (`species <name> <id>` then
`clip <species> <clip> <poses> <sourceFrames> <frames...>`) is staging data
only; the native loader and fixture are the next slice.

## Real-GL visual runtime

The native display consumer now exists, built on the lane-01 reconciled line:

- Native branch `opencode/p2-lane31-integ` @ `5d38a9184644f53f080dfbce317cd7ac518e5f9d`,
  base `opencode/p2-lane01-hardlanes` @ `07f173ae` (Batch E), clean. Commits:
  `d1c15ff1` (visual module + fixture), `a2156640` (host seam + per-species
  draw), `f5274522` (policy cherry-pick), `5d38a918` (CMake TU lines). New
  `pc_port/pc_p2_waterwraith_visual.{h,cpp}` (two-species
  `P2_WATERWRAITH_VISUAL_1` loader/draw), `pc_port/pc_p2_waterwraith_host.{h,cpp}`
  (fixed-route wraith drives the rig), plus `tools/p2_waterwraith_runtime.cpp`
  and `tools/p2_waterwraith_runtime_run.py`.
- Private build `output/native-lane31-integ-build`, `ninja -n` = no work, exe
  SHA-256
  `c580fa59375d46c9c1d904bf36ee00d9ff6f97a4d367bbae678b261d5b2b88b6`.
- Fixture `output/lane31-waterwraith-fixture-02` SHA-256
  `940bcdaaaeb005123d59a5c5b74b41a1f950e4c24a2ad80648c378e46523e8f0`; run
  `output/lane31-waterwraith-runtime-02/f11baf5861c247ec82916ec29f50452c`
  status `passed`, exit 0:
  - `P2_WATERWRAITH_VISUAL_READY species=2 clips=16`
  - `P2_WATERWRAITH_WINDOW size=960x540 pos=373,263`
  - `P2_WATERWRAITH_VISUAL_PLAY BlackMan=kagebozu_walk Tyre=tyre_move`
  - `P2_WATERWRAITH_VISUAL_DRAW species=1`
  - `P2_WATERWRAITH_HOST_PASS ticks=90 distance=240.000 roll=43.4059 phase=Move`
  - `PASS WATERWRAITH_RUNTIME`, capture `waterwraith-visual.ppm`.

The host seam births the single Tyre child, drives the wraith along a straight
route (fp05 retail speed 120), and the rig derives the roll from planar
distance; after the first floor contact the roller freezes and then restarts
into `move`, so the drawn Tyre travels 240 units and rolls 43.4 rad over 90
ticks. This is a display + policy-binding slice: baked sampled poses with
approximate materials, no skeletal playback, no retail events, no source
actor/AI/receivers. Bundle: `native-candidates/waterwraith-visual/`
(`...-full.patch`, `patches/0001..0004`, `provenance.json`).

## Source-correct actor phase machine

`pc_port/pc_p2_waterwraith_actor.{h,cpp}` adds the nine-phase BlackMan machine
(walk/dead/freeze/bend/escape/fall/flick/recover/tired) with host-fed triggers,
host-driven route locomotion (fp05 120, ip01 two-step timer), a
`P2WaterwraithRig`-owned Tyre child, and a `p2_waterwraith_actor_apply_damage`
hook that gates the riding roller on `damageable()` and the dismounted body on
`ownerInvulnerableSet()` (roller Purple-only structurally; the dismounted body
accepts all Pikmin, mirroring `blackMan.cpp:680`).

Branch `opencode/p2-lane31-actor` @ `e8da82aa938c33d9d5564bfdc75bc9c5fd150a8c`
(base `opencode/p2-lane31-integ` @ `5d38a918`, clean). Standalone fixture
(12 groups) `PASS WATERWRAITH_ACTOR`, exe SHA-256
`8ddc0c5eb6dd2aef4ad8b5c77afb6b0c9b80f1485954dd123f8d8441aa76aa20`. Real-GL
actor run `output/lane31-waterwraith-actor-runtime-01/29771a321454432d95c7813934d2c50d`
status `passed`, `P2_WATERWRAITH_ACTOR_PASS ticks=90 distance=345.667 roll=62.5165
phase=walk`, exe `3f2abf65…`, fixture `8d7b032f…`; capture
`waterwraith-actor.ppm`. Bundle `native-candidates/waterwraith-actor/`.

Limits: host-driven route (not the retained-asm pathfinder), host-fed animation
pulses, no source actor/Map/receiver registration.

## Engine-driven actor registration

`pc_port/pc_p2_waterwraith_register.{h,cpp}` registers the actor through the
real room-preview tick/draw (opt-in `P2_WATERWRAITH_ACTOR_1` profile; no-op when
absent), mirroring the BigTreasure host seam. The fixture never calls the
register API: the engine drives the actor.

Branch `opencode/p2-lane31-register` @ `a4526e6a5cb96d1d89e8687fcdd777845de9aa92`
(base `opencode/p2-lane31-actor` @ `e8da82aa`, clean). Real-GL run
`output/lane31-register-runtime-01/65c2a272e7704db0838146aafce10b3a` status
`passed`: `P2_HARDLANES_READY family=Waterwraith register=1 placement=fixed`,
`P2_WATERWRAITH_REGISTER_PASS ticks=90 distance=349.667 roll=63.2400`,
`PASS WATERWRAITH_REGISTER_RUNTIME`; exe `3c5434b9…`, fixture `d76c5246…`.
Additive hooks live in `pc_port/pc_p2_hardlanes.cpp` (tagged for lane 01).
Bundle `native-candidates/waterwraith-register/`.

## Roller attacks, Purple vulnerability receiver and cleanup

`pc_port/pc_p2_waterwraith_attack_policy.h` carries the engine-free combat rules
(Purple-only damage, Purple landing stun, non-Purple roller crush while rolling,
dismounted body acceptance). `pc_port/pc_p2_waterwraith_encounter.{h,cpp}` is the
engine-facing consumer: each source tick it scans the live `pikiMgr` squad
around the registered actor, routes accepted Purple hits through
`p2_waterwraith_actor_apply_damage`, flick-crushes non-Purple Pikmin under the
rolling wraith, and drives the roller death script (dismount -> `tyre_getoff` ->
child removal). The register seam calls it from its tick; `reset` clears it, so
teardown/re-entry leaves no stale actor, child or squad state. A standalone
fixture (`PASS WATERWRAITH_ATTACK_POLICY`, 8 groups, exe `4195a9f8…`) covers the
rules; the runtime fixture drives the real squad.

Branch `opencode/p2-lane31-encounter` @
`5e42ba1d1ef8a0eb46755265ce0eadd84e615025` (base `opencode/p2-lane31-register` @
`a4526e6a`, clean). Real-GL run
`output/lane31-waterwraith-encounter-runtime-06/c05e29fb3ac641019a59212ebc9f53e8`
status `passed`, fixture `ace285f3…` (built at native head `5e42ba1d`):

- `P2_WATERWRAITH_ENCOUNTER_STAGE_A crushes=20 damage=0.0` — non-Purple Pikmin
  under the rollers are flicked but cannot damage the actor.
- `P2_WATERWRAITH_STUN tick=43` -> `P2_WATERWRAITH_ROLLER_ZERO tick=53` ->
  `P2_WATERWRAITH_TYRE_REMOVED tick=56` — real Purple squad hits stun the riding
  roller and deplete the Tyre; the death script dismounts and removes the child.
- `P2_WATERWRAITH_ENCOUNTER_REENTRY ready=1 attached=1` — reset then re-setup
  with no stale state.
- `P2_WATERWRAITH_ENCOUNTER_PASS stuns=1 hits=39 crushes=20 damage=2340.0
  zeroed=1 child_removed=1`, `PASS WATERWRAITH_ENCOUNTER_RUNTIME`, capture
  `waterwraith-encounter.ppm` (`9749616c…`).

Bundle `native-candidates/waterwraith-encounter/`. No new `pc_p2_hardlanes.cpp`
hook hunk; the register hook is reused. The crush uses `InteractFlick` with the
captain as the acting owner (documented adaptation) and the treasure release is
logged only (lane 06 owns the durable reward path).

## Approved-base candidate (rebased onto `f14c6851`)

The full lane was replayed onto the approved native pair, clean, with no
conflicts: `opencode/p2-lane31-approved` @
`923b9443b438c7af3b3a87df7e43d530b6590474` (base
`f14c6851473ac1161be56c8b98f4f905232f3635`). It builds (`output/native-lane31-approved-build`,
`ninja -n pikmin_pc` no work, exe `e3702bbc…`), the engine-free policy test
passes (`7797290f…`), and the encounter runtime re-run reproduces the same
result on this base in
`output/lane31-approved-encounter-runtime-01/dcf3c11092d445f5917704463013dd4b`
(fixture `b482aa97…`, capture `ae3263ee…`).

One integration-shape change was required: adding the six `pc_p2_waterwraith_*`
TUs directly to `PC_PORT_SOURCES` pushes the `pikmin_pc` link over the Windows
command-line threshold, so CMake emits `@CMakeFiles/pikmin_pc.rsp`, which
`scripts/build_pikmin2_fixture.py` fails closed on. The lane therefore builds
them into `libp2_waterwraith_lane31.a` (linked before `pikmin_legacy`), keeping
the executable link inline. If lane 01 prefers the TUs inline, the fixture
builder must gain response-file support instead.

The lane's engine-free fixtures are also registered in the native ctest gate
(`p2_waterwraith_policy_test`, `p2_waterwraith_actor_test`,
`p2_waterwraith_attack_policy_test`; `-UNDEBUG` keeps the assert-based checks
active in Release). `ctest -R waterwraith` = 3/3 passed. This does not change
the `pikmin_pc` game target.

Bundle `native-candidates/waterwraith-approved/` (10-commit series).

## Remaining / next slice

- **Locomotion and route pathfinding are not implemented.** The wraith walk
  route, two-step speed, `findNextRoutePoint` and joint matrix callbacks are
  retained-assembly functions with inferred evaluation order
  (`blackMan.cpp:831+`, `:1938+`); they need a natural-runtime pass.
- **Actor wiring.** No source actor is registered; the real-Map/world seam must
  drive `push()` and read the roller transform once the actor exists. This is
  lane-01-owned integration plus the family actor module.
- **Purple vulnerability is wired for the live squad, not the generic receiver.**
  The family consumer accepts Purple hits at the rig's `damageable()` gate and
  rejects all other Pikmin; the shared lane 10/11 damage adapter and the Purple
  direct-hit contract are still the production route for ordinary combat.
- **BlackMan FSM and signals.** Only the roller-facing wraith phases are
  carried; the full boss FSM (bend/escape/fall/flick/recover/tired) is a later
  slice. Boss phase transitions currently go through `setWraithPhase`.
- **Arena.** The batch-4 room-preview arena used a P1 Chappy proxy and hit the
  invincibility wall; it must be regenerated on the source-correct actor when
  wired. The already-converted assets and install/arena glue are the inputs.
