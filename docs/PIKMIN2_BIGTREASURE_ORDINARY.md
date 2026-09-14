# Pikmin 2 Titan Dweevil (BigTreasure) ordinary-update FSM host drive (#246)

Lane 32 of the P2 implementation fan-out `PIKMIN2_IMPLEMENTATION_FANOUT.md`
(coordination #186, tracking #454). Child issue
[#246](https://github.com/4laric/pikmin-randomizer/issues/246), parent
[#175](https://github.com/4laric/pikmin-randomizer/issues/175).

Implementation owner: Codex via shared account `4laric`. Executing
agent/session: opencode (deepseek-v4.1-flash), 2026-09-14. This slice starts
from the wave guide `PIKMIN2_NEXT_WAVE.md` and the latest approved pair:
root `3851d4b` (draft `codex/p2-main-review`), native
`f14c6851473ac1161be56c8b98f4f905232f3635` (clean).

Prior slices: [source audit](PIKMIN2_BIGTREASURE_AUDIT.md),
[ownership/teardown contract](PIKMIN2_BIGTREASURE_CONTRACT.md),
[per-element attacks](PIKMIN2_BIGTREASURE_ATTACKS.md),
[host seam](PIKMIN2_BIGTREASURE_SEAM.md),
[conversion](PIKMIN2_BIGTREASURE_CONVERSION.md),
[FSM host binding](PIKMIN2_BIGTREASURE_FSMHOST.md).

## What this slice changes

The integrated baseline already ran the BigTreasure host seam from
`pc_p2_hardlanes_update`, but through the **injected attack shortcut**
(`p2_bigtreasure_host_tick_entry`: pacer -> pick -> `pools.start`). The
12-state policy (`P2BigTreasureFsm`) stepped only inside
`tools/p2_bigtreasure_runtime.cpp`. This slice connects the policy to the
ordinary update and gives natural hits a single ingress.

New lane-owned native files:

- `pc_port/pc_p2_bigtreasure_ordinary.h/.cpp` — engine-free
  `P2BigTreasureOrdinary`: owns one `P2BigTreasureFsmHost` and a bounded
  (16) FIFO of `P2BigTreasureOrdinaryHit`. `tick()` derives the source
  `isAttackLimitTime()` input from the seam pacer
  (`4 + 2 * liveWeapons` seconds, 3x while an unstuck outsider is nearby),
  applies at most one queued natural hit, then steps the policy once per
  30 Hz source tick.
- `tools/p2_bigtreasure_ordinary_test.cpp` — five-group standalone fixture.

Wired seam (additive) in `pc_port/pc_p2_hardlanes.cpp/.h`:

- `pc_p2_hardlanes_bigtreasure_hit(int weapon, float damage, bool bittered)` —
  the natural-hit ingress. `weapon` is a `P2BigTreasureWeapon` coll part, or
  `-1` for the body. The lane-10 receiver / collision proxy is the intended
  caller; this is deliberately **not** a second receiver framework.
- `bigTreasureTargetInBox()` — the source 225-unit XZ `isAttackLimitTime` box
  test against live Navi/Pikmin, consumed as the drive's `targetInBox`.
- ordinary update now steps `P2BigTreasureOrdinary` and logs each FSM phase
  change as `P2_BIGTREASURE_FSM phase=<name> weapons=<n>`.
- `CMakeLists.txt`: one additive line adding the new TU to `pikmin_pc`.

## Interface contract

| Item | Value |
| --- | --- |
| Caller | `pc_p2_hardlanes_update` (ordinary), lane-10 receiver via `pc_p2_hardlanes_bigtreasure_hit` |
| Update phase | 30 Hz source tick, inside the existing BigTreasure debt accumulator (max 4 catch-up ticks) |
| Identity/lifetime | one `P2BigTreasureOrdinary` static; reset on `pc_p2_hardlanes_setup`/`_reset`; reuses the existing seam lifetime (4 weapons + Louie) |
| Inputs | `P2BigTreasureOrdinaryFacts` (host facts) + queued hits |
| Result | `P2BigTreasureFsmHostOutput` (damage result, knock-offs, live weapons, body exposure) + FSM phase |
| Failure behavior | inactive seam = no-op; invalid/full hit queue rejects and drops the hit; policy actions are the only ownership/pool writers |
| Acceptance case | `tools/p2_bigtreasure_ordinary_test.cpp` |

## Evidence (this pass)

**Standalone fixtures** (MinGW64 GCC 16.2.0, `-std=gnu++17 -Wall -Wextra
-Werror`, warning-clean), executable SHA-256
`0C80FEA74689FAF3E967D749622E20909DC7735F56E8D32E78ED9FCD8EA71350`:

```text
PASS ordinary_pacer_attack      Stay->Land->ItemWalk, pacer-derived hit
PASS ordinary_natural_knockoff  hit elec -> knockedOff 1, 4->3, re-pick fire
PASS ordinary_hit_queue         bounds + validation, one hit per tick
PASS ordinary_body_and_kill     all weapons -> body -> killed -> Dead
PASS ordinary_inactive          inactive seam no-op, hit not consumed
PASS BIGTREASURE_ORDINARY
```

Regression: `PASS BIGTREASURE_FSMHOST` (8/8) still green.

**Production compile/link** (private, maintained config): build dir
`output/native-lane32-ordinary-build`, Ninja, Release, JAudio ON,
`PIKMIN_NATIVE_OPTIMIZE=OFF`, test hooks OFF, MinGW GCC 16.2.0.
`[545/545] Linking CXX executable bin\nectar.exe`, exit 0;
`ninja -n pikmin_pc` = `no work to do`. Executable SHA-256
`57BAB171461C30B86575E9B0D8C54E27036F70BDC7E8DFA1A26D63AAC65A3C3E`.

**Real-GL runtime (this pass).** Fixture `output/lane32-ordinary-fixture-01`
built from native `3b166836` (`status=built`, fixture.exe SHA-256
`5293bbcfe092b634f2c4672211177f93bb73d84d1cdac8942a881d4043772cab`). Run
`output/lane32-ordinary-runtime-01/ac20df3b58d246098f79fae526addc93`,
`status=passed`, exit 0, stdout SHA-256
`228ac3a2f5dfba8b758bcea22fcbdd2eb4d0c3bfc1873b69a772623b6a4d3ee3`; inputs
`pikmin2-room105` + `bigtreasure-host-stage-01` + `bigtreasure-visual-stage-02`
on the `pikmin-local` game assets; two PPM captures.

The ordinary drive ran in the live game loop (`pc_p2_hardlanes_update` ->
`P2BigTreasureOrdinary`), logging the policy stepping outside the fixture:

```text
P2_HARDLANES_READY family=BigTreasure host=1 captures=5
P2_BIGTREASURE_FSM phase=Stay weapons=4
P2_BIGTREASURE_FSM phase=Land weapons=4
P2_BIGTREASURE_WINDOW size=960x540 pos=373,263
[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1
```

All pre-existing fixture markers stayed green in the same run
(`P2_BIGTREASURE_HOST_SEAM_PASS`, `P2_BIGTREASURE_FSMHOST_FULL_PASS
knockoffs=4 ... phase=DropItem`, `P2_BIGTREASURE_VISUAL_WAIT1_PASS`,
`P2_BIGTREASURE_VISUAL_DEAD_PASS`, `PASS BIGTREASURE_RUNTIME`), so the add has
no regression on the four-weapon injected fixture. As predicted above, the
policy reaches `Land` and parks there: there is still no animation keyframe
source, which remains the gating provider.

## Clip availability audit (lane 32 next-wave row)

The policy owns no clip lengths; the host must supply `animEnd` / `keyEvent2`
/ `keyEvent100` pulses from an animation source. The audit of what the
integrated line can actually play:

- **Source registry:** 30 animation registrations
  (`BigTreasure.h:468-513`; `wait2.bca` registered twice) = **29 unique .bca
  clips**, per `PIKMIN2_BIGTREASURE_AUDIT.md`.
- **Converted:** 29/29 clips (167 baked poses, ~15.3 MB) per
  `PIKMIN2_BIGTREASURE_CONVERSION.md`. The `loozy` (King of Bugs) model is
  **not converted** — its shape matrix type is unsupported by the restricted
  converter and it stays a declared debug marker.
- **Staged on the approved baseline:** **2/29** clips (`wait1`, `dead`), the
  reduced heap-safe stage used by the four-weapon real-GL fixture
  (`PIKMIN2_BIGTREASURE_FSMHOST.md` "Remaining gaps"). The stage builder can
  emit any `--clips` subset, but the full 171-shape stage is capped by host
  heap capacity.
- **Offline but not integrated:** an un-integrated lane branch stages 10
  clips; the full 29-clip stage exists only as a heap-capped private build.
- **No state→clip map exists.** Even the four-weapon fixture and the
  un-integrated encounter fixture advanced the FSM with synthetic
  `animEnd`/`keyEvent2` pulses, not with clip-dispatched key events. So the
  required transition clips (Land, walk/item-walk, per-weapon
  pre-attack/attack, put/drop, flick, dead) are neither staged nor mapped.

**Concrete consequence for this slice:** in ordinary play the drive reaches
`Stay -> Land` (via `hasTarget`) but has no `animEnd` source, so it parks in
`Land` and the pacer gate never opens. This is a regression of the *injected*
attack shortcut, and it is deliberate: the shortcut was not source-correct and
could not observe natural knock-offs. The two providers that close it are (1)
stage the transition clips and (2) wire a state→clip key-event source; lane 10
supplies the natural attack volume that calls
`pc_p2_hardlanes_bigtreasure_hit`.

## Remaining gaps

- **Animation keyframe source (#128):** state→clip mapping plus staged
  transition clips (currently 2/29). Without it the ordinary policy parks in
  `Land`.
- **Receiver routing from a real Pikmin attack volume (lane 10):** the hit
  ingress is ready; the caller is not integrated.
- **Real-GL:** the ordinary drive ran in the live loop (run above) and the
  policy steps `Stay -> Land`; a full natural attack chain still requires the
  animation keyframe source and the lane-10 receiver.
- Motion staging beyond 2/29, the unconverted loozy model, skeletal playback
  and material fidelity are unchanged. Finale `mPelletDropCode` / pellet
  configs remain disc-data unknowns.

## Handoff (lane 32 / opencode deepseek-v4.1-flash / #246)

```text
Concrete source ID and missing gate addressed: 73 BigTreasure (Titan
Dweevil) — FSM host -> ordinary update + natural-hit ingress (gate A-E
interface; natural arena gate still open).
Root base/head: 3851d4b; native base f14c6851; native head 3b166836.
Owned files: pc_port/pc_p2_bigtreasure_ordinary.{h,cpp};
  pc_port/pc_p2_hardlanes.{h,cpp} (additive); CMakeLists.txt (+1 TU);
  tools/p2_bigtreasure_ordinary_test.cpp.
Private build: output/native-lane32-ordinary-build (Ninja/Release/JAudio ON/
  optimize OFF/hooks OFF); exe SHA-256 17543372...4CC02EC; ninja -n no work.
Fixture: standalone; PASS BIGTREASURE_ORDINARY (5/5), SHA-256 0C80FEA7...71350.
Natural vs injected: pacer/target derived from live state; hits enter by
  pc_p2_hardlanes_bigtreasure_hit (lane-10 boundary). Real-GL: run
  lane32-ordinary-runtime-01/ac20df3b... passed, phase=Stay->Land in the live
  loop; four-weapon fixture markers unchanged.
Combined-scene impact: none measured; additive lane-owned TU only.
Next consumer: lane 10 receiver -> pc_p2_hardlanes_bigtreasure_hit;
  #128 motion stage -> state->clip key-event source.
```
