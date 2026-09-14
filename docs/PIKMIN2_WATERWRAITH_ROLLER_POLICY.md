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

## Remaining / next slice

- **Locomotion and route pathfinding are not implemented.** The wraith walk
  route, two-step speed, `findNextRoutePoint` and joint matrix callbacks are
  retained-assembly functions with inferred evaluation order
  (`blackMan.cpp:831+`, `:1938+`); they need a natural-runtime pass.
- **Actor wiring.** No source actor is registered; the real-Map/world seam must
  drive `push()` and read the roller transform once the actor exists. This is
  lane-01-owned integration plus the family actor module.
- **Purple vulnerability is expressed structurally, not by receiver.** The gate
  is in place; the generic damage/receiver adapter and the Purple direct-hit
  contract are lane 10 / lane 11 and must be wired for ordinary combat.
- **BlackMan FSM and signals.** Only the roller-facing wraith phases are
  carried; the full boss FSM (bend/escape/fall/flick/recover/tired) is a later
  slice. Boss phase transitions currently go through `setWraithPhase`.
- **Arena.** The batch-4 room-preview arena used a P1 Chappy proxy and hit the
  invincibility wall; it must be regenerated on the source-correct actor when
  wired. The already-converted assets and install/arena glue are the inputs.
