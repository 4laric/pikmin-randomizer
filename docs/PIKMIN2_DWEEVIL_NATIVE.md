# Lane 22 dweevil native capture/drop slice

Issue [#170](https://github.com/4laric/pikmin-randomizer/issues/170), child
#447. Root behavior model: `experimental/pikmin2_elemental_behavior.py`
(branch `opencode/p2-lane22-elemental` @ `7dc1a24`). This document records the
first bounded native slice: the four elemental dweevils' treasure
capture/carry/drop policy.

## 1. Scope

Delivered:

- `native/pc_port/pc_p2_dweevil_policy.h` — engine-free, machine-checkable
  policy mirroring the delivered Python model: identity, shared 14-state
  `OtakaraBase` FSM IDs, per-species stimulus, receiver colour immunity,
  theft eligibility, capture health, damage routing, exactly-once drop, fixed
  hazard activation, and the strict `P2_DWEEVIL_NATIVE_1` sidecar reader.
- `native/pc_port/pc_p2_dweevil.{h,cpp}` — sidecar-gated runtime driver for
  source IDs FireOtakara (59), WaterOtakara (60), GasOtakara (61) and
  ElecOtakara (62): a bounded 30 Hz OtakaraBase state subset that acquires a
  nearby unheld treasure, carries/follows it homeward, and drops it exactly
  once on death or a fatal/interrupting receiver.
- Adoptive registration: `PC_PORT_SOURCES` in `native/CMakeLists.txt`,
  `pc_p2_dweevil_setup()` in `pc_p2_preview_setup()`, `pc_p2_dweevil_reset()`
  in the three `TekiMgr` reset paths, and `pc_p2_dweevil_update()` beside the
  existing `pc_p2_king_update()` call in `GameCoreSection::update`.
- `tests/pikmin2_dweevil_policy.cpp` — strict standalone policy test
  (`-Wall -Wextra -Werror`).
- `tests/test_pikmin2_dweevil_native.py` — protocol, synthetic-exactly-once,
  Python-model consistency, and native policy compile/run checks.
- `experimental/pikmin2_dweevil_runtime.py` — root harness mirroring
  `experimental/pikmin2_king_runtime.py` (`build`/`run`/`play`).

Out of scope (see §6): fixed hazard actors, BombOtakara blast/payload reuse,
dweevil visuals, and engine-actor/pellet binding.

## 2. Source anchors

Decompilation revision `632af93787b9c95b63f0c13be32b161375ce3a96`
(`native/pikmin2-research`, read-only), audit
`docs/PIKMIN2_ELEMENTAL_ENEMY_AUDIT.md`:

| Behavior | Anchor |
|---|---|
| Shared 14-state FSM | `OtakaraBase.h:22-39`, `OtakaraBaseState.cpp:14-34` |
| Theft search (alive/pickable/uncaptured/territory/not-carrying) | `OtakaraBase.cpp:395-417` |
| Capture on the `otakara` joint, `mOtakaraLife` health | `OtakaraBase.cpp:472-524` |
| Damage routes to treasure while carried, else the dweevil | `OtakaraBase.cpp:550-574` |
| `fallTreasure` drop; item-drop event type 2 | `OtakaraBase.cpp:530-544,242-304`; `OtakaraBaseState.cpp:680-727` |
| Per-species stimulus (Fire/Bubble/Gas/Denki) | `FireOtakara.cpp:41-46`, `WaterOtakara.cpp:42-47`, `GasOtakara.cpp:41-46`, `ElecOtakara.cpp:41-61` |
| Receiver colour immunity | `src/plugProjectKandoU/interactPiki.cpp:334,445,503,531` |
| Bomb delegated blast/payload | `BombOtakara.cpp:42-87`; `OtakaraBase.cpp:649-677,699-707` |

Production parameter values used by the lane: territory 200 (fp09), Fire/
Water/Elec/Bomb disc `mOtakaraLife` 80 (Gas 100)
(`docs/PIKMIN2_DWEEVIL_ASSETS.md` §4).

## 3. Sidecar contract

Absent `p2-dweevil-native.txt` means the module is inert. A present but
malformed file fails closed (`PC_P2_DWEEVIL invalid profile` + `abort()`).
The strict grammar is shared verbatim with the C++ test and the Python
`protocol()` serializer:

```text
P2_DWEEVIL_NATIVE_1
<unitCount>                                                   # 1..8
<generatorId> <speciesId> <x> <y> <z> <yaw> <otakaraLife>     # x unitCount
<treasureCount>                                               # 0..8
<treasureId> <x> <y> <z> <alive> <pickable> <captured>        # x treasureCount
```

`speciesId` is one of 59/60/61/62/93; ids are unique across units and
treasures; transforms are finite and bounded; flags are 0/1. The optional
fixture injection file `p2-dweevil-inject.txt` is a sequence of
`P2_DWEEVIL_INJECT_1 <tick> <generatorId> <kill|interrupt|replay>` lines and
is never present in a normal run.

## 4. Exactly-once evidence design

The driver keeps one `Unit` per configured dweevil. On each 30 Hz tick it:

1. picks the nearest sidecar treasure satisfying
   `theftDecision(alive, pickable, captured, withinTerritory, carrying)` within
   the capture reach, then logs
   `P2_DWEEVIL_CAPTURE ... otakara_life=<f> health=<f>` and marks the treasure
   captured;
2. while carrying, logs `P2_DWEEVIL_CARRY ... state=item_move` once and moves
   the captured treasure homeward;
3. on death (`kill` injection or `!alive` path) or a fatal/interrupting
   receiver (`interrupt`, or the treasure becoming ineligible) calls the
   policy `drop(carrying, alreadyDropped, reason)`.

`drop` returns `(dropped, carryingAfter) = (false,false)` when not carrying or
when this capture already dropped. A successful drop logs
`P2_DWEEVIL_DROP ... dropped=1 exactly_once=1 total_drops=<n>`; any later drop
attempt for the same capture logs
`P2_DWEEVIL_DROP_SUPPRESSED ... dropped=0 already_dropped=1`. This is the
recovery-cannot-be-duplicated evidence the source audit calls for
(`fallTreasure` on death/stone/earthquake, item-drop event type 2 once).

Two invariants keep the run deterministic:

1. A death drop leaves the unit in the `Dead` state; the drop path never
   rewrites state to `item_drop`, so a dead dweevil cannot resume stealing.
2. A dropped treasure is marked `resolved` and excluded from further theft for
   the bounded run, so a second kill/replay of the same capture cannot produce
   a fresh capture and a fresh drop.

The startup `p2-dweevil-native.txt` profile is intentionally inert (its
treasure is not pickable); the fixture installs the pickable scenario profiles
only after the squad/window baseline is observed. The harness therefore asserts
exactly two captures, two carries, exactly two real drops (death and
interruption, each `total_drops=1`), and exactly two `DROP_SUPPRESSED` markers
(the death replay and the post-interruption kill). A third drop or an extra
capture fails the gate.

## 5. Fixture baseline

`experimental/pikmin2_dweevil_runtime.py run` stages the original P1 practice
course into the existing `chal0` experimental slot using
`scripts.preview_pikmin2_room.overlay`, adds the standard 5-red/5-blue squad
overlay, sets `p2-cargo-free.txt`, and launches the private replacement-main
fixture with `PIKMIN_P2_ROOM_WINDOW=960x540`. It is the #404 baseline: 960x540
centred window and a live squad, recorded as
`P2_DWEEVIL_BASELINE red=5 blue=5` and
`Experimental preview window set to 960x540 windowed and centered`.

Scenario 1 injects `kill 40` + `replay 100` (death drop, then suppressed
replay). Scenario 2 injects `interrupt 40` + `kill 100` (fatal-receiver drop,
then suppressed death). All placements and ticks are labeled injections. This
worker only builds the fixture; the coordinator owns the serialized GL run.

Approximations, labeled:

- **No engine actor binding.** This base (`57bb1a4e`) predates the batch-2
  dweevil arena; there is no P2 dweevil actor or committed dweevil visual in
  this worktree. The driver is a policy-driven actor-local simulation over a
  sidecar-staged treasure set, not a `TEKI_Chappy` vehicle driven through
  `Pellet::startStickTeki`/`doCarry`/`endStickTeki`.
- **Capture reach and carry speed** (`kPickRadius` 30, `kCarryStepPerTick`
  0.5) are lane approximations; the source collision reach and item-move speed
  are not pinned by the audit.
- **Elemental immunity is policy-only**: `stimulusFor`/`pikminImmune`/
  `receiverAccepts` live in the header and are not routed into any engine
  damage path. No generic damage/physics, receiver, reward or save code changed.

## 6. Remaining work / BLOCKED

- **Fixed hazards** Hiba (20), GasHiba (21), ElecHiba (22): header policy
  (`hazardActivate`, disc wait times) only; no actor, linked bridge/gate owner,
  or two-node ElecHiba team.
- **BombOtakara (93)** is excluded from the runtime driver: it consumes the
  shared Bomb blast/projectile contract owned by the projectiles lane (#169).
  `stimulusFor(Bomb)=StimNone` is recorded; payload birth, `mCarrier` linkage,
  bittered/earthquake detonation and cleanup stay BLOCKED.
- **Engine binding and cleanup**: treasure capture onto a real
  `Creature`/`Pellet` (`startStickTeki`), real death receiver, corpse and
  re-entry cleanup, and visuals remain open. Elemental discharge effects are
  not spawned.
- No natural gameplay acceptance is claimed; the bounded injected GL run below
  passed, but engine actor binding and cleanup remain open.

## 7. Runtime evidence (bounded, labeled injections)

GL run `output/p2-lane22-dweevil-run-02/dweevil/e1a752dc7b1341b98ec271270bc388d4`
(fixture `output/p2-lane22-dweevil-fixture-02/build/fixture.exe` SHA-256
`ad9d8b130691ca65b14ca2d78a40c5c9ce1fc682e399b14c2fe6d4480aecc8a5`), validator
all-true (`completion`, `baseline`, `window`, `captures`, `carries`,
`capture_a/b`, `death_drop`, `interrupt_drop`, `suppressed_death`,
`suppressed_interrupt`, `exactly_two_drops`, `exactly_two_suppressed`,
`no_rewards`):

```text
P2_DWEEVIL_DROP generator=235300 treasure=900001 reason=death dropped=1 exactly_once=1 total_drops=1
P2_DWEEVIL_DROP_SUPPRESSED generator=235300 treasure=900001 reason=death dropped=0 already_dropped=1
P2_DWEEVIL_DROP generator=235300 treasure=900002 reason=interruption dropped=1 exactly_once=1 total_drops=1
P2_DWEEVIL_DROP_SUPPRESSED generator=235300 treasure=900002 reason=death dropped=0 already_dropped=1
PASS P2_DWEEVIL_RUNTIME bounded_behavior_tick
```

The captures, carries and kill/interrupt triggers are labeled injections; the
base is a 5-red/5-blue squad at 960×540. This is not natural dweevil gameplay.
